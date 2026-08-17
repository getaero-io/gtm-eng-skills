import { definePlay } from 'deepline';

type InputRow = {
  account_id: string;
  company_name: string;
  domain_hint: string;
};

type SearchItem = { title?: string; link?: string; snippet?: string; date?: string };
type Extracted = {
  company_name?: string;
  what_they_sell?: string;
  what_they_sell_excerpt?: string;
  primary_buyer?: string;
  primary_buyer_excerpt?: string;
};

const claims = ['canonical_domain', 'what_they_sell', 'primary_buyer'] as const;

function rawPayload(result: any): any {
  const raw = result?.toolResponse?.raw ?? {};
  return raw?.data ?? raw;
}

function host(value: string): string {
  try {
    return new URL(value.startsWith('http') ? value : `https://${value}`).hostname
      .toLowerCase()
      .replace(/^www\./, '');
  } catch {
    return '';
  }
}

function officialCandidate(items: SearchItem[], row: InputRow): SearchItem | undefined {
  const hint = host(row.domain_hint);
  const tokens = row.company_name
    .toLowerCase()
    .replace(/\b(inc|llc|corp|corporation)\b/g, '')
    .match(/[a-z0-9]+/g) ?? [];
  return items.find((item) => host(item.link ?? '') === hint) ?? items.find((item) => {
    const hay = `${item.title ?? ''} ${item.snippet ?? ''}`.toLowerCase();
    return Boolean(item.link) && tokens.every((token) => hay.includes(token));
  });
}

function extractedJson(result: any): Extracted {
  const payload = rawPayload(result);
  const value = payload?.json ?? payload?.data?.json ?? {};
  if (typeof value !== 'string') return value;
  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}

function evidenceId(
  accountId: string,
  phase: string,
  mechanism: string,
  url: string,
  excerpt: string,
): string {
  const source = `${accountId}|${phase}|${mechanism}|${url}|${excerpt}`;
  let hash = 2166136261;
  for (let index = 0; index < source.length; index++) {
    hash = Math.imul(hash ^ source.charCodeAt(index), 16777619);
  }
  return `ev_${(hash >>> 0).toString(16).padStart(8, '0')}`;
}

function scrapeInput(url: string): any {
  return {
    url,
    onlyMainContent: true,
    formats: [
      {
        type: 'json',
        prompt:
          'Using only this page, identify the company and extract concise, evidence-close statements for what it sells and its primary buyer. Copy one short exact page excerpt supporting each statement. Return an empty string when the page does not explicitly support a field.',
        schema: {
          type: 'object',
          additionalProperties: false,
          properties: {
            company_name: { type: 'string' },
            what_they_sell: { type: 'string' },
            what_they_sell_excerpt: { type: 'string' },
            primary_buyer: { type: 'string' },
            primary_buyer_excerpt: { type: 'string' },
          },
          required: [
            'company_name',
            'what_they_sell',
            'what_they_sell_excerpt',
            'primary_buyer',
            'primary_buyer_excerpt',
          ],
        },
      },
    ],
  };
}

export default definePlay(
  'company-research-kernel',
  async (ctx, input: { file: string; referenceDate: string }) => {
    const csv = await ctx.csv<InputRow>(input.file, {
      required: ['account_id', 'company_name', 'domain_hint'],
    });
    const inputRows = await ctx
      .dataset('input_rows', csv)
      .run({ key: 'account_id', description: 'Preserve every input row.' });

    const broad = await ctx
      .dataset('research_broad', inputRows)
      .withColumn('broad_result', async (row, rowCtx) => {
        const query = `\"${row.company_name}\" official website products customers`;
        let searchStatus = 'success';
        let searchError = '';
        let searchItems: SearchItem[] = [];
        try {
          const result = await rowCtx.tools.execute({
            id: 'broad_search_index',
            tool: 'serper_google_search',
            input: { query, gl: 'us', hl: 'en', num: 5 },
            description: 'Find current official company web evidence.',
          });
          const payload = rawPayload(result);
          searchItems = Array.isArray(payload?.organic) ? payload.organic : [];
          if (!searchItems.length) searchStatus = 'no_result';
        } catch (error) {
          searchStatus = 'provider_error';
          searchError = String(error);
        }
        const candidate = officialCandidate(searchItems, row);
        const candidateUrl = candidate?.link ?? `https://${host(row.domain_hint)}/`;
        let scrapeStatus = 'success';
        let scrapeError = '';
        let extracted: Extracted = {};
        try {
          const result = await rowCtx.tools.execute({
            id: 'broad_official_page',
            tool: 'firecrawl_scrape',
            input: scrapeInput(candidateUrl),
            description: 'Read the candidate official page for product and buyer evidence.',
          });
          extracted = extractedJson(result);
          if (!Object.values(extracted).some(Boolean)) scrapeStatus = 'no_result';
        } catch (error) {
          scrapeStatus = 'provider_error';
          scrapeError = String(error);
        }
        return {
          query,
          searchStatus,
          searchError,
          searchItems,
          candidate,
          candidateUrl,
          canonicalDomain: host(candidateUrl),
          scrapeStatus,
          scrapeError,
          extracted,
        };
      })
      .run({ key: 'account_id', description: 'Broad search plus official-page retrieval.' });

    const broadRows = await broad.materialize(100);
    const withBroad = broadRows.map((row: any) => {
      const result = row.broad_result;
      const supported = {
        canonical_domain: Boolean(result.candidate && result.canonicalDomain),
        what_they_sell: Boolean(
          result.extracted?.what_they_sell && result.extracted?.what_they_sell_excerpt,
        ),
        primary_buyer: Boolean(
          result.extracted?.primary_buyer && result.extracted?.primary_buyer_excerpt,
        ),
      };
      return {
        ...row,
        broad_supported: supported,
        broad_gaps: claims.filter((key) => !supported[key]),
      };
    });

    const finalRowsDs = await ctx
      .dataset('research_final', withBroad)
      .withColumn('supplemental_result', async (row: any, rowCtx) => {
        if (!row.broad_gaps.length) return { status: 'skipped', query: '', url: '', extracted: {} };
        const query = `site:${row.broad_result.canonicalDomain || host(row.domain_hint)} \"${row.company_name}\" solutions industries customers`;
        try {
          const search = await rowCtx.tools.execute({
            id: 'supplemental_recovered_search',
            tool: 'serper_google_search',
            input: { query, gl: 'us', hl: 'en', num: 5 },
            description:
              'Find a different official product, solution, or customer page for unresolved claims.',
          });
          const items: SearchItem[] = rawPayload(search)?.organic ?? [];
          const targetHost = row.broad_result.canonicalDomain || host(row.domain_hint);
          const page =
            items.find(
              (item) =>
                host(item.link ?? '') === targetHost &&
                host(item.link ?? '') !== '' &&
                item.link !== row.broad_result.candidateUrl,
            ) ?? items.find((item) => host(item.link ?? '') === targetHost);
          if (!page?.link) return { status: 'no_result', query, url: '', extracted: {} };
          const scrape = await rowCtx.tools.execute({
            id: 'supplemental_official_page',
            tool: 'firecrawl_scrape',
            input: scrapeInput(page.link),
            description: 'Read a distinct official page only for unresolved claims.',
          });
          const extracted = extractedJson(scrape);
          return {
            status: Object.values(extracted).some(Boolean) ? 'success' : 'no_result',
            query,
            url: page.link,
            title: page.title ?? '',
            extracted,
          };
        } catch (error) {
          return { status: 'provider_error', query, url: '', extracted: {}, error: String(error) };
        }
      })
      .run({
        key: 'account_id',
        description: 'One bounded, materially different pass for unresolved claims only.',
      });
    const finalRows = await finalRowsDs.materialize(100);

    const evidenceRows: any[] = [];
    const claimRows: any[] = [];
    const coverageRows: any[] = [];
    const gapRows: any[] = [];
    for (const row of finalRows as any[]) {
      const broadResult = row.broad_result;
      const supplemental = row.supplemental_result;
      const searchExcerpt = `${broadResult.candidate?.title ?? ''}${
        broadResult.candidate?.snippet ? ` — ${broadResult.candidate.snippet}` : ''
      }`.trim();
      if (broadResult.candidate?.link && searchExcerpt) {
        evidenceRows.push({
          evidence_id: evidenceId(
            row.account_id,
            'broad',
            'serper_google_search',
            broadResult.candidate.link,
            searchExcerpt,
          ),
          account_id: row.account_id,
          phase: 'broad',
          mechanism_id: 'serper_google_search',
          mechanism_class: 'search_index',
          source_family: 'public_search',
          url: broadResult.candidate.link,
          title: broadResult.candidate.title ?? '',
          excerpt: searchExcerpt,
          published_at: broadResult.candidate.date ?? '',
          query: broadResult.query,
          provider_status: broadResult.searchStatus,
        });
      }
      const addPageEvidence = (
        phase: string,
        url: string,
        title: string,
        extracted: Extracted,
        query: string,
        status: string,
      ) => {
        for (const [key, excerpt] of [
          ['what_they_sell', extracted.what_they_sell_excerpt],
          ['primary_buyer', extracted.primary_buyer_excerpt],
        ] as const) {
          if (excerpt) {
            evidenceRows.push({
              evidence_id: evidenceId(row.account_id, phase, 'firecrawl_scrape', url, excerpt),
              account_id: row.account_id,
              phase,
              mechanism_id: 'firecrawl_scrape',
              mechanism_class: 'page_fetch',
              source_family: 'official_site',
              url,
              title,
              excerpt,
              published_at: '',
              query,
              provider_status: status,
              claim_key: key,
            });
          }
        }
      };
      addPageEvidence(
        'broad',
        broadResult.candidateUrl,
        broadResult.candidate?.title ?? '',
        broadResult.extracted ?? {},
        broadResult.query,
        broadResult.scrapeStatus,
      );
      if (supplemental.status !== 'skipped') {
        addPageEvidence(
          'supplemental',
          supplemental.url,
          supplemental.title ?? '',
          supplemental.extracted ?? {},
          supplemental.query,
          supplemental.status,
        );
      }
      const uniqueEvidence = () => evidenceRows.filter((item) => item.account_id === row.account_id);
      for (const key of claims) {
        const broadSupported = row.broad_supported[key];
        let value = '';
        if (key === 'canonical_domain') value = broadSupported ? broadResult.canonicalDomain : '';
        else {
          value = broadSupported
            ? (broadResult.extracted?.[key] ?? '')
            : (supplemental.extracted?.[key] ?? '');
        }
        let ids: string[] = [];
        if (key === 'canonical_domain') {
          ids = uniqueEvidence()
            .filter(
              (item) =>
                item.phase === 'broad' &&
                item.mechanism_id === 'serper_google_search' &&
                host(item.url) === value,
            )
            .map((item) => item.evidence_id);
        } else {
          ids = uniqueEvidence()
            .filter((item) =>
              broadSupported
                ? item.phase === 'broad' &&
                  (item.claim_key === key || item.mechanism_id === 'serper_google_search')
                : item.phase === 'supplemental' && item.claim_key === key,
            )
            .map((item) => item.evidence_id);
        }
        const supported = Boolean(value && ids.length);
        claimRows.push({
          account_id: row.account_id,
          claim_key: key,
          broad_status: broadSupported
            ? 'supported'
            : broadResult.searchStatus === 'provider_error' || broadResult.scrapeStatus === 'provider_error'
              ? 'provider_error'
              : 'gap',
          final_status: supported ? 'supported' : 'insufficient_evidence',
          claim_text: supported ? value : '',
          supporting_evidence_ids: ids.join('|'),
          insufficient_reason: supported
            ? ''
            : supplemental.status === 'provider_error'
              ? 'supplemental provider error'
              : 'no explicit public evidence found after broad and bounded supplemental retrieval',
        });
        if (!broadSupported) {
          gapRows.push({
            gap_id: `${row.account_id}|${key}`,
            account_id: row.account_id,
            claim_key: key,
            trigger_status:
              broadResult.searchStatus === 'provider_error' ||
              broadResult.scrapeStatus === 'provider_error'
                ? 'provider_error'
                : 'gap',
            trigger_evidence_ids: '',
            supplemental_query: supplemental.query ?? '',
            supplemental_mechanism_id: 'serper_google_search|firecrawl_scrape',
            outcome_status: supported ? 'supported' : 'insufficient_evidence',
            outcome_evidence_ids: ids.join('|'),
          });
        }
      }
      coverageRows.push({
        account_id: row.account_id,
        phase: 'broad',
        mechanism_id: 'serper_google_search',
        mechanism_class: 'search_index',
        provider_status: broadResult.searchStatus,
        result_count: broadResult.searchItems.length,
        useful_evidence_count: broadResult.candidate ? 1 : 0,
        remaining_claim_gaps: row.broad_gaps.join('|'),
      });
      coverageRows.push({
        account_id: row.account_id,
        phase: 'broad',
        mechanism_id: 'firecrawl_scrape',
        mechanism_class: 'page_fetch',
        provider_status: broadResult.scrapeStatus,
        result_count: Object.values(broadResult.extracted ?? {}).some(Boolean) ? 1 : 0,
        useful_evidence_count: [
          broadResult.extracted?.what_they_sell_excerpt,
          broadResult.extracted?.primary_buyer_excerpt,
        ].filter(Boolean).length,
        remaining_claim_gaps: row.broad_gaps.join('|'),
      });
      if (supplemental.status !== 'skipped') {
        coverageRows.push({
          account_id: row.account_id,
          phase: 'supplemental',
          mechanism_id: 'serper_google_search|firecrawl_scrape',
          mechanism_class: 'recovered_identity_page_fetch',
          provider_status: supplemental.status,
          result_count: supplemental.url ? 1 : 0,
          useful_evidence_count: [
            supplemental.extracted?.what_they_sell_excerpt,
            supplemental.extracted?.primary_buyer_excerpt,
          ].filter(Boolean).length,
          remaining_claim_gaps: claims
            .filter(
              (key) =>
                !claimRows.find(
                  (claim) =>
                    claim.account_id === row.account_id &&
                    claim.claim_key === key &&
                    claim.final_status === 'supported',
                ),
            )
            .join('|'),
        });
      }
    }
    for (const row of evidenceRows) delete row.claim_key;
    const researchClaims = await ctx
      .dataset('research_claims', claimRows)
      .run({ key: (row) => `${row.account_id}|${row.claim_key}`, description: 'One row per input and required claim.' });
    const researchEvidence = await ctx
      .dataset('research_evidence', evidenceRows)
      .run({ key: 'evidence_id', description: 'Public evidence supporting claims.' });
    const sourceCoverage = await ctx
      .dataset('source_coverage', coverageRows)
      .run({
        key: (row) => `${row.account_id}|${row.phase}|${row.mechanism_id}`,
        description: 'Per-mechanism retrieval coverage.',
      });
    const supplementalGaps = await ctx
      .dataset('supplemental_gaps', gapRows)
      .run({ key: 'gap_id', description: 'Bounded follow-up audit for every broad gap.' });
    return {
      inputRows,
      broad,
      finalRows: finalRowsDs,
      researchClaims,
      researchEvidence,
      sourceCoverage,
      supplementalGaps,
    };
  },
  {
    description: 'Evidence-backed company domain, offering, and primary-buyer research.',
    billing: { maxCreditsPerRun: 2.9 },
  },
);
