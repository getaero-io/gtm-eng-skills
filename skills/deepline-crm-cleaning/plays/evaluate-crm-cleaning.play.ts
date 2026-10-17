import { definePlay } from 'deepline';
import {
  evaluate,
  validate_receipts,
  type ArtifactEvidence,
} from './shared/evaluate';
import { readRecords, recordRows } from './shared/io';
import schema from './schemas/receipt.schema.json';
import { Buffer } from './shared/native';
import type { JsonObject } from './shared/json';

export default definePlay(
  'crm-evaluate-cleaning',
  async (
    ctx,
    input: {
      mode: 'evaluate' | 'validate_receipts';
      predictions_file: string;
      inputs_file?: string;
      labels_file?: string;
      artifacts_file?: string;
    },
  ) => {
    if (!['evaluate', 'validate_receipts'].includes(input.mode))
      throw new Error('Unsupported evaluation mode');
    if (input.mode === 'evaluate' && (!input.inputs_file || !input.labels_file))
      throw new Error('Evaluation requires inputs_file and labels_file');
    if (
      input.mode === 'validate_receipts' &&
      (input.inputs_file || input.labels_file)
    )
      throw new Error(
        'Receipt validation does not accept labels or case inputs',
      );
    const predictions = await readRecords(
      await ctx.csv<{ record_json: string }>(input.predictions_file),
    );
    let artifacts: ArtifactEvidence | undefined;
    if (input.artifacts_file) {
      artifacts = Object.create(null) as ArtifactEvidence;
      const rows = await readRecords(
        await ctx.csv<{ record_json: string }>(input.artifacts_file),
      );
      for (const row of rows) {
        if (
          typeof row.ref !== 'string' ||
          typeof row.content_base64 !== 'string' ||
          Object.hasOwn(artifacts, row.ref)
        )
          throw new Error(
            'Artifacts require unique ref and content_base64 strings',
          );
        const bytes = Buffer.from(row.content_base64, 'base64');
        if (bytes.toString('base64') !== row.content_base64)
          throw new Error('Artifact content requires canonical base64');
        artifacts[row.ref] = bytes;
      }
    }
    let report;
    if (input.mode === 'validate_receipts') {
      report = validate_receipts(predictions, schema, artifacts);
    } else {
      const inputs = await readRecords(
        await ctx.csv<{ record_json: string }>(input.inputs_file!),
      );
      const labels = await readRecords(
        await ctx.csv<{ record_json: string }>(input.labels_file!),
      );
      report = evaluate(inputs, labels, predictions, schema, artifacts);
    }
    const { case_results, results, failures, ...summary } = report;
    return {
      passed: report.passed,
      artifact_validation_mode: report.artifact_validation_mode,
      summary: await ctx
        .dataset('evaluation_summary', recordRows([summary], ctx.run.id))
        .run({ key: 'row_id' }),
      cases: await ctx
        .dataset(
          'evaluation_cases',
          recordRows(case_results ?? results, ctx.run.id),
        )
        .run({ key: 'row_id' }),
      failures: await ctx
        .dataset(
          'evaluation_failures',
          recordRows(
            failures ??
              results.flatMap((result: JsonObject) =>
                result.errors.map((error: JsonObject) => ({
                  case_id: result.case_id,
                  ...error,
                })),
              ),
            ctx.run.id,
          ),
        )
        .run({ key: 'row_id' }),
      live_crm_verified: false,
      crm_mutations: 0,
    };
  },
  {
    description:
      'Grade frozen CRM receipts or validate receipt contracts, retaining failures and missing-prediction coverage.',
  },
);
