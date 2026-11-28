# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-28 09:37 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
32 forecast snapshots, 31 with results so far, 116,292 matched
point-hours, Fri Nov 13 4 PM – Fri Nov 27 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 58146 | 0.0 | 100.1 | 0.37 | -0.2 |
| NOAA-driven | 58146 | -1.41 | 70.67 | 1.42 | 0.1 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.1 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 14539 | -0.26 | 96.47 | 0.58 | -0.04 |
| NOAA-driven | 14539 | -1.86 | 75.2 | 1.86 | -0.17 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 8118 | 0.06 | 101.12 | 0.32 | -0.25 |
| ECMWF-driven | 12–24 h | 7854 | 0.04 | 100.74 | 0.27 | -0.13 |
| ECMWF-driven | 1–2 days | 14916 | -0.0 | 99.93 | 0.31 | 0.1 |
| ECMWF-driven | 2–4 days | 27258 | -0.02 | 99.67 | 0.45 | -0.36 |
| NOAA-driven | 0–12 h | 8118 | -1.39 | 72.87 | 1.4 | -0.2 |
| NOAA-driven | 12–24 h | 7854 | -1.43 | 71.24 | 1.44 | -0.23 |
| NOAA-driven | 1–2 days | 14916 | -1.4 | 70.44 | 1.4 | 0.01 |
| NOAA-driven | 2–4 days | 27258 | -1.42 | 69.9 | 1.43 | 0.34 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
