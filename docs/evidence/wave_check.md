# Wave check: logged forecasts vs what happened

_Rewritten by `pipeline/verify_forecasts.py` on 2026-11-24 23:31 UTC. Do not edit by hand._

"What happened" = CDIP MOP nowcast (same model and points, driven by measured buoys).
26 forecast snapshots, 25 with results so far, 93,192 matched
point-hours, Fri Nov 13 4 PM – Tue Nov 24 1 PM PT. Heights are significant wave height at ~10 m depth, feet.

- **bias**: average forecast minus actual (negative = forecast too small)
- **ratio**: forecast as a percent of actual (100% = right on average)
- **error**: average size of the miss, either direction

## Overall
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 46596 | 0.02 | 100.45 | 0.38 | -0.3 |
| NOAA-driven | 46596 | -1.49 | 68.68 | 1.49 | 0.24 |

## Bigger-wave hours only (top quarter of actual heights, ≥ 6.0 ft)
| model_name | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|
| ECMWF-driven | 11656 | -0.3 | 96.0 | 0.63 | -0.24 |
| NOAA-driven | 11656 | -1.96 | 73.52 | 1.96 | -0.18 |

## By how far ahead the forecast was made
| model_name | lead | pairs | bias_ft | ratio_pct | error_ft | period_bias_s |
|---|---|---|---|---|---|---|
| ECMWF-driven | 0–12 h | 6600 | 0.06 | 101.27 | 0.31 | -0.36 |
| ECMWF-driven | 12–24 h | 6270 | 0.05 | 100.92 | 0.26 | -0.18 |
| ECMWF-driven | 1–2 days | 11880 | 0.02 | 100.46 | 0.31 | 0.03 |
| ECMWF-driven | 2–4 days | 21846 | 0.0 | 100.03 | 0.48 | -0.5 |
| NOAA-driven | 0–12 h | 6600 | -1.41 | 72.28 | 1.41 | -0.16 |
| NOAA-driven | 12–24 h | 6270 | -1.48 | 70.74 | 1.48 | -0.14 |
| NOAA-driven | 1–2 days | 11880 | -1.46 | 68.63 | 1.46 | 0.08 |
| NOAA-driven | 2–4 days | 21846 | -1.53 | 66.86 | 1.53 | 0.55 |

## Caveats
- Very little data yet (logging started 2026-11-13); this becomes meaningful after a few weeks and
  several swells. Do not tune the model on one swell.
- The nowcast is itself a model (driven by buoys), not a direct measurement at each stretch.
