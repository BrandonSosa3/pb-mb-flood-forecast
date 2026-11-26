# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-26 22:56 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
29 forecast snapshots, 28 with results so far, 105,996 matched
point-hours, Fri Nov 13 4 PM – Thu Nov 26 1 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 52998 | -0.01 | 99.87 | 0.38 | -0.21 |
| NOAA-driven | 52998 | -1.46 | 69.69 | 1.46 | 0.2 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.2 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 13257 | -0.3 | 96.02 | 0.6 | -0.03 |
| NOAA-driven | 13257 | -1.91 | 74.88 | 1.91 | -0.15 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 7392 | 0.03 | 100.59 | 0.32 | -0.27 |
| ECMWF-driven | 12–24 h | 7128 | 0.02 | 100.41 | 0.26 | -0.15 |
| ECMWF-driven | 1–2 days | 13728 | -0.01 | 99.85 | 0.31 | 0.12 |
| ECMWF-driven | 2–4 days | 24750 | -0.02 | 99.48 | 0.47 | -0.39 |
| NOAA-driven | 0–12 h | 7392 | -1.43 | 72.39 | 1.43 | -0.15 |
| NOAA-driven | 12–24 h | 7128 | -1.47 | 70.59 | 1.47 | -0.16 |
| NOAA-driven | 1–2 days | 13728 | -1.43 | 69.88 | 1.43 | 0.08 |
| NOAA-driven | 2–4 days | 24750 | -1.48 | 68.42 | 1.49 | 0.48 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
