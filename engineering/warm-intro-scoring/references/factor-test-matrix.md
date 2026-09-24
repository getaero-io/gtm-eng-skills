# Factor and evaluation coverage

These are heuristic evidence weights, not introduction-success probabilities. A factor can have scoring tests without being populated for every real contact. Positive evidence must identify the subjects, source, and applicable dates.

| Factor | Default weight | What is tested | Data status |
|---|---:|---|---|
| Recorded introduction | 160 | Source references, review holds, future-outcome leakage | Reviewed records only; not inferred from a draft or profile |
| Direct investor role | 120 | Actual investor versus investor-facing employee; target-company identity and dated overlap | Extracted from supported professional roles |
| Work overlap | 80 | Exact employer, conservative dates, company size, same function/location, strongest overlap, no duplicate bonuses | Extracted |
| Board overlap | 30 | Same company board role and overlapping dates, separate from employment | Extracted where profiles contain it |
| School overlap | 20 | Exact school and overlapping attendance; missing/uncertain dates stay unknown | Extracted |
| Job function | 20 | Comparable current duties; suppress duplicate credit from the same work overlap | Extracted; this is not an industry classifier |
| Shared public appearance | 20 | Normalized score/evidence contract | Reviewed evidence only; shared podcast series or a large event is not proof of meeting |
| Requester–connector relationship | 15 | Both-edge eligibility, willingness, missing evidence and declines in legacy evaluator | Reviewed evidence only; no automatic email/meeting ingestion |
| Work city and time | 10 | Dated co-location, ambiguous cities and multiple locations, duplicate suppression | Extracted; no inference of residence or origin |
| Industry / vertical / niche | 10 | Normalized weight/evidence contract | Reviewed evidence only; broad job function does not populate it |
| Shared investor / portfolio context | 3 | Company identity, current dated employer role, named investing firm, owner/target portfolio evidence, deduplication | Extracted when canonical links are supported; user can tune weight |
| Professional community | 2 | Normalized weight/evidence contract | Reviewed public or voluntarily supplied evidence only |

## Evidence and workflow tests

Tests also cover stale source dates, future observations, conservative month/year precision, identity collisions, self-pairs, missing and ambiguous targets, conflicting company sizes, unsupported claims, malformed JSON, score reweighting, missing target exports, durable declines, changed-evidence readiness, source coverage, CSV safety, and desktop/mobile report behavior.

The uncertainty fallback uses `deeplineagent` for contextual review and `ai_evaluate` with `typesafe-ai/jev` for a second evaluation. It checks exact source quotes and subject bindings. An unclear answer remains unclear. The initial live fixture covers explicit investment, title-only ambiguity, and explicit denial; additional contexts are covered by deterministic fixtures or remain candidates, not empirically validated outcomes.

## Candidate additions—not yet proven improvements

1. Shared team, manager, customer account or project, with actual timing.
2. Reciprocal replies, calls and attended meetings; distinguish these from outbound volume, bulk CCs and meeting invitations.
3. Recency, frequency and duration of direct interaction, separately for requester→connector and connector→target.
4. Same podcast episode, small panel or working group; distinguish this from appearing on the same podcast at different times.
5. Direct co-authorship, collaboration and specific two-way social exchanges; group tags, likes and follows remain weak.
6. Same school program, lab, cohort or dated non-sensitive professional club, rather than school prestige.
7. Career stage, company type and complementary goals, as relevance—not proof of access.
8. Connector capacity, recent asks, declines, willingness expiry and current conflicts as operational gates.
9. Multiple independently verified intro paths; popularity and duplicate sources must not inflate confidence.

Countries worked in remain excluded. No sensitive-trait inference is used.

## How to test whether a factor helps

Use point-in-time evidence and compare each added factor against the same baseline candidate list. Hold out accounts and time periods. Measure top-three relevant-path recall and ranking only where paths have independent labels. Measure introductions, replies and meetings only on observed eligible attempts with enough time to mature. Unknown or unsent paths are not failures. Report coverage by job function, company size and profile completeness. No current result proves outcome lift for the proposed additions.
