"""Building heights from the 2024 USGS lidar point cloud, for the 3D view.

The lidar plane records every laser hit. Hits on rooftops are "first returns" that the survey left
unclassified (class 1; the 2024 survey has no separate building class) or marked as building (class 6,
used by the 2014 survey). Tiles of the 2024 survey we couldn't download yet are filled from the 2014
survey (lpc_fill_2014.py); a 2014 tile is used only while its 2024 tile is missing. For each OpenStreetMap
building outline:
  roof   = 75th percentile height of class-1 first returns inside the outline, shrunk by 0.5 m
           (so overhanging trees and the neighbor's wall count less)
  ground = median bare-earth height under the outline (our 1 m DEM)
  height = roof - ground, kept between MIN_M and MAX_M; buildings with too few hits get the
           median measured height.

For display only (3D blocks). Flood answers never use building height: "water reaches this
property" is about the ground next to it.

Inputs : data/raw/lpc/*.laz (USGS LPC CA_SanDiegoCo_D24, tiles listed in data/raw/lpc/urls.txt),
         data/processed/buildings_danger.geojson, dem_pbmb_navd88_ft.tif
Outputs: data/processed/building_heights.csv (+ .meta.json),
         web/public/data/buildings3d.geojson (every building: h, d, db, g)

Usage: python pipeline/building_heights.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import geopandas as gpd
import laspy
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT

LPC_DIR = PROJECT_ROOT / "data" / "raw" / "lpc"
SHRINK_M = 0.5
ROOF_PERCENTILE = 75
MIN_POINTS = 8
MIN_M, MAX_M = 2.5, 40.0  # buildings with too few hits get the median measured height
FT_TO_M = 0.3048
OUT_CSV = PROCESSED_DIR / "building_heights.csv"
OUT_3D = PROJECT_ROOT / "web" / "public" / "data" / "buildings3d.geojson"


def main() -> None:
    bld = gpd.read_file(PROCESSED_DIR / "buildings_danger.geojson")
    with rasterio.open(PROCESSED_DIR / "dem_pbmb_navd88_ft.tif") as src:
        dem, transform, crs, shape = src.read(1), src.transform, src.crs, src.shape
    bld = bld.to_crs(crs).reset_index(drop=True)
    bld["bid"] = np.arange(1, len(bld) + 1, dtype=np.int32)

    # 1 m grid of building ids: full outlines for the ground, shrunk outlines for the roof.
    full = rasterize(zip(bld.geometry, bld.bid), out_shape=shape, transform=transform, fill=0, dtype="int32")
    inner_geom = bld.geometry.buffer(-SHRINK_M)
    inner_geom = inner_geom.where(~inner_geom.is_empty, bld.geometry)  # tiny buildings: keep the outline
    inner = rasterize(zip(inner_geom, bld.bid), out_shape=shape, transform=transform, fill=0, dtype="int32")

    ground_ft = pd.Series(dem[full > 0]).groupby(full[full > 0]).median()

    ids, zs = [], []
    tiles_2024 = sorted(LPC_DIR.glob("USGS_LPC_CA_SanDiegoCo_D24_*.laz"))
    have = {p.stem.rsplit("_", 1)[1] for p in tiles_2024}
    tiles_2014 = [p for p in sorted(LPC_DIR.glob("USGS_LPC_2014fill_*.laz")) if p.stem.rsplit("_", 1)[1] not in have]
    tiles = tiles_2024 + tiles_2014
    year_of = np.zeros(len(bld) + 1, dtype=np.int16)
    inv = ~transform
    for i, path in enumerate(tiles, 1):
        las = laspy.read(path)
        keep = np.isin(np.asarray(las.classification), (1, 6)) & (np.asarray(las.return_number) == 1)
        x, y, z = np.asarray(las.x)[keep], np.asarray(las.y)[keep], np.asarray(las.z)[keep]
        col, row = inv * (x, y)
        row, col = np.floor(row).astype(np.int64), np.floor(col).astype(np.int64)
        ok = (row >= 0) & (row < shape[0]) & (col >= 0) & (col < shape[1])
        b = np.zeros(len(z), dtype=np.int32)
        b[ok] = inner[row[ok], col[ok]]
        ids.append(b[b > 0])
        year_of[np.unique(b[b > 0])] = 2014 if "2014fill" in path.name else 2024
        zs.append(z[b > 0].astype(np.float32))
        print(f"  {i}/{len(tiles)} {path.name}: {int((b > 0).sum()):,} roof hits")
    pts = pd.DataFrame({"bid": np.concatenate(ids), "z": np.concatenate(zs)})
    g = pts.groupby("bid").z
    roof = pd.DataFrame({"roof_m": g.quantile(ROOF_PERCENTILE / 100), "n": g.size()})

    out = bld[["osm_id", "bid"]].set_index("bid").join(roof).join((ground_ft * FT_TO_M).rename("ground_m"))
    out["height_m"] = (out.roof_m - out.ground_m).clip(MIN_M, MAX_M)
    out["estimated"] = out.n.fillna(0) < MIN_POINTS
    out["lidar_year"] = np.where(out.estimated, 0, year_of[out.index.to_numpy()])
    default_m = round(float(out.loc[~out.estimated, "height_m"].median()), 1)
    out.loc[out.estimated, "height_m"] = default_m
    out = out.round(2)
    out.to_csv(OUT_CSV)

    site = bld.join(out[["height_m"]], on="bid")
    site = site[["height_m", "danger_bay_ft", "danger_bay_berm_ft", "ground_min_ft", "geometry"]].rename(
        columns={"height_m": "h", "danger_bay_ft": "d", "danger_bay_berm_ft": "db", "ground_min_ft": "g"}).to_crs(4326)
    site["geometry"] = site.geometry.set_precision(1e-5)
    for c in ("d", "db", "g"):
        site[c] = site[c].round(1)
    site["h"] = site.h.round(1)
    OUT_3D.write_text(site.to_json(drop_id=True))

    meta = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "USGS 3DEP Lidar Point Cloud CA_SanDiegoCo_D24 (collected Nov 2024), via rockyweb.usgs.gov",
            "tiles": [p.name for p in tiles], "tiles_2024": len(tiles_2024), "tiles_2014_fill": len(tiles_2014),
            "fill_source": "USGS CA_SanDiegoQL2_2014 (AWS usgs-lidar-public, EPT) where the 2024 tile is missing",
            "buildings_by_lidar_year": {str(k): int(v) for k, v in out.lidar_year.value_counts().items()},
            "points": "first returns, class 1 (unclassified) or 6 (building)",
            "roof_percentile": ROOF_PERCENTILE, "shrink_m": SHRINK_M, "min_points": MIN_POINTS,
            "clip_m": [MIN_M, MAX_M], "default_m": default_m, "buildings": int(len(out)),
            "estimated_default_height": int(out.estimated.sum()),
            "height_m_median": float(out.height_m.median()), "purpose": "3D display only"}
    (PROCESSED_DIR / "building_heights.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"{len(out):,} buildings; median height {out.height_m.median():.1f} m; "
          f"{int(out.estimated.sum()):,} without enough lidar hits (set to {default_m} m) "
          f"-> {OUT_3D.relative_to(PROJECT_ROOT)} ({OUT_3D.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
