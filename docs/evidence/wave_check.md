# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-21 08:57 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
20 forecast snapshots, 19 with results so far, 67,716 matched
point-hours, Fri Nov 13 4 PM – Fri Nov 20 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 33858 | 0.03 | 100.61 | 0.47 | -0.21 |
| NOAA-driven | 33858 | -1.64 | 69.95 | 1.65 | 0.16 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.6 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 8469 | -0.43 | 94.45 | 0.69 | -0.1 |
| NOAA-driven | 8469 | -2.09 | 73.18 | 2.09 | -0.12 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 4950 | 0.1 | 101.69 | 0.36 | -0.3 |
| ECMWF-driven | 12–24 h | 4752 | 0.07 | 101.14 | 0.3 | -0.24 |
| ECMWF-driven | 1–2 days | 9108 | 0.04 | 100.71 | 0.35 | 0.05 |
| ECMWF-driven | 2–4 days | 15048 | -0.0 | 99.98 | 0.62 | -0.33 |
| NOAA-driven | 0–12 h | 4950 | -1.5 | 73.95 | 1.51 | -0.36 |
| NOAA-driven | 12–24 h | 4752 | -1.62 | 72.06 | 1.63 | -0.4 |
| NOAA-driven | 1–2 days | 9108 | -1.59 | 69.73 | 1.59 | 0.07 |
| NOAA-driven | 2–4 days | 15048 | -1.73 | 67.96 | 1.73 | 0.55 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
