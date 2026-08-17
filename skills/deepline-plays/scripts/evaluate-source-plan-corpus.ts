#!/usr/bin/env bun
/**
 * Offline bridge eval: prove that a last30days-parity pre-research source plan
 * survives compilation into an executable Deepline Play topology.
 *
 * This runs no tools or providers. The caller supplies the pre-research Python
 * planner and the corpus so each skill can remain independently packageable.
 */
import { spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import {
  compileSourcePlan,
  sourcePlanContractGaps,
  type ResearchQueryType,
} from '../plays/shared/source-plan';

type CorpusCase = {
  id: string;
  topic: string;
  expectedQueryTypes: ResearchQueryType[];
  mustIncludeSources?: string[];
  mustIncludeExtractionKeys?: string[];
};

type Corpus = {
  defaults: {
    depth?: 'quick' | 'default' | 'deep';
    requiredBaseSources?: string[];
    requiredBaseExtractionKeys?: string[];
  };
  cases: CorpusCase[];
};

function required(name: string): string {
  const index = process.argv.indexOf(name);
  const value = index >= 0 ? process.argv[index + 1] : undefined;
  if (!value || value.startsWith('--')) throw new Error(`${name} is required.`);
  return value;
}

function optional(name: string): string | undefined {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function unique(values: readonly string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}

function expectedStages(queryType: ResearchQueryType): string[] {
  if (queryType === 'gtm_dataset')
    return [
      'public-fanout',
      'artifact-resolution',
      'supplemental-gap-fill',
      'terminal-extraction',
    ];
  if (queryType === 'private_workflow')
    return [
      'public-fanout',
      'identity-resolution',
      'private-join',
      'supplemental-gap-fill',
      'terminal-extraction',
    ];
  return ['public-fanout', 'supplemental-gap-fill', 'terminal-extraction'];
}

function expectedRouteFamily(queryType: ResearchQueryType): string {
  if (queryType === 'gtm_dataset') return 'materializable-source-fetch';
  if (queryType === 'private_workflow') return 'public-to-private-join';
  if (queryType === 'custom_language') return 'evidence-to-language';
  return 'evidence-verified-answer';
}

const RESEARCH_QUERY_TYPES = new Set<ResearchQueryType>([
  'gtm_dataset',
  'private_workflow',
  'custom_language',
  'how_to',
  'concept',
  'comparison',
  'product',
  'opinion',
  'prediction',
  'breaking_news',
]);

function strings(value: unknown, name: string): string[] {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== 'string'))
    throw new Error(`pre-research planner returned invalid ${name}.`);
  return value;
}

function parsePlannerPlan(planned: Record<string, unknown>): {
  queryType: ResearchQueryType;
  sourceFamilies: string[];
  extractionKeys: string[];
} {
  const queryType = planned.query_type;
  if (
    typeof queryType !== 'string' ||
    !RESEARCH_QUERY_TYPES.has(queryType as ResearchQueryType)
  )
    throw new Error(
      `pre-research planner returned unsupported query_type: ${String(queryType)}`,
    );
  const enabled = planned.enabled_sources;
  if (!enabled || typeof enabled !== 'object' || Array.isArray(enabled))
    throw new Error('pre-research planner returned invalid enabled_sources.');
  const sourceFamilies = unique(
    Object.values(enabled as Record<string, unknown>).flatMap((value) =>
      strings(value, 'enabled_sources values'),
    ),
  );
  return {
    queryType: queryType as ResearchQueryType,
    sourceFamilies,
    extractionKeys: strings(planned.extraction_keys, 'extraction_keys'),
  };
}

function runPreResearchPlanner(input: {
  planner: string;
  topic: string;
  depth: string;
  sources: string[];
}): Record<string, unknown> {
  const result = spawnSync(
    'python3',
    [
      input.planner,
      input.topic,
      '--depth',
      input.depth,
      '--sources',
      input.sources.join(','),
    ],
    { encoding: 'utf8' },
  );
  if (result.status !== 0)
    throw new Error(
      `pre-research planner failed for ${input.topic}: ${result.stderr}`,
    );
  return JSON.parse(result.stdout) as Record<string, unknown>;
}

function markdown(output: Record<string, unknown>): string {
  const cases = output.cases as Array<Record<string, unknown>>;
  const passed = cases.filter((entry) => entry.same_or_better).length;
  const lines = [
    '# Deepline Plays Source-Plan Fetch Eval',
    '',
    `Result: ${passed}/${cases.length} cases preserve last30days-parity source plans through executable fetch topology compilation.`,
    '',
    '| Case | Route | Fetch route | Missing sources | Missing keys | Missing stages | Result |',
    '| --- | --- | --- | --- | --- | --- | --- |',
  ];
  for (const entry of cases) {
    const text = (key: string) => {
      const value = entry[key];
      return Array.isArray(value)
        ? value.join(', ') || 'none'
        : String(value ?? 'none');
    };
    lines.push(
      `| ${entry.id} | ${entry.actual_route} | ${entry.fetch_route_family} | ${text('missing_sources')} | ${text('missing_extraction_keys')} | ${text('missing_stages')} | ${entry.same_or_better ? 'same_or_better' : 'gap'} |`,
    );
  }
  lines.push(
    '',
    'This offline eval checks strategy topology only. It does not claim provider availability or execute retrieval.',
    '',
  );
  return lines.join('\n');
}

const corpusPath = required('--corpus');
const plannerPath = required('--pre-research-planner');
const outJson = optional('--out-json');
const outMd = optional('--out-md');
const corpus = JSON.parse(readFileSync(corpusPath, 'utf8')) as Corpus;
const defaults = corpus.defaults;

const cases = corpus.cases.map((testCase) => {
  const expectedSources = unique([
    ...(defaults.requiredBaseSources ?? []),
    ...(testCase.mustIncludeSources ?? []),
  ]);
  const expectedKeys = unique([
    ...(defaults.requiredBaseExtractionKeys ?? []),
    ...(testCase.mustIncludeExtractionKeys ?? []),
  ]);
  const planned = runPreResearchPlanner({
    planner: plannerPath,
    topic: testCase.topic.replace(' --agent', '').trim(),
    depth: defaults.depth ?? 'deep',
    sources: expectedSources,
  });
  const plannerPlan = parsePlannerPlan(planned);
  const actualRoute = plannerPlan.queryType;
  const strategy = compileSourcePlan({
    objective: testCase.topic,
    queryType: actualRoute,
    sourceFamilies: plannerPlan.sourceFamilies,
    extractionKeys: plannerPlan.extractionKeys,
  });
  const preserved = sourcePlanContractGaps(
    {
      sourceFamilies: plannerPlan.sourceFamilies,
      extractionKeys: plannerPlan.extractionKeys,
    },
    strategy,
  );
  const actualSources = strategy.sourceContract.map((leg) => leg.sourceFamily);
  const actualKeys = strategy.terminalExtractionKeys;
  const actualStages: string[] = strategy.stages.map((stage) => stage.id);
  const requiredStages = expectedStages(actualRoute);
  const missingSources = expectedSources.filter(
    (source) => !actualSources.includes(source),
  );
  const missingKeys = expectedKeys.filter((key) => !actualKeys.includes(key));
  const missingStages = requiredStages.filter(
    (stage) => !actualStages.includes(stage),
  );
  return {
    id: testCase.id,
    expected_routes: testCase.expectedQueryTypes,
    actual_route: actualRoute,
    fetch_route_family: strategy.routeFamily,
    missing_sources: missingSources,
    missing_extraction_keys: missingKeys,
    missing_stages: missingStages,
    dropped_planner_sources: preserved.sourceFamilies,
    dropped_planner_extraction_keys: preserved.extractionKeys,
    route_family_matches_query_type:
      strategy.routeFamily === expectedRouteFamily(actualRoute),
    same_or_better:
      testCase.expectedQueryTypes.includes(actualRoute) &&
      !missingSources.length &&
      !missingKeys.length &&
      !missingStages.length &&
      !preserved.sourceFamilies.length &&
      !preserved.extractionKeys.length &&
      strategy.routeFamily === expectedRouteFamily(actualRoute),
  };
});

const output = {
  total_cases: cases.length,
  same_or_better_cases: cases.filter((entry) => entry.same_or_better).length,
  all_same_or_better: cases.every((entry) => entry.same_or_better),
  cases,
};
if (outJson) {
  mkdirSync(dirname(outJson), { recursive: true });
  writeFileSync(outJson, `${JSON.stringify(output, null, 2)}\n`);
}
if (outMd) {
  mkdirSync(dirname(outMd), { recursive: true });
  writeFileSync(outMd, markdown(output));
}
console.log(
  JSON.stringify({
    total_cases: output.total_cases,
    same_or_better_cases: output.same_or_better_cases,
    all_same_or_better: output.all_same_or_better,
  }),
);
if (!output.all_same_or_better) process.exit(1);
