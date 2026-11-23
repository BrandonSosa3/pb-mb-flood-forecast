# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-23 09:58 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
23 forecast snapshots, 22 with results so far, 82,500 matched
point-hours, Fri Nov 13 4 PM – Sun Nov 22 10 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 41250 | 0.03 | 100.62 | 0.41 | -0.13 |
| NOAA-driven | 41250 | -1.54 | 69.17 | 1.54 | 0.31 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.2 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 10328 | -0.34 | 95.46 | 0.65 | -0.22 |
| NOAA-driven | 10328 | -2.0 | 73.48 | 2.0 | -0.17 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 5808 | 0.1 | 101.85 | 0.33 | -0.25 |
| ECMWF-driven | 12–24 h | 5808 | 0.07 | 101.26 | 0.27 | -0.11 |
| ECMWF-driven | 1–2 days | 10824 | 0.03 | 100.67 | 0.31 | 0.15 |
| ECMWF-driven | 2–4 days | 18810 | -0.0 | 99.95 | 0.53 | -0.25 |
| NOAA-driven | 0–12 h | 5808 | -1.44 | 73.14 | 1.45 | -0.15 |
| NOAA-driven | 12–24 h | 5808 | -1.5 | 71.31 | 1.5 | -0.16 |
| NOAA-driven | 1–2 days | 10824 | -1.49 | 69.21 | 1.49 | 0.13 |
| NOAA-driven | 2–4 days | 18810 | -1.6 | 67.09 | 1.6 | 0.69 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
