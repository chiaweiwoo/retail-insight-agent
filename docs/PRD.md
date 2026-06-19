# Retail Insight Agent - PRD

## 1. Project Overview

Retail Insight Agent is a personal learning project for building an evidence-backed retail root cause analysis system.

The near-term priority is to create a clean, scoped local analytical database from FreshRetailNet-50K. That evidence layer will support later RCA logic and, after that, a lightweight analyst-facing UI.

This is not a production system. It is a learning project built in phases.

## 2. Current Delivery Milestone

The current implementation milestone is Phase 1 only:

1. Read the raw FreshRetailNet-50K parquet file.
2. Filter to the agreed project scope.
3. Aggregate raw product-level data into daily store-level tables.
4. Save the tables into a local DuckDB database.
5. Validate table counts and basic metric integrity.
6. Stop after the ingestion layer is complete.

Not part of this milestone:

- RCA report generation
- deterministic RCA rules
- UI
- agents
- LLM integration

## 3. Problem Statement

Retail sales movement can be affected by many factors, including stockout, discount, activity, holiday and weekend effects, weather, and peer-store patterns.

A useful RCA system should not give generic explanations. It should eventually produce concise explanations backed by measurable evidence. Phase 1 exists to build that evidence foundation first.

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

## 9. UI Direction

UI is intentionally deferred until the evidence tables are stable.

The first interface phase should be a simple analyst view over DuckDB, focused on:

- selecting a store and date
- viewing sales, stockout, discount, activity, holiday, and weather context
- displaying metrics before any generated narrative

## 10. Non-Goals For This Milestone

Do not build:

```text
autonomous agents
LangGraph workflow
MCP server
skills
persistent memory
web search
news agent
customer analysis
product/category drilldown
dashboard UI
FastAPI service
production deployment
RCA report generation
```

## 11. Future Roadmap

After Phase 1 works:

1. Add evidence query helpers over DuckDB.
2. Add deterministic RCA logic.
3. Add a lightweight UI.
4. Add an LLM report writer later, if still useful.
