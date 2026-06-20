import duckdb
import pandas as pd
import numpy as np

def run_experiments():
    con = duckdb.connect("data/rca.duckdb")
    df = con.execute("""
        SELECT city_id, dt, total_sales 
        FROM fact_sales_city_day 
        ORDER BY city_id, dt
    """).fetchdf()
    
    df['dt'] = pd.to_datetime(df['dt'])
    
    # We will test on the last 60 days
    max_date = df['dt'].max()
    test_start_date = max_date - pd.Timedelta(days=60)
    
    results = []
    
    for city_id, group in df.groupby('city_id'):
        group = group.sort_values('dt').reset_index(drop=True)
        
        # 1. 7-Day Trailing Baseline (Captures the Trend)
        group['trend_baseline'] = group['total_sales'].rolling(window=7, min_periods=7).mean().shift(1)
        
        # 2. Calculate Day-of-Week (DoW) Seasonality Multiplier
        group['dow'] = group['dt'].dt.dayofweek
        
        # To avoid data leakage, we calculate the DoW multiplier dynamically using a rolling 28-day window
        # We need the ratio of actual_sales / trend_baseline for the last 4 matching DoW
        group['ratio'] = group['total_sales'] / group['trend_baseline']
        
        # Shift ratios so we don't include today
        group['r_minus_7'] = group['ratio'].shift(7)
        group['r_minus_14'] = group['ratio'].shift(14)
        group['r_minus_21'] = group['ratio'].shift(21)
        group['r_minus_28'] = group['ratio'].shift(28)
        
        # The expected DoW multiplier is the average of the ratios from the last 4 matching days
        group['expected_dow_multiplier'] = group[['r_minus_7', 'r_minus_14', 'r_minus_21', 'r_minus_28']].mean(axis=1)
        
        # 3. Expected Sales = Trend * Expected Seasonality
        group['expected_sales'] = group['trend_baseline'] * group['expected_dow_multiplier']
        
        # 4. Anomaly Calculation
        group['pct_error'] = (group['total_sales'] - group['expected_sales']) / group['expected_sales']
        
        # Because the baseline is now VERY accurate, we can use tight thresholds
        group['is_drop'] = group['pct_error'] <= -0.15
        group['is_lift'] = group['pct_error'] >= 0.15
        
        # Original logic for comparison
        group['old_pct'] = (group['total_sales'] - group['trend_baseline']) / group['trend_baseline']
        group['old_drop'] = group['old_pct'] <= -0.20
        group['old_lift'] = group['old_pct'] >= 0.35
        
        test_window = group[group['dt'] >= test_start_date].copy()
        results.append(test_window)
        
    all_res = pd.concat(results)
    total_days = len(all_res)
    
    print(f"--- TIME SERIES DECOMPOSITION EXPERIMENT ---")
    print(f"Total City-Days Evaluated: {total_days}\\n")
    
    def print_stats(name, drop_col, lift_col):
        drops = all_res[drop_col].sum()
        lifts = all_res[lift_col].sum()
        print(f"[{name}]")
        print(f"  Drops Flagged: {drops} ({drops/total_days*100:.1f}%)")
        print(f"  Lifts Flagged: {lifts} ({lifts/total_days*100:.1f}%)")
        print(f"  Total Anomalies: {drops+lifts} ({((drops+lifts)/total_days)*100:.1f}%)\\n")
        
    print_stats("Old Logic (7-Day Avg, fixed -20%/+35%)", 'old_drop', 'old_lift')
    print_stats("New Logic (Trend + Seasonality, fixed -15%/+15%)", 'is_drop', 'is_lift')
    
    # Print a sample comparison to show how the expected sales perfectly traces the real sales
    print("--- HOW IT WORKS IN PRACTICE (City 0) ---")
    c0 = all_res[all_res['city_id'] == 0].head(7)
    
    for _, row in c0.iterrows():
        dt = row['dt'].strftime('%Y-%m-%d (%a)')
        sales = row['total_sales']
        trend = row['trend_baseline']
        mult = row['expected_dow_multiplier']
        expected = row['expected_sales']
        err = row['pct_error'] * 100
        old_err = row['old_pct'] * 100
        
        print(f"Date: {dt} | Actual Sales: {sales:.0f}")
        print(f"  Old Baseline: {trend:.0f} (Error: {old_err:+.1f}%)")
        print(f"  New Baseline: {trend:.0f} * {mult:.2f}x (DoW factor) = Expected {expected:.0f} (Error: {err:+.1f}%)")
        print("-" * 50)

if __name__ == "__main__":
    run_experiments()
