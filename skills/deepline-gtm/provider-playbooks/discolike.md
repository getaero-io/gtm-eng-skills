# DiscoLike Integration Guide

Use DiscoLike for website-first company discovery and domain intelligence.

## Best entry points

1. `discolike_count` when you want a fast volume estimate for supported search filters like phrase, category, geography, technology, or business model before paying to retrieve a large result set.
2. `discolike_discover` when you have seed domains or a natural-language ICP.
3. `discolike_bizdata` when you already know the domain and need a firmographic profile.
4. `discolike_match` when you start from a company name and need the best matching domain.
5. `discolike_search_indexed_contacts` when you want indexed contacts from DiscoLike's contact dataset at known company domains or matching contact/company filters.
6. `discolike_generate_candidate_contacts` when you want ContaGen-style open-web research to generate candidate contacts at known company domains using DiscoLike-configured BYOK model and search-provider integrations.
7. `discolike_run_company_research` when you want Claygent-style arbitrary company research: run one prompt per domain against company context and optional web search.
8. `discolike_vendors`, `discolike_publiclink`, `discolike_subsidiaries`, and `discolike_redirects` for relationship mapping.

## Segment behavior

`discolike_segment` is public and synchronous from the agent perspective: it submits DiscoLike's async segment job, polls the provider status endpoint, and returns the completed segment rows when available.

If the sync wait times out, call `discolike_get_segment_status` with the returned `task_id` to retrieve the provider result later. This status call is a free read-only recovery step for tasks created by the same organization; final customer billing is reconciled by Deepline's async provider cron against the original `discolike_segment` billing row.

## Contact generation behavior

`discolike_search_indexed_contacts` searches DiscoLike's indexed contact/persona data.

`discolike_generate_candidate_contacts` is the ContaGen path: it submits `POST /contacts/discover/generate`, then polls DiscoGen status until terminal results are available or the caller's wait budget expires. Use it only when candidate open-web contact discovery is acceptable. Treat generated `email`, `linkedin_url`, phone, and identity fields as candidates until validated.

`discolike_run_company_research` is the Claygent-like path: it submits `POST /discogen/process`, runs an arbitrary prompt against each company domain, and polls DiscoGen status for final results.

DiscoGen/ContaGen are BYOK from DiscoLike's perspective: they use the DiscoLike-configured LLM and search-provider integrations and may return a provider-side `estimated_cost` for model/search usage. For Deepline-managed DiscoLike execution, those configured model/search integrations are Deepline-managed upstream costs, so returned `estimated_cost` is included in Deepline billing. If the caller omits `integration_id`, Deepline uses the cheapest verified managed LLM config, OpenAI `gpt-5-nano`; if the caller omits `search_context_size`, Deepline uses `low`. Caller-selected model/search overrides, high search context, and `web_search: true` are blocked on the managed shared-key path. Deepline charges $0.01 for domain-mode generated-contact or company-research task launches, plus returned `estimated_cost` when present. Website/profile context modes also add Deepline DiscoLike Pro usage pricing for company context: $0.21/query plus $4.20 per 1,000 submitted domains.

## Pricing caveat

DiscoLike bills directly in USD and the exact query / record rate depends on the account plan. Deepline's shared Pro-plan model prices customer-facing paid DiscoLike usage at 40% above the provider rate: $0.21 per query plus $4.20 per 1,000 net-new records. Records cached within the provider account for 90 days are free on repeat retrieval upstream, but Deepline still uses stable customer-facing modeled pricing.
