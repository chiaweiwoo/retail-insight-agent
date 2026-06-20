---
name: rca-story
description: Regenerate the reader-facing story report for a completed RCA run.
---

# Skill: rca-story

Regenerate the reader-facing story report for a completed RCA run.

## When to use
The user says "generate story for <run_folder>" or "write the story report for <store> <date>".

## Steps
1. Locate the run folder under `data/analysis/agent_benchmark_runs/<run_folder>/`
2. Run: `uv run python -m rca.cli story --run-dir data/analysis/agent_benchmark_runs/<run_folder>`
3. Output is written to `output/story_reports/<run_folder>/`
4. Read and summarise the story report for the user.

## Grounding rules
- Do not invent drivers not present in the coordinator trace.
- Do not claim certainty beyond what the decision card confidence field states.
- Normalized sales figures are coefficients, not currency.
