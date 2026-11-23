CREATE TABLE IF NOT EXISTS storage.erm_candidate_queue (
 profile text PRIMARY KEY, name text NOT NULL, title text NOT NULL, domain text NOT NULL,
 vertical text NOT NULL CHECK(vertical IN ('law','consulting')),company text NOT NULL,location text,
 source text NOT NULL,evidence jsonb NOT NULL,status text NOT NULL DEFAULT 'research_pending'
 CHECK(status IN ('research_pending','ready','contacted','onboarding','active','declined','rejected')),
 suppressed boolean NOT NULL DEFAULT false, email text, email_verified boolean NOT NULL DEFAULT false,
 source_run text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS storage.erm_recruiting_control (
 id text PRIMARY KEY, search_enabled boolean NOT NULL DEFAULT true, outreach_enabled boolean NOT NULL DEFAULT false,
 program_name text, sender_email text, application_url text, campaign_id text,
 lock_token text,lock_until timestamptz
);
INSERT INTO storage.erm_recruiting_control(id) VALUES('main') ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS storage.erm_refill_runs (
 id text PRIMARY KEY,before_count integer,after_count integer,inserted_count integer,returned_count integer,rejected_count integer,
 created_at timestamptz NOT NULL DEFAULT now()
);
