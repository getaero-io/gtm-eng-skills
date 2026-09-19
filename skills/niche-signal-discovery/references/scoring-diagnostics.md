# Diagnose scoring disagreements

Read this when a customer disputes a driver, a new extract changes rankings, or a proposed fix improves one metric while making routing worse. Keep the current validated path until the candidate passes the acceptance test for the named decision.

## Find the failing layer

| Symptom | Check first | Smallest useful correction |
| --- | --- | --- |
| Wrong company, branch, or operator type | Domain, name, location, parent/branch and source attribution | Resolve identity; retain ambiguous rows for review |
| Phrase fires in the wrong sense | Full quote, speaker, page type and definition | Correct extraction and test both matches and missed positives |
| Accurate feature gives implausible points | Encoding, scaling, correlated features, intensity and missingness | Diagnose contributions; compare regularized/constrained retraining and versioned caps |
| Scores drift with unchanged coefficients | Page selection, HTML/markdown, extractor, aggregation and source vintage | Compare the same accounts through each extraction path |
| Fewer reported false positives | Queue size, recall, labels, threshold and cohort | Compare at the same capacity and account for lost qualified leads |
| Sheet and Play disagree | Raw value → transform → contribution → score → grade → route | Use one versioned executor and reconcile the export |

## Define features before looking at outcomes

Group synonyms by business meaning before inspecting outcomes. Keep related details inside logical feature families without treating correlated aliases as independent evidence. Grouping for display does not silently change model inputs.

Keep a feature inventory: definition, source, coverage, encoding, role (`scored`, `display_only`, `candidate`, `gate`), and inclusion/exclusion reason. Weak linear correlation does not rule out nonlinear utility. Learn bins and support/shrinkage rules inside training folds. Sparse fields and null results stay visible without invented weights. Small unstable gains stay experimental.

Check literal matches against context: a term can describe a different entity, a quoted experience, a hypothetical condition or a different sense. A navigation link identifies a possible evidence source; follow it within budget before classifying the underlying claim. A stricter matcher must retain genuine paraphrases and be evaluated for recall as well as precision.

Review every declared feature across the error cohort, including nonmatches, plus representative correct cases. For each case record expected meaning, actual extraction, quote/URL, source coverage, encoding, contribution and suspected cause. Freeze annotations independently of model output. Rechecking edited rules on the same cases is regression coverage; measure precision AND recall on new annotated cases before claiming general improvement.

## Separate extraction from weighting

A standardized coefficient is not an account's points. For a linear term, show `contribution = coefficient × (value − training_mean) / training_scale`, then include the intercept and any link function, caps or overrides. Show present and absent contributions for binary features, unknown handling, and raw values behind the top drivers. Scores, probabilities and log-odds are different units.

When a binary feature is positive alone but negative in the fitted model, inspect correlated features, binary-plus-intensity encoding and suppression. Repeated SEO mentions and duplicate pages can amplify intensity without adding business evidence. Do not delete valid synonyms or flip a coefficient to make the story intuitive. Compare grouped/binary features, regularization, approved sign constraints and family caps in a new candidate with a stated tradeoff.

A family cap must include every intended member; test related features cannot bypass it. A positive-contribution cap does not remove negative absent-feature penalties. Test an absent/sparse row separately and change/version the missingness or absent-contribution policy if required. A missing website phrase may reflect coverage or SEO choices; it does not establish business absence. Preserve the old scorer for audit when approving a correction.

## Preserve the whole scoring path

Freeze source bodies or durable references, page-selection recipe, content representation, extraction rules, aggregation/transforms, model coefficients, reference grades and routing policy. Version these together. “model.json unchanged” does not mean scores or routes are unchanged.

Test three claims separately: identical saved inputs reproduce exact outputs; newly extracted features agree with saved features; the resulting live scores and routes remain useful. Correlation, matching grades or similar page depth cannot substitute for exact parity. If the original corpus is unavailable, retain the gold vectors and report reconstruction limits rather than promising exact reproduction.

Use a bounded page plan driven by unresolved features: pages that can resolve the relevant claims. Preserve page roles and deduplicate repeated copy. A source upgrade needs a paired account comparison with coverage, feature flips, score deltas and routing changes before rollout. More pages or more filled fields may worsen performance. Keep paid collection separate from rescoring and preserve a rollback path.

## Qualify, then prioritize and route

Separate verified eligibility (`eligible`, `needs_review`, `hard_DQ`) from propensity among eligible accounts. Define disqualifiers with the customer. Verify exclusions at the scored entity’s scope. Missing or unobserved attributes cannot alone justify hard rejection.

For inbound, define qualification labels and route/review/drop costs. Measure qualified precision at rep capacity, recall, false hard-rejects, review load and response time. For a won/lost target, name high-score losses and low-score wins as outcome disagreements; they are not verified fit errors. Do not lower queue volume or exploit label ambiguity to claim improvement. Reconfirm acceptance when switching between outbound ranking, win propensity and inbound qualification. Grades alone are not routing authorization.

Choose corroborating sources appropriate to the proposed feature. Resolve identity and entity scope before joining records. Check coverage and freshness; missing corroboration stays unknown. Discover the provider contract and test the required capability before scaling.

For semantic feature categorization, reuse saved pages and batch related questions through a supported evaluation tool. Emit observed/absent/unknown, evidence quotes and attribution; retain uncertain cases for review. Keep this separate from the deterministic scorer. Compare against blinded human annotations, including sparse/ambiguous cases. Agreement with old regex is not ground truth. Pin the model/prompt/schema, cache by source and definition hashes, and measure end-to-end latency and Deepline credits including scraping, retries and runtime. Cheap labeling alone does not prove cheap collection or better ranking.

## Deliver one operational answer

Show one approved primary score and routing decision with reasons. Preserve frozen outputs for audit and put candidates under clearly named experimental fields. Link stable Play IDs/revisions and test the links. Reconcile the spreadsheet/report with the final export, including driver values, transformed contributions, thresholds and policy versions.

For every candidate, compare the same cohort and source vintage with the incumbent at a fixed capacity or predeclared threshold. Report score/route movers, qualified precision/recall, outcome metrics where applicable, review/drop counts, coverage, uncertainty, latency and cost. Retain failed experiments. After tuning on those errors, use an untouched cohort for promotion; the reviewed mistakes are now regression cases.
