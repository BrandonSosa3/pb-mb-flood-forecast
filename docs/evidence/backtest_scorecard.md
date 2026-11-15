# Backtest score card (in progress)

Each row is a past day, run through the model with the data that existed for that day
(measured NOAA tides, CDIP MOP wave archive) and compared with what really happened.
Last updated 2026-11-14.

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

## Area ratings (approved scale, pipeline/risk.py)

Levels Low / Minor / Moderate / Major; an area takes the worse of its bay side and ocean side.
Bay side headline assumes the City's sand berms along Bayside Walk **hold** (modeled top 9.0 ft
MLLW, an assumption); the second rating is **if the berm fails** (no-berm model). With the berm
holding, properties lower than the water count as storm-drain risk (≥ 25 → at least Minor).

| Day | Mission Beach | Pacific Beach | Crown Point | Reality |
|---|---|---|---|---|
| Fri Jan 6, 2023 | 🔴 Major (waves) | 🟡 Minor | 🟢 Low | MB boardwalk flooded ✅ |
| Thu Dec 28, 2023 | 🟡 Minor (waves) | 🟢 Low | 🟢 Low | flooding began? (day unconfirmed) |
| Fri Dec 29, 2023 | 🟠 Moderate (waves) | 🟡 Minor | 🟢 Low | boardwalk flooding (day unconfirmed) |
| Sat Dec 30, 2023 | 🔴 Major (waves) | 🟡 Minor | 🟢 Low | boardwalk flooding (day unconfirmed) |
| Thu Jan 4, 2024 | 🟢 Low | 🟢 Low | 🟢 Low | no flooding found ✅ |
| Sun Oct 25, 2026 | 🟡 Minor · Major if berm fails | 🟡 Minor · Moderate if berm fails | 🟢 Low | ❌ corrected 2026-11-14: berm leaked, bay water into Mission Beach yards/homes ~8:30 am ([10News, Oct 26](https://www.10news.com/news/local-news/coastal-flood-warning-hits-san-diego-as-high-tides-send-bay-water-into-mission-beach-yards)); Dawes St flooded to PB Dr (NWS storm report) |
| Mon Oct 26, 2026 | 🟡 Minor · **Major if berm fails** | 🟡 Minor · Moderate if berm fails | 🟢 Low | berm broke → major flooding ✅ (flagged in the berm-fails rating) |
| Tue–Wed Oct 27–28, 2026 | 🟡 Minor · Major if berm fails | 🟡 Minor · Moderate if berm fails | 🟢 Low | rebuilt berm held; some street water (MB, PB) ✅ |

Forecast for Sat Nov 14, 2026 (frozen snapshot 2026-11-13T2241Z): Mission Beach 🟡 Minor (NOAA-driven
waves) / 🟠 Moderate (ECMWF-driven), Pacific Beach 🟡 Minor, Crown Point 🟢 Low.
**Result: ocean side MISSED (under-predicted).** Water splashed over and pooled on the boardwalk at
San Rafael / Santa Rita Pl 11:00-11:45 am (eyewitness); we said "close to the top, not over". Still
water was right (6.31 vs 6.34 ft); the NOAA-driven waves ran low. Bay side right (berm held).
Details: `prediction_2026-11-14.md`.

Lessons:
- Without a berm, every day above ~7.4 ft read Major for Mission Beach (3 over-warnings in Oct 2026).
  The berm-holds headline + berm-fails second rating fixes that while still flagging Oct 26.
- Whether a sand berm breaches can't be forecast from water levels alone; that's why it's shown as
  a scenario, not hidden.

## Batch 2: 35 more days (2026-11-14)
Chosen without looking at the model: every NWS Coastal Flood Advisory/Warning for the San Diego coast
since 2021, NWS storm reports near PB/MB (reports citing Surfline left out), rain-rule days with a
report, two summer 2026 news events, and controls (highest 2021-2025 tides with no NWS alert).
Run with `pipeline/backtest_days.py` (measured tides, CDIP hindcast/nowcast waves, airport rain);
every day and area: `backtest_days_model.csv`. "Perfect forecast" test: checks the flood model and
thresholds, not the weather and wave forecasts.

### Days with evidence
| Day | What happened | Model (headline · if berm fails) | Score |
|---|---|---|---|
| Tue Jul 14, 2026 (night) | King tide: water over both Mission Beach walkways, alleys and underground garages; City doesn't build sand berms in summer ([10News, Jul 15](https://www.10news.com/news/local-news/mission-beach-flooding-king-tides-flood-alleyway-and-underground-parking)) | MB 🟡 Minor · 🔴 Major (924 properties); bay 7.77 ft | ❌ Missed by the headline (it assumed a berm that wasn't there); ✅ "if the berm fails" right |
| Tue Aug 11, 2026 (night) | Homes and cars around Mission Bay surrounded by water ([Times of San Diego, Aug 13](https://timesofsandiego.com/newsletter/flooding-from-king-tides/)) | MB 🟡 Minor · 🔴 Major (624); bay 7.54 ft | ❌ Missed by the headline; ✅ "if the berm fails" right |
| Sun Oct 11, 2026 | PB bayside neighborhood near Pacific Beach Dr flooded after the morning high tide (NWS storm report) | PB 🟡 Minor (storm drains) · 🟠 Moderate; bay 7.53 ft | 🟠 Close (right place, under-stated) |
| Sun Oct 25, 2026 | Berm leaked: bay water into Mission Beach yards/homes; Dawes St flooded (see above) | MB 🟡 Minor · 🔴 Major; PB 🟡 Minor | ❌ Missed by the headline (MB); 🟠 close (PB) |
| Sat–Sun Nov 7–8, 2026 | City had enlarged the berm; no new flooding reported ([10News, Nov 8](https://www.10news.com/news/local-news/mission-beach-residents-brace-for-high-tides-again-with-another-coastal-flood-advisory-in-effect-in-san-diego)) | MB 🟡 Minor (storm drains); bay 7.5 ft | ✅ Right (weak: no reports) |
| Sat Jan 21, 2023 | King tides ~7 ft: Kendall-Frost marsh underwater; no street flooding named ([10News, Jan 21](https://www.10news.com/news/local-news/king-tides-engulf-mission-bay-marsh-flood-parts-of-san-diego)) | MB 🟡 Minor (storm drains); bay 7.07 ft | ✅ Right (weak) |
| Sun Dec 22, 2024 | NWS storm report: social media video of water washing onto the Mission Beach boardwalk; 8-12 ft surf (Dec 22-23) | 🟢 Low: 11 ft waves but only a 4.2 ft tide; closest stretch 3.0 ft below the top | ❌ Missed (ocean, under-predicted) |
| Thu–Fri Apr 9–10, 2020 | NWS storm report Apr 10 ~8:30 am: flash flooding 1 mi ESE of Mission Beach, water above tires (1.8 in rain) | Apr 9: MB 🟠 Moderate (rain near the 10:54 pm high tide, 1.03 in) | 🟠 Close (flagged the night before) |
| Thu Nov 29, 2018 | NWS storm report: minor street flooding near Mission Bay, evening rain | 🟢 Low (0.22 in rain, low 5.2 ft tide) | ❌ Missed (rain away from high tide: not modeled) |

### Days with no evidence either way (not scored)
Model ran on: Jan 18 2019 (MB Moderate, 17 stretches reach the top; 15 ft sets), Jan 11-12 2021,
Jan 14 2023, Jan 11-12 & 21-22 2024, Feb 20 2024 (13 reach), Dec 23-24 2024 (Dec 24: 14 reach),
Feb 2 2026, Jul 31, Aug 12, Sep 7, Sep 29, Oct 8-10 2026, and the controls Aug 11 2022, Jul 31 &
Aug 1 2023, Dec 5 2025 (bay 7.4-7.7 ft: headline Minor, "if the berm fails" Major). No news or NWS
report found for these, which doesn't prove nothing happened (a Mission Beach contractor told 10News
water "comes over both walkways" on every king tide above ~7.2). Searched: NWS storm reports, news.

### What batch 2 teaches
1. **The berm assumption is the biggest error.** The headline assumes the bay-side berm holds, but
   (a) the City doesn't build it in summer (Jul 14, Aug 11 2026 flooded, headline said Minor), and
   (b) it leaked or broke at ~7.9-8.1 ft (Oct 25, 26) and held at 8.1-8.2 ft only after being
   enlarged (Oct 27-28). The "if the berm fails" rating was right every time it mattered.
2. **Ocean side under-predicts again** (Dec 22 2024 at 3.0 ft below the top; Nov 14 2026). Same
   lesson as batch 1.
3. **Rain rule:** one close call (Apr 2020); rain away from high tide is outside the model (Nov 2018).
4. **Calibration still to do (step 2):** fixes proposed to Brandon; not applied yet.

## Rain rule (added 2026-11-14)
Rule: ≥ 0.25 in of rain within 3 h of the day's highest tide, with 10+ properties below the water →
rating up one level (max Moderate). History check (`rain_near_high_tide.md`): fires ~1.1 times a
year since 2000 (32 days), including Jan 22, 2024 (2.35 in near a 6.3 ft tide; Pacific Beach water
rescues from stuck cars: https://timesofsandiego.com/life/2024/01/22/widespread-heavy-rain-prompts-flash-flood-warning-for-coast-and-valleys/,
https://www.axios.com/local/san-diego/2024/01/23/historic-rain-flood-sd). Mechanism: the City closes
Mission Beach storm drains before high tide because they empty into the ocean
(https://www.10news.com/news/local-news/mission-beach-flooding-king-tides-flood-alleyway-and-underground-parking).
Not yet checked street by street for the other 31 days.

## Still to add
- Feb 2023 and other king-tide days (bay side), more near-miss days with no flooding.
- NWS Local Storm Reports as an independent, location-specific source.
