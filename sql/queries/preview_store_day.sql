SELECT
    s.store_alias,
    s.dt,
    s.product_count,
    s.active_product_count,
    s.total_sales,
    st.avg_stockout_hours,
    st.stockout_product_rate,
    d.avg_discount,
    d.discounted_product_rate,
    a.activity_product_rate,
    a.activity_sales_share,
    h.weekday,
    h.holiday_name_inferred,
    w.precpt,
    w.avg_temperature,
    w.avg_humidity,
    w.avg_wind_level
FROM fact_sales_store_day AS s
JOIN fact_stockout_store_day AS st USING (store_alias, dt)
JOIN fact_discount_store_day AS d USING (store_alias, dt)
JOIN fact_activity_store_day AS a USING (store_alias, dt)
JOIN dim_holiday_day AS h USING (dt)
JOIN dim_weather_day AS w USING (dt)
WHERE s.store_alias = 'h263'
  AND s.dt = DATE '2024-06-24';
