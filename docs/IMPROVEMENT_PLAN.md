# Remediation Plan — City-Grain Pivot + Intraday + Analytical Layer

> **Planned on Opus. Execute on Sonnet.** Supersedes the v2 redesign plan (that work shipped; see git history `8bc8529`…`47e3fe6`).
> A previous session pivoted store→city using two blunt find-and-replace scripts; the pivot is conceptually
> right but mechanically half-broken and uncommitted on `main`. This plan stabilises it, makes the city grain
> real, **adds an intraday (24-hour) explanatory layer and a statistical/ML layer**, fixes the trigger science,
> and moves logging mostly to the cloud.
> 
> **Archived note:** this file is historical planning material. The current public CLI is documented in `README.md` and is limited to `build`, `signal`, `run --city --date`, `replay --city [--reset]`, and `mcp`.
>
> **Status: City-Grain Pivot and Dashboard Heatmap are Complete.** The core metrics, database logic, agent prompts, and the Next.js frontend have been successfully refactored to focus on City-Level aggregations (18 cities, 90 days). The Fleet Overview dashboard now uses an elegant 14-day heatmap.
> 
> The next phase will focus on the Statistical/ML layer (STL detrending, KMeans clustering, Intraday anomaly tracking).

---

## Locked decisions

| Topic | Decision |
| --- | --- |
| **Analysis grain** | **City aggregate** — one row per city-day. No store level (too many stores, too noisy). |
| **Scope** | **All 18 cities** (`CITY_IDS = range(18)`). 1,620 city-days over 90 days. |
| **Storytelling layer** | **Intraday: the 24-hour city sales profile is the primary explanatory texture.** The day triggers; the hourly shape explains *when* and (via hourly stockout) *whether availability is the cause*. |
| **Segmentation** | **Cluster cities into a few labelled, human-readable segments for storytelling.** No cross-city weighting/averaging — each replay is one city, so segments are *descriptors* (color/context on the card), not a peer-mixing mechanism. Replaces the meaningless density-tier hack. |
| **Triggers** | **Restudy the city distribution and detrend** before setting thresholds (city data is lift-dominated with +6% drift; raw `-20%/+30%` is store-era and wrong). |
| **Logging** | **Mostly cloud.** Supabase + Langfuse are authoritative for everything that persists across runs or feeds the dashboard. Local keeps only the build/compute layer + an optional gitignored debug mirror. (See "Data tiering".) |
| **Storage** | **Supabase is the single read source for both the agent and the dashboard.** It stores only city-grain data + memory + analytics; never store/product rows. **DuckDB is ingestion-only** — it aggregates raw parquet → city-day/city-hour + analytics, pushes to Supabase, and is then idle. The agent never reads DuckDB in production (only an offline test fixture does — see "Data tiering"). |

### Confirmed decisions

1. **Analytical approach** → **Focused statistical layer**: STL detrend for triggers, scikit-learn city segmentation with labels, per-city correlation priors. Adds `statsmodels` + `scikit-learn`.
2. **Read path** → **Supabase is the read source for the agent and the dashboard.** DuckDB is ingestion-only; offline dry-run/CI use a local fixture source.

*Decided without a question (override if you disagree):* intraday is **explain-first** — the primary trigger stays on the daily detrended residual; we also compute an intraday anomaly score and may optionally flag "flat day, broken peak" cases, but intraday is not the primary alarm.

---

## Data tiering (the "mostly cloud" split)

| Local — **ingestion + offline test only** (gitignored) | Cloud — **the read source + record** (Supabase + Langfuse) |
| --- | --- |
| `data/raw/train.parquet` — raw source | `rca_city_series` (city-day) + `rca_city_hourly` (city-day-hour) — agent + dashboard time series |
| `data/rca.duckdb` — ingestion staging (raw→aggregate→push), then idle; also the offline test fixture source | `rca_city_normals` + analytics: `rca_city_signal` (STL residual + anomaly score per city-day), `rca_city_segment` (label), `rca_city_correlations` (driver priors) |
| `data/context_pack.json` — prompt grounding (rebuilt by `rca profile`) | `rca_city_profile` — accumulating per-city memory |
| `data/analysis/*.csv` — threshold-study outputs (summary `.md` stays committed) | `rca_outcome` — run outcomes + decision card + report |
| **Optional** `--save-local` debug mirror of the *last* run | **Langfuse** — every LLM call's trace, cost, latency |

**Deleted:** `data/runs.duckdb` (legacy), committed `data/analysis/agent_benchmark_runs/` folders, `output/story_reports/`, and the Supabase `store_series` (store×product grain) table.

**Read-source abstraction (new work):** every tool currently reads `data/rca.duckdb`. They move behind a `DataSource` interface with two implementations — `SupabaseSource` (production: the agent's tools and the dashboard both read here) and `DuckDBSource` (offline dry-run/CI only, reading the local staging file or a tiny committed fixture). This keeps CI network-free without contradicting "the agent reads Supabase" in production.

**CI/dry-run:** read via `DuckDBSource`/fixture; write via in-memory or `--save-local`. Never the network.

---

## Analytical layer (new — the "more stats/ML" ask)

Precomputed offline (deterministic), pushed to Supabase, and injected into prompts as priors. On-theme with "spend compute where it's hard; precompute structure; let the LLM reason over it." Recommended dependencies: `statsmodels`, `scikit-learn`.

1. **STL trend/seasonal decomposition** (statsmodels) per city daily series → trend + weekly seasonality + **residual**. The residual is the drift-free anomaly signal — this is what fixes the lift-dominance/+6%-drift problem. Triggers fire on a **robust z-score (median + MAD)** of the residual, not raw trailing-7d %.
2. **Intraday deviation profile** — per-hour z-score of the day's 24-hour vector vs the city's typical hourly shape → "which hours drove the move." (Verified on real data: ~4 hours carry 40–51% of a drop day's shortfall; hourly stockout often does *not* align, which lets the agent honestly distinguish demand- vs availability-driven dips.)
3. **City segmentation** (scikit-learn KMeans on per-city features: volume level, volatility, weekday shape, intraday shape, trend slope) → 3–4 clusters, **hand-labelled** ("steady high-volume", "volatile low-volume", "weekend-led", …). Replaces the density-tier hack; the label is storytelling context, not a peer-average.
4. **Per-city driver correlation priors** (numpy/pandas) — correlation of the daily sales residual vs stockout / discount / activity / weather → a prior each specialist sees ("in this city, residual correlates −0.5 with stockout rate"). Keeps the agent from re-discovering structure every run.
5. **(Optional/maximal)** changepoint detection (CUSUM in numpy, or `ruptures`) for structural level shifts → feeds the controller's "one-off vs structural" question; multivariate anomaly (IsolationForest) as a cross-check.

---

## Known breakage inventory (what the blunt rename left behind)

Verified by reading the tree. The rounds below fix each; this is the "why".

1. **Benchmark broken** — `bench.py` passes store aliases (`"h555"`) into a `city_id: int` field.
2. **`rca run --store h555` crashes** — string matched against an integer `city_id` column.
3. **Tool type bug** — `city_id` declared `string` in most tool schemas but `integer` in `get_peer_city_context`; dataframe match is on `int`, so a string arg silently returns no rows.
4. **Schema lies** — Supabase `rca_outcome.store_id` holds city ids; `prefix` overloaded as a density tier; committed migration `0001` still defines `retail_rca.store_id text` / `prefix char(1)`, not matching what the code writes.
5. **Latent reset bug** — `profiles.reset_store_profile` does `.neq("store_id", "")` (string vs int column).
6. **Readability damage** — `by_store`/`store_frame`/`store_rows` over city data; "store-day"/"this store" in tool descriptions; `DISTIL_SYSTEM_PROMPT` says "individual retail store".
7. **Dead code** — `STORE_MAP`, `STORE_ID_TO_ALIAS`, `_make_store_alias`.
8. **Weak validation** — `_validate_scope_counts` only prints; `EXPECTED_TABLE_ROWS` no longer covers fact tables.
9. **No first-week warmup** — only an implicit 3-day `min_periods`, not an explicit 7-day no-trigger window.
10. **Peer tool is noise** — density-tier ranking with few cities per tier; being replaced by labelled segments.
11. **Logging split** — Langfuse + Supabase **and** `runs.duckdb` + local card/report/trace/memo files; `eval`/`story` read those files.
12. **Scratch + stale files** — `refactor.py`, `refactor_dashboard.py`, `query_schema.py`, `.agents/AGENTS.md` (dup), `docs/UI_PLAN.md`, `docs/analysis/rca_test_scenarios.md`, `docs/analysis/agent_benchmark_review.md`, old run/story folders.
13. **Uncommitted on `main`** — no checkpoint, no branch.

---

## Round A — Stabilise and checkpoint (no behaviour change)

- **A1.** Branch `redesign/city-pivot` off `main`; commit the uncommitted WIP as a single labelled checkpoint (rollback-safe).
- **A2.** Delete scratch scripts (`refactor.py`, `refactor_dashboard.py`, `query_schema.py`) — intent now captured here.
- **A3.** Get green as-is: `uv run python -c "import rca"`, `uv run pytest`, dry-run smoke (after the CLI fix in B2 if needed). Fix only what's needed for import + tests; no refactor yet.

_Checkpoint:_ branch exists, WIP committed, scratch gone, import + pytest green.

---

## Round B — Make the city grain real and consistent

- **B1. Scope + validation.** Confirm `CITY_IDS = range(18)`; make `_validate_scope_counts` **assert**; restore/assert fact-table coverage. **Soft pause:** confirm all 18 cities have the full 90-day span; if some are short, decide drop-or-relax per city.
- **B2. Identity rename, by hand.** Delete `STORE_MAP`/`STORE_ID_TO_ALIAS`/`_make_store_alias`; CLI `--store`→`--city` (int); fix `bench.py` scenarios (or retire bench for `replay`, Round D); rename vars (`by_store`→`by_city`, `store_frame`→`city_frame`, etc.); rename lying functions (`get_store_day_evidence`→`get_city_day_evidence`, `get_store_profile`→`get_city_profile`, `distil_store_profile`→`distil_city_profile`, `distil_all_stores`→`distil_all_cities`, `reset_store_profile`→`reset_city_profile`); sweep tool/prompt text ("store-day"→"city-day", "individual retail store"→"a city").
- **B3. Tool param types.** `city_id` is `integer` in every schema; coerce to int at the tool boundary.
- **B4. Replace peer tool with segment descriptor.** Swap the density-tier averaging for the labelled-segment descriptor from the analytical layer; state the small-sample caveat ("18-city aggregate sample"). Update the stale "15-store" caveat everywhere.
- **B5. Supabase schema truth (you run the SQL).** One migration: rename `store_id`→`city_id` (int), `prefix`→`density_tier`/segment, drop the `store_series` (store×product) table, align table names to the `rca_city_*` set, add `rca_city_hourly` + analytics tables. **I author it; you run it in the SQL Editor.** Then fix every `.eq("store_id", …)`/upsert key and the `reset` `.neq` bug.
- **B6. Read-source abstraction.** Introduce `DataSource` with `SupabaseSource` (production) and `DuckDBSource` (offline test). Move `signals.py` / `tools.py` / `evidence.py` data access off the direct `duckdb.connect(...)` calls onto the injected source. Production runs read Supabase; dry-run/CI inject `DuckDBSource`. (Can land incrementally: keep DuckDB reads working until `SupabaseSource` is verified against the same numbers.)

_Checkpoint:_ graph integration tests use injected stubs; a live run reads Supabase and returns the same numbers as the local staging file for a spot-checked city-day; pytest green; no "store" except in raw-data column notes and git history.

---

## Round C — Trigger science + analytical layer (the core)

- **C1. Build the analytical layer (at ingestion time).** Add the aggregation for **city-hour**; compute STL residuals + anomaly scores, intraday deviation profiles, city segments (+ labels), and driver-correlation priors — all in the DuckDB ingestion stage using `statsmodels`/`scikit-learn`. **Push every result to Supabase analytics tables**; the agent reads them back from Supabase at run time (it never recomputes).
- **C2. Recompute the distribution + choose triggers.** Run `rca analyze` over 18 cities on the **STL residual**; regenerate `docs/analysis/sales_signal_distribution_summary.md` with correct city headers. Set `DEFAULT_SIGNAL_METRIC` (residual robust-z), `DEFAULT_DROP/LIFT` thresholds from percentiles; write the drop/lift-focus rationale into the doc.
- **C3. Explicit 7-day warmup.** No triggers in the first 7 calendar days; flag warmup days distinctly from `insufficient_history`.
- **C4. Intraday tool + prompts.** New `get_intraday_profile(city_id, dt)` (hourly sales + hourly stockout vs typical shape, with per-hour deviation). Add an intraday section to the sales/ops specialist prompts and an "hours that drove it" line to the decision card. Note the honest limit: discount/activity are daily-only (no hourly).
- **C5. Recompute prompt data-context.** Rebuild `context_pack` for 18-city grain incl. segment label + correlation priors. Run `/prompt-audit` on any prompt text touched in B2/C4/C5 before committing.

_Checkpoint:_ residual-based triggers balanced (not lift-swamped); summary doc regenerated and self-consistent; warmup verified; intraday tool returns sane hours on a known drop day; context pack rebuilt; prompt-audit clean.

---

## Round D — Chronological replay + mostly-cloud logging

- **D1. `rca replay --city <id>`.** Select that city's trigger days (post-warmup), run oldest to newest, distil after each so memory accumulates; write a short "how the profile evolved" summary. Primary demo/test.
- **D2. `rca reset-memory --city <id> | --all`.** Int-safe; clears `rca_outcome` (+ `rca_city_profile`); never touches dim/fact/analytics; prints what was cleared.
- **D3. Mostly-cloud logging.** `RunSink` abstraction (the write side, paired with the `DataSource` read side from B6): `CloudSink` (Supabase + Langfuse) authoritative; `LocalMirrorSink` writes the optional `--save-local` debug copy; dry-run/CI use in-memory or the mirror (no network). Remove `RunLogger.write_to_db`→`runs.duckdb` and the always-on local artifact writes.
- **D4. Cleanup.** Delete `data/runs.duckdb`, `output/story_reports/`, old `agent_benchmark_runs/`; update `.gitignore`. `eval`/`story` read from Supabase in prod, the local mirror/fixture in dev.

_Checkpoint:_ `replay --city 0 --reset` shows triggered dates processed oldest to newest and memory reflecting history by later runs; pytest green.

---

## Round E — Tests, docs, dashboard, land

- **E1. Tests to city grain.** Update `test_signals`/`test_tools`/`test_database`/`test_evidence`/`test_outcomes`; add tests for the 7-day warmup, the intraday tool, the STL residual trigger, and a no-local-writes assertion; replace the broken bench-scenario test with a `replay` dry-run smoke.
- **E2. Docs consolidation (conflict pass each).** Delete `docs/UI_PLAN.md`, `rca_test_scenarios.md`, `agent_benchmark_review.md`. Reconcile `README`/`AGENTS`/`CLAUDE`/`PRD` to: city grain, 18 cities, intraday layer, statistical/segment layer, restudied triggers, mostly-cloud logging, DuckDB-as-cache, `replay`. Resolve the `.agents/AGENTS.md` duplicate. Fix the "15-store" caveat everywhere.
- **E3. Dashboard.** Finish `dashboard/src/app/cities/`; add an **intraday view** (24-hour profile vs typical) and the **segment label**; point reads at renamed `city_id`/`density_tier`/analytics tables; remove store routes.
- **E4. Land.** Delete this plan. Final green: import, pytest, `rca build` (18 cities) → `analyze` → `replay --city <id>` live smoke, dashboard loads. Commit, push, `gh run list --limit 1` green.

---

## Open risks / watch items

- **Dep weight:** `statsmodels` + `scikit-learn` are sizeable; justified by the analytical layer but confirm before adding (fork 1).
- **18-city span:** not all cities guaranteed 90 complete days (B1 soft pause).
- **Thin stories are valid:** muted city-days with no driver are an honest "no material driver" outcome; the evaluator's restraint dimension should reward that, not punish a short card.
- **STL on 90 days:** ~12 weekly cycles — enough for a weekly seasonal STL, but trend estimates near the series ends are shaky; use robust settings and don't over-read the first/last week (aligns with the warmup).
- **Intraday honesty:** hourly alignment exists for sales+stockout only; discount/activity stay daily — prompts must not imply intraday precision we don't have.
- **Supabase read latency/quota:** the agent now reads Supabase per tool call (several per specialist). Data is tiny and indexed, so reads are cheap — but batch where natural (one context fetch per specialist rather than many) and confirm the free-tier request budget is comfortable for a full `replay`.
- **`SupabaseSource` parity:** the live read path must return the same numbers as the DuckDB staging file — verify with a spot-check before deleting any DuckDB read code (B6 lands incrementally for this reason).
