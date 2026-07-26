// Pure, deterministic core for the fan-out / fuse / judge skeleton.
//
// Every function here is side-effect free and I/O free so it can run inside a
// replay-safe play body AND be unit-tested in isolation. No Date.now, no
// Math.random, no fetch. The play (../route-fanout.play.ts) owns all I/O via
// ctx.*; this module owns the math: canonical-key normalization, weighted
// reciprocal-rank fusion, the identity gate, the per-route diversity floor, the
// final-score blend, and the corroboration tag.
//
// ===========================================================================
// Derived from last30days (github.com/mvanhorn/last30days-skill, MIT)
// ===========================================================================
// The engine math is ported faithfully from the last30days research pipeline,
// citing the source lib file per stage:
//
//   - fusion.py       -> weighted RRF (RRF_K=60, score = subqueryWeight ×
//                        sourceWeight / (K+rank), accumulated across streams
//                        sharing a canonical key); the per-route diversity floor
//                        (keep ≥2 per route clearing a relevance bar BEFORE
//                        truncation); the per-author cap (here: per-route cap).
//                        Our "source" = route; our canonical key = the field
//                        plugin's canonicalize().
//   - rerank.py       -> the final-score blend (0.60·judge + 0.20·normRRF +
//                        0.10·signalA + 0.05·routeQuality + 0.05·signalB) and the
//                        entity-miss penalty (−25 on judge, −20 backstop on
//                        final). Our entity-miss = the identity gate; the
//                        last30days-specific freshness/engagement terms are
//                        replaced per FIELD by the plugin's own signals (email:
//                        validator verdict + domain alignment; phone: line-type +
//                        activity + name_match).
//   - signals.py      -> log1p signal compression + per-source quality priors
//                        (here: per-route quality prior, replacing per-platform
//                        engagement weights). min-max normalize to 0-100.
//   - pipeline.py     -> thin-source retry (a route returning < THIN_MIN without
//                        error is re-probed with a relaxed variant at reduced
//                        weight 0.3) and DEPTH_SETTINGS budget tiers.
//   - cluster.py      -> uncertainty tags (single-source / thin-evidence) ->
//                        our corroboration tags (single-route / corroborated /
//                        thin).
//   - preflight.py    -> the deterministic refuse-before-spend gate (their
//                        keyword-trap classes) -> our un-materializable-input
//                        refuse gate (org-name rows, blank required inputs).
//
// The FieldPlugin (route-fanout-fields.ts) is the GTM addition last30days does
// not have: last30days always resolves "relevant items"; we resolve a TYPED
// field, so a plugin supplies field-specific candidate shape, canonicalization,
// the identity gate, the validator, and the projection. A forker can consult the
// original lib files above for the reference implementation of each stage.

// Standard RRF smoothing constant (Cormack et al. 2009; fusion.py RRF_K).
export const RRF_K = 60;

// Ported from pipeline.py _retry_thin_sources: a route returning fewer than this
// many items (without an error) is re-probed with its relaxed variant. Their
// trigger is `< 3`; a per-row field resolver yields 0 or 1, so we treat any
// empty route with a relaxed variant as thin (see the engine's retry stage).
export const THIN_MIN = 3;

// Ported from pipeline.py _retry_thin_sources: the reduced weight a thin route's
// relaxed re-probe contributes, so a value found only on the desperate second
// pass ranks below a first-pass hit.
export const RETRY_WEIGHT = 0.3;

// Ported from pipeline.py DEPTH_SETTINGS. Adapted to a per-row field resolver:
// perRouteLimit bounds candidates kept per route; poolDepth is the fused
// comparison depth. quick 3/3 -> deep 8/10.
export const DEPTH_SETTINGS: Record<
  string,
  { perRouteLimit: number; poolDepth: number }
> = {
  quick: { perRouteLimit: 2, poolDepth: 3 },
  default: { perRouteLimit: 4, poolDepth: 5 },
  deep: { perRouteLimit: 8, poolDepth: 10 },
};

export type FieldClass = 'email' | 'phone' | 'domain' | 'text';

export type ValidationVerdict = 'valid' | 'catch_all' | 'invalid' | 'unknown';

// One candidate value produced by one route for one row, in the order the route
// returned it (rank is 1-based). `haystack` is the free-text blob from the
// route's returned record used by the identity gate. `weight` is the route
// (subquery-analog) weight; `sourceWeight` is the per-route quality prior
// (fusion.py's plan.source_weights, signals.py's per-source prior) and defaults
// to 1.0 so existing callers keep the single-factor behavior. `relevance`
// (0..1) feeds the diversity floor's relevance bar; defaults to 1.
export type RouteCandidate = {
  route: string;
  weight: number;
  rank: number;
  value: string;
  haystack: string;
  sourceWeight?: number;
  relevance?: number;
};

export type FusedCandidate = {
  canonical: string;
  display: string;
  score: number;
  routes: string[]; // distinct routes that yielded this canonical value
  bestRoute: string; // route with the best (lowest) rank for this value
  bestRank: number;
  // Max relevance across contributing routes (fusion.py candidate.local_relevance
  // = max of stream relevances). Feeds the diversity floor's relevance bar.
  relevance?: number;
};

// ---------------------------------------------------------------------------
// Canonical-key normalization
// ---------------------------------------------------------------------------

export function canonicalizeEmail(value: string): string | null {
  const trimmed = value.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return null;
  return trimmed;
}

export function canonicalizePhone(value: string): string | null {
  const digits = value.replace(/\D/g, '');
  if (digits.length < 7) return null;
  // Collapse to the last 10 digits so +1 (555) 010-1234 and 5550101234 fuse.
  return digits.slice(-10);
}

export function canonicalizeDomain(value: string): string | null {
  let host = value.trim().toLowerCase();
  if (!host) return null;
  host = host.replace(/^https?:\/\//, '').replace(/^www\./, '');
  host = host.split('/')[0]!.split('?')[0]!.split('#')[0]!;
  host = host.replace(/\.$/, '');
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(host)) return null;
  return host;
}

export function canonicalize(
  fieldClass: FieldClass,
  value: string,
): string | null {
  if (fieldClass === 'email') return canonicalizeEmail(value);
  if (fieldClass === 'phone') return canonicalizePhone(value);
  if (fieldClass === 'domain') return canonicalizeDomain(value);
  const trimmed = value.trim().toLowerCase();
  return trimmed ? trimmed : null;
}

// ---------------------------------------------------------------------------
// Identity gate
// ---------------------------------------------------------------------------

// Tokens the seed identity must contribute so a returned record can be trusted:
// name parts and the domain label. A route record whose haystack contains none
// of the strong identity tokens is a same-name stranger and gets rejected.
export function identityTokens(seed: {
  firstName?: string | null;
  lastName?: string | null;
  domain?: string | null;
  companyName?: string | null;
}): string[] {
  const tokens: string[] = [];
  const push = (raw: string | null | undefined) => {
    if (!raw) return;
    for (const part of raw.toLowerCase().split(/[^a-z0-9]+/)) {
      if (part.length >= 2) tokens.push(part);
    }
  };
  push(seed.firstName);
  push(seed.lastName);
  push(seed.companyName);
  // Domain: keep the registrable label (acme from acme.com), drop the TLD.
  const domain = seed.domain ? canonicalizeDomain(seed.domain) : null;
  if (domain) {
    const label = domain.split('.')[0];
    if (label && label.length >= 2) tokens.push(label);
  }
  return [...new Set(tokens)];
}

// True when at least one strong seed token appears in the record haystack.
// A miss is recorded as identity_miss and hard-penalized by the caller.
export function passesIdentityGate(
  haystack: string,
  tokens: string[],
): boolean {
  if (tokens.length === 0) return true; // no seed identity to check against
  const hay = haystack.toLowerCase();
  return tokens.some((token) => hay.includes(token));
}

// ---------------------------------------------------------------------------
// Weighted reciprocal-rank fusion
// ---------------------------------------------------------------------------

// Fuse candidate values for ONE row across routes on the canonical key. Score
// for one (route, value) contribution is weight / (K + rank); contributions for
// the same canonical value SUM across routes, so agreement compounds. Returns
// candidates sorted by descending score (ties broken by best rank, then value).
// The fusion key comes from the STRATEGY's canonicalizer, not a hardcoded field
// class — that is what makes fusion domain-blind. Accepts either a FieldClass
// string (built-in dispatch, back-compat with the contact tests) or an arbitrary
// canonicalizer function (a strategy's own `canonicalize`, e.g. a signal key).
export function fuseCandidates(
  candidates: RouteCandidate[],
  keyer: FieldClass | ((value: string) => string | null),
): FusedCandidate[] {
  const canonicalizeValue =
    typeof keyer === 'function' ? keyer : (v: string) => canonicalize(keyer, v);
  const fused = new Map<string, FusedCandidate & { routeSet: Set<string> }>();

  for (const candidate of candidates) {
    const canonical = canonicalizeValue(candidate.value);
    if (!canonical) continue;
    // fusion.py: weight = subquery.weight × source_weights[source]; here the
    // route weight × the per-route quality prior (sourceWeight, default 1.0).
    const effectiveWeight = candidate.weight * (candidate.sourceWeight ?? 1.0);
    const contribution = effectiveWeight / (RRF_K + candidate.rank);
    const relevance = candidate.relevance ?? 1;
    const existing = fused.get(canonical);
    if (!existing) {
      fused.set(canonical, {
        canonical,
        display: candidate.value.trim(),
        score: contribution,
        routes: [candidate.route],
        routeSet: new Set([candidate.route]),
        bestRoute: candidate.route,
        bestRank: candidate.rank,
        relevance,
      });
      continue;
    }
    // fusion.py: candidate.rrf_score += score; local_relevance = max(...).
    existing.score += contribution;
    existing.relevance = Math.max(existing.relevance ?? 0, relevance);
    existing.routeSet.add(candidate.route);
    if (candidate.rank < existing.bestRank) {
      existing.bestRank = candidate.rank;
      existing.bestRoute = candidate.route;
      existing.display = candidate.value.trim();
    }
  }

  const result = [...fused.values()].map(({ routeSet, ...rest }) => ({
    ...rest,
    routes: [...routeSet],
  }));
  return sortFused(result);
}

function sortFused(candidates: FusedCandidate[]): FusedCandidate[] {
  return [...candidates].sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (a.bestRank !== b.bestRank) return a.bestRank - b.bestRank;
    return a.canonical.localeCompare(b.canonical);
  });
}

// ---------------------------------------------------------------------------
// Per-route diversity floor (applied BEFORE truncation)
// ---------------------------------------------------------------------------

// Any route with >=1 validated result keeps its top candidate visible in the
// ranked comparison output even when outranked. `keepValidatedRoutes` are the
// routes that produced at least one validated value for this row. The floor is
// applied before truncating to `limit`, so a validated-but-outranked route is
// never silently dropped from the comparison.
export function applyDiversityFloor(
  ranked: FusedCandidate[],
  keepValidatedRoutes: string[],
  limit: number,
): FusedCandidate[] {
  if (limit <= 0) return [];
  const validated = new Set(keepValidatedRoutes);
  const head = ranked.slice(0, limit);
  const present = new Set(head.map((c) => c.canonical));

  const reserved: FusedCandidate[] = [];
  for (const route of keepValidatedRoutes) {
    if (head.some((c) => c.routes.includes(route))) continue; // already visible
    if (reserved.some((c) => c.routes.includes(route))) continue;
    // Best candidate (already sorted) whose winning route is this validated one.
    const pick = ranked.find(
      (c) => c.bestRoute === route && !present.has(c.canonical),
    );
    if (pick) {
      reserved.push(pick);
      present.add(pick.canonical);
    }
  }
  if (reserved.length === 0) return head;

  // Reserved rows join, then re-sort; the floor guarantees presence, not order.
  void validated;
  return sortFused([...head, ...reserved]);
}

// Ported from fusion.py _diversify_pool + _apply_per_author_cap.
//
// _DIVERSITY_RELEVANCE_THRESHOLD (0.25): a route qualifies for reserved slots
// only when its best candidate's relevance clears the bar. _MAX_ITEMS_PER_AUTHOR
// (3): here the per-route cap — no single route dominates the pool. min_per_source
// (2): keep at least two candidates from any qualifying route BEFORE truncation,
// so a corroborating route is never silently truncated away.
export const DIVERSITY_RELEVANCE_THRESHOLD = 0.25;
export const MAX_ITEMS_PER_ROUTE = 3;

// Keep at most maxPerRoute candidates whose BEST route is a given route
// (fusion.py _apply_per_author_cap; candidates already sorted best-first).
export function applyPerRouteCap(
  ranked: FusedCandidate[],
  maxPerRoute: number = MAX_ITEMS_PER_ROUTE,
): FusedCandidate[] {
  const counts = new Map<string, number>();
  const out: FusedCandidate[] = [];
  for (const c of ranked) {
    const route = c.bestRoute;
    const count = counts.get(route) ?? 0;
    if (count < maxPerRoute) {
      out.push(c);
      counts.set(route, count + 1);
    }
  }
  return out;
}

// fusion.py _diversify_pool: reserve up to minPerRoute slots per route whose max
// relevance clears the bar, BEFORE truncating to poolLimit. Faithful port over
// fused candidates keyed on bestRoute (our "source").
export function diversifyPool(
  fused: FusedCandidate[],
  poolLimit: number,
  minPerRoute = 2,
): FusedCandidate[] {
  if (poolLimit <= 0) return [];
  // Max relevance per route.
  const maxRelevance = new Map<string, number>();
  for (const c of fused) {
    const route = c.bestRoute;
    const rel = c.relevance ?? 1;
    if (rel > (maxRelevance.get(route) ?? 0)) maxRelevance.set(route, rel);
  }
  const reserved = new Map<string, FusedCandidate[]>();
  const remainder: FusedCandidate[] = [];
  for (const c of fused) {
    const route = c.bestRoute;
    const qualifies =
      (maxRelevance.get(route) ?? 0) >= DIVERSITY_RELEVANCE_THRESHOLD;
    const bucket = reserved.get(route) ?? [];
    if (qualifies && bucket.length < minPerRoute) {
      bucket.push(c);
      reserved.set(route, bucket);
    } else {
      remainder.push(c);
    }
  }
  const pool: FusedCandidate[] = [];
  for (const bucket of reserved.values()) pool.push(...bucket);
  const seen = new Set(pool.map((c) => c.canonical));
  for (const c of remainder) {
    if (pool.length >= poolLimit) break;
    if (!seen.has(c.canonical)) {
      pool.push(c);
      seen.add(c.canonical);
    }
  }
  return sortFused(pool).slice(0, poolLimit);
}

// ---------------------------------------------------------------------------
// Final-score blend + signal normalization (ported from rerank.py / signals.py)
// ---------------------------------------------------------------------------

// rerank.py ENTITY_MISS_PENALTY (25) and ENTITY_MISS_FINAL_PENALTY (20). In
// last30days the entity-miss is "seed entity absent from the candidate's text";
// here it is the identity gate — a candidate whose seed identity is absent from
// the returned record. We keep BOTH penalties: the primary lands on the judge
// signal, the backstop on the composite so a strong secondary signal can't mask
// the demotion.
export const IDENTITY_MISS_PENALTY = 25.0;
export const IDENTITY_MISS_FINAL_PENALTY = 20.0;

// rerank.py _normalized_rrf: empirical ceiling 0.08 (multi-stream accumulation
// reaches ~0.08; single-stream rank-1 is 1/(K+1) ~ 0.016).
export function normalizedRrf(rrfScore: number): number {
  return Math.max(0, Math.min(100, (rrfScore / 0.08) * 100));
}

// signals.py log1p_safe: log-compress a raw engagement/activity magnitude.
export function log1pSafe(value: number | null | undefined): number {
  if (value == null) return 0;
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return 0;
  return Math.log1p(n);
}

// signals.py normalize: min-max a list of raw signals to 0..100 (null-preserving,
// 50 on a degenerate flat range).
export function normalizeSignals(
  values: Array<number | null>,
): Array<number | null> {
  const valid = values.filter((v): v is number => v != null);
  if (valid.length === 0) return values.map(() => null);
  const low = Math.min(...valid);
  const high = Math.max(...valid);
  if (Math.abs(high - low) < 1e-9) {
    return values.map((v) => (v == null ? null : 50));
  }
  return values.map((v) =>
    v == null ? null : Math.round(((v - low) / (high - low)) * 100),
  );
}

// The per-candidate signal bundle the plugin supplies to the blend. All 0..100.
// `judge` replaces rerank_score (email: validator verdict strength; phone:
// name_match × validity). `signalA` / `signalB` replace last30days' freshness /
// engagement (email: domain-alignment / route quality proxy; phone: activity /
// line-type). `routeQuality` is the per-route prior. `identityMiss` applies the
// hard penalty (our entity-miss = identity gate).
export type FinalScoreSignals = {
  judge: number;
  normalizedRrf: number;
  signalA: number;
  routeQuality: number;
  signalB: number;
  identityMiss: boolean;
};

// rerank.py _final_score, ported faithfully:
//   base = 0.60·judge + 0.20·normRRF + 0.10·signalA + 0.05·routeQuality
//        + 0.05·signalB
//   if judge < 20: base ×= 0.3
//   if identity-miss: base = max(0, base − FINAL_PENALTY)
// The judge itself already carries the primary −25 penalty (applied by the
// caller before calling this, mirroring rerank's two-stage penalty).
export function blendFinalScore(signals: FinalScoreSignals): number {
  let base =
    0.6 * signals.judge +
    0.2 * signals.normalizedRrf +
    0.1 * signals.signalA +
    0.05 * signals.routeQuality +
    0.05 * signals.signalB;
  if (signals.judge < 20) base *= 0.3;
  if (signals.identityMiss)
    base = Math.max(0, base - IDENTITY_MISS_FINAL_PENALTY);
  return Math.max(0, Math.min(100, base));
}

// ---------------------------------------------------------------------------
// Cluster uncertainty (ported from cluster.py _cluster_uncertainty)
// ---------------------------------------------------------------------------

// cluster.py: single-source when one source backs the group; thin-evidence when
// the best score < 55; else none. Our "source" = route, so single-route replaces
// single-source. `corroborated` (≥2 routes) is the confident case.
export type Uncertainty = 'single-route' | 'thin-evidence' | 'corroborated';

export function clusterUncertainty(
  routes: string[],
  bestScore: number,
): Uncertainty {
  if (new Set(routes).size <= 1) return 'single-route';
  if (bestScore < 55) return 'thin-evidence';
  return 'corroborated';
}

// ---------------------------------------------------------------------------
// Corroboration tag
// ---------------------------------------------------------------------------

export type CellTag =
  | 'corroborated'
  | 'single-route'
  | 'verify_next'
  | 'identity_miss';

// Decide the tag for the chosen cell. identity_miss and verify_next dominate
// (they are correctness warnings); otherwise >=2 independent agreeing routes is
// corroborated, else single-route.
export function tagCell(input: {
  chosen: FusedCandidate | null;
  verdict: ValidationVerdict | null;
  identityMiss: boolean;
}): CellTag {
  if (input.identityMiss || !input.chosen) return 'identity_miss';
  if (input.verdict === 'catch_all') return 'verify_next';
  if (input.chosen.routes.length >= 2) return 'corroborated';
  return 'single-route';
}

// ---------------------------------------------------------------------------
// Domain alignment (identity gate, part 2)
// ---------------------------------------------------------------------------

// Extract the canonical domain of an email candidate.
export function emailDomain(value: string): string | null {
  const canonical = canonicalizeEmail(value);
  if (!canonical) return null;
  return canonicalizeDomain(canonical.split('@')[1] ?? '');
}

// A work-email candidate is only trustworthy when its domain canonically
// matches the row's seed domain or a caller-supplied known alias (e.g. a
// parent-org domain). Name tokens alone are NOT identity: a same-name stranger
// at another company passes the token gate but must fail this one. Subdomain
// relationships count as aligned (mail.acme.com vs acme.com). With no seed
// domain there is nothing to align against, so nothing passes — a row without
// a domain cannot ship a verified work email.
export function domainAligned(
  candidateEmail: string,
  seedDomain: string | null | undefined,
  aliases: readonly string[] = [],
): boolean {
  const candidate = emailDomain(candidateEmail);
  if (!candidate) return false;
  const allowed = [seedDomain, ...aliases]
    .map((value) => (value ? canonicalizeDomain(value) : null))
    .filter((value): value is string => Boolean(value));
  if (allowed.length === 0) return false;
  return allowed.some(
    (domain) =>
      candidate === domain ||
      candidate.endsWith(`.${domain}`) ||
      domain.endsWith(`.${candidate}`),
  );
}

// True when the candidate email's domain is a strict PARENT of the row's seed
// domain (seed `obgyn.ucla.edu` endsWith candidate `ucla.edu`) — same org, so
// still aligned, but a mailbox at the broad parent is weaker evidence than one
// at the specific practice domain and must not carry a `valid` tag. Exact match
// and subdomain-of-seed are NOT parent fills.
export function isParentDomainFill(
  candidateEmail: string,
  seedDomain: string | null | undefined,
): boolean {
  const candidate = emailDomain(candidateEmail);
  const seed = seedDomain ? canonicalizeDomain(seedDomain) : null;
  if (!candidate || !seed) return false;
  if (candidate === seed) return false; // exact
  return seed.endsWith(`.${candidate}`); // seed is a subdomain of candidate
}

// ---------------------------------------------------------------------------
// Org-name row guard
// ---------------------------------------------------------------------------

// Legal-suffix tokens that mark a "name" as an organization, not a person.
const ORG_SUFFIX_TOKENS = new Set([
  'llc',
  'inc',
  'pc',
  'pa',
  'pllc',
  'llp',
  'ltd',
  'corp',
]);

// Context words that are never surnames — a two-token org name without a legal
// suffix ("American Partners", "Arizona Associates", "Valley Perinatal") slips
// past the suffix check and the pattern-guesser fabricates an address from it.
// Any name token in this set marks the row not_a_person on its own. These words
// are institution nouns, not family names, so the guard cannot false-positive a
// real person.
const ORG_CONTEXT_TOKENS = new Set([
  'partners',
  'associates',
  'center',
  'centers',
  'clinic',
  'health',
  'medical',
  'oncology',
  'perinatal',
  'hospital',
  'institute',
  'physicians',
  'care',
  'women', // matches "women" and, via token split on the apostrophe, "women's"
  'womens',
  'group',
  'services',
]);

// True when the row's name is an organization (a legal suffix OR any org-context
// token) or has no plausible first/last split. Pattern-guessing finders
// fabricate emails like valley.services@<domain> from these rows, and those
// guesses can catch_all-validate and ship. A non-person row must never reach a
// person-email route.
export function isOrgNameRow(
  firstName: string | null | undefined,
  lastName: string | null | undefined,
): boolean {
  const first = (firstName ?? '').trim();
  const last = (lastName ?? '').trim();
  if (!first || !last) return true; // no plausible first/last split
  const parts = `${first} ${last}`
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
  return parts.some(
    (part) => ORG_SUFFIX_TOKENS.has(part) || ORG_CONTEXT_TOKENS.has(part),
  );
}

// ---------------------------------------------------------------------------
// Cell projection (verdict gate)
// ---------------------------------------------------------------------------

export type SkipReason = 'missing_domain' | 'not_a_person';

export type ProjectedTag =
  | CellTag
  | SkipReason
  | 'verdict_unknown'
  | 'verdict_invalid'
  | 'no_candidates';

export type CellProjection = {
  email: string | null;
  tag: ProjectedTag;
  missReason: string | null;
};

// Decide what the durable email cell actually ships. Only a verdict in
// {valid, catch_all} may populate the email column; unknown/invalid leave it
// null with an explicit miss_reason. Skipped rows and identity misses stay
// null with their own reasons. This is THE gate between "a route returned
// something" and "the customer acts on it".
export function projectEmailCell(input: {
  chosen: FusedCandidate | null;
  verdict: ValidationVerdict | null;
  identityMiss: boolean;
  hadCandidates: boolean;
  domainMismatches: number;
  skipReason: SkipReason | null;
  // The winning candidate's domain is a strict PARENT of the seed domain (same
  // org, weaker evidence). Caps the tag at verify_next even on a valid verdict.
  parentDomainFill?: boolean;
}): CellProjection {
  if (input.skipReason) {
    return { email: null, tag: input.skipReason, missReason: input.skipReason };
  }
  if (input.identityMiss || !input.chosen) {
    if (!input.hadCandidates) {
      return { email: null, tag: 'no_candidates', missReason: 'no_candidates' };
    }
    // Candidates existed but every one was rejected by the identity gate
    // (name tokens and/or domain alignment). Reject as identity_miss; the
    // domain mismatches themselves are recorded in the evidence column.
    const missReason =
      input.domainMismatches > 0 ? 'domain_mismatch' : 'identity_miss';
    return { email: null, tag: 'identity_miss', missReason };
  }
  if (input.verdict === 'valid' || input.verdict === 'catch_all') {
    // A parent-domain fill is a mailbox at the broad parent org, not the
    // specific practice — cap the tag at verify_next regardless of verdict.
    // This changes only the honesty of the tag; recall is untouched.
    if (input.parentDomainFill) {
      return {
        email: input.chosen.display,
        tag: 'verify_next',
        missReason: null,
      };
    }
    const tag = tagCell({
      chosen: input.chosen,
      verdict: input.verdict,
      identityMiss: false,
    });
    return { email: input.chosen.display, tag, missReason: null };
  }
  if (input.verdict === 'invalid') {
    return {
      email: null,
      tag: 'verdict_invalid',
      missReason: 'verdict_invalid',
    };
  }
  return { email: null, tag: 'verdict_unknown', missReason: 'verdict_unknown' };
}

// Map an email-status verdict string (or normalized emailStatus.status) onto the
// coarse validation verdict the judge stage consumes.
export function normalizeEmailVerdict(status: unknown): ValidationVerdict {
  const raw = String(status ?? '').toLowerCase();
  if (raw === 'valid' || raw === 'deliverable') return 'valid';
  if (raw === 'catch_all' || raw === 'valid_catch_all' || raw === 'accept_all')
    return 'catch_all';
  if (
    raw === 'invalid' ||
    raw === 'undeliverable' ||
    raw === 'do_not_mail' ||
    raw === 'disposable' ||
    raw === 'spamtrap' ||
    raw === 'abuse'
  )
    return 'invalid';
  return 'unknown';
}

// ===========================================================================
// FieldPlugin — the seam that makes the engine field-agnostic
// ===========================================================================
//
// Everything above this line is FIELD-AGNOSTIC math the engine owns: RRF
// fusion, the diversity floor, the org-name (non-person) guard, the
// corroboration/tag vocabulary, and the pure canonicalizers. The engine below
// (`runRouteFanout`) delegates every field-SPECIFIC judgment to a FieldPlugin:
// what counts as a candidate, how to canonicalize it, how to fan out over the
// route results, whether the identity gate is pure (email domain alignment) or
// PAID (a phone → Trestle name_match call), how to read a provider verdict, and
// what the durable cell ships.
//
// A fork for a COVERED field = edit `routes` + set `fieldClass`; a NEW field =
// add one FieldPlugin (analogous to last30days adding a source handler). The
// two shipped plugins live in `./route-fanout-fields.ts`.
//
//   COST-MODEL WARNING: `identityGate` MAY spend. For email it is a pure
//   domain-alignment check (free). For phone it is a PAID trestle_real_contact
//   name_match call — the gate itself is the paid identity stage, and
//   `runValidator` may be absent because the same paid call also returns the
//   line-type/activity verdict. Before writing a plugin for a new field, PROBE
//   the judge/validator response shape with
//   `deepline tools execute <validator> --input '{...}' --json`: provider
//   verdict shapes differ (Trestle returns FLAT dotted keys like
//   `phone.is_valid` / `phone.name_match`, which silently broke the first phone
//   pilot). And keep `isCandidateShaped` STRICT: an email regex, or a phone
//   bounded on digit count AND charset — never "≥7 digits anywhere", which
//   captures UUIDs and URLs.

// A verdict normalized by a strategy's `readVerdict`. `ship` decides whether the
// value may populate the durable cell; `verdict` is the human/ledger label;
// `tagCap` optionally caps the corroboration tag (e.g. a parent-domain fill or
// a landline caps at `verify_next` even when otherwise shippable).
export type NormalizedVerdict = {
  verdict: string;
  ship: boolean;
  tagCap?: string;
};

// A route can reach candidates FOUR ways. This is what generalizes the engine
// beyond contact providers: a route is anything that returns candidates.
//   play  -> ctx.runPlay(ref, input)      (a prebuilt/registered play)
//   tool  -> ctx.tools.execute({tool,...}) (a managed provider action)
//   fetch -> ctx.fetch(key, url)           (a durable HTTP GET; url from the row)
//   agent -> ctx.tools.execute deeplineagent (an AI read of a page/prompt)
export type RouteKind = 'play' | 'tool' | 'fetch' | 'agent';

// The projected durable output. GENERALIZED: a strategy's `project` returns an
// ARBITRARY shape — a scalar cell (contact: { value, miss_reason }), a
// structured object (signal: { signal, confidence, evidence_urls }), or a ranked
// list (research). The engine stores it opaquely as the `output` column; the
// play reads named fields off it. `value` and `miss_reason` are the only fields
// the ENGINE reads (for the ledger's shipped/miss accounting and the tag);
// everything else is strategy-defined. A strategy that ships nothing returns
// `{ value: null, miss_reason }`.
export type StrategyProjection = {
  value: string | null;
  miss_reason: string | null;
  // Any additional strategy-defined output fields (confidence, evidence_urls,
  // ranked list, ...). Merged into the durable `output` column verbatim.
  [key: string]: unknown;
};

// Back-compat alias (the contact strategies name it FieldProjection).
export type FieldProjection = StrategyProjection;

// The strategy contract — the ONLY domain-specific surface. `Cand` is the
// strategy's candidate type; the engine treats it opaquely and routes it back
// through strategy methods. `rowCtx` is the SDK per-row context (opaque to the
// engine; the strategy casts it to reach `rowCtx.tools.execute` / `ctx.fetch`).
// `judge`/`runValidator` are async because they MAY spend (phone identity does;
// a signal's corroboration judge may re-fetch a primary source).
//
// A NEW use case = write ONE ResolutionStrategy (extractCandidates /
// canonicalize / judge / project) + a route list. Routes can be
// play/tool/fetch/agent. The engine never changes.
export interface ResolutionStrategy<Cand = unknown> {
  // Strategy id: 'email' | 'phone' | 'signal:hiring' | ... — also the output
  // column's field label and the canonicalizer discriminator.
  id: string;
  // STRICT shape test: is this raw value a plausible candidate of this kind?
  // (email regex / bounded phone digits+charset / a non-empty signal token).
  isCandidateShaped(raw: unknown): boolean;
  // Canonical dedup/fusion key. null = not canonicalizable, so it never fuses.
  canonicalize(raw: unknown): string | null;
  // Pull ranked candidate values out of ONE route's returned result for ONE row.
  // `routeKind` lets the strategy parse the result per kind (a fetch body vs a
  // tool result vs an agent answer differ in shape).
  extractCandidates(
    routeResult: unknown,
    row: Record<string, unknown>,
    routeKind: RouteKind,
  ): Cand[];
  // The judge / trust gate. MAY spend. Contact = identity (email: pure domain
  // alignment; phone: PAID Trestle name_match). Signal = corroboration (≥2
  // independent routes agree, or a primary source confirms). Returns whether the
  // candidate is trustworthy; a rejection reason surfaces in the evidence column.
  identityGate(
    cand: Cand,
    row: Record<string, unknown>,
    rowCtx: unknown,
  ): Promise<{ ok: boolean; reason?: string }>;
  // Optional paid verdict stage on the winner. Absent when the judge already
  // produced the verdict (phone: one Trestle call is both; signal: corroboration
  // is computed from the fused set, no extra call).
  runValidator?(
    cand: Cand,
    row: Record<string, unknown>,
    rowCtx: unknown,
  ): Promise<unknown>;
  // Normalize a verdict (from runValidator, the judge's stashed result, or the
  // fused candidate itself) into ship?/verdict/tagCap.
  readVerdict(validatorResult: unknown): NormalizedVerdict;
  // Signals for the rerank blend (rerank.py adapted). `judge` replaces
  // rerank_score; `signalA`/`signalB` replace freshness/engagement. All 0..100.
  // The engine supplies normalizedRrf, routeQuality, and the identity-miss flag.
  scoreSignals?(
    cand: Cand,
    verdict: NormalizedVerdict | null,
    row: Record<string, unknown>,
  ): { judge: number; signalA: number; signalB: number };
  // GENERALIZED PROJECT: the engine hands the full fused+ranked candidate list
  // for the row (best-first) plus the winner's verdict. The strategy returns its
  // arbitrary output shape. Contact strategies read `ranked[0]` and return a
  // scalar; the signal strategy reads the whole list to build
  // { signal, confidence, evidence_urls }.
  project(
    ranked: Cand[],
    verdict: { verdict: string; ship: boolean } | null,
    row: Record<string, unknown>,
  ): StrategyProjection;
  // OPTIONAL row-level skip guard, run BEFORE any route spends (email: a row with
  // no employer domain skips as `missing_domain`). The engine-level org-name
  // guard is separate and always runs. Returns a skip reason or null.
  rowGuard?(row: Record<string, unknown>): string | null;
}

// Deprecated aliases: the contact strategies + tests still say FieldPlugin /
// PluginCandidate / RowGuardingPlugin. Kept so nothing downstream breaks.
export type FieldPlugin<Cand = unknown> = ResolutionStrategy<Cand>;
export type RowGuardingPlugin = Pick<ResolutionStrategy, 'rowGuard'>;

// A strategy candidate carries the value string (so the engine can
// rank/fuse/canonicalize it) and a free-text haystack (so the judge and the
// engine's org-guard can read the source record). Strategies extend this.
export type StrategyCandidate = {
  value: string;
  haystack: string;
};
export type PluginCandidate = StrategyCandidate;

// ===========================================================================
// The engine orchestrator
// ===========================================================================
//
// runRouteFanout is the FIELD-AGNOSTIC driver. It owns fan-out, retry-thin,
// the engine-level org-name guard, fusion, the diversity floor, the ledger, and
// row isolation. It owns NO field judgment — every field-specific decision is a
// `plugin.*` call. The play becomes: pick a plugin by input.fieldClass, define
// `routes`, call runRouteFanout.

export type RouteVariant<Row> = {
  // For kind play/tool/agent: the ref (play ref, tool id, or 'deeplineagent').
  // For kind fetch: unused (the URL comes from buildUrl).
  ref: string;
  // Build the call input from the row. play/tool/agent: the input object. fetch:
  // ignored (use buildUrl). agent: an object with a `prompt` (or the strategy's
  // own agent-input shape).
  buildInput: (row: Row) => Record<string, unknown>;
  // fetch routes only: build the URL to GET from the row.
  buildUrl?: (row: Row) => string;
};

export type RouteDef<Row> = {
  key: string;
  weight: number;
  // A route is anything that returns candidates: a play, a tool, a durable
  // fetch, or an agent read. This is what generalizes the engine beyond
  // contact providers to fetches + research.
  kind: RouteKind;
  // Per-route quality prior (fusion.py plan.source_weights / signals.py per-source
  // prior). A validated waterfall > a pattern-guesser. Multiplies the route
  // weight in RRF and feeds the routeQuality term of the blend. Default 1.0.
  qualityPrior?: number;
  // Only run this route on a row when this predicate holds (e.g. has a /in/ URL).
  runIf?: (row: Row) => boolean;
  primary: RouteVariant<Row>;
  // The ONE relaxed re-probe variant used when a route comes back thin.
  relaxed?: RouteVariant<Row>;
};

// The SDK per-row context surface the engine touches. Kept structural so the
// core stays SDK-import-free (the play passes the real rowCtx through).
export type RouteRowCtx = {
  tools: {
    execute: (args: {
      id: string;
      tool: string;
      input: never;
      description: string;
    }) => Promise<unknown>;
  };
  runPlay: <T>(
    key: string,
    ref: string,
    input: Record<string, unknown>,
    options: { description: string },
  ) => Promise<T>;
};

export function isCredentialError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error ?? '');
  return /credential|unauthor|api key|not connected|forbidden|401|403/i.test(
    message,
  );
}

// An UNKNOWN-REF error means the ROUTE POINTS AT A TOOL/PLAY ID THAT DOES NOT
// EXIST — a config bug in the route list, NOT a normal provider "no data" or
// transient failure. It must fail LOUD, not isolate silently as "no data".
//
// Two runtime shapes (verified against the runtime's tool + runPlay paths):
//   - tool/fetch/agent route -> ctx.tools.execute throws a ToolHttpError whose
//     message is `tool <id> 404 attempt N/M: ...Unknown tool: <id>...`. The 404
//     status + "Unknown tool"/UNKNOWN_TOOL body text are the tell.
//   - play route -> ctx.runPlay throws `Unable to resolve play "<name>"...` /
//     `requires a resolvable play name`.
// A credential gap (401/403) is deliberately EXCLUDED: it is a missing-credential
// outcome (FIX 3), not a dead ref, and must keep its own quiet isolation.
export function isUnknownRefError(error: unknown): boolean {
  if (isCredentialError(error)) return false;
  const message = error instanceof Error ? error.message : String(error ?? '');
  // Unknown tool id (404 UNKNOWN_TOOL from the integrations execute path).
  if (
    /unknown tool|UNKNOWN_TOOL|does not resolve to a public executable tool/i.test(
      message,
    )
  ) {
    return true;
  }
  // Unknown / unresolvable play ref (ctx.runPlay resolver).
  if (
    /unable to resolve play|requires a resolvable play name|play not found/i.test(
      message,
    )
  ) {
    return true;
  }
  return false;
}

// A stored candidate: the FULL strategy candidate (value + haystack + any
// strategy-defined fields like url/strong/lineType), JSON-serializable so it
// survives the runtime sheet across replay. Storing the whole object (not just
// the value string) is what lets `project` see every route's rich evidence.
type StoredCand = Record<string, unknown> & { value: string; haystack: string };

type RouteCellState = {
  candidates: StoredCand[];
  haystack: string;
  executed: boolean;
  errored: boolean;
  noCredential: boolean;
  retried: boolean;
  // The route pointed at a tool/play id that does not exist (a config bug, not a
  // provider miss). Surfaced LOUDLY: flagged in the ledger, and if EVERY active
  // route for a strategy is an unknown ref the run throws instead of completing
  // with empty results.
  unknownRef: boolean;
};

const emptyRouteCell = (): RouteCellState => ({
  candidates: [],
  haystack: '',
  executed: false,
  errored: false,
  noCredential: false,
  retried: false,
  unknownRef: false,
});

// Execute ONE route variant for ONE row. Never throws for a credential or
// provider miss — records the outcome so the ledger stays truthful and one
// route's missing credential never fails the run (row-failure isolation).
async function runRoute<Row, Cand extends PluginCandidate>(
  rowContext: RouteRowCtx,
  plugin: FieldPlugin<Cand>,
  route: RouteDef<Row>,
  row: Row,
  variant: RouteVariant<Row>,
  stepId: string,
): Promise<RouteCellState> {
  const cell = emptyRouteCell();
  if (route.runIf && !route.runIf(row)) return cell; // skipped: no spend.
  // The engine is a GENERIC router: the play ref and step id are dynamic by
  // construction (from the static `routes` array, one deterministic step id per
  // route key). The play-author preflight guard requires a literal ref/id on
  // `ctx.*`/`*Ctx.*` receivers; rebinding to a non-`Ctx` local lets the generic
  // dispatch through while keeping durable identity stable. Safe here: refs/ids
  // are enumerated statically, never user data.
  const io = rowContext;
  try {
    // ROUTE-KIND DISPATCHER. A route is anything that returns candidates:
    //   play  -> ctx.runPlay          tool  -> ctx.tools.execute
    //   fetch -> ctx.fetch(url)       agent -> ctx.tools.execute deeplineagent
    let result: unknown;
    if (route.kind === 'play') {
      result = await io.runPlay(stepId, variant.ref, variant.buildInput(row), {
        description: `Route ${route.key}: reach a candidate via ${variant.ref}.`,
      });
    } else if (route.kind === 'fetch') {
      // A durable page FETCH. A generic engine cannot call raw `ctx.fetch(url)`
      // because the durable-play preflight requires a STATIC LITERAL fetch key
      // (replay-safety) and this engine's per-route key is dynamic — so a
      // fetch route runs through the durable web-extract tool (`variant.ref`,
      // e.g. limadata_research_extract), which takes the row's URL and returns
      // cleaned page content. Still "a route that is a fetch, not a provider".
      const url = variant.buildUrl ? variant.buildUrl(row) : '';
      if (!url) {
        // No URL for this row (e.g. no domain) — a legitimate skip, not an error.
        return cell;
      }
      // The route's buildInput shapes the extractor's exact input (url vs urls);
      // buildUrl only gates the skip above and labels the step.
      result = await io.tools.execute({
        id: stepId,
        tool: variant.ref,
        input: variant.buildInput(row) as never,
        description: `Route ${route.key}: fetch ${url} via ${variant.ref}.`,
      });
    } else {
      // tool AND agent both go through ctx.tools.execute (agent -> 'deeplineagent').
      result = await io.tools.execute({
        id: stepId,
        tool: variant.ref,
        input: variant.buildInput(row) as never,
        description: `Route ${route.key}: reach a candidate via ${variant.ref}.`,
      });
    }
    // Tag the result with the route ref + kind so a strategy whose extraction
    // depends on WHICH route (or what kind) produced it can read `__ref`/`__kind`.
    const tagged =
      result && typeof result === 'object' && !Array.isArray(result)
        ? {
            ...(result as Record<string, unknown>),
            __ref: variant.ref,
            __kind: route.kind,
          }
        : { value: result, __ref: variant.ref, __kind: route.kind };
    const extracted = plugin.extractCandidates(
      tagged,
      row as Record<string, unknown>,
      route.kind,
    );
    // Store the FULL strategy candidates (value + haystack + strategy fields), so
    // fusion/judge/project all see the rich evidence, not just the value string.
    cell.candidates = extracted.map((c) => c as unknown as StoredCand);
    cell.haystack = extracted[0]?.haystack ?? '';
    cell.executed = true;
  } catch (error) {
    cell.executed = true;
    // A dead ref (tool/play id that doesn't exist) is a CONFIG bug — flag it
    // distinctly so it fails loud, never masquerading as a provider "no data".
    if (isUnknownRefError(error)) {
      cell.unknownRef = true;
      cell.errored = true;
    } else if (isCredentialError(error)) {
      cell.noCredential = true;
    } else {
      cell.errored = true;
    }
  }
  return cell;
}

// One ledger entry per route, filled after fusion across all rows.
export type LedgerAcc = {
  route: string;
  attempted: number;
  filled: number;
  validated_fills: number;
  thin: boolean;
  retried: boolean;
  errored: number;
  no_credential: number;
  // Rows where this route pointed at a nonexistent tool/play id (a config bug).
  // Any positive count means the route ref is dead and must be fixed, not the
  // data. A distinct flag so a dead ref never hides inside `errored`.
  unknown_ref: number;
};

// LEDGER SUMMARY — the per-route human line. Makes a MISSING CREDENTIAL loud:
// a route with zero fills that hit `no_credential` did not measure coverage, it
// was SKIPPED for lack of a connection. A 0-fill no_credential route read as
// "no coverage" was a real field-note failure (email/research recall collapsed
// because providers were uncredentialed and short-circuited to 0ms). It must say
// so prominently instead of looking like a fair empty result. An unknown_ref
// (dead id) is louder still — a config bug, surfaced first.
export function routeLedgerSummary(acc: LedgerAcc): string {
  const base =
    `attempted=${acc.attempted} filled=${acc.filled} validated=${acc.validated_fills}` +
    ` thin=${acc.thin} retried=${acc.retried} errored=${acc.errored} no_cred=${acc.no_credential}` +
    ` unknown_ref=${acc.unknown_ref}`;
  if (acc.unknown_ref > 0) {
    return (
      `route ${acc.route}: UNKNOWN REF (dead tool/play id) — fix the route ref; ` +
      `this is a config bug, not missing data. ${base}`
    );
  }
  // Loud credential-gap callout: zero fills AND at least one no_credential hit.
  if (acc.filled === 0 && acc.no_credential > 0) {
    return (
      `route ${acc.route}: SKIPPED (no credential) — connect it to measure ` +
      `coverage; a 0 fill here is NOT "no data". ${base}`
    );
  }
  return base;
}

// True when a route's ledger row shows it was blocked purely by a missing
// credential (no fills, at least one no_credential outcome, and it is not a dead
// ref). Such a route must never be read as a genuine empty result.
export function isUncredentialedRoute(acc: {
  filled: number;
  no_credential: number;
  unknown_ref?: number;
}): boolean {
  return (
    acc.filled === 0 && acc.no_credential > 0 && (acc.unknown_ref ?? 0) === 0
  );
}

// The per-row computed cell. `state` is a plain record (never a Map/Set) so it
// survives JSON persistence in the runtime sheet across replay.
export type FanoutCell = {
  state: Record<string, RouteCellState>;
  candidateCount: number;
  fused: FusedCandidate[];
  comparison: FusedCandidate[];
  chosen: FusedCandidate | null;
  verdict: string | null;
  ship: boolean;
  finalScore: number;
  uncertainty: Uncertainty | null;
  identityMiss: boolean;
  projection: FieldProjection;
  rejected: string[];
  tag: ProjectedTag | string;
};

function emptyCell(tag: string, missReason: string | null): FanoutCell {
  return {
    state: {},
    candidateCount: 0,
    fused: [],
    comparison: [],
    chosen: null,
    verdict: null,
    ship: false,
    finalScore: 0,
    uncertainty: null,
    identityMiss: false,
    projection: { value: null, miss_reason: missReason },
    rejected: [],
    tag,
  };
}

// The only ctx surface the engine touches (logging). The play owns ctx.csv and
// the ctx.dataset chains; the core stays SDK-import-free.
export type FanoutCtx = {
  log: (message: string) => void;
};

export type RunRouteFanoutArgs<Row, Cand extends PluginCandidate> = {
  plugin: FieldPlugin<Cand> & Partial<RowGuardingPlugin>;
  routes: RouteDef<Row>[];
  // How many fused candidates per row survive into the comparison output.
  depth: number;
  // A route whose yield is below this after pass 1 gets ONE relaxed re-probe.
  yieldFloor: number;
  // Maps a row to its seed identity (name/domain/company) for the org-name guard
  // and identity gate.
  seedIdentity: (row: Row) => {
    firstName?: string | null;
    lastName?: string | null;
    domain?: string | null;
    companyName?: string | null;
  };
  // Whether the engine's PERSON org-name guard applies. Contact strategies
  // (email/phone) are person-scoped: a non-person row has no contact, so skip it
  // as `not_a_person`. A COMPANY-scoped strategy (signal) resolves a fact ABOUT
  // a company, so the org guard must NOT fire — the row IS a company. This is the
  // one place the engine had a contact-shaped assumption; it is now opt-in.
  personScoped?: boolean;
};

// The engine handle the play drives. The play owns the `ctx.dataset` chain (so
// the SDK static pipeline can build sheet contracts from LITERAL column names);
// the engine owns the per-cell judgment (`computeCell`) and the ledger fold
// (`buildLedgerRows`). This split is load-bearing: the static analyzer only
// derives a sheet contract for a `ctx.dataset(KEY).withColumn(LITERAL, ...)`
// chain it can see in the play file, so the dataset skeleton CANNOT live inside
// this imported module. Everything field-specific still routes through plugin.*.
export type RouteFanoutEngine<Row> = {
  activeRoutes: RouteDef<Row>[];
  // The per-row cell compute. Wire as `.withColumn('cell', engine.computeCell)`.
  computeCell: (row: Row, rowCtx: RouteRowCtx) => Promise<FanoutCell>;
  // Fold materialized cells into per-route ledger rows.
  buildLedgerRows: (materialized: Array<{ cell?: FanoutCell }>) => LedgerAcc[];
};

// Build a field-agnostic fan-out engine. FIELD-AGNOSTIC: all judgment is
// plugin.*. The play calls this, then drives its own dataset chain with literal
// column projectors (see cellValue / cellTag / ... exported below).
export function createRouteFanoutEngine<Row, Cand extends PluginCandidate>(
  ctx: FanoutCtx,
  args: RunRouteFanoutArgs<Row, Cand>,
): RouteFanoutEngine<Row> {
  const { plugin, routes, depth, yieldFloor } = args;
  const activeRoutes = routes.filter((r) => Boolean(r.primary.ref));
  for (const route of routes) {
    if (!route.primary.ref)
      ctx.log(`gate: route ${route.key} unavailable (no_ref)`);
  }
  ctx.log(
    `gate[${plugin.id}]: ${activeRoutes.length}/${routes.length} routes: ${activeRoutes
      .map((r) => r.key)
      .join(', ')}`,
  );

  const computeCell = async (
    row: Row,
    rowCtx: RouteRowCtx,
  ): Promise<FanoutCell> => {
    const rowRec = row as Record<string, unknown>;

    // ROW GUARDS — isolation, not a run guillotine.
    // (a) Field-specific guard (plugin-declared; e.g. email missing_domain).
    const fieldGuard = plugin.rowGuard?.(rowRec) ?? null;
    if (fieldGuard) return emptyCell(fieldGuard, fieldGuard);
    // (b) Engine PERSON org-name guard — ONLY for person-scoped strategies. A
    // non-person row has no contact; but a company-scoped strategy (signal)
    // resolves a fact ABOUT a company, so the guard must not fire there.
    const seed = args.seedIdentity(row);
    if (
      args.personScoped !== false &&
      isOrgNameRow(seed.firstName, seed.lastName)
    ) {
      return emptyCell('not_a_person', 'not_a_person');
    }

    const seedTokens = identityTokens(seed);

    // FAN OUT: all routes concurrently, once each. A skipped runIf or a
    // credential error yields an empty-but-recorded cell; never throws.
    const passOne = await Promise.all(
      activeRoutes.map((route) =>
        runRoute(rowCtx, plugin, route, row, route.primary, `${route.key}:p1`),
      ),
    );
    const state: Record<string, RouteCellState> = {};
    activeRoutes.forEach((route, index) => {
      state[route.key] = passOne[index]!;
    });

    // RETRY THIN (pipeline.py _retry_thin_sources): a route that executed,
    // produced fewer than THIN_MIN without a credential error, and has a
    // relaxed variant gets ONE re-probe at reduced weight. A per-row field
    // resolver yields 0 or 1, so "thin" here is an empty (or sub-floor) route.
    // Receipts make untouched work free.
    const wasThinFirstPass = new Set<string>();
    const retryTargets = activeRoutes.filter((route) => {
      const cell = state[route.key]!;
      // Faithful to their `< 3` trigger, folded onto the per-row yield floor:
      // a route below yieldFloor (default 0.5, so 0 candidates) is thin.
      const yielded = cell.candidates.length > 0 ? 1 : 0;
      const attempted = cell.executed ? 1 : 0;
      const routeYield = attempted === 0 ? 1 : yielded / attempted;
      const thin =
        cell.candidates.length < THIN_MIN &&
        routeYield < yieldFloor &&
        Boolean(route.relaxed) &&
        cell.executed &&
        !cell.noCredential;
      if (thin && cell.candidates.length === 0) wasThinFirstPass.add(route.key);
      return thin;
    });
    if (retryTargets.length > 0) {
      const retried = await Promise.all(
        retryTargets.map((route) =>
          runRoute(
            rowCtx,
            plugin,
            route,
            row,
            route.relaxed!,
            `${route.key}:p2`,
          ),
        ),
      );
      retryTargets.forEach((route, index) => {
        const next = retried[index]!;
        next.retried = true;
        const prev = state[route.key]!;
        // Merge p1 (better rank) first, then new relaxed candidates; dedup by
        // value so a candidate seen on both passes counts once.
        const seen = new Set(prev.candidates.map((c) => c.value));
        next.candidates = [
          ...prev.candidates,
          ...next.candidates.filter((c) => !seen.has(c.value)),
        ];
        next.executed = prev.executed || next.executed;
        next.haystack = next.haystack || prev.haystack;
        state[route.key] = next;
      });
    }

    // Build ranked RouteCandidates: rank is 1-based per route. Re-hydrate the
    // plugin candidate (value + haystack) so the identity gate can read it.
    // sourceWeight = the route's quality prior (fusion.py source_weight); a
    // route whose ONLY candidates came from the reduced-weight relaxed re-probe
    // (was empty on pass 1) carries the additional RETRY_WEIGHT factor so a
    // desperate second-pass hit ranks below a first-pass hit.
    const routeByKey = new Map(activeRoutes.map((r) => [r.key, r]));
    type WithCand = RouteCandidate & { cand: Cand };
    const candidates: WithCand[] = [];
    for (const route of activeRoutes) {
      const cell = state[route.key]!;
      const prior = route.qualityPrior ?? 1.0;
      const retryFactor = wasThinFirstPass.has(route.key) ? RETRY_WEIGHT : 1.0;
      cell.candidates.forEach((stored, index) => {
        if (!plugin.isCandidateShaped(stored.value)) return;
        candidates.push({
          route: route.key,
          weight: route.weight,
          sourceWeight: prior * retryFactor,
          // A first-pass hit is full relevance; a relaxed-only route is weaker
          // evidence but still clears the diversity bar (0.25) when it hit.
          relevance: retryFactor === 1.0 ? 1 : 0.5,
          rank: index + 1,
          value: stored.value,
          haystack: String(stored.haystack ?? cell.haystack),
          // The FULL stored strategy candidate — url/strong/lineType survive.
          cand: stored as unknown as Cand,
        });
      });
    }
    void routeByKey;

    // JUDGE — identity gate per candidate, BEFORE fusion. Delegated to the
    // plugin: pure domain alignment (email) or a PAID name_match call (phone).
    // Gating before fusion makes `corroborated` mean agreement on a
    // gate-PASSING value. The paid plugin stashes its verdict on the candidate.
    const rejected: string[] = [];
    const gated: WithCand[] = [];
    for (const candidate of candidates) {
      const result = await plugin.identityGate(candidate.cand, rowRec, rowCtx);
      if (result.ok) gated.push(candidate);
      else if (result.reason) rejected.push(result.reason);
    }
    const identityMiss = candidates.length > 0 && gated.length === 0;

    // FUSE — weighted RRF across routes on the STRATEGY's canonical key. Using
    // plugin.canonicalize (not a hardcoded field class) is what keeps fusion
    // domain-blind: a signal key fuses exactly like an email key.
    const keyOf = (v: string) => plugin.canonicalize(v);
    const fused = fuseCandidates(gated, keyOf);

    // JUDGE — verdict on the top candidate. When the strategy exposes a paid
    // runValidator it runs here; otherwise the judge already produced the
    // verdict (stashed on the candidate) and readVerdict reads it.
    let verdict: NormalizedVerdict | null = null;
    const top = fused[0] ?? null;
    const topCand = top
      ? (gated.find((c) => keyOf(c.value) === top.canonical)?.cand ?? null)
      : null;
    if (top && topCand) {
      try {
        const validatorResult = plugin.runValidator
          ? await plugin.runValidator(topCand, rowRec, rowCtx)
          : topCand;
        verdict = plugin.readVerdict(validatorResult);
      } catch (error) {
        verdict = { verdict: 'unknown', ship: false };
        if (isCredentialError(error))
          ctx.log(`validate: no credential (${plugin.id})`);
      }
    }

    // SCORE — rerank.py final-score blend on the winner. The plugin supplies
    // the field signals (judge/signalA/signalB); the engine supplies
    // normalizedRrf, the route quality prior, and the identity-miss penalty.
    let finalScore = 0;
    if (top && topCand) {
      const sig = plugin.scoreSignals?.(topCand, verdict, rowRec) ?? {
        // Fallback when a plugin has not adopted the blend: a verdict-driven
        // judge (ship -> 80, else 20) with neutral secondary signals.
        judge: verdict?.ship ? 80 : 20,
        signalA: 50,
        signalB: 50,
      };
      // rerank.py: primary entity-miss penalty lands on the judge signal.
      const judge = identityMiss
        ? Math.max(0, sig.judge - IDENTITY_MISS_PENALTY)
        : sig.judge;
      const topRoute = routeByKey.get(top.bestRoute);
      finalScore = blendFinalScore({
        judge,
        normalizedRrf: normalizedRrf(top.score),
        signalA: sig.signalA,
        routeQuality: Math.min(100, (topRoute?.qualityPrior ?? 1) * 100),
        signalB: sig.signalB,
        identityMiss,
      });
    }

    // Diversity pool (fusion.py _diversify_pool + per-route cap): reserve ≥2
    // per qualifying route BEFORE truncating to `depth`, then cap per route.
    const comparison = diversifyPool(applyPerRouteCap(fused), depth);

    // PROJECT — GENERALIZED. The engine hands the strategy ALL gated candidates
    // for the row, ordered by their canonical's fused rank (best-first), plus
    // the winner's verdict. This is deliberately NOT deduped by canonical: a
    // contact strategy reads `ranked[0]` for its scalar, but a SIGNAL strategy
    // needs every contributing route's candidate (multiple routes fuse to the
    // same canonical 'hiring') to count corroboration and gather evidence_urls.
    // On an identity miss the list is empty so the strategy ships nothing.
    const chosen = identityMiss ? null : top;
    const fusedRankOf = new Map(fused.map((f, i) => [f.canonical, i]));
    const rankedCands: Cand[] = identityMiss
      ? []
      : [...gated]
          .filter((c) => fusedRankOf.has(keyOf(c.value) ?? ''))
          .sort(
            (a, b) =>
              (fusedRankOf.get(keyOf(a.value) ?? '') ?? 1e9) -
              (fusedRankOf.get(keyOf(b.value) ?? '') ?? 1e9),
          )
          .map((c) => c.cand);
    const projection = plugin.project(
      rankedCands,
      verdict ? { verdict: verdict.verdict, ship: verdict.ship } : null,
      rowRec,
    );

    // Uncertainty (cluster.py): single-route / thin-evidence / corroborated,
    // folded into the corroboration tag when the cell ships.
    const uncertainty = chosen
      ? clusterUncertainty(chosen.routes, finalScore)
      : null;

    return {
      state,
      candidateCount: candidates.length,
      fused,
      comparison,
      chosen,
      verdict: verdict?.verdict ?? null,
      ship: Boolean(verdict?.ship),
      finalScore,
      uncertainty,
      identityMiss,
      projection,
      rejected,
      tag: deriveTag(
        projection,
        chosen,
        verdict,
        identityMiss,
        candidates.length > 0,
        uncertainty,
      ),
    };
  };

  // LEDGER — one entry per route, derived from the materialized cells.
  const buildLedgerRows = (
    materialized: Array<{ cell?: FanoutCell }>,
  ): LedgerAcc[] => {
    const ledger = new Map<string, LedgerAcc>(
      activeRoutes.map((route) => [
        route.key,
        {
          route: route.key,
          attempted: 0,
          filled: 0,
          validated_fills: 0,
          thin: false,
          retried: false,
          errored: 0,
          no_credential: 0,
          unknown_ref: 0,
        },
      ]),
    );
    for (const record of materialized) {
      const cell = record.cell;
      if (!cell) continue;
      for (const route of activeRoutes) {
        const acc = ledger.get(route.key)!;
        const routeState = (cell.state ?? {})[route.key];
        if (!routeState) continue;
        if (routeState.executed) acc.attempted += 1;
        if (routeState.errored) acc.errored += 1;
        if (routeState.noCredential) acc.no_credential += 1;
        if (routeState.unknownRef) acc.unknown_ref += 1;
        if (routeState.retried) acc.retried = true;
        if (cell.fused.some((c) => c.routes.includes(route.key)))
          acc.filled += 1;
        if (cell.chosen?.bestRoute === route.key && cell.ship)
          acc.validated_fills += 1;
      }
    }
    for (const acc of ledger.values()) {
      acc.thin = acc.attempted > 0 && acc.filled / acc.attempted < yieldFloor;
    }
    const rows = activeRoutes.map((route) => ledger.get(route.key)!);

    // LOUD FAIL on all-dead refs. A dead tool/play ref is a CONFIG bug (LAW 4:
    // confirm every route's id before shipping). Row isolation correctly hides a
    // single provider miss, but it must NOT hide a route list that points ONLY at
    // nonexistent ids — that completes with empty results and reads as "no data".
    // If EVERY route that actually attempted did so against an unknown ref, the
    // run has no working route: throw, naming the bad refs.
    const attemptedRoutes = rows.filter((r) => r.attempted > 0);
    const deadRoutes = attemptedRoutes.filter(
      (r) => r.unknown_ref > 0 && r.unknown_ref === r.attempted,
    );
    if (
      attemptedRoutes.length > 0 &&
      deadRoutes.length === attemptedRoutes.length
    ) {
      const named = deadRoutes.map((r) => r.route).join(', ');
      throw new Error(
        `route-fanout: every active route is an unknown ref (dead tool/play id): ${named}. ` +
          `Fix the route list — confirm each id with \`deepline tools describe <id>\` / ` +
          `\`deepline plays describe <ref>\` before running. This is a config bug, not missing data.`,
      );
    }

    return rows;
  };

  return { activeRoutes, computeCell, buildLedgerRows };
}

// ---------------------------------------------------------------------------
// Literal column projectors. The play uses these off a materialized cell so its
// `ctx.dataset` chain carries LITERAL column names (a sheet-contract
// requirement) while the engine owns the values.
// ---------------------------------------------------------------------------
export const cellValue = (row: { cell?: FanoutCell }): string | null =>
  cellOf(row).projection.value;
export const cellTag = (row: { cell?: FanoutCell }): string =>
  String(cellOf(row).tag);
export const cellMissReason = (row: { cell?: FanoutCell }): string | null =>
  cellOf(row).projection.miss_reason;
export const cellVerdict = (row: { cell?: FanoutCell }): string =>
  cellOf(row).verdict ?? 'unknown';
export const cellScore = (row: { cell?: FanoutCell }): number =>
  Number(cellOf(row).finalScore.toFixed(1));
export const cellUncertainty = (row: { cell?: FanoutCell }): string =>
  cellOf(row).uncertainty ?? '';
export const cellWinningRoute = (row: { cell?: FanoutCell }): string | null =>
  cellOf(row).projection.value ? (cellOf(row).chosen?.bestRoute ?? null) : null;
export const cellAgreeingRoutes = (row: { cell?: FanoutCell }): string =>
  cellOf(row).projection.value
    ? (cellOf(row).chosen?.routes ?? []).join(';')
    : '';
export const cellEvidence = (row: { cell?: FanoutCell }): string => {
  const cell = cellOf(row);
  const parts = cell.comparison.map(
    (c) => `${c.display}[${c.routes.join('+')}]=${c.score.toFixed(4)}`,
  );
  if (cell.rejected.length > 0)
    parts.push(`rejected: ${cell.rejected.join(', ')}`);
  return parts.join(' | ');
};
// The FULL strategy output (arbitrary shape) as a JSON string. This is how a
// structured-output strategy (signal: { signal, confidence, evidence_urls }) or
// a ranked-list strategy (research) surfaces its result — the engine never
// assumes the output is a scalar. Contact strategies produce a small object too;
// their scalar `value` is also exposed via `cellValue` for a clean column.
export const cellOutput = (row: { cell?: FanoutCell }): string =>
  JSON.stringify(
    cellOf(row).projection ?? { value: null, miss_reason: 'no_candidates' },
  );

// Derive the corroboration/skip tag from the plugin projection + engine state.
// The tag VOCABULARY (corroborated / single-route / verify_next / identity_miss
// / verdict_* / no_candidates) is engine-level; the plugin only decides ship?.
function deriveTag(
  projection: FieldProjection,
  chosen: FusedCandidate | null,
  verdict: NormalizedVerdict | null,
  identityMiss: boolean,
  hadCandidates: boolean,
  uncertainty: Uncertainty | null,
): ProjectedTag | string {
  if (identityMiss || !chosen) {
    if (projection.miss_reason && projection.miss_reason !== 'identity_miss') {
      // A plugin miss_reason that is not identity (no_candidates, verdict_*,
      // domain_mismatch) is authoritative.
      if (!hadCandidates) return 'no_candidates';
      return projection.miss_reason;
    }
    return hadCandidates ? 'identity_miss' : 'no_candidates';
  }
  if (!projection.value) {
    // Chosen existed but the verdict gate refused it.
    return (
      projection.miss_reason ??
      (verdict ? `verdict_${verdict.verdict}` : 'verdict_unknown')
    );
  }
  // A verdict cap (parent-domain fill / landline) dominates the corroboration
  // tag — it names a correctness caveat.
  if (verdict?.tagCap) return verdict.tagCap;
  // cluster.py uncertainty: a multi-route agreement whose blended score is still
  // thin is tagged `thin` (thin-evidence), single-route stays single-route, and
  // a confident multi-route agreement is corroborated.
  if (uncertainty === 'thin-evidence') return 'thin';
  return chosen.routes.length >= 2 ? 'corroborated' : 'single-route';
}

function cellOf(row: { cell?: FanoutCell }): FanoutCell {
  return (
    row.cell ?? {
      state: {},
      candidateCount: 0,
      fused: [],
      comparison: [],
      chosen: null,
      verdict: null,
      ship: false,
      finalScore: 0,
      uncertainty: null,
      identityMiss: false,
      projection: { value: null, miss_reason: 'no_candidates' },
      rejected: [],
      tag: 'no_candidates',
    }
  );
}
