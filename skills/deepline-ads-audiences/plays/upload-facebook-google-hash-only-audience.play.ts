import { definePlay } from 'deepline';
import { prepareHashOnlyUploadRows } from './shared/audience-hash';

type HashOnlyRow = {
  email_sha256?: string;
  email?: string;
};

export default definePlay(
  'ads-audience-upload-facebook-google-hash-only',
  async (
    ctx,
    input: {
      file: string;
      audience_name: string;
      google_account_id?: string;
      google_login_account_id?: string;
      meta_ad_account_id?: string;
      meta_audience_id?: string;
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

    if (!input.google_account_id && !input.meta_ad_account_id) {
      throw new Error(
        'Provide google_account_id, meta_ad_account_id, or both for upload.',
      );
    }

    const google =
      input.google_account_id !== undefined
        ? await (async () => {
            const createResult = await ctx.tools.execute({
              id: 'create_google_audience',
              tool: 'google_ads_audiences_create_audience',
              input: {
                account_id: input.google_account_id,
                login_account_id: input.google_login_account_id,
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
              throw new Error(
                'Google audience create did not return an audience id.',
              );
            }
            const syncResult = await ctx.tools.execute({
              id: 'sync_google_audience_members',
              tool: 'google_ads_audiences_sync_audience_members',
              input: {
                account_id: input.google_account_id,
                login_account_id: input.google_login_account_id,
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
                account_id: input.google_account_id,
                login_account_id: input.google_login_account_id,
                audience_id: audienceId,
              },
              description: 'Read back Google audience status after upload.',
            });
            return {
              audience_id: audienceId,
              create_result: createResult,
              sync_result: syncResult,
              status_result: statusResult,
            };
          })()
        : null;

    const meta =
      input.meta_ad_account_id !== undefined
        ? await (async () => {
            if (!input.meta_audience_id) {
              throw new Error(
                'Meta upload requires meta_audience_id for an existing Custom Audience.',
              );
            }
            const syncResult = await ctx.tools.execute({
              id: 'sync_meta_audience_members',
              tool: 'meta_audiences_sync_audience_members',
              input: {
                ad_account_id: input.meta_ad_account_id,
                audience_id: input.meta_audience_id,
                mode: 'replace',
                rows,
              },
              description:
                'Upload hash-only audience members to an existing Meta Custom Audience.',
            });
            return {
              audience_id: input.meta_audience_id,
              sync_result: syncResult,
            };
          })()
        : null;

    return {
      uploaded_rows: rows.length,
      audit,
      google,
      meta,
    };
  },
);
