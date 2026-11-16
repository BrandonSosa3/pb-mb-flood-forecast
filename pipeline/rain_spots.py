"""Rain flooding spots for the site: ground spots + spots people report again and again.

Two sources (piece 3 showed which to trust where, docs/evidence/rain/README.md):
  ground   street ponding spots from the lidar ground map (rain_ponds.py), Pacific Beach and Mission
           Beach only: there, rain-day reports land at them 3.6x more often than chance. In La Jolla
           they did no better than chance, so they are not shown.
  reports  places with "street flooded" reports on >= MIN_DAYS different rainy days, within
           CLUSTER_M of each other (all three neighborhoods). Reports whose text points to a water
           main, leak, sprinkler or irrigation are left out.
A ground spot with repeat reports within MATCH_M becomes source "both".

Privacy: spots carry a street name only, never a house number or report text.

Inputs : data/processed/ponds.geojson, flood_reports.csv
Output : data/processed/rain_spots.geojson (+ .meta.json): points; source, neighborhood, street,
         depth_in, drains_acres (ground), report_days, first, last (reports)

Usage: python pipeline/rain_spots.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from noaa_tides import PROCESSED_DIR

CRS = 26911
GROUND_NEIGHBORHOODS = ["Pacific Beach", "Mission Beach"]
CLUSTER_M = 75
MIN_DAYS = 2
MATCH_M = 50
NOT_RAIN = re.compile(r"water ?main|main break|leak|sprinkl|irrigat|broken pipe|pipe burst|hydrant|pool", re.I)
ACRE_M2 = 4046.86
OUT = PROCESSED_DIR / "rain_spots.geojson"


def street_name(address: str) -> str:
    """'754 Bonair St, La Jolla, CA' -> 'Bonair St'; 'TORREY PINES RD & GLENBROOK' -> 'Torrey Pines Rd & Glenbrook'."""
    first = str(address).split(",")[0]
    first = re.sub(r"^\s*[\d?\-]+\s+", "", first)
    first = re.sub(r"\s*\b\d{5}\b.*$", "", first)
    return first.strip().title()


def report_spots() -> gpd.GeoDataFrame:
    rep = pd.read_csv(PROCESSED_DIR / "flood_reports.csv")
    rep = rep[(rep["type"] == "flooded") & (rep.cause == "rain") & rep.lat.notna()]
    rep = rep[~rep.public_description.fillna("").str.contains(NOT_RAIN)]
    g = gpd.GeoDataFrame(rep, geometry=gpd.points_from_xy(rep.lng, rep.lat), crs=4326).to_crs(CRS).reset_index(drop=True)
    xy = np.c_[g.geometry.x, g.geometry.y]
    pairs = cKDTree(xy).query_pairs(CLUSTER_M, output_type="ndarray")
    adj = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(g), len(g)))
    g["cluster"] = connected_components(adj, directed=False)[1]
    rows = []
    for _, c in g.groupby("cluster"):
        days = sorted(set(c.date))
        if len(days) < MIN_DAYS:
            continue
        rows.append({"source": "reports", "neighborhood": c.neighborhood.mode().iloc[0],
                     "street": c.street_address.dropna().map(street_name).mode().iloc[0]
                     if c.street_address.notna().any() else None,
                     "report_days": len(days), "first": days[0], "last": days[-1],
                     "geometry": c.geometry.union_all().centroid})
    return gpd.GeoDataFrame(rows, crs=CRS)


def main() -> None:
    ponds = gpd.read_file(PROCESSED_DIR / "ponds.geojson").to_crs(CRS)
    ground = ponds[(ponds.kind == "street") & ponds.neighborhood.isin(GROUND_NEIGHBORHOODS)].copy()
    ground = gpd.GeoDataFrame({
        "source": "ground", "neighborhood": ground.neighborhood,
        "street": ground.streets.str.split(" / ").str[0],
        "depth_in": (ground.street_max_depth_ft * 12).round(), "drains_acres": (ground.drainage_m2 / ACRE_M2).round(1),
        "area_m2": ground.area_m2}, geometry=ground.geometry.representative_point(), crs=CRS)
    reps = report_spots()

    # Ground spot with a repeat-report spot nearby -> "both" (keep the ground spot, add report facts).
    near = gpd.sjoin_nearest(reps, ground[["geometry"]], max_distance=MATCH_M, distance_col="d")
    near = near.sort_values("d").drop_duplicates("index_right")
    for i, r in near.iterrows():
        g = r.index_right
        ground.loc[g, ["source", "report_days", "first", "last"]] = ["both", r.report_days, r["first"], r["last"]]
        if pd.isna(ground.loc[g, "street"]):
            ground.loc[g, "street"] = r.street
    reps = reps.drop(index=near.index.unique())
    spots = pd.concat([ground, reps], ignore_index=True).to_crs(4326)
    spots["geometry"] = spots.geometry.set_precision(1e-5)
    OUT.write_text(spots.to_json(drop_id=True))
    meta = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ground_neighborhoods": GROUND_NEIGHBORHOODS, "cluster_m": CLUSTER_M, "min_rain_days": MIN_DAYS,
            "match_m": MATCH_M, "excluded_text": NOT_RAIN.pattern,
            "counts": {f"{k[0]}/{k[1]}": int(v) for k, v in spots.groupby(["neighborhood", "source"]).size().items()}}
    OUT.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(spots.groupby(["neighborhood", "source"]).size().unstack(fill_value=0).to_string())
    print(spots[spots.source != "ground"].sort_values("report_days", ascending=False)
          [["neighborhood", "source", "street", "report_days", "first", "last"]].head(25).to_string(index=False))


if __name__ == "__main__":
    main()
