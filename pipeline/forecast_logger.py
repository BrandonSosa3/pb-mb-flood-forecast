"""Save one snapshot of everything we know about the next few days.

Each run freezes the forecast INPUTS as they were at that moment, so that
later we can show exactly what the tool would have predicted - with no
hindsight. Run it on a schedule (GitHub Actions, twice a day).

What it saves, in forecast_log/YYYY/MM/<issued>Z/:
  tides.csv.gz   Predicted tide (6-min) for the next 4 days at La Jolla
                 (ocean side) and San Diego (bay side), plus the current
                 extra water and the still-water forecast = tide + extra water.
  waves.csv.gz   CDIP MOP wave forecast (every 3 h, next 4 days) at ~66 points
                 along Mission Beach + Pacific Beach, from two models.
  alerts.json    Active National Weather Service alerts for the San Diego coast.
  weather.csv.gz NWS hourly forecast for Mission Beach (next 4 days): rain amount,
                 chance of rain, wind and gusts. Rain during a high tide can't drain
                 (storm-drain outlets are underwater), and onshore wind pushes water up.
  surf.json      NWS Surf Zone Forecast for San Diego County beaches (surf height text per day).
  weather_obs.csv.gz  What the San Diego airport weather station (KSAN) measured over
                 the last 2 days, to check the weather forecast against later.
  meta.json      When it ran, data sources and their issue times, current
                 extra water, and any errors.

"Persistence forecast" for extra water: we assume the current extra water
(its 25-hour average) stays the same for the next 4 days. Simple on purpose;
the logs will tell us how well that works.

Usage:
  python pipeline/forecast_logger.py
"""

from __future__ import annotations

import json
import re
import sys
import traceback
import warnings
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import xarray as xr

from noaa_tides import PROJECT_ROOT, STATIONS, fetch_noaa, to_frame

LOG_DIR = PROJECT_ROOT / "forecast_log"
HORIZON = timedelta(days=4)

# Which gauge represents which side of our study area.
# Gauges with live measurements. 9410170 (San Diego Bay) is kept as a reference;
# its side label was "bay" in snapshots before 2026-11-13T2330Z.
TIDE_STATIONS = {"9410230": "ocean", "9410170": "san_diego_bay"}
# Mission Bay has tide predictions but no gauge: we add La Jolla's extra water.
MISSION_BAY = "9410196"

# CDIP MOP points ~100 m apart, from the Mission Beach jetty (D0360) to north
# Pacific Beach near Tourmaline (D0425). Each sits at ~10 m water depth.
MOP_POINTS = range(360, 426)
MOP_URL = "https://thredds.cdip.ucsd.edu/thredds/dodsC/cdip/model/MOP_alongshore/D{:04d}_{}.nc"
MOP_MODELS = {
    "forecast": "CDIP MOP driven by NOAA WaveWatch III",
    "ecmwf_fc": "CDIP MOP driven by ECMWF wave model",
}
WAVE_VARS = {
    "waveHs": "wave_height_m",       # significant wave height
    "waveTp": "peak_period_s",       # period of the strongest waves
    "waveDp": "peak_direction_deg",  # direction they come FROM (degrees, true north)
    "waveTa": "mean_period_s",
}

NWS_ALERTS_URL = "https://api.weather.gov/alerts/active?zone=CAZ043"  # San Diego County Coastal Areas
# NWS hourly forecast grid cell that covers Mission Beach / south Pacific Beach
# (from api.weather.gov/points/32.78,-117.252 -> office SGX, cell 54,17).
NWS_GRID_URL = "https://api.weather.gov/gridpoints/SGX/54,17"
NWS_OBS_URL = "https://api.weather.gov/stations/KSAN/observations"  # San Diego airport, ~5 km SE
GRID_VARS = {  # NWS name: (our column, conversion from NWS units, how to spread over its time span)
    "quantitativePrecipitation": ("rain_in", 1 / 25.4, "split"),     # mm per span -> inches per hour
    "probabilityOfPrecipitation": ("rain_chance_pct", 1, "repeat"),
    "windSpeed": ("wind_mph", 0.621371, "repeat"),                  # km/h -> mph
    "windGust": ("gust_mph", 0.621371, "repeat"),
    "windDirection": ("wind_from_deg", 1, "repeat"),                 # direction wind comes FROM
}
NWS_SRF_URL = "https://api.weather.gov/products/types/SRF/locations/SGX"  # Surf Zone Forecast
SRF_ZONE = "CAZ043"  # San Diego County Coastal Areas
# NWS asks every client to identify itself; generic name, no personal info.
HTTP_HEADERS = {"User-Agent": "coastal-flood-forecast-research (github.com)"}


def log_tides(now: datetime) -> tuple[pd.DataFrame, dict]:
    """Predicted tide for the next 4 days + current extra water, per gauge."""
    frames, summary = [], {}
    for station, side in TIDE_STATIONS.items():
        # Last ~2 days of measurements (to measure current extra water).
        past_start = (now - timedelta(days=2)).date()
        observed = to_frame(fetch_noaa(station, "water_level", past_start, now.date()))["v"]
        predicted = to_frame(
            fetch_noaa(station, "predictions", past_start, (now + HORIZON).date())
        )["v"]

        extra = (observed - predicted.reindex(observed.index)).dropna()
        last_obs_time = extra.index.max()
        extra_25h = extra[extra.index > last_obs_time - timedelta(hours=25)].mean()

        future = predicted[(predicted.index >= now) & (predicted.index <= now + HORIZON)]
        frame = pd.DataFrame({
            "station": station,
            "side": side,
            "predicted_tide_ft": future,
            "extra_water_ft": extra_25h,
            "still_water_ft": future + extra_25h,
        })
        frame.index.name = "time_utc"
        frames.append(frame)

        peak_time = frame["still_water_ft"].idxmax()
        summary[station] = {
            "name": STATIONS[station],
            "side": side,
            "last_observation_utc": str(last_obs_time),
            "latest_observed_ft": round(float(observed.loc[last_obs_time]), 3),
            "extra_water_25h_ft": round(float(extra_25h), 3),
            "peak_still_water_ft": round(float(frame.loc[peak_time, "still_water_ft"]), 3),
            "peak_time_utc": str(peak_time),
        }
    # Mission Bay (what the bay-side flood model uses): prediction + La Jolla extra water.
    lj_extra = summary["9410230"]["extra_water_25h_ft"]
    mb = to_frame(fetch_noaa(MISSION_BAY, "predictions", now.date(), (now + HORIZON).date()))["v"]
    future = mb[(mb.index >= now) & (mb.index <= now + HORIZON)]
    frame = pd.DataFrame({"station": MISSION_BAY, "side": "mission_bay", "predicted_tide_ft": future,
                          "extra_water_ft": lj_extra, "still_water_ft": future + lj_extra})
    frame.index.name = "time_utc"
    frames.append(frame)
    peak_time = frame["still_water_ft"].idxmax()
    summary[MISSION_BAY] = {
        "name": STATIONS[MISSION_BAY], "side": "mission_bay",
        "extra_water_25h_ft": round(float(lj_extra), 3), "extra_water_from": "9410230",
        "peak_still_water_ft": round(float(frame.loc[peak_time, "still_water_ft"]), 3),
        "peak_time_utc": str(peak_time),
    }
    return pd.concat(frames).round(3), summary


def log_waves(now: datetime) -> tuple[pd.DataFrame, dict]:
    """CDIP MOP wave forecast at every point along the study coast, both models."""
    frames, issued = [], {}
    warnings.filterwarnings("ignore")  # netCDF chatter
    for model in MOP_MODELS:
        for point in MOP_POINTS:
            label = f"D{point:04d}"
            ds = xr.open_dataset(MOP_URL.format(point, model))
            # CDIP times are UTC but stored without a timezone label, so compare without one.
            start, end = (now - timedelta(hours=3)).replace(tzinfo=None), (now + HORIZON).replace(tzinfo=None)
            window = ds[list(WAVE_VARS)].sel(waveTime=slice(start, end))
            frame = window.to_dataframe()[list(WAVE_VARS)].rename(columns=WAVE_VARS)
            frame.index = frame.index.tz_localize("UTC")
            frame.index.name = "time_utc"
            frame.insert(0, "model", model)
            frame.insert(1, "point", label)
            frame.insert(2, "lat", round(float(ds.metaLatitude), 5))
            frame.insert(3, "lon", round(float(ds.metaLongitude), 5))
            frame.insert(4, "shore_normal_deg", round(float(ds.metaShoreNormal), 1))
            frames.append(frame)
            issued.setdefault(model, ds.attrs.get("date_issued"))
            ds.close()
    return pd.concat(frames).round(3), issued


def log_alerts() -> list[dict]:
    """Active NWS alerts (coastal flood, high surf, ...) for the San Diego coast."""
    response = requests.get(NWS_ALERTS_URL, headers=HTTP_HEADERS, timeout=30)
    response.raise_for_status()
    keep = ["event", "severity", "headline", "onset", "ends", "expires", "sent", "description"]
    return [{k: f["properties"].get(k) for k in keep} for f in response.json()["features"]]


def hourly(values: list[dict], scale: float, how: str) -> pd.Series:
    """NWS grid values come as "start/duration" spans (e.g. 6 hours of rain). Turn them into one
    value per hour: rain totals are split evenly across the span, everything else repeats."""
    out = {}
    for v in values:
        if v["value"] is None:
            continue
        start, span = v["validTime"].split("/")
        hours = max(1, round(pd.Timedelta(span).total_seconds() / 3600))
        value = v["value"] * scale / (hours if how == "split" else 1)
        for t in pd.date_range(pd.Timestamp(start), periods=hours, freq="h"):
            out[t] = value
    return pd.Series(out, dtype=float)


def log_weather(now: datetime) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """NWS hourly forecast for Mission Beach + last 2 days measured at the airport."""
    r = requests.get(NWS_GRID_URL, headers=HTTP_HEADERS, timeout=30)
    r.raise_for_status()
    grid = r.json()["properties"]
    cols = {col: hourly(grid[name]["values"], scale, how) for name, (col, scale, how) in GRID_VARS.items()}
    fc = pd.DataFrame(cols)
    fc = fc[(fc.index >= pd.Timestamp(now).floor("h")) & (fc.index <= pd.Timestamp(now + HORIZON))]
    fc.index.name = "time_utc"

    r = requests.get(NWS_OBS_URL, headers=HTTP_HEADERS, timeout=30,
                     params={"start": (now - timedelta(days=2)).isoformat()})
    r.raise_for_status()
    rows = []
    for f in r.json()["features"]:
        p = f["properties"]
        val = lambda k: (p.get(k) or {}).get("value")  # missing or null -> None
        rows.append({"time_utc": pd.Timestamp(p["timestamp"]),
                     "rain_last_hour_in": None if val("precipitationLastHour") is None else val("precipitationLastHour") / 25.4,
                     "pressure_hpa": None if val("barometricPressure") is None else val("barometricPressure") / 100,
                     "wind_mph": None if val("windSpeed") is None else val("windSpeed") * 0.621371,
                     "gust_mph": None if val("windGust") is None else val("windGust") * 0.621371,
                     "wind_from_deg": val("windDirection"), "sky": p.get("textDescription")})
    obs = pd.DataFrame(rows).set_index("time_utc").sort_index()

    summary = {"grid_updated_utc": grid.get("updateTime"),
               "rain_next_4_days_in": round(float(fc["rain_in"].sum()), 2),
               "max_rain_chance_pct": None if fc["rain_chance_pct"].isna().all() else int(fc["rain_chance_pct"].max()),
               "max_gust_mph": None if fc["gust_mph"].isna().all() else round(float(fc["gust_mph"].max()), 1)}
    return fc.round(3), obs.round(3), summary


def log_surf() -> dict:
    """Latest NWS Surf Zone Forecast: surf height text for each day it covers (San Diego County)."""
    r = requests.get(NWS_SRF_URL, headers=HTTP_HEADERS, timeout=30)
    r.raise_for_status()
    latest = r.json()["@graph"][0]
    r = requests.get(latest["@id"], headers=HTTP_HEADERS, timeout=30)
    r.raise_for_status()
    text = r.json()["productText"]
    block = next(b for b in text.split("$$") if SRF_ZONE in b)
    days = []
    # Each day starts with a line like ".TODAY..." or ".SUNDAY..."; "Surf Height....." may wrap onto
    # indented continuation lines.
    for m in re.finditer(r"^\.([A-Z ]+)\.\.\.\s*$(.*?)(?=^\.[A-Z]|^&&)", block, re.M | re.S):
        h = re.search(r"Surf Height\.+(.*?)\n(?! {10,})", m.group(2), re.S)
        if h:
            days.append({"label": m.group(1).strip().title(), "surf": " ".join(h.group(1).split())})
    return {"issued_utc": latest["issuanceTime"], "zone": SRF_ZONE, "product_url": latest["@id"], "days": days}


def main() -> int:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    run_dir = LOG_DIR / f"{now:%Y}" / f"{now:%m}" / f"{now:%Y-%m-%dT%H%M}Z"
    run_dir.mkdir(parents=True, exist_ok=True)
    meta: dict = {"issued_at_utc": now.isoformat(), "horizon_hours": HORIZON.total_seconds() / 3600,
                  "sources": {}, "errors": {}}

    # Each source is independent: if one fails, still save the others.
    def attempt(name, fn):
        try:
            return fn()
        except Exception:
            meta["errors"][name] = traceback.format_exc(limit=3)
            print(f"  ! {name} failed (recorded in meta.json)")
            return None

    print("Tides ...")
    tides = attempt("tides", lambda: log_tides(now))
    if tides:
        tides[0].to_csv(run_dir / "tides.csv.gz")
        meta["tides"] = tides[1]
        meta["sources"]["tides"] = "NOAA CO-OPS API (water_level + predictions, MLLW, feet, 6-min)"

    print("Waves ...")
    waves = attempt("waves", lambda: log_waves(now))
    if waves:
        waves[0].to_csv(run_dir / "waves.csv.gz")
        meta["sources"]["waves"] = {"url": MOP_URL.format(0, "<model>"), "models": MOP_MODELS,
                                    "model_issued_utc": waves[1], "points": f"D{MOP_POINTS[0]:04d}-D{MOP_POINTS[-1]:04d}"}

    print("NWS alerts ...")
    alerts = attempt("alerts", log_alerts)
    if alerts is not None:
        (run_dir / "alerts.json").write_text(json.dumps(alerts, indent=2))
        meta["active_alerts"] = [a["event"] for a in alerts]
        meta["sources"]["alerts"] = NWS_ALERTS_URL

    print("Weather ...")
    weather = attempt("weather", lambda: log_weather(now))
    if weather:
        weather[0].to_csv(run_dir / "weather.csv.gz")
        weather[1].to_csv(run_dir / "weather_obs.csv.gz")
        meta["weather"] = weather[2]
        meta["sources"]["weather"] = {"forecast": NWS_GRID_URL, "observed": NWS_OBS_URL + " (San Diego airport)",
                                      "units": "inches, mph, hPa; rain totals split evenly over each NWS time span"}

    print("NWS surf forecast ...")
    surf = attempt("surf", log_surf)
    if surf:
        (run_dir / "surf.json").write_text(json.dumps(surf, indent=2))
        meta["sources"]["surf"] = NWS_SRF_URL + f" (zone {SRF_ZONE})"

    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Short human-readable summary.
    print(f"\nSaved {run_dir.relative_to(PROJECT_ROOT)}")
    for station, s in meta.get("tides", {}).items():
        peak_local = pd.Timestamp(s["peak_time_utc"]).tz_convert("America/Los_Angeles")
        print(f"  {s['name']} ({s['side']}): extra water {s['extra_water_25h_ft']:+.2f} ft; "
              f"highest still water next 4 days {s['peak_still_water_ft']:.2f} ft, {peak_local:%a %b %d %-I:%M %p}")
    if waves:
        all_waves = waves[0].reset_index()  # many rows share a time, so use row numbers
        for model in MOP_MODELS:
            w = all_waves[all_waves["model"] == model]
            biggest = w.loc[w["wave_height_m"].idxmax()]
            local = biggest["time_utc"].tz_convert("America/Los_Angeles")
            print(f"  Biggest waves next 4 days ({model}): {biggest['wave_height_m'] * 3.281:.1f} ft, "
                  f"{biggest['peak_period_s']:.0f} s period at {biggest['point']}, {local:%a %-I %p}")
    print(f"  NWS alerts: {', '.join(meta.get('active_alerts', [])) or 'none'}")
    if weather:
        w = weather[2]
        print(f"  Weather next 4 days: {w['rain_next_4_days_in']:.2f} in of rain "
              f"(highest chance {w['max_rain_chance_pct']}%), strongest gust {w['max_gust_mph']} mph")

    if len(meta["errors"]) == 5:
        return 1  # nothing worked - make the scheduled run show as failed
    return 0


if __name__ == "__main__":
    sys.exit(main())
