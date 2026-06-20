-- Move retail_rca tables to public schema with rca_ prefix.
-- PostgREST on Supabase free tier only exposes `public` by default.
-- Tables: rca_store_series, rca_store_normals, rca_outcome, rca_store_profile
-- Applied via Supabase MCP (migration name: retail_rca_0004_move_to_public_schema)

CREATE TABLE IF NOT EXISTS public.rca_store_series (
    store_id                text        NOT NULL,
    city_id                 smallint    NOT NULL,
    prefix                  char(1)     NOT NULL,
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
    PRIMARY KEY (store_id, dt)
);
CREATE INDEX IF NOT EXISTS idx_rca_store_series_city_dt ON public.rca_store_series (city_id, dt);
CREATE INDEX IF NOT EXISTS idx_rca_store_series_store   ON public.rca_store_series (store_id);

CREATE TABLE IF NOT EXISTS public.rca_store_normals (
    store_id      text PRIMARY KEY,
    city_id       smallint    NOT NULL,
    prefix        char(1)     NOT NULL,
    p25_sale      float8,
    p50_sale      float8,
    p75_sale      float8,
    avg_sale      float8,
    stddev_sale   float8,
    dow_pattern   jsonb,
    updated_at    timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.rca_outcome (
    id                      bigserial PRIMARY KEY,
    run_name                text        UNIQUE NOT NULL,
    store_id                text        NOT NULL,
    dt                      date        NOT NULL,
    signal_label            text,
    top_driver              text,
    driver_class            text,
    confidence              text,
    escalated               boolean     DEFAULT false,
    brief_headline          text,
    decision_card_markdown  text,
    created_at              timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rca_outcome_store ON public.rca_outcome (store_id, dt DESC);

CREATE TABLE IF NOT EXISTS public.rca_store_profile (
    store_id          text PRIMARY KEY,
    city_id           smallint,
    profile_markdown  text,
    episode_count     int         DEFAULT 0,
    distilled_at      timestamptz,
    updated_at        timestamptz DEFAULT now()
);

ALTER TABLE public.rca_store_series   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rca_store_normals  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rca_outcome        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rca_store_profile  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_rca_store_series"   ON public.rca_store_series  FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_rca_store_normals"  ON public.rca_store_normals FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_rca_outcome"        ON public.rca_outcome        FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_rca_store_profile"  ON public.rca_store_profile  FOR SELECT TO anon USING (true);

DROP TABLE IF EXISTS retail_rca.store_series  CASCADE;
DROP TABLE IF EXISTS retail_rca.store_normals CASCADE;
DROP TABLE IF EXISTS retail_rca.rca_outcome   CASCADE;
DROP TABLE IF EXISTS retail_rca.store_profile CASCADE;
DROP SCHEMA IF EXISTS retail_rca CASCADE;
