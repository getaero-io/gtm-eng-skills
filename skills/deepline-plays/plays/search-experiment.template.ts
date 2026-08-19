import { definePlay } from 'deepline';
import {
  runSearchExperiment,
  type SearchProgram,
  verifiedSearchClaimValue,
} from './shared/search-experiment';
import { attempt, boundClaim, found } from './shared/search-strategy';

type ScopeRow = { scope: string };

// 1. Replace this with supplied rows, a small CSV-derived sample, or bounded
// source scopes. The row key is the input unit, not a discovered candidate.
const rows: ScopeRow[] = [{ scope: 'replace-with-a-real-input-scope' }];

export default definePlay(
  'search-experiment-template',
  async (ctx) => {
    // 2. A strategy is ordinary TypeScript. It can call one provider, several
    // sequential tools, fetch a public source, or use local code. Add 3–5
    // structurally different strategies by copying a block below. The helper
    // pilots a small shared wave in parallel; it does not spend every strategy
    // on every row.
    const programs: SearchProgram<ScopeRow, typeof ctx>[] = [
      {
        id: 'structured-source',
        hypothesis: 'A structured source directly covers this scope.',
        diversityFeatures: ['structured-index', 'pivot:scope'],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        async run({ row }) {
          // 3. Copy this call and replace exactly: tool, input, getter, source,
          // lineage. `tools describe <tool>` is the authority for input and
          // getter names. Never guess a raw response path. This draft throws
          // before a paid run until all five marked values are real.
          void row;
          throw new Error(
            'CATALOG_REQUIRED: replace the structured-source strategy block with one described tool call.',
          );
          // const response = await ctx.tools.execute({
          //   id: 'stable_step_id', tool: 'described_tool_id',
          //   input: { described_input: row.scope }, description: 'Describe the lookup.',
          // });
          // const value = response.extractedValues.described_getter?.get() ?? null;
          // if (!value) return attempt({ totalCalls: 1 }); // typed source miss
          // const entity = String(value).trim();
          // const claim = boundClaim({ value: entity, source: 'described_tool_id',
          //   independenceClass: 'structured-corpus', excerpt: entity,
          //   rawSourceText: JSON.stringify(response.toolResponse.raw ?? null) });
          // return attempt({ totalCalls: 1, results: [found({
          //   canonicalEntityKey: entity, claims: { entity_identity: claim },
          // })] });
        },
      },
      {
        id: 'public-source',
        hypothesis: 'A distinct public source directly covers this scope.',
        diversityFeatures: ['first-party-web', 'pivot:scope'],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        async run({ row }) {
          // Copy/edit this whole block for another source geometry. A different
          // vendor with the same terminal corpus is a coverage challenger, not
          // independent claim consensus.
          void row;
          throw new Error(
            'CATALOG_REQUIRED: replace the public-source strategy block with one described tool call.',
          );
          // Use the same `attempt → found → boundClaim` shape as above, with a
          // distinct source corpus, join, or proof path.
        },
      },
    ];

    const experiment = await runSearchExperiment({
      ctx,
      rows,
      definition: {
        contract: {
          rowKey: 'scope',
          // This is the desired coverage target. A weaker acceptable floor is
          // a cohort check, never a reason to stop recoverable rows early.
          targetRows: rows.length,
          claims: [
            {
              id: 'entity_identity',
              question: 'What exact entity satisfies this scope?',
              allowAuthoritativeSingle: true,
            },
          ],
          minimumPilotCompleteRows: 1,
        },
        programs,
        // maximumDeeplineCredits: <whole-experiment cap>,
      },
    });

    const verifiedRows = experiment.finalResults
      .filter((result) => result.complete)
      .map((result) => ({
        ...result.row,
        canonical_entity_key: result.canonicalEntityKey,
        entity_identity: verifiedSearchClaimValue<string>(
          result,
          'entity_identity',
        ),
      }));

    return { experiment, verifiedRows };
  },
  { description: 'Explore and exploit a verified GTM search route' },
);
