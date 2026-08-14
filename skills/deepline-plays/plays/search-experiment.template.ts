import { definePlay } from 'deepline';
import {
  bindResearchEvidenceToSource,
  type ResearchClaimValue,
} from './shared/research-experiment';
import {
  applyRejectOnlyDecision,
  extractGroundedPersonCandidates,
} from './shared/grounded-extraction';
import {
  runSearchExperiment,
  type SearchProgram,
  type SearchProgramResult,
  verifiedSearchClaimValue,
} from './shared/search-experiment';

type ScopeRow = {
  scope: string;
};

// rowKey identifies the input unit being tested. canonicalEntityKey identifies
// a discovered result. They are usually different for open-world search.
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
        diversityFeatures: [
          'role:candidate-generator',
          'replace-with-source-universe',
          'replace-with-input-pivot',
        ],
        maximumCallsPerAttempt: 1,
        billingUnit: 'unknown',
        // Add maximumDeeplineCreditsPerAttempt from tools describe/quote when
        // this route cannot return an attempt-level billing receipt. Also set
        // billingUnit to the described call/result unit; leave it unknown when absent.
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
          // Candidate identity is the normalized discovered value, never the
          // input row key: email, domain, profile URL, source URL, stable ID.
          // const canonicalEntityKey = String(value);
          // const claim = bindLiteralClaim({
          //   value, source: 'described-tool-id', independenceClass: 'terminal-corpus',
          //   excerpt: String(value), rawSourceText: raw,
          // });
          // return { totalCalls: 1, results: claim ? [{
          //   resultKey: canonicalEntityKey, canonicalEntityKey,
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
        diversityFeatures: [
          'role:acceptance-test',
          'replace-with-independent-lineage',
          'pivot:canonical-entity',
        ],
        maximumCallsPerAttempt: 2,
        billingUnit: 'unknown',
        // Add maximumDeeplineCreditsPerAttempt from tools describe/quote when
        // this route cannot return an attempt-level billing receipt. Also set
        // billingUnit to the described call/result unit; leave it unknown when absent.
        async run({ candidates, gaps }) {
          if (!candidates.length || !gaps.length)
            return { totalCalls: 0, deeplineCredits: 0, results: [] };
          const candidatesToTest = candidates.slice(0, 2);
          const results: SearchProgramResult[] = [];
          for (const candidate of candidatesToTest) {
            // CATALOG_REQUIRED: call the acceptance mechanism, then push this
            // same candidate identity with either an accepted claim or a typed
            // verifier rejection. Different finder candidates are alternatives,
            // not hard failures merely because they disagree with each other.
            void candidate;
          }
          // CATALOG_REQUIRED: inspect candidatesToTest in order. For every
          // candidate called, emit the same canonicalEntityKey with either an
          // accepted claim or hardCheckFailures such as rejected:catch_all.
          // Never test only candidates[0] when another bounded sibling exists.
          // Set deeplineCredits only from this attempt's receipt; otherwise omit it.
          // Use this extractor only when the contract contains a person claim.
          // A model may pass grounded candidates through applyRejectOnlyDecision;
          // retained IDs can remove candidates but cannot create facts/evidence.
          void extractGroundedPersonCandidates;
          void applyRejectOnlyDecision;
          return { totalCalls: 0, results };
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
              // For a time-bounded claim, also set both fields:
              // maximumEvidenceAgeDays: 30,
              // referenceDate: 'YYYY-MM-DD',
            },
            {
              id: 'optional_supporting_signal',
              question:
                'What optional evidence would make this row more useful?',
              required: false,
            },
          ],
          cohortChecks: [
            {
              id: 'identity_coverage',
              minimumRatio: 1,
              // Allowed: pilot_units, eligible_results, complete_results.
              // targetRows is a stopping count, never a denominator.
              denominator: 'complete_results',
              verifiedClaimId: 'entity_identity',
            },
          ],
          minimumPilotCompleteRows: 1,
        },
        programs,
        // maximumDeeplineCredits: replace-with-a-whole-experiment-credit-cap,
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
