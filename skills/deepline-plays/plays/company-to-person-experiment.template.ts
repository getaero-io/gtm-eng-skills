import { definePlay } from 'deepline';
import { bindResearchEvidenceToSource } from './shared/research-experiment';
import {
  runSearchExperiment,
  routeScorecardRows,
  type SearchProgram,
  verifiedSearchClaimValue,
} from './shared/search-experiment';
import { attempt, boundClaim, found } from './shared/search-strategy';

// This topology is intentionally one normal TypeScript Play. Company strategies
// create accepted rows; people strategies run only against those rows.
type CompanyScope = { partition: string };
type ContactRow = { company_name: string; company_domain: string };

// Source partitions are not hand-picked companies. Replace these with bounded
// query shards, registry pages, or geography × category slices. The later
// partitions give the selected route fresh units to exploit after the pilot.
const companyScopes: CompanyScope[] = [
  { partition: 'replace-with-pilot-market-partition' },
  { partition: 'replace-with-exploit-market-partition' },
  { partition: 'replace-with-recovery-market-partition' },
];
const boundProgramIds: readonly string[] = [];

function assertBound(
  programs: readonly { id: string; diversityFeatures?: readonly string[] }[],
) {
  if (
    companyScopes.some((row) => row.partition.includes('replace-with')) ||
    programs
      .flatMap((program) => program.diversityFeatures ?? [])
      .some((value) => value.includes('replace-with'))
  ) {
    throw new Error(
      'CATALOG_REQUIRED: replace scaffold rows and route geometry.',
    );
  }
  const missing = programs
    .map((program) => program.id)
    .filter((id) => !boundProgramIds.includes(id));
  if (missing.length > 0) {
    throw new Error(
      `CATALOG_REQUIRED: bind every registered strategy body (${missing.join(', ')}).`,
    );
  }
}

export default definePlay(
  'search-experiment-template',
  async (ctx) => {
    // Stage 1: each route discovers and qualifies companies from the same partition.
    const companyPrograms: SearchProgram<CompanyScope, typeof ctx>[] = [
      {
        id: 'company-index',
        hypothesis:
          'A structured or private index enumerates qualified companies.',
        incumbent: true,
        diversityFeatures: [
          'replace-with-company-index-corpus',
          'replace-with-company-filter-pivot',
        ],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        async run({ row }) {
          // Copy one literal described company call and named getter here.
          // Return only companies with bound company_name, company_domain, and qualification evidence.
          // `boundClaim` calls bindResearchEvidenceToSource. A raw/provider value
          // without a successful exact source binding remains a candidate only.
          void row;
          void attempt;
          void boundClaim;
          void found;
          void bindResearchEvidenceToSource;
          throw new Error('CATALOG_REQUIRED: bind company index.');
        },
      },
      {
        id: 'company-proof-route',
        hypothesis:
          'A different corpus catches or proves companies the index misses.',
        diversityFeatures: [
          'replace-with-company-proof-corpus',
          'replace-with-company-proof-pivot',
        ],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        async run({ row }) {
          void row;
          throw new Error('CATALOG_REQUIRED: bind company proof route.');
        },
      },
      {
        id: 'company-dormant-recovery',
        hypothesis:
          'A distinct company route is spent only on unqualified gaps.',
        diversityFeatures: [
          'replace-with-company-recovery-corpus',
          'replace-with-company-recovery-pivot',
        ],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        async run({ row }) {
          void row;
          throw new Error('CATALOG_REQUIRED: bind company recovery route.');
        },
      },
    ];

    // Stage 2: each route finds and proves a person at an accepted company.
    const contactPrograms: SearchProgram<ContactRow, typeof ctx>[] = [
      {
        id: 'people-index',
        hypothesis:
          'A current-role/profile index finds the requested role at this company.',
        incumbent: true,
        diversityFeatures: [
          'replace-with-people-index-corpus',
          'replace-with-people-input-pivot',
        ],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        async run({ row }) {
          // Copy one literal described people call and named getter here.
          // Bind contact_name, contact_title, and contact_linkedin from this response.
          void row;
          throw new Error('CATALOG_REQUIRED: bind people index.');
        },
      },
      {
        id: 'role-proof-route',
        hypothesis:
          'A separate public/profile corpus proves current responsibility.',
        diversityFeatures: [
          'replace-with-role-proof-corpus',
          'replace-with-role-proof-pivot',
        ],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        async run({ row }) {
          void row;
          throw new Error('CATALOG_REQUIRED: bind role proof route.');
        },
      },
      {
        id: 'people-dormant-recovery',
        hypothesis:
          'A different people route recovers a real role or profile gap.',
        diversityFeatures: [
          'replace-with-people-recovery-corpus',
          'replace-with-people-recovery-pivot',
        ],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        async run({ row }) {
          void row;
          throw new Error('CATALOG_REQUIRED: bind people recovery route.');
        },
      },
    ];
    assertBound([...companyPrograms, ...contactPrograms]);

    const companyExperiment = await runSearchExperiment({
      ctx,
      rows: companyScopes,
      definition: {
        contract: {
          rowKey: 'partition',
          claims: [
            { id: 'company_name', question: 'What is the company name?' },
            { id: 'company_domain', question: 'What is its canonical domain?' },
            {
              id: 'qualification_evidence',
              question:
                'What proves it matches the requested company condition?',
            },
          ],
          minimumPilotCompleteRows: 1,
        },
        programs: companyPrograms,
        explorationProgramCount: 2,
      },
    });

    // Do not replace this with raw candidates or hand-picked companies.
    const contactRows = companyExperiment.finalResults
      .filter((result) => result.complete)
      .flatMap((result) => {
        const companyName = verifiedSearchClaimValue<string>(
          result,
          'company_name',
        );
        const companyDomain = verifiedSearchClaimValue<string>(
          result,
          'company_domain',
        );
        return companyName && companyDomain
          ? [{ company_name: companyName, company_domain: companyDomain }]
          : [];
      });
    const contactExperiment =
      contactRows.length === 0
        ? null
        : await runSearchExperiment({
            ctx,
            rows: contactRows,
            definition: {
              contract: {
                rowKey: 'company_domain',
                claims: [
                  {
                    id: 'contact_name',
                    question: 'Who currently holds the role?',
                  },
                  {
                    id: 'contact_title',
                    question: 'What is their exact current responsibility?',
                  },
                  {
                    id: 'contact_linkedin',
                    question: 'What profile URL identifies that person?',
                  },
                ],
                minimumPilotCompleteRows: 1,
              },
              programs: contactPrograms,
              explorationProgramCount: 2,
            },
          });

    const outputRows = contactRows.map((row) => {
      const result = contactExperiment?.finalResults.find(
        (candidate) =>
          candidate.unitKey === row.company_domain.trim() && candidate.complete,
      );
      const attemptedSources = contactExperiment?.attempts
        .filter((trace) => trace.unitKey === row.company_domain.trim())
        .map((trace) => `${trace.programId}:${trace.outcome}`)
        .filter((value, index, values) => values.indexOf(value) === index);
      return {
        company_name: row.company_name,
        // Preserve the user's requested output names. Internal claim ids stay
        // explicit; changing `domain` to `company_domain` here loses a simple
        // CSV contract at export time.
        domain: row.company_domain,
        contact_name: result
          ? verifiedSearchClaimValue<string>(result, 'contact_name')
          : null,
        title: result
          ? verifiedSearchClaimValue<string>(result, 'contact_title')
          : null,
        linkedin_url: result
          ? verifiedSearchClaimValue<string>(result, 'contact_linkedin')
          : null,
        status: result ? 'verified' : 'unresolved',
        // An unresolved row still says which routes were actually attempted.
        source:
          result?.programIds.join(' -> ') ??
          attemptedSources?.join(' -> ') ??
          null,
      };
    });
    const results = await ctx
      .dataset('company_people_results', outputRows)
      .run({
        key: 'domain',
        description:
          'Accepted company-to-person rows plus explicit unresolved gaps.',
      });
    const companyScorecard = await ctx
      .dataset(
        'company_route_scorecard',
        routeScorecardRows(companyExperiment.scorecard),
      )
      .run({
        key: 'program_id',
        description: 'Measured company-route coverage, reliability, and cost.',
      });
    const contactScorecard = contactExperiment
      ? await ctx
          .dataset(
            'contact_route_scorecard',
            routeScorecardRows(contactExperiment.scorecard),
          )
          .run({
            key: 'program_id',
            description:
              'Measured people-route coverage, reliability, and cost.',
          })
      : null;
    return {
      companyExperiment,
      contactExperiment,
      results,
      companyScorecard,
      contactScorecard,
    };
  },
  { description: 'Discover companies, then compare and recover contacts' },
);
