import duckdb
import pandas as pd
import numpy as np

def analyze_new_thresholds():
    con = duckdb.connect("data/rca.duckdb")
    df = con.execute("""
        SELECT city_id, dt, total_sales 
        FROM fact_sales_city_day 
        ORDER BY city_id, dt
    """).fetchdf()
    df['dt'] = pd.to_datetime(df['dt'])
    
    fleet = con.execute("""
        SELECT dt, SUM(total_sales) as fleet_sales 
        FROM fact_sales_city_day 
        GROUP BY dt ORDER BY dt
    """).fetchdf()
    fleet['dt'] = pd.to_datetime(fleet['dt'])
    fleet['fleet_7d_avg'] = fleet['fleet_sales'].rolling(7, min_periods=7).mean().shift(1)
    fleet['fleet_ratio'] = fleet['fleet_sales'] / fleet['fleet_7d_avg']
    fleet_dict = dict(zip(fleet['dt'], fleet['fleet_ratio']))
    
    results = []
    
    for city_id, group in df.groupby('city_id'):
        group = group.sort_values('dt').reset_index(drop=True)
        group['city_7d_avg'] = group['total_sales'].rolling(7, min_periods=7).mean().shift(1)
        group['macro_ratio'] = group['dt'].map(fleet_dict)
        group['expected_sales'] = group['city_7d_avg'] * group['macro_ratio']
        
        # Calculate new Fleet-Adjusted Percentage Error
        group['pct_error'] = (group['total_sales'] - group['expected_sales']) / group['expected_sales']
        
        results.append(group.dropna())
        
    all_res = pd.concat(results)
    
    valid = all_res['pct_error'].dropna()
    
    print("--- DISTRIBUTION OF FLEET-ADJUSTED PERCENTAGE ERROR ---")
    print(f"Total valid city-days: {len(valid)}")
    print(f"Mean pct_error: {valid.mean():.4f}")
    print(f"Median pct_error: {valid.median():.4f}")
    print(f"Std Dev: {valid.std():.4f}")
    print("\\nPercentiles:")
    
    percentiles = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    for p in percentiles:
        val = valid.quantile(p)
        print(f"P{int(p*100):02d}: {val*100:6.2f}%")

    print("\\n--- RECOMMENDED ASYMMETRIC THRESHOLDS ---")
    print(f"Drop (Bottom 5%): {valid.quantile(0.05)*100:.1f}%")
    print(f"Lift (Top 5%):    {valid.quantile(0.95)*100:.1f}%")

if __name__ == "__main__":
    analyze_new_thresholds()
