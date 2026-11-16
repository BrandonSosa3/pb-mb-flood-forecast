# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-16 08:47 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
10 forecast snapshots, 9 with results so far, 15,708 matched
point-hours, Fri Nov 13 4 PM – Sun Nov 15 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 7854 | 0.17 | 102.78 | 0.27 | -0.28 |
| NOAA-driven | 7854 | -1.79 | 70.49 | 1.79 | -0.34 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 7.0 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 1966 | 0.11 | 101.39 | 0.39 | -0.2 |
| NOAA-driven | 1966 | -2.28 | 71.07 | 2.29 | -0.64 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 2376 | 0.24 | 103.9 | 0.35 | -0.54 |
| ECMWF-driven | 12–24 h | 2112 | 0.13 | 102.03 | 0.29 | -0.52 |
| ECMWF-driven | 1–2 days | 2904 | 0.15 | 102.57 | 0.21 | 0.12 |
| ECMWF-driven | 2–4 days | 462 | 0.07 | 101.5 | 0.12 | -0.37 |
| NOAA-driven | 0–12 h | 2376 | -1.54 | 75.24 | 1.55 | -0.68 |
| NOAA-driven | 12–24 h | 2112 | -1.92 | 70.5 | 1.92 | -0.8 |
| NOAA-driven | 1–2 days | 2904 | -1.91 | 67.16 | 1.91 | 0.15 |
| NOAA-driven | 2–4 days | 462 | -1.66 | 64.08 | 1.66 | 0.37 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
