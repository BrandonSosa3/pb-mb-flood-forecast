"""Build the small data files the website reads (web/public/data/).

The website does no heavy computing: this script turns the latest logged
forecast and the model outputs into ready-to-display files.

  forecast.json        latest forecast: per area, per day - status, "could reach",
                       "if the berm fails", worst time, drivers, places to watch
  area_curves.json     slider counts per area and water level (copied)
  areas.geojson        area outlines (copied)
  buildings.geojson    buildings water can reach at <= MAX_LEVEL_FT (shape + danger heights only)
  streets.geojson      25 m street pieces water can reach at <= MAX_LEVEL_FT
  about.json           "How it works" page: monthly extra water since 1980 (San Diego gauge),
                       the hand-kept track record (docs/evidence/track_record.json), and
                       how many live forecasts the logger has saved

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
from risk import (LEVELS, MISSION_BAY, RAIN_6H_LEVELS_IN, RAIN_WINDOW_H, area_status, berm_status, load_curves,
                  rain_level, with_rain)
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


def rain_forecast(snapshot: Path) -> pd.DataFrame | None:
    """NWS hourly rain forecast (inches per hour + chance) in local time; None for old snapshots."""
    f = snapshot / "weather.csv.gz"
    if not f.exists():
        return None
    w = pd.read_csv(f, parse_dates=["time_utc"]).set_index("time_utc")
    w.index = w.index.tz_convert(LOCAL_TZ)
    return w[["rain_in", "rain_chance_pct"]].fillna(0)


RAIN_NEIGHBORHOODS = ["La Jolla", "Pacific Beach", "Mission Beach"]


def rain_areas_json(snapshot: Path, issued: pd.Timestamp) -> dict | None:
    """Rain-flooding rating per neighborhood and day: heaviest 6 hours of forecast rain (rain_thresholds.py).
    Uses rain_areas.csv.gz (per neighborhood, since 2026-11-16); older snapshots: the one Mission Beach point."""
    f = snapshot / "rain_areas.csv.gz"
    if f.exists():
        r = pd.read_csv(f, parse_dates=["time_utc"])
        source = "per neighborhood"
    else:
        w = rain_forecast(snapshot)
        if w is None:
            return None
        w = w.reset_index().rename(columns={"index": "time_utc"})
        r = pd.concat([w.assign(area=a) for a in RAIN_NEIGHBORHOODS])
        source = "one point (Mission Beach) for all"
    out = []
    for area in RAIN_NEIGHBORHOODS:
        a = r[r.area == area].set_index("time_utc").sort_index()
        a.index = pd.DatetimeIndex(a.index).tz_convert(LOCAL_TZ)
        a = a.asfreq("h", fill_value=0)
        six = a.rain_in.iloc[::-1].rolling(6, min_periods=1).sum().iloc[::-1]  # 6 hours starting each hour
        days = []
        for d in sorted(set(a.index.date)):
            if d < issued.date():
                continue
            day = a[a.index.date == d]
            if len(day) < 6:
                continue
            s6 = six[six.index.date == d]
            start = s6.idxmax()
            days.append({"date": str(d), "level": rain_level(float(s6.max())),
                         "max_6h_in": round(float(s6.max()), 2),
                         "heaviest_from": start.isoformat(),
                         "total_in": round(float(day.rain_in.sum()), 2),
                         "chance_pct": int(day.rain_chance_pct.max())})
        out.append({"name": area, "days": days[:4]})
    return {"source": source, "levels_6h_in": RAIN_6H_LEVELS_IN, "areas": out}


def rain_for_day(rain: pd.DataFrame | None, d, tide_time: pd.Timestamp) -> dict:
    """Rain that day, and within RAIN_WINDOW_H hours of the day's highest tide."""
    if rain is None:
        return {"rain_day_in": None, "rain_near_tide_in": None, "rain_chance_pct": None, "rain_hourly": []}
    day = rain[rain.index.date == d]
    win = rain[(rain.index >= tide_time - pd.Timedelta(hours=RAIN_WINDOW_H)) &
               (rain.index <= tide_time + pd.Timedelta(hours=RAIN_WINDOW_H))]
    covered = len(day) >= 6  # the forecast's last day can be cut short
    return {"rain_day_in": round(float(day.rain_in.sum()), 2) if covered else None,
            "rain_near_tide_in": round(float(win.rain_in.sum()), 2) if len(win) else None,
            "rain_chance_pct": int(day.rain_chance_pct.max()) if len(day) else None,
            # [local hour ISO, inches, chance %] for the details view
            "rain_hourly": [[t.isoformat(), round(float(r.rain_in), 3), int(r.rain_chance_pct)] for t, r in day.iterrows()]}


def nws_surf_by_date(snapshot: Path) -> dict[str, str]:
    """NWS Surf Zone Forecast text per local date ("Today"/"Tonight" = issue date, "Sunday" = the
    next Sunday on or after it). Empty for snapshots saved before surf.json existed."""
    f = snapshot / "surf.json"
    if not f.exists():
        return {}
    srf = json.loads(f.read_text())
    issued = pd.Timestamp(srf["issued_utc"]).tz_convert(LOCAL_TZ).date()
    out = {}
    for d in srf["days"]:
        label = d["label"].split()[0].lower()
        if label in ("today", "tonight", "this"):
            day = issued
        else:
            names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            if label not in names:
                continue
            day = issued + pd.Timedelta(days=(names.index(label) - issued.weekday()) % 7)
        out.setdefault(str(day), d["surf"].rstrip("."))
    return out


def surf_range(t: pd.DataFrame) -> list[float] | None:
    """Surf size along an area's beach for one day: each stretch's biggest breaking-wave estimate,
    then [typical stretch (median), biggest stretch]. Uses the average of the two wave models
    (a size readout, so no cautious "higher model" choice here)."""
    if t.empty:
        return None
    m = t.groupby("point").surf_ft.max()
    return [round(float(m.median())), round(float(m.max()))]


def stretch_worst(t: pd.DataFrame) -> dict[str, list]:
    """Every beach stretch's closest call of the day: [ft below the boardwalk/ridge top
    (negative = over), local time], for the search card's "waves near you" line."""
    if t.empty:
        return {}
    worst = t.loc[t.groupby("point").margin_ft.idxmin()]
    return {r.point: [round(float(r.margin_ft), 1), r.local.isoformat()] for r in worst.itertuples()}


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
    # Cautious choice (Nov 14, 2026 wave check: the NOAA-driven model ran ~15-20% low): for every
    # stretch and hour, use whichever model puts the water higher.
    both = pd.concat(twl.values(), ignore_index=True)
    twl["higher"] = both.loc[both.groupby(["time_utc", "point"]).twl_ft.idxmax()].reset_index(drop=True)
    surf = both.groupby(["time_utc", "point"], as_index=False).agg(surf_ft=("surf_ft", "mean"), local=("local", "first"))

    issued = pd.Timestamp(meta["issued_at_utc"]).tz_convert(LOCAL_TZ)
    nws_surf = nws_surf_by_date(snapshot)
    rain = rain_forecast(snapshot)
    days = sorted(d for d in set(bay.index.date) if d >= issued.date())[:4]
    areas_out = []
    for name in curves["areas"]:
        day_rows = []
        for d in days:
            b = bay[bay.index.date == d]
            bay_peak, bay_time = float(b.max()), b.idxmax()
            berm_up = berm_status(d)[0]
            per_model = {}
            for model, t in twl.items():  # includes "higher" (the headline)
                td = t[t.local.dt.date == d]
                margins = td.groupby("point").margin_ft.min() if len(td) else None
                per_model[model] = (area_status(name, curves, bay_peak, margins, berm_up), td)
            head, td = per_model["higher"]
            upper = max((LEVELS.index(s["risk"]) for s, _ in per_model.values()))  # = headline now
            pts = curves["areas"][name]["beach_points"]
            tdp = td[td.point.isin(pts)]
            worst_wave_time = tdp.loc[tdp.margin_ft.idxmin(), "local"] if len(tdp) else None
            cause = head["cause"]
            worst = worst_wave_time if cause == "ocean" and worst_wave_time is not None else bay_time
            r = rain_for_day(rain, d, bay_time)
            risk, ponding = with_rain(head["risk"], r["rain_near_tide_in"], head["drain_buildings"])
            risk_fail, _ = with_rain(head["risk_if_berm_fails"], r["rain_near_tide_in"], head["drain_buildings"])
            day_rows.append({
                "date": str(d), "risk": risk, "could_reach": max(LEVELS[upper], risk, key=LEVELS.index),
                "risk_if_berm_fails": risk_fail, "cause": cause, "rain_ponding": ponding, **r,
                "worst_time": worst.isoformat() if worst is not None else None,
                "bay_peak_ft": round(bay_peak, 2), "bay_peak_time": bay_time.isoformat(),
                "berm_up": berm_up, "berm_may_leak": head["berm_may_leak"],
                "berm_overtopped": head["berm_overtopped"],
                "properties_below_water": head["drain_buildings"],
                "properties_reached": head["buildings"],
                "properties_if_berm_fails": head["buildings_if_berm_fails"],
                "stretches_reach_top": head.get("stretches_reach_top"),
                "stretches_over": head.get("stretches_over"),
                "stretches_reach_top_upper": max(s.get("stretches_reach_top") or 0 for s, _ in per_model.values()),
                "wave_height_ft": [round(float(tdp.wave_height_ft.min()), 1), round(float(tdp.wave_height_ft.max()), 1)] if len(tdp) else None,
                "wave_period_s": [round(float(tdp.period_s.min())), round(float(tdp.period_s.max()))] if len(tdp) else None,
                # Surf size: each stretch's biggest breaking-wave estimate of the day, smallest-biggest stretch.
                "surf_ft": surf_range(surf[(surf.local.dt.date == d) & surf.point.isin(pts)]),
                "nws_surf": nws_surf.get(str(d)) if pts else None,
                "places_to_watch": places_to_watch(td[td.local.dt.date == d], profiles, pts) if pts else [],
                "stretches": stretch_worst(tdp),
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
        "wave_rule": "higher of the two models, per stretch and hour (since 2026-11-14)",
        "areas": areas_out,
        "rain": rain_areas_json(snapshot, issued),
        "notes": {
            "heights": "feet above MLLW (an ordinary low tide), NOAA La Jolla datums",
            "berm": "when the bay-side berm is up (docs/evidence/berm_status.csv, else Oct-Apr) the headline "
                    "assumes it holds (assumed top 9.0 ft); at 7.8 ft or more it may leak (at least Moderate)",
        },
    }


def rain_site_files() -> None:
    """Rain spots (rain_spots.py) and simplified neighborhood outlines for the map's Rain view."""
    shutil.copy(PROCESSED_DIR / "rain_spots.geojson", SITE_DATA / "rain_spots.geojson")
    from rain_ponds import PLAN_FILE
    if not PLAN_FILE.exists():  # raw City file is local-only (not in git); the published outlines don't change
        return
    plan = gpd.read_file(PLAN_FILE)
    plan = plan[plan.cpname.isin(RAIN_NEIGHBORHOODS)].to_crs(26911)
    plan["geometry"] = plan.geometry.simplify(15)
    plan = plan[["cpname", "geometry"]].rename(columns={"cpname": "name"}).to_crs(4326)
    plan["geometry"] = plan.geometry.set_precision(1e-5)
    (SITE_DATA / "rain_neighborhoods.geojson").write_text(plan.to_json(drop_id=True))


HISTORY_STATION = "9410170"  # San Diego: the longest record, and the gauge the news quotes
TRACK_RECORD = PROJECT_ROOT / "docs" / "evidence" / "track_record.json"


AUTO_SCORES = PROJECT_ROOT / "docs" / "evidence" / "auto" / "scores.json"


def auto_scores() -> dict:
    """Forecasts scored automatically (auto_verify.py): scored days for the list, plus how many weren't."""
    if not AUTO_SCORES.exists():
        return {"days": [], "unverified": 0}
    s = json.loads(AUTO_SCORES.read_text())
    return {"days": [d for d in s if d["result"] != "unverified"],
            "unverified": sum(d["result"] == "unverified" for d in s),
            "updated": max((d["scored_utc"] for d in s), default=None)}


def about_json() -> dict:
    m = pd.read_csv(PROCESSED_DIR / f"monthly_extra_water_{HISTORY_STATION}.csv", parse_dates=["month"])
    m = m[m.month >= "1980-01-01"]
    hist_meta = json.loads((PROCESSED_DIR / f"monthly_extra_water_{HISTORY_STATION}.meta.json").read_text())
    months = [{"m": r.month.strftime("%Y-%m"),
               "a": None if pd.isna(r.anomaly_ft) else round(float(r.anomaly_ft), 2),
               "n": r.el_nino_winter if isinstance(r.el_nino_winter, str) else "",
               "p": bool(r.partial)} for r in m.itertuples()]
    full = m[~m.partial & m.anomaly_ft.notna()]
    before = full[full.month < "2026-01-01"]
    top = before.loc[before.anomaly_ft.idxmax()]
    runs = sorted(p for p in LOG_DIR.glob("*/*/*Z") if (p / "meta.json").exists())
    return {
        "history": {
            "station": HISTORY_STATION, "station_name": "San Diego (Broadway Pier)",
            "downloaded": hist_meta.get("downloaded_at_utc", hist_meta.get("created_utc", ""))[:10],
            "months": months,
            "record_before_2026": {"month": top.month.strftime("%Y-%m"), "anomaly_ft": round(float(top.anomaly_ft), 2)},
        },
        "track_record": json.loads(TRACK_RECORD.read_text()),
        "auto": auto_scores(),
        "log": {"first": runs[0].name if runs else None, "count": len(runs)},
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
    # Keep what was published with its snapshot, so auto_verify.py scores exactly what people saw (first version wins).
    published = snapshot / "site_forecast.json"
    if not published.exists():
        published.write_text(json.dumps({**fc, "published_at": fc["built_at"]}, separators=(",", ":")))
    (SITE_DATA / "about.json").write_text(json.dumps(about_json(), separators=(",", ":")))
    for name in ("area_curves.json", "areas.geojson"):
        shutil.copy(PROCESSED_DIR / name, SITE_DATA / name)
    rain_site_files()
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
