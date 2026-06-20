-- RLS policies for retail_rca schema
-- Applied via Supabase MCP (migration name: retail_rca_0002_rls_policies)
-- service_role bypasses RLS automatically — no policy needed for backend writes.
-- anon key gets SELECT only (enforced by policy) — safe for Next.js dashboard.

ALTER TABLE retail_rca.store_series   ENABLE ROW LEVEL SECURITY;
ALTER TABLE retail_rca.store_normals  ENABLE ROW LEVEL SECURITY;
ALTER TABLE retail_rca.rca_outcome    ENABLE ROW LEVEL SECURITY;
ALTER TABLE retail_rca.store_profile  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_store_series"
    ON retail_rca.store_series FOR SELECT
    TO anon USING (true);

CREATE POLICY "anon_read_store_normals"
    ON retail_rca.store_normals FOR SELECT
    TO anon USING (true);

CREATE POLICY "anon_read_rca_outcome"
    ON retail_rca.rca_outcome FOR SELECT
    TO anon USING (true);

CREATE POLICY "anon_read_store_profile"
    ON retail_rca.store_profile FOR SELECT
    TO anon USING (true);

GRANT USAGE ON SCHEMA retail_rca TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA retail_rca TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA retail_rca
    GRANT SELECT ON TABLES TO anon, authenticated;
