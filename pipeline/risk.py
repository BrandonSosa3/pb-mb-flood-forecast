"""Turn water levels and wave run-up into a plain-language risk level per area.

Levels: Low, Minor, Moderate, Major. An area's level is the worse of:

  Bay side (Mission Bay still water, from area_curves.json):
    Minor     water on Bayside Walk / paths (>= 0.1 mi) or 3-24 properties
    Moderate  25-199 properties, or >= 0.25 mi of road covered
    Major     >= 200 properties, or >= 1 mi of road covered
  Ocean side (wave run-up per ~100 m beach stretch, from runup.py):
    Minor     waves reach the boardwalk/ridge top (within 2 ft) at 1-4 stretches
    Moderate  reach the top at >= 5 stretches, or over the top at 1-2
    Major     over the top at >= 3 stretches
(Thresholds proposed 2026-11-13 and checked against the backtest days.)

Mission Bay still water = NOAA Mission Bay (9410196) tide prediction + extra
water measured at La Jolla (9410230). Mission Bay has no live gauge.

Usage (rate past days with measured data):
  python pipeline/risk.py --start 2026-10-25 --end 2026-10-29
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

from noaa_tides import PROCESSED_DIR, fetch_noaa, to_frame

LEVELS = ["Low", "Minor", "Moderate", "Major"]
MISSION_BAY, LA_JOLLA = "9410196", "9410230"


def load_curves() -> dict:
    return json.loads((PROCESSED_DIR / "area_curves.json").read_text())


def bay_risk(curve: dict, levels: list[float], level: float) -> tuple[int, dict]:
    if level < levels[0]:  # below the lowest level we track: nothing beyond the routine high-tide line
        return 0, {k: 0 for k in ("buildings", "drain_buildings", "road_mi", "walk_mi")}
    i = int(min(np.searchsorted(levels, level, side="right") - 1, len(levels) - 1))
    facts = {k: curve[k][i] for k in ("buildings", "drain_buildings", "road_mi", "walk_mi")}
    if facts["buildings"] >= 200 or facts["road_mi"] >= 1.0:
        return 3, facts
    if facts["buildings"] >= 25 or facts["road_mi"] >= 0.25:
        return 2, facts
    if facts["buildings"] >= 3 or facts["walk_mi"] >= 0.1:
        return 1, facts
    return 0, facts


def ocean_risk(margins: pd.Series) -> tuple[int, dict]:
    """margins: crest minus total water level (ft) per beach stretch; < 0 means over the top."""
    over, reaches = int((margins < 0).sum()), int(((margins >= 0) & (margins < 2)).sum())
    facts = {"stretches_over": over, "stretches_reach_top": reaches}
    if over >= 3:
        return 3, facts
    if reaches >= 5 or over >= 1:
        return 2, facts
    if reaches >= 1:
        return 1, facts
    return 0, facts


def area_status(name: str, curves: dict, bay_level: float, ocean_margins: pd.Series | None) -> dict:
    curve = curves["areas"][name]
    b, bf = bay_risk(curve, curves["levels_ft_mllw"], bay_level)
    o, of = (0, {})
    if curve["beach_points"] and ocean_margins is not None:
        o, of = ocean_risk(ocean_margins.reindex(curve["beach_points"]).dropna())
    level = max(b, o)
    cause = "both" if b == o and b > 0 else ("bay" if b > o else ("ocean" if o > 0 else "none"))
    return {"area": name, "risk": LEVELS[level], "cause": cause, "bay_risk": LEVELS[b], "ocean_risk": LEVELS[o],
            "bay_level_ft": round(bay_level, 2), **bf, **of}


def mission_bay_still_water(start: date, end: date) -> pd.Series:
    """6-min Mission Bay level = Mission Bay prediction + La Jolla extra water (measured)."""
    mb = to_frame(fetch_noaa(MISSION_BAY, "predictions", start, end))["v"]
    lj_obs = to_frame(fetch_noaa(LA_JOLLA, "water_level", start, end))["v"]
    lj_pred = to_frame(fetch_noaa(LA_JOLLA, "predictions", start, end))["v"]
    extra = (lj_obs - lj_pred).dropna()
    return (mb + extra.reindex(mb.index).interpolate(limit=5)).dropna().rename("mission_bay_ft")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=date.fromisoformat, required=True)
    p.add_argument("--end", type=date.fromisoformat, required=True)
    args = p.parse_args()

    curves = load_curves()
    bay = mission_bay_still_water(args.start, args.end + timedelta(days=1))
    bay_daily = bay.tz_convert("America/Los_Angeles").groupby(lambda t: t.date()).max()
    runup_file = PROCESSED_DIR / "runup" / f"twl_{args.start}_{args.end}_archive.csv"
    margins_daily = {}
    if runup_file.exists():
        t = pd.read_csv(runup_file, parse_dates=["time_utc"])
        t["day"] = t.time_utc.dt.tz_convert("America/Los_Angeles").dt.date
        margins_daily = {d: g.groupby("point").margin_ft.min() for d, g in t.groupby("day")}
    else:
        print(f"(no run-up file {runup_file.name}; run runup.py for the same dates to include waves)")

    rows = []
    for day, level in bay_daily.items():
        if not (args.start <= day <= args.end):
            continue
        for name in curves["areas"]:
            rows.append({"day": day, **area_status(name, curves, float(level), margins_daily.get(day))})
    df = pd.DataFrame(rows)
    cols = ["day", "area", "risk", "cause", "bay_level_ft", "buildings", "road_mi", "walk_mi",
            "stretches_over", "stretches_reach_top"]
    print(df[[c for c in cols if c in df]].to_string(index=False))


if __name__ == "__main__":
    main()
