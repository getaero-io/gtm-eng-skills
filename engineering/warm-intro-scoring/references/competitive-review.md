# Warm introduction tools: feature review

Reviewed 2026-09-23. Research window: 2026-08-24 through 2026-09-23. This is a feature comparison, not a purchase ranking. Product descriptions below are vendor claims. They do not establish that a feature improves conversion or that a vendor is best in class.

## What the products add

| Product | Verified product documentation | Gap in this package |
| --- | --- | --- |
| Centralize | Account maps show buying committee coverage, missing stakeholders, team relationships, and next actions. | We rank people and paths. We need account coverage, committee roles, and a clear view of which required roles lack paths. |
| Connect The Dots | Scores interaction metadata, including recency and frequency. Two-way exchanges outrank a stale connection. It pools team networks and supports intro requests, drafts, and outcomes. | Our profile features estimate shared experience. They do not verify a current relationship on both sides of the connector. |
| The Swarm | Relationship strength includes employment overlap duration, shared area/domain, email, meetings, and LinkedIn connections. Users can edit their own relationship status. | We need explicit connector review, overlap duration sensitivity, and interaction evidence. A profile match must remain separate from confirmed willingness to introduce. |

Sources: [Centralize product](https://www.usecentralize.com/), [CTD relationship intelligence](https://ctd.ai/relationship-intelligence-software), [Swarm scoring help, dated 2025-08-19](https://help.theswarm.com/en/articles/8117404-how-is-relationship-status-calculated). These pages describe current or established features. Retrieval date is not a release date.

## Changes useful for the current full-list review

1. **Show account coverage.** Group targets by account. Report total targets, profiles matched, targets with positive evidence, and targets without a candidate path. Preserve missing targets in the report. Do not substitute a ten-person sample.
2. **Collect path feedback.** Add local labels such as Useful, Weak, Wrong person, and Cannot introduce, plus a note. Export the labels with stable target and connector IDs, model version, weights, and run date. User feedback is a review signal, not consent from the connector.
3. **Show evidence freshness.** Display source observation dates. Do not treat a recent score computation as a recent profile check. Mark unknown or old employment status clearly.
4. **Separate path strength from account priority.** Committee role, customer status, and account fit help decide whom to contact. They do not prove that the connector knows that person.
5. **Keep investor roles strong and communities weak.** A dated, named investment role at the target company is more direct evidence than a shared backer elsewhere. Do not multiply the same investment across role, employer, and portfolio features.
6. **Keep the large-company rule.** Shared company, role function, location, and timing provide more specific evidence than a company name alone. Do not copy current title or city onto an old employment period.

These are implementation recommendations inferred from the product comparison and this package's evidence contract. The vendors do not publish weights that validate our 120/80/3/2 defaults.

## Next data and workflow gaps

| Priority | Capability | Required evidence or implementation | Scoring rule |
| --- | --- | --- | --- |
| High | Both relationship edges | Separate requester-to-connector and connector-to-target evidence, with timestamps | The weak or unknown edge must remain visible. Do not sum away a missing edge. |
| High | Recency, frequency, reciprocity | Dated inbound and outbound interaction metadata; attended small meetings | Aggregate message counts alone are insufficient. Exclude bulk mail and declined meetings. |
| High | Connector confirmation | A first-person statement of knowing the target and willingness to help | Keep confirmation separate from automated similarity. Record actor, date, scope, and revocation. |
| High | Historical overlap duration | Guaranteed dated overlap, capped contribution, tested sensitivity | A one-month overlap should not silently equal several years. Test new duration weights against feedback before adopting. |
| High | Fresh job changes | New profile observations and event-based re-scoring | Refresh affected paths. Preserve prior evidence and run lineage. |
| Medium | Buying committee coverage | Verified role in the purchase and account ownership | Use as an account view and relevance field, not fabricated relationship warmth. |
| Medium | Connector load and duplicate asks | Intro request ledger, owner, cooldown, approved contacts | Avoid repeated asks and route through the relationship owner. |
| Medium | Outcome tracking | Confirmed intro, accepted intro, meeting, qualified opportunity | Evaluate top-k usefulness first. Calibrate probabilities only after enough unbiased outcomes. |
| Medium | Multi-hop and pooled networks | Authorized network imports; identity resolution for every edge | Penalize added hops and show each edge. A company investment graph alone is not a person-to-person introduction. |
| Medium | Social interactions | Attributed replies and repeated exchanges with dates | Mere following, shared posting topics, and likes are weak evidence. Do not infer personal closeness. |

[CTD release notes](https://ctd.ai/release-notes) document editable relationship scores, manual path stages, request history, approved connectors, event-triggered refresh, and public-data paths through external members. The latest visible entry is August 2026; the page provides no exact release day for that entry, so it cannot be asserted to fall wholly inside the 30-day window.

[CTD job-change lists](https://ctd.ai/guide/article/lists-job-changes) support static people lists, dynamic company/persona lists, and webhooks. [The Swarm web application](https://www.theswarm.com/product/web-application) provides shared lists, role-based access, and intro-request pipelines. These are established product capabilities, not observed performance results.

## Evaluation additions

- Positive profile-only paths must stay `needs_confirmation` until explicit relationship evidence is present.
- Adding an unsupported interaction count must not increase relationship points.
- Old or undated interactions must not rank above otherwise identical verified recent two-way interactions.
- One duplicated email or meeting must not earn points twice.
- Current same-city data must not strengthen a past job overlap without historical location evidence.
- A shared investor must not become a direct investment role without a named person, company, and valid dates.
- An angel investor's employer must not become an investing firm. Verify the named investing entity before assigning company-link points to its employees.
- Blocked or declined intro requests must not appear as ready paths, regardless of similarity score.
- Every source-list target must appear as scored, unmatched, or held for identity review.
- Evaluate precision at 3 and pairwise preference agreement from exported human reviews. Split evaluation by account and connector to reduce leakage. Do not call a ranking score a probability of a successful intro.

## Recent community evidence

The actual last30days engine ran with a four-query product-specific plan for 2026-08-24 through 2026-09-23. It returned 48 candidate items across seven sources. Manual review rejected unrelated social posts and videos. These counts are retrieval counts, not 48 product reviews. Reddit was partial because of HTTP 429 responses. Instagram returned HTTP 404. These failures do not show that either community had no discussion.

Relevant material was mainly vendor-authored. [The Swarm founder describes target-first network expansion](https://www.linkedin.com/posts/olivier-roth_we-can-now-find-hundreds-of-possible-intro-activity-7497759676726538240-gCZ2): map both networks, find intersections, then rank paths. [The Swarm Claude walkthrough](https://www.linkedin.com/posts/wearetheswarm_activity-7499155174922510336-wb2L) emphasizes relationship context and a person choosing the introduction. The public pages show relative dates, so the search provider's exact dates were not treated as verified publication dates.

[Happenstance's guide, updated 2026-08-28](https://happenstance.ai/guides/warm-intro-tools), distinguishes connected-account evidence from inferred profile overlap and emphasizes both relationship edges. This is a competitor's positioning, not an independent comparison. Its claim that a connected account guarantees an introducer can say yes is too strong for our model: willingness still requires confirmation.

No sufficiently strong recent independent evidence was found to declare a best product, calibrate success probabilities, or replace the user's chosen weights. Preserve the model's explicit evidence rules and use the full-list feedback artifact to test ranking usefulness.
