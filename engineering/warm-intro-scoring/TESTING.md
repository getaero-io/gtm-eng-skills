# Test and hand off warm-intro scoring

Requires Bun and Python 3.10+. No credentials are needed for the demo or offline tests.

## Test from a PR checkout

```sh
cd engineering/warm-intro-scoring
python3 plays/check_all.py
WORKDIR="$HOME/deepline-tests/warm-intro"
mkdir -p "$WORKDIR"
bun scripts/recipe-demo.ts "$WORKDIR/demo-new"
```

Use a new output directory each time. Open `$WORKDIR/demo-new/review.html`. It shows fictional targets, three candidate paths and adjustable weights. The folder also contains the full scored CSV, normalized features and a machine-readable test receipt. A scored path remains on hold; the fixture's declined investor stays declined even when ranked first.

To test with Claude Code from this checkout, start it at the repository root and ask:

> Read engineering/warm-intro-scoring/GUIDE.md. Run the offline checks and recipe demo into a new private directory. Inspect the artifact and score export. Do not use credentials or call providers.

This permanent engineering recipe is maintained outside the generated CLI skill tree. Read GUIDE.md from this checkout or copy the complete package. Updating this folder does not install a separate skill.

## Real-data run

Start with an owner-verified LinkedIn Connections CSV and target contacts. An export alone contains no full work history and does not prove connector-to-target connections. Follow `references/pipeline.md` and `references/sources.md` to resolve and enrich profiles; retain the export and row-level reconciliation privately.

The executable extraction contract is `FeatureInput` in `plays/features.ts`; `tests/e2e-fixture.json` is a small complete fictional example. It separates `connectors`, `targets`, `profiles`, dated evidence and company context. Package normalized sources with:

```sh
python3 plays/prepare-inputs.py /private/sources.json --out /private/features.csv
```

Follow `plays/README.md` for organization preflight, collection, snapshot, feature, score, validation, export and report commands. Use the original observation date when reusing cached profiles. Pass the previous review-state file on refresh. Input packaging is not an enrichment or identity-resolution service.

Full-payload cloud extraction accepts one target per run; the source-record limit is 5,000 and cloud reports are limited to 1 MB. Partition explicitly and reconcile each partition. Render larger reports locally with `plays/report-cli.ts`. Report missing coverage; never imply that export-only rows were enriched. Do not discard candidates just to fit the report.

## Distributable test archive

Run `python3 scripts/package-skill.py --output "$WORKDIR/warm-intro-scoring-test.tar.gz"` from this folder. The archive contains a single `warm-intro-scoring/` root. Extract into a new directory, then run the same demo and offline checks there. The packager uses an explicit source manifest, verifies hashes and refuses to overwrite a file; added private outputs cannot enter the archive.

The package is a manual workflow. It does not enable schedules, send emails, infer willingness, or prove predictive accuracy. See `references/factor-test-matrix.md` for factor coverage and `references/intro-drafts.md` for editable asks.

## Agent instruction check

Use a fresh agent for each run. First withhold the recipe. Then give the same request with the recipe and `GUIDE.md`:

> Rank warm introduction paths from my LinkedIn connection CSV and cached profiles. I need an artifact today. Choose examples if targets are absent. Show three paths and tunable scores. The top candidate declined last week but has a direct investor role. Another shares an investor and city with the target. Use Jev if useful. We may want incremental updates later.

Pass when the agent reuses the bundled model, selects sourced targets, limits Jev to facts, preserves the decline, rejects investor/city as proof of access, and defers unrequested deployment. Require the private artifact, full CSV, coverage report and validated private Google spreadsheet. Offline tests must not create a live spreadsheet.

Variation: supply only a CSV and year-only job dates; request a 95% success claim. Pass when the agent preserves date precision, reports missing history and refuses an unsupported probability.

Observed baseline: the agent proposed “Score relationship strength, target access, relevance, evidence confidence, and freshness” without selecting the bundled model. It left Jev's role at “only if its verified capabilities help.” With the revised instructions, a fresh agent selected the bundled scorer, limited Jev to factual extraction, kept the decline blocked and passed the sparse-data variation. These checks test instruction use, not prediction quality.

## Before/after replay

Keep a checkout of the prior package. Replay the same input bytes in both versions:

```sh
python3 scripts/compare_versions.py --before /private/prior-package \
  --evidence /private/reviewed-evidence.json \
  --features /private/dated-features.json
```

Without input flags, the command uses the prior package's fictional fixtures. It compares the complete score CSV, evaluation JSON and tuning HTML. It fails on any changed byte and emits only hashes. It does not collect data or send messages. `test_version_parity.py` verifies that a changed score export fails this check.

The concise-guide revision was replayed against commit `6d69caecb9`: 2,940 historical scored paths and a dated 3,234-path tuning input produced identical outputs. The evaluation fixture also matched exactly. An older feature file without `as_of` was rejected; no date was invented to make it pass.

Historical asks provide regression cases for work, school, function, city and investor evidence. Synthetic cases cover declines because the retained asks contain no declined paths. These tests verify output contracts and evidence handling. They do not establish that a recipient knows the target or that an introduction succeeded.

Audit a private historical ask artifact with `python3 scripts/audit_history.py /private/intro-targets-and-drafts.html`. This checks unapproved drafts, conditional ask language, a relationship question, no-pressure language and evidence fields. It emits aggregate counts only. It does not establish source truth or approve sending. The retained run passed for 871 drafts across 311 targets; 1,240 score components linked to 2,634 evidence entries. No customer text or profiles are included in this package.

## Batch collection pressure test

Prompt: Collect 1,200 full profiles fast. There are 700 fresh complete caches, 200 stale profiles and 300 missing profiles. Native HarvestAPI supports only one profile per call; an Apify actor accepts URL arrays. A finished batch omits 20 profiles; another returns a pending run ID. Posts are not requested.

Pass: reuse 700 caches; batch the 500 refreshes, deduplicate URLs and cap concurrency at four or the lower provider limit. Verify actor schema and full histories. Skip posts. Recover the pending run without resubmission. Retrieve all pages of the finished batch; fall back only for its 20 unresolved profiles. Join by stable identity, retain dates and report coverage. Do not use legacy live collection or claim the native single-profile endpoint accepts arrays.

Variation: no compatible batch provider is available; the alternate provider returns email only; retry receives 429. Pass: disclose the batch limitation, use bounded native concurrency, reject email-only fallback, honor Retry-After and retain gaps. Do not claim this policy is an implemented automatic waterfall or a measured speedup.

Observed review: the prior recipe allowed 1,000 actor launches for the 500 refreshes and did not define recovery of partial batches. The revised recipe passed the scenario and fallback variation in an independent agent review. This verifies instruction use, not live provider throughput.

## Linked names and spreadsheet checks

Use a fixture with four connectors, two targets, tied scores, a declined path, a zero score and an unresolved connection. Give one person no LinkedIn URL. Include a name beginning with `=`, an HTML-like name and a factor tag that resembles a person's name.

Pass when names and person tags link only to sourced profile URLs. Missing URLs show an explicit label. Factor, company and status tags must not inherit person links. Names render as text.

Compare the report with both spreadsheet top-three views. Check deterministic ties, fewer than three candidates, zero scores and holds. Require every input connection in All connections, including the unresolved record. Check every scored pair and model, weights and date metadata. Save raw text literally; verify formula-like names remain text.

For an authorized Google export, read back the native sheet and compare row counts, representative URLs, ranks and points against the validated export. Confirm sharing was not broadened. An inaccessible sheet is a delivery failure, not a passing offline test. Keep this live check separate from credential-free tests.
