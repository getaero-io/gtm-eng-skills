#!/usr/bin/env bun
// ===========================================================================
// rerank-cli — the runnable batched-judge wrapper. Deterministic in, model
// step delegated to a cheap subagent, deterministic out.
// ===========================================================================
//
// The skill's 3-tier loop uses this after a route-experiment research run:
//
//   1. Extract the shortlist from the run output (the research `findings`) to a
//      JSON file, e.g. shortlist.json = [{title,url,snippet,relevance,entity_miss}].
//
//   2. bun rerank-cli.ts build --shortlist shortlist.json \
//        --query "Stripe recent funding" --intent factual --entity "Stripe" > prompt.txt
//
//   3. Hand prompt.txt to a CHEAP subagent (Haiku-class — NOT deeplineagent).
//      It returns {"scores":[{"id":"<url>","score":0-100}]}. Save as scores.json.
//
//   4. bun rerank-cli.ts apply --shortlist shortlist.json --scores scores.json
//      -> the reranked list (JSON), best-first.
//
// For people, companies, or arbitrary entities, replace --query/--intent with
// --task task.json. The task supplies criteria, disqualifiers, and an optional
// deterministic blend policy. The same --task file must be passed to apply or
// fallback so ranking uses that policy:
//
//   bun rerank-cli.ts build --shortlist entities.json --task task.json
//   bun rerank-cli.ts apply --shortlist entities.json --scores scores.json --task task.json
//
//   No subagent available / want pure-deterministic? Skip 2-3 and run:
//   bun rerank-cli.ts fallback --shortlist shortlist.json
//
// The shortlist may be the raw research `findings` array (with title/url/snippet/
// relevance/entity_miss) — build/fallback both auto-adapt it via fromFindings.

import { readFileSync } from 'node:fs';
import {
  applyRerank,
  buildRerankPrompt,
  buildTaskRerankPrompt,
  ENTITY_RETRIEVAL_POLICY,
  fallbackRank,
  fromFindings,
  parseModelScores,
  policyForTask,
  type Intent,
  type RerankItem,
  type RerankPolicy,
  type RerankTask,
} from './rerank';

const INTENTS: Intent[] = [
  'comparison',
  'how_to',
  'prediction',
  'factual',
  'opinion',
  'breaking_news',
  'concept',
  'product',
  'general',
];

export class RerankCliError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RerankCliError';
  }
}

function fail(msg: string): never {
  throw new RerankCliError(msg);
}

function readJson(path: string): unknown {
  const text =
    path === '-' ? readFileSync(0, 'utf8') : readFileSync(path, 'utf8');
  try {
    return JSON.parse(text);
  } catch (e) {
    fail(`could not parse JSON from ${path}: ${(e as Error).message}`);
  }
}

// Accept either RerankItem[] or the raw research findings array.
export function toItems(raw: unknown): RerankItem[] {
  const arr = Array.isArray(raw)
    ? raw
    : raw &&
        typeof raw === 'object' &&
        Array.isArray((raw as { findings?: unknown }).findings)
      ? (raw as { findings: unknown[] }).findings
      : null;
  if (!arr)
    fail(
      'shortlist must be a JSON array (RerankItem[] or research findings[])',
    );
  if (
    arr.some((row) => !row || typeof row !== 'object' || Array.isArray(row))
  ) {
    fail('every shortlist item must be a JSON object');
  }
  const list = arr as Array<Record<string, unknown>>;
  // Heuristic: if items look like findings (snake_case entity_miss or no `id`), adapt.
  const looksLikeFindings = list.some(
    (r) => 'entity_miss' in r || (!('id' in r) && 'url' in r),
  );
  if (looksLikeFindings) validateRawFindings(list);
  const items = looksLikeFindings
    ? fromFindings(list as never)
    : (list as unknown as RerankItem[]);
  if (items.length === 0) fail('shortlist contains no rankable items');
  validateItems(items);
  return items;
}

function getFlag(args: string[], name: string): string | undefined {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : undefined;
}

function readTask(path: string | undefined): RerankTask | undefined {
  if (!path) return undefined;
  return parseTask(readJson(path));
}

export function parseTask(raw: unknown): RerankTask {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    fail('task must be a JSON object');
  }
  const task = raw as Partial<RerankTask>;
  if (typeof task.question !== 'string' || !task.question.trim()) {
    fail('task.question must be a non-empty string');
  }
  for (const name of ['primaryEntity', 'scoreMeaning'] as const) {
    if (task[name] != null && typeof task[name] !== 'string') {
      fail(`task.${name} must be a string`);
    }
  }
  if (task.criteria != null && !Array.isArray(task.criteria)) {
    fail('task.criteria must be an array of strings');
  }
  if (task.criteria?.some((value) => typeof value !== 'string')) {
    fail('task.criteria must contain only strings');
  }
  if (task.disqualifiers != null && !Array.isArray(task.disqualifiers)) {
    fail('task.disqualifiers must be an array of strings');
  }
  if (task.disqualifiers?.some((value) => typeof value !== 'string')) {
    fail('task.disqualifiers must contain only strings');
  }
  if (task.kind != null) validateKind(task.kind, 'task.kind');
  if (task.policy != null) validatePolicy(task.policy);
  return task as RerankTask;
}

function validateKind(value: unknown, field: string): void {
  if (
    typeof value !== 'string' ||
    !value.trim() ||
    value !== value.trim() ||
    value.length > 80 ||
    /[\u0000-\u001f\u007f<>]/.test(value)
  ) {
    fail(
      `${field} must be a non-empty task-defined string of at most 80 characters with no surrounding whitespace, control characters, or angle brackets`,
    );
  }
}

function validatePolicy(policy: RerankTask['policy']): void {
  if (!policy || typeof policy !== 'object' || Array.isArray(policy)) {
    fail('task.policy must be a JSON object');
  }
  const weights = policy.weights;
  if (!weights || typeof weights !== 'object' || Array.isArray(weights)) {
    fail('task.policy.weights must be a JSON object');
  }
  const names = [
    'model',
    'rrf',
    'relevance',
    'freshness',
    'sourceQuality',
    'engagement',
    'verification',
    'corroboration',
  ] as const;
  let total = 0;
  for (const name of names) {
    const value = weights[name] ?? 0;
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
      fail(`task.policy.weights.${name} must be a finite non-negative number`);
    }
    total += value;
  }
  if (total <= 0)
    fail('task.policy.weights must include at least one positive weight');
  if (
    policy.requireVerification != null &&
    typeof policy.requireVerification !== 'boolean'
  ) {
    fail('task.policy.requireVerification must be a boolean');
  }
  for (const name of [
    'entityMissPenalty',
    'unverifiedPenalty',
    'minimumVerification',
    'lowModelScoreThreshold',
    'lowModelScoreMultiplier',
    'entityMissFinalPenalty',
  ] as const) {
    const value = policy[name];
    if (
      value != null &&
      (typeof value !== 'number' ||
        !Number.isFinite(value) ||
        value < 0 ||
        value > 1)
    ) {
      fail(`task.policy.${name} must be a number from 0 to 1`);
    }
  }
}

function validateItems(items: RerankItem[]): void {
  const ids = new Set<string>();
  const stringFields = ['label', 'title', 'snippet', 'url', 'content'] as const;
  const scoreFields = [
    'relevance',
    'rrf',
    'freshness',
    'sourceQuality',
    'engagement',
    'verification',
    'corroboration',
  ] as const;
  for (const [index, item] of items.entries()) {
    if (typeof item.id !== 'string' || !item.id.trim()) {
      fail(`shortlist[${index}].id must be a non-empty string`);
    }
    if (
      item.id !== item.id.trim() ||
      item.id.length > 500 ||
      /[\u0000-\u001f\u007f<>]/.test(item.id)
    ) {
      fail(
        `shortlist[${index}].id must be at most 500 characters with no surrounding whitespace, control characters, or angle brackets`,
      );
    }
    if (ids.has(item.id)) {
      fail(`shortlist contains duplicate id "${item.id}"`);
    }
    ids.add(item.id);
    if (item.kind != null) validateKind(item.kind, `shortlist[${index}].kind`);
    for (const name of stringFields) {
      if (item[name] != null && typeof item[name] !== 'string') {
        fail(`shortlist[${index}].${name} must be a string`);
      }
    }
    for (const name of scoreFields) {
      const value = item[name];
      if (
        value != null &&
        (typeof value !== 'number' ||
          !Number.isFinite(value) ||
          value < 0 ||
          value > 1)
      ) {
        fail(`shortlist[${index}].${name} must be a number from 0 to 1`);
      }
    }
    for (const name of ['entityMiss', 'hardFail'] as const) {
      if (item[name] != null && typeof item[name] !== 'boolean') {
        fail(`shortlist[${index}].${name} must be a boolean`);
      }
    }
    if (
      item.attributes != null &&
      (typeof item.attributes !== 'object' || Array.isArray(item.attributes))
    ) {
      fail(`shortlist[${index}].attributes must be a JSON object`);
    }
    if (item.evidence != null && !Array.isArray(item.evidence)) {
      fail(`shortlist[${index}].evidence must be an array`);
    }
    for (const [evidenceIndex, evidence] of (item.evidence ?? []).entries()) {
      if (
        !evidence ||
        typeof evidence !== 'object' ||
        Array.isArray(evidence)
      ) {
        fail(
          `shortlist[${index}].evidence[${evidenceIndex}] must be a JSON object`,
        );
      }
      for (const name of ['source', 'url', 'text'] as const) {
        if (evidence[name] != null && typeof evidence[name] !== 'string') {
          fail(
            `shortlist[${index}].evidence[${evidenceIndex}].${name} must be a string`,
          );
        }
      }
    }
  }
}

function validateRawFindings(findings: Array<Record<string, unknown>>): void {
  const stringFields = ['title', 'url', 'snippet'] as const;
  const scoreFields = [
    'relevance',
    'rrf',
    'freshness',
    'source_quality',
    'engagement',
  ] as const;
  for (const [index, finding] of findings.entries()) {
    for (const name of stringFields) {
      if (finding[name] != null && typeof finding[name] !== 'string') {
        fail(`shortlist[${index}].${name} must be a string or null`);
      }
    }
    for (const name of scoreFields) {
      const value = finding[name];
      if (
        value != null &&
        (typeof value !== 'number' ||
          !Number.isFinite(value) ||
          value < 0 ||
          value > 1)
      ) {
        fail(`shortlist[${index}].${name} must be a number from 0 to 1`);
      }
    }
    if (
      finding.entity_miss != null &&
      typeof finding.entity_miss !== 'boolean'
    ) {
      fail(`shortlist[${index}].entity_miss must be a boolean`);
    }
  }
}

function hasDeterministicWeight(
  policy: NonNullable<RerankTask['policy']>,
): boolean {
  const weights = policy.weights;
  return (
    weights.rrf +
      weights.relevance +
      weights.freshness +
      (weights.sourceQuality ?? 0) +
      (weights.engagement ?? 0) +
      weights.verification +
      weights.corroboration >
    0
  );
}

export function validateFallbackPolicy(policy: RerankTask['policy']): void {
  if (policy && !hasDeterministicWeight(policy)) {
    fail('fallback requires at least one positive non-model policy weight');
  }
}

export function policyForInvocation(
  items: RerankItem[],
  task?: RerankTask,
): RerankPolicy | undefined {
  if (task) return policyForTask(task);
  return items.some((item) => item.kind != null && item.kind !== 'source')
    ? ENTITY_RETRIEVAL_POLICY
    : undefined;
}

function main(): void {
  const [sub, ...args] = process.argv.slice(2);
  if (!sub || ['-h', '--help', 'help'].includes(sub)) {
    process.stdout.write(
      'usage:\n' +
        '  rerank-cli build --shortlist <f.json> --query "..." [--intent <i>] [--entity "..."]\n' +
        '  rerank-cli build --shortlist <entities.json> --task <task.json>\n' +
        '  rerank-cli apply --shortlist <f.json> --scores <s.json> [--task <task.json>]\n' +
        '  rerank-cli fallback --shortlist <f.json> [--task <task.json>]\n' +
        `intents: ${INTENTS.join(', ')}\n`,
    );
    return;
  }

  const shortlistPath = getFlag(args, 'shortlist');
  if (!shortlistPath) fail('missing --shortlist');
  const items = toItems(readJson(shortlistPath));
  const task = readTask(getFlag(args, 'task'));
  const taskPolicy = policyForInvocation(items, task);

  if (sub === 'build') {
    if (task) {
      process.stdout.write(buildTaskRerankPrompt(task, items) + '\n');
      return;
    }
    const query = getFlag(args, 'query');
    if (!query) fail('build requires --query or --task');
    const intentRaw = getFlag(args, 'intent');
    const intent = (intentRaw ?? 'general') as Intent;
    if (!INTENTS.includes(intent))
      fail(`unknown --intent "${intentRaw}" (use: ${INTENTS.join(', ')})`);
    const primaryEntity = getFlag(args, 'entity');
    process.stdout.write(
      buildRerankPrompt(query, items, { intent, primaryEntity }) + '\n',
    );
    return;
  }

  if (sub === 'apply') {
    const scoresPath = getFlag(args, 'scores');
    if (!scoresPath) fail('apply requires --scores');
    const scores = parseModelScores(readJson(scoresPath));
    process.stdout.write(
      JSON.stringify(applyRerank(items, scores, taskPolicy), null, 2) + '\n',
    );
    return;
  }

  if (sub === 'fallback') {
    validateFallbackPolicy(taskPolicy);
    process.stdout.write(
      JSON.stringify(fallbackRank(items, taskPolicy), null, 2) + '\n',
    );
    return;
  }

  fail(`unknown subcommand "${sub}" (build | apply | fallback)`);
}

if ((import.meta as ImportMeta & { main?: boolean }).main === true) {
  try {
    main();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`rerank-cli: ${message}\n`);
    process.exitCode = 1;
  }
}
