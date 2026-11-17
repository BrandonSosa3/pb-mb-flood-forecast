# Forecasting street-level flooding in Pacific Beach, Mission Beach and La Jolla: method, accuracy, limits

*November 2026. Live site: https://pb-mb-flood-forecast.vercel.app*

## 1. The question
This winter, El Niño and a Kelvin wave held San Diego's sea level more than a foot above normal:
- **Oct–Nov 2026 averaged +1.1 to +1.2 ft** of "extra water" (measured minus predicted tide). That is about twice
  any month since 1980, including the 1997–98 and 2015–16 El Niños.
- **Oct 27, 2026** was the highest hour on record at both the San Diego and La Jolla gauges.
- **Oct 26, 2026:** the bay-side sand berm along Bayside Walk broke, and bay water reached Mission Beach yards and homes.

Residents need a short-term answer: **will water reach my street this week, when, and from which side?**
The project gives a 3-day forecast per area (Low / Minor / Moderate / Major), a map down to each street and
building, and a public record of every forecast checked against what happened.

## 2. Method
**Total water level = predicted tide + extra water + wave run-up** (run-up on the ocean side only).

1. **Tide and extra water.** NOAA CO-OPS predictions for La Jolla (ocean), San Diego and Mission Bay (bay).
   Extra water is the 25-hour average of measured minus predicted at La Jolla. The forecast holds it constant
   ("persistence"). Mission Bay has no live gauge, so its level = the Mission Bay prediction + La Jolla's extra water.
2. **Ground and connectivity.** USGS 3DEP 2024 lidar at 1 m resolution. For every cell, a flood fill (morphological
   reconstruction) finds the lowest bay level at which water can actually *flow* there. Isolated low dips stay dry
   unless water can connect to them. Each building gets the lowest such level within 2 m of it. Streets are split
   into 25 m pieces.
3. **The bay-side berm.** The City builds a temporary sand berm in winter, and its height isn't published (we assume 9.0 ft MLLW).
   The headline rating assumes the berm holds when it is up (a hand-kept file of news reports, defaulting to Oct–Apr),
   except at **≥ 7.8 ft**, where it leaked or broke on 2 of the 4 days that high (then the rating is at least Moderate).
   A second rating always shows "if the berm fails."
4. **Waves.** Scripps CDIP MOP nearshore forecasts (WaveWatch III-driven and ECMWF-driven) every ~100 m of beach.
   **Stockdon et al. (2006) R2%** run-up uses the beach slope and the boardwalk or seawall crest measured from lidar.
   The margin is the crest minus the total water level: "reaches the top" means within 2 ft; "over" means above it.
   Because the NOAA-driven model ran low (below), the site uses the higher of the two models each hour.
5. **Rain (added after Phase 2).**
   - *Coast:* rain within 3 h of high tide, while drain outlets are underwater, raises the rating one level.
   - *Greater PB + La Jolla:*
     - **Ponding spots** come from a priority-flood fill (Barnes et al. 2014) of the 1 m ground over 76 million
       land cells, with drainage areas from D8 flow routing (custom numba code, about 3 minutes in 8 GB of RAM).
     - **The rain rating** uses the heaviest 6 hours of NWS forecast rain per neighborhood. The 6-hour measure
       matches the NWS forecast's own time blocks.
     - **Thresholds** come from 141 storms since 2018 compared with City Get It Done flood reports:
       Low < 0.25 in, Minor < 0.75, Moderate < 1.5, Major ≥ 1.5.
6. **Ratings.** Each area takes the worse of its bay and ocean sides:
   - **Bay:** properties reached, road covered, or properties below the water (where storm drains may back up).
   - **Ocean:** stretches of beach where waves reach or go over the top.

   All thresholds are in `pipeline/risk.py`, with the date and evidence for each. The bay and ocean scale was set
   before the backtest. The berm and rain thresholds were learned from past events, so days used to tune them are
   not counted as wins.

**Architecture:**
- **Pipeline:** Python (pandas, rasterio, GeoPandas, xarray, numba) writes static JSON and GeoJSON files.
- **Website:** React + MapLibre GL, with 3D building extrusions and a water surface that rises with a slider.
  It is hosted on Vercel.
- **Forecast log:** GitHub Actions saves every forecast twice a day *before* the event, to `forecast_log/`.
- **Automatic scoring (since Nov 17, 2026):** every day, `auto_verify.py` compares each published forecast with
  evidence collected without a human: airport rain, Mission Bay level, City Get It Done flood reports, NWS storm
  reports and local news RSS. Fixed rules turn that evidence into an observed level (e.g. 1 City report in a
  neighborhood → Minor, 3 → Moderate, 6 → Major). Scores stay preliminary for 3 days. Coast days with no reports
  either way are left unscored, because water on the boardwalk is rarely reported.

## 3. Accuracy
**Backtest and live forecasts: 18 scored days.** Evidence: news, NWS storm reports, eyewitness photos.

| | Right | Close | Missed |
|---|---|---|---|
| Bay side | 5 | 3 | 4 |
| Ocean side | 4 | 0 | 2 |

What the misses taught:
- **The berm assumption caused most of the bay-side misses.**
  - Summer king tides (Jul 14 and Aug 11, 2026) flooded while the model assumed a berm the City hadn't built.
  - Oct 25, 2026: the berm leaked at about 7.9 ft.
  - The "if the berm fails" rating was right every time.
  - The fixes (berm season, leak level) were tuned on these same days, so the track record still counts those days as misses.
- **The ocean side under-predicts.** On Nov 14, 2026 (live forecast, checked in person) and Dec 22, 2024, water reached
  the boardwalk while the model said the waves would stay 2–3 ft below the top. This will be recalibrated after the
  December king tides.
- **The wave forecasts were checked** against the CDIP nowcast (15,708 matched point-hours, Nov 13–15).
  - The ECMWF-driven model averaged **103%** of actual height.
  - The NOAA-driven model averaged **70%**.

  Hence the "higher of the two" rule.
- **Rain spots** were checked with a fair test against random points on the same streets:
  - Rain-day "street flooded" reports fall within 50 m of a ponding spot **3.1× more often than chance** overall,
    and **3.6×** in Pacific Beach.
  - Dry-day reports (water mains, a control) show only 1.5×.
  - **La Jolla fails** (0.6×). Its rain trouble is hillside runoff, mud and clogged drains, so there the map shows
    only places with repeat reports.

## 4. Limits
- **Not an official warning.** The NWS issues those.
- **Floor heights are unknown.** "Water reaches this property" refers to the ground next to it.
- **Static flood fill.** Water spreads instantly, so a short high tide may not get as far as shown.
- **Storm drains and the berm's real height aren't public.** Ratings for drain backup and berm failure are therefore
  flags, not simulations.
- **Run-up is a 2% exceedance estimate** for each ~100 m stretch. Beaches change after the Nov 2024 lidar.
- **Rain:** one airport gauge for history. Flood reports undercount flooding. The NWS forecast can't see a single
  heavy hour.
- **Few events so far.** The record grows with every king tide and storm; December 2026 is the next big test.

## 5. How this differs from existing tools
| | This project | USGS CoSMoS / NOAA SLR Viewer | NWS coastal flood products |
|---|---|---|---|
| Time frame | Next 3 days, updated twice a day | Long-term scenarios (sea-level rise + design storms) | Hours to days |
| Detail | Each street piece and building | Scenario flood extents | Coastal zones |
| Bay-side berm, rain | Modeled (with "if it fails") | No | Mentioned in text |
| Verification | Every forecast logged before the event and scored publicly | n/a | Internal |

## 6. Data
- NOAA CO-OPS
- Scripps CDIP MOP
- USGS 3DEP lidar (2024; gaps filled from 2014)
- NWS (forecasts, alerts, Surf Zone Forecast, storm reports via the Iowa Environmental Mesonet)
- City of San Diego open data
- OpenStreetMap

Every dataset's source and download date is listed in `docs/DATA_SOURCES.md`.
