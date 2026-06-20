-- Migration 0007: outcome table — overwrite-per-city-day model
--
-- Changes:
--   TRUNCATE rca_outcome (all rows are store-era with null city_id, safe to drop)
--   DROP UNIQUE constraint on run_name
--   ADD UNIQUE (city_id, dt) — new conflict key (one row per triggered day per city)
--   ADD report_markdown text — full drill-down RCA from rca run
--   ADD story_markdown text  — polished narrative from rca story (nullable)
--   ADD generated_at timestamptz — when this row was last written/updated
--   DROP created_at (replaced by generated_at)
--   Enable RLS + anon read policy
--
-- Run in Supabase SQL Editor (service role). Safe to re-run (idempotent).

-- ============================================================
-- 1. Clear store-era rows (all have null city_id post-0005)
-- ============================================================

TRUNCATE TABLE public.rca_outcome;

-- ============================================================
-- 2. Drop old run_name unique constraint
-- ============================================================

ALTER TABLE public.rca_outcome
    DROP CONSTRAINT IF EXISTS rca_outcome_run_name_key;

-- ============================================================
-- 3. Add new columns
-- ============================================================

ALTER TABLE public.rca_outcome
    ADD COLUMN IF NOT EXISTS report_markdown  text,
    ADD COLUMN IF NOT EXISTS story_markdown   text,
    ADD COLUMN IF NOT EXISTS generated_at     timestamptz DEFAULT now();

-- ============================================================
-- 4. Drop created_at (superseded by generated_at)
-- ============================================================

ALTER TABLE public.rca_outcome
    DROP COLUMN IF EXISTS created_at;

-- ============================================================
-- 5. Add unique constraint on (city_id, dt)
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name   = 'rca_outcome'
          AND constraint_type = 'UNIQUE'
          AND constraint_name = 'rca_outcome_city_dt_key'
    ) THEN
        ALTER TABLE public.rca_outcome
            ADD CONSTRAINT rca_outcome_city_dt_key UNIQUE (city_id, dt);
    END IF;
END $$;

-- ============================================================
-- 6. Refresh index
-- ============================================================

DROP INDEX IF EXISTS public.idx_rca_outcome_city;
CREATE INDEX IF NOT EXISTS idx_rca_outcome_city ON public.rca_outcome (city_id, dt DESC);

-- ============================================================
-- 7. RLS
-- ============================================================

ALTER TABLE public.rca_outcome ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_rca_outcome" ON public.rca_outcome;
CREATE POLICY "anon_read_rca_outcome" ON public.rca_outcome FOR SELECT TO anon USING (true);
