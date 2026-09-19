# Final report contract

Deliver one Markdown report per workspace. If publishing to Notion, put the same content on one page. Combine the findings, scoring rules, runnable Play and evaluation results so the reader can decide what to do without opening another report. Link supporting files at the end.

Lead with the recommendation and its limits. Use plain language, short explanations and tables for comparisons. State the actual completion state: `research_only`, `replay_only`, `exploratory_end_to_end` or `validated_for_named_use_case`. Keep all five sections; mark unfinished work as not run or unavailable with the reason and next step. A polished enrichment sample is not a completed scoring evaluation.

Build tables and counts from the final export. Reconcile every displayed value, status and timestamp, then check that prose makes no stronger claim than its evidence. Link the actual Play, run and artifacts. Missing model or label prerequisites are unmet evaluation requirements, not proof that the model failed.

## 1. Who should we target?

Summarize the best-fit customer profile, strongest supported signals, verified disqualifiers and recommended action. State the product/use case, decision question, analysis unit, cohort, dates and split. Keep fit, engagement and capacity distinct. End the summary with a recommendation to use, pilot or revise, bounded by the validation completed.

## 2. Why these signals?

Combine relevant website, hiring, technology and buyer-language findings in one review table: signal/concept, aliases, source, won matches/observed, lost matches/observed, prevalence ratio, uncertainty, interpretation and evidence links. Include neutral, negative-association and inconclusive findings, plus rejected candidates and their reasons.

Show coverage by outcome and source: success, empty, missing, partial and error. Report population membership, exclusions and collection gaps. Support interpretations with exact evidence and counterevidence from both outcomes, including URLs, dates, roles and entity scope. Mark negated, uncertain and vendor mentions. Put the full candidate inventory, truncation flags, prevalence intervals, p-values, correction family and q-values in supporting files.

Name the metric: feature prevalence ratio is not conditional win-rate lift. Do not rank by raw lift bars or infer confidence from a large ratio with few matches. Low ratios do not establish hard anti-fit rules; job ads do not prove software intent, and title counts do not measure headcount. Citation quantity does not establish statistical validity.

## 3. Which accounts come first?

Use one ranked table with account/identifier, requested score and grade, contributing signals, missing evidence, buyer persona and next action. Show requested score dimensions separately. Keep unresolved or insufficient-evidence rows visible with null scores and reasons. Distinguish known customers, held-out deals and unlabeled alternatives; existing customers are not net-new prospects.

Explain every displayed score using the same versioned scoring definition used by the Play and evaluation. Include raw values, transforms, account contributions (including present/absent effects), caps, penalties and missing-value handling so totals reconcile. Separate the primary routing policy from frozen audit outputs and experimental candidates. Follow the scoring delivery contract for percentile grades and frozen references. Do not invent weights or force a ranking when no supported model exists.

## 4. How do we run this?

Include the checked Play link or source artifact, input requirements, example invocation, output fields and actual run status. Explain which evidence it collects through Deepline and which approved rules or frozen model it applies. Identify model/reference versions and link run receipts. State clearly if only cached replay was tested or live enrichment remains unimplemented.

When prospecting is requested, include usable company searches, buyer titles and evidence-based messaging angles. Record scope, authorization and budget for follow-on collection. Report generation does not authorize external sends or CRM writes.

## 5. Does it work?

Summarize each evaluation in a table: input/cohort, independent expected result, observed output, metric and acceptance threshold, verdict, and remaining limitation. Cover extraction accuracy, exact score reproduction, and held-out ranking against existing rules and a simple baseline separately. Include precision/lift at the intended outreach capacity, uncertainty, coverage controls and the most important mistakes. Report measured runtime and Deepline credits, including failures; identify unavailable costs rather than assuming zero. Link complete CLI receipts and evaluator outputs.

Explain the adversarial findings: coverage confounding, post-cutoff evidence, parent overlap, label selection, phrase tuning, multiple tests, rare estimates and source mismatch. Current enrichment cannot validate past predictions. If validation is not independent or point-in-time, say exploratory. Report failed comparisons and unmet gates, then state whether to use, pilot or revise and the next useful test. A useful result can be better ROI sizing or a rejected hypothesis rather than a new win predictor.

## Supporting files

Link the full input population and labels, candidate inventory and statistics, evidence/counterevidence, score export, frozen model/reference artifacts, Play source/checks, evaluation outputs and run/cost receipts. Keep private customer artifacts in the authorized workspace. These files support the report; the recommendation and key results stay in the report itself.

Version 2 analyzer exports `signals[]` and statistics; old `keyword_results`/lift consumers require migration. Fisher/Wilson/BH/BY assume account-level observations; disclose parent dependence and design limitations. Corrections cover one invocation, not all prior experiments.
