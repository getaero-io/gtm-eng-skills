import { definePlay } from 'deepline';
import { normalizeEmail } from './shared/audience-hash';

type SourceRow = {
  contact_id: string;
  first_name?: string;
  last_name?: string;
  linkedin_url?: string;
  account_name?: string;
  domain?: string;
  title?: string;
  lead_score?: string;
};

type EvaluatedRow = SourceRow & {
  provider: 'leadmagic_personal_email_finder';
  personal_emails: string;
  personal_email_count: number;
  accepted: boolean;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object'
    ? (value as Record<string, unknown>)
    : {};
}

function raw(result: unknown): Record<string, unknown> {
  const wrapped = asRecord(result);
  return asRecord(asRecord(wrapped.toolResponse).raw ?? wrapped);
}

function extractPersonalEmails(result: unknown): string[] {
  const data = raw(result);
  const candidates = [
    data.personal_email,
    data.first_personal_email,
    ...(Array.isArray(data.personal_emails) ? data.personal_emails : []),
  ];
  return [
    ...new Set(
      candidates
        .map((value) => normalizeEmail(value))
        .filter((email): email is string => Boolean(email)),
    ),
  ];
}

export default definePlay(
  'ads-audience-leadmagic-eval',
  async (
    ctx,
    input: {
      file: string;
      limit?: number;
    },
  ) => {
    const rows = (await ctx.csv<SourceRow>(input.file))
      .filter((row) => Boolean(row.contact_id && row.linkedin_url))
      .slice(0, Math.max(1, Math.min(input.limit ?? 25, 500)));
    const rowCount = await rows.count();

    const evaluated = await ctx
      .dataset('leadmagic_eval', rows)
      .withColumn('leadmagic_result', (row, rowCtx) =>
        rowCtx.tools.execute({
          id: 'leadmagic_personal_email_finder',
          tool: 'leadmagic_personal_email_finder',
          input: { profile_url: String(row.linkedin_url) },
          description:
            'Evaluate LeadMagic personal-email finder for one remaining ads-audience miss.',
        }),
      )
      .withColumn('evaluated', (row) => {
        const emails = extractPersonalEmails(row.leadmagic_result);
        return {
          ...row,
          provider: 'leadmagic_personal_email_finder',
          personal_emails: emails.join(';'),
          personal_email_count: emails.length,
          accepted: emails.length > 0,
        } satisfies EvaluatedRow;
      })
      .run({
        key: 'contact_id',
        description:
          'Evaluate LeadMagic personal-email finder on remaining paid-audience misses.',
      });

    const previewRows = (await evaluated.materialize(500)) as Array<{
      evaluated?: EvaluatedRow;
    }>;
    const rowsOut = previewRows
      .map((row) => row.evaluated)
      .filter((row): row is EvaluatedRow => Boolean(row));
    const hitRows = rowsOut.filter((row) => row.accepted);

    return {
      provider: 'leadmagic_personal_email_finder',
      attempted_rows: rowCount,
      validated_contacts: hitRows.length,
      validated_personal_emails: hitRows.reduce(
        (sum, row) => sum + row.personal_email_count,
        0,
      ),
      hit_rate_pct: rowCount === 0 ? 0 : (hitRows.length * 100) / rowCount,
      deepline_usd_per_result: 0.068,
      estimated_deepline_cost_per_incremental_validated_contact: 0.068,
      evaluated_rows: evaluated,
    };
  },
);
