# Cached pipeline: end-to-end and adversarial review

Reviewed with Claude Code CLI on 2026-09-23/24. This is a functional and adversarial review, not a prediction-accuracy evaluation. No new paid profile or public-post collection was needed.

## Reproduce

Run the offline suite from this package:

```sh
python3 plays/check_all.py
```

The opt-in cloud harness writes fictional test revisions and a private review to the selected Deepline workspace. Run preflight separately and confirm the organization before starting. Use a new output directory; credentials use the caller's CLI scope.

```sh
deepline preflight --json
python3 /absolute/path/to/tests/cloud_e2e.py --out /private/new-test-directory
PLAYWRIGHT_MODULE=/path/to/playwright node tests/browser_e2e.cjs /private/new-test-directory/review.html /private/browser-receipt.json
```

The harness runs cached collection → normalized profiles → immutable DB snapshot → DB read-back → feature extraction → exported payload merge → tuned scoring → cloud report → independent file read-back. It checks all input and output identities. The fixture has five contacts and four paths: investor 120, coworker 80, employer only 20, sparse 0. Increasing work weight to 160 produces 160, 120, 40, 0 and preserves a declined investor path. Browser checks cover the top three, the blocked state, selected weights, mobile layout, script errors, and network requests.

## Corrections made after adversarial review

- Invalid or duplicate connector identities fail closed. Known LinkedIn language/detail URLs are normalized. Member-ID URLs need a reviewed vanity alias; they are rejected until resolved. Stable equal person IDs exclude self-pairs.
- Investor-facing employee titles do not qualify as direct investment roles.
- Investor-employer links require both reviewed investment evidence and a current, dated role at `investor_company_id`. Company names alone cannot produce portfolio points.
- Cached profiles retain the earliest supplied original receipt date. A missing original date fails. Cached collection now produces normalized profiles. `account_domain` is an explicit reviewed account assignment, not inferred from a person's name.
- Duplicate company sizes, reversed dates, invalid months, duplicate JSON keys, nonfinite numbers, and dangling feature-catalog references fail.
- Declines survive missing/unresolved refreshes in the exported review-state ledger. A changed feature set invalidates a prior ready state. Keep this ledger with the next refresh.
- `--source-input` reconciles target export keys against the original input. Without it, completeness is explicitly unverified.
- Reports show unresolved targets and unmatched prior review states. Cloud and local TypeScript reports require an evidence registry. CSV text is escaped against spreadsheet formulas.
- Location matching no longer treats similarly named cities outside California, or ambiguous multi-location text, as one verified Bay Area location.

The added adversarial regression suite contains 20 TypeScript cases; together with the 12 existing feature cases, all 32 pass. Seven Python packaging, refresh-ledger, export-reconciliation, and CSV safety cases pass. The full offline suite also passes.

The original migration matched the frozen Python output. Correctness fixes deliberately change source-derived features. On the reviewed full snapshot, all 311 targets and 91,428 paths remain. 323 baseline scores decreased, none increased; 240 city-overlap values and 81 investor-portfolio values were removed. Some paths have more than one correction. These changes must not be described as unchanged-output parity. Historical source receipts and individual differences remain private.

## Remaining prebuilt release gates

- Live provider contracts, charges, asynchronous actor recovery, and partial profile/posts failures have not been exercised by this cached test. Live collection still requests profiles and posts for supplied rows; it is not an automatic gap-only refresh service.
- Profile age is visible through observation dates but there is no calibrated relationship-decay policy or enforced refresh threshold. Historical coworker evidence can still rank highly; it does not imply a current personal relationship.
- An evidence ID and a source locator do not prove source truth or subject relevance. Arbitrary caller-supplied features need a trusted, reviewed evidence-binding layer. The package does not independently verify every cited claim.
- The prebuilt needs tenant/requester-scoped persistent willingness and deletion handling. The local review ledger is not a substitute for reading the latest DB willingness records. Preserve stable canonical identities across imports.
- Automatic source-table mapping, identity-alias resolution, queue/leases, affected-pair triggers, per-run budget enforcement, and recovery orchestration are not enabled.
- Bad shared source records fail a target batch instead of entering a complete per-record quarantine/recovery workflow. Resolve or isolate invalid inputs before retrying.
- Large reports still use local assembly; cloud output has a 1 MB cap. Database page reads are not transactionally consistent during source updates.

Status: the bounded cached pipeline is testable and passes. A fully automatic, unattended prebuilt is not release-ready yet. No messages, consent updates, or schedules are enabled by these checks.
