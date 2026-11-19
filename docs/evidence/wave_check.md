# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-19 22:08 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
18 forecast snapshots, 17 with results so far, 54,780 matched
point-hours, Fri Nov 13 4 PM – Thu Nov 19 10 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 27390 | 0.03 | 100.53 | 0.49 | -0.37 |
| NOAA-driven | 27390 | -1.65 | 70.32 | 1.65 | 0.11 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 7.0 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 6852 | -0.52 | 93.5 | 0.73 | -0.02 |
| NOAA-driven | 6852 | -2.19 | 72.72 | 2.19 | -0.05 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 4422 | 0.11 | 101.81 | 0.38 | -0.3 |
| ECMWF-driven | 12–24 h | 4158 | 0.06 | 101.0 | 0.31 | -0.29 |
| ECMWF-driven | 1–2 days | 7524 | 0.01 | 100.23 | 0.35 | 0.0 |
| ECMWF-driven | 2–4 days | 11286 | 0.0 | 100.01 | 0.7 | -0.67 |
| NOAA-driven | 0–12 h | 4422 | -1.5 | 74.44 | 1.51 | -0.32 |
| NOAA-driven | 12–24 h | 4158 | -1.65 | 72.09 | 1.65 | -0.43 |
| NOAA-driven | 1–2 days | 7524 | -1.62 | 69.33 | 1.62 | 0.17 |
| NOAA-driven | 2–4 days | 11286 | -1.73 | 68.52 | 1.73 | 0.45 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
