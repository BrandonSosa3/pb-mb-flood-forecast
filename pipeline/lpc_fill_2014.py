"""Fill missing 2024 lidar point-cloud tiles with the 2014 USGS survey (building heights for the 3D view).

The 2024 point cloud (CA_SanDiegoCo_D24) is only on USGS rockyweb, which rate-limits bulk downloads. For the
1 km tiles we don't have yet, this reads the 2014 survey CA_SanDiegoQL2_2014 (the same survey that fills the
ground-map gaps; the 2015 survey on AWS doesn't cover the coast) from USGS's open-data copy on
AWS (s3://usgs-lidar-public, Entwine Point Tile format: one big point cloud split into a tree of small
.laz chunks, so only the chunks covering our tiles are downloaded).

For each missing tile it keeps first returns of classes 1 (unclassified), 2 (ground) and 6 (building),
converts web-mercator x/y to UTM 11N (EPSG:26911), and writes data/raw/lpc/USGS_LPC_2014fill_<tile>.laz.
building_heights.py uses a fill tile only while the 2024 tile is missing. Heights are checked against the
2024 ground map (ground points vs DEM) before use.

Usage: python pipeline/lpc_fill_2014.py
"""

from __future__ import annotations

import io
import json
import re
from concurrent.futures import ThreadPoolExecutor

import laspy
import numpy as np
import requests
from pyproj import Transformer

from noaa_tides import PROJECT_ROOT

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CA_SanDiegoQL2_2014/"
LPC_DIR = PROJECT_ROOT / "data" / "raw" / "lpc"
HEADERS = {"User-Agent": "coastal-flood-forecast-research"}
KEEP_CLASSES = (1, 2, 6)
TILE_RE = re.compile(r"_(11S\w\w)(\d{3})(\d{3})\.laz$")


def missing_tiles() -> dict[str, tuple[float, float, float, float]]:
    """Missing 2024 tile -> UTM bounds (tile 'MS475628' = 475-476 km E, 3628-3629 km N)."""
    out = {}
    for url in (LPC_DIR / "urls.txt").read_text().split():
        name = url.rsplit("/", 1)[1]
        if (LPC_DIR / name).exists():
            continue
        m = TILE_RE.search(name)
        e, n = int(m.group(2)) * 1000, 3_000_000 + int(m.group(3)) * 1000
        out[m.group(1) + m.group(2) + m.group(3)] = (e, n, e + 1000, n + 1000)
    return out


def nodes_in(box3857: tuple[float, float, float, float]) -> list[str]:
    """EPT chunks (D-X-Y-Z keys) whose cube overlaps the box, walking the hierarchy files."""
    info = requests.get(EPT + "ept.json", headers=HEADERS, timeout=60).json()
    b = info["bounds"]
    keys, todo = [], ["0-0-0-0"]
    while todo:
        h = requests.get(EPT + f"ept-hierarchy/{todo.pop()}.json", headers=HEADERS, timeout=60).json()
        for key, count in h.items():
            d, x, y, _ = map(int, key.split("-"))
            size = (b[3] - b[0]) / 2 ** d
            x0, y0 = b[0] + x * size, b[1] + y * size
            if x0 > box3857[2] or x0 + size < box3857[0] or y0 > box3857[3] or y0 + size < box3857[1]:
                continue
            if count == -1:
                todo.append(key)  # this branch's hierarchy is in its own file
            elif count > 0:
                keys.append(key)
    return sorted(set(keys))


def main() -> None:
    tiles = missing_tiles()
    if not tiles:
        print("No missing tiles.")
        return
    to_utm = Transformer.from_crs(3857, 26911, always_xy=True)
    to_web = Transformer.from_crs(26911, 3857, always_xy=True)
    xs, ys = zip(*[to_web.transform(x, y) for t in tiles.values() for x, y in ((t[0], t[1]), (t[2], t[3]))])
    box = (min(xs) - 50, min(ys) - 50, max(xs) + 50, max(ys) + 50)
    keys = nodes_in(box)
    print(f"{len(tiles)} missing tiles; {len(keys)} EPT chunks to read")

    parts: dict[str, list[np.ndarray]] = {t: [] for t in tiles}

    def fetch(key: str) -> np.ndarray | None:
        r = requests.get(EPT + f"ept-data/{key}.laz", headers=HEADERS, timeout=120)
        r.raise_for_status()
        las = laspy.read(io.BytesIO(r.content))
        keep = np.isin(np.asarray(las.classification), KEEP_CLASSES) & (np.asarray(las.return_number) == 1)
        if not keep.any():
            return None
        x, y = to_utm.transform(np.asarray(las.x)[keep], np.asarray(las.y)[keep])
        return np.c_[x, y, np.asarray(las.z)[keep], np.asarray(las.classification)[keep]]

    with ThreadPoolExecutor(8) as pool:
        for i, pts in enumerate(pool.map(fetch, keys), 1):
            if pts is not None:
                for t, (x0, y0, x1, y1) in tiles.items():
                    inside = (pts[:, 0] >= x0) & (pts[:, 0] < x1) & (pts[:, 1] >= y0) & (pts[:, 1] < y1)
                    if inside.any():
                        parts[t].append(pts[inside])
            if i % 200 == 0:
                print(f"  {i}/{len(keys)} chunks")

    for t, chunks in parts.items():
        if not chunks:
            print(f"  {t}: no points (water?)")
            continue
        p = np.concatenate(chunks)
        hdr = laspy.LasHeader(point_format=1, version="1.2")
        hdr.offsets, hdr.scales = p[:, :3].min(axis=0), np.array([0.01, 0.01, 0.01])
        las = laspy.LasData(hdr)
        las.x, las.y, las.z = p[:, 0], p[:, 1], p[:, 2]
        las.classification = p[:, 3].astype(np.uint8)
        las.return_number = np.ones(len(p), np.uint8)
        las.number_of_returns = np.ones(len(p), np.uint8)
        las.write(LPC_DIR / f"USGS_LPC_2014fill_{t}.laz")
        print(f"  {t}: {len(p):,} points")
    (LPC_DIR / "fill_2014.meta.json").write_text(json.dumps({
        "source": EPT, "project": "CA_SanDiegoQL2_2014 (USGS 3DEP, AWS open data)",
        "tiles": sorted(tiles), "classes_kept": KEEP_CLASSES, "returns": "first",
        "crs": "EPSG:26911 (from EPSG:3857)", "purpose": "3D building heights only, where 2024 tiles are missing"},
        indent=2))


if __name__ == "__main__":
    main()
