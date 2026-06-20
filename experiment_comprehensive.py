import duckdb
import pandas as pd
import numpy as np

def run():
    con = duckdb.connect("data/rca.duckdb")
    df = con.execute("""
        SELECT city_id, dt, total_sales 
        FROM fact_sales_city_day 
        ORDER BY city_id, dt
    """).fetchdf()
    df['dt'] = pd.to_datetime(df['dt'])
    
    # Pre-calculate Fleet Macro Pattern
    fleet = df.groupby('dt')['total_sales'].sum().reset_index()
    fleet['fleet_7d_avg'] = fleet['total_sales'].rolling(7, min_periods=7).mean().shift(1)
    fleet['fleet_ratio'] = fleet['total_sales'] / fleet['fleet_7d_avg']
    # shift fleet_ratio so we don't leak today's fleet data into the prediction?
    # Actually, for an anomaly detection baseline, using today's fleet behavior to baseline today's city is completely valid!
    # Because if the whole fleet drops 10% today, the city dropping 10% isn't a city anomaly.
    fleet_dict = dict(zip(fleet['dt'], fleet['fleet_ratio']))
    
    results = []
    
    for city_id, group in df.groupby('city_id'):
        group = group.sort_values('dt').reset_index(drop=True)
        
        # A. Simple 7-Day Moving Avg
        group['baseline_A'] = group['total_sales'].rolling(7, min_periods=7).mean().shift(1)
        
        # B. Seasonal Decomposition (Trend * Rolling DoW)
        group['dow'] = group['dt'].dt.dayofweek
        group['ratio'] = group['total_sales'] / group['baseline_A']
        
        r_7 = group['ratio'].shift(7)
        r_14 = group['ratio'].shift(14)
        r_21 = group['ratio'].shift(21)
        r_28 = group['ratio'].shift(28)
        
        group['dow_mult'] = group[['ratio'].copy()].shift(7) # Fallback to last week's ratio if needed
        group['dow_mult'] = pd.concat([r_7, r_14, r_21, r_28], axis=1).mean(axis=1)
        
        group['baseline_B'] = group['baseline_A'] * group['dow_mult']
        
        # C. Fleet-Adjusted Baseline (Macro Context)
        # Expected sales = City's 7-day trend * Fleet's actual performance ratio today
        group['macro_ratio'] = group['dt'].map(fleet_dict)
        group['baseline_C'] = group['baseline_A'] * group['macro_ratio']
        
        # Calculate Error for each baseline to see which traces the actual human-visible graph best
        group['err_A'] = abs((group['total_sales'] - group['baseline_A']) / group['baseline_A'])
        group['err_B'] = abs((group['total_sales'] - group['baseline_B']) / group['baseline_B'])
        group['err_C'] = abs((group['total_sales'] - group['baseline_C']) / group['baseline_C'])
        
        results.append(group.dropna())
        
    res = pd.concat(results)
    
    print("=== MODEL ACCURACY EVALUATION (MAPE) ===")
    print("Which baseline best predicts 'Normal' sales across all 18 Cities?")
    print(f"  Model A (7-Day Avg):       {res['err_A'].mean()*100:.1f}% average error")
    print(f"  Model B (Trend + DoW):     {res['err_B'].mean()*100:.1f}% average error")
    print(f"  Model C (Trend + Fleet):   {res['err_C'].mean()*100:.1f}% average error\\n")
    
    print("=== CITY DIVERSITY ANALYSIS ===")
    cities_to_check = [0, 5, 17] # A large city, a medium city, a small city
    
    for c in cities_to_check:
        c_res = res[res['city_id'] == c]
        mape_a = c_res['err_A'].mean() * 100
        mape_b = c_res['err_B'].mean() * 100
        mape_c = c_res['err_C'].mean() * 100
        print(f"City {c}:")
        print(f"  Model A Error: {mape_a:.1f}%")
        print(f"  Model B Error: {mape_b:.1f}%")
        print(f"  Model C Error: {mape_c:.1f}%")
        
        # Check standard deviation of the errors to see stability
        print(f"  Model B StdDev (Stability): {c_res['err_B'].std()*100:.1f}%")
        print(f"  Model C StdDev (Stability): {c_res['err_C'].std()*100:.1f}%\\n")

if __name__ == "__main__":
    run()
