# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-19 09:41 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
17 forecast snapshots, 16 with results so far, 50,160 matched
point-hours, Fri Nov 13 4 PM – Wed Nov 18 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 25080 | -0.0 | 99.95 | 0.5 | -0.31 |
| NOAA-driven | 25080 | -1.7 | 70.78 | 1.7 | -0.04 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 7.2 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 6336 | -0.54 | 93.29 | 0.74 | 0.02 |
| NOAA-driven | 6336 | -2.22 | 72.62 | 2.22 | -0.03 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 4158 | 0.1 | 101.66 | 0.39 | -0.25 |
| ECMWF-driven | 12–24 h | 3894 | 0.04 | 100.72 | 0.31 | -0.24 |
| ECMWF-driven | 1–2 days | 6996 | -0.02 | 99.67 | 0.34 | 0.08 |
| ECMWF-driven | 2–4 days | 10032 | -0.05 | 99.09 | 0.74 | -0.63 |
| NOAA-driven | 0–12 h | 4158 | -1.53 | 74.82 | 1.54 | -0.38 |
| NOAA-driven | 12–24 h | 3894 | -1.69 | 72.47 | 1.69 | -0.56 |
| NOAA-driven | 1–2 days | 6996 | -1.66 | 69.76 | 1.66 | 0.05 |
| NOAA-driven | 2–4 days | 10032 | -1.81 | 69.02 | 1.81 | 0.24 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
