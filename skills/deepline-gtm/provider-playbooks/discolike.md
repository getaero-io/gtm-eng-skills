# DiscoLike Integration Guide

Use DiscoLike for website-first company discovery and domain intelligence.

## Best entry points

1. `discolike_count` when you want a fast volume estimate for supported search filters like phrase, category, geography, technology, or business model before paying to retrieve a large result set.
2. `discolike_discover` when you have seed domains or a natural-language ICP.
3. `discolike_bizdata` when you already know the domain and need a firmographic profile.
4. `discolike_search_indexed_contacts` when you want indexed contacts from DiscoLike's contact dataset at known company domains or matching contact/company filters.
5. `discolike_generate_candidate_contacts` when you want ContaGen-style open-web research to generate candidate contacts at known company domains using DiscoLike-configured BYOK model and search-provider integrations.
6. `discolike_run_company_research` when you want Claygent-style arbitrary company research: run one prompt per domain against company context and optional web search.

## Segment behavior

`discolike_segment` is public and synchronous from the agent perspective: it submits DiscoLike's async segment job, polls the provider status endpoint, and returns the completed segment rows when available.

If the sync wait times out, call `discolike_get_segment_status` with the returned `task_id` to retrieve the provider result later. This is a free read-only job-ID action for tasks created by the same organization. Billing separately tracks accepted provider work until terminal usage is known; no result cache resumes the task.

## Contact generation behavior

`discolike_search_indexed_contacts` searches DiscoLike's indexed contact/persona data.

To leave specific people out, pass `exclude_persona_ids` (up to 1,000 DiscoLike `persona_id` values, for example from earlier calls to this tool when paging through a market). DiscoLike exclusion lists accept only persona IDs and domains, so LinkedIn URLs, emails, or names cannot be excluded. Deepline creates a temporary exclusion list for that one search and deletes it afterwards; callers never manage lists. If DiscoLike does not confirm the deletion, the call fails as retryable and is not charged.

`discolike_generate_candidate_contacts` is the ContaGen path: it submits `POST /contacts/discover/generate`, then polls DiscoGen status until terminal results are available or the caller's wait budget expires. Use it only when candidate open-web contact discovery is acceptable. Treat generated `email`, `linkedin_url`, phone, and identity fields as candidates until validated.

`discolike_run_company_research` is the Claygent-like path: it submits `POST /discogen/process`, runs an arbitrary prompt against each company domain, and polls DiscoGen status for final results.

Inspect the Deepline price estimate for DiscoGen/ContaGen before execution. If the caller omits `integration_id`, Deepline uses the managed LLM config, OpenAI `gpt-5-nano`; if the caller omits `search_context_size`, Deepline uses `low`. Caller-selected model/search overrides, high search context, and `web_search: true` are blocked on the managed shared-key path. Website/profile context modes cost more than domain mode because they add company-context usage on top of the task launch.

## Pricing caveat

Deepline credit pricing for these actions is generated from the provider pricing metadata and rendered on the public provider pages.
