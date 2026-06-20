# Context Pack

**Source:** FreshRetailNet-50K (anonymized 2024 dataset)
**Window:** 2024-03-28 to 2024-06-25 (18 cities, 90 days)
**Granularity:** city-day

> City IDs (integers 0–17) and product IDs are opaque anonymized identifiers. Do not assign business meaning to them beyond what is computed from the data. holiday_name_inferred values are themselves inferred — treat as uncertain priors. sale_amount and hours_sale are normalized sales amounts multiplied by a specific coefficient in the source dataset. Treat aggregated sales values as relative sales amounts for comparison, not literal unit counts and not currency revenue.

## Fleet

- Average daily sales (all cities, all days): **2773.86**
- Weekend vs weekday avg: {'weekday': 2558.53, 'weekend': 3303.92}

## Density tier averages (empirical)

Average daily sales grouped by density tier (1 = >100 stores, 2 = 20-99, 3 = <20). Use as a weak prior for relative scale comparisons only.

- Tier 1: avg 10985.62 / day
- Tier 2: avg 2219.92 / day
- Tier 3: avg 405.91 / day

## Per-city normals

| city_id | avg / day | stddev | min | max |
| --- | --- | --- | --- | --- |
| 0 | 26384.71 | 4331.9 | 18829.16 | 37557.31 |
| 1 | 456.49 | 87.14 | 300.25 | 688.96 |
| 2 | 393.06 | 77.3 | 277.05 | 613.0 |
| 3 | 1798.65 | 348.18 | 1224.05 | 2945.67 |
| 4 | 1520.24 | 404.95 | 818.66 | 2417.61 |
| 5 | 593.31 | 115.78 | 374.25 | 923.2 |
| 6 | 2462.59 | 494.39 | 1564.34 | 4236.77 |
| 7 | 420.9 | 86.06 | 280.72 | 671.17 |
| 8 | 51.37 | 11.32 | 32.47 | 96.67 |
| 9 | 184.01 | 38.4 | 122.49 | 288.51 |
| 10 | 413.06 | 89.62 | 245.05 | 658.88 |
| 11 | 2121.69 | 460.21 | 1253.27 | 3257.25 |
| 12 | 4773.5 | 1075.62 | 2975.74 | 7759.91 |
| 13 | 2324.31 | 517.29 | 1517.16 | 3533.5 |
| 14 | 519.98 | 121.84 | 310.12 | 877.99 |
| 15 | 756.46 | 131.69 | 497.07 | 1203.52 |
| 16 | 4469.79 | 828.52 | 2924.15 | 6774.26 |
| 17 | 285.45 | 79.97 | 151.75 | 456.45 |

## Holidays in window (inferred — uncertain)

- 2024-03-30: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-03-31: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-04: qingming_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-05: qingming_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-06: qingming_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-13: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-14: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-20: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-21: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-27: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-04-28: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-01: labor_day_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-02: labor_day_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-03: labor_day_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-04: labor_day_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-05: labor_day_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-11: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-12: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-18: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-19: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-25: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-05-26: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-01: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-02: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-08: dragon_boat_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-09: dragon_boat_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-10: dragon_boat_period (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-15: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-16: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-22: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)
- 2024-06-23: weekend (Inferred from project date rules; source dataset only provides holiday_flag.)

## Limitations

- No cost, margin, or product-category data available.
- No real-time or external data — this is a historical anonymized dataset.
- Treat all context as a weak prior, not ground truth.
- The analysis window is fixed: 2024-03-28 to 2024-06-25.
- sale_amount and hours_sale are normalized sales amounts multiplied by a specific coefficient in the source dataset. Treat aggregated sales values as relative sales amounts for comparison, not literal unit counts and not currency revenue.
