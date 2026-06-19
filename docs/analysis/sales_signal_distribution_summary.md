# Sales Signal Distribution Summary

Recommended primary signal candidate: `trailing_7d_pct_change`

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

## Notes

- `day_over_day` captures immediate swings but is the noisiest candidate.
- `trailing_7d` is smoother and currently the best default operational trigger when we want broad coverage.
- `same_weekday_4w` is the most retail-shaped benchmark, but it only covers 77.5% of the rows that `day_over_day` covers in this 90-day slice.
- `same_weekday_4w` also has an upward mean drift of 5.19% in this sample, so it is better as a reasoning baseline than as the first trigger baseline.
- Final RCA trigger logic should likely use both percentage change and absolute sales change.
