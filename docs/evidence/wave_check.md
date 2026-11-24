# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-24 11:47 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
25 forecast snapshots, 24 with results so far, 89,496 matched
point-hours, Fri Nov 13 4 PM – Tue Nov 24 1 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 44748 | 0.03 | 100.63 | 0.39 | -0.25 |
| NOAA-driven | 44748 | -1.5 | 68.99 | 1.5 | 0.24 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.1 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 11187 | -0.31 | 95.8 | 0.63 | -0.25 |
| NOAA-driven | 11187 | -1.97 | 73.49 | 1.98 | -0.19 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 6270 | 0.08 | 101.5 | 0.32 | -0.31 |
| ECMWF-driven | 12–24 h | 6072 | 0.06 | 101.08 | 0.26 | -0.16 |
| ECMWF-driven | 1–2 days | 11616 | 0.03 | 100.58 | 0.31 | 0.06 |
| ECMWF-driven | 2–4 days | 20790 | 0.01 | 100.22 | 0.5 | -0.44 |
| NOAA-driven | 0–12 h | 6270 | -1.42 | 72.77 | 1.42 | -0.17 |
| NOAA-driven | 12–24 h | 6072 | -1.49 | 71.01 | 1.49 | -0.15 |
| NOAA-driven | 1–2 days | 11616 | -1.47 | 68.82 | 1.47 | 0.08 |
| NOAA-driven | 2–4 days | 20790 | -1.54 | 67.18 | 1.54 | 0.57 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
