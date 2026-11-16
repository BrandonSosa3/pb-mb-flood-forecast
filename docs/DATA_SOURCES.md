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
- Known gap: the 2024 tiles have no data for 64 ha of east Pacific Beach (about Ingraham St to
  Mission Bay Dr, Grand Ave to Felspar St, incl. part of the Rose Creek channel) and two smaller
  patches near UTC / La Jolla Village Dr. Found 2026-11-16; both grids are now gap-filled from
  2014 (below). Phase 2 re-run the same day: the 543 buildings in the gap all sit at 14.7 ft+
  (bay danger), so area totals, ratings and the 3D water were unchanged.
- Rain area (added 2026-11-16, `dem_prepare.py --area rain`): Mission Beach jetty to La Jolla
  Shores, ocean to I-5 (-117.290..-117.200, 32.752..32.880), tiles x47y363, x47y364, x48y363,
  x48y364, cut on the tiles' own 1 m grid. Outputs (not in git): `dem_rain_navd88_ft.tif`,
  `water_mask_rain.tif`, `dem_rain_filled_cells.tif` (1 = gap-filled cell).

### USGS 3DEP 1 m lidar DEM, project San_Diego_CA_2014_LiDAR (gap fill only)
- Source: https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/San_Diego_CA_2014_LiDAR/
  (tiles x47y363, x47y364, x48y364). Metadata: https://www.sciencebase.gov/catalog/item/662c86edd34ea70bd5f126b3
- Lidar flown 2014; same grid and datum as the 2024 tiles. Downloaded 2026-11-16.
- Used only inside the 2024 gaps (59 ha filled in the rain grid, 57 ha in the pbmb grid; +0.25 ft), raised by the median
  2024 - 2014 difference on land within 150 m of each gap (+0.22, +0.32, +0.33 ft).

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

## NWS weather forecast + airport observations (forecast logger, from 2026-11-14)
- **Forecast:** National Weather Service hourly forecast grid, office SGX cell 54,17
  (covers Mission Beach / south Pacific Beach): https://api.weather.gov/gridpoints/SGX/54,17
  Saved every logger run (next 4 days): rain amount (in/hour; NWS gives totals per
  multi-hour span, split evenly), chance of rain, wind, gusts, wind direction.
- **Observed:** San Diego airport station KSAN, last 2 days each run:
  https://api.weather.gov/stations/KSAN/observations (rain is reported on the hourly
  reports only; pressure in hPa).
- **Why:** rain during a high tide can't drain (storm-drain outlets are underwater), and
  strong onshore wind pushes water up. First logged 2026-11-14; public domain (NWS).

## Hourly rain history, San Diego airport (rain rule check)
- Iowa Environmental Mesonet ASOS archive, station KSAN, routine hourly METAR precipitation
  (p01i, inches; trace counted as 0), 2000-01-01 to 2026-11-14. Downloaded 2026-11-14 by
  `pipeline/rain_history.py` -> `data/processed/hourly_rain_KSAN.csv.gz` (wet hours only) + meta.
  https://mesonet.agron.iastate.edu/request/download.phtml
- Used to check how often the rain-near-high-tide rule fires (docs/evidence/rain_near_high_tide.md).

## USGS lidar point cloud, 2024 (building heights for the 3D view)
- USGS 3DEP Lidar Point Cloud, project CA_SanDiegoCo_D24 (flown Nov 8 - Dec 1, 2024; published
  Sep 2026), LAZ tiles from https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_SanDiegoCo_D24/
  (tile list from the TNM Access API, saved in data/raw/lpc/urls.txt). Downloaded 2026-11-14.
  Public domain. Raw tiles (~1.7 GB) stay in data/raw (not committed).
- `pipeline/building_heights.py`: roof = 75th percentile of unclassified first returns inside each
  OSM outline (shrunk 0.5 m); ground = median bare-earth DEM under it. Display only.

## Derived files for the 3D view (no new downloads)
- `pipeline/water_bands.py` -> web/public/data/water_bands.geojson: bay flood shapes in 0.1 ft bands
  (6.0-9.5 ft MLLW), berm holds / fails, from the existing connected-flood rasters.
- `pipeline/events_3d.py` -> web/public/data/events.json: Mission Bay level every 20 min for the
  Oct 26 and Oct 27, 2026 high tides (NOAA 9410196 prediction + La Jolla measured extra water).
