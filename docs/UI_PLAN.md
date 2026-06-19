# UI Plan

UI is part of the current Milestone B and should stay simple and analyst-oriented:

- select a store alias
- select a date
- show store-day metrics from the five analytical domains
- show the raw evidence before any narrative explanation

Current UI boundary:

1. A lightweight local app over exported DuckDB evidence data.
2. Read-only exploration first.
3. No agent workflow, no dashboard sprawl, and no generated RCA text until the metrics are trusted.
