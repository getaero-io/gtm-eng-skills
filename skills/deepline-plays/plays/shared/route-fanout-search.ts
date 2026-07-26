// ===========================================================================
// GOLDEN-TRUTH SCORING — the `mode: 'search'` scorer.
// ===========================================================================
//
// Plain deterministic play code, NOT a runtime primitive. Golden truth is a
// `<strategy>__truth` CSV column of known-correct values; this module joins it
// to each materialized cell and grades every route, so a small "sweep many
// providers over ~10 golden rows" run produces a ranked accuracy scorecard.
// Read the scorecard, carry the winners into the exploit `routes` list.
//
// It lives in shared/ (next to route-fanout-fields.ts / -signals.ts) so it is
// unit-testable without importing the play's `deepline` entrypoint — the engine
// math it reads (cell.state[route].candidates, cell.chosen) is owned by
// route-fanout-core.ts.

import {
  canonicalizeEmail,
  canonicalizePhone,
  type FanoutCell,
} from './route-fanout-core';

// One row of the search scorecard: how a single route performed against truth.
//  - tested:    golden rows graded (rows carrying a truth value) — same for all.
//  - attempted: rows where this route executed.
//  - filled:    rows where this route returned ≥1 candidate.
//  - correct:   rows where ANY of this route's candidates matched truth.
//  - precision: correct / filled (of what it returned, how much was right).
//  - recall:    correct / tested (of all gradable rows, how many it got).
export type RouteScore = {
  route: string;
  tested: number;
  attempted: number;
  filled: number;
  correct: number;
  precision: number;
  recall: number;
  // no_credential: rows where this route short-circuited on a missing credential.
  no_credential: number;
  // A route is UNCREDENTIALED when it filled nothing and every executed row hit
  // a missing credential. Its 0.0 precision/recall is NOT a fair score — it never
  // ran. Surfaced so route selection reads "connect this, then re-measure",
  // never "this route is bad". A field-note failure: uncredentialed providers
  // short-circuited to 0ms and their 0-fill read as "no coverage".
  uncredentialed: boolean;
};

// Field-aware truth match. Contact fields canonicalize (so formatting and
// +1/parenthesization differences fuse); anything else is normalized string
// equality. Exact-value match only — a domain-only hit is NOT counted correct.
export function matchTruth(
  fieldClass: string,
  candidate: string,
  truth: string,
): boolean {
  if (!candidate || !truth) return false;
  if (fieldClass === 'email') {
    const a = canonicalizeEmail(candidate);
    const b = canonicalizeEmail(truth);
    return a != null && a === b;
  }
  if (fieldClass === 'phone') {
    const a = canonicalizePhone(candidate);
    const b = canonicalizePhone(truth);
    return a != null && a === b;
  }
  return candidate.trim().toLowerCase() === truth.trim().toLowerCase();
}

// Grade every route against the golden truth on the materialized cells, plus a
// synthetic `[fused-winner]` row for what the engine would actually ship. Ranked
// best-first by correct, then precision, then filled.
export function scoreRoutesAgainstTruth(
  materialized: Array<{ cell?: FanoutCell; truth?: string }>,
  routeKeys: string[],
  fieldClass: string,
): RouteScore[] {
  // Only rows carrying golden truth are gradable.
  const graded = materialized.filter((row) => (row.truth ?? '').trim() !== '');
  const tested = graded.length;

  const scores: RouteScore[] = [];

  for (const key of routeKeys) {
    let attempted = 0;
    let filled = 0;
    let correct = 0;
    let noCredential = 0;
    for (const row of graded) {
      const state = row.cell?.state?.[key];
      if (!state) continue;
      if (state.executed) attempted += 1;
      if (state.noCredential) noCredential += 1;
      const candidates = state.candidates ?? [];
      if (candidates.length > 0) filled += 1;
      const truth = row.truth ?? '';
      const hit = candidates.some((candidate) =>
        matchTruth(fieldClass, String(candidate.value ?? ''), truth),
      );
      if (hit) correct += 1;
    }
    // Uncredentialed = it filled nothing AND every executed row hit a missing
    // credential. Its 0.0 score is not a fair measurement — flag it so route
    // selection does not discard a route that was never actually run.
    const uncredentialed =
      filled === 0 && noCredential > 0 && noCredential === attempted;
    scores.push({
      route: key,
      tested,
      attempted,
      filled,
      correct,
      precision: filled ? correct / filled : 0,
      recall: tested ? correct / tested : 0,
      no_credential: noCredential,
      uncredentialed,
    });
  }

  // The engine's fused winner — what an exploit run ships. Its accuracy is the
  // number that matters; individual-route rows show where the wins came from.
  let engineFilled = 0;
  let engineCorrect = 0;
  for (const row of graded) {
    const chosen = row.cell?.chosen;
    const value = chosen?.display ?? chosen?.canonical ?? '';
    if (value) engineFilled += 1;
    if (value && matchTruth(fieldClass, String(value), row.truth ?? '')) {
      engineCorrect += 1;
    }
  }
  scores.push({
    route: '[fused-winner]',
    tested,
    attempted: tested,
    filled: engineFilled,
    correct: engineCorrect,
    precision: engineFilled ? engineCorrect / engineFilled : 0,
    recall: tested ? engineCorrect / tested : 0,
    no_credential: 0,
    uncredentialed: false,
  });

  // Rank best-first, but SINK uncredentialed routes below scored ones: a route
  // that never ran (no credential) must not sit among fair 0.0 scores as if it
  // had been measured and lost. It ranks last, flagged for connection.
  return scores.sort(
    (a, b) =>
      Number(a.uncredentialed) - Number(b.uncredentialed) ||
      b.correct - a.correct ||
      b.precision - a.precision ||
      b.filled - a.filled ||
      a.route.localeCompare(b.route),
  );
}
