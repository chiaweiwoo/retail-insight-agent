import os
import glob

def replace_in_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Global replacements for functions and variables
global_reps = {
    "get_store_day_evidence": "get_city_day_evidence",
    "_assert_store_and_date_exist": "_assert_city_and_date_exist",
    "store_exists = connection.execute": "city_exists = connection.execute",
    "if int(store_exists) != 1:": "if int(city_exists) != 1:",
    "per_store_rows": "per_city_rows",
    "store_spread": "city_spread",
    "triggered_store_days": "triggered_city_days",
    "triggered store-days": "triggered city-days",
    "store_day_sales_signals.csv": "city_day_sales_signals.csv",
    "store_signal_stability.csv": "city_signal_stability.csv"
}

for py_file in glob.glob("rca/*.py"):
    replace_in_file(py_file, global_reps)

# Specific fixes for context.py
replace_in_file("rca/context.py", {
    "store_count = con.execute(\"SELECT COUNT(DISTINCT city_id)": "city_count = con.execute(\"SELECT COUNT(DISTINCT city_id)",
    "\"cities\": store_count,": "\"cities\": city_count,"
})

# Fix prompt in agents.py
agents_prompt_old = """                "PEER COMPARISON CAUTION: The peer group tool groups stores by their alias prefix (h/m/l) "
                "or store type. For the well-known city-0 stores, each prefix group contains only ~5 stores — "
                "statistically noisy. For stores aliased as 's{id}', the peer pool is large but spans multiple "
                "cities with different demand patterns, making fleet-average comparisons unreliable as root-cause evidence. "
                "In either case: peer comparison can support a hypothesis but CANNOT be the primary root cause. \""""

agents_prompt_new = """                "PEER COMPARISON CAUTION: The peer group tool groups cities by their density tier "
                "(based on their store count). While this provides a baseline, macro-economic factors can affect "
                "all cities simultaneously. "
                "Peer comparison can support a hypothesis but CANNOT be the primary root cause. \""""

replace_in_file("rca/agents.py", {agents_prompt_old: agents_prompt_new})

# Also fix the focus text
replace_in_file("rca/agents.py", {"peer store comparison": "peer city comparison"})

print("Legacy store terms cleaned up!")
