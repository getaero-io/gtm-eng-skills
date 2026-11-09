import { definePlay } from 'deepline';
import { COMPANY_MAX_RECORDS } from './shared/company-candidates';
import { score_companies_with_jev } from './shared/identity-evaluation';
import { recordStream, recordRows } from './shared/io';
import type { JsonObject } from './shared/json';

export default definePlay(
  'crm-score-company-candidates',
  async (
    ctx,
    input: {
      records_file: string;
      name_similarity_threshold?: number;
      max_evaluations?: number;
    },
  ) => {
    const records: JsonObject[] = [];
    for await (const record of recordStream(
      await ctx.csv<{ record_json: string }>(input.records_file),
    )) {
      if (records.length === COMPANY_MAX_RECORDS)
        throw new Error(
          `Company candidate scoring accepts at most ${COMPANY_MAX_RECORDS} records; no rows were silently dropped`,
        );
      records.push(record);
    }
    const result = await score_companies_with_jev(
      ctx,
      records,
      input.name_similarity_threshold,
      input.max_evaluations,
    );
    return {
      record_count: result.metadata.record_count,
      pair_space: result.metadata.pair_space,
      generated_pair_count: result.metadata.generated_pair_count,
      candidate_group_count: result.metadata.candidate_group_count,
      unassessed_pair_count: result.metadata.unassessed_pair_count,
      inventory: await ctx
        .dataset('company_inventory', recordRows(result.inventory, ctx.run.id))
        .run({ key: 'row_id' }),
      pair_groups: await ctx
        .dataset(
          'company_candidate_groups',
          recordRows(result.pair_groups, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      metadata: await ctx
        .dataset(
          'company_candidate_metadata',
          recordRows([result.metadata], ctx.run.id),
        )
        .run({ key: 'row_id' }),
      crm_mutations: 0,
      identity_judgments: await ctx
        .dataset(
          'company_identity_judgments',
          recordRows(result.judgments, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      auto_merge_allowed: false,
    };
  },
  {
    description:
      'Retrieve company review candidates with Jev name-variant judgments and eligible domains. Preserve diagnostic name scores without merging or inferring hierarchy.',
  },
);
