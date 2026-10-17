import { definePlay } from 'deepline';
import { collectCompanies } from './shared/hubspot';
import { recordRows } from './shared/io';

export default definePlay(
  'crm-collect-hubspot-companies',
  async (ctx, input: { expected_portal_id: string; properties?: string[] }) => {
    const inventory = await collectCompanies(ctx, input);
    const companies = await ctx
      .dataset('company_inventory', recordRows(inventory.rows, ctx.run.id))
      .run({ key: 'row_id' });
    const manifest = await inventory.manifest();
    return {
      companies,
      manifest: await ctx
        .dataset('inventory_manifest', recordRows([manifest], ctx.run.id))
        .run({ key: 'row_id' }),
      crm_mutations: 0,
    };
  },
  {
    description:
      'Read and reconcile a complete HubSpot company inventory from a verified portal.',
    secrets: ['HUBSPOT_API_KEY'],
  },
);
