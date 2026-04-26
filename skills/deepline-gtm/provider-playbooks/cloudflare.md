# Cloudflare Browser Rendering — Agent Guidance

## When to use
- You need to crawl a website and extract structured content (markdown, HTML, or JSON).
- You need browser-rendered pages (JavaScript-heavy SPAs, dynamic content).
- You want a managed crawl that follows links up to a configurable depth/limit.

## Key parameters
- **`url`** (required): The starting URL.
- **`limit`**: Max pages to crawl. Default 10. Keep low unless the user needs broad coverage.
- **`depth`**: Max link depth from the starting URL. Default 100,000.
- **`source`**: URL discovery method — `"all"` (default), `"sitemaps"`, or `"links"`.
- **`formats`**: Array of `"html"`, `"markdown"`, `"json"`. Default `["markdown"]`. Markdown is best for LLM consumption. JSON uses Workers AI for extraction and requires `jsonOptions`.
- **`render`**: Browser rendering toggle. Default `true`. Set `false` for simple static pages to save browser seconds.
- **`options.includePatterns`** / **`excludePatterns`**: Wildcard patterns to filter which URLs get crawled. Exclude takes priority.
- **`timeoutMs`**: How long to poll before returning partial results. Default 5 minutes.

## Timeout behavior
- On timeout, the action returns whatever partial results are available with `timedOut: true`.
- The `jobId` is included so you can construct a follow-up poll if needed.
- The action does NOT throw on timeout.

## Job statuses
- `running` — crawl in progress (non-terminal)
- `completed` — all pages crawled successfully
- `errored` — unrecoverable error
- `cancelled_due_to_timeout` — exceeded 7-day max runtime
- `cancelled_due_to_limits` — hit account browser time limits
- `cancelled_by_user` — manually cancelled

## Cost awareness
- Priced at **$0.20 per 1,000 browser-seconds** (render=true). Billed post-deduct based on `browserSecondsUsed` in the response.
- `render: false` crawls use 0 browser-seconds (free during beta).
- Keep `limit` reasonable — large crawls consume significant browser time.
- Crawl jobs expire after 7 days; results available 14 days post-completion.

## Robots.txt
- Cloudflare respects `robots.txt` by default, including `crawl-delay`.
- Blocked URLs appear in results with `"status": "disallowed"`.
