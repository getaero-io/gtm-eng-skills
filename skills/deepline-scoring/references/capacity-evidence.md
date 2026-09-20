# Staff and operational volume: measurement boundaries

## Google Maps can supply context, not a staff or ticket census

Public Places data provides business identity, location, hours, rating and userRatingCount. It does not expose employee count, CSR count, calls handled or support tickets. A place is not necessarily the corporate parent; deduplicate locations, departments, duplicates and service-area listings before aggregation.

Places returns at most five reviews sorted by relevance. They are not a complete chronological sample. Do not derive review velocity or complaint frequency from those five. If permitted by applicable storage/licensing terms, repeated aggregate counts measure NET review-count change (deletions also occur). A licensed chronological corpus supports review trends, still not ticket volume. Do not assume a third-party scraper removes Google licensing obligations.

Popular times use relative physical-visit activity, not absolute traffic. They are especially weak for businesses that perform work at customer sites. No multiplication of popular-times bars or review counts into employees, callers or tickets.

With owner-authorized Google Business Profile access, CALL_CLICKS measures clicks on the profile call button, not answered calls, unique callers, completed calls or all inbound calls. The Business Profile Performance API uses OAuth business.manage authorization. This is private authorized data, not available for arbitrary prospects. Availability in Google's API does not establish a Deepline connector exists; inspect the live catalog before promising one.

## Preferred evidence hierarchy

| Need | Better evidence | Report as |
| --- | --- | --- |
| Total team size | Dated company disclosure, authorized HR roster, licensed company headcount with scope | Reported count/range with date; reconcile contractors and acquired brands |
| CSR / dispatch team | Authorized role roster; named current employees on team pages and licensed profiles | Deduplicated observed-person lower bound; title vocabulary is NOT a count |
| Call volume | Authorized telephony or call-tracking logs, same business and period | Separate attempts, answered calls, callers, transfers, outbound and spam |
| Tickets | Authorized helpdesk export | Distinct tickets created per period; not messages, threads, calls or resolved backlog |
| Booking workload | Authorized FSM/scheduler records | Separate appointments, completed jobs, cancellations and repeat visits |
| Prospect-only demand context | Location count, hours, dated review trends, jobs, service mix | Observed features; operational volume unknown |

## Estimation gate

No universal review-to-job, job-to-call, or calls-per-CSR multiplier. A speculative scenario must be labeled as user-supplied assumptions, not a measured estimate. Do not fill an unknown count with zero.

To develop an estimate, join consenting customers' dated external features with actual headcount/call/ticket outcomes. Separate vertical, geography, season, parent/location and channel mix. Freeze before temporal and parent-isolated holdout evaluation. Compare against a simple segment baseline; report prediction intervals, interval coverage and error by segment. Abstain outside the training population or where intervals are not useful. Set business error tolerances before model selection. The current skill has no calibrated model.

Required output: metric_name, unit, entity_scope, period_start/end, value_or_range, evidence_type (measured/reported/observed_lower_bound/estimated/unknown), source, retrieved_at, assumptions, uncertainty, calibration_version. Unknown Maps-derived employee and ticket counts must remain null, with the reason explicit.

Acceptance checks: five relevance reviews cannot become monthly review volume; 100 CALL_CLICKS cannot become 100 answered calls; a 20-title roster cannot become 20 employees; a multi-location chain must not duplicate parent headcount; 0 indexed jobs cannot become 0 staff; no model version means no calibrated estimate. Test these as downstream integration fixtures before activation.

Sources: [Places fields and review limits](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places), [popular-times methodology](https://support.google.com/business/answer/6263531?hl=en), [Business Profile performance metrics](https://developers.google.com/my-business/reference/performance/rpc/google.mybusiness.performance.v1), [OAuth access](https://developers.google.com/my-business/content/implement-oauth).
