-- Rename rca.replay_review to rca.simulate_review.
-- Run in Supabase SQL Editor after deploying this commit.

alter table rca.replay_review rename to simulate_review;

alter index if exists rca.idx_replay_review_city_batch rename to idx_simulate_review_city_batch;
alter index if exists rca.idx_replay_review_city_dt    rename to idx_simulate_review_city_dt;
alter index if exists rca.idx_replay_review_batch      rename to idx_simulate_review_batch;

alter sequence if exists rca.replay_review_id_seq rename to simulate_review_id_seq;

drop policy if exists "anon_read_replay_review" on rca.simulate_review;
create policy "anon_read_simulate_review"
    on rca.simulate_review for select to anon, authenticated using (true);
