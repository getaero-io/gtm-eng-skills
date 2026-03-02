Use Apify when you need controlled web automation/scraping workflows.

- Use `apify_list_store_actors` first when you do not know the actor id yet.
- Build `actorId` as `username/name` from store results.
- Use `apify_get_actor_input_schema` to inspect required/optional fields before running.
- `deepline tools get`/`execute` actor fields and `actor-contracts.md` should match because both are generated from typed actor contracts.
- Wrapper-level fields (`actorId`, `input`, `params`, `timeoutMs`) and runtime validation behavior can differ from actor-page docs.
- Prefer `apify_run_actor_sync` as the default execution path when you want results in one call.
- Use `apify_run_actor` only when you need non-blocking execution, then poll run status before fetching outputs.
- Use `actor-contracts.md` for actor-specific required/optional input fields and sample payloads.
- Validate payload shape with a tiny run before scaling row counts.

Schema drift guardrail:
- If `tools get/execute` actor fields differ from `actor-contracts.md`, treat it as a typed-contract bug and fix source data.
- For page-vs-wrapper drift, trust Deepline wrapper validation for execution payload shape.
- If still unclear, run a 1-row/1-item pilot payload and adjust to pass Deepline validation before scaling.

```bash
deepline tools get apify_run_actor_sync --json
```

```bash
deepline tools execute apify_list_store_actors --payload '{"search":"linkedin jobs scraper","sortBy":"relevance","limit":10}' --json
```

```bash
# Convert first result into actorId: username/name
deepline tools execute apify_list_store_actors --payload '{"search":"linkedin jobs scraper","sortBy":"relevance","limit":10}' --json | jq -r '.result.data.actors[0] | "\(.username)/\(.name)"'
```

```bash
# Inspect the actor's input schema page before execution
deepline tools execute apify_get_actor_input_schema --payload '{"actorId":"bebity/linkedin-jobs-scraper"}' --json
```

```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"bebity/linkedin-jobs-scraper","input":{"title":"Web Developer","location":"United States","rows":10},"timeoutMs":300000}' --json
```

```bash
deepline tools execute apify_get_dataset_items --payload '{"datasetId":"{{dataset_id}}","limit":10,"offset":0}' --json
```
