type UnknownRecord = Record<string, unknown>;

const MAX_RESEARCH_EVIDENCE_EXCERPT_CHARS = 800;
const MAX_RESEARCH_RAW_SOURCE_CONTEXT_CHARS = 1_200;

export type ResearchEvidence = {
  source: string;
  independenceClass: string;
  url?: string;
  text?: string;
  publishedAt?: string;
  /** Set only by bindResearchEvidenceToSource after exact raw-text validation. */
  sourceBinding?: {
    kind: 'raw_source_text_excerpt';
    evidenceText: string;
    publishedAt?: string;
    /** Bounded literal source context retained for durable revalidation. */
    rawSourceContext: string;
    /** The exact raw source date span that produced publishedAt, when present. */
    dateExcerpt?: string;
  };
  /** A first-party or governed private record can stand alone when the claim says so. */
  authority?: 'authoritative' | 'supporting';
};

/**
 * Build a durable, short evidence excerpt only after matching it against the
 * raw document returned by the adapter. The raw document is deliberately not
 * retained in the evidence ledger: it is used to reject fabricated extractor
 * quotes before the candidate outcome is emitted.
 */
export function bindResearchEvidenceToSource(input: {
  source: string;
  independenceClass: string;
  url?: string;
  excerpt: unknown;
  rawSourceText: unknown;
  /**
   * The raw source span that states this evidence's publication date. The
   * binder parses and retains the date only after proving this span is local to
   * the bound evidence excerpt.
   */
  dateExcerpt?: unknown;
  /**
   * Opt in only when an extractor is known to normalize line breaks or runs of
   * whitespace. The stored evidence is still the exact substring recovered
   * from `rawSourceText`; any non-whitespace character change is rejected.
   */
  allowWhitespaceNormalization?: boolean;
  /**
   * Opt in only for extractors known to alter typography or punctuation. The
   * recovered evidence remains a literal source span and every letter and
   * digit must match case-sensitively and in order; this never permits a
   * paraphrase or a word-form change.
   */
  allowFormattingNormalization?: boolean;
  authority?: 'authoritative' | 'supporting';
}): ResearchEvidence | null {
  if (
    typeof input.excerpt !== 'string' ||
    typeof input.rawSourceText !== 'string' ||
    (input.dateExcerpt !== undefined && typeof input.dateExcerpt !== 'string')
  ) {
    return null;
  }
  const excerpt = input.excerpt;
  const sourceText = input.rawSourceText;
  const exactExcerpt =
    findExactRawExcerpt(excerpt, sourceText) ??
    (input.allowWhitespaceNormalization
      ? findWhitespaceEquivalentRawExcerpt(excerpt, sourceText)
      : null) ??
    (input.allowFormattingNormalization
      ? findFormattingEquivalentRawExcerpt(
          excerpt,
          sourceText,
          input.allowWhitespaceNormalization,
        )
      : null);
  if (!exactExcerpt) {
    return null;
  }
  if (exactExcerpt.length > MAX_RESEARCH_EVIDENCE_EXCERPT_CHARS) {
    return null;
  }
  const dateExcerpt = input.dateExcerpt ?? '';
  const boundDateExcerpt = dateExcerpt
    ? findExactRawExcerpt(dateExcerpt, sourceText)
    : null;
  if (
    dateExcerpt &&
    (!boundDateExcerpt || !exactExcerpt.includes(boundDateExcerpt))
  ) {
    return null;
  }
  const publishedAt = boundDateExcerpt
    ? parseResearchSourceDate(boundDateExcerpt)
    : null;
  if (dateExcerpt && !publishedAt) {
    return null;
  }
  const rawSourceContext = researchRawSourceContext(sourceText, exactExcerpt);
  const evidence = {
    source: input.source,
    independenceClass: input.independenceClass,
    ...(input.url ? { url: input.url } : {}),
    text: exactExcerpt,
    ...(publishedAt ? { publishedAt } : {}),
    sourceBinding: {
      kind: 'raw_source_text_excerpt',
      evidenceText: exactExcerpt,
      ...(publishedAt ? { publishedAt } : {}),
      rawSourceContext,
      ...(boundDateExcerpt ? { dateExcerpt: boundDateExcerpt } : {}),
    },
    ...(input.authority ? { authority: input.authority } : {}),
  } satisfies ResearchEvidence;
  return evidence;
}

/** Keep enough returned source text to revalidate a bound excerpt after replay. */
function researchRawSourceContext(
  sourceText: string,
  exactExcerpt: string,
): string {
  let start = sourceText.indexOf(exactExcerpt);
  while (start >= 0) {
    const end = start + exactExcerpt.length;
    if (hasResearchExcerptBoundaries(sourceText, start, end)) break;
    start = sourceText.indexOf(exactExcerpt, start + 1);
  }
  if (start < 0) return exactExcerpt;
  const contextBudget =
    MAX_RESEARCH_RAW_SOURCE_CONTEXT_CHARS - exactExcerpt.length;
  const prefixPadding = Math.floor(contextBudget / 2);
  const suffixPadding = contextBudget - prefixPadding;
  return sourceText.slice(
    Math.max(0, start - prefixPadding),
    Math.min(sourceText.length, start + exactExcerpt.length + suffixPadding),
  );
}

function startsWithResearchWordCharacter(value: string): boolean {
  return /^[\p{L}\p{N}\p{M}_]/u.test(value);
}

function endsWithResearchWordCharacter(value: string): boolean {
  return /[\p{L}\p{N}\p{M}_]$/u.test(value);
}

/**
 * An evidence excerpt may not start or stop midway through a source token.
 * This prevents a plausible-looking prefix such as "Example launch" from
 * being bound to a source sentence that actually says "Example launched".
 */
function hasResearchExcerptBoundaries(
  sourceText: string,
  start: number,
  end: number,
): boolean {
  const excerpt = sourceText.slice(start, end);
  if (!excerpt) return false;
  return (
    !(
      startsWithResearchWordCharacter(excerpt) &&
      endsWithResearchWordCharacter(sourceText.slice(0, start))
    ) &&
    !(
      endsWithResearchWordCharacter(excerpt) &&
      startsWithResearchWordCharacter(sourceText.slice(end))
    )
  );
}

function researchTextContainsLiteralValue(
  evidenceText: string,
  value: string,
): boolean {
  let start = evidenceText.indexOf(value);
  while (start >= 0) {
    const end = start + value.length;
    if (hasResearchExcerptBoundaries(evidenceText, start, end)) return true;
    start = evidenceText.indexOf(value, start + 1);
  }
  return false;
}

function findExactRawExcerpt(
  excerpt: string,
  sourceText: string,
): string | null {
  if (!excerpt || !sourceText) return null;
  let start = sourceText.indexOf(excerpt);
  while (start >= 0) {
    const end = start + excerpt.length;
    if (hasResearchExcerptBoundaries(sourceText, start, end)) {
      return sourceText.slice(start, end);
    }
    start = sourceText.indexOf(excerpt, start + 1);
  }
  return null;
}

/**
 * Recover a literal raw source span after an extractor changed only whitespace.
 * This is intentionally not case-insensitive, Unicode-normalizing, or fuzzy:
 * every non-whitespace character must still match exactly.
 */
function findWhitespaceEquivalentRawExcerpt(
  excerpt: string,
  sourceText: string,
): string | null {
  if (!excerpt || !sourceText) return null;
  const pattern = excerpt
    .split(/(\s+)/)
    .map((part) =>
      /^\s+$/.test(part) ? '\\s+' : part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
    )
    .join('');
  for (const match of sourceText.matchAll(new RegExp(pattern, 'gu'))) {
    const start = match.index ?? -1;
    const rawExcerpt = match[0] ?? '';
    if (
      start >= 0 &&
      hasResearchExcerptBoundaries(sourceText, start, start + rawExcerpt.length)
    ) {
      return rawExcerpt;
    }
  }
  return null;
}

/**
 * Recover a literal source span after only whitespace and punctuation differ.
 * The match is deliberately case-sensitive and token-exact: all letters and
 * digits from the extractor output must appear in the same order in the raw
 * source. This is narrower than fuzzy matching but accommodates curly quotes,
 * em dashes, and markdown punctuation emitted by structured extractors.
 */
function findFormattingEquivalentRawExcerpt(
  excerpt: string,
  sourceText: string,
  allowWhitespaceNormalization = false,
): string | null {
  if (!excerpt || !sourceText || !/[\p{L}\p{N}]/u.test(excerpt)) return null;
  const pattern = excerpt
    .split(/(\s+|[^\p{L}\p{N}\s]+)/u)
    .map((part) => {
      if (/^\s+$/u.test(part)) {
        return allowWhitespaceNormalization
          ? '\\s+'
          : part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      }
      if (/^[^\p{L}\p{N}\s]+$/u.test(part)) {
        return allowWhitespaceNormalization
          ? '[^\\p{L}\\p{N}]+?'
          : '[^\\p{L}\\p{N}\\s]+';
      }
      return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    })
    .join('');
  for (const match of sourceText.matchAll(new RegExp(pattern, 'gu'))) {
    const start = match.index ?? -1;
    const rawExcerpt = match[0] ?? '';
    if (
      start >= 0 &&
      hasResearchExcerptBoundaries(sourceText, start, start + rawExcerpt.length)
    ) {
      return rawExcerpt;
    }
  }
  return null;
}

/**
 * Verify that already-bound evidence atoms describe one local part of a raw
 * document rather than an accidental join between its headline, navigation,
 * related-content rail, or footer. Every supplied atom must be nonempty and
 * occur in one source window no larger than `maximumSpanChars`.
 */
export function areResearchEvidenceAtomsCoLocated(input: {
  rawSourceText: unknown;
  excerpts: readonly unknown[];
  maximumSpanChars?: number;
}): boolean {
  if (
    typeof input.rawSourceText !== 'string' ||
    !input.excerpts.every((excerpt) => typeof excerpt === 'string')
  ) {
    return false;
  }
  const sourceText = input.rawSourceText;
  const excerpts = input.excerpts;
  const maximumSpanChars = input.maximumSpanChars ?? 1_200;
  if (!sourceText || !excerpts.length || maximumSpanChars < 0) return false;
  type Occurrence = { group: number; start: number; end: number };
  const occurrences: Occurrence[] = [];
  for (const [group, excerpt] of excerpts.entries()) {
    if (!excerpt) return false;
    let start = sourceText.indexOf(excerpt);
    if (start < 0) return false;
    while (start >= 0) {
      occurrences.push({ group, start, end: start + excerpt.length });
      start = sourceText.indexOf(excerpt, start + 1);
    }
  }
  occurrences.sort((left, right) => left.start - right.start);
  const covered = new Map<number, number>();
  let left = 0;
  for (let right = 0; right < occurrences.length; right += 1) {
    const current = occurrences[right]!;
    covered.set(current.group, (covered.get(current.group) ?? 0) + 1);
    while (covered.size === excerpts.length) {
      const windowStart = occurrences[left]!.start;
      let windowEnd = 0;
      for (let index = left; index <= right; index += 1) {
        windowEnd = Math.max(windowEnd, occurrences[index]!.end);
      }
      if (windowEnd - windowStart <= maximumSpanChars) return true;
      const removed = occurrences[left]!;
      const remaining = (covered.get(removed.group) ?? 1) - 1;
      if (remaining) covered.set(removed.group, remaining);
      else covered.delete(removed.group);
      left += 1;
    }
  }
  return false;
}

const ENGLISH_MONTH_INDEX: Record<string, number> = {
  january: 0,
  february: 1,
  march: 2,
  april: 3,
  may: 4,
  june: 5,
  july: 6,
  august: 7,
  september: 8,
  october: 9,
  november: 10,
  december: 11,
};

function validIsoDate(
  year: number,
  monthIndex: number,
  day: number,
): string | null {
  const date = new Date(Date.UTC(year, monthIndex, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== monthIndex ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return date.toISOString().slice(0, 10);
}

/**
 * Parse one unambiguous date from a source excerpt. It supports ISO dates and
 * English `Month D, YYYY` / `D Month YYYY` text; ambiguous numeric dates and
 * excerpts with multiple distinct valid dates are rejected instead of silently
 * treating a model-normalized date as evidence.
 */
export function parseResearchSourceDate(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const text = value;
  const parsedDates = new Set<string>();
  const add = (date: string | null) => {
    if (date) parsedDates.add(date);
  };
  for (const match of text.matchAll(/(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)/g)) {
    add(validIsoDate(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  }
  for (const match of text.matchAll(
    /\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})\b/gi,
  )) {
    add(
      validIsoDate(
        Number(match[3]),
        ENGLISH_MONTH_INDEX[match[1]!.toLowerCase()]!,
        Number(match[2]),
      ),
    );
  }
  for (const match of text.matchAll(
    /\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b/gi,
  )) {
    add(
      validIsoDate(
        Number(match[3]),
        ENGLISH_MONTH_INDEX[match[2]!.toLowerCase()]!,
        Number(match[1]),
      ),
    );
  }
  return parsedDates.size === 1 ? [...parsedDates][0]! : null;
}

export type ResearchClaimValue = {
  value?: unknown;
  facts?: Record<string, unknown>;
  evidence?: readonly ResearchEvidence[];
  /** A deliberate no-answer is different from an unsupported answer. */
  abstainReason?: string;
};

export type ClaimAcceptanceInput<Row extends UnknownRecord> = {
  row: Row;
  claim: ResearchClaimValue;
  evidence: readonly ResearchEvidence[];
  independentEvidenceClasses: readonly string[];
};

export type ClaimAcceptance<Row extends UnknownRecord> =
  | boolean
  | { accepted: boolean; reason?: string }
  | ((
      input: ClaimAcceptanceInput<Row>,
    ) => boolean | { accepted: boolean; reason?: string });

export type ResearchClaim<Row extends UnknownRecord> = {
  id: string;
  question: string;
  required?: boolean;
  /** Facts that the candidate must expose separately from display text. */
  requiredFacts?: readonly string[];
  minimumEvidence?: number;
  minimumIndependentEvidenceClasses?: number;
  maximumEvidenceAgeDays?: number;
  referenceDate?: string;
  allowAuthoritativeSingle?: boolean;
  /**
   * Require a string claim value to occur exactly in one captured evidence
   * excerpt. This is the safe default.
   * Set false only for a genuinely derived value and pair it with an explicit
   * acceptance contract that explains how the derivation is validated.
   */
  requireValueInEvidence?: boolean;
  accept?: ClaimAcceptance<Row>;
};

export type CandidateOutcome = {
  claims: Readonly<Record<string, ResearchClaimValue | undefined>>;
  /**
   * Agent-authored, compact route telemetry. It is deliberately descriptive
   * rather than prescriptive: the kernel stores what the topology observed but
   * never chooses a source or a next action from it.
   */
  routeObservations?: readonly ResearchRouteObservation[];
  /**
   * Deepline credits observed for this candidate and row from its tool receipt
   * or run ledger. Leave unset when the receipt cannot attribute credits; an
   * unknown measurement is never scored as free.
   */
  deeplineCredits?: number | null;
  /**
   * Observed end-to-end candidate duration, not a provider-specific latency.
   * Leave unset rather than inventing a value.
   */
  durationMs?: number;
  /** A broken adapter invalidates selection; it is not a retrieval miss. */
  adapterFailures?: readonly string[];
  /**
   * A violation of the topology's authored private-data or activation policy.
   * Keep it separate from an adapter failure: a candidate can retrieve correct
   * evidence and still be unsafe to promote.
   */
  policyViolations?: readonly string[];
};

export type ResearchRouteObservation = {
  stage: string;
  sourcePolicy?: ResearchSourcePolicy;
  query?: string;
  requestedClaimIds?: readonly string[];
  consideredUrls?: readonly string[];
  selectedUrl?: string;
  fetchedUrl?: string;
  outcome: 'selected' | 'not_found' | 'fetched' | 'rejected' | 'skipped';
  detail?: string;
};

export type ResearchCandidate<Row extends UnknownRecord, Context> = {
  id: string;
  hypothesis: string;
  /**
   * The agent writes this callback beside the Play. It owns literal tool calls,
   * source policy, response adapters, and gap behavior. The compiler never
   * selects a provider or manufactures a claim.
   */
  run: (input: { row: Row; context: Context }) => Promise<CandidateOutcome>;
};

export type InputContract<Row extends UnknownRecord> = {
  rowKey: keyof Row & string;
  required: readonly (keyof Row & string)[];
  columns?: Partial<Record<keyof Row & string, string>>;
};

export type PromotionMetric =
  | 'verified_required_claim_coverage'
  | 'complete_rows'
  | 'independent_evidence_coverage'
  | 'deepline_credits_per_complete_row'
  | 'p95_duration_ms';

export type ResearchExperiment<Row extends UnknownRecord, Context> = {
  input: InputContract<Row>;
  claims: readonly ResearchClaim<Row>[];
  candidates: readonly ResearchCandidate<Row, Context>[];
  promotion?: {
    require?: {
      minimumVerifiedRequiredClaimCoverage?: number;
      minimumCompleteRows?: number;
      /** Legacy whole-route gate. Prefer typed per-row failure handling. */
      noAdapterFailures?: boolean;
      noPolicyViolations?: boolean;
      /**
       * Legacy opt-in cost gate. The runtime may not expose per-call credits;
       * unknown cost must never be replaced with a fabricated zero or estimate.
       */
      noUnknownDeeplineCredits?: boolean;
    };
    /** Defaults to quality first, then Deepline credits and wall time. */
    rank?: readonly PromotionMetric[];
  };
};

export type ClaimEvaluation = {
  claimId: string;
  required: boolean;
  status: 'verified' | 'abstained' | 'insufficient_evidence' | 'rejected';
  reason: string;
  value?: unknown;
  facts: Record<string, unknown>;
  evidence: ResearchEvidence[];
  independentEvidenceClasses: string[];
};

declare const validatedClaimEvaluationBrand: unique symbol;

/**
 * An evaluation minted by `evaluateResearchClaimValues(...)` in this process.
 * The private brand prevents callers from satisfying the pilot contract with a
 * structurally similar object, while the runtime receipt is checked again when
 * a strategy is scored.
 */
export type ValidatedClaimEvaluation = ClaimEvaluation & {
  readonly [validatedClaimEvaluationBrand]: true;
};

type ValidatedClaimEvaluationReceipt = {
  scope: string;
  claimId: string;
  status: ClaimEvaluation['status'];
  value: unknown;
  evidenceSnapshots: readonly string[];
  independentEvidenceClasses: readonly string[];
};

const validatedClaimEvaluations = new WeakMap<
  object,
  ValidatedClaimEvaluationReceipt
>();

function researchEvidenceSnapshot(evidence: ResearchEvidence): string {
  return JSON.stringify({
    source: evidence.source,
    independenceClass: evidence.independenceClass,
    url: evidence.url ?? null,
    text: evidence.text ?? null,
    publishedAt: evidence.publishedAt ?? null,
    authority: evidence.authority ?? null,
    sourceBinding: evidence.sourceBinding
      ? {
          kind: evidence.sourceBinding.kind,
          evidenceText: evidence.sourceBinding.evidenceText,
          publishedAt: evidence.sourceBinding.publishedAt ?? null,
          rawSourceContext: evidence.sourceBinding.rawSourceContext,
          dateExcerpt: evidence.sourceBinding.dateExcerpt ?? null,
        }
      : null,
  });
}

/**
 * A claim that a topology has not yet established. This is deliberately a
 * small, source-agnostic planning artifact: the agent still authors which
 * first-party or independent route can fill the gap.
 */
export type ResearchClaimGap = Pick<
  ClaimEvaluation,
  'claimId' | 'required' | 'status' | 'reason'
>;

export type CandidateRowEvaluation<Row extends UnknownRecord> = {
  candidateId: string;
  row: Row;
  rowKey: string;
  claims: ClaimEvaluation[];
  /** Compact topology telemetry is retained with the evaluated pilot row. */
  routeObservations: ResearchRouteObservation[];
  complete: boolean;
  deeplineCredits: number | null;
  durationMs: number | null;
  adapterFailures: string[];
  policyViolations: string[];
};

export type CandidateScorecard = {
  candidateId: string;
  hypothesis: string;
  pilotRows: number;
  verifiedRequiredClaims: number;
  requiredClaims: number;
  verifiedRequiredClaimCoverage: number;
  completeRows: number;
  independentEvidenceClaims: number;
  independentEvidenceCoverage: number;
  totalDeeplineCredits: number | null;
  deeplineCreditsPerCompleteRow: number | null;
  p95DurationMs: number | null;
  unobservedCreditRows: number;
  unobservedDurationRows: number;
  adapterFailures: string[];
  policyViolations: string[];
  eligible: boolean;
  exclusionReasons: string[];
};

export type PromotionArtifact = {
  type: 'deepline.research_experiment_promotion';
  schemaVersion: 1;
  status: 'promoted' | 'not_promoted';
  selectedCandidateId: string | null;
  scorecard: CandidateScorecard[];
  reason: string;
};

export type ExperimentAttempt<Row extends UnknownRecord> = {
  row: Row;
  candidateId: string;
  outcome: CandidateOutcome;
};

/**
 * Attach agent-observed timing without reading the clock itself. Play authors
 * obtain both timestamps inside one literal `ctx.step(...)` so replay sees a
 * checkpointed measurement rather than fresh wall-clock reads.
 */
export function measureResearchCandidate(
  outcome: CandidateOutcome,
  timing: { startedAt: number; finishedAt: number },
): CandidateOutcome {
  if (outcome.durationMs !== undefined) return outcome;
  if (
    !Number.isFinite(timing.startedAt) ||
    !Number.isFinite(timing.finishedAt) ||
    timing.finishedAt < timing.startedAt
  ) {
    throw new Error('Research candidate measurement has invalid timestamps.');
  }
  return {
    ...outcome,
    durationMs: timing.finishedAt - timing.startedAt,
  };
}

const DEFAULT_RANK: readonly PromotionMetric[] = [
  'verified_required_claim_coverage',
  'complete_rows',
  'independent_evidence_coverage',
  'deepline_credits_per_complete_row',
  'p95_duration_ms',
];

const DEFAULT_PROMOTION_REQUIREMENTS: NonNullable<
  NonNullable<
    ResearchExperiment<UnknownRecord, unknown>['promotion']
  >['require']
> = {
  minimumVerifiedRequiredClaimCoverage: 1,
  minimumCompleteRows: 1,
  noAdapterFailures: false,
  noPolicyViolations: true,
  noUnknownDeeplineCredits: false,
};

/**
 * A sourceBinding's shape alone is not proof that the raw-text binder made it:
 * an adapter could construct the same JSON. Revalidate a bounded literal source
 * context and, for dated claims, the exact source date span on every evaluation.
 * This is durable across dataset materialization and replay, but not a sealed
 * provider receipt: a hostile Play author can still fabricate raw content.
 */
function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function isResearchSourceBoundEvidence(
  value: unknown,
): value is ResearchEvidence {
  const evidence = asRecord(value);
  const sourceBinding = asRecord(evidence.sourceBinding);
  return (
    typeof evidence.source === 'string' &&
    typeof evidence.independenceClass === 'string' &&
    typeof evidence.text === 'string' &&
    evidence.text.length <= MAX_RESEARCH_EVIDENCE_EXCERPT_CHARS &&
    sourceBinding.kind === 'raw_source_text_excerpt' &&
    sourceBinding.evidenceText === evidence.text &&
    typeof sourceBinding.rawSourceContext === 'string' &&
    sourceBinding.rawSourceContext.length <=
      MAX_RESEARCH_RAW_SOURCE_CONTEXT_CHARS &&
    findExactRawExcerpt(evidence.text, sourceBinding.rawSourceContext) ===
      evidence.text &&
    (evidence.publishedAt === undefined
      ? sourceBinding.publishedAt === undefined &&
        sourceBinding.dateExcerpt === undefined
      : typeof evidence.publishedAt === 'string' &&
        sourceBinding.publishedAt === evidence.publishedAt &&
        typeof sourceBinding.dateExcerpt === 'string' &&
        evidence.text.includes(sourceBinding.dateExcerpt) &&
        parseResearchSourceDate(sourceBinding.dateExcerpt) ===
          evidence.publishedAt) &&
    (evidence.url === undefined || typeof evidence.url === 'string') &&
    (evidence.authority === undefined ||
      evidence.authority === 'authoritative' ||
      evidence.authority === 'supporting')
  );
}

/**
 * Verify that a claim evaluation came from this module's evaluator and still
 * carries valid literal source bindings. Receipts are intentionally
 * process-local: evaluate claims and select a strategy in the same Play run.
 */
export function isValidatedResearchClaimEvaluation(
  value: unknown,
  expectedScope?: string,
): value is ValidatedClaimEvaluation {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const receipt = validatedClaimEvaluations.get(value);
  if (!receipt) return false;
  const evaluation = value as ClaimEvaluation;
  return (
    (expectedScope === undefined || receipt.scope === expectedScope) &&
    evaluation.claimId === receipt.claimId &&
    evaluation.status === receipt.status &&
    Object.is(evaluation.value, receipt.value) &&
    Array.isArray(evaluation.evidence) &&
    evaluation.evidence.length === receipt.evidenceSnapshots.length &&
    evaluation.evidence.every(
      (evidence, index) =>
        researchEvidenceSnapshot(evidence) === receipt.evidenceSnapshots[index],
    ) &&
    evaluation.evidence.every(isResearchSourceBoundEvidence) &&
    Array.isArray(evaluation.independentEvidenceClasses) &&
    sameStringArray(
      evaluation.independentEvidenceClasses,
      receipt.independentEvidenceClasses,
    ) &&
    evaluation.evidence.every((evidence) =>
      evaluation.independentEvidenceClasses.includes(
        evidence.independenceClass,
      ),
    )
  );
}

function sameStringArray(
  left: readonly string[],
  right: readonly string[],
): boolean {
  return (
    left.length === right.length &&
    left.every((item, index) => item === right[index])
  );
}

function hasValue(value: unknown): boolean {
  return typeof value === 'string'
    ? value.trim().length > 0
    : value !== undefined && value !== null;
}

/**
 * Normalize either a bare domain or a URL before an agent applies a
 * first-party evidence gate. `new URL('example.com')` throws, so accepting
 * bare domains here avoids silently rejecting every official page.
 */
export function normalizeResearchHost(value: unknown): string {
  const candidate = String(value ?? '').trim();
  if (!candidate) return '';
  try {
    const url = new URL(
      /^[a-z][a-z\d+.-]*:\/\//i.test(candidate)
        ? candidate
        : `https://${candidate}`,
    );
    return url.hostname.toLowerCase().replace(/^www\./, '');
  } catch {
    return '';
  }
}

/**
 * Check an exact canonical host, its `www` alias, or an explicitly admitted
 * first-party host. An unconstrained suffix match would treat `evil.co.uk` as
 * first-party for the invalid canonical input `co.uk`.
 */
export function isResearchFirstPartySource(
  sourceUrlOrHost: unknown,
  canonicalDomain: unknown,
  additionalFirstPartyHosts: readonly unknown[] = [],
): boolean {
  const sourceHost = normalizeResearchHost(sourceUrlOrHost);
  const expectedHost = normalizeResearchHost(canonicalDomain);
  const allowedHosts = new Set([
    expectedHost,
    expectedHost ? `www.${expectedHost}` : '',
    ...additionalFirstPartyHosts.map(normalizeResearchHost),
  ]);
  return Boolean(sourceHost && expectedHost && allowedHosts.has(sourceHost));
}

export type ResearchSourcePolicy = 'first_party_only' | 'non_first_party_only';

/** Apply a topology's source policy to the URL actually returned by its adapter. */
export function matchesResearchSourcePolicy(
  sourceUrlOrHost: unknown,
  canonicalDomain: unknown,
  policy: ResearchSourcePolicy,
  additionalFirstPartyHosts: readonly unknown[] = [],
): boolean {
  const sourceHost = normalizeResearchHost(sourceUrlOrHost);
  const expectedHost = normalizeResearchHost(canonicalDomain);
  if (!sourceHost || !expectedHost) return false;
  const firstParty = isResearchFirstPartySource(
    sourceHost,
    canonicalDomain,
    additionalFirstPartyHosts,
  );
  return policy === 'first_party_only' ? firstParty : !firstParty;
}

function daysOld(publishedAt: string, referenceDate: string): number | null {
  const parseIsoDate = (value: string): number | null => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) return null;
    const normalized = validIsoDate(
      Number(match[1]),
      Number(match[2]) - 1,
      Number(match[3]),
    );
    if (normalized !== value) return null;
    return Date.parse(`${normalized}T00:00:00.000Z`);
  };
  const published = parseIsoDate(publishedAt);
  const reference = parseIsoDate(referenceDate);
  if (published === null || reference === null) return null;
  return Math.floor((reference - published) / 86_400_000);
}

function percentile95(values: readonly number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.ceil(sorted.length * 0.95) - 1] ?? 0;
}

function normalizeAcceptance<Row extends UnknownRecord>(
  acceptance: ClaimAcceptance<Row> | undefined,
  input: ClaimAcceptanceInput<Row>,
): { accepted: boolean; reason?: string } {
  if (acceptance === undefined) return { accepted: true };
  const result =
    typeof acceptance === 'function' ? acceptance(input) : acceptance;
  return typeof result === 'boolean' ? { accepted: result } : result;
}

function evaluateClaim<Row extends UnknownRecord>(input: {
  row: Row;
  definition: ResearchClaim<Row>;
  result: ResearchClaimValue | undefined;
}): ClaimEvaluation {
  const { row, definition } = input;
  const result = input.result ?? {};
  const facts = asRecord(result.facts);
  const rawEvidence = Array.isArray(result.evidence) ? result.evidence : [];
  const candidateEvidence = rawEvidence.filter(isResearchSourceBoundEvidence);
  const rejectedEvidence = rawEvidence.length !== candidateEvidence.length;
  const candidateEvidenceClasses = [
    ...new Set(
      candidateEvidence.map((item) => item.independenceClass).filter(Boolean),
    ),
  ];
  const required = definition.required !== false;
  if (result.abstainReason) {
    return {
      claimId: definition.id,
      required,
      status: 'abstained',
      reason: result.abstainReason,
      facts,
      evidence: candidateEvidence,
      independentEvidenceClasses: candidateEvidenceClasses,
    };
  }
  if (rejectedEvidence && !candidateEvidence.length) {
    return {
      claimId: definition.id,
      required,
      status: 'insufficient_evidence',
      reason: 'requires source-bound evidence',
      value: result.value,
      facts,
      evidence: candidateEvidence,
      independentEvidenceClasses: candidateEvidenceClasses,
    };
  }
  if (!hasValue(result.value)) {
    return {
      claimId: definition.id,
      required,
      status: 'insufficient_evidence',
      reason: 'candidate returned no claim value',
      facts,
      evidence: candidateEvidence,
      independentEvidenceClasses: candidateEvidenceClasses,
    };
  }
  const literalClaimValue =
    definition.requireValueInEvidence !== false
      ? typeof result.value === 'string'
      : true;
  if (!literalClaimValue) {
    return {
      claimId: definition.id,
      required,
      status: 'insufficient_evidence',
      reason: 'literal claim values must be strings',
      facts,
      evidence: candidateEvidence,
      independentEvidenceClasses: candidateEvidenceClasses,
    };
  }
  const value = typeof result.value === 'string' ? result.value : '';
  const evidenceSupportsClaim = (item: ResearchEvidence): boolean =>
    definition.requireValueInEvidence === false
      ? Boolean(item.text?.trim())
      : researchTextContainsLiteralValue(item.text ?? '', value);
  const evidence = candidateEvidence.filter(evidenceSupportsClaim);
  const independentEvidenceClasses = [
    ...new Set(evidence.map((item) => item.independenceClass).filter(Boolean)),
  ];
  const missingFact = (definition.requiredFacts ?? []).find(
    (fact) => !hasValue(facts[fact]),
  );
  if (missingFact) {
    return {
      claimId: definition.id,
      required,
      status: 'insufficient_evidence',
      reason: `missing required fact: ${missingFact}`,
      value: result.value,
      facts,
      evidence,
      independentEvidenceClasses,
    };
  }
  const authoritativeSingle =
    definition.allowAuthoritativeSingle === true &&
    evidence.some((item) => item.authority === 'authoritative');
  const minimumEvidence = definition.minimumEvidence ?? 1;
  if (evidence.length < minimumEvidence) {
    return {
      claimId: definition.id,
      required,
      status: 'insufficient_evidence',
      reason: `requires at least ${minimumEvidence} evidence item(s)`,
      value: result.value,
      facts,
      evidence,
      independentEvidenceClasses,
    };
  }
  const minimumClasses = definition.minimumIndependentEvidenceClasses ?? 1;
  if (
    !authoritativeSingle &&
    independentEvidenceClasses.length < minimumClasses
  ) {
    return {
      claimId: definition.id,
      required,
      status: 'insufficient_evidence',
      reason: `requires ${minimumClasses} independent evidence class(es)`,
      value: result.value,
      facts,
      evidence,
      independentEvidenceClasses,
    };
  }
  if (definition.maximumEvidenceAgeDays !== undefined) {
    const referenceDate = definition.referenceDate;
    const withinWindow = referenceDate
      ? evidence.some((item) => {
          if (!item.publishedAt) return false;
          const age = daysOld(item.publishedAt, referenceDate);
          return (
            age !== null &&
            age >= 0 &&
            age <= definition.maximumEvidenceAgeDays!
          );
        })
      : false;
    if (!withinWindow) {
      return {
        claimId: definition.id,
        required,
        status: 'insufficient_evidence',
        reason: 'claim evidence is undated or outside the requested window',
        value: result.value,
        facts,
        evidence,
        independentEvidenceClasses,
      };
    }
  }
  if (definition.requireValueInEvidence !== false) {
    const valueOccursInEvidence = evidence.length > 0;
    if (!valueOccursInEvidence) {
      return {
        claimId: definition.id,
        required,
        status: 'insufficient_evidence',
        reason: 'claim value does not occur in a captured evidence excerpt',
        value: result.value,
        facts,
        evidence,
        independentEvidenceClasses,
      };
    }
  }
  const accepted = normalizeAcceptance(definition.accept, {
    row,
    claim: result,
    evidence,
    independentEvidenceClasses,
  });
  return {
    claimId: definition.id,
    required,
    status: accepted.accepted ? 'verified' : 'rejected',
    reason:
      accepted.reason ??
      (accepted.accepted
        ? 'claim meets acceptance contract'
        : 'claim rejected by acceptance contract'),
    value: result.value,
    facts,
    evidence,
    independentEvidenceClasses,
  };
}

/**
 * Evaluate a partial candidate result before deciding whether a supplemental
 * source is worth calling. This uses the same literal-evidence and semantic
 * acceptance gates as the final experiment evaluation, so an extractor's
 * nonempty string never suppresses a necessary gap-only lookup.
 */
export function evaluateResearchClaimValues<Row extends UnknownRecord>(input: {
  row: Row;
  definitions: readonly ResearchClaim<Row>[];
  claims: Readonly<Record<string, ResearchClaimValue | undefined>>;
  /** Bind receipts to a pilot route/result when they will drive promotion. */
  receiptScope?: string;
}): ValidatedClaimEvaluation[] {
  return input.definitions.map((definition) => {
    const evaluation = evaluateClaim({
      row: input.row,
      definition,
      result: input.claims[definition.id],
    });
    validatedClaimEvaluations.set(evaluation, {
      scope: input.receiptScope ?? '',
      claimId: evaluation.claimId,
      status: evaluation.status,
      value: evaluation.value,
      evidenceSnapshots: evaluation.evidence.map(researchEvidenceSnapshot),
      independentEvidenceClasses: [...evaluation.independentEvidenceClasses],
    });
    return evaluation as ValidatedClaimEvaluation;
  });
}

/**
 * Return the exact claims that remain unverified after one source pass.
 * By default this includes required and optional claims: an agent can narrow
 * the route to required-only when the task's budget demands it.
 */
export function getResearchClaimGaps<Row extends UnknownRecord>(input: {
  row: Row;
  definitions: readonly ResearchClaim<Row>[];
  claims: Readonly<Record<string, ResearchClaimValue | undefined>>;
  requiredOnly?: boolean;
}): ResearchClaimGap[] {
  return evaluateResearchClaimValues(input)
    .filter(
      (claim) =>
        claim.status !== 'verified' &&
        (input.requiredOnly !== true || claim.required),
    )
    .map(({ claimId, required, status, reason }) => ({
      claimId,
      required,
      status,
      reason,
    }));
}

/**
 * Admit supplemental output only for claim IDs proven unresolved after the
 * first pass. This protects already-verified evidence from a broader follow-up
 * extractor and leaves all source selection and semantic contracts with the
 * agent-authored topology. A supplemental result clears an explicit abstention
 * only when it independently passes that claim's full authored contract.
 */
export function fillResearchClaimGaps<Row extends UnknownRecord>(input: {
  row: Row;
  definitions: readonly ResearchClaim<Row>[];
  primary: Readonly<Record<string, ResearchClaimValue | undefined>>;
  supplemental: Readonly<Record<string, ResearchClaimValue | undefined>>;
  gapIds: readonly string[];
}): Record<string, ResearchClaimValue | undefined> {
  const definitions = new Map(
    input.definitions.map((definition) => [definition.id, definition]),
  );
  const unresolvedClaimIds = new Set(
    getResearchClaimGaps({
      row: input.row,
      definitions: input.definitions,
      claims: input.primary,
    }).map((gap) => gap.claimId),
  );
  const merged: Record<string, ResearchClaimValue | undefined> = {
    ...input.primary,
  };
  for (const claimId of input.gapIds) {
    if (!unresolvedClaimIds.has(claimId)) continue;
    const supplementalClaim = input.supplemental[claimId];
    if (supplementalClaim !== undefined) {
      const primaryClaim = input.primary[claimId];
      const definition = definitions.get(claimId);
      merged[claimId] = primaryClaim
        ? (() => {
            const preservePrimaryAbstention =
              Boolean(primaryClaim.abstainReason) &&
              (!definition ||
                evaluateClaim({
                  row: input.row,
                  definition,
                  result: supplementalClaim,
                }).status !== 'verified');
            const { abstainReason: _primaryAbstainReason, ...primaryValue } =
              primaryClaim;
            const {
              abstainReason: supplementalAbstainReason,
              ...supplementalValue
            } = supplementalClaim;
            return {
              ...primaryValue,
              ...supplementalValue,
              ...(supplementalAbstainReason
                ? { abstainReason: supplementalAbstainReason }
                : preservePrimaryAbstention
                  ? { abstainReason: primaryClaim.abstainReason }
                  : {}),
              facts: {
                ...(primaryClaim.facts ?? {}),
                ...(supplementalClaim.facts ?? {}),
              },
              evidence: [
                ...(primaryClaim.evidence ?? []),
                ...(supplementalClaim.evidence ?? []),
              ],
            };
          })()
        : supplementalClaim;
    }
  }
  return merged;
}

/**
 * Combine one measured action into a row's accumulated research outcome.
 *
 * This is deliberately narrow: an action may supplement only the unresolved
 * claim IDs declared on its action card. It cannot overwrite already-verified
 * facts simply because a later provider returned a different value. Credits
 * become unknown when either leg is unknown, so a multi-action candidate can
 * never become eligible by accidentally treating an unmeasured action as free.
 */
export function mergeResearchActionOutcome<Row extends UnknownRecord>(input: {
  row: Row;
  definitions: readonly ResearchClaim<Row>[];
  primary: CandidateOutcome;
  supplemental: CandidateOutcome;
  gapIds: readonly string[];
}): CandidateOutcome {
  const totalCredits = sumObservedResearchMeasurement(
    'Deepline credits',
    input.primary.deeplineCredits,
    input.supplemental.deeplineCredits,
  );
  const totalDuration = sumOptionalResearchDuration(
    input.primary.durationMs,
    input.supplemental.durationMs,
  );
  return {
    claims: fillResearchClaimGaps({
      row: input.row,
      definitions: input.definitions,
      primary: input.primary.claims,
      supplemental: input.supplemental.claims,
      gapIds: input.gapIds,
    }),
    routeObservations: [
      ...(input.primary.routeObservations ?? []),
      ...(input.supplemental.routeObservations ?? []),
    ],
    deeplineCredits: totalCredits,
    ...(totalDuration === undefined ? {} : { durationMs: totalDuration }),
    adapterFailures: [
      ...(input.primary.adapterFailures ?? []),
      ...(input.supplemental.adapterFailures ?? []),
    ],
    policyViolations: [
      ...(input.primary.policyViolations ?? []),
      ...(input.supplemental.policyViolations ?? []),
    ],
  };
}

function sumObservedResearchMeasurement(
  name: string,
  left: number | null | undefined,
  right: number | null | undefined,
): number | null {
  for (const value of [left, right]) {
    if (
      value !== undefined &&
      value !== null &&
      (!Number.isFinite(value) || value < 0)
    ) {
      throw new Error(`${name} must be finite and non-negative.`);
    }
  }
  if (
    left === undefined ||
    left === null ||
    right === undefined ||
    right === null
  ) {
    return null;
  }
  return left + right;
}

function sumOptionalResearchDuration(
  left: number | undefined,
  right: number | undefined,
): number | undefined {
  for (const value of [left, right]) {
    if (value !== undefined && (!Number.isFinite(value) || value < 0)) {
      throw new Error(
        'Research action duration must be finite and non-negative.',
      );
    }
  }
  return left === undefined || right === undefined ? undefined : left + right;
}

/** Preserve the agent-authored program while rejecting ambiguous topology config early. */
export function defineResearchExperiment<Row extends UnknownRecord, Context>(
  definition: ResearchExperiment<Row, Context>,
): ResearchExperiment<Row, Context> {
  const ids = definition.candidates.map((candidate) => candidate.id);
  if (!ids.length)
    throw new Error(
      'Research experiment needs at least one candidate topology.',
    );
  if (new Set(ids).size !== ids.length)
    throw new Error('Research experiment candidate IDs must be unique.');
  const claimIds = definition.claims.map((claim) => claim.id);
  if (!claimIds.length) {
    throw new Error('Research experiment needs at least one claim contract.');
  }
  if (new Set(claimIds).size !== claimIds.length)
    throw new Error('Research experiment claim IDs must be unique.');
  for (const claim of definition.claims) {
    if (
      claim.requireValueInEvidence === false &&
      typeof claim.accept !== 'function'
    ) {
      throw new Error(
        `Research claim "${claim.id}" opts out of literal evidence but has no explicit acceptance function.`,
      );
    }
  }
  if (!definition.input.required.includes(definition.input.rowKey)) {
    throw new Error(
      'Research experiment rowKey must be a required input field.',
    );
  }
  const requirements = definition.promotion?.require;
  if (
    requirements?.minimumVerifiedRequiredClaimCoverage !== undefined &&
    (!Number.isFinite(requirements.minimumVerifiedRequiredClaimCoverage) ||
      requirements.minimumVerifiedRequiredClaimCoverage < 0 ||
      requirements.minimumVerifiedRequiredClaimCoverage > 1)
  ) {
    throw new Error(
      'Research experiment minimumVerifiedRequiredClaimCoverage must be finite and between 0 and 1.',
    );
  }
  if (
    requirements?.minimumCompleteRows !== undefined &&
    (!Number.isSafeInteger(requirements.minimumCompleteRows) ||
      requirements.minimumCompleteRows < 0)
  ) {
    throw new Error(
      'Research experiment minimumCompleteRows must be a non-negative safe integer.',
    );
  }
  return definition;
}

function candidateScore<Row extends UnknownRecord, Context>(input: {
  definition: ResearchExperiment<Row, Context>;
  candidate: ResearchCandidate<Row, Context>;
  rows: readonly CandidateRowEvaluation<Row>[];
}): CandidateScorecard {
  const requiredClaims = input.rows.reduce(
    (total, row) => total + row.claims.filter((claim) => claim.required).length,
    0,
  );
  const verifiedRequiredClaims = input.rows.reduce(
    (total, row) =>
      total +
      row.claims.filter(
        (claim) => claim.required && claim.status === 'verified',
      ).length,
    0,
  );
  const independentEvidenceClaims = input.rows.reduce(
    (total, row) =>
      total +
      row.claims.filter(
        (claim) =>
          claim.status === 'verified' &&
          claim.independentEvidenceClasses.length >= 2,
      ).length,
    0,
  );
  const totalClaims = input.rows.reduce(
    (total, row) => total + row.claims.length,
    0,
  );
  const completeRows = input.rows.filter((row) => row.complete).length;
  const observedCredits = input.rows
    .map((row) => row.deeplineCredits)
    .filter((credits): credits is number => credits !== null);
  const observedDurations = input.rows
    .map((row) => row.durationMs)
    .filter((duration): duration is number => duration !== null);
  const unobservedCreditRows = input.rows.length - observedCredits.length;
  const unobservedDurationRows = input.rows.length - observedDurations.length;
  const totalDeeplineCredits = unobservedCreditRows
    ? null
    : observedCredits.reduce((total, credits) => total + credits, 0);
  return {
    candidateId: input.candidate.id,
    hypothesis: input.candidate.hypothesis,
    pilotRows: input.rows.length,
    verifiedRequiredClaims,
    requiredClaims,
    verifiedRequiredClaimCoverage: requiredClaims
      ? verifiedRequiredClaims / requiredClaims
      : 1,
    completeRows,
    independentEvidenceClaims,
    independentEvidenceCoverage: totalClaims
      ? independentEvidenceClaims / totalClaims
      : 0,
    totalDeeplineCredits,
    deeplineCreditsPerCompleteRow: completeRows
      ? totalDeeplineCredits === null
        ? null
        : totalDeeplineCredits / completeRows
      : null,
    p95DurationMs: unobservedDurationRows
      ? null
      : percentile95(observedDurations),
    unobservedCreditRows,
    unobservedDurationRows,
    adapterFailures: [
      ...new Set(input.rows.flatMap((row) => row.adapterFailures)),
    ],
    policyViolations: [
      ...new Set(input.rows.flatMap((row) => row.policyViolations)),
    ],
    eligible: false,
    exclusionReasons: [],
  };
}

function promotionExclusionReasons(
  score: CandidateScorecard,
  require: NonNullable<
    ResearchExperiment<UnknownRecord, unknown>['promotion']
  >['require'],
): string[] {
  const reasons: string[] = [];
  if (
    require?.minimumVerifiedRequiredClaimCoverage !== undefined &&
    score.verifiedRequiredClaimCoverage <
      require.minimumVerifiedRequiredClaimCoverage
  ) {
    reasons.push(
      `verified required-claim coverage ${score.verifiedRequiredClaimCoverage.toFixed(3)} is below ${require.minimumVerifiedRequiredClaimCoverage.toFixed(3)}`,
    );
  }
  if (
    require?.minimumCompleteRows !== undefined &&
    score.completeRows < require.minimumCompleteRows
  ) {
    reasons.push(
      `complete rows ${score.completeRows} is below ${require.minimumCompleteRows}`,
    );
  }
  if (require?.noAdapterFailures === true && score.adapterFailures.length) {
    reasons.push(`adapter failures: ${score.adapterFailures.join('; ')}`);
  }
  if (require?.noPolicyViolations === true && score.policyViolations.length) {
    reasons.push(`policy violations: ${score.policyViolations.join('; ')}`);
  }
  if (
    require?.noUnknownDeeplineCredits === true &&
    score.unobservedCreditRows
  ) {
    reasons.push(
      `Deepline credits were unobserved for ${score.unobservedCreditRows} pilot row(s)`,
    );
  }
  return reasons;
}

function stableResearchInputValue(
  value: unknown,
  ancestors: Set<object> = new Set(),
): string {
  if (value === null) return 'null';
  switch (typeof value) {
    case 'undefined':
      return 'undefined';
    case 'string':
      return `string:${JSON.stringify(value)}`;
    case 'boolean':
      return `boolean:${value}`;
    case 'number':
      return Number.isNaN(value)
        ? 'number:NaN'
        : value === Number.POSITIVE_INFINITY
          ? 'number:+Infinity'
          : value === Number.NEGATIVE_INFINITY
            ? 'number:-Infinity'
            : `number:${Object.is(value, -0) ? '-0' : value}`;
    case 'bigint':
      return `bigint:${value}`;
    case 'symbol':
    case 'function':
      throw new Error(
        'Research experiment required input cannot be snapshotted for pilot comparison.',
      );
    case 'object': {
      const object = value as object;
      if (ancestors.has(object)) {
        throw new Error(
          'Research experiment required input cannot be cyclic for pilot comparison.',
        );
      }
      ancestors.add(object);
      let snapshot: string;
      if (Array.isArray(value)) {
        snapshot = `array:[${value
          .map((item) => stableResearchInputValue(item, ancestors))
          .join(',')}]`;
      } else {
        const prototype = Object.getPrototypeOf(value);
        if (prototype !== Object.prototype && prototype !== null) {
          throw new Error(
            'Research experiment required input must be plain JSON data for pilot comparison.',
          );
        }
        snapshot = `object:{${Object.entries(value as Record<string, unknown>)
          .sort(([left], [right]) => left.localeCompare(right))
          .map(
            ([key, item]) =>
              `${JSON.stringify(key)}:${stableResearchInputValue(item, ancestors)}`,
          )
          .join(',')}}`;
      }
      ancestors.delete(object);
      return snapshot;
    }
  }
  throw new Error(
    'Research experiment required input cannot be snapshotted for pilot comparison.',
  );
}

function researchRequiredInputSnapshot<Row extends UnknownRecord>(
  row: Row,
  fields: readonly (keyof Row & string)[],
): string {
  return [...new Set(fields)]
    .sort()
    .map(
      (field) =>
        `${JSON.stringify(field)}:${stableResearchInputValue(row[field])}`,
    )
    .join('|');
}

const SCORECARD_FIELD_BY_METRIC: Record<
  PromotionMetric,
  keyof Pick<
    CandidateScorecard,
    | 'verifiedRequiredClaimCoverage'
    | 'completeRows'
    | 'independentEvidenceCoverage'
    | 'deeplineCreditsPerCompleteRow'
    | 'p95DurationMs'
  >
> = {
  verified_required_claim_coverage: 'verifiedRequiredClaimCoverage',
  complete_rows: 'completeRows',
  independent_evidence_coverage: 'independentEvidenceCoverage',
  deepline_credits_per_complete_row: 'deeplineCreditsPerCompleteRow',
  p95_duration_ms: 'p95DurationMs',
};

function compareScores(
  left: CandidateScorecard,
  right: CandidateScorecard,
  rank: readonly PromotionMetric[],
): number {
  for (const metric of rank) {
    const field = SCORECARD_FIELD_BY_METRIC[metric];
    const leftValue = left[field];
    const rightValue = right[field];
    const direction =
      metric === 'deepline_credits_per_complete_row' ||
      metric === 'p95_duration_ms'
        ? 1
        : -1;
    const a = leftValue === null ? Number.POSITIVE_INFINITY : leftValue;
    const b = rightValue === null ? Number.POSITIVE_INFINITY : rightValue;
    if (a !== b) return direction * (a - b);
  }
  return left.candidateId.localeCompare(right.candidateId);
}

export function compileResearchExperiment<Row extends UnknownRecord, Context>(
  definition: ResearchExperiment<Row, Context>,
) {
  const program = defineResearchExperiment(definition);
  const candidateById = new Map(
    program.candidates.map((candidate) => [candidate.id, candidate]),
  );

  function evaluateAttempt(
    attempt: ExperimentAttempt<Row>,
  ): CandidateRowEvaluation<Row> {
    if (!candidateById.has(attempt.candidateId)) {
      throw new Error(
        `Unknown research experiment candidate: ${attempt.candidateId}`,
      );
    }
    const rowKey = String(attempt.row[program.input.rowKey] ?? '');
    if (!rowKey)
      throw new Error(
        `Research experiment row is missing ${program.input.rowKey}.`,
      );
    const missingRequiredField = program.input.required.find(
      (field) => !hasValue(attempt.row[field]),
    );
    if (missingRequiredField) {
      throw new Error(
        `Research experiment row is missing required input field: ${missingRequiredField}.`,
      );
    }
    const claims = evaluateResearchClaimValues({
      row: attempt.row,
      definitions: program.claims,
      claims: attempt.outcome.claims,
    });
    const deeplineCredits = attempt.outcome.deeplineCredits;
    if (
      deeplineCredits !== undefined &&
      deeplineCredits !== null &&
      (!Number.isFinite(deeplineCredits) || deeplineCredits < 0)
    ) {
      throw new Error(
        `Research experiment candidate ${attempt.candidateId} returned an invalid Deepline credit observation.`,
      );
    }
    const durationMs = attempt.outcome.durationMs;
    if (
      durationMs !== undefined &&
      (!Number.isFinite(durationMs) || durationMs < 0)
    ) {
      throw new Error(
        `Research experiment candidate ${attempt.candidateId} returned an invalid duration observation.`,
      );
    }
    return {
      candidateId: attempt.candidateId,
      row: attempt.row,
      rowKey,
      claims,
      routeObservations: [...(attempt.outcome.routeObservations ?? [])],
      complete: claims
        .filter((claim) => claim.required)
        .every((claim) => claim.status === 'verified'),
      deeplineCredits: deeplineCredits ?? null,
      durationMs: durationMs ?? null,
      adapterFailures: [...(attempt.outcome.adapterFailures ?? [])],
      policyViolations: [...(attempt.outcome.policyViolations ?? [])],
    };
  }

  function evaluate(
    attempts: readonly ExperimentAttempt<Row>[],
  ): CandidateRowEvaluation<Row>[] {
    return attempts.map(evaluateAttempt);
  }

  function assertComparablePilot(
    evaluations: readonly CandidateRowEvaluation<Row>[],
  ): void {
    const rowKeysByCandidate = new Map<string, string[]>();
    for (const evaluation of evaluations) {
      const keys = rowKeysByCandidate.get(evaluation.candidateId) ?? [];
      keys.push(evaluation.rowKey);
      rowKeysByCandidate.set(evaluation.candidateId, keys);
    }
    const expectedCandidate = program.candidates[0]!;
    const expected = rowKeysByCandidate.get(expectedCandidate.id) ?? [];
    if (!expected.length) {
      throw new Error(
        `Pilot is missing all rows for candidate topology ${expectedCandidate.id}.`,
      );
    }
    const expectedSet = new Set(expected);
    if (expectedSet.size !== expected.length) {
      throw new Error(
        `Pilot has duplicate row keys for candidate topology ${expectedCandidate.id}.`,
      );
    }
    const expectedSnapshots = new Map(
      evaluations
        .filter((evaluation) => evaluation.candidateId === expectedCandidate.id)
        .map((evaluation) => [
          evaluation.rowKey,
          researchRequiredInputSnapshot(evaluation.row, program.input.required),
        ]),
    );
    for (const candidate of program.candidates) {
      const candidateRows = evaluations.filter(
        (evaluation) => evaluation.candidateId === candidate.id,
      );
      const rowKeys = candidateRows.map((evaluation) => evaluation.rowKey);
      const actualSet = new Set(rowKeys);
      if (actualSet.size !== rowKeys.length) {
        throw new Error(
          `Pilot has duplicate row keys for candidate topology ${candidate.id}.`,
        );
      }
      if (
        actualSet.size !== expectedSet.size ||
        [...expectedSet].some((rowKey) => !actualSet.has(rowKey))
      ) {
        throw new Error(
          `Pilot row keys must match for every topology; ${candidate.id} differs from ${expectedCandidate.id}.`,
        );
      }
      for (const evaluation of candidateRows) {
        const expectedSnapshot = expectedSnapshots.get(evaluation.rowKey);
        const actualSnapshot = researchRequiredInputSnapshot(
          evaluation.row,
          program.input.required,
        );
        if (expectedSnapshot !== actualSnapshot) {
          throw new Error(
            `Pilot required input snapshot must match for every topology; ${candidate.id} differs from ${expectedCandidate.id} on row ${evaluation.rowKey}.`,
          );
        }
      }
    }
  }

  function promote(attempts: readonly ExperimentAttempt<Row>[]): {
    evaluations: CandidateRowEvaluation<Row>[];
    promotion: PromotionArtifact;
  } {
    return promoteEvaluations(evaluate(attempts));
  }

  /**
   * Score evaluations materialized by a dataset. This does not re-run source
   * adapters, but it does reconstruct each claim value and pass it through the
   * current evidence and acceptance gates again. A sheet is a durable cache,
   * not authority to promote an old or altered verdict.
   */
  function revalidateMaterializedEvaluation(
    evaluation: CandidateRowEvaluation<Row>,
  ): CandidateRowEvaluation<Row> {
    const materialized = asRecord(evaluation);
    const candidateId = materialized.candidateId;
    if (typeof candidateId !== 'string' || !candidateById.has(candidateId)) {
      throw new Error(
        `Unknown research experiment candidate: ${String(candidateId)}`,
      );
    }
    const row = asRecord(materialized.row) as Row;
    const rowKey = String(row[program.input.rowKey] ?? '');
    if (!rowKey || materialized.rowKey !== rowKey) {
      throw new Error(
        'Materialized research evaluation has an invalid row key.',
      );
    }
    if (!Array.isArray(materialized.claims)) {
      throw new Error(
        'Materialized research evaluation is missing claim results.',
      );
    }
    if (materialized.claims.length !== program.claims.length) {
      throw new Error(
        'Materialized research evaluation claim set does not match the experiment contract.',
      );
    }
    const definitionsById = new Map(
      program.claims.map((definition) => [definition.id, definition]),
    );
    const seenClaimIds = new Set<string>();
    const claims: Record<string, ResearchClaimValue> = {};
    for (const rawClaim of materialized.claims) {
      const claim = asRecord(rawClaim);
      const claimId = claim.claimId;
      if (typeof claimId !== 'string') {
        throw new Error(
          'Materialized research evaluation claim set does not match the experiment contract.',
        );
      }
      const definition = definitionsById.get(claimId);
      if (!definition || seenClaimIds.has(claimId)) {
        throw new Error(
          'Materialized research evaluation claim set does not match the experiment contract.',
        );
      }
      seenClaimIds.add(claimId);
      if (
        typeof claim.required !== 'boolean' ||
        claim.required !== (definition.required !== false) ||
        typeof claim.reason !== 'string' ||
        !Array.isArray(claim.evidence) ||
        !claim.facts ||
        typeof claim.facts !== 'object' ||
        Array.isArray(claim.facts)
      ) {
        throw new Error(
          `Materialized research claim ${claimId} has an invalid shape.`,
        );
      }
      if (
        claim.status !== 'verified' &&
        claim.status !== 'abstained' &&
        claim.status !== 'insufficient_evidence' &&
        claim.status !== 'rejected'
      ) {
        throw new Error(
          `Materialized research claim ${claimId} has an invalid status.`,
        );
      }
      claims[claimId] = {
        ...(claim.value === undefined ? {} : { value: claim.value }),
        facts: claim.facts as Record<string, unknown>,
        evidence: claim.evidence as ResearchEvidence[],
        ...(claim.status === 'abstained'
          ? { abstainReason: claim.reason }
          : {}),
      };
    }
    if (seenClaimIds.size !== definitionsById.size) {
      throw new Error(
        'Materialized research evaluation claim set does not match the experiment contract.',
      );
    }
    if (
      !Array.isArray(materialized.routeObservations) ||
      !Array.isArray(materialized.adapterFailures) ||
      !materialized.adapterFailures.every(
        (failure) => typeof failure === 'string',
      ) ||
      !Array.isArray(materialized.policyViolations) ||
      !materialized.policyViolations.every(
        (violation) => typeof violation === 'string',
      )
    ) {
      throw new Error('Materialized research evaluation has an invalid shape.');
    }
    const deeplineCredits = materialized.deeplineCredits;
    if (
      deeplineCredits !== null &&
      deeplineCredits !== undefined &&
      (typeof deeplineCredits !== 'number' ||
        !Number.isFinite(deeplineCredits) ||
        deeplineCredits < 0)
    ) {
      throw new Error(
        'Materialized research evaluation has an invalid Deepline credit observation.',
      );
    }
    const durationMs = materialized.durationMs;
    if (
      durationMs !== null &&
      durationMs !== undefined &&
      (typeof durationMs !== 'number' ||
        !Number.isFinite(durationMs) ||
        durationMs < 0)
    ) {
      throw new Error(
        'Materialized research evaluation has an invalid duration observation.',
      );
    }
    return evaluateAttempt({
      row,
      candidateId,
      outcome: {
        claims,
        routeObservations:
          materialized.routeObservations as ResearchRouteObservation[],
        deeplineCredits: deeplineCredits ?? null,
        ...(durationMs === null || durationMs === undefined
          ? {}
          : { durationMs }),
        adapterFailures: materialized.adapterFailures as string[],
        policyViolations: materialized.policyViolations as string[],
      },
    });
  }

  function promoteEvaluations(
    evaluations: readonly CandidateRowEvaluation<Row>[],
  ): {
    evaluations: CandidateRowEvaluation<Row>[];
    promotion: PromotionArtifact;
  } {
    const revalidatedEvaluations = evaluations.map(
      revalidateMaterializedEvaluation,
    );
    assertComparablePilot(revalidatedEvaluations);
    const required = {
      ...DEFAULT_PROMOTION_REQUIREMENTS,
      ...program.promotion?.require,
    };
    const scorecard = program.candidates.map((candidate) => {
      const score = candidateScore({
        definition: program,
        candidate,
        rows: revalidatedEvaluations.filter(
          (row) => row.candidateId === candidate.id,
        ),
      });
      const exclusionReasons = promotionExclusionReasons(score, required);
      return {
        ...score,
        eligible: exclusionReasons.length === 0,
        exclusionReasons,
      };
    });
    const eligible = scorecard.filter((score) => score.eligible);
    const rank = program.promotion?.rank ?? DEFAULT_RANK;
    const selected = [...eligible].sort((left, right) =>
      compareScores(left, right, rank),
    )[0];
    const rankingRationale = rank
      .map((metric) => metric.replaceAll('_', ' '))
      .join(', then ');
    const reason = selected
      ? `Selected the eligible topology by applied ranking: ${rankingRationale}, after applying authored adapter, policy, and measurement gates.`
      : 'No topology met the authored promotion requirements; return the same-row pilot and explicit gaps.';
    return {
      evaluations: revalidatedEvaluations,
      promotion: {
        type: 'deepline.research_experiment_promotion',
        schemaVersion: 1,
        status: selected ? 'promoted' : 'not_promoted',
        selectedCandidateId: selected?.candidateId ?? null,
        scorecard,
        reason,
      },
    };
  }

  return {
    program,
    evaluateAttempt,
    evaluate,
    promote,
    promoteEvaluations,
  };
}
