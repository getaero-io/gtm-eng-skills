# Prevent overfitting and leakage

## Define the decision

Cold-account targeting, engaged-deal forecasting and customer-value estimation have different admissible features and targets. Set the scoring date BEFORE collection. Before close is not before scoring.

Activity counts, champion fields, visits, notes, demo requests and provider installations can be downstream of engagement or purchase. They may be legitimate later-stage features only when available at that later decision and evaluated for that target. Never transfer their apparent lift into cold ICP scoring.

Public content is time-varying too. A current re-scrape cannot retrospectively validate historical prediction. Preserve publication, provider first-seen, retrieval and known-at timestamps separately. Bulk import timestamps are not event times. Use a conservative latest-known-at for all source material in a validation row.

## Separate discovery from confirmation

- Split by time and buyer/parent before choosing phrases. Resolve parent mappings externally; domain equality is insufficient.
- Mine phrases without outcome labels. If labels inform refinements, disclose discovery fitting.
- Freeze aliases, extraction rules, config hashes, cohort rules and the comparator baseline.
- Keep the validation partition untouched. Repeated peeks or revised configurations consume it.
- Lookalikes never count as won; dual-outcome accounts require a defined acquisition/renewal cohort.
- Evaluate incremental performance, calibration and operational utility on a later cohort. A descriptive script does not do this automatically.
- Correct the full tested hypothesis family and log all searches, including negative findings. BH/BY for one invocation cannot correct undisclosed repeated experiments.
- Account-level Fisher tests are not valid cluster-adjusted evidence for correlated subsidiaries. Use grouped bootstrap/model evaluation in a dedicated analysis.
- No fixed n=3 or n=20 establishes power. Plan around baseline, useful effect, uncertainty and class imbalance.

## Missingness and selection

Analyze source coverage by label, size, region and vintage. Restrict descriptive denominators to observed source records and report exclusions. This does NOT eliminate completeness-selection bias. A more thoroughly worked won account often has more data.

Do not require won companies to have more job listings as a quality check. Conditioning on later funnel stages changes the population and can introduce collider bias.

Lost reasons are diagnostic, not automatic targeting rules. Unresponsive can mean poor contact data, timing, message, channel, execution or fit. Verify the correct CRM property and interview evidence before changing ICP.

Never manufacture weights from a raw ratio. Confirm predictive usefulness separately from causality; neither lexical matching nor observational lift establishes causal effect.
