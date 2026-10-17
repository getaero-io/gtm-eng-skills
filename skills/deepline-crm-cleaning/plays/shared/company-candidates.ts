import { classify_company_url, POLICY_VERSION } from './domain-policy';
import { PSL_HASH } from './domain';
import { canonicalJson, HASH_FORMAT, pythonCasefold, sha256 } from './json';
import { runtimeUnicodeVersion } from './native';
import casefoldTable from './unicode-casefold.json';

export const COMPANY_CANDIDATE_VERSION = 'company-candidates.v1';
export const COMPANY_MAX_RECORDS = 1000;
const MAX_NAME_CODEPOINTS = 256;
const CASEFOLD_TABLE_SHA256 = sha256(canonicalJson(casefoldTable));
const ACCOUNT_GRAINS = new Set([
  'legal_entity',
  'brand',
  'business_unit',
  'location',
  'unknown',
]);

type Source = { system: string; scope_id: string };
type CompanyFields = {
  name: string | null;
  domain: string | null;
  country: string | null;
  address: string | null;
  account_grain: string | null;
};
type Company = {
  id: string;
  object_type: 'company';
  source: Source;
  fields: CompanyFields;
  normalized_name: string;
  normalized_address: string;
  domain: ReturnType<typeof classify_company_url>;
  eligible_domain_key: string | null;
};
type CompanyPolicy = { name_similarity_threshold?: number };

function object(value: unknown, label: string): Record<string, unknown> {
  if (
    value === null ||
    typeof value !== 'object' ||
    Array.isArray(value) ||
    ![Object.prototype, null].includes(Object.getPrototypeOf(value))
  )
    throw new Error(`${label}: expected a plain object`);
  return value as Record<string, unknown>;
}
function keys(
  value: Record<string, unknown>,
  allowed: string[],
  label: string,
) {
  if (Object.keys(value).some((key) => !allowed.includes(key)))
    throw new Error(`${label}: unsupported field`);
}
function text(value: unknown, label: string, limit: number): string {
  if (
    typeof value !== 'string' ||
    Array.from(value).length > limit ||
    /[\uD800-\uDFFF]/u.test(value)
  )
    throw new Error(
      `${label}: expected a Unicode string of at most ${limit} code points`,
    );
  return value;
}
function identifier(value: unknown, label: string): string {
  const result = text(value, label, 256);
  if (
    !result ||
    result !== result.trim() ||
    /[\u0000-\u001f\u007f]/u.test(result)
  )
    throw new Error(
      `${label}: expected an exact nonempty identifier without padding or ASCII controls`,
    );
  return result;
}

export function normalize_company_name(value: string): string {
  return pythonCasefold(value.normalize('NFKC'))
    .replace(/[^\p{L}\p{M}\p{N}]+/gu, ' ')
    .trim();
}

/** Character similarity only. Empty/empty is 1; missing CRM names are not scored. */
export function jaro_winkler(left: string, right: string): number {
  if (left === right) return 1;
  let a = Array.from(left),
    b = Array.from(right);
  if (!a.length || !b.length) return 0;
  // Fix the orientation for repeated-character ties and input-order invariance.
  if (a.length > b.length || (a.length === b.length && left > right))
    [a, b] = [b, a];
  const window = Math.max(0, Math.floor(Math.max(a.length, b.length) / 2) - 1);
  const usedA = new Uint8Array(a.length),
    usedB = new Uint8Array(b.length);
  let matches = 0;
  for (let i = 0; i < a.length; i++) {
    const end = Math.min(i + window + 1, b.length);
    for (let j = Math.max(0, i - window); j < end; j++) {
      if (usedB[j] || a[i] !== b[j]) continue;
      usedA[i] = 1;
      usedB[j] = 1;
      matches++;
      break;
    }
  }
  if (!matches) return 0;
  let mismatches = 0,
    j = 0;
  for (let i = 0; i < a.length; i++) {
    if (!usedA[i]) continue;
    while (!usedB[j]) j++;
    if (a[i] !== b[j]) mismatches++;
    j++;
  }
  const jaro =
    (matches / a.length +
      matches / b.length +
      (matches - Math.floor(mismatches / 2)) / matches) /
    3;
  if (jaro <= 0.7) return jaro;
  let prefix = 0;
  while (prefix < Math.min(4, a.length, b.length) && a[prefix] === b[prefix])
    prefix++;
  return jaro + prefix * 0.1 * (1 - jaro);
}

function company(value: unknown, index: number): Company {
  const label = `Company row ${index + 1}`;
  const row = object(value, label);
  keys(row, ['id', 'object_type', 'source', 'fields'], label);
  if (row.object_type !== 'company')
    throw new Error(`${label}: object_type must be company`);
  const id = identifier(row.id, `${label}.id`);
  const source = object(row.source, `${label}.source`);
  keys(source, ['system', 'scope_id'], `${label}.source`);
  const system = identifier(source.system, `${label}.source.system`);
  if (!/^[a-z][a-z0-9_-]*$/.test(system))
    throw new Error(`${label}.source.system: use a lowercase source name`);
  const scope_id = identifier(source.scope_id, `${label}.source.scope_id`);
  const supplied = object(row.fields, `${label}.fields`);
  keys(
    supplied,
    ['name', 'domain', 'country', 'address', 'account_grain'],
    `${label}.fields`,
  );
  if (!Object.hasOwn(supplied, 'name'))
    throw new Error(`${label}.fields.name: required; use null when missing`);
  const fields: CompanyFields = {
    name: null,
    domain: null,
    country: null,
    address: null,
    account_grain: null,
  };
  for (const key of Object.keys(fields) as Array<keyof CompanyFields>) {
    if (supplied[key] === undefined && key !== 'name') continue;
    if (supplied[key] === null) continue;
    fields[key] = text(
      supplied[key],
      `${label}.fields.${key}`,
      key === 'domain' ? 4096 : key === 'address' ? 1024 : MAX_NAME_CODEPOINTS,
    );
  }
  if (fields.country !== null && !/^[A-Z]{2}$/.test(fields.country))
    throw new Error(
      `${label}.fields.country: expected a two-letter uppercase country code or null`,
    );
  if (
    fields.account_grain !== null &&
    !ACCOUNT_GRAINS.has(fields.account_grain)
  )
    throw new Error(`${label}.fields.account_grain: unsupported account grain`);
  const normalized_name = normalize_company_name(fields.name ?? '');
  if (Array.from(normalized_name).length > MAX_NAME_CODEPOINTS)
    throw new Error(
      `${label}.fields.name: normalized name exceeds ${MAX_NAME_CODEPOINTS} code points`,
    );
  const domain = classify_company_url(fields.domain);
  return {
    id,
    object_type: 'company',
    source: { system, scope_id },
    fields,
    normalized_name,
    normalized_address: normalize_company_name(fields.address ?? ''),
    domain,
    eligible_domain_key: domain.eligible_company_domain
      ? domain.category === 'hosted_site'
        ? domain.hostname
        : domain.registrable_domain
      : null,
  };
}
function identity(row: Company): string {
  return canonicalJson([row.source.system, row.source.scope_id, row.id]);
}
function sameDomain(a: Company, b: Company): boolean {
  return (
    a.eligible_domain_key !== null &&
    a.eligible_domain_key === b.eligible_domain_key
  );
}
function selected(
  a: Company,
  b: Company,
  score: number,
  threshold: number,
): boolean {
  return score >= threshold || sameDomain(a, b);
}
const RETRIEVAL_FLAGS = {
  similar_name: 1,
  same_eligible_domain: 2,
};
const REVIEW_FLAGS = {
  same_name_is_not_identity_proof: 1,
  shared_domain_is_not_identity_or_hierarchy_proof: 2,
  different_countries_require_review: 4,
  different_account_grains_require_review: 8,
  different_addresses_require_review: 16,
  different_eligible_domains_require_review: 32,
  cross_source_scope_pair: 64,
};
function pairCodes(a: Company, b: Company, score: number, threshold: number) {
  let retrieval_mask = 0,
    review_mask = 0;
  if (score >= threshold) retrieval_mask |= RETRIEVAL_FLAGS.similar_name;
  if (sameDomain(a, b)) {
    retrieval_mask |= RETRIEVAL_FLAGS.same_eligible_domain;
    review_mask |=
      REVIEW_FLAGS.shared_domain_is_not_identity_or_hierarchy_proof;
  }
  if (score === 1) review_mask |= REVIEW_FLAGS.same_name_is_not_identity_proof;
  if (
    a.fields.country &&
    b.fields.country &&
    a.fields.country !== b.fields.country
  )
    review_mask |= REVIEW_FLAGS.different_countries_require_review;
  if (
    a.fields.account_grain &&
    b.fields.account_grain &&
    a.fields.account_grain !== 'unknown' &&
    b.fields.account_grain !== 'unknown' &&
    a.fields.account_grain !== b.fields.account_grain
  )
    review_mask |= REVIEW_FLAGS.different_account_grains_require_review;
  if (
    a.normalized_address &&
    b.normalized_address &&
    a.normalized_address !== b.normalized_address
  )
    review_mask |= REVIEW_FLAGS.different_addresses_require_review;
  if (
    a.eligible_domain_key &&
    b.eligible_domain_key &&
    a.eligible_domain_key !== b.eligible_domain_key
  )
    review_mask |= REVIEW_FLAGS.different_eligible_domains_require_review;
  if (
    a.source.system !== b.source.system ||
    a.source.scope_id !== b.source.scope_id
  )
    review_mask |= REVIEW_FLAGS.cross_source_scope_pair;
  return { retrieval_mask, review_mask };
}
function decodeFlags(mask: number, flags: Record<string, number>): string[] {
  return Object.entries(flags)
    .filter(([, bit]) => (mask & bit) !== 0)
    .map(([name]) => name);
}
function pair(a: Company, b: Company, score: number, threshold: number) {
  const { retrieval_mask, review_mask } = pairCodes(a, b, score, threshold);
  return {
    pair_id: sha256(canonicalJson([identity(a), identity(b)])),
    left: { id: a.id, source: a.source },
    right: { id: b.id, source: b.source },
    name_jaro_winkler: Number.isNaN(score) ? null : score,
    reasons: decodeFlags(retrieval_mask, RETRIEVAL_FLAGS),
    review_flags: decodeFlags(review_mask, REVIEW_FLAGS),
    evidence: {
      left_name: a.fields.name,
      right_name: b.fields.name,
      left_normalized_name: a.normalized_name,
      right_normalized_name: b.normalized_name,
      left_domain_key: a.eligible_domain_key,
      right_domain_key: b.eligible_domain_key,
      left_country: a.fields.country,
      right_country: b.fields.country,
      same_normalized_address:
        a.normalized_address && b.normalized_address
          ? a.normalized_address === b.normalized_address
          : null,
      left_account_grain: a.fields.account_grain,
      right_account_grain: b.fields.account_grain,
    },
    decision: 'unresolved' as const,
    auto_merge_allowed: false as const,
    hierarchy_inferred: false as const,
  };
}

export function score_company_candidates(records: unknown[], policy?: unknown) {
  if (!Array.isArray(records) || records.length > COMPANY_MAX_RECORDS)
    throw new Error(
      `Expected at most ${COMPANY_MAX_RECORDS} company records; partition explicitly and evaluate cross-partition coverage for larger inputs`,
    );
  const options =
    policy === undefined ? {} : object(policy, 'Company candidate policy');
  keys(options, ['name_similarity_threshold'], 'Company candidate policy');
  const name_similarity_threshold =
    (options as CompanyPolicy).name_similarity_threshold ?? 0.88;
  if (
    typeof name_similarity_threshold !== 'number' ||
    !Number.isFinite(name_similarity_threshold) ||
    name_similarity_threshold <= 0 ||
    name_similarity_threshold > 1
  )
    throw new Error(
      'name_similarity_threshold must be finite, greater than 0 and at most 1',
    );
  if (
    Object.hasOwn(options, 'name_similarity_threshold') &&
    options.name_similarity_threshold == null
  )
    throw new Error('name_similarity_threshold cannot be null or undefined');
  const inventory = records
    .map(company)
    .sort((a, b) =>
      identity(a) < identity(b) ? -1 : identity(a) > identity(b) ? 1 : 0,
    )
    .map((row, record_index) => ({ ...row, record_index }));
  if (new Set(inventory.map(identity)).size !== inventory.length)
    throw new Error(
      'Repeated company identity within the same source system and scope; reconcile the snapshot first',
    );
  const effectivePolicy = {
    version: COMPANY_CANDIDATE_VERSION,
    name_similarity_threshold,
    calibration: 'provisional_not_calibrated',
    normalization: 'NFKC_full_casefold_letters_marks_numbers_space_v1',
    normalization_runtime_unicode_version: runtimeUnicodeVersion,
    casefold_table_sha256: CASEFOLD_TABLE_SHA256,
    jaro_winkler: {
      transpositions: 'floor_mismatched_matched_codepoints_divided_by_2',
      prefix_scale: 0.1,
      max_prefix_codepoints: 4,
      prefix_boost_when_jaro_greater_than: 0.7,
    },
    max_records: COMPANY_MAX_RECORDS,
    max_name_codepoints: MAX_NAME_CODEPOINTS,
    domain_policy_version: POLICY_VERSION,
    public_suffix_list_sha256: PSL_HASH,
  };
  const pair_space = (inventory.length * (inventory.length - 1)) / 2;
  const scores = new Float64Array(pair_space);
  let index = 0,
    generated_pair_count = 0,
    candidate_group_count = 0,
    name_scored_pair_count = 0;
  for (let i = 0; i < inventory.length; i++) {
    let groupSelected = false;
    for (let j = i + 1; j < inventory.length; j++) {
      const a = inventory[i],
        b = inventory[j];
      const score =
        a.normalized_name && b.normalized_name
          ? jaro_winkler(a.normalized_name, b.normalized_name)
          : NaN;
      scores[index++] = score;
      if (!Number.isNaN(score)) name_scored_pair_count++;
      if (selected(a, b, score, name_similarity_threshold)) {
        generated_pair_count++;
        groupSelected = true;
      }
    }
    if (groupSelected) candidate_group_count++;
  }
  function* pairs() {
    let index = 0;
    for (let i = 0; i < inventory.length; i++) {
      for (let j = i + 1; j < inventory.length; j++) {
        const a = inventory[i],
          b = inventory[j],
          score = scores[index++];
        if (selected(a, b, score, name_similarity_threshold))
          yield pair(a, b, score, name_similarity_threshold);
      }
    }
  }
  function* pairGroups() {
    let index = 0;
    for (let i = 0; i < inventory.length; i++) {
      const candidates: Array<[number, number | null, number, number]> = [];
      for (let j = i + 1; j < inventory.length; j++) {
        const a = inventory[i],
          b = inventory[j],
          score = scores[index++];
        if (!selected(a, b, score, name_similarity_threshold)) continue;
        const { retrieval_mask, review_mask } = pairCodes(
          a,
          b,
          score,
          name_similarity_threshold,
        );
        candidates.push([
          j,
          Number.isNaN(score) ? null : score,
          retrieval_mask,
          review_mask,
        ]);
      }
      if (candidates.length)
        yield {
          left_record_index: i,
          candidates,
          decision: 'unresolved' as const,
          auto_merge_allowed: false as const,
          hierarchy_inferred: false as const,
        };
    }
  }
  return {
    inventory,
    pairs: { [Symbol.iterator]: pairs },
    pair_groups: { [Symbol.iterator]: pairGroups },
    metadata: {
      version: COMPANY_CANDIDATE_VERSION,
      policy: effectivePolicy,
      policy_sha256: sha256(canonicalJson(effectivePolicy)),
      hash_format: HASH_FORMAT,
      input_sha256: sha256(
        canonicalJson(
          inventory.map(({ id, object_type, source, fields }) => ({
            id,
            object_type,
            source,
            fields,
          })),
        ),
      ),
      pair_group_schema: {
        version: 'crm-company-pair-groups.v1',
        inventory_join_key: 'record_index',
        candidate_tuple_columns: [
          'right_record_index',
          'name_jaro_winkler',
          'retrieval_mask',
          'review_mask',
        ],
        retrieval_mask_flags: RETRIEVAL_FLAGS,
        review_mask_flags: REVIEW_FLAGS,
        mask_semantics:
          'Bitwise OR of the named flags; zero means no flags in that mask.',
        missing_name_score: null,
      },
      record_count: inventory.length,
      candidate_group_count,
      pair_space,
      scored_pair_count: pair_space,
      name_scored_pair_count,
      generated_pair_count,
      unassessed_pair_count: pair_space - generated_pair_count,
      unresolved_candidate_pair_count: generated_pair_count,
      resolved_pair_count: 0,
      candidate_pair_coverage: pair_space
        ? generated_pair_count / pair_space
        : null,
      unresolved_candidate_coverage: generated_pair_count ? 1 : null,
      candidate_generation_complete: true,
      all_pairs_within_input_compared: true,
      auto_merge_allowed: false,
      hierarchy_inferred: false,
      candidate_semantics:
        'Name/domain similarities retrieve review candidates only. Non-generated pairs are unassessed, not proven distinct. Scores are not identity probabilities.',
    },
  };
}
