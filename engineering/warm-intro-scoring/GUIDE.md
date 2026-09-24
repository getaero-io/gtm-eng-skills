# Find warm introduction paths

Help a requester choose whom to ask for an introduction. Use the bundled model. Do not create a new score for each run.

## Inputs

Require the requester's warm connections and customer context. Accept CSV or database records. Confirm export ownership and date. Match canonical profile URLs or verified stable IDs, never names alone. Retain missing profiles, ambiguous matches and excluded self-pairs in the reconciliation.

When the requester supplies a source company, retrieve all current employees, obtain full profiles for each and score every employee against every target through [company expansion](references/company-network.md). Merge employees with personal connections by stable identity. Label coworkers as company-network candidates; employment does not prove a LinkedIn connection.

Use supplied target contacts. If absent, follow the [ten-target selection rules](references/pipeline.md). Use verified customers or sourced examples in the same market. Label examples and explain shortfalls. Do not substitute fictional contacts in a real run.

## Run

1. Read the [source contract](references/sources.md). Follow [batch collection](references/batch-collection.md): reuse complete caches, batch HarvestAPI or Apify calls, bound concurrency and fall back only for unresolved records. Report source dates and missing history. An export alone does not contain full profiles or prove connector-to-target access.
2. Run the bundled TypeScript [Play workflow](plays/README.md) in Deepline for collection, feature extraction, scoring, validation and export. Python is the reference and test harness, not the default production scorer. Use the bundled defaults and record the model version. Do not mix event similarity, legacy scores and tuned scores.
3. Preserve source IDs, observation dates and date precision. Code computes overlap. Use the [tuning contract](references/tuning.md) for dated work, school and board evidence. At large employers, same function and location strengthen dated work overlap. Keep sourced direct investor roles distinct from shared portfolio context. Keep community weight low.
4. Use Jev only for true/false facts, feature extraction and entity mapping. Never ask it for scores, weights or relationship-strength labels. Use the [uncertainty Play](plays/README.md) for unresolved claims. Missing evidence stays on hold.
5. Render the private report under the [output rules](references/readable-output.md). Show each target, up to three candidate paths, evidence, points and adjustable weights. Link names and person tags to sourced LinkedIn URLs; mark missing URLs. Keep all candidates in the export; do not silently drop zero scores. Report fewer paths when fewer exist.

## Review gates

Check both relationships: requester-to-connector and connector-to-target. Unknown willingness stays unknown. A decline blocks action, even when its factual score ranks first. Weight changes cannot clear holds. Shared company, investor, city or event attendance does not prove personal access.

Use short sentences, active voice and one term per concept. Scores are evidence points, not success probabilities. Follow the [evaluator](references/evaluator.md) before claiming improved predictions. Structural tests do not measure meeting success.

## Optional stages

- **Live data or updates:** Follow the [database and incremental contract](references/pipeline.md). Verify tenant, reuse compatible tables and pilot collection before a bounded batch. Enable triggers only within the requested scope. Report prepared versus deployed stages.
- **Investor expansion:** Follow [company networks](references/company-network.md) when the requester supplies an employer.
- **Draft asks:** Follow [intro drafts](references/intro-drafts.md). Do not invent prior conversations or failed outreach. Do not send.

## Test and deliver

Run from this folder:

```sh
python3 plays/check_all.py
bun scripts/recipe-demo.ts /private/new-demo-directory
```

The demo uses fictional data and no credentials. See [TESTING.md](TESTING.md) for real inputs. After all requested scoring batches finish, reconcile coverage and validate results. Generate the review with `report.play.ts`, open it and create the private Google spreadsheet specified in the output rules. Include all connections, both top-three views, all scored paths and run details. Validate Sheets readback against the scored export. Link the artifact, spreadsheet and full scored CSV with model version, checks and coverage. For reports over the 1 MB cloud limit, use `bun plays/report-cli.ts input.json output.html`; this uses the same TypeScript renderer. Do not present an older artifact as the result of a new employee run. Keep contact data outside Git and public hosting.
