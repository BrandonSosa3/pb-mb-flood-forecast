# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-21 20:28 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
21 forecast snapshots, 20 with results so far, 71,544 matched
point-hours, Fri Nov 13 4 PM – Sat Nov 21 10 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 35772 | 0.03 | 100.49 | 0.45 | -0.27 |
| NOAA-driven | 35772 | -1.64 | 69.6 | 1.64 | 0.13 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.5 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 8945 | -0.41 | 94.75 | 0.67 | -0.13 |
| NOAA-driven | 8945 | -2.07 | 73.29 | 2.07 | -0.13 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 5280 | 0.1 | 101.78 | 0.35 | -0.39 |
| ECMWF-driven | 12–24 h | 4950 | 0.07 | 101.21 | 0.29 | -0.3 |
| ECMWF-driven | 1–2 days | 9438 | 0.03 | 100.59 | 0.34 | 0.0 |
| ECMWF-driven | 2–4 days | 16104 | -0.01 | 99.75 | 0.6 | -0.38 |
| NOAA-driven | 0–12 h | 5280 | -1.49 | 73.61 | 1.5 | -0.4 |
| NOAA-driven | 12–24 h | 4950 | -1.61 | 71.91 | 1.61 | -0.41 |
| NOAA-driven | 1–2 days | 9438 | -1.58 | 69.6 | 1.58 | 0.04 |
| NOAA-driven | 2–4 days | 16104 | -1.73 | 67.42 | 1.73 | 0.52 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
