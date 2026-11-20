# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-20 21:47 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
19 forecast snapshots, 18 with results so far, 63,624 matched
point-hours, Fri Nov 13 4 PM – Fri Nov 20 10 AM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 31812 | 0.05 | 100.86 | 0.47 | -0.23 |
| NOAA-driven | 31812 | -1.65 | 70.17 | 1.65 | 0.17 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.7 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 7962 | -0.46 | 94.13 | 0.7 | -0.08 |
| NOAA-driven | 7962 | -2.12 | 73.06 | 2.12 | -0.1 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 4752 | 0.11 | 101.83 | 0.37 | -0.31 |
| ECMWF-driven | 12–24 h | 4686 | 0.07 | 101.12 | 0.3 | -0.24 |
| ECMWF-driven | 1–2 days | 8580 | 0.05 | 100.95 | 0.35 | 0.05 |
| ECMWF-driven | 2–4 days | 13794 | 0.02 | 100.35 | 0.65 | -0.38 |
| NOAA-driven | 0–12 h | 4752 | -1.5 | 74.25 | 1.51 | -0.35 |
| NOAA-driven | 12–24 h | 4686 | -1.63 | 72.04 | 1.63 | -0.4 |
| NOAA-driven | 1–2 days | 8580 | -1.6 | 69.69 | 1.6 | 0.11 |
| NOAA-driven | 2–4 days | 13794 | -1.73 | 68.27 | 1.73 | 0.59 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
