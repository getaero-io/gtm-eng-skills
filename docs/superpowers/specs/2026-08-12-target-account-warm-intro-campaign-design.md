# Target Account Warm Intro Campaign — Design

**Date:** 2026-08-12
**Status:** Approved for implementation
**Scope:** `examples/office-hours/`

## Objective

Turn the existing warm-intro scoring and ask-thread examples into a reusable, end-to-end office-hours workflow for building a target-account list, mapping each buying committee, finding the strongest warm entry path, and preparing reviewed outreach.

The example will mirror the real campaign process while replacing company names, people, URLs, and private interaction details with realistic fictional data. It must be useful without exposing customer, prospect, investor, or connector identities.

## Design choice

Add a new `target-account-warm-intro-campaign/` example as the orchestration layer. Keep `warm-intro-scoring/` focused on connector ranking and `warm-intro-ask-threads/` focused on drafting and controlled activation.

This avoids turning either focused example into a monolith. The orchestrator will define shared schemas, stage gates, provider routing, sample data, expected outputs, and the complete runbook. Existing scripts will be corrected where their current interface prevents the full workflow.

## Workflow

### 1. Establish the campaign boundary

Inputs:

- named workspace or campaign owner;
- target-account candidates;
- ICP rules;
- existing customers, vendors, partners, and do-not-contact exclusions;
- per-provider and total cost caps.

Completion criterion: every candidate account has a stable domain, an inclusion or exclusion decision, and the evidence behind that decision.

### 2. Prioritize target accounts

Rank accounts on:

- B2B and engineering-led product fit;
- technical GTM, RevOps, GTM Systems, Growth Engineering, BizOps, and GTM Analytics hiring;
- growth and recency signals;
- similarity to successful customers;
- evidence that the company is building data, automation, AI-agent, or AI-native GTM workflows;
- first-party engagement.

Outputs preserve score components instead of exposing only a blended score. Existing customers and non-prospects remain in the audit file with exclusion reasons; they are never silently dropped.

### 3. Define qualified titles and build the buying committee

Use a versioned title catalog with role family, seniority, buying role, and qualification reason. Discover contacts through the primary contact route, then hydrate known people through a waterfall.

People Data Labs people search is gap-fill only. Before each PDL query, exclude every known LinkedIn URL, work email, and normalized identity tuple. The gap-fill must report the exclusions it sent and reject duplicate results after return.

### 4. Hydrate and validate contacts

Hydrate current role, full work history, education, location, role tenure, profile URL, and public-source evidence. Resolve each person to one canonical record.

Provider guidance:

- Sentrion for current and historical job evidence;
- Apify for LinkedIn profiles, company posts, and person posts;
- TwitterAPI for X posts;
- Reddit sources where identity and relevance can be supported;
- public web, podcasts, talks, blogs, and GitHub for research context;
- no Bloomberry;
- no CrustData LinkedIn-post data.

Every record carries source, retrieval time, confidence, and cache key. Unsupported Reddit or social-account identity is marked as unverified and cannot drive outreach.

### 5. Build person-centric org charts

For each target contact, map up to three levels upward and downward and identify adjacent GTM functions. Separate:

- confirmed reporting relationships;
- inferred functional proximity;
- open roles;
- unknown relationships.

An open role is never represented as an incumbent. Inferred reporting lines are never presented as confirmed.

### 6. Audit first-party interaction history

Check CRM, email, event attendance, website forms, sales calls, and other available first-party systems. Normalize interactions into a common event schema with timestamp, source system, direction, participants, and evidence ID.

Confirmed prior introductions and direct conversations outrank inferred social similarity.

### 7. Build and score warm paths

Construct candidate connector-to-target paths from the owner's contact graph. A path score exposes these components in priority order:

1. confirmed introduction or direct relationship evidence;
2. verified overlapping employer dates, with functional proximity;
3. relationship strength and recency between owner and connector;
4. shared school, city, community, event, or public appearance;
5. role and industry proximity;
6. investor overlap, capped as the lowest-priority signal.

Same-company history only counts as strong overlap when the employment dates overlap. Name-only matches, non-overlapping tenures, and unverified current employers must be downgraded or rejected.

Results split into:

- `strong_warm_intro`: enough factual and relationship evidence for a direct ask;
- `review_warm_intro`: plausible path requiring human confirmation;
- `no_strong_path`: continue with researched direct outreach.

### 8. Research the entry angle

For prioritized contacts, assemble cited context from jobs, company initiatives, professional posts, X, Reddit, podcasts, talks, blogs, and GitHub. Research must answer:

- what the person is likely responsible for;
- what the company is actively building;
- which handoff, data-quality, routing, research, or orchestration problem is visible;
- why the target would benefit from engaging;
- what permissionless artifact could demonstrate value before a meeting.

The artifact and outreach angle must be account-specific. Generic personalization and unsupported personal trivia are excluded.

### 9. Thread the account and draft the ask

Produce an account threading plan containing the technical champion, operational buyer, economic buyer, adjacent validators, sequence, and escalation condition.

Warm-intro asks remain short:

1. direct ask;
2. factual reason this connector is the right person;
3. one sentence explaining why the target may care.

The target's current title is always included in the review output. Drafting never activates outreach automatically.

### 10. Review, activate, and audit

All outbound begins in dry-run mode. Reviewers approve individual paths and
messages. The send outbox is a mutable current-state projection; its attempts and
events are immutable and append-only. Failed enrichment, ambiguous delivery, or
reconciliation does not erase the underlying candidate or attempt audit.

The final campaign ledger reports:

- accounts and contacts at every stage;
- exclusions and reasons;
- provider calls, cache hits, and estimated spend;
- evidence freshness in exact age/future/unknown buckets;
- exact strong, review, and no-strong-path counts, with direct outreach as a
  separate artifact;
- approved and activated message counts, where the fixture boundary is zero.

## Files

### New orchestrator example

`examples/office-hours/target-account-warm-intro-campaign/`

- `README.md` — full runbook, stage gates, provider decisions, and expected artifacts;
- `pipeline.py` — deterministic local orchestration over CSV inputs and cached research;
- `schemas.py` — canonical account, contact, evidence, interaction, org-edge, and warm-path schemas;
- `score_accounts.py` — transparent account-priority components;
- `build_campaign.py` — dedupe, segmentation, threading, and campaign-ledger generation;
- `config.example.json` — title catalog, weights, exclusions, providers, and cost caps;
- `sample_data/` — fictional target accounts, contacts, work history, interactions, org edges, research evidence, and contact graph;
- `expected_output/` — representative normalized CSV artifacts; the deterministic
  campaign ledger is asserted from fresh output rather than committed recursively;
- `tests/` — unit and end-to-end fixture tests.

### Existing scoring example fixes

- Add deterministic CSV export to `lookup.py`.
- Add target name and current title to result rows.
- Score date-overlapping work history and expose component scores.
- Distinguish factual path strength from owner-to-connector relationship confidence.
- Add community, location, event, and direct-introduction evidence fields.
- Cap investor overlap below every relationship and work-overlap signal.
- Make enrichment idempotent and cache-aware.
- Update README, anonymized examples, and tests.

### Existing ask-thread fixes

- Accept the scorer's real CSV output without manual transformation.
- Use the strongest supported path reason, including direct-introduction and dated work overlap.
- Carry target title and account-specific value context into review output.
- Require an explicit approval field before sending.
- Preserve dry-run, rate limits, idempotent send logging, and human review.
- Update README, anonymized examples, and tests.

## Data contracts

Stable identifiers:

- account: normalized domain;
- contact: normalized LinkedIn URL and verified work email are candidate strong
  identifiers; weak normalized name + company + title identity routes collisions
  to review and never merges automatically. Conflicting strong-ID components also
  remain separate. Safe merges retain all aliases and remap downstream foreign
  keys while keeping the chosen canonical primary fields;
- evidence: source type + source URL or immutable source ID + observed timestamp;
- path: versioned JSON hash of campaign + owner + connector + target IDs;
- outbound: versioned JSON hash of campaign + owner + path ID + channel + message
  version.

The drafter and sender independently recompute the path from its namespace and
endpoint columns before any model or provider call. A nonblank but forged path is
rejected. On sender upgrades, any non-preview row without a complete namespaced
intent fingerprint blocks all live activation until explicit reconciliation and
migration, because both the path and activation-key algorithms changed.

No stage may overwrite raw provider evidence. Normalized outputs point back to their source record.

## Error handling and safety

- Missing identifiers route to review instead of speculative merging.
- Only failures proven to occur before dispatch are automatically retryable.
  Response loss, malformed/missing provider results, non-success/unknown status,
  interruption, and stale post-dispatch recovery become
  `needs_reconciliation`. The provider exposes no atomic idempotency token.
- Paid calls require remaining budget and a cache miss.
- PDL people search requires a non-empty exclusion set for any account with known contacts.
- Unsupported personal-account matches cannot influence a message.
- Outreach requires `approved=true`; dry-run is the default.
- Re-running the workflow must not duplicate contacts, paths, or sends.

## Testing and acceptance

The fixture campaign will use fictional accounts and people but retain realistic titles, signals, and conflicts.

Acceptance requires:

- all sample accounts receive an inclusion or exclusion decision;
- safe identity dedupe retains every LinkedIn/email/weak alias, maps aliases to one
  canonical ID, refuses contextual conflicts, and remaps all dependent records;
- PDL gap-fill inputs exclude the full alias union of previously discovered contacts;
- only date-overlapping employment earns the strong work-overlap component;
- direct-introduction evidence ranks above work, school, city, social, and investor overlap;
- investor overlap cannot independently create a strong path;
- open roles and inferred org edges remain labeled;
- lookup CSV feeds ask drafting without manual column edits;
- the same path ID is built by the orchestrator/scorer/lookup, independently
  recomputed and validated by the drafter/sender, and embedded in the namespaced
  activation identity;
- invalid owner/evidence/type/subject/participant claims cannot make a strong path;
- review drafting requires explicit human provenance and no-path rows never create
  warm asks;
- unapproved messages cannot send;
- ambiguous post-dispatch attempts remain blocked with immutable attempt/event
  history; only proven pre-dispatch failure can create a later attempt;
- unmigrated live history blocks namespaced activation until every historical row
  receives explicit reconciliation/migration;
- a second run produces the same normalized artifacts and no duplicate sends;
- every public example is anonymized and contains no private identities or credentials.

## Out of scope

- Automatically purchasing gifts or Cameos;
- guessing private social accounts;
- bypassing platform terms or access controls;
- fully automated outbound without review;
- reproducing private customer or prospect datasets in the public repository.
