import { definePlay } from 'deepline';
import { bindResearchEvidenceToSource } from './shared/research-experiment';
import {
  runSearchExperiment,
  routeScorecardRows,
  type SearchProgram,
  verifiedSearchClaimValue,
} from './shared/search-experiment';
import { attempt, boundClaim, found } from './shared/search-strategy';
// Change route mechanism, input, extraction, entity key, and source geometry.
type ScopeRow = { scope: string };
const rows: ScopeRow[] = [{ scope: 'replace-with-live-input' }];
// List only programs with literal mechanisms; delete unused dormant programs.
const boundProgramIds: readonly string[] = [];
function assertBound(
  programs: readonly { id: string; diversityFeatures?: readonly string[] }[],
) {
  if (
    rows.some((row) => row.scope.includes('replace-with')) ||
    programs
      .flatMap((program) => program.diversityFeatures ?? [])
      .some((value) => value.includes('replace-with'))
  ) {
    throw new Error(
      'CATALOG_REQUIRED: replace scaffold rows and route geometry.',
    );
  }
  const missingProgramIds = programs
    .map((program) => program.id)
    .filter((id) => !boundProgramIds.includes(id));
  if (missingProgramIds.length > 0) {
    throw new Error(
      `CATALOG_REQUIRED: bind every registered strategy body to an executable mechanism (${missingProgramIds.join(', ')}).`,
    );
  }
}
export default definePlay(
  'search-experiment-template',
  async (ctx) => {
    const programs: SearchProgram<ScopeRow, typeof ctx>[] = [
      {
        id: 'incumbent',
        hypothesis: 'The proven route covers this contract cheaply.',
        incumbent: true,
        diversityFeatures: ['replace-with-source', 'replace-with-pivot'],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        tools: [], // catalog tool ids for the observed-credit join; [] = calls none
        async run({ row }) {
          // Run `tools describe <id> --json | show-declared-getters.py` and copy one getter.
          // const response = await ctx.tools.execute({ id: 'described-tool-id',
          //   tool: 'described-tool-id', input: { described_input: row.scope }, description: 'First route.' });
          // const value = response.extractedValues.described_value?.get() ?? null;
          // List getters: map rows through `list.keys`, never a guessed raw path.
          // Worked example in SKILL.md, "Catalog".
          // Raw is evidence context for boundClaim, never first extraction.
          // const raw = JSON.stringify(response.toolResponse.raw);
          // `boundClaim` calls bindResearchEvidenceToSource: an unbound value is a candidate, not a claim.
          // const claim = boundClaim({ value, source: 'described-tool-id', independenceClass: 'terminal-corpus', excerpt: String(value), rawSourceText: raw });
          // return attempt({ totalCalls: 1, results: claim ? [found({ canonicalEntityKey: String(value), claims: { entity_identity: claim } })] : [] });
          void row;
          void attempt;
          void boundClaim;
          void found;
          void bindResearchEvidenceToSource;
          throw new Error('CATALOG_REQUIRED: bind incumbent.');
        },
      },
      {
        id: 'independent-challenger',
        hypothesis: 'A distinct terminal corpus improves coverage or evidence.',
        diversityFeatures: ['replace-with-independent'],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        tools: [],
        async run({ row }) {
          // Change tool, literal input, named getter, lineage, and evidence rule.
          void row;
          throw new Error('CATALOG_REQUIRED: bind independent challenger.');
        },
      },
      {
        id: 'dormant-challenger',
        hypothesis: 'A third path recovers only verified gaps.',
        diversityFeatures: ['replace-with-dormant'],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        tools: [],
        async run({ row }) {
          // An active-route variant spent only on verified gaps.
          void row;
          throw new Error('CATALOG_REQUIRED: bind dormant challenger.');
        },
      },
    ];
    assertBound(programs);
    const experiment = await runSearchExperiment({
      ctx,
      rows,
      definition: {
        contract: {
          rowKey: 'scope',
          // Omit targetRows to maximize coverage; cohort rules set pass floors.
          claims: [
            {
              id: 'entity_identity',
              question: 'What exact entity satisfies this scope?',
              minimumEvidence: 2,
              minimumIndependentEvidenceClasses: 2,
            },
          ],
          minimumPilotCompleteRows: 1,
          // One row can pass every `accept` and still mix two entities; this is the only cross-claim gate.
          coherenceChecks: [],
        },
        programs,
        explorationProgramCount: 2,
      },
    });
    const outputRows = rows.map((row) => {
      const result = experiment.finalResults.find(
        (candidate) =>
          candidate.unitKey === row.scope.trim() && candidate.complete,
      );
      return {
        scope: row.scope,
        status: result ? 'verified' : 'unresolved',
        entity_identity: result
          ? verifiedSearchClaimValue<string>(result, 'entity_identity')
          : null,
        program_lineage: result?.programIds.join(' -> ') ?? null,
      };
    });
    const results = await ctx.dataset('search_results', outputRows).run({
      key: 'scope',
      description: 'Accepted rows plus explicit unresolved scopes.',
    });
    const scorecard = await ctx
      .dataset('route_scorecard', routeScorecardRows(experiment.scorecard))
      .run({
        key: 'program_id',
        description: 'Measured route coverage, reliability, and Deepline cost.',
      });
    return { experiment, results, scorecard };
  },
  { description: 'Compare, exploit, recover' },
);
