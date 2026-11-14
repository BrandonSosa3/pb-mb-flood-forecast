"""Search list for the website: streets, addresses and landmarks, each with the water levels
at which bay water reaches it. The whole list ships with the site, so what people type in the
search box never leaves their phone.

Inputs : osm_ways.geojson, street_pieces_danger.geojson, buildings_danger.geojson,
         areas.geojson, area_curves.json, shore_profiles.csv (all in data/processed/)
         + OpenStreetMap addresses (downloaded here, Overpass API)
Output : web/public/data/search.json and data/processed/search_index.meta.json

Heights are feet above MLLW (same as the map). Per spot:
  d  = water reaches it from the bay if the berm fails     db = ... if the berm holds
  g  = lowest ground nearby (lower than the water -> storm drains may back up)
  pt = nearest ocean-beach stretch (CDIP MOP point; streets: pts = all of them) if the spot is within OCEANFRONT_M of the
       boardwalk (Ocean Front Walk / Ocean Blvd), so the site can add that stretch's wave forecast
Landmarks are large places, so they get a location + area only (no single danger height).

Privacy: addresses are only used for search; the map never lists them. Only house number +
street + location are kept (no names, no other tags).

Usage: python pipeline/search_index.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from areas import ROUTINELY_WET_FT
from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from osm_download import OVERPASS_URL, overpass

OUT = PROJECT_ROOT / "web" / "public" / "data" / "search.json"
BBOX_S_W_N_E = (32.7585, -117.2700, 32.8120, -117.2285)  # union of the three areas
OCEANFRONT_M = 120       # spots this close to the boardwalk also get that stretch's waves forecast
ADDRESS_TO_BUILDING_M = 20
LANDMARKS = {  # name: (lat, lon)
    "Crystal Pier": (32.79614, -117.2575),
    "Belmont Park": (32.77089, -117.25205),
    "Mission Beach boardwalk": (32.7700, -117.2528),
    "Santa Clara Point": (32.7810, -117.2440),
    "El Carmel Point": (32.7790, -117.2475),
    "Sail Bay": (32.79219, -117.24822),
    "Crown Point": (32.78685, -117.23685),
    "Tourmaline Surf Park": (32.80528, -117.26202),
    "South Mission Beach jetty": (32.7600, -117.2540),
}
UTM = 26911


def r1(x: float) -> float | None:
    return None if pd.isna(x) else round(float(x), 1)


def lowest(values: pd.Series) -> float | None:
    """Lowest level that reaches a spot, ignoring the shoreline edge that is wet on every ordinary
    high tide (same rule as the map and the counts)."""
    return r1(values[values > ROUTINELY_WET_FT].min())


def coastline(profiles: pd.DataFrame) -> gpd.GeoDataFrame:
    """Where each beach stretch meets the water: from the wave-model point (offshore, ~10 m deep)
    walk landward along the shore normal by the measured distance to the shoreline."""
    pts = gpd.GeoSeries(gpd.points_from_xy(profiles.lon, profiles.lat), crs=4326).to_crs(UTM)
    landward = np.radians(profiles.shore_normal_deg.to_numpy() + 180)
    dist = profiles.shoreline_dist_m.to_numpy()
    xy = [Point(p.x + d * np.sin(a), p.y + d * np.cos(a)) for p, d, a in zip(pts, dist, landward)]
    return gpd.GeoDataFrame({"point": profiles.point.to_numpy()}, geometry=xy, crs=UTM)


def main() -> None:
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    areas = gpd.read_file(PROCESSED_DIR / "areas.geojson").to_crs(UTM)
    curves = json.loads((PROCESSED_DIR / "area_curves.json").read_text())
    beach_pts = {a: set(c["beach_points"]) for a, c in curves["areas"].items()}
    profiles = pd.read_csv(PROCESSED_DIR / "shore_profiles.csv")
    shore = coastline(profiles)
    shore = shore[shore.point.isin(set().union(*beach_pts.values()))]
    ways = gpd.read_file(PROCESSED_DIR / "osm_ways.geojson").to_crs(UTM)
    boardwalk = ways[ways.name.isin(["Ocean Front Walk", "Ocean Boulevard"])].union_all()

    def attach(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Add area name and nearest beach stretch (if oceanfront) to points in UTM."""
        gdf = gpd.sjoin(gdf, areas[["name", "geometry"]].rename(columns={"name": "area"}), how="inner",
                        predicate="within").drop(columns="index_right")
        gdf = gdf[~gdf.index.duplicated()]  # on a shared border: keep the first area
        near = gpd.sjoin_nearest(gdf[["geometry"]], shore, how="left")
        near = near[~near.index.duplicated()].reindex(gdf.index)
        ok = (gdf.geometry.distance(boardwalk) <= OCEANFRONT_M) & gdf["area"].isin(["Mission Beach", "Pacific Beach"])
        gdf["pt"] = np.where(ok, near.point, None)
        return gdf

    # ---- streets: one entry per street name per area ----
    pieces = gpd.read_file(PROCESSED_DIR / "street_pieces_danger.geojson").to_crs(UTM)
    pieces = pieces[pieces.name.fillna("") != ""]
    pieces["geometry_line"] = pieces.geometry
    pieces["geometry"] = pieces.geometry.interpolate(0.5, normalized=True)
    pieces = attach(pieces)
    streets = []
    for (name, area), g in pieces.groupby(["name", "area"]):
        line = gpd.GeoSeries(g.geometry_line, crs=UTM).to_crs(4326)
        w, s, e, n = line.total_bounds
        center = Point((w + e) / 2, (s + n) / 2)
        center_utm = gpd.GeoSeries([center], crs=4326).to_crs(UTM)[0]
        mid = g.geometry.iloc[int(np.argmin(g.geometry.distance(center_utm).to_numpy()))]
        lon, lat = gpd.GeoSeries([mid], crs=UTM).to_crs(4326)[0].coords[0]
        pts = sorted({p for p in g.pt if isinstance(p, str)})
        streets.append({
            "name": name, "area": area, "kind": g.kind.iloc[0],
            "bbox": [round(w, 5), round(s, 5), round(e, 5), round(n, 5)], "lon": round(lon, 5), "lat": round(lat, 5),
            "d": lowest(g.danger_bay_ft), "db": lowest(g.danger_bay_berm_ft),
            "c": lowest(g.covered_bay_ft), "cb": lowest(g.covered_bay_berm_ft),
            "g": r1(g.ground_min_ft.min()), "pts": pts,
        })

    # ---- addresses ----
    s, w, n, e = BBOX_S_W_N_E
    raw = overpass(f'[out:json][timeout:120];nwr["addr:housenumber"]["addr:street"]({s},{w},{n},{e});out center tags;')
    rows = []
    for el in raw["elements"]:
        c = el if el["type"] == "node" else el.get("center")
        if c:
            rows.append({"num": el["tags"]["addr:housenumber"], "street": el["tags"]["addr:street"],
                         "geometry": Point(c["lon"], c["lat"])})  # every other tag dropped
    addr = gpd.GeoDataFrame(rows, crs=4326).drop_duplicates(["num", "street"]).to_crs(UTM)
    addr = attach(addr)
    bld = gpd.read_file(PROCESSED_DIR / "buildings_danger.geojson").to_crs(UTM)
    addr = gpd.sjoin_nearest(addr, bld[["danger_bay_ft", "danger_bay_berm_ft", "ground_min_ft", "geometry"]],
                             how="left", max_distance=ADDRESS_TO_BUILDING_M)
    addr = addr[~addr.index.duplicated()]
    ll = addr.geometry.to_crs(4326)
    street_names = sorted(addr.street.unique())
    sidx = {name: i for i, name in enumerate(street_names)}
    addresses = [[r.num, sidx[r.street], round(p.x, 5), round(p.y, 5),
                  r1(r.danger_bay_ft), r1(r.danger_bay_berm_ft), r1(r.ground_min_ft), r.area,
                  r.pt if isinstance(r.pt, str) else None]
                 for r, p in zip(addr.itertuples(), ll)]

    # ---- landmarks ----
    lm = gpd.GeoDataFrame({"name": list(LANDMARKS)},
                          geometry=[Point(lon, lat) for lat, lon in LANDMARKS.values()], crs=4326).to_crs(UTM)
    lm = attach(lm)
    landmarks = []
    for r in lm.itertuples():
        lon, lat = gpd.GeoSeries([r.geometry], crs=UTM).to_crs(4326)[0].coords[0]
        landmarks.append({"name": r.name, "area": r.area, "lon": round(lon, 5), "lat": round(lat, 5),
                          "pt": r.pt if isinstance(r.pt, str) else None})

    out = {"streets": streets, "street_names": street_names, "addresses": addresses, "landmarks": landmarks,
           "address_fields": ["num", "street", "lon", "lat", "d", "db", "g", "area", "pt"]}
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    meta = {"created_utc": created, "addresses_source": "OpenStreetMap contributors, ODbL", "api": OVERPASS_URL,
            "bbox_s_w_n_e": BBOX_S_W_N_E, "addresses": len(addresses), "streets": len(streets),
            "landmarks": len(landmarks), "privacy": "address = house number + street + location only",
            "addresses_matched_to_building": int(addr.danger_bay_ft.notna().sum())}
    (PROCESSED_DIR / "search_index.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"{len(streets)} streets, {len(addresses):,} addresses "
          f"({meta['addresses_matched_to_building']:,} matched to a building), {len(landmarks)} landmarks "
          f"-> {OUT.relative_to(PROJECT_ROOT)} ({OUT.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
