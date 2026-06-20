-- Migration 0005: city-grain pivot
-- Replaces store-era tables with city-grain schema.
-- Run in Supabase SQL Editor (service role). Safe to re-run (idempotent).
--
-- Changes:
--   DROP rca_store_series (store×product grain — eliminated)
--   DROP rca_store_normals, rca_store_profile (replaced by city-keyed versions)
--   ALTER rca_outcome: rename store_id text → city_id integer
--   CREATE rca_city_series, rca_city_normals, rca_city_profile (city-grain replacements)
--   CREATE analytics placeholder tables (populated by rca build → rca sync in Round C):
--     rca_city_signal, rca_city_segment, rca_city_correlations, rca_city_hourly

-- ============================================================
-- 1. Drop store-era tables
-- ============================================================

DROP TABLE IF EXISTS public.rca_store_series   CASCADE;
DROP TABLE IF EXISTS public.rca_store_normals  CASCADE;
DROP TABLE IF EXISTS public.rca_store_profile  CASCADE;

-- ============================================================
-- 2. rca_outcome: rename store_id → city_id
--    (city_id is integer 0–17; was text store alias like "h555")
-- ============================================================

ALTER TABLE public.rca_outcome
    DROP COLUMN IF EXISTS store_id;

ALTER TABLE public.rca_outcome
    ADD COLUMN IF NOT EXISTS city_id smallint;

DROP INDEX IF EXISTS idx_rca_outcome_store;
CREATE INDEX IF NOT EXISTS idx_rca_outcome_city ON public.rca_outcome (city_id, dt DESC);

-- ============================================================
-- 3. rca_city_series  (city-day aggregate time series)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.rca_city_series (
    city_id                 smallint    NOT NULL,
    density_tier            char(1),          -- "1" (>100 stores) / "2" (20-99) / "3" (<20)
    dt                      date        NOT NULL,
    total_sales             float8,
    product_count           int,
    active_product_count    int,
    avg_sales_per_product   float8,
    stockout_product_rate   float8,
    severe_stockout_rate    float8,
    avg_discount            float8,
    discounted_product_rate float8,
    activity_product_rate   float8,
    activity_sales_share    float8,
    holiday_flag            boolean,
    is_weekend              boolean,
    weekday                 text,
    PRIMARY KEY (city_id, dt)
);
CREATE INDEX IF NOT EXISTS idx_rca_city_series_dt ON public.rca_city_series (dt);

ALTER TABLE public.rca_city_series ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_rca_city_series" ON public.rca_city_series;
CREATE POLICY "anon_read_rca_city_series" ON public.rca_city_series FOR SELECT TO anon USING (true);

-- ============================================================
-- 4. rca_city_normals  (per-city sales baselines)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.rca_city_normals (
    city_id       smallint    PRIMARY KEY,
    density_tier  char(1),
    p25_sale      float8,
    p50_sale      float8,
    p75_sale      float8,
    avg_sale      float8,
    stddev_sale   float8,
    dow_pattern   jsonb,
    updated_at    timestamptz DEFAULT now()
);

ALTER TABLE public.rca_city_normals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_rca_city_normals" ON public.rca_city_normals;
CREATE POLICY "anon_read_rca_city_normals" ON public.rca_city_normals FOR SELECT TO anon USING (true);

-- ============================================================
-- 5. rca_city_profile  (episodic LLM memory per city)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.rca_city_profile (
    city_id           smallint    PRIMARY KEY,
    profile_markdown  text,
    episode_count     int         DEFAULT 0,
    distilled_at      timestamptz,
    updated_at        timestamptz DEFAULT now()
);

ALTER TABLE public.rca_city_profile ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_rca_city_profile" ON public.rca_city_profile;
CREATE POLICY "anon_read_rca_city_profile" ON public.rca_city_profile FOR SELECT TO anon USING (true);

-- ============================================================
-- 6. Analytics placeholder tables (populated in Round C)
-- ============================================================

-- rca_city_signal: STL residual + anomaly score per city-day
CREATE TABLE IF NOT EXISTS public.rca_city_signal (
    city_id         smallint    NOT NULL,
    dt              date        NOT NULL,
    stl_residual    float8,     -- detrended, deseasonalized residual
    residual_zscore float8,     -- robust z-score (median+MAD)
    signal_label    text,       -- "drop" | "lift" | "neutral" | "warmup"
    PRIMARY KEY (city_id, dt)
);
ALTER TABLE public.rca_city_signal ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_rca_city_signal" ON public.rca_city_signal;
CREATE POLICY "anon_read_rca_city_signal" ON public.rca_city_signal FOR SELECT TO anon USING (true);

-- rca_city_segment: KMeans cluster label per city
CREATE TABLE IF NOT EXISTS public.rca_city_segment (
    city_id         smallint    PRIMARY KEY,
    cluster_id      smallint,
    segment_label   text,       -- e.g. "steady high-volume", "volatile low-volume"
    updated_at      timestamptz DEFAULT now()
);
ALTER TABLE public.rca_city_segment ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_rca_city_segment" ON public.rca_city_segment;
CREATE POLICY "anon_read_rca_city_segment" ON public.rca_city_segment FOR SELECT TO anon USING (true);

-- rca_city_correlations: per-city driver correlation priors
CREATE TABLE IF NOT EXISTS public.rca_city_correlations (
    city_id                 smallint    PRIMARY KEY,
    corr_stockout           float8,
    corr_discount           float8,
    corr_activity           float8,
    corr_precpt             float8,
    corr_temperature        float8,
    updated_at              timestamptz DEFAULT now()
);
ALTER TABLE public.rca_city_correlations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_rca_city_correlations" ON public.rca_city_correlations;
CREATE POLICY "anon_read_rca_city_correlations" ON public.rca_city_correlations FOR SELECT TO anon USING (true);

-- rca_city_hourly: 24-hour intraday city-day profile
CREATE TABLE IF NOT EXISTS public.rca_city_hourly (
    city_id         smallint    NOT NULL,
    dt              date        NOT NULL,
    hour            smallint    NOT NULL CHECK (hour BETWEEN 0 AND 23),
    sales           float8,
    sales_share     float8,     -- this hour's % of city-day total
    deviation_z     float8,     -- z-score vs city's typical hourly shape
    stockout_rate   float8,
    PRIMARY KEY (city_id, dt, hour)
);
ALTER TABLE public.rca_city_hourly ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_rca_city_hourly" ON public.rca_city_hourly;
CREATE POLICY "anon_read_rca_city_hourly" ON public.rca_city_hourly FOR SELECT TO anon USING (true);
