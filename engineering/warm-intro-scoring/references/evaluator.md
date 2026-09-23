# Evaluating warm-intro matches

Evaluate a frozen baseline against one candidate on the same point-in-time candidate universe. Research chooses hypotheses and adversarial cases; observed held-out data decides whether they improve rankings. The saved [last30days synthesis](research-brief.md) did not establish coefficients or outcome uplift.

## Required evaluation record

Record campaign/request IDs, target/account split groups, per-query scoring cutoff (`scored_at`), report observation cutoff (`as_of`), baseline/candidate versions, candidate IDs in ranked order, independent relevance labels, evidence observation dates, and both-edge/willingness states. Features must have been observed by that query's scoring cutoff. Outcomes may arrive later but must be observed by the report cutoff. Keep identifiable records private. The executable fixture is fictional. Ordinal points are not probabilities.

Freeze the cohort and metrics before running the candidate. Label routes independently of model score, blind reviewers to ordering, and adjudicate disagreements. Label `1` only for a source-supported suitable route for the specified ask; `0` for an assessed unsuitable route; `null` for unjudged. A declined connector is operationally blocked even if the historical relationship is real. Record relationship, relevance and operational eligibility separately.

| Question | Metric and eligible denominator |
|---|---|
| Can we compare rankings? | Identical complete candidate sets and unique IDs for both models. A retrieval change requires a separately judged union and retrieval coverage report. |
| Are useful routes near the top? | Recall@3, MRR, binary nDCG@3 on fully judged queries with at least one relevant candidate. Exclude incomplete labels and no-positive queries with explicit counts. |
| What is missing? | Total queries, eligible queries, incomplete-label queries, no-positive queries; include no-route targets in the cohort. |
| Did the candidate improve? | Paired per-query deltas and seeded account-cluster bootstrap intervals, plus query and account counts. Shared connectors across accounts require additional dependence analysis before release claims. |
| Are paths actionable? | Zero ready paths with unknown/weak edges or non-yes willingness. Factual scores remain separate. |
| Did introductions work? | Sent asks whose fixed observation windows have closed. Report drafts, unsent, censored/open and mature counts separately. A missing observation is not zero. |

For incomplete labels, the primary ranking metrics exclude the entire query. Do not silently turn unjudged routes into negatives or substitute the first *known* relevant rank for MRR. Diagnostic bounds are separately named and never pooled into the primary result.

For outcomes, require dated sent events, a predeclared window, and explicit observed reply/meeting values with event timestamps for positives. Count successes only within the closed interval from sent time through sent time plus the declared window. A day-60 reply is not a success for a 30-day rate. Validate event chronology against both the observation watermark and evaluation cutoff. An open-window sent ask is excluded from both success-rate numerators and denominators, even if it already has a reply. Show the reply as a raw event if useful. If maturity cannot be established, report counts and “rate unavailable.” Never divide observed meetings by all drafts or immature sends. Observational rates describe the selected sends; they do not establish causal uplift between rankers.

## Research-driven challenge matrix

| Research signal | Controlled contrast / failure to catch |
|---|---|
| Both directed ties (Happenstance) | Strong requester edge plus unknown target edge must remain held. |
| Observed versus inferred networks (Happenstance) | Large-company overlap, alumni match or profile URL must not become relationship proof. |
| Recency/frequency (Affinity) | Recent substantive interaction versus stale, repeated or duplicated receipts; never use post-ask evidence. |
| Reciprocity (research hypothesis) | Replies versus outbound bulk mail, CC lists and unaccepted invitations. |
| Team/project context | Actual dated shared small team versus same company and title only. |
| Willingness and specific ask (Happenstance) | Newer decline overrides old yes; unrelated yes remains unknown for this ask. |
| Relevance/complementarity | Shared job function versus supported fit for the request; avoid rewarding sameness regardless of goal. |
| Capacity and provenance | Overloaded connector, missing history, duplicate sources, identity collision and sparse profiles. |

Run one-factor additions and leave-one-factor-out ablations against the fixed baseline. Use function, company size and profile completeness slices; retain missing values as an explicit slice. Do not infer protected traits. Each slice needs its own counts and uncertainty. A tiny slice is descriptive, not a ranking-quality verdict.

## Release gates

1. **Invalid evaluation:** identity/universe mismatch, post-cutoff features, target/account train/test leakage, or an unsafe ready path. Fix and rerun; an attractive average cannot override this gate.
2. **Insufficient evidence:** few independent queries, incomplete labels, unknown outcome maturity, unverified provenance or only synthetic fixtures. Keep the baseline; publish diagnostic results with limitations.
3. **Candidate for prospective trial:** provenance reviewed, no hard-gate violations, preregistered primary metric meets the chosen practical improvement threshold with group-aware uncertainty, and no unacceptable slice regression. A positive exploratory metric is not automatic production approval.

Separate dataset correctness from source truth. The runner can check supplied metadata and invariants, not prove a human knows another human. Source audits and blinded relevance adjudication remain required. The bundled bootstrap resamples accounts and preserves their query groups. It assumes independent accounts; shared connectors across accounts remain an unmodeled dependency. Fewer than 30 eligible accounts triggers an insufficient-evidence warning; reaching 30 is not a power calculation or proof of adequacy. The runner does not automate factor ablations or slice analysis: run frozen candidate variants and retain labeled slice counts separately. Calibrated probabilities, survival modeling, causal inference and automated weight search are outside this runner.

## Common mistakes and red flags

| Shortcut | Correction |
|---|---|
| “One reply out of two sends” when one window is open | Compute the fixed-window rate only on mature sends; keep other events as counts. |
| “First known relevant rank” under missing judgments | Exclude incompletely judged queries from primary ranking aggregates. |
| “Research says recency matters, ship a half-life” | Treat recency as an ablation hypothesis, not an established coefficient. |
| “All tests pass, therefore match accuracy improved” | Structural tests establish implementation behavior only. |

Stop an uplift claim if evidence includes future observations, labels were derived from model scores, only selected successes were retained, or the sample has no outcome-complete comparisons.

## Run the evaluator

```bash
python3 "$SKILL_DIR/scripts/evaluate.py" "$SKILL_DIR/assets/evaluation-example.json" \
  --output evaluation.json --html evaluation.html
```

Use new output paths on each run. Both outputs are private files and refuse overwrite. `--help` documents the strict JSON schema; input requires per-query `scored_at` and report `as_of`, ordered baseline/candidate IDs, independent binary/null judgments, and path metadata. Optional outcome records carry dated events and observation watermarks. Omitted train/test split metadata forces insufficient evidence. Invalid inputs exit 2 without writing reports; complete account-cluster uncertainty and per-query results are retained in JSON and the HTML disclosure. [Validation record](evaluator-validation.md) documents the agent pressure test and executable checks.
