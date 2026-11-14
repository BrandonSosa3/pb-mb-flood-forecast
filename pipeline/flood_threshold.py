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
from rasterio.warp import transform as warp_transform
from skimage.morphology import reconstruction

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

DEM_PATH = PROCESSED_DIR / "dem_pbmb_navd88_ft.tif"
WATER_MASK_PATH = PROCESSED_DIR / "water_mask_pbmb.tif"
BARRIER_FT = 1000.0  # "water can't pass" (used for survey gaps / the other water body)
FOUR_NEIGHBOURS = ndimage.generate_binary_structure(2, 1)
OCEAN_SIDE_MIN_LAT = 32.7598  # just north of the Mission Bay north jetty

# "Berm holds" scenario. Each winter the City builds a sand berm along Mission
# Beach's bay shoreline (Bayside Walk). Exact alignment and height are not
# published; reports give "six to seven feet" tall, and on Oct 27-28, 2026 the
# rebuilt berm held with Mission Bay at ~8.1-8.2 ft. We model it as a band of
# shoreline ground raised to an effective top of BERM_TOP_MLLW_FT, along the
# bay-facing shore along Bayside Walk. (Assumption - documented.)
BERM_TOP_MLLW_FT = 9.0
BERM_BAND_M = 4
BERM_WALK_DISTANCE_M = 60  # shoreline within this distance of Bayside Walk gets the berm
MISSION_BEACH_LONLAT = (-117.2620, 32.7585, -117.2425, 32.7908)  # all of its bay shore (same box as areas.py)
NAVD88_ABOVE_MLLW_FT = 0.19  # NOAA La Jolla datums


def danger_heights(ground: np.ndarray, source: np.ndarray) -> np.ndarray:
    """Lowest water level at which water from `source` cells reaches each cell."""
    seed = np.full_like(ground, BARRIER_FT)
    seed[source] = ground[source]  # water is already there
    # Reconstruction by erosion: lowers the seed as far as it can while staying
    # above the ground, spreading only through connected cells.
    return reconstruction(seed, ground, method="erosion", footprint=FOUR_NEIGHBOURS)


def berm_band(mask: np.ndarray, profile: dict) -> np.ndarray:
    """Shoreline land cells (within BERM_BAND_M of Mission Bay water) that get the berm:
    all of Mission Beach's bay shore, plus the shore along Bayside Walk.

    The berm follows Bayside Walk (OpenStreetMap), which runs from Mission Beach
    around Sail Bay to Crown Point, so its ends tie into higher ground instead of
    letting water walk around them along the beach.
    """
    import geopandas as gpd
    from rasterio.features import rasterize

    ways = gpd.read_file(PROCESSED_DIR / "osm_ways.geojson")
    walk = ways[ways.name == "Bayside Walk"].to_crs(profile["crs"])
    near_walk = rasterize([(g, 1) for g in walk.geometry.buffer(BERM_WALK_DISTANCE_M)],
                          out_shape=mask.shape, transform=profile["transform"]).astype(bool)
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds

    win = from_bounds(*transform_bounds("EPSG:4326", profile["crs"], *MISSION_BEACH_LONLAT),
                      profile["transform"]).round_offsets().round_lengths()
    in_mission_beach = np.zeros(mask.shape, bool)
    r0, c0 = max(int(win.row_off), 0), max(int(win.col_off), 0)
    in_mission_beach[r0:r0 + int(win.height), c0:c0 + int(win.width)] = True
    near_bay = ndimage.binary_dilation(mask == 1, structure=FOUR_NEIGHBOURS, iterations=BERM_BAND_M) & (mask == 0)
    return near_bay & (near_walk | in_mission_beach)


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

    # Ocean-side water (where waves matter) enters only across the PB / MB beach.
    # Ocean cells at the channel mouth and south of it are walls for that run:
    # water in the channel is at the same level as the bay and is handled by
    # the bay run.
    (_,), (y_cut,) = warp_transform("EPSG:4326", profile["crs"], [-117.256], [OCEAN_SIDE_MIN_LAT])
    rows_south = np.arange(dem.shape[0]) > rasterio.transform.rowcol(profile["transform"], 0, y_cut)[0]
    channel_ocean = ocean & rows_south[:, None]
    beach_ocean = ocean & ~channel_ocean

    OCEAN_SURFACE_FT = -3.0  # ocean cells have no height in the data; any value below land works
    outputs = {}
    berm = berm_band(mask, profile)
    berm_top_navd = BERM_TOP_MLLW_FT - NAVD88_ABOVE_MLLW_FT
    print(f"  berm band: {berm.sum():,} cells (~{berm.sum() / BERM_BAND_M / 1000:.1f} km of shoreline), "
          f"top {BERM_TOP_MLLW_FT} ft MLLW")
    runs = [("bay", bay, ocean | gaps, False),
            ("bay_berm", bay, ocean | gaps, True),
            ("ocean", beach_ocean, bay | gaps | channel_ocean, False)]
    for name, source, blocked, with_berm in runs:
        ground = dem.copy()
        if with_berm:
            ground[berm] = np.maximum(ground[berm], berm_top_navd)
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
            "Ocean run: water enters only across the PB/MB beach (north of the channel mouth).",
            f"bay_berm run: bay shoreline along Bayside Walk ({BERM_BAND_M} m band) raised to "
            f"{BERM_TOP_MLLW_FT} ft MLLW (assumed effective berm top).",
        ],
    }
    (PROCESSED_DIR / "danger_heights.meta.json").write_text(json.dumps(meta, indent=2))
    meta["berm"] = {"top_ft_mllw": BERM_TOP_MLLW_FT, "band_m": BERM_BAND_M,
                    "along": f"Bayside Walk (OSM), shoreline within {BERM_WALK_DISTANCE_M} m"}
    (PROCESSED_DIR / "danger_heights.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved {', '.join(outputs.values())} in {PROCESSED_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
