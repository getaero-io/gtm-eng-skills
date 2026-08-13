import { definePlay } from 'deepline';
import { normalizeEmail, normalizeSha256, sha256Hex } from './shared/audience-hash';

/**
 * Personal-identifier waterfall for paid-ads audiences.
 *
 * The rule that makes this a waterfall rather than a fan-out: each layer runs
 * only on rows that still have no usable hash. A row covered by an earlier,
 * cheaper layer is never sent to a later, dearer one.
 *
 * Skipping that rule is expensive in a way that looks fine in the logs. Every
 * call still returns 200, so the run reads as healthy while paying several
 * providers for the same person.
 *
 * ContactOut is the deliberate exception. Its response is an unattributed pool
 * of hashes with no mapping back to input rows, so it cannot skip rows another
 * provider covered and later providers cannot skip rows it covered. It runs as
 * a bulk pass over everyone with a LinkedIn URL. See
 * shared/contactout-hash-pool.md.
 */

const CONTACTOUT_MAX_BATCH = 100;
const CONTACTOUT_MIN_BATCH = 5;

type SourceRow = {
  external_id?: string;
  first_name?: string;
  last_name?: string;
  company_name?: string;
  company_domain?: string;
  work_email?: string;
  person_linkedin_url?: string;
  linkedin_url?: string;
  // Any hash an earlier layer already wrote. These are the column names the
  // other plays in this skill read and write.
  email_sha256?: string;
  personal_email_sha256?: string;
  hashed_personal_email_sha256?: string;
  personal_email_hashes_sha256?: string;
  email_hashes_sha256?: string;
  aviato_hash?: string;
  limadata_hash?: string;
};

type EnrichedRow = SourceRow & {
  personal_hash: string | null;
  hash_source: string | null;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object'
    ? (value as Record<string, unknown>)
    : {};
}

/** ctx.tools.execute returns a wrapper; the provider body sits under toolResponse.raw. */
function raw(result: unknown): Record<string, unknown> {
  const wrapped = asRecord(result);
  return asRecord(
    asRecord(wrapped.toolResponse).raw ??
      asRecord(wrapped.tool_response).raw ??
      asRecord(wrapped.toolOutput).raw ??
      wrapped.raw ??
      wrapped.data ??
      result,
  );
}

/**
 * Any personal hash this row already carries, from any earlier layer.
 *
 * This list has to match what the sibling plays write, or a covered row reads
 * as uncovered and gets sent through paid providers a second time. See
 * firstHash in build-hash-only-audience.play.ts.
 */
function existingHash(row: SourceRow): string | null {
  for (const candidate of [
    row.email_sha256,
    row.personal_email_sha256,
    row.hashed_personal_email_sha256,
    row.aviato_hash,
    row.limadata_hash,
    row.personal_email_hashes_sha256,
    row.email_hashes_sha256,
  ]) {
    const hash = normalizeSha256(candidate);
    if (hash) return hash;
  }
  return null;
}

/**
 * Validate on the parsed hostname, not a substring.
 *
 * A substring check accepts `https://evil.example/linkedin.com/in/person`.
 * LimaData and ContactOut would reject that later, but LeadMagic's schema only
 * requires a string, so a malformed row becomes a paid miss.
 */
function readLinkedInUrl(row: SourceRow): string | null {
  const value = row.person_linkedin_url ?? row.linkedin_url;
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  let parsed: URL;
  try {
    parsed = new URL(trimmed.startsWith('http') ? trimmed : `https://${trimmed}`);
  } catch {
    return null;
  }
  const host = parsed.hostname.toLowerCase();
  if (host !== 'linkedin.com' && !host.endsWith('.linkedin.com')) return null;
  if (!/^\/(in|pub)\/[^/]+/i.test(parsed.pathname)) return null;
  return `${parsed.origin}${parsed.pathname.replace(/\/+$/, '')}`;
}

/**
 * Every hash a provider returned, not just the first.
 *
 * Aviato returns `hashedEmails[]` and LimaData returns `hashed_emails[]`, one
 * entry per address it knows for that person. The call is already paid for, so
 * taking only the first discards coverage that costs nothing more to keep. A
 * person with several personal addresses gets several chances to match.
 */
function readProviderHashes(result: unknown): string[] {
  const body = raw(result);
  const data = asRecord(body.data ?? body);
  const found: string[] = [];
  const push = (value: unknown) => {
    const hash = normalizeSha256(value);
    if (hash && !found.includes(hash)) found.push(hash);
  };

  for (const candidate of [
    data.hashed_email,
    data.normalized_hash,
    data.hash,
    data.sha256,
    asRecord(data.matched_result).hash,
  ]) {
    push(candidate);
  }
  if (Array.isArray(data.hashedEmails)) {
    for (const entry of data.hashedEmails) push(entry);
  }
  if (Array.isArray(data.hashed_emails)) {
    for (const entry of data.hashed_emails) {
      const record = asRecord(entry);
      push(record.normalized_hash ?? record.hash ?? entry);
    }
  }
  return found;
}

/** First hash only, for deciding whether a layer covered a row. */
function readProviderHash(result: unknown): string | null {
  return readProviderHashes(result)[0] ?? null;
}

/**
 * Pull a raw personal email and hash it once.
 *
 * Only fields explicitly typed as personal count. An untyped trailing email can
 * be a work address, and uploading one as a personal hash quietly pollutes the
 * audience with an identifier the platform already failed to match.
 */
function readPersonalEmailHashes(result: unknown): string[] {
  const body = raw(result);
  const data = asRecord(body.data ?? body);
  const found: string[] = [];
  const push = (value: unknown) => {
    const email = normalizeEmail(value);
    if (!email) return;
    const hash = sha256Hex(email);
    if (!found.includes(hash)) found.push(hash);
  };

  push(data.personal_email);
  push(data.first_personal_email);
  if (Array.isArray(data.personal_emails)) {
    for (const entry of data.personal_emails) push(entry);
  }
  return found;
}

function readPersonalEmailHash(result: unknown): string | null {
  return readPersonalEmailHashes(result)[0] ?? null;
}

function chunkProfiles(profiles: string[]): string[][] {
  const chunks: string[][] = [];
  for (let i = 0; i < profiles.length; i += CONTACTOUT_MAX_BATCH) {
    chunks.push(profiles.slice(i, i + CONTACTOUT_MAX_BATCH));
  }
  // ContactOut rejects a call with fewer than 5 profiles, so a short tail chunk
  // borrows from the one before it rather than failing the batch.
  if (chunks.length > 1) {
    const last = chunks[chunks.length - 1];
    if (last.length < CONTACTOUT_MIN_BATCH) {
      const previous = chunks[chunks.length - 2];
      const needed = CONTACTOUT_MIN_BATCH - last.length;
      chunks[chunks.length - 1] = [
        ...previous.splice(previous.length - needed, needed),
        ...last,
      ];
    }
  }
  return chunks;
}

export default definePlay(
  'ads-audience-enrich-waterfall',
  async (
    ctx,
    input: {
      file: string;
      /** Buy raw personal emails for rows the hash layers missed. Costs more per row. */
      includeRawEmailFallback?: boolean;
      /** Run the ContactOut bulk pass. Needs LinkedIn URLs. */
      includeContactOut?: boolean;
      /** Send already-covered rows to ContactOut too, for max coverage. */
      contactOutIncludeCoveredRows?: boolean;
    },
  ) => {
    const dataset = await ctx.csv<SourceRow>(input.file);
    const sourceRows = await dataset.materialize();

    const rows: EnrichedRow[] = sourceRows.map((row) => {
      const hash = existingHash(row);
      return {
        ...row,
        personal_hash: hash,
        hash_source: hash ? 'source_csv' : null,
      };
    });

    const stats: Array<{
      layer: string;
      attempted: number;
      hits: number;
      skipped_already_covered: number;
    }> = [];

    // Each layer is a dataset column with runIf, so the runtime maps rows in
    // parallel instead of a serial per-row loop, and runIf is what makes this a
    // waterfall: a row already carrying a hash is skipped without a provider
    // call. A serial loop over a few thousand rows would also be thousands of
    // sequential round trips.
    const enriched = await ctx
      .dataset('audience_rows', rows)
      .withColumn('aviato_result', {
        // Aviato takes identifier fields only and is additionalProperties:false,
        // so name and domain cannot be sent. Seed with a LinkedIn URL or an email.
        runIf: (row) =>
          !row.personal_hash &&
          Boolean(readLinkedInUrl(row) || normalizeEmail(row.work_email)),
        run: ({ row, ctx: rowCtx }) => {
          const linkedinUrl = readLinkedInUrl(row);
          const workEmail = normalizeEmail(row.work_email);
          return rowCtx.tools.execute({
            id: 'aviato_hash',
            tool: 'aviato_pull_email_hash',
            input: (linkedinUrl
              ? { linkedinURL: linkedinUrl }
              : { email: workEmail }) as never,
            description: 'Pull a hashed personal email for one contact',
          });
        },
      })
      .withColumn('limadata_result', {
        // LimaData accepts linkedin_url and work_email only.
        runIf: (row) =>
          !row.personal_hash &&
          !readProviderHash((row as Record<string, unknown>).aviato_result) &&
          Boolean(readLinkedInUrl(row) || normalizeEmail(row.work_email)),
        run: ({ row, ctx: rowCtx }) => {
          const linkedinUrl = readLinkedInUrl(row);
          const workEmail = normalizeEmail(row.work_email);
          return rowCtx.tools.execute({
            id: 'limadata_hash',
            tool: 'limadata_find_audience_identifiers',
            input: {
              ...(linkedinUrl ? { linkedin_url: linkedinUrl } : {}),
              ...(workEmail ? { work_email: workEmail } : {}),
            } as never,
            description: 'Find hashed audience identifiers for one contact',
          });
        },
      })
      .withColumn('leadmagic_result', {
        // The dearest layer, so it is opt-in and only sees rows the hash layers
        // missed. LeadMagic takes exactly one required field, profile_url.
        runIf: (row) =>
          Boolean(input.includeRawEmailFallback) &&
          !row.personal_hash &&
          !readProviderHash((row as Record<string, unknown>).aviato_result) &&
          !readProviderHash((row as Record<string, unknown>).limadata_result) &&
          Boolean(readLinkedInUrl(row)),
        run: ({ row, ctx: rowCtx }) =>
          rowCtx.tools.execute({
            id: 'leadmagic_personal_email',
            tool: 'leadmagic_personal_email_finder',
            input: { profile_url: readLinkedInUrl(row) } as never,
            description: 'Find a raw personal email for one contact',
          }),
      })
      .run({ description: 'Personal-identifier waterfall, cheapest layer first' });

    const enrichedRows = await enriched.materialize();

    // Fold each layer's result into the row, cheapest source winning.
    for (const row of enrichedRows as unknown as Array<
      EnrichedRow & Record<string, unknown>
    >) {
      if (row.personal_hash) continue;
      const aviato = readProviderHash(row.aviato_result);
      if (aviato) {
        row.personal_hash = aviato;
        row.hash_source = 'aviato';
        continue;
      }
      const lima = readProviderHash(row.limadata_result);
      if (lima) {
        row.personal_hash = lima;
        row.hash_source = 'limadata';
        continue;
      }
      const leadmagic = readPersonalEmailHash(row.leadmagic_result);
      if (leadmagic) {
        row.personal_hash = leadmagic;
        row.hash_source = 'leadmagic_personal_email';
      }
    }

    const layerRows = enrichedRows as unknown as Array<
      EnrichedRow & Record<string, unknown>
    >;
    for (const [layer, column] of [
      ['aviato_hash', 'aviato_result'],
      ['limadata_hash', 'limadata_result'],
      ['leadmagic_personal_email', 'leadmagic_result'],
    ] as const) {
      const attempted = layerRows.filter(
        (row) => row[column] !== null && row[column] !== undefined,
      ).length;
      const hits = layerRows.filter(
        (row) => row.hash_source === layer.replace('_hash', ''),
      ).length;
      stats.push({
        layer,
        attempted,
        hits,
        skipped_already_covered: layerRows.length - attempted,
      });
    }

    rows.length = 0;
    rows.push(...(layerRows as unknown as EnrichedRow[]));

    // --- ContactOut: bulk pass, not a waterfall step -----------------------
    // Deliberately not filtered on coverage by default. The response is an
    // unattributed pool, so its hashes join the audience-level pool rather than
    // per-row cells, and it is recommended for everyone with a LinkedIn URL.
    const contactOutHashes = new Set<string>();
    let contactOutMatched = 0;
    let contactOutSent = 0;
    if (input.includeContactOut) {
      const seen = new Set<string>();
      const profiles: string[] = [];
      for (const row of rows) {
        const url = readLinkedInUrl(row);
        if (!url) continue;
        if (!input.contactOutIncludeCoveredRows && row.hash_source === 'source_csv') {
          // Rows that arrived already hashed are the one cheap exclusion: they
          // were covered before this run started. Rows covered by a layer above
          // still go, because ContactOut often returns a second address for a
          // person another provider already matched.
          continue;
        }
        const key = url.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        profiles.push(url);
      }

      if (profiles.length >= CONTACTOUT_MIN_BATCH) {
        contactOutSent = profiles.length;
        for (const chunk of chunkProfiles(profiles)) {
          const result = await ctx.tools.execute({
            id: 'contactout_hashes',
            tool: 'contactout_get_hashed_email_identifiers',
            input: { profiles: chunk } as never,
            description: 'Hash a batch of LinkedIn profiles into email identifiers',
          });
          const body = raw(result);
          const emails = asRecord(body.matches).emails;
          if (Array.isArray(emails)) {
            for (const value of emails) {
              const hash = normalizeSha256(value);
              if (hash) contactOutHashes.add(hash);
            }
          }
          const found = asRecord(body).matches_found;
          if (typeof found === 'number' && Number.isInteger(found) && found > 0) {
            contactOutMatched += found;
          }
        }
      }
    }

    const perRowHashes = rows
      .map((row) => row.personal_hash)
      .filter((hash): hash is string => Boolean(hash));
    const pool = new Set(perRowHashes);

    // Providers often return several addresses for one person. The row keeps
    // one hash for lineage, but every hash bought belongs in the audience pool:
    // more addresses per person means more chances a platform matches them, and
    // these cost nothing beyond the call already made.
    for (const row of layerRows) {
      for (const extra of [
        ...readProviderHashes(row.aviato_result),
        ...readProviderHashes(row.limadata_result),
        ...readPersonalEmailHashes(row.leadmagic_result),
      ]) {
        pool.add(extra);
      }
    }
    const contactOutNetNew = [...contactOutHashes].filter(
      (hash) => !pool.has(hash),
    );
    for (const hash of contactOutHashes) pool.add(hash);

    return {
      source_rows: rows.length,
      rows_with_hash: perRowHashes.length,
      rows_still_missing: rows.length - perRowHashes.length,
      layers: stats,
      contactout: {
        profiles_sent: contactOutSent,
        matched_profiles: contactOutMatched,
        hashes_returned: contactOutHashes.size,
        net_new_hashes: contactOutNetNew.length,
      },
      audience_hash_pool_size: pool.size,
      // Slim, hash-only rows. The dataset carries a full tool envelope per
      // provider per row, and the LeadMagic envelope holds the raw personal
      // email this play otherwise only ever hashes. Returning those rows
      // verbatim would leak purchased personal emails into the play output and
      // could also cross the output-size ceiling on a few thousand rows.
      enriched_rows: rows.map((row) => ({
        external_id: row.external_id ?? null,
        company_domain: row.company_domain ?? null,
        person_linkedin_url: readLinkedInUrl(row),
        personal_hash: row.personal_hash,
        hash_source: row.hash_source,
      })),
      audience_hash_pool: [...pool],
    };
  },
  {
    description:
      'Enrich a contact list for paid ads audiences: cheap hash layers first, each running only on rows still missing a hash, with ContactOut as a bulk pass over everyone with a LinkedIn URL.',
  },
);
