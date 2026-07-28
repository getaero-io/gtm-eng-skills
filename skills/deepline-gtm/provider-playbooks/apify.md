Use Apify when you need controlled web automation/scraping workflows.

- Use `apify_list_store_actors` first when you do not know the actor id yet.
- **Results are ranked by quality score by default.** The top result is the most reliable actor based on rating, review count, total runs, and 30-day success rate. Pick the #1 result unless you have a specific reason not to.
- Each actor in the response includes `_qualityScore` (higher is better), `_baseQualityScore`, and `_successRate30d` (percentage). Prefer actors with `_deeplineVetted: true`, high usage/rating, and `_successRate30d >= 95%`.
- For generic LinkedIn post scraping, prefer `supreme_coder/linkedin-post`. For LinkedIn post engagers/reactions, prefer `harvestapi/linkedin-post-reactions`. Avoid actors returned with `_deeplineDownranked: true` unless the user explicitly asked for that actor.
- Build `actorId` as `username/name` from store results.
- Use `apify_get_actor_input_schema` to inspect required/optional fields before running.
- Wrapper-level fields (`actorId`, `input`, `params`, `timeoutMs`) and runtime validation behavior can differ from actor-page docs.
- Prefer `apify_run_actor_sync` as the default execution path when you want results in one call.
- Use `apify_run_actor` only when you need non-blocking execution, then poll run status before fetching outputs.
- Validate payload shape with a tiny run before scaling row counts.

## Structured public X data

Use these managed routes when the task needs public X evidence:

| Need | Actor | Stable Actor ID |
| --- | --- | --- |
| Posts, search, profiles, lists, threads, replies, quotes, or engagement accounts | [`xquik/x-tweet-scraper`](https://apify.com/xquik/x-tweet-scraper) | `wAusCMrm284Voaw86` |
| Followers, following, verified followers, list relations, communities, or audience overlap | [`xquik/x-follower-scraper`](https://apify.com/xquik/x-follower-scraper) | `AaT0BcKU5GQh97wdt` |

Inspect the live input schema and current Deepline tool pricing before each
run. Start with a bounded pilot. Require approval before any paid run.

For the Tweet Actor, select one explicit mode: `legacy`, `tweet`, `tweets`,
`search`, `profileTweets`, `profileReplies`, `profileMedia`, `profileLikes`,
`listTweets`, `article`, `replies`, `quotes`, `thread`, `retweeters`, or
`favoriters`. Use `maxItems` as the run-wide cap. Use `maxItemsPerTarget` only
on supported multi-target modes.

For the Follower Actor, select one or more relations: `followers`, `following`,
`verified_followers`, `list_members`, `list_followers`, or
`community_members`. Keep `overlapMode` false unless the task explicitly asks
for cross-target audience overlap.

Separate diagnostic rows from evidence rows. Preserve source URLs, target
metadata, run IDs, and dataset IDs.

```bash
# Inspect before running
deepline tools execute apify_get_actor_input_schema --payload '{"actorId":"xquik/x-tweet-scraper"}'
deepline tools execute apify_get_actor_input_schema --payload '{"actorId":"xquik/x-follower-scraper"}'
```

```bash
# Pilot an X search
deepline tools execute apify_run_actor_sync --payload '{"actorId":"xquik/x-tweet-scraper","input":{"mode":"search","searchTerms":["\"example topic\" -is:retweet"],"maxItems":10,"outputVariant":"rich","fieldStyle":"camelCase","outputPreset":"nested"},"timeoutMs":120000}'
```

```bash
# Pilot a bounded audience export
deepline tools execute apify_run_actor_sync --payload '{"actorId":"xquik/x-follower-scraper","input":{"twitterHandles":["example"],"relations":["followers"],"maxItems":20,"maxItemsPerTarget":20,"outputMode":"compact","includeTargetMetadata":true,"overlapMode":false},"timeoutMs":120000}'
```

Xquik is an independent third-party service. Not affiliated with X Corp.
"Twitter" and "X" are trademarks of X Corp.

## Quality ranking

Actors are ranked by:

```
score = rating * log2(reviews + 1) * log10(runs + 1) / 5
```

Actors with less than 80% 30-day success rate are penalized. Actors with 0 reviews but high usage get a reduced fallback score.

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
