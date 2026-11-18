# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-18 21:48 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
16 forecast snapshots, 15 with results so far, 45,540 matched
point-hours, Fri Nov 13 4 PM – Wed Nov 18 10 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 22770 | -0.05 | 99.25 | 0.51 | -0.3 |
| NOAA-driven | 22770 | -1.75 | 71.35 | 1.75 | -0.1 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 7.3 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 5702 | -0.55 | 93.26 | 0.74 | 0.07 |
| NOAA-driven | 5702 | -2.25 | 72.63 | 2.25 | -0.01 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 3894 | 0.08 | 101.34 | 0.39 | -0.25 |
| ECMWF-driven | 12–24 h | 3630 | 0.02 | 100.34 | 0.31 | -0.24 |
| ECMWF-driven | 1–2 days | 6270 | -0.07 | 98.85 | 0.34 | 0.13 |
| ECMWF-driven | 2–4 days | 8976 | -0.12 | 98.14 | 0.77 | -0.65 |
| NOAA-driven | 0–12 h | 3894 | -1.55 | 75.27 | 1.56 | -0.45 |
| NOAA-driven | 12–24 h | 3630 | -1.72 | 72.87 | 1.73 | -0.64 |
| NOAA-driven | 1–2 days | 6270 | -1.71 | 70.35 | 1.71 | 0.01 |
| NOAA-driven | 2–4 days | 8976 | -1.88 | 69.65 | 1.88 | 0.2 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
