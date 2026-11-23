# All 14 Plays

Names below are the `config.name` values. Files are executable source; helper modules and local type copies are included. Credit values are configured per-run caps, not price quotes or guarantees that a run will finish within them.

## Synthetic lifecycle

Each child takes `{payload: Payload}` and returns a `Result` with a permitted next state, reasons and evidence. The authoritative field types and validation are in [types.ts](types.ts). Each has a 1-credit cap and makes no paid enrichment calls.

| Play | Source | Decision / outcome |
|---|---|---|
| expert-relationship-engine-v1 | [Entry point](expert-relationship-engine.play.ts) | Takes `{episodeId, payload}`; persists and advances an immutable episode, returning history and its terminal state. Calls the seven children below. |
| erm-discover-v1 | [discover](transitions/discover/erm-discover.play.ts) | Source identity and human identity review → qualify or waiting |
| erm-qualify-v1 | [qualify](transitions/qualify/erm-qualify.play.ts) | Supplied credential/domain decision → recruit, waiting or declined |
| erm-recruit-v1 | [recruit](transitions/recruit/erm-recruit.play.ts) | Interest and consent → onboard, waiting or declined |
| erm-onboard-v1 | [onboard](transitions/onboard/erm-onboard.play.ts) | Conflicts, agreement, training and availability → match or waiting |
| erm-match-v1 | [match](transitions/match/erm-match.play.ts) | Approved task, specialty, capacity, brief and rubric → review or waiting |
| erm-review-v1 | [review](transitions/review/erm-review.play.ts) | Human submission decision → learn or waiting; retains revisions and quality evidence |
| erm-learn-v1 | [learn](transitions/learn/erm-learn.play.ts) | Join task/world usage and feedback → complete with a relationship recommendation |

Terminal states have database input/output records but no child Plays. Each child owns a `transform.ts`; local `types.ts` copies support CLI bundling and are generated from the root contract.

## Provider-backed recruiting

| Play / source | Input | Tools or children | Result | Cap |
|---|---|---|---|---|
| [erm-source-experts-v1](refill/erm-source-experts.play.ts) | domain, limit 1–25, excludedNames | search_contact | Normalized candidates, returned/rejected counts | 2 |
| [erm-refill-experts-v1](refill/erm-refill-experts.play.ts) | optional batchLimit, at most 100 | Customer DB; source Play | Queue count, admitted candidates or skip/busy | 12 |
| [erm-qualify-candidate-v1](refill/erm-qualify-candidate.play.ts) | profile, domain, vertical | prebuilt/person-linkedin-to-company; prebuilt/person-to-email | qualified or held, with role/email evidence | 2 |
| [erm-enroll-candidate-v1](refill/erm-enroll-candidate.play.ts) | profile, email, firstName, lastName, company | Customer DB; lemlist_get_campaign; lemlist_list_unsubscribed_variables; lemlist_get_contacts; lemlist_add_to_campaign | confirmed, submitted, held, suppressed, already_claimed; errors retain uncertain writes | 2 |
| [erm-qualify-enroll-v1](refill/erm-qualify-enroll.play.ts) | optional limit 1–5 | Customer DB; qualify and enroll children | Per-person results; durable input/output history | 12 |
| [erm-recruitment-cycle-v1](refill/erm-recruitment-cycle.play.ts) | optional qualificationLimit and refillLimit | Customer DB; qualify-enroll, then refill | Below 100: bounded qualification then sourcing; otherwise skipped | 24 |

The two `prebuilt/` Plays are platform dependencies, not project-owned source. Describe their current contracts in your workspace before running. Their implementation is not copied into this repository. All 14 project-owned Plays are present.

On an empty queue, the first cycle sources candidates. Qualification happens on a later call. If the queue reaches 100, the cycle skips qualification too; call `erm-qualify-enroll-v1` separately to process that backlog. Newly sourced candidates are not qualified during the same cycle.
