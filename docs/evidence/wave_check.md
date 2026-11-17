# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-17 09:55 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
13 forecast snapshots, 12 with results so far, 26,796 matched
point-hours, Fri Nov 13 4 PM – Mon Nov 16 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 13398 | -0.08 | 98.61 | 0.36 | -0.05 |
| NOAA-driven | 13398 | -1.71 | 71.12 | 1.71 | -0.01 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.8 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 3351 | -0.2 | 97.4 | 0.55 | -0.15 |
| NOAA-driven | 3351 | -2.06 | 73.05 | 2.06 | -0.45 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 2904 | 0.14 | 102.24 | 0.37 | -0.41 |
| ECMWF-driven | 12–24 h | 2640 | 0.05 | 100.77 | 0.3 | -0.38 |
| ECMWF-driven | 1–2 days | 4488 | -0.05 | 99.04 | 0.31 | 0.15 |
| ECMWF-driven | 2–4 days | 3366 | -0.41 | 92.76 | 0.46 | 0.24 |
| NOAA-driven | 0–12 h | 2904 | -1.54 | 75.02 | 1.55 | -0.51 |
| NOAA-driven | 12–24 h | 2640 | -1.84 | 70.94 | 1.84 | -0.57 |
| NOAA-driven | 1–2 days | 4488 | -1.84 | 67.81 | 1.84 | 0.29 |
| NOAA-driven | 2–4 days | 3366 | -1.59 | 72.05 | 1.59 | 0.48 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
