-- Migration 0009: Full Supabase migration
--
-- Changes:
--   rca_city_series: add missing detail columns (stockout detail, discount detail, weather, holiday detail)
--   DROP rca_city_signal (STL approach retired; finance-forecast is the sole trigger)
--   CREATE VIEW rca_city_signal_v — pct-change vs forecast + trailing baselines + drop/lift label
--   Grant anon SELECT on the view
--
-- Run in Supabase SQL Editor (service role). Safe to re-run (idempotent).

-- ============================================================
-- 1. Expand rca_city_series with missing columns
-- ============================================================

ALTER TABLE public.rca_city_series
    ADD COLUMN IF NOT EXISTS avg_stockout_hours        double precision,
    ADD COLUMN IF NOT EXISTS full_stockout_product_rate double precision,
    ADD COLUMN IF NOT EXISTS deep_discount_product_rate double precision,
    ADD COLUMN IF NOT EXISTS precpt                    double precision,
    ADD COLUMN IF NOT EXISTS avg_temperature           double precision,
    ADD COLUMN IF NOT EXISTS avg_humidity              double precision,
    ADD COLUMN IF NOT EXISTS avg_wind_level            double precision,
    ADD COLUMN IF NOT EXISTS holiday_name_inferred     text,
    ADD COLUMN IF NOT EXISTS holiday_note              text;

-- ============================================================
-- 2. Drop STL signal table (replaced by the view below)
-- ============================================================

DROP TABLE IF EXISTS public.rca_city_signal CASCADE;

-- ============================================================
-- 3. Create signal view (finance-forecast trigger, pct baselines)
-- ============================================================
-- Drop first so re-runs are safe
DROP VIEW IF EXISTS public.rca_city_signal_v CASCADE;

CREATE VIEW public.rca_city_signal_v AS
WITH lagged AS (
    SELECT
        s.city_id,
        s.dt,
        s.total_sales,
        s.weekday,
        s.density_tier,
        s.holiday_name_inferred,
        f.forecast_sales,
        LAG(s.total_sales, 1) OVER (PARTITION BY s.city_id ORDER BY s.dt) AS previous_day_sales
    FROM public.rca_city_series s
    LEFT JOIN public.rca_finance_forecast f USING (city_id, dt)
),
windowed AS (
    SELECT
        city_id,
        dt,
        total_sales,
        weekday,
        density_tier,
        holiday_name_inferred,
        previous_day_sales,
        forecast_sales,
        AVG(total_sales) OVER (
            PARTITION BY city_id
            ORDER BY dt
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS trailing_7d_avg_sales,
        AVG(total_sales) OVER (
            PARTITION BY city_id, weekday
            ORDER BY dt
            ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING
        ) AS same_weekday_4w_avg_sales
    FROM lagged
)
SELECT
    city_id,
    dt,
    total_sales,
    weekday,
    density_tier,
    holiday_name_inferred,
    previous_day_sales,
    trailing_7d_avg_sales,
    same_weekday_4w_avg_sales,
    forecast_sales,
    CASE WHEN previous_day_sales > 0
         THEN (total_sales - previous_day_sales) / previous_day_sales * 100.0
    END AS day_over_day_pct_change,
    CASE WHEN trailing_7d_avg_sales > 0
         THEN (total_sales - trailing_7d_avg_sales) / trailing_7d_avg_sales * 100.0
    END AS trailing_7d_pct_change,
    CASE WHEN same_weekday_4w_avg_sales > 0
         THEN (total_sales - same_weekday_4w_avg_sales) / same_weekday_4w_avg_sales * 100.0
    END AS same_weekday_4w_pct_change,
    CASE WHEN forecast_sales > 0
         THEN (total_sales - forecast_sales) / forecast_sales * 100.0
    END AS finance_forecast_pct_change,
    CASE
        WHEN forecast_sales IS NULL OR forecast_sales = 0
            THEN 'insufficient_history'
        WHEN (total_sales - forecast_sales) / forecast_sales * 100.0 <= -10.0
            THEN 'drop'
        WHEN (total_sales - forecast_sales) / forecast_sales * 100.0 >= 25.0
            THEN 'lift'
        ELSE 'neutral'
    END AS signal_label
FROM windowed;

-- ============================================================
-- 4. Grant anon read access to the view
-- ============================================================

GRANT SELECT ON public.rca_city_signal_v TO anon;
GRANT SELECT ON public.rca_city_signal_v TO authenticated;
