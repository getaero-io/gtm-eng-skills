# Warm-intro scoring

This example stores a LinkedIn connection export in SQLite, enriches contact job
histories, ranks possible connectors, and exports a stable CSV that
[`../warm-intro-ask-threads/draft_asks.py`](../warm-intro-ask-threads/draft_asks.py)
accepts directly.

Use the broader
[`../target-account-warm-intro-campaign/`](../target-account-warm-intro-campaign/)
example first when you need account qualification, contact deduplication, buying
committees, org-edge review, provider controls, or campaign ledgers. This example
owns connector discovery and target-person scoring, not activation.

## Two scoring interfaces

The module deliberately separates discovery from evidence-backed target-person
scoring.

### Criteria discovery: `score_contact()` and `lookup.py`

The CLI searches enriched contacts by target company, school, role, or appearance
platform. Its legacy discovery score is:

```text
discovery_score =
  50 × distinct normalized company matches
  + 20 × distinct normalized school matches
  + 40 × distinct normalized appearance-platform matches
  + 15 × role-keyword overlap ratio
  + 5 × connection-recency factor
```

The recency factor is `1.0` for connections no older than 30 days, decays linearly
to `0.5` at three years, and is `0.5` when the date is absent or at least three
years old. The discovery path does not have a target person's employment history,
so a company-name match is `company_proximity`; it does not establish overlapping
dates or a personal relationship.

### Target-person evidence: `score_target_connector()`

When you have an explicit target contact and both employment histories, use
`WarmIntroScorer.score_target_connector()`. Its score is the sum of visible
components:

| Component | Points | Rule |
|---|---:|---|
| `direct_intro_score` | 160 or 0 | At least one direct-introduction evidence ID. |
| `work_overlap_score` | 80 or 0 | Exact normalized employer identity plus an inclusive dated overlap. |
| `relationship_score` | 0, 5, 10, or 15 | Owner-to-connector confidence: unknown, low, medium, high/confirmed. |
| `school_city_community_score` | 40 or 0 | At least one school, city, community, or appearance signal. |
| `role_industry_score` | 20 or 0 | At least one role/industry signal. |
| `investor_score` | 0–3 | Distinct investor signals, globally capped at 3. |

The fixed weights preserve evidence priority even after all weaker components and
relationship confidence are combined. Multiple facts within the same non-investor
tier add reasons and citations, not points.

A dated work overlap requires matching employer identity, both start dates, and a
resolvable end for each interval. A blank end is resolved to `as_of` only for a
current role. A same-company name with missing or non-overlapping dates remains
`company_proximity`, earns no work-overlap points, and routes to review. Legal
suffixes and punctuation are normalized; meaningful identity tokens are not
discarded.

Target-person segmentation is:

- `strong_warm_intro`: direct-introduction or dated-overlap evidence plus a scored
  owner-to-connector relationship;
- `review_warm_intro`: another non-investor signal, including company proximity;
- `no_strong_path`: no qualifying fact or investor-only context.

No score is activation approval. Confirm that the connector knows the target,
verify the cited dates and relationship, and review the proposed ask.

## Input and storage

`ingest.py` reads the standard LinkedIn Connections export. It skips any preamble
until a header beginning with `First Name,`.

| CSV column | Requirement | Stored field |
|---|---|---|
| `First Name` | Required value | `Contact.first_name` |
| `Last Name` | Required value | `Contact.last_name` |
| `URL` | Required value | `Contact.linkedin_url` |
| `Email Address` | Optional | `Contact.email` |
| `Company` | Optional | `Contact.current_company` |
| `Position` | Optional | `Contact.current_position` |
| `Connected On` | Optional | Parsed as `%d %b %Y`; invalid values become unknown. |

Rows missing a required value are skipped. Ingestion generates UUID contact IDs;
do not reingest the same export into the same production database without a
separate deduplication policy.

`enrich.py` batches unenriched profile URLs through its configured Apify actor,
polls the actor run, and replaces stored experiences and education records for a
matched contact. This is live external collection. Review provider terms,
authorization, privacy purpose, actor schema, cost, and account/platform risk
before running it. Keep tokens outside the repository.

## CLI

Run these commands from the parent of `examples` so the package imports resolve,
or adapt the module prefix to your repository checkout:

```bash
# 1. Ingest a LinkedIn connections export.
python -m examples.office-hours.warm-intro-scoring.ingest \
  ~/Downloads/Connections.csv \
  --db /tmp/warm-intros.db

# 2. Enrich a reviewed, bounded set of contacts.
APIFY_TOKEN=... python -m examples.office-hours.warm-intro-scoring.enrich \
  --db /tmp/warm-intros.db \
  --limit 100 \
  --batch-size 25

# 3. Inspect human-readable company-proximity results.
python -m examples.office-hours.warm-intro-scoring.lookup \
  --db /tmp/warm-intros.db \
  --company "Northstar AI" \
  --role "Head of GTM Engineering" \
  --limit 20

# 4. Export deterministic ask-thread input. --target-title is preserved in CSV.
python -m examples.office-hours.warm-intro-scoring.lookup \
  --db /tmp/warm-intros.db \
  --company "Northstar AI" \
  --target-name "Nora Imani" \
  --target-title "Head of GTM Engineering" \
  --csv /tmp/scored_connectors.csv \
  --quiet
```

`--csv` is implemented. Without `--quiet`, CSV export supplements the normal
database summary and formatted results. With `--quiet`, it writes the same CSV
bytes without terminal output. Rows sort by descending `total_score`, normalized
connector name, and contact ID. If a match has no `path_id`, export derives one
from connector ID plus target name/title/company.

The CSV schema is:

| Column | Semantics |
|---|---|
| `path_id` | Stable path identifier used by downstream send idempotency. |
| `connector_name` | Connector display name. |
| `connector_linkedin` | Connector profile URL. |
| `connector_company` | Connector current company, if known. |
| `target_name` | Target name supplied by CLI or scorer result. |
| `target_title` | Target title supplied by `--target-title` or scorer result. |
| `target_company` | Target company supplied by CLI or scorer result. |
| `shared_signal` | Highest-priority signal label, such as `direct_introduction`, `verified_work_overlap`, or `company_proximity`. |
| `shared_detail` | Evidence-safe description; proximity text explicitly says dates were not compared or did not overlap. |
| `relationship_confidence` | Owner-to-connector confidence label. |
| `direct_intro_score` | Explicit component. |
| `work_overlap_score` | Explicit component. |
| `relationship_score` | Explicit component. |
| `school_city_community_score` | Explicit component. |
| `role_industry_score` | Explicit component. |
| `investor_score` | Explicit component. |
| `total_score` | Component sum for target-person results; legacy discovery score otherwise. |
| `segment` | `strong_warm_intro`, `review_warm_intro`, or `no_strong_path`. |
| `evidence_ids` | Sorted, semicolon-delimited citations. |

Pass this file directly to the ask drafter; do not rename columns or manually
retype rows:

```bash
python examples/office-hours/warm-intro-ask-threads/draft_asks.py \
  --input /tmp/scored_connectors.csv \
  --output /tmp/ask_drafts.csv \
  --top 20
```

Draft generation calls a model, records failed rows with empty bodies, and sets
`approved=false`. Review evidence and copy before changing selected rows to
`approved=true`. The sender rejects unapproved live rows and deduplicates successful
sends by `path_id`, channel, and `message_version`.

## Files

- `models.py`: contact, employment, education, affiliation, appearance, and match
  records.
- `db.py`: SQLite schema and query helpers.
- `ingest.py`: LinkedIn Connections CSV ingestion.
- `enrich.py`: live profile enrichment and experience/education replacement.
- `scorer.py`: discovery and target-person score implementations.
- `lookup.py`: query, terminal display, and deterministic `--csv` export.
- `blog_post.md`: anonymized methodological write-up.

## Known limitations

- Discovery mode compares a connector with criteria, not with a target person's
  dated history. Treat its employer result as proximity.
- Name, company, role keywords, recency, and public appearances are imperfect
  proxies for an actual relationship.
- Ingestion creates new UUIDs and does not provide production-grade contact
  resolution. Use the orchestrator's strong-ID/weak-review model before combining
  sources.
- Profile enrichment is not cached by content hash, has no spend ledger, and
  retries by polling rather than by a durable request state machine.
- The appearance discoverer is a no-network stub in this standalone example unless
  an implementation is supplied.
- The scorer ranks evidence. It does not determine consent, channel eligibility,
  suppression status, or whether an ask should be sent.
