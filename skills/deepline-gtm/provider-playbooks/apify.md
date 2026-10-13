# Apify — Agent Guidance

## Existing outputs

Use Apify to read results from an existing, authorized run or dataset.

- `apify_get_dataset_items` reads a dataset, with `limit` and `offset` pagination.
- `apify_get_actor_run` and `apify_list_actor_runs` read run status and history.
- `apify_get_log` reads a saved run's log.
- `apify_get_kv_record` reads a stored key-value record.
- `apify_check_credits` reads the account's available credits.
- `apify_stop_actor_run` stops an existing actor run; confirm this mutation with the user.

```bash
deepline tools execute apify_get_dataset_items --payload '{"datasetId":"existing-authorized-dataset","limit":10,"offset":0}'
```

## MCP availability

Actor discovery, schema lookup, and launch are unavailable through MCP pending source-platform authorization review: `apify_list_store_actors`, `apify_get_actor`, `apify_get_actor_input_schema`, `apify_run_actor`, and `apify_run_actor_sync`. Confirmation does not override this restriction. Existing output and run operations above remain available.

## SDK/API actor execution

SDK/CLI/API actor contracts remain available. Establish authorization from the source platform before designing collection; an actor listing or intermediary agreement does not establish that permission. Use only inputs and sources the user is authorized to process. Do not collect private profiles or saved searches through browser-session credentials.

Actor wrapper fields (`actorId`, `input`, `params`, `timeoutMs`) and runtime validation can differ from actor-page docs. Inspect the current operation schema. Actor IDs use `username/name`. Store search quality ranking considers rating, review count, total runs, and 30-day success rate; `rankBy: "relevance"` selects Apify's native sort.

Deepline permits four unresolved actor jobs per organization by default; an explicit execution limit can override this. Capacity refusals are retryable and occur before another billable launch.

An HTTP 200 with an empty dataset is classified as `meta.resultOutcome.classification = "ambiguous_empty"`. It does not prove the input was attempted or that there was no result. Do not automatically retry: the first run remains billable and a retry may create a second charge.
