import { createHash } from './native';
import type { DeeplinePlayRuntimeContext } from 'deepline';
import { canonicalJson, sha256, HASH_FORMAT, type JsonObject } from './json';
import { identifier } from './audit';

export type HubspotContext = Pick<
  DeeplinePlayRuntimeContext,
  'fetch' | 'secrets' | 'step' | 'run'
>;
export { HASH_FORMAT } from './json';
const PROPERTIES = [
  'name',
  'domain',
  'website',
  'country',
  'city',
  'industry',
  'lifecyclestage',
  'num_associated_contacts',
  'createdate',
  'hs_lastmodifieddate',
];
export const FIELDS: Record<string, string[]> = {
  companies: [
    ...PROPERTIES,
    'hubspot_owner_id',
    'hs_parent_company_id',
    'hs_object_source',
    'hs_object_source_label',
    'hs_object_source_detail_1',
    'hs_object_source_detail_2',
    'hs_object_source_detail_3',
  ],
  contacts: [
    'firstname',
    'lastname',
    'email',
    'jobtitle',
    'company',
    'associatedcompanyid',
    'phone',
    'country',
    'city',
    'website',
    'lifecyclestage',
    'createdate',
    'lastmodifieddate',
    'hubspot_owner_id',
    'hs_email_hard_bounce_reason',
    'hs_email_last_send_date',
    'hs_email_optout',
    'hs_linkedin_url',
    'hs_object_source',
    'hs_object_source_label',
    'hs_object_source_detail_1',
    'hs_object_source_detail_2',
    'hs_object_source_detail_3',
  ],
};
function object(
  value: unknown,
  message = 'Expected a response object',
): JsonObject {
  if (value === null || typeof value !== 'object' || Array.isArray(value))
    throw new Error(message);
  return value as JsonObject;
}
function rows(value: unknown, message: string): JsonObject[] {
  if (!Array.isArray(value)) throw new Error(message);
  return value.map((v) => object(v, message));
}
function cursor(page: JsonObject): string | null {
  if (page.paging === undefined || page.paging === null) return null;
  const paging = object(page.paging, 'Malformed pagination');
  if (paging.next === undefined || paging.next === null) return null;
  const next = object(paging.next, 'Malformed next page');
  if (
    next.after === undefined ||
    next.after === null ||
    String(next.after) === ''
  )
    throw new Error('Next page omitted cursor');
  return identifier(next.after);
}
export async function createHubspotReader(
  ctx: HubspotContext,
  expectedPortalId: string,
) {
  if (typeof expectedPortalId !== 'string' || !expectedPortalId.trim())
    throw new Error('expected_portal_id is required');
  const observedAt = await ctx.step(
    'hubspot-collection-clock',
    async () => new Date().toISOString(),
    { semanticKey: ctx.run.id },
  );
  const token = await ctx.secrets.get('HUBSPOT_API_KEY');
  async function request(
    path: string,
    payload?: JsonObject,
    verify = false,
  ): Promise<JsonObject> {
    if (
      !path.startsWith('/') ||
      path.startsWith('//') ||
      path.includes('#') ||
      path.includes('\\')
    )
      throw new Error('Invalid fixed-origin HubSpot path');
    const url = new URL(path, 'https://api.hubapi.com');
    if (url.origin !== 'https://api.hubapi.com')
      throw new Error('HubSpot origin mismatch');
    const response = verify
      ? await ctx.fetch(
          'hubspot-current-read',
          url.href,
          {
            method: payload === undefined ? 'GET' : 'POST',
            auth: ctx.secrets.bearer(token),
            redirect: 'error',
            headers: {
              'Content-Type': 'application/json',
              'Idempotency-Key':
                'crm-read-' +
                sha256(canonicalJson([true, url.href, payload ?? null])),
            },
            body: payload === undefined ? undefined : canonicalJson(payload),
          },
          { staleAfterSeconds: 0 },
        )
      : await ctx.fetch(
          'hubspot-read',
          url.href,
          {
            method: payload === undefined ? 'GET' : 'POST',
            auth: ctx.secrets.bearer(token),
            redirect: 'error',
            headers: {
              'Content-Type': 'application/json',
              'Idempotency-Key':
                'crm-read-' +
                sha256(canonicalJson([false, url.href, payload ?? null])),
            },
            body: payload === undefined ? undefined : canonicalJson(payload),
          },
          { staleAfterSeconds: 0 },
        );
    return object(response.json, 'HubSpot returned a malformed JSON object');
  }
  const account = await request('/account-info/v3/details');
  if (String(account.portalId ?? '') !== expectedPortalId)
    throw new Error(
      'HubSpot portal mismatch; no schema or CRM records requested',
    );
  return {
    request,
    account,
    portal_id: expectedPortalId,
    observed_at: observedAt,
    finished_at: () =>
      ctx.step(
        'hubspot-completion-clock',
        async () => new Date().toISOString(),
        { semanticKey: ctx.run.id },
      ),
  };
}
export type HubspotReader = Awaited<ReturnType<typeof createHubspotReader>>;
function total(value: unknown): number {
  if (!Number.isSafeInteger(value) || Number(value) < 0)
    throw new Error('Search response omitted a valid total');
  return Number(value);
}
export async function collectCompanies(
  ctx: HubspotContext,
  input: { expected_portal_id: string; properties?: string[] },
) {
  const reader = await createHubspotReader(ctx, input.expected_portal_id);
  const requested = input.properties ?? PROPERTIES;
  if (
    !Array.isArray(requested) ||
    requested.some((p) => typeof p !== 'string' || !p.trim()) ||
    new Set(requested).size !== requested.length
  )
    throw new Error('properties must contain distinct property names');
  const available = new Set(
    rows(
      (await reader.request('/crm/v3/properties/companies')).results,
      'Property schema omitted results',
    ).map((p) => identifier(p.name)),
  );
  const properties = requested.filter((p) => available.has(p)),
    unavailable = requested.filter((p) => !available.has(p));
  const search = { limit: 1, properties: ['name'] };
  const before = total(
    (await reader.request('/crm/v3/objects/companies/search', search)).total,
  );
  const started = reader.observed_at;
  let final: JsonObject | null = null,
    consumed = false;
  const completedManifest = () =>
    ctx.step(
      'hubspot-inventory-manifest',
      async () => {
        if (!final)
          throw new Error(
            'Inventory has not completed; a partial stream is not a verified inventory',
          );
        return final;
      },
      { semanticKey: canonicalJson([ctx.run.id, reader.portal_id, requested]) },
    );
  async function* stream(): AsyncGenerator<JsonObject> {
    if (consumed) throw new Error('Inventory stream is single-use');
    consumed = true;
    const seen = new Set<string>(),
      cursors = new Set<string>(),
      digest = createHash('sha256');
    let after: string | null = null,
      pages = 0;
    do {
      const query = new URLSearchParams({
        limit: '100',
        archived: 'false',
        properties: properties.join(','),
      });
      if (after !== null) query.set('after', after);
      const page = await reader.request(`/crm/v3/objects/companies?${query}`);
      pages++;
      for (const record of rows(
        page.results,
        'Company page omitted result list',
      )) {
        const id = identifier(record.id);
        if (seen.has(id))
          throw new Error(
            'Repeated record across pages; inventory requires reconciliation',
          );
        seen.add(id);
        const rawProperties = object(
          record.properties,
          'Company record omitted properties',
        );
        const item = {
          source_record_id: id,
          properties: Object.fromEntries(
            properties.map((p) => [p, rawProperties[p] ?? null]),
          ),
          source_url: `https://app.hubspot.com/contacts/${encodeURIComponent(reader.portal_id)}/company/${encodeURIComponent(id)}`,
          retrieved_at: reader.observed_at,
        };
        digest.update(canonicalJson(item) + '\n');
        yield item;
      }
      after = cursor(page);
      if (after !== null) {
        if (cursors.has(after)) throw new Error('Repeated pagination cursor');
        cursors.add(after);
      }
    } while (after !== null);
    const countAfter = total(
      (await reader.request('/crm/v3/objects/companies/search', search, true))
        .total,
    );
    final = {
      schema_version: 2,
      classification: 'private_internal_do_not_publish',
      source: 'HubSpot companies; archived=false',
      portal_id: reader.portal_id,
      expected_portal_verified: true,
      started_at: started,
      finished_at: await reader.finished_at(),
      properties,
      unavailable_properties: unavailable,
      records: seen.size,
      pages,
      pagination_exhausted: true,
      search_total_before: before,
      search_total_after: countAfter,
      search_count_matches: before === countAfter && before === seen.size,
      atomic_snapshot: false,
      observation_clock:
        'checkpointed collection-start processing time; not an atomic source snapshot',
      contact_data_collected: false,
      crm_mutations: 0,
      hash_format: HASH_FORMAT,
      sha256: digest.digest('hex'),
    };
    // A resumed map may restore admitted rows without iterating the source.
    // Keep its bounded reconciliation in a durable step before rows can settle.
    await completedManifest();
  }
  return {
    rows: stream(),
    manifest: completedManifest,
  };
}
export function sample_ids(
  ids: unknown[],
  count: number,
  seed: string,
): string[] {
  if (!Number.isSafeInteger(count) || count < 0 || typeof seed !== 'string')
    throw new Error('Invalid sample count or seed');
  return [...new Set(ids.map(identifier))]
    .map((id) => ({ id, rank: sha256(`${seed}:${id}`) }))
    .sort((a, b) =>
      a.rank < b.rank
        ? -1
        : a.rank > b.rank
          ? 1
          : a.id < b.id
            ? -1
            : a.id > b.id
              ? 1
              : 0,
    )
    .slice(0, count)
    .map((r) => r.id);
}
export async function read_objects(
  reader: HubspotReader,
  kind: 'companies' | 'contacts',
  ids: string[],
  fields: string[],
) {
  const result: JsonObject[] = [];
  for (let start = 0; start < ids.length; start += 100) {
    const wanted = ids.slice(start, start + 100),
      response = await reader.request(`/crm/v3/objects/${kind}/batch/read`, {
        inputs: wanted.map((id) => ({ id })),
        properties: fields,
      });
    if (
      (Array.isArray(response.errors)
        ? response.errors.length
        : response.errors) ||
      response.numErrors ||
      response.status !== 'COMPLETE'
    )
      throw new Error('Incomplete batch read; do not infer empty results');
    const batch = rows(response.results, 'Object batch omitted result list');
    const seen = batch.map((row) => identifier(row.id));
    if (
      seen.length !== wanted.length ||
      new Set(seen).size !== wanted.length ||
      seen.some((id) => !wanted.includes(id))
    )
      throw new Error('Object batch did not return the exact requested cohort');
    for (const row of batch) {
      const properties = object(
        row.properties,
        'Object batch omitted properties',
      );
      result.push({
        id: identifier(row.id),
        object_type: kind === 'companies' ? 'company' : 'contact',
        properties: Object.fromEntries(
          fields.map((field) => [field, properties[field] ?? null]),
        ),
        source: { system: 'hubspot', scope_id: reader.portal_id },
        retrieved_at: reader.observed_at,
      });
    }
  }
  return result;
}
export async function associations(
  reader: HubspotReader,
  from: 'companies' | 'contacts',
  to: 'companies' | 'contacts',
  ids: string[],
) {
  const result: JsonObject[] = [];
  for (let start = 0; start < ids.length; start += 100) {
    const wanted = ids.slice(start, start + 100),
      response = await reader.request(
        `/crm/v4/associations/${from}/${to}/batch/read`,
        { inputs: wanted.map((id) => ({ id })) },
      );
    const errors = rows(
      response.errors ?? [],
      'Association response errors must be a list',
    );
    if (
      response.status !== 'COMPLETE' ||
      (response.numErrors ?? 0) !== errors.length
    )
      throw new Error('Incomplete association read');
    const batch = rows(
      response.results,
      'Association response omitted result list',
    );
    for (const error of errors) {
      if (
        error.category !== 'OBJECT_NOT_FOUND' ||
        error.subCategory !== 'crm.associations.NO_ASSOCIATIONS_FOUND'
      )
        throw new Error('Association read returned an unresolved error');
      const sources = object(
        error.context,
        'Unscoped no-associations response',
      ).fromObjectId;
      if (
        !Array.isArray(sources) ||
        sources.length !== 1 ||
        !wanted.includes(String(sources[0]))
      )
        throw new Error('Unscoped no-associations response');
      batch.push({ from: { id: String(sources[0]) }, to: [] });
    }
    const seen = new Set<string>();
    for (const row of batch) {
      const sourceId = identifier(
        object(row.from, 'Association row omitted source').id,
      );
      if (!wanted.includes(sourceId) || seen.has(sourceId))
        throw new Error('Association batch source mismatch or repeated source');
      seen.add(sourceId);
      const targets = rows(row.to, 'Association row omitted edge list');
      let after = cursor(row);
      const cursors = new Set<string>();
      while (after !== null) {
        if (cursors.has(after)) throw new Error('Repeated association cursor');
        cursors.add(after);
        const page = await reader.request(
          `/crm/v4/associations/${from}/${to}/batch/read`,
          { inputs: [{ id: sourceId, after }] },
        );
        const pageErrors = rows(
          page.errors ?? [],
          'Association page errors must be a list',
        );
        if (
          page.status !== 'COMPLETE' ||
          pageErrors.length !== 0 ||
          (page.numErrors ?? 0) !== 0
        )
          throw new Error('Incomplete association continuation');
        const pageRows = rows(
          page.results,
          'Association page omitted result list',
        );
        if (
          pageRows.length !== 1 ||
          identifier(object(pageRows[0].from).id) !== sourceId
        )
          throw new Error('Association continuation source mismatch');
        targets.push(
          ...rows(pageRows[0].to, 'Association page omitted edge list'),
        );
        after = cursor(pageRows[0]);
      }
      const targetIds = targets.map((target) => identifier(target.toObjectId));
      if (new Set(targetIds).size !== targetIds.length)
        throw new Error(
          'Repeated association target across pages; reconcile before sampling',
        );
      result.push({ from_id: sourceId, to: targets });
    }
    if (seen.size !== wanted.length)
      throw new Error('Association read omitted requested source IDs');
  }
  return result;
}
export type SampleInput = {
  expected_portal_id: string;
  inventory: Iterable<JsonObject> | AsyncIterable<JsonObject>;
  inventory_manifest: JsonObject;
  seed: string;
  company_limit?: number;
  contact_limit?: number;
};
export async function sampleHubspot(ctx: HubspotContext, input: SampleInput) {
  const { inventory, inventory_manifest: manifest, seed } = input;
  const companyLimit = input.company_limit ?? 1000,
    contactLimit = input.contact_limit ?? 1000;
  if (
    ![companyLimit, contactLimit].every(
      (n) => Number.isSafeInteger(n) && n >= 1 && n <= 1000,
    ) ||
    typeof seed !== 'string' ||
    !seed
  )
    throw new Error('Sampler requires seed and 1–1000 per object');
  if (manifest.hash_format !== HASH_FORMAT)
    throw new Error(
      'Unsupported inventory hash_format; preserve legacy file hash only as provenance',
    );
  if (
    manifest.pagination_exhausted !== true ||
    manifest.search_count_matches !== true ||
    manifest.expected_portal_verified !== true
  )
    throw new Error('Company inventory is not hash-verified and reconciled');
  if (manifest.portal_id !== input.expected_portal_id)
    throw new Error('Inventory portal mismatch');
  const digestBuilder = createHash('sha256'),
    ids = new Set<string>();
  type RankedId = { id: string; rank: string };
  const cohort: RankedId[] = [];
  const compare = (a: RankedId, b: RankedId) =>
    a.rank < b.rank
      ? -1
      : a.rank > b.rank
        ? 1
        : a.id < b.id
          ? -1
          : a.id > b.id
            ? 1
            : 0;
  // A max-heap retains the lowest hashes without retaining CRM properties.
  function retain(candidate: RankedId) {
    if (cohort.length < companyLimit) {
      cohort.push(candidate);
      let index = cohort.length - 1;
      while (index > 0) {
        const parent = Math.floor((index - 1) / 2);
        if (compare(cohort[parent], cohort[index]) >= 0) break;
        [cohort[parent], cohort[index]] = [cohort[index], cohort[parent]];
        index = parent;
      }
      return;
    }
    if (compare(candidate, cohort[0]) >= 0) return;
    cohort[0] = candidate;
    let index = 0;
    while (true) {
      const left = index * 2 + 1,
        right = left + 1;
      let largest = index;
      if (left < cohort.length && compare(cohort[left], cohort[largest]) > 0)
        largest = left;
      if (right < cohort.length && compare(cohort[right], cohort[largest]) > 0)
        largest = right;
      if (largest === index) break;
      [cohort[index], cohort[largest]] = [cohort[largest], cohort[index]];
      index = largest;
    }
  }
  for await (const row of inventory) {
    const id = identifier(row.source_record_id);
    if (ids.has(id))
      throw new Error('Company inventory count/uniqueness mismatch');
    ids.add(id);
    const url = new URL(row.source_url),
      parts = url.pathname.split('/');
    if (
      url.protocol !== 'https:' ||
      url.hostname !== 'app.hubspot.com' ||
      parts[1] !== 'contacts' ||
      decodeURIComponent(parts[2]) !== input.expected_portal_id ||
      parts[3] !== 'company' ||
      decodeURIComponent(parts[4]) !== id
    )
      throw new Error('Mixed or unverified portal inventory');
    digestBuilder.update(canonicalJson(row) + '\n');
    retain({ id, rank: sha256(`${seed}:companies:${id}`) });
  }
  if (ids.size !== manifest.records)
    throw new Error('Company inventory count/uniqueness mismatch');
  const digest = digestBuilder.digest('hex');
  if (manifest.sha256 !== digest)
    throw new Error('Company inventory is not hash-verified and reconciled');
  const reader = await createHubspotReader(ctx, input.expected_portal_id),
    started = reader.observed_at;
  const fields: Record<string, string[]> = {},
    unavailable: Record<string, string[]> = {};
  for (const [kind, desired] of Object.entries(FIELDS)) {
    const available = new Set(
      rows(
        (await reader.request(`/crm/v3/properties/${kind}`)).results,
        'Property schema omitted results',
      ).map((p) => identifier(p.name)),
    );
    fields[kind] = desired.filter((p) => available.has(p));
    unavailable[kind] = desired.filter((p) => !available.has(p));
  }
  const companyIds = cohort.sort(compare).map((row) => row.id);
  const companies = await read_objects(
    reader,
    'companies',
    companyIds,
    fields.companies,
  );
  const companyContacts = await associations(
    reader,
    'companies',
    'contacts',
    companyIds,
  );
  const eligibleContacts = [
    ...new Set(
      companyContacts.flatMap((row) =>
        row.to.map((target: JsonObject) => identifier(target.toObjectId)),
      ),
    ),
  ];
  const contactIds = sample_ids(
    eligibleContacts,
    contactLimit,
    `${seed}:contacts`,
  );
  const contacts = await read_objects(
    reader,
    'contacts',
    contactIds,
    fields.contacts,
  );
  const contactCompanies = await associations(
    reader,
    'contacts',
    'companies',
    contactIds,
  );
  const hierarchy = await associations(
    reader,
    'companies',
    'companies',
    companyIds,
  );
  const contactMap = new Map(
    contactCompanies.map((row) => [
      row.from_id,
      row.to.map((target: JsonObject) => identifier(target.toObjectId)),
    ]),
  );
  for (const contact of contacts)
    contact.company_ids = contactMap.get(contact.id);
  const labels = await reader.request(
    '/crm/v4/associations/companies/companies/labels',
  );
  rows(labels.results, 'Association labels response omitted results');
  return {
    companies,
    contacts,
    associations: {
      company_contacts: companyContacts,
      contact_companies: contactCompanies,
      company_hierarchy: hierarchy,
      company_hierarchy_labels: labels,
    },
    manifest: {
      classification: 'private_internal_do_not_publish',
      expected_portal_verified: true,
      portal_id: reader.portal_id,
      credential_route: 'workspace_HUBSPOT_API_KEY_verified_against_inventory',
      started_at: started,
      finished_at: await reader.finished_at(),
      atomic_snapshot: false,
      observation_clock:
        'checkpointed collection-start processing time; not an atomic source snapshot',
      inventory_sha256: digest,
      hash_format: HASH_FORMAT,
      inventory_finished_at: manifest.finished_at,
      company_population: ids.size,
      company_sample: companies.length,
      eligible_linked_contacts: eligibleContacts.length,
      contact_sample: contacts.length,
      seed,
      sampling:
        'lowest_SHA256(seed:object:ID); companies from reconciled inventory; contacts conditional on company cohort',
      limitations: [
        'Contact sample excludes contacts not linked to the company cohort',
        'In-sample duplicate candidates are not global CRM duplicate burden',
        'Record modification timestamps do not verify employment freshness',
      ],
      requested_properties: fields,
      unavailable_properties: unavailable,
      crm_mutations: 0,
    },
  };
}
