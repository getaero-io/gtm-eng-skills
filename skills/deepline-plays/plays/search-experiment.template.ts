import { definePlay } from 'deepline';
import {
  bindResearchEvidenceToSource,
  type ResearchClaimValue,
} from './shared/research-experiment';
import { extractGroundedPersonCandidates } from './shared/grounded-extraction';
import {
  runSearchExperiment,
  type SearchProgram,
  verifiedSearchClaimValue,
} from './shared/search-experiment';

type ScopeRow = {
  scope: string;
};

const rows: ScopeRow[] = [{ scope: 'replace-with-a-real-input-scope' }];

function bindLiteralClaim(input: {
  value: unknown;
  source: string;
  independenceClass: string;
  excerpt: string;
  rawSourceText: string;
  url?: string;
}): ResearchClaimValue | undefined {
  const evidence = bindResearchEvidenceToSource({
    source: input.source,
    independenceClass: input.independenceClass,
    excerpt: input.excerpt,
    rawSourceText: input.rawSourceText,
    ...(input.url ? { url: input.url } : {}),
    authority: 'authoritative',
  });
  return evidence ? { value: input.value, evidence: [evidence] } : undefined;
}

export default definePlay(
  'search-experiment-template',
  async (ctx) => {
    const programs: SearchProgram<ScopeRow, typeof ctx>[] = [
      {
        id: 'seed',
        hypothesis: 'The most likely mechanism can discover useful candidates.',
        maximumCallsPerAttempt: 1,
        async run({ row, gaps }) {
          void row;
          void gaps;
          // CATALOG_REQUIRED: replace this return with one literal call:
          // const response = await ctx.tools.execute({
          //   id: 'described-tool-id', tool: 'described-tool-id',
          //   input: { described_input: row.scope },
          //   description: 'Resolve this scope with the seed mechanism.',
          // });
          // const raw = JSON.stringify(response.toolResponse.raw);
          // const value = response.extractedValues.described_value.get();
          // const claim = bindLiteralClaim({
          //   value, source: 'described-tool-id', independenceClass: 'terminal-corpus',
          //   excerpt: String(value), rawSourceText: raw,
          // });
          // return { totalCalls: 1, results: claim ? [{
          //   resultKey: row.scope, canonicalEntityKey: row.scope,
          //   claims: { entity_identity: claim },
          // }] : [] };
          void bindLiteralClaim;
          return { totalCalls: 0, deeplineCredits: 0, results: [] };
        },
      },
      {
        id: 'evidence-closer',
        hypothesis:
          'An independent mechanism can verify unresolved claims on discovered candidates.',
        maximumCallsPerAttempt: 1,
        async run({ candidates, gaps }) {
          if (!candidates.length || !gaps.length)
            return { totalCalls: 0, deeplineCredits: 0, results: [] };
          // CATALOG_REQUIRED: fetch/refetch candidate sources and bind only gaps.
          // Set deeplineCredits only from this attempt's receipt; otherwise omit it.
          // Use this extractor only when the contract contains a person claim.
          void extractGroundedPersonCandidates;
          return { totalCalls: 0, results: [] };
        },
      },
    ];

    const experiment = await runSearchExperiment({
      ctx,
      rows,
      definition: {
        contract: {
          rowKey: 'scope',
          targetRows: 1,
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
        comparisonUnitCount: 1,
        pilotUnitCount: Math.min(4, rows.length),
        holdoutUnitCount: rows.length >= 3 ? 1 : 0,
        maxFallbacks: 1,
      },
    });

    // Consume accepted values through the public accessor. Do not inspect the
    // copied helper or trust raw provider fields at the output boundary.
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
  {
    description:
      'Dataset-conditioned search experiment. Replace the contract and literal program bodies.',
  },
);
