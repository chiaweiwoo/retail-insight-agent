---
name: rca-run
description: Run an end-to-end RCA workflow for a specific store and date.
---

# Skill: rca-run

Run an end-to-end RCA workflow for a specific store and date and summarise the outcome.

## When to use
The user says "run rca for store <store_alias> on <date>" or "investigate store <store_alias> drop/lift on <date>".

## Steps
1. Run: `uv run python -m rca.cli run --store <store_alias> --dt <date> --full`
2. If the user asked for a quick run without the coordinator, use `--quick` instead of `--full`.
3. If the user asked for reflection, append `--reflect`.
4. Read the printed decision card and summarise the top driver and confidence level.

## Grounding rules
- Do not invent or hallucinate the analysis.
- Rely solely on the output of the CLI tool.
- Normalized sales figures are coefficients, not currency.
