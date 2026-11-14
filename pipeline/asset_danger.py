"""Danger height of every building and every 25 m stretch of street.

Danger height = the lowest still-water level (feet above MLLW, tide terms)
at which water reaches it, from the bay or from the ocean, with
connectivity (see flood_threshold.py).

Buildings: water "reaches the property" when it reaches ground within
  2 m of the building outline. We never claim the inside floods - floor
  heights are unknown.
Streets/walkways: split into pieces of at most 25 m. Each piece is sampled
  every 1 m along its centerline AND 3 m to each side (roads are crowned,
  so gutters flood first). A piece's danger height is its lowest sample.

Also stored: the lowest GROUND height near each asset. If the water is
higher than that ground but below the danger height, there is no surface
path - but water can still arrive through storm drains.

Outputs (data/processed/):
  buildings_danger.geojson
  street_pieces_danger.geojson
Values are feet above MLLW (converted with NOAA La Jolla datums).

Usage:
  python pipeline/asset_danger.py
"""

from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from shapely.geometry import LineString
from shapely.ops import substring

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from plot_dem import NAVD88_ABOVE_MLLW_FT

UTM = "EPSG:26911"
BUILDING_BUFFER_M = 2.0
PIECE_LENGTH_M = 25.0
SIDE_OFFSET_M = 3.0


def load_grids() -> dict:
    grids = {}
    for key, name in [("ground", "dem_pbmb_navd88_ft.tif"), ("bay", "danger_from_bay_navd88_ft.tif"),
                      ("bay_berm", "danger_from_bay_berm_navd88_ft.tif"),
                      ("ocean", "danger_from_ocean_navd88_ft.tif"), ("mask", "water_mask_pbmb.tif")]:
        with rasterio.open(PROCESSED_DIR / name) as src:
            grids[key] = src.read(1)
            grids["transform"], grids["shape"] = src.transform, src.shape
    return grids


def to_mllw(values: np.ndarray) -> np.ndarray:
    return np.round(values + NAVD88_ABOVE_MLLW_FT, 2)


def building_danger(buildings: gpd.GeoDataFrame, g: dict) -> gpd.GeoDataFrame:
    out = {"danger_bay_ft": [], "danger_bay_berm_ft": [], "danger_ocean_ft": [], "ground_min_ft": []}
    for geom in buildings.geometry.buffer(BUILDING_BUFFER_M):
        win = from_bounds(*geom.bounds, g["transform"]).round_offsets().round_lengths()
        r0, c0 = max(int(win.row_off), 0), max(int(win.col_off), 0)
        r1 = min(int(win.row_off + win.height) + 1, g["shape"][0])
        c1 = min(int(win.col_off + win.width) + 1, g["shape"][1])
        if r1 <= r0 or c1 <= c0:
            for k in out:
                out[k].append(np.nan)
            continue
        wt = rasterio.windows.transform(rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0), g["transform"])
        inside = ~geometry_mask([geom], (r1 - r0, c1 - c0), wt, all_touched=True)
        land = inside & (g["mask"][r0:r1, c0:c1] == 0)
        for key, grid in [("danger_bay_ft", "bay"), ("danger_bay_berm_ft", "bay_berm"),
                          ("danger_ocean_ft", "ocean"), ("ground_min_ft", "ground")]:
            vals = g[grid][r0:r1, c0:c1][land]
            vals = vals[np.isfinite(vals)]
            out[key].append(vals.min() if vals.size else np.nan)
    for k, v in out.items():
        buildings[k] = to_mllw(np.array(v, dtype=float))
    return buildings


def split_line(line: LineString, max_len: float) -> list[LineString]:
    n = max(1, int(np.ceil(line.length / max_len)))
    step = line.length / n
    return [substring(line, i * step, (i + 1) * step) for i in range(n)]


def sample(grid: np.ndarray, g: dict, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    rows, cols = rasterio.transform.rowcol(g["transform"], xs, ys)
    rows, cols = np.asarray(rows), np.asarray(cols)
    ok = (rows >= 0) & (rows < g["shape"][0]) & (cols >= 0) & (cols < g["shape"][1])
    vals = np.full(xs.shape, np.nan)
    land = np.zeros(xs.shape, bool)
    land[ok] = g["mask"][rows[ok], cols[ok]] == 0
    vals[land] = grid[rows[land], cols[land]]
    return vals


def street_danger(ways: gpd.GeoDataFrame, g: dict) -> gpd.GeoDataFrame:
    rows = []
    for _, way in ways.iterrows():
        for piece in split_line(way.geometry, PIECE_LENGTH_M):
            if piece.length < 0.5:
                continue
            lines = [piece]
            for side in (SIDE_OFFSET_M, -SIDE_OFFSET_M):
                off = piece.offset_curve(side)
                if not off.is_empty and off.geom_type == "LineString":
                    lines.append(off)
            pts = [[ln.interpolate(d) for d in np.arange(0, ln.length + 0.01, 1.0)] for ln in lines]
            center_n = len(pts[0])  # the first line is the centerline
            flat = [p for line_pts in pts for p in line_pts]
            xs, ys = np.array([p.x for p in flat]), np.array([p.y for p in flat])
            vals = {k: sample(g[k], g, xs, ys) for k in ("bay", "bay_berm", "ocean", "ground")}
            if np.all(np.isnan(vals["ground"])):
                continue  # bridge / over water

            def lowest(v):
                return np.nanmin(v) if np.isfinite(v).any() else np.nan

            def middle(v):  # level at which at least half the centerline is under water
                v = v[:center_n]
                return np.nanmedian(v) if np.isfinite(v).any() else np.nan

            rows.append({"osm_id": way.osm_id, "name": way["name"], "highway": way.highway, "kind": way.kind,
                         "length_m": round(piece.length, 1),
                         # water reaches the edges / gutters / low spots of this stretch
                         "danger_bay_ft": lowest(vals["bay"]),
                         "danger_bay_berm_ft": lowest(vals["bay_berm"]),
                         "danger_ocean_ft": lowest(vals["ocean"]),
                         # water covers the middle of the road along most of this stretch
                         "covered_bay_ft": middle(vals["bay"]),
                         "covered_bay_berm_ft": middle(vals["bay_berm"]),
                         "covered_ocean_ft": middle(vals["ocean"]),
                         "ground_min_ft": lowest(vals["ground"]),
                         "geometry": piece})
    pieces = gpd.GeoDataFrame(rows, crs=UTM)
    for k in ("danger_bay_ft", "danger_bay_berm_ft", "danger_ocean_ft", "covered_bay_ft",
              "covered_bay_berm_ft", "covered_ocean_ft", "ground_min_ft"):
        pieces[k] = to_mllw(pieces[k].to_numpy(dtype=float))
    return pieces


def main() -> None:
    g = load_grids()
    buildings = gpd.read_file(PROCESSED_DIR / "osm_buildings.geojson").to_crs(UTM)
    ways = gpd.read_file(PROCESSED_DIR / "osm_ways.geojson").to_crs(UTM)

    print(f"Buildings ({len(buildings):,}) ...")
    buildings = building_danger(buildings, g)
    print(f"Streets and walkways ({len(ways):,} ways) ...")
    pieces = street_danger(ways, g)

    for name, gdf in [("buildings_danger", buildings), ("street_pieces_danger", pieces)]:
        gdf = gdf.to_crs("EPSG:4326")
        gdf.geometry = gdf.geometry.set_precision(1e-6)  # ~10 cm; keeps files small
        gdf.to_file(PROCESSED_DIR / f"{name}.geojson", driver="GeoJSON")
    meta = {
        "inputs": ["osm_buildings.geojson", "osm_ways.geojson", "danger_from_bay/ocean_navd88_ft.tif",
                   "dem_pbmb_navd88_ft.tif"],
        "units": "feet above MLLW (NAVD88 + 0.19 ft, NOAA La Jolla datums)",
        "building_buffer_m": BUILDING_BUFFER_M, "piece_length_m": PIECE_LENGTH_M, "side_offset_m": SIDE_OFFSET_M,
        "columns": {
            "danger_bay_ft": "lowest still-water level at which water from Mission Bay reaches it",
            "danger_bay_berm_ft": "same, if Mission Beach's bay-side sand berm holds (see flood_threshold.py)",
            "danger_ocean_ft": "same, from the open ocean (waves not included)",
            "covered_bay_ft / covered_ocean_ft": "streets only: level at which the middle of the road is under "
                                                 "water along at least half of the 25 m stretch",
            "ground_min_ft": "lowest ground nearby (below the water but above danger height = storm-drain risk)",
        },
    }
    (PROCESSED_DIR / "asset_danger.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved {len(buildings):,} buildings and {len(pieces):,} street pieces "
          f"to {PROCESSED_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
