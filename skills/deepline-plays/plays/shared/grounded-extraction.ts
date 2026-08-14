import {
  bindResearchEvidenceToSource,
  type ResearchEvidence,
} from './research-experiment';

export type GroundedPersonCandidate = {
  name: string;
  relation: string;
  excerpt: string;
  evidence: ResearchEvidence;
};

type SourceTextInput = {
  source: string;
  independenceClass: string;
  rawSourceText: unknown;
};

const DEFAULT_RELATIONS = [
  'owner',
  'co-owner',
  'founder',
  'co-founder',
  'proprietor',
  'president',
  'chief executive officer',
  'ceo',
  'founded',
  'started',
  'owns',
] as const;

const DEFAULT_NAME_STOPWORDS = new Set([
  'about',
  'business',
  'canvas',
  'chief',
  'company',
  'contact',
  'corporation',
  'district',
  'executive',
  'farm',
  'farms',
  'founder',
  'fuel',
  'gas',
  'group',
  'history',
  'interview',
  'llc',
  'magazine',
  'manager',
  'oil',
  'officer',
  'owner',
  'podcast',
  'propane',
  'president',
  'rebels',
  'region',
  'services',
  'story',
  'team',
  'vice',
]);

const NAME_TOKEN = String.raw`[\p{Lu}][\p{L}\p{M}'’-]{1,30}`;
const SUFFIX = String.raw`(?:Jr\.?|Sr\.?|II|III|IV)`;
const SINGLE_NAME = String.raw`${NAME_TOKEN}(?:\s+${NAME_TOKEN}){1,2}(?:\s+${SUFFIX})?`;
const COUPLE_NAME = String.raw`${NAME_TOKEN}\s+(?:and|&)\s+${NAME_TOKEN}(?:\s+${NAME_TOKEN})?(?:\s+${SUFFIX})?`;
const PERSON_NAME = String.raw`(?:${COUPLE_NAME}|${SINGLE_NAME})`;

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function normalizeToken(value: string): string {
  return value
    .toLocaleLowerCase('en-US')
    .replace(/[^\p{L}\p{N}]+/gu, '')
    .trim();
}

function organizationTokens(value: string | undefined): Set<string> {
  if (!value) return new Set();
  return new Set(
    value
      .split(/\s+/u)
      .map(normalizeToken)
      .filter(
        (token) => token.length >= 4 && !DEFAULT_NAME_STOPWORDS.has(token),
      ),
  );
}

function looksLikeGroundedPersonName(input: {
  name: string;
  organizationName?: string;
  extraStopwords?: readonly string[];
}): boolean {
  const name = input.name.trim().replace(/\s+/g, ' ');
  if (!name || name.length > 90 || /\d/u.test(name)) return false;
  if (/['’]s\b/iu.test(name)) return false;
  if (/\b(?:at|for|from|of|the)\b/iu.test(name)) return false;

  const tokens = name.split(/\s+/u).map(normalizeToken).filter(Boolean);
  const stopwords = new Set([
    ...DEFAULT_NAME_STOPWORDS,
    ...(input.extraStopwords ?? []).map(normalizeToken),
  ]);
  if (tokens.some((token) => stopwords.has(token))) return false;

  // A person may legitimately lend one surname to a company. Reject only when
  // two or more substantial tokens make the candidate look like the company.
  const company = organizationTokens(input.organizationName);
  const overlap = tokens.filter((token) => company.has(token));
  if (overlap.length >= 2) return false;
  return true;
}

function sentenceWindow(
  sourceText: string,
  start: number,
  end: number,
  maximumChars: number,
): string {
  const leftBoundary = Math.max(
    sourceText.lastIndexOf('.', start - 1),
    sourceText.lastIndexOf('!', start - 1),
    sourceText.lastIndexOf('?', start - 1),
    sourceText.lastIndexOf('\n', start - 1),
  );
  const rightCandidates = [
    sourceText.indexOf('.', end),
    sourceText.indexOf('!', end),
    sourceText.indexOf('?', end),
    sourceText.indexOf('\n', end),
  ].filter((index) => index >= 0);
  const rightBoundary = rightCandidates.length
    ? Math.min(...rightCandidates) + 1
    : sourceText.length;
  let excerpt = sourceText.slice(leftBoundary + 1, rightBoundary).trim();
  if (excerpt.length <= maximumChars) return excerpt;

  const padding = Math.max(0, maximumChars - (end - start));
  const windowStart = Math.max(0, start - Math.floor(padding / 2));
  excerpt = sourceText
    .slice(windowStart, Math.min(sourceText.length, windowStart + maximumChars))
    .trim();
  return excerpt;
}

function normalizeWindowSize(input: { maximumChars?: number }): number {
  return input.maximumChars ?? 600;
}

function readSourceText(input: SourceTextInput): string | null {
  return typeof input.rawSourceText === 'string' &&
    input.rawSourceText.trim().length
    ? input.rawSourceText
    : null;
}

function buildPersonEvidence(input: {
  source: string;
  independenceClass: string;
  url: string | undefined;
  rawSourceText: string;
  excerpt: string;
  authority: 'authoritative' | 'supporting' | undefined;
}): ResearchEvidence | null {
  return bindResearchEvidenceToSource({
    source: input.source,
    independenceClass: input.independenceClass,
    url: input.url,
    excerpt: input.excerpt,
    rawSourceText: input.rawSourceText,
    authority: input.authority,
  });
}

/**
 * Bind a literal context window around an already-known source anchor. This is
 * useful after search or scraping identifies a name, role, date, or keyword.
 */
export function bindGroundedExcerptWindow(input: {
  source: string;
  independenceClass: string;
  rawSourceText: unknown;
  anchor: unknown;
  url?: string;
  maximumChars?: number;
  authority?: 'authoritative' | 'supporting';
}): ResearchEvidence | null {
  if (typeof input.anchor !== 'string' || !input.anchor) {
    return null;
  }
  const sourceText = readSourceText(input);
  if (!sourceText) return null;
  const start = sourceText.indexOf(input.anchor);
  if (start < 0) return null;
  const excerpt = sentenceWindow(
    sourceText,
    start,
    start + input.anchor.length,
    normalizeWindowSize(input),
  );
  return buildPersonEvidence({
    source: input.source,
    independenceClass: input.independenceClass,
    url: input.url,
    rawSourceText: sourceText,
    excerpt,
    authority: input.authority,
  });
}

/**
 * Extract role-linked full names from literal source text. The helper is a
 * candidate generator, not an owner/current-role oracle: the caller still
 * applies its task-specific claim policy and may use a reject-only judge.
 */
export function extractGroundedPersonCandidates(input: {
  source: string;
  independenceClass: string;
  rawSourceText: unknown;
  url?: string;
  organizationName?: string;
  relations?: readonly string[];
  extraNameStopwords?: readonly string[];
  authority?: 'authoritative' | 'supporting';
  maximumExcerptChars?: number;
}): GroundedPersonCandidate[] {
  const sourceText = readSourceText(input);
  if (!sourceText) {
    return [];
  }
  const relations = (input.relations ?? DEFAULT_RELATIONS)
    .map((value) => value.trim())
    .filter(Boolean);
  if (!relations.length) return [];
  const relation = relations.map(escapeRegex).join('|');
  const leadingTitleRelations = relations
    .filter((value) =>
      /^(?:co-)?(?:owner|founder)$|^(?:proprietor|president|chief executive officer|ceo)$/iu.test(
        value,
      ),
    )
    .map(escapeRegex)
    .join('|');
  const patterns = [
    new RegExp(
      String.raw`(?<name>${PERSON_NAME})\s*(?:,|—|-|\bis\b|\bwas\b)?\s*(?:the\s+)?(?<relation>${relation})\b`,
      'giu',
    ),
    ...(leadingTitleRelations
      ? [
          new RegExp(
            String.raw`\b(?<relation>${leadingTitleRelations})\s+(?<name>${PERSON_NAME})\b`,
            'giu',
          ),
        ]
      : []),
    new RegExp(
      String.raw`\b(?<relation>founded|started|owned)\s+by\s+(?<name>${PERSON_NAME})\b`,
      'giu',
    ),
  ];
  const candidates = new Map<string, GroundedPersonCandidate>();

  for (const pattern of patterns) {
    for (const match of sourceText.matchAll(pattern)) {
      const name = match.groups?.name
        ?.trim()
        .replace(/\s+/g, ' ')
        .replace(/\.$/u, '');
      const matchedRelation = match.groups?.relation
        ?.trim()
        .toLocaleLowerCase('en-US');
      if (!matchedRelation) continue;
      if (
        !name ||
        !looksLikeGroundedPersonName({
          name,
          organizationName: input.organizationName,
          extraStopwords: input.extraNameStopwords,
        })
      ) {
        continue;
      }
      const start = match.index ?? 0;
      const excerpt = sentenceWindow(
        sourceText,
        start,
        start + match[0].length,
        input.maximumExcerptChars ?? 600,
      );
      const evidence = buildPersonEvidence({
        source: input.source,
        independenceClass: input.independenceClass,
        url: input.url,
        rawSourceText: sourceText,
        excerpt,
        authority: input.authority,
      });
      if (!evidence) continue;
      const key = `${normalizeToken(name)}:${normalizeToken(matchedRelation)}`;
      if (!candidates.has(key)) {
        candidates.set(key, {
          name,
          relation: matchedRelation,
          excerpt,
          evidence,
        });
      }
    }
  }

  return [...candidates.values()];
}

/** A reject-only judge may remove known IDs, but can never add a fact. */
export function applyRejectOnlyDecision<T extends { id: string }>(input: {
  candidates: readonly T[];
  retainedIds: readonly string[];
}): T[] {
  const rawCandidateIds = input.candidates.map((candidate) => candidate.id);
  const candidateIds = new Set(rawCandidateIds);
  if (candidateIds.size !== rawCandidateIds.length) {
    throw new Error('Reject-only candidates must have unique IDs.');
  }
  const unknown = input.retainedIds.filter((id) => !candidateIds.has(id));
  if (unknown.length) {
    throw new Error(
      `Reject-only decision attempted to add unknown candidate IDs: ${unknown.join(', ')}`,
    );
  }
  const retained = new Set(input.retainedIds);
  return input.candidates.filter((candidate) => retained.has(candidate.id));
}
