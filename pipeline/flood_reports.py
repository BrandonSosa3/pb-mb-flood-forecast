"""City of San Diego "Get It Done" reports about flooding and storm drains in La Jolla, Pacific Beach and
Mission Beach, 2016 to now, each tagged with what likely caused it.

Why: these are real people reporting water in the street, at an exact place and time. We use them to
check the rain ponding spots (do reports cluster at our spots?) and, later, to learn how much rain it
takes to flood each neighborhood.

Report types kept:
  flooded  service "Street Flooded", or detail FLOODED / PONDING WATER IN GUTTER/STREET
  drain    storm drain problems: detail DRAIN INLET, DRAINAGE DITCH, DRAINAGE CULVERT, DRAIN OUTFALL, ...
Likely cause (from the report's date):
  rain     >= RAIN_DAY_IN at San Diego airport (KSAN) that day or the day before
  tide     otherwise, La Jolla water level >= TIDE_FT that day (bay/king-tide flooding)
  other    neither (water-main breaks, irrigation, ...)

Source: data.sandiego.gov Get It Done (closed requests by year + open requests). Each yearly file is
~100 MB; we keep only the matching rows (data/processed/flood_reports.csv) and delete the download.

Usage: python pipeline/flood_reports.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import requests

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

BASE = "https://seshat.datasd.org/get_it_done_reports/"
FILES = [f"get_it_done_requests_closed_{y}_datasd.csv" for y in range(2016, datetime.now().year + 1)] + \
        ["get_it_done_requests_open_datasd.csv"]
TMP = PROJECT_ROOT / "data" / "raw" / "get_it_done"
OUT = PROCESSED_DIR / "flood_reports.csv"
HEADERS = {"User-Agent": "coastal-flood-forecast-research"}
COMM_PLANS = {"LA JOLLA": "La Jolla", "PACIFIC BEACH": "Pacific Beach", "MISSION BEACH": "Mission Beach"}
FLOODED_DETAIL = {"FLOODED", "PONDING WATER IN GUTTER/STREET"}
DRAIN_DETAIL = {"DRAIN INLET", "DRAINAGE DITCH", "DRAINAGE CULVERT", "DRAIN CLEANOUT", "DRAIN HEADWALL",
                "DRAIN OUTFALL", "DRAINS - Drain Maintenance", "Broken Storm Drain", "STORM WATER"}
RAIN_DAY_IN = 0.10
TIDE_FT = 7.0
KEEP = ["service_request_id", "date_requested", "service_name", "service_name_detail", "status", "lat", "lng",
        "street_address", "comm_plan_name", "case_origin", "public_description"]


def download(name: str) -> pd.DataFrame:
    TMP.mkdir(parents=True, exist_ok=True)
    path = TMP / name
    with requests.get(BASE + name, stream=True, timeout=300, headers=HEADERS) as r:
        if r.status_code == 404:
            return pd.DataFrame(columns=KEEP)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    df = pd.read_csv(path, low_memory=False, dtype=str)
    path.unlink()
    df = df[df.comm_plan_name.str.upper().isin(COMM_PLANS)]
    detail = df.service_name_detail.fillna("")
    flooded = (df.service_name == "Street Flooded") | detail.isin(FLOODED_DETAIL)
    drain = detail.isin(DRAIN_DETAIL) & ~flooded
    df = df[flooded | drain][KEEP].copy()
    df["type"] = "flooded"
    df.loc[drain[flooded | drain].to_numpy(), "type"] = "drain"
    return df


def main() -> None:
    parts = []
    for name in FILES:
        d = download(name)
        print(f"  {name}: {len(d):,} flood/drain reports in La Jolla, PB, MB")
        parts.append(d)
    df = pd.concat(parts).drop_duplicates("service_request_id")
    df["neighborhood"] = df.comm_plan_name.str.upper().map(COMM_PLANS)
    df["time_local"] = pd.to_datetime(df.date_requested).dt.tz_localize("America/Los_Angeles", ambiguous="NaT",
                                                                        nonexistent="NaT")
    df["date"] = df.time_local.dt.date
    df[["lat", "lng"]] = df[["lat", "lng"]].astype(float)

    # Likely cause from the date: rain (airport gauge) or a very high tide (La Jolla gauge).
    rain = pd.read_csv(PROCESSED_DIR / "hourly_rain_KSAN.csv.gz", parse_dates=["time_utc"]).set_index("time_utc").rain_in
    daily_rain = rain.tz_convert("America/Los_Angeles").groupby(lambda t: t.date()).sum()
    tide = pd.read_csv(PROCESSED_DIR / "hourly_extra_water_9410230.csv.gz", parse_dates=["time_utc"])
    tide = tide.set_index("time_utc").observed_ft.tz_convert("America/Los_Angeles")
    daily_tide = tide.groupby(lambda t: t.date()).max()
    prev = df.date.map(lambda d: d - pd.Timedelta(days=1) if pd.notna(d) else d)
    df["rain_in_day"] = df.date.map(daily_rain).fillna(0).round(2)
    df["rain_in_prev_day"] = prev.map(daily_rain).fillna(0).round(2)
    df["tide_ft"] = df.date.map(daily_tide).round(2)
    rainy = (df.rain_in_day >= RAIN_DAY_IN) | (df.rain_in_prev_day >= RAIN_DAY_IN)
    df["cause"] = "other"
    df.loc[df.tide_ft >= TIDE_FT, "cause"] = "tide"
    df.loc[rainy, "cause"] = "rain"
    df = df.drop(columns=["comm_plan_name", "date_requested"]).sort_values("time_local")
    df.to_csv(OUT, index=False)

    meta = {"source": "City of San Diego Get It Done, data.sandiego.gov", "base_url": BASE, "files": FILES,
            "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "neighborhoods": list(COMM_PLANS.values()), "rain_day_in": RAIN_DAY_IN, "tide_ft_mllw": TIDE_FT,
            "rows": int(len(df)), "by_type_cause": {f"{k[0]}/{k[1]}": int(v) for k, v in
                                                     df.groupby(["type", "cause"]).size().items()},
            "note": "public descriptions are as written by the public/City; no names. Not shown on the site."}
    OUT.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(df.groupby(["neighborhood", "type", "cause"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
