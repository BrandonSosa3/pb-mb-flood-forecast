"""Map where water reaches at a given still-water level.

Uses the danger heights from flood_threshold.py. A cell is reached by water
when its danger height <= the water level. Three kinds of land are shown:
  - water reaches it (colored by depth),
  - lower than the water but walled off (water can't get there),
  - dry.

Water levels are given in tide terms (feet above MLLW, like NOAA's gauges)
and converted to NAVD88 with La Jolla's datum offset.

Usage:
  python pipeline/plot_flood_scenario.py --level 8.2 --side bay \
      --label "Oct 27, 2026 peak (estimated for Mission Bay)"
"""

from __future__ import annotations

import argparse
import json
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from rasterio.warp import transform as warp_transform
from rasterio.windows import from_bounds

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from plot_dem import LANDMARKS, NAVD88_ABOVE_MLLW_FT, hillshade

FIGURES_DIR = PROJECT_ROOT / "figures"
DEM_PATH = PROCESSED_DIR / "dem_pbmb_navd88_ft.tif"
MASK_PATH = PROCESSED_DIR / "water_mask_pbmb.tif"
# Mission Bay (NOAA 9410196) normal high tide: MHHW is 5.45 ft above MLLW.
# Land below this is wet on an ordinary day (beach sand), so we don't count it.
NORMAL_HIGH_TIDE_MLLW = 5.45
VIEW_LONLAT = (-117.262, 32.7585, -117.222, 32.802)  # Mission Beach, Sail Bay, Crown Point

SURFACE, TEXT, TEXT_MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
BAY, LAND_LIGHT, WALLED = "#e3eef8", "#f1f0ec", "#eda100"
DEPTH_RAMP = LinearSegmentedColormap.from_list("depth", ["#8fbcef", "#2a78d6", "#0d3a73"])
DEPTH_MAX_FT = 3.0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--level", type=float, required=True, help="still-water level, feet above MLLW")
    p.add_argument("--side", choices=["bay", "ocean", "both"], default="bay")
    p.add_argument("--label", default="")
    args = p.parse_args()
    level_navd = args.level - NAVD88_ABOVE_MLLW_FT

    with rasterio.open(DEM_PATH) as src:
        win = from_bounds(*rasterio.warp.transform_bounds("EPSG:4326", src.crs, *VIEW_LONLAT), src.transform)
        win = win.round_offsets().round_lengths()
        dem = src.read(1, window=win)
        bounds = rasterio.windows.bounds(win, src.transform)
        crs = src.crs
    with rasterio.open(MASK_PATH) as src:
        mask = src.read(1, window=win)
    sides = ["bay", "ocean"] if args.side == "both" else [args.side]
    danger = np.full(dem.shape, np.inf)
    for side in sides:
        with rasterio.open(PROCESSED_DIR / f"danger_from_{side}_navd88_ft.tif") as src:
            d = src.read(1, window=win)
        danger = np.fmin(danger, np.where(np.isfinite(d), d, np.inf))

    land = mask == 0
    reached = land & (danger <= level_navd)
    walled = land & ~reached & (dem < level_navd)
    depth = np.where(reached, level_navd - dem, np.nan)
    unusual = reached & (dem + NAVD88_ABOVE_MLLW_FT > NORMAL_HIGH_TIDE_MLLW)  # not normally wet

    # --- Draw ---
    shade = hillshade(dem)[..., None]
    rgb = np.ones(dem.shape + (3,)) * matplotlib.colors.to_rgb(LAND_LIGHT)
    rgb = rgb * (0.78 + 0.22 * shade)
    rgb[mask != 0] = matplotlib.colors.to_rgb(BAY)
    rgb[walled] = matplotlib.colors.to_rgb(WALLED)
    rgb[reached] = DEPTH_RAMP(np.clip(depth[reached] / DEPTH_MAX_FT, 0, 1))[:, :3]

    fig, ax = plt.subplots(figsize=(9, 11.5))
    fig.patch.set_facecolor(SURFACE)
    ax.imshow(rgb, extent=(bounds[0], bounds[2], bounds[1], bounds[3]), interpolation="nearest")
    ax.set_axis_off()

    lats, lons = zip(*LANDMARKS.values())
    xs, ys = warp_transform("EPSG:4326", crs, lons, lats)
    for name, x, y in zip(LANDMARKS, xs, ys):
        if bounds[0] < x < bounds[2] and bounds[1] < y < bounds[3]:
            ax.annotate(name, (x, y), fontsize=9, color=TEXT, ha="center",
                        bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.85})

    # Extra place labels for this view (positions checked against the elevation map).
    for name, (lat, lon) in {"Campland area": (32.7955, -117.2265), "Mission Beach": (32.7800, -117.2565)}.items():
        x, y = warp_transform("EPSG:4326", crs, [lon], [lat])
        ax.annotate(name, (x[0], y[0]), fontsize=9, color=TEXT, ha="center", rotation=0,
                    bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.85})

    acres = lambda m: m.sum() / 4046.86  # 1 cell = 1 m^2
    ax.legend(handles=[
        Patch(color=DEPTH_RAMP(0.6), label=f"Water reaches this ground ({acres(unusual):.0f} acres above normal high tide)"),
        Patch(color=WALLED, label=f"Lower than the water, but walled off ({acres(walled):.0f} acres)"),
        Patch(color=BAY, label="Bay / ocean"),
    ], loc="upper right", frameon=True, facecolor="white", edgecolor="none", fontsize=9, framealpha=0.95)

    title = f"Still water at {args.level:.2f} ft"
    ax.set_title(title + (f": {args.label}" if args.label else ""), loc="left",
                 fontsize=13, fontweight="bold", color=TEXT, pad=10)
    fig.text(0.13, 0.06,
             f"Water from: {' + '.join(sides)}. Waves not included. Level in ft above MLLW "
             f"(= {level_navd:.2f} ft NAVD88 using NOAA La Jolla datums; ±0.2 ft).\n"
             f"Water spreads only where it can flow from the {' / '.join(sides)} without climbing anything higher. "
             "Blue darkens with depth (0 to 3+ ft).\n"
             "Ground: USGS 3DEP lidar flown Nov-Dec 2024. Storm drains and temporary berms are not modeled.",
             fontsize=7.5, color=TEXT_MUTED, va="top")

    FIGURES_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", f"{args.side}_{args.level:.2f}").strip("_")
    out = FIGURES_DIR / f"flood_{slug}.png"
    fig.savefig(out, dpi=170, bbox_inches="tight", facecolor=SURFACE)
    print(f"Saved {out.relative_to(PROJECT_ROOT)}")
    print(f"  Water reaches {acres(unusual):.1f} acres of ground above normal high tide; "
          f"{acres(walled):.1f} acres are below the water but walled off.")
    print(json.dumps({"level_mllw": args.level, "level_navd88": round(level_navd, 2), "sides": sides}))


if __name__ == "__main__":
    main()
