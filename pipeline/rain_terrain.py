"""Where rain water flows and where it ponds, from the 1 m ground grid (greater PB + La Jolla).

Plain idea: rain runs downhill. Where the ground has a dip with no downhill way out (except a storm
drain, which the ground map can't see), water collects. We find:

  ponding spots  every dip, with how deep it gets when full, how much it holds, and its edge
  drainage area  how much land uphill sends its rain into each cell / each dip, two ways:
                 own   = land draining in without passing through another spot first (normal storm:
                         upstream dips and their drains take their share)
                 total = everything uphill (if every dip and drain upstream overflows)
  flow paths     cells that collect water from a large area (where water runs in a storm)

Method (standard terrain hydrology, done in one pass to fit in memory):
  1. Priority-flood fill (Barnes, Lehman & Mulla 2014): start at the shoreline and grid edge and
     "raise water" uphill, always from the lowest open cell. A cell lower than the water reaching it
     is inside a dip; its filled height = the dip's spill level. Pop order is a valid downhill order.
  2. Flow direction: steepest drop on the filled surface (D8); inside filled dips and flats, toward
     the cell the flood came from (so water crosses the dip to its spill point).
  3. Drainage area: add each cell's 1 m2 to the cell it drains to, uphill to downhill.
  4. Ponding spots: connected cells where filled - ground >= MIN_DEPTH_FT.

Limits: storm drains and culverts are not in the ground map. Roads built across canyons over a culvert
look like dams, so the ground behind them looks like a deep pond ("digital dams"); those are flagged.
Water entering from outside the grid (Rose Creek and canyons east of I-5) is not counted.

Inputs : data/processed/dem_rain_navd88_ft.tif, water_mask_rain.tif (dem_prepare.py --area rain)
Outputs: data/processed/rain_depth_ft.tif      depth of water when each dip is full (0 outside dips)
         data/processed/rain_drainage_m2.tif   drainage area per cell (m2)
         data/processed/ponds.csv (+ .meta.json) one row per ponding spot

Usage: python pipeline/rain_terrain.py
"""

from __future__ import annotations

import heapq
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import rasterio
from numba import njit
from scipy import ndimage

from noaa_tides import PROCESSED_DIR

DEM = PROCESSED_DIR / "dem_rain_navd88_ft.tif"
MASK = PROCESSED_DIR / "water_mask_rain.tif"
MIN_DEPTH_FT = 0.1     # cells at least this deep when full count as part of a dip
MIN_POND_DEPTH_FT = 0.25  # a ponding spot must be at least 3 in deep somewhere
MIN_POND_AREA_M2 = 20
M3_PER_M2FT = 0.3048

# 8 neighbours: row step, column step, distance (cells)
DR = np.array([-1, -1, 0, 1, 1, 1, 0, -1], np.int64)
DC = np.array([0, 1, 1, 1, 0, -1, -1, -1], np.int64)
DIST = np.array([1, 2 ** 0.5, 1, 2 ** 0.5, 1, 2 ** 0.5, 1, 2 ** 0.5], np.float32)
OUTLET = 8  # drains off the land (to the bay, ocean or grid edge)
NONE = 9    # not land


@njit(cache=True)
def priority_flood(z, land):
    """Filled heights, the direction each cell's flood came from, and the pop order (low to high)."""
    nr, nc = z.shape
    filled = z.copy()
    came = np.full((nr, nc), NONE, np.uint8)
    order = np.empty(nr * nc, np.int32)
    heap = [(np.float32(0.0), np.int64(0))]
    heap.pop()
    # Seeds: land cells on the grid edge or next to water / no-data.
    for r in range(nr):
        for c in range(nc):
            if not land[r, c]:
                continue
            edge = r == 0 or c == 0 or r == nr - 1 or c == nc - 1
            if not edge:
                for k in range(8):
                    if not land[r + DR[k], c + DC[k]]:
                        edge = True
                        break
            if edge:
                came[r, c] = OUTLET
                heapq.heappush(heap, (z[r, c], np.int64(r * nc + c)))
    n = 0
    while len(heap) > 0:
        e, i = heapq.heappop(heap)
        order[n] = i
        n += 1
        r, c = i // nc, i % nc
        for k in range(8):
            rr, cc = r + DR[k], c + DC[k]
            if rr < 0 or cc < 0 or rr >= nr or cc >= nc or not land[rr, cc] or came[rr, cc] != NONE:
                continue
            came[rr, cc] = (k + 4) % 8  # direction back to (r, c)
            if filled[rr, cc] < e:
                filled[rr, cc] = e
            heapq.heappush(heap, (filled[rr, cc], np.int64(rr * nc + cc)))
    return filled, came, order[:n]


@njit(cache=True)
def drainage(filled, came, order):
    """D8 on the filled surface (flood direction in flats), then drainage area in m2."""
    nr, nc = filled.shape
    to = came.copy()
    for idx in range(order.size):
        i = order[idx]
        r, c = i // nc, i % nc
        best, bk = np.float32(0.0), -1
        for k in range(8):
            rr, cc = r + DR[k], c + DC[k]
            if rr < 0 or cc < 0 or rr >= nr or cc >= nc or came[rr, cc] == NONE:
                continue
            drop = (filled[r, c] - filled[rr, cc]) / DIST[k]
            if drop > best:
                best, bk = drop, k
        if bk >= 0:
            to[r, c] = bk
    acc = np.zeros((nr, nc), np.float32)
    for idx in range(order.size - 1, -1, -1):  # uphill first
        i = order[idx]
        r, c = i // nc, i % nc
        acc[r, c] += 1.0
        k = to[r, c]
        if k < 8:
            acc[r + DR[k], c + DC[k]] += acc[r, c]
    return to, acc


@njit(cache=True)
def local_drainage(to, order, absorb):
    """Drainage area that reaches each cell WITHOUT first passing through a ponding spot: water that
    flows into a spot stays there (its storm drain / the dip takes it) instead of running on."""
    nr, nc = to.shape
    acc = np.zeros((nr, nc), np.float32)
    for idx in range(order.size - 1, -1, -1):
        i = order[idx]
        r, c = i // nc, i % nc
        acc[r, c] += 1.0
        k = to[r, c]
        if k < 8:
            rr, cc = r + DR[k], c + DC[k]
            if not (absorb[r, c] and not absorb[rr, cc]):  # leaving a spot: stop
                acc[rr, cc] += acc[r, c]
    return acc


def main() -> None:
    t0 = time.time()
    with rasterio.open(DEM) as src:
        z = src.read(1)
        profile = src.profile
    with rasterio.open(MASK) as src:
        land = (src.read(1) == 0) & np.isfinite(z)
    z = np.where(land, z, np.float32(0)).astype(np.float32)
    print(f"{land.sum() / 1e6:.0f} million land cells")

    filled, came, order = priority_flood(z, land)
    print(f"  filled in {time.time() - t0:.0f} s")
    to, acc = drainage(filled, came, order)
    del came
    print(f"  drainage area in {time.time() - t0:.0f} s")

    depth = np.where(land, filled - z, np.float32(0)).astype(np.float32)
    spill = filled
    del filled
    out = {**profile, "dtype": "float32", "nodata": None, "compress": "deflate", "predictor": 3, "tiled": True}
    with rasterio.open(PROCESSED_DIR / "rain_depth_ft.tif", "w", **out) as dst:
        dst.write(depth, 1)
    with rasterio.open(PROCESSED_DIR / "rain_drainage_m2.tif", "w", **out) as dst:
        dst.write(np.where(land, acc, 0).astype(np.float32), 1)

    # Ponding spots: connected (8-neighbour) cells at least MIN_DEPTH_FT deep when full.
    wet = depth >= MIN_DEPTH_FT
    labels, n = ndimage.label(wet, structure=np.ones((3, 3), bool))
    print(f"  {n:,} dips before filtering ({time.time() - t0:.0f} s)")
    idx = np.arange(1, n + 1)
    area = ndimage.sum(wet, labels, idx)
    maxd = ndimage.maximum(depth, labels, idx)
    vol = ndimage.sum(depth, labels, idx) * M3_PER_M2FT
    drain = ndimage.maximum(acc, labels, idx)  # largest drainage area inside = everything flowing in
    level = ndimage.maximum(spill, labels, idx)
    deepest = ndimage.maximum_position(depth, labels, idx)
    keep = (maxd >= MIN_POND_DEPTH_FT) & (area >= MIN_POND_AREA_M2)
    kept_ids = np.flatnonzero(keep) + 1
    absorb = np.isin(labels, kept_ids)
    own = ndimage.maximum(local_drainage(to, order, absorb), labels, idx)
    del to, order, absorb
    t = profile["transform"]
    rows = []
    for j in np.flatnonzero(keep):
        r, c = deepest[j]
        x, y = t * (c + 0.5, r + 0.5)
        rows.append({"pond": int(j + 1), "x": round(x, 1), "y": round(y, 1), "area_m2": int(area[j]),
                     "max_depth_ft": round(float(maxd[j]), 2), "volume_m3": round(float(vol[j]), 1),
                     "drainage_m2": int(own[j]), "drainage_total_m2": int(drain[j]),
                     "spill_ft_navd88": round(float(level[j]), 2)})
    ponds = pd.DataFrame(rows)
    # Rain needed to fill the dip if every drop ran off and no drain worked (inches).
    ponds["fill_rain_in"] = (ponds.volume_m3 / ponds.drainage_m2 / 0.0254).round(2)
    ponds.to_csv(PROCESSED_DIR / "ponds.csv", index=False)
    np.save(PROCESSED_DIR / "rain_pond_labels.npy", labels.astype(np.int32))  # for the next step (not in git)
    meta = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "inputs": [DEM.name, MASK.name], "method": "priority-flood fill (Barnes et al. 2014), D8 on filled "
            "surface, flood direction in flats", "min_depth_ft": MIN_DEPTH_FT,
            "pond_filter": {"min_max_depth_ft": MIN_POND_DEPTH_FT, "min_area_m2": MIN_POND_AREA_M2},
            "ponds": int(len(ponds)), "dips_before_filter": int(n),
            "drainage_m2": "own drainage area (not through another spot); drainage_total_m2 = all uphill",
            "fill_rain_in": "volume / own drainage area: rain that fills the dip with 100% runoff and no drains"}
    (PROCESSED_DIR / "ponds.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"{len(ponds):,} ponding spots (>= {MIN_POND_DEPTH_FT} ft deep, >= {MIN_POND_AREA_M2} m2) "
          f"in {time.time() - t0:.0f} s")
    print(ponds.describe().round(2).to_string())


if __name__ == "__main__":
    main()
