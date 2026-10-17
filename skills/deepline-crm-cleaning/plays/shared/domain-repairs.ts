import { classify_company_url } from './domain-policy';
import { canonicalJson, pythonCasefold, type JsonObject } from './json';

export const VERSION = 'company-domain-repair-plan.v1.3';
const FIELDS = ['domain', 'Domain', 'website', 'Website'] as const;
const ATTRIBUTES: Record<string, string[]> = {
  name: ['name', 'Name'],
  address: [
    'address',
    'Address',
    'street',
    'Street',
    'BillingStreet',
    'billing_street',
  ],
  phone: ['phone', 'Phone'],
  registration_id: ['registration_id', 'company_number', 'CompanyNumber'],
  legal_entity: ['legal_entity', 'legal_name', 'LegalName'],
};
function object(value: unknown): JsonObject | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as JsonObject)
    : null;
}
export function key(row: JsonObject): string {
  const source = object(row.source);
  if (
    !source ||
    !['system', 'scope_id'].every(
      (k) => typeof source[k] === 'string' && String(source[k]).trim(),
    )
  )
    throw new Error(
      'Every record/candidate needs an exact source.system and source.scope_id',
    );
  if (typeof row.id !== 'string' || !row.id.trim())
    throw new Error('Every record/candidate needs a nonempty string id');
  return canonicalJson([source.system, source.scope_id, row.id]);
}
function refs(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((x) => typeof x === 'string' && x.trim())
  );
}
function comparable(value: unknown, attribute: string): string | null {
  if (typeof value !== 'string' || !value.trim()) return null;
  if (attribute === 'phone') {
    const v = value.replace(/[^0-9]/g, '');
    return v.length >= 7 ? v : null;
  }
  return pythonCasefold(value).trim().replace(/\s+/gu, ' ');
}
export function assess_candidate(
  candidate: JsonObject,
  record: JsonObject,
  context?: unknown,
) {
  const classification = classify_company_url(
    candidate.candidate_domain,
    context,
  );
  const result = {
    candidate_domain: candidate.candidate_domain ?? null,
    classification,
    status: 'review',
    reason: 'incomplete_evidence',
  };
  if (!classification.eligible_company_domain)
    return {
      ...result,
      status: 'rejected',
      reason: 'candidate_not_eligible_for_company_website',
    };
  if (!refs(candidate.discovery_refs)) return result;
  const evidence = object(candidate.domain_evidence);
  if (!evidence || !refs(evidence.refs)) return result;
  if (
    classify_company_url(evidence.domain, context).normalized_url !==
    classification.normalized_url
  )
    return { ...result, reason: 'evidence_domain_mismatch' };
  const checks = object(evidence.checks);
  if (!checks) return result;
  const stages = ['dns', 'mx', 'web', 'legal'];
  for (const stage of stages) {
    const check = object(checks[stage]);
    if (
      !check ||
      !['success', 'failed', 'unknown', 'partial'].includes(
        String(check.status),
      ) ||
      !refs(check.refs)
    )
      return { ...result, reason: `missing_documented_${stage}_attempt` };
  }
  const stage = (name: string) =>
    checks[name] as { status: string; refs: string[] };
  if (['dns', 'web'].some((name) => stage(name).status !== 'success'))
    return { ...result, reason: 'dns_and_web_success_required' };
  const identity = object(candidate.identity_assessment);
  if (
    !identity ||
    !['supported', 'review', 'rejected'].includes(String(identity.status))
  )
    return result;
  if (identity.status !== 'supported')
    return {
      ...result,
      status: String(identity.status),
      reason: `identity_${identity.status}`,
    };
  if (
    typeof identity.reason !== 'string' ||
    !identity.reason.trim() ||
    !refs(identity.official_source_refs)
  )
    return { ...result, reason: 'missing_official_identity_attribution' };
  const technical = new Set([
    ...['dns', 'mx', 'web'].flatMap((name) => stage(name).refs),
    ...evidence.refs,
    ...candidate.discovery_refs,
  ]);
  const failed = new Set(
    stages
      .filter((name) => stage(name).status !== 'success')
      .flatMap((name) => stage(name).refs),
  );
  const contextual = new Set(
    identity.official_source_refs.filter(
      (ref) => !technical.has(ref) && !failed.has(ref),
    ),
  );
  if (!contextual.size)
    return {
      ...result,
      reason: 'identity_requires_contextual_source_not_technical_receipt',
    };
  const attributes = identity.matching_attributes ?? [];
  if (!Array.isArray(attributes))
    return { ...result, reason: 'invalid_identity_attributes' };
  const matched = new Set<string>();
  const properties = object(record.properties);
  if (!properties) throw new Error('Every company needs properties');
  for (const value of attributes) {
    const item = object(value);
    if (
      !item ||
      typeof item.attribute !== 'string' ||
      !Object.hasOwn(ATTRIBUTES, item.attribute) ||
      !refs(item.refs)
    )
      continue;
    const attribute = item.attribute;
    const expected = comparable(item.crm_value, attribute);
    const actual = new Set(
      ATTRIBUTES[attribute].map((alias) =>
        comparable(properties[alias], attribute),
      ),
    );
    if (
      expected !== null &&
      expected === comparable(item.observed_value, attribute) &&
      actual.has(expected) &&
      item.refs.some((ref) => contextual.has(ref))
    )
      matched.add(attribute);
  }
  if (
    !matched.has('legal_entity') &&
    !(matched.has('name') && matched.size > 1)
  )
    return {
      ...result,
      reason: 'name_alone_or_unmatched_context_is_insufficient',
    };
  return {
    ...result,
    status: 'supported',
    reason: 'documented_domain_checks_and_contextual_identity',
    matching_attributes: [...matched].sort(),
    evidence: structuredClone(candidate),
  };
}
function projection(properties: JsonObject, context?: unknown) {
  const classifications = Object.fromEntries(
    FIELDS.filter((f) => Object.hasOwn(properties, f)).map((f) => [
      f,
      classify_company_url(properties[f], context),
    ]),
  );
  const canonical = Object.entries(classifications)
    .filter(([, value]) => value.eligible_company_domain)
    .map(([field, value]) => ({
      field,
      hostname: value.hostname,
      registrable_domain: value.registrable_domain,
      category: value.category,
    }));
  const invalid = Object.fromEntries(
    Object.entries(classifications).filter(
      ([, value]) =>
        !value.eligible_company_domain && value.category !== 'missing',
    ),
  );
  return { classifications, canonical, invalid };
}
export function plan_records(
  records: JsonObject[],
  candidates: JsonObject[],
  contextRows: JsonObject[] = [],
) {
  const indexed = new Map<string, JsonObject>();
  for (const row of records) {
    const identity = key(row);
    if (indexed.has(identity))
      throw new Error('Duplicate scoped company id in input');
    if (!object(row.properties))
      throw new Error('Every company needs properties');
    const objectType = row.object_type ?? 'company';
    if (
      typeof objectType !== 'string' ||
      !['company', 'companies', 'account', 'accounts'].includes(
        objectType.toLowerCase(),
      )
    )
      throw new Error('Domain repair accepts company/account records only');
    indexed.set(identity, row);
  }
  const contexts = new Map<string, unknown>();
  for (const row of contextRows) {
    const identity = key(row);
    if (!indexed.has(identity))
      throw new Error(
        'Policy context references an unknown or foreign scoped company',
      );
    if (contexts.has(identity))
      throw new Error('Duplicate policy context identity');
    contexts.set(identity, row.context);
  }
  const candidateRows = new Map<string, JsonObject[]>();
  for (const candidate of candidates) {
    const identity = key(candidate);
    if (!indexed.has(identity))
      throw new Error(
        'Candidate references an unknown or foreign scoped company',
      );
    candidateRows.set(identity, [
      ...(candidateRows.get(identity) ?? []),
      candidate,
    ]);
  }
  const metrics: Record<string, number> = Object.fromEntries(
    [
      'records_with_invalid_fields_before',
      'invalid_fields_before',
      'records_with_eligible_candidate_before',
      'records_with_eligible_candidate_after',
      'records_with_invalid_fields_after',
      'invalid_fields_after',
      'records_proposed_for_repair',
      'fields_proposed_for_repair',
      'records_needing_review',
      'records_unresolved',
    ].map((name) => [name, 0]),
  );
  Object.assign(metrics, {
    records: records.length,
    crm_writes: 0,
    network_requests: 0,
  });
  const issueCategories: Record<string, number> = {};
  const results: JsonObject[] = [],
    proposed: JsonObject[] = [];
  for (const [identity, record] of indexed) {
    const context = contexts.get(identity),
      properties = record.properties as JsonObject;
    const {
      classifications,
      canonical: before,
      invalid,
    } = projection(properties, context);
    const assessments = (candidateRows.get(identity) ?? [])
      .map((c) => assess_candidate(c, record, context))
      .sort((a, b) =>
        canonicalJson(a) < canonicalJson(b)
          ? -1
          : canonicalJson(a) > canonicalJson(b)
            ? 1
            : 0,
      );
    const supported = new Map(
      assessments
        .filter((a) => a.status === 'supported')
        .map((a) => [a.classification.normalized_url, a]),
    );
    let decision = 'unchanged',
      selected: ReturnType<typeof assess_candidate> | undefined;
    if (Object.keys(invalid).length) {
      metrics.records_with_invalid_fields_before++;
      metrics.invalid_fields_before += Object.keys(invalid).length;
      for (const c of Object.values(invalid))
        issueCategories[c.category] = (issueCategories[c.category] ?? 0) + 1;
      decision = 'unresolved';
      if (
        Object.values(invalid).some((item) =>
          ['invalid', 'hosted_path'].includes(item.category),
        )
      )
        decision = 'review_existing_value_requires_identity';
      else if (supported.size > 1)
        decision = 'review_conflicting_supported_destinations';
      else if (supported.size === 1) {
        selected = supported.values().next().value;
        const chosen = selected!.classification;
        if (
          before.some(
            (item) =>
              item.registrable_domain !== chosen.registrable_domain ||
              ((item.category === 'hosted_site' ||
                chosen.category === 'hosted_site') &&
                item.hostname !== chosen.hostname),
          )
        ) {
          decision = 'review_conflict_with_existing_eligible_field';
          selected = undefined;
        } else decision = 'proposed_repair';
      } else if (assessments.length) decision = 'review_insufficient_evidence';
    } else if (
      !before.length &&
      supported.size &&
      Object.values(classifications).some((item) => item.category === 'missing')
    ) {
      decision = 'review_missing_value_requires_enrichment';
    }
    const changes: JsonObject[] = [],
      next = structuredClone(record),
      nextProps = next.properties as JsonObject;
    if (selected && 'evidence' in selected) {
      for (const [field, issue] of Object.entries(invalid)) {
        const value =
          field.toLowerCase() === 'domain'
            ? selected.classification.hostname
            : selected.classification.normalized_url;
        nextProps[field] = value;
        changes.push({
          field,
          before: properties[field],
          after: value,
          issue: issue.category,
          candidate_evidence: selected.evidence,
        });
      }
    }
    const { canonical: after, invalid: invalidAfter } = projection(
      nextProps,
      context,
    );
    metrics.records_with_eligible_candidate_before += Number(before.length > 0);
    metrics.records_with_eligible_candidate_after += Number(after.length > 0);
    metrics.records_with_invalid_fields_after += Number(
      Object.keys(invalidAfter).length > 0,
    );
    metrics.invalid_fields_after += Object.keys(invalidAfter).length;
    metrics.records_proposed_for_repair += Number(changes.length > 0);
    metrics.fields_proposed_for_repair += changes.length;
    metrics.records_needing_review += Number(decision.startsWith('review'));
    metrics.records_unresolved += Number(decision === 'unresolved');
    proposed.push(next);
    results.push({
      id: record.id,
      source: structuredClone(record.source),
      decision,
      before: Object.fromEntries(
        FIELDS.filter((f) => Object.hasOwn(properties, f)).map((f) => [
          f,
          properties[f],
        ]),
      ),
      after: Object.fromEntries(
        FIELDS.filter((f) => Object.hasOwn(nextProps, f)).map((f) => [
          f,
          nextProps[f],
        ]),
      ),
      classifications,
      canonical_before: before,
      canonical_after: after,
      candidate_assessments: assessments,
      proposals: changes,
      applied: false,
    });
  }
  return {
    before_after: results,
    proposed_records: proposed,
    metrics: {
      ...metrics,
      issue_categories_before: issueCategories,
      mode: 'offline_dry_run',
      after_is_simulated: true,
      eligibility_is_not_identity_verification: true,
      evidence_authenticity_and_freshness:
        'externally_assessed_not_verified_by_offline_planner',
    },
  };
}
