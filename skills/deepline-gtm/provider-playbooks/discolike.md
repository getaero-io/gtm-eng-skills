# DiscoLike Integration Guide

DiscoLike indexes companies by their website (87M+ business domains, 60 languages). Its edge is the long tail: small and local businesses such as law firms, medical and dental practices, contractors, agencies, and other SMBs that have a website but little LinkedIn or funding footprint. Reach for it when person- or LinkedIn-first providers return nothing for a small company.

## Pick the right tool

| You have | You want | Use |
| --- | --- | --- |
| A company name, optionally city, state, zip, country, or phone | Its website domain | `discolike_match` |
| A domain | Firmographics (name, address, phone, industry, size, revenue range, socials) | `discolike_bizdata`, or `discolike_append_bizdata` for up to 10,000 domains in one call |
| An ICP description, filters, or seed domains | A list of similar companies | `discolike_count` first (free), then `discolike_discover` |
| Company domains, or an ICP description such as "roofers in Texas" | People with a validated work email | `discolike_find_contacts` |
| A person's name, optionally company or domain | Which company they are at, and their title | `discolike_match_contact` (free) |
| A domain | Related domains | `discolike_vendors`, `discolike_publiclink`, `discolike_subsidiaries`, `discolike_redirects` |
| A domain | Footprint size or growth | `discolike_score`, `discolike_growth` |
| A URL | Page text | `discolike_extract` |
| A set of domains | Clusters of similar companies | `discolike_segment` |
| Domains plus a question | An AI-researched answer per company | `discolike_run_company_research` |

## Company match (name + geo)

`discolike_match` resolves a company name to ranked domain candidates, each with a `match_confidence` from 0 to 100 and a full BizData profile. Use it as a fallback when other providers can't find a domain for a small business, or as a first pass for local businesses.

- Pass the clean company name in `name`. Add `city`, `state` (code or full name), `zip_code`, `country` (ISO-2), or `phone` to separate businesses with common names, such as "Smith & Associates" in Austin and in Denver.
- `local_mode: true` keeps state and country during DiscoLike's filter relaxation, so it won't return a same-named company in another state.
- `strict: true` requires an exact normalized name match.
- `min_match_confidence` (50-100) drops weak candidates. Use about 80 when writing the domain back without review.
- No match means an empty result, which bills nothing. You pay one record per returned match.

## Discovery

- `discolike_count` is free. Run it before `discolike_discover` to size a list.
- `discolike_discover` accepts seed `domain`s (lookalikes), `icp_text`, or `icp_prompt` (natural language converted to filters), plus filters such as `phrase_match`, `category`, `tech_stack`, `country`, `state`, `employee_range`, `revenue_range`, and `business_model`. Each returned company bills one record.

## Contacts

`discolike_find_contacts` finds people and validates their work emails in one call. It works well for small businesses that LinkedIn-first tools cover poorly.

- Choose companies with `companies.source`:
  - `domains`: a list of up to 10,000 company domains. No company charge.
  - `prompt`: `icp_text` (for example "family law firms in Austin with 1 to 50 employees") and/or `filters` (`filter_industry`, `sub_industry`, `filter_country`, `filter_state`, `employee_range`, `revenue_range`, and their `negate_` forms). Locations and sizes written in `icp_text` become filters; the result shows them in `applied_company_filters`.
  - `lookalike`: `persona_ids` or `linkedin_urls` of example people. It finds similar people at similar companies.
- Describe who you want in `people.fit` (plain language, default "Senior executives and decision makers"). There are no seniority or source controls.
- `max_companies` (required) is the number of companies that must deliver a contact. `per_company` (default 10) caps contacts per company. Set `email_cap_usd` to cap spend.
- Every returned contact has `email_status` `Validated` or `Validated (catch-all resolved)`. Both are verified mailboxes, so you don't need to verify them again.
- Pricing: only validated contacts bill, plus one company record for each company that delivers on `prompt` and `lookalike` runs. Deepline holds the run's maximum cost before it starts and settles to what it actually spent.
- The call waits up to `max_wait_ms` (default 2 minutes). If the run is still working, the result has `status: running` and an `id`. Read it later with `discolike_get_contacts_run` (`rows_offset`/`rows_limit` page companies). Use `discolike_get_contacts_run_events` for a progress feed, and `discolike_cancel_contacts_run` to stop it. Contacts delivered before a cancel stay charged.
- Reuse the same `create_key` to get the existing run back instead of starting a new one.

`discolike_match_contact` finds a named person in DiscoLike's contact index. It returns name, title, company domain and name, and `match_score`. It returns no email, phone, or LinkedIn, and it is free.

`discolike_search_indexed_contacts` and `discolike_generate_candidate_contacts` call DiscoLike endpoints that stop working after 2026-12-31. Use `discolike_find_contacts` for new workflows. Treat emails, LinkedIn URLs, and phones returned by `discolike_generate_candidate_contacts` as unvalidated candidates.

## Async tools

`discolike_segment`, `discolike_generate_candidate_contacts`, and `discolike_run_company_research` submit a DiscoLike task and wait for it to finish. If the wait times out, call `discolike_get_segment_status` or `discolike_get_discogen_status` with the returned `task_id`. Status checks are free. `discolike_segment` needs at least 5 domains.

DiscoGen tools (`discolike_generate_candidate_contacts`, `discolike_run_company_research`) run on a Deepline-managed model (OpenAI `gpt-5-nano`, low search context). Caller model and search overrides, high search context, and `web_search: true` are blocked. Website and profile context modes cost more than `domain` mode.

## Pricing

DiscoLike bills per returned record, with no per-query fee. Deepline charges per returned company record on discovery, match, enrichment, and relationship tools, and per validated contact on `discolike_find_contacts`. `discolike_count`, `discolike_match_contact`, contacts run reads, and status checks are free.
