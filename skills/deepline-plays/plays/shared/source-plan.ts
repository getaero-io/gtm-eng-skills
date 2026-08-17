/**
 * Compile a source-plan contract into a fetch topology before binding it to
 * live tools. This is intentionally provider-agnostic: catalog discovery
 * decides native versus generic routes at task-authoring time.
 */

export type ResearchQueryType =
  | 'gtm_dataset'
  | 'private_workflow'
  | 'custom_language'
  | 'how_to'
  | 'concept'
  | 'comparison'
  | 'product'
  | 'opinion'
  | 'prediction'
  | 'breaking_news';

export type SourcePlanInput = {
  objective: string;
  queryType: ResearchQueryType;
  sourceFamilies: readonly string[];
  extractionKeys: readonly string[];
  /** Stable row identifiers already supplied by the caller. */
  initialInputs?: readonly string[];
};

export type StrategyStage = {
  id:
    | 'public-fanout'
    | 'artifact-resolution'
    | 'identity-resolution'
    | 'private-join'
    | 'supplemental-gap-fill'
    | 'terminal-extraction';
  mode: 'parallel' | 'dependency' | 'gap-only';
  sourceFamilies: string[];
  requires: string[];
  /** At least one of these inputs must be available when listed. */
  requiresAnyOf?: string[];
  produces: string[];
  reason: string;
};

export type SourceLeg = {
  sourceFamily: string;
  class: 'public' | 'private' | 'unknown';
  execution: 'discover_then_fetch' | 'private_connector' | 'catalog_gap_check';
  requiresCatalogDiscovery: boolean;
};

export type FetchStrategyPlan = {
  objective: string;
  queryType: ResearchQueryType;
  routeFamily:
    | 'materializable-source-fetch'
    | 'public-to-private-join'
    | 'evidence-to-language'
    | 'evidence-verified-answer';
  sourceContract: SourceLeg[];
  initialInputs: string[];
  terminalExtractionKeys: string[];
  stages: StrategyStage[];
};

const PRIVATE_SOURCES = new Set(['crm', 'warehouse', 'workflow', 'support']);
const PUBLIC_SOURCES = new Set([
  'web',
  'reddit',
  'x',
  'github',
  'youtube',
  'tiktok',
  'instagram',
  'hn',
  'bluesky',
  'polymarket',
]);

const TERMINAL_PROVENANCE_KEYS = [
  'source_family',
  'source_status',
  'source_url',
  'canonical_id',
  'evidence',
];

function unique(values: readonly string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}

function routeFamily(
  queryType: ResearchQueryType,
): FetchStrategyPlan['routeFamily'] {
  if (queryType === 'gtm_dataset') return 'materializable-source-fetch';
  if (queryType === 'private_workflow') return 'public-to-private-join';
  if (queryType === 'custom_language') return 'evidence-to-language';
  return 'evidence-verified-answer';
}

/**
 * Keep every planned source and requested key through compilation. Losing an
 * extraction key because a route changed creates plausible-looking, incomplete
 * results that cannot be detected after the run.
 */
export function compileSourcePlan(input: SourcePlanInput): FetchStrategyPlan {
  const objective = input.objective.trim();
  const sourceFamilies = unique(input.sourceFamilies);
  const extractionKeys = unique(input.extractionKeys);
  const initialInputs = unique(['objective', ...(input.initialInputs ?? [])]);
  if (!objective) throw new Error('A source plan needs an objective.');
  if (!sourceFamilies.length)
    throw new Error('A source plan needs at least one source family.');
  if (!extractionKeys.length)
    throw new Error('A source plan needs at least one extraction key.');

  const publicSources = sourceFamilies.filter((source) =>
    PUBLIC_SOURCES.has(source),
  );
  const privateSources = sourceFamilies.filter((source) =>
    PRIVATE_SOURCES.has(source),
  );
  const unknownSources = sourceFamilies.filter(
    (source) => !PUBLIC_SOURCES.has(source) && !PRIVATE_SOURCES.has(source),
  );
  const discoverySources = unique([...publicSources, ...unknownSources]);
  if (input.queryType === 'gtm_dataset' && !discoverySources.length)
    throw new Error(
      'A materializable dataset plan needs a public or catalog-gap discovery source.',
    );
  if (input.queryType === 'private_workflow' && !privateSources.length)
    throw new Error(
      'A private workflow plan needs at least one CRM, warehouse, workflow, or support source.',
    );
  const identityInputs = [
    'canonical_id',
    'domain_or_account_key',
    'crm_object_id',
  ];
  if (
    privateSources.length &&
    !discoverySources.length &&
    !identityInputs.some((key) => initialInputs.includes(key))
  )
    throw new Error(
      'A private-only plan needs a canonical_id, domain_or_account_key, or crm_object_id input.',
    );
  const sourceContract: SourceLeg[] = sourceFamilies.map((sourceFamily) => ({
    sourceFamily,
    class: PRIVATE_SOURCES.has(sourceFamily)
      ? 'private'
      : PUBLIC_SOURCES.has(sourceFamily)
        ? 'public'
        : 'unknown',
    execution: PRIVATE_SOURCES.has(sourceFamily)
      ? 'private_connector'
      : PUBLIC_SOURCES.has(sourceFamily)
        ? 'discover_then_fetch'
        : 'catalog_gap_check',
    requiresCatalogDiscovery: true,
  }));

  const stages: StrategyStage[] = [];
  if (discoverySources.length) {
    stages.push({
      id: 'public-fanout',
      mode: 'parallel',
      sourceFamilies: discoverySources,
      requires: ['objective'],
      produces: [
        'source_url',
        'canonical_id',
        'candidate_artifact',
        'evidence',
        ...extractionKeys,
      ],
      reason:
        'Search independent public sources in parallel, then retain source provenance for the fetch and extraction pass.',
    });
  }
  if (input.queryType === 'gtm_dataset') {
    stages.push({
      id: 'artifact-resolution',
      mode: 'dependency',
      sourceFamilies: discoverySources,
      requires: ['candidate_artifact'],
      produces: [
        'canonical_id',
        'source_url',
        'schema_or_endpoint',
        'stable_join_key',
      ],
      reason:
        'Resolve a named dataset family into its canonical artifact before creating rows or spending on enrichment.',
    });
  }
  if (privateSources.length) {
    const privateJoinKeys = unique(
      privateSources.flatMap((source) => {
        if (source === 'crm') return ['crm_object_id'];
        if (source === 'warehouse') return ['warehouse_join_key'];
        if (source === 'workflow') return ['workflow_run_id'];
        return ['support_ticket_id'];
      }),
    );
    stages.push({
      id: 'identity-resolution',
      mode: 'dependency',
      sourceFamilies: [],
      requires: discoverySources.length ? ['canonical_id'] : [],
      ...(discoverySources.length ? {} : { requiresAnyOf: identityInputs }),
      produces: privateJoinKeys,
      reason:
        'Private joins need a resolved identity; querying broad private data first creates unverifiable matches and unnecessary cost.',
    });
    stages.push({
      id: 'private-join',
      mode: 'dependency',
      sourceFamilies: privateSources,
      requires: privateJoinKeys,
      produces: [
        'evidence',
        'private_evidence',
        'private_provenance',
        ...extractionKeys,
      ],
      reason:
        'Join only authorized private records to the public evidence cluster and preserve their provenance separately.',
    });
  }
  stages.push({
    id: 'supplemental-gap-fill',
    mode: 'gap-only',
    sourceFamilies,
    requires: ['evidence'],
    produces: extractionKeys,
    reason:
      'Spend only on unresolved keys with a materially independent source; never rerun the same broad search cosmetically.',
  });
  stages.push({
    id: 'terminal-extraction',
    mode: 'dependency',
    sourceFamilies: [],
    requires: ['evidence'],
    produces: unique([...extractionKeys, ...TERMINAL_PROVENANCE_KEYS]),
    reason:
      'Emit one inspectable terminal record per unit with every requested extraction key and evidence needed to audit it.',
  });

  return {
    objective,
    queryType: input.queryType,
    routeFamily: routeFamily(input.queryType),
    sourceContract,
    initialInputs,
    terminalExtractionKeys: unique([
      ...TERMINAL_PROVENANCE_KEYS,
      ...(privateSources.length ? ['private_provenance'] : []),
      ...extractionKeys,
    ]),
    stages,
  };
}

/** Return any planner requirements that a compiled topology silently lost. */
export function sourcePlanContractGaps(
  input: Pick<SourcePlanInput, 'sourceFamilies' | 'extractionKeys'>,
  strategy: Pick<
    FetchStrategyPlan,
    'sourceContract' | 'terminalExtractionKeys'
  >,
): { sourceFamilies: string[]; extractionKeys: string[] } {
  const actualSources = new Set(
    strategy.sourceContract.map((leg) => leg.sourceFamily),
  );
  const actualKeys = new Set(strategy.terminalExtractionKeys);
  return {
    sourceFamilies: unique(input.sourceFamilies).filter(
      (source) => !actualSources.has(source),
    ),
    extractionKeys: unique(input.extractionKeys).filter(
      (key) => !actualKeys.has(key),
    ),
  };
}
