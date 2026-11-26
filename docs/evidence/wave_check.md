# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-26 10:13 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
28 forecast snapshots, 27 with results so far, 102,828 matched
point-hours, Fri Nov 13 4 PM – Thu Nov 26 1 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 51414 | 0.0 | 100.02 | 0.37 | -0.21 |
| NOAA-driven | 51414 | -1.46 | 69.19 | 1.46 | 0.23 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.0 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 12865 | -0.28 | 96.27 | 0.59 | -0.01 |
| NOAA-driven | 12865 | -1.91 | 74.29 | 1.91 | -0.08 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 7128 | 0.04 | 100.86 | 0.31 | -0.27 |
| ECMWF-driven | 12–24 h | 6864 | 0.04 | 100.72 | 0.25 | -0.14 |
| ECMWF-driven | 1–2 days | 13464 | -0.0 | 99.97 | 0.3 | 0.13 |
| ECMWF-driven | 2–4 days | 23958 | -0.02 | 99.57 | 0.47 | -0.4 |
| NOAA-driven | 0–12 h | 7128 | -1.42 | 72.06 | 1.42 | -0.14 |
| NOAA-driven | 12–24 h | 6864 | -1.44 | 70.58 | 1.44 | -0.14 |
| NOAA-driven | 1–2 days | 13464 | -1.43 | 69.45 | 1.43 | 0.1 |
| NOAA-driven | 2–4 days | 23958 | -1.49 | 67.67 | 1.49 | 0.52 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
