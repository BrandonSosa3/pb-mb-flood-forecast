"""Draw a first look at the PB + MB elevation grid.

Colors show height in "tide terms" (feet above MLLW, like the tide gauge),
so you can compare directly with water levels such as the 8.52 ft peak on
Oct 27, 2026. Shading (a "hillshade") adds fake sunlight from the northwest
so streets, berms, and the boardwalk stand out.

NOTE: this is just height. It is NOT a flood map yet - a low spot only
floods if water can actually reach it (that comes next).

Usage:
  python pipeline/plot_dem.py
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap
from rasterio.warp import transform as warp_transform

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

DEM_PATH = PROCESSED_DIR / "dem_pbmb_navd88_ft.tif"
FIGURES_DIR = PROJECT_ROOT / "figures"

# NOAA La Jolla 9410230 datums (epoch 1983-2001): NAVD88 is 0.19 ft above MLLW.
NAVD88_ABOVE_MLLW_FT = 0.19
COLOR_RANGE_FT = (4, 20)  # tide-terms feet; the range that matters for flooding

SURFACE, TEXT, TEXT_MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
WATER, NO_DATA = "#cfe2f3", "#bdbcb6"
# Land: sequential, one warm hue. Low ground darkest (it's what we care about),
# high ground near-white. Blue is reserved for water.
RAMP = LinearSegmentedColormap.from_list("low_dark", ["#5a1f08", "#b8481c", "#eb6834", "#f6b99a", "#fbf1ea"])
WATER_MASK_PATH = PROCESSED_DIR / "water_mask_pbmb.tif"

# Verified with OpenStreetMap (Nominatim) lookups.
LANDMARKS = {
    "Crystal Pier": (32.79614, -117.2575),
    "Belmont Park": (32.77089, -117.25205),
    "Crown Point": (32.78685, -117.23685),
    "Sail Bay": (32.79219, -117.24822),
    "Tourmaline": (32.80528, -117.26202),
}


def hillshade(elev: np.ndarray, azimuth: float = 315, altitude: float = 45) -> np.ndarray:
    """Fake sunlight on the terrain: 0 (shadow) .. 1 (fully lit)."""
    filled = np.where(np.isfinite(elev), elev, np.nanmedian(elev))
    dy, dx = np.gradient(filled)
    slope = np.pi / 2 - np.arctan(np.hypot(dx, dy) * 0.3)  # 0.3 = exaggeration in ft per m
    aspect = np.arctan2(-dx, dy)
    az, alt = np.radians(360 - azimuth + 90), np.radians(altitude)
    shade = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
    return np.clip(shade, 0, 1)


def main() -> None:
    with rasterio.open(DEM_PATH) as src:
        elev_navd = src.read(1)
        bounds, crs = src.bounds, src.crs
    with rasterio.open(WATER_MASK_PATH) as src:
        mask = src.read(1)
    meta = json.loads(DEM_PATH.with_suffix(".meta.json").read_text())
    elev = elev_navd + NAVD88_ABOVE_MLLW_FT  # -> feet above MLLW

    norm = np.clip((elev - COLOR_RANGE_FT[0]) / (COLOR_RANGE_FT[1] - COLOR_RANGE_FT[0]), 0, 1)
    rgb = RAMP(norm)[..., :3]
    shade = hillshade(elev_navd)[..., None]
    rgb = rgb * (0.7 + 0.3 * shade)  # gentle shading so colors stay readable
    rgb[mask == 1] = matplotlib.colors.to_rgb(WATER)
    # Ocean: no-data cells touching the west edge; other no-data = gaps in the survey.
    from scipy import ndimage
    labels, _ = ndimage.label(mask == 2)
    ocean_ids = np.setdiff1d(np.unique(labels[:, 0]), [0])
    ocean = np.isin(labels, ocean_ids)
    rgb[ocean] = matplotlib.colors.to_rgb(WATER)
    rgb[(mask == 2) & ~ocean] = matplotlib.colors.to_rgb(NO_DATA)

    extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)
    fig, ax = plt.subplots(figsize=(8.5, 13))
    fig.patch.set_facecolor(SURFACE)
    ax.imshow(rgb, extent=extent, interpolation="bilinear")
    ax.set_axis_off()

    lats, lons = zip(*LANDMARKS.values())
    xs, ys = warp_transform("EPSG:4326", crs, lons, lats)
    for name, x, y in zip(LANDMARKS, xs, ys):
        ax.scatter([x], [y], s=18, color=TEXT, edgecolor="white", lw=1, zorder=3)
        ax.annotate(name, (x, y), xytext=(6, 4), textcoords="offset points", fontsize=9, color=TEXT,
                    bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.8})
    for label, (fx, fy) in {"Pacific Ocean": (0.06, 0.55), "Mission Bay": (0.70, 0.30)}.items():
        ax.text(bounds.left + fx * (bounds.right - bounds.left), bounds.bottom + fy * (bounds.top - bounds.bottom),
                label, fontsize=11, color=TEXT_MUTED, style="italic")

    # Color key
    cax = fig.add_axes([0.14, 0.085, 0.72, 0.012])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(*COLOR_RANGE_FT), cmap=RAMP),
                      cax=cax, orientation="horizontal", extend="both")
    cb.set_ticks([4, 6, 8.52, 10, 12, 14, 16, 18, 20])
    cb.set_ticklabels(["4", "6", "8.5\nOct 27\npeak", "10", "12", "14", "16", "18", "20+"])
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, length=0, colors=TEXT_MUTED)
    cb.set_label("Ground height, feet above an ordinary low tide (MLLW)", fontsize=9, color=TEXT_MUTED)

    ax.set_title("Pacific Beach & Mission Beach: ground height", loc="left",
                 fontsize=14, fontweight="bold", color=TEXT, pad=10)
    fig.text(0.12, 0.035,
             f"Source: USGS 3DEP 1 m bare-earth lidar DEM ({meta['project']}), flown {meta['lidar_collected']}.\n"
             f"Heights converted from NAVD88 to MLLW with NOAA La Jolla datums (+{NAVD88_ABOVE_MLLW_FT} ft). "
             "Light blue = water. Gray = gap in the survey.\nThis shows height only, not flooding.",
             fontsize=7.5, color=TEXT_MUTED, va="top")

    FIGURES_DIR.mkdir(exist_ok=True)
    out = FIGURES_DIR / "dem_pbmb.png"
    fig.savefig(out, dpi=170, bbox_inches="tight", facecolor=SURFACE)
    print(f"Saved {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
