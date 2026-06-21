-- Replay review table: stores per-run quality scores from rca replay.
-- One row per (batch, city, date). Batches let you compare quality across replays.

create table if not exists rca.replay_review (
    id                   bigserial         primary key,
    batch_id             text              not null,
    run_id               text              not null,
    city_id              integer           not null,
    dt                   text              not null,
    signal_label         text              not null,
    eval_score           double precision  not null,
    eval_passed          boolean           not null,
    alignment_score      double precision,
    alignment_label      text,
    pros                 jsonb             not null default '[]'::jsonb,
    cons                 jsonb             not null default '[]'::jsonb,
    improvements         jsonb             not null default '[]'::jsonb,
    reviewer_comment     text              not null default '',
    deterministic_checks jsonb             not null default '[]'::jsonb,
    created_at           text              not null
);

create index if not exists idx_replay_review_city_batch
    on rca.replay_review (city_id, batch_id);
create index if not exists idx_replay_review_city_dt
    on rca.replay_review (city_id, dt);
create index if not exists idx_replay_review_batch
    on rca.replay_review (batch_id);

alter table rca.replay_review enable row level security;

drop policy if exists "anon_read_replay_review" on rca.replay_review;
create policy "anon_read_replay_review"
    on rca.replay_review for select to anon, authenticated using (true);

grant all    on rca.replay_review to service_role;
grant select on rca.replay_review to anon, authenticated;
grant usage, select on sequence rca.replay_review_id_seq to service_role;
