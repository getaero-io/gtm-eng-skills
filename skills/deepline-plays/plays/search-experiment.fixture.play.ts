import { definePlay } from 'deepline';
import { bindResearchEvidenceToSource } from './shared/research-experiment';
import {
  runSearchExperiment,
  type SearchProgram,
} from './shared/search-experiment';

type FixtureRow = {
  domain: string;
  segment: 'ordinary' | 'long_tail';
};

const rows: FixtureRow[] = [
  { domain: 'alpha.example', segment: 'ordinary' },
  { domain: 'bravo.example', segment: 'ordinary' },
  { domain: 'charlie.example', segment: 'long_tail' },
  { domain: 'delta.example', segment: 'ordinary' },
  { domain: 'echo.example', segment: 'long_tail' },
  { domain: 'foxtrot.example', segment: 'ordinary' },
];

const evidenceResult = (row: FixtureRow, source: 'official' | 'registry') => {
  const operator = `${row.domain.split('.')[0]} operator`;
  const rawSourceText = `${operator} is the current operator of ${row.domain}.`;
  const evidence = bindResearchEvidenceToSource({
    source: `${source} fixture`,
    independenceClass: source,
    url:
      source === 'official'
        ? `https://${row.domain}/about`
        : `https://registry.example/${row.domain}`,
    excerpt: rawSourceText,
    rawSourceText,
    authority: 'authoritative',
  });
  if (!evidence) throw new Error('Fixture evidence failed to bind.');
  return {
    resultKey: row.domain,
    canonicalEntityKey: row.domain,
    claims: {
      operator: { value: operator, evidence: [evidence] },
    },
  };
};

const makeProgram = <Context>(
  id: string,
  hypothesis: string,
  source: 'official' | 'registry',
  segment: FixtureRow['segment'],
): SearchProgram<FixtureRow, Context> => ({
  id,
  hypothesis,
  maximumCallsPerAttempt: 1,
  async run({ row }) {
    return {
      totalCalls: 1,
      results: row.segment === segment ? [evidenceResult(row, source)] : [],
    };
  },
});

export default definePlay(
  'search-experiment-fixture',
  async (ctx) => {
    const programs: SearchProgram<FixtureRow, typeof ctx>[] = [
      makeProgram<typeof ctx>(
        'official-site',
        'Most rows expose the required fact on their own site.',
        'official',
        'ordinary',
      ),
      makeProgram<typeof ctx>(
        'public-record',
        'A public record covers rows missed by ordinary sites.',
        'registry',
        'long_tail',
      ),
    ];

    const experiment = await runSearchExperiment({
      ctx,
      rows,
      definition: {
        contract: {
          rowKey: 'domain',
          targetRows: 4,
          claims: [
            {
              id: 'operator',
              question: 'Who is the current operator?',
              allowAuthoritativeSingle: true,
            },
          ],
          minimumPilotCompleteRows: 2,
          minimumHoldoutCompleteRows: 1,
        },
        programs,
        comparisonUnitCount: 2,
        pilotUnitCount: 4,
        holdoutUnitCount: 1,
        maxFallbacks: 1,
      },
    });

    const results = await ctx
      .dataset(
        'search_experiment_fixture_results',
        experiment.finalResults.map((result) => ({
          identity: result.identity,
          unit_key: result.unitKey,
          complete: result.complete,
          programs: result.programIds.join(','),
        })),
      )
      .run({ key: 'identity' });
    const scorecard = await ctx
      .dataset(
        'search_experiment_fixture_scorecard',
        experiment.scorecard.map((score) => ({
          program_id: score.programId,
          complete_results: score.completeResults,
          verified_required_claims: score.verifiedRequiredClaims,
          total_calls: score.totalCalls,
        })),
      )
      .run({ key: 'program_id' });
    return { experiment, results, scorecard };
  },
  {
    description:
      'Provider-free fixture for dataset-conditioned search, evidence binding, holdout, and deterministic exploitation.',
  },
);
