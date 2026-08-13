/**
 * A deterministic controller for agent-authored research moves.
 *
 * The controller never discovers a provider, writes a query, or accepts an
 * answer. The agent writes those pieces as literal Play callbacks. This helper
 * decides which admissible callback has the best expected marginal value for
 * the claims that remain unresolved, while preserving a compact decision
 * artifact that can be replayed and audited.
 */

export type ResearchActionEvidenceMode =
  | 'terminal_evidence'
  | 'corroborating_evidence'
  | 'lead_only';

export type ResearchActionStage =
  | 'discovery'
  | 'claim_completion'
  | 'verification'
  | 'private_join'
  | 'activation';

export type ResearchActionCard = {
  /** Stable identifier. Keep tool calls inside this action literal and static. */
  id: string;
  /** A falsifiable statement of why this move can close the stated claim gaps. */
  hypothesis: string;
  /** A broad, durable source category, not a vendor name. */
  sourceFamily: string;
  /**
   * Actions in one group are correlated observations. Two search APIs scraping
   * the same public index belong in one group; a registry and an official site
   * normally do not.
   */
  correlationGroup: string;
  stage: ResearchActionStage;
  evidenceMode: ResearchActionEvidenceMode;
  /** Final claim IDs this move can materially advance. */
  producesClaimIds: readonly string[];
  /** Claim IDs that must already be verified before this move is meaningful. */
  requiresVerifiedClaimIds?: readonly string[];
  /**
   * Ephemeral artifacts this action can materialize for a later action, such
   * as a one-person people-search lead. Artifacts are not customer facts and
   * cannot complete a research claim.
   */
  producesArtifactIds?: readonly string[];
  /**
   * Ephemeral artifacts that must exist before this action is callable. Use
   * this for a validator that consumes a lead-only action result rather than
   * misrepresenting the lead as a verified customer claim.
   */
  requiresArtifactIds?: readonly string[];
  /**
   * Maximum Deepline credits for one row/action invocation, derived from the
   * live tool contract or a measured previous run. Unknown cost is not
   * admissible under a bounded budget.
   */
  maximumDeeplineCredits: number;
  /** Optional p95/upper-bound latency estimate used only for tie-breaking. */
  expectedDurationMs?: number;
  /**
   * An aggregate, context-matched historical prior. Store only counts and
   * never customer rows, queries, raw evidence, identities, or provider cost.
   */
  historicalPrior?: {
    /** Final customer claims confirmed by evidence. Zero for a lead-only action. */
    verifiedClaims: number;
    /** Usable intermediate artifacts materialized by a lead-only action. */
    materializedLeadArtifacts?: number;
    attemptedClaims: number;
  };
};

export type ResearchActionObservation = {
  actionId: string;
  rowKey: string;
  /** Match only the current task phenotype or `*`; do not pool unrelated jobs. */
  contextKey?: string;
  outcome:
    | 'verified'
    | 'lead_only'
    | 'no_result'
    | 'rejected'
    | 'adapter_failure'
    | 'policy_violation';
  /** A subset of the action's declared producesClaimIds. */
  verifiedClaimIds?: readonly string[];
  /** A subset of the action's declared producesArtifactIds. */
  producedArtifactIds?: readonly string[];
  observedDeeplineCredits?: number | null;
  observedDurationMs?: number | null;
  detail?: string;
};

export type ResearchPortfolioConfig = {
  /** Beta-posterior upper-confidence coefficient. Default: 0.5. */
  explorationWeight?: number;
  /** Utility penalty per Deepline credit. Default: 0.1. */
  costPenaltyPerDeeplineCredit?: number;
  /** Utility penalty per minute of expected wall time. Default: 0.02. */
  durationPenaltyPerMinute?: number;
  /** Bonus for a source-correlation group not yet attempted on this row. */
  diversityBonus?: number;
  /** How quickly repeat attempts in one correlation group are discounted. */
  correlationPenalty?: number;
  /** Relative value of a terminal, corroborating, or lead-only observation. */
  evidenceModeMultiplier?: Partial<Record<ResearchActionEvidenceMode, number>>;
  /** Relative value of each final claim. Defaults to 1. */
  claimWeights?: Readonly<Record<string, number>>;
};

export type ResearchPortfolioInput = {
  rowKey: string;
  /** A non-secret task/segment signature, such as `local_fuel:philly:operator`. */
  contextKey: string;
  requiredClaimIds: readonly string[];
  verifiedClaimIds: readonly string[];
  budgetDeeplineCredits: number;
  /** Funds intentionally held for a final verification or selected-run step. */
  reservedDeeplineCredits?: number;
  actions: readonly ResearchActionCard[];
  observations: readonly ResearchActionObservation[];
  config?: ResearchPortfolioConfig;
};

export type ResearchActionPosterior = {
  alpha: number;
  beta: number;
  verifiedClaims: number;
  materializedLeadArtifacts: number;
  successfulOutcomes: number;
  attemptedClaims: number;
  mean: number;
  standardDeviation: number;
};

export type ResearchPortfolioDecision = {
  actionId: string;
  sourceFamily: string;
  correlationGroup: string;
  stage: ResearchActionStage;
  claimGapIds: string[];
  maximumDeeplineCredits: number;
  expectedDurationMs: number | null;
  posterior: ResearchActionPosterior;
  expectedVerifiedClaimUtility: number;
  uncertaintyUtility: number;
  diversityUtility: number;
  correlationDiscount: number;
  costPenalty: number;
  durationPenalty: number;
  netUtility: number;
  mode: 'explore' | 'exploit';
  rationale: string;
};

export type ResearchPortfolioPlan = {
  type: 'deepline.research_portfolio_plan';
  schemaVersion: 1;
  rowKey: string;
  contextKey: string;
  remainingRequiredClaimIds: string[];
  /** Credits observed on prior current-row actions, or null when unknown. */
  spentDeeplineCredits: number | null;
  availableDeeplineCredits: number;
  selectedActionId: string | null;
  selectedMode: 'explore' | 'exploit' | 'stop';
  stopReason: string | null;
  ranked: ResearchPortfolioDecision[];
  excluded: Array<{ actionId: string; reasons: string[] }>;
};

const DEFAULT_EVIDENCE_MODE_MULTIPLIER: Record<
  ResearchActionEvidenceMode,
  number
> = {
  terminal_evidence: 1,
  corroborating_evidence: 0.75,
  lead_only: 0.1,
};

const DEFAULT_CONFIG: Required<
  Pick<
    ResearchPortfolioConfig,
    | 'explorationWeight'
    | 'costPenaltyPerDeeplineCredit'
    | 'durationPenaltyPerMinute'
    | 'diversityBonus'
    | 'correlationPenalty'
  >
> = {
  explorationWeight: 0.5,
  costPenaltyPerDeeplineCredit: 0.1,
  durationPenaltyPerMinute: 0.02,
  diversityBonus: 0.15,
  correlationPenalty: 0.35,
};

const RESEARCH_ACTION_OUTCOMES = new Set<ResearchActionObservation['outcome']>([
  'verified',
  'lead_only',
  'no_result',
  'rejected',
  'adapter_failure',
  'policy_violation',
]);

function isFiniteNonNegative(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0;
}

function uniqueNonEmpty(values: readonly string[]): string[] {
  return [...new Set(values.filter((value) => Boolean(value.trim())))];
}

function assertFiniteNonNegative(value: number, label: string): void {
  if (!isFiniteNonNegative(value)) {
    throw new Error(`${label} must be a finite non-negative number.`);
  }
}

/**
 * Validate the portable description the agent writes beside each literal
 * retrieval callback. This fails before a paid action can be selected.
 */
export function defineResearchActionPortfolio(
  actions: readonly ResearchActionCard[],
): readonly ResearchActionCard[] {
  if (!actions.length) {
    throw new Error('Research portfolio needs at least one action card.');
  }
  const ids = new Set<string>();
  for (const action of actions) {
    if (!action.id.trim())
      throw new Error('Research action ID must not be empty.');
    if (ids.has(action.id)) {
      throw new Error(
        `Research portfolio action ID is duplicated: ${action.id}.`,
      );
    }
    ids.add(action.id);
    if (!action.hypothesis.trim()) {
      throw new Error(`Research action ${action.id} needs a hypothesis.`);
    }
    if (!action.sourceFamily.trim() || !action.correlationGroup.trim()) {
      throw new Error(
        `Research action ${action.id} needs sourceFamily and correlationGroup.`,
      );
    }
    if (!uniqueNonEmpty(action.producesClaimIds).length) {
      throw new Error(`Research action ${action.id} needs producesClaimIds.`);
    }
    const producedArtifactIds = uniqueNonEmpty(
      action.producesArtifactIds ?? [],
    );
    const requiredArtifactIds = uniqueNonEmpty(
      action.requiresArtifactIds ?? [],
    );
    if (action.evidenceMode === 'lead_only' && !producedArtifactIds.length) {
      throw new Error(
        `Lead-only research action ${action.id} needs producesArtifactIds for its non-terminal result.`,
      );
    }
    const impossibleArtifact = requiredArtifactIds.find((artifactId) =>
      producedArtifactIds.includes(artifactId),
    );
    if (impossibleArtifact) {
      throw new Error(
        `Research action ${action.id} cannot require its own artifact ${impossibleArtifact}.`,
      );
    }
    if (!isFiniteNonNegative(action.maximumDeeplineCredits)) {
      throw new Error(
        `Research action ${action.id} needs a finite non-negative maximumDeeplineCredits.`,
      );
    }
    if (
      action.expectedDurationMs !== undefined &&
      !isFiniteNonNegative(action.expectedDurationMs)
    ) {
      throw new Error(
        `Research action ${action.id} has an invalid expectedDurationMs.`,
      );
    }
    if (action.historicalPrior) {
      const {
        verifiedClaims,
        materializedLeadArtifacts = 0,
        attemptedClaims,
      } = action.historicalPrior;
      if (
        !Number.isInteger(verifiedClaims) ||
        !Number.isInteger(materializedLeadArtifacts) ||
        !Number.isInteger(attemptedClaims) ||
        verifiedClaims < 0 ||
        materializedLeadArtifacts < 0 ||
        attemptedClaims < verifiedClaims + materializedLeadArtifacts
      ) {
        throw new Error(
          `Research action ${action.id} has an invalid aggregate historical prior.`,
        );
      }
      if (
        action.evidenceMode !== 'lead_only' &&
        materializedLeadArtifacts > 0
      ) {
        throw new Error(
          `Only a lead-only research action may have materialized lead artifacts in its historical prior: ${action.id}.`,
        );
      }
      if (action.evidenceMode === 'lead_only' && verifiedClaims > 0) {
        throw new Error(
          `Lead-only research action ${action.id} cannot have verified claims in its historical prior.`,
        );
      }
    }
  }
  return actions;
}

function matchingObservations(
  input: ResearchPortfolioInput,
  action: ResearchActionCard,
): ResearchActionObservation[] {
  return input.observations.filter(
    (observation) =>
      observation.actionId === action.id &&
      matchesResearchContext(observation, input.contextKey),
  );
}

function matchesResearchContext(
  observation: ResearchActionObservation,
  contextKey: string,
): boolean {
  return (
    observation.contextKey === '*' || observation.contextKey === contextKey
  );
}

function currentRowObservations(
  portfolio: ResearchPortfolioInput,
): ResearchActionObservation[] {
  return portfolio.observations.filter(
    (observation) =>
      observation.rowKey === portfolio.rowKey &&
      // A row key binds an observation to one concrete invocation. A wildcard
      // still supplies an aggregate posterior for other rows, but when it has
      // this exact row key it is necessarily a paid current-row action and
      // must consume budget and suppress a duplicate invocation.
      (observation.contextKey === portfolio.contextKey ||
        observation.contextKey === '*'),
  );
}

function observedResearchSpend(
  observations: readonly ResearchActionObservation[],
): number | null {
  let total = 0;
  for (const observation of observations) {
    const credits = observation.observedDeeplineCredits;
    if (credits === undefined || credits === null) return null;
    if (!isFiniteNonNegative(credits)) {
      throw new Error(
        'Research action observation has invalid observedDeeplineCredits.',
      );
    }
    total += credits;
  }
  return total;
}

/**
 * Construct a Beta posterior from anonymous aggregate data plus observations
 * whose task phenotype is comparable to the present row. A terminal action's
 * success is an evidence-verified claim; a lead-only action's success is a
 * materialized artifact that unlocks its independent validator. Infrastructure
 * and policy failures do not count as evidence that the source is low-yield.
 */
export function summarizeResearchActionPosterior(input: {
  action: ResearchActionCard;
  observations: readonly ResearchActionObservation[];
  relevantClaimIds: readonly string[];
}): ResearchActionPosterior {
  const relevantClaimIds = new Set(input.relevantClaimIds);
  const prior = input.action.historicalPrior;
  let verifiedClaims = prior?.verifiedClaims ?? 0;
  let materializedLeadArtifacts = prior?.materializedLeadArtifacts ?? 0;
  let attemptedClaims = prior?.attemptedClaims ?? 0;

  for (const rawObservation of input.observations) {
    const observation = validateResearchActionObservation(
      input.action,
      rawObservation,
      { requireContextKey: false, enforceActionCostMaximum: false },
    );
    if (
      observation.outcome === 'adapter_failure' ||
      observation.outcome === 'policy_violation'
    ) {
      continue;
    }
    const attemptedHere = input.action.producesClaimIds.filter((claimId) =>
      relevantClaimIds.has(claimId),
    );
    attemptedClaims += attemptedHere.length;
    const verified = uniqueNonEmpty(observation.verifiedClaimIds ?? []).filter(
      (claimId) => relevantClaimIds.has(claimId),
    );
    verifiedClaims += verified.length;
    if (
      input.action.evidenceMode === 'lead_only' &&
      observation.outcome === 'lead_only'
    ) {
      materializedLeadArtifacts += Math.min(
        attemptedHere.length,
        uniqueNonEmpty(observation.producedArtifactIds ?? []).length,
      );
    }
  }

  // Beta(1,1) is intentionally weak: measured observations dominate quickly.
  const successfulOutcomes = verifiedClaims + materializedLeadArtifacts;
  const alpha = 1 + successfulOutcomes;
  const beta = 1 + Math.max(0, attemptedClaims - successfulOutcomes);
  const total = alpha + beta;
  const mean = alpha / total;
  const standardDeviation = Math.sqrt(
    (alpha * beta) / (total * total * (total + 1)),
  );
  return {
    alpha,
    beta,
    verifiedClaims,
    materializedLeadArtifacts,
    successfulOutcomes,
    attemptedClaims,
    mean,
    standardDeviation,
  };
}

function actionExclusionReasons(input: {
  portfolio: ResearchPortfolioInput;
  action: ResearchActionCard;
  remainingClaimIds: Set<string>;
  availableDeeplineCredits: number;
  verifiedClaimIds: Set<string>;
  producedArtifactIds: Set<string>;
}): string[] {
  const reasons: string[] = [];
  const relevantClaims = input.action.producesClaimIds.filter((claimId) =>
    input.remainingClaimIds.has(claimId),
  );
  if (!relevantClaims.length)
    reasons.push('does not advance a remaining claim');
  const missingPrerequisite = (
    input.action.requiresVerifiedClaimIds ?? []
  ).find((claimId) => !input.verifiedClaimIds.has(claimId));
  if (missingPrerequisite) {
    reasons.push(`requires verified claim ${missingPrerequisite}`);
  }
  const missingArtifact = (input.action.requiresArtifactIds ?? []).find(
    (artifactId) => !input.producedArtifactIds.has(artifactId),
  );
  if (missingArtifact) {
    reasons.push(`requires artifact ${missingArtifact}`);
  }
  if (input.action.maximumDeeplineCredits > input.availableDeeplineCredits) {
    reasons.push(
      `maximum cost ${input.action.maximumDeeplineCredits} exceeds available budget ${input.availableDeeplineCredits}`,
    );
  }
  const previousSameAction = currentRowObservations(input.portfolio).some(
    (observation) => observation.actionId === input.action.id,
  );
  if (previousSameAction) {
    reasons.push('already attempted for this row');
  }
  return reasons;
}

/**
 * Rank the next research move using a budgeted contextual UCB objective:
 *
 *   U(a) = D(a) * [Σ gapWeight * evidenceMultiplier * (μ + κσ)]
 *          + diversityBonus - creditPenalty - latencyPenalty
 *
 * D(a) discounts observations from correlated source families. This is a
 * one-step policy by design: execute exactly one literal action, record its
 * observed outcome, then call this function again. That is what lets the
 * policy exploit a good route without assuming provider performance is
 * stationary across industries, geographies, entity types, or claim classes.
 */
export function planResearchPortfolio(
  portfolio: ResearchPortfolioInput,
): ResearchPortfolioPlan {
  const actions = defineResearchActionPortfolio(portfolio.actions);
  const actionsById = new Map(actions.map((action) => [action.id, action]));
  const observations = portfolio.observations.map((observation) => {
    if (
      observation.rowKey === portfolio.rowKey &&
      !observation.contextKey?.trim()
    ) {
      throw new Error(
        'Current-row research action observation needs a contextKey so its spend and prior attempt cannot be ignored.',
      );
    }
    const action = actionsById.get(observation.actionId);
    if (!action) {
      throw new Error(
        `Unknown research portfolio action: ${observation.actionId}.`,
      );
    }
    return validateResearchActionObservation(action, observation, {
      requireContextKey: false,
      enforceActionCostMaximum: false,
    });
  });
  const validatedPortfolio = { ...portfolio, actions, observations };
  if (!portfolio.rowKey.trim() || !portfolio.contextKey.trim()) {
    throw new Error(
      'Research portfolio needs non-empty rowKey and contextKey.',
    );
  }
  if (!isFiniteNonNegative(portfolio.budgetDeeplineCredits)) {
    throw new Error(
      'Research portfolio budgetDeeplineCredits must be finite and non-negative.',
    );
  }
  const reserved = portfolio.reservedDeeplineCredits ?? 0;
  if (
    !isFiniteNonNegative(reserved) ||
    reserved > portfolio.budgetDeeplineCredits
  ) {
    throw new Error('Research portfolio reservedDeeplineCredits is invalid.');
  }
  const remainingRequiredClaimIds = uniqueNonEmpty(
    portfolio.requiredClaimIds,
  ).filter((claimId) => !new Set(portfolio.verifiedClaimIds).has(claimId));
  const rowObservations = currentRowObservations(validatedPortfolio);
  const spentDeeplineCredits = observedResearchSpend(rowObservations);
  const unreservedBudget = portfolio.budgetDeeplineCredits - reserved;
  const availableDeeplineCredits =
    spentDeeplineCredits === null
      ? 0
      : Math.max(0, unreservedBudget - spentDeeplineCredits);
  if (!remainingRequiredClaimIds.length) {
    return {
      type: 'deepline.research_portfolio_plan',
      schemaVersion: 1,
      rowKey: portfolio.rowKey,
      contextKey: portfolio.contextKey,
      remainingRequiredClaimIds,
      spentDeeplineCredits,
      availableDeeplineCredits,
      selectedActionId: null,
      selectedMode: 'stop',
      stopReason: 'all required claims are already verified',
      ranked: [],
      excluded: [],
    };
  }

  const terminalRouteFailure = rowObservations.find(
    (observation) =>
      observation.outcome === 'adapter_failure' ||
      observation.outcome === 'policy_violation',
  );
  if (terminalRouteFailure) {
    return {
      type: 'deepline.research_portfolio_plan',
      schemaVersion: 1,
      rowKey: portfolio.rowKey,
      contextKey: portfolio.contextKey,
      remainingRequiredClaimIds,
      spentDeeplineCredits,
      availableDeeplineCredits: 0,
      selectedActionId: null,
      selectedMode: 'stop',
      stopReason:
        `current-row ${terminalRouteFailure.outcome} on ${terminalRouteFailure.actionId}; ` +
        'budgeted exploration stops until the route is repaired or the cohort advances a replacement row',
      ranked: [],
      excluded: [],
    };
  }

  if (spentDeeplineCredits === null) {
    return {
      type: 'deepline.research_portfolio_plan',
      schemaVersion: 1,
      rowKey: portfolio.rowKey,
      contextKey: portfolio.contextKey,
      remainingRequiredClaimIds,
      spentDeeplineCredits: null,
      availableDeeplineCredits: 0,
      selectedActionId: null,
      selectedMode: 'stop',
      stopReason:
        'a prior current-row action has unknown Deepline credits; budgeted exploration stops rather than treating it as free',
      ranked: [],
      excluded: [],
    };
  }

  if (spentDeeplineCredits > unreservedBudget) {
    return {
      type: 'deepline.research_portfolio_plan',
      schemaVersion: 1,
      rowKey: portfolio.rowKey,
      contextKey: portfolio.contextKey,
      remainingRequiredClaimIds,
      spentDeeplineCredits,
      availableDeeplineCredits: 0,
      selectedActionId: null,
      selectedMode: 'stop',
      stopReason:
        'observed current-row Deepline credits already consume the budget reserve; no further action is admissible',
      ranked: [],
      excluded: [],
    };
  }

  const config = { ...DEFAULT_CONFIG, ...portfolio.config };
  for (const [label, value] of [
    ['explorationWeight', config.explorationWeight],
    ['costPenaltyPerDeeplineCredit', config.costPenaltyPerDeeplineCredit],
    ['durationPenaltyPerMinute', config.durationPenaltyPerMinute],
    ['diversityBonus', config.diversityBonus],
    ['correlationPenalty', config.correlationPenalty],
  ] as const) {
    assertFiniteNonNegative(value, label);
  }
  for (const [claimId, weight] of Object.entries(
    portfolio.config?.claimWeights ?? {},
  )) {
    assertFiniteNonNegative(weight, `claimWeights.${claimId}`);
  }
  const evidenceMultiplier = {
    ...DEFAULT_EVIDENCE_MODE_MULTIPLIER,
    ...portfolio.config?.evidenceModeMultiplier,
  };
  for (const [mode, multiplier] of Object.entries(evidenceMultiplier)) {
    if (!isFiniteNonNegative(multiplier)) {
      throw new Error(
        `Research portfolio evidence multiplier for ${mode} is invalid.`,
      );
    }
  }
  const remainingClaimSet = new Set(remainingRequiredClaimIds);
  const verifiedClaimSet = new Set(portfolio.verifiedClaimIds);
  const contextObservations = rowObservations;
  const attemptsByCorrelationGroup = new Map<string, number>();
  for (const observation of contextObservations) {
    const action = actions.find(
      (candidate) => candidate.id === observation.actionId,
    );
    if (!action) continue;
    attemptsByCorrelationGroup.set(
      action.correlationGroup,
      (attemptsByCorrelationGroup.get(action.correlationGroup) ?? 0) + 1,
    );
  }
  const producedArtifactIds = new Set(
    contextObservations.flatMap(
      (observation) => observation.producedArtifactIds ?? [],
    ),
  );

  const excluded: Array<{ actionId: string; reasons: string[] }> = [];
  const ranked: ResearchPortfolioDecision[] = [];
  for (const action of actions) {
    const reasons = actionExclusionReasons({
      portfolio: validatedPortfolio,
      action,
      remainingClaimIds: remainingClaimSet,
      availableDeeplineCredits,
      verifiedClaimIds: verifiedClaimSet,
      producedArtifactIds,
    });
    if (reasons.length) {
      excluded.push({ actionId: action.id, reasons });
      continue;
    }
    const claimGapIds = action.producesClaimIds.filter((claimId) =>
      remainingClaimSet.has(claimId),
    );
    const posterior = summarizeResearchActionPosterior({
      action,
      observations: matchingObservations(validatedPortfolio, action),
      relevantClaimIds: claimGapIds,
    });
    const claimWeight = claimGapIds.reduce(
      (total, claimId) =>
        total + (portfolio.config?.claimWeights?.[claimId] ?? 1),
      0,
    );
    const expectedVerifiedClaimUtility =
      claimWeight * posterior.mean * evidenceMultiplier[action.evidenceMode];
    const uncertaintyUtility =
      claimWeight * posterior.standardDeviation * config.explorationWeight;
    const correlatedAttempts =
      attemptsByCorrelationGroup.get(action.correlationGroup) ?? 0;
    const correlationDiscount = Math.exp(
      -config.correlationPenalty * correlatedAttempts,
    );
    const diversityUtility =
      correlatedAttempts === 0 ? config.diversityBonus : 0;
    const costPenalty =
      action.maximumDeeplineCredits * config.costPenaltyPerDeeplineCredit;
    const durationPenalty =
      ((action.expectedDurationMs ?? 0) / 60_000) *
      config.durationPenaltyPerMinute;
    const netUtility =
      correlationDiscount *
        (expectedVerifiedClaimUtility + uncertaintyUtility) +
      diversityUtility -
      costPenalty -
      durationPenalty;
    const mode: 'explore' | 'exploit' =
      correlatedAttempts === 0 && attemptsByCorrelationGroup.size > 0
        ? 'explore'
        : 'exploit';
    ranked.push({
      actionId: action.id,
      sourceFamily: action.sourceFamily,
      correlationGroup: action.correlationGroup,
      stage: action.stage,
      claimGapIds,
      maximumDeeplineCredits: action.maximumDeeplineCredits,
      expectedDurationMs: action.expectedDurationMs ?? null,
      posterior,
      expectedVerifiedClaimUtility,
      uncertaintyUtility,
      diversityUtility,
      correlationDiscount,
      costPenalty,
      durationPenalty,
      netUtility,
      mode,
      rationale:
        `${action.hypothesis} Targets ${claimGapIds.join(', ')}; ` +
        `posterior mean ${posterior.mean.toFixed(3)}, uncertainty ${posterior.standardDeviation.toFixed(3)}, ` +
        `correlation discount ${correlationDiscount.toFixed(3)}.`,
    });
  }
  ranked.sort(
    (left, right) =>
      right.netUtility - left.netUtility ||
      right.expectedVerifiedClaimUtility - left.expectedVerifiedClaimUtility ||
      left.maximumDeeplineCredits - right.maximumDeeplineCredits ||
      left.actionId.localeCompare(right.actionId),
  );
  const selected = ranked.find((decision) => decision.netUtility > 0) ?? null;
  return {
    type: 'deepline.research_portfolio_plan',
    schemaVersion: 1,
    rowKey: portfolio.rowKey,
    contextKey: portfolio.contextKey,
    remainingRequiredClaimIds,
    spentDeeplineCredits,
    availableDeeplineCredits,
    selectedActionId: selected?.actionId ?? null,
    selectedMode: selected?.mode ?? 'stop',
    stopReason: selected
      ? null
      : ranked.length
        ? 'no admissible action has positive expected marginal utility under the remaining budget'
        : 'no action can advance a remaining claim within the remaining budget and prerequisites',
    ranked,
    excluded,
  };
}

/**
 * Validate and append a durable observation after the literal action has run.
 * The caller still binds evidence and evaluates claims through
 * research-experiment.ts; this function records only strategy telemetry.
 */
function validateResearchActionObservation(
  action: ResearchActionCard,
  observation: ResearchActionObservation,
  options: {
    requireContextKey?: boolean;
    enforceActionCostMaximum?: boolean;
  } = {},
): ResearchActionObservation {
  if (!observation.rowKey.trim()) {
    throw new Error('Research action observation needs a rowKey.');
  }
  if (options.requireContextKey !== false && !observation.contextKey?.trim()) {
    throw new Error('Research action observation needs a contextKey.');
  }
  if (!RESEARCH_ACTION_OUTCOMES.has(observation.outcome)) {
    throw new Error('Research action observation has an invalid outcome.');
  }
  const verifiedClaimIds = uniqueNonEmpty(observation.verifiedClaimIds ?? []);
  if (action.evidenceMode === 'lead_only' && verifiedClaimIds.length) {
    throw new Error(
      `Lead-only research action ${action.id} cannot record verified claims.`,
    );
  }
  if (
    action.evidenceMode === 'lead_only' &&
    observation.outcome === 'verified'
  ) {
    throw new Error(
      `Lead-only research action ${action.id} cannot record a verified outcome.`,
    );
  }
  if (observation.outcome === 'verified' && !verifiedClaimIds.length) {
    throw new Error(
      `Research action ${action.id} needs verifiedClaimIds for a verified outcome.`,
    );
  }
  if (observation.outcome !== 'verified' && verifiedClaimIds.length) {
    throw new Error(
      `Research action ${action.id} can record verified claims only for a verified outcome.`,
    );
  }
  const invalidClaim = verifiedClaimIds.find(
    (claimId) => !action.producesClaimIds.includes(claimId),
  );
  if (invalidClaim) {
    throw new Error(
      `Research action ${action.id} cannot record undeclared verified claim ${invalidClaim}.`,
    );
  }
  const producedArtifactIds = uniqueNonEmpty(
    observation.producedArtifactIds ?? [],
  );
  const invalidArtifact = producedArtifactIds.find(
    (artifactId) => !action.producesArtifactIds?.includes(artifactId),
  );
  if (invalidArtifact) {
    throw new Error(
      `Research action ${action.id} cannot record undeclared artifact ${invalidArtifact}.`,
    );
  }
  if (observation.outcome === 'lead_only' && !producedArtifactIds.length) {
    throw new Error(
      `Lead-only research action ${action.id} needs producedArtifactIds for a lead-only outcome.`,
    );
  }
  if (
    producedArtifactIds.length &&
    observation.outcome !== 'verified' &&
    observation.outcome !== 'lead_only'
  ) {
    throw new Error(
      `Research action ${action.id} cannot record artifacts for a ${observation.outcome} outcome.`,
    );
  }
  if (
    observation.observedDeeplineCredits !== undefined &&
    observation.observedDeeplineCredits !== null &&
    !isFiniteNonNegative(observation.observedDeeplineCredits)
  ) {
    throw new Error(
      'Research action observation has invalid observedDeeplineCredits.',
    );
  }
  if (
    observation.observedDeeplineCredits !== undefined &&
    observation.observedDeeplineCredits !== null &&
    options.enforceActionCostMaximum !== false &&
    observation.observedDeeplineCredits > action.maximumDeeplineCredits
  ) {
    throw new Error(
      `Research action ${action.id} observed Deepline credits exceed its declared maximum.`,
    );
  }
  if (
    observation.observedDurationMs !== undefined &&
    observation.observedDurationMs !== null &&
    !isFiniteNonNegative(observation.observedDurationMs)
  ) {
    throw new Error(
      'Research action observation has invalid observedDurationMs.',
    );
  }
  return {
    ...observation,
    ...(verifiedClaimIds.length ? { verifiedClaimIds } : {}),
    ...(producedArtifactIds.length ? { producedArtifactIds } : {}),
  };
}

export function recordResearchActionObservation(input: {
  actions: readonly ResearchActionCard[];
  observations: readonly ResearchActionObservation[];
  observation: ResearchActionObservation;
}): ResearchActionObservation[] {
  const actions = defineResearchActionPortfolio(input.actions);
  const action = actions.find(
    (candidate) => candidate.id === input.observation.actionId,
  );
  if (!action) {
    throw new Error(
      `Unknown research portfolio action: ${input.observation.actionId}.`,
    );
  }
  return [
    ...input.observations,
    validateResearchActionObservation(action, input.observation),
  ];
}
