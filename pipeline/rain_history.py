"""Hourly rain at San Diego airport (KSAN), and how often rain has fallen near a high tide.

Why: storm drains in Mission Beach / Pacific Beach empty into Mission Bay and the ocean. Near high
tide their outlets are underwater, so rain has nowhere to go and ponds in low streets. This script
checks how often the site's rain rule would have fired in the past (so it warns on real storms,
not every drizzle) and lists those days for checking against reports.

Rain rule (used by build_site_data.py):
  rain within RAIN_WINDOW_H hours of the day's highest tide >= RAIN_NEAR_TIDE_IN inches
  AND the water is above the ground of at least RAIN_MIN_PROPERTIES properties in the area
  -> the area's rating goes up one level (at most to Moderate).

Data: Iowa Environmental Mesonet ASOS archive (routine hourly METAR precipitation, inches; "T" =
trace, counted as 0). Station KSAN, ~5 km SE of Mission Beach. Water level: NOAA La Jolla hourly
observed (already downloaded in Phase 1), standing in for Mission Bay.

Outputs: data/processed/hourly_rain_KSAN.csv.gz (+ .meta.json), docs/evidence/rain_near_high_tide.md

Usage: python pipeline/rain_history.py
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pandas as pd
import requests

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

IEM_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
START_YEAR = 2000
RAIN_NEAR_TIDE_IN = 0.25
RAIN_WINDOW_H = 3
LEVEL_FT = 6.0  # lowest Mission Bay level at which Mission Beach has many properties below the water
OUT = PROCESSED_DIR / "hourly_rain_KSAN.csv.gz"
REPORT = PROJECT_ROOT / "docs" / "evidence" / "rain_near_high_tide.md"
HEADERS = {"User-Agent": "coastal-flood-forecast-research (github.com)"}


def download() -> pd.Series:
    now = datetime.now(timezone.utc)
    params = {"station": "SAN", "data": "p01i", "year1": START_YEAR, "month1": 1, "day1": 1,
              "year2": now.year, "month2": now.month, "day2": now.day, "tz": "Etc/UTC",
              "format": "onlycomma", "latlon": "no", "missing": "M", "trace": "T", "report_type": 3}
    r = requests.get(IEM_URL, params=params, headers=HEADERS, timeout=300)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df["time_utc"] = pd.to_datetime(df.valid, utc=True)
    rain = pd.to_numeric(df.p01i.replace("T", "0"), errors="coerce")
    s = pd.Series(rain.to_numpy(), index=df.time_utc).dropna()
    s = s.groupby(s.index.floor("h")).max()  # one routine report per hour
    s[s > 0].rename("rain_in").to_csv(OUT)  # dry hours dropped (missing = dry)
    meta = {"source": "Iowa Environmental Mesonet ASOS archive, station KSAN (San Diego Intl)",
            "url": IEM_URL, "downloaded_utc": now.isoformat(timespec="seconds"),
            "variable": "p01i, precipitation in the past hour, inches (routine METAR); trace = 0",
            "start": str(s.index.min()), "end": str(s.index.max()), "hours_reported": int(len(s)),
            "file_holds": "only hours with rain > 0"}
    (OUT.with_suffix("").with_suffix(".meta.json")).write_text(json.dumps(meta, indent=2))
    return s


def main() -> None:
    rain = download()
    tide = pd.read_csv(PROCESSED_DIR / "hourly_extra_water_9410230.csv.gz", parse_dates=["time_utc"])
    tide = tide.set_index("time_utc").observed_ft.dropna()
    tide = tide[tide.index >= rain.index.min()]
    local = tide.tz_convert("America/Los_Angeles")
    hourly_rain = rain.reindex(pd.date_range(rain.index.min(), rain.index.max(), freq="h"), fill_value=0)

    rows = []
    for day, t in local.groupby(local.index.date):
        peak_t = t.idxmax()
        w = hourly_rain[peak_t - pd.Timedelta(hours=RAIN_WINDOW_H): peak_t + pd.Timedelta(hours=RAIN_WINDOW_H)]
        day_rain = hourly_rain[(hourly_rain.index >= peak_t.normalize()) &
                               (hourly_rain.index < peak_t.normalize() + pd.Timedelta(days=1))].sum()
        rows.append({"day": day, "high_tide": peak_t.strftime("%-I %p"), "level_ft": round(float(t.max()), 2),
                     "rain_near_tide_in": round(float(w.sum()), 2), "rain_day_in": round(float(day_rain), 2)})
    days = pd.DataFrame(rows)
    rainy = days[days.rain_near_tide_in >= RAIN_NEAR_TIDE_IN]
    fires = rainy[rainy.level_ft >= LEVEL_FT]
    years = days.day.map(lambda d: d.year).nunique()

    lines = [
        "# Rain near high tide, 2000–2026 (rule check)",
        "",
        f"_Written by `pipeline/rain_history.py` on {datetime.now(timezone.utc):%Y-%m-%d}._",
        "",
        f"Rule: ≥ {RAIN_NEAR_TIDE_IN} in of rain at San Diego airport within {RAIN_WINDOW_H} h of the day's highest",
        f"tide, with the water at La Jolla ≥ {LEVEL_FT} ft MLLW (Mission Beach then has 100+ properties on ground",
        "below the water). La Jolla stands in for Mission Bay (similar levels).",
        "",
        f"- Days with ≥ {RAIN_NEAR_TIDE_IN} in near the high tide: **{len(rainy)}** in {years} years "
        f"(~{len(rainy) / years:.1f} a year)",
        f"- Of those, high tide ≥ {LEVEL_FT} ft (rule fires): **{len(fires)}** (~{len(fires) / years:.1f} a year)",
        "",
        "## Days the rule would have fired",
        "| Day | High tide | Water (ft) | Rain near tide (in) | Rain that day (in) |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {r.day:%a %b %d, %Y} | {r.high_tide} | {r.level_ft} | {r.rain_near_tide_in} | {r.rain_day_in} |"
              for r in fires.itertuples()]
    lines += ["", "## Wettest high tides below the level (rule does not fire)",
              "| Day | Water (ft) | Rain near tide (in) |", "|---|---|---|"]
    lines += [f"| {r.day:%a %b %d, %Y} | {r.level_ft} | {r.rain_near_tide_in} |"
              for r in rainy[rainy.level_ft < LEVEL_FT].nlargest(8, "rain_near_tide_in").itertuples()]
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
