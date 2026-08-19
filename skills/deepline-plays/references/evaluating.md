# Evaluate strategy concepts

Use this when a route will be reused, a skill or scaffold changed, or someone
claims a route is cheaper, broader, or more reliable. A live Play's pilot
chooses a route for that run. An evaluation tests whether the same strategy
concept holds across a frozen set of cases.

## Do not collapse two decisions

| Decision      | Unit                       | Evidence                          | Output                                 |
| ------------- | -------------------------- | --------------------------------- | -------------------------------------- |
| Run score     | route on a row/partition   | live receipts in one Play         | selected waterfall and route scorecard |
| Strategy eval | concept across fixed cases | one comparable run score per case | promote, recovery-only, or reject      |

A concept names information geometry: `structured company index`, `registry
document`, `official leadership page`, `public profile`, or `first-party event
feed`. It does not name a vendor. Two transports that reach the same terminal
corpus are one concept for consensus, though either may still be useful as an
operational fallback.

## Freeze the evaluation

Use the same contract, acceptance verifier, rows/partitions, and credit ceiling
for every candidate. Stratify a small evaluation set rather than picking easy
rows after seeing results:

- normal cases, where the requested fact should be available;
- sparse or niche cases, where a broad public or registry route matters;
- likely misses, which reveal whether the route returns an honest absence;
- collision-prone cases, when entity identity is the risk.

Keep source/date snapshots when freshness or a public corpus can move. A route
may improve only an unresolved gap; do not re-buy completed rows to inflate its
apparent coverage.

## Read the scorecard in order

`runSearchExperiment` returns `scorecard`, `costCoverageFrontier`, `attempts`,
`adaptations`, and `leverage`. Export them with the completed run. Decide in
this order:

1. Reject unsupported, contradictory, stale, or cohort-failing output.
2. Compare verified coverage and the failure slices, not raw candidate count.
3. Compare marginal observed Deepline credits and calls for the additional
   verified rows. Unknown credit remains unknown.
4. Use latency and adapter failures as reliability diagnostics. Repair an
   adapter seam before treating it as a source miss.
5. Retain a route only when it adds unique verified coverage or a distinct,
   useful recovery path.

Do not average these into a model-generated scalar. Truth gates decide whether
a row counts; economics break ties between valid choices.

## Run the right-sized eval

For one live job, the shared comparison rows plus untouched holdout are the
eval. Preserve the scorecard dataset next to the final result dataset and
report the winning and dormant route IDs, coverage, cost basis, adaptations,
and unresolved reasons.

For a repeated customer job, run the same Play contract against the frozen
case set. Compare each concept's scorecard rows and list the cases where its
coverage was unique, absent, or invalid. Promote a default only if it clears
the hard gates on the intended cohort; otherwise keep it as a gap-only route.

For a change to this skill in the Deepline repository, run a focused agent eval
before reporting the improvement. Use the repository's `evals` contributor
skill for the current harness and canonical results viewer. Compare candidate
and baseline from the same SHA, model, prompt, cases, credit policy, and run
count. A transcript anecdote is a diagnostic, not an evaluation result.
