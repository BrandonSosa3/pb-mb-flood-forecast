"""Map buildings and streets the water reaches at a given level (bay side).

Building colors:  water reaches the property / storm-drain risk only / dry
Street colors:    road covered / water at the edges / dry

Usage:
  python pipeline/plot_assets_scenario.py --level 8.12 --label "Mon Oct 26, 2026"
"""

from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import box

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

FIGURES_DIR = PROJECT_ROOT / "figures"
VIEW = box(-117.2590, 32.7585, -117.2440, 32.7935)  # Mission Beach + south Pacific Beach
SURFACE, TEXT, TEXT_MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
REACHED, DRAIN, DRY = "#2a78d6", "#eda100", "#dddcd7"
COVERED, EDGES, ROAD = "#0d3a73", "#8fbcef", "#c9c8c3"
WATER_BG = "#e3eef8"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--level", type=float, required=True, help="Mission Bay still-water level, ft above MLLW")
    p.add_argument("--label", default="")
    args = p.parse_args()
    W = args.level

    b = gpd.read_file(PROCESSED_DIR / "buildings_danger.geojson")
    s = gpd.read_file(PROCESSED_DIR / "street_pieces_danger.geojson")
    b, s = b[b.intersects(VIEW)].to_crs(26911), s[s.intersects(VIEW)].to_crs(26911)

    reached = b.danger_bay_ft <= W
    drain = ~reached & (b.ground_min_ft < W)
    covered = s.covered_bay_ft <= W
    edges = ~covered & (s.danger_bay_ft <= W)

    fig, ax = plt.subplots(figsize=(7, 13))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(WATER_BG)
    s[~covered & ~edges].plot(ax=ax, color=ROAD, linewidth=0.8)
    s[edges].plot(ax=ax, color=EDGES, linewidth=1.6)
    s[covered].plot(ax=ax, color=COVERED, linewidth=1.8)
    b[~reached & ~drain].plot(ax=ax, color=DRY, edgecolor="none")
    b[drain].plot(ax=ax, color=DRAIN, edgecolor="none")
    b[reached].plot(ax=ax, color=REACHED, edgecolor="none")
    ax.set_axis_off()
    vb = gpd.GeoSeries([VIEW], crs=4326).to_crs(26911).total_bounds
    ax.set_xlim(vb[0], vb[2]); ax.set_ylim(vb[1], vb[3])

    mi = lambda m: s.loc[m, "length_m"].sum() / 1609.34
    ax.legend(handles=[
        Patch(color=REACHED, label=f"Water reaches the property ({reached.sum():,} buildings)"),
        Patch(color=DRAIN, label=f"Storm-drain risk only ({drain.sum():,})"),
        Patch(color=DRY, label="Dry"),
        Line2D([], [], color=COVERED, lw=2.5, label=f"Road covered ({mi(covered & (s.kind == 'street')):.1f} mi of street)"),
        Line2D([], [], color=EDGES, lw=2.5, label="Water at the edges"),
    ], loc="upper left", frameon=True, facecolor="white", edgecolor="none", fontsize=8.5, framealpha=0.95)
    ax.set_title(f"Bay water at {W:.2f} ft" + (f": {args.label}" if args.label else ""),
                 loc="left", fontsize=13, fontweight="bold", color=TEXT, pad=8)
    fig.text(0.02, 0.02,
             "Mission Beach + south Pacific Beach. Still water from Mission Bay, no berm, no waves.\n"
             "\"Water reaches the property\" = within 2 m of the building; floor heights unknown.\n"
             "Buildings & streets: OpenStreetMap. Ground: USGS 3DEP lidar (2024).",
             fontsize=7.5, color=TEXT_MUTED, va="bottom")

    FIGURES_DIR.mkdir(exist_ok=True)
    out = FIGURES_DIR / f"assets_bay_{W:.2f}".replace(".", "_")
    fig.savefig(f"{out}.png", dpi=170, bbox_inches="tight", facecolor=SURFACE)
    print(f"Saved {out.relative_to(PROJECT_ROOT)}.png")


if __name__ == "__main__":
    main()
