-- Migration: Create Finance Forecast Table
CREATE TABLE IF NOT EXISTS public.rca_finance_forecast (
    city_id smallint NOT NULL,
    dt date NOT NULL,
    forecast_sales double precision NOT NULL,
    PRIMARY KEY (city_id, dt)
);

CREATE INDEX IF NOT EXISTS idx_rca_finance_forecast_dt ON public.rca_finance_forecast (dt);

ALTER TABLE public.rca_finance_forecast ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_rca_finance_forecast" ON public.rca_finance_forecast;
CREATE POLICY "anon_read_rca_finance_forecast" ON public.rca_finance_forecast FOR SELECT TO anon USING (true);
