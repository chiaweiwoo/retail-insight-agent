# Sales Signal Distribution Summary

Recommended primary signal candidate: `trailing_7d_pct_change`

Current working discussion thresholds:

- `drop <= -20%`
- `lift >= +30%`

## Distribution Snapshot

| metric | rows_with_baseline | min | p10 | p25 | median | p75 | p90 | max | mean | std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| day_over_day_abs_change | 1335 | -82.96000000000001 | -22.55 | -7.945 | 1.1199999999999974 | 9.959999999999994 | 22.908000000000023 | 85.41999999999999 | 0.5063146067415731 | 20.091353091886756 |
| day_over_day_pct_change | 1335 | -44.93821562181159 | -21.989836549355246 | -10.124213920679004 | 1.8061996582865596 | 13.255866739029047 | 24.96051271764815 | 74.00277221623286 | 2.1491188611132 | 18.128758043992253 |
| trailing_7d_abs_change | 1305 | -47.82000000000002 | -17.508285714285716 | -7.374285714285705 | -0.2042857142857173 | 8.785714285714292 | 23.502000000000027 | 86.31571428571428 | 1.5647441160372193 | 17.031278282987614 |
| trailing_7d_pct_change | 1305 | -33.04471112461391 | -16.496404148115218 | -9.807880396814308 | -0.25861055601271077 | 11.402095084609192 | 23.639176297551558 | 77.32864978975967 | 1.8651004058097698 | 15.850704517085935 |
| same_weekday_4w_abs_change | 1035 | -43.0925 | -8.833499999999992 | -2.1487499999999997 | 2.5574999999999974 | 9.80375 | 20.958833333333338 | 62.75000000000003 | 4.144588566827697 | 13.006450804299158 |
| same_weekday_4w_pct_change | 1035 | -31.25300048007682 | -8.817288182316924 | -3.355666708550442 | 3.7825120899228777 | 12.323050525617116 | 21.851237938772087 | 57.74553943638485 | 5.193344665328693 | 12.44668407818346 |

## Threshold Grid Candidates

| metric | pct_threshold | abs_threshold | drop_count | lift_count | trigger_count |
| --- | --- | --- | --- | --- | --- |
| trailing_7d_pct_change | 20 | 30 | 10 | 60 | 70 |
| trailing_7d_pct_change | 30 | 10 | 5 | 72 | 77 |
| trailing_7d_pct_change | 25 | 20 | 11 | 67 | 78 |
| trailing_7d_pct_change | 15 | 30 | 37 | 81 | 118 |
| trailing_7d_pct_change | 25 | 10 | 17 | 101 | 118 |

## Pure Percent Trigger Distribution

| metric | pct_threshold | eligible_store_days | triggered_store_days | drop_store_days | lift_store_days | triggered_dates | triggered_stores |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trailing_7d_pct_change | 10 | 1305 | 681 | 321 | 360 | 85 | 15 |
| trailing_7d_pct_change | 15 | 1305 | 430 | 175 | 255 | 73 | 15 |
| trailing_7d_pct_change | 20 | 1305 | 242 | 66 | 176 | 49 | 15 |
| trailing_7d_pct_change | 25 | 1305 | 136 | 22 | 114 | 39 | 15 |
| trailing_7d_pct_change | 30 | 1305 | 77 | 5 | 72 | 28 | 15 |

## Per-Store Spread At 20%

| store_alias | triggered_days | trigger_rate_pct |
| --- | --- | --- |
| m041 | 30 | 34.48275862068966 |
| l185 | 27 | 31.03448275862069 |
| m236 | 27 | 31.03448275862069 |
| l165 | 26 | 29.88505747126437 |
| m648 | 18 | 20.689655172413794 |
| h235 | 15 | 17.24137931034483 |
| l164 | 15 | 17.24137931034483 |
| h182 | 14 | 16.091954022988507 |

## Grid Legend

- `D` = drop trigger
- `L` = lift trigger
- `.` = no trigger

## Notes

- `day_over_day` captures immediate swings but is the noisiest candidate.
- `trailing_7d` is smoother and currently the best default operational trigger when we want broad coverage.
- `same_weekday_4w` is the most retail-shaped benchmark, but it only covers 77.5% of the rows that `day_over_day` covers in this 90-day slice.
- `same_weekday_4w` also has an upward mean drift of 5.19% in this sample, so it is better as a reasoning baseline than as the first trigger baseline.
- Pure `trailing_7d_pct_change` at 20% gives 242 triggered store-days across 49 calendar dates.
- Pure `trailing_7d_pct_change` at 25% gives 136 triggered store-days across 39 calendar dates, which is a better anomaly-style discussion set.
- The current trigger exploration is per store-day, not a single global daily alarm.

## Recommended Working Interpretation

- Treat the signal as a precomputed store-day label, not an on-demand query.
- Use `trailing_7d_pct_change` as the first signal metric because it balances coverage and stability better than `day_over_day`.
- For stronger learning-stage scenarios, use asymmetric thresholds:
  - `drop <= -20%`
  - `lift >= +30%`
- This is intentionally selective and discussion-oriented rather than production-tuned.

## Grid References

- `20%` active-only grid: `docs/analysis/trigger_grids/trailing_7d_pct_trigger_grid_20_active_only.md`
- `25%` active-only grid: `docs/analysis/trigger_grids/trailing_7d_pct_trigger_grid_25_active_only.md`
- `30%` active-only grid: `docs/analysis/trigger_grids/trailing_7d_pct_trigger_grid_30_active_only.md`
