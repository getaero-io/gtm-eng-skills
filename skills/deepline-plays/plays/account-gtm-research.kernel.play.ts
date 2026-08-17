import { definePlay } from 'deepline';

type InputRow = {
  account_id: string;
  company_name: string;
  domain_hint: string;
  company_aliases?: string;
};

type SearchItem = {
  title?: string;
  link?: string;
  snippet?: string;
  date?: string;
};

type CompanyClaims = {
  what_they_sell?: string;
  what_they_sell_excerpt?: string;
  primary_buyer?: string;
  primary_buyer_excerpt?: string;
  market_language?: string;
};

type SignalClaims = {
  recent_signal?: string;
  recent_signal_date?: string;
  signal_excerpt?: string;
  company_identity_excerpt?: string;
};

function rawPayload(result: any): any {
  const raw = result?.toolResponse?.raw ?? {};
  return raw?.data ?? raw;
}

function extractedJson<T>(result: any): T {
  const payload = rawPayload(result);
  const value = payload?.json ?? payload?.data?.json ?? {};
  if (typeof value !== 'string') return value as T;
  try {
    return JSON.parse(value) as T;
  } catch {
    return {} as T;
  }
}

function organic(result: any): SearchItem[] {
  const items = rawPayload(result)?.organic;
  return Array.isArray(items) ? items : [];
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

function isOfficialUrl(url: string, domain: string): boolean {
  const pageHost = host(url);
  const targetHost = host(domain);
  return Boolean(pageHost && targetHost && (pageHost === targetHost || pageHost.endsWith(`.${targetHost}`)));
}

function normalizeWords(value: string): string {
  return value
    .toLowerCase()
    .replace(/\b(inc|llc|ltd|corp|corporation|company|co|north america|coffee)\b/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function identityLabels(row: InputRow): string[] {
  const labels = [normalizeWords(row.company_name)];
  for (const alias of (row.company_aliases ?? '').split('|')) {
    const value = normalizeWords(alias);
    if (value) labels.push(value);
  }
  return [...new Set(labels.filter((value) => value.length >= 4))];
}

function mentionsCompany(row: InputRow, value: string): boolean {
  const text = ` ${normalizeWords(value)} `;
  return identityLabels(row).some((label) => text.includes(` ${label} `));
}

function lookbackStart(referenceDate: string): string {
  const date = new Date(`${referenceDate}T00:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() - 365);
  return date.toISOString().slice(0, 10);
}

function inWindow(date: string, referenceDate: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(date) && date >= lookbackStart(referenceDate) && date <= referenceDate;
}

function validSignal(row: InputRow, claims: SignalClaims, referenceDate: string): boolean {
  return Boolean(
    claims.recent_signal &&
    claims.signal_excerpt &&
    claims.company_identity_excerpt &&
    inWindow(claims.recent_signal_date ?? '', referenceDate) &&
    mentionsCompany(row, claims.company_identity_excerpt),
  );
}

function eventScore(item: SearchItem, row: InputRow, officialDomain = ''): number {
  if (!mentionsCompany(row, `${item.title ?? ''} ${item.snippet ?? ''}`)) return Number.NEGATIVE_INFINITY;
  const title = item.title ?? '';
  const url = item.link ?? '';
  const text = `${title} ${item.snippet ?? ''}`;
  let score = 0;
  if (/\b(announce[ds]?|appoint(?:ed|s|ment)?|earnings|expand(?:ed|s|ing)?|introduc(?:e|es|ed|ing)|launch(?:ed|es)?|partner(?:ed|ship|s)?|raise[ds]?|funding round|result[s]?|redeem(?:ed|s|ption)?|acquir(?:e|ed|es|ing))\b/i.test(title)) score += 12;
  if (/\b(announce[ds]?|appoint(?:ed|s|ment)?|earnings|expand(?:ed|s|ing)?|introduc(?:e|es|ed|ing)|launch(?:ed|es)?|partner(?:ed|ship|s)?|raise[ds]?|funding round|result[s]?|redeem(?:ed|s|ption)?|acquir(?:e|ed|es|ing))\b/i.test(text)) score += 3;
  if (/\b(20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b/i.test(item.date ?? '')) score += 2;
  if (/\/(news|press|blog|announcement|media)\b/i.test(url)) score += 2;
  if (officialDomain && isOfficialUrl(url, officialDomain)) score += 2;
  if (/\b(profile|review|directory|job|career|linkedin|facebook|wikipedia|docs?)\b/i.test(`${title} ${url}`)) score -= 30;
  return score;
}

function companyPageInput(url: string): any {
  return {
    url,
    onlyMainContent: true,
    formats: [
      {
        type: 'json',
        prompt:
          'Using only this page, extract a concise statement of what the company sells, its explicit primary business buyer or user, and one useful exact line of customer or market language. Copy one short exact excerpt supporting each of the first two claims. Return empty strings when the page does not explicitly support a field.',
        schema: {
          type: 'object',
          additionalProperties: false,
          properties: {
            what_they_sell: { type: 'string' },
            what_they_sell_excerpt: { type: 'string' },
            primary_buyer: { type: 'string' },
            primary_buyer_excerpt: { type: 'string' },
            market_language: { type: 'string' },
          },
          required: [
            'what_they_sell',
            'what_they_sell_excerpt',
            'primary_buyer',
            'primary_buyer_excerpt',
            'market_language',
          ],
        },
      },
    ],
  };
}

function signalPageInput(row: InputRow, url: string, referenceDate: string): any {
  const labels = identityLabels(row).join(' or ');
  return {
    url,
    onlyMainContent: true,
    formats: [
      {
        type: 'json',
        prompt: `Using only this page, identify one company-level operating, hiring, product, funding, risk, or growth event for ${row.company_name} between ${lookbackStart(referenceDate)} and ${referenceDate}. Return a concise event description, exact YYYY-MM-DD event date, and one exact supporting excerpt. Also return a separate exact excerpt that explicitly names ${labels}. Customer reviews, individual complaints, directories, job listings, and generic profile pages are not company-level events: return empty strings for them. Return empty strings unless the page itself establishes the event, its date, and company identity.`,
        schema: {
          type: 'object',
          additionalProperties: false,
          properties: {
            recent_signal: { type: 'string' },
            recent_signal_date: { type: 'string' },
            signal_excerpt: { type: 'string' },
            company_identity_excerpt: { type: 'string' },
          },
          required: [
            'recent_signal',
            'recent_signal_date',
            'signal_excerpt',
            'company_identity_excerpt',
          ],
        },
      },
    ],
  };
}

function companyPageScore(item: SearchItem, domain: string): number {
  if (!item.link || !isOfficialUrl(item.link, domain)) return Number.NEGATIVE_INFINITY;
  const text = `${item.title ?? ''} ${item.snippet ?? ''}`;
  const url = item.link;
  let score = 0;
  if (/\b(product|platform|solution|customer|revenue|sales|compliance|observability|payment|automation)\b/i.test(text)) score += 8;
  if (/\/(product|platform|solution|customer|why-|use-cases?|about)\b/i.test(url)) score += 4;
  if (host(url) === host(domain) && new URL(url).pathname === '/') score += 2;
  if (/\b(contact|legal|privacy|terms|cookie|login|career|job|docs?)\b/i.test(`${text} ${url}`)) score -= 30;
  return score;
}

function bestCompanyPage(items: SearchItem[], domain: string): SearchItem | undefined {
  return items
    .map((item) => ({ item, score: companyPageScore(item, domain) }))
    .filter((candidate) => candidate.score > 0)
    .sort((left, right) => right.score - left.score)[0]?.item;
}

function bestEventCandidate(
  items: SearchItem[],
  row: InputRow,
  officialDomain = '',
  exceptUrl = '',
): SearchItem | undefined {
  return items
    .filter((item) => Boolean(item.link) && item.link !== exceptUrl)
    .map((item) => ({ item, score: eventScore(item, row, officialDomain) }))
    .filter((candidate) => candidate.score >= 7)
    .sort((left, right) => right.score - left.score)[0]?.item;
}

function bestIndependentCandidate(items: SearchItem[], row: InputRow): SearchItem | undefined {
  return items.find(
    (item) =>
      Boolean(item.link && item.snippet) &&
      !isOfficialUrl(item.link ?? '', row.domain_hint) &&
      mentionsCompany(row, `${item.title ?? ''} ${item.snippet ?? ''}`) &&
      !/\b(linkedin|facebook|wikipedia|directory|review|jobs?|careers?)\b/i.test(
        `${item.title ?? ''} ${item.link ?? ''}`,
      ),
  );
}

function evidenceId(accountId: string, phase: string, url: string, excerpt: string): string {
  const source = `${accountId}|${phase}|${url}|${excerpt}`;
  let hash = 2166136261;
  for (let index = 0; index < source.length; index += 1) {
    hash = Math.imul(hash ^ source.charCodeAt(index), 16777619);
  }
  return `ev_${(hash >>> 0).toString(16).padStart(8, '0')}`;
}

export default definePlay(
  'account-gtm-research-kernel',
  async (ctx, input: { file: string; referenceDate: string }) => {
    const csv = await ctx.csv<InputRow>(input.file, {
      required: ['account_id', 'company_name', 'domain_hint'],
    });
    const inputRows = await ctx
      .dataset('input_rows', csv)
      .run({ key: 'account_id', description: 'Preserve every account denominator row.' });
    if ((await inputRows.count()) > 25) {
      throw new Error('This bounded account-research kernel supports at most 25 rows per run.');
    }

    const broad = await ctx
      .dataset('account_research_broad', inputRows)
      .withColumn('broad_result', async (row: InputRow, rowCtx) => {
        const start = lookbackStart(input.referenceDate);
        const companyQuery = `site:${row.domain_hint} (products OR solutions OR platform OR customers) "${row.company_name}"`;
        const signalQuery = `site:${row.domain_hint} "${identityLabels(row)[0] ?? row.company_name}" (press OR news OR newsroom OR announce OR launch OR appoint OR partnership OR funding OR results) after:${start}`;
        const independentQuery = `"${row.company_name}" (${identityLabels(row)[0] ?? row.company_name} platform OR software OR product) -site:${row.domain_hint}`;
        let companyItems: SearchItem[] = [];
        let signalItems: SearchItem[] = [];
        let independentItems: SearchItem[] = [];
        let companyError = '';
        let signalError = '';
        let independentError = '';
        try {
          companyItems = organic(
            await rowCtx.tools.execute({
              id: 'account_company_search',
              tool: 'serper_google_search',
              input: { query: companyQuery, gl: 'us', hl: 'en', num: 5 },
              description: 'Discover a first-party product or customer page for this account.',
            }),
          );
        } catch (error) {
          companyError = String(error);
        }
        try {
          signalItems = organic(
            await rowCtx.tools.execute({
              id: 'account_official_signal_search',
              tool: 'serper_google_search',
              input: { query: signalQuery, gl: 'us', hl: 'en', num: 8 },
              description: 'Discover a recent first-party company event before using a broader source.',
            }),
          );
        } catch (error) {
          signalError = String(error);
        }
        try {
          independentItems = organic(
            await rowCtx.tools.execute({
              id: 'account_independent_search',
              tool: 'serper_google_search',
              input: { query: independentQuery, gl: 'us', hl: 'en', num: 8 },
              description: 'Find one independent public source that describes the account or its market.',
            }),
          );
        } catch (error) {
          independentError = String(error);
        }
        const companyPage = bestCompanyPage(companyItems, row.domain_hint) ?? {
          title: `${row.company_name} home page`,
          link: `https://${host(row.domain_hint)}/`,
        };
        const signalPage = bestEventCandidate(signalItems, row, row.domain_hint);
        const independentPage = bestIndependentCandidate(independentItems, row);
        let companyClaims: CompanyClaims = {};
        let signalClaims: SignalClaims = {};
        let companyPageError = '';
        let signalPageError = '';
        if (companyPage?.link) {
          try {
            companyClaims = extractedJson<CompanyClaims>(
              await rowCtx.tools.execute({
                id: 'account_company_page',
                tool: 'firecrawl_scrape',
                input: companyPageInput(companyPage.link),
                description: 'Extract attributable offering, buyer, and market language.',
              }),
            );
          } catch (error) {
            companyPageError = String(error);
          }
        }
        if (signalPage?.link) {
          try {
            signalClaims = extractedJson<SignalClaims>(
              await rowCtx.tools.execute({
                id: 'account_official_signal_page',
                tool: 'firecrawl_scrape',
                input: signalPageInput(row, signalPage.link, input.referenceDate),
                description: 'Verify event date, event detail, and company identity on the first-party page.',
              }),
            );
          } catch (error) {
            signalPageError = String(error);
          }
        }
        return {
          start,
          companyQuery,
          signalQuery,
          independentQuery,
          companyItems,
          signalItems,
          independentItems,
          companyPage,
          signalPage,
          independentPage,
          companyClaims,
          signalClaims,
          companyError,
          signalError,
          independentError,
          companyPageError,
          signalPageError,
        };
      })
      .run({ key: 'account_id', description: 'First-party account research plus an official dated-event route.' });

    const broadRows = await broad.materialize(25);
    const withBroadGate = broadRows.map((row: any) => ({
      ...row,
      official_signal_verified: validSignal(row, row.broad_result.signalClaims ?? {}, input.referenceDate),
    }));

    const finalDataset = await ctx
      .dataset('account_research_final', withBroadGate)
      .withColumn('fallback_signal_result', async (row: any, rowCtx) => {
        if (row.official_signal_verified) {
          return { status: 'skipped', query: '', page: undefined, claims: {} };
        }
        const query = `"${row.company_name}" (launch OR partnership OR funding OR hiring OR growth OR risk OR results) after:${row.broad_result.start}`;
        try {
          const items = organic(
            await rowCtx.tools.execute({
              id: 'account_fallback_signal_search',
              tool: 'serper_google_search',
              input: { query, gl: 'us', hl: 'en', num: 10 },
              description: 'Use a broader dated-event route only after first-party discovery lacked a verified event.',
            }),
          );
          const page = bestEventCandidate(items, row);
          if (!page?.link) return { status: 'no_result', query, items, page: undefined, claims: {} };
          const claims = extractedJson<SignalClaims>(
            await rowCtx.tools.execute({
              id: 'account_fallback_signal_page',
              tool: 'firecrawl_scrape',
              input: signalPageInput(row, page.link, input.referenceDate),
              description: 'Verify the fallback event, date, and target-company identity before accepting it.',
            }),
          );
          return {
            status: validSignal(row, claims, input.referenceDate) ? 'verified' : 'insufficient_evidence',
            query,
            items,
            page,
            claims,
          };
        } catch (error) {
          return { status: 'provider_error', query, page: undefined, claims: {}, error: String(error) };
        }
      })
      .run({
        key: 'account_id',
        description: 'One broader event route only for accounts unresolved by first-party evidence.',
      });
    const finalRows = await finalDataset.materialize(25);

    const accountRows: any[] = [];
    const evidenceRows: any[] = [];
    const coverageRows: any[] = [];
    for (const row of finalRows as any[]) {
      const broadResult = row.broad_result;
      const fallback = row.fallback_signal_result;
      const officialClaims: SignalClaims = broadResult.signalClaims ?? {};
      const fallbackClaims: SignalClaims = fallback.claims ?? {};
      const officialSignal = validSignal(row, officialClaims, input.referenceDate);
      const fallbackSignal = validSignal(row, fallbackClaims, input.referenceDate);
      const signalClaims = officialSignal ? officialClaims : fallbackClaims;
      const signalPage = officialSignal ? broadResult.signalPage : fallback.page;
      const companyClaims: CompanyClaims = broadResult.companyClaims ?? {};
      const offeringVerified = Boolean(companyClaims.what_they_sell && companyClaims.what_they_sell_excerpt);
      const buyerVerified = Boolean(companyClaims.primary_buyer && companyClaims.primary_buyer_excerpt);
      const languageVerified = Boolean(companyClaims.market_language);
      const signalVerified = officialSignal || fallbackSignal;
      const independentVerified = Boolean(
        broadResult.independentPage?.link && broadResult.independentPage?.snippet,
      );
      const claimText = `${companyClaims.what_they_sell ?? ''} ${companyClaims.primary_buyer ?? ''} ${companyClaims.market_language ?? ''}`.toLowerCase();
      const directGtmUseCase = /\b(sales|revenue|customer|crm|marketing|questionnaire)\b/.test(
        claimText,
      );
      const automationOrDataComplexity = /\b(ai|automation|platform|monitor|security|compliance|cloud|finance|data|risk)\b/.test(
        claimText,
      );
      const fitTier = offeringVerified && buyerVerified && directGtmUseCase
        ? 'high'
        : offeringVerified && buyerVerified && automationOrDataComplexity
          ? 'medium'
          : 'low';
      const privateDataJoin = fitTier === 'high'
        ? 'CRM account and opportunity history + warehouse product or risk events + prior enrichment/provider logs'
        : 'CRM account and opportunity history + warehouse engagement data + prior research/enrichment logs';
      const status = offeringVerified && buyerVerified && languageVerified && signalVerified && independentVerified
        ? 'complete'
        : 'insufficient_evidence';
      accountRows.push({
        account_id: row.account_id,
        company_name: row.company_name,
        domain: host(row.domain_hint),
        what_they_sell: offeringVerified ? companyClaims.what_they_sell : '',
        primary_buyer: buyerVerified ? companyClaims.primary_buyer : '',
        recent_signal: signalVerified ? signalClaims.recent_signal : '',
        recent_signal_date: signalVerified ? signalClaims.recent_signal_date : '',
        recent_signal_url: signalVerified ? signalPage?.link ?? '' : '',
        market_language: languageVerified ? companyClaims.market_language : '',
        market_language_url: languageVerified ? broadResult.companyPage?.link ?? '' : '',
        independent_evidence_url: independentVerified ? broadResult.independentPage.link : '',
        private_data_join: privateDataJoin,
        fit_tier: fitTier,
        fit_reason: directGtmUseCase
          ? 'Public evidence shows a direct sales, revenue, or customer-workflow use case; validate cross-source workflow demand in private data.'
          : automationOrDataComplexity
            ? 'Public evidence shows automation or data complexity, but the direct GTM-research workflow need requires private-data validation.'
            : 'Public evidence does not establish a direct reusable GTM-research or cross-source automation need.',
        research_status: status,
        signal_route: officialSignal ? 'first_party' : fallbackSignal ? 'broader_fallback' : 'unresolved',
      });
      const pushEvidence = (
        phase: string,
        sourceFamily: string,
        item: SearchItem | undefined,
        excerpt: string,
        query: string,
        publishedAt = '',
        admissionStatus = 'verified',
      ) => {
        if (!item?.link || !excerpt) return;
        evidenceRows.push({
          evidence_id: evidenceId(row.account_id, phase, item.link, excerpt),
          account_id: row.account_id,
          phase,
          source_family: sourceFamily,
          url: item.link,
          title: item.title ?? '',
          excerpt,
          published_at: publishedAt,
          query,
          provider_status: 'success',
          admission_status: admissionStatus,
        });
      };
      pushEvidence(
        'company',
        'official_page',
        broadResult.companyPage,
        [companyClaims.what_they_sell_excerpt, companyClaims.primary_buyer_excerpt, companyClaims.market_language]
          .filter(Boolean)
          .join(' | '),
        broadResult.companyQuery,
      );
      pushEvidence(
        'independent_market_candidate',
        'independent_public_search',
        broadResult.independentPage,
        broadResult.independentPage?.snippet ?? '',
        broadResult.independentQuery,
        broadResult.independentPage?.date ?? '',
        independentVerified ? 'verified' : 'rejected',
      );
      pushEvidence(
        'official_signal_candidate',
        'first_party_event_candidate',
        broadResult.signalPage,
        `${broadResult.signalPage?.title ?? ''} ${broadResult.signalPage?.snippet ?? ''}`.trim(),
        broadResult.signalQuery,
        broadResult.signalPage?.date ?? '',
        officialSignal ? 'verified' : 'rejected',
      );
      pushEvidence(
        'fallback_signal_candidate',
        'independent_event_candidate',
        fallback.page,
        `${fallback.page?.title ?? ''} ${fallback.page?.snippet ?? ''}`.trim(),
        fallback.query,
        fallback.page?.date ?? '',
        fallbackSignal ? 'verified' : 'rejected',
      );
      if (signalVerified) {
        pushEvidence(
          officialSignal ? 'official_signal' : 'fallback_signal',
          officialSignal ? 'first_party_event' : 'independent_event',
          signalPage,
          `${signalClaims.signal_excerpt} | ${signalClaims.company_identity_excerpt}`,
          officialSignal ? broadResult.signalQuery : fallback.query,
          signalClaims.recent_signal_date,
          'verified',
        );
      }
      coverageRows.push({
        account_id: row.account_id,
        company_name: row.company_name,
        offering_verified: offeringVerified,
        buyer_verified: buyerVerified,
        market_language_verified: languageVerified,
        dated_signal_verified: signalVerified,
        independent_evidence_verified: independentVerified,
        independent_error: broadResult.independentError ?? '',
        selected_signal_route: officialSignal ? 'first_party' : fallbackSignal ? 'broader_fallback' : 'unresolved',
        unresolved_reason: signalVerified ? '' : 'No page passed date, event, and direct target-company identity gates.',
      });
    }

    const accountResearch = await ctx
      .dataset('account_research', accountRows)
      .run({ key: 'account_id', description: 'One evidence-backed GTM research row per account.' });
    const accountEvidence = await ctx
      .dataset('account_evidence', evidenceRows)
      .run({ key: 'evidence_id', description: 'Attributable evidence ledger for account research.' });
    const sourceCoverage = await ctx
      .dataset('source_coverage', coverageRows)
      .run({ key: 'account_id', description: 'Per-account claim and route coverage, including honest unresolved signals.' });

    const deliveryResearchRows = accountRows.map((row) => ({
      company_name: row.company_name,
      domain: row.domain,
      what_they_sell: row.what_they_sell,
      primary_buyer: row.primary_buyer,
      recent_signal: row.recent_signal,
      recent_signal_date: row.recent_signal_date,
      recent_signal_url: row.recent_signal_url,
      market_language: row.market_language,
      market_language_url: row.market_language_url,
      independent_evidence_url: row.independent_evidence_url,
      private_data_join: row.private_data_join,
      fit_tier: row.fit_tier,
      fit_reason: row.fit_reason,
      research_status: row.research_status,
    }));
    const deliveryEvidenceRows = evidenceRows.map((row) => ({
      company_name:
        accountRows.find((account) => account.account_id === row.account_id)?.company_name ?? '',
      source_family: row.source_family,
      url: row.url,
      title_or_label: row.title,
      excerpt: row.excerpt,
      published_at: row.published_at,
      query: row.query,
      provenance: `account-gtm-research-kernel/account_evidence/${row.admission_status}`,
    }));
    const accountResearchDelivery = await ctx
      .dataset('account_research_delivery', deliveryResearchRows)
      .run({ key: 'domain', description: 'Customer-facing account-research projection.' });
    const accountEvidenceDelivery = await ctx
      .dataset('account_evidence_delivery', deliveryEvidenceRows)
      .run({ key: 'url', description: 'Customer-facing evidence projection.' });

    return {
      inputRows,
      broad,
      finalDataset,
      accountResearch,
      accountEvidence,
      sourceCoverage,
      accountResearchDelivery,
      accountEvidenceDelivery,
    };
  },
  {
    description:
      'Bounded public account research: offering, buyer language, dated company signal, private-data join, and fit hypothesis.',
    billing: { maxCreditsPerRun: 4 },
  },
);
