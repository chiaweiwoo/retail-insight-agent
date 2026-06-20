-- Migration 0006: fix column types on pre-existing city tables
-- The 0005 migration used CREATE TABLE IF NOT EXISTS, so tables that already
-- existed kept their old schemas (city_id text, prefix char). This fixes them.
--
-- Changes:
--   rca_city_series:  city_id text→smallint, prefix→density_tier
--   rca_city_normals: city_id text→smallint, prefix→density_tier
--   rca_city_profile: city_id text→smallint
--   rca_outcome:      city_id text→smallint

-- ============================================================
-- rca_city_series
-- ============================================================

-- Rename column first (column rename doesn't require dropping PK)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rca_city_series'
          AND column_name = 'prefix'
    ) THEN
        ALTER TABLE public.rca_city_series RENAME COLUMN prefix TO density_tier;
    END IF;
END $$;

-- Change city_id to smallint (requires drop+recreate of PK)
ALTER TABLE public.rca_city_series DROP CONSTRAINT IF EXISTS rca_store_series_pkey;
ALTER TABLE public.rca_city_series
    ALTER COLUMN city_id TYPE smallint USING city_id::smallint;
ALTER TABLE public.rca_city_series ADD PRIMARY KEY (city_id, dt);

-- ============================================================
-- rca_city_normals
-- ============================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rca_city_normals'
          AND column_name = 'prefix'
    ) THEN
        ALTER TABLE public.rca_city_normals RENAME COLUMN prefix TO density_tier;
    END IF;
END $$;

ALTER TABLE public.rca_city_normals DROP CONSTRAINT IF EXISTS rca_store_normals_pkey;
ALTER TABLE public.rca_city_normals
    ALTER COLUMN city_id TYPE smallint USING city_id::smallint;
ALTER TABLE public.rca_city_normals ADD PRIMARY KEY (city_id);

-- ============================================================
-- rca_city_profile
-- ============================================================

ALTER TABLE public.rca_city_profile DROP CONSTRAINT IF EXISTS rca_store_profile_pkey;
ALTER TABLE public.rca_city_profile
    ALTER COLUMN city_id TYPE smallint USING city_id::smallint;
ALTER TABLE public.rca_city_profile ADD PRIMARY KEY (city_id);

-- ============================================================
-- rca_outcome
-- ============================================================

-- city_id is NOT part of the PK (PK is id bigserial), safe to alter directly
ALTER TABLE public.rca_outcome
    ALTER COLUMN city_id TYPE smallint USING city_id::smallint;

DROP INDEX IF EXISTS public.idx_rca_outcome_city;
CREATE INDEX IF NOT EXISTS idx_rca_outcome_city ON public.rca_outcome (city_id, dt DESC);
