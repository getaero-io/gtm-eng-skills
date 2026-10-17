import { definePlay } from 'deepline';
import { sampleHubspot } from './shared/hubspot';
import { recordStream, readDocument, recordRows } from './shared/io';

export default definePlay(
  'crm-sample-hubspot-crm',
  async (
    ctx,
    input: {
      expected_portal_id: string;
      inventory_file: string;
      manifest_file: string;
      seed: string;
      company_limit?: number;
      contact_limit?: number;
    },
  ) => {
    const inventory = recordStream(
      await ctx.csv<{ record_json: string }>(input.inventory_file),
    );
    const inventory_manifest = await readDocument(
      await ctx.csv<{ record_json: string }>(input.manifest_file),
    );
    const result = await sampleHubspot(ctx, {
      ...input,
      inventory,
      inventory_manifest,
    });
    return {
      company_count: result.companies.length,
      contact_count: result.contacts.length,
      companies: await ctx
        .dataset('sample_companies', recordRows(result.companies, ctx.run.id))
        .run({ key: 'row_id' }),
      contacts: await ctx
        .dataset('sample_contacts', recordRows(result.contacts, ctx.run.id))
        .run({ key: 'row_id' }),
      company_contacts: await ctx
        .dataset(
          'company_contacts',
          recordRows(result.associations.company_contacts, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      contact_companies: await ctx
        .dataset(
          'contact_companies',
          recordRows(result.associations.contact_companies, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      company_hierarchy: await ctx
        .dataset(
          'company_hierarchy',
          recordRows(result.associations.company_hierarchy, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      hierarchy_labels: await ctx
        .dataset(
          'hierarchy_labels',
          recordRows(
            result.associations.company_hierarchy_labels.results,
            ctx.run.id,
          ),
        )
        .run({ key: 'row_id' }),
      manifest: await ctx
        .dataset('sample_manifest', recordRows([result.manifest], ctx.run.id))
        .run({ key: 'row_id' }),
      crm_mutations: 0,
    };
  },
  {
    description:
      'Collect a reproducible HubSpot company cohort with fully paginated associated contacts and portal checks.',
    secrets: ['HUBSPOT_API_KEY'],
  },
);
