Use `ai_inference` for plain text or structured-output model calls with no tool use.

Use `deeplineagent` when the task benefits from streaming output and tool use across the current whitelist: `serper_google_search`, `exa_search`, `firecrawl_scrape`, `firecrawl_map`, `firecrawl_crawl`, and `bash`.

For research tasks, prefer an adaptive loop: cheap Serper search first, synthesize, then only run targeted Exa follow-up searches if key gaps remain.

When using `exa_search`, prefer `type: "auto"` with `contents.highlights` and no `contents.summary`; highlights are token-efficient snippets, while summaries add an extra AI pass.

Use Firecrawl only after you know the target site or section. Prefer `firecrawl_scrape` for one known URL, `firecrawl_map` for URL inventory before crawling, and keep `firecrawl_crawl` tightly scoped with explicit low `limit`, `includePaths`/`excludePaths`, or `maxDiscoveryDepth`. Firecrawl work scales with discovered pages, crawled pages, and requested modifiers, so do not run broad speculative crawls.

When `bash` is enabled, `/refs/prompts.json` is available as a lazily loaded reference file for GTM prompt-template lookup.

Prefer Deepline-native tools over freeform bash when structured provider actions already exist.
