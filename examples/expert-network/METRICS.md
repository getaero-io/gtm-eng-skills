# Maximize activated and retained experts

**Product objective:** grow the number of experts who create useful work and keep coming back. A full recruiting queue is an input, not success. Profiles found, verified emails and Lemlist enrollments do not count as activation.

## North-star definition

**Retained contributing experts, trailing 28 days (RCE28):** distinct experts with at least one accepted production contribution in `[as_of − 28 days, as_of)` and at least one *different* accepted production contribution before that window. This measures returning contributors across periods, not repeated edits or several tasks completed in one first burst.

**Activated:** an expert's first human-accepted production contribution. Practice tasks, logins, onboarding completion, campaign membership and synthetic artifacts do not count. A contribution must be a real, distinct artifact such as a scenario, task or evaluation rubric, accepted against the applicable quality criteria. Revisions of the same artifact count once; withdrawn acceptances are excluded and affected metrics restated.

**Retained:** activated experts who return to produce accepted work in a later observation period. RCE28 is the current operating count. Separately track cohort retention: the fraction of activated experts with another distinct accepted contribution in days `[30,60)` after activation, among activation cohorts whose full 60 days have elapsed. Never treat immature cohorts as failures.

Report RCE28 weekly with newly activated experts in the last 28 days and mature-cohort retention alongside it. RCE28 can grow through acquisition while cohort retention deteriorates, so never present the count alone. Two accepted artifacts within the expert's first 28-day window show early repeat contribution, but do not yet satisfy RCE28 if neither predates the current window.

These are proposed product definitions, not historical facts or configured incentives. Review the 28/30/60-day windows once real task cadence is known. Lawyers and consultants may have different assignment cycles; segment the same definitions by vertical, specialty, source and activation cohort.

## What every state contributes

| Engine state | Contribution to the objective | Primary submetric | Time / diagnostic | Intervention |
|---|---|---|---|---|
| discover | Supply relevant, distinct potential contributors | Discovery yield = unique identity-resolved candidates / raw returned profiles | Cost per identity-resolved candidate; unresolved identity age | Tighten sources when yield falls; do not fill the queue with duplicates |
| qualify | Select people able to create the required work | Domain-qualified rate = domain-approved candidates / completed domain reviews | Review turnaround; activation within 30 days by qualification cohort | Revisit criteria when approved people fail to activate; recruiting email-fit alone is insufficient |
| recruit | Turn fit into willingness to contribute | Interested rate = unique positive replies / uniquely delivered invitations | Reply within 14 days; suppression violations | Revise the real offer or channel if qualified people decline; enrollment is not delivery |
| onboard | Remove barriers before an expert can work | 7-day readiness rate = interested experts fully ready within 7 days / interested experts observed for 7 days | Prerequisite completion time; blocked reason | Resolve agreement, conflicts, training or availability blockers |
| match | Connect ready experts to suitable work | 7-day match rate = ready experts who accept an assignment within 7 days / ready experts observed for 7 days | Ready experts without suitable offered work; offer acceptance rate | Add relevant briefs or fix scope, capacity and compensation mismatch |
| review | Convert expert effort into useful production work | 30-day activation rate = newly ready experts with a first accepted production artifact within 30 days / newly ready experts observed for 30 days | First-pass acceptance; submission-to-decision time; revision cycles | Clarify briefs, support experts and unblock reviewers; never lower the quality bar to inflate activation |
| learn | Improve subsequent work and bring experts back | Mature 30–60-day repeat rate = activated experts with a distinct accepted artifact in days 30–60 / activated experts observed for 60 days | RCE28; accepted artifacts with observed use; next-opportunity availability | Offer suitable next work and act on feedback; absent usage evidence is unknown, not failure |
| waiting | Recover stalled relationships | 14-day recovery rate = waits resumed within 14 days / waits observed for 14 days | Age by blocker, owner and stage | Assign an owner; escalate overdue blockers; a new episode ID is not recovery without real progress |
| declined | Learn why people exit and respect their choice | Reason coverage = declines with a recorded reason / total declines | Decline rate by stage; unwanted re-contact incidents | Fix recurring avoidable causes; honor opt-outs; do not optimize by hiding declines |
| complete | Preserve learning and a useful next action | Handoff coverage = completed episodes with evidence and an owner-assigned next action or explicit pause / completed episodes | Subsequent repeat contribution | Follow through on next actions; episode completion does not mean activated or retained |

State transitions are observations, not proof of causation. Compare downstream activation and retention by source and qualification cohort before scaling a step.

## Submetric for every operating workflow

All rates use distinct experts, assignments or artifacts as specified, not event counts. The timing windows below are proposed operating defaults. `N/A` is required for a zero denominator; missing events mean `unknown`, never zero.

| Workflow | Primary measure and denominator | When / how well it is working | Owner |
|---|---|---|---|
| Define demand | Brief readiness = open briefs with specialty, rubric, approved scope and terms / open briefs | Ready experts have suitable work available; review weekly by specialty | World designer |
| Build pools / below-100 refill | Eligible unique additions / raw profiles returned; queue coverage = active candidate count / 100 | On a successful run below 100, add only remaining capacity; inspect why a bounded run stays short. Queue size is not expert success | Research ops |
| Resolve identity | Verified unique identities / identities reviewed | No duplicate expert IDs or unresolved identity promoted downstream | Research ops |
| Enrich expertise | Evidence completeness = candidates with source-linked specialty and experience evidence / candidates researched | Evidence is usable for domain review; record freshness and source, not just field fill | Research ops |
| Recruiting qualification | Current-role + employer + verified-email passes / completed recruiting checks | Higher later interest and activation, with zero suppressed enrollments; pass rate alone is not a quality score | Recruiter |
| Domain qualification | Approved task-fit reviews / completed domain reviews | Accepted first contributions validate the review; credentials and specialty are human-reviewed | Domain lead |
| Lemlist enrollment | Confirmed destination memberships / eligible new enrollment attempts | Membership readback confirmed; zero duplicate or suppressed additions; uncertain writes await reconciliation | Recruiting ops |
| Reach out | Unique delivered invitations / unique attempted sends | Campaign has real sender and offer; inspect bounces and complaints before scaling | Recruiter |
| Capture response | Interested experts / uniquely delivered invitations in a cohort observed for 14 days | Interest and declines are captured accurately; response time improves without unwanted contact | Recruiter |
| Onboard | Fully ready within 7 days / interested experts observed for 7 days | Agreement, conflicts clearance, orientation and availability are all recorded | Expert ops |
| Assess readiness | Practice-task passes / completed practice assessments | Practice feedback predicts production acceptance; practice completion never counts as activation | Domain reviewer |
| Match opportunity | Accepted assignments / offers with a decision or 7 elapsed days | More ready experts get suitable offers; report no-offer cases separately | Project lead |
| Create world/task | On-time submission = assignments submitted by agreed due time / assignments whose due time passed | Experts submit complete artifacts; exclude documented cancellations before due time and show them separately | Expert |
| Review and revise | First-pass acceptance = artifacts accepted at first review / artifacts receiving first review | Quality stays stable while review time and revision burden fall; preserve original review outcomes | Reviewer |
| Observe use | Usage coverage = accepted artifacts used within 28 days / accepted artifacts observed for 28 days | Join artifacts to real use; separately show acceptance among evaluable uses and missing instrumentation | Data ops |
| Maintain relationship | Next-opportunity coverage = activated experts offered suitable follow-on work within 14 days / activated experts observed for 14 days | Experts receive relevant opportunities; track early repeat acceptance and support-resolution time | Relationship owner |
| Settle and retain | On-time payment = payable items settled by agreed due time / payable items whose due time passed | Honor payment commitments; compare mature repeat rates with payment/support experience | Finance + expert ops |
| Pause or exit | Pause/exit requests honored within agreed handling window / requests whose handling window elapsed | Respect explicit pauses and exits; record reasons and prevent further unwanted contact | Expert ops |

For workflow health, show numerator, denominator, cohort dates, missing-event count and trend. Establish a baseline using the first four fully observed weekly cohorts; until then label performance as baseline-building. After that, flag a primary conversion rate below its previous four mature cohorts for two consecutive weeks for investigation, not an automatic verdict. Contractual due dates and suppression/duplicate violations trigger action immediately. No unsupported industry benchmark or automatic firing/rejection rule is introduced.

## Avoid blaming the expert for a supply problem

The headline metric and cohort-retention denominator include all activated experts, including those never offered a next task. Also show the repeat rate among experts actually offered suitable work and the percentage offered no work. This diagnoses demand, matching and availability problems without removing them from the product outcome. Report voluntary pauses/exits as a segment rather than quietly excluding them from retention.

Quality, payment timeliness, opt-outs and expert-reported friction are guardrails. Do not maximize invitations, task fragmentation, permissive acceptance or low-value repeat tasks to raise the metric. A second version of the same artifact is not a second contribution.

## Measurement contract and implementation status

The lifecycle CSVs lack cohort timestamps; the separate metrics event fixture demonstrates those calculations. Recruiting outputs support search and enrollment diagnostics only. **This package contains no production activation, retention or conversion measurements.** It is a metric specification plus a reproducible synthetic calculation, not a live dashboard or installed alert system.

Minimum production events: `candidate_discovered`, `identity_resolved`, `recruiting_check_completed`, `domain_review_completed`, `campaign_membership_confirmed`, `invitation_delivered`, `interest_recorded`, `expert_ready`, `assignment_offered`, `assignment_accepted`, `submission_received`, `artifact_accepted`, `acceptance_withdrawn`, `artifact_used`, `feedback_recorded`, `payment_due`, `payment_settled`, `wait_started`, `wait_resolved`, `pause_requested`, `pause_honored`, `declined` and `episode_completed`.

Every event needs `event_id`, `expert_id`, `occurred_at` (UTC), `recorded_at`, `source`, `is_synthetic` and the relevant artifact/assignment/episode/campaign ID. Preserve `artifact_id` across revisions. Capture actual external events instead of inferring them from pipeline states. Store first-ready and first-valid-acceptance timestamps once and retain corrections with audit history. Join recruiting profile identity to the stable expert ID explicitly; names are not join keys.

Deduplicate event IDs and accepted artifact IDs. Calculate time windows as half-open intervals with an explicit UTC as-of cutoff; label displayed reporting dates in America/New_York. Use event time, restate late/corrected data, exclude synthetic and practice records from production metrics, and retain missing evidence as unknown. Each submetric needs its stated events before it can be reported.

`metrics/calculate.py` demonstrates the north-star and activation/retention definitions on labeled synthetic events. `metrics/events.csv` is a fixture only. No provider calls, outreach or live workflow settings are changed by this metric layer.
