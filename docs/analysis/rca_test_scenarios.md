# RCA Test Scenarios

This file defines the fixed early-stage RCA scenario set we will use before broader LLM evaluation.

The goal is not coverage. The goal is to use strong, discussion-friendly scenarios across different store tiers while the project is still in a learning phase.

These six scenarios are regression fixtures. They should remain stable unless we intentionally redefine the benchmark.

## Signal Definition

- metric: `trailing_7d_pct_change`
- drop trigger: `<= -20%`
- lift trigger: `>= +30%`

## Fixed Scenario Set

### Drops

| tier | store_alias | dt | total_sales | trailing_7d_avg_sales | trailing_7d_abs_change | trailing_7d_pct_change |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| high | h555 | 2024-05-16 | 131.91 | 175.632857 | -43.722857 | -24.894463 |
| medium | m041 | 2024-05-09 | 56.67 | 84.638571 | -27.968571 | -33.044711 |
| low | l165 | 2024-05-16 | 25.38 | 37.168571 | -11.788571 | -31.716504 |

### Lifts

| tier | store_alias | dt | total_sales | trailing_7d_avg_sales | trailing_7d_abs_change | trailing_7d_pct_change |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| high | h235 | 2024-05-05 | 270.80 | 184.484286 | 86.315714 | 46.787570 |
| medium | m041 | 2024-05-12 | 146.40 | 82.558571 | 63.841429 | 77.328650 |
| low | l185 | 2024-04-13 | 49.40 | 32.025714 | 17.374286 | 54.251048 |

## Why These Scenarios

- one high-tier, one medium-tier, and one low-tier example for drops
- one high-tier, one medium-tier, and one low-tier example for lifts
- all six are clear trigger cases under the current asymmetric thresholds
- stores are intentionally varied so early RCA work does not overfit a single store pattern

## Usage

Use these six store-day cases as the default benchmark set for:

- deterministic RCA evidence checks
- prompt design and grounding checks
- early LLM report evaluation
- regression comparisons when RCA logic changes

## Exploratory Story Report Candidates

Story-report examples can be selected outside the fixed benchmark set. These are for narrative quality and human review, not regression comparison.

Selection criteria for a good exploratory negative example:

- strong drop signal
- enough history for same-weekday comparison
- possible tension between stockout, promotion, peer, or calendar evidence
- room for the system to say "not actionable" when the signal is a measurement artifact

Current exploratory negative candidate:

| store_alias | dt | total_sales | trailing_7d_avg_sales | trailing_7d_pct_change | same_weekday_4w_avg_sales | same_weekday_4w_pct_change | why interesting |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| l165 | 2024-06-06 | 28.10 | 40.40 | -30.4% | 28.83 | -2.5% | Strong trailing-window drop, but nearly normal Thursday baseline; tests whether the RCA avoids over-attribution. |

Notes from the first search pass:

- `l165 2024-04-03` is the largest-scoring drop candidate, but it is early in the dataset and lacks same-weekday baseline.
- `l165 2024-06-06` is a better calibration test because it has stronger historical context and a plausible "window composition artifact" conclusion.
- Negative examples may be more useful than lifts for report demos because they force the system to handle operational risk, stockout ambiguity, and false-positive alerts.
