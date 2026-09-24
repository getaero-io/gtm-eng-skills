# Historical warm-intro audit (aggregate only)

Run: 2026-09-23. Offline, read-only analysis of retained historical output snapshots. No sends, providers, database changes, or external requests. Private audit code and raw snapshots are retained outside the repository. No personal names, emails, profile URLs, source quotes, or record IDs are included here.

## What was evaluated

- Historical email-inspired Python evaluation file: 20 test functions. Its module description narrates 16 intro examples. These are not 16 independently labeled evaluation rows.
- Expanded account workflow: 125 accounts, 1,168 target contacts, 2,339 retained top-three path rows. 971 targets have a path; 197 do not.
- Actual ask review: 4 draft asks. All four uniquely match a retained work-overlap route in the same snapshot; all four have moderate requester-to-connector warmth; all four are unapproved and marked for organizer edits. This linkage used account and names only inside a single known snapshot, not a proposed production identity resolver.
- Dinner workflow: 345 enriched target rows, 123 with paths, 271 candidate paths; 222 targets have no retained route. Best routes: 34 company overlap, 76 current target-company connections, 7 first-party relationships, 6 direct requester connections.

## Executed checks

The original account-output invariant validator passed. It checks duplicate target identities, connector exclusion from account target lists, maximum three distinct connectors per target, contiguous ranks, sorting, evidence fields, investor coverage, and same-function constraints/caps for large-company work overlap. It covers 83 verified investor-contact records and 1,487 account-investor edges.

Independent formula recomputation matched all 2,339 scores to 0.011 tolerance. Formula: `0.72 * min(edgeA, edgeB) + 0.18 * sqrt(edgeA * edgeB) + 0.10 * max(edgeA, edgeB)`.

These are structural consistency checks, not validation of source truth, relationship quality, successful introductions, or model calibration.

## Findings that must change the reusable skill

1. **Readiness must consider both edges.** The legacy readiness label only checks requester-to-connector warmth. Four rows say strong warm intro, but two have target-edge scores below 55. Separate path strength, evidence confidence, and actionable readiness; require both relationships and permission/availability checks.
2. **Confidence is currently easy to misread.** 976 rows labeled high confidence have an unverified requester edge. There are 1,524 unverified paths, 811 confirm-relationship paths, and 4 strong-labeled paths. Never present source/profile confidence as end-to-end relationship certainty.
3. **A profile URL is not a connection.** The historical relationship helper treats a LinkedIn URL or connection date as first-degree evidence. Require explicit owner-scoped imported edge provenance. Generic profile enrichment must never manufacture a relationship edge.
4. **Historical test fixtures contain assumptions.** Several tests invent or assume target-company employment to explain a known intro, then assert same-company scores. One example tests the connector's current employer rather than the actual destination of the narrated intro. Another multi-hop test scores a single contact rather than validating both directed edges. Use these only as heuristic regression examples after anonymization and correction, not observed outcome labels.
5. **Calls and messages need semantics, not just counts.** Legacy calls gain a strong score without date decay; email participant counts do not necessarily establish reciprocity, personal familiarity, willingness, or a real introduction. Preserve timestamps, participant validation, interaction direction, and outcome types; distinguish intro-language detection from intro completed.
6. **Large-company overlap is a candidate lead.** Existing safeguards cap same-function overlap and reject cross-function overlaps, but neither same function nor overlapping dates prove familiarity. Same-school, same employer in different years, investor portfolio, social mentions, and common interests likewise cannot establish known relationships.
7. **Ask drafting and transmission remain separate.** The four asks are draft artifacts, not proof that the connector accepted, target responded, or meeting occurred. Every retained path has a blank selected-intro field. No outcome-complete evaluation dataset was present in these inspected CSVs.

## Baseline distribution

| Path type | Rows |
|---|---:|
| Dated work overlap | 1,159 |
| Shared investor | 542 |
| Account-internal LinkedIn | 417 |
| Education overlap | 212 |
| Social mention | 9 |

## Evaluation recommendation

Add deterministic fictional regressions for identity ambiguity; LinkedIn profile versus owner-scoped edge; source-only evidence; both-edge bottlenecks; stale calls; one-way bulk mail; dated same-employer and same-team overlap; large-company false familiarity; investor portfolio versus individual partner relationship; connector equals target; contradictory/no-consent evidence; duplicate sources; and two-hop versus longer routes.

For a genuine outcome evaluation, build a private dated table keyed by request and route with the ask timestamp, available-as-of evidence, connector confirmation/decline, intro actually sent, target reply, meeting completion, and censored/unknown outcome. Split by time and target/account, hold out outcomes from prompts/features, compare a baseline on the same candidate universe, and report recall@3/ranking only when relevant-route labels exist. Measure reply/meeting rates only over comparable observed sent asks; do not count unsent drafts as failures. Report small-sample uncertainty and selection bias. Do not fit weights to the four hand-selected drafts.

**Conclusion:** available private assets support structural regression and historical ask-pattern checks. They do not support an accuracy percentage, probability calibration, measured uplift, or a claim that new factors improve real-world intro outcomes.

## Delivered behavior checks

`python3 scripts/check.py --repo /path/to/gtm-eng-skills` exercises baseline parity, both-edge holds, unknown willingness, explicit decline, missing and non-overlapping history, future evidence, wrong-subject evidence, duplicate paths, reversed intervals, HTML injection and the actual ask-thread CSV loader. All inputs are fictional. These checks validate behavior, not outcome accuracy.

Independent forward testing found a willingness flag could contradict a cited decline or ignore a newer decline. The wrapper now binds willingness values to evidence, honors the latest dated record, and holds same-day conflicts. Relationship confidence is also bound to its reviewed evidence value. Seventeen offline checks passed, along with ten existing ask-drafter tests. Desktop/mobile browser checks covered search, filtering, top-three cards, details, empty state and no horizontal overflow or JavaScript errors.

The four historical asks were not passed through the new as-of wrapper: two lack precise retained employment intervals and none of the inspected rows retain source observation dates. The aggregate audit is the real-data evaluation delivered; no missing dates were fabricated.

## Known introductions and CLI receipts

The retained email-derived historical test module was rerun: 19 passed and one expected failure for unsupported `get` company-prefix normalization. Some fixtures contain assumed roles or dates. Treat these as historical pattern regressions, not a verified set of introductions made through the CLI.

For each claimed CLI introduction, retain a private source receipt with the run/message ID, requester, connector, target and event time. Separate an ask sent to the connector from an introduction actually sent to the target. Dry runs, drafts, approvals and successful enrichment runs are not introduction outcomes. Deduplicate retries by the provider message or event ID. Keep replies and completed meetings as separate outcomes; unknown is not false.

Evaluate known routes using the candidates and evidence available before the ask. Do not add facts learned from the successful introduction to the scoring input. Keep the outcome receipt outside the feature set and split evaluation by time and target account. An observed introduction can label a known route, but it does not label all other routes as failures or establish a conversion denominator.

No verified CLI introduction receipts were located in the retained scoring and draft artifacts inspected for this revision. Those outcomes remain unevaluated until the source run or message records are supplied. Do not count the 871 unapproved drafts as sent asks or introductions.
