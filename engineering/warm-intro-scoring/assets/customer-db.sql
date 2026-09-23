-- PostgreSQL reference migration. Verify active customer tenant and existing schema first.
-- Apply with the customer DB's supported migration/SQL interface; no credentials here.
BEGIN;
CREATE TABLE IF NOT EXISTS warm_intro_contacts (
  contact_id text PRIMARY KEY,
  source_system text NOT NULL,
  source_id text NOT NULL,
  display_name text NOT NULL,
  linkedin_url text,
  profile_hash text,
  profile_observed_at timestamptz,
  raw_profile_ref text,
  enrichment_status text NOT NULL DEFAULT 'pending'
    CHECK (enrichment_status IN ('pending','complete','partial','failed','identity_hold')),
  miss_reason text,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_system, source_id)
);
CREATE TABLE IF NOT EXISTS warm_intro_memberships (
  campaign_id text NOT NULL,
  owner_id text NOT NULL,
  contact_id text NOT NULL REFERENCES warm_intro_contacts(contact_id),
  role text NOT NULL CHECK (role IN ('connector','target')),
  selection_kind text NOT NULL CHECK (selection_kind IN ('provided','customer_sample','example_target')),
  selection_source text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  PRIMARY KEY (campaign_id, owner_id, contact_id, role)
);
CREATE TABLE IF NOT EXISTS warm_intro_features (
  contact_id text NOT NULL REFERENCES warm_intro_contacts(contact_id),
  profile_hash text NOT NULL,
  feature_version text NOT NULL,
  features jsonb NOT NULL,
  evidence jsonb NOT NULL,
  extracted_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (contact_id, profile_hash, feature_version)
);
CREATE TABLE IF NOT EXISTS warm_intro_jobs (
  job_key text PRIMARY KEY,
  campaign_id text NOT NULL,
  owner_id text NOT NULL,
  source_event_id text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','running','complete','failed','held')),
  attempts integer NOT NULL DEFAULT 0,
  available_at timestamptz NOT NULL DEFAULT now(),
  lease_until timestamptz,
  last_error text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS warm_intro_jobs_pending ON warm_intro_jobs(status, available_at);
CREATE TABLE IF NOT EXISTS warm_intro_scores (
  campaign_id text NOT NULL,
  owner_id text NOT NULL,
  connector_id text NOT NULL REFERENCES warm_intro_contacts(contact_id),
  target_id text NOT NULL REFERENCES warm_intro_contacts(contact_id),
  input_version text NOT NULL,
  model_version text NOT NULL,
  score numeric NOT NULL,
  review_status text NOT NULL,
  components jsonb NOT NULL,
  evidence_ids jsonb NOT NULL,
  scored_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (campaign_id, owner_id, connector_id, target_id, input_version, model_version),
  CHECK (connector_id <> target_id)
);
COMMIT;
