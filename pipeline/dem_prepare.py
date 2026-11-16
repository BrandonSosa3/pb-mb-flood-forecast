"""Download the 2024 USGS LiDAR elevation grid and cut it to a study area.

Areas:
  pbmb  Pacific Beach + Mission Beach shoreline (tide/wave flooding). Default.
  rain  Greater Pacific Beach + La Jolla, Mission Beach jetty to La Jolla Shores, ocean to I-5
        (rain flooding: where water flows and ponds; added 2026-11-16).

Source: USGS 3D Elevation Program (3DEP), project CA_SanDiegoCo_D24,
        standard 1-meter bare-earth DEM, flown 2024-11-08 to 2024-12-01.
        https://www.usgs.gov/3d-elevation-program
Each grid cell is a 1 m x 1 m square of ground holding one height:
  - horizontal: NAD83 / UTM zone 11N (meters east/north)
  - vertical:   NAVD88, meters (the land-survey "zero")

This script:
  1. downloads the 1 m tiles covering the area (10 km x 10 km each, 130-490 MB, once),
  2. merges them and cuts out the area,
  3. converts heights from meters to feet (still NAVD88),
  4. saves data/processed/dem_<area>_navd88_ft.tif (+ .meta.json) and water_mask_<area>.tif.

We keep land heights in NAVD88 and convert WATER levels to NAVD88 when we
compare them (water level in MLLW minus the gauge's NAVD88-above-MLLW offset).
That way the grid is never modified beyond a units change.

Usage:
  python pipeline/dem_prepare.py              # pbmb
  python pipeline/dem_prepare.py --area rain
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import rasterio
import requests
from rasterio.merge import merge
from rasterio.warp import transform_bounds

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

PROJECT = "CA_SanDiegoCo_D24"
TILE_URL = ("https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/"
            "{project}/TIFF/USGS_1M_11_{tile}_{project}.tif")
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "usgs_dem"
FILL_PROJECT = "San_Diego_CA_2014_LiDAR"
FILL_DIR = PROJECT_ROOT / "data" / "raw" / "usgs_dem_2014"
FILL_RING_M = 150  # offset 2024 - 2014 measured on land within this distance of each gap
MIN_GAP_M2 = 100   # smaller gaps are left as they are

# Study areas (longitude/latitude: west, south, east, north) and the tiles covering them.
AREAS = {
    # Mission Beach jetty to Tourmaline (N-S), ocean to the east edge of Crown Point / Sail Bay
    # (west edge a little offshore of Tourmaline so the whole PB beach is included).
    "pbmb": {"bbox": (-117.270, 32.752, -117.222, 32.812), "tiles": ["x47y363", "x47y364"]},
    # Mission Beach jetty to La Jolla Shores / Scripps (N-S), ocean to I-5 (W-E): all of Mt Soledad,
    # so rain falling on it is inside the grid. Rose Creek's watershed reaches far inland (outside).
    "rain": {"bbox": (-117.290, 32.752, -117.200, 32.880),
             "tiles": ["x47y363", "x47y364", "x48y363", "x48y364"], "snap": True,
             # The 2024 tiles have land gaps (largest: 64 ha of east Pacific Beach, Ingraham St to
             # Mission Bay Dr, Grand Ave to Felspar St). Fill them from the 2014 USGS lidar DEM.
             "fill": {"project": FILL_PROJECT, "tiles": ["x47y363", "x47y364", "x48y364"]}},
}

METERS_TO_FEET = 3.28084

# "Hydro-flattening": lidar can't measure water, so the data producer replaced
# water with one flat height (Mission Bay, plus a strip along the ocean edge);
# the open ocean further out is no-data. We detect it to build a water mask.
MIN_WATER_AREA_M2 = 5_000  # ignore small flat patches on land (parking lots etc.)
FLAT_TOLERANCE_FT = 0.01
# The flattened ocean strip and Mission Bay touch through the entrance channel
# (and through gaps in the narrow jetties). Rule: flattened water within
# OCEAN_REACH_M of the open ocean, measured by "swimming" through water, is
# OCEAN; the rest is bay. The beach-side strip is ~55 m wide, so it all becomes
# ocean; only the outer channel mouth between the jetties is affected otherwise.
OCEAN_REACH_M = 250


def download_tiles(tiles: list[str], project: str = PROJECT, raw_dir=RAW_DIR) -> list:
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for tile in tiles:
        url = TILE_URL.format(project=project, tile=tile)
        path = raw_dir / url.rsplit("/", 1)[1]
        if path.exists():
            print(f"  already have {path.name}")
        else:
            print(f"  downloading {path.name} ...")
            with requests.get(url, stream=True, timeout=120,
                              headers={"User-Agent": "coastal-flood-forecast-research"}) as r:
                r.raise_for_status()
                tmp = path.with_suffix(".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                tmp.rename(path)  # only "done" once fully downloaded
        paths.append(path)
    return paths


def fill_gaps(elev_ft: np.ndarray, bounds, fill: dict) -> tuple[np.ndarray, np.ndarray, list]:
    """Fill no-data gaps on land (not the open ocean) from an older USGS 1 m DEM on the same grid.
    Each gap gets the older heights plus the median (new - old) difference on land around it, so
    the filled ground joins its surroundings without a step. Returns (elev, filled mask, report)."""
    from scipy import ndimage

    paths = download_tiles(fill["tiles"], fill["project"], FILL_DIR)
    srcs = [rasterio.open(p) for p in paths]
    old, _ = merge(srcs, bounds=bounds, nodata=np.nan, dtype="float32")
    nodata_in = srcs[0].nodata
    for s in srcs:
        s.close()
    old = old[0]
    if nodata_in is not None:
        old[old == nodata_in] = np.nan
    old *= METERS_TO_FEET
    assert old.shape == elev_ft.shape, "fill DEM must be on the same grid"

    missing = ~np.isfinite(elev_ft)
    labels, n = ndimage.label(missing)
    open_ocean = np.setdiff1d(np.unique(labels[:, 0]), [0])  # no-data touching the west edge
    sizes = ndimage.sum(missing, labels, index=np.arange(1, n + 1))
    filled = np.zeros(elev_ft.shape, bool)
    report = []
    for i in np.flatnonzero(sizes >= MIN_GAP_M2) + 1:
        if i in open_ocean:
            continue
        gap = labels == i
        ring = ndimage.binary_dilation(gap, iterations=FILL_RING_M) & ~gap & np.isfinite(elev_ft) & np.isfinite(old)
        if ring.sum() < 1000 or not np.isfinite(old[gap]).any():
            continue
        offset = float(np.median(elev_ft[ring] - old[ring]))
        put = gap & np.isfinite(old)
        elev_ft[put] = old[put] + offset
        filled |= put
        rows, cols = np.nonzero(gap)
        report.append({"area_m2": int(gap.sum()), "filled_m2": int(put.sum()), "offset_ft": round(offset, 2),
                       "row_col_center": [int(rows.mean()), int(cols.mean())]})
        print(f"  filled a {gap.sum() / 1e4:.1f} ha gap from {fill['project']} (+{offset:.2f} ft to match 2024)")
    return elev_ft, filled, report


def build_water_mask(elev_ft: np.ndarray) -> tuple[np.ndarray, float]:
    """0 = land, 1 = Mission Bay water (hydro-flattened), 2 = ocean (or no-data)."""
    from scipy import ndimage

    valid = np.isfinite(elev_ft)
    values, counts = np.unique(np.round(elev_ft[valid], 3), return_counts=True)
    flat_value = float(values[np.argmax(counts)])  # the single most common height
    candidate = valid & (np.abs(elev_ft - flat_value) <= FLAT_TOLERANCE_FT)
    labels, n = ndimage.label(candidate)
    sizes = ndimage.sum(candidate, labels, index=np.arange(1, n + 1))
    big = np.flatnonzero(sizes >= MIN_WATER_AREA_M2) + 1
    flattened = np.isin(labels, big)

    # Open ocean = no-data connected to the west edge (other no-data = survey gaps).
    nodata_labels, _ = ndimage.label(~valid)
    west_ids = np.setdiff1d(np.unique(nodata_labels[:, 0]), [0])
    open_ocean = np.isin(nodata_labels, west_ids)
    # Grow from the open ocean through flattened water, 1 m per step (4-neighbour).
    four = ndimage.generate_binary_structure(2, 1)
    reach = ndimage.binary_dilation(open_ocean, structure=four, iterations=OCEAN_REACH_M,
                                    mask=open_ocean | flattened)
    ocean_flat = reach & flattened

    mask = np.zeros(elev_ft.shape, dtype="uint8")
    mask[flattened] = 1
    mask[ocean_flat | ~valid] = 2
    return mask, flat_value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", choices=AREAS, default="pbmb")
    area = ap.parse_args().area
    tiles, bbox = AREAS[area]["tiles"], AREAS[area]["bbox"]
    out_path = PROCESSED_DIR / f"dem_{area}_navd88_ft.tif"
    water_mask_path = PROCESSED_DIR / f"water_mask_{area}.tif"

    print(f"1. Tiles ({area})")
    paths = download_tiles(tiles)

    print("2. Merge + cut to study area")
    sources = [rasterio.open(p) for p in paths]
    crs = sources[0].crs
    bounds = transform_bounds("EPSG:4326", crs, *bbox)  # lon/lat -> UTM meters
    if AREAS[area].get("snap"):
        # Line the cut up with the tiles' own 1 m grid, so every cell is an original lidar cell
        # (the pbmb grid predates this and sits up to 0.5 m off; kept as is, Phase 2 was built on it).
        x0, y0, res = sources[0].transform.c, sources[0].transform.f, sources[0].res[0]
        snap = lambda v, o: o + round((v - o) / res) * res
        bounds = (snap(bounds[0], x0), snap(bounds[1], y0), snap(bounds[2], x0), snap(bounds[3], y0))
    mosaic, transform = merge(sources, bounds=bounds, nodata=np.nan, dtype="float32")
    nodata_in = sources[0].nodata
    for s in sources:
        s.close()

    elev_m = mosaic[0]
    if nodata_in is not None:
        elev_m[elev_m == nodata_in] = np.nan
    elev_ft = (elev_m * METERS_TO_FEET).astype("float32")

    fill_report, filled = [], None
    if AREAS[area].get("fill"):
        print("2b. Fill survey gaps")
        elev_ft, filled, fill_report = fill_gaps(elev_ft, bounds, AREAS[area]["fill"])

    print("3. Save")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff", "height": elev_ft.shape[0], "width": elev_ft.shape[1], "count": 1,
        "dtype": "float32", "crs": crs, "transform": transform, "nodata": np.nan,
        "compress": "deflate", "predictor": 3, "tiled": True,
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(elev_ft, 1)
        dst.update_tags(units="feet", vertical_datum="NAVD88", source=PROJECT)

    if filled is not None:
        filled_path = PROCESSED_DIR / f"dem_{area}_filled_cells.tif"
        with rasterio.open(filled_path, "w", **{**profile, "dtype": "uint8", "nodata": None, "predictor": 2}) as dst:
            dst.write(filled.astype("uint8"), 1)
            dst.update_tags(values=f"1 = height from {AREAS[area]['fill']['project']} (2024 gap), 0 = 2024")

    print("4. Water mask")
    mask, flat_value = build_water_mask(elev_ft)
    mask_profile = {**profile, "dtype": "uint8", "nodata": None, "predictor": 2}
    with rasterio.open(water_mask_path, "w", **mask_profile) as dst:
        dst.write(mask, 1)
        dst.update_tags(values="0 = land, 1 = Mission Bay water (hydro-flattened), 2 = ocean / no data")

    valid = elev_ft[np.isfinite(elev_ft) & (mask == 0)]  # land only
    meta = {
        "source": "USGS 3DEP standard 1 m bare-earth DEM",
        "project": PROJECT,
        "area": area,
        "tiles": [TILE_URL.format(project=PROJECT, tile=t) for t in tiles],
        "lidar_collected": "2024-11-08 to 2024-12-01",
        "published": "2026-09-14",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "crs": str(crs),
        "vertical_datum": "NAVD88",
        "units": "feet",
        "cell_size_m": abs(transform.a),
        "study_bbox_lonlat": bbox,
        "shape_rows_cols": list(elev_ft.shape),
        "water_mask": {
            "file": water_mask_path.name,
            "hydro_flattened_bay_height_ft_navd88": round(flat_value, 3),
            "bay_water_fraction": round(float(np.mean(mask == 1)), 4),
            "ocean_or_nodata_fraction": round(float(np.mean(mask == 2)), 4),
        },
        "land_elevation_ft_min_median_max": [round(float(np.min(valid)), 2), round(float(np.median(valid)), 2),
                                        round(float(np.max(valid)), 2)],
        "nodata_fraction": round(float(np.mean(~np.isfinite(elev_ft))), 4),
        "gap_fill": ({"project": AREAS[area]["fill"]["project"],
                      "tiles": [TILE_URL.format(project=AREAS[area]["fill"]["project"], tile=t)
                                for t in AREAS[area]["fill"]["tiles"]],
                      "method": f"older heights + median (2024 - 2014) on land within {FILL_RING_M} m of each gap",
                      "gaps": fill_report} if AREAS[area].get("fill") else None),
    }
    out_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))

    print(f"Saved {out_path.relative_to(PROJECT_ROOT)}: {elev_ft.shape[1]} x {elev_ft.shape[0]} cells "
          f"({elev_ft.shape[1] / 1000:.1f} km x {elev_ft.shape[0] / 1000:.1f} km), "
          f"{out_path.stat().st_size / 1e6:.0f} MB")
    lo, med, hi = meta["land_elevation_ft_min_median_max"]
    wm = meta["water_mask"]
    print(f"  Land heights (ft, NAVD88): min {lo}, median {med}, max {hi}")
    print(f"  Bay water (flattened at {wm['hydro_flattened_bay_height_ft_navd88']} ft): {wm['bay_water_fraction']:.1%}"
          f" of area; ocean / no-data: {wm['ocean_or_nodata_fraction']:.1%}")


if __name__ == "__main__":
    main()
