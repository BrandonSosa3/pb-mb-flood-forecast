# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-15 19:42 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
9 forecast snapshots, 8 with results so far, 10,956 matched
point-hours, Fri Nov 13 4 PM – Sun Nov 15 10 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 5478 | 0.21 | 103.22 | 0.33 | -0.45 |
| NOAA-driven | 5478 | -1.78 | 73.02 | 1.79 | -0.7 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 7.5 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 1371 | 0.04 | 100.47 | 0.39 | -0.09 |
| NOAA-driven | 1371 | -2.36 | 71.05 | 2.36 | -0.58 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 2112 | 0.25 | 103.98 | 0.37 | -0.61 |
| ECMWF-driven | 12–24 h | 1848 | 0.14 | 102.01 | 0.31 | -0.59 |
| ECMWF-driven | 1–2 days | 1518 | 0.25 | 103.7 | 0.31 | -0.05 |
| NOAA-driven | 0–12 h | 2112 | -1.5 | 76.47 | 1.52 | -0.81 |
| NOAA-driven | 12–24 h | 1848 | -1.94 | 71.29 | 1.94 | -0.97 |
| NOAA-driven | 1–2 days | 1518 | -1.97 | 70.54 | 1.97 | -0.23 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
