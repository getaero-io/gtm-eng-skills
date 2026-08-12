# Warm-intro ask threads

This example converts reviewed warm-path rows into grounded draft messages, then
provides a separate approval-gated LinkedIn activation command. Draft generation
does not imply approval, and scoring does not prove that a connector knows the
target.

Run [`../target-account-warm-intro-campaign/`](../target-account-warm-intro-campaign/)
for campaign selection and audit artifacts, then
[`../warm-intro-scoring/`](../warm-intro-scoring/) for target-person scoring and
CSV export. This example owns drafting, approval state, send idempotency, rate
policy, and the activation log.

## Input: scorer CSV

`draft_asks.py` consumes either the campaign orchestrator's `warm_paths.csv` or
the output of `warm-intro-scoring/lookup.py --csv` directly. Both use the same
namespaced path and drafting contract; no manual export or column rename is
required.

All of these columns are required:

| Column | Semantics |
|---|---|
| `campaign_id` | Stable campaign namespace. |
| `owner_id` | Stable campaign-owner namespace. |
| `connector_id` | Stable canonical connector ID. |
| `target_id` | Stable canonical target ID. |
| `path_id` | Versioned ID derived from campaign, owner, connector, and target IDs. |
| `connector_name` | Connector display name. |
| `connector_linkedin` | Connector profile URL. |
| `connector_company` | Connector current company, if known. |
| `target_name` | Person requested in the introduction. |
| `target_title` | Target's current title; preserved in the prompt and draft output. |
| `target_company` | Target company. |
| `shared_signal` | Highest-priority evidence type. |
| `shared_detail` | Human-readable evidence detail. |
| `relationship_confidence` | Owner-to-connector confidence. |
| `direct_intro_score` | Explicit score component. |
| `work_overlap_score` | Explicit score component. |
| `relationship_score` | Explicit score component. |
| `school_city_community_score` | Explicit score component. |
| `role_industry_score` | Explicit score component. |
| `investor_score` | Explicit score component. |
| `total_score` | Sum of target-person components, or legacy discovery score. |
| `segment` | `strong_warm_intro`, `review_warm_intro`, or `no_strong_path`. |
| `evidence_ids` | Semicolon-delimited citations. |

`why_target_cares`, `permissionless_value`, and `reviewed_override` are optional
additive columns. When the first two are absent or blank, the prompt tells the
model to omit that context rather than invent it. `reviewed_override` is a
human-set provenance gate for a review path; it is never inferred from score.
Before any model call, the drafter recomputes `path_id` from the campaign,
owner, connector, and target columns and rejects a mismatch. The sender repeats
that validation and requires the same four fields, so an edited or forged path
cannot mint a fresh activation identity.

The drafter selects the strongest scored reason in this order: confirmed direct
introduction, dated work overlap, school/city/community, role/industry, then
investor context. A legacy `verified_work_overlap` signal is normalized to dated
work overlap. Company proximity explicitly says that dates and familiarity are not
confirmed.

Draft eligibility is fail closed:

- `strong_warm_intro` is eligible, but every generated row still starts
  `approved=false`;
- `review_warm_intro` is eligible only when the command includes
  `--allow-reviewed` and that specific row has `reviewed_override=true`;
- `no_strong_path` is routed to direct outreach and never causes a model call.

## Output: draft CSV

`draft_asks.py` writes one row per selected path:

| Column | Semantics |
|---|---|
| `campaign_id` | Preserved campaign namespace. |
| `owner_id` | Preserved owner namespace. |
| `connector_id` | Preserved canonical connector ID. |
| `target_id` | Preserved canonical target ID. |
| `path_id` | Preserved path identity. |
| `connector_name` | Preserved display name. |
| `connector_linkedin` | Preserved activation coordinate. |
| `target_name` | Preserved target name. |
| `target_title` | Preserved target title. |
| `target_company` | Preserved target company. |
| `shared_signal` | Preserved source signal. |
| `shared_detail` | Preserved evidence detail. |
| `why_target_cares` | Supplied target context, possibly blank. |
| `permissionless_value` | Supplied value offer, possibly blank. |
| `draft_subject` | Model-generated subject. |
| `draft_body` | Model-generated body, or blank on failure. |
| `total_score` | Preserved score. |
| `segment` | Preserved eligibility segment. |
| `reviewed_override` | Preserved explicit review provenance, default `false`. |
| `approved` | Always `false` when generated. |
| `message_version` | Starts at `1`. Increment after a material edit. |
| `status` | `ok` or an `error: ...` diagnostic. |

Each eligible model call is independent. Rows are sorted by descending
`total_score`; `--top` limits that ordered eligible set. A model/API failure
produces an error row with empty draft fields and does not stop later rows. There
is no automatic retry, response cache, or cost ledger in this script. Rerun only
the reviewed failed paths, and check your provider's current pricing and retention
behavior rather than relying on a fixed cost estimate.

## Drafting

The prompt requires a body under 80 words with the ask first, an evidence-safe
reason second, and concrete context third when supplied. It prohibits filler and
invention. Model output is parsed as strict JSON with `subject` and `body` keys;
Markdown code fences are tolerated, but missing/non-JSON content is an error.

From the repository root:

```bash
# Produce the scorer CSV first.
python3 -m examples.office-hours.warm-intro-scoring.lookup \
  --db /tmp/warm-intros.db \
  --company "Northstar AI" \
  --target-name "Nora Imani" \
  --target-title "Head of GTM Engineering" \
  --campaign-id "fictional-warm-intro-campaign" \
  --owner-id "campaign-owner" \
  --target-id "contact-northstar-gtm" \
  --csv /tmp/scored_connectors.csv \
  --quiet

# After loading DEEPLINE_API_KEY from your secret manager or ignored environment,
# draft the highest-ranked 20 paths.
python3 \
  examples/office-hours/warm-intro-ask-threads/draft_asks.py \
  --input /tmp/scored_connectors.csv \
  --output /tmp/ask_drafts.csv \
  --top 20 \
  --verbose
```

To draft a human-reviewed `review_warm_intro` row, first verify its evidence and
set only that row's `reviewed_override=true`, then add `--allow-reviewed`. The CLI
flag alone is insufficient.

Do not put API keys in the CSV, command line, or shell history. Load them from a
secret manager or ignored environment before starting the process, and never
commit the credential source.

## Mandatory human review

Before activation, review each row against the cited source:

- Confirm the connector's identity and that the profile URL belongs to that person.
- Confirm the target's name, title, company, and current relevance.
- For work overlap, verify both employment intervals overlap. Treat missing or
  non-overlapping dates as company proximity only.
- Confirm the owner-to-connector relationship can support the ask. Shared employer,
  role, school, city, community, appearance, or investor context alone is not proof
  of familiarity.
- Remove invented claims, private details, sensitive inferences, and any value offer
  you cannot deliver.
- Check consent, do-not-contact/suppression state, legal purpose, channel policy,
  and the connector's reasonable expectations.
- Leave failed or empty rows unapproved. Set `approved=true` only on selected,
  final copy. Increment `message_version` after any material edit that should be a
  distinct send.

The live sender admits only rows whose body is non-empty and whose `approved` value
case-insensitively equals `true`. Dry-run mode may display unapproved rows for
review; that does not make them live-sendable.

## Dry run and activation

```bash
# Preview. No actor call; a zero delay is allowed in dry-run mode.
python3 examples/office-hours/warm-intro-ask-threads/send_via_linkedin.py \
  --input /tmp/ask_drafts.csv \
  --dry-run \
  --delay 0 \
  --log-db /tmp/warm-intro-send-log.db

# Live activation. Load DEEPLINE_API_KEY from your secret manager or ignored
# environment first. Only explicitly approved rows are loaded.
python3 \
  examples/office-hours/warm-intro-ask-threads/send_via_linkedin.py \
  --input /tmp/ask_drafts.csv \
  --limit 5 \
  --delay 90 \
  --log-db /tmp/warm-intro-send-log.db
```

LinkedIn automation carries platform and account risk. Revalidate the selected
actor and platform terms before use. Live delay must be at least 60 seconds. The
per-run limit must be 1–10, defaults to 5, and is reduced by successful sends in
the preceding rolling 24 hours. The hard rolling limit is 10. Unresolved
`dispatching` and `needs_reconciliation` intents also consume capacity so
concurrent or ambiguous work cannot oversubscribe the last slot.

## Idempotency, retries, and the send log

For each live row:

```text
idempotency_key = SHA256(JSON([
  "warm-activation-v1", campaign_id, owner_id, path_id, "linkedin", message_version
]))
```

The exact serialization is shared with path scoring and is versioned; it is not a
delimiter-concatenation contract. `BEGIN IMMEDIATE` commits the immutable send
intent, one attempt row, and a `dispatch_started` event before the actor call. The
mutable `sends` row is the current outbox projection. A second process cannot
claim `dispatching`, `needs_reconciliation`, or `sent` work. Reusing a key with a
different URL/body/intent hash is rejected and requires a new message version.

Only `FileNotFoundError` at process creation is treated as proven pre-dispatch:
the event remains immutable, the projection returns to `ready`, and a retry
creates attempt 2. `SUCCEEDED` plus a provider run ID is the only result recorded
as `sent`. Every non-success/`UNKNOWN` status, missing run ID, malformed response,
response loss, normal exception, `KeyboardInterrupt`, `SystemExit`, or stale
post-dispatch recovery becomes `needs_reconciliation` and blocks automatic retry.
Process-control exceptions are re-raised after the durable state update. Dry-run
rows consume no live idempotency key.

The documented Apify actor invocation exposes no atomic provider idempotency key.
The local outbox prevents concurrent or automatic retry, but it cannot determine
whether an ambiguous provider call delivered the message. Reconcile against the
provider run/request evidence before any manual state transition or new version.

The mutable `sends` outbox projection stores:

| Column | Semantics |
|---|---|
| `id` | Autoincrement log row ID. |
| `sent_at` | UTC reservation/result timestamp used by the rolling window after success. |
| `connector_linkedin` | Activation coordinate. |
| `connector_name` | Display name. |
| `target_name` | Target named in the ask. |
| `message_preview` / `message_body` | Immutable intent snapshot; both remain sensitive. |
| `status` | `ready`, `dispatching`, `needs_reconciliation`, `sent`, or `dry_run`. |
| `apify_run_id` | External run ID when available. |
| `error_detail` | Truncated diagnostic for failed work. |
| `idempotency_key` / `intent_hash` | Stable live identity and immutable-intent fingerprint; null for previews. |
| `campaign_id`, `owner_id`, `connector_id`, `target_id`, `path_id`, `channel`, `message_version` | Explicit activation namespace and path endpoints. |
| `contract_version` | Explicit current outbox/migration marker (`warm-send-outbox-v1`). |
| `reservation_owner` / `current_attempt_id` | Owning process and current immutable attempt while dispatching. |
| `reservation_updated_at` / `dispatch_started_at` | UTC state timestamps; stale dispatch is reconciled, never reclaimed for resend. |

`send_attempts` has one immutable row per dispatch number and owner token.
`send_events` is the immutable event stream, including `dispatch_started`,
`pre_dispatch_failure`, provider results, ambiguity, and stale recovery. SQLite
triggers reject updates and deletes from both audit tables; state changes update
only the outbox projection and append events.

Existing logs are migrated additively when opened. Because both the path builder
and activation key changed, any non-preview row without a complete namespaced
intent fingerprint and the explicit current contract marker is a global
activation barrier. Before every reservation, the sender recomputes and matches
the versioned path ID, activation key, and full intent hash for every historical
live row. Nonblank placeholders, forged keys, and old path/key algorithms do not
count as migration. Activation fails closed until an operator reconciles and
explicitly migrates every historical live row. Stop older sender processes during
the upgrade; they do not understand the namespaced contract. Back up and
access-control this database: it contains personal data and message excerpts. The
local log is the activation source of truth; deleting it removes duplicate-send
protection.

## Files and fixtures

- `draft_asks.py`: validated scorer input, grounded prompt construction, model
  calls, and unapproved draft output.
- `send_via_linkedin.py`: approval filtering, dry-run display, rate enforcement,
  durable outbox claim, immutable attempt/event audit, external actor call, and
  reconciliation-safe lifecycle logging.
- `sample_scored_connectors.csv`: fictional scorer-contract input.
- `sample_ask_drafts.csv`: fictional, unapproved draft output for dry-run testing.
- `test_draft_asks.py` and `test_send_via_linkedin.py`: contract, segment gates,
  evidence wording, approval, migration, idempotency, response-loss,
  interruption, immutable audit, concurrency, and rate-policy tests.

For a safe local smoke check:

```bash
python3 examples/office-hours/warm-intro-ask-threads/send_via_linkedin.py \
  --input examples/office-hours/warm-intro-ask-threads/sample_ask_drafts.csv \
  --dry-run \
  --delay 0 \
  --log-db /tmp/warm-intro-example-send-log.db
```
