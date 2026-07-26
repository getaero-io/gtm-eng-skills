// ===========================================================================
// CORROBORATION — reconcile the NUMBER, not just rank the sources.
// ===========================================================================
//
// Pure, deterministic, model-free. The research strategy ranks sources by
// relevance; this reconciles the quantitative FACT those sources make. Truth of
// a number = how many INDEPENDENT credible sources agree on the same value, not
// which source ranks highest. A field note from a real run: "$965B valuation"
// came from ONE domain and "$380B" from THREE — ranking put a credible source
// #1 but nothing decided which number was true. This module decides.
//
// The pipeline mirrors the research engine's shape:
//   extractFigures  -> pull normalized numeric claims from a finding's text
//   corroborate     -> cluster findings by figure (tolerance band), count the
//                      DISTINCT registrable domains behind each cluster, rank by
//                      independent-source count then by source quality.
//
// No I/O, no Date.now, no Math.random. Additive to the research projection — it
// never removes the ranked findings, it adds a `corroboration` field beside them.

// A finding as this module reads it: the URL (for the domain = independence key)
// plus the free-text (title + snippet) the figures are extracted from.
export type CorroborationFinding = {
  url?: string | null;
  title?: string | null;
  snippet?: string | null;
  // Optional per-source quality (0..1) so a cluster backed by better sources
  // wins a tie on independent-source count. Defaults to 1.
  quality?: number | null;
};

// A normalized numeric claim. `value` is in the unit's BASE magnitude (usd:
// dollars, percent: the raw percent number, count: the raw number). `unit`
// discriminates money from percentages from bare counts so $380B never fuses
// with 380%.
export type FigureUnit = 'usd' | 'percent' | 'count';

export type Figure = {
  value: number;
  unit: FigureUnit;
  // The exact text the figure was read from (for evidence / display).
  raw: string;
};

export type FigureCluster = {
  value: number;
  unit: FigureUnit;
  // Distinct registrable domains that asserted a figure in this cluster's band.
  sources: string[];
  // Independent-source count = sources.length. Named for legibility downstream.
  independentSources: number;
  // Max source quality across the cluster (tiebreaker on equal source count).
  quality: number;
  // A representative raw string for display (the first-seen exact text).
  raw: string;
};

export type CorroborationResult = {
  // The consensus figure: the cluster with the most independent sources. null
  // when no findings carried an extractable figure.
  consensus: {
    value: number;
    unit: FigureUnit;
    raw: string;
    sources: string[];
    // 'high' when >=2 independent domains agree; 'low' when a lone source.
    confidence: 'high' | 'low';
  } | null;
  // Every OTHER figure cluster, ranked, each flagged with its source count. A
  // lone-source dissenting number (the "$965B" case) surfaces here with
  // independent_sources = 1 so a reader sees it was never corroborated.
  dissent: Array<{
    value: number;
    unit: FigureUnit;
    raw: string;
    sources: string[];
    independent_sources: number;
    // 'high' when this dissenting value itself has >=2 independent sources
    // (a genuine disagreement between two corroborated numbers); 'low' when it
    // is lone-source (a dubious outlier).
    confidence: 'high' | 'low';
  }>;
};

// Clusters within this relative band fuse (rerank on the same claim). 2% covers
// rounding across sources ("$380B" vs "$379.5B" vs "$385B") without merging
// genuinely different numbers ($380B vs $965B).
export const FIGURE_TOLERANCE = 0.02;

// ---------------------------------------------------------------------------
// Registrable-domain extraction (independence key). Duplicated intentionally
// from the research URL canonicalizer's spirit but reduced to the REGISTRABLE
// domain — two findings from example.com/a and example.com/b are the SAME
// source, so they must NOT count as two independent corroborations.
// ---------------------------------------------------------------------------
export function registrableDomain(url: unknown): string | null {
  if (typeof url !== 'string') return null;
  let host = url.trim().toLowerCase();
  if (!host) return null;
  host = host
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('/')[0]!
    .split('?')[0]!
    .split('#')[0]!
    .replace(/\.$/, '');
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(host)) return null;
  // Registrable domain = last two labels (acme.com from news.acme.com). This is
  // a deliberate heuristic: it treats a multi-label public suffix (.co.uk) as
  // three labels, which slightly over-merges a handful of ccTLDs but never
  // splits one publisher into two fake "independent" sources.
  const labels = host.split('.');
  if (labels.length <= 2) return host;
  return labels.slice(-2).join('.');
}

// ---------------------------------------------------------------------------
// Figure extraction.
// ---------------------------------------------------------------------------

// Magnitude multipliers for money / large numbers. Handles billion/bn/B,
// million/mn/M, thousand/k. Case-insensitive; the caller lowercases.
const MAGNITUDES: Array<{ re: RegExp; factor: number }> = [
  { re: /^(?:trillion|tn|t)$/i, factor: 1e12 },
  { re: /^(?:billion|bn|b)$/i, factor: 1e9 },
  { re: /^(?:million|mn|mm|m)$/i, factor: 1e6 },
  { re: /^(?:thousand|k)$/i, factor: 1e3 },
];

function magnitudeFactor(token: string | undefined | null): number {
  if (!token) return 1;
  for (const { re, factor } of MAGNITUDES) {
    if (re.test(token)) return factor;
  }
  return 1;
}

// A number written with optional thousands separators -> a plain float.
function parseNumeric(raw: string): number | null {
  const cleaned = raw.replace(/,/g, '');
  if (!/^\d+(?:\.\d+)?$/.test(cleaned)) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

// Money: `$380 billion`, `$65B`, `$30bn`, `USD 12.5 million`, `$1,200`. The
// currency marker ($ or a leading/trailing USD) is required so a bare "380"
// count is not misread as dollars.
const MONEY_RE =
  /(?:\$|\busd\s*)(\d+(?:,\d{3})*(?:\.\d+)?)\s*(trillion|billion|million|thousand|tn|bn|mm|mn|[tbmk])?\b/gi;

// Percentages: `65%`, `12.5 percent`.
const PERCENT_RE = /(\d+(?:\.\d+)?)\s*(?:%|percent\b)/gi;

// Plain large magnitude numbers WITH an explicit magnitude word (`30 million
// users`, `2 billion`). A bare integer with no marker is too ambiguous to be a
// quantitative claim, so it is intentionally NOT captured.
const COUNT_RE =
  /\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(trillion|billion|million|thousand|tn|bn|mm|mn)\b/gi;

// Extract candidate normalized figures from a finding's title + snippet. Money
// and percent are unambiguous; a plain magnitude number is only captured when
// it is NOT already part of a money match (so `$380 billion` yields one usd
// figure, not also a count).
export function extractFigures(text: string): Figure[] {
  if (typeof text !== 'string' || !text.trim()) return [];
  const figures: Figure[] = [];

  // Track [start,end) spans already claimed by money so COUNT does not double-count.
  const moneySpans: Array<[number, number]> = [];

  for (const match of text.matchAll(MONEY_RE)) {
    const numeric = parseNumeric(match[1] ?? '');
    if (numeric == null) continue;
    const value = numeric * magnitudeFactor(match[2]);
    figures.push({ value, unit: 'usd', raw: match[0].trim() });
    const start = match.index ?? 0;
    moneySpans.push([start, start + match[0].length]);
  }

  for (const match of text.matchAll(PERCENT_RE)) {
    const numeric = parseNumeric(match[1] ?? '');
    if (numeric == null) continue;
    figures.push({ value: numeric, unit: 'percent', raw: match[0].trim() });
  }

  for (const match of text.matchAll(COUNT_RE)) {
    const start = match.index ?? 0;
    const end = start + match[0].length;
    // Skip if this magnitude number overlaps a money span (already counted).
    const overlapsMoney = moneySpans.some(([ms, me]) => start < me && end > ms);
    if (overlapsMoney) continue;
    const numeric = parseNumeric(match[1] ?? '');
    if (numeric == null) continue;
    const value = numeric * magnitudeFactor(match[2]);
    figures.push({ value, unit: 'count', raw: match[0].trim() });
  }

  return figures;
}

// The text a finding contributes to figure extraction.
function findingText(f: CorroborationFinding): string {
  return `${f.title ?? ''} ${f.snippet ?? ''}`.trim();
}

// Two figures corroborate when same unit AND within the tolerance band. Zero is
// handled by absolute equality (a relative band around 0 is undefined).
function withinBand(a: number, b: number): boolean {
  if (a === b) return true;
  const denom = Math.max(Math.abs(a), Math.abs(b));
  if (denom === 0) return false;
  return Math.abs(a - b) / denom <= FIGURE_TOLERANCE;
}

// ---------------------------------------------------------------------------
// Corroboration: cluster by figure, count independent domains, rank.
// ---------------------------------------------------------------------------
export function corroborate(
  findings: CorroborationFinding[],
): CorroborationResult {
  // Per (unit) accumulate clusters. Each cluster tracks the set of registrable
  // domains that asserted a figure in its band and the max source quality.
  type MutableCluster = {
    value: number;
    unit: FigureUnit;
    raw: string;
    domains: Set<string>;
    quality: number;
    // Kept for a stable representative value (weighted toward first-seen).
    sampleCount: number;
  };
  const clusters: MutableCluster[] = [];

  for (const finding of findings) {
    const domain = registrableDomain(finding.url);
    // A finding with no resolvable domain still contributes its figure but its
    // "source" is unknown — it cannot count toward INDEPENDENT corroboration, so
    // we skip it for the source count. (An anonymous claim is not a source.)
    const figures = extractFigures(findingText(finding));
    if (figures.length === 0) continue;
    const quality =
      typeof finding.quality === 'number' && Number.isFinite(finding.quality)
        ? finding.quality
        : 1;
    // Dedup figures WITHIN one finding by unit+band so one source asserting the
    // same number twice is not double-counted.
    const seenInFinding: Figure[] = [];
    for (const figure of figures) {
      const dup = seenInFinding.some(
        (s) => s.unit === figure.unit && withinBand(s.value, figure.value),
      );
      if (dup) continue;
      seenInFinding.push(figure);

      const existing = clusters.find(
        (c) => c.unit === figure.unit && withinBand(c.value, figure.value),
      );
      if (existing) {
        if (domain) existing.domains.add(domain);
        existing.quality = Math.max(existing.quality, quality);
        existing.sampleCount += 1;
      } else {
        clusters.push({
          value: figure.value,
          unit: figure.unit,
          raw: figure.raw,
          domains: domain ? new Set([domain]) : new Set(),
          quality,
          sampleCount: 1,
        });
      }
    }
  }

  const ranked: FigureCluster[] = clusters
    .map((c) => ({
      value: c.value,
      unit: c.unit,
      raw: c.raw,
      sources: [...c.domains].sort(),
      independentSources: c.domains.size,
      quality: c.quality,
    }))
    .sort(
      (a, b) =>
        b.independentSources - a.independentSources ||
        b.quality - a.quality ||
        b.value - a.value,
    );

  if (ranked.length === 0) {
    return { consensus: null, dissent: [] };
  }

  const [top, ...rest] = ranked;
  return {
    consensus: {
      value: top!.value,
      unit: top!.unit,
      raw: top!.raw,
      sources: top!.sources,
      confidence: top!.independentSources >= 2 ? 'high' : 'low',
    },
    dissent: rest.map((c) => ({
      value: c.value,
      unit: c.unit,
      raw: c.raw,
      sources: c.sources,
      independent_sources: c.independentSources,
      confidence: c.independentSources >= 2 ? 'high' : 'low',
    })),
  };
}
