# Candidate matching factors and evidence policy

Research date: 2026-09-23. The last30days window was August 24–September 23. Current first-party descriptions support examining both edges and communication context; they do not validate numeric weights or prove causal uplift. Recent social evidence was sparse/promotional, Reddit coverage partial, and some retrieved items unrelated. Those items do not justify new coefficients. The [retained synthesis](research-brief.md) records coverage separately.

[Happenstance's August 28 guide](https://happenstance.ai/guides/warm-intro-tools) distinguishes observed relationship networks from inferred co-employment networks and ranks both links in an intro path. Its companion guide to requesting an introduction emphasizes connector willingness, a specific target and a forwardable reason. These are vendor descriptions, not independent validation.

[Affinity's API documentation](https://api-docs.affinity.co/#relationship-strengths) describes relationship estimates from emails, calls and meetings and explicitly notes that these do not tell the whole story. Its [product description](https://www.affinity.co/product/relationship-intelligence) identifies recency and frequency. These are evergreen sources checked this run, not claims of a change within 30 days.

## Broad factor inventory

| Factor family | Evidence to collect | Treatment and failure mode |
|---|---|---|
| Actual introduction / collaboration | Dated intro completed, project/team records, connector confirmation | Strong evidence; a draft ask is not a completed intro. Never use future outcomes in retrospective features. |
| Both directed relationships | Owner→connector and connector→target evidence separately | An unknown edge holds the path; profile confidence cannot substitute for either edge. |
| Recency, frequency, duration | Dated interactions, distinct periods, relationship tenure | Candidate tie-break features; no arbitrary universal half-life. Old close colleagues can retain useful ties. |
| Reciprocity and channel | Replies in both directions, attended small meetings, calls, coauthorship | One-way sequences, newsletter opens, meeting invitations and bulk CCs are not reciprocal relationships. |
| Willingness and capacity | Explicit current yes/no, outstanding intro requests, connector cooldown | A decline blocks; unknown holds. Load-balancing is an operational constraint, not lower human worth. |
| Work overlap | Same canonical employer, real intersecting dates, duration | Candidate familiarity; verify team/location/reporting context, especially at a large employer. |
| Shared team / manager / project | Source-supported team identity and intersecting tenure | Potential improvement over company overlap; never infer from job title alone. |
| Previous roles and function | Normalized duties, adjacent functions, shared problems | Stronger room-match relevance than intro proof. Different titles may describe similar work. |
| Career stage and company type | Scope/seniority, operator/founder stage, B2B/B2C, startup/enterprise | Context-specific affinity or complementarity; no age inference. |
| Industry, vertical, niche | Explicit customer sector and projects, sourced professional posts | Prefer task-specific relevance over generic title similarity. Separate product fit. |
| School, cohort, course, lab | Canonical school, dated cohort, shared lab/project | Broad alumni overlap is weak; actual shared small-group activity is stronger context. No prestige weighting. |
| Clubs, co-ops, college sports | Public/self-declared non-sensitive activity and overlap | Conversation context only; exclude affiliations revealing protected/sensitive traits. No inference from name, appearance or fraternity label. |
| Hometown, location, language | Voluntary professional context, relevant time/location overlap | Optional context, not origin/ethnicity proxy or automatic warmth. Countries worked in remain excluded from the event baseline. |
| Public social interaction | Verified account identity, reciprocal specific replies/co-creation | Likes, follows, mentions and popularity are weak; do not infer personality or private relationships. |
| Common interests | Explicit professional interests, activities people choose to share | Useful event icebreakers; do not mine private life or infer sensitive traits. |
| Network structure | Verified mutual edges, independent supporting sources, hop count | Duplicate sources do not add evidence; celebrity degree/popularity does not imply access. Each extra hop needs proof. |
| Investor, board, advisor, partner | Named individual role and actual relationship, not just portfolio overlap | Investor context capped; portfolio adjacency cannot carry a warm route alone. |
| Reason to meet / complementarity | Requester's specific ask, target remit, shared or complementary goal | Rank task fit separately; identical backgrounds are not always the best match. |
| Availability and eligibility | Current roles, conflicts, opt-in, suppression, already-introduced status | Gates outside factual similarity. Do not equate Going with arrival or arrival with consent. |
| Provenance and uncertainty | Identity resolution, date precision, contradictions, source age, coverage | Show missingness; avoid penalizing sparse profiles as if evidence disproved a tie. |

## What changes now

Preserve deterministic baseline weights and source priority. The implemented improvement is a conservative review gate requiring evidence on both edges and specific willingness; it changes draft eligibility, not numerical fit. The artifact displays the separate fields. Recency/reciprocity, team-level overlap, relevance, capacity and complementary goals remain candidate extensions until sufficient point-in-time labels exist. No honest study can establish that “all potential factors” improve matching merely by listing them.

Test one feature family at a time, use ablation against the fixed baseline, and measure performance on the same held-out candidate set. Evaluate subgroup coverage by job function/company size/profile completeness to detect systematic missing-data artifacts without inferring protected traits.
