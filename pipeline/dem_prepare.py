"""Download the 2024 USGS LiDAR elevation grid and cut it to PB + MB.

Source: USGS 3D Elevation Program (3DEP), project CA_SanDiegoCo_D24,
        standard 1-meter bare-earth DEM, flown 2024-11-08 to 2024-12-01.
        https://www.usgs.gov/3d-elevation-program
Each grid cell is a 1 m x 1 m square of ground holding one height:
  - horizontal: NAD83 / UTM zone 11N (meters east/north)
  - vertical:   NAVD88, meters (the land-survey "zero")

This script:
  1. downloads the two 1 m tiles covering our study area (~320 MB, once),
  2. merges them and cuts out just Pacific Beach + Mission Beach,
  3. converts heights from meters to feet (still NAVD88),
  4. saves data/processed/dem_pbmb_navd88_ft.tif (+ .meta.json).

We keep land heights in NAVD88 and convert WATER levels to NAVD88 when we
compare them (water level in MLLW minus the gauge's NAVD88-above-MLLW offset).
That way the grid is never modified beyond a units change.

Usage:
  python pipeline/dem_prepare.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import rasterio
import requests
from rasterio.merge import merge
from rasterio.warp import transform_bounds

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

PROJECT = "CA_SanDiegoCo_D24"
TILES = ["x47y363", "x47y364"]
TILE_URL = ("https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/"
            "{project}/TIFF/USGS_1M_11_{tile}_{project}.tif")
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "usgs_dem"

# Study area (longitude/latitude): Mission Beach jetty to Tourmaline (N-S),
# ocean to the east edge of Crown Point / Sail Bay (W-E).
STUDY_BBOX_LONLAT = (-117.270, 32.752, -117.222, 32.812)  # west, south, east, north
# (west edge a little offshore of Tourmaline so the whole PB beach is included)

METERS_TO_FEET = 3.28084
OUT_PATH = PROCESSED_DIR / "dem_pbmb_navd88_ft.tif"
WATER_MASK_PATH = PROCESSED_DIR / "water_mask_pbmb.tif"

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


def download_tiles() -> list:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for tile in TILES:
        url = TILE_URL.format(project=PROJECT, tile=tile)
        path = RAW_DIR / url.rsplit("/", 1)[1]
        if path.exists():
            print(f"  already have {path.name}")
        else:
            print(f"  downloading {path.name} ...")
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = path.with_suffix(".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                tmp.rename(path)  # only "done" once fully downloaded
        paths.append(path)
    return paths


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
    print("1. Tiles")
    paths = download_tiles()

    print("2. Merge + cut to study area")
    sources = [rasterio.open(p) for p in paths]
    crs = sources[0].crs
    bounds = transform_bounds("EPSG:4326", crs, *STUDY_BBOX_LONLAT)  # lon/lat -> UTM meters
    mosaic, transform = merge(sources, bounds=bounds, nodata=np.nan, dtype="float32")
    nodata_in = sources[0].nodata
    for s in sources:
        s.close()

    elev_m = mosaic[0]
    if nodata_in is not None:
        elev_m[elev_m == nodata_in] = np.nan
    elev_ft = (elev_m * METERS_TO_FEET).astype("float32")

    print("3. Save")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff", "height": elev_ft.shape[0], "width": elev_ft.shape[1], "count": 1,
        "dtype": "float32", "crs": crs, "transform": transform, "nodata": np.nan,
        "compress": "deflate", "predictor": 3, "tiled": True,
    }
    with rasterio.open(OUT_PATH, "w", **profile) as dst:
        dst.write(elev_ft, 1)
        dst.update_tags(units="feet", vertical_datum="NAVD88", source=PROJECT)

    print("4. Water mask")
    mask, flat_value = build_water_mask(elev_ft)
    mask_profile = {**profile, "dtype": "uint8", "nodata": None, "predictor": 2}
    with rasterio.open(WATER_MASK_PATH, "w", **mask_profile) as dst:
        dst.write(mask, 1)
        dst.update_tags(values="0 = land, 1 = Mission Bay water (hydro-flattened), 2 = ocean / no data")

    valid = elev_ft[np.isfinite(elev_ft) & (mask == 0)]  # land only
    meta = {
        "source": "USGS 3DEP standard 1 m bare-earth DEM",
        "project": PROJECT,
        "tiles": [TILE_URL.format(project=PROJECT, tile=t) for t in TILES],
        "lidar_collected": "2024-11-08 to 2024-12-01",
        "published": "2026-09-14",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "crs": str(crs),
        "vertical_datum": "NAVD88",
        "units": "feet",
        "cell_size_m": abs(transform.a),
        "study_bbox_lonlat": STUDY_BBOX_LONLAT,
        "shape_rows_cols": list(elev_ft.shape),
        "water_mask": {
            "file": WATER_MASK_PATH.name,
            "hydro_flattened_bay_height_ft_navd88": round(flat_value, 3),
            "bay_water_fraction": round(float(np.mean(mask == 1)), 4),
            "ocean_or_nodata_fraction": round(float(np.mean(mask == 2)), 4),
        },
        "land_elevation_ft_min_median_max": [round(float(np.min(valid)), 2), round(float(np.median(valid)), 2),
                                        round(float(np.max(valid)), 2)],
        "nodata_fraction": round(float(np.mean(~np.isfinite(elev_ft))), 4),
    }
    OUT_PATH.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))

    print(f"Saved {OUT_PATH.relative_to(PROJECT_ROOT)}: {elev_ft.shape[1]} x {elev_ft.shape[0]} cells "
          f"({elev_ft.shape[1] / 1000:.1f} km x {elev_ft.shape[0] / 1000:.1f} km), "
          f"{OUT_PATH.stat().st_size / 1e6:.0f} MB")
    lo, med, hi = meta["land_elevation_ft_min_median_max"]
    wm = meta["water_mask"]
    print(f"  Land heights (ft, NAVD88): min {lo}, median {med}, max {hi}")
    print(f"  Bay water (flattened at {wm['hydro_flattened_bay_height_ft_navd88']} ft): {wm['bay_water_fraction']:.1%}"
          f" of area; ocean / no-data: {wm['ocean_or_nodata_fraction']:.1%}")


if __name__ == "__main__":
    main()
