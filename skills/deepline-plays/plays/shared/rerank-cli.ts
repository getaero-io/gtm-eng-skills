#!/usr/bin/env bun
// ===========================================================================
// rerank-cli — the runnable batched-judge wrapper. Deterministic in, model
// step delegated to a cheap subagent, deterministic out.
// ===========================================================================
//
// The skill's 3-tier loop uses this AFTER a route-fanout research run:
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
//   No subagent available / want pure-deterministic? Skip 2-3 and run:
//   bun rerank-cli.ts fallback --shortlist shortlist.json
//
// The shortlist may be the raw research `findings` array (with title/url/snippet/
// relevance/entity_miss) — build/fallback both auto-adapt it via fromFindings.

import { readFileSync } from 'node:fs';
import {
  applyRerank,
  buildRerankPrompt,
  fallbackRank,
  fromFindings,
  parseModelScores,
  type Intent,
  type RerankItem,
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

function fail(msg: string): never {
  process.stderr.write(`rerank-cli: ${msg}\n`);
  process.exit(1);
}

function readJson(path: string): unknown {
  const text = path === '-' ? readFileSync(0, 'utf8') : readFileSync(path, 'utf8');
  try {
    return JSON.parse(text);
  } catch (e) {
    fail(`could not parse JSON from ${path}: ${(e as Error).message}`);
  }
}

// Accept either RerankItem[] or the raw research findings array.
function toItems(raw: unknown): RerankItem[] {
  const arr = Array.isArray(raw)
    ? raw
    : raw && typeof raw === 'object' && Array.isArray((raw as { findings?: unknown }).findings)
      ? (raw as { findings: unknown[] }).findings
      : null;
  if (!arr) fail('shortlist must be a JSON array (RerankItem[] or research findings[])');
  const list = arr as Array<Record<string, unknown>>;
  // Heuristic: if items look like findings (snake_case entity_miss or no `id`), adapt.
  const looksLikeFindings = list.some((r) => 'entity_miss' in r || (!('id' in r) && 'url' in r));
  return looksLikeFindings ? fromFindings(list as never) : (list as unknown as RerankItem[]);
}

function getFlag(args: string[], name: string): string | undefined {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : undefined;
}

function main(): void {
  const [sub, ...args] = process.argv.slice(2);
  if (!sub || ['-h', '--help', 'help'].includes(sub)) {
    process.stdout.write(
      'usage:\n' +
        '  rerank-cli build --shortlist <f.json> --query "..." [--intent <i>] [--entity "..."]\n' +
        '  rerank-cli apply --shortlist <f.json> --scores <s.json>\n' +
        '  rerank-cli fallback --shortlist <f.json>\n' +
        `intents: ${INTENTS.join(', ')}\n`,
    );
    return;
  }

  const shortlistPath = getFlag(args, 'shortlist');
  if (!shortlistPath) fail('missing --shortlist');
  const items = toItems(readJson(shortlistPath));

  if (sub === 'build') {
    const query = getFlag(args, 'query');
    if (!query) fail('build requires --query');
    const intentRaw = getFlag(args, 'intent');
    const intent = (intentRaw ?? 'general') as Intent;
    if (!INTENTS.includes(intent)) fail(`unknown --intent "${intentRaw}" (use: ${INTENTS.join(', ')})`);
    const primaryEntity = getFlag(args, 'entity');
    process.stdout.write(buildRerankPrompt(query, items, { intent, primaryEntity }) + '\n');
    return;
  }

  if (sub === 'apply') {
    const scoresPath = getFlag(args, 'scores');
    if (!scoresPath) fail('apply requires --scores');
    const scores = parseModelScores(readJson(scoresPath));
    process.stdout.write(JSON.stringify(applyRerank(items, scores), null, 2) + '\n');
    return;
  }

  if (sub === 'fallback') {
    process.stdout.write(JSON.stringify(fallbackRank(items), null, 2) + '\n');
    return;
  }

  fail(`unknown subcommand "${sub}" (build | apply | fallback)`);
}

main();
