# RCA Agent Benchmark Review

This note captures the first benchmarked live-agent runs over the fixed six-scenario RCA set.

## Runs Reviewed

- baseline run: `data/analysis/agent_benchmark_runs/20260619T142035Z/`
- prompt-refined run: `data/analysis/agent_benchmark_runs/20260619T142335Z/`

Model used in both runs:

- `deepseek-v4-flash`

## Summary

The first runnable agent is working end to end:

- all 6 benchmark scenarios completed successfully
- trigger alignment was `6 / 6` in both runs
- reports were generated for all 6 store-day cases
- tool traces were saved for later regression review

## What Improved In The Second Run

The prompt-refined run improved two practical issues:

1. tool efficiency
2. causal discipline in the writing

Most visible gain:

- `lift_medium_m041_2024-05-12` went from `11` tool calls down to `7`

This suggests the prompt change that asked the agent to avoid unnecessary repeated tool calls helped.

The report tone also became more careful:

- more explicit caveats
- clearer distinction between observation and inference
- less aggressive "single cause" language

## Remaining Issues

### 1. Some repeated tool usage still happens

Example:

- `drop_high_h555_2024-05-16` still called `get_stockout_context` twice in both runs

This is not a functional bug, but it is unnecessary token spend and a sign that the tool surface may still be a bit too fragmented for the model.

### 2. Model output still contains non-ASCII punctuation

Even after the prompt asked for ASCII-only output, the live reports still included punctuation such as smart dashes and arrows.

This is mainly a formatting annoyance right now, but it matters because:

- terminal rendering can look messy on Windows
- committed benchmark markdown becomes less clean than the rest of the repo

### 3. Causal confidence is better, but still not fully constrained

The reports are now more careful, but the model can still lean into phrases that sound stronger than the evidence fully supports.

That is expected at this stage because:

- tools expose same-day evidence, not richer history or item-level attribution
- the current benchmark is designed for grounded discussion, not formal causal proof

## Current Conclusion

The project now has a usable benchmark loop for agent quality:

- fixed benchmark set
- repeatable batch runner
- saved traces
- visible before/after comparison when prompt or tool design changes

This is enough to start iterative backend quality work without adding more orchestration.

## Recommended Next Step

The best next move is to improve the tool surface before adding more agent complexity.

Priority order:

1. add a compact combined evidence tool that returns the most important RCA fields in one call
2. keep the current domain tools for follow-up drilling
3. rerun the six-scenario benchmark and compare tool counts plus tone again

That should reduce repeated calls and make the model less likely to over-assemble its own narrative from scattered fragments.
