import duckdb
import pandas as pd
from rca.database import get_supabase_client
from rca.config import DB_PATH

def generate_and_sync_forecast():
    print("Generating Finance Forecast...")
    con = duckdb.connect(str(DB_PATH))
    
    df = con.execute("""
        SELECT city_id, dt, total_sales 
        FROM fact_sales_city_day 
        ORDER BY dt, city_id
    """).fetchdf()
    df['dt'] = pd.to_datetime(df['dt'])
    
    fleet_daily = df.groupby('dt')['total_sales'].sum().reset_index().rename(columns={'total_sales': 'fleet_sales'})
    fleet_daily['dow'] = fleet_daily['dt'].dt.dayofweek
    
    dates = sorted(fleet_daily['dt'].unique())
    forecasts = []
    
    for i in range(28, len(dates), 7):
        current_monday = dates[i]
        forecast_horizon = dates[i:i+7]
        lookback_start = current_monday - pd.Timedelta(days=28)
        
        fleet_lookback = fleet_daily[(fleet_daily['dt'] >= lookback_start) & (fleet_daily['dt'] < current_monday)]
        city_lookback = df[(df['dt'] >= lookback_start) & (df['dt'] < current_monday)]
        
        if len(fleet_lookback) < 28:
            continue
            
        fleet_avg_daily = fleet_lookback['fleet_sales'].mean()
        dow_means = fleet_lookback.groupby('dow')['fleet_sales'].mean()
        dow_mults = dow_means / fleet_avg_daily
        
        total_fleet_sales = fleet_lookback['fleet_sales'].sum()
        city_shares = city_lookback.groupby('city_id')['total_sales'].sum() / total_fleet_sales
        
        for d in forecast_horizon:
            dow = d.dayofweek
            fleet_forecast_d = fleet_avg_daily * dow_mults.get(dow, 1.0)
            
            for city_id in city_shares.index:
                city_forecast = fleet_forecast_d * city_shares[city_id]
                forecasts.append({
                    'city_id': int(city_id),
                    'dt': d.strftime('%Y-%m-%d'),
                    'forecast_sales': float(city_forecast)
                })
                
    client = get_supabase_client()
    
    print(f"Upserting {len(forecasts)} forecast rows to Supabase...")
    batch_size = 1000
    for i in range(0, len(forecasts), batch_size):
        batch = forecasts[i:i+batch_size]
        client.table("rca_finance_forecast").upsert(batch).execute()
        
    print("Done!")

if __name__ == "__main__":
    generate_and_sync_forecast()
