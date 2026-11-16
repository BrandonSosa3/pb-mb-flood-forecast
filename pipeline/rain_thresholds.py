"""How much rain causes flood reports in La Jolla, Pacific Beach and Mission Beach? (rain rating scale)

Storms = runs of days with rain at San Diego airport (KSAN, hourly, 2018 on: when Get It Done reports
start). For each storm: total, heaviest hour, heaviest 6 hours. Reports = City Get It Done
"street flooded" reports (water-main / leak / sprinkler text removed) dated during the storm or the
day after, per neighborhood; "extra" = minus the usual dry-day rate of such reports.

The rating uses the heaviest 6 hours, because the NWS forecast gives rain in 6-hour blocks (it can't
see a single heavy hour). Levels are in risk.RAIN_6H_LEVELS_IN; this script shows the evidence.

Inputs : data/processed/hourly_rain_KSAN.csv.gz (rain_history.py), flood_reports.csv (flood_reports.py)
Outputs: data/processed/storms.csv, docs/evidence/rain/rain_thresholds.md

Usage: python pipeline/rain_thresholds.py
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from rain_ponds import NEIGHBORHOODS
from risk import RAIN_6H_LEVELS_IN, rain_level

TZ = "America/Los_Angeles"
START = "2018-01-01"
WET_DAY_IN = 0.01
MIN_STORM_IN = 0.05
NOT_RAIN = re.compile(r"water ?main|main break|leak|sprinkl|irrigat|broken pipe|pipe burst|hydrant", re.I)
OUT_MD = PROJECT_ROOT / "docs" / "evidence" / "rain" / "rain_thresholds.md"


def storms(hourly: pd.Series) -> pd.DataFrame:
    day = hourly.resample("D").sum()
    wet = day >= WET_DAY_IN
    run = (wet != wet.shift()).cumsum()[wet]
    rows = []
    for _, g in day[wet].groupby(run):
        s, e = g.index.min(), g.index.max() + pd.Timedelta(days=1)
        h = hourly[s:e - pd.Timedelta(hours=1)]
        rows.append({"start": s.date(), "end": g.index.max().date(), "total_in": round(h.sum(), 2),
                     "max_1h_in": round(h.max(), 2), "max_6h_in": round(h.rolling(6, min_periods=1).sum().max(), 2)})
    df = pd.DataFrame(rows)
    return df[df.total_in >= MIN_STORM_IN].reset_index(drop=True)


def main() -> None:
    rain = pd.read_csv(PROCESSED_DIR / "hourly_rain_KSAN.csv.gz", parse_dates=["time_utc"]).set_index("time_utc")
    hourly = rain.rain_in.tz_convert(TZ).resample("h").sum()
    hourly = hourly[hourly.index >= pd.Timestamp(START, tz=TZ)]
    st = storms(hourly)

    rep = pd.read_csv(PROCESSED_DIR / "flood_reports.csv")
    rep = rep[(rep["type"] == "flooded") & ~rep.public_description.fillna("").str.contains(NOT_RAIN)]
    rep["date"] = pd.to_datetime(rep.date).dt.date
    span_days = (hourly.index.max() - hourly.index.min()).days
    dry = rep[rep.cause == "other"]
    background = {n: (dry.neighborhood == n).sum() / span_days for n in NEIGHBORHOODS}
    st["window_days"] = [(e - s).days + 2 for s, e in zip(st.start, st.end)]
    for n in NEIGHBORHOODS:
        r = rep[rep.neighborhood == n]
        st[n] = [int(((r.date >= s) & (r.date <= e + pd.Timedelta(days=1))).sum()) for s, e in zip(st.start, st.end)]
        st[f"{n} extra"] = (st[n] - background[n] * st.window_days).round(2)
    st["level"] = st.max_6h_in.map(rain_level)
    st.to_csv(PROCESSED_DIR / "storms.csv", index=False)

    years = span_days / 365.25
    lines = ["# How much rain causes flood reports? (rain rating scale)", "",
             f"_Written by `pipeline/rain_thresholds.py` on {datetime.now(timezone.utc):%Y-%m-%d}. Rain: San Diego "
             f"airport hourly, {START[:4]}–now ({len(st)} storms). Reports: City Get It Done 'street flooded' "
             "(water-main / leak / sprinkler text removed), during the storm or the day after._", "",
             "Rated by the **heaviest 6 hours of rain**, because the NWS forecast gives rain in 6-hour blocks. "
             "*With reports* = share of storms with at least one report in that neighborhood; *extra* = reports "
             "per storm above the usual dry-day rate (most flooding is never reported, so these are small "
             "numbers; what matters is that they rise with rain).", "",
             "| Rating | Heaviest 6 h | Storms | Per year | " +
             " | ".join(f"{n}: with reports / extra" for n in NEIGHBORHOODS) + " |",
             "|---|---|---|---|" + "---|" * len(NEIGHBORHOODS)]
    bounds = [0.0] + list(RAIN_6H_LEVELS_IN.values()) + [99.0]
    names = ["Low"] + list(RAIN_6H_LEVELS_IN)
    for i, name in enumerate(names):
        g = st[st.level == name]
        rng = f"{bounds[i]:g}–{bounds[i + 1]:g} in" if bounds[i + 1] < 99 else f"{bounds[i]:g} in +"
        cells = [f"{(g[n] >= 1).mean():.0%} / {g[f'{n} extra'].mean():+.1f}" if len(g) else "–" for n in NEIGHBORHOODS]
        lines.append(f"| {name} | {rng} | {len(g)} | {len(g) / years:.1f} | " + " | ".join(cells) + " |")
    lines += ["", "## Biggest storms", "", "| Start | Total | Heaviest hour | Heaviest 6 h | Rating | " +
              " | ".join(NEIGHBORHOODS) + " |", "|---|---|---|---|---|" + "---|" * len(NEIGHBORHOODS)]
    for r in st.nlargest(15, "max_6h_in").itertuples():
        lines.append(f"| {r.start} | {r.total_in} in | {r.max_1h_in} in | {r.max_6h_in} in | {r.level} | " +
                     " | ".join(str(st.loc[r.Index, n]) for n in NEIGHBORHOODS) + " |")
    lines += ["", "Limits: one rain gauge (the airport, ~5 km SE of Mission Beach; La Jolla's hills get more); "
              "reports undercount flooding and depend on who reports; same scale for all three neighborhoods "
              "(too few reports to tune each).", ""]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
