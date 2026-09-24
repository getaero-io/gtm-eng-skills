/* eslint-disable @typescript-eslint/no-explicit-any -- Ported JSON contract/parity boundary; runtime validators reject malformed values. */
/** Credential-free installed-package smoke test. Only fictional bundled inputs. */
import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { buildFeatures } from '../plays/features';
import { validatePayload, MODEL } from '../plays/core';
import { renderReview } from '../plays/report';

const output = process.argv[2];
if (!output || process.argv.length !== 3) {
  throw new Error(
    'Usage: bun scripts/recipe-demo.ts /private/new-output-directory',
  );
}
const source = JSON.parse(
  readFileSync(new URL('../tests/e2e-fixture.json', import.meta.url), 'utf8'),
);
const features = buildFeatures(source);
// Explicit fictional prior decline. Numeric ranking cannot clear this hold.
features.paths.find((p) => p.connector_id === 'investor').review_status =
  'blocked_declined';
const result = validatePayload(features);
assert.deepEqual(
  Object.fromEntries(
    result.paths.map((p: any) => [p.connector_id, p.tuned_score]),
  ),
  {
    investor: 120,
    coworker: 80,
    company: 20,
    sparse: 0,
  },
);
const tuned = validatePayload(features, { work_overlap: 160 });
assert.deepEqual(
  tuned.paths.map((p: any) => p.tuned_score),
  [160, 120, 40, 0],
);
assert.equal(
  tuned.paths.find((p: any) => p.connector_id === 'investor').review_status,
  'blocked_declined',
);
const html = renderReview(result);
const cell = (v: unknown) => `"${String(v).replaceAll('"', '""')}"`;
const csv =
  [
    'path_id,target_id,connector_id,score,review_status',
    ...result.paths.map((p: any) =>
      [p.id, p.target_id, p.connector_id, p.tuned_score, p.review_status]
        .map(cell)
        .join(','),
    ),
  ].join('\n') + '\n';
// All computation and assertions complete before creating the output folder.
mkdirSync(output, { mode: 0o700 });
const save = (name: string, value: string) =>
  writeFileSync(resolve(output, name), value, { flag: 'wx', mode: 0o600 });
save('review.html', html);
save('scores.csv', csv);
save('features.json', JSON.stringify(result, null, 2));
const receipt = {
  status: 'pass',
  model: MODEL,
  fixture: 'fictional',
  targets: 1,
  paths: 4,
  expected_scores: [120, 80, 20, 0],
  tuned_scores: [160, 120, 40, 0],
  decline_preserved: true,
  provider_calls: 0,
  database_writes: 0,
  messages_sent: 0,
  output: resolve(output),
};
save('receipt.json', JSON.stringify(receipt, null, 2));
console.log(JSON.stringify(receipt));
