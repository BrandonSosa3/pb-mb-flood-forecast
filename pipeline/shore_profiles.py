"""Measure the beach at every CDIP MOP point: beach slope and barrier height.

For each MOP point (~100 m apart, at ~10 m water depth) we walk a straight
line from the point toward land, along the direction the shore faces
("shore normal"), sampling the 2024 lidar ground height every 0.5 m:

  ocean ~~~~ | wet sand / beach face | dry sand | boardwalk/seawall | town
             ^ shoreline              (slope)     ^ barrier crest

  beach_slope   rise over run of the beach face between mean sea level and
                ~2 ft above an ordinary high tide - the part waves run up.
                (Stockdon 2006 calls this the "foreshore slope".)
  crest_ft      the top of the barrier: the highest point before the ground
                drops at least RIDGE_DROP_FT toward town (beach ridge /
                boardwalk / seawall). Where the land just keeps rising (bluff),
                barrier = "rising ground". Feet above MLLW.

Wave run-up only acts on the beach face, so the ocean side is judged per
stretch of beach (run-up vs crest), not by spreading water inland.

Output: data/processed/shore_profiles.csv

Usage:
  python pipeline/shore_profiles.py
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from rasterio.warp import transform as warp_transform

from noaa_tides import PROCESSED_DIR, PROJECT_ROOT
from forecast_logger import MOP_POINTS, MOP_URL
from plot_dem import NAVD88_ABOVE_MLLW_FT

DEM_PATH = PROCESSED_DIR / "dem_pbmb_navd88_ft.tif"
OUT_PATH = PROCESSED_DIR / "shore_profiles.csv"
STEP_M = 0.5
MAX_DISTANCE_M = 1500     # how far to walk from the MOP point toward land
RIDGE_SEARCH_M = 300      # look for the barrier within this distance of the shoreline
RIDGE_DROP_FT = 2.0       # ground must fall this far behind the crest to count as a barrier
# Beach face band for the slope, feet above MLLW (La Jolla: MSL = 2.73, MHHW = 5.32)
SLOPE_BAND_MLLW = (2.7, 7.3)
SLOPE_SEARCH_M = 100
# Points whose transects actually cross the PB / MB beach (jetty/channel and the
# reef off Pacific Beach Point are excluded).
STUDY_POINTS = range(365, 418)
MASK_PATH = PROCESSED_DIR / "water_mask_pbmb.tif"


def mop_metadata() -> pd.DataFrame:
    warnings.filterwarnings("ignore")
    rows = []
    for point in MOP_POINTS:
        ds = xr.open_dataset(MOP_URL.format(point, "nowcast"))
        rows.append({"point": f"D{point:04d}", "lat": float(ds.metaLatitude), "lon": float(ds.metaLongitude),
                     "depth_m": float(ds.metaWaterDepth), "shore_normal_deg": float(ds.metaShoreNormal)})
        ds.close()
    return pd.DataFrame(rows)


def profile(grids: dict, x0: float, y0: float, normal_deg: float) -> dict:
    """Sample ground and water mask along a line toward land."""
    # Shore normal = compass direction the beach FACES (toward the ocean).
    # Walking toward land means heading the opposite way.
    heading = np.radians((normal_deg + 180) % 360)
    d = np.arange(0, MAX_DISTANCE_M, STEP_M)
    pts = list(zip(x0 + d * np.sin(heading), y0 + d * np.cos(heading)))
    out = {"d": d}
    for key, src in grids.items():
        out[key] = np.array([v[0] for v in src.sample(pts)], dtype=float)
    land = (out["mask"] == 0) & np.isfinite(out["ground"])
    out["z"] = np.where(land, out["ground"] + NAVD88_ABOVE_MLLW_FT, np.nan)
    return out


def analyze(p: dict) -> dict:
    d, z = p["d"], p["z"]
    land = np.isfinite(z)
    if not land.any():
        return {"barrier": "no beach found"}
    i0 = int(np.argmax(land))  # first land cell = waterline at survey time
    n = lambda meters: int(meters / STEP_M)

    # Beach slope (Stockdon's "foreshore slope"), in meters per meter.
    dd, zz = d[i0:i0 + n(SLOPE_SEARCH_M)], z[i0:i0 + n(SLOPE_SEARCH_M)]
    band = np.isfinite(zz) & (zz >= SLOPE_BAND_MLLW[0]) & (zz <= SLOPE_BAND_MLLW[1])
    slope = np.polyfit(dd[band], zz[band] / 3.28084, 1)[0] if band.sum() >= 10 else np.nan

    # Barrier: highest point before the ground drops RIDGE_DROP_FT below it.
    zs = z[i0:i0 + n(RIDGE_SEARCH_M)]
    running_max = np.fmax.accumulate(np.where(np.isfinite(zs), zs, -np.inf))
    drop = np.flatnonzero(np.isfinite(zs) & (zs < running_max - RIDGE_DROP_FT))
    if drop.size:
        j = int(drop[0])
        i_crest = i0 + int(np.nanargmax(zs[:j + 1]))
        barrier = "ridge"  # boardwalk / seawall / beach berm with lower town behind
    else:
        i_crest = i0 + int(np.nanargmax(zs))
        barrier = "rising ground"  # bluff / hill: no low town right behind
    return {"shoreline_dist_m": round(float(d[i0]), 1), "beach_slope": round(float(slope), 4),
            "barrier": barrier, "crest_ft": round(float(z[i_crest]), 2),
            "crest_from_shore_m": round(float(d[i_crest] - d[i0]), 1)}


def main() -> None:
    print("MOP point locations ...")
    pts = mop_metadata()
    pts = pts[pts.point.isin([f"D{i:04d}" for i in STUDY_POINTS])]
    grids = {"ground": rasterio.open(DEM_PATH), "mask": rasterio.open(MASK_PATH)}
    xs, ys = warp_transform("EPSG:4326", grids["ground"].crs, pts.lon.tolist(), pts.lat.tolist())
    rows = [{**p.to_dict(), **analyze(profile(grids, x, y, p.shore_normal_deg))}
            for (_, p), x, y in zip(pts.iterrows(), xs, ys)]
    for g in grids.values():
        g.close()
    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)
    meta = {"dem": DEM_PATH.name, "units": "feet above MLLW (La Jolla datums)", "step_m": STEP_M,
            "ridge_search_m": RIDGE_SEARCH_M, "ridge_drop_ft": RIDGE_DROP_FT, "slope_band_ft_mllw": SLOPE_BAND_MLLW,
            "mop_source": MOP_URL.format(0, "nowcast")}
    OUT_PATH.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(out[["point", "lat", "beach_slope", "barrier", "crest_ft", "crest_from_shore_m"]].to_string(index=False))
    print(f"Saved {OUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
