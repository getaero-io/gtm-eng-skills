import { definePlay } from 'deepline';
import { normalizeEmail, sha256Hex } from './shared/audience-hash';

type SourceRow = {
  contact_id: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  linkedin_url?: string;
  work_email?: string;
  account_name?: string;
  domain?: string;
  title?: string;
  lead_score?: string;
};

type ProviderName =
  | 'leadmagic_personal_email_finder'
  | 'crustdata_v2_enrich_person'
  | 'contactout_enrich_person'
  | 'datagma_full_enrichment'
  | 'enformion_person_search'
  | 'fullenrich_bulk_enrich'
  | 'limadata_find_personal_email'
  | 'lusha_enrich_person'
  | 'wiza_reveal_person';

type EvaluatedRow = SourceRow & {
  provider: ProviderName;
  validated_personal_email_hashes_sha256: string;
  validated_hash_count: number;
  candidate_email_count: number;
  accepted: boolean;
  rejection_reason?: string;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object'
    ? (value as Record<string, unknown>)
    : {};
}

function raw(result: unknown): Record<string, unknown> {
  const wrapped = asRecord(result);
  return asRecord(
    asRecord(wrapped.toolResponse).raw ??
      asRecord(wrapped.tool_response).raw ??
      wrapped.raw ??
      result,
  );
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function arrayValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function hashEmails(emails: string[]): string[] {
  return [...new Set(emails.map((email) => sha256Hex(email)))];
}

function emailsFromCandidates(candidates: unknown[]): string[] {
  return [
    ...new Set(
      candidates
        .map((value) => normalizeEmail(stringValue(value)))
        .filter((email): email is string => Boolean(email)),
    ),
  ];
}

function collectValuesByKey(value: unknown, keyMatcher: RegExp): unknown[] {
  if (Array.isArray(value)) {
    return value.flatMap((item) => collectValuesByKey(item, keyMatcher));
  }
  if (!value || typeof value !== 'object') return [];
  const output: unknown[] = [];
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    if (keyMatcher.test(key)) output.push(child);
    output.push(...collectValuesByKey(child, keyMatcher));
  }
  return output;
}

function flattenValues(values: unknown[]): unknown[] {
  const output: unknown[] = [];
  for (const value of values) {
    if (Array.isArray(value)) output.push(...flattenValues(value));
    else output.push(value);
  }
  return output;
}

function leadmagicEmails(result: unknown): string[] {
  const data = raw(result);
  return emailsFromCandidates([
    data.personal_email,
    data.first_personal_email,
    ...arrayValue(data.personal_emails),
  ]);
}

function crustdataPersonalEmails(result: unknown): string[] {
  const data = raw(result);
  const rows = Array.isArray(data) ? data : [data, objectValue(data.data)];
  const candidates = rows.flatMap((row) => {
    const contact = objectValue(objectValue(row).personal_contact_info);
    return arrayValue(contact.personal_emails);
  });
  return emailsFromCandidates(candidates);
}

function contactoutPersonalEmails(result: unknown): string[] {
  const data = raw(result);
  return emailsFromCandidates([
    data.personal_email,
    ...arrayValue(data.personal_email),
  ]);
}

function datagmaPersonalEmails(result: unknown): string[] {
  const data = raw(result);
  return emailsFromCandidates(
    flattenValues(collectValuesByKey(data, /personal.*email|email.*personal/i)),
  );
}

function enformionPersonalEmails(result: unknown): string[] {
  const data = raw(result);
  const candidates: unknown[] = [];
  for (const person of arrayValue(data.persons)) {
    for (const email of arrayValue(objectValue(person).emailAddresses)) {
      const row = objectValue(email);
      if (row.nonBusiness === 1 || row.nonBusiness === true) {
        candidates.push(row.emailAddress);
      }
    }
  }
  return emailsFromCandidates(candidates);
}

function fullenrichPersonalEmails(result: unknown): string[] {
  const data = raw(result);
  return emailsFromCandidates(
    flattenValues(collectValuesByKey(data, /personal.*email/i)),
  );
}

function lushaPersonalEmails(result: unknown): string[] {
  const data = raw(result);
  const output: string[] = [];
  for (const item of [
    ...arrayValue(data.emails),
    ...arrayValue(data.emailAddresses),
  ]) {
    const row = asRecord(item);
    const type = String(row.type ?? row.emailType ?? '').toLowerCase();
    const email = normalizeEmail(stringValue(row.email));
    if (email && /personal|private|home/.test(type)) output.push(email);
  }
  return [...new Set(output)];
}

function wizaPersonalEmails(result: unknown): string[] {
  const data = raw(result);
  return emailsFromCandidates([
    data.personal_email,
    data.personal_email1,
    data.personal_email2,
    data.personal_email3,
    ...arrayValue(data.personal_emails),
  ]);
}

function providerInput(provider: ProviderName, row: SourceRow): Record<string, unknown> {
  if (provider === 'leadmagic_personal_email_finder') {
    return { profile_url: row.linkedin_url };
  }
  if (provider === 'crustdata_v2_enrich_person') {
    return {
      linkedin_profile_url: row.linkedin_url,
      fields: 'personal_contact_info.personal_emails',
    };
  }
  if (provider === 'contactout_enrich_person') {
    return {
      linkedin_url: row.linkedin_url,
      include: ['personal_email'],
    };
  }
  if (provider === 'datagma_full_enrichment') {
    return {
      data: row.linkedin_url || row.work_email,
      fullName:
        row.full_name ||
        [row.first_name, row.last_name].filter(Boolean).join(' '),
      company: row.account_name || row.domain,
    };
  }
  if (provider === 'enformion_person_search') {
    return {
      first_name: row.first_name,
      last_name: row.last_name,
    };
  }
  if (provider === 'fullenrich_bulk_enrich') {
    return {
      name: `ads-audience-personal-email-${row.contact_id}`,
      wait_for_completion: true,
      max_wait_ms: 120000,
      data: [
        {
          first_name: row.first_name,
          last_name: row.last_name,
          domain: row.domain,
          company_name: row.account_name,
          linkedin_url: row.linkedin_url,
          enrich_fields: ['contact.personal_emails'],
          custom: { contact_id: row.contact_id },
        },
      ],
    };
  }
  if (provider === 'limadata_find_personal_email') {
    return {
      linkedin_url: row.linkedin_url,
      work_email: row.work_email,
    };
  }
  if (provider === 'lusha_enrich_person') {
    return {
      linkedin_url: row.linkedin_url,
      first_name: row.first_name,
      last_name: row.last_name,
      company_name: row.account_name,
      company_domain: row.domain,
      reveal_emails: true,
      reveal_phones: false,
    };
  }
  return {
    linkedin_url: row.linkedin_url,
    full_name:
      row.full_name ||
      [row.first_name, row.last_name].filter(Boolean).join(' '),
    company_name: row.account_name,
    company_domain: row.domain,
    enrichment_level: 'partial',
  };
}

function providerDescription(provider: ProviderName): string {
  return `Evaluate ${provider} personal emails for one remaining ads-audience miss.`;
}

function extractEmails(provider: ProviderName, result: unknown): string[] {
  if (provider === 'leadmagic_personal_email_finder') {
    return leadmagicEmails(result);
  }
  if (provider === 'crustdata_v2_enrich_person') {
    return crustdataPersonalEmails(result);
  }
  if (provider === 'contactout_enrich_person') {
    return contactoutPersonalEmails(result);
  }
  if (provider === 'datagma_full_enrichment') {
    return datagmaPersonalEmails(result);
  }
  if (provider === 'enformion_person_search') {
    return enformionPersonalEmails(result);
  }
  if (provider === 'fullenrich_bulk_enrich') {
    return fullenrichPersonalEmails(result);
  }
  if (provider === 'limadata_find_personal_email') {
    return emailsFromCandidates(arrayValue(raw(result).emails));
  }
  if (provider === 'lusha_enrich_person') {
    return lushaPersonalEmails(result);
  }
  return wizaPersonalEmails(result);
}

export default definePlay(
  'ads-audience-provider-eval',
  async (
    ctx,
    input: {
      file: string;
      provider: ProviderName;
      limit?: number;
    },
  ) => {
    const rows = (await ctx.csv<SourceRow>(input.file))
      .filter((row) => Boolean(row.contact_id && row.linkedin_url))
      .slice(0, Math.max(1, Math.min(input.limit ?? 25, 500)));
    const rowCount = await rows.count();

    const evaluated = await ctx
      .dataset('eval_rows', rows)
      .withColumn('provider_result', (row, rowCtx) => {
        if (input.provider === 'leadmagic_personal_email_finder') {
          return rowCtx.tools.execute({
            id: 'leadmagic_personal_email_finder',
            tool: 'leadmagic_personal_email_finder',
            input: providerInput(input.provider, row) as never,
            description: providerDescription(input.provider),
          }) as Promise<unknown>;
        }
        if (input.provider === 'crustdata_v2_enrich_person') {
          return rowCtx.tools.execute({
            id: 'crustdata_v2_enrich_person',
            tool: 'crustdata_v2_enrich_person',
            input: providerInput(input.provider, row) as never,
            description: providerDescription(input.provider),
          }) as Promise<unknown>;
        }
        if (input.provider === 'contactout_enrich_person') {
          return rowCtx.tools.execute({
            id: 'contactout_enrich_person',
            tool: 'contactout_enrich_person',
            input: providerInput(input.provider, row) as never,
            description: providerDescription(input.provider),
          }) as Promise<unknown>;
        }
        if (input.provider === 'datagma_full_enrichment') {
          return rowCtx.tools.execute({
            id: 'datagma_full_enrichment',
            tool: 'datagma_full_enrichment',
            input: providerInput(input.provider, row) as never,
            description: providerDescription(input.provider),
          }) as Promise<unknown>;
        }
        if (input.provider === 'enformion_person_search') {
          return rowCtx.tools.execute({
            id: 'enformion_person_search',
            tool: 'enformion_person_search',
            input: providerInput(input.provider, row) as never,
            description: providerDescription(input.provider),
          }) as Promise<unknown>;
        }
        if (input.provider === 'fullenrich_bulk_enrich') {
          return rowCtx.tools.execute({
            id: 'fullenrich_bulk_enrich',
            tool: 'fullenrich_bulk_enrich',
            input: providerInput(input.provider, row) as never,
            description: providerDescription(input.provider),
          }) as Promise<unknown>;
        }
        if (input.provider === 'limadata_find_personal_email') {
          return rowCtx.tools.execute({
            id: 'limadata_find_personal_email',
            tool: 'limadata_find_personal_email',
            input: providerInput(input.provider, row) as never,
            description: providerDescription(input.provider),
          }) as Promise<unknown>;
        }
        if (input.provider === 'lusha_enrich_person') {
          return rowCtx.tools.execute({
            id: 'lusha_enrich_person',
            tool: 'lusha_enrich_person',
            input: providerInput(input.provider, row) as never,
            description: providerDescription(input.provider),
          }) as Promise<unknown>;
        }
        return rowCtx.tools.execute({
          id: 'wiza_reveal_person',
          tool: 'wiza_reveal_person',
          input: providerInput(input.provider, row) as never,
          description: providerDescription(input.provider),
        }) as Promise<unknown>;
      })
      .withColumn('evaluated', (row) => {
        const emails = extractEmails(input.provider, row.provider_result);
        const hashes = hashEmails(emails);
        return {
          ...row,
          provider: input.provider,
          validated_personal_email_hashes_sha256: hashes.join(';'),
          validated_hash_count: hashes.length,
          candidate_email_count: emails.length,
          accepted: hashes.length > 0,
          rejection_reason: hashes.length
            ? undefined
            : 'no_valid_personal_email',
        } satisfies EvaluatedRow;
      })
      .run({
        key: 'contact_id',
        description:
          'Evaluate one personal-email provider on remaining paid-audience misses.',
      });

    const outputRows = (await evaluated.materialize(500)) as Array<{
      evaluated?: EvaluatedRow;
    }>;
    const rowsOut = outputRows
      .map((row) => row.evaluated)
      .filter((row): row is EvaluatedRow => Boolean(row));
    const hitRows = rowsOut.filter((row) => row.accepted);
    const hashes = new Set(
      hitRows.flatMap((row) =>
        row.validated_personal_email_hashes_sha256
          .split(';')
          .filter(Boolean),
      ),
    );

    return {
      provider: input.provider,
      attempted_rows: rowCount,
      validated_contacts: hitRows.length,
      validated_hashes: hashes.size,
      hit_rate_pct:
        rowCount === 0 ? 0 : (hitRows.length * 100) / rowCount,
      evaluated_rows: evaluated,
    };
  },
);
