import { definePlay } from 'deepline';
import {
  auditHashRows,
  normalizeEmail,
  normalizeSha256,
  sha256Hex,
} from './shared/audience-hash';

type AudienceInputRow = {
  source_row?: string;
  person_id?: string;
  work_email?: string;
  email?: string;
  personal_email?: string;
  personal_emails?: string;
  email_sha256?: string;
  personal_email_sha256?: string;
  hashed_personal_email_sha256?: string;
  personal_email_hashes_sha256?: string;
  email_hashes_sha256?: string;
  aviato_hash?: string;
  limadata_hash?: string;
  first_name?: string;
  last_name?: string;
  company?: string;
  company_name?: string;
  domain?: string;
  company_domain?: string;
  linkedin_url?: string;
  person_linkedin_url?: string;
};

type HashOnlyRow = {
  email_sha256: string;
  source_row?: string;
  provider_used: string;
  identifier_type: 'work_email' | 'provider_hash' | 'personal_email';
};

function firstHash(
  row: AudienceInputRow,
): { hash: string; provider: string } | null {
  const candidates: Array<[string, unknown]> = [
    ['email_sha256', row.email_sha256],
    ['personal_email_sha256', row.personal_email_sha256],
    ['hashed_personal_email_sha256', row.hashed_personal_email_sha256],
    ['aviato_hash', row.aviato_hash],
    ['limadata_hash', row.limadata_hash],
  ];
  for (const [provider, value] of candidates) {
    const hash = normalizeSha256(value);
    if (hash) return { hash, provider };
  }
  return null;
}

function splitMultiValue(value: unknown): string[] {
  if (Array.isArray(value)) return value.flatMap(splitMultiValue);
  if (typeof value !== 'string') return [];
  const trimmed = value.trim();
  if (!trimmed) return [];
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (Array.isArray(parsed)) return parsed.flatMap(splitMultiValue);
  } catch {
    // Not JSON; fall through to delimiter split.
  }
  return trimmed
    .split(/[;,|\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function allProviderHashes(row: AudienceInputRow): Array<{
  hash: string;
  provider: string;
}> {
  const scalar = firstHash(row);
  const output = scalar ? [scalar] : [];
  const multiCandidates: Array<[string, unknown]> = [
    ['personal_email_hashes_sha256', row.personal_email_hashes_sha256],
    ['email_hashes_sha256', row.email_hashes_sha256],
  ];
  for (const [provider, value] of multiCandidates) {
    for (const item of splitMultiValue(value)) {
      const hash = normalizeSha256(item);
      if (hash) output.push({ hash, provider });
    }
  }
  const seen = new Set<string>();
  return output.filter(({ hash }) => {
    if (seen.has(hash)) return false;
    seen.add(hash);
    return true;
  });
}

function personalEmails(row: AudienceInputRow): string[] {
  const output = [
    row.personal_email,
    ...splitMultiValue(row.personal_emails),
  ].flatMap((value) => {
    const normalized = normalizeEmail(value);
    return normalized ? [normalized] : [];
  });
  return [...new Set(output)];
}

function sourceRow(row: AudienceInputRow, index: number): string {
  return String(row.source_row || row.person_id || index);
}

function dedupe(rows: HashOnlyRow[]): HashOnlyRow[] {
  const seen = new Set<string>();
  const output: HashOnlyRow[] = [];
  for (const row of rows) {
    if (seen.has(row.email_sha256)) continue;
    seen.add(row.email_sha256);
    output.push(row);
  }
  return output;
}

export default definePlay(
  'ads-audience-build-hash-only',
  async (ctx, input: { file: string }) => {
    const dataset = await ctx.csv<AudienceInputRow>(input.file);
    const rows = await dataset.materialize();
    const baseline: HashOnlyRow[] = [];
    const enriched: HashOnlyRow[] = [];

    rows.forEach((row, index) => {
      const rowId = sourceRow(row, index);
      const workEmail = normalizeEmail(row.work_email || row.email);
      if (workEmail) {
        const hash = sha256Hex(workEmail);
        baseline.push({
          email_sha256: hash,
          source_row: rowId,
          provider_used: 'work_email',
          identifier_type: 'work_email',
        });
        enriched.push({
          email_sha256: hash,
          source_row: rowId,
          provider_used: 'work_email',
          identifier_type: 'work_email',
        });
      }

      for (const providerHash of allProviderHashes(row)) {
        enriched.push({
          email_sha256: providerHash.hash,
          source_row: rowId,
          provider_used: providerHash.provider,
          identifier_type: 'provider_hash',
        });
      }

      for (const personalEmail of personalEmails(row)) {
        enriched.push({
          email_sha256: sha256Hex(personalEmail),
          source_row: rowId,
          provider_used: 'personal_email',
          identifier_type: 'personal_email',
        });
      }
    });

    const baselineRows = dedupe(baseline);
    const enrichedRows = dedupe(enriched);
    const baselineAudit = auditHashRows(baselineRows);
    const enrichedAudit = auditHashRows(enrichedRows);

    const baselineDataset = await ctx
      .dataset('baseline_hash_only_audience', baselineRows)
      .run({ description: 'Baseline work-email hash-only audience rows.' });
    const enrichedDataset = await ctx
      .dataset('enriched_hash_only_audience', enrichedRows)
      .run({ description: 'Enriched hash-only audience rows.' });

    return {
      baseline_rows: baselineDataset,
      enriched_rows: enrichedDataset,
      baseline_audit: baselineAudit,
      enriched_audit: enrichedAudit,
      unique_hash_lift: enrichedAudit.outputRows - baselineAudit.outputRows,
    };
  },
);
