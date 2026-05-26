import { definePlay, steps, when } from 'deepline';
import type { ToolExecuteResult } from 'deepline';

type Lead = {
  first_name: string;
  last_name: string;
  domain: string;
};

type EmailRow = Lead & {
  hunter_email?: string | null;
  leadmagic_email?: string | null;
  icypeas_email?: string | null;
};

function clean(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim().toLowerCase() : null;
}

type EmailPayload = {
  email?: unknown;
};

function extractEmail(result: ToolExecuteResult<EmailPayload>): string | null {
  return clean(
    result.extractedValues.email?.get?.() ?? result.toolResponse.raw?.email,
  );
}

function workEmailSteps<T extends Lead>() {
  return steps<T>()
    .step('hunter_email', async (row: EmailRow, ctx) => {
      const result = (await ctx.tools.execute({
        // Stable checkpoint; later providers depend on this miss.
        id: 'hunter_email',
        tool: 'hunter_email_finder',
        input: {
          first_name: row.first_name,
          last_name: row.last_name,
          domain: row.domain,
        },
        description: 'Find work email with Hunter.',
      })) as ToolExecuteResult<EmailPayload>;

      return extractEmail(result);
    })
    .step(
      'leadmagic_email',
      when(
        (row: EmailRow) => row.hunter_email == null,
        async (row: EmailRow, ctx) => {
          const result = (await ctx.tools.execute({
            id: 'leadmagic_email',
            tool: 'leadmagic_email_finder',
            input: {
              first_name: row.first_name,
              last_name: row.last_name,
              domain: row.domain,
              company_domain: row.domain,
            },
            description: 'Find work email with LeadMagic.',
          })) as ToolExecuteResult<EmailPayload>;

          return extractEmail(result);
        },
      ),
    )
    .step(
      'icypeas_email',
      when(
        (row: EmailRow) => row.hunter_email == null && row.leadmagic_email == null,
        async (row: EmailRow, ctx) => {
          const result = (await ctx.tools.execute({
            id: 'icypeas_email',
            tool: 'icypeas_email_search',
            input: {
              firstname: row.first_name,
              lastname: row.last_name,
              domainOrCompany: row.domain,
            },
            description: 'Find work email with Icypeas.',
          })) as ToolExecuteResult<EmailPayload>;

          return extractEmail(result);
        },
      ),
    )
    .return(
      (row: EmailRow) =>
        row.hunter_email ?? row.leadmagic_email ?? row.icypeas_email ?? null,
    );
}

export default definePlay('work-email-helper-waterfall', async (ctx, input: Lead) => {
  const rows = await ctx
    .map('one_work_email_lookup', [input])
    .step('email', workEmailSteps<Lead>())
    .run({
      key: () => `${input.first_name}:${input.last_name}:${input.domain}`.toLowerCase(),
      description: 'Resolve one work email with explicit provider checkpoints.',
    });

  const [row] = await rows.materialize(1);
  return { email: row?.email ?? null };
});
