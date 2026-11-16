"""Maps + list of the rain ponding spots per neighborhood, for checking by eye.

Inputs : data/processed/ponds.geojson (rain_ponds.py), dem_rain_navd88_ft.tif, water_mask_rain.tif,
         data/raw/city/cmty_plan_datasd.geojson
Outputs: docs/evidence/rain/ponding_spots.md, ponding_la_jolla.png, ponding_pb_mb.png

Usage: python pipeline/plot_ponds.py
"""

from __future__ import annotations

import geopandas as gpd
import matplotlib
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import bounds as window_bounds
from rasterio.windows import from_bounds

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from rain_ponds import NEIGHBORHOODS, PLAN_FILE

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT_DIR = PROJECT_ROOT / "docs" / "evidence" / "rain"
TOP_N = 12
ACRE_M2 = 4046.86


def hillshade(z: np.ndarray, cell_m: float) -> np.ndarray:
    gy, gx = np.gradient(np.nan_to_num(z) * 0.3048 / cell_m)
    slope, aspect = np.arctan(np.hypot(gx, gy)), np.arctan2(-gx, gy)
    return np.clip(0.7 * np.cos(slope) + 0.7 * np.sin(slope) * np.cos(np.radians(315) - aspect), 0, 1)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ponds = gpd.read_file(PROCESSED_DIR / "ponds.geojson").to_crs(26911)
    plan = gpd.read_file(PLAN_FILE)
    plan = plan[plan.cpname.isin(NEIGHBORHOODS)].to_crs(26911)
    dem = rasterio.open(PROCESSED_DIR / "dem_rain_navd88_ft.tif")
    mask = rasterio.open(PROCESSED_DIR / "water_mask_rain.tif")
    to_ll = Transformer.from_crs(26911, 4326, always_xy=True)

    lines = ["# Rain ponding spots: first look", "",
             "_Written by `pipeline/plot_ponds.py` from `rain_terrain.py` + `rain_ponds.py` (2024 USGS lidar, "
             "OpenStreetMap streets). Not yet checked against flood reports._", "",
             "Each spot is a dip where rain water collects on a public street or alley when storm drains can't "
             "keep up.",
             "**Drains** = land whose rain flows straight into the spot, not through another dip first (bigger = "
             "more water arrives); in brackets, all land uphill (if every drain upstream fails). **Depth** = deepest "
             "water on the street when the dip is full. Numbers match the maps.", ""]

    def figure(names: list[str], fname: str, title: str) -> None:
        area = plan[plan.cpname.isin(names)]
        x0, y0, x1, y1 = area.total_bounds
        win = from_bounds(x0 - 150, y0 - 150, x1 + 150, y1 + 150, dem.transform).round_offsets().round_lengths()
        f = 3
        shape = (int(win.height // f), int(win.width // f))
        z = dem.read(1, window=win, out_shape=shape)
        m = mask.read(1, window=win, out_shape=shape)
        b = window_bounds(win, dem.transform)
        fig, ax = plt.subplots(figsize=(8.5, 11 if "La Jolla" in names else 10), dpi=120)
        ax.set_facecolor("#cfe3f5")
        ax.imshow(np.where(m == 0, hillshade(z, f), np.nan), cmap="gray", extent=(b[0], b[2], b[1], b[3]),
                  vmin=0, vmax=1.25, alpha=0.75)
        area.boundary.plot(ax=ax, color="#555", linewidth=1, linestyle="--")
        sp = ponds[ponds.neighborhood.isin(names)]
        sp[sp.kind == "street"].buffer(8).plot(ax=ax, color="#2171b5", linewidth=0)
        if (sp.kind == "check").any():
            sp[sp.kind == "check"].buffer(10).plot(ax=ax, color="#e6550d", linewidth=0)
        for n in names:
            top = sp[(sp.neighborhood == n) & (sp.kind == "street")].nlargest(TOP_N, "drainage_m2")
            lines.extend([f"## {n}", "", "| # | Street | Depth on street | Drains (all uphill) | Map |", "|---|---|---|---|---|"])
            prefix = n[0] if len(names) > 1 else ""  # P1, M1 when two neighborhoods share a map
            for i, r in enumerate(top.itertuples(), 1):
                c = r.geometry.centroid
                ax.annotate(f"{prefix}{i}", (c.x, c.y), fontsize=7, weight="bold", color="white", ha="center", va="center",
                            bbox=dict(boxstyle="circle,pad=0.2", fc="#08306b", ec="white", lw=0.8))
                lon, lat = to_ll.transform(c.x, c.y)
                street = r.streets if isinstance(r.streets, str) else "(unnamed street or alley)"
                lines.append(f"| {prefix}{i} | {street} | {r.street_max_depth_ft * 12:.0f} in | "
                             f"{r.drainage_m2 / ACRE_M2:,.0f} acres ({r.drainage_total_m2 / ACRE_M2:,.0f}) | [map](https://www.openstreetmap.org/"
                             f"?mlat={lat:.5f}&mlon={lon:.5f}#map=18/{lat:.5f}/{lon:.5f}) |")
            n_street = int(((sp.neighborhood == n) & (sp.kind == "street")).sum())
            n_check = int(((sp.neighborhood == n) & (sp.kind == "check")).sum())
            lines.extend(["", f"Street spots: {n_street}. Flagged to check (very deep on a street or a creek behind a road, usually a "
                          f"culvert the ground map cannot see): {n_check}.", ""])
        ax.set_xlim(b[0], b[2])
        ax.set_ylim(b[1], b[3])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{title}\nblue = street ponding spot · orange = check · numbers = most land draining in",
                     fontsize=9)
        plt.tight_layout()
        plt.savefig(OUT_DIR / fname)
        plt.close()
        lines.append(f"![{title}]({fname})\n")

    figure(["La Jolla"], "ponding_la_jolla.png", "La Jolla: rain ponding spots (first look)")
    figure(["Pacific Beach", "Mission Beach"], "ponding_pb_mb.png", "Pacific Beach + Mission Beach (first look)")
    (OUT_DIR / "ponding_spots.md").write_text("\n".join(lines) + "\n")
    print(f"-> {OUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
