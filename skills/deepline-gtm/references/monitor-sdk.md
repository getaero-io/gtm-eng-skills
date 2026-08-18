# Monitor SDK example

Use the SDK when monitor lifecycle belongs in a script, agent loop, or play
repository. The CLI and SDK are two surfaces over the same product model.
`defineMonitor` gives the authoring shape type checking; it does not remove the
access gate, approval, dry-run, or durable read-back requirements.

```ts
import { DeeplineClient, defineMonitor } from 'deepline';

const client = new DeeplineClient();

const access = await client.monitors.status();
if (!access.has_access) throw new Error(access.reason ?? 'No monitor access');

// Read the live job-opening variant before authoring a definition.
await client.getTool('deepline_native.company_job_openings');

function storedPayload(
  detail: Record<string, unknown>,
): Record<string, unknown> {
  const definition = detail.definition;
  if (!definition || typeof definition !== 'object') {
    throw new Error('Monitor read-back did not include a definition.');
  }
  const payload = (definition as { payload?: unknown }).payload;
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('Monitor read-back did not include a payload.');
  }
  return payload as Record<string, unknown>;
}

const monitor = defineMonitor({
  key: 'company-job-openings',
  tool: 'deepline_native.company_radar',
  name: 'Company job openings',
  payload: {
    domain: 'stripe.com',
    radar_type: 'company_job_openings',
    job_titles: '"Chief Financial Officer"',
  },
});

// Safe preflight.
await client.monitors.check(monitor);
await client.monitors.deploy(monitor, { dryRun: true });

// Obtain approval before this write, then prove the stored filter.
await client.monitors.deploy(monitor);
const stored = await client.monitors.get('company-job-openings');
if (storedPayload(stored).job_titles !== '"Chief Financial Officer"') {
  throw new Error(
    'Monitor deploy did not persist the requested job-title filter.',
  );
}

// The lifecycle verbs mirror the CLI. Read before changing or deleting.
await client.monitors.update('company-job-openings', {
  payload: { job_titles: '"Chief Financial Officer" OR "VP Finance"' },
});
const updated = await client.monitors.get('company-job-openings');
if (
  storedPayload(updated).job_titles !==
  '"Chief Financial Officer" OR "VP Finance"'
) {
  throw new Error(
    'Monitor update did not persist the requested job-title filter.',
  );
}
await client.monitors.delete('company-job-openings', { dryRun: true });
```

Read-only calls (`getTool`, `status`, `available`, `check`, `list`, `get`,
`dependents`, and a `{ dryRun: true }` mutation preview) are safe before
approval. `deploy`, `update`, `reactivate`, and `delete` change workspace or
provider state and can spend Deepline credits. Use the CLI recipe's approval
summary and verify the stored definition after every approved mutation.
