# Rain flooding, greater PB + La Jolla: evidence so far

Hand-kept summary. The numbers come from generated files in this folder:
- `ponding_spots.md`: the spots
- `ponding_check.md`: the fair test

## Piece 2: ponding spots (2026-11-16)
- **Ground:** 2024 USGS lidar, 1 m.
- **Method:** priority-flood fill plus drainage areas.
- **Result:** 288 street ponding spots in La Jolla, Pacific Beach and Mission Beach.
- **Excluded:** canyons behind roads (culverts the lidar can't see), driveways, parking aisles, bridges.

## Piece 3: do real reports land at the spots? (2026-11-16)
**Data:**
- City Get It Done "street flooded" reports, 2017–2026.
- Each report is tagged **rain-day** if the airport recorded at least 0.1 in that day or the day before.
- **Dry-day** reports (water-main breaks, sprinklers) serve as a control.

**Test:** what share of reports fall within 50 m of a street ponding spot, compared with random points on the same streets.

| | Reports | Near a spot | Chance | Lift |
|---|---|---|---|---|
| Rain-day, all three | 271 | 48% | 16% | 3.1× |
| Dry-day (control) | 895 | 24% | 16% | 1.5× |
| Pacific Beach, rain-day | 98 | 48% | 13% | **3.6×** |
| Mission Beach, rain-day | 85 | 92% | 82% | 1.1× (spots cover almost the whole peninsula) |
| La Jolla, rain-day | 88 | 7% | 12% | **0.6×** |

### What it means
**Pacific Beach: the ground map finds real trouble spots.**
- Top repeat spots: Oliver/Reed Ave and Dawes St / Pacific Beach Dr.
- An NWS employee measured 7 in of water at Ingraham St & La Playa Ave on Mar 1, 2014. That is next to the La Playa Ave / Jewell St spot.

**Mission Beach: rain floods streets all over the low peninsula.**
- Many reports cluster on Bayside Ln and the "Place" streets (San Gabriel, San Juan, San Luis Rey).
- The useful answer here is per area, not per spot.

**La Jolla: the ground map does not predict where.** Rain-day reports there are scattered and mixed:
- hillside runoff and mud (e.g. Bonair St, Torrey Pines Rd mudslide)
- groundwater seeping up through cracks on Mt Soledad streets
- clogged or backed-up drains
- a few spots of true standing water (La Jolla Hermosa Ave, Vallecitos, Paseo del Ocaso)

A runoff test didn't help either: La Jolla's rain-day reports sit on high-runoff streets no more often than its dry-day reports do.

**NWS storm reports:** only 8 in the neighborhoods, with coordinates rounded to about 1 km. They are useful for dates and descriptions, not for exact places.

**Limits:**
- Report locations are where people chose to report (often a house address), not exactly where the water stood.
- Some rain-day reports are coincidences: a water main can break on a rainy day.

## Map spots (hybrid, 2026-11-16, `rain_spots.py`)
- **Ground spots:** Pacific Beach and Mission Beach only, the neighborhoods where they passed the test.
- **Repeat-report spots:** all three neighborhoods. A spot needs flood reports on 2+ rainy days within 75 m. Reports that mention a water main, leak or sprinkler are dropped.
- **Counts:**
  - Pacific Beach: 90 ground, 4 reports, 3 both
  - Mission Beach: 34 ground, 4 reports, 8 both
  - La Jolla: 10 reports
- **Privacy:** spots show street names only.

## Piece 4: rain rating scale (2026-11-16, `rain_thresholds.py`, `risk.rain_level`)
- **Measure:** the heaviest 6 hours of rain at the airport, which the NWS forecast can supply.
- **Scale:** Low < 0.25 in, Minor 0.25–0.75, Moderate 0.75–1.5, Major ≥ 1.5.
- **Result:** the share of storms with flood reports rises steadily with this measure in all three neighborhoods. Details are in `rain_thresholds.md`.
- **How often:** Moderate about 2 storms a year; Major about 1 every 3 years (Dec 2018, Jan 22 2024, Dec 31 2025).

