# Create an artifact-backed scorecard

Build scoring from explicit raw inputs, saved preprocessing and model artifacts, one deterministic scorer, and explanations derived from the same contributions. Reproduce the requested customer's approved outputs; do not transplant another customer's weights, thresholds or feature requirements.

## Build the scoring path

1. **Define the input row.** Resolve account identity and preserve source evidence, dates and coverage. Specify required raw fields, types, units, unknown values and the decision cutoff. Keep fit inputs separate from activity and outcomes. Choose fields for the defined decision rather than copying another model’s inputs.
2. **Freeze preprocessing.** Save raw-to-feature mappings, categorical/numeric bins, missing/unseen-category handling and transforms. Apply the identical artifact to training, batch scoring and a new singleton account.
3. **Save the model.** Store feature/bin points, intercept, scale, optional calibration, fixed reference cutoffs and explicit overrides. Keep a content hash for every artifact. Any approved extraction, override, grading or routing change creates a new full-system version.
4. **Score once.** Load the artifacts into a shared pure runner. Compute per-feature contributions, total points and model output. Calibration and percentile/tier assignment are separate transformations. Both the Play and offline report consume this result; neither recomputes a competing formula.
5. **Explain the actual result.** Join each contribution to its raw value, chosen bin, source and applied override. Build account drivers and the readable scorecard from the same model artifacts. Show how points reconcile and distinguish points, probabilities, percentiles, tiers and routing decisions.
6. **Wrap collection around scoring.** A Play resolves the input identifier, collects or reuses evidence, applies the frozen feature definitions and calls the runner. Keep enrichment receipts separate so rescoring does not repurchase data. Export every input row, including unknowns and errors.
7. **Promote explicitly.** Separate fit, engagement, expected value and routing policy. Use approved output parity and the customer's decision-specific acceptance evidence before replacing the incumbent. Keep the old artifact bundle for audit and rollback. See the testing contract; executable evals are maintained separately.

## Keep artifacts and outputs consistent

Use one preprocessing specification, model definition and contribution breakdown across scoring, explanation and reporting. Define override precedence explicitly. Freeze calibration and reference cutoffs separately from raw points. A probability, percentile and routing tier are different outputs; return only those supported by the approved definition.

A readable account export includes `account_id`, raw feature values, chosen bins, per-feature points, total points, model output, calibration/reference versions, requested percentile/tier, evidence coverage and routing reason. The UI can show the primary score and a few drivers while retaining the complete breakdown for audit.

## Fail explicitly

Validate required artifacts and return explicit errors or unknowns when they are missing. Avoid silent failures in explanations or grading. A saved-output snapshot is a compatibility target, not independent evidence of predictive quality.
