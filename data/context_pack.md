# Context Pack

**Source:** FreshRetailNet-50K (anonymized 2024 dataset)
**Window:** 2024-03-28 to 2024-06-25 (15 stores, 90 days)
**Granularity:** store-day

> Store aliases, city IDs, and product IDs are opaque anonymized identifiers. Do not assign business meaning to them beyond what is computed from the data. holiday_name_inferred values are themselves inferred — treat as uncertain priors.

## Fleet

- Average daily sales (all stores, all days): **103.06**
- Weekend vs weekday avg: {'weekday': 96.73, 'weekend': 118.62}

## Store prefix groupings (empirical, not tier labels)

Average daily sales grouped by the first letter of store_alias. This is a computed grouping only — the prefix is an opaque identifier and is NOT labelled as a tier or size category.

- `h` prefix: avg 188.36 / day
- `l` prefix: avg 36.71 / day
- `m` prefix: avg 84.11 / day

## Per-store normals

| store | avg / day | stddev | min | max |
| --- | --- | --- | --- | --- |
| h018 | 187.54 | 25.85 | 130.27 | 253.57 |
| h182 | 191.89 | 30.51 | 148.2 | 274.6 |
| h235 | 194.56 | 30.36 | 138.77 | 270.8 |
| h263 | 193.42 | 28.23 | 141.67 | 254.7 |
| h555 | 174.37 | 21.29 | 126.23 | 220.05 |
| l164 | 35.5 | 6.56 | 22.6 | 53.47 |
| l165 | 36.88 | 7.5 | 22.3 | 57.2 |
| l175 | 34.28 | 5.54 | 23.04 | 47.6 |
| l185 | 37.59 | 7.97 | 25.5 | 55.3 |
| l260 | 39.28 | 7.05 | 24.55 | 62.9 |
| m041 | 84.41 | 20.51 | 48.57 | 146.4 |
| m236 | 82.97 | 15.45 | 53.56 | 122.78 |
| m386 | 82.86 | 14.85 | 48.24 | 112.84 |
| m648 | 84.99 | 14.51 | 61.68 | 127.1 |
| m679 | 85.34 | 13.45 | 62.0 | 122.5 |

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
