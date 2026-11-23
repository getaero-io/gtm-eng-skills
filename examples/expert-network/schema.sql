CREATE TABLE IF NOT EXISTS storage.erm_v1_episodes (id text PRIMARY KEY, payload jsonb NOT NULL, received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_discover_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_discover_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_qualify_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_qualify_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_recruit_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_recruit_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_onboard_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_onboard_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_match_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_match_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_review_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_review_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_learn_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_learn_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_complete_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_complete_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_waiting_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_waiting_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_declined_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_declined_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_invalid_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS storage.erm_v1_invalid_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now());
