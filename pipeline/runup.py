"""Wave run-up and total water level along Pacific Beach + Mission Beach.

Total water level (TWL) = still water (tide + extra water) + wave run-up.

Run-up: Stockdon et al. (2006), "Empirical parameterization of setup,
swash, and runup", Coastal Engineering 53, 573-588. R2 = the height above
still water that the highest 2% of waves rush up the beach:

    setup  = 0.35 * slope * sqrt(H0 * L0)          (average water level rise)
    swash  = sqrt(H0 * L0 * (0.563 * slope^2 + 0.004))  (up-and-down rush)
    R2     = 1.1 * (setup + swash / 2)
    (very flat, "dissipative" beaches: R2 = 0.043 * sqrt(H0 * L0))

  H0    deep-water wave height. CDIP MOP gives height at ~10 m depth, so we
        "un-shoal" it with linear wave theory (waves grow as they reach
        shallow water; we reverse that).
  L0    deep-water wavelength = g T^2 / (2 pi), T = peak period.
  slope beach face slope from the 2024 lidar (shore_profiles.py).

Each 100 m stretch is then compared with its barrier crest:
  clear     TWL more than 2 ft below the crest
  reaches   within 2 ft of the crest: waves reach the top, spray / splash
  over      TWL above the crest: water over the boardwalk / ridge

Usage (backtest, measured tides + CDIP nowcast/hindcast):
  python pipeline/runup.py --start 2026-10-25 --end 2026-10-29
Usage (a logged forecast snapshot):
  python pipeline/runup.py --snapshot forecast_log/2026/11/2026-11-13T2241Z
"""

from __future__ import annotations

import argparse
import warnings
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from forecast_logger import MOP_URL
from noaa_tides import PROCESSED_DIR, PROJECT_ROOT, fetch_noaa, to_frame

G = 9.81
M_TO_FT = 3.28084
REACHES_MARGIN_FT = 2.0
HINDCAST_END = pd.Timestamp("2025-03-31 23:00", tz="UTC")  # CDIP: hindcast before, nowcast after


# ---------- physics ----------

def wavenumber(T: np.ndarray, h: float) -> np.ndarray:
    """Solve the linear dispersion relation w^2 = g k tanh(k h) for k."""
    w = 2 * np.pi / T
    k = w**2 / G  # deep-water guess
    for _ in range(50):
        k = k - (G * k * np.tanh(k * h) - w**2) / (G * np.tanh(k * h) + G * k * h / np.cosh(k * h) ** 2)
    return k


def deshoal(H: np.ndarray, T: np.ndarray, h: float) -> np.ndarray:
    """Wave height at depth h -> equivalent deep-water height (linear theory)."""
    k = wavenumber(T, h)
    c = 2 * np.pi / T / k
    n = 0.5 * (1 + 2 * k * h / np.sinh(2 * k * h))
    cg, cg0 = n * c, G * T / (4 * np.pi)
    return H / np.sqrt(cg0 / cg)


def stockdon_r2(H0: np.ndarray, T: np.ndarray, slope: np.ndarray) -> np.ndarray:
    L0 = G * T**2 / (2 * np.pi)
    HL = np.sqrt(H0 * L0)
    setup = 0.35 * slope * HL
    swash = np.sqrt(H0 * L0 * (0.563 * slope**2 + 0.004))
    r2 = 1.1 * (setup + swash / 2)
    iribarren = slope / np.sqrt(H0 / L0)
    return np.where(iribarren < 0.3, 0.043 * HL, r2)


# ---------- inputs ----------

def waves_archive(points: list[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Hourly CDIP MOP waves (hindcast before Apr 2025, nowcast after)."""
    warnings.filterwarnings("ignore")
    frames = []
    for point in points:
        for product in (["hindcast"] if end <= HINDCAST_END else
                        ["nowcast"] if start > HINDCAST_END else ["hindcast", "nowcast"]):
            ds = xr.open_dataset(MOP_URL.format(int(point[1:]), product))
            sub = ds[["waveHs", "waveTp"]].sel(waveTime=slice(start.tz_localize(None), end.tz_localize(None)))
            df = sub.to_dataframe()[["waveHs", "waveTp"]].rename(columns={"waveHs": "wave_height_m",
                                                                         "waveTp": "peak_period_s"})
            df.index = df.index.tz_localize("UTC")
            frames.append(df.assign(point=point))
            ds.close()
    return pd.concat(frames).rename_axis("time_utc").reset_index()


def still_water_measured(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Measured La Jolla water level (ft MLLW) = tide + extra water, as it happened."""
    obs = to_frame(fetch_noaa("9410230", "water_level", start.date(), end.date()))["v"]
    return obs.rename("still_water_ft")


def from_snapshot(snapshot: Path, model: str) -> tuple[pd.DataFrame, pd.Series]:
    waves = pd.read_csv(snapshot / "waves.csv.gz", parse_dates=["time_utc"])
    waves = waves[waves.model == model][["time_utc", "point", "wave_height_m", "peak_period_s"]]
    tides = pd.read_csv(snapshot / "tides.csv.gz", parse_dates=["time_utc"])
    tides = tides[tides.station == 9410230].set_index("time_utc")["still_water_ft"]
    return waves, tides


# ---------- combine ----------

def total_water_level(waves: pd.DataFrame, still: pd.Series, profiles: pd.DataFrame) -> pd.DataFrame:
    """Hourly TWL per point. Waves (hourly or 3-hourly) are interpolated to each hour."""
    hours = pd.date_range(max(waves.time_utc.min(), still.index.min()).ceil("h"),
                          min(waves.time_utc.max(), still.index.max()).floor("h"), freq="h")
    sw = still.sort_index()
    sw = sw[~sw.index.duplicated()].reindex(sw.index.union(hours)).interpolate("time").reindex(hours)
    rows = []
    for point, w in waves[waves.point.isin(profiles.index)].groupby("point"):
        prof = profiles.loc[point]
        if not np.isfinite(prof.beach_slope):
            continue
        w = w.set_index("time_utc").sort_index()[["wave_height_m", "peak_period_s"]]
        w = w.reindex(w.index.union(hours)).interpolate("time").reindex(hours)
        H0 = deshoal(w.wave_height_m.to_numpy(), w.peak_period_s.to_numpy(), prof.depth_m)
        r2_ft = stockdon_r2(H0, w.peak_period_s.to_numpy(), prof.beach_slope) * M_TO_FT
        rows.append(pd.DataFrame({
            "time_utc": hours, "point": point, "wave_height_ft": w.wave_height_m.to_numpy() * M_TO_FT,
            "period_s": w.peak_period_s.to_numpy(), "still_water_ft": sw.to_numpy(), "runup_ft": r2_ft,
            "twl_ft": sw.to_numpy() + r2_ft, "crest_ft": prof.crest_ft, "barrier": prof.barrier}))
    out = pd.concat(rows, ignore_index=True)
    out["margin_ft"] = out.crest_ft - out.twl_ft  # positive = water stays below the crest
    out["category"] = np.select([out.margin_ft < 0, out.margin_ft < REACHES_MARGIN_FT],
                                ["over", "reaches"], "clear")
    return out


def summarize(twl: pd.DataFrame) -> pd.DataFrame:
    """Worst moment per point."""
    worst = twl.loc[twl.groupby("point").margin_ft.idxmin()].set_index("point")
    worst["time_local"] = worst.time_utc.dt.tz_convert("America/Los_Angeles").dt.strftime("%a %b %d %-I %p")
    return worst[["time_local", "wave_height_ft", "period_s", "still_water_ft", "runup_ft", "twl_ft",
                  "crest_ft", "margin_ft", "category"]].round(2)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=date.fromisoformat)
    p.add_argument("--end", type=date.fromisoformat)
    p.add_argument("--snapshot", type=Path, help="forecast_log run folder (uses its frozen forecast)")
    p.add_argument("--model", default="forecast", choices=["forecast", "ecmwf_fc"])
    args = p.parse_args()

    profiles = pd.read_csv(PROCESSED_DIR / "shore_profiles.csv").set_index("point")
    profiles = profiles[profiles.barrier.isin(["ridge", "rising ground"])]
    if args.snapshot:
        waves, still = from_snapshot(args.snapshot, args.model)
        label = f"snapshot {args.snapshot.name} ({args.model})"
    else:
        start = pd.Timestamp(args.start, tz="UTC")
        end = pd.Timestamp(args.end + timedelta(days=1), tz="UTC")
        waves = waves_archive(profiles.index.tolist(), start, end)
        still = still_water_measured(start, end)
        label = f"{args.start} to {args.end} (measured tides, CDIP archive)"

    twl = total_water_level(waves, still, profiles)
    worst = summarize(twl)
    print(f"Run-up check, {label}")
    print(worst.to_string())
    print("\nStretches by worst category:", worst.category.value_counts().to_dict())
    tag = args.snapshot.name if args.snapshot else f"{args.start}_{args.end}"
    out = PROCESSED_DIR / "runup" / f"twl_{tag}_{args.model if args.snapshot else 'archive'}.csv"
    out.parent.mkdir(exist_ok=True)
    twl.round({c: 3 for c in twl.select_dtypes("number").columns}).to_csv(out, index=False)
    print(f"Saved {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
