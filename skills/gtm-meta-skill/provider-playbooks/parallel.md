Use Parallel for managed research/extraction runs without custom orchestration.

- Prefer `parallel_run_task`, `parallel_search`, and `parallel_extract` for agent-friendly workflows.
- Prefer `parallel_search` first for attendee/discovery workflows, then `parallel_extract` for targeted pages.
- Use `parallel_run_task` when you need synthesized, schema-shaped outputs from multiple sources.
- Keep monitor/stream endpoints out of default flows unless a user explicitly needs them.
- Pilot on a small objective first, then widen `max_results` and scope.

```bash
deepline tools execute parallel_search --payload '{"mode":"agentic","objective":"Find recent hiring and launch signals for OpenAI","max_results":5,"excerpts":{"max_chars_per_result":1200,"max_chars_total":10000}}' --json
```

```bash
deepline tools execute parallel_extract --payload '{"urls":["https://openai.com/research/index/release/"],"objective":"Extract key product launch signal, release summary, and source evidence","full_content":true}' --json
```

```bash
deepline tools execute parallel_run_task --payload '{"processor":"lite-fast","input":"Summarize key GTM signals for OpenAI from recent public web sources in 3 bullets."}' --json
```

```bash
deepline tools execute parallel_search --payload '{"objective":"Find AI companies that raised Series A funding in 2024 with source links","max_results":10}' --json
deepline tools execute parallel_extract --payload '{"urls":["https://techcrunch.com/2024/12/20/heres-the-full-list-of-49-us-ai-startups-that-have-raised-100m-or-more-in-2024/"],"objective":"Extract company name, funding round, amount, date, and source evidence","excerpts":true}' --json
```
