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

`draft_asks.py` consumes the output of `warm-intro-scoring/lookup.py --csv`
directly. No manual export or column rename is required.

All of these columns are required:

| Column | Semantics |
|---|---|
| `path_id` | Stable connector-to-target path ID. |
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

`why_target_cares` and `permissionless_value` are optional additive columns. When
they are absent or blank, the prompt tells the model to omit that context rather
than invent it.

The drafter selects the strongest scored reason in this order: confirmed direct
introduction, dated work overlap, school/city/community, role/industry, then
investor context. A legacy `verified_work_overlap` signal is normalized to dated
work overlap. Company proximity explicitly says that dates and familiarity are not
confirmed.

## Output: draft CSV

`draft_asks.py` writes one row per selected path:

| Column | Semantics |
|---|---|
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
| `approved` | Always `false` when generated. |
| `message_version` | Starts at `1`. Increment after a material edit. |
| `status` | `ok` or an `error: ...` diagnostic. |

Each model call is independent. Rows are sorted by descending `total_score`; `--top`
limits that ordered set. A model/API failure produces an error row with empty draft
fields and does not stop later rows. There is no automatic retry, response cache,
or cost ledger in this script. Rerun only the reviewed failed paths, and check your
provider's current pricing and retention behavior rather than relying on a fixed
cost estimate.

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
  --csv /tmp/scored_connectors.csv \
  --quiet

# Draft the highest-ranked 20 paths.
DEEPLINE_API_KEY=... python3 \
  examples/office-hours/warm-intro-ask-threads/draft_asks.py \
  --input /tmp/scored_connectors.csv \
  --output /tmp/ask_drafts.csv \
  --top 20 \
  --verbose
```

Do not put API keys in the CSV or commit them. Use the repository's approved
credential-loading method in a real environment.

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

# Live activation. Only explicitly approved rows are loaded.
DEEPLINE_API_KEY=... python3 \
  examples/office-hours/warm-intro-ask-threads/send_via_linkedin.py \
  --input /tmp/ask_drafts.csv \
  --limit 5 \
  --delay 90 \
  --log-db /tmp/warm-intro-send-log.db
```

LinkedIn automation carries platform and account risk. Revalidate the selected
actor and platform terms before use. Live delay must be at least 60 seconds. The
per-run limit must be 1–10, defaults to 5, and is reduced by successful sends in
the preceding rolling 24 hours. The hard rolling limit is 10. Fresh pending
reservations also consume capacity so concurrent processes cannot oversubscribe
the last slot.

## Idempotency, retries, and the send log

For each live row:

```text
idempotency_key = SHA256(path_id + "|linkedin|" + message_version)
```

The SQLite log places a partial unique index on non-null idempotency keys. Before
the external actor call, `BEGIN IMMEDIATE` atomically creates or claims one
`pending` lifecycle row with a random owner token. A second process cannot claim a
fresh reservation for the same key. Only the owning process can finish it.

`SUCCEEDED` is the only terminal actor status recorded as `sent`. Provider status
`FAILED`, `ABORTED`, `TIMED-OUT`, `UNKNOWN`, malformed results, missing executable,
and other ordinary exceptions become `error` and remain retryable. A process
interruption may leave `pending`; it blocks through the exact one-hour TTL and may
be reclaimed only after it becomes older than that TTL. Successful keys are never
resent. Dry-run log rows use no durable idempotency key and do not block a later
live send.

The `sends` table stores:

| Column | Semantics |
|---|---|
| `id` | Autoincrement log row ID. |
| `sent_at` | UTC lifecycle timestamp. |
| `connector_linkedin` | Activation coordinate. |
| `connector_name` | Display name. |
| `target_name` | Target named in the ask. |
| `message_preview` | First 120 characters; still sensitive. |
| `status` | `pending`, `sent`, `error`, or `dry_run`. |
| `apify_run_id` | External run ID when available. |
| `error_detail` | Truncated diagnostic for failed work. |
| `idempotency_key` | Stable live-send identity; null for previews/errors logged outside the reservation lifecycle. |
| `reservation_owner` | Process owner token while pending. |
| `reservation_updated_at` | UTC reservation/finish time used for stale recovery. |

Existing logs are migrated additively when opened. Back up and access-control this
database: it contains personal data and message excerpts. The local log is the
activation source of truth; deleting it removes duplicate-send protection.

## Files and fixtures

- `draft_asks.py`: validated scorer input, grounded prompt construction, model
  calls, and unapproved draft output.
- `send_via_linkedin.py`: approval filtering, dry-run display, rate enforcement,
  atomic reservation, external actor call, and lifecycle logging.
- `sample_scored_connectors.csv`: fictional scorer-contract input.
- `sample_ask_drafts.csv`: fictional, unapproved draft output for dry-run testing.
- `test_draft_asks.py` and `test_send_via_linkedin.py`: contract, evidence wording,
  approval, migration, idempotency, retry, concurrency, and rate-policy tests.

For a safe local smoke check:

```bash
python3 examples/office-hours/warm-intro-ask-threads/send_via_linkedin.py \
  --input examples/office-hours/warm-intro-ask-threads/sample_ask_drafts.csv \
  --dry-run \
  --delay 0 \
  --log-db /tmp/warm-intro-example-send-log.db
```
