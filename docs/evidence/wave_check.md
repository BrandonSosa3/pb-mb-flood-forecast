# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-17 02:03 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
11 forecast snapshots, 10 with results so far, 23,628 matched
point-hours, Fri Nov 13 4 PM – Mon Nov 16 4 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 11814 | 0.01 | 100.22 | 0.3 | -0.05 |
| NOAA-driven | 11814 | -1.72 | 70.53 | 1.72 | 0.03 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.6 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 2958 | 0.06 | 100.76 | 0.41 | -0.24 |
| NOAA-driven | 2958 | -2.08 | 72.53 | 2.08 | -0.55 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 2640 | 0.22 | 103.66 | 0.34 | -0.45 |
| ECMWF-driven | 12–24 h | 2508 | 0.09 | 101.39 | 0.28 | -0.39 |
| ECMWF-driven | 1–2 days | 4224 | 0.0 | 100.01 | 0.27 | 0.17 |
| ECMWF-driven | 2–4 days | 2442 | -0.27 | 94.93 | 0.34 | 0.34 |
| NOAA-driven | 0–12 h | 2640 | -1.55 | 74.53 | 1.57 | -0.53 |
| NOAA-driven | 12–24 h | 2508 | -1.86 | 70.53 | 1.87 | -0.57 |
| NOAA-driven | 1–2 days | 4224 | -1.85 | 67.18 | 1.85 | 0.33 |
| NOAA-driven | 2–4 days | 2442 | -1.5 | 71.72 | 1.5 | 0.71 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
