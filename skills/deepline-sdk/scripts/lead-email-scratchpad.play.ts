import { definePlay } from 'deepline';
import type { ColumnMap, CsvInput, ToolExecuteResult } from 'deepline';

type LeadRow = {
  first_name: string;
  last_name: string;
  company: string;
  domain?: string;
};

type Input = {
  csv: CsvInput<LeadRow>;
  columns?: ColumnMap<LeadRow>;
};

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

type CompanyDomainPayload = {
  domain?: unknown;
};

type EmailPayload = {
  email?: unknown;
};

function extractDomain(result: ToolExecuteResult<CompanyDomainPayload>): string {
  return text(
    result.extractedValues.company_domain?.get?.() ??
      result.toolResponse.raw?.domain,
  );
}

function extractEmail(result: ToolExecuteResult<EmailPayload>): string {
  return text(
    result.extractedValues.email?.get?.() ?? result.toolResponse.raw?.email,
  ).toLowerCase();
}

export default definePlay('lead-email-scratchpad', async (ctx, input: Input) => {
  const leads = await ctx.csv<LeadRow>(input.csv, {
    columns: {
      first_name: 'First Name',
      last_name: 'Last Name',
      company: 'Company',
      domain: 'Domain',
      ...input.columns,
    },
    required: ['first_name', 'last_name', 'company'],
  });

  const withDomains = await ctx
    .map('company_domain_resolution', leads)
    .step('resolved_domain', async (lead, rowCtx) => {
      if (!lead.domain) {
        // Add real company -> domain search here; never invent a domain.
        return null;
      }

      const search = (await rowCtx.tools.execute({
        // Durable domain check; email/validation reuse it.
        id: 'company_domain_search',
        tool: 'test_company_search',
        input: { domain: lead.domain },
        description: 'Verify company domain before email lookup.',
      })) as ToolExecuteResult<CompanyDomainPayload>;

      return extractDomain(search) || lead.domain;
    })
    .run({
      key: (lead) => `${lead.first_name}:${lead.last_name}:${lead.company}`.toLowerCase(),
      description: 'Resolve domains for leads.',
    });

  const withEmails = await ctx
    .map('work_email_enrichment', withDomains)
    .step('work_email', async (lead, rowCtx) => {
      const enrichedLead = lead as LeadRow & { resolved_domain?: string | null };
      const domain = enrichedLead.domain ?? enrichedLead.resolved_domain;
      if (!domain) return null;

      const email = (await rowCtx.tools.execute({
        // Separate checkpoint; validation should not rerun lookup.
        id: 'work_email_lookup',
        tool: 'hunter_email_finder',
        input: {
          first_name: enrichedLead.first_name,
          last_name: enrichedLead.last_name,
          domain,
        },
        description: 'Find work email from name and domain.',
      })) as ToolExecuteResult<EmailPayload>;

      return extractEmail(email) || null;
    })
    .run({
      key: (lead) => `${lead.first_name}:${lead.last_name}:${lead.company}`.toLowerCase(),
      description: 'Find work emails.',
    });

  return { rows: withEmails };
});
