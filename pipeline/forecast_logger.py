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
TIDE_STATIONS = {"9410230": "ocean", "9410170": "bay"}

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

    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Short human-readable summary.
    print(f"\nSaved {run_dir.relative_to(PROJECT_ROOT)}")
    for station, s in meta.get("tides", {}).items():
        peak_local = pd.Timestamp(s["peak_time_utc"]).tz_convert("America/Los_Angeles")
        print(f"  {s['name']} ({s['side']}): extra water now {s['extra_water_25h_ft']:+.2f} ft; "
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

    if len(meta["errors"]) == 3:
        return 1  # nothing worked - make the scheduled run show as failed
    return 0


if __name__ == "__main__":
    sys.exit(main())
