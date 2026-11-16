"""Turn water levels and wave run-up into a plain-language risk level per area.

Levels: Low, Minor, Moderate, Major. An area's level is the worse of:

  Bay side (Mission Bay still water, from area_curves.json). When the City's
  sand berm along Bayside Walk is up (docs/evidence/berm_status.csv; default
  Oct-Apr), the headline assumes it holds unless the water is above its assumed
  top. With no berm (default May-Sep) the headline uses the no-berm model.
  At BERM_LEAK_FT or more the berm may leak (it leaked/broke on 2 of the 4 days
  that high in Oct 2026), so the headline is at least Moderate when the no-berm
  model says so. "risk_if_berm_fails" always uses the no-berm model.
    Minor     water on Bayside Walk / paths (>= 0.1 mi), 3-24 properties, or
              >= 25 properties below the water level (storm drains may back up)
    Moderate  25-199 properties, or >= 0.25 mi of road covered
    Major     >= 200 properties, or >= 1 mi of road covered
  Ocean side (wave run-up per ~100 m beach stretch, from runup.py):
    Minor     waves reach the boardwalk/ridge top (within 2 ft) at 1-4 stretches
    Moderate  reach the top at >= 5 stretches, or over the top at 1-2
    Major     over the top at >= 3 stretches
(Thresholds proposed 2026-11-13 and checked against the backtest days; berm season and
leak rule added 2026-11-16 after backtest batch 2, docs/evidence/backtest_scorecard.md.)

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

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT, fetch_noaa, to_frame

LEVELS = ["Low", "Minor", "Moderate", "Major"]
# Properties lower than the water but walled off (berm / high ground): water can
# still come up through storm drains. This many or more -> at least Minor.
DRAIN_MINOR = 25
# Rain rule: drain outlets are underwater near high tide, so rain ponds in low streets.
# Fires ~1x a year since 2000 (docs/evidence/rain_near_high_tide.md), incl. Jan 22, 2024.
RAIN_NEAR_TIDE_IN = 0.25   # inches within RAIN_WINDOW_H hours of the day's highest tide
RAIN_WINDOW_H = 3
RAIN_MIN_PROPERTIES = 10   # properties on ground below the water (storm-drain count)
BERM_TOP_MLLW_FT = 9.0  # must match flood_threshold.py
BERM_LEAK_FT = 7.8      # leaked Oct 25 (7.9 ft), broke Oct 26 (8.1), held Oct 27-28 (8.1-8.2) after rebuilding
BERM_SEASON_MONTHS = {10, 11, 12, 1, 2, 3, 4}  # berm usually up; outside these months, no berm
BERM_FILE = PROJECT_ROOT / "docs" / "evidence" / "berm_status.csv"
MISSION_BAY, LA_JOLLA = "9410196", "9410230"


def load_curves() -> dict:
    return json.loads((PROCESSED_DIR / "area_curves.json").read_text())


def berm_status(day: date) -> tuple[bool, str]:
    """Is the bay-side berm up on this local date? (up, where the answer comes from)."""
    up, source = day.month in BERM_SEASON_MONTHS, "season rule (berm up Oct-Apr, none May-Sep)"
    if BERM_FILE.exists():
        rows = pd.read_csv(BERM_FILE, comment="#").rename(columns={"from": "start", "to": "end"})
        for r in rows.itertuples():
            if date.fromisoformat(r.start) <= day <= date.fromisoformat(r.end):
                up, source = r.status == "up", r.source
    return up, source


def bay_risk(curve: dict, levels: list[float], level: float, sfx: str = "") -> tuple[int, dict]:
    """sfx '' = berm fails / no berm, '_berm' = berm holds."""
    keys = ("buildings", "drain_buildings", "road_mi", "walk_mi")
    if level < levels[0]:  # below the lowest level we track: nothing beyond the routine high-tide line
        return 0, {k: 0 for k in keys}
    i = int(min(np.searchsorted(levels, level, side="right") - 1, len(levels) - 1))
    facts = {k: curve[k + sfx][i] for k in keys}
    if facts["buildings"] >= 200 or facts["road_mi"] >= 1.0:
        return 3, facts
    if facts["buildings"] >= 25 or facts["road_mi"] >= 0.25:
        return 2, facts
    if facts["buildings"] >= 3 or facts["walk_mi"] >= 0.1 or facts["drain_buildings"] >= DRAIN_MINOR:
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


def area_status(name: str, curves: dict, bay_level: float, ocean_margins: pd.Series | None,
                berm_up: bool = True) -> dict:
    curve = curves["areas"][name]
    # Headline assumes the bay-side sand berm holds, if it is up and the water is below its top.
    berm_holds = berm_up and bay_level < BERM_TOP_MLLW_FT
    may_leak = berm_holds and bay_level >= BERM_LEAK_FT
    b, bf = bay_risk(curve, curves["levels_ft_mllw"], bay_level, "_berm" if berm_holds else "")
    b_fail, bf_fail = bay_risk(curve, curves["levels_ft_mllw"], bay_level, "")
    if may_leak:  # at least Moderate, if water would reach that far without the berm
        b = max(b, min(b_fail, LEVELS.index("Moderate")))
    o, of = (0, {})
    if curve["beach_points"] and ocean_margins is not None:
        o, of = ocean_risk(ocean_margins.reindex(curve["beach_points"]).dropna())
    level = max(b, o)
    cause = "both" if b == o and b > 0 else ("bay" if b > o else ("ocean" if o > 0 else "none"))
    level_fail = max(b_fail, o)
    return {"area": name, "risk": LEVELS[level], "cause": cause, "bay_risk": LEVELS[b], "ocean_risk": LEVELS[o],
            "risk_if_berm_fails": LEVELS[level_fail], "berm_up": berm_up, "berm_may_leak": may_leak,
            "berm_overtopped": berm_up and bay_level >= BERM_TOP_MLLW_FT,
            "bay_level_ft": round(bay_level, 2), **bf, **of,
            "buildings_if_berm_fails": bf_fail["buildings"], "road_mi_if_berm_fails": bf_fail["road_mi"]}


def with_rain(level: str, rain_near_tide_in: float | None, drain_properties: int) -> tuple[str, bool]:
    """Raise a rating one step (at most to Moderate) when enough rain falls near high tide in an
    area with homes on ground below the water. Returns (level, rain_ponding)."""
    if rain_near_tide_in is None or rain_near_tide_in < RAIN_NEAR_TIDE_IN or drain_properties < RAIN_MIN_PROPERTIES:
        return level, False
    i = LEVELS.index(level)
    return LEVELS[max(i, min(i + 1, LEVELS.index("Moderate")))], True


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
            rows.append({"day": day, **area_status(name, curves, float(level), margins_daily.get(day),
                                                   berm_status(day)[0])})
    df = pd.DataFrame(rows)
    cols = ["day", "area", "risk", "risk_if_berm_fails", "berm_up", "berm_may_leak", "cause", "bay_level_ft", "buildings", "drain_buildings",
            "buildings_if_berm_fails", "stretches_over", "stretches_reach_top"]
    print(df[[c for c in cols if c in df]].to_string(index=False))


if __name__ == "__main__":
    main()
