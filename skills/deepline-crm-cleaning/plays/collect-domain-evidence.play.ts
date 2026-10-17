import { definePlay } from 'deepline';
import { collectDomain, redact_domain_input } from './shared/collect-domains';
import { readRecords } from './shared/io';
import { canonicalJson } from './shared/json';

export default definePlay(
  'crm-collect-domain-evidence',
  async (
    ctx,
    input: {
      domains_file: string;
      max_domains?: number;
      timeout?: number;
      max_bytes?: number;
      max_legal_pages?: number;
      max_redirects?: number;
    },
  ) => {
    const maxDomains = input.max_domains ?? 1000;
    if (!Number.isSafeInteger(maxDomains) || maxDomains < 1)
      throw new Error('max_domains must be a positive safe integer');
    const domains = await readRecords(
      await ctx.csv<{ record_json: string }>(input.domains_file),
    );
    if (domains.length > maxDomains)
      throw new Error('Domain row count exceeds max_domains');
    if (domains.some((row) => typeof row.domain !== 'string'))
      throw new Error('Each domain row requires a domain string');
    const evidence = await ctx
      .dataset(
        'domain_evidence',
        domains.map((row, index) => {
          const sanitized = redact_domain_input(row.domain as string);
          return {
            row_id: `${ctx.run.id}:${index}`,
            source_index: index,
            domain: sanitized.value,
            domain_input_state: sanitized.state,
          };
        }),
      )
      .withColumn('record_json', async (row, rowCtx) =>
        canonicalJson(
          await collectDomain(
            rowCtx,
            domains[row.source_index].domain as string,
            input,
          ),
        ),
      )
      .run({ key: 'row_id' });
    return { domain_count: domains.length, evidence, crm_mutations: 0 };
  },
  {
    description:
      'Collect DNS, MX, website, redirect and legal-page evidence through guarded runtime requests.',
  },
);
