"""Do real flood reports land at our rain ponding spots? A fair test.

Compares how often reports fall within D meters of a street ponding spot (rain_ponds.py) for:
  rain-day "street flooded" reports   (City Get It Done; should cluster at spots if the spots are real)
  dry-day "street flooded" reports    (water-main breaks, sprinklers: a control, should NOT cluster)
  random points on the same streets   (what chance alone gives)
  NWS storm reports of rain flooding  (few, but measured by trained observers)
Lift = share near a spot / share for random street points. 1 = no better than chance.

Also lists rain-day report clusters with no spot nearby (what the ground map misses).

Inputs : data/processed/flood_reports.csv (flood_reports.py), ponds.geojson, data/raw/osm/rain_ways.geojson,
         Iowa Environmental Mesonet NWS Local Storm Report archive (downloaded here)
Outputs: data/processed/nws_rain_flood_reports.csv, docs/evidence/rain/ponding_check.md, ponding_check.png

Usage: python pipeline/check_ponds.py
"""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import requests

from dem_prepare import AREAS
from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from osm_download import HEADERS, RAW_DIR
from rain_ponds import NEIGHBORHOODS, PLAN_FILE

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DISTANCES_M = [25, 50, 100]
N_RANDOM = 20_000
LSR_URL = ("https://mesonet.agron.iastate.edu/cgi-bin/request/gis/lsr.py?wfo[]=SGX"
           "&sts=2003-01-01T00:00Z&ets={end}&fmt=csv")
OUT_DIR = PROJECT_ROOT / "docs" / "evidence" / "rain"
CRS = 26911


def nws_reports(plan: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00Z")
    r = requests.get(LSR_URL.format(end=end), headers=HEADERS, timeout=300)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text), on_bad_lines="skip")
    w, s, e, n = AREAS["rain"]["bbox"]
    d = d[d.LAT.between(s, n) & d.LON.between(w, e) & d.TYPETEXT.isin(["FLOOD", "FLASH FLOOD"])]
    g = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.LON, d.LAT), crs=4326).to_crs(CRS)
    g = gpd.sjoin(g, plan[["cpname", "geometry"]], how="left").drop(columns="index_right")
    g["time_utc"] = pd.to_datetime(g.VALID.astype(str), format="%Y%m%d%H%M", utc=True)
    out = g[["time_utc", "TYPETEXT", "CITY", "LAT", "LON", "cpname", "REMARK"]].rename(
        columns={"TYPETEXT": "type", "CITY": "place", "LAT": "lat", "LON": "lon", "cpname": "neighborhood",
                 "REMARK": "remark"})
    out.to_csv(PROCESSED_DIR / "nws_rain_flood_reports.csv", index=False)
    return g


def street_points(plan: gpd.GeoDataFrame, rng: np.random.Generator) -> gpd.GeoSeries:
    ways = gpd.read_file(RAW_DIR / "rain_ways.geojson").to_crs(CRS)
    st = ways[(ways.kind == "street") & ways.bridge.isna() & ways.tunnel.isna()]
    st = gpd.clip(st, plan.union_all())
    lengths = st.length.to_numpy()
    pick = rng.choice(len(st), size=N_RANDOM, p=lengths / lengths.sum())
    frac = rng.random(N_RANDOM)
    geoms = st.geometry.to_numpy()
    return gpd.GeoSeries([geoms[i].interpolate(f, normalized=True) for i, f in zip(pick, frac)], crs=CRS)


def share_near(points: gpd.GeoSeries, spots: gpd.GeoDataFrame) -> dict[int, float]:
    if len(points) == 0:
        return {d: float("nan") for d in DISTANCES_M}
    dist = gpd.sjoin_nearest(gpd.GeoDataFrame(geometry=points.reset_index(drop=True)), spots[["geometry"]],
                             distance_col="d").groupby(level=0).d.min()
    return {d: float((dist <= d).mean()) for d in DISTANCES_M}


def to_block(address: str) -> str:
    """'754 Bonair St, La Jolla, CA 92037' -> '700 block of Bonair St' (no house numbers in the write-up)."""
    m = re.match(r"\s*(\d+)\S*\s+([^,]+)", str(address))
    if not m:
        return str(address).split(",")[0].title()
    return f"{int(m.group(1)) // 100 * 100} block of {m.group(2).strip().title()}"


def main() -> None:
    rng = np.random.default_rng(0)
    plan = gpd.read_file(PLAN_FILE)
    plan = plan[plan.cpname.isin(NEIGHBORHOODS)].to_crs(CRS)
    spots = gpd.read_file(PROCESSED_DIR / "ponds.geojson").to_crs(CRS)
    spots = spots[spots.kind == "street"]
    rep = pd.read_csv(PROCESSED_DIR / "flood_reports.csv")
    rep = gpd.GeoDataFrame(rep, geometry=gpd.points_from_xy(rep.lng, rep.lat), crs=4326).to_crs(CRS)
    rep = rep[rep.lat.notna() & rep.within(plan.union_all())]
    nws = nws_reports(plan)
    rand = street_points(plan, rng)

    groups = {
        "Rain-day 'street flooded' reports": rep[(rep["type"] == "flooded") & (rep.cause == "rain")].geometry,
        "Dry-day 'street flooded' reports (control)": rep[(rep["type"] == "flooded") & (rep.cause == "other")].geometry,
        "Rain-day storm-drain reports": rep[(rep["type"] == "drain") & (rep.cause == "rain")].geometry,
        "NWS rain-flood reports (in the neighborhoods)": nws[nws.cpname.notna()].geometry,
        "Random points on the same streets (chance)": rand,
    }
    base = share_near(rand, spots)
    rows = []
    for name, pts in groups.items():
        s = share_near(pts, spots)
        rows.append({"group": name, "n": len(pts), **{f"within {d} m": s[d] for d in DISTANCES_M},
                     **{f"lift {d} m": s[d] / base[d] for d in DISTANCES_M}})
    tab = pd.DataFrame(rows)
    print(tab.round(2).to_string(index=False))

    # Per neighborhood, rain-day flooded reports vs chance on that neighborhood's streets.
    per = []
    for n in NEIGHBORHOODS:
        poly = plan[plan.cpname == n].union_all()
        r = rep[(rep["type"] == "flooded") & (rep.cause == "rain") & rep.within(poly)].geometry
        b = share_near(rand[rand.within(poly)], spots)
        s = share_near(r, spots)
        per.append({"neighborhood": n, "n": len(r), "within 50 m": s[50], "chance": b[50], "lift": s[50] / b[50]})
    per = pd.DataFrame(per)
    print(per.round(2).to_string(index=False))

    # Misses: rain-day flooded reports > 100 m from any spot, grouped into ~150 m clusters.
    rf = rep[(rep["type"] == "flooded") & (rep.cause == "rain")].copy()
    rf["d"] = gpd.sjoin_nearest(rf[["geometry"]], spots[["geometry"]], distance_col="d").groupby(level=0).d.min()
    miss = rf[rf.d > 100].copy()
    miss["cell"] = (miss.geometry.x // 150).astype(int).astype(str) + "_" + (miss.geometry.y // 150).astype(int).astype(str)
    clusters = (miss.groupby("cell").agg(n=("service_request_id", "size"), neighborhood=("neighborhood", "first"),
                                         where=("street_address", lambda s: to_block(s.dropna().iloc[0]) if s.notna().any() else ""),
                                         days=("date", lambda s: ", ".join(sorted(set(map(str, s)))[:3])))
                .sort_values("n", ascending=False))
    # Hits: spots with the most rain-day reports within 50 m.
    near = gpd.sjoin_nearest(rf[["geometry", "date"]], spots[["geometry", "streets", "neighborhood"]],
                             distance_col="d", max_distance=50)
    hits = (near.groupby(["streets", "neighborhood"], dropna=False)
            .agg(reports=("date", "size"), days=("date", lambda s: len(set(s)))).sort_values("reports", ascending=False))

    pct = lambda v: f"{v:.0%}"
    lines = ["# Do flood reports land at our rain ponding spots?", "",
             f"_Written by `pipeline/check_ponds.py` on {datetime.now(timezone.utc):%Y-%m-%d}. Reports: City of San "
             "Diego Get It Done (2017-2026) and NWS storm reports (2003-2026)._", "",
             "**Fair test:** share of reports within 25 / 50 / 100 m of a street ponding spot, compared with random "
             "points on the same streets. *Lift* 2.0 = twice as often as chance. Dry-day reports (water mains, "
             "sprinklers) are a control: they should not cluster at rain spots.", "",
             "| Group | Reports | ≤25 m | ≤50 m | ≤100 m | Lift at 50 m |", "|---|---|---|---|---|---|"]
    for r in tab.itertuples():
        lines.append(f"| {r.group} | {r.n} | {pct(r[3])} | {pct(r[4])} | {pct(r[5])} | {r[7]:.1f}× |")
    lines += ["", "## By neighborhood (rain-day 'street flooded', within 50 m)", "",
              "| Neighborhood | Reports | Near a spot | Chance | Lift |", "|---|---|---|---|---|"]
    lines += [f"| {r.neighborhood} | {r.n} | {pct(r[3])} | {pct(r.chance)} | {r.lift:.1f}× |" for r in per.itertuples()]
    lines += ["", "## Spots with the most rain-day reports (within 50 m)", "",
              "| Spot (streets) | Neighborhood | Reports | Different days |", "|---|---|---|---|"]
    lines += [f"| {s if isinstance(s, str) else '(unnamed)'} | {n} | {r.reports} | {r.days} |"
              for (s, n), r in hits.head(12).iterrows()]
    lines += ["", "## Reported rain flooding with no spot within 100 m (top clusters)", "",
              "| Near (block) | Neighborhood | Reports | Days (first 3) |", "|---|---|---|---|"]
    lines += [f"| {r.where} | {r.neighborhood} | {r.n} | {r.days} |" for r in clusters.head(12).itertuples()]
    lines += ["", "## NWS rain-flood reports in the neighborhoods", "", "| When (UTC) | Where | Remark |", "|---|---|---|"]
    for r in nws[nws.cpname.notna()].sort_values("time_utc").itertuples():
        lines.append(f"| {r.time_utc:%Y-%m-%d %H:%M} | {r.CITY} | {str(r.REMARK)[:140]} |")
    lines += ["", "![Rain-day reports and ponding spots](ponding_check.png)", ""]

    fig, axes = plt.subplots(1, 2, figsize=(13, 9), dpi=110)
    for ax, names in zip(axes, (["La Jolla"], ["Pacific Beach", "Mission Beach"])):
        poly = plan[plan.cpname.isin(names)]
        poly.boundary.plot(ax=ax, color="#777", linewidth=0.8, linestyle="--")
        spots[spots.neighborhood.isin(names)].buffer(10).plot(ax=ax, color="#2171b5", alpha=0.8)
        sub = rep[rep.neighborhood.isin(names)]
        sub[(sub["type"] == "flooded") & (sub.cause == "other")].plot(ax=ax, color="#bbb", markersize=6, label="dry-day report")
        sub[(sub["type"] == "flooded") & (sub.cause == "rain")].plot(ax=ax, color="#e6550d", markersize=10, label="rain-day report")
        nws[nws.cpname.isin(names)].plot(ax=ax, color="#000", marker="*", markersize=80, label="NWS report")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(" + ".join(names), fontsize=10)
    axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Blue = street ponding spots · orange = rain-day 'street flooded' reports · grey = dry-day", fontsize=10)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "ponding_check.png")
    (OUT_DIR / "ponding_check.md").write_text("\n".join(lines) + "\n")
    print(clusters.head(12).to_string())
    print(hits.head(12).to_string())


if __name__ == "__main__":
    main()
