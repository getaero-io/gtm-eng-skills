# Run logs and events

<!-- Generated from CLI help, the runtime event catalog and packages/sdk/src/client.ts JSDoc. Do not edit manually. -->

Read existing run logs, find failures and filter events. These commands do not execute tools.

## Read logs or search events

A run ID alone reads text logs. Use the returned nextCursor with --cursor for older lines. Omit the run ID or add a search flag to search events; a supplied run ID narrows the search. --out, --failed and --log-level cannot be combined with event search.

Search defaults to the last hour, newest first; maximum lookback is seven days. Follow the returned next.logs command for the next page. --payloads adds available event details or saved work results, not dataset rows.

```bash
deepline runs logs '<run-id>'
deepline runs logs '<run-id>' --out run.log
deepline runs logs --kind run.failed --json
deepline runs logs --play my-play --since 2026-10-06T00:00:00Z --until 2026-10-06T01:00:00Z --json
```

Text logs default to 200 lines. Event search defaults to 100 events (maximum 200); with `--payloads`, the limit is 10 events and 16 MiB. Check returned retention warnings; `--out` saves all available log lines.

## Known event kinds

<!-- prettier-ignore -->
| `--kind` | Meaning |
| --- | --- |
| `run.created` | Run accepted. |
| `run.started` | Execution started. |
| `run.waiting` | Run waiting. |
| `run.resumed` | Execution resumed. |
| `run.completed` | Run succeeded. |
| `run.failed` | Run failed. |
| `run.cancelled` | Run cancelled. |
| `step.started` | Step started. |
| `step.progress` | Progress update. |
| `step.completed` | Step succeeded. |
| `step.failed` | Step failed. |
| `step.skipped` | Step skipped. |
| `log.appended` | Text log line. |
| `dataset.lifecycle` | Dataset registered, available or failed. |
| `activity.observed` | Provider or workflow activity. |
| `work.counters` | Call, request and rate-limit totals. |
| `receipt.completed` | Saved work result: succeeded. |
| `receipt.failed` | Saved work result: failed. |
| `receipt.skipped` | Saved work result: skipped. |
| `runtime.event` | Other event. |

## Filter with --where

String fields: orgId, runId, playName, runtimeScope, kind, status, source, stepId, stepKind, datasetId, phase, provider, operation. producerAttempt is a positive integer; context.&lt;key&gt; accepts flat string, number or boolean log fields.

Use $.field == value joined with &&, at most eight predicates and 512 bytes. Wrap the filter in single shell quotes; strings use double quotes, numbers and booleans are unquoted. Missing fields do not match. No OR, ranges, wildcards or text/payload search.

Use --kind for run/step outcomes; status is not inferred from kind. provider/operation match activity.observed where recorded, not every provider call. Replace example values with values from your events.

The context examples use `ctx.log("Lookup finished", { context: { companyId: "acme_123", attempt: 2, cached: false } })`.

```bash
# Failed work with saved details
deepline runs logs --kind receipt.failed --where '$.status == "failed"' --payloads --json
# One failed step
deepline runs logs --kind step.failed --where '$.stepId == "company-lookup"' --payloads --json
# Provider and operation
deepline runs logs --kind activity.observed --where '$.provider == "apollo" && $.operation == "company_lookup"' --json
# Failed dataset
deepline runs logs --kind dataset.lifecycle --where '$.datasetId == "companies" && $.phase == "failed"' --payloads --json
# String log context
deepline runs logs --kind log.appended --where '$.context.companyId == "acme_123"' --json
# Number and boolean log context
deepline runs logs --kind log.appended --where '$.context.attempt == 2 && $.context.cached == false' --json
# One run and step
deepline runs logs '<run-id>' --where '$.stepId == "company-lookup"' --json
```

## Retrieve results

`--payloads` adds `eventPayload` for event details or `payload` for saved work results. Details can be unavailable. For dataset rows use `runs export`; for one saved tool response use `runs receipt` with the key from your exported evidence. Inspect `runs get <run-id> --json` for available outputs.

## SDK and HTTP field contract

`client.runs.searchEvents(options)` calls `GET /api/v2/runs/events` and returns `RunsEventSearchResult`. Options map to query parameters except `includePayloads` → `payloads=true`; Preview `runtime` uses runtime credentials. Raw HTTP defaults `since` to one hour before `until`.

<!-- prettier-ignore -->
| Type | Field | Value type | Required | Contract |
| --- | --- | --- | --- | --- |
| `RunsEventSearchOptions` | `since` | `string` | No | Inclusive UTC timestamp; defaults to one hour before the request. |
| `RunsEventSearchOptions` | `until` | `string` | No | Exclusive UTC timestamp; defaults to the request time. A window spans at most seven days; event retention is seven days. |
| `RunsEventSearchOptions` | `runId` | `string` | No | Optional run filter. Omit to search across the active organization. |
| `RunsEventSearchOptions` | `playName` | `string` | No | Exact Play name; HTTP query parameter `playName`, CLI `--play`. |
| `RunsEventSearchOptions` | `kind` | `string` | No | Exact dotted event kind, such as `step.failed`. The catalog is discoverable with `runs logs --help`; future stored kinds are accepted too. |
| `RunsEventSearchOptions` | `jsonpath` | `string` | No | JSONPath equality joined with `&&`, at most eight predicates and 512 bytes. See `runs logs --help` for fields and examples. Missing fields do not match; status is not inferred from kind. HTTP `jsonpath`, CLI `--where`. |
| `RunsEventSearchOptions` | `includePayloads` | `boolean` | No | Include available `eventPayload` details and receipt `payload` results; maximum ten events and 16 MiB. HTTP `payloads=true`, CLI `--payloads`. |
| `RunsEventSearchOptions` | `limit` | `number` | No | Page size: default 100, maximum 200; with payloads, default and maximum ten. |
| `RunsEventSearchOptions` | `cursor` | `string` | No | Opaque `nextCursor` from the preceding page. Reuse that page's returned since/until and the same filters and runtime scope. |
| `RunsEventSearchOptions` | `runtime` | `PlayRuntimeSelection` | No | Explicit Preview selection requires the existing runtime credential. |
| `RunsEventSearchEntry` | `eventId` | `string` | Yes | Stable event identity; also breaks ties in newest-first pagination. |
| `RunsEventSearchEntry` | `occurredAt` | `string` | Yes | Producer occurrence time as a UTC timestamp string. |
| `RunsEventSearchEntry` | `ingestedAt` | `string` | Yes | Index ingestion time as a UTC timestamp string; may be later than occurrence. |
| `RunsEventSearchEntry` | `runId` | `string` | Yes | Public run identity associated with this observation. |
| `RunsEventSearchEntry` | `playName` | `string` | Yes | Recorded Play name. |
| `RunsEventSearchEntry` | `kind` | `string` | Yes | Exact dotted event kind, such as `step.failed`. |
| `RunsEventSearchEntry` | `level` | `string \| null` | Yes | Recorded log severity, or null; not a JSONPath filter field. |
| `RunsEventSearchEntry` | `message` | `string \| null` | Yes | Log message preview of at most 2,048 characters, or null. Use text logs/export for the full retained line. |
| `RunsEventSearchEntry` | `searchDoc` | `Record<string, unknown>` | Yes | Recorded filter fields. SDK/API keep this nested; the CLI places these fields directly on each event. |
| `RunsEventSearchEntry` | `eventPayload` | `Record<string, unknown>` | No | Available event details when requested with `includePayloads`; dataset events contain metadata, not dataset rows. |
| `RunsEventSearchEntry` | `payload` | `RunsEventPayload \| null` | No | Retained work result for a receipt match when payloads are requested; null if unavailable. Other events need not carry this field. |
| `RunsEventSearchResult` | `events` | `RunsEventSearchEntry[]` | Yes | Matching observations in descending occurredAt/eventId order. |
| `RunsEventSearchResult` | `nextCursor` | `string \| null` | Yes | Opaque continuation token, or null when no further page exists. |
| `RunsEventSearchResult` | `since` | `string` | Yes | Resolved inclusive UTC bound, including a defaulted bound. |
| `RunsEventSearchResult` | `until` | `string` | Yes | Resolved exclusive UTC bound, including a defaulted bound. |
| `RunsEventPayload` | `status` | `'completed' \| 'failed' \| 'skipped'` | Yes | Recorded terminal work outcome. |
| `RunsEventPayload` | `output` | `unknown \| null` | Yes | Stored result data, or null when no output was retained. |
| `RunsEventPayload` | `error` | `string \| null` | Yes | Stored failure message, or null when absent. |
| `RunsEventPayload` | `errorPayload` | `unknown \| null` | Yes | Stored structured failure details, or null when absent. |
