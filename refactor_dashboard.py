import os
import glob
import re

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Supabase table names
    content = content.replace('rca_store_series', 'rca_city_series')
    content = content.replace('rca_store_normals', 'rca_city_normals')
    content = content.replace('rca_store_profile', 'rca_city_profile')
    
    # DB columns and variables
    content = content.replace('store_id', 'city_id')
    content = content.replace('storeId', 'cityId')
    
    # UI text
    content = content.replace('Store {storeId}', 'City {cityId}')
    content = content.replace('Store {cityId}', 'City {cityId}')
    content = content.replace('This store', 'This city')
    content = content.replace('store_alias', 'city_id')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for root, dirs, files in os.walk("dashboard/src"):
    for file in files:
        if file.endswith((".ts", ".tsx")):
            refactor_file(os.path.join(root, file))

print("Dashboard refactor complete.")
