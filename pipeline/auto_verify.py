"""Score past forecasts automatically: what we said vs. what happened, with no human in the loop.

Runs in the forecast bot (GitHub Actions) every time. For each recent day (the last LOOKBACK_DAYS, not today):

  What we said   the forecast the site PUBLISHED from the last snapshot saved before that day began
                 (forecast_log/<snapshot>/site_forecast.json, written by build_site_data.py; for snapshots before
                 2026-11-17 recovered from git history, first published version). Never rebuilt with newer code:
                 coast rating per area (Mission Beach, Pacific Beach, Crown Point) and rain rating per
                 neighborhood (La Jolla, Pacific Beach, Mission Beach).
  What happened  evidence collected automatically:
                   - measured rain at San Diego airport (hourly, Iowa Environmental Mesonet)
                   - measured Mission Bay level (Mission Bay prediction + La Jolla measured extra water)
                   - City of San Diego Get It Done "street flooded" reports (water-main / leak / sprinkler
                     text removed), placed in each area by their coordinates
                   - NWS Local Storm Reports (flood, flash flood, heavy rain, coastal flood, high surf)
                   - local news headlines (outlets' own RSS feeds, checked every run and kept in a log)
                 turned into an observed level by fixed rules (OBSERVED_* below).
  Score          same level = right, one level apart = close, two or more = missed (under) or false alarm (over).
                 Coast days with no evidence at all are "unverified" (not counted): almost nobody reports water on
                 the boardwalk, so silence proves nothing. Rain days with no City reports still count (weak).
                 "Preliminary" until FINAL_AFTER_DAYS have passed (late City reports), then final.

Only days worth scoring are kept: rain days (>= 0.1 in measured, or forecast Minor+) and coast days with a
forecast of Minor+, an observed level of Minor+, or an NWS coastal alert. A quiet day with no reports counts
as "nothing happened" for rain (labeled weak evidence) and as "unverified" on the coast.

Outputs (committed): docs/evidence/auto/scores.json, scorecard.md, news.csv, city_reports.csv (date, area,
block only; no addresses or report text), nws_reports.csv; forecast_log/<snapshot>/site_forecast.json cache.

Usage: python pipeline/auto_verify.py [--days 14]
"""

from __future__ import annotations

import argparse
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

from forecast_logger import LOG_DIR
from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from risk import LEVELS, mission_bay_still_water

TZ = "America/Los_Angeles"
OUT = PROJECT_ROOT / "docs" / "evidence" / "auto"
SITE_DATA = PROJECT_ROOT / "web" / "public" / "data"
HEADERS = {"User-Agent": "coastal-flood-forecast-research"}
LOOKBACK_DAYS = 14
FINAL_AFTER_DAYS = 3
RAIN_LEAD_H = 2            # a rain forecast must be published at least this long before the rain began
RAIN_DAY_IN = 0.10
TIDE_DAY_FT = 7.0          # Mission Bay level above which "street flooded" reports count as tide-caused
GID_BASE = "https://seshat.datasd.org/get_it_done_reports/"
GID_PAGE = "https://data.sandiego.gov/datasets/get-it-done-311/"
LSR_URL = "https://mesonet.agron.iastate.edu/geojson/lsr.php"
LSR_PAGE = "https://mesonet.agron.iastate.edu/lsr/"
IEM_ASOS = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
FEEDS = {
    "Times of San Diego": "https://timesofsandiego.com/feed/",
    "Times of San Diego (weather)": "https://timesofsandiego.com/weather/feed/",
    "10News": "https://www.10news.com/news/local-news.rss",
    "NBC 7 San Diego": "https://www.nbcsandiego.com/?rss=y",
    "KPBS": "https://www.kpbs.org/index.rss",
    "KPBS (environment)": "https://www.kpbs.org/news/environment.rss",
    "FOX 5 San Diego": "https://fox5sandiego.com/feed/",
}
PLACES = {"Mission Beach": r"\b(?:mission beach|mission bay|bayside walk|belmont park)\b",
          "Pacific Beach": r"\b(?:pacific beach|crystal pier|crown point|sail bay)\b",
          "La Jolla": r"\b(?:la jolla|bird rock|windansea)\b"}
HAZARD = re.compile(r"\b(?:flood\w*|king tides?|high tides?|high surf|storm surge|boardwalk|berm|ponding|swamped|"
                    r"under ?water|downpours?|heavy rain|rain\w*|storms?)\b", re.I)
NOT_RAIN = re.compile(r"water ?main|main break|leak|sprinkl|irrigat|broken pipe|pipe burst|hydrant", re.I)
COMM_PLANS = {"LA JOLLA": "La Jolla", "PACIFIC BEACH": "Pacific Beach", "MISSION BEACH": "Mission Beach"}
LSR_TYPES = {"FLOOD", "FLASH FLOOD", "HEAVY RAIN", "COASTAL FLOOD", "HIGH SURF", "HIGH ASTR TIDES", "DEBRIS FLOW"}


def level_from_reports(n: int, big: tuple[int, int, int]) -> int:
    """Reports -> 0..3 (Low..Major) with thresholds (Minor, Moderate, Major)."""
    return 3 if n >= big[2] else 2 if n >= big[1] else 1 if n >= big[0] else 0


OBSERVED_RAIN = (1, 3, 6)   # City reports in a neighborhood on the storm day: 1 Minor, 3 Moderate, 6 Major
OBSERVED_TIDE = (1, 3, 10)  # tide-day reports in a coast area


# ---------------------------------------------------------------- evidence

def update_news() -> pd.DataFrame:
    """Check each outlet's RSS feed; add matching headlines (place + flood word) to news.csv."""
    path = OUT / "news.csv"
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["published", "outlet", "title", "url", "areas"])
    rows = []
    for outlet, url in FEEDS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            items = ET.fromstring(r.content).findall(".//item")
        except Exception as err:  # one outlet down must not stop the rest
            print(f"  news: {outlet} skipped ({err.__class__.__name__})")
            continue
        for it in items:
            title = (it.findtext("title") or "").strip()
            text = f"{title} {it.findtext('description') or ''}"
            areas = [a for a, pat in PLACES.items() if re.search(pat, text, re.I)]
            if not areas or not HAZARD.search(text):
                continue
            try:
                pub = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
            except Exception:
                continue
            rows.append({"published": pub.isoformat(timespec="minutes"), "outlet": outlet, "title": title,
                         "url": (it.findtext("link") or "").strip(), "areas": "|".join(areas)})
    news = pd.concat([old, pd.DataFrame(rows)]).drop_duplicates("url").sort_values("published")
    news = news[news.title.fillna("").str.contains(HAZARD)]  # re-check the whole log with the current rule
    news.to_csv(path, index=False)
    print(f"  news: {len(rows)} matching items in feeds now, {len(news)} in the log")
    return news


def city_reports(start: date, polys: gpd.GeoDataFrame) -> pd.DataFrame:
    """Get It Done flood reports since `start` in La Jolla / PB / MB (open + this year's closed requests)."""
    frames = []
    years = {start.year, date.today().year}
    for name in ["get_it_done_requests_open_datasd.csv"] + [f"get_it_done_requests_closed_{y}_datasd.csv" for y in years]:
        content = None
        for attempt in range(3):  # big files; the City server sometimes drops the connection
            try:
                with requests.get(GID_BASE + name, headers=HEADERS, timeout=300, stream=True) as r:
                    r.raise_for_status()
                    content = b"".join(r.iter_content(1 << 20))
                break
            except Exception as err:
                print(f"  city: {name} attempt {attempt + 1} failed ({err.__class__.__name__})")
        if content is None:
            continue
        d = pd.read_csv(io.BytesIO(content), dtype=str, low_memory=False)
        d = d[d.comm_plan_name.str.upper().isin(COMM_PLANS)]
        detail = d.service_name_detail.fillna("")
        d = d[(d.service_name == "Street Flooded") | detail.isin({"FLOODED", "PONDING WATER IN GUTTER/STREET"})]
        d = d[~d.public_description.fillna("").str.contains(NOT_RAIN)]
        frames.append(d)
    if not frames:
        return pd.DataFrame(columns=["service_request_id", "time_local", "date", "neighborhood", "area", "block"])
    d = pd.concat(frames).drop_duplicates("service_request_id")
    t = pd.to_datetime(d.date_requested)
    d = d.assign(time_local=t, date=t.dt.date)
    d = d[d.date >= start]
    d["neighborhood"] = d.comm_plan_name.str.upper().map(COMM_PLANS)
    pts = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.lng.astype(float), d.lat.astype(float)), crs=4326)
    coast = gpd.sjoin(pts, polys[["area", "geometry"]], how="left").groupby(level=0).area.first()
    d["area"] = coast
    d["block"] = d.street_address.map(to_block)
    keep = d[["service_request_id", "time_local", "date", "neighborhood", "area", "block"]].sort_values("time_local")
    return keep


def to_block(address) -> str:
    m = re.match(r"\s*(\d+)\S*\s+([^,]+)", str(address))
    if not m:
        return str(address).split(",")[0].title()
    return f"{int(m.group(1)) // 100 * 100} block of {m.group(2).strip().title()}"


def nws_reports(start: date, end: date, hoods: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    r = requests.get(LSR_URL, params={"wfos": "SGX", "sts": f"{start}T00:00Z", "ets": f"{end + timedelta(days=1)}T12:00Z"},
                     headers=HEADERS, timeout=120)
    r.raise_for_status()
    feats = r.json()["features"]
    if not feats:
        return gpd.GeoDataFrame(columns=["valid", "typetext", "city", "remark", "neighborhood", "geometry"], crs=4326)
    g = gpd.GeoDataFrame.from_features(feats, crs=4326)
    g = g[g.typetext.isin(LSR_TYPES)]
    near = hoods.to_crs(26911).buffer(1000).to_crs(4326)  # report coordinates are rounded to ~1 km
    g["neighborhood"] = [next((n for n, poly in zip(hoods.name, near) if poly.contains(p)), None) for p in g.geometry]
    g = g[g.neighborhood.notna()].copy()
    g["valid"] = pd.to_datetime(g.valid, utc=True).dt.tz_convert(TZ)
    return g


def measured_rain(start: date, end: date) -> pd.Series:
    stop = end + timedelta(days=2)  # archive dates are UTC: a Pacific evening falls on the next UTC day
    r = requests.get(IEM_ASOS, params={"station": "SAN", "data": "p01i", "year1": start.year, "month1": start.month,
                                       "day1": start.day, "year2": stop.year, "month2": stop.month, "day2": stop.day,
                                       "tz": "Etc/UTC", "format": "onlycomma", "missing": "M", "trace": "T",
                                       "report_type": 3}, headers=HEADERS, timeout=120)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    s = pd.Series(pd.to_numeric(d.p01i.replace("T", "0"), errors="coerce").to_numpy(),
                  index=pd.to_datetime(d.valid, utc=True)).dropna()
    s = s.groupby(s.index.floor("h")).max()
    return s.tz_convert(TZ).resample("h").sum()


# ---------------------------------------------------------------- forecasts

def snapshots() -> list:
    return sorted(p for p in LOG_DIR.glob("*/*/*Z") if (p / "meta.json").exists())


def issued_forecast(day: date, snaps: list, before: pd.Timestamp | None = None,
                    need: str | None = None) -> tuple[dict | None, str | None]:
    """The forecast the site published last before `before` (default: the start of `day`, local), at most 36 h
    earlier. need="rain": only forecasts that included the rain section (its own publish time if later)."""
    cutoff = before if before is not None else pd.Timestamp(day, tz=TZ)
    best = None
    for p in snaps:
        f = p / "site_forecast.json"
        if not f.exists():  # nothing was published from this snapshot: don't guess
            continue
        fc = json.loads(f.read_text())
        if need == "rain" and not fc.get("rain"):
            continue
        when = fc.get("rain_published_at") if need == "rain" and fc.get("rain_published_at") else \
            fc.get("published_at") or json.loads((p / "meta.json").read_text())["issued_at_utc"]
        t = pd.Timestamp(when).tz_convert(TZ)
        if t <= cutoff and t >= cutoff - pd.Timedelta(hours=36) and (best is None or t > best[1]):
            best = (fc, t)
    return (best[0], best[1].isoformat()) if best else (None, None)


# ---------------------------------------------------------------- scoring

def verdict(fc: int, obs: int) -> str:
    d = obs - fc
    return "right" if d == 0 else "close" if abs(d) == 1 else "missed" if d > 0 else "false_alarm"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=LOOKBACK_DAYS)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    today = pd.Timestamp.now(tz=TZ).date()
    start, end = today - timedelta(days=args.days), today - timedelta(days=1)

    hoods = gpd.read_file(SITE_DATA / "rain_neighborhoods.geojson")
    areas = gpd.read_file(PROCESSED_DIR / "areas.geojson").to_crs(4326)
    areas = areas.rename(columns={c: "area" for c in areas.columns if c in ("name", "area_name")})

    news = update_news()
    rain = measured_rain(start - timedelta(days=1), today)
    bay = mission_bay_still_water(start - timedelta(days=1), today).tz_convert(TZ)
    # City reports: add what this run finds to the saved log; never drop a report found earlier
    # (a report moves from the "open" file to the "closed" file, and a download can fail).
    log_path = OUT / "city_reports.csv"
    saved = pd.read_csv(log_path, dtype={"service_request_id": str}) if log_path.exists() else None
    reports = city_reports(start, areas)
    if saved is not None and "service_request_id" in saved:
        saved["time_local"] = pd.to_datetime(saved.time_local)
        saved["date"] = saved.time_local.dt.date
        reports = pd.concat([saved, reports]).drop_duplicates("service_request_id", keep="last")
    reports = reports.sort_values("time_local")
    reports.to_csv(log_path, index=False)
    nws = nws_reports(start, end, hoods)
    nws.drop(columns="geometry")[["valid", "typetext", "city", "neighborhood", "remark"]].to_csv(
        OUT / "nws_reports.csv", index=False)

    news_t = pd.to_datetime(news.published, utc=True).dt.tz_convert(TZ) if len(news) else pd.Series(dtype="datetime64[ns, UTC]")
    snaps = snapshots()
    path = OUT / "scores.json"
    scores = {s["key"]: s for s in (json.loads(path.read_text()) if path.exists() else [])}

    for i in range(args.days):
        day = start + timedelta(days=i)
        if day > end:
            break
        fc, issued = issued_forecast(day, snaps)
        final = (today - day).days >= FINAL_AFTER_DAYS
        d0 = pd.Timestamp(day, tz=TZ)
        rain_day = rain[(rain.index >= d0) & (rain.index < d0 + pd.Timedelta(days=1))]
        next_day = rain[(rain.index >= d0 + pd.Timedelta(days=1)) & (rain.index < d0 + pd.Timedelta(days=2))]
        total = float(rain_day.sum())
        max6 = float(rain_day.rolling(6, min_periods=1).sum().max()) if len(rain_day) else 0.0
        rainy = total >= RAIN_DAY_IN
        b = bay[(bay.index >= d0) & (bay.index < d0 + pd.Timedelta(days=1))]
        bay_peak = float(b.max()) if len(b) else float("nan")
        # Reports filed the next morning count for a storm day, unless the next day had its own rain.
        rep_days = {day} | ({day + timedelta(days=1)} if next_day.sum() < RAIN_DAY_IN else set())
        day_reports = reports[reports.date.isin(rep_days)]
        day_news = news[(news_t.dt.date >= day) & (news_t.dt.date <= day + timedelta(days=1))] if len(news) else news
        day_nws = nws[nws.valid.dt.date == day] if len(nws) else nws
        stamp = lambda t: pd.Timestamp(t).tz_convert(TZ).strftime("%a %b %-d, %-I:%M %p").replace("AM", "am").replace("PM", "pm")
        label = pd.Timestamp(day).strftime("%a %b %-d, %Y")

        def sources(area: str, kinds: set[str]) -> list[dict]:
            src = [{"name": f"{r.outlet}: {r.title[:80]}", "url": r.url}
                   for r in day_news.itertuples() if area in str(r.areas).split("|")]
            if len(day_nws[day_nws.neighborhood == area]):
                src.append({"name": "NWS storm reports", "url": LSR_PAGE})
            if kinds:
                src.append({"name": "City Get It Done reports", "url": GID_PAGE})
            return src[:6]

        # --- rain, per neighborhood: forecast published >= RAIN_LEAD_H before the rain began
        # "The rain began" = first wet hour of the day's heaviest 6 hours (a morning trace doesn't count).
        if len(rain_day) and rain_day.max() >= 0.01:
            win_end = rain_day.rolling(6, min_periods=1).sum().idxmax()
            win = rain_day[(rain_day.index > win_end - pd.Timedelta(hours=6)) & (rain_day.index <= win_end)]
            wet_hours = win[win >= 0.01]
        else:
            wet_hours = rain_day.iloc[0:0]
        rain_start = wet_hours.index[0] if len(wet_hours) else d0
        rfc, r_issued = issued_forecast(day, snaps, before=min(d0, rain_start) if not len(wet_hours)
                                        else rain_start - pd.Timedelta(hours=RAIN_LEAD_H), need="rain")
        for area in ((rfc or {}).get("rain") or {}).get("areas", []):
            name = area["name"]
            fday = next((x for x in area["days"] if x["date"] == str(day)), None)
            if fday is None:
                continue
            f_lv = LEVELS.index(fday["level"])
            if not rainy and f_lv == 0:
                continue
            n = int((day_reports.neighborhood == name).sum()) if rainy else 0
            lsr = day_nws[(day_nws.neighborhood == name) & day_nws.typetext.isin({"FLOOD", "FLASH FLOOD", "DEBRIS FLOW"})]
            art = [r for r in day_news.itertuples() if name in str(r.areas).split("|")
                   and re.search(r"\b(?:flood\w*|rain\w*|storms?|downpours?|ponding|swamped)\b", r.title, re.I)] if len(day_news) else []
            obs = level_from_reports(n, OBSERVED_RAIN)
            if len(lsr):
                obs = max(obs, 3 if (lsr.typetext == "FLASH FLOOD").any() else 1)
            if art:
                obs = max(obs, 1)
            evidence = n + len(lsr) + len(art)
            happened = (f"{total:.2f} in of rain at San Diego airport (heaviest 6 hours {max6:.2f} in). "
                        + (f"{plural(n, 'City flood report')} in {name}"
                           + (f", {plural(len(lsr), 'NWS storm report')}" if len(lsr) else "")
                           + (f", {plural(len(art), 'news story', )}" if art else "") + "."
                           if evidence else f"No flood reports from {name} to the City, NWS or local news."))
            key = f"{day}|rain|{name}"
            scores[key] = {
                "key": key, "date": str(day), "label": label, "side": "rain", "how": "auto", "title": f"Rain: {name}",
                "happened": happened,
                "we_said": f"{fday['level']} (forecast heaviest 6 hours {fday['max_6h_in']:.2f} in), published {stamp(r_issued)}"
                           + (f", before the rain began around {stamp(rain_start).split(', ')[1]}." if len(wet_hours) else "."),
                "result": verdict(f_lv, obs), "observed": LEVELS[obs], "forecast": fday["level"],
                "final": final, "weak": evidence == 0,
                "note": ("Preliminary: City reports can still come in. " if not final else "")
                        + ("Weak evidence: most flooding is never reported." if evidence == 0 else ""),
                "sources": sources(name, {"city"} if n else set()), "scored_utc": datetime.now(timezone.utc).isoformat(timespec="minutes"),
            }

        # --- coast (tide + waves), per area
        if fc is None:
            continue
        alerts = [a for a in (fc.get("nws_alerts") or []) if re.search(r"coastal flood|high surf", a.get("event", ""), re.I)]
        for area in fc.get("areas", []):
            name = area["name"]
            fday = next((x for x in area["days"] if x["date"] == str(day)), None)
            if fday is None:
                continue
            f_lv = LEVELS.index(fday["risk"])
            tide_day = bay_peak >= TIDE_DAY_FT
            # City "street flooded" reports count as tide flooding only on a high-tide day without rain.
            n = int((day_reports.area == name).sum()) if tide_day and not rainy else 0
            hood = "Mission Beach" if name == "Mission Beach" else "Pacific Beach"
            lsr = day_nws[(day_nws.neighborhood == hood) & day_nws.typetext.isin({"COASTAL FLOOD", "HIGH SURF", "HIGH ASTR TIDES"})]
            surge = lsr[lsr.typetext.isin({"COASTAL FLOOD", "HIGH ASTR TIDES"}) |
                        lsr.remark.fillna("").str.contains(r"boardwalk|overtop|over the wall|wash|flood", case=False)]
            art = [r for r in day_news.itertuples() if hood in str(r.areas).split("|")
                   and re.search(r"\b(?:flood\w*|king tides?|high tides?|high surf|boardwalk|berm|swamped)\b", r.title, re.I)] if len(day_news) else []
            obs = level_from_reports(n, OBSERVED_TIDE)
            if len(surge):
                obs = max(obs, 2 if (surge.typetext == "COASTAL FLOOD").any() else 1)
            if art:
                obs = max(obs, 1)
            if f_lv == 0 and obs == 0 and not alerts:
                continue
            evidence = n + len(surge) + len(art)
            happened = (f"Mission Bay peaked at {bay_peak:.1f} ft. "
                        + (f"{plural(n, 'City flood report')} in {name} on a high-tide day"
                           + (f", {plural(len(surge), 'NWS storm report')}" if len(surge) else "")
                           + (f", {plural(len(art), 'news story')}" if art else "") + "."
                           if evidence else f"No flooding reported from {name} to the City, NWS or local news."))
            cause = {"bay": "bay water", "ocean": "waves", "both": "bay water and waves"}.get(fday.get("cause"), "")
            key = f"{day}|coast|{name}"
            scores[key] = {
                "key": key, "date": str(day), "label": label, "side": "waves" if fday.get("cause") == "ocean" else "bay",
                "how": "auto", "title": f"Coast: {name}", "happened": happened,
                "we_said": f"{fday['risk']}{' (' + cause + ')' if cause and f_lv else ''}, published {stamp(issued)}.",
                "result": verdict(f_lv, obs) if evidence else "unverified", "observed": LEVELS[obs] if evidence else "No reports",
                "forecast": fday["risk"], "final": final, "weak": evidence == 0,
                "note": ("Preliminary: City reports can still come in. " if not final else "")
                        + ("Not scored: no reports either way, and water on the boardwalk is almost never reported. "
                           if evidence == 0 else "")
                        + (f"NWS {' and '.join(sorted({a['event'] for a in alerts}))} was in effect." if alerts else ""),
                "sources": sources(hood, {"city"} if n else set()),
                "scored_utc": datetime.now(timezone.utc).isoformat(timespec="minutes"),
            }

    ordered = sorted(scores.values(), key=lambda s: (s["date"], s["key"]), reverse=True)
    path.write_text(json.dumps(ordered, indent=1))
    write_markdown(ordered)
    print(f"  scored {len(ordered)} day-areas ({sum(not s['final'] for s in ordered)} preliminary)")


def write_markdown(scores: list[dict]) -> None:
    from collections import Counter
    c = Counter(s["result"] for s in scores)
    weak_rain = sum(s["weak"] and s["result"] != "unverified" for s in scores)
    lines = ["# Automatic scorecard", "",
             f"_Rewritten by `pipeline/auto_verify.py` on {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. Do not edit by hand._", "",
             "Every saved forecast is compared with what happened, using evidence collected automatically: measured rain "
             "and water level, City Get It Done flood reports, NWS storm reports and local news. Rules are in the script.", "",
             f"**{c['right']} right · {c['close']} close · {c['missed']} missed · {c['false_alarm']} false alarms**, "
             f"plus {c['unverified']} coast days not scored (no reports either way). {weak_rain} rain scores rest on "
             "zero City reports (weak evidence).", "",
             "| Day | What | We said | Observed | Result | Evidence |", "|---|---|---|---|---|---|"]
    for s in scores:
        lines.append(f"| {s['date']} | {s['title']} | {s['forecast']} | {s['observed']} | "
                     f"{s['result'].replace('_', ' ')}{'' if s['final'] else ' (prelim.)'} | {s['happened']} |")
    (OUT / "scorecard.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
