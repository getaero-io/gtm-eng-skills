import { definePlay } from 'deepline';
import { plan_records } from './shared/domain-repairs';
import { readRecords, recordRows } from './shared/io';

export default definePlay(
  'crm-plan-domain-repairs',
  async (
    ctx,
    input: {
      records_file: string;
      candidates_file: string;
      contexts_file?: string;
    },
  ) => {
    const records = await readRecords(
      await ctx.csv<{ record_json: string }>(input.records_file),
    );
    const candidates = await readRecords(
      await ctx.csv<{ record_json: string }>(input.candidates_file),
    );
    const contexts = input.contexts_file
      ? await readRecords(
          await ctx.csv<{ record_json: string }>(input.contexts_file),
        )
      : [];
    const result = plan_records(records, candidates, contexts);
    return {
      record_count: records.length,
      before_after: await ctx
        .dataset('before_after', recordRows(result.before_after, ctx.run.id))
        .run({ key: 'row_id' }),
      proposed_records: await ctx
        .dataset(
          'proposed_records',
          recordRows(result.proposed_records, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      metrics: await ctx
        .dataset('repair_metrics', recordRows([result.metrics], ctx.run.id))
        .run({ key: 'row_id' }),
      crm_mutations: 0,
    };
  },
  {
    description:
      'Propose evidence-supported website replacements and show before and after without changing the CRM.',
  },
);
