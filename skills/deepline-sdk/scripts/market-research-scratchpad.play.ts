import { definePlay } from 'deepline';
import type { ToolExecuteResult } from 'deepline';

type Input = {
  target_domains?: string[];
};

type Company = {
  name: string;
  domain: string;
};

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

type CompanySearchPayload = {
  name?: unknown;
  company_name?: unknown;
  domain?: unknown;
};

type PositioningPayload = {
  what_they_sell?: unknown;
  buyer?: unknown;
};

function companyFromSearch(
  result: ToolExecuteResult<CompanySearchPayload>,
  fallbackDomain: string,
): Company | null {
  const data = result.toolResponse.raw ?? {};
  const domain = text(data.domain) || fallbackDomain;
  const name = text(data.name ?? data.company_name) || domain;
  return domain ? { name, domain } : null;
}

export default definePlay('market-research-scratchpad', async (ctx, input: Input = {}) => {
  const targets = (input.target_domains?.length ? input.target_domains : ['stripe.com', 'brex.com'])
    .map((domain) => ({ domain }))
    .slice(0, 10);

  const searched = await ctx
    .map('target_company_search', targets)
    .step('company', async (target, rowCtx) => {
      const search = (await rowCtx.tools.execute({
        // Durable search; later stages build on it.
        id: 'company_search',
        tool: 'test_company_search',
        input: { domain: target.domain },
        description: 'Search for the target company by domain.',
      })) as ToolExecuteResult<CompanySearchPayload>;

      return companyFromSearch(search, target.domain);
    })
    .run({
      // Business key; new rows compute without redoing old rows.
      key: 'domain',
      description: 'Search target companies.',
    });

  const researched = await ctx
    .map('company_research', searched)
    .step('positioning', async (row, rowCtx) => {
      const company = row.company;
      if (!company) return null;

      const research = (await rowCtx.tools.execute({
        // New checkpoint; search should not rerun.
        id: 'positioning_research',
        tool: 'deeplineagent',
        input: {
          model: 'openai/gpt-5.4-mini',
          prompt: `Using verifiable context, summarize what ${company.name} (${company.domain}) sells and who buys it.`,
          jsonSchema: {
            type: 'object',
            properties: {
              what_they_sell: { type: 'string' },
              buyer: { type: 'string' },
            },
            required: ['what_they_sell', 'buyer'],
            additionalProperties: false,
          },
        },
        description: 'Summarize company positioning.',
      })) as ToolExecuteResult<PositioningPayload>;

      return research.toolResponse.raw;
    })
    .run({
      key: 'domain',
      description: 'Research searched companies.',
    });

  return { rows: researched };
});
