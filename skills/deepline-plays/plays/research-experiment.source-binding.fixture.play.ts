import { definePlay } from 'deepline';
import {
  bindResearchEvidenceToSource,
  compileResearchExperiment,
  defineResearchExperiment,
  matchesResearchSourcePolicy,
  parseResearchSourceDate,
  type CandidateOutcome,
  type ExperimentAttempt,
} from './shared/research-experiment';

type FixtureRow = {
  id: string;
  canonical_domain: string;
  /** URL that the adapter reports after fetching, not merely its request URL. */
  returned_source_url: string;
  requested_url?: string;
  source_policy: 'first_party_only' | 'non_first_party_only';
  raw_source_text: string;
  evidence_excerpt: string;
  claim_value: string;
  date_excerpt: string;
  expected_date: string;
  kind: 'quote' | 'derived';
  expected_status: 'verified' | 'insufficient_evidence' | 'rejected';
};

const FIXTURES: FixtureRow[] = [
  {
    id: 'valid-first-party-quote-and-date',
    canonical_domain: 'cloudflare.com',
    returned_source_url: 'https://www.cloudflare.com/news/example',
    source_policy: 'first_party_only',
    raw_source_text:
      'Cloudflare announced a new security feature on April 7, 2026.',
    evidence_excerpt:
      'Cloudflare announced a new security feature on April 7, 2026.',
    claim_value:
      'Cloudflare announced a new security feature on April 7, 2026.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'verified',
  },
  {
    id: 'extractor-only-quote',
    canonical_domain: 'cloudflare.com',
    returned_source_url: 'https://www.cloudflare.com/news/example',
    source_policy: 'first_party_only',
    raw_source_text: 'Cloudflare published a product update.',
    evidence_excerpt: 'Cloudflare doubled revenue.',
    claim_value: 'Cloudflare doubled revenue.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'value-not-in-bound-quote',
    canonical_domain: 'cloudflare.com',
    returned_source_url: 'https://www.cloudflare.com/news/example',
    source_policy: 'first_party_only',
    raw_source_text:
      'Cloudflare announced a new security feature on April 7, 2026.',
    evidence_excerpt:
      'Cloudflare announced a new security feature on April 7, 2026.',
    claim_value: 'Cloudflare doubled revenue.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'whitespace-altered-quote',
    canonical_domain: 'example.com',
    returned_source_url: 'https://example.com/news/example',
    source_policy: 'first_party_only',
    raw_source_text:
      'Example announced a new workflow product on April 7, 2026.',
    evidence_excerpt:
      'Example announced a new  workflow product on April 7, 2026.',
    claim_value: 'Example announced a new workflow product on April 7, 2026.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'ambiguous-source-date',
    canonical_domain: 'cloudflare.com',
    returned_source_url: 'https://www.cloudflare.com/news/example',
    source_policy: 'first_party_only',
    raw_source_text:
      'Cloudflare announced a new security feature on 04/07/2026.',
    evidence_excerpt:
      'Cloudflare announced a new security feature on 04/07/2026.',
    claim_value: 'Cloudflare announced a new security feature on 04/07/2026.',
    date_excerpt: '04/07/2026',
    expected_date: '',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'first-party-policy-host-spoof',
    canonical_domain: 'cloudflare.com',
    returned_source_url: 'https://not-cloudflare.com/news/example',
    source_policy: 'first_party_only',
    raw_source_text:
      'Cloudflare announced a new security feature on April 7, 2026.',
    evidence_excerpt:
      'Cloudflare announced a new security feature on April 7, 2026.',
    claim_value:
      'Cloudflare announced a new security feature on April 7, 2026.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'first-party-request-redirected-external',
    canonical_domain: 'cloudflare.com',
    requested_url: 'https://www.cloudflare.com/news/example',
    returned_source_url: 'https://redirect.example.net/news/example',
    source_policy: 'first_party_only',
    raw_source_text:
      'Cloudflare announced a new security feature on April 7, 2026.',
    evidence_excerpt:
      'Cloudflare announced a new security feature on April 7, 2026.',
    claim_value:
      'Cloudflare announced a new security feature on April 7, 2026.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'independent-request-redirected-first-party',
    canonical_domain: 'example.com',
    requested_url: 'https://news.example.net/releases/example',
    returned_source_url: 'https://example.com/releases/example',
    source_policy: 'non_first_party_only',
    raw_source_text:
      'Example announced a new workflow product on April 7, 2026.',
    evidence_excerpt:
      'Example announced a new workflow product on April 7, 2026.',
    claim_value: 'Example announced a new workflow product on April 7, 2026.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'invalid-canonical-domain',
    canonical_domain: 'not a valid host',
    returned_source_url: 'https://news.example.net/releases/example',
    source_policy: 'non_first_party_only',
    raw_source_text:
      'Example announced a new workflow product on April 7, 2026.',
    evidence_excerpt:
      'Example announced a new workflow product on April 7, 2026.',
    claim_value: 'Example announced a new workflow product on April 7, 2026.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'multiple-source-dates',
    canonical_domain: 'cloudflare.com',
    returned_source_url: 'https://www.cloudflare.com/news/example',
    source_policy: 'first_party_only',
    raw_source_text:
      'Cloudflare announced a new security feature on April 7, 2026. It became available May 1, 2026.',
    evidence_excerpt:
      'Cloudflare announced a new security feature on April 7, 2026. It became available May 1, 2026.',
    claim_value:
      'Cloudflare announced a new security feature on April 7, 2026. It became available May 1, 2026.',
    date_excerpt:
      'Cloudflare announced a new security feature on April 7, 2026. It became available May 1, 2026.',
    expected_date: '',
    kind: 'quote',
    expected_status: 'insufficient_evidence',
  },
  {
    id: 'valid-independent-source',
    canonical_domain: 'example.com',
    returned_source_url: 'https://news.example.net/releases/example',
    source_policy: 'non_first_party_only',
    raw_source_text:
      'Example announced a new workflow product on April 7, 2026.',
    evidence_excerpt:
      'Example announced a new workflow product on April 7, 2026.',
    claim_value: 'Example announced a new workflow product on April 7, 2026.',
    date_excerpt: 'April 7, 2026',
    expected_date: '2026-04-07',
    kind: 'quote',
    expected_status: 'verified',
  },
  {
    id: 'derived-value-rejected-by-contract',
    canonical_domain: 'example.com',
    returned_source_url: 'https://example.com/',
    source_policy: 'first_party_only',
    raw_source_text: 'Example provides workflow software.',
    evidence_excerpt: 'Example provides workflow software.',
    claim_value: 'smb',
    date_excerpt: '',
    expected_date: '',
    kind: 'derived',
    expected_status: 'rejected',
  },
];

const experiment = compileResearchExperiment(
  defineResearchExperiment<FixtureRow, undefined>({
    input: { rowKey: 'id', required: ['id', 'canonical_domain'] },
    claims: [
      {
        id: 'quote',
        question:
          'Is the exact claim value bound to an allowed source and date?',
        required: false,
        maximumEvidenceAgeDays: 365,
        referenceDate: '2026-08-11',
        allowAuthoritativeSingle: true,
        accept: ({ row, evidence }) => ({
          accepted: evidence.some(
            (item) => item.publishedAt === row.expected_date,
          ),
          reason: 'The source-bound date must equal the fixture date.',
        }),
      },
      {
        id: 'derived',
        question:
          'Does the explicit deterministic derivation accept this value?',
        required: false,
        minimumEvidence: 0,
        minimumIndependentEvidenceClasses: 0,
        requireValueInEvidence: false,
        accept: ({ claim }) => ({
          accepted: claim.value === 'enterprise',
          reason: 'Only the declared enterprise derivation is accepted.',
        }),
      },
    ],
    candidates: [
      {
        id: 'fixture',
        hypothesis: 'Exercise source-binding guards without provider calls.',
        run: async () => ({ claims: {} }),
      },
    ],
  }),
);

function outcomeFor(row: FixtureRow): CandidateOutcome {
  if (row.kind === 'derived') {
    return { claims: { derived: { value: row.claim_value, evidence: [] } } };
  }
  const parsedDate = parseResearchSourceDate(row.date_excerpt);
  const policyAllowsSource = matchesResearchSourcePolicy(
    row.returned_source_url,
    row.canonical_domain,
    row.source_policy,
  );
  const evidence = policyAllowsSource
    ? bindResearchEvidenceToSource({
        source: 'fixture-source',
        independenceClass: new URL(row.returned_source_url).hostname,
        url: row.returned_source_url,
        excerpt: row.evidence_excerpt,
        rawSourceText: row.raw_source_text,
        ...(parsedDate ? { dateExcerpt: row.date_excerpt } : {}),
        authority:
          row.source_policy === 'first_party_only'
            ? 'authoritative'
            : 'supporting',
      })
    : null;
  return {
    claims: {
      quote: {
        value: row.claim_value,
        evidence: evidence ? [evidence] : [],
      },
    },
  };
}

export default definePlay(
  'research-source-binding-fixture',
  async (ctx) => {
    const attempts: ExperimentAttempt<FixtureRow>[] = FIXTURES.map((row) => ({
      row,
      candidateId: 'fixture',
      outcome: outcomeFor(row),
    }));
    const evaluations = experiment.evaluate(attempts);
    const results = await ctx
      .dataset(
        'source_binding_results',
        evaluations.map((evaluation) => {
          const row = evaluation.row;
          const claim = evaluation.claims.find((item) =>
            row.kind === 'derived'
              ? item.claimId === 'derived'
              : item.claimId === 'quote',
          );
          if (!claim) throw new Error(`Fixture claim missing for ${row.id}.`);
          return {
            id: row.id,
            expected_status: row.expected_status,
            actual_status: claim.status,
            pass: claim.status === row.expected_status,
            evidence_count: claim.evidence.length,
            evidence_url: claim.evidence[0]?.url ?? '',
            evidence_excerpt: claim.evidence[0]?.text ?? '',
            published_at: claim.evidence[0]?.publishedAt ?? '',
            reason: claim.reason,
          };
        }),
      )
      .run({
        key: 'id',
        description:
          'Exercise raw-source, source-policy, exact-value, date, and derived-value guards without provider calls.',
      });
    const failed = (await results.materialize(FIXTURES.length)).filter(
      (row) => !row.pass,
    );
    if (failed.length) {
      throw new Error(
        `Source-binding fixture mismatches: ${failed.map((row) => row.id).join(', ')}.`,
      );
    }
    return { results };
  },
  {
    description:
      'Provider-free adversarial fixture for research evidence binding and source-policy guards.',
  },
);
