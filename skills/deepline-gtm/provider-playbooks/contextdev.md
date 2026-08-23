# Context.dev

Use scrape or retrieval actions for one-off reads. Use crawl, extract, batch, monitor, and WebDB actions only when the broader or persistent workflow is intentional.

Read the current resource before updating or deleting it. Confirm IDs before monitor runs, batch cancellation, WebDB sync or reprocessing, purges, and deletes. These operations can change customer-owned state.

Start with `contextdev_get_web_scrape_markdown` for a single page and `contextdev_post_web_crawl` for a bounded site crawl. Keep page limits and timeouts small while validating a workflow.
