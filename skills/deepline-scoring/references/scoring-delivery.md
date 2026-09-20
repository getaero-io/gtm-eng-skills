# Scoring delivery contract

## Freeze the decision

Record customer/workspace, analysis unit, supported identifier types, full scoring population, target/horizon, cutoff policy, requested dimensions, reference population, destination and spend scope. Resolve “main” to a named table/project and version before writes. Never switch customer data through another customer's workspace.

Return every input row with its original key. Invalid identity, insufficient evidence, and out-of-scope rows remain visible with null score/grade and a reason. Never silently drop them or assign D for missing data.

Score the full requested universe, not a post-opportunity filter. Evaluation can include a settled acquisition won/lost subset and a separately named engaged subset. Report each denominator. For win-within-H, require complete follow-up for negatives; pending rows are censored. Preserve renewal/expansion and dual-outcome episode rules. Accounts, deals, contacts and parent groups are distinct grains.

## Four dimensions, requested outputs only

| Dimension          | Inputs                                                                               | Excluded                                                    |
| ------------------ | ------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| account_fit        | External trade, geography, size, operating footprint, verified technology, ownership | Visits, replies, deal stage, AE notes, internal pain/budget |
| account_engagement | Dated relevant first-party activity, deduplicated across contacts                    | Fit points; lifetime counters with no recency               |
| lead_fit           | Account fit plus current role, seniority, responsibility and persona match           | Engagement points; seller-assigned champion labels          |
| lead_engagement    | Dated individual activity, relevance, channel and recency                            | Account size and title points                               |

Keep hiring spikes/acquisitions in separately named timing features unless the customer defines their place. Distinguish steady department structure from a fresh hiring event. Separation does not imply statistical independence. A customer-requested combined priority score is a separate tested policy; preserve the components.

## Point-in-time and proxies

Every observation carries entity ID/scope, feature/value/units, source ID/URL, source class, event_at, known_at, retrieved_at, extraction version and collection status. Default historical account cutoff is before the earliest relevant outreach/interaction or opportunity creation, according to the customer's decision. Verify histories; creation/import date may not be the original event. Enforce strict earlier-than for a pre-contact/pre-opportunity cutoff.

Do not declare a feature safe because it is firmographic or mostly pre-close. A fact learned later requires audited historical availability and a distinct reconstructed-backtest vintage. Current observations cannot validate older outcomes. Retain historical snapshots.

AE facts are discovery targets: map `internal variable → hypothesis → external proxy → source/units → match rules → availability → proxy error → incremental predictive test`. CSR count might map to dated named staff or department estimates. Review velocity/service footprint are call-demand proxies, NOT measured calls. Evaluate count estimates against CRM actuals separately from win prediction. Never assume proxy equivalence.

## A/B/C/D grades

Default bands, highest scores first: A top 10%; B next 15% (10–25%); C next 25% (25–50%); D remaining 50%. These are unequal percentile bands, not quartiles, probabilities, or validation criteria.

Freeze a representative reference distribution per dimension/model version. A singleton or new batch uses that reference, never itself. Persist reference ID, definition, date, N, model hash, sorted scores and tie policy. Do not derive cutoffs on the final holdout when measuring generalization.

Default tie policy: percentile = 100 × (strictly lower reference values + half the equal reference values) / N. A ≥90; B ≥75 and <90; C ≥50 and <75; D <50. Equal raw scores receive equal grades. Report actual shares and tie mass instead of claiming exact quotas. Fewer than two distinct reference values yields `insufficient_reference_variation`. Exact-capacity queues may use a disclosed stable-ID tie-break for queue position only. Missing scores stay unscored. Reference changes are versioned migrations.

## Required runnable artifact

Search/describe fitting Plays first. Inputs may be domain, company LinkedIn, email, person LinkedIn, or name plus company context; implement requested forms rather than promising every form. Ambiguous names fail with candidates/reason. Verify company/person URL types and parent/branch scope.

Create a reusable end-to-end Play with a shared pure scorer. Use the same transforms, missing-value policy, learned coefficients or approved heuristic rules, and reference distribution offline and online. No per-row LLM-generated weights. Prevalence ratios are not model coefficients. Pin provider schemas and extraction versions; retain provider attempts and source lineage. Separate paid enrichment from deterministic scoring so changing grades does not repurchase data.

Output: input, resolved identity, enriched attributes, requested numeric scores/grades/percentiles, model/reference versions, evidence, eligibility decisions, confidence/coverage, status and miss_reason. Export every row. Preserve run IDs, final export, observed costs and provider statuses. A domain-to-cached-row replay is NOT live enrichment for unseen domains; label it accordingly.

## Backtest and acceptance

- Assert no future/AE-derived inputs, outcome-derived features, or parent split overlap.
- Verify expected IDs, row counts, duplicates, outcome conflicts and pagination across all raw populations.
- Apply collection uniformly; report coverage-only negative controls.
- Fit selection, imputation, transforms and tuning inside training folds. Freeze temporal evaluation once; repeated peeks consume it.
- Compare trade/geo/size baseline and feature-family ablations. Report grade N/wins/losses/pending, precision@K, lift@K, PR-AUC and uncertainty at natural prevalence. Band shares are not performance.
- Calibrate before claiming probabilities. Test outreach impact prospectively, not from observational association alone.
- Fixtures: normal, sparse, ambiguous, wrong entity, stale/future source, import/backfill, negative evidence, provider error, ties, exact boundaries, zero variation, unknown domain, reference mismatch, singleton/batch parity, replay after version changes.
- Invariants: engagement cannot change fit; AE edits cannot change pre-contact scores; batch membership cannot change frozen-reference grades; customer data cannot cross workspaces.

Completion states: `research_only`, `replay_only`, `exploratory_end_to_end`, `validated_for_named_use_case`. Name unmet gates. Preserve report/HTML, signal inventory, evidence, score export, model/reference artifacts, Play source/checks, backtest, costs and unresolved rows.

Finish with the implementation-test stage routed from the skill. Known-answer regression, selected win/loss sanity checks and untouched predictive validation are separate gates; preserve independent oracles and failure receipts for each.
