# Bring your own Exa key

Choose this optional mode when you want Alpha Copy to retrieve historical and current
observations automatically. It adds two Deepline `generic_http_request` calls to Exa
`/contents`, authenticated with your own Exa key, followed by the normal research, audit,
score and copy steps. The ordinary run still works without Exa.

Deepline's managed `exa_contents` tool (no key needed) does not expose Exa's `snapshotAsOf`
input, so historical snapshots need your own key through `generic_http_request`.

## Add your key

1. Export it in the shell that runs the script: `export EXA_API_KEY=...` (or source it from a
   private env file). Do not put the key in a brief, CSV column, prompt, chat or this package.
2. The runner reads `EXA_API_KEY` only at call time and passes it as the `x-api-key` header.
   It is not written to the graph or the run record; Deepline redacts reflected auth values
   from `generic_http_request` results.

Exa documents `x-api-key`, `snapshotAsOf` and fresh content retrieval here:
https://exa.ai/docs/reference/get-contents.
An API key alone does not guarantee Snapshot entitlement or coverage for a particular date.

## Run the Exa-enabled version

```bash
python3 scripts/run.py --state PRIVATE_RUN_DIR --brief BRIEF.json --exa
```

Add `--start` to run. `--exa` combines with `--csv`/`--field-map`. It adds four nodes
(prepare, past fetch, current fetch, normalize) in front of research; it never sends anything.

The Exa graph builder is `../scripts/exa.py`. Request preparation and response checks
are in `exa-prepare.py` and `exa-normalize.py`.

## Configure the comparison at the beginning

- **Offer / ICP / greeting / CTA / signature:** unchanged; set once for the batch.
- **Company domain:** comes from each person's employer.
- **Comparison as of:** required past date (`comparison_as_of`, YYYY-MM-DD).
- **Page path:** optional (`comparison_page_path`), default `/`; use `/pricing` for pricing.
- **Comparison focus:** the type of change you want investigated.

No evidence JSON columns are needed in automatic Exa mode. Leave imported receipt inputs
empty so the workflow cannot mix a supplied historical claim with an unrelated fresh pair.
The same-company URL and cutoff are generated per run; one URL is requested per call.
The Exa version requires the historical comparison and cannot silently fall back to a
current-state pitch when history is missing.

## The two calls and checks

Both calls POST to the fixed endpoint `https://api.exa.ai/contents`.
The historical body has `urls`, `text=true` and `snapshotAsOf`; the current body has
`urls`, `text=true` and `maxAgeHours=0`. Redirect following is disabled.

The response check requires one successful result for the exact requested HTTPS page,
a provider request ID and substantive text. Current content must be marked freshly crawled.
It retains the actual request receipts and observation time. `publishedDate` is **not** used
as the historical capture time. Exact capture time stays unknown unless independently supplied
and verified; requested cutoff is still not the change date.

`generic_http_request` returns `{status_code, ok, data, ...}`; the parser unwraps `data` to
the Exa body and fails on unknown shapes or non-200 status. Before a real batch, run one
authorized company, inspect both outputs in the run record, and confirm the actual
fresh/history semantics. Local or synthetic tests are not proof of an authenticated call.

A failed key, unavailable Snapshot entitlement, trial cap, unavailable historical page,
title-only result, changed URL, stale current response or unrecognized envelope stops at
retrieval/normalization. It does not become an approved draft or a fictional observation.
The usual evidence gates still reject unchanged content and unsupported commercial connections.

Each person processed by this version makes two Exa requests. It does not deduplicate
coworkers' company lookups. Exa usage is billed by Exa on your key; `generic_http_request`
itself is free in Deepline. Verify plan limits and a bounded test before scaling.
No fixed price or successful historical coverage is promised.
