# Website evidence in account scoring

Read this for account-fit or propensity work, including Salesforce account rescoring. Website-language features are a required layer alongside firmographics. The output must show what was collected, which concepts matched each account, and how those features enter the score. If collection is unavailable, preserve unknowns and deliver the baseline separately; do not silently call it the full model. Exact replay of an existing approved model may keep its inputs, but must disclose this missing layer and evaluate it as a separately versioned candidate.

## Collect relevant pages, then define concepts

Resolve the account domain and Salesforce Account ID. Use the same page-selection recipe across accounts, covering the homepage plus relevant product, use-case, pricing, customer and developer/help pages within the approved budget. Follow evidence gaps rather than imposing an arbitrary page count. Retain page URLs, source bodies/hashes, page roles, publication/availability/retrieval dates and collection outcomes. A company description, industry taxonomy or generated summary does not replace the website corpus.

Discover vocabulary from the discovery accounts without labels, review aliases, and freeze the concept catalog before evaluation. Include both product-specific language and general operating concepts:

| Family                        | Candidate website language                                                                     | Feature to verify                                                                            |
| ----------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Workflow or pain              | Account opening, invoice reconciliation, appointment scheduling, manual approvals              | The account operates or needs the named workflow, rather than merely selling advice about it |
| Billing model                 | Usage-based billing, metered billing, per seat, subscription, transaction fees, take rate      | How the account charges, separately from what its software can help customers charge         |
| Revenue type                  | Recurring revenue, one-time purchases, advertising, services, commissions                      | The account's supported revenue streams; allow multiple values                               |
| Customer model                | Sell to businesses, enterprise customers, consumer checkout, merchants, resellers, marketplace | Evidence-backed B2B, B2C, B2B2C, marketplace or mixed model; do not force a binary label     |
| Operating complexity          | Multi-entity, multi-currency, channel partners, locations, high-volume transactions            | The account's operating footprint and complexity                                             |
| Product-specific requirements | Regulatory programs, technical integrations, implementation constraints                        | Requirements relevant to this product and cohort                                             |

These are discovery prompts, not a seed list of universal positive weights. Finance terms belong only where relevant. A billing-software vendor saying “support usage-based billing” does not prove it bills its own customers that way. “Enterprise” alone does not prove B2B. Review speaker, entity, negation, historical context and buyer-versus-seller language. Keep the raw lexical observation separate from the adjudicated business trait.

## Materialize one account-level feature table

Preserve every requested Account ID, including unlabeled/open accounts and accounts with source failures. For each account/concept/source, export:

- stable account ID/domain and concept definition/version, aliases and source family;
- lexical value, matched terms, exact quotes and URLs, including counterevidence;
- source coverage/status and links to retained date/provenance records;
- reviewed interpretation, entity role, confidence and review reason;
- model role (`scored`, `display_only`, `candidate`, `gate`), encoding, coefficient/approved points and contribution, or an explicit exclusion reason.

The analyzer's `--include-account-features` option supplies the complete lexical observations in `account_features[]`; it does not supply semantic adjudication, model weights or verified deployment. Key a row by `(account_id, family, category, signal, source)`. Repeated aliases/pages still produce a single binary feature. Its evidence is complete and independent of `--evidence-limit`, which only limits cohort evidence samples. It exports accounts in the selected partition; run each required partition and reconcile IDs with the full scoring population.

Values: `1` means an affirmative lexical mention, `0` means no affirmative match in the successfully collected source, and `null` means unknown coverage without a positive match. Partial collection may establish a positive observation but cannot establish a nonmatch. A zero is not proof that the business trait is absent. Review wrong-entity and vendor contexts before converting lexical observations into business-model features. Missing dates, URLs or attribution must remain explicit rather than being supplied by a model guess.

Keep `scoring_eligible:false` until the required context/availability checks and approved model mapping are supplied. Join by Account ID, not company display name. Do not use won/lost labels, opportunity notes or score explanations as predictor inputs. Discovery documents supply vocabulary; the sample report's prose and example weights are not an extraction corpus or customer-independent scoring model.

## Use the features in the actual scorer

For a new or revised account model, compare firmographics alone with firmographics plus website concepts. Inspect feature inclusion before final scoring: a configured phrase with a hit but no model mapping must appear as `candidate`/`display_only` with a reason, never disappear. A phrase-backed scoring delivery requires mapped website features and an account contribution export. If no website feature has earned inclusion, label the result a firmographic baseline and report the attempted candidate and its evidence; do not add arbitrary points just to populate the layer.

Use learned coefficients from the training split or customer-approved heuristic rules. Prevalence ratios and raw mention counts are not weights. Preserve the intercept, transforms, missingness policy and any link/calibration function so account contributions reconcile to the model output. Group synonyms and correlated concepts to avoid awarding points repeatedly for the same underlying evidence. Distinguish match flags, score points, grades and calibrated probabilities.

Show at least one observed positive match, a reviewed nonmatch and an unknown-source account through the full path: retained page → extracted feature → reviewed interpretation → scorer input → contribution → final account score. Freeze independent expected values before testing. Compare ranking at the actual rep capacity against the incumbent and firmographic baseline using an untouched time/parent split. A better extraction table alone is not proof of higher win propensity.

## Optional customer-provided competitive evidence

Include competitive evidence only when the customer requests it and supplies or authorizes an available source. It is optional and must not gate website collection, feature extraction or scoring delivery. First identify what the dataset actually measures and join it to the correct account/product/entity and dates. Retain vendor/source record IDs and provenance. Keep these separate:

| Competitive feature               | Supporting evidence                                                                                      | Interpretation boundary                                                  |
| --------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Brand mention                     | Website copy names a competitor                                                                          | Lexical mention only, not installation or buying intent                  |
| Verified incumbent use            | Attributed customer case study, corroborated deployment record, or approved current first-party evidence | Category fit may be positive while near-term switching likelihood is low |
| Replacement or migration          | Dated evaluation, migration docs or explicit replacement evidence                                        | A potential change event; historical migration is not current intent     |
| Dissatisfaction or limitation     | Attributed current complaint tied to this account's use                                                  | A named pain hypothesis; an anonymous review is not an account fact      |
| Partner/integration               | Official partnership or supported integration                                                            | Not equivalent to customer use, direct competition or dissatisfaction    |
| Account sells a competing product | Product and buyer overlap verified at the account's scope                                                | Separate competitor-company eligibility from use of a competing tool     |

Do not give every competitor mention a bonus or penalty. Evaluate incumbent use and displacement evidence separately, with possible interactions such as incumbent + relevant pain + recent migration signal. Freeze the relationship classifier and weights before holdout evaluation. Internal competitor intelligence learned during a sales opportunity belongs in the permitted engagement/timing view unless its pre-decision availability is proven; it must not leak into historical pre-contact fit.

When competitive evidence is included, compare that candidate separately with the website-feature model. Report feature/coverage changes, top-account rank movers, precision at capacity and uncertainty. Keep new competitive features experimental until that comparison supports promotion. Record collection/extraction versions so the same approved model can be rerun without purchasing the evidence again. Report generation does not authorize Salesforce writes or replacing the live model.
