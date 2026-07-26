// A RESEARCH ResolutionStrategy for the route-fanout engine — the topic-based
// generalization. It resolves a RESEARCH QUESTION about an entity ("what did
// this company raise recently?", "who are their competitors?") into a RANKED
// LIST of corroborated findings, through the SAME engine, over a HETEROGENEOUS
// mix of routes (web-search tools + a page fetch + a deeplineagent read).
//
// This is last30days' fan-out → fuse → rerank, specialized to research and made
// TOPIC-AGNOSTIC. Nothing here is about hiring or emails or any one domain:
//   - canonical key = the normalized URL, so the same source found by two
//     routes fuses into one finding (last30days fusion.py keys on URL).
//   - the JUDGE is RELEVANCE, not identity: a finding is trustworthy when it is
//     on-topic (token overlap with the question) AND mentions the entity
//     (last30days rerank.py entity-miss penalty). No paid call.
//   - `project` returns a RANKED LIST: { findings: [...], top_answer,
//     evidence_urls, confidence } — the list-shaped output, not a scalar.
//
// The routes (which search providers, which pages) are the FORK SLOT in the
// play — this strategy just parses their shapes and judges relevance. Keep it
// general: do not bake a topic in here. The row carries the question.
//
// Discover live refs before hardcoding routes: `deepline tools search "web
// search"` (serper_search, exa_search), `deepline tools search "scrape"`.

import {
  type NormalizedVerdict,
  type ResolutionStrategy,
  type StrategyCandidate,
  type StrategyProjection,
} from './route-fanout-core';
import { corroborate, type CorroborationFinding } from './corroboration';

// ---------------------------------------------------------------------------
// Pure adapters.
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

// The research row: a QUESTION plus optional entity to disambiguate. Falls back
// to company_name/domain as the topic so a plain company row still works.
type ResearchRow = {
  query?: string;
  question?: string;
  entity?: string;
  company_name?: string;
  domain?: string;
};

// A finding candidate. `value` is the CANONICAL URL (fusion key). `title` /
// `snippet` are the evidence; `relevance` (0..1) is the token-overlap score
// against the question, stamped at extraction time (where the row is in scope).
// `entityMiss` marks a finding that does not mention the entity — the engine
// penalizes it (rerank.py ENTITY_MISS_PENALTY) rather than dropping it.
type ResearchCand = StrategyCandidate & {
  title?: string;
  snippet?: string;
  url?: string;
  relevance?: number;
  entityMiss?: boolean;
};

const REL_MIN = 0.18; // below this a result is off-topic noise (relevance.py bar)

// ---------------------------------------------------------------------------
// Topic-agnostic relevance (last30days relevance.py, condensed). Query-centric
// token overlap with stopword removal; exact-phrase bonus. No domain knowledge.
// ---------------------------------------------------------------------------
const STOPWORDS = new Set([
  'the',
  'a',
  'an',
  'to',
  'for',
  'how',
  'is',
  'in',
  'of',
  'on',
  'and',
  'with',
  'from',
  'by',
  'at',
  'this',
  'that',
  'it',
  'what',
  'are',
  'do',
  'can',
  'its',
  'be',
  'or',
  'not',
  'no',
  'so',
  'if',
  'but',
  'about',
  'all',
  'just',
  'get',
  'has',
  'have',
  'was',
  'will',
  'their',
  'they',
  'them',
]);

function tokenize(text: string): Set<string> {
  const words = text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 1 && !STOPWORDS.has(w));
  return new Set(words);
}

// 0..1 relevance of `text` to `query`. Coverage of query tokens, with a small
// exact-phrase bonus. Empty query -> neutral 0.5.
export function relevanceScore(query: string, text: string): number {
  const q = tokenize(query);
  if (q.size === 0) return 0.5;
  const t = tokenize(text);
  let overlap = 0;
  for (const token of q) if (t.has(token)) overlap += 1;
  if (overlap === 0) return 0;
  const coverage = overlap / q.size;
  const normQuery = query
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  const normText = text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ');
  const phraseBonus = normQuery && normText.includes(normQuery) ? 0.15 : 0;
  return Math.min(1, Math.round((coverage + phraseBonus) * 100) / 100);
}

// The research question for a row: explicit query/question, else the entity or
// company topic. Never empty (falls back to the domain).
function questionFor(row: ResearchRow): string {
  return (
    row.query?.trim() ||
    row.question?.trim() ||
    [row.entity, row.company_name].filter(Boolean).join(' ').trim() ||
    row.domain?.trim() ||
    ''
  );
}

function entityFor(row: ResearchRow): string {
  return (row.entity || row.company_name || row.domain || '')
    .trim()
    .toLowerCase();
}

// Canonical URL = registrable path without protocol/www/query/hash/trailing
// slash, so the same page from two routes fuses to one finding.
export function canonicalizeUrl(raw: unknown): string | null {
  if (typeof raw !== 'string') return null;
  const s = raw.trim().toLowerCase();
  if (!s) return null;
  const stripped = s
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('#')[0]!
    .split('?')[0]!
    .replace(/\/+$/, '');
  return stripped || null;
}

// Build a finding from a title/snippet/url against the row's question.
function toFinding(
  row: ResearchRow,
  title: string,
  snippet: string,
  url: string | undefined,
): ResearchCand | null {
  const canonical = canonicalizeUrl(url);
  if (!canonical) return null;
  const question = questionFor(row);
  const entity = entityFor(row);
  const hay = `${title} ${snippet}`.trim();
  const relevance = relevanceScore(question, hay);
  const entityMiss = entity ? !hay.toLowerCase().includes(entity) : false;
  return {
    value: canonical,
    haystack: hay || title || canonical,
    title: title || undefined,
    snippet: snippet || undefined,
    url,
    relevance,
    entityMiss,
  };
}

// tool route (serper/exa/generic web search): organic results -> findings.
function extractSearch(result: unknown, row: ResearchRow): ResearchCand[] {
  const raw = rawResponse(result);
  const list =
    (Array.isArray(raw.organic) && raw.organic) ||
    (Array.isArray(raw.results) && raw.results) ||
    (Array.isArray(raw.data) && raw.data) ||
    [];
  const findings: ResearchCand[] = [];
  for (const item of list) {
    const r = asRecord(item);
    const title = (typeof r.title === 'string' && r.title) || '';
    const snippet =
      (typeof r.snippet === 'string' && r.snippet) ||
      (typeof r.text === 'string' && r.text) ||
      (typeof r.description === 'string' && r.description) ||
      '';
    const url =
      (typeof r.link === 'string' && r.link) ||
      (typeof r.url === 'string' && r.url) ||
      undefined;
    const finding = toFinding(row, title, snippet, url);
    if (finding) findings.push(finding);
  }
  return findings;
}

// fetch route: a fetched page -> one finding (the page itself as evidence).
function extractFetch(result: unknown, row: ResearchRow): ResearchCand[] {
  const raw = rawResponse(result);
  const data = asRecord(raw.data);
  const meta = asRecord(raw.metadata ?? data.metadata);
  const page =
    (typeof raw.markdown === 'string' && raw.markdown) ||
    (typeof data.markdown === 'string' && data.markdown) ||
    (typeof raw.bodyText === 'string' && raw.bodyText) ||
    '';
  const url =
    (typeof meta.sourceURL === 'string' && meta.sourceURL) ||
    (typeof meta.url === 'string' && meta.url) ||
    (typeof raw.url === 'string' && raw.url) ||
    undefined;
  const title = (typeof meta.title === 'string' && meta.title) || '';
  if (!page) return [];
  const finding = toFinding(row, title, page.slice(0, 400), url);
  return finding ? [finding] : [];
}

// agent route: deeplineagent returns { extracted_json: { findings: [{title,
// url, snippet}] } } or free text with a source URL.
function extractAgent(result: unknown, row: ResearchRow): ResearchCand[] {
  const raw = rawResponse(result);
  const extracted = asRecord(raw.extracted_json);
  const list = Array.isArray(extracted.findings) ? extracted.findings : [];
  const findings: ResearchCand[] = [];
  for (const item of list) {
    const r = asRecord(item);
    const title = (typeof r.title === 'string' && r.title) || '';
    const snippet =
      (typeof r.snippet === 'string' && r.snippet) ||
      (typeof r.summary === 'string' && r.summary) ||
      '';
    const url = (typeof r.url === 'string' && r.url) || undefined;
    const finding = toFinding(row, title, snippet, url);
    if (finding) findings.push(finding);
  }
  return findings;
}

export const researchStrategy: ResolutionStrategy<ResearchCand> = {
  id: 'research',

  // A candidate is finding-shaped if it is a URL string or an object with one.
  isCandidateShaped: (raw) => {
    if (typeof raw === 'string') return canonicalizeUrl(raw) != null;
    const r = asRecord(raw);
    return canonicalizeUrl(r.url) != null || canonicalizeUrl(r.link) != null;
  },

  canonicalize: (raw) => {
    if (typeof raw === 'string') return canonicalizeUrl(raw);
    const r = asRecord(raw);
    return canonicalizeUrl(r.url ?? r.link);
  },

  extractCandidates: (routeResult, row, routeKind) => {
    const r = row as ResearchRow;
    if (routeKind === 'fetch') return extractFetch(routeResult, r);
    if (routeKind === 'agent') return extractAgent(routeResult, r);
    return extractSearch(routeResult, r);
  },

  // JUDGE = RELEVANCE. On-topic findings pass; off-topic noise is gated out. The
  // entity-miss penalty is applied in scoreSignals (a penalty, not a drop, per
  // rerank.py) so a strong on-topic source without the exact entity token still
  // ranks — just lower.
  identityGate: async (cand) => {
    const rel = (cand as ResearchCand).relevance ?? 0;
    if (rel >= REL_MIN) return { ok: true };
    return {
      ok: false,
      reason: `off-topic (relevance ${rel.toFixed(2)} < ${REL_MIN})`,
    };
  },

  // The winning finding: ship when it cleared the relevance gate. A lone
  // low-relevance survivor is flagged verify_next.
  readVerdict: (validatorResult): NormalizedVerdict => {
    const cand = validatorResult as ResearchCand;
    if (!cand) return { verdict: 'no_findings', ship: false };
    const rel = cand.relevance ?? 0;
    if (cand.entityMiss)
      return { verdict: 'off_entity', ship: true, tagCap: 'verify_next' };
    if (rel >= 0.4) return { verdict: 'relevant', ship: true };
    return { verdict: 'weak', ship: true, tagCap: 'verify_next' };
  },

  // Relevance drives the blend; an entity miss takes the rerank.py penalty.
  scoreSignals: (cand) => {
    const c = cand as ResearchCand;
    const rel = c.relevance ?? 0;
    const judge = Math.round(rel * 100) - (c.entityMiss ? 25 : 0);
    return {
      judge: Math.max(0, judge),
      signalA: Math.round(rel * 100),
      signalB: 50,
    };
  },

  // RANKED LIST output. Reads the whole fused, judged list and returns the top
  // findings with their evidence — the list-shaped projection.
  project: (ranked, verdict): StrategyProjection => {
    const relevant = ranked.filter((c) => {
      const rel = (c as ResearchCand).relevance ?? 0;
      return rel >= REL_MIN;
    });
    if (relevant.length === 0 || !verdict || !verdict.ship) {
      return {
        value: 'no_findings',
        miss_reason: ranked.length === 0 ? 'no_candidates' : 'off_topic',
        findings: [],
        top_answer: null,
        evidence_urls: [],
        confidence: 0,
      };
    }
    const findings = relevant.slice(0, 8).map((c) => {
      const r = c as ResearchCand;
      return {
        title: r.title ?? null,
        url: r.url ?? r.value,
        snippet: r.snippet ?? null,
        relevance: r.relevance ?? 0,
        entity_miss: r.entityMiss === true,
      };
    });
    const evidence_urls = [
      ...new Set(
        relevant
          .map((c) => (c as ResearchCand).url)
          .filter((u): u is string => Boolean(u)),
      ),
    ];
    const top = relevant[0] as ResearchCand;
    // Confidence: high when the top finding is strongly on-topic AND ≥2 sources
    // corroborate the topic; medium otherwise.
    const corroborating = relevant.length;
    const confidence =
      (top.relevance ?? 0) >= 0.4 && corroborating >= 2
        ? 0.9
        : (top.relevance ?? 0) >= 0.4
          ? 0.6
          : 0.4;

    // FIGURE CORROBORATION (additive). Ranking the SOURCES does not decide which
    // NUMBER is true. When the findings carry extractable quantitative claims
    // ($ amounts, %, magnitudes), reconcile them: cluster by value, count the
    // distinct independent domains behind each, and surface the consensus figure
    // (>=2 independent domains) with lone-source outliers flagged as dissent.
    // This never removes a ranked finding — it adds a `corroboration` field.
    const corroborationFindings: CorroborationFinding[] = relevant.map((c) => {
      const r = c as ResearchCand;
      return {
        url: r.url ?? r.value,
        title: r.title ?? null,
        snippet: r.snippet ?? null,
        quality: r.relevance ?? null,
      };
    });
    const figureCorroboration = corroborate(corroborationFindings);
    // Only attach when at least one finding actually carried a figure — a purely
    // qualitative research answer leaves the field null (no false precision).
    const corroboration =
      figureCorroboration.consensus !== null ? figureCorroboration : null;

    return {
      value: top.url ?? top.value,
      miss_reason: null,
      findings,
      top_answer: top.title ?? top.snippet ?? top.value,
      corroborating_sources: corroborating,
      evidence_urls,
      confidence,
      corroboration,
    };
  },
};
