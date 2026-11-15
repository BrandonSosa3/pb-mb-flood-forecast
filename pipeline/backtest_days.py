"""Run the full model on a list of past days, exactly as the live site rates a day.

For each day (local date):
  bay side   Mission Bay level = NOAA 9410196 prediction + La Jolla measured extra water
  ocean side wave run-up per beach stretch from measured La Jolla water level + CDIP MOP
             hindcast/nowcast waves (what the waves really were)
  rain       San Diego airport hourly rain within 3 h of the day's highest bay tide
  -> area ratings with risk.area_status + risk.with_rain (berm-holds headline and berm-fails)

This is a "perfect forecast" test: it uses what the water and waves actually did, so it checks
the flood model and thresholds, not the weather/wave forecasts (the live log checks those).

Days come from docs/evidence/backtest_days.csv (date, why). Output:
docs/evidence/backtest_days_model.csv (one row per day and area) + a printed table.

Usage: python pipeline/backtest_days.py
"""

from __future__ import annotations

import warnings
from datetime import timedelta

import numpy as np
import pandas as pd
import xarray as xr

from forecast_logger import MOP_URL
from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from risk import RAIN_WINDOW_H, area_status, load_curves, mission_bay_still_water, with_rain
from runup import HINDCAST_END, still_water_measured, total_water_level

DAYS = PROJECT_ROOT / "docs" / "evidence" / "backtest_days.csv"
OUT = PROJECT_ROOT / "docs" / "evidence" / "backtest_days_model.csv"
TZ = "America/Los_Angeles"


def waves_for_days(points: list[str], days: list[pd.Timestamp]) -> pd.DataFrame:
    """Hourly CDIP MOP waves for each local day (+/- 3 h), opening each point's archive once."""
    warnings.filterwarnings("ignore")
    frames = []
    for point in points:
        opened = {}
        for d in days:
            t0 = (d - pd.Timedelta(hours=3)).tz_convert("UTC")
            t1 = (d + pd.Timedelta(hours=27)).tz_convert("UTC")
            product = "hindcast" if t1 <= HINDCAST_END else "nowcast"
            if product not in opened:
                opened[product] = xr.open_dataset(MOP_URL.format(int(point[1:]), product))
            ds = opened[product]
            sub = ds[["waveHs", "waveTp"]].sel(waveTime=slice(t0.tz_localize(None), t1.tz_localize(None)))
            df = sub.to_dataframe()[["waveHs", "waveTp"]].rename(columns={"waveHs": "wave_height_m", "waveTp": "peak_period_s"})
            df.index = df.index.tz_localize("UTC")
            frames.append(df.assign(point=point, day=d.date()))
        for ds in opened.values():
            ds.close()
    return pd.concat(frames).rename_axis("time_utc").reset_index()


def main() -> None:
    days_in = pd.read_csv(DAYS, comment="#")
    days = [pd.Timestamp(d, tz=TZ) for d in days_in.date]
    curves = load_curves()
    profiles = pd.read_csv(PROCESSED_DIR / "shore_profiles.csv").set_index("point")
    profiles = profiles[profiles.barrier.isin(["ridge", "rising ground"])]
    rain = pd.read_csv(PROCESSED_DIR / "hourly_rain_KSAN.csv.gz", parse_dates=["time_utc"]).set_index("time_utc").rain_in

    print(f"Waves for {len(days)} days at {len(profiles)} beach stretches ...")
    waves = waves_for_days(profiles.index.tolist(), days)

    rows = []
    for d, why in zip(days, days_in.why):
        t0, t1 = d.tz_convert("UTC"), (d + pd.Timedelta(days=1)).tz_convert("UTC")
        bay = mission_bay_still_water(d.date() - timedelta(days=1), d.date() + timedelta(days=1)).tz_convert(TZ)
        bay = bay[(bay.index >= d) & (bay.index < d + pd.Timedelta(days=1))]
        bay_peak, bay_time = float(bay.max()), bay.idxmax()
        still = still_water_measured(t0 - pd.Timedelta(hours=3), t1 + pd.Timedelta(hours=3))
        w = waves[waves.day == d.date()].drop(columns="day")
        twl = total_water_level(w, still, profiles)
        twl = twl[(twl.time_utc >= t0) & (twl.time_utc < t1)]
        margins = twl.groupby("point").margin_ft.min()
        worst = twl.loc[twl.margin_ft.idxmin()]
        near = rain[(rain.index >= bay_time - pd.Timedelta(hours=RAIN_WINDOW_H)) &
                    (rain.index <= bay_time + pd.Timedelta(hours=RAIN_WINDOW_H))].sum()
        for name in curves["areas"]:
            s = area_status(name, curves, bay_peak, margins)
            risk, ponding = with_rain(s["risk"], float(near), s["drain_buildings"])
            fail, _ = with_rain(s["risk_if_berm_fails"], float(near), s["drain_buildings"])
            rows.append({
                "date": str(d.date()), "why": why, "area": name, "risk": risk, "risk_if_berm_fails": fail,
                "cause": s["cause"] + ("+rain" if ponding else ""), "bay_peak_ft": round(bay_peak, 2),
                "bay_peak_time": bay_time.strftime("%-I:%M %p"), "rain_near_tide_in": round(float(near), 2),
                "props_reached": s["buildings"], "props_below_water": s["drain_buildings"],
                "props_if_berm_fails": s["buildings_if_berm_fails"],
                "stretches_over": s.get("stretches_over"), "stretches_reach": s.get("stretches_reach_top"),
                "max_wave_ft": round(float(twl.wave_height_ft.max()), 1),
                "worst_margin_ft": round(float(worst.margin_ft), 1),
                "worst_time": worst.time_utc.tz_convert(TZ).strftime("%-I %p"),
            })
        print(f"  {d.date()} bay {bay_peak:.2f} ft · waves up to {twl.wave_height_ft.max():.1f} ft · "
              f"over {int((margins < 0).sum())}, reach {int(((margins >= 0) & (margins < 2)).sum())} · rain {near:.2f} in")
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    piv = out.pivot_table(index="date", columns="area", values="risk", aggfunc="first")
    print(piv.to_string())


if __name__ == "__main__":
    main()
