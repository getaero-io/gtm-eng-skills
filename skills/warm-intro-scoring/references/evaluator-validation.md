# Evaluator validation record

All examples in this record are fictional. These checks assess evaluator behavior, not intro success.

## Documentation RED → GREEN

Pressure scenario: an imminent demo, prior team investment and a product-owner demand for uplift. Two queries compare the same candidate sets; one has an unjudged route and post-cutoff evidence. Four asks were drafted, two sent, one replied, and one sent ask's observation window remains open.

The no-guidance control correctly held promotion, but reported:

> Reciprocal rank of first **known** relevant result, averaged over 2 queries | 1.00 | 0.75

> 1/2 sent asks received a reply (50%)

The first is a partial-label diagnostic rather than primary MRR. The second uses an immature denominator without knowing which ask replied. These failures motivated explicit eligibility rules in `evaluator.md`; the control did not demonstrate a tendency to approve deployment, so no such failure is claimed.

A fresh agent given the reference contract excluded the incomplete query, computed all three primary metrics as 1.0 on the single eligible query, and reported:

> Verified mature denominator: **unavailable** without dated sends, the fixed window, and observation dates.

> Fixed-window reply and meeting rates: **unavailable**.

It retained the temporal-leakage failure and declined an uplift claim despite deadline, sunk-cost and authority pressure. This is one control and one guided full scenario, not a five-repetition wording study or a statistically established agent-compliance rate. No behavioral-shaping wording comparison is claimed; the change is a metric eligibility reference contract.

## Reproduce the executable checks

Run the evaluator unit tests with the standard Python unittest runner from the repository:

```bash
python3 -m unittest discover -s skills/warm-intro-scoring/scripts -p 'test_evaluate.py'
python3 skills/warm-intro-scoring/scripts/check.py --repo .
```

The numerical fixture uses hand-derived ranking expectations. Tests exercise real parsing, metrics, gates and file output without provider mocks or paid calls. The demo dataset is synthetic and cannot establish predictive quality. See `evaluator.md` for human labeling, provenance and prospective trial requirements.

## Executed verification

The evaluator has 13 executable tests. Initial missing-module tests ran red before implementation; additional red tests preceded account clustering, separate scoring cutoffs, explicit-null split rejection and readable scorecard output. Fixed-window tests cover immature early replies, late replies, unknown outcomes and dated chronology. The complete repository run passed 129 tests and 78 subtests; the separate scorer suite passed 17 checks.

Independent adversarial review verified rejection of post-scoring features with timezone offsets, evaluated accounts outside the declared test split and declined ready paths. An outcome exactly at its horizon counted; one microsecond later did not. The reviewer identified the initially missing event-horizon rule; both contract and runner now enforce it.

Desktop/mobile browser checks passed for the two tables, expandable metadata, absence of page overflow and script errors. The fixture scorecard is explicitly insufficient evidence: one eligible query out of three and one complete account. Neither this fictional result nor the pressure-test pass is a real-world accuracy estimate.
