Use Parallel for managed research/extraction runs without custom orchestration.

- Prefer `parallel_run_task`, `parallel_search`, and `parallel_extract` for agent-friendly workflows.
- Prefer `parallel_search_mcp` and `parallel_fetch_mcp` when you want the free hosted Search MCP instead of the paid REST APIs.
- Prefer `parallel_search` first for attendee/discovery workflows, then `parallel_extract` for targeted pages.
- `parallel_search_mcp` is best for lightweight current-events or broad-source web lookups where zero provider spend matters more than advanced REST-side controls.
- `parallel_fetch_mcp` is best after `parallel_search_mcp` narrows candidates, or when you already have a small list of URLs to read.
- Use `parallel_run_task` when you need synthesized, schema-shaped outputs from multiple sources.
- Call `parallel_run_task` first. If it finishes quickly, use that result.
- If `parallel_run_task` returns pending or times out, keep the `run_id` and use `parallel_get_task_run_result` later to fetch the final output.
- Ignore `parallel_get_task_run` unless you specifically need run metadata like status timestamps or processor info.
- Keep monitor/stream endpoints out of default flows unless a user explicitly needs them.
- Pilot on a small objective first, then widen `max_results` and scope.
- For the free MCP actions, pass a stable `session_id` across related calls when possible to reduce anonymous-tier throttling.

```bash
deepline tools execute parallel_search --payload '{"mode":"agentic","objective":"Find recent hiring and launch signals for OpenAI","max_results":5,"excerpts":{"max_chars_per_result":1200,"max_chars_total":10000}}'
```

```bash
deepline tools execute parallel_search_mcp --payload '{"objective":"Find recent OpenAI product announcements","search_queries":["OpenAI recent announcements","site:openai.com/news OpenAI product"],"session_id":"demo-session"}'
```

```bash
deepline tools execute parallel_extract --payload '{"urls":["https://openai.com/research/index/release/"],"objective":"Extract key product launch signal, release summary, and source evidence","full_content":true}'
```

```bash
deepline tools execute parallel_fetch_mcp --payload '{"urls":["https://openai.com/news"],"objective":"Extract the latest product announcement headlines","search_queries":["OpenAI latest product announcements"],"session_id":"demo-session"}'
```

```bash
deepline tools execute parallel_run_task --payload '{"processor":"lite-fast","input":"Summarize key GTM signals for OpenAI from recent public web sources in 3 bullets."}'
```

```bash
deepline tools execute parallel_get_task_run_result --payload '{"run_id":"trun_123"}'
```

```bash
deepline tools execute parallel_search --payload '{"objective":"Find AI companies that raised Series A funding in 2024 with source links","max_results":10}'
deepline tools execute parallel_extract --payload '{"urls":["https://techcrunch.com/2024/12/20/heres-the-full-list-of-49-us-ai-startups-that-have-raised-100m-or-more-in-2024/"],"objective":"Extract company name, funding round, amount, date, and source evidence","excerpts":true}'
```
