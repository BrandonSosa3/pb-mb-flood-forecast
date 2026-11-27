# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-27 22:40 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
31 forecast snapshots, 30 with results so far, 113,388 matched
point-hours, Fri Nov 13 4 PM – Fri Nov 27 1 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 56694 | -0.01 | 99.87 | 0.37 | -0.25 |
| NOAA-driven | 56694 | -1.44 | 70.22 | 1.44 | 0.11 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.1 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 14174 | -0.27 | 96.35 | 0.58 | -0.04 |
| NOAA-driven | 14174 | -1.87 | 75.19 | 1.87 | -0.18 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 7920 | 0.04 | 100.83 | 0.32 | -0.3 |
| ECMWF-driven | 12–24 h | 7656 | 0.02 | 100.38 | 0.26 | -0.21 |
| ECMWF-driven | 1–2 days | 14520 | -0.01 | 99.73 | 0.3 | 0.06 |
| ECMWF-driven | 2–4 days | 26598 | -0.02 | 99.48 | 0.45 | -0.42 |
| NOAA-driven | 0–12 h | 7920 | -1.41 | 72.6 | 1.42 | -0.22 |
| NOAA-driven | 12–24 h | 7656 | -1.46 | 70.93 | 1.46 | -0.23 |
| NOAA-driven | 1–2 days | 14520 | -1.42 | 70.0 | 1.42 | 0.01 |
| NOAA-driven | 2–4 days | 26598 | -1.45 | 69.36 | 1.45 | 0.36 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
