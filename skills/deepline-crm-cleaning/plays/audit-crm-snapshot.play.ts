import { definePlay } from 'deepline';
import { audit } from './shared/audit';
import { readRecords, recordRows, objectJson } from './shared/io';

export default definePlay(
  'crm-audit-snapshot',
  async (
    ctx,
    input: {
      records_file: string;
      as_of: string;
      company_population_complete?: boolean;
      stale_days?: number;
      source_lag_hours?: number;
      required_fields_json?: string;
    },
  ) => {
    const records = await readRecords(
      await ctx.csv<{ record_json: string }>(input.records_file),
    );
    const result = await audit(records, input.as_of, {
      company_population_complete: input.company_population_complete,
      stale_days: input.stale_days,
      source_lag_hours: input.source_lag_hours,
      required_fields: input.required_fields_json
        ? objectJson(input.required_fields_json, 'required_fields_json')
        : undefined,
    });
    return {
      record_count: records.length,
      summary: await ctx
        .dataset('audit_summary', recordRows([result.summary], ctx.run.id))
        .run({ key: 'row_id' }),
      normalized: await ctx
        .dataset(
          'normalized_records',
          recordRows(result.normalized, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      issues: await ctx
        .dataset('issues', recordRows(result.issues, ctx.run.id))
        .run({ key: 'row_id' }),
      candidates: await ctx
        .dataset(
          'duplicate_candidates',
          recordRows(result.candidates, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      crm_mutations: 0,
    };
  },
  {
    description:
      'Audit observed CRM fields, missing values, staleness, associations and duplicate candidates.',
  },
);
