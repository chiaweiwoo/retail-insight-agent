import os
import glob
import re

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Type hints: store_alias: str -> city_id: int
    content = content.replace("store_alias: str", "city_id: int")
    content = content.replace("store_alias:str", "city_id:int")
    
    # 2. Variable names: store_alias -> city_id
    content = content.replace("store_alias", "city_id")
    
    # 3. Table names and logic
    content = content.replace("rca_store", "rca_city")
    content = content.replace("fact_sales_store_day", "fact_sales_city_day")
    content = content.replace("fact_stockout_store_day", "fact_stockout_city_day")
    content = content.replace("fact_discount_store_day", "fact_discount_city_day")
    content = content.replace("fact_activity_store_day", "fact_activity_city_day")
    content = content.replace("dim_store", "dim_city")
    
    # 4. Text and strings
    content = content.replace("store alias", "city ID")
    content = content.replace("store alias:", "city ID:")

    # 5. Fix tools.py peer comparison
    # We will manually fix peer comparison later, but let's replace prefix logic strings if they appear
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for py_file in glob.glob("rca/*.py"):
    if os.path.basename(py_file) == "database.py":
        # we already manually refactored database.py mostly, but we can let it run over it if safe.
        # It's better to avoid database.py to prevent messing up anything we just carefully fixed.
        continue
    refactor_file(py_file)

print("Refactor complete.")
