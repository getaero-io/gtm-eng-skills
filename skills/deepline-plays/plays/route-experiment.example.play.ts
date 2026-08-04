import { definePlay } from 'deepline';
import {
  bindSelection,
  createRouteExperiment,
  selectRoutes,
  type RetrievalRoute,
} from './shared/route-experiment';

type Row = Record<string, unknown> & {
  id: string;
  result_kind: string;
  goal: string;
};

const routes = [
  {
    id: 'structured',
    sourceFamilies: ['structured-index'],
    queryFamily: 'exact task result',
    estimatedCreditsPerRow: 0,
    maxItems: 3,
    retrieve: ({ row }) => [
      {
        id: `${row.id}-shared`,
        label: `${row.goal} shared result`,
        relevance: 0.8,
        attributes: { result_kind: row.result_kind, route_shape: 'structured' },
        facts: { result_kind: row.result_kind },
      },
      {
        id: `${row.id}-structured`,
        label: `${row.goal} structured-only result`,
        relevance: 0.7,
        attributes: { result_kind: row.result_kind },
      },
    ],
  },
  {
    id: 'semantic',
    sourceFamilies: ['semantic-index'],
    queryFamily: 'broad semantic task evidence',
    estimatedCreditsPerRow: 0,
    maxItems: 3,
    retrieve: ({ row }) => [
      {
        id: `${row.id}-shared`,
        label: `${row.goal} shared result`,
        relevance: 0.9,
        attributes: { result_kind: row.result_kind, route_shape: 'semantic' },
        facts: { result_kind: row.result_kind },
      },
      {
        id: `${row.id}-semantic`,
        label: `${row.goal} semantic-only result`,
        relevance: 0.85,
        attributes: { result_kind: row.result_kind },
      },
    ],
  },
] satisfies RetrievalRoute<Row>[];

export default definePlay(
  'route-experiment-example',
  async (ctx) => {
    const task = {
      kind: 'arbitrary-result' as const,
      question:
        'Rank any retrieved item by how well it satisfies the row-specific goal.',
      rowKey: 'id',
      minimumPilotRows: 3,
      minimumRelevantRows: 2,
      portfolioSize: 2,
    };
    const config = {
      routes,
      task,
      judge: async ({ items }: { items: readonly { id: string }[] }) => ({
        scores: items.map((item, index) => ({
          id: item.id,
          score: 95 - index * 5,
        })),
      }),
      maximumCreditsPerRow: 0,
    };
    const experiment = createRouteExperiment(config);
    const pilot = await ctx
      .dataset('route_experiment_pilot', [
        { id: 'one', result_kind: 'person', goal: 'Find a security leader' },
        { id: 'two', result_kind: 'company', goal: 'Find an ICP account' },
        { id: 'three', result_kind: 'signal', goal: 'Find a hiring signal' },
      ])
      .withColumn('route_results', experiment.routeResults)
      .withColumn('fused_items', experiment.fusedItems)
      .withColumn('judge_result', experiment.judgeResult)
      .withColumn('ranked_items', experiment.rankedItems)
      .run({ key: experiment.rowKey });
    const pilotRows = await pilot.materialize(100);
    const selection = selectRoutes({
      rows: pilotRows,
      routes,
      task,
      maximumCreditsPerRow: 0,
    });
    const scorecard = await ctx
      .dataset(
        'route_experiment_scorecard',
        selection.promotionEvidence.scorecard.map((row) => ({
          route: row.route,
          attempted: row.attempted,
          evaluable: row.evaluable,
          excluded: row.excluded,
          relevant_top_k: row.relevantTopK,
          unique_items: row.uniqueItems,
          reliability: row.reliability,
          estimated_credits_per_row: row.estimatedCreditsPerRow,
          retrieval_utility_per_credit: row.retrievalUtilityPerCredit,
          relevant_units: row.relevantUnits,
          unit_scores: row.unitScores,
        })),
      )
      .run({ key: 'route' });
    const selectionArtifact = await ctx
      .dataset('route_experiment_selection', [
        {
          id: 'selection',
          status: selection.status,
          selected_route_ids: selection.selectedRouteIds,
          selection_json: JSON.stringify(selection),
        },
      ])
      .run({ key: 'id' });
    if (selection.status !== 'promoted')
      return { pilot, scorecard, selectionArtifact, selection, exploit: null };

    const selectedRoutes = bindSelection(routes, selection, 0);
    const exploitExperiment = createRouteExperiment({
      ...config,
      phase: 'exploit',
      routes: selectedRoutes,
    });
    const exploit = await ctx
      .dataset('route_experiment_exploit', [
        { id: 'one', result_kind: 'person', goal: 'Find a security leader' },
        { id: 'two', result_kind: 'company', goal: 'Find an ICP account' },
        { id: 'three', result_kind: 'signal', goal: 'Find a hiring signal' },
        { id: 'four', result_kind: 'source', goal: 'Find supporting evidence' },
        { id: 'five', result_kind: 'product', goal: 'Recommend a data tool' },
        {
          id: 'six',
          result_kind: 'event',
          goal: 'Find a recent company event',
        },
        {
          id: 'seven',
          result_kind: 'recommendation',
          goal: 'Recommend the next action',
        },
        { id: 'eight', result_kind: 'claim', goal: 'Find the strongest claim' },
        { id: 'nine', result_kind: 'opaque', goal: 'Rank an arbitrary object' },
      ])
      .withColumn('route_results', exploitExperiment.routeResults)
      .withColumn('fused_items', exploitExperiment.fusedItems)
      .withColumn('judge_result', exploitExperiment.judgeResult)
      .withColumn('ranked_items', exploitExperiment.rankedItems)
      .withColumn('enriched_items', exploitExperiment.enrichedItems)
      .withColumn('selected_item', exploitExperiment.selectedItem)
      .withColumn('selected_items', exploitExperiment.selectedItems)
      .run({ key: exploitExperiment.rowKey });
    return { pilot, scorecard, selectionArtifact, selection, exploit };
  },
  {
    description:
      'Exercise code-native route fanout, RRF, reranking, selection, and atomic exploit without provider spend.',
  },
);
