"""Download building outlines and streets/walkways from OpenStreetMap.

Source: OpenStreetMap contributors (ODbL license), via the Overpass API.
  https://www.openstreetmap.org/copyright
  https://overpass-api.de/

Privacy rule for this project: we keep only each building's SHAPE and TYPE
(house, apartments, ...). Addresses, names, and every other tag are dropped
on download, so they never reach the map.

Streets keep their name and type (names are public street names, needed for
"Bayside Walk floods at 7.4 ft" style results).

Outputs (data/processed/):
  osm_buildings.geojson   polygons, columns: osm_id, building
  osm_ways.geojson        lines, columns: osm_id, name, highway, kind
                          kind = "street" (cars) or "walkway" (boardwalk,
                          bike paths, Bayside Walk, ...)

Usage:
  python pipeline/osm_download.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import requests
from shapely.geometry import LineString, Polygon

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "coastal-flood-forecast-research"}
# Same study box as the elevation grid: south, west, north, east
BBOX = (32.752, -117.262, 32.810, -117.222)
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "osm"

STREET_TYPES = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
                "residential", "living_street", "service", "motorway_link", "trunk_link",
                "primary_link", "secondary_link", "tertiary_link"}
WALKWAY_TYPES = {"pedestrian", "footway", "cycleway", "path"}


def overpass(query: str) -> dict:
    response = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=180)
    response.raise_for_status()
    return response.json()


def main() -> None:
    s, w, n, e = BBOX
    bbox = f"{s},{w},{n},{e}"
    downloaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Buildings ...")
    raw = overpass(f'[out:json][timeout:120];way["building"]({bbox});out geom;')
    (RAW_DIR / "buildings.json").write_text(json.dumps(raw))
    rows = []
    for el in raw["elements"]:
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        if len(pts) >= 4:
            rows.append({"osm_id": el["id"], "building": el["tags"].get("building", "yes"),
                         "geometry": Polygon(pts)})  # every other tag (addresses etc.) dropped
    buildings = gpd.GeoDataFrame(rows, crs="EPSG:4326")

    print("Streets and walkways ...")
    types = "|".join(sorted(STREET_TYPES | WALKWAY_TYPES))
    raw = overpass(f'[out:json][timeout:120];way["highway"~"^({types})$"]({bbox});out geom;')
    (RAW_DIR / "ways.json").write_text(json.dumps(raw))
    rows = []
    for el in raw["elements"]:
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        hw = el["tags"]["highway"]
        if len(pts) >= 2:
            rows.append({"osm_id": el["id"], "name": el["tags"].get("name", ""), "highway": hw,
                         "kind": "street" if hw in STREET_TYPES else "walkway",
                         "geometry": LineString(pts)})
    ways = gpd.GeoDataFrame(rows, crs="EPSG:4326")

    buildings.to_file(PROCESSED_DIR / "osm_buildings.geojson", driver="GeoJSON")
    ways.to_file(PROCESSED_DIR / "osm_ways.geojson", driver="GeoJSON")
    meta = {"source": "OpenStreetMap contributors, ODbL", "api": OVERPASS_URL, "bbox_s_w_n_e": BBOX,
            "downloaded_at_utc": downloaded_at, "buildings": len(buildings),
            "ways": ways["kind"].value_counts().to_dict(),
            "privacy": "building tags other than 'building' type dropped at download"}
    (PROCESSED_DIR / "osm.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved {len(buildings):,} buildings and {len(ways):,} ways "
          f"({meta['ways']}) to {PROCESSED_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
