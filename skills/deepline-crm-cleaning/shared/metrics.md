# Metrics

Select metrics for the requested outcome. Keep candidates, verified facts, proposals, and applied changes separate.

Record definition, numerator, denominator, population, exclusions, window, source, coverage, owner, and target for each metric. New receipt metrics also need measurement state and reporting cutoff.

Use `not_measured` for unavailable data. Use `zero_denominator` for an observed ratio with no eligible records. Both have null values.

| Outcome                       | Measurement                                                                                                                                                 |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Usable contacts               | Canonical contacts with all required valid, current fields / eligible canonical contacts.                                                                   |
| Enrichment coverage           | Entities with all requested useful fields verified / eligible canonical entities. Report starting and newly completed coverage.                             |
| Field completeness            | Present values / eligible records for that field. Measure accuracy and freshness separately.                                                                |
| Duplicate burden              | Excess active records in independently reviewed duplicate clusters / scoped active records. Show adjudication coverage and unresolved candidate burden.     |
| Duplicate incidence           | Confirmed newly created excess records / observed creation attempts. State window and scale.                                                                |
| Same-domain collision         | Domain groups containing multiple accounts / eligible nonconflicting company-domain groups. Use exact hosts for hosted tenants. This is not duplicate rate. |
| Prevention coverage           | Creation attempts checked by an enforced guard / all observed attempts, including blocked, held, and bypassed attempts.                                     |
| Guard errors                  | False accepts, false blocks, and unresolved holds against independently reviewed creation attempts. Report rates and counts.                                |
| Domain-stage coverage         | Inputs attempted or reused at each required stage / eligible inputs, including missing domains.                                                             |
| Legal-role coverage           | Inputs with verified legal roles / eligible entity inputs. Show failures and unresolved roles.                                                              |
| Employment freshness          | People with accepted current-role evidence within policy / eligible people. Score employer, title, and false-change errors separately.                      |
| Hierarchy precision           | Correct independently reviewed predicted typed edges / independently reviewed predicted typed edges. Show adjudication coverage.                            |
| Hierarchy recall              | Correct found reference edges / complete known reference edges. An unknown child total cannot support recall.                                               |
| Complete-path accuracy        | Fully correct typed paths / independently reviewed reference paths. Include effective-time correctness.                                                     |
| Parent coverage               | Identified parent slots / requested slots. Separate explicit no-applicable-parent states from unresolved slots.                                             |
| Domain candidate precision    | Relevant independently reviewed candidates / independently reviewed proposed candidates. Show independently reviewed / all proposed candidates separately.  |
| Domain candidate recall       | Found reference domains / complete known eligible portfolio domains. Otherwise report not measured.                                                         |
| Unsupported parent assertions | Unsupported assertions / all parent assertions. Include counts and correct-edge recall to expose excessive abstention.                                      |
| Added signal value            | Newly correct relationships beyond the frozen baseline. Also report added false positives and overlapping evidence families.                                |
| Signal collection quality     | Complete, partial, failed, unavailable, reused, and stale attempts / original eligible source-input attempts.                                               |
| Confounder errors             | False ownership links / independently reviewed cases in each relevant shared-service, franchise, clone, or divestiture class.                               |
| Domain discovery cost         | Deepline cost / newly verified useful domain or entity relationships. Include latency and no-result charges.                                                |
| Association preservation      | Required prior links verified after repair / required prior links. Also report unexpected added and lost links.                                             |
| Repair success                | Logical actions passing all postconditions / frozen due actions. Include deferred, failed, and abandoned actions; count retries separately.                 |
| Repair latency and backlog    | Issue age and completion-time distributions by action, source, and unresolved reason.                                                                       |
| Recurrence                    | Repaired entities with the same defect again / repaired entities observed during the stated window.                                                         |
| Routing efficiency            | Correct assignments, assignment latency, response-SLA attainment, owner conflicts, and distribution fairness under the routing policy.                      |
| Redundant outreach            | Audited redundant events / audited outreach events. Keep complaints separate.                                                                               |
| Useful cost                   | Authorized Deepline cost / newly useful canonical entities or verified repairs. State reuse and no-result charges.                                          |

## Compare equivalent populations

Keep a fixed baseline separate from the current record set. Show deletions and exclusions; do not count them as repairs. Add numerators and denominators before calculating aggregate rates. Do not average subgroup percentages.

Report sample rates unless the sampling design supports population estimates. Related records are not independent samples. Repeated tests on one sample add no independent evidence.

Measure only defined, observed fields. An unknown property is not blank. An unqueried relationship is not absent. Show schema and scan coverage beside field and hierarchy measures.

Group defects by writer, version, age, account unit, region, lifecycle, and missing fields within scope. Compare defect rates with write volumes. Keep review signals separate from verified record classes.

Separate requested, admitted, rejected, retried, returned, and distinct records or calls. Use actual budget accounting. A rejected request does not prove budget exhaustion.

Count website and legal-page attempts separately. Report transport failures, incomplete reads, truncation, and category overlap. Do not count copied page flags as new attempts. Use each source's actual observation window.

Identify hierarchy edges by source, target, type, and time. Declare the interval-matching rule. Keep unknown dates and complete-path accuracy separate from edge scores.

## Check outcome claims

For each adopted outcome claim, record source, definition, needed data, test, result, and limitation. Mark unavailable routing, funnel, meeting, organization-health, and field-governance measures unmeasured or unsupported.

A complete requirement list does not mean each outcome passes. Attribute gains only with a supported comparison.

For URL repair, separate invalid values, affected records, proposed replacements, simulated defects, applied writes, and rejected provider values. Compare guarded attempts with all known writers before claiming full prevention.
