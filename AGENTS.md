# AGENTS.md

This file is intentionally short.

`README.md` is the main project document and the source of truth for:

- runtime design
- agent roles
- tool access
- DAG
- commands
- benchmark artifacts

## Current Guardrails

- keep the system evidence-first and read-only over the local DuckDB artifact
- prefer normal Python modules and explicit tool functions
- keep agent tool access domain-bounded
- document important project decisions in `README.md`, `docs/PRD.md`, and `docs/analysis/`

## Still Out Of Scope

- MCP runtime
- skills runtime
- persistent memory
- external news agent
- FastAPI or Streamlit app layer
- product/category drilldown
- customer analysis
