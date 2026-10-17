/** Deterministic receipt grading. Contract checks do not certify execution or model accuracy. */
import { canonicalJson, sha256 } from './json';
import { timestamp, normalized_timestamp } from './time';
import type { JsonObject } from './json';
type Row = JsonObject;
export type ArtifactEvidence = Record<string, string | Uint8Array>;
export const HASH_PROTOCOL = 'crm-json-js-v1';
export const MUTATING = new Set([
  'merge_records',
  'delete_record',
  'patch_fields',
  'create_record',
  'upsert_record',
  'link_entities',
  'end_relationship',
  'convert_lead',
  'clear_field',
  'change_owner',
  'refresh_employment',
  'schedule_refresh',
  'emit_alert',
  'block_create',
]);
const RECORD_MUTATIONS = new Set(
  [...MUTATING].filter(
    (k) => !['schedule_refresh', 'emit_alert', 'block_create'].includes(k),
  ),
);
const EXPECTED_KEYS = [
  'status',
  'decision',
  'required_reason_codes',
  'required_evidence_refs',
  'required_actions',
  'forbidden_actions',
  'action_specs',
  'facts',
  'metrics',
];
const METRIC_PROVENANCE = ['source_ref', 'window_start', 'window_end'];
const object = (v: unknown): v is Row =>
  v !== null && typeof v === 'object' && !Array.isArray(v);
const equal = (a: unknown, b: unknown): boolean =>
  canonicalJson(a) === canonicalJson(b);
const subset = (a: unknown[], b: unknown[]): boolean =>
  a.every((v) => b.includes(v));
const setEqual = (a: unknown[], b: unknown[]) => subset(a, b) && subset(b, a);
const unique = (a: unknown[]) => new Set(a).size === a.length;
const finite = (v: unknown): v is number =>
  typeof v === 'number' && Number.isFinite(v);
const close = (a: number, b: number) =>
  Number.isFinite(a) &&
  Math.abs(a - b) <= Math.max(1e-9, 1e-9 * Math.max(Math.abs(a), Math.abs(b)));
export const digest = (value: unknown): string => sha256(canonicalJson(value));
export function validate_schema_vocabulary(schema: Row, location = '$'): void {
  const supported = new Set([
    '$schema',
    '$id',
    'title',
    'description',
    'type',
    'properties',
    'required',
    'additionalProperties',
    'items',
    'uniqueItems',
    'minLength',
    'pattern',
    'format',
    'minimum',
    'enum',
    'const',
    'anyOf',
    'allOf',
    'if',
    'then',
    'x-ordering',
    'x-value-definitions',
  ]);
  const types = [
    'object',
    'array',
    'string',
    'null',
    'boolean',
    'number',
    'integer',
  ];
  if (!object(schema)) throw new Error(`${location}: schema must be an object`);
  const unsupported = Object.keys(schema).filter((k) => !supported.has(k));
  if (unsupported.length)
    throw new Error(
      `${location}: unsupported schema keywords: ${unsupported.sort().join(', ')}`,
    );
  if ('type' in schema) {
    const declared = Array.isArray(schema.type) ? schema.type : [schema.type];
    if (
      !declared.length ||
      !unique(declared) ||
      declared.some((v) => !types.includes(v))
    )
      throw new Error(`${location}: unsupported schema type`);
  }
  for (const keyword of ['anyOf', 'allOf'])
    if (keyword in schema) {
      if (!Array.isArray(schema[keyword]) || !schema[keyword].length)
        throw new Error(
          `${location}: ${keyword} requires a nonempty schema array`,
        );
      schema[keyword].forEach((s: Row, i: number) =>
        validate_schema_vocabulary(s, `${location}.${keyword}[${i}]`),
      );
    }
  if ('if' in schema !== 'then' in schema)
    throw new Error(
      `${location}: conditional schemas require both if and then`,
    );
  for (const keyword of ['if', 'then'])
    if (keyword in schema)
      validate_schema_vocabulary(schema[keyword], `${location}.${keyword}`);
  if ('properties' in schema) {
    if (!object(schema.properties))
      throw new Error(`${location}: properties must be an object`);
    for (const [key, child] of Object.entries(schema.properties))
      validate_schema_vocabulary(child, `${location}.properties.${key}`);
  }
  if ('items' in schema)
    validate_schema_vocabulary(schema.items, `${location}.items`);
  for (const keyword of ['additionalProperties', 'uniqueItems'])
    if (keyword in schema && typeof schema[keyword] !== 'boolean')
      throw new Error(`${location}: ${keyword} supports boolean values only`);
  if (
    'required' in schema &&
    (!Array.isArray(schema.required) ||
      schema.required.some((v: unknown) => typeof v !== 'string') ||
      !unique(schema.required))
  )
    throw new Error(`${location}: required must contain unique field names`);
  if ('enum' in schema && (!Array.isArray(schema.enum) || !schema.enum.length))
    throw new Error(`${location}: enum requires a nonempty array`);
  if ('format' in schema && schema.format !== 'date-time')
    throw new Error(`${location}: unsupported schema format`);
  if ('x-ordering' in schema) {
    const arrayType =
      schema.type === 'array' ||
      (Array.isArray(schema.type) &&
        schema.type.includes('array') &&
        subset(schema.type, ['array', 'null']));
    if (
      schema['x-ordering'] !== 'set' ||
      !arrayType ||
      schema.uniqueItems !== true
    )
      throw new Error(
        `${location}: x-ordering supports set-valued unique arrays only`,
      );
  }
  if ('x-value-definitions' in schema) {
    const defs = schema['x-value-definitions'];
    if (
      !object(defs) ||
      Object.values(defs).some((v) => typeof v !== 'string' || !v.trim())
    )
      throw new Error(
        `${location}: x-value-definitions must map category strings to nonempty definitions`,
      );
    if (
      !subset(
        Object.keys(defs),
        (schema.enum ?? []).filter((v: unknown) => typeof v === 'string'),
      )
    )
      throw new Error(
        `${location}: definitions must describe declared enum values`,
      );
  }
  if (
    'minLength' in schema &&
    (!Number.isSafeInteger(schema.minLength) || schema.minLength < 0)
  )
    throw new Error(`${location}: minLength must be a nonnegative integer`);
  if ('minimum' in schema && !finite(schema.minimum))
    throw new Error(`${location}: minimum must be finite numeric data`);
  if ('pattern' in schema) {
    if (typeof schema.pattern !== 'string')
      throw new Error(`${location}: pattern must be a string`);
    try {
      new RegExp(schema.pattern, 'u');
    } catch {
      throw new Error(`${location}: invalid schema pattern`);
    }
  }
}
export function schema_errors(
  value: unknown,
  schema: Row,
  location = '$',
): string[] {
  validate_schema_vocabulary(schema, location);
  const errors: string[] = [];
  if (
    schema.anyOf &&
    schema.anyOf.every((s: Row) => schema_errors(value, s, location).length)
  )
    errors.push(`${location}: no allowed type matches`);
  for (const child of schema.allOf ?? [])
    errors.push(...schema_errors(value, child, location));
  if (schema.if && !schema_errors(value, schema.if, location).length)
    errors.push(...schema_errors(value, schema.then, location));
  if ('const' in schema && !equal(value, schema.const))
    errors.push(`${location}: wrong constant`);
  if (schema.enum && schema.enum.every((v: unknown) => !equal(value, v)))
    errors.push(`${location}: outside allowed vocabulary`);
  const checks: Record<string, (v: unknown) => boolean> = {
    object,
    array: Array.isArray,
    string: (v) => typeof v === 'string',
    null: (v) => v === null,
    boolean: (v) => typeof v === 'boolean',
    number: finite,
    integer: (v) => finite(v) && Number.isInteger(v),
  };
  if (Array.isArray(schema.type)) {
    if (!schema.type.some((t: string) => checks[t](value)))
      return [...errors, `${location}: no allowed type matches`];
  } else if (schema.type && !checks[schema.type](value))
    return [...errors, `${location}: expected ${schema.type}`];
  if (object(value)) {
    const properties = schema.properties ?? {};
    for (const field of schema.required ?? [])
      if (!Object.hasOwn(value, field))
        errors.push(`${location}.${field}: required`);
    for (const [field, item] of Object.entries(value)) {
      if (Object.hasOwn(properties, field))
        errors.push(
          ...schema_errors(item, properties[field], `${location}.${field}`),
        );
      else if (schema.additionalProperties === false)
        errors.push(`${location}.${field}: unexpected field`);
    }
  } else if (Array.isArray(value)) {
    value.forEach((item, i) =>
      errors.push(
        ...schema_errors(item, schema.items ?? {}, `${location}[${i}]`),
      ),
    );
    if (
      schema.uniqueItems &&
      !unique(value.map((v: unknown) => canonicalJson(v)))
    )
      errors.push(`${location}: duplicate values`);
  } else if (typeof value === 'string') {
    if ([...value.trim()].length < (schema.minLength ?? 0))
      errors.push(`${location}: empty string`);
    if ('pattern' in schema && !new RegExp(schema.pattern, 'u').test(value))
      errors.push(`${location}: invalid format`);
    if (schema.format === 'date-time') {
      try {
        timestamp(value);
      } catch {
        errors.push(`${location}: timestamp with timezone required`);
      }
    }
  } else if (typeof value === 'number') {
    if (!finite(value)) errors.push(`${location}: non-finite number`);
    if ('minimum' in schema && value < schema.minimum)
      errors.push(`${location}: below minimum`);
  }
  return errors;
}
export function subset_errors(
  actual: unknown,
  expected: unknown,
  location = 'outcome',
  schema: Row = {},
): string[] {
  if (object(expected)) {
    if (!object(actual)) return [`${location}: expected object`];
    const errors = Object.keys(actual)
      .filter((k) => !Object.hasOwn(expected, k))
      .map((k) => `${location}.${k}: unrequested claim`);
    for (const [key, value] of Object.entries(expected))
      if (!Object.hasOwn(actual, key))
        errors.push(`${location}.${key}: missing`);
      else
        errors.push(
          ...subset_errors(
            actual[key],
            value,
            `${location}.${key}`,
            schema.properties?.[key] ?? {},
          ),
        );
    return errors;
  }
  if (Array.isArray(expected) && schema['x-ordering'] === 'set') {
    if (!Array.isArray(actual)) return [`${location}: expected array`];
    const encoded = actual.map((v: unknown) => canonicalJson(v));
    return unique(encoded) &&
      setEqual(
        encoded,
        expected.map((v: unknown) => canonicalJson(v)),
      )
      ? []
      : [`${location}: set values differ or contain duplicates`];
  }
  const matches =
    typeof expected === 'number' && typeof actual === 'number'
      ? Number.isInteger(expected)
        ? finite(actual) && actual === expected
        : close(actual, expected)
      : equal(actual, expected);
  return matches
    ? []
    : [
        `${location}: expected ${canonicalJson(expected)}, got ${canonicalJson(actual)}`,
      ];
}
export function index_unique(rows: Row[], label: string): Map<string, Row> {
  if (!Array.isArray(rows) || !rows.length)
    throw new Error(`${label}: empty dataset`);
  const result = new Map<string, Row>();
  for (const row of rows) {
    if (
      !object(row) ||
      typeof row.case_id !== 'string' ||
      !row.case_id ||
      result.has(row.case_id)
    )
      throw new Error(`${label}: missing or duplicate case_id`);
    result.set(row.case_id, row);
  }
  return result;
}
export function metric_errors(metric: Row): string[] {
  const n = metric.numerator,
    d = metric.denominator,
    value = metric.value,
    state = metric.state ?? null,
    errors: string[] = [];
  if (state !== null || METRIC_PROVENANCE.some((k) => k in metric))
    if (state === null || !METRIC_PROVENANCE.every((k) => metric[k]))
      errors.push(
        'explicit measurement state requires source_ref and observation window',
      );
  if ('window_start' in metric && 'window_end' in metric) {
    if (timestamp(metric.window_start) > timestamp(metric.window_end))
      errors.push('observation window ends before it starts');
    if (
      'as_of' in metric &&
      timestamp(metric.window_end) > timestamp(metric.as_of)
    )
      errors.push('observation window ends after as_of');
  }
  if (state === 'not_measured')
    return [
      ...errors,
      ...(n === null && d === null && value === null
        ? []
        : ['not_measured requires null numerator, denominator and value']),
    ];
  if (state === 'zero_denominator')
    return [
      ...errors,
      ...(metric.unit === 'ratio' && n === 0 && d === 0 && value === null
        ? []
        : ['zero_denominator requires ratio 0/0 and null value']),
    ];
  if (state !== null && state !== 'measured')
    return [...errors, 'unknown measurement state'];
  if (!finite(n) || n < 0)
    return [
      ...errors,
      'measured numerator must be a finite nonnegative number',
    ];
  if (metric.unit === 'ratio') {
    if (!finite(d) || n > d)
      return [...errors, 'ratio denominator missing or smaller than numerator'];
    if (d === 0)
      return [
        ...errors,
        ...(state === 'measured'
          ? [
              'measured ratio requires a positive denominator; use zero_denominator',
            ]
          : value === null
            ? []
            : ['zero denominator requires null value']),
      ];
    return [
      ...errors,
      ...(finite(value) && close(value, n / d)
        ? []
        : ['ratio does not reconcile']),
    ];
  }
  return [
    ...errors,
    ...(d === null &&
    finite(value) &&
    (metric.unit === 'count' ? value === n : close(value, n))
      ? []
      : ['non-ratio requires denominator null and value equal numerator']),
  ];
}
export function metric_values(metric: Row): Row {
  const values = Object.fromEntries(
    Object.entries(metric).filter(([key]) => !METRIC_PROVENANCE.includes(key)),
  );
  if (!('state' in values))
    values.state =
      metric.unit === 'ratio' && metric.denominator === 0
        ? 'zero_denominator'
        : 'measured';
  values.as_of = normalized_timestamp(metric.as_of);
  return values;
}
export function metric_provenance_errors(
  metric: Row,
  evidence: Row[],
  citedRefs: string[],
): string[] {
  if (!METRIC_PROVENANCE.some((k) => k in metric)) return [];
  if (!METRIC_PROVENANCE.every((k) => k in metric))
    return ['metric provenance requires source_ref and both window timestamps'];
  const matching = evidence.filter(
    (e) =>
      citedRefs.includes(e.id) &&
      [e.id, e.source_ref].includes(metric.source_ref),
  );
  if (!matching.length)
    return [
      'metric source_ref must identify supplied evidence cited by the receipt',
    ];
  try {
    const cutoff = timestamp(metric.as_of);
    if (!matching.some((e) => timestamp(e.observed_at) <= cutoff))
      return [
        'metric source observation must not be after the reporting cutoff',
      ];
  } catch {
    return ['metric source observation requires a timestamp with timezone'];
  }
  return [];
}
export function coverage_errors(status: string, outcome: Row): string[] {
  const c = outcome.coverage;
  if (c == null)
    return status === 'partial' ? ['partial status requires coverage'] : [];
  if (
    !object(c) ||
    ['planned', 'attempted', 'resolved', 'unresolved'].some(
      (k) => !Number.isSafeInteger(c[k]) || c[k] < 0,
    )
  )
    return ['coverage requires nonnegative integer counts'];
  const errors = !(
    c.resolved <= c.attempted &&
    c.attempted <= c.planned &&
    c.resolved + c.unresolved === c.planned
  )
    ? [
        'coverage requires resolved <= attempted <= planned and resolved + unresolved = planned',
      ]
    : [];
  if (['completed', 'no_change'].includes(status) && c.attempted < c.planned)
    errors.push(
      'completed/no_change requires every planned item to be attempted',
    );
  return errors;
}
export function relationship_errors(
  action: Row,
  reasonCodes?: string[],
): string[] {
  const errors: string[] = [];
  if (
    action.reason_code != null &&
    reasonCodes &&
    !reasonCodes.includes(action.reason_code)
  )
    errors.push('action reason_code must be included in receipt reason_codes');
  const r = action.relationship;
  if (r == null) return errors;
  if (
    r.valid_from !== null &&
    r.valid_to !== null &&
    timestamp(r.valid_from) > timestamp(r.valid_to)
  )
    errors.push('relationship interval ends before it starts');
  if (!setEqual(action.target_refs, [r.source_ref, r.target_ref]))
    errors.push('relationship targets must match both relationship endpoints');
  if (action.operation === 'end_relationship') {
    if (
      r.valid_to === null &&
      (!['proposed', 'blocked'].includes(action.status) || !action.reason_code)
    )
      errors.push(
        'unknown closing date requires a proposed/blocked action and reason_code',
      );
    if (
      r.valid_to !== null &&
      ['executed', 'verified'].includes(action.status) &&
      timestamp(r.valid_to) > timestamp(r.observed_at)
    )
      errors.push(
        'executed relationship ending cannot be future-dated relative to its observation',
      );
  }
  return errors;
}
export function relationships_equal(left: unknown, right: unknown): boolean {
  if (
    !object(left) ||
    !object(right) ||
    !setEqual(Object.keys(left), Object.keys(right))
  )
    return false;
  try {
    return Object.keys(left).every((k) =>
      ['valid_from', 'valid_to', 'observed_at'].includes(k) &&
      left[k] !== null &&
      right[k] !== null
        ? timestamp(left[k]) === timestamp(right[k])
        : equal(left[k], right[k]),
    );
  } catch {
    return false;
  }
}
export function action_specs_match(actions: Row[], specs: Row[]): boolean {
  if (actions.length !== specs.length) return false;
  const matches = (a: Row, s: Row) =>
    a.operation === s.operation &&
    a.status === s.status &&
    setEqual(a.target_refs, s.target_refs) &&
    (!('relationship' in s) ||
      relationships_equal(a.relationship, s.relationship)) &&
    (!('reason_code' in s) || a.reason_code === s.reason_code);
  const assigned = new Map<number, number>();
  function assign(specIndex: number, visited: Set<number>): boolean {
    for (let i = 0; i < actions.length; i++) {
      if (visited.has(i) || !matches(actions[i], specs[specIndex])) continue;
      visited.add(i);
      if (!assigned.has(i) || assign(assigned.get(i)!, visited)) {
        assigned.set(i, specIndex);
        return true;
      }
    }
    return false;
  }
  return specs.every((_, i) => assign(i, new Set()));
}
export function validate_dataset(
  inputs: Row[],
  labels: Row[],
  schema: Row,
): [Map<string, Row>, Map<string, Row>] {
  validate_schema_vocabulary(schema);
  const cases = index_unique(inputs, 'inputs'),
    gold = index_unique(labels, 'labels');
  if (!setEqual([...cases.keys()], [...gold.keys()]))
    throw new Error('Input/label coverage differs; select identical case IDs');
  const families = new Map<string, string>(),
    p = schema.properties,
    operations = p.actions.items.properties.operation.enum;
  const string = { type: 'string', minLength: 1 },
    strings = { type: 'array', items: string, uniqueItems: true },
    actionSchema = p.actions.items;
  const specSchema: Row = {
    type: 'object',
    properties: Object.fromEntries(
      Object.entries(actionSchema.properties).filter(
        ([k]) => k !== 'provider_receipt_ref',
      ),
    ),
    required: ['operation', 'target_refs', 'status'],
    additionalProperties: false,
    ...(actionSchema.allOf ? { allOf: actionSchema.allOf } : {}),
  };
  const expectedSchema = {
    type: 'object',
    required: [...EXPECTED_KEYS].sort(),
    additionalProperties: false,
    properties: {
      status: p.status,
      decision: string,
      required_reason_codes: strings,
      required_evidence_refs: strings,
      required_actions: strings,
      forbidden_actions: strings,
      action_specs: { type: 'array', items: specSchema },
      action_alternatives: {
        type: 'array',
        items: { type: 'array', items: specSchema },
      },
      acceptable_statuses: {
        type: 'array',
        items: p.status,
        uniqueItems: true,
      },
      allowed_reason_codes: strings,
      facts: { type: 'object' },
      metrics: p.metrics,
    },
  };
  for (const [key, c] of cases) {
    const fail = (message: string): never => {
      throw new Error(`${key}: ${message}`);
    };
    if (!p.path.enum.includes(c.path) || !p.crm.enum.includes(c.crm))
      fail('invalid path/crm');
    if (
      typeof c.family_id !== 'string' ||
      !c.family_id ||
      !['dev', 'test', 'holdout', 'public_challenge'].includes(c.split)
    )
      fail('family_id and explicit split required');
    if (families.has(c.family_id) && families.get(c.family_id) !== c.split)
      fail('family crosses partitions');
    families.set(c.family_id, c.split);
    const payload = c.input;
    if (!object(payload)) fail('input object required');
    const evidence = payload.evidence ?? [];
    if (!Array.isArray(evidence) || !evidence.every(object))
      fail('evidence array of objects required');
    const refs = evidence.map((e: Row) => e.id);
    if (
      !refs.length ||
      !refs.every((r: unknown) => typeof r === 'string' && r) ||
      !unique(refs)
    )
      fail('evidence IDs missing or duplicated');
    if (
      evidence.some(
        (e: Row) => !['kind', 'source_ref', 'observed_at'].every((k) => e[k]),
      )
    )
      fail('evidence provenance incomplete');
    const policy = payload.policy;
    if (!object(policy)) fail('policy object required');
    if (
      !['tenant_ref', 'snapshot_ref', 'policy_ref'].every(
        (k) => typeof policy[k] === 'string' && policy[k],
      )
    )
      fail('scope bindings missing');
    const expected = gold.get(key)!.expected,
      expectedErrors = schema_errors(expected, expectedSchema);
    if (expectedErrors.length)
      fail('invalid expected contract: ' + expectedErrors.join('; '));
    if (!p.status.enum.includes(expected.status) || !expected.decision)
      fail('invalid expected status/decision');
    if (
      schema_errors(
        { status: expected.status, outcome: expected.facts },
        { allOf: schema.allOf ?? [{}] },
      ).length ||
      schema_errors(expected.facts, p.outcome).length ||
      coverage_errors(expected.status, expected.facts).length
    )
      fail('invalid coverage');
    if (!subset(expected.required_evidence_refs, refs))
      fail('label refers to unavailable evidence');
    const required = expected.required_actions,
      forbidden = expected.forbidden_actions;
    if (
      required.some((v: unknown) => forbidden.includes(v)) ||
      !subset([...required, ...forbidden], operations)
    )
      fail('contradictory or unknown actions');
    if (
      !setEqual(
        expected.action_specs.map((a: Row) => a.operation),
        required,
      )
    )
      fail('action specs do not cover exactly the required actions');
    const actionSets = [
      expected.action_specs,
      ...(expected.action_alternatives ?? []),
    ];
    for (const specs of actionSets) {
      if (!unique(specs.map((v: unknown) => canonicalJson(v))))
        fail('duplicate action specs');
      if (specs.some((a: Row) => forbidden.includes(a.operation)))
        fail('alternative permits forbidden action');
    }
    const allowedReasons =
      expected.allowed_reason_codes ?? expected.required_reason_codes;
    if (!subset(expected.required_reason_codes, allowedReasons))
      fail('allowed reasons exclude required reason');
    const contract = payload.response_contract;
    if (!object(contract)) fail('visible response_contract required');
    for (const field of ['decision_vocabulary', 'reason_code_vocabulary'])
      if (schema_errors(contract[field], strings).length)
        fail(
          `visible response_contract.${field} must be an explicit array of unique nonempty strings`,
        );
    if (!object(contract.outcome_schema))
      fail(
        'visible response_contract.outcome_schema must be an explicit schema object',
      );
    validate_schema_vocabulary(
      contract.outcome_schema,
      `${key}: response_contract.outcome_schema`,
    );
    if (!contract.decision_vocabulary.includes(expected.decision))
      fail('decision missing from visible vocabulary');
    if (!subset(allowedReasons, contract.reason_code_vocabulary))
      fail('reason missing from visible vocabulary');
    if (schema_errors(expected.facts, contract.outcome_schema).length)
      fail('facts contradict visible output schema');
    if (
      [expected.status, ...(expected.acceptable_statuses ?? [])].includes(
        'partial',
      )
    ) {
      const coverage = expected.facts.coverage ?? {
        unit: 'records',
        planned: 1,
        attempted: 0,
        resolved: 0,
        unresolved: 1,
      };
      if (
        schema_errors({ ...expected.facts, coverage }, contract.outcome_schema)
          .length
      )
        fail('partial status requires an outcome schema that admits coverage');
    }
    const targets = contract.action_target_policy?.available_target_refs ?? [];
    for (const action of actionSets.flat()) {
      if (
        !subset(action.target_refs, targets) ||
        (RECORD_MUTATIONS.has(action.operation) && !action.target_refs.length)
      )
        fail('reference action target is outside visible scope');
      if (relationship_errors(action, allowedReasons).length)
        fail('invalid reference relationship action');
    }
    if (!unique(expected.metrics.map((m: Row) => m.name)))
      fail('duplicate reference metrics');
    if (
      !Array.isArray(contract.metrics) ||
      contract.metrics.some(
        (m: unknown) =>
          !object(m) || !['name', 'unit', 'cohort_ref'].every((k) => k in m),
      )
    )
      fail('visible metric definitions required');
    const definition = (m: Row) =>
      canonicalJson(
        Object.fromEntries(
          ['name', 'unit', 'cohort_ref'].map((k) => [k, m[k]]),
        ),
      );
    if (
      !equal(
        expected.metrics.map(definition).sort(),
        contract.metrics.map(definition).sort(),
      )
    )
      fail('reference metrics differ from visible request');
    for (const metric of expected.metrics) {
      if (
        schema_errors(metric, p.metrics.items).length ||
        metric_errors(metric).length
      )
        fail('invalid reference metric');
      if (metric_provenance_errors(metric, evidence, refs).length)
        fail('invalid reference metric provenance');
    }
  }
  return [cases, gold];
}
export function grade_case(
  c: Row,
  expected: Row,
  receipt: Row,
  schema: Row,
): Row[] {
  const failures: Row[] = [],
    fail = (code: string, detail: string) => {
      failures.push({ case_id: c.case_id, code, detail });
    };
  for (const error of schema_errors(receipt, schema))
    fail('receipt_schema', error);
  if (failures.length) return failures;
  for (const error of coverage_errors(receipt.status, receipt.outcome))
    fail('receipt_consistency', error);
  for (const field of ['case_id', 'path', 'crm'])
    if (receipt[field] !== c[field]) fail('route_binding', field);
  if (receipt.decision !== expected.decision) fail('wrong_outcome', 'decision');
  if (
    ![expected.status, ...(expected.acceptable_statuses ?? [])].includes(
      receipt.status,
    )
  )
    fail('wrong_outcome', 'status');
  const policy = c.input.policy,
    contract = c.input.response_contract;
  if (!subset(receipt.reason_codes, contract.reason_code_vocabulary))
    fail('unknown_reason_code', 'Use the visible response vocabulary');
  if (
    !subset(
      receipt.reason_codes,
      expected.allowed_reason_codes ?? expected.required_reason_codes,
    )
  )
    fail(
      'unsupported_reason',
      'A permitted vocabulary term still requires support in this case',
    );
  for (const field of ['tenant_ref', 'snapshot_ref', 'policy_ref'])
    if (receipt.scope[field] !== policy[field]) fail('scope_binding', field);
  const evidence = new Map<string, Row>(
    c.input.evidence.map((e: Row) => [e.id, e]),
  );
  if (
    !receipt.evidence_refs.length ||
    !subset(receipt.evidence_refs, [...evidence.keys()])
  )
    fail('unsupported_evidence', 'Reference supplied evidence IDs');
  for (const [field, actual] of [
    ['required_reason_codes', receipt.reason_codes],
    ['required_evidence_refs', receipt.evidence_refs],
  ] as const)
    for (const value of expected[field])
      if (!actual.includes(value))
        fail('missing_required_evidence_or_reason', value);
  const operations = receipt.actions.map((a: Row) => a.operation);
  for (const operation of expected.forbidden_actions)
    if (operations.includes(operation)) fail('forbidden_action', operation);
  if (
    ![expected.action_specs, ...(expected.action_alternatives ?? [])].some(
      (specs) => action_specs_match(receipt.actions, specs),
    )
  ) {
    for (const operation of expected.required_actions)
      if (!operations.includes(operation)) fail('missing_action', operation);
    fail(
      'action_contract',
      'Action operations, target sets, statuses and multiplicity must match one adjudicated contract',
    );
  }
  for (const action of receipt.actions) {
    for (const error of relationship_errors(action, receipt.reason_codes))
      fail('action_contract', error);
    if (
      MUTATING.has(action.operation) &&
      ['executed', 'verified', 'failed', 'unknown'].includes(action.status) &&
      policy.mutation_authorized !== true
    )
      fail('unauthorized_execution', action.operation);
    if (['executed', 'verified'].includes(action.status)) {
      const proof = evidence.get(action.provider_receipt_ref) ?? {},
        facts = object(proof.facts) ? proof.facts : {};
      const targets = facts.target_refs;
      if (
        proof.kind !== 'provider_receipt' ||
        facts.operation !== action.operation ||
        !Array.isArray(targets) ||
        targets.some((r) => typeof r !== 'string') ||
        !setEqual(targets, action.target_refs) ||
        !['executed', 'verified'].includes(facts.status) ||
        (action.status === 'verified' && facts.status !== 'verified')
      )
        fail('unproved_execution', action.operation);
      if (
        facts.tenant_ref !== policy.tenant_ref ||
        facts.snapshot_ref !== policy.snapshot_ref
      )
        fail('execution_scope', action.operation);
      if ('relationship' in action) {
        if (!relationships_equal(facts.relationship, action.relationship))
          fail(
            'unproved_execution',
            'relationship proof must match the typed edge and interval',
          );
        try {
          if (
            timestamp(proof.observed_at) <
            timestamp(action.relationship.observed_at)
          )
            throw new Error('proof predates observation');
        } catch {
          fail(
            'unproved_execution',
            'relationship requires dated provider proof at or after the relationship observation',
          );
        }
      }
    } else if (
      action.provider_receipt_ref !== null &&
      !evidence.has(action.provider_receipt_ref)
    )
      fail('unsupported_evidence', 'unknown action receipt');
  }
  for (const error of schema_errors(receipt.outcome, contract.outcome_schema))
    fail('outcome_schema', error);
  const comparedOutcome =
    'coverage' in expected.facts
      ? receipt.outcome
      : Object.fromEntries(
          Object.entries(receipt.outcome).filter(([k]) => k !== 'coverage'),
        );
  for (const error of subset_errors(
    comparedOutcome,
    expected.facts,
    'outcome',
    contract.outcome_schema,
  ))
    fail('fact_mismatch', error);
  if (!unique(receipt.metrics.map((m: Row) => m.name)))
    fail('duplicate_metric', 'Metric names must be unique within a receipt');
  const metrics = new Map<string, Row>(
    receipt.metrics.map((m: Row) => [m.name, m]),
  );
  if (
    !setEqual(
      [...metrics.keys()],
      expected.metrics.map((m: Row) => m.name),
    )
  )
    fail(
      'metric_contract',
      'Metric names must match the requested set; extra success claims are not accepted',
    );
  for (const metric of receipt.metrics) {
    for (const error of metric_errors(metric))
      fail('metric_arithmetic', metric.name + ': ' + error);
    for (const error of metric_provenance_errors(
      metric,
      c.input.evidence,
      receipt.evidence_refs,
    ))
      fail('metric_provenance', metric.name + ': ' + error);
  }
  for (const metric of expected.metrics) {
    if (!metrics.has(metric.name)) fail('missing_metric', metric.name);
    else
      for (const error of subset_errors(
        metric_values(metrics.get(metric.name)!),
        metric_values(metric),
        'metric.' + metric.name,
      ))
        fail('metric_mismatch', error);
  }
  return failures;
}
function validate_artifact_evidence(evidence: ArtifactEvidence): void {
  if (
    !object(evidence) ||
    Object.values(evidence).some(
      (v) => typeof v !== 'string' && !(v instanceof Uint8Array),
    )
  )
    throw new Error(
      'Artifact evidence requires explicit retained bytes by relative reference; claimed hashes are not file verification',
    );
}
export function artifact_errors(
  receipt: Row,
  evidence: ArtifactEvidence,
): Row[] {
  validate_artifact_evidence(evidence);
  const failures: Row[] = [];
  for (const artifact of receipt.artifacts) {
    const ref = artifact.ref;
    let detail: string | null = null;
    if (
      typeof ref !== 'string' ||
      !ref ||
      /[\\\x00]/.test(ref) ||
      ref.startsWith('/') ||
      /^[A-Za-z][A-Za-z0-9+.-]*:/.test(ref) ||
      ref.split('/').includes('..')
    )
      detail = 'Artifact ref must be a relative retained-artifact reference';
    else if (!Object.hasOwn(evidence, ref))
      detail =
        'Artifact bytes are unavailable; file validation was not performed';
    else if (artifact.sha256 === null)
      detail =
        'Artifact bytes are not bound to the receipt; sha256 is required';
    else if (sha256(evidence[ref]) !== artifact.sha256)
      detail = 'Artifact content hash does not match its receipt';
    if (detail)
      failures.push({
        case_id: receipt.case_id,
        code: 'artifact_verification',
        detail: `${ref}: ${detail}`,
      });
  }
  return failures;
}
export function component_results(
  errors: Row[],
  artifactsChecked: boolean,
): Row {
  const codes = new Set(errors.map((e) => e.code)),
    ungradable = [
      'missing_prediction',
      'duplicate_prediction',
      'receipt_schema',
      'receipt_consistency',
    ].some((c) => codes.has(c));
  const groups: Record<string, string[]> = {
    decisions: [],
    facts: ['outcome_schema', 'fact_mismatch'],
    metrics: [
      'duplicate_metric',
      'metric_contract',
      'metric_arithmetic',
      'metric_provenance',
      'missing_metric',
      'metric_mismatch',
    ],
    actions: [
      'forbidden_action',
      'missing_action',
      'action_contract',
      'unauthorized_execution',
      'unproved_execution',
      'execution_scope',
    ],
    evidence_and_scope: [
      'route_binding',
      'scope_binding',
      'unknown_reason_code',
      'unsupported_reason',
      'unsupported_evidence',
      'missing_required_evidence_or_reason',
    ],
    status: [],
  };
  const result: Row = Object.fromEntries(
    Object.entries(groups).map(([k, list]) => [
      k,
      !ungradable && !list.some((c) => codes.has(c)),
    ]),
  );
  for (const error of errors)
    if (error.code === 'wrong_outcome')
      result[error.detail === 'decision' ? 'decisions' : 'status'] = false;
  result.artifacts = artifactsChecked
    ? !ungradable && !codes.has('artifact_verification')
    : null;
  return result;
}
export function evaluate(
  inputs: Row[],
  labels: Row[],
  predictions: Row[],
  schema: Row,
  artifactEvidence?: ArtifactEvidence,
): Row {
  const [cases, gold] = validate_dataset(inputs, labels, schema);
  if (!Array.isArray(predictions))
    throw new Error('predictions array required');
  if (artifactEvidence !== undefined)
    validate_artifact_evidence(artifactEvidence);
  const byId = new Map<string, Row[]>(),
    failures: Row[] = [];
  for (const receipt of predictions) {
    if (!object(receipt) || typeof receipt.case_id !== 'string')
      failures.push({
        case_id: null,
        code: 'malformed_prediction',
        detail: 'case_id required',
      });
    else {
      if (!byId.has(receipt.case_id)) byId.set(receipt.case_id, []);
      byId.get(receipt.case_id)!.push(receipt);
    }
  }
  for (const key of [...byId.keys()].filter((k) => !cases.has(k)).sort())
    failures.push({
      case_id: key,
      code: 'unexpected_prediction',
      detail: 'Outside planned cohort',
    });
  const results: Row[] = [],
    slices: Row = { path: {}, crm: {}, split: {} };
  for (const [key, c] of cases) {
    const rows = byId.get(key) ?? [];
    const errors: Row[] =
      rows.length !== 1
        ? [
            {
              case_id: key,
              code: rows.length ? 'duplicate_prediction' : 'missing_prediction',
              detail: `Expected one receipt, got ${rows.length}`,
            },
          ]
        : grade_case(c, gold.get(key)!.expected, rows[0], schema);
    if (
      rows.length === 1 &&
      artifactEvidence !== undefined &&
      !errors.some((e) => e.code === 'receipt_schema')
    )
      errors.push(...artifact_errors(rows[0], artifactEvidence));
    failures.push(...errors);
    results.push({
      case_id: key,
      path: c.path,
      crm: c.crm,
      split: c.split,
      passed: !errors.length,
      failure_codes: [...new Set(errors.map((e) => e.code))].sort(),
      components: component_results(errors, artifactEvidence !== undefined),
    });
    for (const axis of Object.keys(slices)) {
      const counts = (slices[axis][c[axis]] ??= { planned: 0, passed: 0 });
      counts.planned++;
      counts.passed += Number(!errors.length);
    }
  }
  const passedCount = results.filter((r) => r.passed).length,
    components: Row = {};
  for (const name of Object.keys(results[0].components)) {
    const checked = results.filter((r) => r.components[name] !== null).length,
      passed = results.filter((r) => r.components[name] === true).length;
    components[name] = {
      planned: cases.size,
      checked,
      passed,
      pass_rate: checked ? passed / cases.size : null,
    };
  }
  return {
    schema_version: 'crm-cleaning-evaluation.v2',
    evaluation_kind: 'deterministic_receipt_contract',
    passed: !failures.length,
    live_crm_verified: false,
    universal_accuracy_claim: false,
    artifact_validation_mode:
      artifactEvidence !== undefined ? 'retained_bytes' : 'receipt_only',
    hash_protocol: HASH_PROTOCOL,
    summary: {
      planned_cases: cases.size,
      passed_cases: passedCount,
      failed_cases: cases.size - passedCount,
      pass_rate: passedCount / cases.size,
      missing_predictions: [...cases.keys()].filter((k) => !byId.has(k)).length,
      unexpected_predictions: [...byId.keys()].filter((k) => !cases.has(k))
        .length,
      duplicate_predictions: [...byId.values()].reduce(
        (n, v) => n + v.length - 1,
        0,
      ),
    },
    fingerprints: {
      inputs: digest(inputs),
      labels: digest(labels),
      predictions: digest(predictions),
      receipt_schema: digest(schema),
    },
    components,
    component_policy:
      'diagnostic_only; every failure still blocks the overall gate',
    slices,
    case_results: results,
    failures,
  };
}
export function validate_receipts(
  receipts: Row[],
  schema: Row,
  artifactEvidence?: ArtifactEvidence,
): Row {
  validate_schema_vocabulary(schema);
  if (!Array.isArray(receipts) || !receipts.length)
    throw new Error('At least one receipt is required');
  if (artifactEvidence !== undefined)
    validate_artifact_evidence(artifactEvidence);
  const results = receipts.map((receipt) => {
    const errors: Row[] = schema_errors(receipt, schema).map((detail) => ({
      code: 'receipt_schema',
      detail,
    }));
    if (!errors.length) {
      errors.push(
        ...coverage_errors(receipt.status, receipt.outcome).map((detail) => ({
          code: 'receipt_consistency',
          detail,
        })),
      );
      if (!unique(receipt.metrics.map((m: Row) => m.name)))
        errors.push({
          code: 'duplicate_metric',
          detail: 'Metric names must be unique within a receipt',
        });
      for (const metric of receipt.metrics)
        errors.push(
          ...metric_errors(metric).map((error) => ({
            code: 'metric_arithmetic',
            detail: metric.name + ': ' + error,
          })),
        );
      for (const action of receipt.actions)
        errors.push(
          ...relationship_errors(action, receipt.reason_codes).map(
            (detail) => ({ code: 'action_contract', detail }),
          ),
        );
      if (artifactEvidence !== undefined)
        errors.push(...artifact_errors(receipt, artifactEvidence));
    }
    return {
      case_id: object(receipt) ? (receipt.case_id ?? null) : null,
      valid: !errors.length,
      errors,
    };
  });
  return {
    validation_kind: 'receipt_structure_and_consistency',
    passed: results.every((r) => r.valid),
    live_crm_verified: false,
    execution_proof_checked: false,
    labels_checked: false,
    artifact_validation_mode:
      artifactEvidence !== undefined ? 'retained_bytes' : 'receipt_only',
    hash_protocol: HASH_PROTOCOL,
    summary: {
      receipts: results.length,
      valid: results.filter((r) => r.valid).length,
    },
    results,
    fingerprints: {
      receipt_schema: digest(schema),
      receipts: digest(receipts),
    },
  };
}
