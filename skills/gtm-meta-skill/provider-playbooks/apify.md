Use Apify when you need controlled web automation/scraping workflows.

- Use `apify_list_store_actors` first when you do not know the actor id yet.
- Build `actorId` as `username/name` from store results.
- Use `apify_get_actor_input_schema` to inspect required/optional fields before running.
- Wrapper-level fields (`actorId`, `input`, `params`, `timeoutMs`) and runtime validation behavior can differ from actor-page docs.
- Prefer `apify_run_actor_sync` as the default execution path when you want results in one call.
- Use `apify_run_actor` only when you need non-blocking execution, then poll run status before fetching outputs.
- Validate payload shape with a tiny run before scaling row counts.

```bash
deepline tools get apify_run_actor_sync
```

```bash
deepline tools execute apify_list_store_actors --payload '{"search":"linkedin jobs scraper","sortBy":"relevance","limit":10}'
```

```bash
deepline tools execute apify_list_store_actors --payload '{"search":"linkedin jobs scraper","sortBy":"relevance","limit":10}' 
```

```bash
# Inspect the actor's input schema page before execution
deepline tools execute apify_get_actor_input_schema --payload '{"actorId":"bebity/linkedin-jobs-scraper"}'
```

```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"bebity/linkedin-jobs-scraper","input":{"title":"Web Developer","location":"United States","rows":10},"timeoutMs":300000}'
```

```bash
deepline tools execute apify_get_dataset_items --payload '{"datasetId":"EU1bcB5F9gY3J1Zq2","limit":10,"offset":0}'
```
