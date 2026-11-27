# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-27 10:19 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
30 forecast snapshots, 29 with results so far, 109,692 matched
point-hours, Fri Nov 13 4 PM – Fri Nov 27 1 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 54846 | -0.0 | 99.9 | 0.37 | -0.23 |
| NOAA-driven | 54846 | -1.45 | 70.08 | 1.45 | 0.15 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.2 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 13717 | -0.29 | 96.22 | 0.59 | -0.04 |
| NOAA-driven | 13717 | -1.88 | 75.16 | 1.89 | -0.18 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 7656 | 0.04 | 100.72 | 0.32 | -0.29 |
| ECMWF-driven | 12–24 h | 7392 | 0.02 | 100.38 | 0.26 | -0.18 |
| ECMWF-driven | 1–2 days | 13992 | -0.01 | 99.83 | 0.3 | 0.1 |
| ECMWF-driven | 2–4 days | 25806 | -0.02 | 99.53 | 0.46 | -0.41 |
| NOAA-driven | 0–12 h | 7656 | -1.42 | 72.6 | 1.42 | -0.19 |
| NOAA-driven | 12–24 h | 7392 | -1.46 | 70.87 | 1.46 | -0.21 |
| NOAA-driven | 1–2 days | 13992 | -1.43 | 69.93 | 1.43 | 0.05 |
| NOAA-driven | 2–4 days | 25806 | -1.46 | 69.1 | 1.46 | 0.41 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
