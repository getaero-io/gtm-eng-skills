// A SIGNAL ResolutionStrategy for the route-fanout engine — the generalization
// proof. It resolves a company-level SIGNAL ("is this company actively hiring?")
// instead of a contact field, through the SAME engine, with a HETEROGENEOUS mix
// of routes (a tool + a ctx.fetch of the careers page + a deeplineagent read).
//
// What this proves that email/phone did not:
//   1. Routes need not be contact providers — one route is a `ctx.fetch`, one is
//      a `deeplineagent` read. The engine's route-kind dispatcher runs all four.
//   2. The judge is CORROBORATION, not identity: a signal is trustworthy when
//      ≥2 independent routes agree (or a primary source — the fetched careers
//      page — confirms). No paid identity call.
//   3. `project` returns a STRUCTURED OBJECT, not a scalar:
//      { signal, confidence, evidence_urls }.
//
// Discover live refs before hardcoding: `deepline tools search "hiring jobs"`.
// jsearch (openwebninja_jsearch_search) takes { query } and returns
// { data: [{ job_title, employer_name, job_apply_link, ... }] }.

import {
  type NormalizedVerdict,
  type ResolutionStrategy,
  type StrategyCandidate,
  type StrategyProjection,
} from './route-fanout-core';

// ---------------------------------------------------------------------------
// Shared adapters (pure).
// ---------------------------------------------------------------------------
function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function rawResponse(result: unknown): Record<string, unknown> {
  const wrapped = asRecord(result);
  return asRecord(asRecord(wrapped.toolResponse).raw ?? wrapped);
}

type SignalRow = {
  company_name?: string;
  domain?: string;
};

// A hiring-signal candidate. `value` is ALWAYS the canonical signal token
// ('hiring') when the route found hiring evidence — so every route that found
// hiring fuses to the same key and corroboration = a route count. `haystack`
// carries the concrete evidence (job titles / page text). `url` is the evidence
// URL surfaced in the structured output. `strong` marks a PRIMARY-source route
// (the fetched careers page) whose lone confirmation is trustworthy on its own.
type SignalCand = StrategyCandidate & {
  url?: string;
  strong?: boolean;
};

const HIRING_TERMS =
  /\b(hiring|careers?|job openings?|now hiring|apply now|join our team|open positions?|we're hiring|open roles?|job opportunit)/i;

// The signal token. Any hiring evidence canonicalizes to 'hiring' so routes
// corroborate; a non-hiring token stays itself (and never fuses with 'hiring').
function canonicalizeSignal(raw: unknown): string | null {
  if (typeof raw !== 'string') return null;
  const s = raw.trim().toLowerCase();
  if (!s) return null;
  return s === 'hiring' ? 'hiring' : s;
}

// A candidate is a plausible signal token when it is a short non-empty string.
function isSignalShaped(raw: unknown): boolean {
  return typeof raw === 'string' && raw.trim().length > 0 && raw.trim().length <= 40;
}

// tool route (jsearch): job postings -> a single 'hiring' candidate whose
// haystack lists the titles and whose url is the first apply link.
function extractToolHiring(result: unknown): SignalCand[] {
  const raw = rawResponse(result);
  const data = raw.data;
  if (!Array.isArray(data) || data.length === 0) return [];
  const titles: string[] = [];
  let url: string | undefined;
  for (const job of data) {
    const j = asRecord(job);
    if (typeof j.job_title === 'string') titles.push(j.job_title);
    if (!url && typeof j.job_apply_link === 'string') url = j.job_apply_link;
  }
  if (titles.length === 0) return [];
  return [
    {
      value: 'hiring',
      haystack: `open roles: ${titles.slice(0, 8).join('; ')}`,
      url,
    },
  ];
}

// fetch route: the careers/site page content, from a web-extract tool
// (firecrawl_scrape -> { markdown, metadata }) or a raw ctx.fetch envelope
// ({ bodyText }). A PRIMARY source — if the page shows hiring terms, that is
// direct evidence (strong=true).
function extractFetchHiring(result: unknown): SignalCand[] {
  const raw = rawResponse(result);
  const data = asRecord(raw.data);
  const meta = asRecord(raw.metadata ?? data.metadata);
  // firecrawl: raw.markdown; raw-fetch envelope: raw.bodyText.
  const page =
    (typeof raw.markdown === 'string' && raw.markdown) ||
    (typeof data.markdown === 'string' && data.markdown) ||
    (typeof raw.bodyText === 'string' && raw.bodyText) ||
    (typeof raw.html === 'string' && raw.html) ||
    '';
  const url =
    (typeof meta.sourceURL === 'string' && meta.sourceURL) ||
    (typeof meta.url === 'string' && meta.url) ||
    (typeof raw.url === 'string' && raw.url) ||
    undefined;
  if (!page) return [];
  if (!HIRING_TERMS.test(page)) return [];
  const match = page.match(HIRING_TERMS);
  return [
    {
      value: 'hiring',
      haystack: `careers page shows: ${match ? match[0] : 'hiring terms'}`,
      url,
      strong: true, // a primary source confirming on its own is trustworthy
    },
  ];
}

// agent route: deeplineagent read. It returns { extracted_json: { hiring: bool,
// evidence, url } } (our jsonSchema) or a free-text result we scan for hiring.
function extractAgentHiring(result: unknown): SignalCand[] {
  const raw = rawResponse(result);
  const extracted = asRecord(raw.extracted_json);
  const resultText = typeof raw.result === 'string' ? raw.result : '';
  // An explicit structured verdict wins over a text scan: `hiring: false` means
  // NOT hiring even if the free text mentions "open roles" (e.g. "no open roles").
  const explicit =
    typeof extracted.hiring === 'boolean'
      ? extracted.hiring
      : typeof extracted.hiring === 'string'
        ? extracted.hiring.toLowerCase() === 'yes' ||
          extracted.hiring.toLowerCase() === 'true'
        : null;
  const hiring =
    explicit === true ||
    (explicit === null && Boolean(resultText) && HIRING_TERMS.test(resultText));
  if (!hiring) return [];
  const evidence =
    (typeof extracted.evidence === 'string' && extracted.evidence) ||
    resultText.slice(0, 120) ||
    'agent confirmed hiring';
  const url = typeof extracted.url === 'string' ? extracted.url : undefined;
  return [{ value: 'hiring', haystack: `agent: ${evidence}`, url, strong: true }];
}

export const signalStrategy: ResolutionStrategy<SignalCand> = {
  id: 'signal:hiring',

  isCandidateShaped: (raw) => isSignalShaped(raw),

  canonicalize: (raw) => canonicalizeSignal(raw),

  // Parse per route KIND: a tool result, a fetch envelope, or an agent answer.
  extractCandidates: (routeResult, _row, routeKind) => {
    if (routeKind === 'fetch') return extractFetchHiring(routeResult);
    if (routeKind === 'agent') return extractAgentHiring(routeResult);
    return extractToolHiring(routeResult);
  },

  // JUDGE = CORROBORATION, not identity. A candidate passes the gate when it is
  // hiring evidence at all; the ENGINE's fusion then counts how many independent
  // routes agree, and the verdict/score below decide trust from that count +
  // whether a primary source confirmed. No paid call.
  identityGate: async (cand) => {
    if (canonicalizeSignal(cand.value) === 'hiring') return { ok: true };
    return { ok: false, reason: `non-hiring token: ${cand.value}` };
  },

  // No runValidator: corroboration is computed from the fused set (readVerdict).

  // The verdict reads the WINNING fused candidate. The engine passes the winning
  // strategy candidate here; we ship when a primary source confirmed (strong) OR
  // when ≥2 routes corroborated. The engine records route count on the fused
  // candidate, but readVerdict only sees one candidate — so we encode
  // corroboration into scoreSignals (which the engine blends) and use `strong`
  // for the primary-source path here. A single non-primary route is verify_next.
  readVerdict: (validatorResult): NormalizedVerdict => {
    const cand = validatorResult as SignalCand;
    if (!cand) return { verdict: 'no_signal', ship: false };
    if (cand.strong) return { verdict: 'confirmed', ship: true };
    // A lone secondary route (tool only) is a soft signal: ship but flag.
    return { verdict: 'single_source', ship: true, tagCap: 'verify_next' };
  },

  // Corroboration feeds the blend: judge = confirmed-source strength; signalA =
  // corroboration is handled by the engine's normalizedRrf term (more routes ->
  // higher RRF). signalB neutral. A strong primary source scores highest.
  scoreSignals: (cand) => {
    const strong = (cand as SignalCand).strong === true;
    return { judge: strong ? 90 : 55, signalA: 50, signalB: 50 };
  },

  // STRUCTURED OUTPUT — not a scalar. Reads the WHOLE ranked list to build the
  // signal object with confidence (from route agreement) and evidence_urls.
  project: (ranked, verdict): StrategyProjection => {
    if (ranked.length === 0 || !verdict || !verdict.ship) {
      return {
        value: 'no_signal',
        miss_reason: ranked.length === 0 ? 'no_candidates' : 'not_confirmed',
        signal: 'no_signal',
        confidence: 0,
        evidence_urls: [],
      };
    }
    // Corroboration = distinct routes that produced hiring evidence. The engine
    // hands the ranked candidate list; each candidate is one route's evidence.
    const hiring = ranked.filter((c) => c.value === 'hiring');
    const routeCount = hiring.length;
    const primary = hiring.some((c) => c.strong);
    const evidence_urls = [
      ...new Set(hiring.map((c) => c.url).filter((u): u is string => Boolean(u))),
    ];
    // Confidence: a primary-source confirmation OR ≥2 corroborating routes is
    // high; a lone secondary route is medium.
    const confidence = primary || routeCount >= 2 ? 0.9 : 0.5;
    return {
      value: 'hiring',
      miss_reason: null,
      signal: 'hiring',
      confidence,
      corroborating_routes: routeCount,
      primary_source: primary,
      evidence_urls,
    };
  },
};
