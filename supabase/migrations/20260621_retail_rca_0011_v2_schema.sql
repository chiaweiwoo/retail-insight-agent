create schema if not exists rca;

create table if not exists rca.sales (
    city_id integer not null,
    dt text not null,
    total_sales double precision not null,
    store_count integer not null,
    product_count integer not null,
    active_product_count integer not null,
    avg_sales_per_product double precision not null,
    hour_00_sales double precision not null,
    hour_01_sales double precision not null,
    hour_02_sales double precision not null,
    hour_03_sales double precision not null,
    hour_04_sales double precision not null,
    hour_05_sales double precision not null,
    hour_06_sales double precision not null,
    hour_07_sales double precision not null,
    hour_08_sales double precision not null,
    hour_09_sales double precision not null,
    hour_10_sales double precision not null,
    hour_11_sales double precision not null,
    hour_12_sales double precision not null,
    hour_13_sales double precision not null,
    hour_14_sales double precision not null,
    hour_15_sales double precision not null,
    hour_16_sales double precision not null,
    hour_17_sales double precision not null,
    hour_18_sales double precision not null,
    hour_19_sales double precision not null,
    hour_20_sales double precision not null,
    hour_21_sales double precision not null,
    hour_22_sales double precision not null,
    hour_23_sales double precision not null,
    primary key (city_id, dt)
);

create table if not exists rca.inventory (
    city_id integer not null,
    dt text not null,
    avg_stockout_hours double precision not null,
    stockout_product_count integer not null,
    severe_stockout_product_count integer not null,
    full_stockout_product_count integer not null,
    stockout_product_rate double precision not null,
    severe_stockout_product_rate double precision not null,
    full_stockout_product_rate double precision not null,
    hour_00_stockout_rate double precision not null,
    hour_01_stockout_rate double precision not null,
    hour_02_stockout_rate double precision not null,
    hour_03_stockout_rate double precision not null,
    hour_04_stockout_rate double precision not null,
    hour_05_stockout_rate double precision not null,
    hour_06_stockout_rate double precision not null,
    hour_07_stockout_rate double precision not null,
    hour_08_stockout_rate double precision not null,
    hour_09_stockout_rate double precision not null,
    hour_10_stockout_rate double precision not null,
    hour_11_stockout_rate double precision not null,
    hour_12_stockout_rate double precision not null,
    hour_13_stockout_rate double precision not null,
    hour_14_stockout_rate double precision not null,
    hour_15_stockout_rate double precision not null,
    hour_16_stockout_rate double precision not null,
    hour_17_stockout_rate double precision not null,
    hour_18_stockout_rate double precision not null,
    hour_19_stockout_rate double precision not null,
    hour_20_stockout_rate double precision not null,
    hour_21_stockout_rate double precision not null,
    hour_22_stockout_rate double precision not null,
    hour_23_stockout_rate double precision not null,
    primary key (city_id, dt)
);

create table if not exists rca.pricing (
    city_id integer not null,
    dt text not null,
    avg_discount double precision not null,
    min_discount double precision not null,
    discounted_product_count integer not null,
    discounted_product_rate double precision not null,
    deep_discounted_product_count integer not null,
    deep_discounted_product_rate double precision not null,
    primary key (city_id, dt)
);

create table if not exists rca.promotions (
    city_id integer not null,
    dt text not null,
    activity_product_count integer not null,
    activity_product_rate double precision not null,
    activity_sales double precision not null,
    activity_sales_share double precision not null,
    primary key (city_id, dt)
);

create table if not exists rca.calendar (
    city_id integer not null,
    dt text not null,
    weekday text not null,
    is_weekend boolean not null,
    holiday_flag boolean not null,
    holiday_name_inferred text not null,
    primary key (city_id, dt)
);

create table if not exists rca.weather (
    city_id integer not null,
    dt text not null,
    precpt double precision not null,
    avg_temperature double precision not null,
    avg_humidity double precision not null,
    avg_wind_level double precision not null,
    primary key (city_id, dt)
);

create table if not exists rca.goals (
    city_id integer not null,
    dt text not null,
    expected_sales double precision,
    goal_method text not null,
    recent_7d_avg_sales double precision,
    same_weekday_4w_avg_sales double precision,
    primary key (city_id, dt)
);

create table if not exists rca.signals (
    city_id integer not null,
    dt text not null,
    total_sales double precision not null,
    expected_sales double precision,
    deviation_pct double precision,
    goal_method text not null,
    signal_label text not null,
    weekday text,
    holiday_name_inferred text,
    build_version text,
    generated_at text,
    primary key (city_id, dt)
);

create table if not exists rca.outcomes (
    run_id text not null,
    city_id integer not null,
    dt text not null,
    signal_label text not null,
    confidence text not null,
    headline text not null,
    decision_card_markdown text not null,
    report_markdown text not null,
    prediction_markdown text not null,
    prescription_markdown text not null,
    generated_at text not null,
    primary key (city_id, dt)
);

create table if not exists rca.events (
    id bigserial primary key,
    run_id text not null,
    city_id integer not null,
    dt text not null,
    seq integer not null,
    ts timestamptz not null,
    actor_type text not null,
    actor_name text not null,
    action text not null,
    source text not null,
    details jsonb not null default '{}'::jsonb
);

create table if not exists rca.completions (
    id bigserial primary key,
    run_id text not null,
    city_id integer not null,
    dt text not null,
    ts timestamptz not null,
    node_name text not null,
    model text not null,
    prompt_tokens integer,
    completion_tokens integer,
    content text not null,
    tool_calls_json jsonb not null default '[]'::jsonb
);

create table if not exists rca.memory (
    id bigserial primary key,
    city_id integer not null,
    dt text not null,
    run_id text not null,
    memory_type text not null,
    topic text not null,
    content text not null,
    signal_label text not null,
    created_at timestamptz not null default now()
);

create table if not exists rca.evidence_cache (
    id bigserial primary key,
    cache_key text not null unique,
    build_version text,
    city_id integer,
    dt text,
    tool_name text not null,
    params_json jsonb not null,
    result_json jsonb not null,
    created_at timestamptz not null default now()
);

create table if not exists rca.external_events (
    id bigserial primary key,
    city_id integer not null,
    dt text not null,
    query text not null,
    source text not null,
    title text not null,
    url text not null,
    snippet text not null,
    published_at text,
    result_json jsonb not null,
    created_at timestamptz not null default now()
);

alter table rca.sales enable row level security;
alter table rca.inventory enable row level security;
alter table rca.pricing enable row level security;
alter table rca.promotions enable row level security;
alter table rca.calendar enable row level security;
alter table rca.weather enable row level security;
alter table rca.goals enable row level security;
alter table rca.signals enable row level security;
alter table rca.outcomes enable row level security;
alter table rca.events enable row level security;
alter table rca.completions enable row level security;
alter table rca.memory enable row level security;
alter table rca.evidence_cache enable row level security;
alter table rca.external_events enable row level security;

drop policy if exists "anon_read_sales" on rca.sales;
create policy "anon_read_sales" on rca.sales for select to anon, authenticated using (true);
drop policy if exists "anon_read_inventory" on rca.inventory;
create policy "anon_read_inventory" on rca.inventory for select to anon, authenticated using (true);
drop policy if exists "anon_read_pricing" on rca.pricing;
create policy "anon_read_pricing" on rca.pricing for select to anon, authenticated using (true);
drop policy if exists "anon_read_promotions" on rca.promotions;
create policy "anon_read_promotions" on rca.promotions for select to anon, authenticated using (true);
drop policy if exists "anon_read_calendar" on rca.calendar;
create policy "anon_read_calendar" on rca.calendar for select to anon, authenticated using (true);
drop policy if exists "anon_read_weather" on rca.weather;
create policy "anon_read_weather" on rca.weather for select to anon, authenticated using (true);
drop policy if exists "anon_read_goals" on rca.goals;
create policy "anon_read_goals" on rca.goals for select to anon, authenticated using (true);
drop policy if exists "anon_read_signals" on rca.signals;
create policy "anon_read_signals" on rca.signals for select to anon, authenticated using (true);
drop policy if exists "anon_read_outcomes" on rca.outcomes;
create policy "anon_read_outcomes" on rca.outcomes for select to anon, authenticated using (true);
drop policy if exists "anon_read_events" on rca.events;
create policy "anon_read_events" on rca.events for select to anon, authenticated using (true);
drop policy if exists "anon_read_completions" on rca.completions;
create policy "anon_read_completions" on rca.completions for select to anon, authenticated using (true);
drop policy if exists "anon_read_memory" on rca.memory;
create policy "anon_read_memory" on rca.memory for select to anon, authenticated using (true);
drop policy if exists "anon_read_evidence_cache" on rca.evidence_cache;
create policy "anon_read_evidence_cache" on rca.evidence_cache for select to anon, authenticated using (true);
drop policy if exists "anon_read_external_events" on rca.external_events;
create policy "anon_read_external_events" on rca.external_events for select to anon, authenticated using (true);

grant usage on schema rca to anon, authenticated, service_role;
grant select on all tables in schema rca to anon, authenticated;
grant all on all tables in schema rca to service_role;
