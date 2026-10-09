# Run logs and events

<!-- Generated from CLI help, the runtime event catalog and packages/sdk/src/client.ts JSDoc. Do not edit manually. -->

Read existing run logs, find failures and filter events. These commands do not execute tools.

## Query retained logs

`--step`, `--level`, `--query`, `--count`, `--sum` or `--group-by` select structured logs for one run; accompanying bounds and `--where` apply to log records. `--step` matches the recorded authored step; `--level warn` includes warn and error. `--query` searches the full retained message literally, including percent signs and underscores. `runs events` applies these operations to lifecycle, receipt and organization-wide events.

Structured reads default to the last hour and 50 records or groups per page (maximum 200). Records are newest first; summary groups use ascending group keys. `--count` returns an exact retained count and cannot combine with `--limit`, `--cursor` or `--payloads`. `--group-by` pages all matching groups; `--sum` totals numeric fields, or returns an ungrouped count and sum without `--group-by`. Numeric sums reject strings and booleans; missing values and null form distinct groups. Sampling and expired history cannot be reconstructed.

`--fields` discovers fields, types and operators. `where` accepts scalar equality, `{ eq, ne, gt, gte, lt, lte, in, exists }`, nested `context: { key: ... }` or flat `"context.key"`, and `{ and: [...] }` / `{ or: [...] }`. String predicates accept equality, inequality, ranges, `in`, `exists`, `&&`, `||` and parentheses; `$.field` is accepted. Quote strings with JSON double quotes; numbers, booleans and null stay unquoted. Missing fields do not match comparisons; use `exists false`. Filters allow 64 comparisons and 8 KiB; custom context fields must be recorded scalars, not nested payload data.

```bash
deepline runs logs '<run-id>' --step company-lookup --level warn --since 1h --where 'context.attempt >= 2 && context.cached == false' --json
deepline runs logs '<run-id>' --query 'timeout %_MARKER' --count --json
deepline runs logs '<run-id>' --group-by stepId --sum context.durationMs --json
deepline runs logs --fields --json
deepline runs events --kind step.failed --since 1h --json
```

`client.runs.logs(runId, options)` remains the callable text reader. Use `logs.query/count/summarize/fields` for structured logs, or `client.runs.events.list/count/summarize/fields` for events; omit `runId` for organization-wide reads. Each method makes one request per page or aggregate.

```ts
import { DeeplineClient } from 'deepline';
const client = new DeeplineClient();
const runId = '<run-id>';
const page = await client.runs.logs.query(runId, {
  since: '1h',
  stepId: 'company-lookup',
  minLevel: 'warn',
  where: { context: { cached: false, attempt: { gte: 2 } } },
});
const count = await client.runs.logs.count(runId, page.query);
```

Lists return flat `logs` or `events`, `page: { returnedCount, hasMore, nextCursor }`, frozen `query` criteria and `retention: { retainedSince, retentionDays }`. Relative bounds resolve once; `since` is inclusive and `until` exclusive. Frozen criteria fix the window, not a snapshot: newly available events may change later pages or aggregates. Start a fresh list to catch late arrivals ahead of its cursor. Follow `next.page`, or reuse `query` with `cursor: page.nextCursor` when `hasMore`. Criteria exclude page options and the positional log run ID, retain an event run ID, and preserve SDK Preview selection. Recorded step, level, source, attempt and context stay together; absent historical fields stay absent.

Counts return `matchedCount` and `exact: true`. Summaries return `groups`, `groupBy`, `measures` and an independent `page`; groups contain `keys` and named numeric `measures`. Missing keys use `{ "missing": true }`, distinct from null or `"<missing>"`.

HTTP uses `POST /api/v2/runs/events` with a flat body: `operation: "list" | "count" | "summarize" | "fields"`, `resource: "logs" | "events"`, `runId`, criteria and options. Log list/count/summary requests require `runId`; fields does not. Summaries require `groupBy` (`[]` for an ungrouped aggregate) and accept `measures: [{ op: "count" }, { op: "sum", field: "context.durationMs", as: "durationMs" }]`. SDK, HTTP and CLI share filter validation. Existing GET and text-log contracts remain available below.

## Read logs or search events

A run ID alone reads text logs. Use the returned nextCursor with --cursor for older lines. Omit the run ID or add a search flag to search events; a supplied run ID narrows the search. --out, --failed and --log-level cannot be combined with event search. Search defaults to the last hour, newest first; maximum lookback is seven days. Follow the returned next.logs command for the next page. --payloads adds available event details or saved work results, not dataset rows. Text logs default to 200 lines; compatibility event search defaults to 100 (maximum 200), or 10 with payloads and 16 MiB. Check retention warnings; --out saves all available log lines.

```bash
deepline runs logs '<run-id>'
deepline runs logs '<run-id>' --out run.log
deepline runs logs --kind run.failed --json
deepline runs logs --play my-play --since 2026-10-06T00:00:00Z --until 2026-10-06T01:00:00Z --json
```

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
| `receipt.completed` | Saved result or call details. |
| `receipt.failed` | Saved work result: failed. |
| `receipt.skipped` | Saved work result: skipped. |
| `runtime.event` | Other event. |

## Compatibility event search with --where

String fields: eventId, orgId, runId, playName, runtimeScope, kind, status, source, level, stepId, stepKind, datasetId, phase, provider, operation. producerAttempt is a positive integer; context.&lt;key&gt; accepts flat string, number or boolean log fields. Use $.field == value joined with &&, at most eight predicates and 512 bytes. Wrap the filter in single shell quotes; strings use double quotes, numbers and booleans are unquoted. Missing fields do not match. No OR, ranges, wildcards or text/payload search. Use --kind for run/step outcomes; status is not inferred from kind. provider/operation match activity.observed where recorded, not every provider call. Replace example values with values from your events.

Bare `runs logs --where`, `--since` and `--kind` keep this equality grammar; text `--failed`, `--out` and `--log-level` keep their established behavior. Context examples use `ctx.log("Lookup finished", { context: { companyId: "acme_123", attempt: 2, cached: false } })`.

```bash
deepline runs logs --kind receipt.failed --where '$.status == "failed"' --payloads --json
deepline runs logs --kind step.failed --where '$.stepId == "company-lookup"' --payloads --json
deepline runs logs --kind activity.observed --where '$.provider == "apollo" && $.operation == "company_lookup"' --json
deepline runs logs --kind dataset.lifecycle --where '$.datasetId == "companies" && $.phase == "failed"' --payloads --json
deepline runs logs --kind log.appended --where '$.context.companyId == "acme_123"' --json
deepline runs logs --kind log.appended --where '$.context.attempt == 2 && $.context.cached == false' --json
deepline runs logs '<run-id>' --where '$.stepId == "company-lookup"' --json
deepline runs logs --kind log.appended --where '$.level == "error" && $.stepId == "company-lookup"' --payloads --json
```

## Retrieve results

`--payloads` adds `eventPayload` details or saved `payload` results; unavailable details are explicit. Select an exact returned `eventId` with its original `--since`/`--until` window. Events retain seven days; details may differ. Redirecting JSON saves one page: follow `next.logs` for compatibility search or `next.page` for structured reads. Use `--out run.log` for all text or `runs export --format json --out results.json` for dataset rows.

```bash
deepline runs logs '<run-id>' --kind receipt.completed --payloads --json
deepline runs logs --where '$.eventId == "receipt:5a32ee1a-46cf-4853-b72b-5f1d782ffab4"' --payloads --json
```

New tool results retain sanitized input under `payload.output.meta.callEvidence.input` and output under `payload.output.toolResponse.rawV2`. `callEvidence.providerRequests` contains observed HTTP requests, response status and failed response bodies; successful output is retained once in `toolResponse.rawV2`. Credentials and provider billing fields are removed. Multipart, binary, streaming, oversized or unobserved evidence reports an unavailable reason. Older results may have no input evidence.

Find new saved failed-call records with `--kind receipt.completed --where '$.context.callStatus == "failed" && $.context.callKey == "lookup"' --payloads`. Details have `payload.output.kind: "tool_call_evidence"`, `status: "failed"`, `callEvidence` and the original error. `receipt.completed` means the diagnostic was saved; use `step.failed` for the causal failure.

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
| `RunsEventSearchOptions` | `jsonpath` | `string` | No | JSONPath equality joined with `&&`, at most eight predicates and 512 bytes. `eventId` selects an exact returned event; add `payloads` to retrieve its saved details. See `runs logs --help` for fields and examples. Missing fields do not match; status is not inferred from kind. HTTP `jsonpath`, CLI `--where`. |
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
| `RunsEventSearchEntry` | `level` | `string \| null` | Yes | Recorded log severity, or null on older events. Filter with `$.level == "error"`. |
| `RunsEventSearchEntry` | `message` | `string \| null` | Yes | Log message preview of at most 2,048 characters, or null. Use text logs/export for the full retained line. |
| `RunsEventSearchEntry` | `searchDoc` | `Record<string, unknown>` | Yes | Recorded filter fields. SDK/API keep this nested; the CLI places these fields directly on each event. |
| `RunsEventSearchEntry` | `eventPayload` | `Record<string, unknown>` | No | Available event details when requested with `includePayloads`; dataset events contain metadata, not dataset rows. |
| `RunsEventSearchEntry` | `payload` | `RunsEventPayload \| null` | No | Retained work result for a receipt match when payloads are requested; null if unavailable. Other events need not carry this field. |
| `RunsEventSearchResult` | `events` | `RunsEventSearchEntry[]` | Yes | Matching observations in descending occurredAt/eventId order. |
| `RunsEventSearchResult` | `nextCursor` | `string \| null` | Yes | Opaque continuation token, or null when no further page exists. |
| `RunsEventSearchResult` | `since` | `string` | Yes | Resolved inclusive UTC bound, including a defaulted bound. |
| `RunsEventSearchResult` | `until` | `string` | Yes | Resolved exclusive UTC bound, including a defaulted bound. |
| `RunsEventPayload` | `status` | `'completed' \| 'failed' \| 'skipped'` | Yes | Recorded terminal work outcome. |
| `RunsEventPayload` | `output` | `unknown \| null` | Yes | Saved result, including available sanitized call input/output details; failed-call records use kind: tool_call_evidence. Null when no output was retained. |
| `RunsEventPayload` | `error` | `string \| null` | Yes | Stored failure message, or null when absent. |
| `RunsEventPayload` | `errorPayload` | `unknown \| null` | Yes | Stored structured failure details, or null when absent. |
