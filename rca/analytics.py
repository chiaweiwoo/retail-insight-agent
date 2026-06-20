"""Analytics pipeline: STL signals, intraday profiles, city segments, driver correlations.

Run after ingest_to_duckdb() via run_analytics_pipeline().
Results land in analytics_city_* tables in local DuckDB, then sync to Supabase rca_city_*.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from rca.config import DB_PATH

WARMUP_DAYS = 7       # first N days per city get signal_label = "warmup"
DROP_THRESHOLD_Z = 2.0
LIFT_THRESHOLD_Z = 2.0
N_CLUSTERS = 4

_SEGMENT_LABELS = {
    0: "steady high-volume",
    1: "volatile high-volume",
    2: "steady low-volume",
    3: "volatile low-volume",
}


def compute_stl_signals(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Run STL(period=7) per city, robust z-score on residual, assign signal labels."""
    from statsmodels.tsa.seasonal import STL

    df = con.execute(
        "SELECT city_id, CAST(dt AS VARCHAR) AS dt, total_sales "
        "FROM fact_sales_city_day ORDER BY city_id, dt"
    ).fetchdf()

    records: list[dict] = []
    for city_id, group in df.groupby("city_id"):
        group = group.sort_values("dt").reset_index(drop=True)
        dates = group["dt"].tolist()
        sales = group["total_sales"].values.astype(float)
        n = len(sales)

        if n < 14:
            for dt in dates:
                records.append({
                    "city_id": int(city_id), "dt": dt,
                    "stl_residual": None, "residual_zscore": None,
                    "signal_label": "warmup",
                })
            continue

        fit = STL(sales, period=7, robust=True).fit()
        residuals = fit.resid

        median = np.median(residuals)
        mad = np.median(np.abs(residuals - median))
        scale = mad * 1.4826 if mad > 0 else 1.0
        zscores = (residuals - median) / scale

        for i, dt in enumerate(dates):
            is_warmup = i < WARMUP_DAYS
            z = float(zscores[i])
            r = float(residuals[i])

            if is_warmup:
                label = "warmup"
            elif z <= -DROP_THRESHOLD_Z:
                label = "drop"
            elif z >= LIFT_THRESHOLD_Z:
                label = "lift"
            else:
                label = "neutral"

            records.append({
                "city_id": int(city_id),
                "dt": dt,
                "stl_residual": None if is_warmup else round(r, 6),
                "residual_zscore": None if is_warmup else round(z, 4),
                "signal_label": label,
            })

    return pd.DataFrame(records)


def compute_intraday_profiles(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Per-city-day: hourly sales, sales share, deviation z-score vs city's typical shape."""
    hour_sales = ", ".join(f"hour_{h:02d}_sales" for h in range(24))
    hour_so = ", ".join(f"hour_{h:02d}_stockout_rate" for h in range(24))

    sales_df = con.execute(
        f"SELECT city_id, CAST(dt AS VARCHAR) AS dt, total_sales, {hour_sales} "
        "FROM fact_sales_city_day ORDER BY city_id, dt"
    ).fetchdf()

    so_df = con.execute(
        f"SELECT city_id, CAST(dt AS VARCHAR) AS dt, {hour_so} "
        "FROM fact_stockout_city_day ORDER BY city_id, dt"
    ).fetchdf()

    records: list[dict] = []
    for city_id, city_sales in sales_df.groupby("city_id"):
        city_sales = city_sales.sort_values("dt").reset_index(drop=True)
        city_so = so_df[so_df["city_id"] == city_id].set_index("dt")

        h_cols = [f"hour_{h:02d}_sales" for h in range(24)]
        sales_mat = city_sales[h_cols].values.astype(float)
        totals = city_sales["total_sales"].values.astype(float)

        safe_totals = np.where(totals > 0, totals, 1.0)
        share_mat = sales_mat / safe_totals[:, None]

        typical_share = np.median(share_mat, axis=0)
        typical_std = np.std(share_mat, axis=0)

        for row_i, dt in enumerate(city_sales["dt"].tolist()):
            day_total = float(totals[row_i])
            so_row = city_so.loc[dt] if dt in city_so.index else None

            for h in range(24):
                hour_sales_val = float(sales_mat[row_i, h])
                hour_share = float(share_mat[row_i, h])

                std = typical_std[h]
                dev_z = float((hour_share - typical_share[h]) / std) if std > 0 else 0.0

                so_col = f"hour_{h:02d}_stockout_rate"
                stockout_rate = None
                if so_row is not None and so_col in so_row:
                    stockout_rate = float(so_row[so_col])

                records.append({
                    "city_id": int(city_id),
                    "dt": dt,
                    "hour": h,
                    "sales": round(hour_sales_val, 4),
                    "sales_share": round(hour_share, 6),
                    "deviation_z": round(dev_z, 4),
                    "stockout_rate": round(stockout_rate, 6) if stockout_rate is not None else None,
                })

    return pd.DataFrame(records)


def compute_city_segments(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """KMeans(k=4) on per-city feature vectors; assign human-readable segment labels."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    features = con.execute(
        """
        SELECT
            s.city_id,
            AVG(s.total_sales)             AS avg_sales,
            STDDEV(s.total_sales)          AS stddev_sales,
            AVG(st.stockout_product_rate)  AS avg_stockout,
            AVG(d.discounted_product_rate) AS avg_discount_rate,
            AVG(a.activity_product_rate)   AS avg_activity_rate
        FROM fact_sales_city_day s
        JOIN fact_stockout_city_day st USING (city_id, dt)
        JOIN fact_discount_city_day d  USING (city_id, dt)
        JOIN fact_activity_city_day a  USING (city_id, dt)
        GROUP BY s.city_id
        ORDER BY s.city_id
        """
    ).fetchdf()

    if features.empty:
        return pd.DataFrame(columns=["city_id", "cluster_id", "segment_label"])

    X = features[["avg_sales", "stddev_sales", "avg_stockout", "avg_discount_rate", "avg_activity_rate"]].values
    X_scaled = StandardScaler().fit_transform(X)

    k = min(N_CLUSTERS, len(features))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(X_scaled)

    # Map cluster ids to descriptive labels based on centroid characteristics
    centroids = kmeans.cluster_centers_
    cluster_avg_sales = centroids[:, 0]   # first feature is avg_sales (standardized)
    cluster_volatility = centroids[:, 1]  # second feature is stddev_sales (standardized)

    median_sales = np.median(cluster_avg_sales)
    median_vol = np.median(cluster_volatility)

    def _label(cluster_idx: int) -> str:
        high_sales = cluster_avg_sales[cluster_idx] >= median_sales
        high_vol = cluster_volatility[cluster_idx] >= median_vol
        sales_word = "high-volume" if high_sales else "low-volume"
        vol_word = "volatile" if high_vol else "steady"
        return f"{vol_word} {sales_word}"

    records = [
        {
            "city_id": int(features.iloc[i]["city_id"]),
            "cluster_id": int(cluster_ids[i]),
            "segment_label": _label(int(cluster_ids[i])),
        }
        for i in range(len(features))
    ]
    return pd.DataFrame(records)


def compute_driver_correlations(
    con: duckdb.DuckDBPyConnection,
    signals_df: pd.DataFrame,
) -> pd.DataFrame:
    """Correlate STL residual vs stockout/discount/activity/weather per city."""
    drivers = con.execute(
        """
        SELECT
            s.city_id,
            CAST(s.dt AS VARCHAR) AS dt,
            st.stockout_product_rate,
            d.avg_discount,
            a.activity_product_rate,
            w.precpt,
            w.avg_temperature
        FROM fact_sales_city_day s
        JOIN fact_stockout_city_day st USING (city_id, dt)
        JOIN fact_discount_city_day d  USING (city_id, dt)
        JOIN fact_activity_city_day a  USING (city_id, dt)
        JOIN dim_weather_day w         USING (dt)
        ORDER BY s.city_id, s.dt
        """
    ).fetchdf()

    valid_signals = signals_df[signals_df["stl_residual"].notna()].copy()
    merged = valid_signals.merge(drivers, on=["city_id", "dt"], how="inner")

    records: list[dict] = []
    for city_id, group in merged.groupby("city_id"):
        if len(group) < 7:
            continue

        def safe_corr(col: str) -> float | None:
            try:
                c = float(group["stl_residual"].corr(group[col]))
                return round(c, 4) if not np.isnan(c) else None
            except Exception:
                return None

        records.append({
            "city_id": int(city_id),
            "corr_stockout": safe_corr("stockout_product_rate"),
            "corr_discount": safe_corr("avg_discount"),
            "corr_activity": safe_corr("activity_product_rate"),
            "corr_precpt": safe_corr("precpt"),
            "corr_temperature": safe_corr("avg_temperature"),
        })

    return pd.DataFrame(records)


def _ensure_analytics_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_city_signal (
            city_id      INTEGER NOT NULL,
            dt           DATE    NOT NULL,
            stl_residual DOUBLE,
            residual_zscore DOUBLE,
            signal_label TEXT,
            PRIMARY KEY (city_id, dt)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_city_hourly (
            city_id      INTEGER NOT NULL,
            dt           DATE    NOT NULL,
            hour         INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
            sales        DOUBLE,
            sales_share  DOUBLE,
            deviation_z  DOUBLE,
            stockout_rate DOUBLE,
            PRIMARY KEY (city_id, dt, hour)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_city_segment (
            city_id       INTEGER PRIMARY KEY,
            cluster_id    INTEGER,
            segment_label TEXT
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_city_correlations (
            city_id          INTEGER PRIMARY KEY,
            corr_stockout    DOUBLE,
            corr_discount    DOUBLE,
            corr_activity    DOUBLE,
            corr_precpt      DOUBLE,
            corr_temperature DOUBLE
        )
        """
    )


def _insert_df(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> int:
    """Truncate + insert a DataFrame into a DuckDB table."""
    con.execute(f"DELETE FROM {table}")
    if df.empty:
        return 0
    con.register("_staging", df)
    con.execute(f"INSERT INTO {table} SELECT * FROM _staging")
    con.unregister("_staging")
    return len(df)


def run_analytics_pipeline(db_path: Path = DB_PATH) -> dict[str, int]:
    """Compute all analytics layers and store results in DuckDB analytics tables.

    Returns row counts for each analytics table.
    """
    con = duckdb.connect(str(db_path))
    try:
        _ensure_analytics_tables(con)

        print("  STL signals...")
        signals = compute_stl_signals(con)
        # Cast dt to DATE for DuckDB insert
        signals["dt"] = pd.to_datetime(signals["dt"]).dt.date
        n_signal = _insert_df(con, "analytics_city_signal", signals)

        # Re-fetch signals with string dt for join with drivers
        signals_str = signals.copy()
        signals_str["dt"] = signals_str["dt"].astype(str)

        print("  Intraday profiles...")
        hourly = compute_intraday_profiles(con)
        hourly["dt"] = pd.to_datetime(hourly["dt"]).dt.date
        n_hourly = _insert_df(con, "analytics_city_hourly", hourly)

        print("  City segments...")
        segments = compute_city_segments(con)
        n_segments = _insert_df(con, "analytics_city_segment", segments)

        print("  Driver correlations...")
        correlations = compute_driver_correlations(con, signals_str)
        n_correlations = _insert_df(con, "analytics_city_correlations", correlations)

    finally:
        con.close()

    return {
        "analytics_city_signal": n_signal,
        "analytics_city_hourly": n_hourly,
        "analytics_city_segment": n_segments,
        "analytics_city_correlations": n_correlations,
    }
