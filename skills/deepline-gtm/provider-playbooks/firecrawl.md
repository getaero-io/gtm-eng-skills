# Firecrawl — Agent Guidance

## Action selection

- **Single page** → `firecrawl_scrape`. Returns markdown by default.
- **Web search + content** → `firecrawl_search`. Replaces Google search + individual page scraping in one call.
- **Site discovery** → `firecrawl_map` first to enumerate URLs, then `firecrawl_batch_scrape` the ones you need.
- **Full site crawl** → `firecrawl_crawl_params_preview` to estimate cost, then `firecrawl_crawl`.
- **Known URL list** → `firecrawl_batch_scrape`. More efficient than individual scrapes.
- **Structured extraction** → `firecrawl_extract` with a JSON schema or natural language prompt.
- **Complex web tasks** → `firecrawl_agent` with a natural language instruction. The agent navigates pages autonomously.

## Budget awareness

- Cost scales with pages processed: scrape, crawl, batch scrape, and map are billed per page, search is billed per result, and agent and extract are dynamic.
- Scrape options increase per-page cost. PDF parsing, JSON format, Enhanced Mode, and Zero Data Retention each add to the base page cost, and they stack.
- Deepline credit pricing for these actions is generated from the provider pricing metadata and rendered on the public provider pages.
- Firecrawl can charge when infrastructure processes a request even if the target returns 403/404. Avoid blind retries of blocked URLs; inspect `metadata.statusCode`.
- Crawl defaults to `limit: 10000` and Firecrawl preflights available balance against that limit. Always pass an explicit lower `limit` unless a 10000-page crawl is intentional.
- `crawl_params_preview` is free and shows estimated usage before committing.

## Async operations

- `crawl`, `batch_scrape`, `agent`, and `extract` are async. They return a job ID immediately.
- The action handler polls automatically for up to 5 minutes and returns results when ready.
- For non-blocking usage, use the corresponding status-check action (`get_crawl_status`, etc.) to poll manually.
- Cancel long-running jobs with the cancel actions when results are no longer needed.

## Format recommendations

- Use `markdown` format for LLM consumption (default).
- Use `html` when you need the raw DOM structure.
- Use `links` to extract all hyperlinks from a page.
- Use `screenshot` when visual layout matters.

## Rate limits

- Standard rate limit is 15 requests/second.
- Batch and crawl operations are rate-limited server-side; the API handles queuing.
