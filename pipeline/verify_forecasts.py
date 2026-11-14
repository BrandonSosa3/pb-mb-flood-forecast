"""Check every logged wave forecast against what actually happened.

"What happened" = CDIP MOP *nowcast*: the same Scripps wave model at the same 66 beach points,
but driven by measured buoy data instead of a weather forecast. It is the closest thing to a
measurement at each 100 m stretch of beach (real buoys are offshore, not at each stretch).

For every snapshot in forecast_log/ and each wave model ("forecast" = NOAA-driven,
"ecmwf_fc" = ECMWF-driven), we pair each forecast value with the nowcast at the same point and
hour, and measure:
  bias  = average of (forecast - nowcast): negative = the model forecasts waves too small
  ratio = forecast / nowcast as a percent (e.g. 75% = forecast is a quarter too small)
  error = average size of the miss, ignoring sign (mean absolute error)
split by how far ahead the forecast was made (lead time).

Outputs:
  data/processed/wave_verification.csv   every matched pair
  docs/evidence/wave_check.md            plain summary (rewritten each run)

Usage: python pipeline/verify_forecasts.py
"""

from __future__ import annotations

import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import xarray as xr

from forecast_logger import LOG_DIR, MOP_MODELS, MOP_POINTS, MOP_URL
from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

M_TO_FT = 3.28084
LEAD_BINS = [0, 12, 24, 48, 96]  # hours ahead
LEAD_LABELS = ["0–12 h", "12–24 h", "1–2 days", "2–4 days"]
OUT_CSV = PROCESSED_DIR / "wave_verification.csv"
OUT_MD = PROJECT_ROOT / "docs" / "evidence" / "wave_check.md"
MODEL_NAMES = {"forecast": "NOAA-driven", "ecmwf_fc": "ECMWF-driven"}


def snapshots() -> list[tuple[pd.Timestamp, pd.DataFrame]]:
    out = []
    for d in sorted(LOG_DIR.glob("*/*/*Z")):
        f = d / "waves.csv.gz"
        if f.exists():
            issued = pd.Timestamp(datetime.strptime(d.name, "%Y-%m-%dT%H%MZ"), tz="UTC")
            out.append((issued, pd.read_csv(f, parse_dates=["time_utc"])))
    return out


def nowcast(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Hourly CDIP MOP nowcast at every study point."""
    warnings.filterwarnings("ignore")
    frames = []
    for p in MOP_POINTS:
        ds = xr.open_dataset(MOP_URL.format(p, "nowcast"))
        sub = ds[["waveHs", "waveTp"]].sel(waveTime=slice(start.tz_localize(None), end.tz_localize(None)))
        df = sub.to_dataframe()[["waveHs", "waveTp"]]
        df.index = df.index.tz_localize("UTC")
        frames.append(df.assign(point=f"D{p:04d}"))
        ds.close()
    now = pd.concat(frames).rename_axis("time_utc").reset_index()
    return now.rename(columns={"waveHs": "now_height_m", "waveTp": "now_period_s"})


def summary_table(pairs: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = pairs.groupby(by, observed=True)
    return pd.DataFrame({
        "pairs": g.size(),
        "bias_ft": g.err_ft.mean(),
        "ratio_pct": g.apply(lambda x: 100 * x.fc_ft.sum() / x.now_ft.sum(), include_groups=False),
        "error_ft": g.err_ft.apply(lambda e: e.abs().mean()),
        "period_bias_s": g.apply(lambda x: (x.peak_period_s - x.now_period_s).mean(), include_groups=False),
    }).round(2)


def main() -> None:
    snaps = snapshots()
    first = min(i for i, _ in snaps) - pd.Timedelta(hours=3)
    now_df = nowcast(first, pd.Timestamp.now(tz="UTC"))
    last_now = now_df.time_utc.max()

    rows = []
    for issued, w in snaps:
        w = w[w.time_utc <= last_now].assign(issued_utc=issued)
        rows.append(w)
    fc = pd.concat(rows)
    pairs = fc.merge(now_df, on=["time_utc", "point"], how="inner")
    pairs["lead_h"] = (pairs.time_utc - pairs.issued_utc).dt.total_seconds() / 3600
    pairs = pairs[pairs.lead_h >= 0]
    pairs["fc_ft"] = pairs.wave_height_m * M_TO_FT
    pairs["now_ft"] = pairs.now_height_m * M_TO_FT
    pairs["err_ft"] = pairs.fc_ft - pairs.now_ft
    pairs["lead"] = pd.cut(pairs.lead_h, LEAD_BINS, labels=LEAD_LABELS, include_lowest=True)
    pairs["model_name"] = pairs.model.map(MODEL_NAMES)
    pairs.drop(columns=["lead"]).round(3).to_csv(OUT_CSV, index=False)

    overall = summary_table(pairs, ["model_name"])
    by_lead = summary_table(pairs, ["model_name", "lead"])
    # Bigger-wave hours matter most for flooding: score the top quarter of nowcast heights too.
    big = pairs[pairs.now_ft >= pairs.now_ft.quantile(0.75)]
    big_tab = summary_table(big, ["model_name"])

    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    def to_md(t: pd.DataFrame) -> str:
        t = t.reset_index()
        lines = ["| " + " | ".join(t.columns) + " |", "|" + "---|" * len(t.columns)]
        lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in t.itertuples(index=False)]
        return "\n".join(lines)
    span = (f"{pairs.time_utc.min().tz_convert('America/Los_Angeles'):%a %b %d %-I %p} – "
            f"{pairs.time_utc.max().tz_convert('America/Los_Angeles'):%a %b %d %-I %p} PT")
    md = f"""# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on {created}. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
{len(snaps)} forecast snapshots, {pairs.issued_utc.nunique()} with results so far, {len(pairs):,} matched
point-hours, {span}. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
{to_md(overall)}

## Bigger-wave hours only (top quarter of actual heights, ≥ {big.now_ft.min():.1f} ft)
{to_md(big_tab)}

## By how far ahead the forecast was made
{to_md(by_lead)}

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
"""
    OUT_MD.write_text(md)
    print(md)


if __name__ == "__main__":
    main()
