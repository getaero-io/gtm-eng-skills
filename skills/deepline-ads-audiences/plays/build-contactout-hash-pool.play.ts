import { definePlay } from 'deepline';
import { normalizeSha256 } from './shared/audience-hash';

/**
 * ContactOut's hashed identifiers endpoint returns an unattributed pool of
 * email hashes for a batch of LinkedIn URLs. It does not say which hash belongs
 * to which profile, so the output is an audience-level hash pool rather than
 * per-row enrichment.
 *
 * Contract details that drive this play:
 * - 5-100 unique LinkedIn URLs per call; fewer than 5 is rejected with HTTP 400
 * - one matched profile can return several hashes, so the hash count overstates
 *   matches; `matches_found` is the exact matched-profile count
 * - a chunk where nothing matches returns HTTP 404 "No hashed emails found",
 *   which is a normal empty result rather than a failure
 */

const CONTACTOUT_MAX_BATCH = 100;
const CONTACTOUT_MIN_BATCH = 5;

type SourceRow = {
  linkedin_url?: string;
  person_linkedin_url?: string;
  // Any column an earlier hash layer may have written. aviato_hash and
  // limadata_hash are the names the other plays in this skill use.
  existing_hash?: string;
  email_sha256?: string;
  personal_email_sha256?: string;
  hashed_personal_email_sha256?: string;
  aviato_hash?: string;
  limadata_hash?: string;
};

type ChunkResult = {
  chunk_index: number;
  profiles_sent: number;
  matches_found: number;
  hashes_returned: number;
  status: 'matched' | 'no_match';
};

function readLinkedInUrl(row: SourceRow): string | null {
  const raw = row.person_linkedin_url ?? row.linkedin_url;
  if (typeof raw !== 'string') return null;
  const trimmed = raw.trim().replace(/\/+$/, '').split('?')[0];
  if (!trimmed) return null;
  return /linkedin\.com\/(in|pub)\//i.test(trimmed) ? trimmed : null;
}

/**
 * Read any personal-email hash an earlier layer already wrote for this row.
 *
 * The column names matter. The hash providers in this skill write into named
 * per-provider columns (`aviato_hash`, `limadata_hash`), which is also what the
 * sibling build-hash-only and audit plays read. A filter that only checked
 * `existing_hash`/`email_sha256` would find nothing on a real CSV from this
 * workflow and would silently send every already-covered row to ContactOut.
 */
function readExistingHash(row: SourceRow): string | null {
  const candidates: Array<unknown> = [
    row.existing_hash,
    row.email_sha256,
    row.personal_email_sha256,
    row.hashed_personal_email_sha256,
    row.aviato_hash,
    row.limadata_hash,
  ];
  for (const candidate of candidates) {
    const hash = normalizeSha256(candidate);
    if (hash) return hash;
  }
  return null;
}

function chunkProfiles(profiles: string[]): string[][] {
  const chunks: string[][] = [];
  for (let i = 0; i < profiles.length; i += CONTACTOUT_MAX_BATCH) {
    chunks.push(profiles.slice(i, i + CONTACTOUT_MAX_BATCH));
  }
  // ContactOut rejects a call with fewer than 5 profiles. If the final chunk is
  // short, pull profiles back from the previous chunk so both stay valid.
  if (chunks.length > 1) {
    const last = chunks[chunks.length - 1];
    if (last.length < CONTACTOUT_MIN_BATCH) {
      const previous = chunks[chunks.length - 2];
      const needed = CONTACTOUT_MIN_BATCH - last.length;
      chunks[chunks.length - 1] = [...previous.splice(previous.length - needed, needed), ...last];
    }
  }
  return chunks;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object'
    ? (value as Record<string, unknown>)
    : {};
}

/**
 * ctx.tools.execute returns a wrapper, not the provider body. The provider
 * response sits under toolResponse.raw. Reading the wrapper root returns
 * nothing, which would report zero hashes after a call that already spent
 * credits.
 */
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

function readHashes(result: unknown): string[] {
  const emails = asRecord(raw(result).matches).emails;
  if (!Array.isArray(emails)) return [];
  return emails
    .map((value) => normalizeSha256(value))
    .filter((value): value is string => Boolean(value));
}

function readMatchesFound(result: unknown): number {
  const count = raw(result).matches_found;
  return typeof count === 'number' && Number.isInteger(count) && count > 0
    ? count
    : 0;
}

export default definePlay(
  'ads-audience-contactout-hash-pool',
  async (
    ctx,
    input: {
      file: string;
      limit?: number;
      /**
       * Send every row with a LinkedIn URL, including rows that already carry a
       * hash from an earlier provider.
       *
       * Off by default, which suits a cost-effective pass: those rows often
       * resolve to hashes the pool already has, and ContactOut bills per
       * matched profile whether or not the hash is new.
       *
       * Turn it on for max-coverage runs. Roughly a third of what ContactOut
       * returns is a second or third address for a person it already matched
       * (measured live: 228 matched profiles returned 313 hashes). Excluding a
       * row because it has an Aviato or LimaData hash forfeits any different
       * address ContactOut would have found for that same person, and more
       * addresses per person means more chances a platform matches them.
       */
      includeRowsWithExistingHash?: boolean;
    },
  ) => {
    const dataset = await ctx.csv<SourceRow>(input.file);
    const allRows = await dataset.materialize();

    const existingPool = new Set<string>();
    const profiles: string[] = [];
    const seenProfiles = new Set<string>();
    let skippedAlreadyHashed = 0;
    let skippedNoLinkedIn = 0;

    for (const row of allRows) {
      const existing = readExistingHash(row);
      if (existing) existingPool.add(existing);

      const url = readLinkedInUrl(row);
      if (!url) {
        skippedNoLinkedIn += 1;
        continue;
      }

      // The response is an unattributed pool, so coverage cannot be reconciled
      // per row after the call. Filtering the send set on what we already know
      // is the only saving available.
      if (existing && !input.includeRowsWithExistingHash) {
        skippedAlreadyHashed += 1;
        continue;
      }

      const key = url.toLowerCase();
      if (seenProfiles.has(key)) continue;
      seenProfiles.add(key);
      profiles.push(url);
    }

    const limited =
      typeof input.limit === 'number' && input.limit > 0
        ? profiles.slice(0, input.limit)
        : profiles;

    // Too few profiles to call ContactOut. This is a normal outcome, not a
    // failure: it usually means the earlier hash layers already covered the
    // list, which is the result you wanted. Throwing here would fail an
    // audience build for succeeding. Return an empty contribution and let the
    // caller see why.
    if (limited.length < CONTACTOUT_MIN_BATCH) {
      return {
        source_rows: allRows.length,
        unique_profiles_sent: 0,
        skipped_already_hashed: skippedAlreadyHashed,
        skipped_no_linkedin_url: skippedNoLinkedIn,
        excluded_rows_may_hold_additional_addresses: skippedAlreadyHashed > 0,
        chunks: 0,
        matched_profiles: 0,
        hashes_returned: 0,
        existing_pool_hashes: existingPool.size,
        net_new_hashes: 0,
        chunk_results: [],
        net_new_hash_pool: [],
        skipped_reason: `Only ${limited.length} eligible profiles after filtering, below the ${CONTACTOUT_MIN_BATCH}-profile minimum. Nothing was sent and nothing was billed.`,
      };
    }

    const chunks = chunkProfiles(limited);
    const chunkResults: ChunkResult[] = [];
    const contactoutHashes = new Set<string>();
    let matchedProfiles = 0;

    for (const [index, chunk] of chunks.entries()) {
      const result = await ctx.tools.execute({
        id: 'contactout_hashes',
        tool: 'contactout_get_hashed_email_identifiers',
        input: { profiles: chunk } as never,
        description: 'Hash a batch of LinkedIn profiles into email identifiers',
      });

      const hashes = readHashes(result);
      const found = readMatchesFound(result);
      for (const hash of hashes) contactoutHashes.add(hash);
      matchedProfiles += found;

      chunkResults.push({
        chunk_index: index,
        profiles_sent: chunk.length,
        matches_found: found,
        hashes_returned: hashes.length,
        status: hashes.length > 0 ? 'matched' : 'no_match',
      });
    }

    const netNew = [...contactoutHashes].filter(
      (hash) => !existingPool.has(hash),
    );

    return {
      source_rows: allRows.length,
      unique_profiles_sent: limited.length,
      skipped_already_hashed: skippedAlreadyHashed,
      skipped_no_linkedin_url: skippedNoLinkedIn,
      // Those skipped rows may still have had a second personal address that
      // ContactOut would have found. Re-run with includeRowsWithExistingHash
      // when the goal is maximum coverage rather than lowest cost.
      excluded_rows_may_hold_additional_addresses: skippedAlreadyHashed > 0,
      chunks: chunkResults.length,
      matched_profiles: matchedProfiles,
      hashes_returned: contactoutHashes.size,
      existing_pool_hashes: existingPool.size,
      net_new_hashes: netNew.length,
      // matched_profiles is the billing signal. hashes_returned is larger
      // whenever a profile resolves to more than one hashed address, so it must
      // not be used to report cost.
      chunk_results: chunkResults,
      net_new_hash_pool: netNew,
      skipped_reason: null,
    };
  },
  {
    description:
      'Resolve LinkedIn URLs into a deduped ContactOut email hash pool for paid ads audiences, reporting net-new hashes and matched-profile cost.',
  },
);
