"""Download decades of hourly NOAA water levels and measure extra water over time.

Steps:
  1. Download hourly measured water level + hourly predicted tide, 1980 -> today.
     NOAA's verified hourly data lags a month or two, so the most recent
     weeks are filled in from the preliminary 6-minute data (top of each hour).
  2. Extra water = measured - predicted, every hour.
  3. Monthly average extra water.
  4. Baseline ("normal for that date"): a straight-line trend through the
     monthly averages, fitted WITHOUT the big El Nino winters so they don't
     drag it up. This captures slow sea level rise since NOAA's prediction
     reference period (1983-2001).
  5. Anomaly = monthly extra water - baseline. This is the part caused by
     El Nino / Kelvin waves / storms, not long-term sea level rise.

Outputs (data/processed/):
  hourly_extra_water_<station>.csv.gz   every hour since 1980
  monthly_extra_water_<station>.csv     monthly averages, baseline, anomaly
  (+ .meta.json for each)

Usage:
  python pipeline/noaa_history.py                 # San Diego, 1980 -> today
  python pipeline/noaa_history.py --start-year 1990 --station 9410230
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from noaa_tides import API_URL, LOCAL_TZ, PROCESSED_DIR, PROJECT_ROOT, STATIONS, fetch_noaa, to_frame

# Winters left out when fitting the baseline (strong El Ninos + the current one).
EL_NINO_WINTERS = {
    "1982-83": ("1982-06", "1983-08"),
    "1997-98": ("1997-05", "1998-08"),
    "2015-16": ("2015-03", "2016-08"),
    "2026-27": ("2026-05", "2027-12"),
}
MIN_HOURS_PER_MONTH = 0.8 * 24 * 28  # skip months where the gauge was mostly offline


def download_hourly(station: str, start: date, end: date) -> pd.DataFrame:
    """Hourly measured + predicted water level, with the recent gap filled from 6-min data."""
    print("  measured (verified hourly) ...")
    measured = to_frame(fetch_noaa(station, "hourly_height", start, end, chunk_days=365))["v"]
    measured = measured.rename("observed_ft").to_frame().assign(quality="v")

    # Fill from the end of verified data to today with preliminary 6-min readings.
    last_verified = measured.index.max()
    fill_start = (last_verified + timedelta(hours=1)).date()
    if fill_start <= end:
        print(f"  measured (preliminary 6-min, {fill_start} -> {end}) ...")
        recent = to_frame(fetch_noaa(station, "water_level", fill_start, end))
        recent = recent[recent.index.minute == 0]  # top of each hour, like hourly_height
        recent = recent[recent.index > last_verified]
        measured = pd.concat([measured, recent[["v", "q"]].rename(columns={"v": "observed_ft", "q": "quality"})])

    print("  predicted (hourly) ...")
    predicted = to_frame(fetch_noaa(station, "predictions", start, end, interval="h", chunk_days=365))["v"]

    table = measured.join(predicted.rename("predicted_ft"), how="outer")
    table["extra_water_ft"] = table["observed_ft"] - table["predicted_ft"]
    table.index.name = "time_utc"
    return table[["observed_ft", "predicted_ft", "extra_water_ft", "quality"]]


def monthly_summary(hourly: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Monthly average extra water, a sea-level-rise baseline, and the anomaly."""
    local = hourly["extra_water_ft"].tz_convert(LOCAL_TZ).tz_localize(None)
    grouped = local.resample("MS")
    monthly = pd.DataFrame({"extra_water_ft": grouped.mean(), "hours": grouped.count()})
    # Months where the gauge was mostly offline are blanked out. The current
    # month is kept (if it has at least a week of data) but flagged as partial.
    monthly["partial"] = False
    current = monthly.index[-1]
    monthly.loc[current, "partial"] = True
    too_few = monthly["hours"] < MIN_HOURS_PER_MONTH
    too_few[current] = monthly.loc[current, "hours"] < 7 * 24
    monthly.loc[too_few, "extra_water_ft"] = np.nan
    monthly.index.name = "month"

    # Mark El Nino winters, then fit the baseline on everything else.
    monthly["el_nino_winter"] = ""
    for name, (a, b) in EL_NINO_WINTERS.items():
        monthly.loc[a:b, "el_nino_winter"] = name
    years = monthly.index.year + (monthly.index.month - 0.5) / 12  # decimal year
    fit_rows = (monthly["el_nino_winter"] == "") & monthly["extra_water_ft"].notna()
    slope, intercept = np.polyfit(years[fit_rows], monthly.loc[fit_rows, "extra_water_ft"], 1)

    monthly["baseline_ft"] = slope * years + intercept
    monthly["anomaly_ft"] = monthly["extra_water_ft"] - monthly["baseline_ft"]
    trend = {
        "slope_ft_per_decade": round(slope * 10, 3),
        "baseline_today_ft": round(slope * (date.today().year + date.today().timetuple().tm_yday / 365) + intercept, 3),
        "fit_excludes": EL_NINO_WINTERS,
    }
    return monthly, trend


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--station", default="9410170")
    parser.add_argument("--start-year", type=int, default=1980)
    args = parser.parse_args()

    start, end = date(args.start_year, 1, 1), date.today()
    station_name = STATIONS.get(args.station, args.station)
    downloaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"Downloading hourly history for {station_name} ({args.station}), {start} -> {end}")

    hourly = download_hourly(args.station, start, end)
    monthly, trend = monthly_summary(hourly)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    hourly_path = PROCESSED_DIR / f"hourly_extra_water_{args.station}.csv.gz"
    monthly_path = PROCESSED_DIR / f"monthly_extra_water_{args.station}.csv"
    hourly.to_csv(hourly_path, float_format="%.3f")
    monthly.to_csv(monthly_path, float_format="%.3f")

    meta = {
        "source": "NOAA CO-OPS Tides & Currents API",
        "source_url": API_URL,
        "products": "hourly_height (verified), water_level (preliminary fill), predictions interval=h",
        "station": args.station,
        "station_name": station_name,
        "start_date": str(start),
        "end_date": str(end),
        "last_verified_hour_utc": str(hourly.index[hourly["quality"] == "v"].max()),
        "datum": "MLLW",
        "units": "feet",
        "downloaded_at_utc": downloaded_at,
        "baseline": trend,
    }
    for path in (hourly_path, monthly_path):
        path.with_name(path.name.split(".")[0] + ".meta.json").write_text(json.dumps(meta, indent=2))

    print(f"Saved {hourly_path.relative_to(PROJECT_ROOT)} ({len(hourly):,} hours)")
    print(f"Saved {monthly_path.relative_to(PROJECT_ROOT)}")
    print(f"  Baseline rises {trend['slope_ft_per_decade']:+.2f} ft per decade; "
          f"'normal' extra water today = {trend['baseline_today_ft']:+.2f} ft")
    for name in EL_NINO_WINTERS:
        winter = monthly[monthly["el_nino_winter"] == name]["anomaly_ft"].dropna()
        if len(winter):
            print(f"  {name}: biggest monthly anomaly {winter.max():+.2f} ft ({winter.idxmax():%b %Y})")


if __name__ == "__main__":
    main()
