# Firecrawl — Agent Guidance

## Action selection

- **Single page** → `firecrawl_scrape`. Returns markdown by default. Costs 1 credit.
- **Web search + content** → `firecrawl_search`. Replaces Google search + individual page scraping in one call.
- **Site discovery** → `firecrawl_map` first to enumerate URLs, then `firecrawl_batch_scrape` the ones you need.
- **Full site crawl** → `firecrawl_crawl_params_preview` to estimate cost, then `firecrawl_crawl`.
- **Known URL list** → `firecrawl_batch_scrape`. More efficient than individual scrapes.
- **Structured extraction** → `firecrawl_extract` with a JSON schema or natural language prompt.
- **Complex web tasks** → `firecrawl_agent` with a natural language instruction. The agent navigates pages autonomously.

## Budget awareness

- Run `firecrawl_check_credits` before large operations (crawl, batch scrape, extract) to confirm remaining balance.
- Credit costs vary by action — scrape is 1 credit, search is 1 credit per result, crawl is 2 credits per page.
- `crawl_params_preview` is free and shows estimated credit usage before committing.

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
