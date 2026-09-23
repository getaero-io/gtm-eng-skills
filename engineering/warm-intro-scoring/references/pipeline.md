# Customer database and incremental scoring contract

This is a deployment recipe, not an already-running Play. Reuse the current workspace's supported database and Play interfaces; inspect their live contracts before authoring provider calls or triggers. Do not claim the SQL template or an installed skill enabled production automation.

## Input and ten-target fallback

Require warm connections plus requester/customer context. Targets are optional. Resolve people by stable source IDs or verified canonical profile URLs. Names alone cannot merge records. A connection-list membership establishes its source provenance, not relationship strength.

If no targets are supplied:

1. Read the scoped customer's existing customer/contact tables and ICP. Select up to ten distinct relevant customer contacts, covering company size, function, industry and career stage where available. Use a recorded deterministic seed or stable ID ordering within strata so reruns retain the cohort. Do not choose only easy-to-match contacts.
2. If fewer than ten real customer contacts are available, discover the remaining example targets in the same market through approved sources. Record why each fits and its source. Label these `example_target`; never claim they are customers.
3. If context, identity verification, available records or the approved budget cannot support ten, retain the smaller verified sample and explain the shortfall. Do not invent people or silently broaden the ICP. Persist the cohort rather than resampling every run.

## Database setup

Inspect the active tenant, dialect, existing schema and permissions. Use `assets/customer-db.sql` for a dedicated PostgreSQL customer database. In a shared database, add tenant keys to every primary/foreign/unique key and apply tenant isolation before use. Never use the template across tenants without this adaptation.

The five tables separate identities, campaign roles, feature snapshots, durable work and score versions. `CREATE TABLE IF NOT EXISTS` is not schema compatibility verification: compare columns and constraints before applying it. Retain relationship/willingness evidence in the existing private evidence store; reference its revision in job payloads. Do not put secrets into job payloads or publish raw profiles. Use parameterized inserts/upserts. Protect raw source storage and the tables with the customer's existing access controls.

## Full-profile extraction

Enrich the union of connectors and targets, once per unique person per freshness window. Use the existing Apify profile adapter or Deepline profile tools in `sources.md`; inspect the provider schema and validate identity plus employment/education on a one-contact pilot. These calls enrich known profiles; connection-list collection is a separate authorized source.

Request all available profile history, not only a headline. Extract current/past roles, normalized employers, dated employment, function, seniority/career stage, industry/vertical/niche, company type, education/school/cohort, and explicitly supported professional communities/projects. Preserve partial dates and unknown values. Optional public interests/social activity require attributable evidence; do not infer sensitive traits. See `factors.md` for candidate factors and which are actually scored.

Each feature carries source/evidence IDs, observation date, uncertainty, extraction version and a normalized profile hash. Retain raw provider receipts privately for audit and retries. Keep fetch timestamps out of the content hash. AI/Jev may extract structured features using the existing event workflow, but must not invent relationships, willingness or score weights. Validate schema and citations before accepting output.

Store `partial` or `failed` with `miss_reason` when unavailable; retry only unresolved rows within the approved budget. No email lookup is required merely to score profiles. Report requested/enriched/partial/held counts separately for connectors and targets.

## Trigger and worker pattern

Register a supported Play trigger or bounded polling job for changes to campaign membership, normalized profile content, and relationship/willingness evidence. Capture ingestion and a durable queue job atomically when possible; otherwise use a persisted cursor with an overlap window and deduplication. Never advance the cursor past an unpersisted event.

For each event:

1. Validate tenant/campaign/owner and canonical identity. Upsert membership and enqueue with a unique key derived from campaign, owner, source event ID and processing version. Duplicate delivery must not schedule duplicate paid work.
2. Claim work atomically with a lease (PostgreSQL `FOR UPDATE SKIP LOCKED` inside a transaction). Recover expired leases. Cap retry attempts and use backoff; ambiguous paid-call outcomes require receipt reconciliation before retry.
3. Enrich only new/stale contacts; create a feature snapshot only when normalized content or extraction version changes. Preserve original source observation times when reusing cached records.
4. Recompute affected pairs: a connector change touches that connector × active targets; a target change touches active connectors × that target; a dual-role contact touches both sets. Exclude self-pairs and the requester. Relationship/willingness updates invalidate precisely the relevant paths. Removal immediately excludes a person from artifacts without deleting historical evidence.
5. Build reviewed evidence input for `scripts/score.py`. Freeze `as_of`. Define `input_version` as a hash of both profile hashes, feature version, relationship/willingness evidence revisions and as-of date. A model or feature-version change explicitly backfills the active campaign. Unknown relationship or willingness remains a hold even with rich profiles.
6. Upsert score snapshots under the full version key. Before publishing, compare input versions against current campaign state so an older worker cannot replace newer results. Complete the job only after persisted results are verified.
7. Refresh the existing HTML/CSV artifact atomically from a consistent current-version snapshot. While changed paths await rescore, mark them pending/stale and exclude them from ready recommendations. A fresh decline must suppress the ask immediately, even before the ranking worker finishes. Recheck current willingness before any separately authorized ask action.

For polling, record interval and last successful cursor; do not describe polling as continuous webhook delivery. Freshness expiry must enqueue work even if no new source event arrived. Retain the last good artifact on render failure while clearly marking its age and invalidated paths.

## Deployment acceptance

Verify on fictional fixtures before enabling the customer's trigger:

- New connector, new target, dual-role contact and profile edit affect only expected pairs.
- Duplicate event and worker restart cause no duplicate records or paid calls.
- Identity ambiguity and provider failures remain visible; partial contacts are not silently dropped.
- Evidence-only changes, latest decline and same-day conflict update holds.
- Concurrent old/new jobs cannot publish stale scores; removed contacts vanish from current recommendations.
- All-unknown profiles yield an honest empty/held state; fewer than three valid paths remain fewer than three.
- Ten-target fallback is reproducible and separates actual customers from example targets.

Run existing scorer checks after wiring the adapter. Report actual table names, migration status, provider/run receipts, coverage, queue failures, model/feature version, trigger ID/status, last successful run and artifact location. If only the recipe was authored, say **prepared, not deployed**. No emails, intro sends or public publication are part of this pattern.
