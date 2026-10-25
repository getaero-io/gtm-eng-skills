# Backtest and score the visible account population

Use this task when asked to backtest, keep a holdout, improve predictive power or score every visible account. Deliver an executable project-specific batch scoring task and a separate evaluation task, with manifests and receipts in the persistent project directory. This reference is the task specification; the packaged lexical analyzer is not a trained propensity model or a backtest runner.

## Choose the evidence path

| Available evidence                                               | Deliver                                                                                                      |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Historical account snapshots, dated features and mature outcomes | Historical backtest with time and corporate-parent isolation                                                 |
| Current websites and historical wins/losses only                 | Current population scores plus a frozen prospective cohort; historical predictive validation remains blocked |
| Previously inspected test outcomes                               | Development results; reserve a new untouched future cohort for final evaluation                              |
| No approved model or outcome definition                          | Feature export and explicit prerequisites; do not invent weights or label the score validated                |

Score the full authorized population and protect a holdout: these are complementary tasks. Scoring a held-out account through a frozen model is allowed. Using its text, outcomes or errors to choose phrases, transforms, weights or thresholds consumes it. A task can complete population scoring while evaluation remains pending.

## Freeze the task before modeling

Record the workspace and visibility boundary, query/filter, extraction time, pagination receipts, full account ID inventory and snapshot hash. Enumerate all readable accounts within that boundary, preserving accounts without websites, missing fields, open opportunities and failed sources. Describe inaccessible partitions and changed/deleted records; do not call a filtered or incomplete extract the whole CRM. Visibility does not grant an unlimited enrichment budget: reuse snapshots, pilot new collection and scale within the authorized budget.

Define the unit as account/product/decision episode, resolve corporate parents, and choose a target such as conversion within a stated horizon after first eligibility. Define eligible population, maturity date, negative outcome and censoring rules before seeing candidate results. A closed-lost opportunity is not automatically a permanent negative for the entire account. Never assign pending, uncontacted or unknown accounts a negative label just to score the full inventory.

Persist a `task_manifest.json` with:

- Task ID, snapshot/query hashes, identity and parent-resolution version, decision cutoff(s), target/horizon and label policy.
- Train, tuning/validation, calibration and final-test time boundaries, parent assignment policy, split seed when needed, split hash and exclusions with reasons.
- Source snapshot hashes and event/known/retrieved timestamps, extraction code and phrase/alias hashes, model/transform/missingness/reference hashes.
- Incumbent and baseline versions, capacity K, primary metric, minimum business improvement, uncertainty method and acceptance threshold.
- Paid-collection budget, actual scorer/Play version, execution command/API inputs and evaluator version.

## Protect the holdout

Prefer rolling forward-time development folds and a final later untouched window. Keep every corporate parent in one partition, including subsidiaries and repeated account episodes. If a parent spans time boundaries, apply a declared purge/exclusion policy and report its impact; do not quietly move future observations into training. Fit phrase mining, learned aliases, feature selection, imputation, embeddings/transforms, model tuning and thresholds inside training folds only. Use calibration data separately when probabilities are requested.

Reserve the final test before development, with its size determined by mature independent-parent counts, positive counts and the precision needed for the decision. Do not require a fixed 20% split when it leaves too few outcomes. Report effective counts and insufficient power. A random parent-group split is acceptable for a stated same-period question, but it does not establish future performance.

Keep test labels in an evaluator-only artifact, outside the feature-generation and tuning inputs. The evaluator joins labels only after it verifies the frozen model and score hashes. Record each reveal in a holdout ledger with cohort ID, model hash and purpose. Once revealed, that cohort can support regression checks and transparent comparisons; further tuning requires a new final cohort. A file hash proves consistency, not that an agent has never inspected the labels; disclose prior access.

Validate point-in-time availability of every feature and exclude post-decision CRM edits, sales notes, opportunity stages and outcome text from pre-contact fit. Today's scrape cannot reconstruct a historical website. Without archival proof, freeze today's scores before outcomes mature and schedule evaluation for the horizon instead of reporting a retrospective lift.

## Score every account

Build the batch task around the delivered model's actual scoring function or checked Play. Keep labels out of its inputs. Reuse evidence by account/source/snapshot identity and resume by task/model/account-episode identity, retaining one canonical output and attempt receipts without duplicate paid collection. Score the full snapshot, including train and holdout rows; retain partition metadata separately from model inputs. Training-row metrics are descriptive only.

Export `population_scores` with account/parent/episode ID, scored-at, model hash, score, optional calibrated probability, grade/reference hash, source coverage, phrase/concept values, evidence pointers, contributions, status and unscored reason. Apply only the frozen missingness policy. Account for every inventory ID as scored, unscored or explicitly excluded, and reject duplicate/unmatched IDs. Paginated storage can preserve the complete export without embedding all rows in a status response.

## Evaluate once against frozen comparisons

Run all candidates on the same eligible holdout and decision dates at natural prevalence. Preserve the entire population result; report both operational coverage and paired comparisons on common scorable rows so dropped hard cases cannot manufacture an improvement.

| Comparison                                                                | Question                                                              |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Existing rules or incumbent                                               | Does the candidate improve the actual decision?                       |
| Industry, size and geography                                              | Does it beat simple firmographics?                                    |
| Firmographics plus reviewed website phrases/concepts                      | Does website language add measurable value?                           |
| Remove each feature family; include coverage-only control                 | Is gain tied to real features, collection bias or one fragile family? |
| Regularized simple model, then a nonlinear challenger if data supports it | Does complexity beat a reproducible baseline?                         |

Treat billing/revenue models, buyer type, workflow/pain, use cases and public technology evidence as candidate families. Test context-reviewed concepts against exact phrases and count correlated aliases once per concept. Optional customer-supplied evidence can be an ablation when available; the task does not depend on gated competitor intelligence. Keep engagement separate from fit, and evaluate any combined priority policy against its intended outreach decision.

Report precision@K, recall@K, lift@K versus the same cohort prevalence, PR-AUC with its exact estimator, grade counts/outcomes and false-positive review. Freeze K to actual sales capacity. Handle ties without labels and include tie-aware precision expectations or ranges. Report parent-clustered uncertainty for paired metric differences, outcome counts and subgroup/coverage slices. Use reliability plots and Brier/log loss for calibrated probabilities; a percentile or arbitrary score is not a probability.

Record every candidate and failed comparison. Choose the winner on development data, then make the final holdout decision using the predeclared primary metric and acceptance threshold. Do not repeatedly peek, pick a favorable K or claim success from whichever subgroup improves. Prediction among previously contacted accounts does not prove causal outreach lift or transfer to uncontacted accounts; retain that selection boundary and use an authorized prospective randomized comparison for incremental impact.

## Deliver and refresh

Deliver `task_manifest.json`, `split_manifest`, an evaluator-only `labels` artifact, `holdout_ledger`, complete `population_scores`, `evaluation_report` and executable scoring/evaluation commands with their receipts. The report reconciles inventory and partitions, flags leakage/censoring/access gaps, compares baselines, states uncertainty and records pass/fail/pending against the acceptance threshold. A runnable task without mature untouched outcomes remains exploratory.

For recurring rescoring, pin a new population snapshot while keeping the approved model frozen. New data does not silently retrain it. Monitor source coverage, feature and score distributions, then realized ranking/calibration as labels mature. Record refresh cadence and retraining triggers. Use rolling development windows and a fresh final cohort for a replacement model; do not recycle the old test as proof of improvement.
