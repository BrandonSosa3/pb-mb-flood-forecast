"""Politely download the 2024 USGS lidar point-cloud tiles listed in data/raw/lpc/urls.txt.

USGS rockyweb rate-limits bulk downloads (HTTP 429). This downloader is deliberately gentle:
  - optional wait before the first request (--start-after-hours), so an existing block can expire
  - checks a file with a single HEAD request (never a throwaway download)
  - one file at a time, PAUSE_S seconds between files, resumes partial files
  - on 429 or a server error: back off 3 h, then 6 h, then 12 h (max), never retry quickly
Finished tiles replace the 2014 fill for that tile automatically (building_heights.py prefers 2024).

Log: data/raw/lpc/download.log. Stop it any time: pkill -f lpc_download.py

Usage: python pipeline/lpc_download.py [--start-after-hours 24]
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime

import requests

from noaa_tides import PROJECT_ROOT

LPC_DIR = PROJECT_ROOT / "data" / "raw" / "lpc"
LOG = LPC_DIR / "download.log"
HEADERS = {"User-Agent": "coastal-flood-forecast-research"}
PAUSE_S = 120
BACKOFF_H = [3, 6, 12]


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def is_las(path) -> bool:
    with open(path, "rb") as f:
        return f.read(4) == b"LASF"


def download(session: requests.Session, url: str) -> str:
    """'done', 'busy' (rate-limited / server trouble) or 'bad' (unexpected content)."""
    name = url.rsplit("/", 1)[1]
    head = session.head(url, allow_redirects=True, timeout=60)
    if head.status_code == 429 or head.status_code >= 500:
        return "busy"
    size = int(head.headers.get("content-length", 0))
    if head.status_code != 200 or size < 1000 or "html" in head.headers.get("content-type", ""):
        return "bad"
    part = LPC_DIR / (name + ".part")
    have = part.stat().st_size if part.exists() else 0
    with session.get(url, stream=True, timeout=300, headers={"Range": f"bytes={have}-"} if have else {}) as r:
        if r.status_code == 429 or r.status_code >= 500:
            return "busy"
        if have and r.status_code != 206:  # server ignored the resume: start over
            part.unlink()
            have = 0
        with open(part, "ab" if have else "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    if part.stat().st_size == size and is_las(part):
        part.rename(LPC_DIR / name)
        return "done"
    return "busy"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-after-hours", type=float, default=0)
    args = ap.parse_args()
    if args.start_after_hours:
        log(f"waiting {args.start_after_hours:g} h before the first request")
        time.sleep(args.start_after_hours * 3600)
    session = requests.Session()
    session.headers.update(HEADERS)
    urls = (LPC_DIR / "urls.txt").read_text().split()
    strikes = 0
    for url in urls:
        name = url.rsplit("/", 1)[1]
        if (LPC_DIR / name).exists() and is_las(LPC_DIR / name):
            continue
        while True:
            try:
                result = download(session, url)
            except requests.RequestException as err:
                result = "busy"
                log(f"{name}: {err.__class__.__name__}")
            if result == "done":
                strikes = 0
                log(f"done {name}")
                break
            if result == "bad":
                log(f"{name}: unexpected response, skipping")
                break
            wait = BACKOFF_H[min(strikes, len(BACKOFF_H) - 1)]
            strikes += 1
            log(f"{name}: server busy (rate limit); next try in {wait} h")
            time.sleep(wait * 3600)
        time.sleep(PAUSE_S)
    have = sum(1 for u in urls if (LPC_DIR / u.rsplit('/', 1)[1]).exists())
    log(f"finished: {have}/{len(urls)} tiles. Next: python pipeline/building_heights.py")


if __name__ == "__main__":
    main()
