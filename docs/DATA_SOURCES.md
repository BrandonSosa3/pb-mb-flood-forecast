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

### USGS 3DEP 1 m lidar DEM, project CA_SanDiegoCo_D24
- Source: https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/CA_SanDiegoCo_D24/
  (tiles x47y363, x47y364), found via the USGS TNM API. Metadata:
  https://www.sciencebase.gov/catalog/item/6aa9fadb1ba49b23655bd480
- Lidar flown 2024-11-08 to 2024-12-01; published 2026-09-14. Bare earth, 1 m cells,
  NAD83 / UTM 11N (EPSG:26911), vertical NAVD88 meters (converted to feet).
- Downloaded 2026-11-13 by `pipeline/dem_prepare.py`. Outputs (not in git, rebuilt by
  the script): `data/processed/dem_pbmb_navd88_ft.tif`, `data/processed/water_mask_pbmb.tif`.
- Mission Bay is hydro-flattened at 2.198 ft NAVD88; the ocean is no-data.

### NOAA tidal datums (for NAVD88 <-> MLLW conversion)
- Source: https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/<id>/datums.json
- Epoch 1983-2001. NAVD88 is 0.19 ft above MLLW at La Jolla 9410230, 0.43 ft above
  MLLW at San Diego 9410170. Retrieved 2026-11-13.

### OpenStreetMap buildings and streets
- Source: OpenStreetMap contributors (ODbL, https://www.openstreetmap.org/copyright), via the
  Overpass API (https://overpass-api.de/api/interpreter). Box S 32.752, W -117.262, N 32.810, E -117.222.
- Downloaded 2026-11-13 by `pipeline/osm_download.py`: 12,762 buildings, 4,489 street/walkway ways.
- Privacy: only building shape + type kept; addresses and all other building tags dropped.
- Outputs: `data/processed/osm_buildings.geojson`, `osm_ways.geojson`, and (with danger heights)
  `buildings_danger.geojson`, `street_pieces_danger.geojson`.

### OpenStreetMap addresses (search only)
- Source: OpenStreetMap contributors (ODbL), Overpass API, all features with `addr:housenumber` +
  `addr:street` in S 32.7585, W -117.2700, N 32.8120, E -117.2285.
- Downloaded 2026-11-14 by `pipeline/search_index.py` (8,049 addresses inside the three areas).
- Privacy: only house number + street + location kept; used for the search box, never drawn on the map.
- Output: `web/public/data/search.json` (+ `data/processed/search_index.meta.json`).
