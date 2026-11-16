"""Sort the ponding spots from rain_terrain.py: which ones put water on a street?

For each spot we measure the water depth ON street surfaces (OpenStreetMap public street centerlines,
incl. alleys, not driveways/parking aisles, widened by STREET_HALF_WIDTH_M; bridges and tunnels left out because the bare-ground map shows the
ground under a bridge, not the deck).

  street      water stands on a street (>= MIN_STREET_DEPTH_FT deep there)
  check       very deep on a street (> DEEP_STREET_FT), or deep (> CREEK_DEPTH_FT) with a creek-sized
              drainage area (> CREEK_DRAINAGE_ACRES total): usually a canyon behind a road embankment
              whose culvert the ground map can't see, sometimes a real underpass. Not rated until checked.
  off-street  only yards, lots, parks, pools, canyons
Each spot also gets its neighborhood: the City's community planning areas La Jolla, Pacific Beach,
Mission Beach (data.sandiego.gov); spots outside them (UTC, Clairemont, Mission Bay Park, Midway)
help the flow math but are not rated.

Inputs : data/processed/rain_pond_labels.npy, rain_depth_ft.tif, ponds.csv (rain_terrain.py),
         data/raw/osm/rain_ways.geojson (rain_osm.py), data/raw/city/cmty_plan_datasd.geojson
Outputs: data/processed/ponds.csv (adds street columns + kind), ponds.geojson (street + check outlines)

Usage: python pipeline/rain_ponds.py
"""

from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.features import rasterize, shapes
from scipy import ndimage
from shapely.geometry import shape

from noaa_tides import PROCESSED_DIR
from osm_download import HEADERS, RAW_DIR

STREET_HALF_WIDTH_M = 4.0   # a typical residential street is ~10-12 m curb to curb
MIN_STREET_DEPTH_FT = 0.25  # 3 in on the street
DEEP_STREET_FT = 5.0
CREEK_DEPTH_FT = 3.0
CREEK_DRAINAGE_ACRES = 100
NEIGHBORHOODS = ["La Jolla", "Pacific Beach", "Mission Beach"]
PLAN_URL = "https://seshat.datasd.org/gis_community_planning_districts/cmty_plan_datasd.geojson"
PLAN_FILE = RAW_DIR.parent / "city" / "cmty_plan_datasd.geojson"
MIN_STREET_CELLS = 10       # at least 10 m2 of street under water


def main() -> None:
    with rasterio.open(PROCESSED_DIR / "rain_depth_ft.tif") as src:
        depth, transform, crs, shp = src.read(1), src.transform, src.crs, src.shape
    labels = np.load(PROCESSED_DIR / "rain_pond_labels.npy")
    ponds = pd.read_csv(PROCESSED_DIR / "ponds.csv").set_index("pond")
    ponds = ponds.drop(columns=["street_m2", "street_max_depth_ft", "streets", "kind", "neighborhood"],
                       errors="ignore")  # columns this script adds (safe to re-run)

    ways = gpd.read_file(RAW_DIR / "rain_ways.geojson").to_crs(crs)
    # Public streets and alleys; not driveways, parking aisles or other "service" ways inside lots/schools.
    private = (ways.highway == "service") & (ways.service.fillna("") != "alley")
    streets = ways[(ways.kind == "street") & ~private & ways.bridge.isna() & ways.tunnel.isna()].reset_index(drop=True)
    streets["sid"] = np.arange(1, len(streets) + 1, dtype=np.int32)
    street_id = rasterize(zip(streets.geometry.buffer(STREET_HALF_WIDTH_M, cap_style="flat"), streets.sid),
                          out_shape=shp, transform=transform, fill=0, dtype="int32")

    on = (street_id > 0) & (labels > 0) & np.isin(labels, ponds.index.to_numpy())
    lab_on, d_on, s_on = labels[on], depth[on], street_id[on]
    df = pd.DataFrame({"pond": lab_on, "depth": d_on, "sid": s_on})
    df = df[df.depth >= MIN_STREET_DEPTH_FT]
    g = df.groupby("pond")
    st = pd.DataFrame({"street_m2": g.size(), "street_max_depth_ft": g.depth.max().round(2)})
    names = df.merge(streets[["sid", "name"]], on="sid").dropna(subset=["name"])
    st["streets"] = names.groupby("pond").name.agg(lambda s: " / ".join(s.value_counts().index[:3]))
    ponds = ponds.join(st)
    ponds["street_m2"] = ponds.street_m2.fillna(0).astype(int)
    creek = (ponds.street_max_depth_ft > CREEK_DEPTH_FT) & (ponds.drainage_total_m2 > CREEK_DRAINAGE_ACRES * 4046.86)
    ponds["kind"] = np.select(
        [ponds.street_m2 < MIN_STREET_CELLS, (ponds.street_max_depth_ft > DEEP_STREET_FT) | creek],
        ["off-street", "check"], "street")
    if not PLAN_FILE.exists():
        PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(PLAN_URL, headers=HEADERS, timeout=120)
        r.raise_for_status()
        PLAN_FILE.write_bytes(r.content)
    plan = gpd.read_file(PLAN_FILE)
    plan = plan[plan.cpname.isin(NEIGHBORHOODS)].to_crs(crs)[["cpname", "geometry"]]
    pts = gpd.GeoDataFrame(ponds[[]], geometry=gpd.points_from_xy(ponds.x, ponds.y), crs=crs)
    ponds["neighborhood"] = gpd.sjoin(pts, plan, how="left").groupby(level=0).cpname.first()
    ponds.to_csv(PROCESSED_DIR / "ponds.csv")

    # Outlines of street + check spots (WGS84) for maps.
    keep = ponds.index[(ponds.kind != "off-street") & ponds.neighborhood.notna()].to_numpy()
    sub = np.where(np.isin(labels, keep), labels, 0).astype(np.int32)
    geoms, ids = [], []
    for geom, val in shapes(sub, mask=sub > 0, transform=transform, connectivity=8):
        geoms.append(shape(geom))
        ids.append(int(val))
    out = gpd.GeoDataFrame({"pond": ids}, geometry=geoms, crs=crs).dissolve("pond")
    out["geometry"] = out.geometry.simplify(0.5)
    out = out.join(ponds[["kind", "area_m2", "max_depth_ft", "street_max_depth_ft", "street_m2", "volume_m3",
                          "drainage_m2", "drainage_total_m2", "fill_rain_in", "streets", "neighborhood"]]).reset_index().to_crs(4326)
    (PROCESSED_DIR / "ponds.geojson").write_text(out.to_json(drop_id=True))
    print(ponds.groupby([ponds.neighborhood.fillna("(outside)"), "kind"]).size().unstack(fill_value=0).to_string())
    print(ponds[ponds.kind == "street"][["street_max_depth_ft", "street_m2", "drainage_m2", "fill_rain_in"]]
          .describe().round(2).to_string())


if __name__ == "__main__":
    main()
