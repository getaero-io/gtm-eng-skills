import { definePlay } from 'deepline';
import { classify_company_url } from './shared/domain-policy';
import { readRecords, recordRows } from './shared/io';

export default definePlay(
  'crm-classify-company-domains',
  async (ctx, input: { records_file: string }) => {
    const records = await readRecords(
      await ctx.csv<{ record_json: string }>(input.records_file),
    );
    const results = records.map((row) => ({
      ...row,
      classification: classify_company_url(row.url, row.context),
    }));
    return {
      record_count: records.length,
      classifications: await ctx
        .dataset('classifications', recordRows(results, ctx.run.id))
        .run({ key: 'row_id' }),
      crm_mutations: 0,
    };
  },
  {
    description:
      'Classify company URLs and separate official-domain candidates from social, map, directory and service URLs.',
  },
);
