import { definePlay } from 'deepline';
import { resolve_contacts_with_jev } from './shared/identity-evaluation';
import { readRecords, recordRows, objectJson } from './shared/io';

export default definePlay(
  'crm-resolve-contact-duplicates',
  async (
    ctx,
    input: {
      records_file: string;
      policy_json?: string;
      max_evaluations?: number;
    },
  ) => {
    const records = await readRecords(
      await ctx.csv<{ record_json: string }>(input.records_file),
    );
    const result = await resolve_contacts_with_jev(
      ctx,
      records,
      input.policy_json
        ? objectJson(input.policy_json, 'policy_json')
        : undefined,
      input.max_evaluations,
    );
    const { pairs, pair_count, clusters, record_ids, ...metadata } = result;
    return {
      record_count: records.length,
      pair_count,
      cluster_count: clusters.length,
      record_inventory: await ctx
        .dataset(
          'record_inventory',
          recordRows(
            record_ids.map((record_id: string) => ({ record_id })),
            ctx.run.id,
          ),
        )
        .run({ key: 'row_id' }),
      pairs: await ctx
        .dataset('pairs', recordRows(pairs, ctx.run.id))
        .run({ key: 'row_id' }),
      clusters: await ctx
        .dataset(
          'clusters',
          recordRows(
            clusters.map((ids: string[], index: number) => ({
              cluster_id: String(index),
              record_ids: ids,
            })),
            ctx.run.id,
          ),
        )
        .run({ key: 'row_id' }),
      metadata: await ctx
        .dataset('duplicate_metadata', recordRows([metadata], ctx.run.id))
        .run({ key: 'row_id' }),
      crm_mutations: 0,
    };
  },
  {
    description:
      'Use Jev to compare contact identities, including name variants and shared inboxes, and quarantine conflicting groups. Return proposals without CRM mutations.',
  },
);
