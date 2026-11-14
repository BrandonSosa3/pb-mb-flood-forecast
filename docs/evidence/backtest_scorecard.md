# Backtest score card (in progress)

Each row is a past day, run through the model with the data that existed for that day
(measured NOAA tides, CDIP MOP wave archive) and compared with what really happened.
Last updated 2026-11-13.

## Ocean side (wave run-up vs. boardwalk / beach ridge)

53 beach stretches of ~100 m, Mission Beach jetty to north Pacific Beach. Worst hour of the day.
"Over" = run-up water level above the ridge top; "reaches" = within 2 ft of the top.

| Day | What happened | Model | Score |
|---|---|---|---|
| Fri Jan 6, 2023 | Mission Beach boardwalk "covered in seawater" ([NBC 7](https://www.nbcsandiego.com/news/local/cleanup-begins-in-mission-beach-after-boardwalk-hit-with-high-waves/3137277/)) | 3 over, 22 reach (6–8 am) | ✅ Hit |
| Thu Dec 28 – Sat Dec 30, 2023 | Boardwalk underwater in MB and PB; water into streets and yards; cleanup Mission Beach → PB lifeguard tower ([NBC 7](https://www.nbcsandiego.com/news/local/cleanup-efforts-in-mission-beach-pacific-beach-after-high-surf/3397736/), [KPBS](https://www.kpbs.org/news/public-safety/2023/12/28/high-surf-flood-advisory-in-effect-at-san-diego-county-beaches)) | Thu 28: 0 over, 4 reach · Fri 29: 0 over, 17 reach · **Sat 30: 5 over, 22 reach** | ✅ Hit for the event; ⚠️ exact flooding day not confirmed (if Thu 28 was the worst, the model was a day late) |
| Thu Jan 4, 2024 | Second big swell (~10 ft at 10 m depth) near **low tide**; no boardwalk flooding found ([KPBS](https://www.kpbs.org/news/environment/2024/01/04/another-big-wave-event-slams-san-diego-coast)) | 0 over, 0 reach | ✅ Correct "no" (weak: absence of reports) |
| Sun Oct 25 – Wed Oct 28, 2026 | Small surf (~2.5 ft); all flooding was bay-side | 0 over, 1 reach | ✅ Correct "no" |

Chart: `figures/runup_backtest.png`.

### What we learned
- The model separates flood days from non-flood days cleanly: on flood days most of Mission Beach
  came within 2 ft of the top; on non-flood days everything stayed 2–9 ft below.
- **The model under-states extent.** Reality on flood days was "much of the boardwalk a river";
  the model puts only 3–5 stretches *over* the top, with ~22 *reaching* it. In practice
  "reaches" (within 2 ft) already meant water on the boardwalk. Likely reasons:
  - R2 is the level only the top 2% of waves reach, but a few minutes of those is enough to
    flood the walk;
  - the beach ridge in winter 2023 may have been lower than in the Nov 2024 lidar (winter erosion);
  - Stockdon (2006) was fit on natural beaches, not seawalls/boardwalk edges.
  → For the public status, "waves reach the top" should be presented as **"water likely on the
  boardwalk"**, not as a near-miss. Revisit after more events (don't over-fit to two days).
- Big waves alone aren't enough: Jan 4, 2024 had near-flood-day surf but peaked at low tide.

## Bay side (still water, connected flood model, no berm)

| Day | Mission Bay level (est.) | What happened | Model | Score |
|---|---|---|---|---|
| Mon Oct 26, 2026 | 8.12 ft | Berm broke; flooding Belmont Park → Catamaran, Mission Blvd & N Jetty Rd, side streets, Pacific Beach Dr | Bay side of Mission Beach reached (1,122 buildings, 9.2 mi road covered) | ✅ Hit (extent likely over-stated: static model) |
| Wed Oct 28, 2026 | 8.10 ft | Briarfield Dr (PB) flooded | Reached at 8.40 ft; nearby ground 5.9 ft (storm drains) | 🟠 Near miss |
| Tue–Wed Oct 27–28, 2026 | 8.16 / 8.10 ft | Rebuilt berm held; Mission Beach mostly dry | Model has no berm → over-predicts | ⏳ Needs berm option |

Details: `docs/evidence/2026-10_king_tides.md`.

## Area ratings (proposed scale, pipeline/risk.py)

Levels Low / Minor / Moderate / Major; an area takes the worse of its bay side and ocean side.
Peak day of each event:

| Day | Mission Beach | Pacific Beach | Crown Point | Reality |
|---|---|---|---|---|
| Fri Jan 6, 2023 | 🔴 Major (waves) | 🟡 Minor | 🟢 Low | MB boardwalk flooded ✅ |
| Thu Dec 28, 2023 | 🟡 Minor (waves) | 🟢 Low | 🟢 Low | flooding began? (day unconfirmed) |
| Fri Dec 29, 2023 | 🟠 Moderate (waves) | 🟡 Minor | 🟢 Low | boardwalk flooding (day unconfirmed) |
| Sat Dec 30, 2023 | 🔴 Major (waves) | 🟡 Minor | 🟢 Low | boardwalk flooding (day unconfirmed) |
| Thu Jan 4, 2024 | 🟢 Low | 🟢 Low | 🟢 Low | no flooding found ✅ |
| Sun Oct 25, 2026 | 🔴 Major (bay) | 🟠 Moderate | 🟡 Minor | berm likely held → ❌ over-warning (model has no berm) |
| Mon Oct 26, 2026 | 🔴 Major (bay) | 🟠 Moderate | 🟡 Minor | berm broke, major bay-side flooding ✅ |
| Tue–Wed Oct 27–28, 2026 | 🔴 Major (bay) | 🟠 Moderate | 🟡 Minor | rebuilt berm held in MB ❌ (no berm); PB streets flooded ✅ |

Forecast for Sat Nov 14, 2026 (frozen snapshot 2026-11-13T2241Z): Mission Beach 🟡 Minor (NOAA-driven
waves) / 🟠 Moderate (ECMWF-driven), Pacific Beach 🟡 Minor, Crown Point 🟢 Low.

Lesson: the bay side needs a **berm option** (Mission Beach's winter sand berm along Bayside Walk);
without it, every day above ~7.4 ft reads Major for Mission Beach even when the berm holds.

## Still to add
- Feb 2023 and other king-tide days (bay side), more near-miss days with no flooding.
- NWS Local Storm Reports as an independent, location-specific source.
- Result of the logged prediction for Sat Nov 14, 2026 (`docs/evidence/prediction_2026-11-14.md`).
