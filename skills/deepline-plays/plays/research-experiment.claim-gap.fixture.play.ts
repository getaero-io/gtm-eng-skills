import { definePlay } from 'deepline';
import {
  bindResearchEvidenceToSource,
  compileResearchExperiment,
  defineResearchExperiment,
  fillResearchClaimGaps,
  getResearchClaimGaps,
  matchesResearchSourcePolicy,
  type CandidateOutcome,
  type ResearchClaimValue,
  type ResearchEvidence,
} from './shared/research-experiment';

type FixtureRow = {
  id: string;
  company: string;
  domain: string;
  expectedPrimaryGaps: string;
  expectedFinalGaps: string;
  expectedSupplementUsed: boolean;
  expectedOfferSource: 'home' | 'claim-family';
};

const FIXTURES: FixtureRow[] = [
  {
    id: 'homepage-offer-gap-only-claim-family-fetch',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: 'market_language|primary_buyer',
    expectedFinalGaps: '',
    expectedSupplementUsed: true,
    expectedOfferSource: 'home',
  },
  {
    id: 'homepage-complete-skips-supplement',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: '',
    expectedFinalGaps: '',
    expectedSupplementUsed: false,
    expectedOfferSource: 'home',
  },
  {
    id: 'social-proof-is-not-primary-buyer',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: 'primary_buyer',
    expectedFinalGaps: '',
    expectedSupplementUsed: true,
    expectedOfferSource: 'home',
  },
  {
    id: 'claim-family-final-url-redirected-external',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: 'primary_buyer',
    expectedFinalGaps: 'primary_buyer',
    expectedSupplementUsed: true,
    expectedOfferSource: 'home',
  },
  {
    id: 'claim-family-extractor-value-not-raw',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: 'primary_buyer',
    expectedFinalGaps: 'primary_buyer',
    expectedSupplementUsed: true,
    expectedOfferSource: 'home',
  },
  {
    id: 'external-event-one-publisher-needs-corroborator',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: 'dated_company_signal',
    expectedFinalGaps: '',
    expectedSupplementUsed: true,
    expectedOfferSource: 'home',
  },
  {
    id: 'external-event-same-publisher-does-not-corroborate',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: 'dated_company_signal',
    expectedFinalGaps: 'dated_company_signal',
    expectedSupplementUsed: true,
    expectedOfferSource: 'home',
  },
  {
    id: 'ambiguous-event-date-remains-a-gap',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: 'dated_company_signal',
    expectedFinalGaps: 'dated_company_signal',
    expectedSupplementUsed: true,
    expectedOfferSource: 'home',
  },
  {
    id: 'verified-home-claim-cannot-be-overwritten',
    company: 'Example',
    domain: 'example.com',
    expectedPrimaryGaps: 'primary_buyer',
    expectedFinalGaps: '',
    expectedSupplementUsed: true,
    expectedOfferSource: 'home',
  },
];

const definition = defineResearchExperiment<FixtureRow, undefined>({
  input: { rowKey: 'id', required: ['id', 'company', 'domain'] },
  claims: [
    {
      id: 'offer',
      question: 'What exact offer language does the company use?',
      requiredFacts: ['company'],
      allowAuthoritativeSingle: true,
      accept: ({ claim }) => ({
        accepted: /platform|software|automation/i.test(
          String(claim.value ?? ''),
        ),
        reason:
          'Offer must state a product, platform, software, or capability.',
      }),
    },
    {
      id: 'primary_buyer',
      question: 'What exact audience does the company serve?',
      requiredFacts: ['company'],
      allowAuthoritativeSingle: true,
      accept: ({ claim }) => ({
        accepted:
          /\b(for|built for|designed for|serving)\b/i.test(
            String(claim.value ?? ''),
          ) &&
          /\b(team|teams|leader|leaders|developer|developers)\b/i.test(
            String(claim.value ?? ''),
          ) &&
          !/^trusted by|^used by/i.test(String(claim.value ?? '')),
        reason:
          'Buyer must be a direct audience statement, not customer-count social proof.',
      }),
    },
    {
      id: 'market_language',
      question: 'What exact market language does the company use?',
      requiredFacts: ['company'],
      allowAuthoritativeSingle: true,
      accept: ({ claim }) => ({
        accepted: /compliance|security|risk|market|industry/i.test(
          String(claim.value ?? ''),
        ),
        reason:
          'Market language must identify a category, industry, or segment.',
      }),
    },
    {
      id: 'dated_company_signal',
      question: 'What recent company-level event is corroborated?',
      requiredFacts: ['company'],
      minimumIndependentEvidenceClasses: 2,
      maximumEvidenceAgeDays: 30,
      referenceDate: '2026-08-11',
      allowAuthoritativeSingle: true,
      accept: ({ claim }) => ({
        accepted: /example.*announced/i.test(String(claim.value ?? '')),
        reason: 'Signal must be a company-level announcement.',
      }),
    },
  ],
  candidates: [
    {
      id: 'fixture',
      hypothesis: 'Evaluate first, then query only unresolved claim families.',
      run: async () => ({ claims: {} }),
    },
  ],
});

const experiment = compileResearchExperiment(definition);

function sourceEvidence(input: {
  row: FixtureRow;
  policy: 'first_party_only' | 'non_first_party_only';
  finalUrl: string;
  source: string;
  independenceClass: string;
  excerpt: string;
  rawSourceText?: string;
  authority?: 'authoritative' | 'supporting';
  dateExcerpt?: string;
}): ResearchEvidence | null {
  if (
    !matchesResearchSourcePolicy(input.finalUrl, input.row.domain, input.policy)
  ) {
    return null;
  }
  return bindResearchEvidenceToSource({
    source: input.source,
    independenceClass: input.independenceClass,
    url: input.finalUrl,
    excerpt: input.excerpt,
    rawSourceText: input.rawSourceText ?? input.excerpt,
    ...(input.authority ? { authority: input.authority } : {}),
    ...(input.dateExcerpt ? { dateExcerpt: input.dateExcerpt } : {}),
  });
}

function officialEvidence(
  row: FixtureRow,
  source: string,
  excerpt: string,
  options: { finalUrl?: string; rawSourceText?: string } = {},
): ResearchEvidence | null {
  return sourceEvidence({
    row,
    policy: 'first_party_only',
    finalUrl: options.finalUrl ?? `https://${row.domain}/${source}`,
    source,
    independenceClass: `official:${row.domain}`,
    excerpt,
    ...(options.rawSourceText ? { rawSourceText: options.rawSourceText } : {}),
    authority: 'authoritative',
  });
}

function externalEventEvidence(
  row: FixtureRow,
  finalUrl: string,
  independenceClass: string,
  context: string,
): ResearchEvidence | null {
  return sourceEvidence({
    row,
    policy: 'non_first_party_only',
    finalUrl,
    source: 'external-event',
    independenceClass,
    excerpt: context,
    rawSourceText: context,
    dateExcerpt: context,
  });
}

function evidenceList(
  ...items: Array<ResearchEvidence | null>
): ResearchEvidence[] {
  return items.filter((item): item is ResearchEvidence => item !== null);
}

function completeHomeClaims(
  row: FixtureRow,
): Record<string, ResearchClaimValue> {
  const offer = 'Example automation platform';
  const buyer = 'Built for security teams';
  const market = 'Security and compliance automation';
  const event = 'Example announced a new workflow on August 1, 2026.';
  return {
    offer: {
      value: offer,
      facts: { company: row.company },
      evidence: evidenceList(officialEvidence(row, 'home', offer)),
    },
    primary_buyer: {
      value: buyer,
      facts: { company: row.company },
      evidence: evidenceList(officialEvidence(row, 'home', buyer)),
    },
    market_language: {
      value: market,
      facts: { company: row.company },
      evidence: evidenceList(officialEvidence(row, 'home', market)),
    },
    dated_company_signal: {
      value: event,
      facts: { company: row.company },
      evidence: evidenceList(
        sourceEvidence({
          row,
          policy: 'first_party_only',
          finalUrl: `https://${row.domain}/news/august`,
          source: 'official-news',
          independenceClass: `official-news:${row.domain}`,
          excerpt: event,
          authority: 'authoritative',
          dateExcerpt: event,
        }),
      ),
    },
  };
}

function primaryClaims(row: FixtureRow): Record<string, ResearchClaimValue> {
  const claims = completeHomeClaims(row);
  const noBuyer = {
    abstainReason: 'Home page did not establish a primary buyer.',
  };
  switch (row.id) {
    case 'homepage-offer-gap-only-claim-family-fetch':
      claims.primary_buyer = noBuyer;
      claims.market_language = {
        abstainReason: 'Home page did not establish market language.',
      };
      return claims;
    case 'social-proof-is-not-primary-buyer': {
      const socialProof = 'Trusted by 100 security teams';
      claims.primary_buyer = {
        value: socialProof,
        facts: { company: row.company },
        evidence: evidenceList(officialEvidence(row, 'home', socialProof)),
      };
      return claims;
    }
    case 'claim-family-final-url-redirected-external':
    case 'claim-family-extractor-value-not-raw':
    case 'verified-home-claim-cannot-be-overwritten':
      claims.primary_buyer = noBuyer;
      return claims;
    case 'external-event-one-publisher-needs-corroborator':
    case 'external-event-same-publisher-does-not-corroborate': {
      const event = 'Example announced a new workflow on August 1, 2026.';
      claims.dated_company_signal = {
        value: event,
        facts: { company: row.company },
        evidence: evidenceList(
          externalEventEvidence(
            row,
            'https://news-one.example.net/example-launch',
            'publisher:news-one',
            event,
          ),
        ),
      };
      return claims;
    }
    case 'ambiguous-event-date-remains-a-gap': {
      const event =
        'Example announced a new workflow on April 7, 2026 and released it May 1, 2026.';
      claims.dated_company_signal = {
        value: event,
        facts: { company: row.company },
        evidence: evidenceList(
          externalEventEvidence(
            row,
            'https://news-one.example.net/example-launch',
            'publisher:news-one',
            event,
          ),
        ),
      };
      return claims;
    }
    default:
      return claims;
  }
}

function supplementalClaims(
  row: FixtureRow,
): Record<string, ResearchClaimValue> {
  const buyer = 'Built for security teams';
  const market = 'Security and compliance automation';
  const event = 'Example announced a new workflow on August 1, 2026.';
  switch (row.id) {
    case 'homepage-offer-gap-only-claim-family-fetch':
      return {
        primary_buyer: {
          value: buyer,
          facts: { company: row.company },
          evidence: evidenceList(
            officialEvidence(row, 'solutions/security', buyer),
          ),
        },
        market_language: {
          value: market,
          facts: { company: row.company },
          evidence: evidenceList(
            officialEvidence(row, 'industries/security', market),
          ),
        },
      };
    case 'social-proof-is-not-primary-buyer':
    case 'verified-home-claim-cannot-be-overwritten':
      return {
        offer: {
          value: 'Different software',
          facts: { company: row.company },
          evidence: evidenceList(
            officialEvidence(row, 'wrong-claim-family', 'Different software'),
          ),
        },
        primary_buyer: {
          value: buyer,
          facts: { company: row.company },
          evidence: evidenceList(
            officialEvidence(row, 'solutions/security', buyer),
          ),
        },
      };
    case 'claim-family-final-url-redirected-external':
      return {
        primary_buyer: {
          value: buyer,
          facts: { company: row.company },
          evidence: evidenceList(
            officialEvidence(row, 'solutions/security', buyer, {
              finalUrl: 'https://redirect.example.net/security',
            }),
          ),
        },
      };
    case 'claim-family-extractor-value-not-raw':
      return {
        primary_buyer: {
          value: buyer,
          facts: { company: row.company },
          evidence: evidenceList(
            officialEvidence(row, 'solutions/security', buyer, {
              rawSourceText: 'Example supports security leaders.',
            }),
          ),
        },
      };
    case 'external-event-one-publisher-needs-corroborator':
      return {
        dated_company_signal: {
          value: event,
          facts: { company: row.company },
          evidence: evidenceList(
            externalEventEvidence(
              row,
              'https://news-one.example.net/example-launch',
              'publisher:news-one',
              event,
            ),
            externalEventEvidence(
              row,
              'https://news-two.example.org/example-launch',
              'publisher:news-two',
              event,
            ),
          ),
        },
      };
    case 'external-event-same-publisher-does-not-corroborate':
      return {
        dated_company_signal: {
          value: event,
          facts: { company: row.company },
          evidence: evidenceList(
            externalEventEvidence(
              row,
              'https://news-one.example.net/example-launch',
              'publisher:news-one',
              event,
            ),
            externalEventEvidence(
              row,
              'https://news-one.example.net/follow-up',
              'publisher:news-one',
              event,
            ),
          ),
        },
      };
    case 'ambiguous-event-date-remains-a-gap':
      return {
        dated_company_signal: {
          value: event,
          facts: { company: row.company },
          evidence: evidenceList(
            externalEventEvidence(
              row,
              'https://news-two.example.org/example-launch',
              'publisher:news-two',
              event,
            ),
          ),
        },
      };
    default:
      return {};
  }
}

function gapIds(gaps: ReturnType<typeof getResearchClaimGaps>): string {
  return gaps
    .map((gap) => gap.claimId)
    .sort()
    .join('|');
}

export default definePlay(
  'research-claim-gap-fixture',
  async (ctx) => {
    const rows = FIXTURES.map((row) => {
      const primary = primaryClaims(row);
      const primaryGaps = getResearchClaimGaps({
        row,
        definitions: definition.claims,
        claims: primary,
      });
      const supplementUsed = primaryGaps.length > 0;
      const finalClaims = supplementUsed
        ? fillResearchClaimGaps({
            row,
            definitions: definition.claims,
            primary,
            supplemental: supplementalClaims(row),
            gapIds: primaryGaps.map((gap) => gap.claimId),
          })
        : primary;
      const finalGaps = getResearchClaimGaps({
        row,
        definitions: definition.claims,
        claims: finalClaims,
      });
      const evaluation = experiment.evaluate([
        {
          row,
          candidateId: 'fixture',
          outcome: { claims: finalClaims } satisfies CandidateOutcome,
        },
      ])[0];
      const offerEvidenceUrl = evaluation?.claims.find(
        (claim) => claim.claimId === 'offer',
      )?.evidence[0]?.url;
      const offerSource = offerEvidenceUrl?.includes('/home')
        ? 'home'
        : 'claim-family';
      const actualPrimaryGaps = gapIds(primaryGaps);
      const actualFinalGaps = gapIds(finalGaps);
      return {
        id: row.id,
        expected_primary_gaps: row.expectedPrimaryGaps,
        actual_primary_gaps: actualPrimaryGaps,
        expected_final_gaps: row.expectedFinalGaps,
        actual_final_gaps: actualFinalGaps,
        expected_supplement_used: row.expectedSupplementUsed,
        actual_supplement_used: supplementUsed,
        expected_offer_source: row.expectedOfferSource,
        actual_offer_source: offerSource,
        pass:
          actualPrimaryGaps === row.expectedPrimaryGaps &&
          actualFinalGaps === row.expectedFinalGaps &&
          supplementUsed === row.expectedSupplementUsed &&
          offerSource === row.expectedOfferSource,
      };
    });
    const results = await ctx.dataset('claim_gap_results', rows).run({
      key: 'id',
      description:
        'Exercise gap-only claim-family planning and adversarial source outcomes without provider calls.',
    });
    const failed = (await results.materialize(FIXTURES.length)).filter(
      (row) => !row.pass,
    );
    if (failed.length) {
      throw new Error(
        `Claim-gap fixture mismatches: ${failed.map((row) => row.id).join(', ')}.`,
      );
    }
    return { results };
  },
  {
    description:
      'Provider-free adversarial fixture for gap-only research routes and claim-family evidence.',
  },
);
