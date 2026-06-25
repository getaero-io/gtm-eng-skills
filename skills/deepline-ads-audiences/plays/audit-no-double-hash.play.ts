import { definePlay } from 'deepline';
import {
  auditHashRows,
  normalizeSha256,
  sha256Hex,
} from './shared/audience-hash';

type HashRow = Record<string, string | undefined>;

function collectHashes(row: HashRow, columns: string[]): string[] {
  const hashes: string[] = [];
  for (const column of columns) {
    const hash = normalizeSha256(row[column]);
    if (hash) hashes.push(hash);
  }
  return hashes;
}

export default definePlay(
  'ads-audience-audit-no-double-hash',
  async (
    ctx,
    input: {
      payloadFile: string;
      providerHashFile: string;
      providerHashColumns?: string[];
    },
  ) => {
    const payloadDataset = await ctx.csv<HashRow>(input.payloadFile);
    const providerDataset = await ctx.csv<HashRow>(input.providerHashFile);
    const payloadRows = await payloadDataset.materialize();
    const providerRows = await providerDataset.materialize();
    const providerHashColumns = input.providerHashColumns ?? [
      'email_sha256',
      'personal_email_sha256',
      'hashed_personal_email_sha256',
      'aviato_hash',
      'limadata_hash',
    ];

    const payloadHashes = new Set(
      payloadRows
        .map((row) => normalizeSha256(row.email_sha256))
        .filter((hash): hash is string => Boolean(hash)),
    );
    const providerHashes = new Set<string>();
    providerRows.forEach((row) => {
      collectHashes(row, providerHashColumns).forEach((hash) =>
        providerHashes.add(hash),
      );
    });

    const missingProviderHashes = Array.from(providerHashes).filter(
      (hash) => !payloadHashes.has(hash),
    );
    const doubleHashedProviderHashes = Array.from(providerHashes)
      .map((hash) => sha256Hex(hash))
      .filter((hash) => payloadHashes.has(hash));
    const audit = auditHashRows(payloadRows);

    const ok =
      audit.malformedHashes === 0 &&
      audit.duplicateHashes === 0 &&
      audit.rawEmailFieldsPresent === false &&
      missingProviderHashes.length === 0 &&
      doubleHashedProviderHashes.length === 0;

    if (!ok) {
      throw new Error(
        JSON.stringify({
          message: 'Audience hash audit failed.',
          audit,
          provider_hashes: providerHashes.size,
          missing_provider_hashes: missingProviderHashes.length,
          double_hashed_provider_hashes: doubleHashedProviderHashes.length,
          missing_provider_hash_examples: missingProviderHashes.slice(0, 5),
          double_hashed_provider_hash_examples:
            doubleHashedProviderHashes.slice(0, 5),
        }),
      );
    }

    return {
      ok: true,
      audit,
      provider_hashes: providerHashes.size,
      missing_provider_hashes: 0,
      double_hashed_provider_hashes: 0,
    };
  },
);
