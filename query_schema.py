import duckdb
import os

DB_PATH = "data/rca.duckdb"

if not os.path.exists(DB_PATH):
    print("Database not found. Is it still building?")
else:
    con = duckdb.connect(DB_PATH, read_only=True)
    tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n=== Table: {table_name} ===")
        columns = con.execute(f"DESCRIBE {table_name}").fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        # Print row count
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  Total Rows: {count}")
        
        if table_name == "dim_city":
            cities = con.execute(f"SELECT COUNT(DISTINCT city_id) FROM {table_name}").fetchone()[0]
            print(f"  Distinct Cities: {cities}")
    con.close()
