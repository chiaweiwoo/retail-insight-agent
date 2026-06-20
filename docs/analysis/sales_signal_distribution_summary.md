# Sales Signal Distribution Summary

Recommended primary signal candidate: `trailing_7d_pct_change`

## Distribution Snapshot

| metric | rows_with_baseline | min | p10 | p25 | median | p75 | p90 | max | mean | std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| day_over_day_abs_change | 445 | -12219.109999999997 | -1444.6525999999994 | -364.4400000000023 | 34.8929999999998 | 594.4800000000005 | 1604.6839999999993 | 8683.04 | 39.051584269662925 | 2157.920194453367 |
| day_over_day_pct_change | 445 | -43.649230467879136 | -25.203739593569317 | -8.189390419042951 | 1.0704571972549626 | 11.773972649721165 | 31.335765351892334 | 63.61488317943888 | 2.3920892840437507 | 19.74445353599052 |
| trailing_7d_abs_change | 435 | -6167.107 | -824.4951142857141 | -436.5460714285714 | -169.77999999999975 | 610.8075714285717 | 1400.8150285714294 | 10828.54157142857 | 138.44467764094148 | 1836.2952469176118 |
| trailing_7d_pct_change | 435 | -27.482707077656997 | -16.373815550776264 | -11.604423395801371 | -5.189251089808948 | 16.638575532027872 | 28.692365850231702 | 66.45532642078102 | 1.746017717739738 | 18.446082007239568 |
| same_weekday_4w_abs_change | 345 | -6426.615000000002 | -366.8791 | -107.47524999999973 | 137.88250000000016 | 559.7155000000002 | 1358.50635 | 6723.9749999999985 | 423.5784483091788 | 1321.034959763345 |
| same_weekday_4w_pct_change | 345 | -25.472946026980104 | -7.416211889367982 | -2.763569541424942 | 4.0346426851411845 | 12.372941606193397 | 22.916284727573693 | 76.17259288853376 | 6.004822144180105 | 13.151563835583818 |

## Threshold Grid Candidates

| metric | pct_threshold | abs_threshold | drop_count | lift_count | trigger_count |
| --- | --- | --- | --- | --- | --- |
| trailing_7d_pct_change | 25 | 10 | 2 | 71 | 73 |
| trailing_7d_pct_change | 25 | 20 | 2 | 71 | 73 |
| trailing_7d_pct_change | 25 | 30 | 2 | 71 | 73 |
| trailing_7d_pct_change | 25 | 40 | 2 | 71 | 73 |
| trailing_7d_pct_change | 25 | 50 | 2 | 71 | 73 |

## Pure Percent Trigger Distribution

| metric | pct_threshold | eligible_store_days | triggered_store_days | drop_store_days | lift_store_days | triggered_dates | triggered_stores |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trailing_7d_pct_change | 10 | 435 | 274 | 142 | 132 | 81 | 5 |
| trailing_7d_pct_change | 15 | 435 | 182 | 66 | 116 | 66 | 5 |
| trailing_7d_pct_change | 20 | 435 | 114 | 21 | 93 | 40 | 5 |
| trailing_7d_pct_change | 25 | 435 | 73 | 2 | 71 | 25 | 5 |
| trailing_7d_pct_change | 30 | 435 | 38 | 0 | 38 | 19 | 5 |

## Per-Store Spread At 20%

| store_alias | triggered_days | trigger_rate_pct |
| --- | --- | --- |
| city_13 | 32 | 36.7816091954023 |
| city_3 | 26 | 29.88505747126437 |
| city_12 | 25 | 28.735632183908045 |
| city_16 | 17 | 19.54022988505747 |
| city_0 | 14 | 16.091954022988507 |

## Grid Legend

- `D` = drop trigger
- `L` = lift trigger
- `.` = no trigger

## Notes

- `day_over_day` captures immediate swings but is the noisiest candidate.
- `trailing_7d` is smoother and currently the best default operational trigger when we want broad coverage.
- `same_weekday_4w` is the most retail-shaped benchmark, but it only covers 77.5% of the rows that `day_over_day` covers in this 90-day slice.
- `same_weekday_4w` also has an upward mean drift of 6.00% in this sample, so it is better as a reasoning baseline than as the first trigger baseline.
- Pure `trailing_7d_pct_change` at 20% gives 114 triggered store-days across 40 calendar dates.
- Pure `trailing_7d_pct_change` at 25% gives 73 triggered store-days across 25 calendar dates, which is a better anomaly-style discussion set.
- The current trigger exploration is per store-day, not a single global daily alarm.
