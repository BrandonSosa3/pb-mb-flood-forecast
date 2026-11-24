# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-24 01:39 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
24 forecast snapshots, 23 with results so far, 87,120 matched
point-hours, Fri Nov 13 4 PM – Mon Nov 23 4 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 43560 | 0.03 | 100.71 | 0.4 | -0.21 |
| NOAA-driven | 43560 | -1.5 | 69.17 | 1.5 | 0.25 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.2 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 10894 | -0.32 | 95.69 | 0.64 | -0.24 |
| NOAA-driven | 10894 | -1.99 | 73.46 | 1.99 | -0.2 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 6072 | 0.09 | 101.62 | 0.32 | -0.28 |
| ECMWF-driven | 12–24 h | 5874 | 0.06 | 101.22 | 0.26 | -0.12 |
| ECMWF-driven | 1–2 days | 11484 | 0.03 | 100.64 | 0.31 | 0.07 |
| ECMWF-driven | 2–4 days | 20130 | 0.01 | 100.28 | 0.51 | -0.38 |
| NOAA-driven | 0–12 h | 6072 | -1.42 | 73.05 | 1.43 | -0.18 |
| NOAA-driven | 12–24 h | 5874 | -1.5 | 71.27 | 1.5 | -0.16 |
| NOAA-driven | 1–2 days | 11484 | -1.47 | 68.92 | 1.47 | 0.08 |
| NOAA-driven | 2–4 days | 20130 | -1.55 | 67.35 | 1.55 | 0.59 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
