# Test and evaluate scoring

Report rule correctness, output parity and predictive usefulness separately. Each needs its own evidence.

## Freeze expected answers

Record the decision, horizon, unit, approved rules, transforms, missingness policy, model/reference versions, source snapshots and expected outputs. Hash them before running the candidate. Author expected answers independently using source quotes and approved definitions. Never call the candidate to generate its own expected answers.

Select cases by a fixed seed or stable ID order, stratified only by declared outcomes and coverage needs. Keep every selected case and exclusion, including failed sources and conflicting labels. Rules learned on those accounts make this a regression replay. Wins can have weak fit and losses strong fit; do not tune scores to force the expected ordering. Keep private cases outside published skills.

For disputed drivers or a changed extraction path, use [scoring diagnostics](scoring-diagnostics.md) to separate definition, coverage, weighting and routing failures before changing the candidate.

## Implementation checks

Run independently frozen positive, counterexample and source-error cases through the generated Play's actual extraction/scoring functions before scaling. Assert emitted fields, not a second implementation of the rules. The shipped lexical analyzer's passing tests do not validate a newly authored Play. Retain a failing pre-fix receipt and replay the corrected code against the same evidence; replay is not a new live run or an untouched holdout.

| Layer      | Check                                                                                                                                                                                                                                                                               |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sources    | Failed pages, empty success, partial results, malformed payloads, pagination and wrong entities. Missing collection stays unknown.                                                                                                                                                  |
| Features   | Negation, uncertainty, misleading substrings, buyer/seller context, title versus duty, duplicates and language coverage. Inspect matches and nonmatches against quoted evidence.                                                                                                    |
| Scores     | Approved transforms, caps, decay, overrides, rounding, exclusions, missingness and exact boundaries. Bind references to model content, including transforms and grade policy; reject changed content under an unchanged ID.                                                         |
| Parity     | Compare original executor, candidate and actual Play export field by field. Keep score, probability, percentile and tier distinct. Preserve requested legacy outputs; version and explain any approved correction to legacy behavior.                                               |
| Invariants | Outcomes and AE edits cannot change pre-contact fit; engagement cannot change fit. Row order, batch neighbors and repeated runs cannot change a frozen score or cause duplicate enrichment. Preserve replay identity across equivalent artifact serialization.                      |
| Agents     | Verify intended reads, successful execution, complete rows and tool receipts. A prescribed sample is a smoke test. Test feature selection and extraction with blinded cases and hidden expected answers. Compare repeated runs using the same wall-clock boundaries and cost units. |

Use a controlled bad expectation or mismatched reference to prove the check fails with a nonzero exit and retained receipt. Fix the implementation when an accurate expectation fails. Changing an expected answer needs independent evidence; never weaken an assertion to get a pass. Do not impose monotonicity on a deliberately nonmonotonic model.

Keep the executable evaluation harness and private expected inputs/outputs in a separate evaluation project. Each case records the input identity, frozen source/config/model versions, independently expected fields, evidence quote and rule source. Preserve the pre-run manifest and failure receipts. A lexical observation, exact numeric replay, live enrichment check and predictive comparison answer different questions.

## Predictive acceptance

1. Define mature outcomes at the decision horizon. Keep pending records censored, unknown alternatives unlabeled and synthetic cases separate. Join labels and scores at the same entity/product/episode grain; do not test a best-product score against one product's outcome. Report all cohorts and unmatched rows.
2. Isolate time and corporate parents. Fit feature selection, imputation, transforms and tuning inside training folds. Use separate calibration data and an untouched future cohort. Record training overlap. Later-retrieved archives need independently verified historical availability.
3. Compare existing rules, an industry/geography/size baseline, feature-family ablations and a coverage-only control. Report coverage by outcome and subgroup before lift. If collection predicts outcomes, investigate the bias; removing coverage flags alone does not resolve it. Retain failed comparisons and all model attempts.
4. Rank without consulting outcomes. Use stable IDs for queue ties and report tie-aware expected precision or its range at capacity K. Report precision/recall, lift, PR curves and grade-level counts/outcomes at natural prevalence. Check qualification and false positives within the top grade; filling a percentile quota is not acceptance.
5. Estimate uncertainty at the independent unit. Grouped bootstrap/permutation controls need appropriate assumptions; permutations must repeat selection and tuning. Account for all tested hypotheses. Small perfect samples and favorable p-values do not establish validation.
6. Report reliability and Brier or log loss on untouched data before calling a score a probability. Predeclare the minimum business improvement, tolerated misses/false positives and confidence requirement. Bind any promotion evidence to the model, population, horizon and evaluation artifacts. A caller's `validated` flag is only a declaration. Measure incremental outreach impact prospectively and monitor drift after release.

Finish with passed/total assertions, skips, population reconciliation, baseline results, uncertainty, failures and the supported completion state from the skill. Keep replay, live enrichment and validated use distinct. Name unmet requirements.
