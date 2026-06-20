"""Analytics pipeline: intraday profiles, city segments, driver correlations.

All functions take pandas DataFrames — no DuckDB dependency.
Called from database.ingest_to_supabase() at build time.
Results are pushed to Supabase rca_city_* tables.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

N_CLUSTERS = 4

_SEGMENT_LABELS = {
    0: "steady high-volume",
    1: "volatile high-volume",
    2: "steady low-volume",
    3: "volatile low-volume",
}


def compute_intraday_profiles(
    sales_df: pd.DataFrame,
    stockout_df: pd.DataFrame,
) -> pd.DataFrame:
    """Per-city-day: hourly sales, sales share, deviation z-score vs city's typical shape.

    Args:
        sales_df: output of build_fact_sales_city_day (has hour_00_sales...hour_23_sales)
        stockout_df: output of build_fact_stockout_city_day (has hour_00_stockout_rate...)
    Returns:
        DataFrame with columns (city_id, dt, hour, sales, sales_share, deviation_z, stockout_rate)
    """
    h_sales_cols = [f"hour_{h:02d}_sales" for h in range(24)]
    h_so_cols = [f"hour_{h:02d}_stockout_rate" for h in range(24)]

    records: list[dict] = []

    for city_id, city_sales in sales_df.groupby("city_id"):
        city_sales = city_sales.sort_values("dt").reset_index(drop=True)
        city_so = stockout_df[stockout_df["city_id"] == city_id].set_index("dt")

        sales_mat = city_sales[h_sales_cols].values.astype(float)
        totals = city_sales["total_sales"].values.astype(float)

        safe_totals = np.where(totals > 0, totals, 1.0)
        share_mat = sales_mat / safe_totals[:, None]

        typical_share = np.median(share_mat, axis=0)
        typical_std = np.std(share_mat, axis=0)

        for row_i, row in city_sales.iterrows():
            dt_str = (
                row["dt"].strftime("%Y-%m-%d")
                if hasattr(row["dt"], "strftime")
                else str(row["dt"])
            )
            so_row = city_so.loc[row["dt"]] if row["dt"] in city_so.index else None

            for h in range(24):
                hour_sales_val = float(sales_mat[city_sales.index.get_loc(row_i), h])
                hour_share = float(share_mat[city_sales.index.get_loc(row_i), h])

                std = typical_std[h]
                dev_z = float((hour_share - typical_share[h]) / std) if std > 0 else 0.0

                so_col = f"hour_{h:02d}_stockout_rate"
                stockout_rate = None
                if so_row is not None and so_col in so_row.index:
                    stockout_rate = float(so_row[so_col])

                records.append({
                    "city_id": int(city_id),
                    "dt": dt_str,
                    "hour": h,
                    "sales": round(hour_sales_val, 4),
                    "sales_share": round(hour_share, 6),
                    "deviation_z": round(dev_z, 4),
                    "stockout_rate": round(stockout_rate, 6) if stockout_rate is not None else None,
                })

    return pd.DataFrame(records)


def compute_city_segments(series_df: pd.DataFrame) -> pd.DataFrame:
    """KMeans(k=4) on per-city feature vectors; assign human-readable segment labels.

    Args:
        series_df: output of build_city_series_df (has total_sales, stockout rates, etc.)
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    features = (
        series_df.groupby("city_id", as_index=False)
        .agg(
            avg_sales=("total_sales", "mean"),
            stddev_sales=("total_sales", "std"),
            avg_stockout=("stockout_product_rate", "mean"),
            avg_discount_rate=("discounted_product_rate", "mean"),
            avg_activity_rate=("activity_product_rate", "mean"),
        )
    )

    if features.empty:
        return pd.DataFrame(columns=["city_id", "cluster_id", "segment_label"])

    X = features[
        ["avg_sales", "stddev_sales", "avg_stockout", "avg_discount_rate", "avg_activity_rate"]
    ].values
    X_scaled = StandardScaler().fit_transform(X)

    k = min(N_CLUSTERS, len(features))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(X_scaled)

    centroids = kmeans.cluster_centers_
    cluster_avg_sales = centroids[:, 0]
    cluster_volatility = centroids[:, 1]

    median_sales = np.median(cluster_avg_sales)
    median_vol = np.median(cluster_volatility)

    def _label(idx: int) -> str:
        high_sales = cluster_avg_sales[idx] >= median_sales
        high_vol = cluster_volatility[idx] >= median_vol
        return f"{'volatile' if high_vol else 'steady'} {'high-volume' if high_sales else 'low-volume'}"

    records = [
        {
            "city_id": int(features.iloc[i]["city_id"]),
            "cluster_id": int(cluster_ids[i]),
            "segment_label": _label(int(cluster_ids[i])),
        }
        for i in range(len(features))
    ]
    return pd.DataFrame(records)


def compute_driver_correlations(series_df: pd.DataFrame) -> pd.DataFrame:
    """Correlate normalized sales vs stockout/discount/activity/weather per city.

    Uses total_sales / city_mean as the sales proxy (removes city-size effect).
    """
    df = series_df.copy()

    city_mean = df.groupby("city_id")["total_sales"].transform("mean")
    df["sales_norm"] = df["total_sales"] / city_mean.replace(0, np.nan)

    records: list[dict] = []
    for city_id, group in df.groupby("city_id"):
        if len(group) < 7:
            continue

        def safe_corr(col: str) -> float | None:
            if col not in group.columns:
                return None
            try:
                c = float(group["sales_norm"].corr(group[col]))
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
