# The scraper ladder — configs, costs, rung tests, failure shapes

Prices read with `deepline tools describe` on 2026-09-30; prices DRIFT — re-read them
(`deepline tools describe <tool_id> --json`, the `pricing` block) before quoting, and
read the real charge afterwards from `deepline billing usage` or the run's
`deepline runs get <run-id> --full --json`. Never quote a remembered price.

## Rung 1 — `generic_http_request` (Free; true APIs and hidden APIs)

- Config: `{method, url, headers, query, body_json | body_text | body_form_urlencoded,
  cookies, follow_redirects, timeout_ms}`; parameterize query/page fields per row.
  Exactly one body representation per call.
- Finding a hidden API: Chrome DevTools → Network → filter Fetch/XHR → perform the
  search in the UI → copy the request that returns the result JSON → replicate,
  parameterized. Most directories are a thin front-end over exactly this.
- Also the right rung for HTTP HEAD/GET header checks and public REST (GitHub etc.),
  and the STATUS-HONEST probe: the output carries `status_code`, `ok`, `final_url`
  and `headers` beside `data`, so redirects and 404s are visible. Some APIs (GitHub)
  403 without a User-Agent header — always set one. Private and localhost targets are
  blocked.
- Credential hygiene (hard rule): auth headers are passed at run time from a local
  `@file` or environment variable — never inlined in chat, a play file, or a skill.
  Auth-like values require https and are redacted from results, which keeps them out
  of the output, not out of wherever you pasted them.

## Rung 2 — URL interpolation (cost = rung 3/4 × fewer pages)

When URL structure is predictable (`/companies/<slug>`, `?page=N`,
`/<city-slug>/listings`), build the URL list by formula from a seed/slug list and
fetch ONLY those pages. Keep 1-2 slug variants when the form is ambiguous. Pagination
idiom: generate `start=0,20,...` URL arrays bounded to a stated page cap.

## Rung 3 — static fetch

- `contextdev_get_web_scrape_markdown` — **Free**. Page to clean Markdown; options
  include `includeLinks`, `includeSelectors` / `excludeSelectors`, `includeHTML`.
  Read whether it rendered JavaScript from its output on the first page rather than
  assuming.
- `firecrawl_scrape` — **0.02 credits per page** base. `formats` takes `markdown`,
  `html`, `rawHtml`, `links`, `images`, `screenshot`, `summary`, `json`;
  `onlyMainContent: true` drops nav and footer. Its `metadata.statusCode` reports the
  real HTTP status — check it, because Firecrawl can bill when a target returns
  403/404. A wrong `formats` value is a schema error, not a silent no-op, but an
  all-empty markdown can still mean a JS shell rather than an empty page.
- `formats: ["links"]` = the canonical index-page move: every link out, filter in
  code, then fetch only the survivors. For a whole site, `firecrawl_map` (0.02 credits
  per call) returns the URL inventory without fetching every page.
- Many known URLs: `firecrawl_batch_scrape` instead of a loop.

## Rung 4 — rendered / anti-bot (`firecrawl_scrape` with options)

- Flags: `waitFor` (ms after load — free reliability), `actions` (click, scroll, wait
  before scraping, for SPAs and lazy grids), `proxy: "enhanced"` for bot-protected
  targets (about **+0.05 credits per page**), `location` for geo-gated content.
- Named fields: add `{"type": "json", "schema": {...}, "prompt": "..."}` to `formats`
  (about **+0.05 credits per page**) to get the user's fields back as an object
  instead of raw markdown. This is a model reading the page, not a selector — keep
  `markdown` in `formats` too, and drop any extracted value whose text does not appear
  in that markdown.
- Alternatives when Firecrawl is blocked: `browserbase_fetch_page` (priced from
  Browserbase usage; takes `proxies` and a `schema`), or an Apify actor for a
  site-specific scraper (`apify_run_actor_sync`; read the actor's own pricing).
- **No Zenrows tool and no CSS-selector extractor exist in Deepline.** If a job needs
  exact selector extraction, take `html` and parse it in code, and ship the selector
  map with the warning that public sites change class names routinely.

## Rung tests (spend nothing before the rung is chosen)

1. DevTools Network pass for a JSON API (rung 1) — two minutes, free.
2. Two sample URLs of the same kind: identical structure → interpolate (rung 2).
3. One free fetch of one page (`generic_http_request` GET or
   `contextdev_get_web_scrape_markdown`): real content in plain HTML → rung 3; empty
   body/JS shell → `firecrawl_scrape` with `waitFor`; challenge page → rung 4.

## Failure shapes (gate on served content, not call success)

| Shape | Looks like | Verdict |
|---|---|---|
| Soft 404 | HTTP 200 + "not found" page body | failed page, say so |
| Consent/cookie interstitial | 200 + consent boilerplate, none of the expected fields | not the data — retry with `waitFor`/`actions`, else report |
| Bot challenge | 200 + challenge/captcha markup | blocked — rung 4 with `proxy: "enhanced"` is the ONLY sanctioned escalation; still blocked → report blocked |
| Empty extraction | 200 + fields all empty | wrong rung or the layout changed — inspect, don't deliver empties silently |
| Model-filled field | JSON value present, text absent from the page markdown | not served content — drop the value, report it |
| End of pagination | 404/empty past page N | normal — report the boundary, stop |

A run summary must count these per shape; "10 pages, 7 extracted, 2 blocked, 1
soft-404" is an honest result. Silently delivering 7 rows as if 7 was the universe
is not.
