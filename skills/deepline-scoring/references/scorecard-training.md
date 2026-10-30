# Train an artifact-backed scorecard

The `scripts/scorecard/` package is the scorecard engine first used for the Prove propensity run
(dbt-aero, September 2025) with a lift mode added. One trainer, one scorer, one artifact bundle;
the offline report, the batch scores and the replay Play all read the same files.

## Which mode

| Mode | Use when | What it fits | Output |
| --- | --- | --- | --- |
| `lift` (default) | Any labeled set with at least 3 of each outcome and about 20 rows | Nothing. Each feature bin contributes `scale × (WOE_bin − WOE_reference)`, Jeffreys-smoothed from won/lost prevalence. Intercept is the training base log-odds. | Points, percentile grade A/B/C/D against the frozen training reference, uncalibrated probability |
| `propensity` | The customer asks for probabilities or tiers and there are at least 100 positives, a later cohort for validation and a separate calibration split | L1 logistic regression on the WOE bins, isotonic calibration on the validation split, A/B/C tier cutoffs chosen for precision ≥ 40% at coverage ≤ 12% | Everything above plus calibrated probability, tiers, tier lifts |

Use `lift` unless the customer specifically asks for a propensity model. The CLI refuses
`propensity` below `--min-positives` (100) and `lift` below 20 labeled rows or 3 of either outcome;
`--force` overrides and records the override in `run_meta.json`.

## Pipeline

```bash
V=.venv/bin/python   # uv venv .venv && uv pip install pandas scikit-learn pydantic pyyaml
# 1. accounts: domain,status,known_at,scored_at,... (HubSpot helper or your own CSV)
cli-sh $V scripts/hubspot_accounts.py --output accounts.csv --universe-sample 300
# 2. sources: website pages + job openings per domain (paid; resumable; receipts per domain)
$V scripts/collect_sources.py --input accounts.csv --output accounts_sources.csv --pages 8 --workers 6
# 3. discover and freeze concepts (see keyword catalog / buyer-language research)
$V scripts/analyze_signals_v2.py --input accounts_sources.csv --discover-phrases --output candidates.json
$V scripts/analyze_signals_v2.py --input accounts_sources.csv --keywords keywords.json --tools tools.json \
   --job-roles roles.json --partition discovery --output signals.json
# 4. per-account feature matrix from the frozen configs (unknown coverage stays blank, not False).
#    analyze_signals_v2.py --include-account-features exports the same observations as long JSON; this
#    builder writes the wide CSV the trainer reads and carries firmographic columns through.
$V scripts/build_feature_matrix.py --input accounts_sources.csv --keywords keywords.json --tools tools.json \
   --job-roles roles.json --carry industry,numberofemployees --output features.csv
# 5. train + score every row + freeze reference + export replay contract
$V scripts/train_scorecard.py --input features.csv --out-dir runs/v1 --mode lift \
   --coverage-cols coverage__website,coverage__jobs   # auto-detected when columns start with coverage__
```

`collect_sources.py` drops job openings first seen on or after a row's `known_at` (close date minus
90 days from the HubSpot helper). Website text is current copy; it carries `retrieved_at` and is
not point-in-time. For a leak-free website backtest, add Wayback copies from before `known_at`
as separate rows with `split=validation`, as the Prove niche-signals audit did (31% coverage there).

## Artifact bundle (`out_dir`)

| File | What it is |
| --- | --- |
| `preprocess.json` | Raw → binned feature transforms (quantile edges, category → bin maps). Learned on fit rows only. |
| `specs.json`, `model.json` | Intercept, scale, points per feature bin, optional calibrator arrays and tier cuts. The scorer reads these. |
| `training_set.csv` | Fit rows with raw and binned columns and `__Y__`. Needed by the explainers. |
| `points_table.csv`, `scorecard_explainer_binned.csv`, `scorecard_explainer_raw.csv` | The readable scorecard: every bin, its points, n, rate, historical lift, reference flag. |
| `feature_summary.csv` | Per feature: beta, IV, |beta|×IV, mean absolute points on validation. |
| `model_lift.csv`, `bucket_report_model.csv`, `storytelling.csv`, `decile_lift.csv` | Validation-split precision and lift at the top 10%, per-predicate lift/WOE/intrusion, deciles. Split is stratified random unless you pass a `split` column; treat as exploratory. |
| `tier_lifts.csv`, `gate_and_tier_meta.json` | Propensity mode only. |
| `scores.csv` | Every input row: points, probability, percentile, grade, top 5 drivers, row_role (train/holdout/unlabeled), status, miss_reason. |
| `reference.json` | Frozen sorted fit-row scores (scaled logits) with model id, population and `frozen_at`; grades for new rows use this, never the batch. |
| `model_contract.json`, `contract_sample.json` | Replay-scorer `Model` for `scoring_contract.ts`: one weight (1.0) per feature, intercept pre-multiplied by scale, `points_by_feature` for the Play to turn a row's bin into the observation value. Score = scaled logit; `reference.json` holds the same quantity. `scripts/tests/contract_check.ts` replays the sample rows through the real TypeScript scorer. |
| `run_meta.json` | Counts, label source, input hash, validation metrics, refusals overridden, completion state. |

Batch replay from a bundle, no retraining:

```python
from scorecard import ScorecardRunner
runner = ScorecardRunner.from_dir("runs/v1"); out = runner.score(raw_df)  # raw_points, p_model, breakdown
```

`overrides.json` in the bundle (`{"feature": {"bin": points}}`) replaces points for named bins at
scoring time and is annotated in the explainers. Any override is a new model version.

## What the Prove run looked like, for calibration of expectations

One row per Salesforce account; ~30 website keyword flags, industry and employee count; label = a
non-renewal opportunity in the last two years won with ACV over baseline. Propensity mode, 340
validation rows, base rate 13.8%, top-10% precision 44% (3.2× lift), AUC 0.69. Tiers A and B held
1 and 4 accounts. Features were current website copy scored against historical outcomes; the later
pre-close audit showed several of the strongest flags were post-purchase artifacts. Report that
class of risk in every run that lacks point-in-time sources.

## Tests

`.venv/bin/python scripts/tests/test_scorecard.py` runs synthetic known-answer checks: lift points
follow prevalence, propensity fits and learns tiers, the CLI round-trips through `ScorecardRunner`
with identical points, the contract weights reproduce a row's points, and propensity is refused on
small data. Keep customer cases out of the skill.
