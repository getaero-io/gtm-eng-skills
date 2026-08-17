import { definePlay } from 'deepline';
import {
  bindSelection,
  createRouteExperiment,
  selectRoutes,
  type RetrievedItemInput,
  type RetrievalRoute,
} from './shared/route-experiment';

/**
 * Copy this kernel for one current senior person at each named account.
 *
 * Before running, describe both literal tools in the live catalog. They are
 * deliberately current hints, not permanent contracts. Change only the two
 * adapter functions if the schema or result path differs.
 */

type Account = Record<string, unknown> & {
  account_id: string;
  company_name: string;
  domain: string;
};

type StructuredPerson = {
  fullName?: string;
  firstName?: string;
  lastName?: string;
  title?: string;
  companyName?: string;
  companyDomain?: string;
  linkedinUrl?: string;
};

type PublicResult = {
  title?: string;
  link?: string;
  snippet?: string;
};

type PublicPayload = { organic?: PublicResult[] };

// Edit these to the user's exact accepted title family. Keep the candidate
// search broad enough to include title spelling variants, then gate locally.
const ROLE_TERMS = [
  'revenue operations',
  'sales operations',
  'gtm operations',
  'go-to-market operations',
];
const SENIORITY_TERMS = [
  'chief',
  'vp',
  'vice president',
  'head',
  'director',
  'senior director',
  'global head',
];

const clean = (value: unknown): string =>
  String(value ?? '').replace(/\s+/g, ' ').trim();
const normalized = (value: unknown): string =>
  clean(value).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const compactDomain = (domain: string): string =>
  normalized(domain.replace(/\.[^.]+$/, ''));

function companyMatches(text: string, row: Account): boolean {
  const candidate = normalized(text);
  return (
    candidate.includes(normalized(row.company_name)) ||
    candidate.includes(compactDomain(row.domain))
  );
}

function acceptedTitle(value: string): boolean {
  const candidate = normalized(value);
  return (
    ROLE_TERMS.some((term) => candidate.includes(normalized(term))) &&
    SENIORITY_TERMS.some((term) => candidate.includes(normalized(term)))
  );
}

function hostClass(url: string): string {
  try {
    return `public-host:${new URL(url).hostname.replace(/^www\./, '')}`;
  } catch {
    return 'public-host:unknown';
  }
}

function differentHost(left: string, right: string): boolean {
  return hostClass(left) !== hostClass(right) && hostClass(right) !== 'public-host:unknown';
}

function publicResultText(result: PublicResult): string {
  return `${clean(result.title)} ${clean(result.snippet)}`;
}

function nameFromResult(result: PublicResult): string {
  const first = clean(result.title)
    .split(/\s+[|–—-]\s+/)[0]
    ?.trim();
  return /^[A-Z][\p{L}'’-]+(?:\s+[A-Z][\p{L}'’.-]+){1,3}$/u.test(first ?? '')
    ? first
    : '';
}

function titleFromResult(result: PublicResult): string {
  const text = publicResultText(result);
  const candidates = text.split(/[|.;]/).map(clean).filter(Boolean);
  return candidates.find(acceptedTitle) ?? '';
}

function verificationIdentifiesCandidate(
  result: PublicResult,
  name: string,
): boolean {
  const fullName = normalized(name);
  const resultTitle = normalized(result.title);
  const resultText = normalized(publicResultText(result));
  if (!fullName || !resultText.includes(fullName)) return false;
  // A named title page for another RevOps person can list the candidate in a
  // related-people widget. It is not independent evidence for this candidate.
  if (acceptedTitle(resultTitle) && !resultTitle.includes(fullName)) return false;
  return true;
}

async function publicCandidateSearch(
  rowCtx: { tools: { execute: Function } },
  query: string,
): Promise<PublicResult[]> {
  const response = await rowCtx.tools.execute({
    id: 'public_candidate_search',
    tool: 'serper_google_search',
    input: { query, gl: 'us', hl: 'en', page: 1, num: 8 },
    description: 'Find public candidate and current-role evidence.',
  });
  const raw = response.toolResponse.raw as PublicPayload;
  return Array.isArray(raw.organic) ? raw.organic : [];
}

async function independentRoleSearch(
  rowCtx: { tools: { execute: Function } },
  query: string,
): Promise<PublicResult[]> {
  const response = await rowCtx.tools.execute({
    id: 'independent_current_role_check',
    tool: 'serper_google_search',
    input: { query, gl: 'us', hl: 'en', page: 1, num: 8 },
    description: 'Find independent public current-role evidence.',
  });
  const raw = response.toolResponse.raw as PublicPayload;
  return Array.isArray(raw.organic) ? raw.organic : [];
}

async function independentCurrentRoleCheck(
  row: Account,
  rowCtx: { tools: { execute: Function } },
  name: string,
  title: string,
  discoveryUrl: string,
): Promise<PublicResult | null> {
  const query = `"${name}" "${row.company_name}" "${title}" -site:linkedin.com`;
  const results = await independentRoleSearch(rowCtx, query);
  return (
    results.find((result) => {
      const url = clean(result.link);
      const text = publicResultText(result);
      return (
        Boolean(url) &&
        differentHost(discoveryUrl, url) &&
        companyMatches(text, row) &&
        verificationIdentifiesCandidate(result, name) &&
        acceptedTitle(text)
      );
    }) ?? null
  );
}

function toRetrievedItem(args: {
  row: Account;
  name: string;
  title: string;
  discoveryUrl: string;
  discoveryText: string;
  verification: PublicResult;
  routeId: string;
  mechanismClass: string;
  sourceQuery: string;
}): RetrievedItemInput {
  const verificationUrl = clean(args.verification.link);
  const verificationText = publicResultText(args.verification);
  const evidence = [
    {
      source: args.routeId,
      independenceClass:
        args.mechanismClass === 'structured_lookup'
          ? 'structured-people-index'
          : hostClass(args.discoveryUrl),
      strength: 'weak' as const,
      url: args.discoveryUrl,
      text: args.discoveryText,
      mechanismId: args.routeId,
      mechanismClass: args.mechanismClass,
      providerStatus: 'ok' as const,
    },
    {
      source: 'independent-current-role-check',
      independenceClass: hostClass(verificationUrl),
      strength: 'weak' as const,
      url: verificationUrl,
      text: verificationText,
      mechanismId: 'independent_current_role_check',
      mechanismClass: 'public_search_and_extract',
      providerStatus: 'ok' as const,
    },
  ];
  const excerpt = `${args.name} — ${args.title} at ${args.row.company_name}. ${verificationText}`;
  return {
    id: `${args.row.account_id}:${normalized(args.name)}`,
    label: `${args.name} — ${args.title}`,
    title: args.title,
    url: args.discoveryUrl,
    snippet: excerpt,
    relevance: 1,
    sourceQuality: 0.9,
    facts: {
      name: { value: args.name, evidence },
      title: { value: args.title, evidence },
      company: { value: args.row.company_name, evidence },
    },
    evidence,
    attributes: {
      name: args.name,
      title: args.title,
      discovery_url: args.discoveryUrl,
      verification_url: verificationUrl,
      evidence_excerpt: excerpt,
      source_strategy: args.routeId,
      source_query: args.sourceQuery,
    },
  };
}

const routes = [
  {
    id: 'structured_company_people',
    mechanismId: 'structured_company_people',
    mechanismClass: 'structured_lookup',
    sourceFamilies: ['structured-people-index', 'public-current-role-check'],
    queryFamily: 'known domain plus broad role family, then independent public check',
    estimatedCreditsPerRow: 0,
    maxItems: 1,
    retrieve: async ({ row, rowCtx }) => {
      // Current catalog hint: free company-scoped Prime-DB people search.
      // Confirm its exact schema before keeping this adapter.
      const response = await rowCtx.tools.execute({
        id: 'structured_candidates',
        tool: 'dropleads_search_people',
        input: {
          filters: {
            companyDomains: [row.domain],
            jobTitles: ROLE_TERMS,
          },
          pagination: { page: 1, limit: 5 },
        },
        description: 'Find a small company-scoped senior-person candidate pool.',
      });
      const people = (await response.extractedLists.leads
        .get()
        .materialize(5)) as StructuredPerson[];
      const person = people.find((candidate) => {
        const name = clean(candidate.fullName || `${candidate.firstName ?? ''} ${candidate.lastName ?? ''}`);
        return (
          Boolean(name) &&
          acceptedTitle(clean(candidate.title)) &&
          companyMatches(
            `${clean(candidate.companyName)} ${clean(candidate.companyDomain)}`,
            row,
          )
        );
      });
      if (!person) return { items: [], sourceOutcome: 'no-results' as const };
      const name = clean(person.fullName || `${person.firstName ?? ''} ${person.lastName ?? ''}`);
      const title = clean(person.title);
      const discoveryUrl = clean(person.linkedinUrl);
      if (!discoveryUrl) return { items: [], sourceOutcome: 'partial' as const };
      const verification = await independentCurrentRoleCheck(
        row,
        rowCtx,
        name,
        title,
        discoveryUrl,
      );
      if (!verification) return { items: [], sourceOutcome: 'no-results' as const };
      return [
        toRetrievedItem({
          row,
          name,
          title,
          discoveryUrl,
          discoveryText: `${name} — ${title} at ${row.company_name}`,
          verification,
          routeId: 'structured_company_people',
          mechanismClass: 'structured_lookup',
          sourceQuery: `domain=${row.domain}; role family=${ROLE_TERMS.join(', ')}`,
        }),
      ];
    },
  },
  {
    id: 'public_serp_people',
    mechanismId: 'public_serp_people',
    mechanismClass: 'public_search_and_extract',
    sourceFamilies: ['public-serp', 'independent-public-artifact'],
    queryFamily: 'public candidate search plus a distinct-host current-role check',
    estimatedCreditsPerRow: 0.16,
    maxItems: 1,
    retrieve: async ({ row, rowCtx }) => {
      const roleQuery = ROLE_TERMS.map((term) => `"${term}"`).join(' OR ');
      const query = `"${row.company_name}" (${roleQuery}) (VP OR "Vice President" OR Head OR Director)`;
      const results = await publicCandidateSearch(rowCtx, query);
      for (const candidate of results) {
        const name = nameFromResult(candidate);
        const title = titleFromResult(candidate);
        const discoveryUrl = clean(candidate.link);
        if (
          !name ||
          !title ||
          !discoveryUrl ||
          !companyMatches(publicResultText(candidate), row)
        )
          continue;
        const verification = await independentCurrentRoleCheck(
          row,
          rowCtx,
          name,
          title,
          discoveryUrl,
        );
        if (!verification) continue;
        return [
          toRetrievedItem({
            row,
            name,
            title,
            discoveryUrl,
            discoveryText: publicResultText(candidate),
            verification,
            routeId: 'public_serp_people',
            mechanismClass: 'public_search_and_extract',
            sourceQuery: query,
          }),
        ];
      }
      return { items: [], sourceOutcome: 'no-results' as const };
    },
  },
] satisfies RetrievalRoute<Account>[];

const task = {
  kind: 'person' as const,
  question: 'Return one current senior person at every named company.',
  rowKey: 'account_id',
  selectionUnit: 'row' as const,
  selectionRequiresEligibility: true,
  optimizationObjective: 'coverage_then_cost' as const,
  minimumPilotRows: 3,
  minimumRelevantRows: 1,
  portfolioSize: 2,
  gates: [
    { name: 'person name', type: 'required' as const, fact: 'name' },
    { name: 'accepted title', type: 'required' as const, fact: 'title' },
    {
      name: 'target company',
      type: 'equals_row' as const,
      fact: 'company',
      rowPath: 'company_name',
      match: 'equals_normalized' as const,
    },
    {
      name: 'independent current-role evidence',
      type: 'evidence_policy' as const,
      fact: 'title',
      minimumIndependentWeak: 2,
    },
  ],
};

const judge = async ({ items }: { items: readonly { id: string }[] }) => ({
  scores: items.map((item) => ({
    id: item.id,
    score: 100,
    reason: 'Passed deterministic company, title, and evidence gates.',
  })),
});

export default definePlay(
  'named-account-people',
  async (ctx, input: { csv: string }) => {
    const accounts = await ctx.csv<Account>(input.csv, {
      required: ['account_id', 'company_name', 'domain'],
    });
    const allRows = await accounts.materialize(500);
    const pilotRows = allRows.slice(0, 3);
    const experiment = createRouteExperiment({
      routes,
      task,
      judge,
      maximumCreditsPerRow: 0.16,
    });
    const pilot = await ctx
      .dataset('people_route_pilot', pilotRows)
      .withColumn('route_results', experiment.routeResults)
      .withColumn('fused_items', experiment.fusedItems)
      .withColumn('judge_result', experiment.judgeResult)
      .withColumn('ranked_items', experiment.rankedItems)
      .run({ key: experiment.rowKey });
    const pilotRowsMeasured = await pilot.materialize(500);
    const selection = selectRoutes({
      rows: pilotRowsMeasured,
      routes,
      task,
      maximumCreditsPerRow: 0.16,
    });
    const scoreRows = pilotRowsMeasured.flatMap((row, index) =>
      (row.route_results ?? []).map((result) => {
        const items = result.items ?? [];
        const accepted = items.filter((item) => item.verification === 'eligible');
        const score = selection.promotionEvidence.scorecard.find(
          (entry) => entry.route === result.route,
        );
        return {
          strategy: result.route,
          mechanism_class: routes.find((route) => route.id === result.route)
            ?.mechanismClass,
          account_id: row.account_id,
          company_name: row.company_name,
          candidate_count: items.length,
          accepted_count: accepted.length,
          verified_count: accepted.length,
          marginal_coverage: score?.relevantUnits.includes(String(index)) ? 1 : 0,
          marginal_credits: routes.find((route) => route.id === result.route)
            ?.estimatedCreditsPerRow,
          source_query: clean(accepted[0]?.attributes?.source_query),
          discovery_url: clean(accepted[0]?.attributes?.discovery_url),
          verification_url: clean(accepted[0]?.attributes?.verification_url),
          evidence_excerpt: clean(accepted[0]?.attributes?.evidence_excerpt),
          provider_outcome: result.sourceOutcome,
        };
      }),
    );
    const scorecard = await ctx
      .dataset('people_route_scorecard', scoreRows)
      .run({ key: (row) => `${row.strategy}:${row.account_id}` });
    const selectionArtifact = await ctx
      .dataset('people_route_selection', [
        {
          id: 'selection',
          status: selection.status,
          selected_route_ids: selection.selectedRouteIds,
          selection_json: JSON.stringify(selection),
        },
      ])
      .run({ key: 'id' });

    if (selection.status !== 'promoted') {
      const finalResults = await ctx
        .dataset('people_final_results_unpromoted', allRows)
        .withColumn('name', () => '')
        .withColumn('title', () => '')
        .withColumn('status', () => 'insufficient_evidence')
        .withColumn('discovery_url', () => '')
        .withColumn('verification_url', () => '')
        .withColumn('evidence_excerpt', () => '')
        .withColumn('source_strategy', () => '')
        .withColumn('miss_reason', () => 'No route earned promotion on the measured pilot.')
        .run({ key: 'account_id' });
      return { pilot, scorecard, selectionArtifact, selection, finalResults };
    }

    const selectedRoutes = bindSelection(routes, selection, 0.16);
    const exploitExperiment = createRouteExperiment({
      routes: selectedRoutes,
      task,
      judge,
      maximumCreditsPerRow: 0.16,
      phase: 'exploit',
    });
    const exploit = await ctx
      .dataset('people_route_exploit', allRows)
      .withColumn('route_results', exploitExperiment.routeResults)
      .withColumn('fused_items', exploitExperiment.fusedItems)
      .withColumn('judge_result', exploitExperiment.judgeResult)
      .withColumn('ranked_items', exploitExperiment.rankedItems)
      .withColumn('selected_item', exploitExperiment.selectedItem)
      .run({ key: exploitExperiment.rowKey });
    const selectedByAccount = new Map(
      (await exploit.materialize(500)).map((row) => [row.account_id, row.selected_item]),
    );
    const finalResults = await ctx
      .dataset('people_final_results', allRows)
      .withColumn('name', (row) => clean(selectedByAccount.get(row.account_id)?.attributes?.name))
      .withColumn('title', (row) => clean(selectedByAccount.get(row.account_id)?.attributes?.title))
      .withColumn('status', (row) =>
        selectedByAccount.get(row.account_id) ? 'found' : 'miss',
      )
      .withColumn('discovery_url', (row) => clean(selectedByAccount.get(row.account_id)?.attributes?.discovery_url))
      .withColumn('verification_url', (row) => clean(selectedByAccount.get(row.account_id)?.attributes?.verification_url))
      .withColumn('evidence_excerpt', (row) => clean(selectedByAccount.get(row.account_id)?.attributes?.evidence_excerpt))
      .withColumn('source_strategy', (row) => clean(selectedByAccount.get(row.account_id)?.attributes?.source_strategy))
      .withColumn('miss_reason', (row) =>
        selectedByAccount.get(row.account_id)
          ? ''
          : 'No candidate passed current-company, accepted-title, and independent-evidence gates.',
      )
      .run({ key: 'account_id' });
    return { pilot, scorecard, selectionArtifact, selection, exploit, finalResults };
  },
  { description: 'Find one verified current person per named account' },
);
