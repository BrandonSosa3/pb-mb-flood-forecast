"""Water shapes for the 3D view: where bay water sits at each Mission Bay level.

Our flood model (flood_threshold.py) gives every 1 m cell the lowest bay level at which water can
flow there ("connected" flood, so isolated low dips stay dry). Here we cut that into bands 0.1 ft
apart and turn each band into map shapes. The website shows every band at or below the slider level,
so moving the slider needs no new downloads.

Two versions: the bay-side sand berm holds (assumed top 9.0 ft) or fails.

Inputs : data/processed/danger_from_bay_navd88_ft.tif, danger_from_bay_berm_navd88_ft.tif
Outputs: web/public/data/water_bands.geojson (+ data/processed/water_bands.meta.json)
         properties: lv = band level (ft MLLW; the band is underwater at that level and above),
                     berm = 1 for the berm-holds version, 0 for berm fails

Usage: python pipeline/water_bands.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape

from flood_threshold import NAVD88_ABOVE_MLLW_FT
from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

LOW_FT, HIGH_FT, STEP_FT = 6.0, 9.5, 0.1     # same range as the map's slider
BAY_SURFACE_MAX_FT = 2.6                     # cells at/below this are the bay itself (basemap shows it)
SIMPLIFY_M = 1.0                             # smooth the 1 m staircase edges
MIN_AREA_M2 = 6.0                            # drop specks
OUT = PROJECT_ROOT / "web" / "public" / "data" / "water_bands.geojson"
INPUTS = {1: "danger_from_bay_berm_navd88_ft.tif", 0: "danger_from_bay_navd88_ft.tif"}


def bands(path) -> gpd.GeoDataFrame:
    with rasterio.open(PROCESSED_DIR / path) as src:
        level = src.read(1) + NAVD88_ABOVE_MLLW_FT  # -> feet above MLLW
        transform, crs = src.transform, src.crs
    wet = np.isfinite(level) & (level > BAY_SURFACE_MAX_FT) & (level <= HIGH_FT + 1e-6)
    # Band k covers (6.0 + 0.1(k-1), 6.0 + 0.1k]; everything at or below 6.0 ft is band 0.
    filled = np.where(wet, level, LOW_FT)  # outside the wet area (ocean, never-wet) the value is unused
    k = np.where(filled <= LOW_FT, 0, np.ceil((filled - LOW_FT) / STEP_FT - 1e-6)).astype(np.int16)
    k[~wet] = -1
    geoms, lvs = [], []
    for geom, val in shapes(k, mask=wet, transform=transform, connectivity=4):
        geoms.append(shape(geom))
        lvs.append(round(LOW_FT + STEP_FT * val, 1))
    gdf = gpd.GeoDataFrame({"lv": lvs}, geometry=geoms, crs=crs)
    gdf = gdf.dissolve("lv").reset_index().explode(index_parts=False)
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_M, preserve_topology=True)
    gdf = gdf[gdf.geometry.area >= MIN_AREA_M2]
    return gdf


def main() -> None:
    parts = []
    for berm, path in INPUTS.items():
        g = bands(path)
        g["berm"] = berm
        parts.append(g)
        print(f"berm={'holds' if berm else 'fails'}: {len(g):,} shapes, {g.geometry.area.sum() / 1e6:.2f} km² "
              f"wet at {HIGH_FT} ft")
    out = gpd.pd.concat(parts, ignore_index=True).to_crs(4326)
    OUT.write_text(out.to_json(drop_id=True, to_wgs84=True))
    # Round coordinates (~0.1 m) to keep the file small.
    data = json.loads(OUT.read_text())
    for f in data["features"]:
        geom = f["geometry"]
        rnd = lambda ring: [[round(x, 6), round(y, 6)] for x, y in ring]
        if geom["type"] == "Polygon":
            geom["coordinates"] = [rnd(r) for r in geom["coordinates"]]
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    meta = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "inputs": list(INPUTS.values()),
            "levels_ft_mllw": [LOW_FT, HIGH_FT, STEP_FT], "simplify_m": SIMPLIFY_M, "min_area_m2": MIN_AREA_M2,
            "bay_surface_excluded_below_ft": BAY_SURFACE_MAX_FT, "features": len(out)}
    (PROCESSED_DIR / "water_bands.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"-> {OUT.relative_to(PROJECT_ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
