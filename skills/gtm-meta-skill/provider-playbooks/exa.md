Use Exa for web-grounded retrieval, then synthesis.

- In AI-column workflows, instruct the model prompt to use Exa retrieval explicitly for website-derived tech stack and on-site signals.
- Use direct Exa tool calls when you need tighter provider controls or auditable step-by-step retrieval outside AI-column orchestration.
- For auditable outputs, run `exa_search`/`exa_contents` first and synthesize after inspecting citations.
- Use focused queries and small `numResults` during pilots, then widen only if coverage is low.
- Treat `exa_answer` as the summarization layer, not the first retrieval step, when precision matters.

```bash
deepline tools execute exa_search --payload '{"query":"series b devtools companies united states","numResults":5,"type":"fast"}' --json
```

```bash
deepline tools execute exa_contents --payload '{"urls":["https://example.com"],"text":true}' --json
```

```bash
deepline tools execute exa_answer --payload '{"query":"Summarize the top GTM signals from these results","text":true}' --json
```
