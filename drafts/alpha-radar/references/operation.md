# Operating contract

## Graph and inputs

The bundled graph contains a manual trigger, five deeplineagent roles (ICP, discovery,
per-candidate research, per-candidate audit, brief), five Python nodes (memory, identity gate,
evidence assembly, scoring, research queue), an empty-search receipt, and two rules conditionals. There are
14 graph nodes, executed locally by `scripts/graph_runner.py`. The actual prompts and executable Python are in blueprint.json;
that configuration is authoritative if an example here is ambiguous.

Manual inputs are focus, memory_json, feedback_json and settings_json. The last
three are optional strings containing JSON. The supplied runner reads the prior
run record from the run-history folder and populates them. There is no custom webhook, database, API provider, cache,
email finder, or sending action in the runtime.

Model: `openai/gpt-5.4` through `deeplineagent` for criteria, discovery, per-candidate
research, audit and the brief (the same model the original graph used). Confirm the ID is
still in the AI Gateway catalog (https://ai-gateway.vercel.sh/v1/models). Do not silently substitute a different model because these semantic
assessments influence evidence extraction and cost.

## Evidence and score

The agent rubric uses integers 0–4: absent, unsupported claim, concrete example,
detailed primary evidence, and corroborated or reproducible evidence. The ICP
defines what those anchors mean in its own context.

For one eligible evidence item:

    q = strength / 4 × source_weight × (0.55 + 0.45 × freshness)
    freshness = 0.5 ** (age_days / half_life_days)

Source weights: primary 1.0, independent 1.0, self_reported 0.65; other source
labels receive 0.4. An unknown date uses freshness 0.65. A future or invalid
date contributes zero. Dates refer to the underlying work, not the observation
timestamp. Older evergreen work retains some weight but cannot be described
as a recent event. “Verified” means the audit inspected that source and the
source supports that claim, not that an agency's reported results were independently
replicated. Model verification can still be wrong.

For each dimension, take the maximum q among eligible, audit-verified items.
Repeated source URLs do not accumulate points. Then:

    raw_score = 100 × product(max(0.03, dimension_q) ** dimension_weight)
    evidence_score = max(0, raw_score - min(30, 10 × contradicted_item_count))

No eligible items means zero. The 0.03 floor prevents numerical collapse; it does
not imply evidence exists. Missing dimensions keep their denominator weights.
Fit and proof also have minimum gates (default 40 each), so strong originality
cannot compensate for the wrong audience. Weights are positive, normalized to one,
and frozen with the same-brief memory so later score changes remain interpretable.

Eligibility requires both research and audit to confirm identity, at least the
configured number of distinct verified URLs (minimum 2), a verified primary
work artifact in proof, insight or usefulness (an identity/fit page alone is insufficient),
the configured total and fit/proof thresholds, no unresolved contradictory
evidence, and no explicit disqualifier. Same-domain URLs are separate artifacts,
not necessarily independent corroboration. The brief must preserve that distinction.
A separately accessed identity_url can count toward the source total when both passes
confirm identity and the exact normalized URL appears in the audit's checked_urls.
It adds no dimension points. This keeps moving an identity citation between the fit
field and the identity field from arbitrarily changing the source count. Its explicit
output field is verified_identity_source; work claims still require verified_evidence.

Every score and threshold is a heuristic. No threshold was fitted to business
outcomes. Source weights, the decay floor, undated-date factor, contradiction
penalty, dimension floor and feedback cap are design constants in the included
Python. Advanced settings expose sample size, total/fit/proof cutoffs, source count,
and half-life; change other constants only as an explicitly reviewed model revision.

## Counterfactual sensitivity

Normalize scheme, www, fragments and trailing slashes so common variants of the same
article count as one source. Meaningful query strings remain distinct. Remove every
claim from one canonical source URL, recompute, and repeat for each
source. Report the lowest resulting score and the source removed. This tests
dependence on an artifact. It is not a causal explanation, predictive confidence
interval, or numerical proof that one source caused a result.

## Review learning

Each ICP-specific archetype starts with Beta(1,1), a neutral reward prior.
An explicit human approval adds one to alpha; rejection adds one to beta.

    posterior_mean = alpha / (alpha + beta)
    priority_bonus = 8 × (posterior_mean - 0.5)
    priority_score = clip(evidence_score + priority_bonus, 0, 100)

No reviews means zero bonus. The adjustment is bounded to ±4. Qualification
is computed BEFORE this bonus. Positive feedback cannot bypass any evidence gate.
Posterior uncertainty is shown as sqrt(alpha*beta / ((alpha+beta)^2*(alpha+beta+1))).
The highest-uncertainty candidate is exposed as a possible exploration choice;
there is no automatic exploration execution, optimized reward policy, or proven lift.
This is a small bandit-style preference update, not reinforcement training of the LLM.

A feedback item contains candidate_id, rating (0 or 1) and feedback_id. Unknown
candidates and invalid ratings fail visibly. Duplicate event IDs are ignored.
The rating ledger replaces a candidate's previous rating contribution when revised,
so repeated likes cannot manufacture extra independent observations.

Scope is the normalized original brief plus normalized settings. Mismatched memory
fails; the runner intentionally starts blank when scope changes. Candidate identities,
last scores, source URLs, scoped criteria, ratings, reward counts and processed event
IDs persist in the score node's memory_json output inside the local run record. No private cache is used to discover candidates.

## Output interpretation

The score node returns ranking_json, memory_json, qualified_count, researched_count,
research_required_count, exploration_candidate, learning_state and method notes.
Each ranking row includes per-dimension components, evidence score, priority score,
verified evidence, unverified count, hold reasons, prior score delta and worst
source-removal result. The research output may contain hypotheses; only the
verified_evidence field supports factual claims in the final brief.

Run records persist in the private run-history folder. Do not distribute raw research outputs inside the
portable skill. A real-data demo and submission package are different artifacts.

## Failure handling

Inspect the exact failed node. Unsupported Python libraries must not be replaced
by custom HTTP calls. Node code uses only json, math and time (kept from the original
sandboxed runtime, so the graph stays portable). Incomplete model JSON should
fail visibly and be corrected at the generating node. Never silently repair a broken
evidence claim, fabricate a missing source, or treat a skipped candidate as qualified.

Zero candidates route to an explicit research-required coverage receipt before
Repeat. A nonempty candidate list whose research all fails is an execution failure,
not a verified empty result. Inspect that failure rather than claiming successful
completion. No additional paid batch is implicit in a failure.
