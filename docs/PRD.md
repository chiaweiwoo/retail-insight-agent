# Retail Insight Agent - PRD

## Data Semantics Guardrail

The source dataset field `sale_amount` is documented as a **daily sales amount after global normalization, multiplied by a specific coefficient**. `hours_sale` is the hourly version of the same normalized measure.

For this project, that means:

- sales values are useful for **relative comparison, anomaly detection, and baseline reasoning**
- sales values are **not** literal unit counts
- sales values are **not** real currency revenue
- report language should prefer `sales amount` or `normalized sales amount`

## 1. Project Overview

Retail Insight Agent is a personal learning project for building an evidence-backed retail root cause analysis system.

The near-term priority is to create a clean, scoped local analytical database from FreshRetailNet-50K, then use it to power a small runnable tool-calling RCA agent with auditable reports.

This is not a production system. It is a learning project built in phases.

## 2. Current Delivery Milestone

The current implementation milestones are:

1. Read the raw FreshRetailNet-50K parquet file.
2. Filter to the agreed project scope.
3. Aggregate raw product-level data into daily store-level tables.
4. Save the tables into a local DuckDB database.
5. Validate table counts and basic metric integrity.
6. Expose a read-only evidence viewer over the DuckDB output.
7. Explore precomputed daily drop/lift signals for store-day RCA triggering.
8. Build a small runnable RCA agent that calls bounded evidence tools over the local DuckDB-backed dataset.
9. Save traceable RCA outputs, logs, evaluator results, and reader-facing story reports.

Not part of the current milestones:

- MCP server runtime
- runtime skill system
- production external research dependence
- production serving stack

Decision hygiene:

- important analytical decisions should be recorded in the PRD and linked analysis notes
- trigger definitions should be data-backed, not guessed
- fixed-snapshot derived layers can be precomputed when that improves consistency
- early trigger windows should be treated carefully when history is still short

## 3. Problem Statement

Retail sales movement can be affected by many factors, including stockout, discount, activity, holiday and weekend effects, weather, and peer-store patterns.

A useful RCA system should not give generic explanations. It should eventually produce concise explanations backed by measurable evidence. Phase 1 exists to build that evidence foundation first. The next learning step is to place a thin agentic layer on top without overbuilding orchestration.

## 4. Scope

### Date Range

`2024-03-28` to `2024-06-25`

Expected number of days: `90`

### City Scope

Use only:

```text
city_id = 0
```

The system should refer to this carefully as:

```text
City 0 - possible core East China market
```

### Store Scope

Use 15 sampled stores:

```text
h235, h263, h182, h018, h555
m679, m648, m041, m236, m386
l260, l185, l165, l164, l175
```

Store aliases are project labels, not official store names.

### Product Scope

Do not analyze products or categories in this phase.

All product rows should be aggregated into daily store-level metrics.

### Analysis Grain

One analytical row represents:

```text
one store on one date
```

Expected store-day rows:

```text
15 stores x 90 days = 1,350 rows
```

For trigger exploration, daily RCA candidates are evaluated per `store_alias + dt`, not as a single market-wide daily alert.

## 5. Required Local Database

Use DuckDB.

Database path:

```text
data/db/rca_foundry.duckdb
```

The database must contain these seven tables:

```text
dim_store
dim_holiday_day
dim_weather_day
fact_sales_store_day
fact_stockout_store_day
fact_discount_store_day
fact_activity_store_day
```

Do not create a combined mart table in this phase.

## 6. Required Tables

### dim_store

```sql
store_alias TEXT PRIMARY KEY
```

Expected rows: `15`

### dim_holiday_day

```sql
dt DATE PRIMARY KEY,
weekday TEXT,
is_weekend BOOLEAN,
holiday_flag BOOLEAN,
holiday_name_inferred TEXT,
holiday_note TEXT
```

Expected rows: `90`

Allowed inferred holiday names:

```text
normal_weekday
weekend
qingming_period
labor_day_period
dragon_boat_period
```

### dim_weather_day

```sql
dt DATE PRIMARY KEY,
precpt DOUBLE,
avg_temperature DOUBLE,
avg_humidity DOUBLE,
avg_wind_level DOUBLE
```

Expected rows: `90`

### fact_sales_store_day

Expected rows: `1,350`

Aggregation:

```text
total_sales = sum(sale_amount)
avg_sales_per_product = avg(sale_amount)
product_count = count(product_id)
active_product_count = count(product_id where sale_amount > 0)
hour_XX_sales = sum(hours_sale[XX])
```

### fact_stockout_store_day

Expected rows: `1,350`

Aggregation:

```text
avg_stockout_hours = avg(stock_hour6_22_cnt)
stockout_product_rate = avg(stock_hour6_22_cnt > 0)
severe_stockout_product_rate = avg(stock_hour6_22_cnt >= 8)
full_stockout_product_rate = avg(stock_hour6_22_cnt = 16)
hour_XX_stockout_rate = avg(hours_stock_status[XX])
```

Rates should be stored as decimals between `0` and `1`.

### fact_discount_store_day

Expected rows: `1,350`

Aggregation:

```text
avg_discount = avg(discount)
discounted_product_rate = avg(discount < 0.999)
deep_discount_product_rate = avg(discount < 0.5)
```

### fact_activity_store_day

Expected rows: `1,350`

Aggregation:

```text
activity_product_rate = avg(activity_flag)
activity_sales_share =
  sum(sale_amount where activity_flag = 1) / sum(sale_amount)
```

If total sales is zero, store `activity_sales_share` as `0`.

## 7. Holiday Inference Rules

The raw dataset only provides `holiday_flag`.

Infer `holiday_name_inferred` from `dt` using:

```text
2024-04-04 to 2024-04-06 = qingming_period
2024-05-01 to 2024-05-05 = labor_day_period
2024-06-08 to 2024-06-10 = dragon_boat_period
Saturday or Sunday = weekend
otherwise = normal_weekday
```

`holiday_note` must state that the label is inferred from project date rules.

## 8. Validation Requirements

Validation must check:

1. DuckDB file exists.
2. All seven tables exist.
3. Row counts are correct.
4. No null `store_alias`.
5. No null `dt`.
6. Each fact table has exactly 15 stores.
7. Each fact table has exactly 90 dates.
8. Rate columns are between 0 and 1.
9. Hourly sales columns are non-negative.
10. Validation summary is concise and readable.

## 9. Agent Direction

The first agentic runtime should be intentionally small:

- one store-day RCA request at a time
- tool-calling LLM over local DuckDB-backed evidence
- tools should be domain-specific functions such as signal, sales, stockout, discount, activity, calendar-weather, and peer-store context
- no raw SQL tool exposed to the model
- optional research tool is gated and should not be used by default
- manager-style synthesis is allowed through explicit coordinator/controller/brief stages

The goal is a runnable evidence-backed RCA note with inspectable reasoning, not a production workflow engine.

## 10. UI Direction

The first interface phase is a simple analyst view over DuckDB-derived evidence, focused on:

- selecting a store and date
- viewing sales, stockout, discount, activity, holiday, and weather context
- displaying metrics before any generated narrative

The current UI work is secondary to backend and LLM workflow quality. Static report HTML is acceptable for now because it makes individual RCA runs easy to inspect without committing to a full app surface.

## 11. Current Signal Direction

The current trigger exploration direction is:

```text
signal metric = trailing_7d_pct_change
signal labels = drop / lift / neutral
signal storage = precomputed derived layer over the fixed DuckDB snapshot
```

Current working discussion thresholds:

```text
drop trigger <= -20%
lift trigger >= +30%
```

These thresholds are intentionally high and asymmetric for learning-stage anomaly review. They are meant to produce stronger scenarios for discussion, not production alert coverage.

Current fixed RCA benchmark set:

```text
3 drop scenarios + 3 lift scenarios
covering different store-prefix groups
used for early deterministic RCA and LLM evaluation
```

Benchmark scenarios are regression fixtures, not necessarily the most interesting demos. Ad hoc story-report examples may be chosen separately.

Current exploratory negative candidate:

```text
l165 on 2024-06-06
```

This candidate is useful because it triggers a strong trailing-7-day drop while same-weekday baseline is nearly normal. The intended lesson is calibration: the system should be able to conclude that an alert may be a window-composition artifact instead of forcing a causal story.

## 12. Reporting Direction

Each full RCA run should produce two classes of outputs:

1. Audit artifacts in the run folder:
   - decision card
   - full RCA report
   - critic note
   - controller note
   - specialist memos
   - trace JSON
   - run logs

2. Reader-facing story artifacts under:

```text
output/story_reports/<run_folder>/
```

The story report should walk through the RCA from trigger to final decision:

- why the store-day triggered
- which analysts were selected
- which tools each analyst used
- what each analyst found
- what the critic challenged
- what action survived synthesis

The story report may use a small LLM polishing step, but it must stay grounded in the saved trace.

## 13. Non-Goals For This Milestone

Do not build:

```text
MCP server
skills
customer analysis
product/category drilldown
FastAPI service
production deployment
```

## 14. Future Roadmap

Next direction:

1. Keep improving the bounded evidence tools before adding more orchestration.
2. Strengthen tests around tool access, trace faithfulness, and story report rendering.
3. Use fixed benchmark scenarios for regression.
4. Use ad hoc examples for report design and narrative quality.
5. Revisit richer orchestration only if the small agent path proves too limited.
