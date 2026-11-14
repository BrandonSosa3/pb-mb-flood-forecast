"""Hour-by-hour Mission Bay water level for past events, for the map's "Play" animation.

Mission Bay level = NOAA Mission Bay (9410196) tide prediction + extra water measured at La Jolla
(same method as the backtest, risk.mission_bay_still_water). Each event plays one high tide.

Output: web/public/data/events.json
Usage : python pipeline/events_3d.py
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pandas as pd

from noaa_tides import PROJECT_ROOT
from risk import mission_bay_still_water

OUT = PROJECT_ROOT / "web" / "public" / "data" / "events.json"
BEFORE_PEAK, AFTER_PEAK = pd.Timedelta(hours=3), pd.Timedelta(hours=2)  # the part of the tide that plays
EVENTS = [  # key, label, local day (searched for its highest tide), berm scenario, note
    ("oct26", "Oct 26, 2026", "2026-10-26 00:00", "2026-10-26 23:59", "fails",
     "The sand berm along Bayside Walk broke during this high tide (exact time not reported), "
     "so this plays it with the berm gone."),
    ("oct27", "Oct 27, 2026", "2026-10-27 00:00", "2026-10-27 23:59", "holds",
     "The City rebuilt the berm and it held, so bay water stayed out of most streets."),
]


def main() -> None:
    out = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "method": "NOAA 9410196 Mission Bay prediction + La Jolla 9410230 measured extra water, ft MLLW",
           "events": []}
    for key, label, start, end, berm, note in EVENTS:
        t0, t1 = pd.Timestamp(start, tz="America/Los_Angeles"), pd.Timestamp(end, tz="America/Los_Angeles")
        s = mission_bay_still_water(t0.date(), (t1 + pd.Timedelta(days=1)).date()).tz_convert("America/Los_Angeles")
        s = s[(s.index >= t0) & (s.index <= t1)]
        peak = s.idxmax()
        s = s[(s.index >= peak - BEFORE_PEAK) & (s.index <= peak + AFTER_PEAK)]
        frames = s.resample("20min").mean().dropna().round(2)  # 20-min steps: smooth but small
        out["events"].append({"key": key, "label": label, "berm": berm, "note": note,
                              "peak_ft": float(s.max().round(2)), "peak_time": peak.isoformat(),
                              "frames": [[t.isoformat(), float(v)] for t, v in frames.items()]})
        print(f"{label}: {len(frames)} frames, peak {s.max():.2f} ft at {s.idxmax():%-I:%M %p}")
    OUT.write_text(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
