# How much rain causes flood reports? (rain rating scale)

_Written by `pipeline/rain_thresholds.py` on 2026-11-16. Rain: San Diego airport hourly, 2018–now (141 storms). Reports: City Get It Done 'street flooded' (water-main / leak / sprinkler text removed), during the storm or the day after._

Rated by the **heaviest 6 hours of rain**, because the NWS forecast gives rain in 6-hour blocks. *With reports* = share of storms with at least one report in that neighborhood; *extra* = reports per storm above the usual dry-day rate (most flooding is never reported, so these are small numbers; what matters is that they rise with rain).

| Rating | Heaviest 6 h | Storms | Per year | La Jolla: with reports / extra | Pacific Beach: with reports / extra | Mission Beach: with reports / extra |
|---|---|---|---|---|---|---|
| Low | 0–0.25 in | 74 | 8.3 | 27% / +0.2 | 18% / +0.1 | 11% / +0.1 |
| Minor | 0.25–0.75 in | 45 | 5.1 | 49% / +0.6 | 33% / +0.5 | 36% / +0.6 |
| Moderate | 0.75–1.5 in | 19 | 2.1 | 63% / +1.4 | 74% / +1.9 | 68% / +1.7 |
| Major | 1.5 in + | 3 | 0.3 | 67% / +1.3 | 33% / +3.1 | 100% / +4.2 |

## Biggest storms

| Start | Total | Heaviest hour | Heaviest 6 h | Rating | La Jolla | Pacific Beach | Mission Beach |
|---|---|---|---|---|---|---|---|
| 2024-01-20 | 3.37 in | 0.81 in | 2.65 in | Major | 2 | 10 | 8 |
| 2025-12-31 | 3.46 in | 0.83 in | 1.89 in | Major | 3 | 0 | 4 |
| 2018-12-05 | 2.6 in | 0.84 in | 1.57 in | Major | 0 | 0 | 1 |
| 2019-12-26 | 1.28 in | 0.43 in | 1.28 in | Moderate | 1 | 1 | 0 |
| 2024-03-30 | 1.63 in | 0.45 in | 1.22 in | Moderate | 0 | 1 | 1 |
| 2023-08-20 | 1.84 in | 0.45 in | 1.15 in | Moderate | 1 | 1 | 1 |
| 2025-11-13 | 2.52 in | 0.39 in | 1.15 in | Moderate | 1 | 3 | 4 |
| 2018-01-08 | 1.75 in | 0.61 in | 1.12 in | Moderate | 0 | 0 | 0 |
| 2020-04-06 | 3.59 in | 0.31 in | 1.03 in | Moderate | 5 | 16 | 2 |
| 2019-12-23 | 1.35 in | 0.36 in | 0.99 in | Moderate | 2 | 1 | 2 |
| 2022-12-31 | 1.66 in | 0.44 in | 0.99 in | Moderate | 2 | 2 | 5 |
| 2019-12-04 | 1.19 in | 0.27 in | 0.95 in | Moderate | 0 | 0 | 0 |
| 2021-12-14 | 0.98 in | 0.41 in | 0.95 in | Moderate | 3 | 3 | 1 |
| 2019-11-27 | 1.95 in | 0.42 in | 0.91 in | Moderate | 3 | 2 | 1 |
| 2023-01-14 | 2.8 in | 0.21 in | 0.87 in | Moderate | 4 | 0 | 2 |

Limits: one rain gauge (the airport, ~5 km SE of Mission Beach; La Jolla's hills get more); reports undercount flooding and depend on who reports; same scale for all three neighborhoods (too few reports to tune each).

