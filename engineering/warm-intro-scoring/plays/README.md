# Warm introduction Plays

These Plays move the existing workflow into Deepline. Python remains the independent reference for scoring and evaluation. The Plays preserve source dates, evidence IDs, conservative date overlap, adjustable weights, and human review gates.

Start with the offline check from the package root:

```sh
python3 plays/check_all.py
```

Requirements: Python 3.10+ and Bun. This command uses fictional fixtures. It does not load credentials, read customer data, call providers, or write to a database. A failure stops the command.

## Workflow

| Stage | Play | Result |
|---|---|---|
| Read existing customer data | `read-sources.play.ts` | Complete bounded source snapshots |
| Collect profiles and posts | `collect.play.ts` | Retained or live Apify receipts with observation dates |
| Discover podcasts, panels, and interviews | `research.play.ts` | Source candidates that require verification |
| Save evidence revisions | `snapshots.play.ts` | Additive records and read-back receipts |
| Build scoring features | `features.play.ts` | Evidence features, scores, coverage, and parity hashes |
| Apply or tune weights | `score.play.ts` | Full ranked scores and contribution breakdowns |
| Audit and evaluate | `validation.play.ts` | Data quality, legacy scoring, ranking diagnostics, and parity results |
| Create the review artifact | `report.play.ts` | Private tuning, legacy, or evaluation HTML |

Company enrichment also has a generic Play at `../assets/company-research.play.ts`. Source research and profile refreshes are separate from deterministic scoring. A refreshed profile can change the ranking; it cannot be expected to match a frozen source snapshot.

## Inputs

Every Play accepts `csv`, a CSV file path staged by the Deepline CLI. JSON fields in CSV cells must use valid CSV quoting. Keep real profiles, evidence, and generated exports outside this repository.

| Play | Additional input fields | Required CSV columns | Optional CSV columns |
|---|---|---|---|
| `read-sources` | `max_rows_per_source` (1–5,000; default 5,000) | `source_id,schema_name,table_name,key_column` | — |
| `collect` | `mode` (`cached` or `live`), `observed_at` (date), `max_posts` (1–100; default 50) | `contact_id,linkedin_url` | `profile_json,posts_json` |
| `research` | `mode` (`cached` or `live`) | `contact_id,name,company` | `cached_json` |
| `snapshots` | `execute` (boolean) | `record_id,kind,revision,observed_at,payload_json` | — |
| `features` | — | `section,key,payload_json` | — |
| `score` | — | `case_id,payload_json` | `weights_json,expected_json` |
| `validation` | — | `case_id,operation,payload_json,today` | `expected_json,expected_error,max_age_days` |
| `report` | — | `case_id,payload_json,artifact_path` | `weights_json,report_kind` |

Dates use `YYYY-MM-DD` unless the evaluator requires a full timestamp. Stable source and row IDs are required; names alone are not identity keys.

### Source collection and snapshots

`read-sources` paginates by a unique non-null key. It rejects repeated keys, truncated pages, and sources that exceed the configured bound. Partition a larger source instead of raising a silent row limit. A database read retains the original profile observation date. Key counts are checked before reading and reconciled afterward. This detects count changes, but it is not a transactionally consistent snapshot during concurrent updates; use a stable source view or frozen table.

`collect` in cached mode requires `profile_json`; optional `posts_json` is an array of retained posts. Live mode calls the full-profile and public-post Apify actors. It verifies the returned profile URL against the requested contact. An unfinished actor receipt is not a completed profile and fails the row for later recovery.

`research` in cached mode requires `cached_json`. Live mode searches for public history. Both modes return `needs_verification`. A matching event name, podcast series, or post tag does not automatically add relationship points.

`snapshots` with `execute:false` returns a write plan. With `execute:true`, it creates the additive `analytics.warm_intro_play_snapshots` table if needed, writes each revision, and verifies its content hash. Supported kinds are `contact`, `target`, `investor_edge`, `relationship`, `willingness`, `feedback`, and `tombstone`. Reusing a revision with changed data fails. It does not send asks or enable a schedule.

### Feature records

`features` accepts at most 5,000 source records per run. Each CSV row contains one JSON record. Use these sections:

- `config`: exactly one record containing `as_of`, `profiles_checked_at`, `requester_name`, and optional requester/exclusion metadata.
- `connectors` and `profiles`: profile snapshots, one per row.
- `targets`: target contact records, one per row.
- Optional `company_sizes`, `funding_edges`, `verified_firms`, and `owner_portfolio`: source-backed context records.

Package the source JSON without manual CSV editing:

```sh
python3 plays/prepare-inputs.py sources.json --out /private/path/features.csv
```

Use `--targets-per-file 25` to split targets while retaining their source context. Each resulting CSV must still fit the 5,000-record bound. The packager preserves unresolved targets, writes private files, and refuses to overwrite existing files.

The exact typed contract is `FeatureInput` in `features.ts`. Profile snapshots contain stable IDs, LinkedIn URLs, source locators, observation dates, work history, and education. Target records contain a name, canonical profile URL, company, and domain. Unresolved or ambiguous target matches stay in coverage; they are not joined by name.

A target row can wrap its record as `{target, expected_feature_sha256, expected_score_sha256}`. These hashes check features and resulting rankings against a frozen independent reference. They must be generated from that reference, not from the new Play under test.

### Scoring and reports

`score` uses the normalized input accepted by `scripts/tuning.py`. It also accepts the report's compact `feature_catalog` form. `weights_json` changes only named weights. `expected_json` checks ordered path IDs, score totals, contributions, and review status.

`report_kind` is `tuning` by default. Use `legacy` for rows from the reviewed-evidence scorer and `evaluation` for an evaluator report. Tuning preserves the existing interactive review UI, weight controls, source explanations, and feedback export.

Cloud reports are limited to **1 MB**. Split larger reports by account or render locally:

```sh
bun plays/report-cli.ts input.json output.html
```

The local renderer keeps all candidates, uses the same UI template, creates a private file, and refuses to overwrite it. Optional third argument: a weight configuration JSON file. Download feedback from the review UI before closing it.

### Validation

Supported `operation` values are `evaluate`, `quality`, `legacy`, `temporal`, and `portfolio`. See [evaluation-contract.md](evaluation-contract.md) for payload shapes and limits.

Each result has `pass`, `fail`, or `not_checked`. An expected rejection is a pass only when `expected_error=true` and the operation rejects the contract. Runtime failures do not satisfy the expected rejection. A completed run alone does not prove parity; export and inspect every result.

## Run a Play

Select the intended Deepline organization before running. Run the CLI preflight before concurrent work. For example:

```sh
deepline preflight --json
deepline plays check plays/score.play.ts
deepline plays run plays/score.play.ts --input '{"csv":"/private/path/score-batches.csv"}' --debug
```

For concurrent CLI work, prefix commands with `DEEPLINE_SKIP_SELF_UPDATE=1` after the preflight. Keep run IDs, debug receipts, exports, and source snapshots in a private handoff directory. Export before reusing dataset keys: a later replay can replace the mutable dataset association of an older run. Immutable source revisions remain in the analytics table. Export the completed run with `deepline runs export <run-id> --out <private-output.csv>`.

No Play here sends introductions, emails, or consent requests. Live collection and research can incur provider charges. Deterministic parity verification does not require fresh paid research.

## What parity covers

The migration was checked against the frozen full review: **311 target contacts and 91,428 paths**. The full cloud score run matched path identity, rank order, score totals, contribution values, and review status. Feature checks also compare dated overlap, evidence IDs, and work-context fields. These are snapshot comparisons, not proof that every source claim is true or that an introduction will succeed.

Cached profile/post collection, public-history candidate holds, database read-back, identical revision replay, and conflicting-revision rejection also passed. No production contact records were changed by those adapter fixtures.

The cloud validation matrix passed **50 cases**, including **16 expected rejection cases**. It covers the evaluator, reviewed legacy scorer, quality audit, temporal overlap, and portfolio expansion. Bootstrap and evaluator numeric comparisons use an absolute tolerance of `1e-12`; scoring comparisons are exact.

The full review was rendered and checked offline. Cloud artifact storage was checked with bounded examples. The full artifact is not claimed to fit the cloud report limit.

The one-command offline check includes:

- Existing Python unit tests, dependency hashes, audits, and artifact smoke tests.
- Python/TypeScript differential scoring, temporal, portfolio, and payload cases.
- Feature extraction regression cases and input-packaging checks with fictional profiles.
- Seeded evaluator, reviewed legacy scorer, and quality comparisons.
- Tuning payload and UI template equivalence, including a 5,001-path fixture.
- Legacy/evaluation embedded data, visible table, warning, and escaping checks.

## Limits and review gates

- Evaluator seeds above `2^53−1` are rejected. Python accepts seeds through `2^63−1`.
- Evaluator timestamps require the extended ISO form documented in `evaluation-contract.md`. Some alternative Python spellings are not accepted.
- Feature parity excludes explanatory wording and unused evidence registry records. It checks the fields that drive scores and their cited evidence.
- LinkedIn posts and public appearances are collected or discovered but require contextual verification before scoring. A mass tag is not equivalent to a direct collaboration.
- A shared investor is portfolio context. It is not evidence of an individual investor role, personal relationship, or board seat.
- Missing profile fields stay unknown. No missing-data fallback changes willingness or clears a review hold.
- Ranking diagnostics do not prove causal uplift. No automatic promotion is allowed.
- Old vendor SQL contact lookup methods are outside the reviewed pair-scoring Play.
- Live provider behavior was not revalidated through a new paid enrichment run solely to establish deterministic parity.

The generated template file must match the assets. After an intentional UI change, run `python3 plays/sync-template.py`, then rerun the offline check.
