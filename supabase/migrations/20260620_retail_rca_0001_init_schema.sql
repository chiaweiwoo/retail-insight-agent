-- retail_rca schema + tables
-- Applied via Supabase MCP (migration name: retail_rca_0001_init_schema)

CREATE SCHEMA IF NOT EXISTS retail_rca;

-- time-series sales rows ingested from parquet
CREATE TABLE IF NOT EXISTS retail_rca.store_series (
    id                    bigserial PRIMARY KEY,
    store_id              text        NOT NULL,
    city_id               smallint    NOT NULL,
    product_id            int         NOT NULL,
    dt                    date        NOT NULL,
    sale_amount           float8,
    hours_sale            float8,
    management_group_id   smallint,
    first_category_id     smallint,
    second_category_id    smallint,
    third_category_id     smallint,
    UNIQUE (store_id, product_id, dt)
);
CREATE INDEX IF NOT EXISTS idx_store_series_store_dt
    ON retail_rca.store_series (store_id, dt);
CREATE INDEX IF NOT EXISTS idx_store_series_city_dt
    ON retail_rca.store_series (city_id, dt);

-- pre-computed per-store baselines
CREATE TABLE IF NOT EXISTS retail_rca.store_normals (
    store_id      text PRIMARY KEY,
    city_id       smallint    NOT NULL,
    prefix        char(1)     NOT NULL,
    p25_sale      float8,
    p50_sale      float8,
    p75_sale      float8,
    avg_sale      float8,
    stddev_sale   float8,
    dow_pattern   jsonb,        -- {"0": 0.91, "1": 1.03, ...} Mon=0..Sun=6
    updated_at    timestamptz DEFAULT now()
);

-- episodic run memory
CREATE TABLE IF NOT EXISTS retail_rca.rca_outcome (
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
CREATE INDEX IF NOT EXISTS idx_rca_outcome_store
    ON retail_rca.rca_outcome (store_id, dt DESC);

-- distilled per-store semantic memory (populated by `rca distil` in Round 2)
CREATE TABLE IF NOT EXISTS retail_rca.store_profile (
    store_id          text PRIMARY KEY,
    city_id           smallint,
    profile_markdown  text,
    episode_count     int         DEFAULT 0,
    distilled_at      timestamptz,
    updated_at        timestamptz DEFAULT now()
);
