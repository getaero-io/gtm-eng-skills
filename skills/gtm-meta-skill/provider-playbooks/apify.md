Use Apify when you need controlled web automation/scraping workflows.

- Use `apify_list_store_actors` first when you do not know the actor id yet.
- **Results are ranked by quality score by default.** The top result is the most reliable actor based on rating, review count, total runs, and 30-day success rate. Pick the #1 result unless you have a specific reason not to.
- Each actor in the response includes `_qualityScore` (higher is better) and `_successRate30d` (percentage). Prefer actors with `_successRate30d >= 95%`.
- Build `actorId` as `username/name` from store results.
- Use `apify_get_actor_input_schema` to inspect required/optional fields before running.
- Wrapper-level fields (`actorId`, `input`, `params`, `timeoutMs`) and runtime validation behavior can differ from actor-page docs.
- Prefer `apify_run_actor_sync` as the default execution path when you want results in one call.
- Use `apify_run_actor` only when you need non-blocking execution, then poll run status before fetching outputs.
- Validate payload shape with a tiny run before scaling row counts.

## Quality ranking

Actors are ranked by:

```
score = rating * log2(reviews + 1) * log10(runs + 1) / 5
```

Actors with <80% 30-day success rate are penalized. Actors with 0 reviews but high usage get a reduced fallback score.

To bypass quality ranking and use Apify's native sort, pass `rankBy: "relevance"`.

## Examples

```bash
# Search for actors, ranked by quality (default)
deepline tools execute apify_list_store_actors --payload '{"search":"google play reviews","limit":5}'
```

```bash
# Search with Apify's native relevance sort
deepline tools execute apify_list_store_actors --payload '{"search":"google play reviews","sortBy":"relevance","rankBy":"relevance","limit":5}'
```

```bash
# Inspect the actor's input schema page before execution
deepline tools execute apify_get_actor_input_schema --payload '{"actorId":"neatrat/google-play-store-reviews-scraper"}'
```

```bash
# Run an actor synchronously
deepline tools execute apify_run_actor_sync --payload '{"actorId":"neatrat/google-play-store-reviews-scraper","input":{"appIdOrUrl":"com.airbnb.android","sortBy":"newest","maxReviews":10},"timeoutMs":120000}'
```

```bash
deepline tools execute apify_get_dataset_items --payload '{"datasetId":"EU1bcB5F9gY3J1Zq2","limit":10,"offset":0}'
```
