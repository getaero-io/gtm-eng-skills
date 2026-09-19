/** Pure replay scorer. No providers, default weights, or claims of validation. */
export function artifactKey(value: unknown): string {
  // Exact-content key; no runtime-specific crypto dependency or hash collisions.
  // Production adapters may replace this with a supported cryptographic content hash.
  return JSON.stringify(value);
}
export type Dimension =
  | 'account_fit'
  | 'account_engagement'
  | 'lead_fit'
  | 'lead_engagement';
export type Observation = {
  entity_id: string;
  feature: string;
  value: number | null;
  dimension: Dimension;
  source_class: 'external' | 'first_party_event' | 'ae';
  source_id: string;
  known_at: string;
  event_at: string;
  retrieved_at: string;
  status: 'observed' | 'missing' | 'error';
};
export type Model = {
  id: string;
  dimension: Dimension;
  intercept: number;
  weights: Record<string, number>;
  max_age_days: Record<string, number>;
  event_window_days?: number;
  validation: 'exploratory' | 'validated';
};
export type Reference = {
  id: string;
  model_id: string;
  dimension: Dimension;
  scores: number[];
  population: string;
  frozen_at: string;
};

function instant(value: string): number {
  if (typeof value !== 'string' || !/(Z|[+-]\d\d:\d\d)$/.test(value))
    throw new Error('timezone_required');
  const parts =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,3})?(Z|[+-]\d{2}:\d{2})$/.exec(
      value,
    );
  if (!parts) throw new Error('invalid_timestamp');
  const [, year, month, day, hour, minute, second, zone] = parts;
  const days = new Date(Date.UTC(Number(year), Number(month), 0)).getUTCDate();
  if (
    +year < 100 ||
    +month < 1 ||
    +month > 12 ||
    +day < 1 ||
    +day > days ||
    +hour > 23 ||
    +minute > 59 ||
    +second > 59 ||
    (zone !== 'Z' && (+zone.slice(1, 3) > 23 || +zone.slice(4, 6) > 59))
  )
    throw new Error('invalid_timestamp');
  const n = Date.parse(value);
  if (!Number.isFinite(n)) throw new Error('invalid_timestamp');
  return n;
}
export function gradePercentile(percentile: number): 'A' | 'B' | 'C' | 'D' {
  if (!Number.isFinite(percentile) || percentile < 0 || percentile > 100)
    throw new Error('invalid_percentile');
  return percentile >= 90
    ? 'A'
    : percentile >= 75
      ? 'B'
      : percentile >= 50
        ? 'C'
        : 'D';
}
export function gradeScore(score: number | null, reference: Reference) {
  if (!reference.id || !reference.model_id || !reference.population)
    throw new Error('invalid_reference');
  instant(reference.frozen_at);
  if (
    !reference.scores.length ||
    reference.scores.some((x) => !Number.isFinite(x))
  )
    throw new Error('invalid_reference_scores');
  if (score === null)
    return { percentile: null, grade: null, reason: 'unscored' };
  if (!Number.isFinite(score)) throw new Error('invalid_score');
  if (new Set(reference.scores).size < 2)
    return {
      percentile: null,
      grade: null,
      reason: 'insufficient_reference_variation',
    };
  const less = reference.scores.filter((x) => x < score).length;
  const equal = reference.scores.filter((x) => x === score).length;
  const percentile = (100 * (less + equal / 2)) / reference.scores.length;
  return { percentile, grade: gradePercentile(percentile), reason: null };
}
export function scoreRow(
  entityId: string,
  scoredAt: string,
  observations: Observation[],
  model: Model,
  reference: Reference,
) {
  const cutoff = instant(scoredAt);
  if (!['exploratory', 'validated'].includes(model.validation))
    throw new Error('invalid_validation');
  if (
    !entityId ||
    !model.id ||
    ![
      'account_fit',
      'account_engagement',
      'lead_fit',
      'lead_engagement',
    ].includes(model.dimension)
  )
    throw new Error('invalid_model_or_entity');
  if (
    reference.model_id !== model.id ||
    reference.dimension !== model.dimension
  )
    throw new Error('reference_model_mismatch');
  if (instant(reference.frozen_at) > cutoff)
    throw new Error('reference_not_frozen_at_scoring');
  if (
    !Number.isFinite(model.intercept) ||
    !Object.keys(model.weights).length ||
    Object.values(model.weights).some((x) => !Number.isFinite(x))
  )
    throw new Error('invalid_weights');
  const fit = model.dimension.endsWith('_fit');
  if (
    !fit &&
    (!Number.isFinite(model.event_window_days) || model.event_window_days! <= 0)
  )
    throw new Error('engagement_window_required');
  const reasons: string[] = [],
    evidence: Observation[] = [],
    enriched: Record<string, number> = {};
  let raw = model.intercept;
  for (const [feature, weight] of Object.entries(model.weights)) {
    const age = model.max_age_days[feature];
    if (!Number.isFinite(age) || age < 0)
      throw new Error('feature_freshness_required');
    const matching = observations.filter(
      (o) =>
        o.feature === feature &&
        o.entity_id === entityId &&
        o.dimension === model.dimension,
    );
    const rejected = new Set<string>();
    const reject = (reason: string) => {
      rejected.add(reason);
      return false;
    };
    const eligible = matching.filter((o) => {
      if (
        o.status !== 'observed' ||
        o.value === null ||
        !Number.isFinite(o.value) ||
        !o.source_id
      )
        return reject(
          o.status === 'error' ? 'provider_error' : 'missing_value_or_source',
        );
      if (o.source_class !== (fit ? 'external' : 'first_party_event'))
        return reject(
          o.source_class === 'ae' ? 'ae_source_excluded' : 'wrong_source_class',
        );
      try {
        const known = instant(o.known_at),
          event = instant(o.event_at),
          retrieved = instant(o.retrieved_at);
        if (known >= cutoff || event >= cutoff || retrieved >= cutoff)
          return reject('not_available_before_cutoff');
        if (event > known || known > retrieved)
          return reject('invalid_chronology');
        if (
          cutoff - event >
          Math.min(age, fit ? age : model.event_window_days!) * 86400000
        )
          return reject('stale_event');
        return true;
      } catch {
        return reject('invalid_timestamp');
      }
    });
    // Explicitly require upstream source conflict resolution; don't pick whichever scores best.
    if (eligible.length !== 1) {
      reasons.push(
        `${feature}:${eligible.length ? 'ambiguous_observation' : [...rejected].sort().join(',') || 'no_matching_observation'}`,
      );
      continue;
    }
    const o = eligible[0];
    enriched[feature] = o.value!;
    raw += weight * o.value!;
    evidence.push(o);
  }
  const score = reasons.length ? null : raw;
  if (score !== null && !Number.isFinite(score))
    throw new Error('score_overflow');
  const graded = gradeScore(score, reference);
  return {
    entity_id: entityId,
    scored_at: scoredAt,
    dimension: model.dimension,
    enriched,
    score,
    ...graded,
    model_id: model.id,
    reference_id: reference.id,
    model_key: artifactKey(model),
    reference_key: artifactKey(reference),
    reference_n: reference.scores.length,
    tie_policy: 'exact_numeric_midrank',
    coverage: evidence.length / Object.keys(model.weights).length,
    confidence: null,
    out_of_reference_range:
      score === null
        ? null
        : reference.scores.every((x) => x > score) ||
          reference.scores.every((x) => x < score),
    validation: model.validation,
    status:
      score === null
        ? 'needs_evidence'
        : graded.grade === null
          ? 'needs_reference'
          : 'scored',
    miss_reason: reasons.length ? reasons.join(';') : graded.reason,
    evidence,
  };
}
