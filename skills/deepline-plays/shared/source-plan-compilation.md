# Source-plan compilation

Read this when the task starts as “what sources could solve this?” but the
deliverable is a Play that actually fetches, joins, and exports data.

## Contract

Pre-research owns source breadth. Plays owns execution topology.

Pass these fields forward unchanged:

- objective;
- query type;
- source families;
- extraction keys.
- initial inputs, when the task begins from an existing account, domain, CRM
  object, or another stable identifier.

`plays/shared/source-plan.ts` compiles those fields into stages. It does not
claim a source is available. Search and describe the live catalog for every
source leg, then mark it native, generic route, private connector, or gap.

## Compile before binding tools

```typescript
import { compileSourcePlan } from './shared/source-plan';

const plan = compileSourcePlan({
  objective: 'Build a target-account dataset from public records.',
  queryType: 'gtm_dataset',
  sourceFamilies: ['web', 'reddit', 'x', 'github'],
  extractionKeys: ['domains', 'dataset_or_api_names', 'company_names'],
});
```

A private-only plan has no public discovery stage to mint an identity. Supply
one stable input instead; a broad CRM scan would be both expensive and
unverifiable:

```typescript
const plan = compileSourcePlan({
  objective: 'Join authorized CRM history for known accounts.',
  queryType: 'private_workflow',
  sourceFamilies: ['crm', 'warehouse'],
  extractionKeys: ['crm_object_ids', 'deal_or_opportunity_ids'],
  initialInputs: ['domain_or_account_key'],
});
```

Use the stages to author routes, not as a substitute for them:

| Compiled stage          | Author in the custom Play                                                       |
| ----------------------- | ------------------------------------------------------------------------------- |
| `public-fanout`         | Parallel search/fetch routes with source URLs and source status.                |
| `artifact-resolution`   | Canonical dataset/API URL, schema, parser, and stable join key.                 |
| `identity-resolution`   | Company/person/account identity gates before any private lookup.                |
| `private-join`          | Authorized CRM, warehouse, workflow, or support lookup with private provenance. |
| `supplemental-gap-fill` | Independent route only for still-missing extraction keys.                       |
| `terminal-extraction`   | One output row that preserves every requested key and evidence.                 |

## Gates

- Do not replace a source family with a provider name. Search is a route to a
  source, not the source itself.
- Do not query CRM/warehouse/workflow broadly before identity resolution. It
  increases spend and makes joins impossible to audit.
- Do not let a chosen route drop extraction keys. Preserve nulls and an
  explicit miss/source status when evidence is absent.
- Do not call an unknown source “native.” Confirm tool schema and pricing from
  the live catalog, or label it generic/private/gap.

## Offline regression

Use the last30days parity corpus to verify source plans compile into fetch
topologies without losing source coverage, keys, or required stages:

```bash
bun .skills/deepline-plays/scripts/evaluate-source-plan-corpus.ts \
  --corpus .skills/deepline-pre-research/evals/last30days-public-private-corpus.json \
  --pre-research-planner .skills/deepline-pre-research/scripts/query_design.py
```

This checks planning only. Run a separate internal/provider test for real tool
availability, schema adapters, coverage, and credit economics.
