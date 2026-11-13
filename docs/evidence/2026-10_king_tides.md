# Evidence: late-October 2026 king tide flooding

Real-world reports used to test the flood model. Collected 2026-11-13 via web search.
We link to sources rather than copying their photos.

## Water levels (computed by us from NOAA data)

| Date | Mission Bay predicted peak (NOAA 9410196) | Extra water (La Jolla 9410230, at peak) | Estimated Mission Bay peak |
|---|---|---|---|
| Sun Oct 25 | 6.38 ft @ 08:48 | +1.53 ft | **7.91 ft MLLW** |
| Mon Oct 26 | 6.66 ft @ 09:18 | +1.45 ft | **8.12 ft MLLW** |
| Tue Oct 27 | 6.79 ft @ 09:48 | +1.37 ft | **8.16 ft MLLW** |
| Wed Oct 28 | 6.73 ft @ 10:24 | +1.37 ft | **8.10 ft MLLW** |
| Thu Oct 29 | 6.48 ft @ 11:12 | +1.33 ft | **7.81 ft MLLW** |

(San Diego Bay's Broadway gauge peaked at 8.52 ft on Oct 27; San Diego Bay has larger tides than Mission Bay.)

## Reports

| Date | Where | What happened | Source | Model (bay side, no berm, still water) |
|---|---|---|---|---|
| Mon Oct 26 | Bayside Walk, Mission Beach | City sand berm broke; bay water flooded yards (Mission Bay Puppy Rescue) | [Times of San Diego](https://timesofsandiego.com/weather/2026/10/27/mission-bay-flooding-continues-raising-concerns-about-winter-storms-during-the-holidays/) | ✅ Bay side of Mission Beach reached from ~7.4 ft; Oct 26 ≈ 8.12 ft |
| Mon Oct 26 | Mission Beach, Belmont Park → Catamaran Hotel | Streets and homes flooded; water through a resident's sliding door | [FOX 5](https://fox5sandiego.com/news/local-news/mission-bay-flooding-high-tide/), [10News](https://www.10news.com/news/local-news/major-coastal-flooding-hits-mission-beach), [CBS 8](https://www.cbs8.com/video/news/local/mission-beach-flooded-as-high-tides-batters-the-coast/509-d721e3af-69ca-4fe6-8ac0-cda7e955c58c) | ✅ Same stretch is reached in the model |
| Mon Oct 26 | Pacific Beach Dr | Cyclist riding through flooded street, overflow from Mission Bay (Getty caption) | [Getty Images](https://www.gettyimages.com/photos/pacific-beach-san-diego-california) | ✅ West end of Pacific Beach Dr (near Mission Blvd) reached from 7.44 ft |
| Mon Oct 26 | Mission Blvd & North Jetty Rd | "Minor flooding", several vehicles driving through water | [CBS 8](https://www.cbs8.com/article/news/local/coastal-flood-warning-san-diego/509-f36dedb5-8b13-4610-8a06-2647997836ab) | ✅ Mission Blvd near N Jetty Rd: road covered at 7.7–8.2 ft (shallow, a few inches) |
| Mon Oct 26 | Side streets to Mission Blvd | Water "rushed into the side streets linking neighborhoods to Mission Boulevard"; Mission Blvd business: water "right up to my doorstep" | [KPBS](https://www.kpbs.org/news/environment/2026/10/27/port-issues-warning-of-street-flooding-as-high-tides-hit-san-diego) | ✅ Bay-side courts/places reached from ~7.4 ft; Mission Blvd covered 7.6–8.2 ft |
| Tue Oct 27 | Mission Beach | Rebuilt berm **held**; still water in streets and bike paths in PB / Mission Bay | [NBC San Diego](https://www.nbcsandiego.com/news/local/floods-in-san-diego-coastal-neighborhoods-continue-with-surge-of-high-tides/4092893/), [KPBS](https://www.kpbs.org/news/environment/2026/10/27/port-issues-warning-of-street-flooding-as-high-tides-hit-san-diego) | Model has no berm → expected to over-predict Mission Beach on this day |
| Wed Oct 28 | Briarfield Dr, Pacific Beach (Sail Bay) | Flooded street, bay water overflowing (photo caption) | [FOX Weather](https://www.foxweather.com/weather-news/california-coast-record-breaking-tidal-flooding) | 🟠 Near miss. E Briarfield Dr reached at 8.40 ft (0.28 ft above the day's level); nearby Dawes St ground is 5.9 ft, so storm-drain backflow is a likely path |
| Wed Oct 28 | Mission Beach | Rebuilt berm kept neighborhoods dry | [NBC San Diego video](https://www.nbcsandiego.com/video/videos/mission-bay-sand-berm-holds-high-tides-at-bay-after-flooding/4093385/) | Model has no berm |
| Oct 26–29 | San Diego County coast | NWS Coastal Flood Warning through Thursday | [CBS 8](https://www.cbs8.com/article/news/local/coastal-flood-warning-san-diego/509-f36dedb5-8b13-4610-8a06-2647997836ab), [NBC San Diego](https://www.nbcsandiego.com/news/local/san-diego-county-under-coastal-flood-warning-until-thursday/4091900/) | — |

## Open questions
- Was there flooding on **Sun Oct 25** (~7.91 ft)? The model says the bay side of Mission Beach starts flooding at ~7.4 ft without a berm. Was the berm in place then?
- Static ("bathtub with connectivity") models assume water has time to fill every connected low
  spot. Real peaks last ~1-2 hours and water enters through limited gaps, so the model can
  over-predict extent/depth. Watch for this in the backtest.
- Model berms: next version should be able to add the temporary Bayside Walk berm to test Oct 27–28.
