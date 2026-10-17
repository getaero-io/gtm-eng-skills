import { definePlay } from 'deepline';
import {
  COMPANY_MAX_RECORDS,
  score_company_candidates,
} from './shared/company-candidates';
import { recordStream, recordRows } from './shared/io';
import type { JsonObject } from './shared/json';

export default definePlay(
  'crm-score-company-candidates',
  async (
    ctx,
    input: { records_file: string; name_similarity_threshold?: number },
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
    const result = score_company_candidates(
      records,
      input.name_similarity_threshold === undefined
        ? undefined
        : { name_similarity_threshold: input.name_similarity_threshold },
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
      auto_merge_allowed: false,
    };
  },
  {
    description:
      'Score up to 1,000 companies with Jaro-Winkler name similarity and eligible domains. Retain review candidates and unresolved coverage without merging or inferring hierarchy.',
  },
);
