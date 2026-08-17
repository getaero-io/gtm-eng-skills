import { definePlay } from 'deepline';
import {
  compileResearchExperiment,
  defineResearchExperiment,
  type ExperimentAttempt,
  type ResearchCandidate,
  type ResearchEvidence,
} from './shared/research-experiment';

type Account = {
  account_id: string;
  company_name: string;
  domain: string;
};

type ExperimentContext = {
  phase: 'pilot' | 'exploit';
};

const REFERENCE_DATE = '2026-08-11';

const PILOT_ROWS: Account[] = [
  {
    account_id: 'acct_aurora',
    company_name: 'Aurora Metrics',
    domain: 'aurora-metrics.example',
  },
  {
    account_id: 'acct_brightline',
    company_name: 'Brightline Systems',
    domain: 'brightline-systems.example',
  },
  {
    account_id: 'acct_cascade',
    company_name: 'Cascade Works',
    domain: 'cascade-works.example',
  },
];

const EXPLOIT_ROWS: Account[] = [
  ...PILOT_ROWS,
  {
    account_id: 'acct_delta',
    company_name: 'Delta Ledger',
    domain: 'delta-ledger.example',
  },
  {
    account_id: 'acct_ember',
    company_name: 'Ember Support',
    domain: 'ember-support.example',
  },
];

function publicEvidence(
  row: Account,
  suffix: string,
  publishedAt?: string,
): ResearchEvidence {
  const excerptBySuffix: Record<string, string> = {
    'official-team': `${row.company_name} RevOps lead is VP, Revenue Operations.`,
    'professional-profile': `${row.company_name} RevOps lead is VP, Revenue Operations at ${row.company_name}.`,
    'official-news': `${row.company_name} announced a GTM hiring initiative.`,
  };
  return {
    source: `fixture-public-${suffix}`,
    independenceClass: suffix,
    url: `https://${row.domain}/${suffix}`,
    text: excerptBySuffix[suffix] ?? `${row.company_name} ${suffix} evidence.`,
    ...(publishedAt ? { publishedAt } : {}),
    authority: suffix.startsWith('official') ? 'authoritative' : 'supporting',
  };
}

function authorizedCrmEvidence(row: Account): ResearchEvidence {
  return {
    source: 'fixture-authorized-crm',
    independenceClass: 'authorized-crm',
    url: `crm://accounts/${row.account_id}`,
    text: `${row.company_name} authorized CRM account record ${row.account_id}.`,
    authority: 'authoritative',
  };
}

/**
 * Topology one deliberately cannot complete the authorized private join. That
 * is a valid, visible result of public-only research, not a value to infer.
 *
 * TODO for a live Play: put literal `rowCtx.tools.execute({ id, tool, input,
 * description })` calls here, then adapt the returned provider payload into
 * the three claim values below. Do not move those calls or the adapter into
 * `compileResearchExperiment`: the agent owns that semantic topology.
 */
const publicPeopleThenFirstParty: ResearchCandidate<
  Account,
  ExperimentContext
> = {
  id: 'public-people-then-first-party-signal',
  hypothesis:
    'Public people evidence plus first-party company pages can verify public claims cheaply, but cannot assert a private CRM match.',
  async run({ row }) {
    return {
      claims: {
        revops_leader: {
          value: `${row.company_name} RevOps lead`,
          facts: {
            full_name: `${row.company_name} RevOps lead`,
            title: 'VP, Revenue Operations',
            company: row.company_name,
          },
          evidence: [
            publicEvidence(row, 'official-team'),
            publicEvidence(row, 'professional-profile'),
          ],
        },
        recent_gtm_signal: {
          value: `${row.company_name} announced a GTM hiring initiative.`,
          facts: { company: row.company_name, signal_type: 'hiring' },
          evidence: [publicEvidence(row, 'official-news', '2026-07-23')],
        },
        crm_match: {
          abstainReason:
            'Public topology has no authorized private CRM access.',
        },
      },
      deeplineCredits: 0,
      durationMs: 120,
    };
  },
};

/**
 * Topology two starts from an explicitly authorized private identity, then
 * requires independently sourced public evidence for claims that will leave
 * the private system.
 *
 * TODO for a live Play: the CRM adapter must request only approved account
 * fields. Keep the public verification calls and response adapters here as
 * literal tool calls. Never make the compiler select a private provider or
 * derive a CRM match from model text.
 */
const authorizedCrmThenPublicVerification: ResearchCandidate<
  Account,
  ExperimentContext
> = {
  id: 'authorized-crm-then-public-verification',
  hypothesis:
    'An authorized CRM identity joined to independent public verification should complete all required claims with durable provenance.',
  async run({ row }) {
    return {
      claims: {
        revops_leader: {
          value: `${row.company_name} RevOps lead`,
          facts: {
            full_name: `${row.company_name} RevOps lead`,
            title: 'VP, Revenue Operations',
            company: row.company_name,
          },
          evidence: [
            publicEvidence(row, 'official-team'),
            publicEvidence(row, 'professional-profile'),
          ],
        },
        recent_gtm_signal: {
          value: `${row.company_name} announced a GTM hiring initiative.`,
          facts: { company: row.company_name, signal_type: 'hiring' },
          evidence: [publicEvidence(row, 'official-news', '2026-07-23')],
        },
        crm_match: {
          value: row.account_id,
          facts: { crm_account_id: row.account_id, matched_domain: row.domain },
          evidence: [authorizedCrmEvidence(row)],
        },
      },
      deeplineCredits: 0,
      durationMs: 170,
    };
  },
};

const definition = defineResearchExperiment<Account, ExperimentContext>({
  input: {
    rowKey: 'account_id',
    required: ['account_id', 'company_name', 'domain'],
    // The agent configures these exact aliases after inspecting the CSV. The
    // compiler never guesses them or rewrites input headers.
    columns: {
      account_id: 'HubSpot Company ID',
      company_name: 'Account Name',
      domain: 'Website',
    },
  },
  claims: [
    {
      id: 'revops_leader',
      question: 'Who is the current senior RevOps leader at this company?',
      requiredFacts: ['full_name', 'title', 'company'],
      minimumEvidence: 2,
      minimumIndependentEvidenceClasses: 2,
    },
    {
      id: 'recent_gtm_signal',
      question: 'What company-specific GTM event occurred in the last 90 days?',
      requiredFacts: ['company', 'signal_type'],
      minimumEvidence: 1,
      maximumEvidenceAgeDays: 90,
      referenceDate: REFERENCE_DATE,
      allowAuthoritativeSingle: true,
    },
    {
      id: 'crm_match',
      question: 'Which authorized CRM account is this?',
      requiredFacts: ['crm_account_id', 'matched_domain'],
      minimumEvidence: 1,
      allowAuthoritativeSingle: true,
      accept: ({ row, claim }) => ({
        accepted: claim.facts?.matched_domain === row.domain,
        reason: 'CRM match domain must equal the canonical input domain.',
      }),
    },
  ],
  candidates: [publicPeopleThenFirstParty, authorizedCrmThenPublicVerification],
  promotion: {
    require: {
      minimumVerifiedRequiredClaimCoverage: 0.95,
      minimumCompleteRows: 3,
      noAdapterFailures: true,
    },
    rank: [
      'verified_required_claim_coverage',
      'complete_rows',
      'independent_evidence_coverage',
      'deepline_credits_per_complete_row',
      'p95_duration_ms',
    ],
  },
});

const experiment = compileResearchExperiment(definition);

async function runCandidates(
  rows: readonly Account[],
  candidates: readonly ResearchCandidate<Account, ExperimentContext>[],
  phase: ExperimentContext['phase'],
): Promise<ExperimentAttempt<Account>[]> {
  return Promise.all(
    rows.flatMap((row) =>
      candidates.map(async (candidate) => ({
        row,
        candidateId: candidate.id,
        outcome: await candidate.run({ row, context: { phase } }),
      })),
    ),
  );
}

// Live adapter note: do not use this fixture-only helper to call tools across
// rows. A real Play must invoke `candidate.run` from a dataset `.withColumn`
// and pass that callback's `rowCtx` into the candidate context. That scopes a
// durable candidate outcome to its input row instead of collapsing all tool
// work into one opaque root-level JavaScript stage.

function claimRows(
  evaluations: ReturnType<typeof experiment.promote>['evaluations'],
) {
  return evaluations.flatMap((evaluation) =>
    evaluation.claims.map((claim) => ({
      id: `${evaluation.candidateId}|${evaluation.rowKey}|${claim.claimId}`,
      candidate_id: evaluation.candidateId,
      account_id: evaluation.rowKey,
      claim_id: claim.claimId,
      status: claim.status,
      reason: claim.reason,
      value: claim.value ?? null,
      fact_json: JSON.stringify(claim.facts),
      evidence_count: claim.evidence.length,
      independent_evidence_classes: claim.independentEvidenceClasses.join('|'),
    })),
  );
}

function evidenceRows(
  evaluations: ReturnType<typeof experiment.promote>['evaluations'],
) {
  return evaluations.flatMap((evaluation) =>
    evaluation.claims.flatMap((claim) =>
      claim.evidence.map((evidence, index) => ({
        id: `${evaluation.candidateId}|${evaluation.rowKey}|${claim.claimId}|${index}`,
        candidate_id: evaluation.candidateId,
        account_id: evaluation.rowKey,
        claim_id: claim.claimId,
        source: evidence.source,
        independence_class: evidence.independenceClass,
        authority: evidence.authority ?? 'supporting',
        url: evidence.url ?? '',
        excerpt: evidence.text ?? '',
        published_at: evidence.publishedAt ?? '',
      })),
    ),
  );
}

export default definePlay(
  'research-experiment-example',
  async (ctx) => {
    const pilotInput = await ctx
      .dataset('research_experiment_pilot_input', PILOT_ROWS)
      .run({
        key: 'account_id',
        description: 'Use the same denominator for every candidate topology.',
      });
    const pilotRows = await pilotInput.materialize(PILOT_ROWS.length);

    const pilotAttempts = await runCandidates(
      pilotRows,
      definition.candidates,
      'pilot',
    );
    const pilotResult = experiment.promote(pilotAttempts);

    const pilotScorecard = await ctx
      .dataset(
        'research_experiment_pilot_scorecard',
        pilotResult.promotion.scorecard.map((score) => ({
          id: score.candidateId,
          candidate_id: score.candidateId,
          hypothesis: score.hypothesis,
          eligible: score.eligible,
          exclusion_reasons: score.exclusionReasons.join('|'),
          pilot_rows: score.pilotRows,
          verified_required_claim_coverage: score.verifiedRequiredClaimCoverage,
          complete_rows: score.completeRows,
          independent_evidence_coverage: score.independentEvidenceCoverage,
          total_deepline_credits: score.totalDeeplineCredits,
          deepline_credits_per_complete_row:
            score.deeplineCreditsPerCompleteRow,
          p95_duration_ms: score.p95DurationMs,
          unobserved_credit_rows: score.unobservedCreditRows,
          unobserved_duration_rows: score.unobservedDurationRows,
          adapter_failures: score.adapterFailures.join('|'),
          policy_violations: score.policyViolations.join('|'),
        })),
      )
      .run({
        key: 'id',
        description: 'Compare candidate topologies on verified claim coverage.',
      });
    const pilotClaims = await ctx
      .dataset(
        'research_experiment_pilot_claims',
        claimRows(pilotResult.evaluations),
      )
      .run({
        key: 'id',
        description: 'Keep claim-level pilot evidence and gaps inspectable.',
      });
    const promotion = await ctx
      .dataset('research_experiment_promotion', [
        {
          id: 'promotion',
          status: pilotResult.promotion.status,
          selected_candidate_id:
            pilotResult.promotion.selectedCandidateId ?? '',
          reason: pilotResult.promotion.reason,
          promotion_json: JSON.stringify(pilotResult.promotion),
        },
      ])
      .run({
        key: 'id',
        description:
          'Persist the promotion decision before exploit work starts.',
      });

    if (pilotResult.promotion.status !== 'promoted') {
      return {
        pilotInput,
        pilotScorecard,
        pilotClaims,
        promotion,
        finalRows: null,
        finalClaims: null,
        finalEvidence: null,
      };
    }

    const selectedCandidate = definition.candidates.find(
      (candidate) => candidate.id === pilotResult.promotion.selectedCandidateId,
    );
    if (!selectedCandidate)
      throw new Error(
        'Promotion selected a candidate that is not in the program.',
      );

    const exploitAttempts = await runCandidates(
      EXPLOIT_ROWS,
      [selectedCandidate],
      'exploit',
    );
    const exploitEvaluations = experiment.evaluate(exploitAttempts);
    const finalRows = await ctx
      .dataset(
        'research_experiment_final_rows',
        exploitEvaluations.map((evaluation) => ({
          id: `${evaluation.candidateId}|${evaluation.rowKey}`,
          account_id: evaluation.rowKey,
          candidate_id: evaluation.candidateId,
          complete: evaluation.complete,
          deepline_credits: evaluation.deeplineCredits,
          duration_ms: evaluation.durationMs,
          adapter_failures: evaluation.adapterFailures.join('|'),
          policy_violations: evaluation.policyViolations.join('|'),
        })),
      )
      .run({
        key: 'id',
        description:
          'Run only the promoted topology over the full denominator.',
      });
    const finalClaims = await ctx
      .dataset(
        'research_experiment_final_claims',
        claimRows(exploitEvaluations),
      )
      .run({
        key: 'id',
        description: 'Persist each final claim with its acceptance outcome.',
      });
    const finalEvidence = await ctx
      .dataset(
        'research_experiment_final_evidence',
        evidenceRows(exploitEvaluations),
      )
      .run({
        key: 'id',
        description: 'Persist source-level evidence for every final claim.',
      });

    return {
      pilotInput,
      pilotScorecard,
      pilotClaims,
      promotion,
      finalRows,
      finalClaims,
      finalEvidence,
    };
  },
  {
    description:
      'Run two explicit research topologies on the same rows, promote on verified evidence, then exploit only the winner without provider spend.',
  },
);
