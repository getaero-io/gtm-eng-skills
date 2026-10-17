import { normalize_domain } from './domain';
import { classify_company_url } from './domain-policy';
import { canonicalJson, sha256, type JsonObject } from './json';

export const VERSION = 'crm-sample-audit.v1.4';
const MISSING = Symbol('unobserved');
const NOT_APPLICABLE = Symbol('not_applicable');
const FIELD_NAMES: Record<string, string[]> = {
  name: ['name', 'Name'],
  first_name: ['firstname', 'FirstName', 'first_name'],
  last_name: ['lastname', 'LastName', 'last_name'],
  domain: ['domain', 'Domain'],
  website: ['website', 'Website'],
  email: ['email', 'Email'],
  job_title: ['jobtitle', 'Title', 'job_title'],
  company_id: ['associatedcompanyid', 'AccountId', 'company_id'],
  parent_id: ['hs_parent_company_id', 'ParentId', 'parent_id'],
  modified_at: [
    'hs_lastmodifieddate',
    'lastmodifieddate',
    'LastModifiedDate',
    'SystemModstamp',
    'modified_at',
  ],
};
const OBJECTS: Record<string, string> = {
  company: 'company',
  companies: 'company',
  account: 'company',
  accounts: 'company',
  contact: 'contact',
  contacts: 'contact',
};
const DEFAULT_REQUIRED_FIELDS = {
  company: ['name'],
  contact: ['name', 'email', 'job_title'],
};
const OPTIONS: Record<string, Set<string>> = {
  company: new Set(['name', 'domain', 'website', 'parent_id']),
  contact: new Set([
    'name',
    'first_name',
    'last_name',
    'email',
    'job_title',
    'company_id',
    'company_ids',
  ]),
};
function object(value: unknown): value is JsonObject {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
export function required_field_policy(value?: unknown) {
  const supplied = value !== undefined && value !== null;
  const policy = supplied ? value : DEFAULT_REQUIRED_FIELDS;
  if (
    !object(policy) ||
    Object.keys(policy).sort().join(',') !== 'company,contact'
  )
    throw new Error('Required fields must define company and contact arrays');
  const fields: Record<string, string[]> = {};
  for (const [type, names] of Object.entries(policy)) {
    if (
      !Array.isArray(names) ||
      names.some(
        (name) => typeof name !== 'string' || !OPTIONS[type].has(name),
      ) ||
      new Set(names).size !== names.length
    )
      throw new Error(
        `Invalid or repeated canonical required fields for ${type}`,
      );
    fields[type] = [...names].sort();
  }
  return {
    fields,
    origin: supplied ? 'configured' : 'legacy_defaults_unvalidated',
    sha256: sha256(canonicalJson(fields)),
  };
}
export function timestamp(value: unknown): number {
  if (typeof value !== 'string' || !/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value))
    throw new Error(
      'Timestamp must be an ISO string with an explicit timezone',
    );
  const parts = value.match(
    /^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?(Z|[+-]\d{2}:?\d{2})$/i,
  );
  if (!parts) throw new Error('Invalid ISO timestamp');
  const [, y, m, d, h, minutes, seconds, offset] = parts;
  const year = Number(y),
    month = Number(m),
    day = Number(d);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const zone = offset.replace(':', '');
  if (
    year < 1 ||
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > days[month - 1] ||
    Number(h) > 23 ||
    Number(minutes) > 59 ||
    Number(seconds ?? 0) > 59 ||
    (zone.toUpperCase() !== 'Z' &&
      (Number(zone.slice(1, 3)) > 23 || Number(zone.slice(3)) > 59))
  )
    throw new Error('Invalid ISO timestamp');
  const parsed = Date.parse(value.replace(',', '.'));
  if (!Number.isFinite(parsed)) throw new Error('Invalid ISO timestamp');
  return parsed;
}
const empty = (value: unknown) =>
  value === null || (typeof value === 'string' && !value.trim());
function field(properties: JsonObject, name: string) {
  for (const key of FIELD_NAMES[name])
    if (Object.hasOwn(properties, key)) return properties[key];
  return MISSING;
}
const field_state = (value: unknown) =>
  value === MISSING ? 'unobserved' : empty(value) ? 'missing' : 'populated';
export function identifier(value: unknown): string {
  if (
    !(
      (typeof value === 'string' && value.trim()) ||
      (typeof value === 'number' && Number.isSafeInteger(value))
    )
  )
    throw new Error(
      'Record and association IDs must be nonempty strings or safe integers',
    );
  return String(value).trim();
}
function company_links(
  row: JsonObject,
  properties: JsonObject,
  adapter?: string,
): [string[], boolean] {
  if (adapter === 'canonical.v1' && Object.hasOwn(row, 'associations'))
    throw new Error(
      'canonical.v1 accepts complete associations only through company_ids',
    );
  if (Object.hasOwn(row, 'company_ids')) {
    if (!Array.isArray(row.company_ids))
      throw new Error('company_ids must be a complete observed list');
    return [[...new Set<string>(row.company_ids.map(identifier))].sort(), true];
  }
  if (
    object(row.associations) &&
    Object.hasOwn(row.associations, 'companies')
  ) {
    const companies = row.associations.companies;
    if (!object(companies) || !Array.isArray(companies.results))
      throw new Error('Malformed companies association response');
    if (
      companies.paging &&
      (!object(companies.paging) || Object.keys(companies.paging).length)
    )
      throw new Error(
        'Company associations are paginated; finish pagination before auditing',
      );
    return [
      [
        ...new Set<string>(
          companies.results.map((value: JsonObject) => identifier(value.id)),
        ),
      ].sort(),
      true,
    ];
  }
  const value = field(properties, 'company_id');
  return [value === MISSING || empty(value) ? [] : [identifier(value)], false];
}
function source_fields(source: JsonObject, properties: JsonObject): JsonObject {
  if (
    typeof source.system !== 'string' ||
    !/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(source.system)
  )
    throw new Error('source.system must be a nonempty CRM/source name');
  if (source.adapter === 'canonical.v1') {
    if (Object.keys(properties).some((key) => !Object.hasOwn(FIELD_NAMES, key)))
      throw new Error(
        'canonical.v1 properties must use canonical field names only',
      );
    for (const [key, value] of Object.entries(properties)) {
      if (value === null) continue;
      if (key === 'company_id' || key === 'parent_id') {
        if (!empty(value)) identifier(value);
      } else if (typeof value !== 'string')
        throw new Error('canonical.v1 field values must be strings or null');
    }
    return Object.fromEntries(
      Object.keys(FIELD_NAMES).map((key) => [
        key,
        Object.hasOwn(properties, key) ? properties[key] : MISSING,
      ]),
    );
  }
  if (source.adapter !== undefined && source.adapter !== null)
    throw new Error(
      'Unsupported source.adapter; use canonical.v1 for mapped fields',
    );
  if (!['hubspot', 'salesforce'].includes(source.system.toLowerCase()))
    throw new Error(
      'Native fields are supported only for hubspot or salesforce; map fields and set source.adapter=canonical.v1',
    );
  return Object.fromEntries(
    Object.keys(FIELD_NAMES).map((key) => [key, field(properties, key)]),
  );
}
const matchKey = (policy: JsonObject) =>
  policy.category === 'hosted_site'
    ? policy.hostname
    : policy.registrable_domain;
export function normalize_email(value: unknown) {
  if (
    typeof value !== 'string' ||
    value.split('@').length !== 2 ||
    /\s/u.test(value)
  )
    throw new Error('invalid_email_syntax');
  const [local, domain] = value.split('@');
  if (
    !local ||
    local.length > 64 ||
    local.startsWith('.') ||
    local.endsWith('.') ||
    local.includes('..')
  )
    throw new Error('invalid_email_syntax');
  if (!/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$/.test(local))
    throw new Error('unsupported_or_invalid_email_local_part');
  if (!domain || /[/:?#\[\]]/.test(domain) || domain.endsWith('.'))
    throw new Error('invalid_email_domain_syntax');
  const normalized = normalize_domain(domain);
  if (value.length > 254) throw new Error('invalid_email_length');
  return { email: `${local}@${normalized.ascii_domain}`, domain: normalized };
}
export function normalize_row(row: JsonObject): JsonObject {
  if (!object(row) || !object(row.properties))
    throw new Error('Every row needs an object and properties mapping');
  const recordId = identifier(row.id),
    type = OBJECTS[String(row.object_type ?? '').toLowerCase()];
  if (!type)
    throw new Error(
      'Unsupported object_type; expected company/account/contact',
    );
  const source =
    typeof row.source === 'string' ? { system: row.source } : row.source;
  if (!object(source))
    throw new Error('source must identify a CRM/source system and scope_id');
  if (typeof source.scope_id !== 'string' || !source.scope_id.trim())
    throw new Error(
      'source.scope_id must be a nonempty tenant/source identifier',
    );
  const values = source_fields(source, row.properties);
  if (values.parent_id !== MISSING && !empty(values.parent_id))
    identifier(values.parent_id);
  if (
    type === 'contact' &&
    values.name === MISSING &&
    [values.first_name, values.last_name].every((value) => value !== MISSING)
  )
    values.name = [values.first_name, values.last_name]
      .filter((value) => !empty(value))
      .map((value) => String(value).trim())
      .join(' ');
  let domainValue = values.domain;
  if (domainValue === MISSING || empty(domainValue)) {
    if (values.website !== MISSING && !empty(values.website))
      domainValue = values.website;
    else if (domainValue === MISSING) domainValue = values.website;
  }
  const out: JsonObject = {
    id: recordId,
    object_type: type,
    system: source.system.toLowerCase(),
    scope_id: source.scope_id,
    source_adapter: source.adapter ?? 'legacy_native_fields',
    fields: Object.fromEntries(
      Object.entries(values).map(([name, value]) => [
        name,
        { state: field_state(value), value: value === MISSING ? null : value },
      ]),
    ),
    domain_state: field_state(domainValue),
    domain: null,
    email_state: field_state(values.email),
    email: null,
    company_ids: [],
    company_links_observed: false,
    company_links_complete: false,
    retrieved_at: Object.hasOwn(row, 'retrieved_at')
      ? row.retrieved_at
      : (source.retrieved_at ?? null),
    source_snapshot_at: Object.hasOwn(row, 'source_snapshot_at')
      ? row.source_snapshot_at
      : (source.snapshot_at ?? null),
  };
  if (out.domain_state === 'populated') {
    try {
      if (typeof domainValue !== 'string') throw new Error('non_string_domain');
      out.domain = normalize_domain(domainValue);
      out.domain_state = 'valid_syntax';
    } catch (error) {
      out.domain_state = 'invalid';
      out.domain_error = error instanceof Error ? error.message : String(error);
    }
  }
  if (type === 'company') {
    const contexts = Object.hasOwn(row, 'company_domain_context')
      ? row.company_domain_context
      : {};
    if (!object(contexts))
      throw new Error(
        'company_domain_context must map field roles to evidence-backed context',
      );
    const policies = Object.fromEntries(
      ['domain', 'website']
        .filter((name) => values[name] !== MISSING && !empty(values[name]))
        .map((name) => [
          name,
          classify_company_url(values[name], contexts[name]),
        ]),
    );
    const eligible = Object.entries(policies).filter(
      ([, policy]) => policy.eligible_company_domain,
    );
    Object.assign(out, {
      company_url_policies: policies,
      canonical_domain: null,
      canonical_domain_source: null,
      canonical_domain_match_key: null,
      domain_role_state: out.domain_state,
    });
    if (new Set(eligible.map(([, policy]) => matchKey(policy))).size > 1)
      out.domain_role_state = 'conflicting_company_domain_candidates';
    else if (eligible.length) {
      const [name, policy] = eligible[0];
      Object.assign(out, {
        canonical_domain: normalize_domain(policy.normalized_url!),
        canonical_domain_source: name,
        canonical_domain_match_key: matchKey(policy),
        domain_role_state: 'eligible_candidate_not_verified_identity',
      });
    } else if (
      Object.values(policies).some(
        (policy) => !['invalid', 'missing'].includes(policy.category),
      )
    )
      out.domain_role_state = 'rejected_company_url_role';
  } else {
    [out.company_ids, out.company_links_complete] = company_links(
      row,
      row.properties,
      source.adapter,
    );
    out.company_links_observed =
      out.company_links_complete || values.company_id !== MISSING;
    if (out.email_state === 'populated') {
      try {
        const result = normalize_email(values.email);
        out.email = result.email;
        out.email_domain = result.domain;
        out.email_state = 'valid_syntax';
      } catch (error) {
        out.email_state = 'invalid_or_unsupported';
        out.email_error =
          error instanceof Error ? error.message : String(error);
      }
    }
  }
  return out;
}
export function metric(
  definition: string,
  observations: Array<boolean | null | typeof NOT_APPLICABLE>,
) {
  const eligible = observations.filter((value) => value !== NOT_APPLICABLE),
    known = eligible.filter((value) => value !== null),
    numerator = known.filter((value) => value === true).length;
  return {
    definition,
    numerator,
    denominator: known.length,
    eligible: eligible.length,
    unknown: eligible.length - known.length,
    excluded_not_applicable: observations.length - eligible.length,
    rate: known.length ? numerator / known.length : null,
    status: !eligible.length
      ? 'zero_denominator'
      : known.length
        ? 'measured'
        : 'not_measured',
  };
}
function missing_field(row: JsonObject, name: string): boolean | null {
  if (name === 'company_ids')
    return row.company_links_complete ? !row.company_ids.length : null;
  return row.fields[name].state === 'unobserved'
    ? null
    : row.fields[name].state === 'missing';
}
function age(row: JsonObject, name: string, asOf: number): number | null {
  const value = Object.hasOwn(row, name) ? row[name] : row.fields[name].value;
  if (value === null) return null;
  try {
    const days = (asOf - timestamp(value)) / 86400000;
    return days >= 0 ? days : null;
  } catch {
    return null;
  }
}
export type AuditOptions = {
  company_population_complete?: boolean;
  stale_days?: number;
  source_lag_hours?: number;
  required_fields?: unknown;
};
export async function audit(
  rows: JsonObject[],
  as_of: string,
  options: AuditOptions = {},
) {
  const asOf = timestamp(as_of),
    complete = options.company_population_complete ?? false,
    staleDays = options.stale_days ?? 365,
    sourceLag = options.source_lag_hours ?? 24;
  if (
    ![staleDays, sourceLag].every((v) => Number.isFinite(v) && v >= 0) ||
    typeof complete !== 'boolean'
  )
    throw new Error('Invalid audit policy');
  const requirements = required_field_policy(options.required_fields),
    normalized = rows.map(normalize_row);
  const scopes = new Set(
    normalized.map((row) => canonicalJson([row.system, row.scope_id])),
  );
  if (scopes.size > 1)
    throw new Error('Mixed CRM scopes; audit each tenant/source separately');
  if (
    new Set(normalized.map((row) => canonicalJson([row.object_type, row.id])))
      .size !== normalized.length
  )
    throw new Error(
      'Repeated record ID within object type; reconcile snapshot first',
    );
  const companies = normalized.filter((row) => row.object_type === 'company'),
    contacts = normalized.filter((row) => row.object_type === 'contact'),
    companyIds = new Set(companies.map((row) => row.id));
  const issues: JsonObject[] = [],
    candidates: JsonObject[] = [];
  function issue(
    row: JsonObject,
    code: string,
    field: string,
    action: string,
    details: JsonObject = {},
  ) {
    issues.push({
      id: row.id,
      object_type: row.object_type,
      code,
      field,
      proposed_action: action,
      details,
      applied: false,
    });
  }
  for (const row of normalized) {
    for (const name of requirements.fields[row.object_type])
      if (missing_field(row, name))
        issue(
          row,
          'MISSING_REQUIRED_FIELD',
          name,
          'propose_evidence_backed_enrichment',
        );
    if (row.object_type === 'company') {
      if (row.domain_state === 'missing')
        issue(
          row,
          'MISSING_COMPANY_DOMAIN',
          'domain',
          'resolve_from_company_identity_evidence',
        );
      for (const [name, policy] of Object.entries(
        row.company_url_policies,
      ) as Array<[string, JsonObject]>) {
        if (policy.category === 'invalid')
          issue(row, 'INVALID_COMPANY_DOMAIN', name, 'review_source_value', {
            reason: policy.reason,
          });
        else if (
          !policy.eligible_company_domain &&
          policy.category !== 'missing'
        )
          issue(
            row,
            'THIRD_PARTY_COMPANY_URL',
            name,
            'discover_and_verify_official_company_domain',
            {
              category: policy.category,
              reason: policy.reason,
              raw_value_preserved: true,
            },
          );
      }
      if (row.domain_role_state === 'conflicting_company_domain_candidates')
        issue(
          row,
          'CONFLICTING_COMPANY_DOMAINS',
          'domain',
          'resolve_field_identity_conflict_before_matching',
        );
      if (row.fields.parent_id.state === 'populated') {
        const parentId = identifier(row.fields.parent_id.value);
        if (parentId === row.id)
          issue(
            row,
            'SELF_PARENT_REFERENCE',
            'parent_id',
            'review_hierarchy_evidence',
          );
        else if (!companyIds.has(parentId))
          issue(
            row,
            complete ? 'DANGLING_PARENT_REFERENCE' : 'PARENT_OUTSIDE_SAMPLE',
            'parent_id',
            'fetch_referenced_record_before_judgment',
            { parent_id: parentId },
          );
      }
    } else {
      if (row.email_state === 'invalid_or_unsupported')
        issue(row, 'EMAIL_SYNTAX_REVIEW', 'email', 'review_source_value', {
          reason: row.email_error,
        });
      if (row.company_links_complete && !row.company_ids.length)
        issue(
          row,
          'MISSING_COMPANY_LINK',
          'company_ids',
          'resolve_current_employment_before_linking',
        );
      for (const id of row.company_ids)
        if (!companyIds.has(id))
          issue(
            row,
            complete ? 'DANGLING_COMPANY_REFERENCE' : 'COMPANY_OUTSIDE_SAMPLE',
            'company_ids',
            'fetch_referenced_record_before_judgment',
            { company_id: id },
          );
      issue(
        row,
        'CURRENT_EMPLOYMENT_UNVERIFIED',
        'employment',
        'verify_dated_employment_evidence',
      );
    }
    row.record_age_days = age(row, 'modified_at', asOf);
    row.snapshot_age_days = age(row, 'source_snapshot_at', asOf);
    for (const name of ['modified_at', 'source_snapshot_at', 'retrieved_at']) {
      const value = name === 'modified_at' ? row.fields[name].value : row[name];
      if (value !== null) {
        try {
          const ahead = (timestamp(value) - asOf) / 1000;
          if (ahead > 0)
            issue(
              row,
              'FUTURE_TIMESTAMP',
              name,
              'review_source_clock_and_timestamp',
              { seconds_ahead: ahead },
            );
        } catch {
          /* Unknown timestamps remain unknown. */
        }
      }
    }
    row.source_lag_hours = null;
    row.source_timestamp_order_state = 'unobserved';
    if (row.source_snapshot_at && row.retrieved_at) {
      try {
        const lag =
          (timestamp(row.retrieved_at) - timestamp(row.source_snapshot_at)) /
          3600000;
        if (lag >= 0) {
          row.source_lag_hours = lag;
          row.source_timestamp_order_state = 'ordered';
        } else {
          row.source_timestamp_order_state = 'snapshot_after_retrieval';
          issue(
            row,
            'SNAPSHOT_AFTER_RETRIEVAL',
            'source_snapshot_at',
            'review_source_clock_and_timestamp',
            { snapshot_ahead_hours: -lag },
          );
        }
      } catch {
        row.source_timestamp_order_state = 'invalid_timestamp';
      }
    }
    if (row.record_age_days !== null && row.record_age_days > staleDays)
      issue(row, 'OLD_RECORD_UPDATE', 'modified_at', 'review_freshness', {
        warning:
          'Old CRM update time does not prove a job change or stale field',
        age_days: row.record_age_days,
      });
    if (row.source_lag_hours !== null && row.source_lag_hours > sourceLag)
      issue(
        row,
        'SOURCE_SNAPSHOT_LAG',
        'source_snapshot_at',
        'refresh_source_snapshot',
        { lag_hours: row.source_lag_hours },
      );
  }
  const groups: Record<string, Map<string, string[]>> = {
    exact_email: new Map(),
    registrable_domain: new Map(),
  };
  for (const row of contacts)
    if (row.email)
      groups.exact_email.set(row.email, [
        ...(groups.exact_email.get(row.email) ?? []),
        row.id,
      ]);
  for (const row of companies)
    if (row.canonical_domain)
      groups.registrable_domain.set(row.canonical_domain_match_key, [
        ...(groups.registrable_domain.get(row.canonical_domain_match_key) ??
          []),
        row.id,
      ]);
  for (const [kind, values] of Object.entries(groups))
    for (const [value, ids] of [...values].sort(([a], [b]) =>
      a < b ? -1 : a > b ? 1 : 0,
    ))
      if (ids.length > 1)
        candidates.push({
          candidate_type: kind,
          match_value: value,
          record_ids: [...ids].sort(),
          candidate_records: ids.length,
          excess_candidate_records: ids.length - 1,
          verified_duplicate: null,
          action: 'review_identity_and_account_grain',
          auto_merge_allowed: false,
        });
  const emailCandidates = new Set(
      [...groups.exact_email.values()].filter((ids) => ids.length > 1).flat(),
    ),
    domainCandidates = new Set(
      [...groups.registrable_domain.values()]
        .filter((ids) => ids.length > 1)
        .flat(),
    );
  const metrics: JsonObject = {};
  for (const [objectName, cohort, names] of [
    ['company', companies, ['name']],
    ['contact', contacts, ['name', 'email', 'job_title']],
  ] as Array<[string, JsonObject[], string[]]>) {
    for (const name of [
      ...new Set([...names, ...requirements.fields[objectName]]),
    ].sort())
      metrics[`${objectName}_missing_${name}`] = metric(
        `Empty ${name} / ${objectName} records with the field observed; omitted fields unknown`,
        cohort.map((row) => missing_field(row, name)),
      );
    for (const name of requirements.fields[objectName])
      metrics[`${objectName}_required_missing_${name}`] = metric(
        `Empty required ${name} / ${objectName} records with the field observed; omitted fields unknown`,
        cohort.map((row) => missing_field(row, name)),
      );
  }
  metrics.company_missing_domain = metric(
    'Empty company domain/website / companies with one of those fields observed',
    companies.map((r) =>
      r.domain_state === 'unobserved' ? null : r.domain_state === 'missing',
    ),
  );
  metrics.company_invalid_domain = metric(
    'Syntactically invalid domain / companies with a nonempty domain or website; not DNS failure rate',
    companies.map((r) =>
      r.domain_state === 'unobserved'
        ? null
        : r.domain_state === 'missing'
          ? NOT_APPLICABLE
          : r.domain_state === 'invalid',
    ),
  );
  const policies = (r: JsonObject): JsonObject[] =>
    Object.values(r.company_url_policies);
  metrics.company_invalid_url_records = metric(
    'Companies with at least one malformed observed domain/website field / companies with either field observed; every field checked independently',
    companies.map((r) =>
      r.domain_state === 'unobserved'
        ? null
        : policies(r).some((p) => p.category === 'invalid'),
    ),
  );
  metrics.company_third_party_url_records = metric(
    'Companies with at least one non-company-role Website/domain URL / companies with either field observed; raw values retained',
    companies.map((r) =>
      r.domain_state === 'unobserved'
        ? null
        : policies(r).some(
            (p) =>
              !p.eligible_company_domain &&
              !['invalid', 'missing'].includes(p.category),
          ),
    ),
  );
  metrics.company_canonical_domain_candidate_coverage = metric(
    'Companies with an eligible, non-conflicting domain candidate / companies with either field observed; not verified identity coverage',
    companies.map((r) =>
      r.domain_state === 'unobserved' ? null : r.canonical_domain !== null,
    ),
  );
  metrics.company_domain_conflict_records = metric(
    'Companies with conflicting eligible domain/website keys, including distinct hosted-site hostnames / companies with two eligible values',
    companies.map((r) =>
      policies(r).filter((p) => p.eligible_company_domain).length > 1
        ? r.domain_role_state === 'conflicting_company_domain_candidates'
        : NOT_APPLICABLE,
    ),
  );
  metrics.contact_email_syntax_review = metric(
    'Invalid or unsupported email syntax / contacts with nonempty email; no deliverability claim',
    contacts.map((r) =>
      r.email_state === 'unobserved'
        ? null
        : r.email_state === 'missing'
          ? NOT_APPLICABLE
          : r.email_state === 'invalid_or_unsupported',
    ),
  );
  metrics.contact_missing_company_link = metric(
    'No company associations / contacts with explicitly complete company association inventory; primary pointers alone are incomplete',
    contacts.map((r) =>
      r.company_links_complete ? !r.company_ids.length : null,
    ),
  );
  metrics.contact_company_link_outside_sample = metric(
    'Contacts with at least one observed referenced company absent from sampled companies / contacts with nonempty observed links; unobserved secondary associations are not evaluated',
    contacts.map((r) =>
      r.company_ids.length
        ? r.company_ids.some((id: string) => !companyIds.has(id))
        : r.company_links_complete
          ? NOT_APPLICABLE
          : null,
    ),
  );
  metrics.same_domain_collision_groups = metric(
    'Domain keys with multiple company records / eligible non-conflicting domain keys; hosted sites use exact hostnames; diagnostic only',
    [...groups.registrable_domain.values()].map((ids) => ids.length > 1),
  );
  metrics.company_same_domain_candidate_records = metric(
    'Company records in repeated registrable-domain groups / companies with eligible non-conflicting domain candidates; not duplicate rate',
    companies.map((r) =>
      r.domain_state === 'unobserved'
        ? null
        : r.canonical_domain
          ? domainCandidates.has(r.id)
          : NOT_APPLICABLE,
    ),
  );
  metrics.contact_exact_email_candidate_records = metric(
    'Contacts sharing exact local-part and case-normalized domain / contacts with supported email syntax; not confirmed duplicates',
    contacts.map((r) =>
      r.email_state === 'unobserved'
        ? null
        : r.email
          ? emailCandidates.has(r.id)
          : NOT_APPLICABLE,
    ),
  );
  metrics.confirmed_duplicate_rate = metric(
    'Excess records in independently adjudicated duplicate clusters / scoped records; requires adjudication',
    normalized.map(() => null),
  );
  metrics.verified_enriched_contact_coverage = metric(
    'Contacts meeting freshness, identity and field-evidence policy / scoped contacts; populated CRM fields alone do not establish enrichment',
    contacts.map(() => null),
  );
  metrics.verified_current_employment_coverage = metric(
    'Contacts with independently verified current employment / scoped contacts; snapshot alone cannot verify',
    contacts.map(() => null),
  );
  metrics.verified_legal_hierarchy_coverage = metric(
    'Companies with independently verified current legal hierarchy / scoped companies; parent pointers alone cannot verify',
    companies.map(() => null),
  );
  metrics.old_record_update = metric(
    `CRM record updates older than ${staleDays} days / records with usable modification timestamp; age is not truth`,
    normalized.map((r) =>
      r.record_age_days === null ? null : r.record_age_days > staleDays,
    ),
  );
  metrics.source_snapshot_lag = metric(
    `Source snapshots more than ${sourceLag} hours behind collection / records with usable snapshot and collection timestamps`,
    normalized.map((r) =>
      r.source_lag_hours === null ? null : r.source_lag_hours > sourceLag,
    ),
  );
  metrics.source_snapshot_after_retrieval = metric(
    'Snapshot later than retrieval / records with both timestamps parseable; impossible ordering is separate from unavailable timestamps',
    normalized.map((r) =>
      ['ordered', 'snapshot_after_retrieval'].includes(
        r.source_timestamp_order_state,
      )
        ? r.source_timestamp_order_state === 'snapshot_after_retrieval'
        : null,
    ),
  );
  metrics.parent_reference_outside_sample = metric(
    'Parent references absent from sampled companies / nonempty observed parent references; does not imply broken hierarchy in a partial sample',
    companies
      .filter((r) => r.fields.parent_id.state === 'populated')
      .map((r) => !companyIds.has(identifier(r.fields.parent_id.value))),
  );
  metrics.parent_field_unobserved = metric(
    'Companies whose parent pointer was not projected / sampled companies; blank projected parent is observed',
    companies.map((r) => r.fields.parent_id.state === 'unobserved'),
  );
  const issueCounts: Record<string, number> = {};
  for (const i of issues) issueCounts[i.code] = (issueCounts[i.code] ?? 0) + 1;
  return {
    normalized,
    issues,
    candidates,
    summary: {
      schema_version: VERSION,
      as_of: new Date(asOf).toISOString(),
      mode: 'read_only_offline_proposal',
      counts: {
        records: normalized.length,
        companies: companies.length,
        contacts: contacts.length,
        issues: issues.length,
        candidate_groups: candidates.length,
      },
      company_population_complete: complete,
      required_field_policy: requirements,
      source_scope_supplied: scopes.size > 0,
      crm_mutations: 0,
      provider_calls: 0,
      metrics,
      issue_counts: Object.fromEntries(Object.entries(issueCounts).sort()),
      limitations: [
        'Sample metrics describe this sample and are not population estimates.',
        'Duplicate candidates are not confirmed duplicates and never authorize merging.',
        'No DNS, MX, website, legal, enrichment or employment verification is performed by this offline stage.',
        'Parent references describe CRM structure, not independently verified legal ownership.',
        'Source lag uses snapshot and retrieval timestamps, never CRM record modification time.',
      ],
    },
  };
}
