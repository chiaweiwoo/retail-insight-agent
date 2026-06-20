-- Migration 0010: Replace rca_city_signal_v VIEW with rca_city_signal stored table.
--
-- Why: Thresholds now live solely in Python config (not duplicated in SQL).
--      The full trigger series becomes visible to the dashboard without re-querying
--      rca_city_series + rca_finance_forecast at read time.
--      rca analyze populates this table; rca run reads triggered dates from it.

-- Drop the real-time view we're replacing
DROP VIEW IF EXISTS rca_city_signal_v;

-- Precomputed trigger table — one row per (city, day)
CREATE TABLE IF NOT EXISTS rca_city_signal (
    city_id                   INTEGER     NOT NULL,
    dt                        TEXT        NOT NULL,
    total_sales               FLOAT,
    business_target           FLOAT,
    target_deviation_pct      FLOAT,
    signal_label              TEXT        NOT NULL DEFAULT 'neutral',
    previous_day_sales        FLOAT,
    trailing_7d_avg_sales     FLOAT,
    same_weekday_4w_avg_sales FLOAT,
    day_over_day_pct_change   FLOAT,
    trailing_7d_pct_change    FLOAT,
    same_weekday_4w_pct_change FLOAT,
    weekday                   TEXT,
    density_tier              TEXT,
    holiday_name_inferred     TEXT,
    PRIMARY KEY (city_id, dt)
);

-- RLS: public read, service-role write
ALTER TABLE rca_city_signal ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_city_signal" ON rca_city_signal;
CREATE POLICY "anon_read_city_signal"
    ON rca_city_signal FOR SELECT
    USING (true);

GRANT SELECT ON rca_city_signal TO anon, authenticated;
