# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-14 20:10 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
7 forecast snapshots, 4 with results so far, 3,036 matched
point-hours, Fri Nov 13 4 PM – Sat Nov 14 10 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 1518 | 0.31 | 105.37 | 0.37 | -1.31 |
| NOAA-driven | 1518 | -0.89 | 84.7 | 0.91 | -1.33 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.6 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 383 | 0.31 | 104.45 | 0.33 | -1.35 |
| NOAA-driven | 383 | -1.17 | 82.94 | 1.22 | -1.64 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 1056 | 0.38 | 106.88 | 0.43 | -1.26 |
| ECMWF-driven | 12–24 h | 462 | 0.16 | 102.43 | 0.23 | -1.43 |
| NOAA-driven | 0–12 h | 1056 | -0.72 | 86.89 | 0.76 | -1.13 |
| NOAA-driven | 12–24 h | 462 | -1.26 | 80.43 | 1.27 | -1.79 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
