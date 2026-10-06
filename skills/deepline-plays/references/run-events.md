# Run logs and events

<!-- Generated from CLI help, the runtime event catalog and packages/sdk/src/client.ts JSDoc. Do not edit manually. -->

Run `deepline runs logs --help` to discover this contract in the installed CLI.

## Choose the read

These commands read existing evidence; they do not start a run or execute a provider. Replace &lt;run-id&gt;, &lt;play-name&gt; and other angle-bracket values with identifiers returned by the CLI.

Text logs: runs logs &lt;run-id&gt; returns the last 200 retained lines by default. When older lines exist, hasMore is true and nextCursor continues the next older page with --cursor. --out writes the full retained stream to a local file. --log-level filters text severity; debug includes all retained levels. --failed reads only a terminal-failed run’s last 20 retained lines and reports retention limitations.

Event search: omit the run ID, or add any of --since, --until, --play, --kind, --where, --payloads, --runtime-namespace or --runtime-backend. A supplied run ID then narrows the search. --cursor continues event search unless it is a returned before:&lt;sequence&gt; text-log cursor. --limit and --json alone do not switch a run’s text logs to event search. Text-only flags --out, --failed and --log-level cannot be combined with event search.

Current status and returned output selectors: runs get &lt;run-id&gt; --json. Live observation: runs watch &lt;run-id&gt;. Dataset rows: runs export &lt;run-id&gt; --dataset &lt;returned-selector&gt; --out rows.csv. A referenced tool response: runs receipt &lt;run-id&gt; --key &lt;returned-receipt-key&gt; --json. Read each command’s --help for its options.

```bash
deepline runs logs <run-id> --cursor before:1201 --json
deepline runs logs <run-id> --out run.log --json
deepline runs logs --kind run.failed --json
deepline runs logs --kind step.failed --payloads --json
deepline runs logs --kind receipt.failed --payloads --json
```

## Known event kinds

<!-- prettier-ignore -->
| `--kind` | Meaning | Recorded by | Possible payload fields |
| --- | --- | --- | --- |
| `run.created` | The run was admitted and received its run ID. | Run admission | `status`, `playName`, `runtimeBackend` |
| `run.started` | The run began execution. | Execution coordinator | `playName`, `runtimeBackend` |
| `run.waiting` | The run entered a durable wait. | Durable wait handling | `waitKind`, `waitUntil` |
| `run.resumed` | The run resumed after a durable wait. | Durable wait handling | Event envelope only |
| `run.completed` | The run completed successfully. | Run finalization | `result`, `resultSummary`, `terminalWorkCounterSegment` |
| `run.failed` | The run ended with a failure. | Run finalization | `error`, `result`, `resultSummary`, `terminalWorkCounterSegment` |
| `run.cancelled` | The run was cancelled. | Run cancellation | `error`, `result` |
| `step.started` | A named step began execution. | Managed step execution | `stepId`, `label`, `kind`, `artifactTableNamespace` |
| `step.progress` | A named step reported progress. | Managed step execution | `stepId`, `label`, `kind`, `status`, `progress` |
| `step.completed` | A named step completed. | Managed step execution | `stepId`, `label`, `kind`, `artifactTableNamespace` |
| `step.failed` | A named step failed. | Managed step execution | `stepId`, `label`, `kind`, `error`, `artifactTableNamespace` |
| `step.skipped` | A named step was skipped. | Managed step execution | `stepId`, `label`, `kind`, `artifactTableNamespace` |
| `log.appended` | A text log line was appended to the unified run history and log view. | ctx.log and runtime/coordinator messages | `lines`, `lineContexts`, `producerAttempt`, `channelOffset`, `logsTruncated` |
| `dataset.lifecycle` | A run dataset was registered, made available, or failed. | Managed dataset storage | `datasetId`, `path`, `tableNamespace`, `phase`, `persistedRows`, `succeededRows`, `failedRows`, `complete`, `bornFrom` |
| `activity.observed` | The runtime recorded an activity observation. | Managed provider/dataset/runner activity | `observation` |
| `work.counters` | A work segment reported logical call, provider request, and rate-limit counters. | Runtime work accounting | `attempt`, `invocationSeq`, `segmentId`, `logicalCalls`, `providerRequests`, `provider429s`, `final` |
| `receipt.completed` | A durable work receipt completed. | Durable work receipt settlement | `status`, `output`, `error`, `errorPayload` |
| `receipt.failed` | A durable work receipt failed. | Durable work receipt settlement | `status`, `output`, `error`, `errorPayload` |
| `receipt.skipped` | A durable work receipt was skipped. | Durable work receipt settlement | `status`, `output`, `error`, `errorPayload` |
| `runtime.event` | Fallback for an observation without a recognized event type. | Event indexing | Producer-specific fields; inspect the returned payload |

## Search window and pagination

Search defaults to the last hour, newest first. Use explicit ISO UTC --since and --until values for reproducible queries; the maximum lookback is seven days. Default page size is 100 events; --limit accepts 1–200. With --payloads, default and maximum are 10 events, with 16 MiB total payload data.

JSON returns events[], returnedCount, since, until, nextCursor and next.logs. Run the returned next.logs command to continue with the same filters and UTC window; nextCursor is opaque. A bounded page or an empty result does not establish whole-run coverage or application health.

```bash
deepline runs logs <run-id> --kind log.appended --json
deepline runs logs --play <play-name> --since <UTC-start> --until <UTC-end> --json
```

## Fields you can filter with --where

Identity strings: orgId, runId, playName, runtimeScope. These come from authenticated execution state; filters only narrow your authorized organization/runtime. Preview reads require the existing runtime credential and an authorized --runtime-namespace; --runtime-backend selects daytona or modal.

Event string: kind. Optional strings: source, stepId, stepKind, status, datasetId, phase, provider, operation. Optional positive integer: producerAttempt. These fields exist only when recorded; inspect a returned event before filtering on an optional field.

stepId/stepKind describe recorded step work; datasetId/phase describe dataset lifecycle (registered, available, failed). provider/operation appear on typed provider activity.observed events, not every receipt or provider call. status is the recorded status or activity state when present: run.completed and step.completed do not imply status == "completed". Select lifecycle outcomes with --kind.

context.&lt;key&gt; matches an authored flat scalar log field: string, number or boolean. Context cannot override event identity. Missing fields do not match. --where supports only $.field == literal predicates joined with &&, at most eight predicates and 512 bytes. No OR, ranges, wildcards, nested payload paths or text search. Time uses --since/--until; level and message are not --where fields.

Wrap the entire predicate in single shell quotes so $ and && reach the CLI unchanged. Inside it, strings use double quotes; numbers and booleans are unquoted. Types must match: 2 differs from "2", false differs from "false". Examples use illustrative recorded values; use your own step IDs, dataset IDs, provider/operation names and authored context. The context examples assume ctx.log recorded companyId: "acme_123", attempt: 2 and cached: false.

```bash
# Failed retained work with its stored error/result
deepline runs logs --kind receipt.failed --where '$.status == "failed"' --payloads --json
# Failure details for one named step
deepline runs logs --kind step.failed --where '$.stepId == "company-lookup"' --payloads --json
# Typed provider observations matching both fields
deepline runs logs --kind activity.observed --where '$.provider == "apollo" && $.operation == "company_lookup"' --json
# Failed lifecycle transitions for one dataset
deepline runs logs --kind dataset.lifecycle --where '$.datasetId == "companies" && $.phase == "failed"' --payloads --json
# Authored string context on log lines
deepline runs logs --kind log.appended --where '$.context.companyId == "acme_123"' --json
# Authored number and boolean context, both required to match
deepline runs logs --kind log.appended --where '$.context.attempt == 2 && $.context.cached == false' --json
# Known producer identity within one run
deepline runs logs <run-id> --where '$.source == "worker" && $.producerAttempt == 1' --json
```

## What you get back

Search events include eventId, occurredAt, ingestedAt, kind, runId, playName, level and message. The CLI puts indexed fields directly on each events[] entry; SDK/API responses keep them under searchDoc. Log search message is a preview (up to 2,048 characters); use text logs or --out for full retained lines.

--payloads adds eventPayload for stored canonical events: lifecycle, step details/errors, activity observations, dataset transitions and work counters. Receipt matches instead hydrate payload with status, output, error and errorPayload. An event without a receipt does not promise a tool response; retained payloads may be unavailable. Neither --where nor event search indexes request/response bodies.

Search does not expose a receipt key or storage reference. To retrieve a specific retained tool response with runs receipt, use the receipt key returned in the run’s exported evidence or tool execution metadata. For full row data, follow runs get output/export actions; dataset.lifecycle contains metadata, not all dataset rows.

The catalog lists known searchable kinds, including receipt outcomes and the runtime.event fallback. Use the exact dotted name with --kind. Future stored kinds can also be queried; this list is not a CLI validation allowlist. Events are observations, not a count of billed provider calls.

Catalog payload fields are possible producer fields, not required fields or --where paths. Canonical eventPayload uses type for the dotted event kind; its kind field, when present on a step, becomes indexed stepKind. Indexed log entries describe individual lines rather than reproducing the original lines batch.

Canonical event envelopes carry runId, type, occurredAt (producer milliseconds), source, optional seq and optional producer-owned payload. Search occurredAt/ingestedAt are UTC timestamp strings. source identifies the recorded producer; producerAttempt is present only when known.

activity.observed stores observation with activityId, stepId, target, state and observedAt. Targets describe provider, dataset, lease, runner, step or capacity work. State kinds are active, queued, waiting, retrying, scheduled, completed or failed; retry/wait detail stays in the payload. work.counters contains aggregate logicalCalls, providerRequests and provider429s, not per-call responses.

## Storage and retention

Event/log/receipt search shares the PlanetScale index. New runs marked runEventStore=planet_scale retain accepted event/log history in PlanetScale; Convex keeps current run/control state and eligible saved-Play rollup facts. Older unmarked runs retain their existing readers. No backfill is implied.

Search retention is seven days; receipt payload retention is independent. Logs reflect accepted, retained lines: runtime sampling and truncation can omit original console output. Read returned retention/sampling warnings; an export contains the full retained stream, not suppressed lines.

## SDK and HTTP field contract

`client.runs.searchEvents(options)` reads `GET /api/v2/runs/events`. Options map directly to HTTP query parameters except `includePayloads` → `payloads=true`; Preview `runtime` uses the existing runtime credential headers. The SDK resolves default time bounds relative to request time; raw HTTP defaults an omitted `since` to one hour before `until`. The response is `RunsEventSearchResult`. Types and descriptions below are generated from the SDK source JSDoc.

<!-- prettier-ignore -->
| Type | Field | Value type | Required | Contract |
| --- | --- | --- | --- | --- |
| `RunsEventSearchOptions` | `since` | `string` | No | Inclusive UTC timestamp; defaults to one hour before the request. |
| `RunsEventSearchOptions` | `until` | `string` | No | Exclusive UTC timestamp; defaults to the request time. A window spans at most seven days; event retention is seven days. |
| `RunsEventSearchOptions` | `runId` | `string` | No | Optional run filter. Omit to search across the active organization. |
| `RunsEventSearchOptions` | `playName` | `string` | No | Exact Play name; HTTP query parameter `playName`, CLI `--play`. |
| `RunsEventSearchOptions` | `kind` | `string` | No | Exact dotted event kind, such as `step.failed`. The catalog is discoverable with `runs logs --help`; future stored kinds are accepted too. |
| `RunsEventSearchOptions` | `jsonpath` | `string` | No | Equality joined with `&&`, at most eight predicates and 512 bytes. Fields: orgId, runId, playName, runtimeScope, producerAttempt, kind, status, source, stepId, stepKind, datasetId, phase, provider, operation and scalar `context.<key>`. Missing fields do not match; status is not inferred from kind. No body, message, level, nested payload, range or OR search. HTTP `jsonpath`, CLI `--where`. |
| `RunsEventSearchOptions` | `includePayloads` | `boolean` | No | Add stored canonical `eventPayload` and, for receipt matches, retained `payload`. At most ten events and 16 MiB; unavailable receipts return null. HTTP `payloads=true`, CLI `--payloads`. Does not execute tools. |
| `RunsEventSearchOptions` | `limit` | `number` | No | Page size: default 100, maximum 200; with payloads, default and maximum ten. |
| `RunsEventSearchOptions` | `cursor` | `string` | No | Opaque `nextCursor` from the preceding page. Reuse that page's returned since/until and the same filters and runtime scope. |
| `RunsEventSearchOptions` | `runtime` | `PlayRuntimeSelection` | No | Explicit Preview selection requires the existing runtime credential. |
| `RunsEventSearchEntry` | `eventId` | `string` | Yes | Stable event identity; also breaks ties in newest-first pagination. |
| `RunsEventSearchEntry` | `occurredAt` | `string` | Yes | Producer occurrence time as a UTC timestamp string. |
| `RunsEventSearchEntry` | `ingestedAt` | `string` | Yes | Index ingestion time as a UTC timestamp string; may be later than occurrence. |
| `RunsEventSearchEntry` | `runId` | `string` | Yes | Public run identity associated with this observation. |
| `RunsEventSearchEntry` | `playName` | `string` | Yes | Recorded Play name. |
| `RunsEventSearchEntry` | `kind` | `string` | Yes | Exact indexed kind; canonical payloads use `type` for this dotted name. |
| `RunsEventSearchEntry` | `level` | `string \| null` | Yes | Recorded log severity, or null; not a JSONPath filter field. |
| `RunsEventSearchEntry` | `message` | `string \| null` | Yes | Log message preview of at most 2,048 characters, or null. Use text logs/export for the full retained line. |
| `RunsEventSearchEntry` | `searchDoc` | `Record<string, unknown>` | Yes | Indexed identity and recorded scalar fields. SDK/API keep this nested; CLI search flattens it onto each event. Provider/operation describe typed activity observations, not every provider call. |
| `RunsEventSearchEntry` | `eventPayload` | `Record<string, unknown>` | No | Stored canonical event details, only when payloads are requested and available. Lifecycle/activity/dataset payloads are observations, not complete tool responses or dataset rows. |
| `RunsEventSearchEntry` | `payload` | `RunsEventPayload \| null` | No | Retained work result for a receipt match when payloads are requested; null if unavailable. Other events need not carry this field. |
| `RunsEventSearchResult` | `events` | `RunsEventSearchEntry[]` | Yes | Matching observations in descending occurredAt/eventId order. |
| `RunsEventSearchResult` | `nextCursor` | `string \| null` | Yes | Opaque continuation token, or null when no further page exists. |
| `RunsEventSearchResult` | `since` | `string` | Yes | Resolved inclusive UTC bound, including a defaulted bound. |
| `RunsEventSearchResult` | `until` | `string` | Yes | Resolved exclusive UTC bound, including a defaulted bound. |
| `RunsEventPayload` | `status` | `'completed' \| 'failed' \| 'skipped'` | Yes | Recorded terminal work outcome. |
| `RunsEventPayload` | `output` | `unknown \| null` | Yes | Stored result data, or null when no output was retained. |
| `RunsEventPayload` | `error` | `string \| null` | Yes | Stored failure message, or null when absent. |
| `RunsEventPayload` | `errorPayload` | `unknown \| null` | Yes | Stored structured failure details, or null when absent. |
