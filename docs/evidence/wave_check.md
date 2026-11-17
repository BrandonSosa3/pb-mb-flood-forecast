# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-17 22:11 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
14 forecast snapshots, 13 with results so far, 35,244 matched
point-hours, Fri Nov 13 4 PM – Tue Nov 17 1 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 17622 | -0.24 | 96.29 | 0.48 | -0.06 |
| NOAA-driven | 17622 | -1.83 | 71.63 | 1.83 | 0.01 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 7.7 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 4413 | -0.64 | 92.4 | 0.79 | 0.02 |
| NOAA-driven | 4413 | -2.31 | 72.58 | 2.31 | -0.15 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 3432 | 0.04 | 100.69 | 0.4 | -0.36 |
| ECMWF-driven | 12–24 h | 3036 | -0.0 | 99.98 | 0.31 | -0.36 |
| ECMWF-driven | 1–2 days | 5082 | -0.13 | 97.76 | 0.36 | 0.13 |
| ECMWF-driven | 2–4 days | 6072 | -0.61 | 91.04 | 0.7 | 0.11 |
| NOAA-driven | 0–12 h | 3432 | -1.56 | 75.86 | 1.57 | -0.47 |
| NOAA-driven | 12–24 h | 3036 | -1.78 | 72.87 | 1.78 | -0.63 |
| NOAA-driven | 1–2 days | 5082 | -1.79 | 70.09 | 1.79 | 0.18 |
| NOAA-driven | 2–4 days | 6072 | -2.03 | 69.9 | 2.03 | 0.44 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
