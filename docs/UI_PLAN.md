# UI Plan

UI is important for this project, but it is not part of the current implementation milestone.

The first interface should come after the DuckDB evidence layer is stable and validated. The early UI should stay simple and analyst-oriented:

- select a store alias
- select a date
- show store-day metrics from the five analytical domains
- show the raw evidence before any narrative explanation

Recommended first UI phase:

1. A lightweight local app over DuckDB.
2. Read-only exploration first.
3. No agent workflow, no dashboards for many personas, and no generated RCA text until the metrics are trusted.
