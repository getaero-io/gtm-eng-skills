# Contents and adaptation notes

This example includes all 14 project-owned `.play.ts` files and every TypeScript module they import. The seven transition type copies match the root contract. The two `prebuilt/` dependencies are hosted platform Plays; their source is not owned by this project.

Included supporting material:

- Lifecycle and recruiting SQL; state diagrams; transformation and policy tests.
- Synthetic expert, task, assignment and usage CSVs; three compiled pilot inputs.
- Metric event fixture, calculator, expected illustration and tests.
- Deployment, bounded pilot, live readback, reconciliation and narrowly scoped retry utilities.
- Workflow, field-to-decision examples, research, metric definitions and editable/rendered diagrams.

Public-package changes: campaign/workspace IDs became explicit configuration; deployment scripts check workspace selection; source publication precedes its parent; the pilot records its replay baseline; diagram rebuilding uses local HTML. The business logic of all 14 Plays is preserved.

Excluded: real candidate exports, actual campaign IDs, workspace IDs, private document links, provider responses, customer run logs and one-off scripts that edited private pages. Their reusable behavior and lessons are documented here. Those operational records are not required to run the example and must not be published with it.

Local tests cover deterministic behavior and mocked providers. The package is not a live deployment. Research notes and earlier diagrams preserve design history; the README, setup guide and Play sources define the runnable example.
