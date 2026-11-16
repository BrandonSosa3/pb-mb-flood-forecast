"""OpenStreetMap streets and waterways for the rain area (greater PB + La Jolla).

Streets: to tell which ponding spots sit in a street (what people see flood).
Waterways: streams, ditches and drains, incl. the pieces that pass under roads in a culvert/pipe.
           The ground map can't see culverts, so a road across a canyon looks like a dam;
           rain_terrain.py cuts the ground down along these lines ("culvert burning").

Output: data/raw/osm/rain_ways.geojson (+ .meta.json); kind = street | walkway | waterway | culvert
Usage : python pipeline/rain_osm.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
from shapely.geometry import LineString

from dem_prepare import AREAS
from osm_download import OVERPASS_URL, RAW_DIR, STREET_TYPES, WALKWAY_TYPES, overpass

OUT = RAW_DIR / "rain_ways.geojson"


def main() -> None:
    w, s, e, n = AREAS["rain"]["bbox"]
    bbox = f"{s},{w},{n},{e}"
    downloaded = datetime.now(timezone.utc).isoformat(timespec="seconds")
    elements = []
    for what in ("waterway", "highway"):  # two smaller queries (one big one times out)
        print(f"  {what} ...")
        elements += overpass(f'[out:json][timeout:170];way["{what}"]({bbox});out geom tags;')["elements"]
    rows = []
    for el in elements:
        tags, pts = el.get("tags", {}), el.get("geometry", [])
        if len(pts) < 2:
            continue
        hw, ww = tags.get("highway"), tags.get("waterway")
        if ww:
            under = tags.get("tunnel") in ("culvert", "yes") or tags.get("culvert") == "yes" or ww == "drain" and tags.get("tunnel")
            kind = "culvert" if under else "waterway"
        elif hw in STREET_TYPES:
            kind = "street"
        elif hw in WALKWAY_TYPES:
            kind = "walkway"
        else:
            continue
        rows.append({"osm_id": el["id"], "kind": kind, "name": tags.get("name"), "highway": hw, "waterway": ww,
                     "service": tags.get("service"), "tunnel": tags.get("tunnel"), "bridge": tags.get("bridge"), "layer": tags.get("layer"),
                     "geometry": LineString([(p["lon"], p["lat"]) for p in pts])})
    gdf = gpd.GeoDataFrame(rows, crs=4326)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(gdf.to_json(drop_id=True))
    meta = {"source": "OpenStreetMap contributors, ODbL", "api": OVERPASS_URL, "bbox_w_s_e_n": AREAS["rain"]["bbox"],
            "downloaded_at_utc": downloaded, "ways": gdf.kind.value_counts().to_dict()}
    OUT.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(gdf.kind.value_counts().to_string())


if __name__ == "__main__":
    main()
