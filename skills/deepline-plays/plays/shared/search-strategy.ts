/**
 * Small authoring conveniences for ordinary search strategies.
 *
 * A strategy still owns its query, tool calls, and value mapping. These
 * helpers only keep the experiment boundary mechanical: exact evidence, a
 * candidate result, and a typed successful miss all have one spelling.
 */

import {
  bindResearchEvidenceToSource,
  type ResearchClaimValue,
} from './research-experiment';
import type {
  SearchProgramAttempt,
  SearchProgramResult,
} from './search-experiment';

export function boundClaim(input: {
  value: unknown;
  source: string;
  independenceClass: string;
  excerpt: string;
  rawSourceText: string;
  url?: string;
  authority?: 'authoritative' | 'supporting';
}): ResearchClaimValue {
  const evidence = bindResearchEvidenceToSource({
    source: input.source,
    independenceClass: input.independenceClass,
    excerpt: input.excerpt,
    rawSourceText: input.rawSourceText,
    ...(input.url ? { url: input.url } : {}),
    authority: input.authority ?? 'authoritative',
  });
  if (!evidence) {
    throw new Error(
      'A strategy getter returned a value that is absent from its source receipt.',
    );
  }
  return { value: input.value, evidence: [evidence] };
}

export function found(input: {
  canonicalEntityKey: string;
  claims: Readonly<Record<string, ResearchClaimValue | undefined>>;
  resultKey?: string;
  eligible?: boolean;
}): SearchProgramResult {
  return {
    resultKey: input.resultKey ?? input.canonicalEntityKey,
    canonicalEntityKey: input.canonicalEntityKey,
    claims: input.claims,
    ...(input.eligible === undefined ? {} : { eligible: input.eligible }),
  };
}

export function rejected(input: {
  canonicalEntityKey: string;
  failures: readonly string[];
  resultKey?: string;
}): SearchProgramResult {
  return {
    resultKey: input.resultKey ?? input.canonicalEntityKey,
    canonicalEntityKey: input.canonicalEntityKey,
    claims: {},
    hardCheckFailures: input.failures,
  };
}

export function attempt(input: {
  totalCalls: number;
  results?: readonly SearchProgramResult[];
  deeplineCredits?: number | null;
}): SearchProgramAttempt {
  return {
    totalCalls: input.totalCalls,
    results: input.results ?? [],
    ...(input.deeplineCredits === undefined
      ? {}
      : { deeplineCredits: input.deeplineCredits }),
  };
}
