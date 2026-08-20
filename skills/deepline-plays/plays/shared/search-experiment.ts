/**
 * Dataset-conditioned explore/exploit orchestration for agent-authored Plays.
 *
 * The agent supplies claim contracts and a broad pool of literal programs.
 * This helper chooses a bounded heterogeneous wave, closes only the remaining
 * evidence gaps, confirms the learned order on untouched rows, and then
 * exploits it. Provider choice and semantic acceptance remain authored;
 * scheduling, accounting, and promotion are deterministic.
 */

import {
  evaluateResearchClaimValues,
  isValidatedResearchClaimEvaluation,
  type ResearchClaim,
  type ResearchClaimGap,
  type ResearchClaimValue,
  type ValidatedClaimEvaluation,
} from './research-experiment';

type JsonRow = Record<string, unknown>;

const MAX_LIVE_CHALLENGES_PER_PROGRAM = 2;
const MAX_LIVE_CHALLENGES_PER_PROVEN_PROGRAM =
  MAX_LIVE_CHALLENGES_PER_PROGRAM + 1;
const DEFAULT_EXPLOIT_BATCH_SIZE = 8;
const DEFAULT_EXPLORATION_PROGRAM_COUNT = 3;
const DEFAULT_CHALLENGE_WAVE_SIZE = 3;
/** Marks a candidate rejected by a cross-claim coherence gate. */
const INCOHERENT_FAILURE_PREFIX = 'incoherent:';
/**
 * Hard ceiling on the dependency-closed waterfall. Portfolio selection
 * enumerates every subset up to this size, so the bound is combinatorial, not
 * stylistic: at 4 a twelve-program pool already enumerates 793 portfolios.
 * Raising it further needs a different selection algorithm, not a bigger number.
 */
const MAX_ALLOWED_FALLBACKS = 4;
/**
 * Loud guard so a wide pool plus a raised cap cannot turn selection into a
 * hang. Enumeration actually runs over the programs that were *observed*, which
 * is normally far fewer than the registered pool, so this pool-level bound is a
 * conservative backstop: it admits the existing 100-program × maxFallbacks-2
 * case (5,050 subsets) and rejects 100 × 3 (166,750).
 */
const MAX_ENUMERATED_PORTFOLIOS = 20_000;

export type SearchExperimentPhase =
  | 'comparison'
  | 'pilot'
  | 'holdout'
  | 'challenge'
  | 'exploit';

export type SearchProgramResult = {
  resultKey: string;
  /** Provider-independent identity: canonical URL, domain, or task-specific key. */
  canonicalEntityKey: string;
  claims: Readonly<Record<string, ResearchClaimValue | undefined>>;
  eligible?: boolean;
  hardCheckFailures?: readonly string[];
  contradiction?: boolean;
};

export type SearchProgramAttempt = {
  results: readonly SearchProgramResult[];
  /** Actual calls observed by this program invocation. Unknown spend is not a call count. */
  totalCalls: number;
  /**
   * Deepline credits attributed by the tool receipt or run ledger. Leave this
   * unset when attribution is unavailable; unknown cost is never scored as 0.
   */
  deeplineCredits?: number | null;
};

export type SearchProgramInput<Row extends JsonRow, Context> = {
  ctx: Context;
  row: Row;
  unitKey: string;
  phase: SearchExperimentPhase;
  /** Only claims still useful for this unit are presented to later programs. */
  gaps: readonly ResearchClaimGap[];
  candidates: readonly SearchLedgerResult<Row>[];
  remainingTargetRows: number;
};

export type SearchProgram<Row extends JsonRow, Context> = {
  id: string;
  hypothesis: string;
  /**
   * The best route known before this dataset-conditioned experiment. It is
   * always included in the first shared wave, then must earn promotion on the
   * same evidence and cost contract as every challenger.
   */
  incumbent?: boolean;
  /**
   * Durable information-shape tags, not provider names. Examples:
   * structured-index, pivot:name+domain, first-party-web, role:verifier.
   * The helper covers as many distinct tags as possible in each bounded wave.
   */
  diversityFeatures?: readonly string[];
  /** Hard per-invocation ceiling. The helper rejects an over-cap result. */
  maximumCallsPerAttempt: number;
  /** Catalog/quote ceiling used only when this attempt has no cost receipt. */
  maximumDeeplineCreditsPerAttempt?: number;
  /** Live catalog pricing unit. A result-priced source miss is known to cost zero. */
  billingUnit?: 'call' | 'result' | 'unknown';
  /**
   * Catalog tool ids this program calls, exactly as `tools describe` names them.
   * The run's billing breakdown is keyed by the same operation id, so declaring
   * them here is what turns the scorecard's cost column from a catalog bound
   * into observed credits after the run. Leave unset for a program that calls no
   * Deepline tool (a direct fetch, a local artifact, deterministic code).
   */
  tools?: readonly string[];
  run(input: SearchProgramInput<Row, Context>): Promise<SearchProgramAttempt>;
};

export type SearchCohortCheck = {
  id: string;
  minimumRatio: number;
  denominator: 'pilot_units' | 'eligible_results' | 'complete_results';
  /** A cohort member passes only when this claim has a validated receipt. */
  verifiedClaimId: string;
};

/**
 * A cross-claim gate. Every claim validates in isolation, so a candidate can
 * satisfy each `accept` while describing two different entities — a practice
 * name from one org beside a website belonging to another. This hook is the
 * only place that sees a candidate's verified claims together.
 *
 * Return `null` to accept, or a short reason to reject. A rejection records
 * `incoherent:<id>` as a hard check failure, which keeps the candidate visible
 * as a tested rejection and reopens the unit for another program.
 */
export type SearchCoherenceCheck<Row extends JsonRow> = {
  id: string;
  check(input: {
    row: Row;
    unitKey: string;
    canonicalEntityKey: string;
    /** Verified claim values only, keyed by claim id. Unverified claims are absent. */
    verified: Readonly<Record<string, unknown>>;
  }): string | null;
};

export type SearchExperimentContract<Row extends JsonRow> = {
  rowKey: keyof Row & string;
  /** Explicit stopping count. Omit to maximize coverage across every supplied row. */
  targetRows?: number;
  claims: readonly ResearchClaim<Row>[];
  /** Cross-claim gates run after per-claim validation. See SearchCoherenceCheck. */
  coherenceChecks?: readonly SearchCoherenceCheck<Row>[];
  cohortChecks?: readonly SearchCohortCheck[];
  minimumCompleteResultsPerUnit?: number;
  minimumPilotCompleteRows?: number;
  minimumHoldoutCompleteRows?: number;
};

export type SearchExperimentDefinition<Row extends JsonRow, Context> = {
  contract: SearchExperimentContract<Row>;
  programs: readonly SearchProgram<Row, Context>[];
  /** Defaults to two. Set to one only for a route already proven deterministic. */
  minimumExplorationPrograms?: number;
  pilotUnitCount?: number;
  comparisonUnitCount?: number;
  holdoutUnitCount?: number;
  /** Optional alternatives beyond any candidate producers required by a winner. */
  maxFallbacks?: number;
  /** Programs run in the first shared wave; the rest remain dormant challengers. */
  explorationProgramCount?: number;
  /** Dormant programs compared concurrently on one unresolved unit. */
  challengeWaveSize?: number;
  /** Maximum rows started concurrently while exploiting a learned program. */
  exploitBatchSize?: number;
  /** Conservative whole-experiment Deepline-credit ceiling. */
  maximumDeeplineCredits?: number;
};

export type DatasetFieldSketch = {
  field: string;
  present: number;
  missing: number;
  distinct: number;
  types: string[];
};

export type DatasetSketch = {
  rowCount: number;
  fields: DatasetFieldSketch[];
  pilotUnitKeys: string[];
  comparisonUnitKeys: string[];
  holdoutUnitKeys: string[];
  exploitUnitKeys: string[];
};

export type SearchAttemptTrace = {
  phase: SearchExperimentPhase;
  programId: string;
  unitKey: string;
  gapsBefore: string[];
  outcome: 'verified' | 'rejected' | 'source_miss' | 'adapter_failure';
  totalCalls: number;
  deeplineCredits: number | null;
  resultIdentities: string[];
  verifiedClaimDelta: number;
  completeResultDelta: number;
  error?: string;
};

export type SearchLedgerResult<Row extends JsonRow> = {
  identity: string;
  unitKey: string;
  canonicalEntityKey: string;
  row: Row;
  eligible: boolean;
  complete: boolean;
  contradiction: boolean;
  hardCheckFailures: string[];
  claimEvaluations: ValidatedClaimEvaluation[];
  programIds: string[];
};

/** Read one accepted claim without inspecting the experiment's internal receipt shape. */
export function verifiedSearchClaimValue<Value = unknown>(
  result: Pick<SearchLedgerResult<JsonRow>, 'claimEvaluations'>,
  claimId: string,
): Value | null {
  const evaluation = result.claimEvaluations.find(
    (candidate) => candidate.claimId === claimId,
  );
  return evaluation?.status === 'verified' ? (evaluation.value as Value) : null;
}

/**
 * Whether a registered program ever got a chance to produce evidence.
 * `never_reached` is not a source miss: the source was never asked. Reporting
 * the two as one number is how a structurally unreachable route gets read as a
 * measured coverage ceiling.
 */
export type SearchProgramReachability = 'ran' | 'never_reached';

export type SearchProgramScore = {
  programId: string;
  /** Invocations of this program across every phase. Zero means never reached. */
  attempts: number;
  reachability: SearchProgramReachability;
  completeResults: number;
  unitsWithCompleteResults: number;
  verifiedRequiredClaims: number;
  supportedEvidenceAtoms: number;
  totalCalls: number;
  callsPerVerifiedRequiredClaim: number;
  deeplineCredits: number | null;
  deeplineCreditsPerVerifiedRequiredClaim: number | null;
  costCredits: number | null;
  costCreditsPerVerifiedRequiredClaim: number | null;
  costBasis: SearchCostBasis;
  unobservedCreditAttempts: number;
  sourceMisses: number;
  adapterFailures: number;
  incoherentResults: number;
  evidenceLineages: string[];
  /**
   * Declared catalog tool ids, for the post-run observed-credit join.
   * `null` means the program declared nothing, so its spend is unknown; an
   * empty array is the author asserting this route calls no Deepline tool.
   */
  toolIds: string[] | null;
};

/**
 * Stable, export-friendly route metrics for the scorecard dataset a Play
 * returns beside final rows. This is diagnostic evidence for an eval, never a
 * replacement for the hard claim and cohort gates used by selection.
 *
 * `deepline_credits` is only populated when the attempt carried a receipt.
 * `tool_ids` exists so `cost-receipt.py` can join the run's billing breakdown
 * onto these rows after the run and produce observed per-route credits — a
 * scorecard whose cost column is empty cannot rank routes by cost, which is
 * the whole reason it exists.
 */
export function routeScorecardRows(
  scorecard: readonly SearchProgramScore[],
): Array<Record<string, string | number | null>> {
  return scorecard.map((score) => ({
    program_id: score.programId,
    attempts: score.attempts,
    reachability: score.reachability,
    complete_results: score.completeResults,
    verified_required_claims: score.verifiedRequiredClaims,
    source_misses: score.sourceMisses,
    incoherent_results: score.incoherentResults,
    adapter_failures: score.adapterFailures,
    total_calls: score.totalCalls,
    deepline_credits: score.deeplineCredits,
    cost_basis: score.costBasis,
    // '' = undeclared, so this route's spend is unknown. 'none' = the author
    // asserted it calls no Deepline tool, so zero is a fact, not a gap.
    tool_ids:
      score.toolIds === null
        ? ''
        : score.toolIds.length
          ? score.toolIds.join(' | ')
          : 'none',
    evidence_lineages: score.evidenceLineages.join(' | '),
  }));
}

export type SearchCostBasis = 'observed' | 'catalog_upper_bound' | 'unknown';

export type SearchAdaptationTrace = {
  unitKey: string;
  beforeProgramIds: string[];
  challengedProgramIds: string[];
  promotedProgramIds: string[];
  afterProgramIds: string[];
  reason: string;
};

export type SearchExperimentLeverage = {
  completeResults: number;
  totalCalls: number;
  exhaustiveCallBaseline: number;
  avoidedCalls: number;
  avoidedCallRatio: number;
  deeplineCredits: number | null;
  unobservedCreditAttempts: number;
  completeResultsPerDeeplineCredit: number | null;
};

/**
 * A non-dominated option observed during the shared comparison wave.
 * Coverage already includes every claim's evidence/consensus contract, so a
 * cheaper point cannot "win" by weakening verification.
 */
export type SearchCostCoveragePoint = {
  programIds: string[];
  completeResults: number;
  verifiedRequiredClaims: number;
  passedCohortChecks: number;
  cohortRatioTotal: number;
  cohortNumeratorTotal: number;
  totalCalls: number;
  observedDeeplineCredits: number | null;
  costCredits: number | null;
  costBasis: SearchCostBasis;
  completeResultsPerCostCredit: number | null;
  /** Won the common comparison wave; later pilot/holdout evidence may change the waterfall. */
  comparisonWinner: boolean;
};

export type SearchCohortResult = SearchCohortCheck & {
  numerator: number;
  denominatorCount: number;
  ratio: number;
  pass: boolean;
};

export type SearchExperimentResult<Row extends JsonRow> = {
  status: 'promoted' | 'not_promoted';
  stoppingReason:
    | 'target_reached'
    | 'programs_exhausted'
    | 'adapter_failures'
    | 'budget_exhausted'
    | 'selection_failed';
  /** Resolved stopping count: the authored target or every supplied row. */
  targetRows: number;
  sketch: DatasetSketch;
  registeredProgramCount: number;
  exploredProgramIds: string[];
  /** Programs whose adapter failed on a unit that remains unresolved. */
  failedProgramIds: string[];
  remainingProgramIds: string[];
  unresolvedUnitKeys: string[];
  selectedProgramIds: string[];
  initialSelectedProgramIds: string[];
  scorecard: SearchProgramScore[];
  attempts: SearchAttemptTrace[];
  adaptations: SearchAdaptationTrace[];
  pilotResults: SearchLedgerResult<Row>[];
  holdoutResults: SearchLedgerResult<Row>[];
  finalResults: SearchLedgerResult<Row>[];
  pilotCohortChecks: SearchCohortResult[];
  holdoutCohortChecks: SearchCohortResult[];
  finalCohortChecks: SearchCohortResult[];
  holdoutPassed: boolean;
  totalCalls: number;
  estimatedDeeplineCredits: number | null;
  maximumDeeplineCredits: number | null;
  exhaustiveComparisonCalls: number;
  avoidedCalls: number;
  leverage: SearchExperimentLeverage;
  /** Fair alternatives from the common comparison wave, not uneven exploit history. */
  costCoverageFrontier: SearchCostCoveragePoint[];
  rationale: string[];
};

type ClaimContribution = {
  programId: string;
  claim: ResearchClaimValue;
};

type LedgerEntry<Row extends JsonRow> = {
  identity: string;
  unitKey: string;
  canonicalEntityKey: string;
  row: Row;
  eligible: boolean;
  contradiction: boolean;
  hardCheckFailures: Set<string>;
  programIds: Set<string>;
  claims: Map<string, ClaimContribution[]>;
};

type AttemptRecord<Row extends JsonRow> = {
  phase: SearchExperimentPhase;
  programId: string;
  unitKey: string;
  row: Row;
  attempt?: SearchProgramAttempt;
  error?: string;
  observedTotalCalls: number;
  observedDeeplineCredits: number | null;
  gapsBefore: string[];
  candidateStateBefore: string;
  candidateProgramIdsBefore: string[];
  candidateDependenciesBefore: Array<{
    identity: string;
    programIds: string[];
  }>;
};

function normalize(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function canonicalText(value: string): string {
  return value.trim().replace(/\s+/g, ' ');
}

function unique<T>(values: readonly T[]): T[] {
  return [...new Set(values)];
}

function programDiversityFeatures<Row extends JsonRow, Context>(
  program: SearchProgram<Row, Context>,
): string[] {
  const declared = unique(
    (program.diversityFeatures ?? [])
      .map(normalize)
      .filter((feature) => feature.length > 0),
  ).sort();
  return declared.length ? declared : [`program:${normalize(program.id)}`];
}

/**
 * Greedy maximum coverage over authored information features. The pool may be
 * large; execution remains bounded. Novel information shape wins first, then
 * a known lower Deepline-credit ceiling, then stable program ID.
 */
export function selectHeterogeneousPrograms<
  Row extends JsonRow,
  Context,
>(input: {
  programs: readonly SearchProgram<Row, Context>[];
  count: number;
  against?: readonly SearchProgram<Row, Context>[];
}): SearchProgram<Row, Context>[] {
  const remaining = [...input.programs];
  const selected: SearchProgram<Row, Context>[] = [];
  const covered = new Set(
    (input.against ?? []).flatMap((program) =>
      programDiversityFeatures(program),
    ),
  );
  const count = Math.max(0, Math.min(input.count, remaining.length));
  const incumbentIndex = remaining.findIndex((program) => program.incumbent);
  if (count > 0 && incumbentIndex >= 0) {
    const [incumbent] = remaining.splice(incumbentIndex, 1);
    selected.push(incumbent!);
    programDiversityFeatures(incumbent!).forEach((feature) =>
      covered.add(feature),
    );
  }
  while (selected.length < count) {
    remaining.sort((left, right) => {
      const leftNovel = programDiversityFeatures(left).filter(
        (feature) => !covered.has(feature),
      ).length;
      const rightNovel = programDiversityFeatures(right).filter(
        (feature) => !covered.has(feature),
      ).length;
      if (leftNovel !== rightNovel) return rightNovel - leftNovel;
      const leftKnown = left.maximumDeeplineCreditsPerAttempt !== undefined;
      const rightKnown = right.maximumDeeplineCreditsPerAttempt !== undefined;
      if (leftKnown !== rightKnown) return leftKnown ? -1 : 1;
      const leftCost =
        left.maximumDeeplineCreditsPerAttempt ?? Number.POSITIVE_INFINITY;
      const rightCost =
        right.maximumDeeplineCreditsPerAttempt ?? Number.POSITIVE_INFINITY;
      return leftCost - rightCost || left.id.localeCompare(right.id);
    });
    const winner = remaining.shift()!;
    selected.push(winner);
    programDiversityFeatures(winner).forEach((feature) => covered.add(feature));
  }
  return selected;
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function validateProgramAttempt(
  programId: string,
  value: unknown,
): asserts value is SearchProgramAttempt {
  if (!isObjectRecord(value)) {
    throw new Error(`Search program ${programId} returned an invalid attempt.`);
  }
  if (!Array.isArray(value.results)) {
    throw new Error(
      `Search program ${programId} returned results that are not an array.`,
    );
  }
  const identities = new Set<string>();
  value.results.forEach((candidate, index) => {
    if (!isObjectRecord(candidate)) {
      throw new Error(
        `Search program ${programId} returned an invalid result at index ${index}.`,
      );
    }
    if (
      typeof candidate.resultKey !== 'string' ||
      !candidate.resultKey.trim() ||
      typeof candidate.canonicalEntityKey !== 'string' ||
      !candidate.canonicalEntityKey.trim()
    ) {
      throw new Error(
        `Search program ${programId} emitted an unkeyed result at index ${index}.`,
      );
    }
    if (!isObjectRecord(candidate.claims)) {
      throw new Error(
        `Search program ${programId} returned invalid claims at index ${index}.`,
      );
    }
    if (
      candidate.eligible !== undefined &&
      typeof candidate.eligible !== 'boolean'
    ) {
      throw new Error(
        `Search program ${programId} returned invalid eligibility at index ${index}.`,
      );
    }
    if (
      candidate.contradiction !== undefined &&
      typeof candidate.contradiction !== 'boolean'
    ) {
      throw new Error(
        `Search program ${programId} returned invalid contradiction state at index ${index}.`,
      );
    }
    if (
      candidate.hardCheckFailures !== undefined &&
      (!Array.isArray(candidate.hardCheckFailures) ||
        candidate.hardCheckFailures.some(
          (failure) => typeof failure !== 'string',
        ))
    ) {
      throw new Error(
        `Search program ${programId} returned invalid hard-check failures at index ${index}.`,
      );
    }
    const identity = canonicalText(candidate.canonicalEntityKey);
    if (identities.has(identity)) {
      throw new Error(
        `Search program ${programId} emitted duplicate result ${identity}.`,
      );
    }
    identities.add(identity);
  });
}

function stableValue(value: unknown, ancestors = new Set<object>()): string {
  if (value === null) return 'null';
  switch (typeof value) {
    case 'undefined':
      return 'undefined';
    case 'string':
      return `string:${JSON.stringify(value)}`;
    case 'number':
      return `number:${Object.is(value, -0) ? '-0' : String(value)}`;
    case 'boolean':
      return `boolean:${value}`;
    case 'bigint':
      return `bigint:${value}`;
    case 'function':
    case 'symbol':
      throw new Error('Search experiment values must be JSON-like data.');
    case 'object': {
      if (ancestors.has(value)) {
        throw new Error('Search experiment values must not be cyclic.');
      }
      ancestors.add(value);
      const rendered = Array.isArray(value)
        ? `array:[${value.map((item) => stableValue(item, ancestors)).join(',')}]`
        : `object:{${Object.entries(value as JsonRow)
            .sort(([left], [right]) => left.localeCompare(right))
            .map(
              ([key, item]) =>
                `${JSON.stringify(key)}:${stableValue(item, ancestors)}`,
            )
            .join(',')}}`;
      ancestors.delete(value);
      return rendered;
    }
    default:
      throw new Error('Search experiment values must be JSON-like data.');
  }
}

function candidateState<Row extends JsonRow>(
  candidates: readonly SearchLedgerResult<Row>[],
): string {
  return stableValue(
    candidates.map((candidate) => ({
      identity: candidate.identity,
      eligible: candidate.eligible,
      complete: candidate.complete,
      contradiction: candidate.contradiction,
      hardCheckFailures: candidate.hardCheckFailures,
      claims: candidate.claimEvaluations.map((claim) => ({
        claimId: claim.claimId,
        status: claim.status,
        value: claim.value,
        evidenceCount: claim.evidence.length,
        independenceClasses: claim.independentEvidenceClasses,
      })),
    })),
  );
}

function candidateDependencies<Row extends JsonRow>(
  candidates: readonly SearchLedgerResult<Row>[],
): AttemptRecord<Row>['candidateDependenciesBefore'] {
  return candidates.map((candidate) => ({
    identity: candidate.identity,
    programIds: [...candidate.programIds],
  }));
}

function trackCandidateReads<Row extends JsonRow>(
  candidates: readonly SearchLedgerResult<Row>[],
): {
  candidates: readonly SearchLedgerResult<Row>[];
  consumedIdentities: Set<string>;
} {
  const consumedIdentities = new Set<string>();
  const tracked = new Proxy(candidates, {
    get(target, property, receiver) {
      if (property === 'length') {
        target.forEach((candidate) =>
          consumedIdentities.add(candidate.identity),
        );
      }
      if (property === Symbol.iterator) {
        return function* iterator() {
          for (const candidate of target) {
            consumedIdentities.add(candidate.identity);
            yield candidate;
          }
        };
      }
      if (typeof property === 'string' && /^\d+$/.test(property)) {
        const candidate = target[Number(property)];
        if (candidate) consumedIdentities.add(candidate.identity);
      }
      return Reflect.get(target, property, receiver);
    },
  });
  return { candidates: tracked, consumedIdentities };
}

export function searchResultIdentity(
  unitKey: string,
  canonicalEntityKey: string,
): string {
  return JSON.stringify([
    normalize(unitKey),
    canonicalText(canonicalEntityKey),
  ]);
}

function claimReceiptScope(identity: string): string {
  return `deepline.search-experiment:${identity}`;
}

function rowKey<Row extends JsonRow>(
  row: Row,
  field: keyof Row & string,
): string {
  const value = row[field];
  const key =
    typeof value === 'string' ? value.trim() : String(value ?? '').trim();
  if (!key) throw new Error(`Search experiment row is missing ${field}.`);
  return key;
}

function valueType(value: unknown): string {
  return value === null
    ? 'null'
    : Array.isArray(value)
      ? 'array'
      : typeof value;
}

function normalizedScalar(value: unknown): string | null {
  if (typeof value === 'string') return normalize(value).slice(0, 120);
  if (typeof value === 'number' || typeof value === 'boolean')
    return String(value);
  return null;
}

function rowTokens<Row extends JsonRow>(
  rows: readonly Row[],
): Map<Row, Set<string>> {
  const fields = unique(rows.flatMap((row) => Object.keys(row))).sort();
  const distinct = new Map<string, Set<string>>();
  for (const field of fields) {
    distinct.set(
      field,
      new Set(
        rows
          .map((row) => normalizedScalar(row[field]))
          .filter((value): value is string => value !== null),
      ),
    );
  }
  return new Map(
    rows.map((row) => {
      const tokens = new Set<string>();
      for (const field of fields) {
        const value = row[field];
        if (value === undefined || value === null || value === '') {
          tokens.add(`${field}:missing`);
          continue;
        }
        const type = valueType(value);
        tokens.add(`${field}:type:${type}`);
        const scalar = normalizedScalar(value);
        if (scalar !== null && (distinct.get(field)?.size ?? 0) <= 12) {
          tokens.add(`${field}:value:${scalar}`);
        }
        if (typeof value === 'string') {
          tokens.add(
            `${field}:length:${value.length < 16 ? 'short' : value.length < 64 ? 'medium' : 'long'}`,
          );
          try {
            const parsed = new URL(value);
            tokens.add(`${field}:host:${parsed.hostname.toLowerCase()}`);
          } catch {
            // Most strings are not URLs. Their field/value/type tokens suffice.
          }
        }
      }
      return [row, tokens] as const;
    }),
  );
}

function jaccardDistance(left: Set<string>, right: Set<string>): number {
  const union = new Set([...left, ...right]);
  if (!union.size) return 0;
  let intersection = 0;
  for (const token of left) if (right.has(token)) intersection += 1;
  return 1 - intersection / union.size;
}

/** Deterministically choose rows that expose different missingness and value shapes. */
export function selectDiverseRows<Row extends JsonRow>(input: {
  rows: readonly Row[];
  rowKey: keyof Row & string;
  count: number;
}): Row[] {
  if (!Number.isInteger(input.count) || input.count < 0) {
    throw new Error('Diverse-row count must be a non-negative integer.');
  }
  if (!input.count || !input.rows.length) return [];
  const keys = input.rows.map((row) => rowKey(row, input.rowKey));
  if (unique(keys.map(normalize)).length !== keys.length) {
    throw new Error(
      'Search experiment row keys must be unique after normalization.',
    );
  }
  const tokens = rowTokens(input.rows);
  const frequencies = new Map<string, number>();
  for (const rowTokenSet of tokens.values()) {
    for (const token of rowTokenSet) {
      frequencies.set(token, (frequencies.get(token) ?? 0) + 1);
    }
  }
  const rarity = (row: Row): number =>
    [...tokens.get(row)!].reduce(
      (score, token) => score + 1 / (frequencies.get(token) ?? 1),
      0,
    );
  const remaining = [...input.rows].sort((left, right) => {
    const difference = rarity(right) - rarity(left);
    return (
      difference ||
      rowKey(left, input.rowKey).localeCompare(rowKey(right, input.rowKey))
    );
  });
  const selected: Row[] = [];
  const covered = new Set<string>();
  while (
    remaining.length &&
    selected.length < Math.min(input.count, input.rows.length)
  ) {
    remaining.sort((left, right) => {
      const score = (row: Row): number => {
        const rowTokenSet = tokens.get(row)!;
        const distance = selected.length
          ? Math.min(
              ...selected.map((item) =>
                jaccardDistance(rowTokenSet, tokens.get(item)!),
              ),
            )
          : 1;
        const novelty = [...rowTokenSet].reduce(
          (total, token) =>
            total +
            (covered.has(token) ? 0 : 1 / (frequencies.get(token) ?? 1)),
          0,
        );
        return distance * 1000 + novelty;
      };
      const difference = score(right) - score(left);
      return (
        difference ||
        rowKey(left, input.rowKey).localeCompare(rowKey(right, input.rowKey))
      );
    });
    const winner = remaining.shift()!;
    selected.push(winner);
    for (const token of tokens.get(winner)!) covered.add(token);
  }
  return selected;
}

function validateDefinition<Row extends JsonRow, Context>(
  definition: SearchExperimentDefinition<Row, Context>,
  rows: readonly Row[],
): void {
  if (!rows.length)
    throw new Error('Search experiment needs at least one row.');
  const { contract, programs } = definition;
  if (
    contract.targetRows !== undefined &&
    (!Number.isInteger(contract.targetRows) || contract.targetRows < 1)
  ) {
    throw new Error('targetRows must be a positive integer.');
  }
  if (
    definition.maximumDeeplineCredits !== undefined &&
    (!Number.isFinite(definition.maximumDeeplineCredits) ||
      definition.maximumDeeplineCredits < 0)
  ) {
    throw new Error('maximumDeeplineCredits must be a non-negative number.');
  }
  if (!contract.claims.length)
    throw new Error('Search experiment needs claim contracts.');
  const claimIds = contract.claims.map((claim) => normalize(claim.id));
  if (
    claimIds.some((id) => !id) ||
    unique(claimIds).length !== claimIds.length
  ) {
    throw new Error('Search experiment claim IDs must be nonempty and unique.');
  }
  const minimumExplorationPrograms = definition.minimumExplorationPrograms ?? 2;
  if (
    !Number.isInteger(minimumExplorationPrograms) ||
    minimumExplorationPrograms < 1
  ) {
    throw new Error('minimumExplorationPrograms must be a positive integer.');
  }
  if (programs.length < minimumExplorationPrograms) {
    throw new Error(
      `Search experiment needs at least ${minimumExplorationPrograms} programs.`,
    );
  }
  const programIds = programs.map((program) => normalize(program.id));
  if (
    programIds.some((id) => !id) ||
    unique(programIds).length !== programIds.length
  ) {
    throw new Error('Search program IDs must be nonempty and unique.');
  }
  if (programs.filter((program) => program.incumbent).length > 1) {
    throw new Error('Search experiment accepts at most one incumbent program.');
  }
  for (const program of programs) {
    if (!program.hypothesis.trim())
      throw new Error(`Search program ${program.id} needs a hypothesis.`);
    if (
      program.diversityFeatures !== undefined &&
      (!program.diversityFeatures.length ||
        program.diversityFeatures.some(
          (feature) => typeof feature !== 'string' || !feature.trim(),
        ))
    ) {
      throw new Error(
        `Search program ${program.id} diversityFeatures must be nonempty strings.`,
      );
    }
    if (
      !Number.isInteger(program.maximumCallsPerAttempt) ||
      program.maximumCallsPerAttempt < 1
    ) {
      throw new Error(
        `Search program ${program.id} needs a positive maximumCallsPerAttempt.`,
      );
    }
    if (
      program.maximumDeeplineCreditsPerAttempt !== undefined &&
      (!Number.isFinite(program.maximumDeeplineCreditsPerAttempt) ||
        program.maximumDeeplineCreditsPerAttempt < 0)
    ) {
      throw new Error(
        `Search program ${program.id} needs a non-negative maximumDeeplineCreditsPerAttempt.`,
      );
    }
    if (
      program.billingUnit !== undefined &&
      !['call', 'result', 'unknown'].includes(program.billingUnit)
    ) {
      throw new Error(
        `Search program ${program.id} billingUnit must be call, result, or unknown.`,
      );
    }
    if (
      definition.maximumDeeplineCredits !== undefined &&
      program.maximumDeeplineCreditsPerAttempt === undefined
    ) {
      throw new Error(
        `Search program ${program.id} needs maximumDeeplineCreditsPerAttempt when the experiment has a credit ceiling.`,
      );
    }
  }
  const maxFallbacks =
    definition.maxFallbacks ?? Math.min(2, programs.length - 1);
  const allowedFallbacks = Math.min(
    MAX_ALLOWED_FALLBACKS,
    Math.max(0, programs.length - 1),
  );
  if (
    !Number.isInteger(maxFallbacks) ||
    maxFallbacks < 0 ||
    maxFallbacks > allowedFallbacks
  ) {
    throw new Error(
      `maxFallbacks must be an integer between 0 and ${allowedFallbacks} for ${programs.length} registered program(s).`,
    );
  }
  if (
    countProgramCombinations(programs.length, maxFallbacks + 1) >
    MAX_ENUMERATED_PORTFOLIOS
  ) {
    throw new Error(
      `maxFallbacks ${maxFallbacks} over ${programs.length} programs could enumerate more than ${MAX_ENUMERATED_PORTFOLIOS} portfolios during selection. Lower maxFallbacks or register fewer competing programs.`,
    );
  }
  const explorationProgramCount = Math.min(
    definition.explorationProgramCount ?? DEFAULT_EXPLORATION_PROGRAM_COUNT,
    programs.length,
  );
  if (maxFallbacks === 0 && explorationProgramCount < programs.length) {
    throw new Error(
      'maxFallbacks cannot be zero while registered programs remain dormant.',
    );
  }
  for (const [name, value] of [
    ['pilotUnitCount', definition.pilotUnitCount],
    ['comparisonUnitCount', definition.comparisonUnitCount],
    ['holdoutUnitCount', definition.holdoutUnitCount],
    ['exploitBatchSize', definition.exploitBatchSize],
    ['explorationProgramCount', definition.explorationProgramCount],
    ['challengeWaveSize', definition.challengeWaveSize],
    ['minimumExplorationPrograms', definition.minimumExplorationPrograms],
    ['minimumCompleteResultsPerUnit', contract.minimumCompleteResultsPerUnit],
    ['minimumPilotCompleteRows', contract.minimumPilotCompleteRows],
    ['minimumHoldoutCompleteRows', contract.minimumHoldoutCompleteRows],
  ] as const) {
    if (
      value !== undefined &&
      (!Number.isInteger(value) ||
        value <
          (name === 'exploitBatchSize' ||
          name === 'explorationProgramCount' ||
          name === 'challengeWaveSize' ||
          name === 'minimumExplorationPrograms'
            ? 1
            : 0))
    ) {
      throw new Error(
        `${name} must be a ${
          name === 'exploitBatchSize' ||
          name === 'explorationProgramCount' ||
          name === 'challengeWaveSize' ||
          name === 'minimumExplorationPrograms'
            ? 'positive'
            : 'non-negative'
        } integer.`,
      );
    }
  }
  if (
    definition.explorationProgramCount !== undefined &&
    definition.explorationProgramCount < minimumExplorationPrograms
  ) {
    throw new Error(
      'explorationProgramCount cannot be smaller than minimumExplorationPrograms.',
    );
  }
  const knownClaims = new Set(contract.claims.map((claim) => claim.id));
  const checkIds = new Set<string>();
  for (const check of contract.cohortChecks ?? []) {
    const checkId = normalize(check.id);
    if (!checkId || checkIds.has(checkId))
      throw new Error('Cohort check IDs must be nonempty and unique.');
    checkIds.add(checkId);
    if (!knownClaims.has(check.verifiedClaimId)) {
      throw new Error(
        `Cohort check ${check.id} names unknown claim ${check.verifiedClaimId}.`,
      );
    }
    if (
      !Number.isFinite(check.minimumRatio) ||
      check.minimumRatio < 0 ||
      check.minimumRatio > 1
    ) {
      throw new Error(
        `Cohort check ${check.id} minimumRatio must be between 0 and 1.`,
      );
    }
  }
  selectDiverseRows({ rows, rowKey: contract.rowKey, count: rows.length });
}

function buildSketch<Row extends JsonRow, Context>(
  definition: SearchExperimentDefinition<Row, Context>,
  rows: readonly Row[],
): {
  sketch: DatasetSketch;
  pilotRows: Row[];
  comparisonRows: Row[];
  holdoutRows: Row[];
  exploitRows: Row[];
} {
  const { rowKey: keyField } = definition.contract;
  const automaticTopology =
    definition.pilotUnitCount === undefined &&
    definition.holdoutUnitCount === undefined;
  const reservedExploitCount = automaticTopology && rows.length > 1 ? 1 : 0;
  const requestedHoldout =
    definition.holdoutUnitCount ??
    (rows.length >= 8 ? 2 : rows.length >= 4 ? 1 : 0);
  const holdoutCount = Math.min(
    requestedHoldout,
    Math.max(0, rows.length - 1 - reservedExploitCount),
  );
  const requestedPilot =
    definition.pilotUnitCount ??
    Math.min(3, rows.length - holdoutCount - reservedExploitCount);
  const pilotCount = Math.max(
    1,
    Math.min(requestedPilot, rows.length - holdoutCount),
  );
  const diverse = selectDiverseRows({
    rows,
    rowKey: keyField,
    count: pilotCount + holdoutCount,
  });
  const pilotRows = diverse.slice(0, pilotCount);
  const holdoutRows = diverse.slice(pilotCount, pilotCount + holdoutCount);
  const reserved = new Set([...pilotRows, ...holdoutRows]);
  const exploitRows = rows.filter((row) => !reserved.has(row));
  const comparisonCount = Math.max(
    1,
    Math.min(definition.comparisonUnitCount ?? 2, pilotRows.length),
  );
  const comparisonRows = pilotRows.slice(0, comparisonCount);
  const fields = unique(rows.flatMap((row) => Object.keys(row)))
    .sort()
    .map((field) => {
      const values = rows.map((row) => row[field]);
      const present = values.filter(
        (value) => value !== undefined && value !== null && value !== '',
      ).length;
      return {
        field,
        present,
        missing: rows.length - present,
        distinct: new Set(values.map((value) => stableValue(value))).size,
        types: unique(values.map(valueType)).sort(),
      };
    });
  const keys = (items: readonly Row[]) =>
    items.map((row) => rowKey(row, keyField));
  return {
    sketch: {
      rowCount: rows.length,
      fields,
      pilotUnitKeys: keys(pilotRows),
      comparisonUnitKeys: keys(comparisonRows),
      holdoutUnitKeys: keys(holdoutRows),
      exploitUnitKeys: keys(exploitRows),
    },
    pilotRows,
    comparisonRows,
    holdoutRows,
    exploitRows,
  };
}

function addAttemptToLedger<Row extends JsonRow>(
  ledger: Map<string, LedgerEntry<Row>>,
  record: AttemptRecord<Row>,
): void {
  if (!record.attempt) return;
  const seen = new Set<string>();
  for (const result of record.attempt.results) {
    if (!result.resultKey.trim() || !result.canonicalEntityKey.trim()) {
      throw new Error(
        `Search program ${record.programId} emitted an unkeyed result.`,
      );
    }
    const identity = searchResultIdentity(
      record.unitKey,
      result.canonicalEntityKey,
    );
    if (seen.has(identity)) {
      throw new Error(
        `Search program ${record.programId} emitted duplicate result ${identity}.`,
      );
    }
    seen.add(identity);
    const entry = ledger.get(identity) ?? {
      identity,
      unitKey: record.unitKey,
      canonicalEntityKey: canonicalText(result.canonicalEntityKey),
      row: record.row,
      eligible: true,
      contradiction: false,
      hardCheckFailures: new Set<string>(),
      programIds: new Set<string>(),
      claims: new Map<string, ClaimContribution[]>(),
    };
    entry.eligible &&= result.eligible !== false;
    entry.contradiction ||= result.contradiction === true;
    for (const failure of result.hardCheckFailures ?? [])
      entry.hardCheckFailures.add(failure);
    entry.programIds.add(record.programId);
    for (const [claimId, claim] of Object.entries(result.claims)) {
      if (claim === undefined) continue;
      entry.claims.set(claimId, [
        ...(entry.claims.get(claimId) ?? []),
        { programId: record.programId, claim },
      ]);
    }
    ledger.set(identity, entry);
  }
}

function mergeClaimGroup(
  contributions: readonly ClaimContribution[],
): ResearchClaimValue {
  const first = contributions[0]!.claim;
  return {
    ...first,
    facts: Object.assign(
      {},
      ...contributions.map(({ claim }) => claim.facts ?? {}),
    ),
    evidence: contributions.flatMap(({ claim }) => claim.evidence ?? []),
    abstainReason: contributions.every(({ claim }) => claim.abstainReason)
      ? contributions
          .map(({ claim }) => claim.abstainReason)
          .filter(Boolean)
          .join('; ')
      : undefined,
  };
}

function materializeLedger<Row extends JsonRow>(input: {
  ledger: Map<string, LedgerEntry<Row>>;
  claims: readonly ResearchClaim<Row>[];
  coherenceChecks?: readonly SearchCoherenceCheck<Row>[];
}): SearchLedgerResult<Row>[] {
  const requiredClaimIds = input.claims
    .filter((claim) => claim.required !== false)
    .map((claim) => claim.id);
  return [...input.ledger.values()]
    .map((entry) => {
      const merged: Record<string, ResearchClaimValue | undefined> = {};
      let conflictingValues = false;
      for (const definition of input.claims) {
        const contributions = entry.claims.get(definition.id) ?? [];
        if (!contributions.length) continue;
        const groups = new Map<string, ClaimContribution[]>();
        for (const contribution of contributions) {
          const key = stableValue(contribution.claim.value);
          groups.set(key, [...(groups.get(key) ?? []), contribution]);
        }
        const ranked = [...groups.values()].sort(
          (left, right) =>
            right.flatMap(({ claim }) => claim.evidence ?? []).length -
              left.flatMap(({ claim }) => claim.evidence ?? []).length ||
            stableValue(left[0]!.claim.value).localeCompare(
              stableValue(right[0]!.claim.value),
            ),
        );
        merged[definition.id] = mergeClaimGroup(ranked[0]!);
        if (ranked.length > 1) {
          const supported = ranked.filter((group) =>
            group.some(({ claim }) => (claim.evidence?.length ?? 0) > 0),
          );
          if (supported.length > 1) conflictingValues = true;
        }
      }
      const scope = claimReceiptScope(entry.identity);
      const claimEvaluations = evaluateResearchClaimValues({
        row: entry.row,
        definitions: input.claims,
        claims: merged,
        receiptScope: scope,
      });
      const verified = new Set(
        claimEvaluations
          .filter(
            (evaluation) =>
              isValidatedResearchClaimEvaluation(evaluation, scope) &&
              evaluation.status === 'verified',
          )
          .map((evaluation) => evaluation.claimId),
      );
      const contradiction = entry.contradiction || conflictingValues;
      const hardCheckFailures = [...entry.hardCheckFailures];
      if (input.coherenceChecks?.length) {
        const verifiedValues: Record<string, unknown> = {};
        for (const evaluation of claimEvaluations) {
          if (verified.has(evaluation.claimId)) {
            verifiedValues[evaluation.claimId] = evaluation.value;
          }
        }
        for (const coherence of input.coherenceChecks) {
          const reason = coherence.check({
            row: entry.row,
            unitKey: entry.unitKey,
            canonicalEntityKey: entry.canonicalEntityKey,
            verified: verifiedValues,
          });
          if (typeof reason === 'string' && reason.trim()) {
            hardCheckFailures.push(
              `${INCOHERENT_FAILURE_PREFIX}${coherence.id}:${reason.trim()}`,
            );
          }
        }
      }
      return {
        identity: entry.identity,
        unitKey: entry.unitKey,
        canonicalEntityKey: entry.canonicalEntityKey,
        row: entry.row,
        eligible: entry.eligible,
        complete:
          entry.eligible &&
          !contradiction &&
          !hardCheckFailures.length &&
          requiredClaimIds.every((claimId) => verified.has(claimId)),
        contradiction,
        hardCheckFailures,
        claimEvaluations,
        programIds: [...entry.programIds].sort(),
      };
    })
    .sort((left, right) => left.identity.localeCompare(right.identity));
}

function verifiedClaimCount<Row extends JsonRow>(
  results: readonly SearchLedgerResult<Row>[],
): number {
  return results.reduce(
    (total, result) =>
      total +
      result.claimEvaluations.filter((claim) => claim.status === 'verified')
        .length,
    0,
  );
}

function requiredVerifiedCount<Row extends JsonRow>(
  results: readonly SearchLedgerResult<Row>[],
): number {
  return results.reduce(
    (total, result) =>
      total +
      result.claimEvaluations.filter(
        (claim) => claim.required && claim.status === 'verified',
      ).length,
    0,
  );
}

function gapsForUnit<Row extends JsonRow>(
  unitKey: string,
  results: readonly SearchLedgerResult<Row>[],
  claims: readonly ResearchClaim<Row>[],
): ResearchClaimGap[] {
  const unitResults = results.filter((result) => result.unitKey === unitKey);
  if (!unitResults.length) {
    return claims.map((claim) => ({
      claimId: claim.id,
      required: claim.required !== false,
      status: 'insufficient_evidence',
      reason: 'no candidate evidence yet',
    }));
  }
  const best = [...unitResults].sort(
    (left, right) =>
      Number(right.complete) - Number(left.complete) ||
      right.claimEvaluations.filter((claim) => claim.status === 'verified')
        .length -
        left.claimEvaluations.filter((claim) => claim.status === 'verified')
          .length ||
      left.identity.localeCompare(right.identity),
  )[0]!;
  return best.claimEvaluations
    .filter((claim) => claim.status !== 'verified')
    .map(({ claimId, required, status, reason }) => ({
      claimId,
      required,
      status,
      reason,
    }));
}

function evaluateCohorts<Row extends JsonRow>(input: {
  checks: readonly SearchCohortCheck[];
  results: readonly SearchLedgerResult<Row>[];
  unitKeys: readonly string[];
}): SearchCohortResult[] {
  return input.checks.map((check) => {
    const passesClaim = (result: SearchLedgerResult<Row>): boolean =>
      result.claimEvaluations.some(
        (claim) =>
          claim.claimId === check.verifiedClaimId &&
          claim.status === 'verified',
      );
    let numerator: number;
    let denominatorCount: number;
    if (check.denominator === 'pilot_units') {
      denominatorCount = input.unitKeys.length;
      numerator = input.unitKeys.filter((unitKey) =>
        input.results.some(
          (result) =>
            result.unitKey === unitKey &&
            result.eligible &&
            passesClaim(result),
        ),
      ).length;
    } else {
      const denominator = input.results.filter((result) =>
        check.denominator === 'eligible_results'
          ? result.eligible
          : result.complete,
      );
      denominatorCount = denominator.length;
      numerator = denominator.filter(passesClaim).length;
    }
    const ratio = denominatorCount ? numerator / denominatorCount : 0;
    return {
      ...check,
      numerator,
      denominatorCount,
      ratio,
      pass: denominatorCount > 0 && ratio >= check.minimumRatio,
    };
  });
}

function unitNeedsWork<Row extends JsonRow>(input: {
  unitKey: string;
  results: readonly SearchLedgerResult<Row>[];
  minimumCompleteResultsPerUnit: number;
  failedCohortClaimIds: ReadonlySet<string>;
}): boolean {
  const unitResults = input.results.filter(
    (result) => result.unitKey === input.unitKey,
  );
  if (
    unitResults.filter((result) => result.complete).length <
    input.minimumCompleteResultsPerUnit
  )
    return true;
  return unitResults.some((result) =>
    result.claimEvaluations.some(
      (claim) =>
        input.failedCohortClaimIds.has(claim.claimId) &&
        claim.status !== 'verified',
    ),
  );
}

function scoreProgram<Row extends JsonRow>(input: {
  program: SearchProgram<Row, unknown>;
  records: readonly AttemptRecord<Row>[];
  claims: readonly ResearchClaim<Row>[];
  coherenceChecks?: readonly SearchCoherenceCheck<Row>[];
}): SearchProgramScore {
  const programRecords = input.records.filter(
    (record) => record.programId === input.program.id,
  );
  const ledger = new Map<string, LedgerEntry<Row>>();
  for (const record of programRecords) {
    addAttemptToLedger(ledger, record);
  }
  const results = materializeLedger({
    ledger,
    claims: input.claims,
    coherenceChecks: input.coherenceChecks,
  });
  const totalCalls = programRecords.reduce(
    (total, record) => total + record.observedTotalCalls,
    0,
  );
  const verifiedRequiredClaims = requiredVerifiedCount(results);
  const completeResults = results.filter((result) => result.complete);
  const credits = summarizeCredits(programRecords);
  const cost = estimateProgramCost({
    program: input.program,
    records: programRecords,
  });
  const evidence = results.flatMap((result) =>
    result.claimEvaluations.flatMap((claim) => claim.evidence),
  );
  return {
    programId: input.program.id,
    attempts: programRecords.length,
    reachability: programRecords.length ? 'ran' : 'never_reached',
    completeResults: completeResults.length,
    unitsWithCompleteResults: unique(
      completeResults.map((result) => result.unitKey),
    ).length,
    verifiedRequiredClaims,
    supportedEvidenceAtoms: evidence.length,
    totalCalls,
    callsPerVerifiedRequiredClaim: verifiedRequiredClaims
      ? totalCalls / verifiedRequiredClaims
      : Number.POSITIVE_INFINITY,
    deeplineCredits: credits.total,
    deeplineCreditsPerVerifiedRequiredClaim:
      verifiedRequiredClaims && credits.total !== null
        ? credits.total / verifiedRequiredClaims
        : null,
    costCredits: cost.credits,
    costCreditsPerVerifiedRequiredClaim:
      verifiedRequiredClaims && cost.credits !== null
        ? cost.credits / verifiedRequiredClaims
        : null,
    costBasis: cost.basis,
    unobservedCreditAttempts: credits.unobserved,
    sourceMisses: programRecords.filter(
      (record) => record.attempt && !record.attempt.results.length,
    ).length,
    adapterFailures: programRecords.filter((record) => record.error).length,
    incoherentResults: results.filter((result) =>
      result.hardCheckFailures.some((failure) =>
        failure.startsWith(INCOHERENT_FAILURE_PREFIX),
      ),
    ).length,
    evidenceLineages: unique(
      evidence.map((item) => item.independenceClass),
    ).sort(),
    toolIds: input.program.tools ? [...input.program.tools].sort() : null,
  };
}

function coverageForPrograms<Row extends JsonRow>(input: {
  programIds: ReadonlySet<string>;
  records: readonly AttemptRecord<Row>[];
  claims: readonly ResearchClaim<Row>[];
  coherenceChecks?: readonly SearchCoherenceCheck<Row>[];
  cohortChecks: readonly SearchCohortCheck[];
}): {
  completeResultIdentities: Set<string>;
  verifiedRequiredClaimKeys: Set<string>;
  passedCohortChecks: number;
  cohortRatioTotal: number;
  cohortNumeratorTotal: number;
  evidenceLineages: Set<string>;
} {
  const ledger = new Map<string, LedgerEntry<Row>>();
  for (const record of input.records) {
    if (input.programIds.has(record.programId))
      addAttemptToLedger(ledger, record);
  }
  const results = materializeLedger({
    ledger,
    claims: input.claims,
    coherenceChecks: input.coherenceChecks,
  });
  const cohort = evaluateCohorts({
    checks: input.cohortChecks,
    results,
    unitKeys: unique(input.records.map((record) => record.unitKey)),
  });
  return {
    completeResultIdentities: new Set(
      results
        .filter((result) => result.complete)
        .map((result) => result.identity),
    ),
    verifiedRequiredClaimKeys: new Set(
      results.flatMap((result) =>
        result.claimEvaluations
          .filter((claim) => claim.required && claim.status === 'verified')
          .map((claim) => `${result.identity}\u0000${claim.claimId}`),
      ),
    ),
    passedCohortChecks: cohort.filter((check) => check.pass).length,
    cohortRatioTotal: cohort.reduce((total, check) => total + check.ratio, 0),
    cohortNumeratorTotal: cohort.reduce(
      (total, check) => total + check.numerator,
      0,
    ),
    evidenceLineages: new Set(
      results.flatMap((result) =>
        result.claimEvaluations.flatMap((claim) =>
          claim.evidence.map((item) => item.independenceClass),
        ),
      ),
    ),
  };
}

function coverageImproved(
  before: ReturnType<typeof coverageForPrograms>,
  after: ReturnType<typeof coverageForPrograms>,
): boolean {
  return (
    after.completeResultIdentities.size >
      before.completeResultIdentities.size ||
    (after.completeResultIdentities.size ===
      before.completeResultIdentities.size &&
      after.verifiedRequiredClaimKeys.size >
        before.verifiedRequiredClaimKeys.size) ||
    (after.completeResultIdentities.size ===
      before.completeResultIdentities.size &&
      after.verifiedRequiredClaimKeys.size ===
        before.verifiedRequiredClaimKeys.size &&
      after.passedCohortChecks > before.passedCohortChecks) ||
    (after.completeResultIdentities.size ===
      before.completeResultIdentities.size &&
      after.verifiedRequiredClaimKeys.size ===
        before.verifiedRequiredClaimKeys.size &&
      after.passedCohortChecks === before.passedCohortChecks &&
      after.cohortRatioTotal > before.cohortRatioTotal) ||
    (after.completeResultIdentities.size ===
      before.completeResultIdentities.size &&
      after.verifiedRequiredClaimKeys.size ===
        before.verifiedRequiredClaimKeys.size &&
      after.passedCohortChecks === before.passedCohortChecks &&
      after.cohortRatioTotal === before.cohortRatioTotal &&
      after.cohortNumeratorTotal > before.cohortNumeratorTotal)
  );
}

/** Number of nonempty subsets of `poolSize` values with at most `maximumSize` members. */
function countProgramCombinations(
  poolSize: number,
  maximumSize: number,
): number {
  let total = 0;
  let choose = 1;
  for (let size = 1; size <= Math.min(maximumSize, poolSize); size += 1) {
    choose = (choose * (poolSize - size + 1)) / size;
    total += choose;
  }
  return total;
}

function programCombinations<T>(
  values: readonly T[],
  maximumSize: number,
): T[][] {
  const combinations: T[][] = [];
  const visit = (start: number, selected: T[]) => {
    if (selected.length) combinations.push(selected);
    if (selected.length === maximumSize) return;
    for (let index = start; index < values.length; index += 1) {
      visit(index + 1, [...selected, values[index]!]);
    }
  };
  visit(0, []);
  return combinations;
}

function replacementRequiredProgramIds<Row extends JsonRow, Context>(input: {
  activePrograms: readonly SearchProgram<Row, Context>[];
  records: readonly AttemptRecord<Row>[];
}): Set<string> {
  const activeIds = new Set(input.activePrograms.map((program) => program.id));
  const required = new Set<string>();
  const primary = input.activePrograms[0];
  if (primary) required.add(primary.id);
  for (const record of input.records) {
    if (!activeIds.has(record.programId) || !record.attempt?.results.length)
      continue;
    for (const result of record.attempt.results) {
      const identity = searchResultIdentity(
        record.unitKey,
        result.canonicalEntityKey,
      );
      const dependency = record.candidateDependenciesBefore.find(
        (candidate) => candidate.identity === identity,
      );
      if (!dependency) continue;
      const activeProducers = dependency.programIds.filter(
        (programId) =>
          programId !== record.programId && activeIds.has(programId),
      );
      if (!activeProducers.length) continue;
      required.add(record.programId);
      activeProducers.forEach((programId) => required.add(programId));
    }
  }
  return required;
}

function orderProgramsForExecution<Row extends JsonRow, Context>(input: {
  programs: readonly SearchProgram<Row, Context>[];
  preferredProgramIds: readonly string[];
  records: readonly AttemptRecord<Row>[];
}): SearchProgram<Row, Context>[] {
  const selectedIds = new Set(input.programs.map((program) => program.id));
  const dependencies = new Map<string, Set<string>>();
  for (const record of input.records) {
    if (!selectedIds.has(record.programId) || !record.attempt?.results.length)
      continue;
    for (const result of record.attempt.results) {
      const identity = searchResultIdentity(
        record.unitKey,
        result.canonicalEntityKey,
      );
      const dependency = record.candidateDependenciesBefore.find(
        (candidate) => candidate.identity === identity,
      );
      for (const producerId of dependency?.programIds ?? []) {
        if (producerId === record.programId || !selectedIds.has(producerId))
          continue;
        const producers = dependencies.get(record.programId) ?? new Set();
        producers.add(producerId);
        dependencies.set(record.programId, producers);
      }
    }
  }

  const rank = new Map(
    input.preferredProgramIds.map((programId, index) => [programId, index]),
  );
  const orderedIds: string[] = [];
  const visited = new Set<string>();
  const visit = (programId: string) => {
    if (visited.has(programId)) return;
    visited.add(programId);
    const producers = [...(dependencies.get(programId) ?? [])].sort(
      (left, right) =>
        (rank.get(left) ?? Number.POSITIVE_INFINITY) -
          (rank.get(right) ?? Number.POSITIVE_INFINITY) ||
        left.localeCompare(right),
    );
    producers.forEach(visit);
    orderedIds.push(programId);
  };
  input.preferredProgramIds.forEach(visit);
  const byId = new Map(input.programs.map((program) => [program.id, program]));
  return orderedIds.map((programId) => byId.get(programId)!);
}

function failedCohortClaimIds(
  checks: readonly SearchCohortResult[],
): Set<string> {
  const failedClaimIds = new Set<string>();
  for (const check of checks) {
    if (!check.pass) failedClaimIds.add(check.verifiedClaimId);
  }
  return failedClaimIds;
}

function rowsNeedingWork<Row extends JsonRow>(input: {
  rows: readonly Row[];
  unitKeyFor: (row: Row) => string;
  results: readonly SearchLedgerResult<Row>[];
  minimumCompleteResultsPerUnit: number;
  failedCohortClaimIds: ReadonlySet<string>;
}): Row[] {
  return input.rows.filter((row) =>
    unitNeedsWork({
      unitKey: input.unitKeyFor(row),
      results: input.results,
      minimumCompleteResultsPerUnit: input.minimumCompleteResultsPerUnit,
      failedCohortClaimIds: input.failedCohortClaimIds,
    }),
  );
}

function catalogProvesZeroCreditMiss<Row extends JsonRow>(input: {
  program: Pick<SearchProgram<Row, unknown>, 'billingUnit'>;
  record: AttemptRecord<Row>;
}): boolean {
  return Boolean(
    input.record.attempt &&
    input.record.observedTotalCalls > 0 &&
    input.record.attempt.results.length === 0 &&
    input.program.billingUnit === 'result',
  );
}

function summarizeCredits<Row extends JsonRow>(
  records: readonly AttemptRecord<Row>[],
): { total: number | null; unobserved: number } {
  const observedCredits = records.map((record) =>
    record.observedDeeplineCredits !== null
      ? record.observedDeeplineCredits
      : record.attempt && record.observedTotalCalls === 0
        ? 0
        : null,
  );
  const unobserved = observedCredits.filter(
    (credits) => credits === null,
  ).length;
  return {
    total: unobserved
      ? null
      : observedCredits.reduce<number>((total, credits) => total + credits!, 0),
    unobserved,
  };
}

function estimateProgramCost<Row extends JsonRow>(input: {
  program: SearchProgram<Row, unknown>;
  records: readonly AttemptRecord<Row>[];
}): { credits: number | null; basis: SearchCostBasis } {
  const observed = summarizeCredits(input.records);
  if (observed.total !== null) {
    return { credits: observed.total, basis: 'observed' };
  }
  const ceiling = input.program.maximumDeeplineCreditsPerAttempt;
  if (ceiling === undefined) return { credits: null, basis: 'unknown' };
  return {
    credits: input.records.reduce(
      (total, record) =>
        total +
        (record.observedDeeplineCredits ??
          (record.attempt && record.observedTotalCalls === 0
            ? 0
            : catalogProvesZeroCreditMiss({
                  program: input.program,
                  record,
                })
              ? 0
              : ceiling)),
      0,
    ),
    basis: 'catalog_upper_bound',
  };
}

function compareNullableCost(
  left: number | null,
  right: number | null,
): number {
  if (left !== null && right !== null) return left - right;
  if (left !== null) return -1;
  if (right !== null) return 1;
  return 0;
}

function compareProgramScores(
  left: SearchProgramScore,
  right: SearchProgramScore,
): number {
  return (
    right.completeResults - left.completeResults ||
    right.verifiedRequiredClaims - left.verifiedRequiredClaims ||
    right.unitsWithCompleteResults - left.unitsWithCompleteResults ||
    left.adapterFailures - right.adapterFailures ||
    compareNullableCost(
      left.costCreditsPerVerifiedRequiredClaim,
      right.costCreditsPerVerifiedRequiredClaim,
    ) ||
    left.callsPerVerifiedRequiredClaim - right.callsPerVerifiedRequiredClaim ||
    left.programId.localeCompare(right.programId)
  );
}

function expandCausalProgramIds<Row extends JsonRow>(input: {
  seedProgramIds: readonly string[];
  records: readonly AttemptRecord<Row>[];
  rankById: ReadonlyMap<string, number>;
}): string[] {
  const expanded = [...input.seedProgramIds];
  for (let index = 0; index < expanded.length; index += 1) {
    const consumerId = expanded[index]!;
    for (const record of input.records) {
      if (record.programId !== consumerId || !record.attempt?.results.length)
        continue;
      for (const result of record.attempt.results) {
        const identity = searchResultIdentity(
          record.unitKey,
          result.canonicalEntityKey,
        );
        const dependency = record.candidateDependenciesBefore.find(
          (candidate) => candidate.identity === identity,
        );
        const producerIds = [...(dependency?.programIds ?? [])]
          .filter((programId) => programId !== consumerId)
          .sort(
            (left, right) =>
              (input.rankById.get(left) ?? Number.POSITIVE_INFINITY) -
                (input.rankById.get(right) ?? Number.POSITIVE_INFINITY) ||
              left.localeCompare(right),
          );
        for (const producerId of producerIds) {
          if (!expanded.includes(producerId)) expanded.push(producerId);
        }
      }
    }
  }
  return expanded;
}

function choosePrograms<Row extends JsonRow, Context>(input: {
  programs: readonly SearchProgram<Row, Context>[];
  records: readonly AttemptRecord<Row>[];
  claims: readonly ResearchClaim<Row>[];
  coherenceChecks?: readonly SearchCoherenceCheck<Row>[];
  maxFallbacks: number;
  requiredProgramIds?: ReadonlySet<string>;
  cohortChecks: readonly SearchCohortCheck[];
}): {
  selected: SearchProgram<Row, Context>[];
  scores: SearchProgramScore[];
  dependencyCycle: string[];
  costCoverageFrontier: SearchCostCoveragePoint[];
} {
  const requiredProgramIds = input.requiredProgramIds ?? new Set<string>();
  const observedProgramIds = new Set(
    input.records.map((record) => record.programId),
  );
  const portfolioPrograms = input.programs.filter(
    (program) =>
      observedProgramIds.has(program.id) || requiredProgramIds.has(program.id),
  );
  const enriched = portfolioPrograms
    .map((program) =>
      scoreProgram({
        program: program as SearchProgram<Row, unknown>,
        records: input.records,
        claims: input.claims,
        coherenceChecks: input.coherenceChecks,
      }),
    )
    .sort(compareProgramScores);
  const maximumPrograms = Math.min(
    portfolioPrograms.length,
    Math.max(1, requiredProgramIds.size) + input.maxFallbacks,
  );
  const rankById = new Map(
    enriched.map((score, index) => [score.programId, index]),
  );
  const scoreById = new Map(enriched.map((score) => [score.programId, score]));
  const comparisonWasEmpty = enriched.every(
    (score) => score.supportedEvidenceAtoms === 0,
  );
  if (comparisonWasEmpty) {
    // There is no evidence to compose, so enumerating every two- or three-way
    // portfolio adds no information and becomes cubic as the catalog grows.
    // Keep the cheapest bounded active set only to prevent retrying it while
    // dormant challenge waves continue through the rest of the pool.
    const selectedScores = enriched.slice(0, maximumPrograms);
    const selectedIds = new Set(selectedScores.map((score) => score.programId));
    const observedDeeplineCredits = selectedScores.every(
      (score) => score.deeplineCredits !== null,
    )
      ? selectedScores.reduce(
          (total, score) => total + score.deeplineCredits!,
          0,
        )
      : null;
    const costCredits = selectedScores.every(
      (score) => score.costCredits !== null,
    )
      ? selectedScores.reduce((total, score) => total + score.costCredits!, 0)
      : null;
    const costBasis = selectedScores.some(
      (score) => score.costBasis === 'unknown',
    )
      ? ('unknown' as const)
      : selectedScores.some(
            (score) => score.costBasis === 'catalog_upper_bound',
          )
        ? ('catalog_upper_bound' as const)
        : ('observed' as const);
    return {
      selected: enriched
        .filter((score) => selectedIds.has(score.programId))
        .map(
          (score) =>
            input.programs.find((program) => program.id === score.programId)!,
        ),
      scores: enriched,
      dependencyCycle: [],
      costCoverageFrontier: selectedScores.length
        ? [
            {
              programIds: selectedScores.map((score) => score.programId),
              completeResults: 0,
              verifiedRequiredClaims: 0,
              passedCohortChecks: 0,
              cohortRatioTotal: 0,
              cohortNumeratorTotal: 0,
              totalCalls: selectedScores.reduce(
                (total, score) => total + score.totalCalls,
                0,
              ),
              observedDeeplineCredits,
              costCredits,
              costBasis,
              completeResultsPerCostCredit: null,
              comparisonWinner: true,
            },
          ]
        : [],
    };
  }
  const expandedPortfolios = programCombinations(enriched, maximumPrograms)
    .map((basePrograms) =>
      expandCausalProgramIds({
        seedProgramIds: basePrograms.map((program) => program.programId),
        records: input.records,
        rankById,
      }).map((programId) => scoreById.get(programId)!),
    )
    .filter((programs) =>
      [...requiredProgramIds].every((requiredId) =>
        programs.some((program) => program.programId === requiredId),
      ),
    )
    .map((programs) => ({
      programs,
      coverage: coverageForPrograms({
        programIds: new Set(programs.map((program) => program.programId)),
        records: input.records,
        claims: input.claims,
        coherenceChecks: input.coherenceChecks,
        cohortChecks: input.cohortChecks,
      }),
      totalCalls: programs.reduce(
        (total, program) => total + program.totalCalls,
        0,
      ),
      deeplineCredits: programs.every(
        (program) => program.deeplineCredits !== null,
      )
        ? programs.reduce(
            (total, program) => total + program.deeplineCredits!,
            0,
          )
        : null,
      costCredits: programs.every((program) => program.costCredits !== null)
        ? programs.reduce((total, program) => total + program.costCredits!, 0)
        : null,
      costBasis: programs.some((program) => program.costBasis === 'unknown')
        ? ('unknown' as const)
        : programs.some(
              (program) => program.costBasis === 'catalog_upper_bound',
            )
          ? ('catalog_upper_bound' as const)
          : ('observed' as const),
    }));
  const seenPortfolioKeys = new Set<string>();
  const portfolios = expandedPortfolios.filter((portfolio) => {
    const key = portfolio.programs
      .map((program) => program.programId)
      .sort()
      .join('\u0000');
    if (seenPortfolioKeys.has(key)) return false;
    seenPortfolioKeys.add(key);
    return true;
  });
  if (!portfolios.length) {
    return {
      selected: [],
      scores: enriched,
      dependencyCycle: [],
      costCoverageFrontier: [],
    };
  }
  portfolios.sort((left, right) => {
    if (comparisonWasEmpty) {
      const sizeDifference = right.programs.length - left.programs.length;
      if (sizeDifference) return sizeDifference;
    }
    return (
      right.coverage.completeResultIdentities.size -
        left.coverage.completeResultIdentities.size ||
      right.coverage.verifiedRequiredClaimKeys.size -
        left.coverage.verifiedRequiredClaimKeys.size ||
      right.coverage.passedCohortChecks - left.coverage.passedCohortChecks ||
      right.coverage.cohortRatioTotal - left.coverage.cohortRatioTotal ||
      right.coverage.cohortNumeratorTotal -
        left.coverage.cohortNumeratorTotal ||
      compareNullableCost(left.costCredits, right.costCredits) ||
      left.totalCalls - right.totalCalls ||
      right.coverage.evidenceLineages.size -
        left.coverage.evidenceLineages.size ||
      left.programs.length - right.programs.length ||
      left.programs
        .map((program) => rankById.get(program.programId)!)
        .join(',')
        .localeCompare(
          right.programs
            .map((program) => rankById.get(program.programId)!)
            .join(','),
        )
    );
  });
  const selectedIds = portfolios[0]!.programs.map(
    (program) => program.programId,
  );
  const dominates = (
    left: (typeof portfolios)[number],
    right: (typeof portfolios)[number],
  ): boolean => {
    if (left.costCredits === null || right.costCredits === null) return false;
    const atLeastAsMuchCoverage =
      left.coverage.completeResultIdentities.size >=
        right.coverage.completeResultIdentities.size &&
      left.coverage.verifiedRequiredClaimKeys.size >=
        right.coverage.verifiedRequiredClaimKeys.size &&
      left.coverage.passedCohortChecks >= right.coverage.passedCohortChecks &&
      left.coverage.cohortRatioTotal >= right.coverage.cohortRatioTotal &&
      left.coverage.cohortNumeratorTotal >=
        right.coverage.cohortNumeratorTotal &&
      (!comparisonWasEmpty || left.programs.length >= right.programs.length);
    const noMoreCost = left.costCredits <= right.costCredits;
    const strictlyBetter =
      left.coverage.completeResultIdentities.size >
        right.coverage.completeResultIdentities.size ||
      left.coverage.verifiedRequiredClaimKeys.size >
        right.coverage.verifiedRequiredClaimKeys.size ||
      left.coverage.passedCohortChecks > right.coverage.passedCohortChecks ||
      left.coverage.cohortRatioTotal > right.coverage.cohortRatioTotal ||
      left.coverage.cohortNumeratorTotal >
        right.coverage.cohortNumeratorTotal ||
      (comparisonWasEmpty && left.programs.length > right.programs.length) ||
      left.costCredits < right.costCredits;
    return atLeastAsMuchCoverage && noMoreCost && strictlyBetter;
  };
  const selectedKey = [...selectedIds].sort().join('\u0000');
  const costCoverageFrontier = portfolios
    .filter(
      (candidate) =>
        !portfolios.some(
          (other) => other !== candidate && dominates(other, candidate),
        ),
    )
    .map<SearchCostCoveragePoint>((portfolio) => {
      const completeResults = portfolio.coverage.completeResultIdentities.size;
      return {
        programIds: portfolio.programs.map((program) => program.programId),
        completeResults,
        verifiedRequiredClaims:
          portfolio.coverage.verifiedRequiredClaimKeys.size,
        passedCohortChecks: portfolio.coverage.passedCohortChecks,
        cohortRatioTotal: portfolio.coverage.cohortRatioTotal,
        cohortNumeratorTotal: portfolio.coverage.cohortNumeratorTotal,
        totalCalls: portfolio.totalCalls,
        observedDeeplineCredits: portfolio.deeplineCredits,
        costCredits: portfolio.costCredits,
        costBasis: portfolio.costBasis,
        completeResultsPerCostCredit:
          portfolio.costCredits !== null && portfolio.costCredits > 0
            ? completeResults / portfolio.costCredits
            : null,
        comparisonWinner:
          portfolio.programs
            .map((program) => program.programId)
            .sort()
            .join('\u0000') === selectedKey,
      };
    });
  const dependencies = new Map<string, Set<string>>();
  for (let index = 0; index < selectedIds.length; index += 1) {
    const consumerId = selectedIds[index]!;
    for (const record of input.records) {
      if (record.programId !== consumerId || !record.attempt?.results.length)
        continue;
      for (const result of record.attempt.results) {
        const identity = searchResultIdentity(
          record.unitKey,
          result.canonicalEntityKey,
        );
        const dependency = record.candidateDependenciesBefore.find(
          (candidate) => candidate.identity === identity,
        );
        const producerIds = dependency?.programIds
          .filter((programId) => programId !== consumerId)
          .sort(
            (left, right) =>
              (rankById.get(left) ?? Number.POSITIVE_INFINITY) -
                (rankById.get(right) ?? Number.POSITIVE_INFINITY) ||
              left.localeCompare(right),
          );
        if (!producerIds?.length) continue;
        const producers = dependencies.get(consumerId) ?? new Set<string>();
        producerIds.forEach((producerId) => producers.add(producerId));
        dependencies.set(consumerId, producers);
        for (const producerId of producerIds) {
          if (!selectedIds.includes(producerId)) selectedIds.push(producerId);
        }
      }
    }
  }
  const orderedIds: string[] = [];
  const visited = new Set<string>();
  const visiting = new Set<string>();
  const path: string[] = [];
  let dependencyCycle: string[] = [];
  const visit = (programId: string) => {
    if (dependencyCycle.length) return;
    if (visited.has(programId)) return;
    if (visiting.has(programId)) {
      const cycleStart = path.indexOf(programId);
      dependencyCycle = [...path.slice(cycleStart), programId];
      return;
    }
    visiting.add(programId);
    path.push(programId);
    for (const producerId of dependencies.get(programId) ?? []) {
      visit(producerId);
    }
    path.pop();
    visiting.delete(programId);
    visited.add(programId);
    orderedIds.push(programId);
  };
  selectedIds.forEach(visit);
  const byId = new Map(input.programs.map((program) => [program.id, program]));
  return {
    selected: dependencyCycle.length
      ? []
      : orderedIds.map((id) => byId.get(id)!),
    scores: enriched,
    dependencyCycle,
    costCoverageFrontier: dependencyCycle.length
      ? costCoverageFrontier.map((point) => ({
          ...point,
          comparisonWinner: false,
        }))
      : costCoverageFrontier,
  };
}

async function invokeProgram<Row extends JsonRow, Context>(input: {
  ctx: Context;
  program: SearchProgram<Row, Context>;
  row: Row;
  unitKey: string;
  phase: SearchExperimentPhase;
  gaps: readonly ResearchClaimGap[];
  candidates: readonly SearchLedgerResult<Row>[];
  remainingTargetRows: number;
}): Promise<AttemptRecord<Row>> {
  let observedTotalCalls = 0;
  let observedDeeplineCredits: number | null = null;
  const trackedCandidates = trackCandidateReads(input.candidates);
  const dependenciesBefore = candidateDependencies(input.candidates);
  const candidateProgramIdsBefore = unique(
    dependenciesBefore.flatMap((candidate) => candidate.programIds),
  );
  try {
    const rawAttempt: unknown = await input.program.run({
      ...input,
      candidates: trackedCandidates.candidates,
    });
    if (isObjectRecord(rawAttempt)) {
      if (
        typeof rawAttempt.totalCalls === 'number' &&
        Number.isFinite(rawAttempt.totalCalls) &&
        rawAttempt.totalCalls >= 0
      ) {
        observedTotalCalls = rawAttempt.totalCalls;
      }
      if (
        rawAttempt.deeplineCredits !== undefined &&
        rawAttempt.deeplineCredits !== null
      ) {
        if (
          typeof rawAttempt.deeplineCredits !== 'number' ||
          !Number.isFinite(rawAttempt.deeplineCredits) ||
          rawAttempt.deeplineCredits < 0
        ) {
          throw new Error(
            `Search program ${input.program.id} returned invalid Deepline credits.`,
          );
        }
        observedDeeplineCredits = rawAttempt.deeplineCredits;
      }
    }
    validateProgramAttempt(input.program.id, rawAttempt);
    const attempt = rawAttempt;
    if (!Number.isInteger(attempt.totalCalls) || attempt.totalCalls < 0) {
      throw new Error(
        `Search program ${input.program.id} returned an invalid totalCalls.`,
      );
    }
    if (attempt.totalCalls > input.program.maximumCallsPerAttempt) {
      throw new Error(
        `Search program ${input.program.id} used ${attempt.totalCalls} calls; cap is ${input.program.maximumCallsPerAttempt}.`,
      );
    }
    return {
      phase: input.phase,
      programId: input.program.id,
      unitKey: input.unitKey,
      row: input.row,
      attempt,
      observedTotalCalls,
      observedDeeplineCredits,
      gapsBefore: input.gaps.map((gap) => gap.claimId),
      candidateStateBefore: candidateState(input.candidates),
      candidateProgramIdsBefore,
      candidateDependenciesBefore: dependenciesBefore.filter((candidate) =>
        trackedCandidates.consumedIdentities.has(candidate.identity),
      ),
    };
  } catch (error) {
    return {
      phase: input.phase,
      programId: input.program.id,
      unitKey: input.unitKey,
      row: input.row,
      error: error instanceof Error ? error.message : String(error),
      observedTotalCalls,
      observedDeeplineCredits,
      gapsBefore: input.gaps.map((gap) => gap.claimId),
      candidateStateBefore: candidateState(input.candidates),
      candidateProgramIdsBefore,
      candidateDependenciesBefore: dependenciesBefore.filter((candidate) =>
        trackedCandidates.consumedIdentities.has(candidate.identity),
      ),
    };
  }
}

/**
 * Run a fair comparison, best-first gap closure, untouched holdout, and
 * exploitation in one Play invocation. Calls inside each wave are concurrent.
 */
export async function runSearchExperiment<Row extends JsonRow, Context>(input: {
  ctx: Context;
  definition: SearchExperimentDefinition<Row, Context>;
  rows: readonly Row[];
}): Promise<SearchExperimentResult<Row>> {
  validateDefinition(input.definition, input.rows);
  const { contract } = input.definition;
  const split = buildSketch(input.definition, input.rows);
  const ledger = new Map<string, LedgerEntry<Row>>();
  const records: AttemptRecord<Row>[] = [];
  const traces: SearchAttemptTrace[] = [];
  const adaptations: SearchAdaptationTrace[] = [];
  const unitKeyFor = (row: Row) => rowKey(row, contract.rowKey);
  const coherenceChecks = contract.coherenceChecks ?? [];
  const materialized = () =>
    materializeLedger({ ledger, claims: contract.claims, coherenceChecks });
  const allRowsUnitKeys = input.rows.map(unitKeyFor);
  const cohortChecks = contract.cohortChecks ?? [];
  const minimumCompleteResultsPerUnit =
    contract.minimumCompleteResultsPerUnit ?? 1;
  const targetRows = contract.targetRows ?? input.rows.length;
  const targetsEveryUnit = contract.targetRows === undefined;
  const completedTargetCount = (
    results: readonly SearchLedgerResult<Row>[],
  ): number => {
    if (!targetsEveryUnit)
      return results.filter((result) => result.complete).length;
    const completeCountsByUnit = new Map<string, number>();
    for (const result of results) {
      if (!result.complete) continue;
      completeCountsByUnit.set(
        result.unitKey,
        (completeCountsByUnit.get(result.unitKey) ?? 0) + 1,
      );
    }
    return unique(allRowsUnitKeys).filter(
      (unitKey) =>
        (completeCountsByUnit.get(unitKey) ?? 0) >=
        minimumCompleteResultsPerUnit,
    ).length;
  };
  const evaluateCohortsForUnitSet = (
    results: readonly SearchLedgerResult<Row>[],
    unitKeys: readonly string[],
  ) => evaluateCohorts({ checks: cohortChecks, results, unitKeys });
  const unitRowsNeedingWork = (
    rows: readonly Row[],
    unitKeys: readonly string[],
    results: readonly SearchLedgerResult<Row>[],
  ) =>
    rowsNeedingWork({
      rows,
      unitKeyFor,
      results,
      minimumCompleteResultsPerUnit,
      failedCohortClaimIds: failedCohortClaimIds(
        evaluateCohortsForUnitSet(results, unitKeys),
      ),
    });
  const recordsForUnit = (unitKey: string) =>
    records.filter((record) => record.unitKey === unitKey);
  const attemptedUnitsInPhase = (
    phase: SearchExperimentPhase,
    programId: string,
  ) =>
    new Set(
      records
        .filter(
          (record) => record.phase === phase && record.programId === programId,
        )
        .map((record) => record.unitKey),
    );
  const attemptedUnitsForProgram = (programId: string) =>
    new Set(
      records
        .filter((record) => record.programId === programId)
        .map((record) => record.unitKey),
    );
  let budgetBlocked = false;
  const estimatedDeeplineCredits = (): number | null => {
    const costs = input.definition.programs.map((program) =>
      estimateProgramCost({
        program: program as SearchProgram<Row, unknown>,
        records: records.filter((record) => record.programId === program.id),
      }),
    );
    return costs.every((cost) => cost.credits !== null)
      ? costs.reduce((total, cost) => total + cost.credits!, 0)
      : null;
  };

  const applyRecords = (batch: readonly AttemptRecord<Row>[]) => {
    for (const record of batch) {
      const before = materialized();
      addAttemptToLedger(ledger, record);
      records.push(record);
      const after = materialized();
      const beforeComplete = new Set(
        before
          .filter((result) => result.complete)
          .map((result) => result.identity),
      );
      const resultIdentities =
        record.attempt?.results.map((result) =>
          searchResultIdentity(record.unitKey, result.canonicalEntityKey),
        ) ?? [];
      const affectedAfter = after.filter((result) =>
        resultIdentities.includes(result.identity),
      );
      const outcome: SearchAttemptTrace['outcome'] = record.error
        ? 'adapter_failure'
        : !record.attempt?.results.length
          ? 'source_miss'
          : affectedAfter.some((result) => result.complete)
            ? 'verified'
            : 'rejected';
      traces.push({
        phase: record.phase,
        programId: record.programId,
        unitKey: record.unitKey,
        gapsBefore: record.gapsBefore,
        outcome,
        totalCalls: record.observedTotalCalls,
        deeplineCredits: record.observedDeeplineCredits,
        resultIdentities,
        verifiedClaimDelta: Math.max(
          0,
          verifiedClaimCount(after) - verifiedClaimCount(before),
        ),
        completeResultDelta: after.filter(
          (result) => result.complete && !beforeComplete.has(result.identity),
        ).length,
        ...(record.error ? { error: record.error } : {}),
      });
    }
  };

  const runWave = async (
    programs: readonly SearchProgram<Row, Context>[],
    rows: readonly Row[],
    phase: SearchExperimentPhase,
  ): Promise<Set<string>> => {
    const before = materialized();
    const completedTargets = completedTargetCount(before);
    const pairs = programs.flatMap((program) =>
      rows.map((row) => ({ program, row })),
    );
    const maximumCredits = input.definition.maximumDeeplineCredits;
    let admitted = pairs;
    if (maximumCredits !== undefined) {
      const current = estimatedDeeplineCredits();
      const remaining = Math.max(0, maximumCredits - (current ?? 0));
      if (phase === 'comparison') {
        const waveCeiling = pairs.reduce(
          (total, pair) =>
            total + pair.program.maximumDeeplineCreditsPerAttempt!,
          0,
        );
        admitted = waveCeiling <= remaining ? pairs : [];
      } else {
        let reserved = 0;
        admitted = pairs.filter(({ program }) => {
          const ceiling = program.maximumDeeplineCreditsPerAttempt!;
          if (reserved + ceiling > remaining) return false;
          reserved += ceiling;
          return true;
        });
      }
      if (!admitted.length && pairs.length) {
        budgetBlocked = true;
        return new Set();
      }
    }
    budgetBlocked = false;
    const batch = await Promise.all(
      admitted.map(({ program, row }) => {
        const unitKey = unitKeyFor(row);
        const candidates = before.filter(
          (result) => result.unitKey === unitKey,
        );
        return invokeProgram({
          ctx: input.ctx,
          program,
          row,
          unitKey,
          phase,
          gaps: gapsForUnit(unitKey, before, contract.claims),
          candidates,
          remainingTargetRows: Math.max(0, targetRows - completedTargets),
        });
      }),
    );
    applyRecords(batch);
    return new Set(admitted.map(({ program }) => program.id));
  };

  const retryUnlockedAttempts = async (
    programs: readonly SearchProgram<Row, Context>[],
    rows: readonly Row[],
    phase: SearchExperimentPhase,
  ) => {
    const priorAttempts = new Map(
      records
        .filter(
          (record) => record.phase === phase && record.attempt !== undefined,
        )
        .map((record) => [
          `${record.programId}\u0000${record.unitKey}`,
          record,
        ]),
    );
    for (const program of programs) {
      const results = materialized();
      const unitKeys = rows.map(unitKeyFor);
      const cohort = evaluateCohortsForUnitSet(results, unitKeys);
      const needed = rowsNeedingWork({
        rows,
        unitKeyFor,
        results,
        minimumCompleteResultsPerUnit,
        failedCohortClaimIds: failedCohortClaimIds(cohort),
      }).filter((row) => {
        const unitKey = unitKeyFor(row);
        const prior = priorAttempts.get(`${program.id}\u0000${unitKey}`);
        if (!prior) return false;
        const candidates = results.filter(
          (result) => result.unitKey === unitKey,
        );
        if (!prior.attempt?.results.length)
          return candidateState(candidates) !== prior.candidateStateBefore;
        const beforeProgramIds = new Set(prior.candidateProgramIdsBefore);
        return candidates.some((candidate) =>
          candidate.programIds.some(
            (programId) =>
              programId !== program.id && !beforeProgramIds.has(programId),
          ),
        );
      });
      if (!needed.length) continue;

      const completedTargets = completedTargetCount(results);
      if (
        phase === 'exploit' &&
        completedTargets >= targetRows &&
        cohort.every((check) => check.pass)
      )
        return;
      const batchSize =
        phase === 'exploit'
          ? Math.min(
              input.definition.exploitBatchSize ?? DEFAULT_EXPLOIT_BATCH_SIZE,
              Math.max(1, targetRows - completedTargets),
              needed.length,
            )
          : needed.length;
      await runWave([program], needed.slice(0, batchSize), phase);
    }
  };

  const explorationPrograms = selectHeterogeneousPrograms({
    programs: input.definition.programs,
    count: Math.min(
      input.definition.explorationProgramCount ??
        DEFAULT_EXPLORATION_PROGRAM_COUNT,
      input.definition.programs.length,
    ),
  });
  await runWave(explorationPrograms, split.comparisonRows, 'comparison');
  const comparisonBudgetBlocked = budgetBlocked;
  // Programs in the common wave intentionally see the same pre-wave ledger.
  // Give source misses one bounded retry when another program discovered a
  // candidate that still has claim or cohort gaps. This admits generic
  // discover -> verify compositions without declaring route-specific stages.
  if (!comparisonBudgetBlocked) {
    await retryUnlockedAttempts(
      explorationPrograms,
      split.comparisonRows,
      'comparison',
    );
  }
  const maxFallbacks =
    input.definition.maxFallbacks ??
    Math.min(2, input.definition.programs.length - 1);
  const provisional = choosePrograms({
    programs: input.definition.programs,
    records,
    claims: contract.claims,
    coherenceChecks,
    maxFallbacks,
    cohortChecks,
  });
  const remainingPilot = split.pilotRows.filter(
    (row) => !split.comparisonRows.includes(row),
  );
  for (const program of provisional.selected) {
    const results = materialized();
    const needed = unitRowsNeedingWork(
      remainingPilot,
      split.sketch.pilotUnitKeys,
      results,
    );
    if (needed.length) await runWave([program], needed, 'pilot');
  }
  await retryUnlockedAttempts(provisional.selected, remainingPilot, 'pilot');

  const finalChoice = choosePrograms({
    programs: input.definition.programs,
    records: records.filter(
      (record) => record.phase === 'comparison' || record.phase === 'pilot',
    ),
    claims: contract.claims,
    coherenceChecks,
    maxFallbacks,
    cohortChecks,
  });
  const selected = finalChoice.selected;
  const initialSelectedProgramIds = selected.map((program) => program.id);
  let activePrograms = [...selected];
  const selectionPassed =
    finalChoice.dependencyCycle.length === 0 && !comparisonBudgetBlocked;
  const pilotResultsBeforeAdaptation = materialized().filter((result) =>
    split.sketch.pilotUnitKeys.includes(result.unitKey),
  );
  const pilotCohortChecksBeforeAdaptation = evaluateCohorts({
    checks: cohortChecks,
    results: pilotResultsBeforeAdaptation,
    unitKeys: split.sketch.pilotUnitKeys,
  });
  const pilotPassedBeforeAdaptation =
    selectionPassed &&
    pilotResultsBeforeAdaptation.filter((result) => result.complete).length >=
      (contract.minimumPilotCompleteRows ?? 1) &&
    pilotCohortChecksBeforeAdaptation.every((check) => check.pass);

  if (pilotPassedBeforeAdaptation && split.holdoutRows.length) {
    for (const program of selected) {
      const results = materialized();
      const holdoutSubset = results.filter((result) =>
        split.sketch.holdoutUnitKeys.includes(result.unitKey),
      );
      const needed = unitRowsNeedingWork(
        split.holdoutRows,
        split.sketch.holdoutUnitKeys,
        holdoutSubset,
      );
      if (needed.length) await runWave([program], needed, 'holdout');
    }
    await retryUnlockedAttempts(selected, split.holdoutRows, 'holdout');
  }

  const gateRows = unique([...split.pilotRows, ...split.holdoutRows]);
  const gateUnitKeys = gateRows.map(unitKeyFor);
  const qualityGatePassed = (
    results: readonly SearchLedgerResult<Row>[],
  ): boolean => {
    const currentPilotResults = results.filter((result) =>
      split.sketch.pilotUnitKeys.includes(result.unitKey),
    );
    const currentPilotCohorts = evaluateCohorts({
      checks: cohortChecks,
      results: currentPilotResults,
      unitKeys: split.sketch.pilotUnitKeys,
    });
    if (
      currentPilotResults.filter((result) => result.complete).length <
        (contract.minimumPilotCompleteRows ?? 1) ||
      currentPilotCohorts.some((check) => !check.pass)
    )
      return false;
    if (!split.holdoutRows.length) return true;
    const currentHoldoutResults = results.filter((result) =>
      split.sketch.holdoutUnitKeys.includes(result.unitKey),
    );
    const currentHoldoutCohorts = evaluateCohorts({
      checks: cohortChecks,
      results: currentHoldoutResults,
      unitKeys: split.sketch.holdoutUnitKeys,
    });
    return (
      currentHoldoutResults.filter((result) => result.complete).length >=
        (contract.minimumHoldoutCompleteRows ?? 1) &&
      currentHoldoutCohorts.every((check) => check.pass)
    );
  };

  if (selectionPassed) {
    const challengeCounts = new Map<string, number>();

    while (true) {
      const results = materialized();
      const completedTargets = completedTargetCount(results);
      const cohort = evaluateCohortsForUnitSet(results, allRowsUnitKeys);
      const gatePassed = qualityGatePassed(results);
      if (
        gatePassed &&
        completedTargets >= targetRows &&
        cohort.every((check) => check.pass)
      )
        break;

      const eligibleRows = gatePassed ? input.rows : gateRows;
      const eligibleUnitKeys = gatePassed ? allRowsUnitKeys : gateUnitKeys;
      const unresolvedAll = unitRowsNeedingWork(
        eligibleRows,
        eligibleUnitKeys,
        results,
      );
      if (!unresolvedAll.length) break;

      const activeIds = new Set(activePrograms.map((program) => program.id));
      const attemptedUnitKeysByProgram = new Map<string, Set<string>>();
      for (const program of activePrograms) {
        attemptedUnitKeysByProgram.set(
          program.id,
          attemptedUnitsForProgram(program.id),
        );
      }
      const attemptedByEveryActive = (unitKey: string) =>
        activePrograms.every((program) =>
          attemptedUnitKeysByProgram.get(program.id)!.has(unitKey),
        );
      const needed = unresolvedAll.filter(
        (row) => !attemptedByEveryActive(unitKeyFor(row)),
      );
      const batchSize = Math.min(
        input.definition.exploitBatchSize ?? DEFAULT_EXPLOIT_BATCH_SIZE,
        Math.max(1, targetRows - completedTargets),
        needed.length,
      );
      const batchRows = needed.slice(0, batchSize);
      if (batchRows.length) {
        for (const program of activePrograms) {
          const currentResults = materialized();
          const attemptedUnitKeys =
            attemptedUnitKeysByProgram.get(program.id) ??
            attemptedUnitsForProgram(program.id);
          const programRows = unitRowsNeedingWork(
            batchRows,
            allRowsUnitKeys,
            currentResults,
          ).filter((row) => !attemptedUnitKeys.has(unitKeyFor(row)));
          if (programRows.length)
            await runWave([program], programRows, 'exploit');
        }
        await retryUnlockedAttempts(activePrograms, batchRows, 'exploit');
      }

      const afterBatch = materialized();
      const unresolved = batchRows.length
        ? unitRowsNeedingWork(batchRows, eligibleUnitKeys, afterBatch)
        : unitRowsNeedingWork(eligibleRows, eligibleUnitKeys, afterBatch);
      const provenProgramIds = new Set(
        input.definition.programs
          .filter(
            (program) =>
              scoreProgram({
                program: program as SearchProgram<Row, unknown>,
                records,
                claims: contract.claims,
                coherenceChecks,
              }).completeResults > 0,
          )
          .map((program) => program.id),
      );
      if (!unresolved.length) continue;
      if (maxFallbacks === 0) {
        if (!batchRows.length) break;
        continue;
      }

      const challengeableForRow = new Map<
        string,
        SearchProgram<Row, Context>[]
      >();
      for (const row of unresolved) {
        const unitKey = unitKeyFor(row);
        challengeableForRow.set(
          unitKey,
          input.definition.programs.filter(
            (program) =>
              !activeIds.has(program.id) &&
              !attemptedUnitsForProgram(program.id).has(unitKey) &&
              (challengeCounts.get(program.id) ?? 0) <
                (provenProgramIds.has(program.id)
                  ? MAX_LIVE_CHALLENGES_PER_PROVEN_PROGRAM
                  : MAX_LIVE_CHALLENGES_PER_PROGRAM),
          ),
        );
      }
      const mostOptions = Math.max(
        0,
        ...[...challengeableForRow.values()].map((programs) => programs.length),
      );
      const challengeRows = unresolved.filter(
        (row) =>
          challengeableForRow.get(unitKeyFor(row))!.length === mostOptions &&
          mostOptions > 0,
      );
      if (!challengeRows.length) {
        if (!batchRows.length) break;
        continue;
      }

      const challengeRow = selectDiverseRows({
        rows: challengeRows,
        rowKey: contract.rowKey,
        count: 1,
      })[0]!;
      const challengeUnitKey = unitKeyFor(challengeRow);
      const challengeable = challengeableForRow.get(challengeUnitKey)!;

      const challengeWave = selectHeterogeneousPrograms({
        programs: challengeable,
        count: Math.min(
          input.definition.challengeWaveSize ?? DEFAULT_CHALLENGE_WAVE_SIZE,
          challengeable.length,
        ),
        against: activePrograms,
      });
      const beforeProgramIds = activePrograms.map((program) => program.id);
      const beforeRecords = recordsForUnit(challengeUnitKey);
      const beforeCoverage = coverageForPrograms({
        programIds: new Set(beforeProgramIds),
        records: beforeRecords,
        claims: contract.claims,
        coherenceChecks,
        cohortChecks,
      });

      const executedChallengeIds = await runWave(
        challengeWave,
        [challengeRow],
        'challenge',
      );
      if (!executedChallengeIds.size && budgetBlocked) break;
      challengeWave
        .filter((program) => executedChallengeIds.has(program.id))
        .forEach((program) =>
          challengeCounts.set(
            program.id,
            (challengeCounts.get(program.id) ?? 0) + 1,
          ),
        );
      // A challenger may discover the candidate or partial evidence that an
      // already-active consumer needs. Give prior source misses one bounded
      // retry before judging whether the challenger improved this row.
      await retryUnlockedAttempts(activePrograms, [challengeRow], 'exploit');
      await retryUnlockedAttempts(challengeWave, [challengeRow], 'challenge');

      const challengeRecords = recordsForUnit(challengeUnitKey);
      const protectedProgramIds = replacementRequiredProgramIds({
        activePrograms,
        records,
      });
      const optionalActiveCount = beforeProgramIds.filter(
        (programId) => !protectedProgramIds.has(programId),
      ).length;
      const challengerChoice = choosePrograms({
        programs: input.definition.programs,
        records: challengeRecords,
        claims: contract.claims,
        coherenceChecks,
        maxFallbacks,
        requiredProgramIds:
          optionalActiveCount < maxFallbacks
            ? new Set(beforeProgramIds)
            : protectedProgramIds,
        cohortChecks,
      });
      const afterProgramIds = challengerChoice.selected.map(
        (program) => program.id,
      );
      const afterCoverage = coverageForPrograms({
        programIds: new Set(afterProgramIds),
        records: challengeRecords,
        claims: contract.claims,
        coherenceChecks,
        cohortChecks,
      });
      const promotedProgramIds = afterProgramIds.filter(
        (programId) => !activeIds.has(programId),
      );
      const promoted =
        challengerChoice.dependencyCycle.length === 0 &&
        promotedProgramIds.length > 0 &&
        coverageImproved(beforeCoverage, afterCoverage);
      if (promoted) {
        const chosenIds = new Set(
          challengerChoice.selected.map((program) => program.id),
        );
        const preferredProgramIds = [
          ...activePrograms
            .filter((program) => chosenIds.has(program.id))
            .map((program) => program.id),
          ...challengerChoice.selected
            .filter((program) => !activeIds.has(program.id))
            .map((program) => program.id),
        ];
        // Preserve the learned waterfall unless evidence proves a new route
        // is its producer. Producers move before consumers to avoid paying a
        // predictable miss-and-retry tax on every later batch.
        activePrograms = orderProgramsForExecution({
          programs: challengerChoice.selected,
          preferredProgramIds,
          records: challengeRecords,
        });
      }
      adaptations.push({
        unitKey: challengeUnitKey,
        beforeProgramIds,
        challengedProgramIds: challengeWave
          .filter((program) => executedChallengeIds.has(program.id))
          .map((program) => program.id),
        promotedProgramIds: promoted ? promotedProgramIds : [],
        afterProgramIds: promoted
          ? activePrograms.map((program) => program.id)
          : beforeProgramIds,
        reason: promoted
          ? 'Challenger evidence improved verified coverage on a shared unresolved unit.'
          : 'No challenger portfolio improved verified coverage within the fallback bound.',
      });
    }
  }

  const finalResults = materialized();
  const finalCohortChecks = evaluateCohorts({
    checks: cohortChecks,
    results: finalResults,
    unitKeys: input.rows.map(unitKeyFor),
  });
  const pilotResults = finalResults.filter((result) =>
    split.sketch.pilotUnitKeys.includes(result.unitKey),
  );
  const pilotCohortChecks = evaluateCohorts({
    checks: cohortChecks,
    results: pilotResults,
    unitKeys: split.sketch.pilotUnitKeys,
  });
  const pilotPassed =
    selectionPassed &&
    pilotResults.filter((result) => result.complete).length >=
      (contract.minimumPilotCompleteRows ?? 1) &&
    pilotCohortChecks.every((check) => check.pass);
  const holdoutResults = finalResults.filter((result) =>
    split.sketch.holdoutUnitKeys.includes(result.unitKey),
  );
  const holdoutCohortChecks = evaluateCohorts({
    checks: cohortChecks,
    results: holdoutResults,
    unitKeys: split.sketch.holdoutUnitKeys,
  });
  const holdoutPassed =
    !split.holdoutRows.length ||
    (holdoutResults.filter((result) => result.complete).length >=
      (contract.minimumHoldoutCompleteRows ?? 1) &&
      holdoutCohortChecks.every((check) => check.pass));
  const unresolvedUnitKeys = unitRowsNeedingWork(
    input.rows,
    allRowsUnitKeys,
    finalResults,
  ).map(unitKeyFor);
  const exploredProgramIds = unique(records.map((record) => record.programId));
  const unresolvedUnitKeySet = new Set(unresolvedUnitKeys);
  const failedProgramIds = unique(
    records
      .filter(
        (record) => record.error && unresolvedUnitKeySet.has(record.unitKey),
      )
      .map((record) => record.programId),
  );
  const exploredProgramIdSet = new Set(exploredProgramIds);
  const remainingProgramIds = input.definition.programs
    .filter((program) => !exploredProgramIdSet.has(program.id))
    .map((program) => program.id);
  const targetReached =
    pilotPassed &&
    holdoutPassed &&
    completedTargetCount(finalResults) >= targetRows &&
    finalCohortChecks.every((check) => check.pass);
  const status = targetReached ? 'promoted' : 'not_promoted';
  const stoppingReason: SearchExperimentResult<Row>['stoppingReason'] =
    targetReached
      ? 'target_reached'
      : comparisonBudgetBlocked || budgetBlocked
        ? 'budget_exhausted'
        : failedProgramIds.length
          ? 'adapter_failures'
          : selectionPassed
            ? 'programs_exhausted'
            : 'selection_failed';
  const totalCalls = traces.reduce(
    (total, trace) => total + trace.totalCalls,
    0,
  );
  const exhaustiveComparisonCalls =
    input.rows.length *
    input.definition.programs.reduce(
      (total, program) => total + program.maximumCallsPerAttempt,
      0,
    );
  const avoidedCalls = Math.max(0, exhaustiveComparisonCalls - totalCalls);
  const credits = summarizeCredits(records);
  const estimatedCredits = estimatedDeeplineCredits();
  const completeResults = finalResults.filter(
    (result) => result.complete,
  ).length;
  const finalScorecard = input.definition.programs
    .map((program) =>
      scoreProgram({
        program: program as SearchProgram<Row, unknown>,
        records,
        claims: contract.claims,
        coherenceChecks,
      }),
    )
    .sort(compareProgramScores);
  return {
    status,
    stoppingReason,
    targetRows,
    sketch: split.sketch,
    registeredProgramCount: input.definition.programs.length,
    exploredProgramIds,
    failedProgramIds,
    remainingProgramIds,
    unresolvedUnitKeys,
    selectedProgramIds: activePrograms.map((program) => program.id),
    initialSelectedProgramIds,
    scorecard: finalScorecard,
    attempts: traces,
    adaptations,
    pilotResults,
    holdoutResults,
    finalResults,
    pilotCohortChecks,
    holdoutCohortChecks,
    finalCohortChecks,
    holdoutPassed,
    totalCalls,
    estimatedDeeplineCredits: estimatedCredits,
    maximumDeeplineCredits: input.definition.maximumDeeplineCredits ?? null,
    exhaustiveComparisonCalls,
    avoidedCalls,
    leverage: {
      completeResults,
      totalCalls,
      exhaustiveCallBaseline: exhaustiveComparisonCalls,
      avoidedCalls,
      avoidedCallRatio: exhaustiveComparisonCalls
        ? avoidedCalls / exhaustiveComparisonCalls
        : 0,
      deeplineCredits: credits.total,
      unobservedCreditAttempts: credits.unobserved,
      completeResultsPerDeeplineCredit:
        credits.total !== null && credits.total > 0
          ? completeResults / credits.total
          : null,
    },
    costCoverageFrontier: provisional.costCoverageFrontier,
    rationale: [
      `Registered ${input.definition.programs.length} programs; compared ${explorationPrograms.length} maximally heterogeneous programs on ${split.comparisonRows.length} shared dataset-conditioned unit(s).`,
      finalChoice.dependencyCycle.length
        ? `Rejected cyclic producer dependencies: ${finalChoice.dependencyCycle.join(' -> ')}.`
        : `Selected ${initialSelectedProgramIds.join(' -> ')} by evidence score, marginal coverage, observed Deepline credits when known, and producer dependencies.`,
      pilotPassed
        ? 'Pilot passed frozen row and cohort checks.'
        : 'Pilot did not pass frozen row and cohort checks.',
      split.holdoutRows.length
        ? holdoutPassed
          ? 'Untouched holdout confirmed the selected order.'
          : 'Untouched holdout rejected the selected order; exploitation was skipped.'
        : 'No holdout was possible for this dataset size.',
      adaptations.length
        ? `Ran ${adaptations.length} bounded live challenge(s); the final waterfall is ${activePrograms.map((program) => program.id).join(' -> ')}.`
        : 'No live challenge was needed or admitted.',
      targetReached
        ? 'Stopped after the final accepted target and cohort checks passed.'
        : stoppingReason === 'budget_exhausted'
          ? `Stopped before the next bounded wave would exceed the ${input.definition.maximumDeeplineCredits} Deepline-credit ceiling.`
          : stoppingReason === 'adapter_failures'
            ? `Stopped with ${unresolvedUnitKeys.length} unresolved unit(s) and adapter failures in ${failedProgramIds.join(', ')}; these failures are not evidence of source absence.`
            : `Stopped with ${unresolvedUnitKeys.length} unresolved unit(s) after bounded eligible programs were exhausted.`,
      remainingProgramIds.length
        ? `Never reached: ${remainingProgramIds.join(', ')}. These registered program(s) were never invoked, so their zero results are not evidence of source absence and must not be read as a coverage ceiling.`
        : 'Every registered program was invoked at least once.',
      `Observed ${provisional.costCoverageFrontier.length} non-dominated cost/coverage option(s) in the shared comparison wave.`,
      credits.total === null
        ? `Per-attempt Deepline credits were unobserved for ${credits.unobserved} attempt(s); run-level billing delta remains authoritative.`
        : `Observed ${credits.total} Deepline credits across all experiment attempts.`,
    ],
  };
}
