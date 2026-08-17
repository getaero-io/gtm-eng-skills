import type { DeeplinePlayRuntimeContext } from 'deepline';
import {
  applyRerank,
  buildTaskRerankPrompt,
  ENTITY_RETRIEVAL_POLICY,
  fallbackRank,
  parseModelScores,
  RESEARCH_RERANK_POLICY,
  tokenOverlapRelevance,
  type RankableKind,
  type RerankItem,
  type RerankPolicy,
} from './rerank';

type UnknownRecord = Record<string, unknown>;

export type SourceOutcome =
  | 'ok'
  | 'no-results'
  | 'partial'
  | 'rate-limited'
  | 'auth-failed'
  | 'unreachable'
  | 'timeout'
  | 'schema-drift'
  | 'skipped'
  | 'error';

export type Evidence = {
  source: string;
  independenceClass: string;
  strength?: 'authoritative' | 'weak';
  url?: string;
  text?: string;
  phase?: 'broad' | 'supplemental';
  mechanismId?: string;
  mechanismClass?: string;
  providerStatus?: SourceOutcome;
};

export type FactAssertion = {
  value: string;
  evidence: Evidence[];
};

export type FactInput =
  | string
  | number
  | boolean
  | FactAssertion
  | Array<string | number | boolean | FactAssertion>;

export type RetrievedItemInput = {
  id: string;
  label?: string;
  title?: string;
  snippet?: string;
  url?: string;
  content?: string;
  author?: string;
  publishedAt?: string;
  facts?: Record<string, FactInput>;
  evidence?: Evidence[];
  attributes?: UnknownRecord;
  relevance?: number;
  freshness?: number;
  sourceQuality?: number;
  engagement?: number;
  entityMiss?: boolean;
};

export type RetrievedItem = Omit<RetrievedItemInput, 'facts'> & {
  label: string;
  facts: Record<string, FactAssertion[]>;
  evidence: Evidence[];
  routes: string[];
  routeRanks: Record<string, number>;
  rawRrf: number;
  rrf: number;
  judgeScore: number;
  judgeSource: 'model' | 'fallback';
  retrievalScore: number;
  verification: 'eligible' | 'rejected' | 'conflict';
  verificationReasons: string[];
};

/** @deprecated Use RetrievedItemInput. */
export type CandidateInput = RetrievedItemInput;
/** @deprecated Use RetrievedItem. */
export type Candidate = RetrievedItem;

export type FactGate =
  | { name: string; type: 'required'; fact: string }
  | {
      name: string;
      type: 'equals_row';
      fact: string;
      rowPath: string;
      match?: 'equals_normalized' | 'contains_normalized' | 'domain';
    }
  | {
      name: string;
      type: 'allowed_values';
      fact: string;
      allowedValues: string[];
      match?: 'equals_normalized' | 'contains_normalized' | 'domain';
    }
  | {
      name: string;
      type: 'evidence_policy';
      fact: string;
      allowAuthoritativeSingle?: boolean;
      minimumIndependentWeak?: number;
    };

export type ExperimentTask = {
  question: string;
  kind?: RankableKind;
  rowKey?: string;
  criteria?: string[];
  disqualifiers?: string[];
  primaryEntity?: (row: UnknownRecord) => string | undefined;
  gates?: FactGate[];
  minimumJudgeScore?: number;
  minimumPilotRows?: number;
  minimumRelevantRows?: number;
  portfolioSize?: number;
  /** What route selection should count as one covered unit. */
  selectionUnit?: 'item' | 'row';
  /** Require terminal fact gates to pass before a route earns coverage. */
  selectionRequiresEligibility?: boolean;
  /** Prefer maximum pilot coverage, then the cheapest portfolio. */
  optimizationObjective?: 'utility_per_credit' | 'coverage_then_cost';
  rerankPolicy?: RerankPolicy;
  research?: {
    referenceDate: string;
    freshnessMode?: 'strict_recent' | 'balanced_recent' | 'evergreen_ok';
    freshnessWindowDays?: number;
    minimumLocalRelevance?: number;
    maximumItemsPerAuthor?: number;
    minimumItemsPerRoute?: number;
  };
};

export type RouteContext<Row extends UnknownRecord> = {
  row: Row;
  rowCtx: DeeplinePlayRuntimeContext;
  limit: number;
};

export type RetrievalRoute<Row extends UnknownRecord> = {
  id: string;
  sourceFamilies: string[];
  queryFamily: string;
  mechanismId?: string;
  mechanismClass?: string;
  estimatedCreditsPerRow: number;
  weight?: number;
  maxItems?: number;
  /** @deprecated Use maxItems. */
  maxCandidates?: number;
  retrieve: (
    input: RouteContext<Row>,
  ) =>
    | Promise<readonly RetrievedItemInput[] | RouteAttempt>
    | readonly RetrievedItemInput[]
    | RouteAttempt;
};

export type RouteAttempt = {
  items?: readonly RetrievedItemInput[];
  /** @deprecated Use items. */
  candidates?: readonly RetrievedItemInput[];
  sourceOutcome?: 'ok' | 'no-results' | 'partial' | 'skipped';
  error?: string;
};

export type RouteResult = {
  route: string;
  phase?: 'broad' | 'supplemental';
  mechanismId?: string;
  mechanismClass?: string;
  outcome: 'retrieved' | 'empty' | 'excluded';
  sourceOutcome: SourceOutcome;
  items?: RetrievedItem[];
  /** @deprecated Use items. */
  candidates?: RetrievedItem[];
  error: string | null;
};

export type Judge<Row extends UnknownRecord> = (input: {
  row: Row;
  rowCtx: DeeplinePlayRuntimeContext;
  task: ExperimentTask;
  items: readonly RetrievedItem[];
  /** @deprecated Use items. */
  candidates: readonly RetrievedItem[];
  prompt: string;
}) => Promise<unknown>;

export type AiInferenceJudgeOptions = {
  model?: string;
  serviceTier?: 'flex' | 'priority';
  providerOptions?: Record<string, unknown>;
};

const AI_JUDGE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['scores'],
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'score', 'reason'],
        properties: {
          id: { type: 'string' },
          score: { type: 'number', minimum: 0, maximum: 100 },
          reason: { type: 'string' },
        },
      },
    },
  },
} as const;

/**
 * One bounded structured-output judge call over the fused shortlist. This is
 * the same deployment boundary as Last30Days: retrieval stays parallel and
 * deterministic, while one cheap model call supplies task-fit scores.
 */
export function createAiInferenceJudge<Row extends UnknownRecord>(
  options: AiInferenceJudgeOptions = {},
): Judge<Row> {
  return async ({ rowCtx, prompt }) =>
    rowCtx.tools.execute({
      id: 'route_experiment_judge',
      tool: 'ai_inference',
      input: {
        prompt,
        model: options.model ?? 'openai/gpt-5.6-luna',
        jsonSchema: JSON.stringify(AI_JUDGE_SCHEMA),
        ...(options.serviceTier ? { serviceTier: options.serviceTier } : {}),
        providerOptions: options.providerOptions ?? {
          openai: { reasoningEffort: 'low' },
        },
      },
      description:
        'Judge one fused route-experiment shortlist for task relevance.',
    });
}

export type SurvivorEnricher<Row extends UnknownRecord> = (input: {
  row: Row;
  rowCtx: DeeplinePlayRuntimeContext;
  items: readonly RetrievedItem[];
  /** @deprecated Use items. */
  candidates: readonly RetrievedItem[];
}) => Promise<readonly RetrievedItemInput[]>;

export type RouteScore = {
  route: string;
  attempted: number;
  evaluable: number;
  excluded: number;
  relevantTopK: number;
  uniqueItems: number;
  /** @deprecated Use uniqueItems. */
  uniqueCandidates: number;
  reliability: number;
  estimatedCreditsPerRow: number;
  retrievalUtilityPerCredit: number;
  relevantUnits: string[];
  unitScores: Record<string, number>;
};

export type RouteSelection = {
  type: 'deepline.route_selection';
  schemaVersion: 1;
  status: 'promoted' | 'not_promoted';
  selectedRouteIds: string[];
  estimatedCreditsPerRow: number;
  promotionEvidence: {
    pilotRows: number;
    relevantPilotRows: number;
    minimumPilotRows: number;
    minimumRelevantRows: number;
    scorecard: RouteScore[];
    selection: Array<{
      route: string;
      marginalRelevantItems: number;
      cumulativeRelevantItems: number;
      /** @deprecated Use marginalRelevantItems. */
      marginalRelevantCandidates: number;
      /** @deprecated Use cumulativeRelevantItems. */
      cumulativeRelevantCandidates: number;
      novelty: number;
      estimatedCreditsPerRow: number;
    }>;
    reason: string;
  };
};

export type RouteExperimentConfig<Row extends UnknownRecord> = {
  phase?: 'explore' | 'exploit';
  task: ExperimentTask;
  routes: readonly RetrievalRoute<Row>[];
  judge?: Judge<Row>;
  enrichSurvivors?: SurvivorEnricher<Row>;
  maximumCreditsPerRow?: number;
  globalPoolLimit?: number;
  rerankLimit?: number;
  enrichmentLimit?: number;
};

type ExperimentRow = UnknownRecord & {
  route_results?: RouteResult[];
  fused_items?: RetrievedItem[];
  ranked_items?: RetrievedItem[];
  selected_item?: RetrievedItem | null;
  enriched_items?: RetrievedItem[];
  /** @deprecated Compatibility with the first route-experiment draft. */
  fused_candidates?: RetrievedItem[];
  judge_result?: unknown;
  /** @deprecated Compatibility with the first route-experiment draft. */
  ranked_candidates?: RetrievedItem[];
  /** @deprecated Compatibility with the first route-experiment draft. */
  selected_candidate?: RetrievedItem | null;
  /** @deprecated Compatibility with the first route-experiment draft. */
  enriched_candidates?: RetrievedItem[];
};

function record(value: unknown): UnknownRecord {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as UnknownRecord)
    : {};
}

function clamp01(value: number | undefined, fallback = 0): number {
  return Number.isFinite(value)
    ? Math.max(0, Math.min(1, value as number))
    : fallback;
}

function text(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) return value.trim();
  if (typeof value === 'number' || typeof value === 'boolean')
    return String(value);
  return null;
}

export function getPath(value: unknown, path: string): unknown {
  if (path === '.') return value;
  return path
    .split('.')
    .reduce<unknown>((current, part) => record(current)[part], value);
}

export const canonicalId = {
  opaque(value: string): string {
    const id = value.trim();
    if (!id) throw new Error('retrieved item id must not be empty');
    return id;
  },
  url(value: string): string {
    const parsed = new URL(value);
    parsed.hash = '';
    for (const key of [...parsed.searchParams.keys()]) {
      if (
        key.toLowerCase().startsWith('utm_') ||
        ['ref', 'source', 'trk'].includes(key.toLowerCase())
      )
        parsed.searchParams.delete(key);
    }
    parsed.hostname = parsed.hostname.toLowerCase().replace(/^www\./, '');
    parsed.pathname = parsed.pathname.replace(/\/+$/, '') || '/';
    return parsed.toString();
  },
  domain(value: string): string {
    const parsed = new URL(value.includes('://') ? value : `https://${value}`);
    return parsed.hostname.toLowerCase().replace(/^www\./, '');
  },
};

function normalizeFacts(
  facts: Record<string, FactInput> | undefined,
  defaultEvidence: Evidence[],
): Record<string, FactAssertion[]> {
  return Object.fromEntries(
    Object.entries(facts ?? {}).flatMap(([name, raw]) => {
      const values = Array.isArray(raw) ? raw : [raw];
      const assertions = values.flatMap<FactAssertion>((entry) => {
        if (
          entry &&
          typeof entry === 'object' &&
          !Array.isArray(entry) &&
          typeof (entry as FactAssertion).value === 'string'
        ) {
          const assertion = entry as FactAssertion;
          return [
            {
              value: assertion.value.trim(),
              evidence: assertion.evidence ?? defaultEvidence,
            },
          ];
        }
        const value = text(entry);
        return value ? [{ value, evidence: defaultEvidence }] : [];
      });
      return assertions.length ? [[name, assertions]] : [];
    }),
  );
}

export function retrievedItem(input: RetrievedItemInput): RetrievedItem {
  const id = canonicalId.opaque(input.id);
  const facts = normalizeFacts(input.facts, input.evidence ?? []);
  const evidence = mergeEvidence(
    input.evidence ?? [],
    Object.values(facts).flatMap((assertions) =>
      assertions.flatMap((assertion) => assertion.evidence),
    ),
  );
  return {
    ...input,
    id,
    label: input.label?.trim() || input.title?.trim() || id,
    facts,
    evidence,
    routes: [],
    routeRanks: {},
    rawRrf: 0,
    rrf: 0,
    judgeScore: 0,
    judgeSource: 'fallback',
    retrievalScore: 0,
    verification: 'eligible',
    verificationReasons: [],
  };
}

export function freshnessFromPublishedAt(
  publishedAt: string | undefined,
  referenceDate: string,
  mode:
    | 'strict_recent'
    | 'balanced_recent'
    | 'evergreen_ok' = 'balanced_recent',
  windowDays = 30,
): number {
  if (!publishedAt)
    return mode === 'evergreen_ok' ? 0.4 : mode === 'balanced_recent' ? 0.1 : 0;
  const published = Date.parse(publishedAt);
  const reference = Date.parse(referenceDate);
  if (!Number.isFinite(published) || !Number.isFinite(reference))
    return mode === 'evergreen_ok' ? 0.4 : mode === 'balanced_recent' ? 0.1 : 0;
  const ageDays = Math.max(0, (reference - published) / 86_400_000);
  const strict = Math.max(0, 1 - ageDays / Math.max(1, windowDays));
  if (mode === 'strict_recent') return strict;
  if (mode === 'evergreen_ok') return strict * 0.6 + 0.4;
  return strict * 0.8 + 0.1;
}

export function normalizeEngagement(
  values: readonly (number | null | undefined)[],
): Array<number | undefined> {
  const logged = values.map((value) =>
    Number.isFinite(value) && Number(value) > 0
      ? Math.log1p(Number(value))
      : undefined,
  );
  const available = logged.filter(
    (value): value is number => value !== undefined,
  );
  if (!available.length) return logged;
  const low = Math.min(...available);
  const high = Math.max(...available);
  if (high === low)
    return logged.map((value) => (value === undefined ? undefined : 0.5));
  return logged.map((value) =>
    value === undefined ? undefined : (value - low) / (high - low),
  );
}

function researchText(item: RetrievedItem): string {
  return [
    item.label,
    item.title,
    item.snippet,
    item.content,
    ...item.evidence.map((entry) => entry.text),
  ]
    .filter(Boolean)
    .join(' ');
}

export function rankResearchStream(
  items: readonly RetrievedItem[],
  task: ExperimentTask,
  row: UnknownRecord,
): RetrievedItem[] {
  if (!task.research) return [...items];
  const query = [
    task.question,
    ...(task.criteria ?? []),
    task.primaryEntity?.(row),
  ]
    .filter(Boolean)
    .join(' ');
  const annotated = items.map((item) => {
    const relevance = clamp01(
      item.relevance,
      tokenOverlapRelevance(query, researchText(item)),
    );
    const freshness = clamp01(
      item.freshness,
      freshnessFromPublishedAt(
        item.publishedAt,
        task.research!.referenceDate,
        task.research!.freshnessMode,
        task.research!.freshnessWindowDays,
      ),
    );
    const engagement = clamp01(item.engagement, 0);
    return {
      ...item,
      relevance,
      freshness,
      sourceQuality: clamp01(item.sourceQuality, 0.6),
      engagement,
      attributes: {
        ...item.attributes,
        localRankScore: 0.65 * relevance + 0.25 * freshness + 0.1 * engagement,
      },
    };
  });
  const minimum = task.research.minimumLocalRelevance ?? 0.15;
  const pruned = annotated.filter((item) => (item.relevance ?? 0) >= minimum);
  return (pruned.length ? pruned : annotated).sort(
    (a, b) =>
      Number(b.attributes.localRankScore ?? 0) -
        Number(a.attributes.localRankScore ?? 0) || a.id.localeCompare(b.id),
  );
}

/** @deprecated Use retrievedItem. */
export const candidate = retrievedItem;

function mergeEvidence(left: Evidence[], right: Evidence[]): Evidence[] {
  const seen = new Set<string>();
  return [...left, ...right].filter((item) => {
    const key = JSON.stringify(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function mergeFacts(
  left: Record<string, FactAssertion[]>,
  right: Record<string, FactAssertion[]>,
): Record<string, FactAssertion[]> {
  const merged = structuredClone(left);
  for (const [name, assertions] of Object.entries(right)) {
    const values = merged[name] ?? [];
    for (const assertion of assertions) {
      const existing = values.find(
        (value) =>
          value.value.trim().toLowerCase() ===
          assertion.value.trim().toLowerCase(),
      );
      if (existing)
        existing.evidence = mergeEvidence(
          existing.evidence,
          assertion.evidence,
        );
      else values.push(structuredClone(assertion));
    }
    merged[name] = values;
  }
  return merged;
}

export function classifyError(error: unknown): SourceOutcome {
  const message = String(
    error instanceof Error ? error.message : error,
  ).toLowerCase();
  if (/422|validation failed|schema|invalid response|malformed/.test(message))
    return 'schema-drift';
  if (/401|403|auth|credential|permission|entitlement/.test(message))
    return 'auth-failed';
  if (/429|rate.?limit/.test(message)) return 'rate-limited';
  if (/timeout|timed out/.test(message)) return 'timeout';
  if (/network|unreachable|dns|connect/.test(message)) return 'unreachable';
  return 'error';
}

export async function mapBounded<T, U>(
  values: readonly T[],
  concurrency: number,
  fn: (value: T, index: number) => Promise<U>,
): Promise<U[]> {
  if (!Number.isInteger(concurrency) || concurrency < 1)
    throw new Error('mapBounded concurrency must be a positive integer');
  const output = new Array<U>(values.length);
  let cursor = 0;
  await Promise.all(
    Array.from({ length: Math.min(concurrency, values.length) }, async () => {
      while (cursor < values.length) {
        const index = cursor++;
        output[index] = await fn(values[index]!, index);
      }
    }),
  );
  return output;
}

export async function executeRoutes<Row extends UnknownRecord>(input: {
  row: Row;
  rowCtx: DeeplinePlayRuntimeContext;
  routes: readonly RetrievalRoute<Row>[];
  task?: ExperimentTask;
  phase?: 'broad' | 'supplemental';
}): Promise<RouteResult[]> {
  return Promise.all(
    input.routes.map(async (route) => {
      try {
        const rawAttempt = await route.retrieve({
          row: input.row,
          rowCtx: input.rowCtx,
          limit: route.maxItems ?? route.maxCandidates ?? 8,
        });
        const attempt: RouteAttempt = Array.isArray(rawAttempt)
          ? { items: rawAttempt as readonly RetrievedItemInput[] }
          : (rawAttempt as RouteAttempt);
        const drafts = attempt.items ?? attempt.candidates ?? [];
        let items = drafts.map(retrievedItem);
        if (input.task?.research)
          items = rankResearchStream(items, input.task, input.row);
        const sourceOutcome =
          attempt.sourceOutcome ?? (items.length ? 'ok' : 'no-results');
        const annotateEvidence = (evidence: Evidence): Evidence => ({
          ...evidence,
          phase: evidence.phase ?? input.phase,
          mechanismId: evidence.mechanismId ?? route.mechanismId ?? route.id,
          mechanismClass:
            evidence.mechanismClass ??
            route.mechanismClass ??
            route.sourceFamilies[0] ??
            route.id,
          providerStatus: evidence.providerStatus ?? sourceOutcome,
        });
        items = items
          .slice(0, route.maxItems ?? route.maxCandidates ?? 8)
          .map((item, index) => ({
            ...item,
            evidence: item.evidence.map(annotateEvidence),
            facts: Object.fromEntries(
              Object.entries(item.facts).map(([fact, assertions]) => [
                fact,
                assertions.map((assertion) => ({
                  ...assertion,
                  evidence: assertion.evidence.map(annotateEvidence),
                })),
              ]),
            ),
            routes: [route.id],
            routeRanks: { [route.id]: index + 1 },
          }));
        return {
          route: route.id,
          phase: input.phase,
          mechanismId: route.mechanismId ?? route.id,
          mechanismClass:
            route.mechanismClass ?? route.sourceFamilies[0] ?? route.id,
          outcome: items.length ? 'retrieved' : 'empty',
          sourceOutcome,
          items,
          candidates: items,
          error: attempt.error?.slice(0, 500) ?? null,
        } satisfies RouteResult;
      } catch (error) {
        return {
          route: route.id,
          phase: input.phase,
          mechanismId: route.mechanismId ?? route.id,
          mechanismClass:
            route.mechanismClass ?? route.sourceFamilies[0] ?? route.id,
          outcome: 'excluded',
          sourceOutcome: classifyError(error),
          items: [],
          candidates: [],
          error:
            error instanceof Error
              ? error.message.slice(0, 500)
              : String(error).slice(0, 500),
        } satisfies RouteResult;
      }
    }),
  );
}

export function weightedRrf(input: {
  results: readonly RouteResult[];
  routes: readonly Pick<RetrievalRoute<UnknownRecord>, 'id' | 'weight'>[];
  poolLimit?: number;
  normalization?: 'theoretical' | 'last30days';
  diversity?: {
    maximumItemsPerAuthor?: number;
    minimumItemsPerRoute?: number;
    minimumRouteRelevance?: number;
  };
}): RetrievedItem[] {
  const routeWeights = new Map(
    input.routes.map((route) => [route.id, route.weight ?? 1]),
  );
  const theoreticalMax = [...routeWeights.values()].reduce(
    (sum, weight) => sum + weight / 61,
    0,
  );
  const fused = new Map<string, RetrievedItem>();
  for (const result of input.results) {
    if (result.outcome === 'excluded') continue;
    const weight = routeWeights.get(result.route) ?? 1;
    (result.items ?? result.candidates ?? []).forEach((item, index) => {
      const rank = item.routeRanks[result.route] ?? index + 1;
      const contribution = weight / (60 + rank);
      const key = item.id;
      const prior = fused.get(key);
      if (!prior) {
        fused.set(key, {
          ...structuredClone(item),
          routes: [result.route],
          routeRanks: { [result.route]: rank },
          rawRrf: contribution,
        });
        return;
      }
      const alreadyContributed = prior.routeRanks[result.route] !== undefined;
      prior.routes = [...new Set([...prior.routes, result.route])];
      prior.routeRanks[result.route] = Math.min(
        prior.routeRanks[result.route] ?? rank,
        rank,
      );
      if (!alreadyContributed) prior.rawRrf += contribution;
      prior.evidence = mergeEvidence(prior.evidence, item.evidence);
      prior.facts = mergeFacts(prior.facts, item.facts);
      prior.attributes = { ...prior.attributes, ...item.attributes };
      if (item.relevance !== undefined)
        prior.relevance =
          prior.relevance === undefined
            ? item.relevance
            : Math.max(prior.relevance, item.relevance);
      if (item.freshness !== undefined)
        prior.freshness =
          prior.freshness === undefined
            ? item.freshness
            : Math.max(prior.freshness, item.freshness);
      if (item.sourceQuality !== undefined)
        prior.sourceQuality =
          prior.sourceQuality === undefined
            ? item.sourceQuality
            : Math.max(prior.sourceQuality, item.sourceQuality);
      if (item.engagement !== undefined)
        prior.engagement =
          prior.engagement === undefined
            ? item.engagement
            : Math.max(prior.engagement, item.engagement);
    });
  }
  const normalized = [...fused.values()]
    .map((item) => ({
      ...item,
      rrf:
        input.normalization === 'last30days'
          ? Math.max(0, Math.min(1, item.rawRrf / 0.08))
          : theoreticalMax
            ? Math.max(0, Math.min(1, item.rawRrf / theoreticalMax))
            : 0,
    }))
    .sort(
      (a, b) =>
        b.rawRrf - a.rawRrf ||
        Math.min(...Object.values(a.routeRanks)) -
          Math.min(...Object.values(b.routeRanks)) ||
        a.id.localeCompare(b.id),
    );
  const limit = input.poolLimit ?? 40;
  if (!input.diversity) return normalized.slice(0, limit);

  const maximumItemsPerAuthor = input.diversity.maximumItemsPerAuthor ?? 3;
  const minimumItemsPerRoute = input.diversity.minimumItemsPerRoute ?? 2;
  const minimumRouteRelevance = input.diversity.minimumRouteRelevance ?? 0.25;
  const reserved: RetrievedItem[] = [];
  const reservedIds = new Set<string>();
  for (const route of input.routes) {
    const routeItems = normalized.filter((item) =>
      item.routes.includes(route.id),
    );
    if (
      !routeItems.some((item) => (item.relevance ?? 0) >= minimumRouteRelevance)
    )
      continue;
    for (const item of routeItems.slice(0, minimumItemsPerRoute)) {
      if (!reservedIds.has(item.id)) {
        reserved.push(item);
        reservedIds.add(item.id);
      }
    }
  }
  const ordered = [
    ...reserved,
    ...normalized.filter((item) => !reservedIds.has(item.id)),
  ];
  const authorCounts = new Map<string, number>();
  const diversified = ordered.filter((item) => {
    const author = item.author?.trim().toLowerCase();
    if (!author) return true;
    const count = authorCounts.get(author) ?? 0;
    if (count >= maximumItemsPerAuthor) return false;
    authorCounts.set(author, count + 1);
    return true;
  });
  return diversified
    .slice(0, limit)
    .sort(
      (a, b) =>
        b.rawRrf - a.rawRrf ||
        Math.min(...Object.values(a.routeRanks)) -
          Math.min(...Object.values(b.routeRanks)) ||
        a.id.localeCompare(b.id),
    );
}

function normalized(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function comparable(
  value: string,
  mode: 'equals_normalized' | 'contains_normalized' | 'domain' | undefined,
): string {
  return mode === 'domain' ? canonicalId.domain(value) : normalized(value);
}

function matches(
  actual: string,
  expected: string,
  mode: 'equals_normalized' | 'contains_normalized' | 'domain' | undefined,
): boolean {
  const left = comparable(actual, mode);
  const right = comparable(expected, mode);
  return mode === 'contains_normalized' ? left.includes(right) : left === right;
}

function evaluateGate(
  item: RetrievedItem,
  row: UnknownRecord,
  gate: FactGate,
): { passed: boolean; conflict: boolean; reason: string } {
  const assertions = item.facts[gate.fact] ?? [];
  if (gate.type === 'required') {
    const passed = assertions.some((assertion) => assertion.evidence.length);
    return {
      passed,
      conflict: false,
      reason: passed ? gate.name : `${gate.name}:missing`,
    };
  }
  if (gate.type === 'evidence_policy') {
    const normalizedValues = new Set(
      assertions.map((assertion) => normalized(assertion.value)),
    );
    if (normalizedValues.size > 1)
      return {
        passed: false,
        conflict: true,
        reason: `${gate.name}:conflicting_values`,
      };
    const evidence = assertions.flatMap((assertion) => assertion.evidence);
    const authoritative =
      (gate.allowAuthoritativeSingle ?? true) &&
      evidence.some((entry) => entry.strength === 'authoritative');
    const weakClasses = new Set(
      evidence
        .filter((entry) => entry.strength !== 'authoritative')
        .map((entry) => entry.independenceClass),
    );
    const required = gate.minimumIndependentWeak ?? 2;
    const passed = authoritative || weakClasses.size >= required;
    return {
      passed,
      conflict: false,
      reason: passed
        ? gate.name
        : `${gate.name}:needs_authoritative_or_${required}_independent_weak`,
    };
  }
  const expected =
    gate.type === 'equals_row'
      ? [text(getPath(row, gate.rowPath))].filter((entry): entry is string =>
          Boolean(entry),
        )
      : gate.allowedValues;
  const accepted = assertions.filter((assertion) =>
    expected.some((value) => matches(assertion.value, value, gate.match)),
  );
  const rejected = assertions.filter(
    (assertion) =>
      !expected.some((value) => matches(assertion.value, value, gate.match)),
  );
  return {
    passed: accepted.length > 0 && rejected.length === 0,
    conflict: accepted.length > 0 && rejected.length > 0,
    reason:
      accepted.length > 0 && rejected.length === 0
        ? gate.name
        : `${gate.name}:${accepted.length ? 'conflicting_values' : 'no_match'}`,
  };
}

export function applyFactGates(
  items: readonly RetrievedItem[],
  task: ExperimentTask,
  row: UnknownRecord,
): RetrievedItem[] {
  return items.map((item) => {
    const results = (task.gates ?? []).map((gate) =>
      evaluateGate(item, row, gate),
    );
    const conflict = results.some((result) => result.conflict);
    const eligible = results.every((result) => result.passed);
    return {
      ...item,
      verification: conflict
        ? ('conflict' as const)
        : eligible
          ? ('eligible' as const)
          : ('rejected' as const),
      verificationReasons: results
        .filter((result) => !result.passed)
        .map((result) => result.reason),
    };
  });
}

function corroboration(item: RetrievedItem): number {
  return Math.min(
    1,
    new Set(item.evidence.map((entry) => entry.independenceClass)).size / 3,
  );
}

function unwrapJudgeResult(raw: unknown): unknown {
  const envelope = record(raw);
  const responseRaw = record(record(envelope.toolResponse).raw);
  const outputRaw = record(record(envelope.toolOutput).raw);
  const toolRaw = Object.keys(outputRaw).length ? outputRaw : responseRaw;
  const result = record(toolRaw.result);
  return (
    toolRaw.extracted_json ??
    toolRaw.object ??
    result.extracted_json ??
    result.object ??
    result.output ??
    (Object.keys(toolRaw).length ? toolRaw : raw)
  );
}

export function buildJudgePrompt(
  task: ExperimentTask,
  items: readonly RetrievedItem[],
  row: UnknownRecord = {},
): string {
  return buildTaskRerankPrompt(
    {
      kind: task.kind,
      question: task.question,
      criteria: task.criteria,
      disqualifiers: task.disqualifiers,
      primaryEntity: task.primaryEntity?.(row),
      policy: task.rerankPolicy,
    },
    items.map((item) => toRerankItem(item, task, row)),
  );
}

function taskRelevanceText(
  item: RetrievedItem,
  task: ExperimentTask,
  row: UnknownRecord,
): {
  query: string;
  itemText: string;
  primaryEntity?: string;
} {
  const primaryEntity = task.primaryEntity?.(row);
  const query = [task.question, ...(task.criteria ?? []), primaryEntity]
    .filter(Boolean)
    .join(' ');
  const facts = Object.values(item.facts)
    .flat()
    .map((assertion) => assertion.value);
  const itemText = [
    item.label,
    item.title,
    item.snippet,
    item.content,
    ...facts,
  ]
    .filter(Boolean)
    .join(' ');
  return { query, itemText, primaryEntity };
}

function toRerankItem(
  item: RetrievedItem,
  task: ExperimentTask,
  row: UnknownRecord,
): RerankItem {
  const local = taskRelevanceText(item, task, row);
  return {
    id: item.id,
    kind: undefined,
    label: item.label,
    title: item.title,
    snippet: item.snippet,
    url: item.url,
    content: item.content,
    attributes: item.attributes,
    evidence: item.evidence,
    relevance: clamp01(
      item.relevance,
      tokenOverlapRelevance(local.query, local.itemText),
    ),
    rrf: item.rrf,
    freshness: clamp01(item.freshness, 0.5),
    sourceQuality: clamp01(item.sourceQuality, 0.6),
    engagement: clamp01(item.engagement, 0),
    verification:
      item.verification === 'eligible'
        ? 1
        : item.verification === 'conflict'
          ? 0
          : 0.25,
    corroboration: corroboration(item),
    entityMiss:
      item.entityMiss ??
      (local.primaryEntity
        ? tokenOverlapRelevance(local.primaryEntity, local.itemText) === 0
        : false),
  };
}

export function rerankItems(input: {
  items: readonly RetrievedItem[];
  task: ExperimentTask;
  row: UnknownRecord;
  judgeResult?: unknown;
}): RetrievedItem[] {
  const gated = applyFactGates(input.items, input.task, input.row);
  const items = gated.map((item) => toRerankItem(item, input.task, input.row));
  const scores =
    input.judgeResult === undefined
      ? new Map<string, number>()
      : parseModelScores(unwrapJudgeResult(input.judgeResult));
  const policy =
    input.task.rerankPolicy ??
    (input.task.kind === 'source'
      ? RESEARCH_RERANK_POLICY
      : ENTITY_RETRIEVAL_POLICY);
  const ranked =
    scores.size > 0
      ? applyRerank(items, scores, policy)
      : fallbackRank(items, policy);
  const byId = new Map(gated.map((item) => [item.id, item]));
  return ranked.map((result) => {
    const original = byId.get(result.id)!;
    return {
      ...original,
      judgeScore: result.rerankScore * 100,
      judgeSource: scores.has(result.id)
        ? ('model' as const)
        : ('fallback' as const),
      retrievalScore: result.finalScore * 100,
    };
  });
}

/** @deprecated Use rerankItems. */
export function rerankCandidates(input: {
  candidates: readonly RetrievedItem[];
  task: ExperimentTask;
  row: UnknownRecord;
  judgeResult?: unknown;
}): RetrievedItem[] {
  return rerankItems({
    items: input.candidates,
    task: input.task,
    row: input.row,
    judgeResult: input.judgeResult,
  });
}

export function scoreRoutes<Row extends UnknownRecord>(
  rows: readonly ExperimentRow[],
  routes: readonly RetrievalRoute<Row>[],
  task: ExperimentTask,
): RouteScore[] {
  const minimum = task.minimumJudgeScore ?? 50;
  const unitId = (rowIndex: number, itemId: string) =>
    task.selectionUnit === 'row'
      ? String(rowIndex)
      : `${rowIndex}\u0000${itemId}`;
  const relevantByUnit = new Map<string, Set<string>>();
  rows.forEach((row, rowIndex) => {
    const relevant = new Set(
      (row.ranked_items ?? row.ranked_candidates ?? [])
        .filter((item) => item.judgeScore >= minimum)
        .map((item) => item.id),
    );
    for (const result of row.route_results ?? []) {
      if (result.outcome === 'excluded') continue;
      const locallyEligible = new Set(
        applyFactGates(result.items ?? result.candidates ?? [], task, row)
          .filter((item) => item.verification === 'eligible')
          .map((item) => item.id),
      );
      for (const item of result.items ?? result.candidates ?? []) {
        if (
          !relevant.has(item.id) ||
          (task.selectionRequiresEligibility && !locallyEligible.has(item.id))
        )
          continue;
        const unit = unitId(rowIndex, item.id);
        const owners = relevantByUnit.get(unit) ?? new Set<string>();
        owners.add(result.route);
        relevantByUnit.set(unit, owners);
      }
    }
  });
  return routes.map((route) => {
    const results = rows.flatMap((row, rowIndex) =>
      (row.route_results ?? [])
        .filter((result) => result.route === route.id)
        .map((result) => ({ result, row, rowIndex })),
    );
    const excluded = results.filter(
      ({ result }) => result.outcome === 'excluded',
    ).length;
    const relevantUnits = new Set<string>();
    const unitScores: Record<string, number> = {};
    let unique = 0;
    for (const { result, row, rowIndex } of results) {
      if (result.outcome === 'excluded') continue;
      const ranked = new Map(
        (row.ranked_items ?? row.ranked_candidates ?? [])
          .filter((item) => item.judgeScore >= minimum)
          .map((item) => [item.id, item]),
      );
      const locallyEligible = new Set(
        applyFactGates(result.items ?? result.candidates ?? [], task, row)
          .filter((item) => item.verification === 'eligible')
          .map((item) => item.id),
      );
      for (const item of result.items ?? result.candidates ?? []) {
        const fused = ranked.get(item.id);
        if (
          !fused ||
          (task.selectionRequiresEligibility && !locallyEligible.has(item.id))
        )
          continue;
        const unit = unitId(rowIndex, item.id);
        const firstContribution = !relevantUnits.has(unit);
        relevantUnits.add(unit);
        unitScores[unit] = Math.max(
          unitScores[unit] ?? 0,
          fused.retrievalScore / 100,
        );
        if (firstContribution && relevantByUnit.get(unit)?.size === 1) {
          unique += 1;
        }
      }
    }
    const evaluable = results.length - excluded;
    const reliability = results.length
      ? results.reduce(
          (sum, { result }) =>
            sum +
            (result.outcome === 'excluded'
              ? 0
              : result.sourceOutcome === 'partial'
                ? 0.5
                : 1),
          0,
        ) / results.length
      : 0;
    const utility =
      Object.values(unitScores).reduce((sum, value) => sum + value, 0) +
      unique * 0.75;
    return {
      route: route.id,
      attempted: results.length,
      evaluable,
      excluded,
      relevantTopK: relevantUnits.size,
      uniqueItems: unique,
      uniqueCandidates: unique,
      reliability,
      estimatedCreditsPerRow: route.estimatedCreditsPerRow,
      retrievalUtilityPerCredit:
        route.estimatedCreditsPerRow > 0
          ? (utility * reliability) / route.estimatedCreditsPerRow
          : utility * reliability,
      relevantUnits: [...relevantUnits].sort(),
      unitScores,
    };
  });
}

type PortfolioChoice<Row extends UnknownRecord> = {
  routes: RetrievalRoute<Row>[];
  covered: Map<string, number>;
  score: number;
  reliability: number;
  credits: number;
};

function compareCoveragePortfolios<Row extends UnknownRecord>(
  left: PortfolioChoice<Row>,
  right: PortfolioChoice<Row>,
): number {
  return (
    left.covered.size - right.covered.size ||
    right.credits - left.credits ||
    right.routes.length - left.routes.length ||
    left.score - right.score ||
    left.reliability - right.reliability ||
    right.routes
      .map((route) => route.id)
      .join('|')
      .localeCompare(left.routes.map((route) => route.id).join('|'))
  );
}

/** Exact small-portfolio search for the common 2-8 route experiment. */
function coverageFirstPortfolio<Row extends UnknownRecord>(input: {
  routes: readonly RetrievalRoute<Row>[];
  scorecard: readonly RouteScore[];
  cap: number;
  maximumCreditsPerRow?: number;
}): PortfolioChoice<Row> | null {
  if (input.routes.length > 12)
    throw new Error(
      'coverage_then_cost supports at most 12 candidate routes; prune the hypothesis set first.',
    );
  const scores = new Map(input.scorecard.map((score) => [score.route, score]));
  let best: PortfolioChoice<Row> | null = null;
  const combinations = 1 << input.routes.length;
  for (let mask = 1; mask < combinations; mask += 1) {
    const routes = input.routes.filter((_, index) => (mask & (1 << index)) > 0);
    if (routes.length > input.cap) continue;
    const credits = routes.reduce(
      (sum, route) => sum + route.estimatedCreditsPerRow,
      0,
    );
    if (
      input.maximumCreditsPerRow !== undefined &&
      credits > input.maximumCreditsPerRow
    )
      continue;
    const covered = new Map<string, number>();
    for (const route of routes) {
      const score = scores.get(route.id)!;
      for (const unit of score.relevantUnits)
        covered.set(
          unit,
          Math.max(covered.get(unit) ?? 0, score.unitScores[unit] ?? 0),
        );
    }
    if (!covered.size) continue;
    const choice: PortfolioChoice<Row> = {
      routes,
      covered,
      score: [...covered.values()].reduce((sum, value) => sum + value, 0),
      reliability:
        routes.reduce(
          (sum, route) => sum + scores.get(route.id)!.reliability,
          0,
        ) / routes.length,
      credits,
    };
    if (!best || compareCoveragePortfolios(choice, best) > 0) best = choice;
  }
  return best;
}

function orderSelectedRoutes<Row extends UnknownRecord>(input: {
  routes: readonly RetrievalRoute<Row>[];
  scorecard: readonly RouteScore[];
}): RouteSelection['promotionEvidence']['selection'] {
  const scores = new Map(input.scorecard.map((score) => [score.route, score]));
  const remaining = new Set(input.routes.map((route) => route.id));
  const covered = new Map<string, number>();
  const selected: RetrievalRoute<Row>[] = [];
  const ordered: RouteSelection['promotionEvidence']['selection'] = [];
  while (remaining.size) {
    const choices = [...remaining]
      .map((id) => {
        const route = input.routes.find((entry) => entry.id === id)!;
        const score = scores.get(id)!;
        const marginal = score.relevantUnits.filter(
          (unit) => !covered.has(unit),
        );
        const improvements = score.relevantUnits.filter(
          (unit) => score.unitScores[unit]! > (covered.get(unit) ?? 0),
        );
        const gain = improvements.reduce(
          (sum, unit) =>
            sum +
            Math.max(0, score.unitScores[unit]! - (covered.get(unit) ?? 0)),
          0,
        );
        return {
          route,
          score,
          marginal,
          improvements,
          gain,
          novelty: routeNovelty(route, selected),
          efficiency:
            marginal.length / Math.max(route.estimatedCreditsPerRow, 0.0001),
        };
      })
      .sort(
        (a, b) =>
          b.efficiency - a.efficiency ||
          b.marginal.length - a.marginal.length ||
          b.gain - a.gain ||
          a.route.estimatedCreditsPerRow - b.route.estimatedCreditsPerRow ||
          a.route.id.localeCompare(b.route.id),
      );
    const next = choices[0]!;
    remaining.delete(next.route.id);
    selected.push(next.route);
    for (const unit of next.score.relevantUnits)
      covered.set(
        unit,
        Math.max(covered.get(unit) ?? 0, next.score.unitScores[unit]!),
      );
    ordered.push({
      route: next.route.id,
      marginalRelevantItems: next.marginal.length,
      cumulativeRelevantItems: covered.size,
      marginalRelevantCandidates: next.marginal.length,
      cumulativeRelevantCandidates: covered.size,
      novelty: next.novelty,
      estimatedCreditsPerRow: next.route.estimatedCreditsPerRow,
    });
  }
  return ordered;
}

function routeNovelty<Row extends UnknownRecord>(
  route: RetrievalRoute<Row>,
  selected: readonly RetrievalRoute<Row>[],
): number {
  if (!selected.length) return 1;
  const tags = new Set([
    ...route.sourceFamilies.map((value) => `source:${value}`),
    `query:${route.queryFamily}`,
  ]);
  return Math.min(
    ...selected.map((prior) => {
      const priorTags = new Set([
        ...prior.sourceFamilies.map((value) => `source:${value}`),
        `query:${prior.queryFamily}`,
      ]);
      const intersection = [...tags].filter((tag) => priorTags.has(tag)).length;
      const union = new Set([...tags, ...priorTags]).size;
      return union ? 1 - intersection / union : 0;
    }),
  );
}

export function selectRoutes<Row extends UnknownRecord>(input: {
  rows: readonly ExperimentRow[];
  routes: readonly RetrievalRoute<Row>[];
  task: ExperimentTask;
  maximumCreditsPerRow?: number;
}): RouteSelection {
  const scorecard = scoreRoutes(input.rows, input.routes, input.task);
  const minimumPilotRows = input.task.minimumPilotRows ?? 3;
  const minimumRelevantRows = input.task.minimumRelevantRows ?? 2;
  const cap = input.task.portfolioSize ?? Math.min(3, input.routes.length);
  if (input.task.optimizationObjective === 'coverage_then_cost') {
    const portfolio = coverageFirstPortfolio({
      routes: input.routes,
      scorecard,
      cap,
      maximumCreditsPerRow: input.maximumCreditsPerRow,
    });
    const ordered = portfolio
      ? orderSelectedRoutes({ routes: portfolio.routes, scorecard })
      : [];
    const relevantPilotRows = portfolio
      ? new Set(
          [...portfolio.covered.keys()].map((unit) =>
            input.task.selectionUnit === 'row'
              ? unit
              : unit.split('\u0000', 1)[0],
          ),
        ).size
      : 0;
    const promoted =
      input.rows.length >= minimumPilotRows &&
      relevantPilotRows >= minimumRelevantRows &&
      Boolean(portfolio);
    return {
      type: 'deepline.route_selection',
      schemaVersion: 1,
      status: promoted ? 'promoted' : 'not_promoted',
      selectedRouteIds: promoted ? ordered.map((entry) => entry.route) : [],
      estimatedCreditsPerRow: promoted ? portfolio!.credits : 0,
      promotionEvidence: {
        pilotRows: input.rows.length,
        relevantPilotRows,
        minimumPilotRows,
        minimumRelevantRows,
        scorecard,
        selection: promoted ? ordered : [],
        reason: promoted
          ? 'Selected the maximum-coverage eligible portfolio under the credit cap, then preferred lower cost, simpler topology, stronger evidence, and reliability.'
          : `Promotion needs ${minimumPilotRows} pilot rows and relevant items on ${minimumRelevantRows} rows.`,
      },
    };
  }
  const remaining = new Set(input.routes.map((route) => route.id));
  const covered = new Map<string, number>();
  const selected: RetrievalRoute<Row>[] = [];
  const selection: RouteSelection['promotionEvidence']['selection'] = [];
  let credits = 0;
  while (remaining.size && selected.length < cap) {
    const choices = [...remaining]
      .map((id) => {
        const route = input.routes.find((entry) => entry.id === id)!;
        const score = scorecard.find((entry) => entry.route === id)!;
        const marginal = score.relevantUnits.filter(
          (unit) => score.unitScores[unit]! > (covered.get(unit) ?? 0),
        );
        const gain = marginal.reduce(
          (sum, unit) =>
            sum +
            Math.max(0, score.unitScores[unit]! - (covered.get(unit) ?? 0)),
          0,
        );
        const novelty = routeNovelty(route, selected);
        return {
          route,
          score,
          marginal,
          novelty,
          utility:
            (gain * score.reliability) /
              Math.max(route.estimatedCreditsPerRow, 0.0001) +
            novelty * 0.15,
        };
      })
      .filter(
        ({ route, marginal }) =>
          marginal.length > 0 &&
          (input.maximumCreditsPerRow === undefined ||
            credits + route.estimatedCreditsPerRow <=
              input.maximumCreditsPerRow),
      )
      .sort(
        (a, b) =>
          b.utility - a.utility ||
          b.marginal.length - a.marginal.length ||
          b.novelty - a.novelty ||
          a.route.estimatedCreditsPerRow - b.route.estimatedCreditsPerRow ||
          a.route.id.localeCompare(b.route.id),
      );
    const next = choices[0];
    if (!next) break;
    remaining.delete(next.route.id);
    selected.push(next.route);
    credits += next.route.estimatedCreditsPerRow;
    for (const unit of next.marginal)
      covered.set(
        unit,
        Math.max(covered.get(unit) ?? 0, next.score.unitScores[unit]!),
      );
    selection.push({
      route: next.route.id,
      marginalRelevantItems: next.marginal.length,
      cumulativeRelevantItems: covered.size,
      marginalRelevantCandidates: next.marginal.length,
      cumulativeRelevantCandidates: covered.size,
      novelty: next.novelty,
      estimatedCreditsPerRow: next.route.estimatedCreditsPerRow,
    });
  }
  const relevantPilotRows = new Set(
    [...covered.keys()].map((unit) => unit.split('\u0000', 1)[0]),
  ).size;
  const promoted =
    input.rows.length >= minimumPilotRows &&
    relevantPilotRows >= minimumRelevantRows &&
    selected.length > 0;
  return {
    type: 'deepline.route_selection',
    schemaVersion: 1,
    status: promoted ? 'promoted' : 'not_promoted',
    selectedRouteIds: promoted ? selected.map((route) => route.id) : [],
    estimatedCreditsPerRow: promoted ? credits : 0,
    promotionEvidence: {
      pilotRows: input.rows.length,
      relevantPilotRows,
      minimumPilotRows,
      minimumRelevantRows,
      scorecard,
      selection,
      reason: promoted
        ? 'Selected the complementary route portfolio with the best marginal relevant-item utility, novelty, reliability, and credit fit.'
        : `Promotion needs ${minimumPilotRows} pilot rows and relevant items on ${minimumRelevantRows} rows.`,
    },
  };
}

export function bindSelection<Row extends UnknownRecord>(
  routes: readonly RetrievalRoute<Row>[],
  selection: RouteSelection,
  maximumCreditsPerRow?: number,
): RetrievalRoute<Row>[] {
  if (
    selection.type !== 'deepline.route_selection' ||
    selection.schemaVersion !== 1 ||
    selection.status !== 'promoted'
  )
    throw new Error('A promoted route selection is required.');
  const unique = new Set(selection.selectedRouteIds);
  if (unique.size !== selection.selectedRouteIds.length || unique.size === 0)
    throw new Error('Selected route ids must be nonempty and unique.');
  const bound = selection.selectedRouteIds.map((id) => {
    const route = routes.find((entry) => entry.id === id);
    if (!route)
      throw new Error(`Selected route is not defined by this Play: ${id}`);
    return route;
  });
  const credits = bound.reduce(
    (sum, route) => sum + route.estimatedCreditsPerRow,
    0,
  );
  if (maximumCreditsPerRow !== undefined && credits > maximumCreditsPerRow)
    throw new Error('Selected routes exceed maximumCreditsPerRow.');
  return bound;
}

export function validateExperiment<Row extends UnknownRecord>(
  config: RouteExperimentConfig<Row>,
): void {
  if (!config.task.question.trim())
    throw new Error('A route experiment needs a task question.');
  if (
    config.task.minimumJudgeScore !== undefined &&
    (!Number.isFinite(config.task.minimumJudgeScore) ||
      config.task.minimumJudgeScore < 0 ||
      config.task.minimumJudgeScore > 100)
  )
    throw new Error('minimumJudgeScore must be between 0 and 100.');
  for (const [name, value] of Object.entries({
    minimumPilotRows: config.task.minimumPilotRows,
    minimumRelevantRows: config.task.minimumRelevantRows,
    portfolioSize: config.task.portfolioSize,
    globalPoolLimit: config.globalPoolLimit,
    rerankLimit: config.rerankLimit,
    enrichmentLimit: config.enrichmentLimit,
  })) {
    if (value !== undefined && (!Number.isInteger(value) || value < 1))
      throw new Error(`${name} must be a positive integer.`);
  }
  if (
    config.maximumCreditsPerRow !== undefined &&
    (!Number.isFinite(config.maximumCreditsPerRow) ||
      config.maximumCreditsPerRow < 0)
  )
    throw new Error('maximumCreditsPerRow must be finite and non-negative.');
  if (
    config.task.optimizationObjective === 'coverage_then_cost' &&
    config.routes.length > 12
  )
    throw new Error(
      'coverage_then_cost supports at most 12 candidate routes; prune the hypothesis set first.',
    );
  if (config.routes.length < (config.phase === 'exploit' ? 1 : 2))
    throw new Error(
      config.phase === 'exploit'
        ? 'EXPLOIT needs at least one selected route.'
        : 'EXPLORE needs at least two materially different routes.',
    );
  const ids = new Set<string>();
  let credits = 0;
  for (const route of config.routes) {
    if (!route.id || ids.has(route.id))
      throw new Error(`Route ids must be nonempty and unique: ${route.id}`);
    ids.add(route.id);
    if (!route.sourceFamilies.length || !route.queryFamily.trim())
      throw new Error(`${route.id} needs sourceFamilies and queryFamily.`);
    if (
      !Number.isFinite(route.estimatedCreditsPerRow) ||
      route.estimatedCreditsPerRow < 0
    )
      throw new Error(
        `${route.id}.estimatedCreditsPerRow must be finite and non-negative.`,
      );
    if (
      route.weight !== undefined &&
      (!Number.isFinite(route.weight) || route.weight <= 0)
    )
      throw new Error(`${route.id}.weight must be finite and positive.`);
    const maxItems = route.maxItems ?? route.maxCandidates;
    if (maxItems !== undefined && (!Number.isInteger(maxItems) || maxItems < 1))
      throw new Error(`${route.id}.maxItems must be a positive integer.`);
    credits += route.estimatedCreditsPerRow;
  }
  if (
    config.maximumCreditsPerRow !== undefined &&
    credits > config.maximumCreditsPerRow
  )
    throw new Error('EXPLORE route estimates exceed maximumCreditsPerRow.');
}

export function createRouteExperiment<Row extends UnknownRecord>(
  config: RouteExperimentConfig<Row>,
) {
  validateExperiment(config);
  const fusedItems = (row: ExperimentRow) =>
    weightedRrf({
      results: row.route_results ?? [],
      routes: config.routes,
      poolLimit: config.globalPoolLimit,
      normalization: config.task.research ? 'last30days' : 'theoretical',
      diversity: config.task.research
        ? {
            maximumItemsPerAuthor: config.task.research.maximumItemsPerAuthor,
            minimumItemsPerRoute: config.task.research.minimumItemsPerRoute,
          }
        : undefined,
    });
  const rankedItems = (row: ExperimentRow & Row) =>
    rerankItems({
      items: row.fused_items ?? row.fused_candidates ?? [],
      task: config.task,
      row,
      judgeResult: row.judge_result ?? undefined,
    });
  const enrichedItems = async (
    row: ExperimentRow & Row,
    rowCtx: DeeplinePlayRuntimeContext,
  ) => {
    const ranked = row.ranked_items ?? row.ranked_candidates ?? [];
    if (!config.enrichSurvivors) return ranked;
    const shortlist = ranked.slice(0, config.enrichmentLimit ?? 5);
    const enriched = await config.enrichSurvivors({
      row,
      rowCtx,
      items: shortlist,
      candidates: shortlist,
    });
    const updates = new Map(
      enriched.map((draft) => {
        const normalized = retrievedItem(draft);
        return [normalized.id, { draft, normalized }] as const;
      }),
    );
    return ranked.map((item) => {
      const update = updates.get(item.id);
      return update
        ? {
            ...item,
            ...(update.draft.label ? { label: update.normalized.label } : {}),
            title: update.draft.title ?? item.title,
            snippet: update.draft.snippet ?? item.snippet,
            url: update.draft.url ?? item.url,
            content: update.draft.content ?? item.content,
            author: update.draft.author ?? item.author,
            publishedAt: update.draft.publishedAt ?? item.publishedAt,
            attributes: {
              ...item.attributes,
              ...update.normalized.attributes,
            },
            facts: mergeFacts(item.facts, update.normalized.facts),
            evidence: mergeEvidence(item.evidence, update.normalized.evidence),
          }
        : item;
    });
  };
  const finalRankedItems = (
    row: ExperimentRow &
      Row & {
        enriched_items?: RetrievedItem[];
        enriched_candidates?: RetrievedItem[];
      },
  ) =>
    rerankItems({
      items:
        row.enriched_items ??
        row.enriched_candidates ??
        row.ranked_items ??
        row.ranked_candidates ??
        [],
      task: config.task,
      row,
      judgeResult: row.judge_result ?? undefined,
    }).filter((item) => !config.task.gates || item.verification === 'eligible');
  const selectedItem = (
    row: ExperimentRow &
      Row & {
        enriched_items?: RetrievedItem[];
        enriched_candidates?: RetrievedItem[];
      },
  ) => finalRankedItems(row)[0] ?? null;
  const selectedItems = (
    row: ExperimentRow &
      Row & {
        enriched_items?: RetrievedItem[];
        enriched_candidates?: RetrievedItem[];
      },
  ) => finalRankedItems(row);
  return {
    routeResults: (row: Row, rowCtx: DeeplinePlayRuntimeContext) =>
      executeRoutes({ row, rowCtx, routes: config.routes, task: config.task }),
    fusedItems,
    judgeResult: async (
      row: ExperimentRow & Row,
      rowCtx: DeeplinePlayRuntimeContext,
    ) => {
      const shortlist = (row.fused_items ?? row.fused_candidates ?? []).slice(
        0,
        config.rerankLimit ?? 40,
      );
      if (!config.judge || shortlist.length === 0) return null;
      return config.judge({
        row,
        rowCtx,
        task: config.task,
        items: shortlist,
        candidates: shortlist,
        prompt: buildJudgePrompt(config.task, shortlist, row),
      });
    },
    rankedItems,
    enrichedItems,
    selectedItem,
    selectedItems,
    /** @deprecated Use fusedItems. */
    fusedCandidates: fusedItems,
    /** @deprecated Use rankedItems. */
    rankedCandidates: rankedItems,
    /** @deprecated Use enrichedItems. */
    enrichedCandidates: enrichedItems,
    /** @deprecated Use selectedItem. */
    selectedCandidate: selectedItem,
    /** @deprecated Use selectedItems. */
    selectedCandidates: selectedItems,
    rowKey: (row: Row, index: number) =>
      String(
        (config.task.rowKey ? getPath(row, config.task.rowKey) : undefined) ??
          record(row).id ??
          index,
      ),
  };
}
