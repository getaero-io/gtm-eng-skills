// Replays a trained bundle through the TypeScript scorer and checks it against the Python CLI.
// Usage: tsx scripts/tests/contract_check.ts <out_dir>
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { scoreRow } from '../scoring_contract';
import type { Model, Reference, Observation } from '../scoring_contract';

const dir = process.argv[2];
if (!dir) throw new Error('usage: contract_check.ts <out_dir>');
const raw = JSON.parse(readFileSync(join(dir, 'model_contract.json'), 'utf8'));
const model: Model = {
  id: raw.id,
  dimension: raw.dimension,
  intercept: raw.intercept,
  weights: raw.weights,
  max_age_days: raw.max_age_days,
  validation: raw.validation,
};
const reference: Reference = JSON.parse(readFileSync(join(dir, 'reference.json'), 'utf8'));
const sample = JSON.parse(readFileSync(join(dir, 'contract_sample.json'), 'utf8'));
let failures = 0;
for (const row of sample.rows as Array<{ entity_id: string; observations: Observation[]; expected: { logit: number; percentile: number | null; grade: string | null } }>) {
  const r = scoreRow(row.entity_id, sample.scored_at, row.observations, model, reference);
  const okLogit = r.score !== null && Math.abs(r.score - row.expected.logit) < 1e-9;
  const okPct =
    (r.percentile === null && row.expected.percentile === null) ||
    (r.percentile !== null && row.expected.percentile !== null && Math.abs(r.percentile - row.expected.percentile) < 1e-9);
  const okGrade = r.grade === row.expected.grade;
  if (!(okLogit && okPct && okGrade)) {
    failures++;
    console.log('MISMATCH', row.entity_id, { got: { score: r.score, percentile: r.percentile, grade: r.grade, status: r.status, miss: r.miss_reason }, expected: row.expected });
  }
}
console.log(failures ? `contract check FAILED (${failures})` : `contract check passed (${sample.rows.length} rows)`);
process.exit(failures ? 1 : 0);
