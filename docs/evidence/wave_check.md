# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-15 08:37 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
8 forecast snapshots, 7 with results so far, 6,732 matched
point-hours, Fri Nov 13 4 PM – Sat Nov 14 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 3366 | 0.15 | 102.27 | 0.34 | -0.53 |
| NOAA-driven | 3366 | -1.66 | 75.56 | 1.67 | -0.85 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 7.8 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 844 | -0.07 | 99.15 | 0.39 | 0.06 |
| NOAA-driven | 844 | -2.43 | 71.04 | 2.43 | -0.42 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 1848 | 0.24 | 103.81 | 0.38 | -0.65 |
| ECMWF-driven | 12–24 h | 1056 | 0.01 | 100.14 | 0.29 | -0.76 |
| ECMWF-driven | 1–2 days | 462 | 0.12 | 101.61 | 0.29 | 0.48 |
| NOAA-driven | 0–12 h | 1848 | -1.45 | 77.4 | 1.47 | -0.85 |
| NOAA-driven | 12–24 h | 1056 | -1.85 | 73.93 | 1.86 | -1.34 |
| NOAA-driven | 1–2 days | 462 | -2.06 | 72.83 | 2.06 | 0.28 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
