import { definePlay } from 'deepline';
import {
  createResearchKernel,
  evidenceHostMatchesDomain,
  isLikelyOfficialDomainCandidate,
  normalizeDomainClaim,
  researchEvidenceId,
  selectOfficialDomainCandidate,
  type ResearchRow,
} from './shared/research-kernel';
import {
  createAiInferenceJudge,
  type RetrievedItemInput,
  type RetrievalRoute,
} from './shared/route-experiment';

/** @mermaid
 * flowchart TD
 * source[(CSV input)] --> input[(Research rows)]
 * input --> broad[(Broad discovery)]
 * broad --> broadLoop
 * subgraph broadLoop["For each research row"]
 *   discover["Run every route, fuse, judge, score coverage"]
 * end
 * broadLoop --> gaps{Required claims missing?}
 * gaps -->|yes| final[(Gap-only follow-up)]
 * gaps -->|no| final
 * final --> finalLoop
 * subgraph finalLoop["For each row with missing claims"]
 *   retry["Retry only the missing claims and re-score"]
 * end
 * finalLoop --> claims[(Research claims)]
 * claims --> evidence[(Research evidence)]
 * evidence --> coverage[(Source coverage)]
 * coverage --> gaplog[(Supplemental gaps)]
 */

type Row = Record<string, unknown> & {
  account_id: string;
  company_name: string;
  domain_hint: string;
};

type WorkingRow = Row & ResearchRow;

// Replace these deterministic fixture routes with literal ctx.tools.execute
// calls and provider adapters. Keep each route a genuinely different
// mechanism, not two prompts sent to one sourced-answer tool.
const broadRoutes = [
  {
    id: 'search_index',
    mechanismId: 'fixture_search',
    mechanismClass: 'search_index',
    sourceFamilies: ['search-index'],
    queryFamily: 'broad identity and product discovery',
    estimatedCreditsPerRow: 0,
    retrieve: ({ row }) => [
      {
        id: `https://${row.domain_hint}/`,
        title: `${row.company_name} official site`,
        url: `https://${row.domain_hint}/`,
        snippet: `${row.company_name} product evidence`,
        sourceQuality: 0.9,
        facts: {
          canonical_domain: {
            value: normalizeDomainClaim(row.domain_hint) ?? row.domain_hint,
            evidence: [
              {
                source: 'fixture-search',
                independenceClass: 'official-site',
                strength: 'weak' as const,
                url: `https://${row.domain_hint}/`,
                text: `${row.company_name} official site`,
              },
            ],
          },
        },
        evidence: [
          {
            source: 'fixture-search',
            independenceClass: 'search-index',
            url: `https://${row.domain_hint}/`,
            text: `${row.company_name} product evidence`,
          },
        ],
      },
    ],
  },
  {
    id: 'page_fetch',
    mechanismId: 'fixture_fetch',
    mechanismClass: 'page_fetch',
    sourceFamilies: ['page-fetch'],
    queryFamily: 'official page text and buyer language',
    estimatedCreditsPerRow: 0,
    retrieve: ({ row }) => [
      {
        id: `https://${row.domain_hint}/product`,
        title: `${row.company_name} product`,
        url: `https://${row.domain_hint}/product`,
        content: `${row.company_name} sells an evidence-backed product.`,
        sourceQuality: 0.9,
        facts: {
          canonical_domain: {
            value: normalizeDomainClaim(row.domain_hint) ?? row.domain_hint,
            evidence: [
              {
                source: 'fixture-fetch',
                independenceClass: 'official-page-fetch',
                strength: 'authoritative' as const,
                url: `https://${row.domain_hint}/product`,
                text: `${row.company_name} product page`,
              },
            ],
          },
          what_they_sell: {
            value: 'an evidence-backed product',
            evidence: [
              {
                source: 'fixture-fetch',
                independenceClass: 'official-product-page',
                strength: 'authoritative' as const,
                url: `https://${row.domain_hint}/product`,
                text: `${row.company_name} sells an evidence-backed product.`,
              },
            ],
          },
        },
      },
    ],
  },
] satisfies RetrievalRoute<Row>[];

const supplementalRoutes = [
  {
    id: 'supplemental_registry',
    mechanismId: 'fixture_registry',
    mechanismClass: 'authoritative_registry',
    sourceFamilies: ['supplemental-registry'],
    queryFamily: 'missing claims through a recovered identity',
    estimatedCreditsPerRow: 0,
    retrieve: ({ row }) => {
      const missing = new Set(row.research_coverage?.missingClaimIds ?? []);
      if (!missing.size) return [];
      // A live adapter should fetch this recovered candidate URL. The fixture
      // fallback keeps the generated example runnable without a provider.
      const recovered = selectOfficialDomainCandidate(
        row.ranked_items ?? [],
        row.company_name,
      );
      const url = recovered?.url ?? `https://${row.domain_hint}/customers`;
      const facts: NonNullable<RetrievedItemInput['facts']> = {};
      if (missing.has('canonical_domain')) {
        facts.canonical_domain = {
          value: normalizeDomainClaim(url) ?? '',
          evidence: [
            {
              source: 'fixture-registry',
              independenceClass: 'official-page-fetch',
              strength: 'authoritative' as const,
              url,
              text: `${row.company_name} official customers page`,
            },
          ],
        };
      }
      if (missing.has('primary_buyer')) {
        facts.primary_buyer = {
          value: 'business teams',
          evidence: [
            {
              source: 'fixture-registry',
              independenceClass: 'customer-registry',
              strength: 'authoritative' as const,
              url,
              text: `${row.company_name} serves business teams.`,
            },
          ],
        };
      }
      return [
        {
          id: url,
          title: `${row.company_name} customers`,
          url,
          snippet: `${row.company_name} serves business teams.`,
          facts,
        },
      ];
    },
  },
] satisfies RetrievalRoute<WorkingRow>[];

export default definePlay(
  'research-kernel-example',
  async (ctx, input: { file: string; referenceDate: string }) => {
    const MAX_ROWS = 250;
    // @mermaid-node source type:"dataset" in:"input.file" out:"rows"
    const rows = await ctx.csv<Row>(input.file, {
      required: ['account_id', 'company_name', 'domain_hint'],
    });
    const kernel = createResearchKernel<Row>({
      task: {
        question:
          'Find attributable company identity, product, and buyer evidence.',
        criteria: ['exact company match', 'evidence-close claims'],
        rowKey: 'account_id',
        primaryEntity: (row) => String(row.company_name),
        research: {
          referenceDate: input.referenceDate,
          freshnessMode: 'evergreen_ok',
          freshnessWindowDays: 365,
        },
      },
      claims: [
        {
          id: 'canonical_domain',
          fact: 'canonical_domain',
          maximumClaimCharacters: 100,
          requiredEvidencePhase: 'supplemental',
          minimumIndependentWeak: 2,
          supports: (item, row) =>
            isLikelyOfficialDomainCandidate(item, row.company_name),
          validateEvidence: ({ value, evidence }) =>
            evidenceHostMatchesDomain(value, evidence),
        },
        {
          id: 'what_they_sell',
          fact: 'what_they_sell',
          maximumClaimCharacters: 200,
          minimumIndependentWeak: 2,
        },
        {
          id: 'primary_buyer',
          fact: 'primary_buyer',
          maximumClaimCharacters: 160,
          minimumIndependentWeak: 2,
        },
      ],
      broadRoutes,
      supplementalRoutes,
      judge: createAiInferenceJudge(),
    });

    // @mermaid-node input type:"dataset" out:"inputRows"
    const inputRows = await ctx.dataset('input_rows', rows).run({
      key: 'account_id',
      description: 'Preserve every research denominator row.',
    });
    const inputCount = await inputRows.count();
    if (inputCount > MAX_ROWS)
      throw new Error(`Research scaffold supports at most ${MAX_ROWS} rows.`);
    const inputMaterialized = await inputRows.materialize(MAX_ROWS);

    // @mermaid-node broad type:"dataset" in:"inputRows" out:"broad"
    const broad = await ctx
      .dataset('research_broad', inputMaterialized)
      // @mermaid-node discover out:"route_results,fused_items,judge_result,ranked_items,research_coverage"
      .withColumn('route_results', kernel.discovery.routeResults)
      .withColumn('fused_items', kernel.discovery.fusedItems)
      .withColumn('judge_result', kernel.discovery.judgeResult)
      .withColumn('ranked_items', kernel.discovery.rankedItems)
      .withColumn('research_coverage', kernel.discovery.coverage)
      .run({ key: kernel.rowKey, description: 'Run broad research routes.' });
    const broadRows = await broad.materialize(MAX_ROWS);

    // @mermaid-node gaps type:"decision" in:"broad" out:"hasGaps"
    const hasGaps = broadRows.some(
      (row) => row.research_coverage?.missingClaimIds.length,
    );

    // @mermaid-node final type:"dataset" in:"broad" out:"finalRows"
    const finalRows = await ctx
      .dataset('research_final', broadRows)
      // @mermaid-node retry out:"supplemental_route_results,combined_route_results,final_fused_items,final_judge_result,final_ranked_items,final_research_coverage"
      .withColumn(
        'supplemental_route_results',
        kernel.supplemental.routeResults,
      )
      .withColumn(
        'combined_route_results',
        kernel.supplemental.combinedRouteResults,
      )
      .withColumn('final_fused_items', kernel.supplemental.fusedItems)
      .withColumn('final_judge_result', kernel.supplemental.judgeResult)
      .withColumn('final_ranked_items', kernel.supplemental.rankedItems)
      .withColumn('final_research_coverage', kernel.supplemental.coverage)
      .run({
        key: kernel.rowKey,
        description: 'Retry only missing research claims.',
      });
    const final = await finalRows.materialize(MAX_ROWS);

    const claimRows = final.flatMap((row) =>
      (row.final_research_coverage?.claims ?? []).map((claim) => ({
        account_id: row.account_id,
        claim_key: claim.claimId,
        broad_status:
          row.research_coverage?.claims.find(
            (entry) => entry.claimId === claim.claimId,
          )?.status ?? 'no_result',
        final_status:
          claim.status === 'supported' ? 'supported' : 'insufficient_evidence',
        claim_text: claim.status === 'supported' ? (claim.values[0] ?? '') : '',
        supporting_evidence_ids: claim.evidenceIds.join('|'),
        insufficient_reason: claim.status === 'supported' ? '' : claim.reason,
      })),
    );
    // @mermaid-node claims type:"dataset" in:"finalRows" out:"researchClaims"
    const researchClaims = await ctx.dataset('research_claims', claimRows).run({
      key: (row) => `${row.account_id}|${row.claim_key}`,
      description: 'Persist one evidence-linked row per required claim.',
    });

    const evidenceById = new Map<
      string,
      {
        evidence_id: string;
        account_id: string;
        phase: string;
        mechanism_id: string;
        mechanism_class: string;
        source_family: string;
        url: string;
        title: string;
        excerpt: string;
        published_at: string;
        query: string;
        provider_status: string;
      }
    >();
    for (const row of final) {
      for (const item of row.final_ranked_items ?? []) {
        for (const evidence of item.evidence) {
          const evidence_id = researchEvidenceId(
            row.account_id,
            evidence.source,
            evidence.url,
            evidence.text,
            evidence.phase,
            evidence.mechanismId,
          );
          if (!evidenceById.has(evidence_id)) {
            evidenceById.set(evidence_id, {
              evidence_id,
              account_id: row.account_id,
              phase: evidence.phase ?? 'broad',
              mechanism_id: evidence.mechanismId ?? item.routes[0] ?? '',
              mechanism_class: evidence.mechanismClass ?? item.routes[0] ?? '',
              source_family: evidence.independenceClass,
              url: evidence.url ?? item.url ?? '',
              title: item.title ?? item.label,
              excerpt: evidence.text ?? item.content ?? item.snippet ?? '',
              published_at: item.publishedAt ?? '',
              query: String(item.attributes?.query ?? ''),
              provider_status:
                evidence.providerStatus === 'ok'
                  ? 'success'
                  : (evidence.providerStatus ?? 'success'),
            });
          }
        }
      }
    }
    const evidenceRows = [...evidenceById.values()];
    // @mermaid-node evidence type:"dataset" in:"finalRows" out:"researchEvidence"
    const researchEvidence = await ctx
      .dataset('research_evidence', evidenceRows)
      .run({
        key: 'evidence_id',
        description: 'Persist attributable source evidence.',
      });

    const routeById = new Map(
      [...broadRoutes, ...supplementalRoutes].map((route) => [route.id, route]),
    );
    const coverageRows = final.flatMap((row) =>
      (row.combined_route_results ?? []).map((attempt) => {
        const route = routeById.get(attempt.route);
        return {
          account_id: row.account_id,
          phase: attempt.phase ?? 'broad',
          mechanism_id:
            attempt.mechanismId ?? route?.mechanismId ?? attempt.route,
          mechanism_class:
            attempt.mechanismClass ?? route?.mechanismClass ?? attempt.route,
          provider_status:
            attempt.sourceOutcome === 'ok' ? 'success' : attempt.sourceOutcome,
          result_count: (attempt.items ?? []).length,
          useful_evidence_count: (attempt.items ?? []).filter(
            (item) => item.evidence.length,
          ).length,
          remaining_claim_gaps: (
            row.final_research_coverage?.missingClaimIds ?? []
          ).join('|'),
        };
      }),
    );
    // @mermaid-node coverage type:"dataset" in:"finalRows" out:"sourceCoverage"
    const sourceCoverage = await ctx
      .dataset('source_coverage', coverageRows)
      .run({
        key: (row) => `${row.account_id}|${row.phase}|${row.mechanism_id}`,
        description: 'Measure every research mechanism and remaining gap.',
      });

    const gapRows = final.flatMap((row) =>
      (row.research_coverage?.claims ?? [])
        .filter((claim) => claim.status !== 'supported')
        .map((claim) => {
          const outcome = row.final_research_coverage?.claims.find(
            (entry) => entry.claimId === claim.claimId,
          );
          const supplementalEvidence = (outcome?.evidenceIds ?? [])
            .map((evidenceId) => evidenceById.get(evidenceId))
            .filter(
              (entry): entry is NonNullable<typeof entry> =>
                entry?.phase === 'supplemental',
            );
          const attemptedMechanism = (
            row.supplemental_route_results ?? []
          ).find((attempt) => attempt.sourceOutcome !== 'skipped')?.mechanismId;
          const supplementalMechanism =
            supplementalEvidence[0]?.mechanism_id ??
            attemptedMechanism ??
            supplementalRoutes[0]?.mechanismId ??
            supplementalRoutes[0]?.id ??
            '';
          return {
            gap_id: `${row.account_id}|${claim.claimId}`,
            account_id: row.account_id,
            claim_key: claim.claimId,
            trigger_status: claim.status,
            trigger_evidence_ids: claim.evidenceIds.join('|'),
            supplemental_query: `${row.company_name} ${claim.claimId}`,
            supplemental_mechanism_id: supplementalMechanism,
            outcome_status:
              outcome?.status === 'supported'
                ? 'supported'
                : 'insufficient_evidence',
            outcome_evidence_ids: supplementalEvidence
              .filter(
                (evidence) => evidence.mechanism_id === supplementalMechanism,
              )
              .map((evidence) => evidence.evidence_id)
              .join('|'),
          };
        }),
    );
    // @mermaid-node gaplog type:"dataset" in:"finalRows" out:"supplementalGaps"
    const supplementalGaps = await ctx
      .dataset('supplemental_gaps', gapRows)
      .run({
        key: 'gap_id',
        description: 'Record why each bounded follow-up ran and what it found.',
      });

    return {
      inputRows,
      broad,
      finalRows,
      researchClaims,
      researchEvidence,
      sourceCoverage,
      supplementalGaps,
      hasGaps,
    };
  },
  {
    description: 'Research evidence-backed company claims',
    billing: { maxCreditsPerRun: 3 },
  },
);
