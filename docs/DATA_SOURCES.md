# Data sources

Every dataset used in this project: where it came from and when we downloaded it.

| Dataset | Source (URL) | What it contains | Date downloaded |
|---|---|---|---|
| NOAA water levels, San Diego 9410170, 2026-09-29 to 2026-11-13 | https://api.tidesandcurrents.noaa.gov/api/prod/datagetter (products `water_level`, `predictions`; datum MLLW; feet; 6-min) | Measured and predicted water level; most readings preliminary (`p`), 480 verified (`v`) | 2026-11-13 |

Each processed CSV in `data/processed/` has a matching `.meta.json` file with the exact
request, download time, and data-quality counts. Recent NOAA data is *preliminary*
and may be revised slightly once NOAA verifies it; re-download before final results.
