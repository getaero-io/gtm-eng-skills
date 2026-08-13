import { definePlay } from 'deepline';
import {
  defineResearchActionPortfolio,
  planResearchPortfolio,
  recordResearchActionObservation,
} from './shared/research-portfolio';

type FixtureRow = {
  id: string;
  expected_first_action: string;
  expected_second_action: string;
};

const FIXTURES: FixtureRow[] = [
  {
    id: 'official-then-registry',
    expected_first_action: 'official_operator_v1',
    expected_second_action: 'registry_operator_v1',
  },
];

const actions = defineResearchActionPortfolio([
  {
    id: 'official_operator_v1',
    hypothesis:
      'Official staff pages may establish an allowed current operator.',
    sourceFamily: 'official_web',
    correlationGroup: 'first_party_site',
    stage: 'claim_completion',
    evidenceMode: 'terminal_evidence',
    producesClaimIds: ['operator'],
    maximumDeeplineCredits: 0.1,
    historicalPrior: { verifiedClaims: 8, attemptedClaims: 10 },
  },
  {
    id: 'registry_operator_v1',
    hypothesis:
      'A license or officer record may recover the operator after a site miss.',
    sourceFamily: 'public_registry',
    correlationGroup: 'public_registry',
    stage: 'claim_completion',
    evidenceMode: 'terminal_evidence',
    producesClaimIds: ['operator'],
    maximumDeeplineCredits: 0.2,
    historicalPrior: { verifiedClaims: 3, attemptedClaims: 5 },
  },
  {
    id: 'broad_people_lead_v1',
    hypothesis:
      'A broad people result is a candidate lead, not terminal role proof.',
    sourceFamily: 'people_database',
    correlationGroup: 'people_database',
    stage: 'discovery',
    evidenceMode: 'lead_only',
    producesClaimIds: ['operator'],
    producesArtifactIds: ['operator_lead'],
    maximumDeeplineCredits: 4.2,
  },
]);

export default definePlay(
  'research-portfolio-fixture',
  async (ctx) => {
    const results = await ctx
      .dataset('portfolio_fixture_rows', FIXTURES)
      .withColumn('portfolio_result', async (row) => {
        const first = planResearchPortfolio({
          rowKey: row.id,
          contextKey: 'local_fuel:philly:operator',
          requiredClaimIds: ['operator'],
          verifiedClaimIds: [],
          budgetDeeplineCredits: 1,
          actions,
          observations: [],
        });
        if (!first.selectedActionId) {
          throw new Error(
            `Fixture failed to select first action for ${row.id}.`,
          );
        }
        const observations = recordResearchActionObservation({
          actions,
          observations: [],
          observation: {
            actionId: first.selectedActionId,
            rowKey: row.id,
            contextKey: 'local_fuel:philly:operator',
            outcome: 'no_result',
            observedDeeplineCredits: 0.1,
            detail: 'Fixture official route had no allowed role.',
          },
        });
        const second = planResearchPortfolio({
          rowKey: row.id,
          contextKey: 'local_fuel:philly:operator',
          requiredClaimIds: ['operator'],
          verifiedClaimIds: [],
          budgetDeeplineCredits: 1,
          actions,
          observations,
        });
        return {
          first_action: first.selectedActionId,
          second_action: second.selectedActionId ?? '',
          second_mode: second.selectedMode,
          second_stop_reason: second.stopReason ?? '',
        };
      })
      .run({
        key: 'id',
        description:
          'Exercise budgeted adaptive action selection without provider calls.',
      });
    const materialized = await results.materialize(FIXTURES.length);
    for (const row of materialized) {
      const expected = FIXTURES.find((fixture) => fixture.id === row.id);
      if (!expected) throw new Error(`Unexpected fixture row ${row.id}.`);
      if (
        row.portfolio_result.first_action !== expected.expected_first_action
      ) {
        throw new Error(`Unexpected first action for ${row.id}.`);
      }
      if (
        row.portfolio_result.second_action !== expected.expected_second_action
      ) {
        throw new Error(`Unexpected second action for ${row.id}.`);
      }
    }
    return { results };
  },
  {
    description:
      'Exercise budgeted adaptive action selection without provider calls.',
  },
);
