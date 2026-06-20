import duckdb
import pandas as pd
import json

def generate_chart():
    con = duckdb.connect("data/rca.duckdb")
    df = con.execute("""
        SELECT city_id, dt, total_sales 
        FROM fact_sales_city_day 
        WHERE city_id = 0
        ORDER BY dt
    """).fetchdf()
    df['dt'] = pd.to_datetime(df['dt'])
    
    # Fleet
    fleet = con.execute("""
        SELECT dt, SUM(total_sales) as fleet_sales 
        FROM fact_sales_city_day 
        GROUP BY dt ORDER BY dt
    """).fetchdf()
    fleet['dt'] = pd.to_datetime(fleet['dt'])
    fleet['fleet_7d_avg'] = fleet['fleet_sales'].rolling(7, min_periods=7).mean().shift(1)
    fleet['fleet_ratio'] = fleet['fleet_sales'] / fleet['fleet_7d_avg']
    fleet_dict = dict(zip(fleet['dt'], fleet['fleet_ratio']))
    
    # Calculate baselines
    df['baseline_A'] = df['total_sales'].rolling(7, min_periods=7).mean().shift(1)
    
    df['dow'] = df['dt'].dt.dayofweek
    df['ratio'] = df['total_sales'] / df['baseline_A']
    r_7 = df['ratio'].shift(7)
    r_14 = df['ratio'].shift(14)
    r_21 = df['ratio'].shift(21)
    r_28 = df['ratio'].shift(28)
    df['dow_mult'] = pd.concat([r_7, r_14, r_21, r_28], axis=1).mean(axis=1)
    df['baseline_B'] = df['baseline_A'] * df['dow_mult']
    
    df['macro_ratio'] = df['dt'].map(fleet_dict)
    df['baseline_C'] = df['baseline_A'] * df['macro_ratio']
    
    # Exponential Smoothing (Simple alpha=0.3 on matching day of week)
    # A human often just remembers "last week" and maybe "the week before"
    df['baseline_D'] = df['total_sales'].shift(7) * 0.7 + df['total_sales'].shift(14) * 0.3
    
    # Filter last 45 days for clean visualization
    viz_df = df.tail(45).copy()
    
    dates = viz_df['dt'].dt.strftime('%Y-%m-%d').tolist()
    actual = viz_df['total_sales'].fillna(0).tolist()
    model_a = viz_df['baseline_A'].fillna(0).tolist()
    model_b = viz_df['baseline_B'].fillna(0).tolist()
    model_c = viz_df['baseline_C'].fillna(0).tolist()
    model_d = viz_df['baseline_D'].fillna(0).tolist()

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Time Series POV Analysis</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: sans-serif; background: #0f172a; color: white; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: #1e293b; padding: 20px; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Human Vision POV: City 0 Sales vs Baseline Models</h2>
            <p>Compare how different mathematical baselines "draw" the expected line compared to actual sales.</p>
            <canvas id="myChart" height="400"></canvas>
        </div>
        <script>
            const ctx = document.getElementById('myChart');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(dates)},
                    datasets: [
                        {{
                            label: 'Actual Sales (What the Human Sees)',
                            data: {json.dumps(actual)},
                            borderColor: '#38bdf8',
                            backgroundColor: '#38bdf8',
                            borderWidth: 4,
                            tension: 0.2,
                            order: 1
                        }},
                        {{
                            label: 'Model A: 7-Day Trailing (Old Logic)',
                            data: {json.dumps(model_a)},
                            borderColor: '#ef4444',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            tension: 0.2,
                            hidden: false,
                            order: 2
                        }},
                        {{
                            label: 'Model B: DoW Seasonal (Historical Waves)',
                            data: {json.dumps(model_b)},
                            borderColor: '#a855f7',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            tension: 0.2,
                            hidden: false,
                            order: 3
                        }},
                        {{
                            label: 'Model C: Fleet Macro (Cross-Sectional)',
                            data: {json.dumps(model_c)},
                            borderColor: '#10b981',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            tension: 0.2,
                            hidden: true,
                            order: 4
                        }},
                        {{
                            label: 'Model D: Last Week Weighted (Human Memory)',
                            data: {json.dumps(model_d)},
                            borderColor: '#f59e0b',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            tension: 0.2,
                            hidden: true,
                            order: 5
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{ legend: {{ labels: {{ color: 'white' }} }} }},
                    scales: {{
                        y: {{ ticks: {{ color: 'white' }}, grid: {{ color: '#334155' }} }},
                        x: {{ ticks: {{ color: 'white' }}, grid: {{ color: '#334155' }} }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open('human_vision_pov.html', 'w') as f:
        f.write(html_content)
    print("Successfully generated human_vision_pov.html")

if __name__ == "__main__":
    generate_chart()
