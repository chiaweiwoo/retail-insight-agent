import duckdb
import pandas as pd
import numpy as np

def analyze():
    # Connect to DuckDB
    con = duckdb.connect("data/rca.duckdb")
    
    # Query all city series
    df = con.execute("""
        SELECT city_id, dt, total_sales
        FROM fact_sales_city_day
        ORDER BY city_id, dt
    """).fetchdf()
    
    # Calculate 7-day trailing average
    # For each city, compute trailing 7 day avg (excluding the current day, or including?
    # standard RCA logic is: (today - trailing_7d_avg) / trailing_7d_avg
    # Let's compute trailing 7d avg excluding today.
    df['dt'] = pd.to_datetime(df['dt'])
    df = df.sort_values(['city_id', 'dt'])
    
    # We use a rolling window of 7, shifted by 1 to exclude current day
    df['trailing_7d_avg'] = df.groupby('city_id')['total_sales'].transform(
        lambda x: x.rolling(window=7, min_periods=3).mean().shift(1)
    )
    
    # Compute pct change
    df['pct_change'] = (df['total_sales'] - df['trailing_7d_avg']) / df['trailing_7d_avg']
    
    # Drop NaNs
    valid = df.dropna(subset=['pct_change']).copy()
    
    print("--- DISTRIBUTION OF 7-DAY TRAILING PERCENTAGE CHANGE ---")
    print(f"Total valid city-days: {len(valid)}")
    print(f"Mean pct_change: {valid['pct_change'].mean():.4f}")
    print(f"Median pct_change: {valid['pct_change'].median():.4f}")
    print(f"Std Dev: {valid['pct_change'].std():.4f}")
    print("\nPercentiles:")
    
    percentiles = [0.01, 0.05, 0.10, 0.15, 0.25, 0.50, 0.75, 0.85, 0.90, 0.95, 0.99]
    for p in percentiles:
        val = valid['pct_change'].quantile(p)
        print(f"P{int(p*100):02d}: {val*100:6.2f}%")

    print("\n--- RECOMMENDED THRESHOLDS ---")
    print("If we want the top ~5% of worst drops:")
    print(f"Drop Threshold: {valid['pct_change'].quantile(0.05)*100:.1f}%")
    
    print("\nIf we want the top ~5% of best lifts:")
    print(f"Lift Threshold: {valid['pct_change'].quantile(0.95)*100:.1f}%")
    
    print("\nIf we want the top ~10% extremes:")
    print(f"Drop Threshold (10%): {valid['pct_change'].quantile(0.10)*100:.1f}%")
    print(f"Lift Threshold (10%): {valid['pct_change'].quantile(0.90)*100:.1f}%")

if __name__ == "__main__":
    analyze()
