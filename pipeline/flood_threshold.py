"""For every 1 m cell of ground: how high must the water rise before it gets there?

This is the "danger height" of each spot, with CONNECTIVITY: water has to be
able to flow there from the bay or ocean without climbing over anything
higher. Example: a parking lot at 6 ft behind a berm at 9 ft gets a danger
height of 9 ft, not 6 ft - it stays dry until the water tops the berm.

How it works (the idea): imagine water rising from the bay. For each cell,
look at every possible path from the water to that cell; along each path,
the water must reach the path's highest point. The cell's danger height is
the LOWEST such "highest point" over all paths. Mathematically this is
"morphological reconstruction by erosion"; scikit-image does it in C, fast.

Water moves only to the 4 direct neighbours (N, S, E, W), not diagonally, so
it can't sneak between two wall cells that only touch at a corner.

We compute it twice, because the two sides will get different water levels
once we add waves:
  danger_from_bay_navd88_ft.tif     water starting from Mission Bay
  danger_from_ocean_navd88_ft.tif   water starting from the open ocean
Heights stay in NAVD88 feet (same as the elevation grid).

Usage:
  python pipeline/flood_threshold.py
"""

from __future__ import annotations

import json
import time

import numpy as np
import rasterio
from scipy import ndimage
from skimage.morphology import reconstruction

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

DEM_PATH = PROCESSED_DIR / "dem_pbmb_navd88_ft.tif"
WATER_MASK_PATH = PROCESSED_DIR / "water_mask_pbmb.tif"
BARRIER_FT = 1000.0  # "water can't pass" (used for survey gaps / the other water body)
FOUR_NEIGHBOURS = ndimage.generate_binary_structure(2, 1)


def danger_heights(ground: np.ndarray, source: np.ndarray) -> np.ndarray:
    """Lowest water level at which water from `source` cells reaches each cell."""
    seed = np.full_like(ground, BARRIER_FT)
    seed[source] = ground[source]  # water is already there
    # Reconstruction by erosion: lowers the seed as far as it can while staying
    # above the ground, spreading only through connected cells.
    return reconstruction(seed, ground, method="erosion", footprint=FOUR_NEIGHBOURS)


def main() -> None:
    with rasterio.open(DEM_PATH) as src:
        dem = src.read(1).astype("float64")
        profile = src.profile
    with rasterio.open(WATER_MASK_PATH) as src:
        mask = src.read(1)

    # Split no-data into ocean (touches the west edge) and survey gaps.
    labels, _ = ndimage.label(mask == 2)
    ocean_ids = np.setdiff1d(np.unique(labels[:, 0]), [0])
    ocean = np.isin(labels, ocean_ids)
    gaps = (mask == 2) & ~ocean
    bay = mask == 1
    print(f"Cells: {dem.size:,}  bay water {bay.mean():.1%}, ocean {ocean.mean():.1%}, survey gaps {gaps.mean():.1%}")

    OCEAN_SURFACE_FT = -3.0  # ocean cells have no height in the data; any value below land works
    outputs = {}
    for name, source, blocked in [("bay", bay, ocean | gaps), ("ocean", ocean, bay | gaps)]:
        ground = dem.copy()
        ground[ocean] = OCEAN_SURFACE_FT
        ground[blocked] = BARRIER_FT  # the OTHER water body is treated as a wall
        start = time.time()
        danger = danger_heights(ground, source)
        danger[source | blocked] = np.nan  # only meaningful on land
        print(f"  from {name}: {time.time() - start:.0f} s")
        out = PROCESSED_DIR / f"danger_from_{name}_navd88_ft.tif"
        with rasterio.open(out, "w", **{**profile, "dtype": "float32"}) as dst:
            dst.write(danger.astype("float32"), 1)
            dst.update_tags(units="feet", vertical_datum="NAVD88",
                            meaning=f"lowest still-water level at which water from the {name} reaches this cell")
        outputs[name] = out.name

    meta = {
        "method": "morphological reconstruction by erosion (4-connected), scikit-image",
        "inputs": [DEM_PATH.name, WATER_MASK_PATH.name],
        "outputs": outputs,
        "units": "feet NAVD88",
        "notes": [
            "Bare-earth ground only: walls/berms narrower than 1 m may be under-represented.",
            "No storm drains: water arriving through pipes is not modeled.",
            "Survey gaps are treated as walls.",
        ],
    }
    (PROCESSED_DIR / "danger_heights.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved {', '.join(outputs.values())} in {PROCESSED_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
