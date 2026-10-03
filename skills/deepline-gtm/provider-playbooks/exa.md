Use Exa for web-grounded retrieval, then synthesis.

**`type` vs `category`:** `type` controls the search strategy (auto/fast/neural/deep). `category` filters result type (company/people/news/financial report). These are independent params. `"type":"news"` is a 422 error — use `"category":"news"` for news results.

- In AI-column workflows, instruct the model prompt to use Exa retrieval explicitly for website-derived tech stack and on-site signals.
- Use direct Exa tool calls when you need tighter provider controls or auditable step-by-step retrieval outside AI-column orchestration.
- For auditable outputs, run `exa_search`/`exa_contents` first and synthesize after inspecting citations.
- For larger or uncertain authorized research, use focused queries and small `numResults` during a pilot, then widen only if coverage is low. A small supplied Play needs no extra pilot; inspect retained citations without rerunning retrieval or adding paid repair.
- Treat `exa_answer` as the summarization layer, not the first retrieval step, when precision matters.

```bash
deepline tools execute exa_search --payload '{"query":"series b devtools companies united states","numResults":5,"type":"fast"}'
```

```bash
deepline tools execute exa_contents --payload '{"urls":["https://example.com"],"text":true}'
```

```bash
deepline tools execute exa_answer --payload '{"query":"Summarize the top GTM signals from these results","text":true}'
```
