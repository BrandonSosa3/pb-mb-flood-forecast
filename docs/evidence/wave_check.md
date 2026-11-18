# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-18 09:27 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
15 forecast snapshots, 14 with results so far, 39,864 matched
point-hours, Fri Nov 13 4 PM – Tue Nov 17 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 19932 | -0.14 | 97.77 | 0.49 | -0.23 |
| NOAA-driven | 19932 | -1.79 | 72.05 | 1.79 | -0.08 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 7.4 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 4990 | -0.59 | 92.89 | 0.76 | -0.01 |
| NOAA-driven | 4990 | -2.28 | 72.59 | 2.28 | -0.16 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 3630 | 0.06 | 100.95 | 0.39 | -0.31 |
| ECMWF-driven | 12–24 h | 3366 | -0.01 | 99.92 | 0.3 | -0.3 |
| ECMWF-driven | 1–2 days | 5544 | -0.11 | 98.23 | 0.35 | 0.1 |
| ECMWF-driven | 2–4 days | 7392 | -0.33 | 94.97 | 0.74 | -0.41 |
| NOAA-driven | 0–12 h | 3630 | -1.56 | 75.8 | 1.57 | -0.46 |
| NOAA-driven | 12–24 h | 3366 | -1.75 | 73.25 | 1.75 | -0.66 |
| NOAA-driven | 1–2 days | 5544 | -1.75 | 70.75 | 1.75 | 0.04 |
| NOAA-driven | 2–4 days | 7392 | -1.95 | 70.61 | 1.95 | 0.27 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
