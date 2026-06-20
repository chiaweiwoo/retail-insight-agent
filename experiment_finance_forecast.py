import duckdb
import pandas as pd
import numpy as np

def run_finance_simulation():
    con = duckdb.connect("data/rca.duckdb")
    
    # 1. Load Data
    df = con.execute("""
        SELECT city_id, dt, total_sales 
        FROM fact_sales_city_day 
        ORDER BY dt, city_id
    """).fetchdf()
    df['dt'] = pd.to_datetime(df['dt'])
    
    # Generate fleet daily
    fleet_daily = df.groupby('dt')['total_sales'].sum().reset_index().rename(columns={'total_sales': 'fleet_sales'})
    fleet_daily['dow'] = fleet_daily['dt'].dt.dayofweek
    
    # 2. Simulate Weekly Finance Forecast
    # Finance generates a forecast every Monday for the next 7 days, based on the prior 28 days.
    # Start forecasting from day 28
    dates = sorted(fleet_daily['dt'].unique())
    forecasts = []
    
    for i in range(28, len(dates), 7):
        current_monday = dates[i]
        forecast_horizon = dates[i:i+7]
        lookback_start = current_monday - pd.Timedelta(days=28)
        
        # 2a. Lookback Data
        fleet_lookback = fleet_daily[(fleet_daily['dt'] >= lookback_start) & (fleet_daily['dt'] < current_monday)]
        city_lookback = df[(df['dt'] >= lookback_start) & (df['dt'] < current_monday)]
        
        if len(fleet_lookback) < 28:
            continue
            
        # 2b. Finance assumptions from lookback
        fleet_avg_daily = fleet_lookback['fleet_sales'].mean()
        
        # Calculate DoW multipliers (Day average / Overall average)
        dow_means = fleet_lookback.groupby('dow')['fleet_sales'].mean()
        dow_mults = dow_means / fleet_avg_daily
        
        # Calculate City Shares (City total / Fleet total)
        total_fleet_sales = fleet_lookback['fleet_sales'].sum()
        city_shares = city_lookback.groupby('city_id')['total_sales'].sum() / total_fleet_sales
        
        # 2c. Generate Forecast for the horizon
        for d in forecast_horizon:
            dow = d.dayofweek
            fleet_forecast_d = fleet_avg_daily * dow_mults.get(dow, 1.0)
            
            for city_id in city_shares.index:
                city_forecast = fleet_forecast_d * city_shares[city_id]
                forecasts.append({
                    'dt': d,
                    'city_id': city_id,
                    'forecast_sales': city_forecast
                })
                
    forecast_df = pd.DataFrame(forecasts)
    
    # 3. Merge and Evaluate
    merged = pd.merge(df, forecast_df, on=['dt', 'city_id'], how='inner')
    merged['pct_error'] = (merged['total_sales'] - merged['forecast_sales']) / merged['forecast_sales']
    
    # 4. Evaluate Thresholds across Sample Cities
    test_cities = [0, 5, 17] # Large, Medium, Small
    thresholds = [0.10, 0.15, 0.20, 0.25]
    
    print("=== FINANCE FORECAST VS ACTUAL ===")
    print("Evaluation of Naive Top-Down S&OP Allocation\\n")
    
    for c in test_cities:
        c_data = merged[merged['city_id'] == c]
        total_days = len(c_data)
        
        # Calculate MAPE to see how good the forecast actually is
        mape = c_data['pct_error'].abs().mean()
        print(f"City {c} (N={total_days} days) - Forecast MAPE: {mape*100:.1f}%")
        
        for t in thresholds:
            drops = (c_data['pct_error'] <= -t).sum()
            lifts = (c_data['pct_error'] >= t).sum()
            print(f"  Threshold +/- {t*100:.0f}% -> Drops: {drops} ({drops/total_days*100:.1f}%), Lifts: {lifts} ({lifts/total_days*100:.1f}%)")
        print()

    # 5. Visual Sentiment / Reasoning Check
    print("=== VISUAL SENTIMENT CHECK (City 0) ===")
    print("Let's look at a 7-day snippet for City 0 to see how the forecast behaves:")
    sample = merged[merged['city_id'] == 0].head(7)
    for _, row in sample.iterrows():
        dt_str = row['dt'].strftime('%Y-%m-%d (%a)')
        act = row['total_sales']
        fcst = row['forecast_sales']
        err = row['pct_error'] * 100
        print(f"{dt_str}: Actual {act:5.0f} | Forecast {fcst:5.0f} | Error: {err:+.1f}%")

if __name__ == "__main__":
    run_finance_simulation()
