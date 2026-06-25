import { definePlay } from 'deepline';
import { prepareHashOnlyUploadRows } from './shared/audience-hash';

type HashOnlyRow = {
  email_sha256?: string;
  email?: string;
};

export default definePlay(
  'ads-audience-upload-google-hash-only',
  async (
    ctx,
    input: {
      file: string;
      account_id: string;
      audience_name: string;
      login_account_id?: string;
      description?: string;
      validate_only?: boolean;
    },
  ) => {
    const sourceDataset = await ctx.csv<HashOnlyRow>(input.file);
    const sourceRows = (await sourceDataset.materialize()) as HashOnlyRow[];
    const { rows, audit } = prepareHashOnlyUploadRows(sourceRows);
    if (
      rows.length === 0 ||
      audit.malformedHashes > 0 ||
      audit.duplicateHashes > 0 ||
      audit.rawEmailFieldsPresent
    ) {
      throw new Error(
        JSON.stringify({
          message: 'Hash-only audience payload did not pass validation.',
          audit,
        }),
      );
    }

    const createResult = await ctx.tools.execute({
      id: 'create_google_audience',
      tool: 'google_ads_audiences_create_audience',
      input: {
        account_id: input.account_id,
        login_account_id: input.login_account_id,
        name: input.audience_name,
        description: input.description,
        membership_life_span_days: 540,
        membership_status: 'OPEN',
        upload_key_types: ['CONTACT_ID'],
        validate_only: input.validate_only === true,
      },
      description: 'Create a Google Customer Match audience.',
    });

    const audienceId = String(
      (createResult as { data?: { audience?: { id?: unknown } } }).data
        ?.audience?.id ?? '',
    );
    if (!audienceId) {
      throw new Error('Google audience create did not return an audience id.');
    }

    const syncResult = await ctx.tools.execute({
      id: 'sync_google_audience_members',
      tool: 'google_ads_audiences_sync_audience_members',
      input: {
        account_id: input.account_id,
        login_account_id: input.login_account_id,
        audience_id: audienceId,
        mode: 'append',
        rows,
        consent: {
          ad_user_data: 'GRANTED',
          ad_personalization: 'GRANTED',
        },
        encoding: 'HEX',
        validate_only: input.validate_only === true,
        terms_of_service_accepted: true,
      },
      description: 'Upload hash-only audience members to Google.',
    });

    const statusResult = await ctx.tools.execute({
      id: 'get_google_audience_status',
      tool: 'google_ads_audiences_get_audience_status',
      input: {
        account_id: input.account_id,
        login_account_id: input.login_account_id,
        audience_id: audienceId,
      },
      description: 'Read back Google audience status after upload.',
    });

    return {
      audience_id: audienceId,
      uploaded_rows: rows.length,
      audit,
      create_result: createResult,
      sync_result: syncResult,
      status_result: statusResult,
    };
  },
);
