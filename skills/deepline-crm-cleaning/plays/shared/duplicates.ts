/** Offline contact-identity proposals. A proposal never authorizes a CRM merge. */
import {
  canonicalJson,
  sha256,
  pythonCasefold,
  sequenceMatcherRatio,
} from './json';
import { compareCodepoints as compare_codepoints } from './json';
import type { JsonObject } from './json';
type Row = JsonObject;
export const VERSION = 'crm-contact-duplicate-resolver.v4';
export const HASH_PROTOCOL = 'crm-json-js-v1';
export const MAX_RECORDS = 5000;
const MIN_FUZZY_LENGTH = 3;
const FEATURES = new Set(['first_name', 'surname', 'email', 'dob', 'city']);
const object = (v: unknown): v is Row =>
  v !== null && typeof v === 'object' && !Array.isArray(v);
const PREVIOUS_POLICY_ASSUMPTIONS: Row = {
  calibration_basis:
    'Provisional heuristics exercised on synthetic person records; no deployment calibration.',
  normalization:
    'Unicode NFKC, case folding, and alphanumeric name components; no transliteration.',
  unequal_fuzzy_min_characters: 3,
  equal_nonempty_short_names_match: true,
  unequal_short_names:
    'Score zero; two observed name components can produce a conflict hold. Validate for each locale.',
  default_shared_mailbox_language:
    'English; review and extend shared_email_locals for the deployment locale.',
  without_dob_and_city:
    'Only exact-email with a corroborating name, or very-similar-email with two compatible names, can match.',
  dob_conflict_tolerance:
    'Both dates must be valid. Distances above near_dob_max_days hold the pair and its proposed cluster.',
  deprecated_thresholds: {
    strong_names_similarity:
      'Accepted and validated for legacy configuration compatibility; no effect on decisions.',
    partial_dob_min_components:
      'Accepted and validated for legacy configuration compatibility; no effect on decisions.',
  },
  rule_field_requirements: {
    exact_email_with_corroboration: ['email', 'one name component or dob'],
    exact_dob_with_corroboration: [
      'dob',
      'one name component',
      'email or city',
    ],
    email_near_dob_city: ['email', 'dob', 'city'],
    names_exact_dob: ['first_name', 'surname', 'dob'],
    names_near_dob_city: ['first_name', 'surname', 'dob', 'city'],
    names_similar_email: ['first_name', 'surname', 'email'],
  },
};
export const POLICY_ASSUMPTIONS: Row = {
  ...PREVIOUS_POLICY_ASSUMPTIONS,
  similarity_scoring:
    'Use the lower of both directional sequence-matcher ratios for decision features. Record IDs and input order do not affect decisions.',
};
export const LEGACY_POLICY_ASSUMPTIONS: Row = {
  calibration_basis:
    'Provisional heuristics exercised on synthetic person records; no deployment calibration.',
  normalization:
    'Unicode NFKC, case folding, and alphanumeric name components; no transliteration.',
  unequal_fuzzy_min_characters: 3,
  equal_nonempty_short_names_match: true,
  unequal_short_names:
    'Score zero; two observed name components can produce a conflict hold. Validate for each locale.',
  default_shared_mailbox_language:
    'English; review and extend shared_email_locals for the deployment locale.',
  without_dob_and_city:
    'Only exact-email with a corroborating name, or very-similar-email with two compatible names, can match.',
  dob_conflict_tolerance:
    'Both dates must be valid. Distances above near_dob_max_days hold the pair and its proposed cluster.',
  rule_field_requirements: {
    exact_email_with_corroboration: ['email', 'one name component or dob'],
    exact_dob_with_corroboration: [
      'dob',
      'one name component',
      'email or city',
    ],
    email_near_dob_city: ['email', 'dob', 'city'],
    names_exact_dob: ['first_name', 'surname', 'dob'],
    names_near_dob_city: ['first_name', 'surname', 'dob', 'city'],
    names_similar_email: ['first_name', 'surname', 'email'],
    names_partial_dob_city: ['first_name', 'surname', 'dob', 'city'],
  },
};
export const DEFAULT_POLICY: Row = {
  name: 'provisional-contact-v1',
  thresholds: {
    candidate_email_similarity: 0.78,
    candidate_name_similarity: 0.8,
    name_conflict_below: 0.6,
    corroborating_name_similarity: 0.86,
    corroborating_email_similarity: 0.8,
    email_local_similarity: 0.8,
    city_similarity: 0.85,
    compatible_names_similarity: 0.8,
    strong_names_similarity: 0.9,
    very_similar_email: 0.92,
    distinct_names_below: 0.5,
    near_dob_max_days: 400,
    partial_dob_min_components: 2,
  },
  shared_email_locals: [
    'accounts',
    'admin',
    'billing',
    'contact',
    'hello',
    'info',
    'no-reply',
    'noreply',
    'office',
    'sales',
    'support',
    'team',
  ],
};
export function resolve_policy(overrides: Row | null = null): Row {
  overrides ??= {};
  if (
    !object(overrides) ||
    Object.keys(overrides).some(
      (k) =>
        !['name', 'thresholds', 'shared_email_locals', 'assumptions'].includes(
          k,
        ),
    )
  )
    throw new Error(
      'Policy accepts only name, thresholds, shared_email_locals, and fixed assumptions',
    );
  if (
    'assumptions' in overrides &&
    ![
      POLICY_ASSUMPTIONS,
      PREVIOUS_POLICY_ASSUMPTIONS,
      LEGACY_POLICY_ASSUMPTIONS,
    ].some((a) => canonicalJson(a) === canonicalJson(overrides.assumptions))
  )
    throw new Error(
      'Policy assumptions describe fixed implementation behavior and cannot be overridden',
    );
  const policyName = Object.hasOwn(overrides, 'name')
    ? overrides.name
    : DEFAULT_POLICY.name;
  if (typeof policyName !== 'string' || !policyName.trim())
    throw new Error('Policy name must be a nonempty string');
  const supplied = Object.hasOwn(overrides, 'thresholds')
    ? overrides.thresholds
    : {};
  if (
    !object(supplied) ||
    Object.keys(supplied).some((k) => !(k in DEFAULT_POLICY.thresholds))
  )
    throw new Error('Unknown or invalid policy thresholds');
  const thresholds = { ...DEFAULT_POLICY.thresholds, ...supplied };
  for (const [key, value] of Object.entries(thresholds)) {
    if (['near_dob_max_days', 'partial_dob_min_components'].includes(key)) {
      if (
        typeof value !== 'number' ||
        !Number.isSafeInteger(value) ||
        value < (key === 'near_dob_max_days' ? 0 : 1) ||
        (key === 'partial_dob_min_components' && value > 3)
      )
        throw new Error(`Invalid integer policy threshold: ${key}`);
    } else if (
      typeof value !== 'number' ||
      !Number.isFinite(value) ||
      value <= 0 ||
      value > 1
    )
      throw new Error(
        `Policy similarity threshold must be finite and in (0, 1]: ${key}`,
      );
  }
  for (const [lower, upper] of [
    ['name_conflict_below', 'compatible_names_similarity'],
    ['distinct_names_below', 'name_conflict_below'],
    ['corroborating_email_similarity', 'very_similar_email'],
  ])
    if (thresholds[lower] > thresholds[upper])
      throw new Error(`Policy requires ${lower} <= ${upper}`);
  const locals = Object.hasOwn(overrides, 'shared_email_locals')
    ? overrides.shared_email_locals
    : DEFAULT_POLICY.shared_email_locals;
  if (
    !Array.isArray(locals) ||
    locals.some(
      (v) => typeof v !== 'string' || !v || v !== v.trim() || /[@\s]/u.test(v),
    )
  )
    throw new Error(
      'shared_email_locals must be a list of nonempty mailbox local parts',
    );
  return {
    name: policyName.trim(),
    thresholds,
    shared_email_locals: [...new Set(locals.map(pythonCasefold))].sort(
      compare_codepoints,
    ),
    assumptions: structuredClone(POLICY_ASSUMPTIONS),
  };
}
export function text(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value !== 'string')
    throw new Error('Contact field values must be strings or null');
  return value.normalize('NFKC').trim();
}
export function name(value: unknown): string {
  return [...pythonCasefold(text(value))]
    .filter((c) => /[\p{L}\p{N}]/u.test(c))
    .join('');
}
export function email(value: unknown): string {
  const v = text(value),
    parts = v.split('@');
  return parts.length !== 2 ||
    /\s/u.test(v) ||
    !parts[0] ||
    !parts[1] ||
    !parts[1].includes('.')
    ? ''
    : `${parts[0]}@${pythonCasefold(parts[1])}`;
}
export function similarity(left: string, right: string): number {
  if (!left || !right) return 0;
  if (left === right) return 1;
  if (Math.min([...left].length, [...right].length) < MIN_FUZZY_LENGTH)
    return 0;
  return sequenceMatcherRatio(left, right);
}
function decision_similarity(left: string, right: string): number {
  return Math.min(similarity(left, right), similarity(right, left));
}
function date(value: string): string {
  if (/^\d{8}$/.test(value))
    value = value.slice(0, 4) + '-' + value.slice(4, 6) + '-' + value.slice(6);
  const week = /^(\d{4})-?W(\d{2})(?:-?([1-7]))?$/.exec(value);
  if (week && +week[1] > 0 && +week[2] >= 1 && +week[2] <= 53) {
    const jan4 = Date.parse(week[1] + '-01-04T00:00:00Z'),
      day = (new Date(jan4).getUTCDay() + 6) % 7;
    const result = new Date(
      jan4 -
        day * 86400000 +
        ((+week[2] - 1) * 7 + +(week[3] ?? '1') - 1) * 86400000,
    );
    const thursday = new Date(
      result.getTime() + (3 - ((result.getUTCDay() + 6) % 7)) * 86400000,
    );
    return thursday.getUTCFullYear() === +week[1]
      ? result.toISOString().slice(0, 10)
      : '';
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || +value.slice(0, 4) === 0) return '';
  const ms = Date.parse(value + 'T00:00:00Z');
  return Number.isFinite(ms) &&
    new Date(ms).toISOString().slice(0, 10) === value
    ? value
    : '';
}
export function normalize(row: Row): Row {
  if (!object(row) || row.object_type !== 'contact')
    throw new Error(
      'This resolver accepts person/contact records only, not companies',
    );
  if (typeof row.id !== 'string' || !row.id)
    throw new Error('Nonempty string record id required');
  if (
    !object(row.source) ||
    ['system', 'scope_id'].some(
      (k) => typeof row.source[k] !== 'string' || !row.source[k].trim(),
    )
  )
    throw new Error('Explicit source system and scope_id required');
  if (
    !object(row.fields) ||
    Object.keys(row.fields).some((k) => !FEATURES.has(k))
  )
    throw new Error(
      'Unexpected fields; do not pass gold labels or CRM metadata as identity features',
    );
  return {
    first_name: name(row.fields.first_name),
    surname: name(row.fields.surname),
    city: name(row.fields.city),
    email: email(row.fields.email),
    dob: date(text(row.fields.dob)),
    id: row.id,
    scope: [row.source.system, row.source.scope_id],
  };
}
export function evidence(
  left: Row,
  right: Row,
  policy = resolve_policy(),
): Row {
  const limits = policy.thresholds;
  const direct = [
    decision_similarity(left.first_name, right.first_name),
    decision_similarity(left.surname, right.surname),
  ];
  const swapped = [
    decision_similarity(left.first_name, right.surname),
    decision_similarity(left.surname, right.first_name),
  ];
  const best =
    Math.min(...swapped) > Math.min(...direct) ||
    (Math.min(...swapped) === Math.min(...direct) &&
      swapped[0] + swapped[1] > direct[0] + direct[1])
      ? swapped
      : direct;
  const [first, last] = best,
    one = Math.max(...direct, ...swapped),
    both = Math.min(first, last);
  const full = !!(
    left.first_name &&
    left.surname &&
    right.first_name &&
    right.surname
  );
  const exactEmail = !!left.email && left.email === right.email;
  const shared = [left, right].some(
    (r) =>
      r.email &&
      policy.shared_email_locals.includes(
        pythonCasefold(r.email.split('@')[0]),
      ),
  );
  const emailSimilarity = decision_similarity(left.email, right.email),
    exactDob = !!left.dob && left.dob === right.dob;
  const days =
    left.dob && right.dob
      ? Math.abs(Date.parse(left.dob) - Date.parse(right.dob)) / 86400000
      : null;
  return {
    first_name_similarity: first,
    surname_similarity: last,
    one_name_similarity: one,
    both_names_similarity: both,
    full_names_observed: full,
    full_names_comparable:
      full &&
      [left, right].every((r) =>
        ['first_name', 'surname'].every(
          (k) => [...r[k]].length >= MIN_FUZZY_LENGTH,
        ),
      ),
    observed_name_conflict: full && both < limits.name_conflict_below,
    email_exact: exactEmail,
    shared_email: shared,
    different_observed_emails: !!(left.email && right.email && !exactEmail),
    email_similarity: emailSimilarity,
    email_local_similarity: decision_similarity(
      left.email.split('@')[0],
      right.email.split('@')[0],
    ),
    dob_exact: exactDob,
    dob_equal_components:
      left.dob && right.dob
        ? left.dob
            .split('-')
            .filter((p: string, i: number) => p === right.dob.split('-')[i])
            .length
        : 0,
    observed_dob_conflict: days !== null && days > limits.near_dob_max_days,
    city_exact: !!left.city && left.city === right.city,
    city_similarity: decision_similarity(left.city, right.city),
    dob_days_apart: days,
    candidate:
      exactEmail ||
      emailSimilarity >= limits.candidate_email_similarity ||
      exactDob ||
      one >= limits.candidate_name_similarity,
  };
}
export function decide(ev: Row, policy = resolve_policy()): [string, string[]] {
  const l = policy.thresholds;
  if (ev.observed_dob_conflict)
    return ['unresolved', ['incompatible_observed_birth_dates']];
  if (ev.observed_name_conflict) {
    if (
      ev.full_names_comparable &&
      ev.one_name_similarity < l.distinct_names_below &&
      ev.different_observed_emails &&
      !ev.shared_email &&
      !ev.dob_exact
    )
      return ['distinct', ['incompatible_names_and_different_observed_emails']];
    return ['unresolved', ['incompatible_observed_name_components']];
  }
  const city = ev.city_similarity >= l.city_similarity,
    names = ev.both_names_similarity >= l.compatible_names_similarity;
  const nearDob =
      ev.dob_days_apart !== null && ev.dob_days_apart <= l.near_dob_max_days,
    local = ev.email_local_similarity >= l.email_local_similarity;
  if (
    ev.email_exact &&
    !ev.shared_email &&
    (ev.one_name_similarity >= l.corroborating_name_similarity || ev.dob_exact)
  )
    return ['duplicate', ['exact_non_role_email', 'corroborating_name_or_dob']];
  if (
    ev.dob_exact &&
    ev.one_name_similarity >= l.corroborating_name_similarity &&
    ((ev.email_similarity >= l.corroborating_email_similarity &&
      local &&
      !ev.shared_email) ||
      city)
  )
    return [
      'duplicate',
      ['exact_dob', 'compatible_name_component', 'corroborating_email_or_city'],
    ];
  if (ev.email_exact && !ev.shared_email && city && nearDob)
    return [
      'duplicate',
      ['exact_non_role_email', 'near_dob', 'compatible_city'],
    ];
  if (ev.full_names_observed && names && ev.dob_exact)
    return ['duplicate', ['two_compatible_name_components', 'exact_dob']];
  if (ev.full_names_observed && names && city && nearDob)
    return [
      'duplicate',
      ['two_compatible_name_components', 'near_dob', 'compatible_city'],
    ];
  if (
    ev.full_names_observed &&
    names &&
    ev.email_similarity >= l.very_similar_email &&
    local &&
    !ev.shared_email
  )
    return [
      'duplicate',
      ['two_compatible_name_components', 'very_similar_email'],
    ];
  return ['unresolved', ['insufficient_independent_identity_evidence']];
}
function compareClusters(a: string[], b: string[]): number {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const c = compare_codepoints(a[i], b[i]);
    if (c) return c;
  }
  return a.length - b.length;
}
function* pairsOf<T>(rows: T[]): Generator<[T, T]> {
  for (let a = 0; a < rows.length; a++)
    for (let b = a + 1; b < rows.length; b++) yield [rows[a], rows[b]];
}
export function resolve_records_stream(
  rows: Row[],
  suppliedPolicy: Row | null = null,
): Row & { pairs: Iterable<Row>; pair_count: number } {
  if (!Array.isArray(rows) || rows.length > MAX_RECORDS)
    throw new Error(
      `Local quadratic policy supports at most ${MAX_RECORDS} records; explicitly design blocking for larger cohorts`,
    );
  const policy = resolve_policy(suppliedPolicy),
    records = rows
      .map(normalize)
      .sort((a, b) => compare_codepoints(a.id, b.id));
  const byId = new Map<string, Row>(records.map((r) => [r.id, r]));
  if (byId.size !== records.length)
    throw new Error('Repeated ids: use one explicit scoped cohort');
  if (new Set(records.map((r) => canonicalJson(r.scope))).size > 1)
    throw new Error('Mixed source scopes; run each tenant independently');
  const pairs = new Map<string, Row>(),
    key = (a: string, b: string) => canonicalJson([a, b]);
  const components = new Map<string, Set<string>>(
    records.map((r) => [r.id, new Set([r.id])]),
  );
  for (let a = 0; a < records.length; a++)
    for (let b = a + 1; b < records.length; b++) {
      const left = records[a],
        right = records[b],
        ev = evidence(left, right, policy);
      if (ev.candidate) {
        const [decision, reasons] = decide(ev, policy);
        pairs.set(key(left.id, right.id), {
          left_id: left.id,
          right_id: right.id,
          candidate: true,
          decision,
          reasons,
        });
      }
    }
  for (const pair of pairs.values())
    if (pair.decision === 'duplicate') {
      const left = components.get(pair.left_id)!,
        right = components.get(pair.right_id)!;
      if (left === right) continue;
      const union = new Set([...left, ...right]);
      for (const rid of union) components.set(rid, union);
    }
  const clusters: string[][] = [],
    clusterMap = new Map<string, string[]>();
  for (const group of new Set(components.values()))
    if (group.size > 1) {
      const cluster = [...group].sort(compare_codepoints);
      clusterMap.set(canonicalJson(cluster), cluster);
    }
  for (const cluster of [...clusterMap.values()].sort(compareClusters)) {
    let conflict = false;
    for (const [a, b] of pairsOf(cluster)) {
      const ev = evidence(byId.get(a)!, byId.get(b)!, policy);
      if (
        ev.observed_name_conflict ||
        ev.observed_dob_conflict ||
        decide(ev, policy)[0] === 'distinct'
      ) {
        conflict = true;
        break;
      }
    }
    if (conflict) {
      for (const [a, b] of pairsOf(cluster)) {
        const pair = pairs.get(key(a, b));
        if (pair?.decision === 'duplicate')
          Object.assign(pair, {
            decision: 'unresolved',
            reasons: ['cluster_cannot_link_conflict'],
          });
      }
    } else clusters.push(cluster);
  }
  for (const cluster of clusters)
    for (const [a, b] of pairsOf(cluster)) {
      const old = pairs.get(key(a, b));
      if (!old)
        pairs.set(key(a, b), {
          left_id: a,
          right_id: b,
          candidate: false,
          decision: 'duplicate',
          reasons: ['transitive_supported_cluster'],
        });
      else if (old.decision !== 'duplicate')
        Object.assign(old, {
          decision: 'duplicate',
          reasons: ['transitive_supported_cluster'],
        });
    }
  const orderedPairs = [...pairs.values()].sort(
    (a, b) =>
      compare_codepoints(a.left_id, b.left_id) ||
      compare_codepoints(a.right_id, b.right_id),
  );
  pairs.clear();
  function* pairRows() {
    for (const pair of orderedPairs)
      yield {
        ...pair,
        reasons: [...pair.reasons],
        evidence: evidence(
          byId.get(pair.left_id)!,
          byId.get(pair.right_id)!,
          policy,
        ),
      };
  }
  return {
    version: VERSION,
    mode: 'offline_identity_proposals',
    policy: structuredClone(policy),
    policy_sha256: sha256(canonicalJson(policy, { ascii: true })),
    hash_protocol: HASH_PROTOCOL,
    policy_status: 'provisional_requires_deployment_validation',
    record_ids: [...byId.keys()].sort(compare_codepoints),
    pairs: { [Symbol.iterator]: pairRows },
    pair_count: orderedPairs.length,
    clusters,
    crm_mutations: 0,
    merge_authorized: false,
    limitations: [
      'Contact identity only; employment identity and companies require separate policy.',
      'A proposed duplicate does not authorize CRM merge.',
      'Pairs not generated remain unassessed, not verified distinct.',
      'DOB and city are optional; evaluate accuracy on the fields available for the deployment.',
      'Default thresholds are provisional; validate on separate deployment data before use.',
    ],
  };
}

/** Materialized compatibility result; Plays generate pair evidence on demand. */
export function resolve_records(
  rows: Row[],
  suppliedPolicy: Row | null = null,
): Row {
  const {
    pairs,
    pair_count: _pairCount,
    ...result
  } = resolve_records_stream(rows, suppliedPolicy);
  return { ...result, pairs: [...pairs] };
}
