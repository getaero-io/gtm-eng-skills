# Target Account Warm Intro Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a runnable, anonymized office-hours example that converts target-account candidates into ranked accounts, deduplicated buying committees, person-centric org context, evidence-backed warm paths, reviewed intro asks, and an auditable campaign ledger.

**Architecture:** A standard-library Python orchestrator reads fictional CSV fixtures and one JSON configuration, normalizes them into typed records, and writes deterministic review artifacts. Existing warm-intro scoring and ask-thread examples gain compatible CSV contracts, dated employment-overlap scoring, visible score components, approval gates, and idempotent send keys.

**Tech Stack:** Python 3.10+ standard library (`argparse`, `csv`, `dataclasses`, `datetime`, `hashlib`, `json`, `sqlite3`, `unittest`), Markdown, JSON, CSV.

## Global Constraints

- All public people, companies, URLs, interaction history, and campaign details are fictional or anonymized.
- The example must run locally without paid calls; provider adapters are documented interfaces, not live fixture dependencies.
- Sentrion is the preferred job-data source.
- Apify is the preferred LinkedIn profile, company-post, and person-post source.
- TwitterAPI is the preferred X source; Reddit is used only when identity and relevance are supported.
- Bloomberry and CrustData LinkedIn-post data are excluded.
- PDL people search is gap-fill only and must exclude known LinkedIn URLs, emails, and normalized identities.
- Direct introduction evidence outranks dated work overlap; dated work overlap outranks school, city, community, social, and investor overlap.
- Investor overlap is capped at the lowest priority and cannot independently create a strong path.
- Open roles are never treated as incumbents; inferred org edges are never represented as confirmed.
- Missing or conflicting identifiers route to review instead of speculative merging.
- Paid calls require a cache miss and remaining budget.
- Outreach defaults to dry-run and requires `approved=true` before any live send.
- Re-running the workflow must not duplicate contacts, paths, artifacts, or send records.

---

### Task 1: Canonical records and identity resolution

**Files:**
- Create: `examples/office-hours/target-account-warm-intro-campaign/schemas.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/tests/test_schemas.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/__init__.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/tests/__init__.py`

**Interfaces:**
- Produces: `normalize_domain(value: str) -> str`
- Produces: `normalize_linkedin_url(value: str) -> str`
- Produces: `normalize_email(value: str) -> str`
- Produces: `normalized_identity(name: str, company: str, title: str) -> str`
- Produces: `canonical_contact_key(contact: ContactRecord) -> tuple[str, str]`
- Produces dataclasses: `AccountRecord`, `ContactRecord`, `ExperienceRecord`, `InteractionRecord`, `OrgEdgeRecord`, `EvidenceRecord`, `ConnectorEdge`, `PathScore`, `CampaignConfig`
- Produces: `load_csv_records(path: Path, record_type: type[T]) -> list[T]`
- Produces: `write_csv_records(path: Path, rows: Iterable[Mapping[str, object]], fieldnames: Sequence[str]) -> None`

- [ ] **Step 1: Write failing identity-resolution tests**

```python
def test_contact_key_prefers_linkedin_then_email_then_fallback():
    linkedin = ContactRecord(contact_id="a", name="Alex Chen", company="Northstar AI", title="GTM Engineer", linkedin_url="https://www.linkedin.com/in/example-alex-chen/")
    email = ContactRecord(contact_id="b", name="Alex Chen", company="Northstar AI", title="GTM Engineer", work_email="ALEX@NORTHSTAR.EXAMPLE")
    fallback = ContactRecord(contact_id="c", name="Alex Chen", company="Northstar AI", title="GTM Engineer")
    assert canonical_contact_key(linkedin) == ("linkedin", "linkedin.com/in/example-alex-chen")
    assert canonical_contact_key(email) == ("email", "alex@northstar.example")
    assert canonical_contact_key(fallback)[0] == "identity"


def test_domain_normalization_rejects_non_domain_noise():
    assert normalize_domain("https://www.northstar.example/careers") == "northstar.example"
    with self.assertRaises(ValueError):
        normalize_domain("Northstar AI")
```

- [ ] **Step 2: Run the tests and verify the red state**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/target-account-warm-intro-campaign/tests -p 'test_schemas.py' -v
```

Expected: FAIL because `schemas.py` and its interfaces do not exist.

- [ ] **Step 3: Implement immutable dataclasses and normalization**

Use frozen dataclasses. Preserve raw IDs and source references. `canonical_contact_key` must select exactly one primary key using this order:

```python
if contact.linkedin_url:
    return "linkedin", normalize_linkedin_url(contact.linkedin_url)
if contact.work_email:
    return "email", normalize_email(contact.work_email)
return "identity", normalized_identity(contact.name, contact.company, contact.title)
```

`PathScore` exposes individual integer components and calculates `total_score` as a property. It must not accept a pre-computed total.

Use these exact score fields:

```python
@dataclass(frozen=True)
class PathScore:
    path_id: str
    connector_id: str
    target_id: str
    target_name: str
    target_title: str
    target_company: str
    direct_intro_score: int = 0
    work_overlap_score: int = 0
    relationship_score: int = 0
    school_city_community_score: int = 0
    role_industry_score: int = 0
    investor_score: int = 0
    relationship_confidence: str = "unknown"
    reasons: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    campaign_id: str = ""
    owner_id: str = ""

    @property
    def total_score(self) -> int:
        return sum((self.direct_intro_score, self.work_overlap_score,
                    self.relationship_score, self.school_city_community_score,
                    self.role_industry_score, self.investor_score))
```

`CampaignConfig` contains the campaign ID, owner ID, as-of date, title catalog, score weights, segment thresholds, exclusions, provider routes, blocked operations, cache directory, provider caps, and campaign cap. Parse money as `Decimal`, never binary float.

- [ ] **Step 4: Add CSV round-trip and unknown-column tests**

Assert stable column order, UTF-8 output, `\n` line endings, and a clear `ValueError` for missing required columns. Extra source columns must be retained in a `source_metadata_json` field rather than discarded.

- [ ] **Step 5: Run the focused tests**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/office-hours/target-account-warm-intro-campaign
git commit -m "feat(examples): add warm intro campaign schemas"
```

### Task 2: Account boundary, transparent ranking, and provider ledger

**Files:**
- Create: `examples/office-hours/target-account-warm-intro-campaign/score_accounts.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/provider_policy.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/tests/test_score_accounts.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/tests/test_provider_policy.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/config.example.json`

**Interfaces:**
- Consumes: `AccountRecord`, `CampaignConfig`
- Produces: `AccountScore(account_id, icp_fit, engineering_led, technical_gtm_signal, growth_recency, customer_similarity, first_party_engagement, total_score, decision, exclusion_reason)`
- Produces: `score_account(account: AccountRecord, config: CampaignConfig) -> AccountScore`
- Produces: `rank_accounts(accounts: Sequence[AccountRecord], config: CampaignConfig) -> list[AccountScore]`
- Produces: `ProviderPolicy.from_config(config: Mapping[str, object]) -> ProviderPolicy`
- Produces: `ProviderPolicy.authorize(provider: str, operation: str, cache_key: str, estimated_cost_usd: Decimal) -> AuthorizationDecision`
- Produces: `build_pdl_exclusions(contacts: Sequence[ContactRecord]) -> PdlExclusionSet`

- [ ] **Step 1: Write failing account-ranking tests**

Create fixtures for:

- a high-growth engineering-led B2B account hiring a GTM Engineer;
- an existing customer with otherwise high fit;
- a consumer account with no technical GTM signal.

Assert that every account remains in output, the customer has `decision=exclude` with `exclusion_reason=existing_customer`, and score components sum to the reported total.

- [ ] **Step 2: Write failing provider-policy tests**

```python
def test_provider_routes_are_explicit():
    policy = ProviderPolicy.from_path(CONFIG)
    assert policy.provider_for("company_jobs") == "sentrion"
    assert policy.provider_for("linkedin_person_posts") == "apify"
    assert policy.provider_for("x_posts") == "twitterapi"
    assert "bloomberry" in policy.blocked_providers
    assert policy.is_blocked("crustdata", "linkedin_person_posts")


def test_paid_call_requires_budget_and_cache_miss():
    decision = policy.authorize("pdl", "people_search", "account:northstar", Decimal("0.40"))
    assert decision.allowed
    policy.record_call(decision, actual_cost_usd=Decimal("0.40"))
    assert not policy.authorize("pdl", "people_search", "account:northstar", Decimal("0.40")).allowed
```

- [ ] **Step 3: Run focused tests and verify failure**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/target-account-warm-intro-campaign/tests -p 'test_score_accounts.py' -v
python3 -m unittest discover -s examples/office-hours/target-account-warm-intro-campaign/tests -p 'test_provider_policy.py' -v
```

Expected: FAIL because account ranking and provider policy are undefined.

- [ ] **Step 4: Implement account ranking**

Use integer component ranges defined in `config.example.json`. Exclusions run before prioritization but retain the computed score for audit. Sort by `decision` (`include`, `review`, `exclude`), descending total, then normalized domain.

- [ ] **Step 5: Implement provider policy and PDL exclusions**

`PdlExclusionSet` contains sorted unique LinkedIn URLs, emails, and normalized identity strings. `authorize` returns a reason code: `allowed`, `blocked_provider`, `blocked_operation`, `cache_hit`, `provider_cap`, or `campaign_cap`.

- [ ] **Step 6: Run focused tests and verify success**

Run both Step 3 commands. Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add examples/office-hours/target-account-warm-intro-campaign
git commit -m "feat(examples): rank accounts and enforce provider policy"
```

### Task 3: Contact resolution, buying committees, org semantics, and interaction audit

**Files:**
- Create: `examples/office-hours/target-account-warm-intro-campaign/build_campaign.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/tests/test_build_campaign.py`

**Interfaces:**
- Consumes: account, contact, experience, org-edge, interaction, and evidence records
- Produces: `dedupe_contacts(contacts: Sequence[ContactRecord]) -> DedupeResult`
- Produces: `qualify_contact(contact: ContactRecord, config: CampaignConfig) -> QualificationResult`
- Produces: `build_buying_committee(account_id: str, contacts: Sequence[ContactRecord], config: CampaignConfig) -> list[CommitteeMember]`
- Produces: `validate_org_edges(edges: Sequence[OrgEdgeRecord], contacts: Sequence[ContactRecord]) -> list[OrgEdgeRecord]`
- Produces: `person_centric_neighborhood(target_id: str, edges: Sequence[OrgEdgeRecord], max_depth: int = 3) -> list[OrgEdgeRecord]`
- Produces: `summarize_interactions(target_id: str, interactions: Sequence[InteractionRecord]) -> InteractionSummary`

- [ ] **Step 1: Write failing dedupe and title-qualification tests**

Assert that:

- URL variants of one LinkedIn profile merge;
- two records sharing a verified work email merge;
- a normalized name/company/title collision without strong ID routes to review instead of auto-merging;
- GTM Engineering, Revenue Systems, RevOps, BizOps, Growth Engineering, GTM Analytics, and Marketing Operations qualify with an explicit role family;
- unrelated sales and recruiting titles do not qualify.

- [ ] **Step 2: Write failing org and interaction tests**

Assert that an `open_role` node cannot be the person side of a `reports_to_confirmed` edge, inferred edges remain `functional_proximity_inferred`, traversal stops at three levels, and prior intro/email/call evidence is summarized with timestamp and evidence ID.

- [ ] **Step 3: Run the focused test and verify failure**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/target-account-warm-intro-campaign/tests -p 'test_build_campaign.py' -v
```

- [ ] **Step 4: Implement dedupe and committee construction**

Return merge groups, canonical records, and review collisions. Keep all contributing source IDs on the canonical record. Buying-committee output sorts technical champions before operational buyers, economic buyers, and adjacent validators within the same account priority.

- [ ] **Step 5: Implement org validation and three-level traversal**

Reject invalid edge shapes with a message containing the edge ID. Traversal must track visited nodes, prevent cycles, retain direction, and preserve confidence and source evidence.

- [ ] **Step 6: Implement interaction normalization**

Use a fixed source enum: `crm`, `email`, `event`, `website_form`, `sales_call`, `manual_confirmation`. Direct introduction requires either `interaction_type=introduction` or `manual_confirmation` with an immutable evidence ID.

- [ ] **Step 7: Run the focused tests and verify success**

Run the Step 3 command. Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add examples/office-hours/target-account-warm-intro-campaign
git commit -m "feat(examples): build deduped buying committees"
```

### Task 4: Evidence-backed warm-path scoring

**Files:**
- Create: `examples/office-hours/target-account-warm-intro-campaign/score_paths.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/tests/test_score_paths.py`
- Modify: `examples/office-hours/warm-intro-scoring/models.py`
- Modify: `examples/office-hours/warm-intro-scoring/scorer.py`
- Modify: `examples/office-hours/warm-intro-scoring/lookup.py`

**Interfaces:**
- Produces: `employment_overlap(left: ExperienceRecord, right: ExperienceRecord, as_of: date) -> EmploymentOverlap | None`
- Produces: `score_warm_path(connector: ContactRecord, target: ContactRecord, evidence: PathEvidence, config: CampaignConfig) -> PathScore`
- Produces: `segment_path(score: PathScore, config: CampaignConfig) -> Literal['strong_warm_intro', 'review_warm_intro', 'no_strong_path']`
- Existing example produces: `WarmIntroLookup.export_csv(matches: Sequence[WarmIntroMatch], output: TextIO, target_name: str, target_title: str, target_company: str, campaign_id: str, owner_id: str, target_id: str) -> None`
- Existing CLI adds: `--csv PATH`, `--target-name`, `--target-title`, `--campaign-id`, `--owner-id`, and `--target-id`

- [ ] **Step 1: Write failing date-overlap tests**

Cover overlapping bounded ranges, non-overlapping ranges at the same employer, a current role with no end date, and missing dates. Missing dates may produce a review signal but never the strong work-overlap component.

- [ ] **Step 2: Write failing score-order tests**

Use separate fixtures to prove:

```python
assert direct_intro.total_score > dated_work_overlap.total_score
assert dated_work_overlap.total_score > school_city_social.total_score
assert investor_only.investor_overlap <= 3
assert segment_path(investor_only, config) == "no_strong_path"
```

Also assert that the score includes reasons, evidence IDs, target name, and target title.

- [ ] **Step 3: Write failing existing-lookup CSV tests**

Load `lookup.py` by file path and assert the CSV header includes:

```text
campaign_id,owner_id,connector_id,target_id,path_id,connector_name,connector_linkedin,connector_company,target_name,target_title,target_company,shared_signal,shared_detail,relationship_confidence,direct_intro_score,work_overlap_score,relationship_score,school_city_community_score,role_industry_score,investor_score,total_score,segment,reviewed_override,evidence_ids
```

`path_id` is built only by the shared versioned function over campaign, owner,
connector, and target IDs. Missing namespaces block CSV export and downstream
drafting; no display-name fallback is permitted. The drafter and sender each
recompute the ID and reject a mismatch before a model or provider call.

- [ ] **Step 4: Run focused tests and verify failure**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/target-account-warm-intro-campaign/tests -p 'test_score_paths.py' -v
```

- [ ] **Step 5: Implement campaign path scoring**

Strong-path eligibility requires at least one of:

- confirmed direct introduction plus non-zero owner-to-connector relationship confidence;
- dated work overlap plus non-zero owner-to-connector relationship confidence.

School, city, community, appearance, role, industry, and investor components can improve ranking but cannot satisfy eligibility.

- [ ] **Step 6: Update the existing scorer without breaking its current API**

Add component fields to `WarmIntroMatch` with defaults. Add a target-to-connector scoring entry point while preserving `score_contact` for the original single-company lookup. Ensure current-company name matches without target-person evidence are labeled `company_proximity`, not `verified_work_overlap`.

- [ ] **Step 7: Implement deterministic CSV export**

Use `csv.DictWriter`, stable headers, `\n` line endings, and stable sort by descending total score then normalized connector name. `--csv` writes the file while retaining human-readable terminal output unless `--quiet` is supplied.

- [ ] **Step 8: Run focused and legacy compilation checks**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/target-account-warm-intro-campaign/tests -p 'test_score_paths.py' -v
python3 -m py_compile examples/office-hours/warm-intro-scoring/models.py examples/office-hours/warm-intro-scoring/scorer.py examples/office-hours/warm-intro-scoring/lookup.py
```

- [ ] **Step 9: Commit**

```bash
git add examples/office-hours/target-account-warm-intro-campaign examples/office-hours/warm-intro-scoring
git commit -m "feat(examples): score evidence-backed warm intro paths"
```

### Task 5: Anonymized fixture campaign and deterministic outputs

**Files:**
- Create: `examples/office-hours/target-account-warm-intro-campaign/pipeline.py`
- Create: `examples/office-hours/target-account-warm-intro-campaign/sample_data/accounts.csv`
- Create: `examples/office-hours/target-account-warm-intro-campaign/sample_data/contacts.csv`
- Create: `examples/office-hours/target-account-warm-intro-campaign/sample_data/experiences.csv`
- Create: `examples/office-hours/target-account-warm-intro-campaign/sample_data/interactions.csv`
- Create: `examples/office-hours/target-account-warm-intro-campaign/sample_data/org_edges.csv`
- Create: `examples/office-hours/target-account-warm-intro-campaign/sample_data/evidence.csv`
- Create: `examples/office-hours/target-account-warm-intro-campaign/sample_data/connector_edges.csv`
- Create: `examples/office-hours/target-account-warm-intro-campaign/expected_output/*.csv`
- Create: `examples/office-hours/target-account-warm-intro-campaign/tests/test_pipeline.py`

**Interfaces:**
- Produces: `run_pipeline(input_dir: Path, output_dir: Path, config_path: Path, as_of: date) -> CampaignLedger`
- CLI: `python3 pipeline.py --input-dir sample_data --output-dir output --config config.example.json --as-of 2026-08-01`
- Outputs: `ranked_accounts.csv`, `contact_dedupe_audit.csv`, `pdl_gapfill_requests.json`, `buying_committee.csv`, `org_edges_review.csv`, `interaction_audit.csv`, `warm_paths.csv`, `direct_outreach.csv`, `campaign_ledger.json`

- [ ] **Step 1: Create fictional fixture data**

Use companies such as `Northstar AI`, `Relay Cloud`, `Harbor Systems`, and `Juniper Consumer`. Use `.example` domains and LinkedIn URLs under `linkedin.com/in/example-*`. Include:

- one excluded existing customer;
- one high-fit account with a confirmed introduction;
- one dated work overlap;
- one same-employer but non-overlapping tenure;
- one investor-only connector;
- one open role and one inferred org edge;
- one duplicate by LinkedIn URL and one duplicate by email;
- cited fictional job, post, talk, and interaction evidence.

- [ ] **Step 2: Write the failing end-to-end test**

Run the pipeline twice into two temporary directories. Assert byte-identical review artifacts, 100% account decisions, non-empty dedupe/alias audit, full-alias PDL exclusions, safe foreign-key remapping, validated evidence ownership/type/subject/participants, all three path segments represented, investor-only path excluded from strong paths, exact evidence-freshness/segment/approval/activation ledger fields, and no real email domains.

- [ ] **Step 3: Run the end-to-end test and verify failure**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/target-account-warm-intro-campaign/tests -p 'test_pipeline.py' -v
```

- [ ] **Step 4: Implement the pipeline**

Stages execute in a fixed order and write a ledger record containing stage, input count, output count, exclusions, review count, cache hits, authorized provider calls, estimated spend, and SHA-256 artifact hashes. The root also records deterministic evidence-age buckets, exact strong/review/no-path counts, and approved/activated message counts. The fixture run records zero live provider calls, zero spend, zero approvals, and zero activations.

- [ ] **Step 5: Generate committed expected output**

Run the CLI with `--as-of 2026-08-01`. Copy only normalized review artifacts into `expected_output`; do not commit caches, credentials, local SQLite files, or transient logs.

- [ ] **Step 6: Run end-to-end and deterministic-hash checks**

Run the Step 3 command and compare a second fixture output with `diff -ru`. Expected: PASS and no differences.

- [ ] **Step 7: Commit**

```bash
git add examples/office-hours/target-account-warm-intro-campaign
git commit -m "feat(examples): add anonymized warm intro fixture campaign"
```

### Task 6: Compatible ask drafts and approval-gated activation

**Files:**
- Modify: `examples/office-hours/warm-intro-ask-threads/draft_asks.py`
- Modify: `examples/office-hours/warm-intro-ask-threads/send_via_linkedin.py`
- Create: `examples/office-hours/warm-intro-ask-threads/test_draft_asks.py`
- Create: `examples/office-hours/warm-intro-ask-threads/test_send_via_linkedin.py`
- Create: `examples/office-hours/warm-intro-ask-threads/sample_scored_connectors.csv`
- Create: `examples/office-hours/warm-intro-ask-threads/sample_ask_drafts.csv`

**Interfaces:**
- `load_scored_csv(path: str) -> list[dict]` consumes Task 4 CSV directly
- `build_signal_description(row: dict) -> str` supports `direct_introduction`, `dated_work_overlap`, `school_city_community`, `role_industry`, and `investor_overlap`
- Draft output preserves `campaign_id`, `owner_id`, `connector_id`, `target_id`, `path_id`, `segment`, `reviewed_override`, `target_title`, `target_company`, `why_target_cares`, `permissionless_value`, `approved`, `message_version`
- `load_drafts_csv(path: str, require_approved: bool = True) -> list[dict]`
- Send idempotency key: versioned SHA-256 JSON hash of `campaign_id`, `owner_id`, `path_id`, `channel`, and `message_version`
- Any non-preview history without a complete namespaced intent fingerprint blocks
  activation until every historical row receives explicit migration/reconciliation;
  both path and send-key algorithms changed

- [ ] **Step 1: Write failing CSV-compatibility and signal tests**

Assert Task 4 output loads without renaming columns and missing or mismatched
namespace/path values fail closed. Confirm dated work overlap renders employer
and overlap dates, direct introduction names the confirmed evidence type, and
investor-only context is not selected when a stronger supported reason exists.
Default drafting admits only `strong_warm_intro`; review paths require both an
explicit command flag and per-row review provenance; no-path rows route to direct
outreach without a model call.

- [ ] **Step 2: Write failing approval and idempotency tests**

Assert unapproved rows are rejected from the sendable set even in non-dry-run mode, an approved row is accepted, blank campaign/owner identity fails closed, forged path IDs fail closed, and a second attempt with the same idempotency key is skipped regardless of connector URL formatting. Add response-loss, malformed/missing provider response, stale post-dispatch recovery, proven pre-dispatch retry, immutable attempt/event audit, legacy-key migration barrier, and process-control exception tests.

- [ ] **Step 3: Run ask-thread tests and verify failure**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/warm-intro-ask-threads -p 'test_*.py' -v
```

- [ ] **Step 4: Update drafting inputs and outputs**

The prompt uses target title, verified path reason, `why_target_cares`, and `permissionless_value`. It must not invent personal facts or claim two people know each other when evidence only shows proximity. Draft output defaults `approved=false`.

- [ ] **Step 5: Enforce approval and idempotency in sender**

Use `sends` as a durable mutable outbox projection with a unique idempotency key
and immutable intent hash. Commit one immutable `send_attempts` row and
`dispatch_started` event before every external call; append provider results to
immutable `send_events`. Only proven process-creation failure returns to `ready`.
Every post-dispatch ambiguity becomes `needs_reconciliation`, consumes capacity,
and blocks automatic retry. Migration uses `PRAGMA table_info` and `ALTER TABLE`;
historical `pending`/`error` rows fail closed into reconciliation. Dry runs remain
separate and do not prevent a later approved live send. The provider has no
documented atomic idempotency token.

- [ ] **Step 6: Replace examples with anonymized fixtures**

Use only `.example` domains, fictional names, and the sample campaign's target titles. Include no real LinkedIn profile path.

- [ ] **Step 7: Run tests and compilation checks**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/warm-intro-ask-threads -p 'test_*.py' -v
python3 -m py_compile examples/office-hours/warm-intro-ask-threads/draft_asks.py examples/office-hours/warm-intro-ask-threads/send_via_linkedin.py
```

- [ ] **Step 8: Commit**

```bash
git add examples/office-hours/warm-intro-ask-threads
git commit -m "feat(examples): gate warm intro outreach on approval"
```

### Task 7: Detailed technical documentation and acceptance audit

**Files:**
- Create: `examples/office-hours/target-account-warm-intro-campaign/README.md`
- Modify: `examples/office-hours/warm-intro-scoring/README.md`
- Modify: `examples/office-hours/warm-intro-scoring/blog_post.md`
- Modify: `examples/office-hours/warm-intro-ask-threads/README.md`
- Create: `examples/office-hours/README.md`

**Interfaces:**
- Documents the exact input/output schemas, stage invariants, provider matrix, score formula, CLI commands, review gates, failure modes, cost ledger, resumability behavior, and relationship between the three examples.

- [ ] **Step 1: Write the orchestrator README in technical English**

Include:

- system boundary and threat model;
- workflow diagram in text or Mermaid;
- required and optional columns for every input;
- stable identifiers and merge precedence;
- account and path score formulas;
- exact provider routing and blocked-provider rules;
- PDL exclusion request example;
- confirmed versus inferred org-edge semantics;
- all generated artifact schemas;
- fixture quickstart and production-adaptation steps;
- retry, cache, budget, and idempotency behavior;
- review and activation checklist;
- privacy and anonymization rules.

- [ ] **Step 2: Correct existing READMEs**

Remove the false claim that `lookup.py --csv` is unimplemented. Document dated overlap versus company proximity, target-title output, score components, approval requirements, and direct use of the scorer CSV by `draft_asks.py`.

- [ ] **Step 3: Anonymize the blog post and examples**

Replace private or identifiable target/connector details with fictional names and generalized counts while preserving the methodological lesson. Remove unsupported conversion-rate claims unless they are explicitly labeled illustrative and uncited.

- [ ] **Step 4: Add an office-hours index**

Link the orchestrator, scorer, and ask-thread examples in execution order and state what each owns.

- [ ] **Step 5: Run the complete acceptance suite**

Run:

```bash
python3 -m unittest discover -s examples/office-hours/target-account-warm-intro-campaign/tests -p 'test_*.py' -v
python3 -m unittest discover -s examples/office-hours/warm-intro-ask-threads -p 'test_*.py' -v
python3 -m py_compile examples/office-hours/warm-intro-scoring/*.py examples/office-hours/warm-intro-ask-threads/*.py examples/office-hours/target-account-warm-intro-campaign/*.py
git diff --check
rg -n -i 'bloomberry|crustdata.*linkedin' examples/office-hours
rg -n -i '@(gmail|yahoo|outlook|deepline|getaero)\.' examples/office-hours/target-account-warm-intro-campaign examples/office-hours/warm-intro-ask-threads
rg -n -i 'linkedin\.(com|example)/in/' examples/office-hours/target-account-warm-intro-campaign examples/office-hours/warm-intro-scoring examples/office-hours/warm-intro-ask-threads docs/superpowers/plans/2026-08-12-target-account-warm-intro-campaign.md docs/superpowers/specs/2026-08-12-target-account-warm-intro-campaign-design.md | rg -v 'linkedin\.(com|example)/in/(example-|[<{])'
```

Expected: tests PASS; compilation PASS; whitespace check PASS; provider mentions occur only in explicit blocked-provider documentation/tests; identity scan returns no private identities.

- [ ] **Step 6: Run a fresh fixture smoke test**

Run:

```bash
python3 examples/office-hours/target-account-warm-intro-campaign/pipeline.py \
  --input-dir examples/office-hours/target-account-warm-intro-campaign/sample_data \
  --output-dir /tmp/target-account-warm-intro-example \
  --config examples/office-hours/target-account-warm-intro-campaign/config.example.json \
  --as-of 2026-08-01
```

Verify the command reports zero live paid calls, zero spend, all accounts decided, and all expected review artifacts written.

- [ ] **Step 7: Commit and push**

```bash
git add examples/office-hours docs/superpowers
git commit -m "docs(examples): document target account warm intro workflow"
git pull --rebase
git push
git status --short --branch
```

Expected: branch is clean and up to date with `origin/codex/warm-intro-campaign`.
