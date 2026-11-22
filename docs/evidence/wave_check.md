# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-22 09:01 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
22 forecast snapshots, 21 with results so far, 75,372 matched
point-hours, Fri Nov 13 4 PM – Sat Nov 21 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 37686 | 0.03 | 100.58 | 0.43 | -0.26 |
| NOAA-driven | 37686 | -1.6 | 69.42 | 1.6 | 0.27 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.4 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 9428 | -0.39 | 94.95 | 0.66 | -0.17 |
| NOAA-driven | 9428 | -2.04 | 73.41 | 2.04 | -0.15 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 5544 | 0.1 | 101.87 | 0.34 | -0.37 |
| ECMWF-driven | 12–24 h | 5280 | 0.07 | 101.35 | 0.28 | -0.29 |
| ECMWF-driven | 1–2 days | 9702 | 0.03 | 100.64 | 0.34 | 0.0 |
| ECMWF-driven | 2–4 days | 17160 | -0.01 | 99.84 | 0.57 | -0.37 |
| NOAA-driven | 0–12 h | 5544 | -1.47 | 73.36 | 1.48 | -0.25 |
| NOAA-driven | 12–24 h | 5280 | -1.57 | 71.67 | 1.57 | -0.24 |
| NOAA-driven | 1–2 days | 9702 | -1.56 | 69.51 | 1.56 | 0.12 |
| NOAA-driven | 2–4 days | 17160 | -1.68 | 67.25 | 1.68 | 0.68 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
