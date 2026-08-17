import { definePlay } from 'deepline';

type InputRow = {
  id: string;
  company: string;
  official_domain: string;
  question: string;
  query: string;
  claim_mode: 'dated_event' | 'customer_list' | 'official_quote' | 'classification' | 'other';
  required_pages: string;
};

type SearchItem = { title?: string; link?: string; snippet?: string; date?: string };
type PageFinding = {
  status?: 'answer' | 'abstain';
  answer?: string;
  evidence_excerpt?: string;
  confidence?: string;
  abstain_reason?: string;
};

function raw(result: any): any {
  const value = result?.toolResponse?.raw ?? {};
  return value?.data ?? value;
}

function host(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase().replace(/^www\./, '');
  } catch {
    return '';
  }
}

function parseFinding(result: any): PageFinding {
  const payload = raw(result);
  const value = payload?.json ?? payload?.data?.json ?? {};
  if (typeof value !== 'string') return value ?? {};
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}

function official(items: SearchItem[], domain: string): SearchItem[] {
  return items.filter((item) => {
    const itemHost = host(item.link ?? '');
    return itemHost === domain || itemHost.endsWith(`.${domain}`);
  });
}

function scrapeInput(url: string, row: InputRow): any {
  return {
    url,
    onlyMainContent: true,
    formats: [
      {
        type: 'json',
        prompt: `Research question: ${row.question}
Claim mode: ${row.claim_mode}.
Use only this official page. Return an answer only when this page explicitly
supports it, with a short exact excerpt. For dated_event, the excerpt must
state both the requested event and requested date. For customer_list, name only
customers explicitly named on the page. For official_quote, preserve the
official wording. For classification, ground the classification in the page's
product-delivery and buyer/customer language. If support is absent, return
status=abstain and explain the bounded reason; silence never proves a negative.`,
        schema: {
          type: 'object',
          additionalProperties: false,
          properties: {
            status: { type: 'string', enum: ['answer', 'abstain'] },
            answer: { type: 'string' },
            evidence_excerpt: { type: 'string' },
            confidence: { type: 'string' },
            abstain_reason: { type: 'string' },
          },
          required: ['status', 'answer', 'evidence_excerpt', 'confidence', 'abstain_reason'],
        },
      },
    ],
  };
}

function evidenceId(id: string, route: string, url: string): string {
  let hash = 2166136261;
  for (const character of `${id}|${route}|${url}`) {
    hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  }
  return `ev_${(hash >>> 0).toString(16).padStart(8, '0')}`;
}

export default definePlay(
  'company-question-research-kernel',
  async (ctx, input: { file: string }) => {
    const csv = await ctx.csv<InputRow>(input.file, {
      required: [
        'id',
        'company',
        'official_domain',
        'question',
        'query',
        'claim_mode',
        'required_pages',
      ],
    });
    const inputRows = await ctx
      .dataset('input_rows', csv)
      .run({ key: 'id', description: 'Preserve every research case.' });

    const searched = await ctx
      .dataset('search_results', inputRows)
      .withColumn('search', async (row, rowCtx) => {
        try {
          const result = await rowCtx.tools.execute({
            id: 'broad_search_index',
            tool: 'serper_google_search',
            input: { query: row.query, gl: 'us', hl: 'en', num: 10 },
            description: 'Discover official first-party evidence for the research question.',
          });
          const items: SearchItem[] = Array.isArray(raw(result)?.organic)
            ? raw(result).organic
            : [];
          return {
            status: items.length ? 'success' : 'no_result',
            query: row.query,
            items,
            official: official(items, row.official_domain),
          };
        } catch (error) {
          return {
            status: 'provider_error',
            query: row.query,
            items: [],
            official: [],
            error: String(error),
          };
        }
      })
      .run({ key: 'id', description: 'Public discovery with official-domain filtering.' });

    const fetched = await ctx
      .dataset('page_findings', searched)
      .withColumn('research', async (row: any, rowCtx) => {
        const limit = Math.max(1, Math.min(3, Number(row.required_pages) || 1));
        const broadCandidates: SearchItem[] = row.search.official.slice(0, limit);
        const broadPages: any[] = [];
        for (const candidate of broadCandidates) {
          try {
            const result = await rowCtx.tools.execute({
              id: 'broad_official_page',
              tool: 'firecrawl_scrape',
              input: scrapeInput(candidate.link ?? '', row),
              description: 'Fetch a selected official page and extract evidence-close support.',
            });
            broadPages.push({
              url: candidate.link ?? '',
              title: candidate.title ?? '',
              date: candidate.date ?? '',
              status: 'success',
              finding: parseFinding(result),
            });
          } catch (error) {
            broadPages.push({
              url: candidate.link ?? '',
              title: candidate.title ?? '',
              status: 'provider_error',
              error: String(error),
              finding: {},
            });
          }
        }

        const broadAnswered = broadPages.some(
          (page) => page.finding?.status === 'answer' && page.finding?.evidence_excerpt,
        );
        if (broadAnswered) {
          return { broadPages, supplemental: { status: 'skipped', query: '', page: null } };
        }

        const gapQuery = `site:${row.official_domain} ${row.question}`;
        try {
          const search = await rowCtx.tools.execute({
            id: 'gap_search_index',
            tool: 'serper_google_search',
            input: { query: gapQuery, gl: 'us', hl: 'en', num: 10 },
            description: 'Make one gap-only official-page discovery pass for unresolved evidence.',
          });
          const candidates = official(raw(search)?.organic ?? [], row.official_domain).filter(
            (candidate) => !broadPages.some((page) => page.url === candidate.link),
          );
          const candidate = candidates[0];
          if (!candidate?.link) {
            return { broadPages, supplemental: { status: 'no_result', query: gapQuery, page: null } };
          }
          const page = await rowCtx.tools.execute({
            id: 'gap_official_page',
            tool: 'firecrawl_scrape',
            input: scrapeInput(candidate.link, row),
            description: 'Fetch one distinct official page only for an unresolved claim.',
          });
          return {
            broadPages,
            supplemental: {
              status: 'success',
              query: gapQuery,
              page: {
                url: candidate.link,
                title: candidate.title ?? '',
                date: candidate.date ?? '',
                status: 'success',
                finding: parseFinding(page),
              },
            },
          };
        } catch (error) {
          return {
            broadPages,
            supplemental: { status: 'provider_error', query: gapQuery, page: null, error: String(error) },
          };
        }
      })
      .run({ key: 'id', description: 'Official-page evidence plus one gap-only follow-up.' });

    const rows = await fetched.materialize(100);
    const evidence: any[] = [];
    const claims: any[] = [];
    const coverage: any[] = [];
    for (const row of rows as any[]) {
      for (const item of row.search.official) {
        evidence.push({
          evidence_id: evidenceId(row.id, 'search_index', item.link ?? ''),
          id: row.id,
          route: 'search_index',
          url: item.link ?? '',
          title: item.title ?? '',
          excerpt: item.snippet ?? '',
          published_at: item.date ?? '',
          query: row.query,
          supports: 'Discovery evidence; page evidence is required for a material answer.',
        });
      }
      const pages = [
        ...row.research.broadPages.map((page: any) => ({ route: 'official_page_fetch', page })),
        ...(row.research.supplemental.page
          ? [{ route: 'gap_official_page', page: row.research.supplemental.page }]
          : []),
      ];
      for (const { route, page } of pages) {
        if (!page.finding?.evidence_excerpt) continue;
        evidence.push({
          evidence_id: evidenceId(row.id, route, page.url),
          id: row.id,
          route,
          url: page.url,
          title: page.title,
          excerpt: page.finding.evidence_excerpt,
          published_at: page.date ?? '',
          query: route === 'gap_official_page' ? row.research.supplemental.query : row.query,
          supports: page.finding.answer || page.finding.abstain_reason || '',
        });
      }
      const answered = pages.filter(
        ({ page }) => page.finding?.status === 'answer' && page.finding?.answer && page.finding?.evidence_excerpt,
      );
      const status = answered.length ? 'answer' : 'abstain';
      const answerEvidence = evidence.filter(
        (item) => item.id === row.id && item.route !== 'search_index',
      );
      claims.push({
        id: row.id,
        status,
        answer: status === 'answer' ? answered.map(({ page }) => page.finding.answer).join(' | ') : '',
        confidence: status === 'answer' ? answered[0].page.finding.confidence || 'medium' : 'medium',
        abstain_reason:
          status === 'abstain'
            ? 'No explicit first-party support after broad discovery and one bounded gap-only follow-up.'
            : '',
        supporting_evidence_ids: answerEvidence.map((item) => item.evidence_id).join('|'),
      });
      coverage.push({
        id: row.id,
        broad_search_status: row.search.status,
        official_result_count: row.search.official.length,
        broad_page_count: row.research.broadPages.length,
        supplemental_status: row.research.supplemental.status,
        final_status: status,
      });
    }

    const researchClaims = await ctx
      .dataset('research_claims', claims)
      .run({ key: 'id', description: 'One answer or explicit abstention per research case.' });
    const researchEvidence = await ctx
      .dataset('research_evidence', evidence)
      .run({ key: 'evidence_id', description: 'Search and official-page evidence.' });
    const sourceCoverage = await ctx
      .dataset('source_coverage', coverage)
      .run({ key: 'id', description: 'Broad and gap-pass coverage by research case.' });
    return { inputRows, searched, fetched, researchClaims, researchEvidence, sourceCoverage };
  },
  {
    description: 'Evidence-backed official-web company questions.',
    billing: { maxCreditsPerRun: 3 },
  },
);
