CREATE TABLE dim_city (
    city_id INTEGER PRIMARY KEY,
    store_count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE dim_holiday_day (
    dt DATE PRIMARY KEY,
    weekday TEXT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    holiday_flag BOOLEAN NOT NULL,
    holiday_name_inferred TEXT NOT NULL,
    holiday_note TEXT NOT NULL
);

CREATE TABLE dim_weather_day (
    dt DATE PRIMARY KEY,
    precpt DOUBLE NOT NULL,
    avg_temperature DOUBLE NOT NULL,
    avg_humidity DOUBLE NOT NULL,
    avg_wind_level DOUBLE NOT NULL
);

CREATE TABLE fact_sales_city_day (
    city_id INTEGER NOT NULL,
    dt DATE NOT NULL,
    product_count INTEGER NOT NULL,
    active_product_count INTEGER NOT NULL,
    total_sales DOUBLE NOT NULL,
    avg_sales_per_product DOUBLE NOT NULL,
    hour_00_sales DOUBLE NOT NULL,
    hour_01_sales DOUBLE NOT NULL,
    hour_02_sales DOUBLE NOT NULL,
    hour_03_sales DOUBLE NOT NULL,
    hour_04_sales DOUBLE NOT NULL,
    hour_05_sales DOUBLE NOT NULL,
    hour_06_sales DOUBLE NOT NULL,
    hour_07_sales DOUBLE NOT NULL,
    hour_08_sales DOUBLE NOT NULL,
    hour_09_sales DOUBLE NOT NULL,
    hour_10_sales DOUBLE NOT NULL,
    hour_11_sales DOUBLE NOT NULL,
    hour_12_sales DOUBLE NOT NULL,
    hour_13_sales DOUBLE NOT NULL,
    hour_14_sales DOUBLE NOT NULL,
    hour_15_sales DOUBLE NOT NULL,
    hour_16_sales DOUBLE NOT NULL,
    hour_17_sales DOUBLE NOT NULL,
    hour_18_sales DOUBLE NOT NULL,
    hour_19_sales DOUBLE NOT NULL,
    hour_20_sales DOUBLE NOT NULL,
    hour_21_sales DOUBLE NOT NULL,
    hour_22_sales DOUBLE NOT NULL,
    hour_23_sales DOUBLE NOT NULL,
    PRIMARY KEY (city_id, dt)
);

CREATE TABLE fact_stockout_city_day (
    city_id INTEGER NOT NULL,
    dt DATE NOT NULL,
    avg_stockout_hours DOUBLE NOT NULL,
    stockout_product_rate DOUBLE NOT NULL,
    severe_stockout_product_rate DOUBLE NOT NULL,
    full_stockout_product_rate DOUBLE NOT NULL,
    hour_00_stockout_rate DOUBLE NOT NULL,
    hour_01_stockout_rate DOUBLE NOT NULL,
    hour_02_stockout_rate DOUBLE NOT NULL,
    hour_03_stockout_rate DOUBLE NOT NULL,
    hour_04_stockout_rate DOUBLE NOT NULL,
    hour_05_stockout_rate DOUBLE NOT NULL,
    hour_06_stockout_rate DOUBLE NOT NULL,
    hour_07_stockout_rate DOUBLE NOT NULL,
    hour_08_stockout_rate DOUBLE NOT NULL,
    hour_09_stockout_rate DOUBLE NOT NULL,
    hour_10_stockout_rate DOUBLE NOT NULL,
    hour_11_stockout_rate DOUBLE NOT NULL,
    hour_12_stockout_rate DOUBLE NOT NULL,
    hour_13_stockout_rate DOUBLE NOT NULL,
    hour_14_stockout_rate DOUBLE NOT NULL,
    hour_15_stockout_rate DOUBLE NOT NULL,
    hour_16_stockout_rate DOUBLE NOT NULL,
    hour_17_stockout_rate DOUBLE NOT NULL,
    hour_18_stockout_rate DOUBLE NOT NULL,
    hour_19_stockout_rate DOUBLE NOT NULL,
    hour_20_stockout_rate DOUBLE NOT NULL,
    hour_21_stockout_rate DOUBLE NOT NULL,
    hour_22_stockout_rate DOUBLE NOT NULL,
    hour_23_stockout_rate DOUBLE NOT NULL,
    PRIMARY KEY (city_id, dt)
);

CREATE TABLE fact_discount_city_day (
    city_id INTEGER NOT NULL,
    dt DATE NOT NULL,
    avg_discount DOUBLE NOT NULL,
    discounted_product_rate DOUBLE NOT NULL,
    deep_discount_product_rate DOUBLE NOT NULL,
    PRIMARY KEY (city_id, dt)
);

CREATE TABLE fact_activity_city_day (
    city_id INTEGER NOT NULL,
    dt DATE NOT NULL,
    activity_product_rate DOUBLE NOT NULL,
    activity_sales_share DOUBLE NOT NULL,
    PRIMARY KEY (city_id, dt)
);
