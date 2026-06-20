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
    
    # We will test on the last 60 days so all methods have enough history
    max_date = df['dt'].max()
    test_start_date = max_date - pd.Timedelta(days=60)
    
    results = []
    
    for city_id, group in df.groupby('city_id'):
        group = group.sort_values('dt').reset_index(drop=True)
        
        # Approach 1: 7-Day Trailing Avg (Current)
        group['a1_baseline'] = group['total_sales'].rolling(window=7, min_periods=7).mean().shift(1)
        group['a1_pct'] = (group['total_sales'] - group['a1_baseline']) / group['a1_baseline']
        group['a1_drop'] = group['a1_pct'] <= -0.20
        group['a1_lift'] = group['a1_pct'] >= 0.35
        
        # Approach 2: 4-Week Same-Day Average (DoW Matched)
        # Shift by 7, 14, 21, 28 days
        group['t_minus_7'] = group['total_sales'].shift(7)
        group['t_minus_14'] = group['total_sales'].shift(14)
        group['t_minus_21'] = group['total_sales'].shift(21)
        group['t_minus_28'] = group['total_sales'].shift(28)
        
        # Mean of last 4 same-days
        group['a2_baseline'] = group[['t_minus_7', 't_minus_14', 't_minus_21', 't_minus_28']].mean(axis=1)
        group['a2_pct'] = (group['total_sales'] - group['a2_baseline']) / group['a2_baseline']
        
        # We can use tighter thresholds for DoW because the baseline is much more accurate
        # Let's try -15% and +20% for DoW matched since the denominator is apples-to-apples
        group['a2_drop'] = group['a2_pct'] <= -0.15
        group['a2_lift'] = group['a2_pct'] >= 0.20
        
        # Approach 3: Z-Score over a 28-day rolling window
        group['rolling_mean_28'] = group['total_sales'].rolling(window=28, min_periods=28).mean().shift(1)
        group['rolling_std_28'] = group['total_sales'].rolling(window=28, min_periods=28).std().shift(1)
        group['a3_zscore'] = (group['total_sales'] - group['rolling_mean_28']) / group['rolling_std_28']
        
        # Z-score thresholds
        group['a3_drop'] = group['a3_zscore'] <= -2.0
        group['a3_lift'] = group['a3_zscore'] >= 2.0
        
        # Approach 4: Z-Score of the DoW Matched (Best of both worlds)
        # std of the 4 matching days
        group['a4_dow_std'] = group[['t_minus_7', 't_minus_14', 't_minus_21', 't_minus_28']].std(axis=1)
        group['a4_zscore'] = (group['total_sales'] - group['a2_baseline']) / group['a4_dow_std'].replace(0, np.nan)
        group['a4_drop'] = group['a4_zscore'] <= -2.0
        group['a4_lift'] = group['a4_zscore'] >= 2.0
        
        # Filter to test window
        test_window = group[group['dt'] >= test_start_date].copy()
        results.append(test_window)
        
    all_res = pd.concat(results)
    
    total_days = len(all_res)
    
    print(f"--- ANOMALY DETECTION EXPERIMENT RESULTS ---")
    print(f"Total City-Days Evaluated: {total_days}\\n")
    
    def print_stats(name, drop_col, lift_col):
        drops = all_res[drop_col].sum()
        lifts = all_res[lift_col].sum()
        print(f"[{name}]")
        print(f"  Drops Flagged: {drops} ({drops/total_days*100:.1f}%)")
        print(f"  Lifts Flagged: {lifts} ({lifts/total_days*100:.1f}%)")
        print(f"  Total Anomalies: {drops+lifts} ({((drops+lifts)/total_days)*100:.1f}%)\\n")
        
    print_stats("Approach 1: 7-Day Trailing (Current)", 'a1_drop', 'a1_lift')
    print_stats("Approach 2: 4-Week DoW Matched (Pct)", 'a2_drop', 'a2_lift')
    print_stats("Approach 3: 28-Day Z-Score", 'a3_drop', 'a3_lift')
    print_stats("Approach 4: DoW Matched Z-Score", 'a4_drop', 'a4_lift')
    
    # Print a sample comparison for a single city to see agreement/disagreement
    print("--- SAMPLE DISAGREEMENTS (City 0) ---")
    c0 = all_res[all_res['city_id'] == 0]
    disagreements = c0[(c0['a1_drop'] != c0['a2_drop']) | (c0['a1_lift'] != c0['a2_lift'])]
    
    for _, row in disagreements.head(5).iterrows():
        dt = row['dt'].strftime('%Y-%m-%d (%a)')
        sales = row['total_sales']
        print(f"Date: {dt} | Sales: {sales:.0f}")
        print(f"  A1 (7-Day): Baseline={row['a1_baseline']:.0f}, Pct={row['a1_pct']*100:.1f}% -> Drop:{row['a1_drop']} Lift:{row['a1_lift']}")
        print(f"  A2 (DoW):   Baseline={row['a2_baseline']:.0f}, Pct={row['a2_pct']*100:.1f}% -> Drop:{row['a2_drop']} Lift:{row['a2_lift']}")
        print("-" * 40)

if __name__ == "__main__":
    run_experiments()
