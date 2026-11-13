"""Download NOAA water levels and compute "extra water".

Extra water = observed water level - predicted tide.
The predicted tide only knows about the moon and sun, so anything left over
(El Nino, Kelvin waves, storms, wind) shows up as extra water.

Data source: NOAA CO-OPS Tides & Currents API
  https://api.tidesandcurrents.noaa.gov/api/prod/
All heights are in feet above MLLW (Mean Lower Low Water, roughly "an
ordinary low tide"). Times are downloaded in UTC (no daylight-saving
ambiguity) and converted to San Diego local time.

Usage:
  python pipeline/noaa_tides.py                      # last 45 days, San Diego
  python pipeline/noaa_tides.py --days 90
  python pipeline/noaa_tides.py --station 9410230    # La Jolla
  python pipeline/noaa_tides.py --start 2026-10-01 --end 2026-11-13
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
STATIONS = {"9410170": "San Diego (Broadway Pier)", "9410230": "La Jolla (Scripps Pier)"}
LOCAL_TZ = "America/Los_Angeles"

# NOAA only returns ~31 days of 6-minute data per request, so we ask in chunks.
MAX_DAYS_PER_REQUEST = 30

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "noaa"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def fetch_noaa(station: str, product: str, start: date, end: date) -> list[dict]:
    """Ask NOAA for one product ('water_level' or 'predictions') over a date range.

    Returns the raw list of readings, e.g. [{'t': '2026-10-27 16:48', 'v': '8.52', ...}].
    """
    readings: list[dict] = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=MAX_DAYS_PER_REQUEST - 1), end)
        params = {
            "station": station,
            "product": product,
            "begin_date": chunk_start.strftime("%Y%m%d"),
            "end_date": chunk_end.strftime("%Y%m%d"),
            "datum": "MLLW",
            "units": "english",
            "time_zone": "gmt",
            "format": "json",
        }
        if product == "predictions":
            params["interval"] = "6"  # every 6 minutes, to line up with observations

        response = requests.get(API_URL, params=params, timeout=60)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"NOAA error for {product} {chunk_start}..{chunk_end}: {body['error']}")

        # Observed data comes back under "data", predictions under "predictions".
        readings.extend(body.get("data") or body.get("predictions") or [])
        chunk_start = chunk_end + timedelta(days=1)
    return readings


def to_frame(readings: list[dict]) -> pd.DataFrame:
    """Turn NOAA readings into a table indexed by UTC time (blank values -> NaN)."""
    df = pd.DataFrame(readings)
    df.index = pd.to_datetime(df["t"]).dt.tz_localize("UTC")
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    return df


def build_table(observed: list[dict], predicted: list[dict]) -> pd.DataFrame:
    """Line up observed and predicted water levels and compute extra water."""
    obs = to_frame(observed)
    pred = to_frame(predicted)
    table = pd.DataFrame({"observed_ft": obs["v"], "predicted_ft": pred["v"]})
    table["extra_water_ft"] = table["observed_ft"] - table["predicted_ft"]
    # Quality flag from NOAA: 'p' = preliminary (not yet reviewed), 'v' = verified.
    table["quality"] = obs["q"]

    table.index.name = "time_utc"
    table.insert(0, "time_local", table.index.tz_convert(LOCAL_TZ))
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--station", default="9410170", help="NOAA station id (default: San Diego)")
    parser.add_argument("--days", type=int, default=45, help="how many days back from today")
    parser.add_argument("--start", type=date.fromisoformat, help="start date YYYY-MM-DD (overrides --days)")
    parser.add_argument("--end", type=date.fromisoformat, help="end date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    end = args.end or date.today()
    start = args.start or end - timedelta(days=args.days)
    station_name = STATIONS.get(args.station, args.station)
    downloaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print(f"Downloading {station_name} ({args.station}) from {start} to {end} ...")
    observed = fetch_noaa(args.station, "water_level", start, end)
    predicted = fetch_noaa(args.station, "predictions", start, end)
    print(f"  {len(observed)} observed readings, {len(predicted)} predicted readings")

    # Keep an untouched copy of exactly what NOAA sent (not committed to git).
    tag = f"{args.station}_{start:%Y%m%d}_{end:%Y%m%d}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"water_levels_{tag}.json"
    raw_path.write_text(json.dumps({"observed": observed, "predicted": predicted}))

    table = build_table(observed, predicted)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"water_levels_{tag}.csv"
    table.to_csv(out_path, float_format="%.3f")

    # A small "label" file next to the data: where it came from and when.
    meta = {
        "source": "NOAA CO-OPS Tides & Currents API",
        "source_url": API_URL,
        "station": args.station,
        "station_name": station_name,
        "start_date": str(start),
        "end_date": str(end),
        "datum": "MLLW",
        "units": "feet",
        "interval": "6 minutes",
        "downloaded_at_utc": downloaded_at,
        "quality_counts": table["quality"].value_counts().to_dict(),
        "columns": {
            "observed_ft": "measured water level",
            "predicted_ft": "astronomical tide prediction (moon + sun only)",
            "extra_water_ft": "observed - predicted",
            "quality": "p = preliminary, v = verified by NOAA",
        },
    }
    out_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))

    # Quick summary in the terminal.
    peak_time = table["observed_ft"].idxmax()
    peak = table.loc[peak_time]
    print(f"Saved {out_path.relative_to(PROJECT_ROOT)}")
    print(f"  Highest water: {peak['observed_ft']:.2f} ft at {peak['time_local']:%a %b %d %I:%M %p} "
          f"(predicted {peak['predicted_ft']:.2f} ft, extra {peak['extra_water_ft']:+.2f} ft)")
    print(f"  Average extra water over the period: {table['extra_water_ft'].mean():+.2f} ft")


if __name__ == "__main__":
    main()
