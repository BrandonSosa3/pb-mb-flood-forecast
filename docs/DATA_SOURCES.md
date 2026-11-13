# Data sources

Every dataset used in this project: where it came from and when we downloaded it.

| Dataset | Source (URL) | What it contains | Date downloaded |
|---|---|---|---|
| NOAA water levels, San Diego 9410170, 2026-09-29 to 2026-11-13 | https://api.tidesandcurrents.noaa.gov/api/prod/datagetter (products `water_level`, `predictions`; datum MLLW; feet; 6-min) | Measured and predicted water level; most readings preliminary (`p`), 480 verified (`v`) | 2026-11-13 |

Each processed CSV in `data/processed/` has a matching `.meta.json` file with the exact
request, download time, and data-quality counts. Recent NOAA data is *preliminary*
and may be revised slightly once NOAA verifies it; re-download before final results.

## Dataset details

### NOAA hourly history, San Diego 9410170, 1980-01-01 to 2026-11-13
- Source: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
- Products: `hourly_height` (verified, through 2026-09-30), `water_level` 6-min
  preliminary data for 2026-10-01 onward (top-of-hour readings), `predictions` (interval=h).
- Datum MLLW, feet, UTC. Downloaded 2026-11-13 by `pipeline/noaa_history.py`.
- Outputs: `data/processed/hourly_extra_water_9410170.csv.gz`,
  `data/processed/monthly_extra_water_9410170.csv` (+ `.meta.json`).
- Baseline: straight-line trend of monthly extra water, fitted excluding the
  1982-83, 1997-98, 2015-16 and 2026-27 El Nino winters (+0.09 ft/decade).

### NOAA hourly history, La Jolla 9410230, 1980-01-01 to 2026-11-13
- Same source, products, and processing as the San Diego history above.
  Downloaded 2026-11-13 by `pipeline/noaa_history.py --station 9410230`.
- Outputs: `data/processed/hourly_extra_water_9410230.csv.gz`,
  `data/processed/monthly_extra_water_9410230.csv` (+ `.meta.json`).
- Baseline trend: +0.05 ft/decade. Two months missing (gauge outages).
