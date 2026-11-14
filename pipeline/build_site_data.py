"""Build the small data files the website reads (web/public/data/).

The website does no heavy computing: this script turns the latest logged
forecast and the model outputs into ready-to-display files.

  forecast.json        latest forecast: per area, per day - status, "could reach",
                       "if the berm fails", worst time, drivers, places to watch
  area_curves.json     slider counts per area and water level (copied)
  areas.geojson        area outlines (copied)
  buildings.geojson    buildings water can reach at <= MAX_LEVEL_FT (shape + danger heights only)
  streets.geojson      25 m street pieces water can reach at <= MAX_LEVEL_FT

Headline wave model: CDIP MOP driven by NOAA WaveWatch III ("forecast").
"Could reach": the worse of that and the ECMWF-driven run.

Usage:
  python pipeline/build_site_data.py                       # latest snapshot
  python pipeline/build_site_data.py --snapshot forecast_log/2026/11/2026-11-13T2241Z
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from forecast_logger import LOG_DIR
from noaa_tides import PROCESSED_DIR, PROJECT_ROOT, fetch_noaa, to_frame
from areas import ROUTINELY_WET_FT
from risk import LEVELS, MISSION_BAY, area_status, load_curves
from runup import from_snapshot, total_water_level

SITE_DATA = PROJECT_ROOT / "web" / "public" / "data"
LOCAL_TZ = "America/Los_Angeles"
MAX_LEVEL_FT = 11.0  # slider tops out below this; anything higher never shows as reached
MODELS = {"forecast": "NOAA-driven", "ecmwf_fc": "ECMWF-driven"}


def latest_snapshot() -> Path:
    runs = sorted(p for p in LOG_DIR.glob("*/*/*Z") if (p / "meta.json").exists())
    return runs[-1]


def mission_bay_series(snapshot: Path, meta: dict) -> pd.Series:
    """Mission Bay still water (ft MLLW), from the snapshot; older snapshots lack it, so rebuild
    it from NOAA's (deterministic) tide prediction + the snapshot's frozen La Jolla extra water."""
    tides = pd.read_csv(snapshot / "tides.csv.gz", parse_dates=["time_utc"])
    mb = tides[tides.station == int(MISSION_BAY)]
    if len(mb):
        return mb.set_index("time_utc")["still_water_ft"]
    t0, t1 = tides.time_utc.min(), tides.time_utc.max()
    pred = to_frame(fetch_noaa(MISSION_BAY, "predictions", t0.date(), t1.date()))["v"]
    pred = pred[(pred.index >= t0) & (pred.index <= t1)]
    return pred + meta["tides"]["9410230"]["extra_water_25h_ft"]


def places_to_watch(twl: pd.DataFrame, profiles: pd.DataFrame, points: list[str], n: int = 3) -> list[dict]:
    """Beach stretches whose waves come closest to the boardwalk top, named by nearest cross street."""
    worst = twl[twl.point.isin(points)].groupby("point").margin_ft.min().sort_values()
    worst = worst[worst < 2.0].head(n)
    if worst.empty:
        return []
    ways = gpd.read_file(PROCESSED_DIR / "osm_ways.geojson").to_crs(26911)
    board = ways[ways.name == "Ocean Front Walk"].union_all()
    cross = ways[(ways.kind == "street") & (ways.name != "")
                 & ~ways.name.isin(["Mission Boulevard", "Ocean Front Walk", "Strandway", "Ocean Boulevard"])]
    out = []
    for point, margin in worst.items():
        r = profiles.loc[point]
        p = gpd.GeoSeries([Point(r.lon, r.lat)], crs=4326).to_crs(26911)[0]
        on = board.interpolate(board.project(p))
        street = cross.loc[cross.distance(on).idxmin(), "name"]
        lon, lat = gpd.GeoSeries([on], crs=26911).to_crs(4326)[0].coords[0]
        out.append({"point": point, "near": street.replace(" Place", " Pl").replace(" Street", " St"),
                    "margin_ft": round(float(margin), 1), "over": bool(margin < 0),
                    "lon": round(lon, 5), "lat": round(lat, 5)})
    return out


def forecast_json(snapshot: Path) -> dict:
    meta = json.loads((snapshot / "meta.json").read_text())
    curves = load_curves()
    profiles = pd.read_csv(PROCESSED_DIR / "shore_profiles.csv").set_index("point")
    profiles_ok = profiles[profiles.barrier.isin(["ridge", "rising ground"])]
    bay = mission_bay_series(snapshot, meta).tz_convert(LOCAL_TZ)

    twl = {}
    for model in MODELS:
        waves, still = from_snapshot(snapshot, model)
        t = total_water_level(waves, still, profiles_ok)
        t["local"] = t.time_utc.dt.tz_convert(LOCAL_TZ)
        twl[model] = t

    issued = pd.Timestamp(meta["issued_at_utc"]).tz_convert(LOCAL_TZ)
    days = sorted(d for d in set(bay.index.date) if d >= issued.date())[:4]
    areas_out = []
    for name in curves["areas"]:
        day_rows = []
        for d in days:
            b = bay[bay.index.date == d]
            bay_peak, bay_time = float(b.max()), b.idxmax()
            per_model = {}
            for model, t in twl.items():
                td = t[t.local.dt.date == d]
                margins = td.groupby("point").margin_ft.min() if len(td) else None
                per_model[model] = (area_status(name, curves, bay_peak, margins), td)
            head, td = per_model["forecast"]
            upper = max((LEVELS.index(s["risk"]) for s, _ in per_model.values()))
            pts = curves["areas"][name]["beach_points"]
            tdp = td[td.point.isin(pts)]
            worst_wave_time = tdp.loc[tdp.margin_ft.idxmin(), "local"] if len(tdp) else None
            cause = head["cause"]
            worst = worst_wave_time if cause == "ocean" and worst_wave_time is not None else bay_time
            day_rows.append({
                "date": str(d), "risk": head["risk"], "could_reach": LEVELS[upper],
                "risk_if_berm_fails": head["risk_if_berm_fails"], "cause": cause,
                "worst_time": worst.isoformat() if worst is not None else None,
                "bay_peak_ft": round(bay_peak, 2), "bay_peak_time": bay_time.isoformat(),
                "berm_overtopped": head["berm_overtopped"],
                "properties_below_water": head["drain_buildings"],
                "properties_reached": head["buildings"],
                "properties_if_berm_fails": head["buildings_if_berm_fails"],
                "stretches_reach_top": head.get("stretches_reach_top"),
                "stretches_over": head.get("stretches_over"),
                "stretches_reach_top_upper": max(s.get("stretches_reach_top") or 0 for s, _ in per_model.values()),
                "wave_height_ft": [round(float(tdp.wave_height_ft.min()), 1), round(float(tdp.wave_height_ft.max()), 1)] if len(tdp) else None,
                "wave_period_s": [round(float(tdp.period_s.min())), round(float(tdp.period_s.max()))] if len(tdp) else None,
                "places_to_watch": places_to_watch(td[td.local.dt.date == d], profiles, pts) if pts else [],
            })
        areas_out.append({"name": name, "days": day_rows})

    tides = meta.get("tides", {})
    return {
        "issued_at": issued.isoformat(),
        "snapshot": snapshot.name,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "extra_water_ft": tides.get("9410230", {}).get("extra_water_25h_ft"),
        "nws_alerts": json.loads((snapshot / "alerts.json").read_text()) if (snapshot / "alerts.json").exists() else [],
        "wave_models": MODELS,
        "areas": areas_out,
        "notes": {
            "heights": "feet above MLLW (an ordinary low tide), NOAA La Jolla datums",
            "berm": "headline assumes the bay-side sand berms hold (assumed top 9.0 ft)",
        },
    }


def trimmed_assets() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    b = gpd.read_file(PROCESSED_DIR / "buildings_danger.geojson")
    b = b[np.fmin(b.danger_bay_ft.fillna(99), b.danger_ocean_ft.fillna(99)) <= MAX_LEVEL_FT]
    b = b[~(b.danger_bay_ft <= ROUTINELY_WET_FT)]  # wet on ordinary high tides; left out of counts too
    b = b[["danger_bay_ft", "danger_bay_berm_ft", "ground_min_ft", "geometry"]].rename(
        columns={"danger_bay_ft": "d", "danger_bay_berm_ft": "db", "ground_min_ft": "g"})
    s = gpd.read_file(PROCESSED_DIR / "street_pieces_danger.geojson")
    s = s[(s.danger_bay_ft.fillna(99) <= MAX_LEVEL_FT) & ~(s.danger_bay_ft <= ROUTINELY_WET_FT)]
    s = s[["name", "kind", "danger_bay_ft", "covered_bay_ft", "danger_bay_berm_ft", "covered_bay_berm_ft",
           "ground_min_ft", "geometry"]].rename(columns={
        "danger_bay_ft": "d", "covered_bay_ft": "c", "danger_bay_berm_ft": "db", "covered_bay_berm_ft": "cb",
        "ground_min_ft": "g"})
    for gdf in (b, s):
        gdf.geometry = gdf.geometry.set_precision(1e-5)  # ~1 m
    return b, s


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path)
    args = p.parse_args()
    snapshot = args.snapshot or latest_snapshot()
    SITE_DATA.mkdir(parents=True, exist_ok=True)

    fc = forecast_json(snapshot)
    (SITE_DATA / "forecast.json").write_text(json.dumps(fc, indent=1))
    for name in ("area_curves.json", "areas.geojson"):
        shutil.copy(PROCESSED_DIR / name, SITE_DATA / name)
    b, s = trimmed_assets()
    b.to_file(SITE_DATA / "buildings.geojson", driver="GeoJSON")
    s.to_file(SITE_DATA / "streets.geojson", driver="GeoJSON")

    print(f"Snapshot {snapshot.name} -> {SITE_DATA.relative_to(PROJECT_ROOT)}")
    for a in fc["areas"]:
        print(f"  {a['name']:14s} " + "  ".join(f"{d['date'][5:]} {d['risk']}"
              + (f"(→{d['could_reach']})" if d['could_reach'] != d['risk'] else "") for d in a["days"]))
    for f in sorted(SITE_DATA.iterdir()):
        print(f"  {f.name:20s} {f.stat().st_size / 1e3:8.0f} KB")


if __name__ == "__main__":
    main()
