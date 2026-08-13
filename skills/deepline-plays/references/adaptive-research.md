# Adaptive research portfolio

Use this reference when a Play needs to decide which source or provider to try
next. It turns heterogeneous provider access into a sequential decision
problem. It does not replace the agent's judgment about claims, queries,
providers, adapters, or evidence semantics.

## Table of contents

1. Controller state
2. Action-card semantics
3. Exact selection objective
4. What the agent authors
5. Research topology for “find N companies from scratch”
6. Priors and strategy memory
7. Failure modes

## Controller state

Maintain four durable state objects per row:

1. **Claim state**: required claim IDs, verified claim IDs, acceptance results,
   and explicit misses. `research-experiment.ts` is the authority.
2. **Action frontier**: the agent-authored cards that could advance a remaining
   claim. Each card points to one literal retrieval branch in the same Play.
3. **Strategy telemetry**: one observation after each branch runs. It records
   verified claim IDs, no-result/rejection/adapter/policy outcome, observed
   Deepline credits, duration, and a compact reason.
4. **Budget state**: a hard budget and a reserve for final verification. The
   controller removes action cards whose upper credit bound does not fit.

The control loop is a contextual, budgeted, combinatorial semi-bandit with
partial observability. It is intentionally one-step greedy: provider yield is
non-stationary, and the evidence returned by the first action changes which
claim and source are valuable next.

```text
while required_claims - verified_claims is nonempty:
    plan = planResearchPortfolio(current_state)
    if plan.selectedActionId is null: stop(plan.stopReason)
    raw = run_literal_branch(plan.selectedActionId)
    candidate_outcome = bind_and_evaluate(raw)
    observations = recordResearchActionObservation(candidate_outcome.telemetry)
    verified_claims = claim_state(candidate_outcome)
```

Do not implement the loop by dynamically constructing a tool ID. Tool IDs and
checkpoint IDs must remain literal in the Play so authoring, replay, receipt
attribution, and review can see the actual execution graph.

## Action-card semantics

An action card is an expected marginal-information unit. It must specify:

| Field                      | Why it exists                                                                                              |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `hypothesis`               | Makes the retrieval falsifiable and prevents “try provider X” cargo culting.                               |
| `sourceFamily`             | A durable category such as official web, registry, jobs, people database, CRM, warehouse, or community.    |
| `correlationGroup`         | Encodes latent dependence. Providers scraping the same corpus belong together even if their brands differ. |
| `producesClaimIds`         | States the exact unresolved terminal claims the action can advance.                                        |
| `requiresVerifiedClaimIds` | Prevents costly work without its required identity or eligibility prerequisite.                            |
| `evidenceMode`             | Distinguishes terminal proof, corroboration, and a lead. A lead cannot complete a customer row.            |
| `maximumDeeplineCredits`   | An upper bound from a live description or observed receipt. Unknown is inadmissible in a bounded pilot.    |
| `historicalPrior`          | Context-matched aggregate terminal-claim or lead-artifact successes/trials, never raw customer data.       |

Write several cards only when they are causally different. A search API and an
extractor are usually different stages of one action, not independent actions.
Two people databases based on the same professional-profile corpus are one
correlation group. An official staff page, a state license record, a private
CRM field, and a warehouse activity metric are normally independent families.

## Exact selection objective

For each action `a`, remaining claim `g`, and context phenotype `x`, the
controller forms a Beta posterior over useful immediate action yield:

```text
successes(a,x) = verified_claims(a,x) + materialized_lead_artifacts(a,x)
α(a,x) = 1 + successes(a,x)
β(a,x) = 1 + attempted_claims(a,x) - successes(a,x)
μ = α / (α + β)
σ = sqrt(αβ / ((α + β)²(α + β + 1)))
```

It then ranks the next action by:

```text
U(a) = exp(-ρ n_c) · Σg w_g · m_a · [μ(a,g,x) + κσ(a,g,x)]
       + I[n_c = 0] · δ - λ · credits(a) - τ · minutes(a)
```

- `n_c`: attempts on this row in `a`'s correlation group.
- `m_a`: `1.0` terminal evidence, `0.75` corroborating evidence, `0.1` lead
  only. A materialized lead is a success for its own retrieval posterior, not
  proof of a customer claim. This prevents a broad people search from looking
  like final proof while still letting it earn its validator branch.
- `κσ`: uncertainty bonus. It pays for a small, novel probe only when it can
  plausibly resolve a live claim.
- `exp(-ρ n_c)`: correlated-retry discount. It changes the next move after a
  genuine miss instead of oscillating across cosmetically different providers.
- `δ`: diversity bonus for an untried correlation group.
- `λ`, `τ`: explicit cost and latency penalties.

The default constants are deliberately mild. They are not universal provider
truth. The agent can tune them in `config` when the user prioritizes recall,
latency, or cost, but it should first run one small probe and use observed
yield. Do not tune them to make a preferred provider win.

## What the agent authors

The agent writes all retrieval intelligence. The portfolio helper only gives it
an objective and an audit trail.

```ts
import { definePlay, type DeeplinePlayRuntimeContext } from 'deepline';
import {
  compileResearchExperiment,
  defineResearchExperiment,
  getResearchClaimGaps,
  mergeResearchActionOutcome,
  type CandidateOutcome,
} from './shared/research-experiment';
import {
  defineResearchActionPortfolio,
  planResearchPortfolio,
  recordResearchActionObservation,
  type ResearchActionObservation,
} from './shared/research-portfolio';

type Row = { id: string; company: string; domain: string };
type OperatorLeadArtifact = {
  fullName: string;
  currentTitle: string | null;
  sourceUrl: string;
  rawEvidence: string;
};
type ResearchArtifactState = {
  operatorLead?: OperatorLeadArtifact;
};

const definition = defineResearchExperiment<Row, DeeplinePlayRuntimeContext>({
  input: { rowKey: 'id', required: ['id', 'company', 'domain'] },
  claims: [
    // The agent writes exact required facts, freshness, evidence policy, and
    // semantic acceptance here. This is the customer-row truth contract.
  ],
  candidates: [
    {
      id: 'adaptive_portfolio',
      hypothesis: 'Replan after every measured action.',
      run: async ({ row, context }) =>
        runAdaptivePortfolio({ row, rowCtx: context }),
    },
  ],
  promotion: {
    require: {
      minimumVerifiedRequiredClaimCoverage: 1,
      minimumCompleteRows: 3,
      noAdapterFailures: true,
      noPolicyViolations: true,
      noUnknownDeeplineCredits: true,
    },
  },
});
const experiment = compileResearchExperiment(definition);

const actions = defineResearchActionPortfolio([
  {
    id: 'official_operator_v1',
    hypothesis:
      'An official staff page can establish the allowed current role.',
    sourceFamily: 'official_web',
    correlationGroup: 'first_party_site',
    stage: 'claim_completion',
    evidenceMode: 'terminal_evidence',
    producesClaimIds: ['operator'],
    maximumDeeplineCredits: 0.1,
  },
  {
    id: 'registry_operator_v1',
    hypothesis:
      'A license or officer record can recover the allowed operator after an official-site miss.',
    sourceFamily: 'public_registry',
    correlationGroup: 'public_registry',
    stage: 'claim_completion',
    evidenceMode: 'terminal_evidence',
    producesClaimIds: ['operator'],
    maximumDeeplineCredits: 0.2,
  },
  {
    id: 'people_operator_lead_v1',
    hypothesis:
      'One company-scoped people result can nominate an operator for separate validation.',
    sourceFamily: 'people_database',
    correlationGroup: 'people_database',
    stage: 'discovery',
    evidenceMode: 'lead_only',
    producesClaimIds: ['operator'],
    // This targets the operator gap for planner eligibility. The branch emits
    // only operator_lead; it must not return a verified operator claim.
    producesArtifactIds: ['operator_lead'],
    maximumDeeplineCredits: 0.1,
  },
  {
    id: 'validate_operator_lead_v1',
    hypothesis:
      'An independent current-role artifact can validate a nominated operator.',
    sourceFamily: 'public_role_validation',
    correlationGroup: 'public_current_role',
    stage: 'verification',
    evidenceMode: 'terminal_evidence',
    producesClaimIds: ['operator'],
    requiresArtifactIds: ['operator_lead'],
    maximumDeeplineCredits: 0.2,
  },
  {
    id: 'official_hiring_v1',
    hypothesis:
      'An official ATS or careers page can prove a dated active hiring signal.',
    sourceFamily: 'official_jobs',
    correlationGroup: 'first_party_jobs',
    stage: 'claim_completion',
    evidenceMode: 'terminal_evidence',
    producesClaimIds: ['hiring'],
    requiresVerifiedClaimIds: ['operator'],
    maximumDeeplineCredits: 0.1,
  },
]);
const actionById = new Map(actions.map((action) => [action.id, action]));
const MAX_ACTIONS_PER_ROW = 6;
const MAX_OPTIONAL_ACTIONS_PER_ROW = 1;

type LiteralActionExecution = {
  outcome: CandidateOutcome;
  /** Ephemeral lead/artifact IDs declared by the selected action card. */
  producedArtifactIds?: readonly string[];
  /** Typed ephemeral payloads. They are never terminal customer facts. */
  artifacts?: ResearchArtifactState;
};

async function dispatchLiteralBranch(
  actionId: string,
  row: Row,
  rowCtx: DeeplinePlayRuntimeContext,
  artifacts: ResearchArtifactState,
): Promise<LiteralActionExecution> {
  switch (actionId) {
    case 'official_operator_v1':
      return runOfficialOperator(row, rowCtx);
    case 'registry_operator_v1':
      return runRegistryOperator(row, rowCtx);
    case 'people_operator_lead_v1':
      return runPeopleOperatorLead(row, rowCtx);
    case 'validate_operator_lead_v1':
      if (!artifacts.operatorLead) {
        throw new Error(
          'Operator-lead validator selected without its typed operatorLead artifact.',
        );
      }
      return runValidateOperatorLead(row, rowCtx, artifacts.operatorLead);
    case 'official_hiring_v1':
      return runOfficialHiring(row, rowCtx);
    default:
      throw new Error(`No literal branch declared for action: ${actionId}`);
  }
}

async function runAdaptivePortfolio({
  row,
  rowCtx,
}: {
  row: Row;
  rowCtx: DeeplinePlayRuntimeContext;
}): Promise<CandidateOutcome> {
  // This is the whole candidate route. Branches return one measured,
  // source-bound action outcome. The controller accumulates it, then replans.
  let outcome: CandidateOutcome = {
    claims: {},
    deeplineCredits: 0,
    durationMs: 0,
  };
  let observations: ResearchActionObservation[] = [];
  let artifacts: ResearchArtifactState = {};
  let optionalActionCount = 0;
  for (let move = 0; move < MAX_ACTIONS_PER_ROW; move += 1) {
    const before = experiment.evaluate([
      { row, candidateId: 'adaptive_portfolio', outcome },
    ])[0]!;
    const requiredGaps = getResearchClaimGaps({
      row,
      definitions: definition.claims,
      claims: outcome.claims,
      requiredOnly: true,
    });
    const optionalGaps = requiredGaps.length
      ? []
      : getResearchClaimGaps({
          row,
          definitions: definition.claims,
          claims: outcome.claims,
        }).filter((gap) => !gap.required);
    if (!requiredGaps.length && !optionalGaps.length) break;
    if (
      !requiredGaps.length &&
      optionalActionCount >= MAX_OPTIONAL_ACTIONS_PER_ROW
    ) {
      break;
    }
    const claimIdsToPlan = (
      requiredGaps.length ? requiredGaps : optionalGaps
    ).map((gap) => gap.claimId);

    const plan = planResearchPortfolio({
      contextKey: 'local_fuel:philly:operator',
      rowKey: row.id,
      requiredClaimIds: claimIdsToPlan,
      verifiedClaimIds: before.claims
        .filter((claim) => claim.status === 'verified')
        .map((claim) => claim.claimId),
      budgetDeeplineCredits: 1,
      reservedDeeplineCredits: 0.2,
      actions,
      observations,
    });
    if (!plan.selectedActionId) break;
    const action = actionById.get(plan.selectedActionId);
    if (!action)
      throw new Error(`Unknown selected action: ${plan.selectedActionId}`);

    const execution = await dispatchLiteralBranch(
      action.id,
      row,
      rowCtx,
      artifacts,
    );
    const materializedLeadArtifactIds = execution.producedArtifactIds ?? [];
    if (
      materializedLeadArtifactIds.includes('operator_lead') !==
      Boolean(execution.artifacts?.operatorLead)
    ) {
      throw new Error(
        'operator_lead ID and typed operatorLead payload must be emitted together.',
      );
    }
    artifacts = { ...artifacts, ...execution.artifacts };
    const actionOutcome = execution.outcome;
    outcome = mergeResearchActionOutcome({
      row,
      definitions: definition.claims,
      primary: outcome,
      supplemental: actionOutcome,
      gapIds: action.producesClaimIds,
    });
    const after = experiment.evaluate([
      { row, candidateId: 'adaptive_portfolio', outcome },
    ])[0]!;
    const previouslyVerified = new Set(
      before.claims
        .filter((claim) => claim.status === 'verified')
        .map((claim) => claim.claimId),
    );
    const newlyVerified = after.claims
      .filter(
        (claim) =>
          claim.status === 'verified' &&
          !previouslyVerified.has(claim.claimId) &&
          action.producesClaimIds.includes(claim.claimId),
      )
      .map((claim) => claim.claimId);
    if (action.evidenceMode === 'lead_only' && newlyVerified.length) {
      throw new Error(
        `Lead-only action ${action.id} attempted to complete a terminal claim. ` +
          'Emit only its declared artifact; the independent validator owns claim completion.',
      );
    }
    const hasRouteFailure = Boolean(
      actionOutcome.adapterFailures?.length ||
      actionOutcome.policyViolations?.length,
    );
    observations = recordResearchActionObservation({
      actions,
      observations,
      observation: {
        actionId: action.id,
        rowKey: row.id,
        contextKey: 'local_fuel:philly:operator',
        outcome: actionOutcome.adapterFailures?.length
          ? 'adapter_failure'
          : actionOutcome.policyViolations?.length
            ? 'policy_violation'
            : newlyVerified.length
              ? 'verified'
              : action.evidenceMode === 'lead_only' &&
                  materializedLeadArtifactIds.length
                ? 'lead_only'
                : 'no_result',
        verifiedClaimIds:
          action.evidenceMode === 'lead_only' ? [] : newlyVerified,
        producedArtifactIds: materializedLeadArtifactIds,
        observedDeeplineCredits: actionOutcome.deeplineCredits ?? null,
        observedDurationMs: actionOutcome.durationMs ?? null,
      },
    });
    // An adapter or policy failure is not a source miss. Do not update a
    // posterior from it or spend the remainder of this row's envelope on a
    // contaminated path. Keep the recorded failure, then let the cohort-level
    // replacement transition advance a fresh candidate (or restart this row
    // from its last durable checkpoint after the failure is repaired).
    if (hasRouteFailure) break;
    if (!requiredGaps.length) optionalActionCount += 1;
  }
  return outcome;
}

async function runOfficialOperator(
  row: Row,
  rowCtx: DeeplinePlayRuntimeContext,
): Promise<LiteralActionExecution> {
  // Literal discovery/fetch tool IDs, rowCtx-bound adapter, final URL policy,
  // raw-source evidence binding, and claim facts belong here.
  throw new Error('Agent must author the official operator branch.');
}

async function runRegistryOperator(
  row: Row,
  rowCtx: DeeplinePlayRuntimeContext,
): Promise<LiteralActionExecution> {
  // A materially different literal provider/query/adapter goes here.
  throw new Error('Agent must author the registry operator branch.');
}

async function runPeopleOperatorLead(
  row: Row,
  rowCtx: DeeplinePlayRuntimeContext,
): Promise<LiteralActionExecution> {
  // Return { outcome, producedArtifactIds: ['operator_lead'], artifacts:
  // { operatorLead: { fullName, currentTitle, sourceUrl, rawEvidence } } }
  // only when this literal branch actually nominates a company-scoped person.
  throw new Error('Agent must author the bounded people-lead branch.');
}

async function runValidateOperatorLead(
  row: Row,
  rowCtx: DeeplinePlayRuntimeContext,
  operatorLead: OperatorLeadArtifact,
): Promise<LiteralActionExecution> {
  void operatorLead;
  throw new Error('Agent must author the independent current-role validator.');
}

async function runOfficialHiring(
  row: Row,
  rowCtx: DeeplinePlayRuntimeContext,
): Promise<LiteralActionExecution> {
  throw new Error('Agent must author the dated active-job branch.');
}
```

## Export the runnable Play

The controller above is an internal helper, not the final artifact. The
customer-facing `.play.ts` must end in a real Deepline entrypoint. The agent
owns candidate materialization, branch bodies, and output projection; this
outer layer makes the topology executable and preserves one cohort-level
promotion artifact.

```ts
export default definePlay(
  'customer-adaptive-research',
  async (ctx, input: { candidates: readonly Row[] }) => {
    const attempts = [];
    for (const row of input.candidates) {
      const outcome = await runAdaptivePortfolio({ row, rowCtx: ctx });
      attempts.push({ row, candidateId: 'adaptive_portfolio', outcome });
    }
    const { evaluations, promotion } = experiment.promote(attempts);
    if (promotion.status !== 'promoted') {
      return {
        status: 'shortfall' as const,
        promotion,
        rows: null,
      };
    }
    const completedRows = evaluations
      .filter((evaluation) => evaluation.complete)
      .map((evaluation) => ({
        ...evaluation.row,
        claims: evaluation.claims,
        deeplineCredits: evaluation.deeplineCredits,
        durationMs: evaluation.durationMs,
      }));
    const rows = await ctx
      .dataset('promoted_research_rows', completedRows)
      .run({
        key: 'id',
        description:
          'Materialize only evidence-complete promoted research rows.',
      });
    return {
      promotion,
      rows,
    };
  },
  { description: 'Bounded evidence-first adaptive research.' },
);
```

Return the materialized final dataset only after the cohort promotion gate
passes, never an in-memory array of evaluations. A failed gate returns an
explicit `shortfall` with its promotion artifact and no customer rows. That
gives the customer a row-shaped export surface and keeps the promotion
artifact, evidence, and measured costs bound to the final row lineage.

For a from-scratch workflow, replace `input.candidates` with the bounded,
agent-authored discovery fanout and preserve the frozen candidate audit in the
returned run artifact. Do not export only `runCohort` or a branch registry: it
cannot be checked, run, or replayed as a Deepline Play.

Inside the actual row-scoped Play callback, invoke `definition.candidates[0]`
through the normal research runner or call `runAdaptivePortfolio` directly,
then promote only the `experiment.evaluate(...)` result. The example's
`dispatchLiteralBranch` is the task-specific implementation surface. Every
branch must bind raw source text with `bindResearchEvidenceToSource(...)`
before it returns its `CandidateOutcome`; `mergeResearchActionOutcome(...)`
then preserves verified facts and turns an unknown action cost into an unknown
route total. Record `producedArtifactIds` only when a lead branch really emits
its declared ephemeral artifact. This prevents a current-role validator from
being selected before its people lead exists. Do not replace the candidate
callback with a no-op that returns only an empty claim map. Keep the action
count bounded in visible config. The `throw`
placeholders above mark only the catalog-informed retrieval branches.

## Research topology for “find N companies from scratch”

The controller operates after a shared candidate-discovery stage. The correct
shape is:

```text
public / registry / structured discovery fanout
  → canonicalize and deduplicate candidate pool
  → cheap ICP/geography eligibility gate
  → adaptive screen for all required admission claims
  → freeze first N fully admissible companies
  → optional claim actions only on that denominator
  → promote only complete rows
```

Do not make every provider prove the entire row. Require that the **final
row** prove every required claim. This avoids paying every source for fields it
cannot answer and lets the controller compose the cheapest admissible evidence
path per row.

When an action identifies a better replacement candidate, retain the original
candidate and reason in the selection audit. A user who requested three rows
does not receive a two-row success decorated with an unresolved third company.

## Priors and strategy memory

Historical data is valuable only after being normalized into a task phenotype.
Use a low-dimensional key such as:

```text
<entity-class>:<vertical-or-data-shape>:<geography>:<claim-family>
```

Examples: `local_business:fuel_delivery:us_pa:current_operator`,
`b2b_saas:domain_known:global:job_signal`,
`existing_accounts:crm_connected:enterprise:propensity_feature`.

Store aggregate `verified_claims`, `materialized_lead_artifacts` (lead-only
actions), and `attempted_claims` by action family and phenotype. Do not store
names, domains, raw URLs, customer CRM values, prompts, retrieved text, or
internal provider cost. A prior is a weak initialization;
session observations dominate it. Separate adapter failures from no-result
outcomes or the system will mislearn runtime outages as source quality.

## Failure modes

**Provider menu paralysis.** An agent lists five tools but does not choose one.
Write cards, cost bounds, and a controller decision artifact before executing.

**False diversity.** Two vendors hit the same web index or people corpus. Put
them in one correlation group; otherwise the controller rewards a redundant
retry as novel exploration.

**Lead laundering.** A people search yields a name and the agent calls it a
current operator. Mark the action `lead_only`, then require a separate terminal
current-role validator.

**Over-exploration.** The agent spends the full pilot budget on ten results per
row. One action is selected at a time; cost ceilings and a verification reserve
are hard admission constraints.

**Under-exploration.** A weak official-page miss terminates the row. If an
independent, positive-utility correlation group remains, execute it and
re-plan. Stop only when the controller states an exhausted terminal condition.

**Global contamination.** The agent pools SaaS people-search yield with local
business operator yield. Use a phenotype key and aggregate counts only; do not
mix incomparable context.
