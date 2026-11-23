CREATE TABLE IF NOT EXISTS storage.erm_qualification_input(profile text PRIMARY KEY, payload jsonb NOT NULL, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS storage.erm_qualification_output(profile text PRIMARY KEY, status text NOT NULL, payload jsonb NOT NULL, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS storage.erm_enrollment_input(profile text PRIMARY KEY, payload jsonb NOT NULL, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS storage.erm_enrollment_output(profile text PRIMARY KEY, status text NOT NULL, payload jsonb NOT NULL, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS storage.erm_enrollment_outbox(campaign_id text NOT NULL,profile text NOT NULL,email text NOT NULL,status text NOT NULL CHECK(status IN ('submitting','submitted','confirmed','uncertain')),request jsonb NOT NULL,receipt jsonb,updated_at timestamptz DEFAULT now(),PRIMARY KEY(campaign_id,profile),UNIQUE(campaign_id,email));
INSERT INTO storage.erm_recruiting_control(id) VALUES('enrollment') ON CONFLICT DO NOTHING;
