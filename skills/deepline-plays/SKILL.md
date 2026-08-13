---
name: deepline-plays
description: 'Design and run a custom Deepline GTM Play when an outcome needs live providers, public web evidence, private data, a waterfall, or adaptive strategy selection. Trigger for company or people discovery, enrichment, research, contact workflows, SERP-to-extraction, provider comparison, or any GTM request whose route is unproven. Skip a simple request to run one named existing Play.'
---

# Deepline Plays

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

Build an agent-authored executable that allocates a bounded retrieval budget to
the next highest-value evidence move. The agent designs the strategy space; the
Play collects durable evidence; deterministic kernels decide whether to explore,
exploit, stop, or promote.

## Contract

- Start from a row contract: final fields, acceptance semantics, evidence
  requirements, denominator, freshness, and permitted unresolved fields.
- The agent writes the Play, mappings, claim policies, action cards, literal
  provider calls, adapters, and output projection. Never ask the user to choose
  a provider, source mapping, or prebuilt Play that the agent can determine.
- Treat a provider call as an **action** that may advance one or more claims,
  not as a monolithic workflow. A row can combine discovery from a registry,
  proof from an official page, a people lead, a current-role validator, and a
  private join.
- Keep every selected fact inside the completed Play. Browser or terminal
  research may orient the agent, but it cannot repair a final row after the
  Play runs because it has no receipt, source binding, or replay path.
- Use AI to design hypotheses, adapters, semantic acceptance, and the next
  source family. Do not use an AI answer as evidence or invoke one research
  model call per candidate.

Names in this skill are hints, not contracts. Discover live capabilities with
`deepline tools search`, then inspect the exact contract, price, and output
shape with `deepline tools describe <tool-id> --json` before authoring a paid
action.

## Decision matrix

| The user needs                                               | Controller shape                                            | Read                                          |
| ------------------------------------------------------------ | ----------------------------------------------------------- | --------------------------------------------- |
| A list from scratch, plus evidence-rich company/contact rows | discovery pool → eligibility gates → adaptive claim actions | `references/company-research-from-scratch.md` |
| One or more unsupported claims on known rows                 | one-step gap controller over row-scoped action cards        | `references/adaptive-research.md`             |
| A private/public/source-plan decision before execution       | broad source fanout and source-plan synthesis               | `deepline-pre-research`                       |
| A known list that needs ordinary enrichment                  | existing Play or one custom row program                     | `jobs/enriching.md`                           |
| A broad ICP or contact search                                | candidate-set generation and filtering                      | `jobs/finding.md`                             |

Use a named prebuilt directly only when its declared input and output contract
already satisfies the full request. Otherwise wrap or replace it with a custom
Play; a prebuilt route can be one action card, never an unexamined strategy.

## The two kernels

Copy both portable helpers into the workspace before authoring an unproven
research workflow:

```bash
for dir in \
  "$PWD/.skills/deepline-plays" \
  "$HOME/.claude/skills/deepline-plays" \
  "$HOME/.agents/skills/deepline-plays"; do
  [ -f "$dir/plays/shared/research-experiment.ts" ] && SKILL_ROOT="$dir" && break
done
[ -n "${SKILL_ROOT:-}" ] || { echo "Could not find deepline-plays skill root" >&2; exit 1; }
mkdir -p ./shared
cp "$SKILL_ROOT/plays/shared/research-experiment.ts" ./shared/research-experiment.ts
cp "$SKILL_ROOT/plays/shared/research-portfolio.ts" ./shared/research-portfolio.ts
```

That copy is a **build boundary**, not a convenience. A customer-authored Play
must import the helpers only through workspace-relative paths:

```ts
import { defineResearchExperiment } from './shared/research-experiment';
import { planResearchPortfolio } from './shared/research-portfolio';
```

Never import from `.agents/skills`, `.claude/skills`, `$HOME`, or a managed
skill root. Those paths are authoring-time inputs and are absent in the
customer's execution environment. The Play and its copied `./shared` kernel
must be self-contained before `plays check` or any pilot run.

## Executable artifact boundary

The experiment and portfolio helpers are libraries. A file is not a runnable
customer Play merely because it exports `runCohort`, `runAdaptiveRow`, or an
action-card array. The final `.play.ts` must import `definePlay` from
`deepline` and default-export the actual runtime entrypoint:

```ts
export default definePlay(
  'customer-adaptive-research',
  async (ctx, input) => {
    // Materialize the agent-authored candidate pool, execute the row
    // controller, and return the promotion artifact and durable output rows.
  },
  { description: 'Bounded adaptive research.' },
);
```

Keep `runAdaptiveRow` as a typed helper called by this entrypoint. Do not hand
the customer a library fragment that an agent must later wrap or reinterpret.

`research-portfolio.ts` is a deterministic **budgeted contextual bandit
controller**. The agent authors action cards, including source family,
correlation class, exact upper credit bound, prerequisites, claim targets, and
an optional aggregate historical prior. The controller ranks one admissible
next action:

```text
U(a) = exp(-ρ·correlated_attempts(a)) ·
       Σgap weight(g) · evidence_weight(a) · [μ(a,g) + κ·σ(a,g)]
       + novelty_bonus(a) - credit_penalty(a) - latency_penalty(a)
```

`μ` and `σ` are the Beta-posterior mean and uncertainty for verified claim
yield. The action is re-ranked after every observed result. This gives the
agent a principled explore/exploit loop without pretending that provider yield
is stationary across segment, geography, entity type, or claim class.

`research-experiment.ts` remains the evidence and promotion kernel. It binds
evidence to returned raw text, re-evaluates claim acceptance, rejects adapter
or policy failures, and decides whether final rows are promotable. The
portfolio controller never manufactures evidence; the experiment compiler never
chooses a provider.

## Author action cards, then execute one move at a time

An action card is a visible, falsifiable hypothesis plus its economics. It is
not a tool name and it is not a natural-language plan. Write cards for
materially different evidence mechanisms, such as official staff page,
operating-license registry, current-role validator, active ATS listing,
structured company database, CRM policy join, or warehouse outcome query.

Use `producesArtifactIds` / `requiresArtifactIds` for a dependency that is
useful but not customer proof. For example, a capped people lookup can produce
`operator_lead`; the later current-role validator requires that artifact. A
lead is still not a verified `operator` claim, so this makes the execution
dependency explicit without laundering a lead into evidence.

```ts
const actions = defineResearchActionPortfolio([
  {
    id: 'official_operator_v1',
    hypothesis:
      'Official staff pages can name a current customer-service operator.',
    sourceFamily: 'official_web',
    correlationGroup: 'first_party_site',
    stage: 'claim_completion',
    evidenceMode: 'terminal_evidence',
    producesClaimIds: ['operator'],
    maximumDeeplineCredits: 0.1,
  },
  {
    id: 'license_operator_v1',
    hypothesis:
      'Operating-license records can identify an owner or operator missed by staff pages.',
    sourceFamily: 'public_registry',
    correlationGroup: 'public_registry',
    stage: 'claim_completion',
    evidenceMode: 'terminal_evidence',
    producesClaimIds: ['operator'],
    maximumDeeplineCredits: 0.2,
  },
]);
```

Use a non-secret `contextKey` that captures the task phenotype, for example
`local_fuel:philly:operator`. Aggregate priors may contain counts only:
verified claims and attempted claims for the same phenotype. Never pool raw
customer rows, identities, prompts, evidence, or provider costs across
workspaces. The current row's run artifact is the authority.

Call `planResearchPortfolio(...)`, then dispatch the selected card through an
explicit `switch` or named branch. Keep each provider tool ID literal inside
that branch. A dynamic provider ID or generic callback registry hides the
actual retrieval graph from the Play checker and later reviewers.

After the branch returns, bind its evidence and evaluate claims through
`research-experiment.ts`; record the observed strategy telemetry with
`recordResearchActionObservation(...)`; then plan again. Only a verified claim
leaves the gap set. `lead_only` results are discovery artifacts, not terminal
facts. A lead-only card may target the eventual claim in `producesClaimIds` so
the controller can select it, but its branch must record **zero**
`verifiedClaimIds`; it must instead declare and emit a concrete
`producesArtifactIds` value such as `operator_lead`. The next terminal
validator must declare the matching `requiresArtifactIds` prerequisite.

`budgetDeeplineCredits` is a hard route envelope, not a per-action allowance.
The controller subtracts observed current-row credits before every next plan.
If an action's observed cost is unknown, it stops budgeted exploration rather
than treating the action as free. Set every action-card maximum from the live
catalog or an observed receipt, and reserve credits for the final proof move.

An adapter failure or policy violation is not a negative source observation.
Record it with its receipt, stop that row's current attempt, and either restart
from its durable checkpoint after repair or take the cohort replacement path.
Do not spend the rest of the row envelope on a contaminated trajectory or feed
the failure into the source-yield posterior.

For a from-scratch cohort, encode a **replacement transition** in both the
Play and its decision artifact: when one retained candidate exhausts its
admissible required-claim actions, retain the exact miss and advance the next
eligible candidate through the same gates. The cohort stop rule is never
“three candidates attempted”; it is “N complete rows promoted,” or an explicit
shortfall after the frozen pool and bounded replacement expansion are exhausted.

The `defineResearchExperiment(...).candidates[].run` callback must invoke this
actual row controller. Never attach a decorative `run: async () => ({ claims:
{} })` candidate beside a real controller, and never make final promotion
evaluate a different path. In a design-only pass, leave **only** catalog-bound
branch bodies as typed implementation points; the candidate still calls the
controller, which plans, dispatches, binds, merges, evaluates, and records an
action result. This prevents the experiment artifact from becoming a passive
comment block that a later author must reconstruct.

Read `references/adaptive-research.md` for the full skeleton and decision
artifact shape.

## Exploit heterogeneity rather than thrash

Provider heterogeneity matters when sources fail differently. Model it
explicitly with `sourceFamily` and `correlationGroup`:

| Claim gap                          | Independent action families                                                          | Terminal condition                                                       |
| ---------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Company identity, offer, geography | official site, public registry, maps/directory validation                            | canonical entity and admissible source-bound excerpt                     |
| Current operator                   | official staff page, registry/officer record, people lead + separate role validation | name, target company, and allowed current role in one admissible context |
| Active hiring                      | official ATS/careers page, job-index discovery + final job-page fetch                | active state, allowed role, dated posting inside window                  |
| Account propensity or intent       | public event/news, private CRM, warehouse/product usage                              | source-specific claim policy and stable join key                         |
| Market language                    | customer calls/support, community discussion, reviews/competitor pages               | exact quote, persona context, and source provenance                      |

Two providers that expose the same index belong in one correlation group. A
registry and an official site normally do not. After a miss, the controller
discounts the same group and makes an untried independent group competitive.
That is persistence with information gain, not retrying a query with cosmetic
filter changes.

Use a broad, cheap discovery fanout when no rows exist. Preserve discovered
URLs, raw excerpts, canonical keys, selected/excluded reasons, and every near
miss. Freeze a common candidate pool before costly row-level work. Then use
the controller to screen more than the requested count through required
admission claims. For example, if a named operator is required, only companies
with both ICP and operator proof may enter an expensive hiring stage.

## Budget, evidence, and stopping gates

**Bound every action before execution.** Set `maximumDeeplineCredits` from a
live tool description or a measured receipt. The controller rejects unknown or
over-budget actions rather than treating them as free. Keep a reserve for final
verification or selected-run work. A people provider is gap-only: request the
smallest candidate set that can alter the next decision, then independently
validate the result. A broad ten-result people search is a high-cost lead
generator, not better evidence.

**Keep action economics separate from truth.** An action that returns a URL,
person, or model extraction has only produced a lead until the exact final URL,
raw excerpt, identity, freshness, and task-specific acceptance function pass.
One authoritative source can be enough only when the claim policy says why.
An unrelated `President` title does not satisfy a request for owner,
operations, customer-service, or CX.

**Stop on measured terminal states.** Continue until every required claim is
verified, a candidate replacement is available, or the controller has no
positive-utility admissible action. Stop when budget, prerequisites, or source
space are exhausted. Report that stopping reason and the retained misses;
never turn lack of evidence into a negative assertion or a partial cohort into
a promoted winner.

**Keep row work row-scoped.** Run actions inside a dataset
`.withColumn(async (row, rowCtx) => ...)`, pass `rowCtx` into every helper, and
use literal checkpoint IDs. Revised query, adapter, source policy, or claim
semantics require a visible policy revision and new checkpoint IDs. Debug only
with `deepline runs get`, `deepline runs logs`, and `deepline runs export`;
never query workspace storage directly.

## Minimal execution loop

1. Inspect inputs and write the final row contract.
2. Search and describe only the source categories needed for the first action
   frontier. Record cost ceilings and evidence fields.
3. Author `defineResearchExperiment(...)` claim contracts and a diversified
   portfolio of literal action branches in one Play.
4. `deepline plays check ./<task>.play.ts`, then run one or a few representative
   rows. An adapter failure is a repair event, not a low-yield source result.
5. After each action, bind evidence, record the outcome, re-plan, and move to
   the next action only if it has positive marginal utility.
6. Compile and promote final evaluations with a floor matching the requested
   count. Project customer rows only from the completed promoted datasets.

Use separate visible commands for validation and billing:

```bash
deepline billing balance --json
deepline plays check ./<task>.play.ts
deepline plays run ./<task>.play.ts --input @input.json --watch
deepline runs get <run-id> --full --json
deepline runs export <run-id> --dataset <final-dataset-path> --out <output>.csv
deepline billing balance --json
```

## Delivery

Return the verified rows, evidence URLs/excerpts, unresolved fields, candidate
selection audit, action decision artifacts, promotion result, run ID, and the
opening-minus-closing Deepline credit delta. Explain what to scale only after a
route is measured. Do not expose provider spend.

## Read only when needed

| Need                                                             | Read                                          |
| ---------------------------------------------------------------- | --------------------------------------------- |
| The adaptive algorithm, card schema, or full executable skeleton | `references/adaptive-research.md`             |
| Company discovery from scratch, operator proof, or hiring proof  | `references/company-research-from-scratch.md` |
| Concrete observed agent failures and regression scars            | `references/pattern-library.md`               |
| Replay, input mapping, row contexts, and SDK authoring           | `shared/authoring.md`                         |
| Evidence, golden data, and adaptive claim correctness            | `shared/correctness.md`                       |
| Receipts, row isolation, resume, and run inspection              | `shared/durability.md`                        |
| Candidate discovery or contacts                                  | `jobs/finding.md`                             |
| Known-row enrichment                                             | `jobs/enriching.md`                           |
| A checked Play has a syntax, replay, or getter error             | `references/debugging.md`                     |
