-- Phase 1: Upgrade rca.signals, rca.outcomes, rca.memory
-- Old runtime data is disposable. Signals and outcomes are safe to rebuild.
-- Base ingestion tables (sales, inventory, pricing, promotions, calendar, weather, goals)
-- are NOT touched here.

-- ── signals ──────────────────────────────────────────────────────────────────

drop table if exists rca.signals cascade;

create table rca.signals (
    city_id             integer           not null,
    dt                  text              not null,
    total_sales         double precision  not null,
    expected_sales      double precision,
    deviation_pct       double precision,
    abs_deviation_pct   double precision,
    goal_method         text              not null,
    signal_label        text              not null,
    signal_strength     text              not null default 'none',
    baseline_quality    text              not null default 'insufficient',
    signal_reason       text              not null default '',
    priority_score      double precision  not null default 0,
    weekday             text,
    holiday_name_inferred text,
    first_hypothesis_hints jsonb          not null default '{}'::jsonb,
    build_version       text,
    generated_at        text,
    primary key (city_id, dt)
);

-- ── outcomes ─────────────────────────────────────────────────────────────────

drop table if exists rca.outcomes cascade;

create table rca.outcomes (
    run_id                    text              not null primary key,
    city_id                   integer           not null,
    dt                        text              not null,
    signal_label              text              not null,
    confidence                text              not null,
    headline                  text              not null,
    status                    text              not null default 'complete',
    round_count               integer           not null default 1,
    generated_at              text              not null,
    -- markdown compatibility (dashboard preview columns)
    decision_card_markdown    text              not null default '',
    report_markdown           text              not null default '',
    prediction_markdown       text              not null default '',
    prescription_markdown     text              not null default '',
    -- evolving agent artifacts stored as JSONB
    decision_brief_json       jsonb             not null default '{}'::jsonb,
    hypotheses_json           jsonb             not null default '[]'::jsonb,
    evidence_ledger_json      jsonb             not null default '[]'::jsonb,
    investigation_rounds_json jsonb             not null default '[]'::jsonb,
    critic_reviews_json       jsonb             not null default '[]'::jsonb,
    monitoring_plan_json      jsonb             not null default '{}'::jsonb,
    evaluation_json           jsonb             not null default '{}'::jsonb,
    memory_context_json       jsonb             not null default '{}'::jsonb
);

create index if not exists idx_outcomes_city_dt
    on rca.outcomes (city_id, dt);
create index if not exists idx_outcomes_city_generated_at
    on rca.outcomes (city_id, generated_at desc);
create index if not exists idx_outcomes_signal_label
    on rca.outcomes (signal_label);
create index if not exists idx_outcomes_status
    on rca.outcomes (status);

-- ── memory (ALTER — keep existing rows) ──────────────────────────────────────

alter table rca.memory
    add column if not exists memory_json    jsonb            not null default '{}'::jsonb,
    add column if not exists influence_score double precision;

-- ── RLS and grants ────────────────────────────────────────────────────────────

alter table rca.signals  enable row level security;
alter table rca.outcomes enable row level security;

drop policy if exists "anon_read_signals"  on rca.signals;
create policy "anon_read_signals"  on rca.signals  for select to anon, authenticated using (true);

drop policy if exists "anon_read_outcomes" on rca.outcomes;
create policy "anon_read_outcomes" on rca.outcomes for select to anon, authenticated using (true);

grant all    on rca.signals  to service_role;
grant select on rca.signals  to anon, authenticated;
grant all    on rca.outcomes to service_role;
grant select on rca.outcomes to anon, authenticated;
