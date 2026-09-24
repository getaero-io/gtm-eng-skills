# Collect full profiles fast

Use this contract for personal connections, targets and source-company employees. Always use a supported batch endpoint or multi-URL actor when available for HarvestAPI or Apify collection. Use single-profile calls only under the explicit exception below. Do not launch one actor per contact when the actor accepts URL arrays. A singleton final batch is valid.

## Plan once

1. Deduplicate canonical profile URLs across all populations. Keep each contact ID and membership source. Reject ambiguous identities; never join by name or response position.
2. Set a freshness window for this run. Reuse complete profiles within that window. Refresh only stale, missing or incomplete profiles. A headline or employee-search row is not a full profile. Preserve original observation dates.
3. Inspect the active tool schema, actor schema and result contract. Record batch size, concurrency limit, pagination, required history fields and spend limit. Never invent a bulk endpoint or assume a CSV wrapper makes the upstream calls bulk.

## Execute in batches

- Prefer the native HarvestAPI batch operation when the active schema exposes one. The current native `harvestapi_get_profile` tool is single-profile. Do not send an array to its `url` field. If native batch is unavailable, use a verified multi-URL Apify actor for full profiles. Inspect its current schema and supported limits before use.
- Start with one small batch. Check stable identities, full employment and education, date fields and result pagination. Then use the largest validated batch within provider, response-size and budget limits. Do not repeat the pilot per contact.
- Use four concurrent batches initially, capped by the provider's lower limit. Increase only when measured latency and throttling permit. Share the limit across this run's stages. Honor `Retry-After`; use bounded backoff for transient failures. Do not add a delay after each successful contact or create unbounded `Promise.all` calls.
- If no suitable batch provider is available, record that limitation and use native single-profile calls with the same bounded concurrency. This is the explicit exception, not a claimed batch endpoint. Do not choose serial collection for a whole roster unless the provider permits only one concurrent request.
- Fetch posts only when the run needs public-interaction evidence. Batch that stage separately. The locally registered `harvestapi/linkedin-profile-posts` actor accepts at most six `targetUrls`; verify the active schema before use. Never infer profile batch limits from post limits. Missing posts do not discard a valid profile.
- Save the batch input hash, provider, tool/actor version, requested IDs, run/dataset ID, status and source dates. Retrieve every result page before declaring missing records. Reuse the same run receipt after a timeout or restart. An `awaiting_apify` response or uncertain timeout is pending, not failure; recover that job before launching a replacement or fallback.

## Recover only unresolved records

Match outputs by canonical URL or verified stable ID. Quarantine duplicate matches, unexpected identities and malformed histories. Keep successful records. Build the next batch from missing, invalid or incomplete records only after the original job has a known terminal outcome.

Use an available alternative provider that returns the required full histories, such as Crustdata or another verified profile actor. Inspect its schema and coverage first; an email-only provider is not a full-profile fallback. Use that provider's batch form when supported. Try one alternate provider per unresolved record by default, within the approved budget. Report remaining gaps instead of looping through paid providers. Authentication and quota failures need provider-level handling; do not retry them once per contact.

Normalize each provider's response to the same snapshot contract. Preserve provenance, date precision and original receipts. Do not overwrite valid history with an empty fallback field or merge contradictory histories silently. Keep unresolved conflicts on review hold. Jev can map entities or extract facts; code still calculates all scores.

## Use the bundled collector correctly

`collect.play.ts` cached mode validates and normalizes retained receipts. Its legacy live mode launches one profile actor and one posts actor per contact; it is not a bulk runner. Do not use legacy live mode for a bulk run. Stage the selected provider's batch results as per-contact `profile_json`, `profile_observed_at` and optional `posts_json`, then run cached mode. Use a provider-specific adapter when its full-profile shape differs from the collector's accepted shape. Do not claim this documentation adds an automatic provider waterfall to that Play.

Before delivery, reconcile unique requested profiles = accepted profiles + unresolved profiles. Report cache hits, refreshed profiles, partial/failed/pending records, batch count, fallback count, elapsed time and Deepline spend. Score accepted snapshots as they become ready, but label the artifact partial until all requested coverage is accounted for. Speed must not remove employees, targets or low-score paths.
