# Searching for Leads/Accounts and Building Lead Lists

Use this doc for prospecting, company research, profile discovery, signal extraction, and news, or any tasks that involve building lead/account lists. 

## Search-to-enrichment handoff (mandatory)

This doc governs **discovery/search only**. The moment the workflow shifts to per-row or per-column enrichment, route to [enrich-waterfall.md](enrich-waterfall.md) and execute there.

Use this handoff trigger:
- You now have a seed list (or can create one) and need contact fill, email finding/validation, signal scoring, personalization, coalescing, or any other column-level transforms.
- You need repeatable, inspectable row-level lineage in Playground.

Required behavior after trigger:
- Stop adding ad-hoc shell/python/node scripts for row stitching, coalescing, ranking, or enrichment.
- Move all per-column operations into `deepline enrich --with ...` columns.
- Keep lineage in-sheet (`_metadata`) and iterate in Playground per [enrich-waterfall.md](enrich-waterfall.md).

Hard rule:
- **Do not use custom scripts for per-row/per-column enrichment pipelines when `deepline enrich` can express the step.**
- Scripts are allowed only for minimal file hygiene outside enrichment semantics (for example: creating a tiny seed CSV), not for enrichment logic.

## Tool discovery loop for signals / potential datasources for lists....

Use `deepline tools search` first for any signal-driven ask.

Rules:
1. Search 3-6 synonyms.
2. Use matched fields exactly; do not invent.
3. Run `Search execute example` as pilot.
4. For CrustData enums, run autocomplete first.

```bash
deepline tools search investor
deepline tools search funding --prefix crustdata
deepline tools search hiring
```

Investor-backed pilot:

```bash
deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"crunchbase_investors","query":"Sequoia","limit":5}' --json
deepline tools execute crustdata_companydb_search --payload '{"filters":[{"filter_type":"crunchbase_investors","type":"(.)","value":"Sequoia Capital"}],"limit":20}' --json
```

## Execution philosophy: parallel-first, no deliberation. Use subagents for independent workstreams when available.

**Do not deliberate about which single provider to use. Fire multiple vectors in parallel immediately.**

**DO not guess params, read schemas either below in this file or by calling deepline tools get <provider>**

Every search/discovery task should launch 2-3+ parallel searches on the first tool call — a mix of web search (exa, google, parallel_search) and structured API (apollo, crustdata, pdl). Don't reason about "which approach is best" — try them all simultaneously and merge results. The cost of an extra cheap search is near-zero; the cost of overthinking is wasted turns.

Website research is super underrated and often the best way to get lists, esp < ~200 leads. But try everything.

**Default pattern for any search task:**
1. Immediately fire parallel searches: web (exa/google/parallel_search) + structured API (apollo/crustdata/pdl) — same tool call, no deliberation step.
2. Read results, validate quality (discard garbage/nonsensical hits), merge/deduplicate.
3. If coverage is short or responses are poor, fan out to more providers or refine queries. Iterate fast.

**Anti-patterns (do NOT do these):**
- Thinking "let me consider which provider is best for this" — just run them all.
- Running a single provider, waiting for results, then deciding whether to try another.
- Writing a multi-step plan before executing anything.
- Asking the user which approach they prefer when you can just try all approaches.
- **Trusting provider responses blindly** — providers often return garbage, nonsensical, or irrelevant data. Validate and fallback immediately.
- **After discovery, continuing in shell/python scripts for per-column enrichment instead of handing off to [enrich-waterfall.md](enrich-waterfall.md).**

## Subagent orchestration for parallel search

When the `deepline-list-builder` subagent is available, use it to fan out searches
across providers in parallel. This is the preferred execution pattern because:
- Each provider search runs in an isolated context (no context pollution)
- Results can be compared side-by-side for quality
- The main agent stays clean for merging/deduplication/next steps

### How to use

1. Identify which providers are relevant for the query type (see Provider mix table below)
2. Spawn one `deepline-list-builder` subagent per provider — all in a single tool call for true parallelism
3. Each subagent receives: the user's query + the provider to use
4. When all subagents return, compare result quality:
   - Which providers returned relevant, complete data?
   - Which returned garbage/empty/irrelevant results?
5. Merge the best results, deduplicate by domain or LinkedIn URL
6. Hand off to enrich-waterfall.md for per-row enrichment

### Example: spawning parallel subagents

For "Find Series B AI companies selling to healthcare in the US":

Spawn these subagents in parallel (single message, multiple Task tool calls):
- deepline-list-builder: query="Series B AI healthcare companies US", provider=exa
- deepline-list-builder: query="Series B AI healthcare companies US", provider=crustdata
- deepline-list-builder: query="Series B AI healthcare companies US", provider=apollo
- deepline-list-builder: query="Series B AI healthcare companies US", provider=google
- deepline-list-builder: query="Series B AI healthcare companies US", provider=peopledatalabs

### Provider selection by query type

Use the same provider mix table already in this doc. The number of subagents is
not fixed — use as many providers as are relevant. For most queries, 3-5 is ideal.

### When NOT to use subagents

- Single-provider lookups (e.g., "get this person's email from Apollo")
- Enrichment tasks (use `deepline enrich` directly)
- When the user has already specified a single provider

## Quick catalog

- `google_search_google_search` — broad recall and URL discovery.
- `parallel_search` — fast candidate discovery when speed matters.
- `exa_answer` — schema-light quick answers with citations.
- `exa_research` — deeper multi-source synthesis under schema constraints.
- `apollo_search_people` — Apollo preview discovery (`mixed_people/api_search`), no Apollo credit charge. Results may include obfuscated last names.
- `apollo_people_search_paid` — Apollo paid search (`mixed_people/search`), billed per page; use when preview is insufficient and you need scalable paid retrieval. Generally OK quality data and mediocre filters. 
- `crustdata_companydb_search` — **primary tool for structured company list building through a vendor, if apollo doesn't have the right filters** Supports investor filters (`crunchbase_investors`), funding stage (`last_funding_round_type`), headcount, industry, geography, revenue. Use autocomplete first for canonical values. This is the right tool for "find companies backed by Sequoia", etc.
- `adyntel_facebook_ad_search` — Meta keyword-based ad search for additional channel coverage.
- `crustdata_job_listings` — **primary tool for hiring signals.** Given a list of company domains or IDs, returns active job listings. Use this to verify "is this company hiring for X?" — far more reliable than Apollo job filters or web search.
- `crustdata_people_search` / `crustdata_persondb_search` — LinkedIn-oriented person discovery.
- `crustdata_companydb_autocomplete` — free, no credits. Always run this before `crustdata_companydb_search` to get exact canonical values for fields like `last_funding_round_type`, `crunchbase_investors`, `linkedin_industries`.
- `parallel_run_task` / `parallel_extract` — richer synthesis or URL-bound extraction. Slow.
- WebSearch/WebFetch — great for discovery and list building.

## Provider mix — run these in parallel, not sequentially

Don't pick one — run several from the appropriate row simultaneously:

| Objective | Run all of these in parallel | Add if coverage is thin |
|---|---|---|
| Discovery/search | `google_search_google_search` + `exa_search` + `apollo_search_people` | `crustdata_people_search`, `parallel_search` |
| Company list building | `exa_search` (or `exa_company_search`) + `crustdata_companydb_search` | `parallel_search`, `google_search_google_search` |
| Profile/company matching | `hunter_people_find` + `apollo_people_match` + `deepline_native_enrich_contact` | `crustdata_person_enrichment` |
| Website evidence + signal extraction | `exa_research` + `parallel_extract` | — |
| LinkedIn scraping | `apify` actors (by far the best) | direct web search tools |
| WebSearch/WebFetch | native tools, great to try out. 

- Use Apify when the task is linkedin-related scraping (likes on a post, posts, people at a company) and actor-level input needs control.
- For lead/account lists > 200, the web search tools generally fall short, try to use apollo, crust, hunter, etc enrichment and search providers. Or web scraping with the users assistance.

## Sample calls by provider

### Google Search

**Query structuring:**
- `site:` scoping to an authoritative domain is the highest-signal pattern — use it whenever you know where the data lives.
  - `site:ycombinator.com` — YC company/job data. Great for YC-specific queries (job listings by role, batch info, funding stage).
  - `site:crunchbase.com` — funding and firmographic lookup.
  - `site:linkedin.com/company` — indexes company **tagline/description only**, not employee data. Useful for finding companies by what they *are* (e.g. a keyword in their description), not by employee titles or funding attributes. Multiple exact-phrase filters (e.g. `"Series B" "Y Combinator"`) return 0 results since those strings don't appear in company descriptions.
  - `site:linkedin.com` (broad) — also surfaces **posts** (`/posts/...`). Useful for signal extraction (who's discussing a topic).
- Keyword soup without `site:` = noisy. Expect Reddit, newsletters, LinkedIn profiles, tangentially related content.
- Use quoted phrases for exact match: `"Series B"`, `"GTM engineer"`. Combine with `site:` for high precision.

```bash
# YC job listings for a specific role — very high precision
deepline tools execute google_search_google_search --payload '{"query":"site:ycombinator.com \"GTM engineer\" \"Series B\"","num":10}'

# Company LinkedIn URL discovery (search without site: scope, then extract)
deepline tools execute google_search_google_search --payload '{"query":"\"{{Company}}\" site:linkedin.com/company","num":3}'
```

### Apollo (people search, preview vs paid)

```bash
deepline tools get apollo_search_people
deepline tools get apollo_people_search_paid
```

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with 'people_search=apollo_search_people:{"person_titles":["VP Sales"],"q_keywords":"{{Company}}","include_similar_titles":true,"per_page":1,"page":1}'
```

Note: `apollo_search_people` maps to Apollo `mixed_people/api_search` (preview, no Apollo credits, obfuscated names/contact gaps). `apollo_people_search_paid` maps to Apollo `mixed_people/search` (paid). Company-targeted `apollo_people_search` requires `q_organization_domains_list` or `organization_ids` — avoid name-only keyword targeting.

**Apollo is unreliable for job posting signals.** The `q_organization_job_titles` and `organization_job_posted_at_range` filters exist but return sparse, inconsistent results — Apollo's job data is not a live feed. For "actively hiring for X" signals, prefer Exa/Google search targeting careers pages, or Apify LinkedIn Jobs scrapers.

### CrustData (company + person search, autocomplete)

**Always read the [crustdata playbook](provider-playbooks/crustdata.md) before building filter payloads if considering crust. .** Filter field names, valid enum values, and operator behavior are non-obvious — guessing wastes rounds. In particular: run `crustdata_companydb_autocomplete` for any field where you don't know the exact canonical value (industries, funding round types, regions, etc.). Autocomplete requires a non-empty `query` string (at least 1 character). Also note: `employee_metrics.latest_count` is valid for `sorts` but NOT as a `filter_type` — use `employee_count_range` (string enum) for headcount filters.

CrustData has structured filters. Use autocomplete to discover canonical values before search.

**Operators**: `(.)` = fuzzy contains (default), `[.]` = substring, `=`, `!=`, `in`, `not_in`, `>`, `<`, `=>`, `=<`.

For investor/funding signals, `deepline tools search investor` should route you directly to `crustdata_companydb_search` with field matches such as `crunchbase_investors` and `tracxn_investors`. Use those exact field names in payloads.

```bash
deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"linkedin_industries","query":"software","limit":5}'
```

```bash
deepline tools execute crustdata_companydb_search --payload '{"filters":[{"filter_type":"linkedin_industries","type":"(.)","value":"software"},{"filter_type":"hq_country","type":"=","value":"USA"}],"limit":5}'
```

```bash
deepline enrich --input accounts.csv --in-place --rows 0:1 \
  --with 'company_lookup=crustdata_companydb_autocomplete:{"field":"company_name","query":"{{Company}}","limit":1}'
```

### People Data Labs

**PDL is expensive — use it as a last resort.** Exhaust Exa, Google, Apollo, and Crustdata first. Only reach for PDL when other providers have clearly failed to return coverage.

**Shell quoting with PDL SQL:** PDL takes a raw SQL string. Avoid inline single-quote escaping in bash — it breaks silently. Instead write the payload to a temp file and pass it with `--payload-file`, or use a bash heredoc with `$()`:

```bash
PAYLOAD=$(cat <<'EOF'
{"sql": "SELECT * FROM company WHERE industry = 'financial services' AND location.country = 'united states' AND size IN ('51-200','201-500') AND latest_funding_stage IN ('series_a','series_b')", "size": 20}
EOF
)
deepline tools execute peopledatalabs_company_search --payload "$PAYLOAD" --json
```

```bash
deepline tools get peopledatalabs_person_search
```

### Parallel (managed research)

**When to use:** Good for broad discovery when you don't have a strong prior on which domains hold the data. Lower precision than domain-scoped Exa/Google but finds things others miss (e.g. company blogs, press releases, niche directories). Use in parallel with scoped searches, not instead of them. Set `max_chars_total` > 10000 for more than ~5 results.

```bash
deepline tools execute parallel_search --payload '{"mode":"agentic","objective":"Find recent hiring and launch signals for OpenAI","max_results":5,"excerpts":{"max_chars_per_result":1200,"max_chars_total":12000}}'
```

```bash
deepline tools execute parallel_extract --payload '{"urls":["https://openai.com/research/index/release/"],"objective":"Extract key product launch signal, release summary, and source evidence","full_content":true}'
```

```bash
deepline tools execute parallel_run_task --payload '{"processor":"lite-fast","input":"Summarize key GTM signals for OpenAI from recent public web sources in 3 bullets."}'
```

Use [src/lib/integrations/parallel/agent-guidance.md](../../src/lib/integrations/parallel/agent-guidance.md) for operator details.

### Exa (search, answer, research)

Exa is a semantic web index — it finds pages by meaning, not just keywords. Structure queries accordingly.

**Query structuring rules:**

- Write queries as natural-language descriptions of what you want to find, not keyword soup. Exa performs semantic matching.
  - Bad: `"SaaS B2B sales tools 2025"`
  - Good: `"B2B SaaS companies that sell sales automation tools"`
- Use `type` to control search strategy:
  - `fast` — keyword-like match. Fast but low precision for concept-driven queries — avoid for GTM discovery.
  - `neural` — semantic similarity. Best for concept-driven queries. Default to this.
  - `deep` — combines multiple strategies; use with `additionalQueries` for broad topic coverage.
  - `auto` (default) — Exa picks the best strategy.
- `startPublishedDate` / `endPublishedDate` — constrain to a time window (ISO date-time). Use for recency-sensitive signals (hiring, funding, launches).
- `contents` — control what you get back:
  - `text: true` for full page text; `{ maxCharacters: 2000 }` for truncated.
  - `highlights: { numSentences: 3, highlightsPerUrl: 2 }` for snippet extraction.
  - `summary: { query: "What does this company do?" }` for LLM-generated summaries per result.
- `context: { maxCharacters: 10000 }` — returns a combined context string from all results. Useful when feeding results directly into `call_ai`.

**Critical: `category` vs `includeDomains` — they are NOT interchangeable:**

- `category: "company"` / `"people"` searches Exa's **dedicated entity index** (LinkedIn-derived company/person profiles). It matches against company *descriptions*, not attributes like funding stage or employee titles. **`includeDomains`, `excludeDomains`, `includeText`, and `excludeText` are NOT supported with `category`** — using them throws an error.
  - Use `category:"company"` for: "companies that *are* X" (concept-driven: "AI sales tools companies", "fintech startups")
  - Do NOT use for: "companies that *have* X" (attribute-based: "companies with GTM engineers", "Series B companies") — it will match company descriptions that mention the phrase, not the underlying attribute

  - You may cross reference multiple queries / this problem is more agentic in nature. Finding proxies and then filtering down via deepline enrich is also a good approach here. 
- `includeDomains` / `excludeDomains` — scope a **regular web search** (no category) to specific sites. This is the right pattern when you know where the data lives (job boards, YC site, news sources).
  - Use for job listing discovery: `includeDomains: ["ycombinator.com", "greenhouse.io", "lever.co"]`
  - Use to avoid aggregator noise: `excludeDomains: ["wellfound.com", "builtinnyc.com"]`

**"Companies that hire X role" pattern — use `includeDomains` on job boards, NOT `category:"company"`:**
```bash
# Find YC companies hiring GTM engineers — scope to YC job board
deepline tools execute exa_search --payload '{"query":"GTM engineer job opening at Y Combinator startup","numResults":15,"type":"neural","includeDomains":["ycombinator.com"],"contents":{"highlights":{"numSentences":2,"highlightsPerUrl":1}}}'
```

**Watch out for duplicate-heavy results.** Exa often returns multiple results for the same company. Mitigate by: (a) using `additionalQueries` with varied phrasings, (b) post-processing to deduplicate by domain, (c) using `excludeDomains` (only valid without `category`) to block aggregator sites.

**Tool selection:**

- `exa_search` — general-purpose semantic search. Start here.
- `exa_company_search` — shorthand for `exa_search` with `category: "company"`. Use for concept-based company discovery only.
- `exa_people_search` — shorthand for `exa_search` with `category: "people"`.
- `exa_answer` — cited answer synthesis. **Low recall by design** — returns only 2-5 well-verified results. Use for fact-checking a specific known entity, NOT for "find me a list of" discovery queries.
- `exa_research` — multi-source deep research. Slower but thorough. Supports `outputSchema`. Use `exa-research-fast` model for speed, `exa-research-pro` for depth.

```bash
# Concept-based company search (category OK here)
deepline tools execute exa_search --payload '{"query":"B2B SaaS companies building AI-powered sales tools","category":"company","numResults":10,"type":"neural","contents":{"summary":{"query":"What does this company do and what funding stage are they?"}}}'
```

```bash
# Attribute + domain-scoped search (NO category — use includeDomains instead)
deepline tools execute exa_search --payload '{"query":"Series B fintech startups in New York","type":"neural","additionalQueries":["fintech companies Series B NYC","New York financial technology startups raised Series B"],"numResults":20,"includeDomains":["techcrunch.com","crunchbase.com"],"startPublishedDate":"2024-01-01T00:00:00Z","contents":{"summary":{"query":"What does this company do and what stage are they?"}}}'
```

```bash
# exa_answer: fact-check a specific company, not list discovery
deepline tools execute exa_answer --payload '{"query":"What are the top hiring signals for Stripe in the last 6 months?","text":true}'
```

```bash
deepline tools execute exa_research --payload '{"instructions":"Research the competitive landscape for AI-powered CRM tools. Identify the top 5 companies, their funding, and key differentiators.","model":"exa-research-fast"}'
```

## Parallel web research and extraction

Use the dedicated integration guide for operator details and examples:
[src/lib/integrations/parallel/agent-guidance.md](../../src/lib/integrations/parallel/agent-guidance.md)

Short rule:
- When the task is managed web research/extraction (including synthesis), prefer `parallel_search` / `parallel_extract` / `parallel_run_task` with a real one-row pilot first.

## Parallel execution and multi-step lead list building

**This is the default execution pattern, not a fallback.** Always run multiple search paths simultaneously and merge results.

Fire searches across multiple providers at the same time — don't wait for one to finish before trying the next.

**Parallel search pattern:**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Run multiple providers simultaneously — each writes to its own column
deepline enrich --input seed.csv --in-place --rows 0:2 \
  --with 'apollo_hits=apollo_search_people:{"person_titles":["CTO","VP Engineering"],"q_keywords":"{{Company}}","per_page":3}' \
  --with 'crust_hits=crustdata_companydb_search:{"filters":[{"filter_type":"company_name","type":"(.)","value":"{{Company}}"}],"limit":3}' \
  --with 'exa_hits=exa_search:{"query":"{{Company}} AI healthcare","category":"company","numResults":3,"type":"fast"}'
```

All `--with` columns in a single `deepline enrich` call execute in parallel. Use this to fan out across providers.

**Multi-step lead list building (hard queries):**

When a single search pass isn't enough, break the task into stages:

1. **Seed stage** — cast a wide net. Run broad searches across 2-3 providers to build a raw candidate list.
2. **Refine stage** — enrich the seed list with additional signals (company size, funding, tech stack) to filter down.
3. **Validate stage** — deduplicate, cross-reference across providers, and score.

Example flow for "Find 50 Series B AI companies selling to healthcare in the US":

```bash
#!/usr/bin/env bash
set -euo pipefail

# Stage 1: Seed from multiple sources in parallel
deepline enrich --input empty_50.csv --in-place \
  --with 'exa=exa_search:{"query":"Series B AI companies selling to healthcare in the United States","category":"company","numResults":50,"type":"deep","additionalQueries":["AI healthcare startups Series B funding USA"],"contents":{"summary":{"query":"Company name, what they do, and funding stage"}}}' \
  --with 'crust=crustdata_companydb_search:{"filters":[{"filter_type":"linkedin_industries","type":"(.)","value":"healthcare"},{"filter_type":"hq_country","type":"=","value":"USA"},{"filter_type":"last_funding_round_type","type":"in","value":["Series B"]}],"limit":50}'

# Stage 2: Take the merged seed list, enrich with Apollo for people
deepline enrich --input seed_merged.csv --in-place --rows 0:4 \
  --with 'contacts=apollo_search_people:{"q_organization_domains_list":["{{domain}}"],"person_seniorities":["c_suite","vp","director"],"per_page":5}'

# Stage 3: Validate emails
deepline enrich --input seed_merged.csv --in-place --rows 0:4 \
  --with 'email_valid=leadmagic_email_validation:{"email":"{{email}}"}'
```

**Always go multi-step when:**
- The user wants a specific count (e.g. "find me 50 companies") — single providers rarely have enough coverage alone.
- The query combines multiple constraints (industry + funding stage + geography + tech stack).
- Initial results from one provider have low hit rates — immediately fan out to others.
- The user needs both account-level and contact-level data — that's inherently two stages.
- **Provider returns poor-quality or nonsensical results** — retry with different params or switch providers immediately. Don't waste turns debugging.

**Provider response quality — validate and fallback:**
Providers often return garbage, nonsensical, or irrelevant data. Don't assume responses are valid.

- If a provider returns empty, sparse, or obviously wrong results (wrong company names, wrong industries, duplicate noise, irrelevant hits): treat it as a miss and fan out to other providers. Don't reason about why — just retry elsewhere.
- Cross-reference across providers when coalescing — prefer the provider that returned consistent, field-rich data. Discard obviously bad rows.
- When responses are suspicious, try different params (broader query, different filters) or a different provider entirely. The cost of an extra search is low; the cost of downstream garbage is high.

Default: parallel. Always go parallel. Use sub-agents for independent workstreams when available.

**Deduplication and coalescing:** After merging results from multiple providers, deduplicate by domain or LinkedIn URL. Coalesce fields: pick the richest non-null value per field from parallel provider outputs. Use `run_javascript` inside `deepline enrich` — see [enrich-waterfall.md](enrich-waterfall.md) "Coalescing and cleaning" for patterns. Never leave raw provider columns as final output; always add a coalesce step.

## Provider search filters reference

All providers support structured filters. This section is auto-generated from provider input schemas.

### Apollo People Search (preview)

`apollo_search_people`

Apollo people API search input.

  - `page` (number, optional) — Page number (1-500).
  - `per_page` (number, optional) — Results per page (1-100).
  - `person_titles` (string[], optional) — Job titles to match.
  - `include_similar_titles` (boolean, optional) — Include similar titles for person_titles matches.
  - `person_seniorities` (("owner" | "founder" | "c_suite" | "partner" | "vp" | "head" | "director" | "manager" | "senior" | "entry" | "intern")[], optional) — Seniority filter values defined by Apollo.
  - `person_locations` (string[], optional) — Person locations.
  - `organization_locations` (string[], optional) — Organization HQ locations.
  - `organization_num_employees_ranges` (string[], optional) — Employee ranges like '1,10', '11,50', '51,200'.
  - `q_organization_domains_list` (string[], optional) — Organization domains to include.
  - `contact_email_status` (string[], optional) — Email status values (e.g., 'verified', 'guessed').
  - `organization_ids` (string[], optional) — Apollo organization IDs to include.
  - `q_keywords` (string, optional) — Keyword query across person and organization fields.
  - `revenue_range.min` (number, optional) — Minimum numeric value.
  - `revenue_range.max` (number, optional) — Maximum numeric value.
  - `currently_using_any_of_technology_uids` (string[], optional) — Organizations using ANY of these technology UIDs.
  - `currently_using_all_of_technology_uids` (string[], optional) — Organizations using ALL of these technology UIDs.
  - `currently_not_using_any_of_technology_uids` (string[], optional) — Exclude organizations using ANY of these technology UIDs.
  - `q_organization_job_titles` (string[], optional) — Organizations hiring for these job titles.
  - `organization_job_locations` (string[], optional) — Organizations hiring in these locations.
  - `organization_num_jobs_range.min` (number, optional) — Minimum integer value.
  - `organization_num_jobs_range.max` (number, optional) — Maximum integer value.
  - `organization_job_posted_at_range.min` (string, optional) — Minimum date/time (ISO 8601).
  - `organization_job_posted_at_range.max` (string, optional) — Maximum date/time (ISO 8601).

### Apollo People Search (paid)

`apollo_people_search_paid`

Apollo people API search input.

  - `page` (number, optional) — Page number (1-500).
  - `per_page` (number, optional) — Results per page (1-100).
  - `person_titles` (string[], optional) — Job titles to match.
  - `include_similar_titles` (boolean, optional) — Include similar titles for person_titles matches.
  - `person_seniorities` (("owner" | "founder" | "c_suite" | "partner" | "vp" | "head" | "director" | "manager" | "senior" | "entry" | "intern")[], optional) — Seniority filter values defined by Apollo.
  - `person_locations` (string[], optional) — Person locations.
  - `organization_locations` (string[], optional) — Organization HQ locations.
  - `organization_num_employees_ranges` (string[], optional) — Employee ranges like '1,10', '11,50', '51,200'.
  - `q_organization_domains_list` (string[], optional) — Organization domains to include.
  - `contact_email_status` (string[], optional) — Email status values (e.g., 'verified', 'guessed').
  - `organization_ids` (string[], optional) — Apollo organization IDs to include.
  - `q_keywords` (string, optional) — Keyword query across person and organization fields.
  - `revenue_range.min` (number, optional) — Minimum numeric value.
  - `revenue_range.max` (number, optional) — Maximum numeric value.
  - `currently_using_any_of_technology_uids` (string[], optional) — Organizations using ANY of these technology UIDs.
  - `currently_using_all_of_technology_uids` (string[], optional) — Organizations using ALL of these technology UIDs.
  - `currently_not_using_any_of_technology_uids` (string[], optional) — Exclude organizations using ANY of these technology UIDs.
  - `q_organization_job_titles` (string[], optional) — Organizations hiring for these job titles.
  - `organization_job_locations` (string[], optional) — Organizations hiring in these locations.
  - `organization_num_jobs_range.min` (number, optional) — Minimum integer value.
  - `organization_num_jobs_range.max` (number, optional) — Maximum integer value.
  - `organization_job_posted_at_range.min` (string, optional) — Minimum date/time (ISO 8601).
  - `organization_job_posted_at_range.max` (string, optional) — Maximum date/time (ISO 8601).

### Apollo People Match

`apollo_people_match`

Apollo people match input. Supports id-based matching. `reveal_personal_emails` defaults to true.

  - `name` (string, optional) — Person's full name.
  - `email` (string, optional) — Person's email address.
  - `hashed_email` (string, optional) — Person's MD5-hashed email address.
  - `first_name` (string, optional) — Person's first name.
  - `last_name` (string, optional) — Person's last name.
  - `linkedin_url` (string, optional) — Person's LinkedIn profile URL.
  - `domain` (string, optional) — Company domain (e.g., 'apollo.io').
  - `organization_name` (string, optional) — Employer/company name.
  - `id` (string, optional) — Apollo person ID from a prior lookup. For best reliability, pair `id` with `first_name` (or email/linkedin_url).
  - `reveal_personal_emails` (boolean, optional) — When true, request personal email reveal (credit-consuming).

### Apollo Company Search

`apollo_company_search`

Apollo company API search input.

  - `page` (number, optional) — Page number (1-500).
  - `per_page` (number, optional) — Results per page (1-100).
  - `q_organization_domains_list` (string[], optional) — Organization domains to include.
  - `q_organization_name` (string, optional) — Organization name keyword search.
  - `organization_ids` (string[], optional) — Apollo organization IDs to include.
  - `organization_num_employees_ranges` (string[], optional) — Employee ranges like '1,10', '11,50', '51,200'.
  - `organization_locations` (string[], optional) — Organization HQ locations to include.
  - `organization_not_locations` (string[], optional) — Organization HQ locations to exclude.
  - `q_organization_keyword_tags` (string[], optional) — Organization keyword tags.
  - `revenue_range.min` (number, optional) — Minimum numeric value.
  - `revenue_range.max` (number, optional) — Maximum numeric value.
  - `currently_using_any_of_technology_uids` (string[], optional) — Organizations using ANY of these technology UIDs.
  - `latest_funding_amount_range.min` (number, optional) — Minimum numeric value.
  - `latest_funding_amount_range.max` (number, optional) — Maximum numeric value.
  - `total_funding_range.min` (number, optional) — Minimum numeric value.
  - `total_funding_range.max` (number, optional) — Maximum numeric value.
  - `latest_funding_date_range.min` (string, optional) — Minimum date/time (ISO 8601).
  - `latest_funding_date_range.max` (string, optional) — Maximum date/time (ISO 8601).
  - `q_organization_job_titles` (string[], optional) — Organizations hiring for these job titles.
  - `organization_job_locations` (string[], optional) — Organizations hiring in these locations.
  - `organization_num_jobs_range.min` (number, optional) — Minimum integer value.
  - `organization_num_jobs_range.max` (number, optional) — Maximum integer value.
  - `organization_job_posted_at_range.min` (string, optional) — Minimum date/time (ISO 8601).
  - `organization_job_posted_at_range.max` (string, optional) — Maximum date/time (ISO 8601).

### CrustData Company Search

`crustdata_companydb_search`

Searches CompanyDB using /screener/companydb/search with filters.

  - `filters` (array, **required**) — Array of filter conditions (AND-combined). Each: {filter_type, type, value} or {filter_name, type, value}. filter_name is syntactic sugar for filter_type (e.g. company_investors → crunchbase_investors, company_funding_stage → last_funding_round_type). Single object is accepted. Nested {op,conditions} groups supported for OR logic.
  - `filters[]` (object, **required**)
  - `filters[].filter_type` ("acquisition_status" | "company_name" | "company_type" | "company_website_domain" | "competitor_ids" | "competitor_websites" | "crunchbase_categories" | "crunchbase_investors" | "crunchbase_total_investment_usd" | "employee_count_range" | "employee_metrics.growth_12m" | "employee_metrics.growth_12m_percent" | "employee_metrics.growth_6m_percent" | "employee_metrics.latest_count" | "estimated_revenue_higher_bound_usd" | "estimated_revenue_lower_bound_usd" | "follower_metrics.growth_6m_percent" | "follower_metrics.latest_count" | "hq_country" | "hq_location" | "ipo_date" | "largest_headcount_country" | "last_funding_date" | "last_funding_round_type" | "linkedin_id" | "linkedin_industries" | "linkedin_profile_url" | "markets" | "region" | "tracxn_investors" | "year_founded", optional) — Field to filter on. Accepts filter_name as alias. Key mappings: company_investors → crunchbase_investors, company_funding_stage → last_funding_round_type, funding stage/round → last_funding_round_type, headcount/size → employee_count_range or employee_metrics.latest_count, industry → linkedin_industries, location → hq_country (ISO alpha-3) or hq_location or region, revenue → estimated_revenue_lower_bound_usd / estimated_revenue_higher_bound_usd, funding amount → crunchbase_total_investment_usd, domain → company_website_domain.
  - `filters[].type` ("=" | "!=" | "in" | "not_in" | ">" | "<" | "=>" | "=<" | "(.)" | "[.]", optional) — Operator: =, !=, in, not_in, >, <, =>, =<, (.) fuzzy contains, [.] substring.
  - `filters[].value` (string | number | boolean | (string | number | boolean)[], optional) — Filter value. When unsure of exact values for a field, call crustdata_companydb_autocomplete first (free, no credits): e.g. deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"last_funding_round_type","query":"series","limit":10}' --json. hq_country uses ISO 3166-1 alpha-3 codes (USA, GBR, CAN).
  - `filters[].value[]` (string | number | boolean, optional)
  - `filters[].op` ("and" | "or", optional) — Logical operator for conditions.
  - `filters[].conditions` (array, optional) — Nested filter conditions.
  - `filters[].conditions[]` (object, optional)
  - `filters[].conditions[].filter_type` ("acquisition_status" | "company_name" | "company_type" | "company_website_domain" | "competitor_ids" | "competitor_websites" | "crunchbase_categories" | "crunchbase_investors" | "crunchbase_total_investment_usd" | "employee_count_range" | "employee_metrics.growth_12m" | "employee_metrics.growth_12m_percent" | "employee_metrics.growth_6m_percent" | "employee_metrics.latest_count" | "estimated_revenue_higher_bound_usd" | "estimated_revenue_lower_bound_usd" | "follower_metrics.growth_6m_percent" | "follower_metrics.latest_count" | "hq_country" | "hq_location" | "ipo_date" | "largest_headcount_country" | "last_funding_date" | "last_funding_round_type" | "linkedin_id" | "linkedin_industries" | "linkedin_profile_url" | "markets" | "region" | "tracxn_investors" | "year_founded", optional) — Field to filter on. Accepts filter_name as alias. Key mappings: company_investors → crunchbase_investors, company_funding_stage → last_funding_round_type, funding stage/round → last_funding_round_type, headcount/size → employee_count_range or employee_metrics.latest_count, industry → linkedin_industries, location → hq_country (ISO alpha-3) or hq_location or region, revenue → estimated_revenue_lower_bound_usd / estimated_revenue_higher_bound_usd, funding amount → crunchbase_total_investment_usd, domain → company_website_domain.
  - `filters[].conditions[].type` ("=" | "!=" | "in" | "not_in" | ">" | "<" | "=>" | "=<" | "(.)" | "[.]", optional) — Operator: =, !=, in, not_in, >, <, =>, =<, (.) fuzzy contains, [.] substring.
  - `filters[].conditions[].value` (string | number | boolean | (string | number | boolean)[], optional) — Filter value. When unsure of exact values for a field, call crustdata_companydb_autocomplete first (free, no credits): e.g. deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"last_funding_round_type","query":"series","limit":10}' --json. hq_country uses ISO 3166-1 alpha-3 codes (USA, GBR, CAN).
  - `filters[].conditions[].op` ("and" | "or", optional) — Logical operator for conditions.
  - `filters[].conditions[].conditions` (array, optional) — Nested filter conditions.
  - `limit` (number, optional)
  - `cursor` (string, optional) — Pagination cursor.
  - `sorts` (array, optional) — Sort criteria array.
  - `sorts[].column` (string, optional) — Field to sort by (e.g. employee_metrics.latest_count).
  - `sorts[].order` ("asc" | "desc", optional) — Sort order: asc or desc.

### CrustData Person Search

`crustdata_persondb_search`

Searches PersonDB using /screener/persondb/search with filters.

  - `filters` (array, **required**) — Array of filter conditions (AND-combined). Each: {filter_type, type, value} or {filter_name, type, value}. filter_name is syntactic sugar for filter_type. Single object is accepted. Nested {op,conditions} groups supported for OR logic.
  - `filters[]` (object, **required**)
  - `filters[].filter_type` ("current_employers.company_website_domain" | "current_employers.seniority_level" | "current_employers.title" | "headline" | "num_of_connections" | "region" | "years_of_experience_raw", optional) — Field to filter on. Key mappings: job title → current_employers.title, seniority → current_employers.seniority_level, company/employer → current_employers.company_website_domain, location → region, experience → years_of_experience_raw, bio/summary → headline, connections → num_of_connections.
  - `filters[].type` ("=" | "!=" | "in" | "not_in" | ">" | "<" | "=>" | "=<" | "(.)" | "[.]" | "geo_distance", optional) — Operator: =, !=, in, not_in, >, <, =>, =<, (.) fuzzy contains, [.] substring, geo_distance (region only).
  - `filters[].value` (string | number | boolean | (string | number | boolean)[] | object, optional) — Filter value (or geo_distance object for region). When unsure of exact values for a field, call crustdata_persondb_autocomplete first (free, no credits): e.g. deepline tools execute crustdata_persondb_autocomplete --payload '{"field":"current_employers.title","query":"engineer","limit":10}' --json.
  - `filters[].value[]` (string | number | boolean, optional)
  - `filters[].value.location` (string, optional)
  - `filters[].value.distance` (number, optional)
  - `filters[].value.unit` ("km" | "mi" | "miles" | "m" | "meters" | "ft" | "feet", optional)
  - `filters[].op` ("and" | "or", optional) — Logical operator for conditions.
  - `filters[].conditions` (array, optional) — Nested filter conditions.
  - `filters[].conditions[]` (object, optional)
  - `filters[].conditions[].filter_type` ("current_employers.company_website_domain" | "current_employers.seniority_level" | "current_employers.title" | "headline" | "num_of_connections" | "region" | "years_of_experience_raw", optional) — Field to filter on. Key mappings: job title → current_employers.title, seniority → current_employers.seniority_level, company/employer → current_employers.company_website_domain, location → region, experience → years_of_experience_raw, bio/summary → headline, connections → num_of_connections.
  - `filters[].conditions[].type` ("=" | "!=" | "in" | "not_in" | ">" | "<" | "=>" | "=<" | "(.)" | "[.]" | "geo_distance", optional) — Operator: =, !=, in, not_in, >, <, =>, =<, (.) fuzzy contains, [.] substring, geo_distance (region only).
  - `filters[].conditions[].value` (string | number | boolean | (string | number | boolean)[] | object, optional) — Filter value (or geo_distance object for region). When unsure of exact values for a field, call crustdata_persondb_autocomplete first (free, no credits): e.g. deepline tools execute crustdata_persondb_autocomplete --payload '{"field":"current_employers.title","query":"engineer","limit":10}' --json.
  - `filters[].conditions[].op` ("and" | "or", optional) — Logical operator for conditions.
  - `filters[].conditions[].conditions` (array, optional) — Nested filter conditions.
  - `limit` (number, optional)
  - `cursor` (string, optional) — Pagination cursor.
  - `sorts` (array, optional) — Sort criteria array.
  - `sorts[].column` (string, optional) — Field to sort by (e.g. employee_metrics.latest_count).
  - `sorts[].order` ("asc" | "desc", optional) — Sort order: asc or desc.
  - `postProcessing.exclude_profiles` (string[], optional) — Exclude specific profile IDs.
  - `postProcessing.exclude_names` (string[], optional) — Exclude matching names.
  - `preview` (boolean, optional) — Enable preview mode.

### CrustData Company Autocomplete

`crustdata_companydb_autocomplete`

Fetches exact filter values using /screener/companydb/autocomplete. Free, no credits consumed.

  - `field` ("acquisition_status" | "company_name" | "company_type" | "company_website_domain" | "competitor_ids" | "competitor_websites" | "crunchbase_categories" | "crunchbase_investors" | "crunchbase_total_investment_usd" | "employee_count_range" | "employee_metrics.growth_12m" | "employee_metrics.growth_12m_percent" | "employee_metrics.growth_6m_percent" | "employee_metrics.latest_count" | "estimated_revenue_higher_bound_usd" | "estimated_revenue_lower_bound_usd" | "follower_metrics.growth_6m_percent" | "follower_metrics.latest_count" | "hq_country" | "hq_location" | "ipo_date" | "largest_headcount_country" | "last_funding_date" | "last_funding_round_type" | "linkedin_id" | "linkedin_industries" | "linkedin_profile_url" | "markets" | "region" | "tracxn_investors" | "year_founded", **required**) — Field name to autocomplete. Must be one of: acquisition_status, company_name, company_type, company_website_domain, competitor_ids, competitor_websites, crunchbase_categories, crunchbase_investors, crunchbase_total_investment_usd, employee_count_range, employee_metrics.growth_12m, employee_metrics.growth_12m_percent, employee_metrics.growth_6m_percent, employee_metrics.latest_count, estimated_revenue_higher_bound_usd, estimated_revenue_lower_bound_usd, follower_metrics.growth_6m_percent, follower_metrics.latest_count, hq_country, hq_location, ipo_date, largest_headcount_country, last_funding_date, last_funding_round_type, linkedin_id, linkedin_industries, linkedin_profile_url, markets, region, tracxn_investors, year_founded. Key mappings: funding stage/round → last_funding_round_type, headcount/size → employee_count_range, industry → linkedin_industries, location → hq_country (ISO alpha-3) or hq_location. Note: hq_country uses 3-letter ISO codes (USA, GBR, CAN), not country names.
  - `query` (string, **required**) — Partial text to match. For hq_country, use ISO code patterns (e.g. "US", "USA", "GBR") rather than country names.
  - `limit` (number, optional)

### CrustData Person Autocomplete

`crustdata_persondb_autocomplete`

Fetches exact filter values using /screener/persondb/autocomplete. Free, no credits consumed.

  - `field` ("current_employers.company_website_domain" | "current_employers.seniority_level" | "current_employers.title" | "headline" | "num_of_connections" | "region" | "years_of_experience_raw", **required**) — Field name to autocomplete. Must be one of: current_employers.company_website_domain, current_employers.seniority_level, current_employers.title, headline, num_of_connections, region, years_of_experience_raw. Key mappings: job title → current_employers.title, seniority → current_employers.seniority_level, location → region, company/employer → current_employers.company_website_domain, experience → years_of_experience_raw, bio/summary → headline.
  - `query` (string, **required**) — Partial text to match. Examples: "san franci" for region, "Eng" for job titles.
  - `limit` (number, optional)

### CrustData People Search

`crustdata_people_search`

Searches people at a company via PersonDB using derived filters.

  - `companyDomain` (string, **required**) — Company website domain to match.
  - `titleKeywords` (string | string[], **required**) — Title keyword(s) to match.
  - `profileKeywords` (string | string[], optional) — Profile headline keyword(s).
  - `country` (string, optional) — Country or region filter.
  - `seniority` (string | string[], optional) — Seniority level(s). Canonical values: CXO, Vice President, Director, Manager, Senior, Entry, Training, Owner, Partner, Unpaid. Common aliases (c-suite, vp, founder, junior, intern) are auto-normalized.
  - `fuzzyTitle` (boolean, optional) — Use fuzzy title matching (default true).
  - `limit` (number, optional)

### PDL Person Search

`peopledatalabs_person_search`

People Data Labs person search input.

  - `query` (record, optional) — Elasticsearch-style query. Use this OR `sql`, not both. If you are unsure about field names, prefer `sql` with known fields.
  - `sql` (string, optional) — SQL must be in the form `SELECT * FROM person WHERE ...`. Use single quotes for string literals (e.g., name='people data labs'). You must use valid PDL field names and nested subfields (e.g., `experience.title.name`, not `experience`). Column selection and LIMIT are ignored by PDL; always use `SELECT *`. Example: SELECT * FROM person WHERE location_country='mexico' AND job_title_role='health' AND phone_numbers IS NOT NULL.
  - `size` (number, optional) — Number of records to return (1-100).
  - `scroll_token` (string, optional) — Token for retrieving the next page of results.
  - `dataset` (string, optional) — Optional dataset selector supported by PDL.
  - `titlecase` (boolean, optional) — Normalize output text casing.
  - `data_include` (string, optional) — Avoid using data_include unless you want partial fields only.
  - `pretty` (boolean, optional) — Pretty-print response JSON.

### PDL Company Search

`peopledatalabs_company_search`

People Data Labs company search input.

  - `query` (record, optional) — Elasticsearch-style query. Use this OR `sql`, not both. If you are unsure about field names, prefer `sql` with known fields.
  - `sql` (string, optional) — SQL must be in the form `SELECT * FROM company WHERE ...`. Use single quotes for string literals. You must use valid PDL field names and nested subfields (e.g., `location.country`, not `location`). Column selection and LIMIT are ignored by PDL; always use `SELECT *`. Example: SELECT * FROM company WHERE location_country='mexico' AND phone IS NOT NULL.
  - `size` (number, optional) — Number of records to return (1-100).
  - `scroll_token` (string, optional) — Token for retrieving the next page of results.
  - `titlecase` (boolean, optional) — Normalize output text casing.
  - `data_include` (string, optional) — Avoid using data_include unless you want partial fields only.
  - `pretty` (boolean, optional) — Pretty-print response JSON.

### Exa Search

`exa_search`

Exa raw search input.

  - `query` (string, **required**) — The search query string.
  - `additionalQueries` (string[], optional) — Additional queries (used with type="deep" to expand coverage).
  - `type` ("auto" | "fast" | "deep" | "neural" | "instant", optional) — Search type (auto chooses the best strategy).
  - `category` ("company" | "people" | "news" | "research paper" | "tweet" | "personal site" | "financial report", optional) — Optional result category filter.
  - `numResults` (number, optional) — Number of results to return (max 100).
  - `includeDomains` (string[], optional) — Only include results from these domains.
  - `excludeDomains` (string[], optional) — Exclude results from these domains.
  - `startCrawlDate` (string, optional) — Only include links crawled after this ISO date-time.
  - `endCrawlDate` (string, optional) — Only include links crawled before this ISO date-time.
  - `startPublishedDate` (string, optional) — Only include links published after this ISO date-time.
  - `endPublishedDate` (string, optional) — Only include links published before this ISO date-time.
  - `includeText` (string[], optional) — Require these text snippets to appear in page content.
  - `excludeText` (string[], optional) — Exclude pages containing these text snippets.
  - `userLocation` (string, optional) — Two-letter ISO country code, e.g. "US".
  - `contents.text` (boolean | object, optional) — Text extraction settings.
  - `contents.text.maxCharacters` (number, optional) — Maximum characters for full page text (use to cap response size).
  - `contents.text.includeHtmlTags` (boolean, optional) — Include HTML tags in the returned text.
  - `contents.text.verbosity` ("compact" | "standard" | "full", optional) — Controls verbosity of extracted text.
  - `contents.text.includeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Only include content from these sections.
  - `contents.text.excludeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Exclude content from these sections.
  - `contents.highlights` (boolean | object, optional) — Highlight settings.
  - `contents.highlights.numSentences` (number, optional) — Number of sentences per highlight snippet.
  - `contents.highlights.highlightsPerUrl` (number, optional) — Number of highlight snippets per URL.
  - `contents.highlights.query` (string, optional) — Custom query to guide highlight selection.
  - `contents.highlights.maxCharacters` (number, optional) — Maximum characters returned for highlights.
  - `contents.summary.query` (string, optional) — Custom query for the summary.
  - `contents.summary.schema` (record, optional) — JSON Schema for structured summary output (validated).
  - `contents.livecrawl` ("never" | "fallback" | "preferred" | "always", optional) — Live crawl behavior (deprecated in Exa docs; prefer maxAgeHours).
  - `contents.livecrawlTimeout` (number, optional) — Live crawl timeout in milliseconds.
  - `contents.maxAgeHours` (number, optional) — Max age (hours) for cached content before live crawl.
  - `contents.subpages` (number, optional) — Number of subpages to crawl from each result.
  - `contents.subpageTarget` (string | string[], optional) — Subpage keyword(s) to target.
  - `contents.extras.links` (number, optional) — Number of links to return per result.
  - `contents.extras.imageLinks` (number, optional) — Number of image links to return per result.
  - `contents.context` (boolean | object, optional) — Combined context settings. Returns a single context string from all results.
  - `contents.context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `context` (boolean | object, optional)
  - `context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `moderation` (boolean, optional) — Enable content moderation (may reduce recall).

### Exa Company Search

`exa_company_search`

Exa company search input.

  - `query` (string, **required**)
  - `additionalQueries` (string[], optional) — Additional queries (used with type="deep" to expand coverage).
  - `type` ("auto" | "fast" | "deep" | "neural" | "instant", optional)
  - `numResults` (number, optional) — Number of results to return (max 100).
  - `includeDomains` (string[], optional)
  - `excludeDomains` (string[], optional) — Exclude results from these domains.
  - `userLocation` (string, optional) — Two-letter ISO country code, e.g. "US".
  - `contents.text` (boolean | object, optional) — Text extraction settings.
  - `contents.text.maxCharacters` (number, optional) — Maximum characters for full page text (use to cap response size).
  - `contents.text.includeHtmlTags` (boolean, optional) — Include HTML tags in the returned text.
  - `contents.text.verbosity` ("compact" | "standard" | "full", optional) — Controls verbosity of extracted text.
  - `contents.text.includeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Only include content from these sections.
  - `contents.text.excludeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Exclude content from these sections.
  - `contents.highlights` (boolean | object, optional) — Highlight settings.
  - `contents.highlights.numSentences` (number, optional) — Number of sentences per highlight snippet.
  - `contents.highlights.highlightsPerUrl` (number, optional) — Number of highlight snippets per URL.
  - `contents.highlights.query` (string, optional) — Custom query to guide highlight selection.
  - `contents.highlights.maxCharacters` (number, optional) — Maximum characters returned for highlights.
  - `contents.summary.query` (string, optional) — Custom query for the summary.
  - `contents.summary.schema` (record, optional) — JSON Schema for structured summary output (validated).
  - `contents.livecrawl` ("never" | "fallback" | "preferred" | "always", optional) — Live crawl behavior (deprecated in Exa docs; prefer maxAgeHours).
  - `contents.livecrawlTimeout` (number, optional) — Live crawl timeout in milliseconds.
  - `contents.maxAgeHours` (number, optional) — Max age (hours) for cached content before live crawl.
  - `contents.subpages` (number, optional) — Number of subpages to crawl from each result.
  - `contents.subpageTarget` (string | string[], optional) — Subpage keyword(s) to target.
  - `contents.extras.links` (number, optional) — Number of links to return per result.
  - `contents.extras.imageLinks` (number, optional) — Number of image links to return per result.
  - `contents.context` (boolean | object, optional) — Combined context settings. Returns a single context string from all results.
  - `contents.context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `context` (boolean | object, optional)
  - `context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `moderation` (boolean, optional) — Enable content moderation (may reduce recall).

### Exa People Search

`exa_people_search`

Exa people search input.

  - `query` (string, **required**)
  - `additionalQueries` (string[], optional) — Additional queries (used with type="deep" to expand coverage).
  - `type` ("auto" | "fast" | "deep" | "neural" | "instant", optional)
  - `numResults` (number, optional) — Number of results to return (max 100).
  - `includeDomains` (string[], optional)
  - `excludeDomains` (string[], optional) — Exclude results from these domains.
  - `userLocation` (string, optional) — Two-letter ISO country code, e.g. "US".
  - `contents.text` (boolean | object, optional) — Text extraction settings.
  - `contents.text.maxCharacters` (number, optional) — Maximum characters for full page text (use to cap response size).
  - `contents.text.includeHtmlTags` (boolean, optional) — Include HTML tags in the returned text.
  - `contents.text.verbosity` ("compact" | "standard" | "full", optional) — Controls verbosity of extracted text.
  - `contents.text.includeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Only include content from these sections.
  - `contents.text.excludeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Exclude content from these sections.
  - `contents.highlights` (boolean | object, optional) — Highlight settings.
  - `contents.highlights.numSentences` (number, optional) — Number of sentences per highlight snippet.
  - `contents.highlights.highlightsPerUrl` (number, optional) — Number of highlight snippets per URL.
  - `contents.highlights.query` (string, optional) — Custom query to guide highlight selection.
  - `contents.highlights.maxCharacters` (number, optional) — Maximum characters returned for highlights.
  - `contents.summary.query` (string, optional) — Custom query for the summary.
  - `contents.summary.schema` (record, optional) — JSON Schema for structured summary output (validated).
  - `contents.livecrawl` ("never" | "fallback" | "preferred" | "always", optional) — Live crawl behavior (deprecated in Exa docs; prefer maxAgeHours).
  - `contents.livecrawlTimeout` (number, optional) — Live crawl timeout in milliseconds.
  - `contents.maxAgeHours` (number, optional) — Max age (hours) for cached content before live crawl.
  - `contents.subpages` (number, optional) — Number of subpages to crawl from each result.
  - `contents.subpageTarget` (string | string[], optional) — Subpage keyword(s) to target.
  - `contents.extras.links` (number, optional) — Number of links to return per result.
  - `contents.extras.imageLinks` (number, optional) — Number of image links to return per result.
  - `contents.context` (boolean | object, optional) — Combined context settings. Returns a single context string from all results.
  - `contents.context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `context` (boolean | object, optional)
  - `context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `moderation` (boolean, optional) — Enable content moderation (may reduce recall).

### Exa Answer

`exa_answer`

Exa answer input.

  - `query` (string, **required**) — Question to answer using web results.
  - `stream` (boolean, optional) — Stream tokens as they are generated.
  - `text` (boolean, optional) — Include full source text in citations.
  - `outputSchema` (any, optional) — JSON Schema to return a structured answer. Supports arbitrary user-defined schema shape.

### Exa Research

`exa_research`

Exa research input.

  - `instructions` (string, **required**)
  - `model` ("exa-research-fast" | "exa-research", optional)
  - `outputSchema` (any, optional)

### Hunter People Find

`hunter_people_find`

Enrich one person by email or LinkedIn profile.

  - `email` (string, optional) — Work email for person enrichment lookup.
  - `linkedin` (string, optional) — LinkedIn profile URL or handle.

### Hunter Companies Find

`hunter_companies_find`

Enrich one company profile by domain.

  - `domain` (string, **required**) — Company domain to enrich.

### Hunter Combined Find

`hunter_combined_find`

Fetch person and company enrichment in one response envelope.

  - `email` (string, optional) — Email for combined person+company enrichment.
  - `linkedin` (string, optional) — LinkedIn profile URL/handle for person enrichment.
  - `domain` (string, optional) — Company domain when person identity is incomplete.

### Hunter Discover

`hunter_discover`

Discover companies matching ICP criteria. This call is free in Hunter.

  - `query` (string, optional) — Natural-language company search query. Prefer this for broad ICP discovery.
  - `organization.domain` (string[], optional)
  - `organization.name` (string[], optional)
  - `similar_to.domain` (string, optional)
  - `similar_to.name` (string, optional)
  - `headquarters_location.include` (array, optional)
  - `headquarters_location.include[].continent` (string, optional) — Continent name (for example Europe, North America).
  - `headquarters_location.include[].business_region` (string, optional) — Business region (AMER, EMEA, APAC, LATAM).
  - `headquarters_location.include[].country` (string, optional) — ISO 3166-1 alpha-2 country code (for example US).
  - `headquarters_location.include[].state` (string, optional) — US state code (for example CA). Requires country=US.
  - `headquarters_location.include[].city` (string, optional) — City name (for example San Francisco).
  - `headquarters_location.exclude` (array, optional)
  - `headquarters_location.exclude[].continent` (string, optional) — Continent name (for example Europe, North America).
  - `headquarters_location.exclude[].business_region` (string, optional) — Business region (AMER, EMEA, APAC, LATAM).
  - `headquarters_location.exclude[].country` (string, optional) — ISO 3166-1 alpha-2 country code (for example US).
  - `headquarters_location.exclude[].state` (string, optional) — US state code (for example CA). Requires country=US.
  - `headquarters_location.exclude[].city` (string, optional) — City name (for example San Francisco).
  - `industry.include` (string[], optional)
  - `industry.exclude` (string[], optional)
  - `headcount` (string[], optional) — Accepted values include 1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5001-10000, 10001+.
  - `company_type.include` (string[], optional)
  - `company_type.exclude` (string[], optional)
  - `keywords.include` (string[], optional)
  - `keywords.exclude` (string[], optional)
  - `keywords.match` ("all" | "any", optional)
  - `technology.include` (string[], optional)
  - `technology.exclude` (string[], optional)
  - `technology.match` ("all" | "any", optional)
  - `limit` (number, optional) — Max domains returned (default 100). Changing this requires a Hunter Premium plan.
  - `offset` (number, optional) — Number of domains to skip for pagination. Non-zero offsets require a Hunter Premium plan.

### Hunter Domain Search

`hunter_domain_search`

Find email addresses for a specific company domain with confidence and sources.

  - `domain` (string, **required**) — Company domain to search (for example stripe.com).
  - `company` (string, optional) — Company name hint to improve matching.
  - `limit` (number, optional) — Max emails returned.
  - `offset` (number, optional) — Pagination offset.
  - `type` ("personal" | "generic", optional) — Return only personal emails or only role-based/generic emails.
  - `seniority` (string[], optional) — Filter by seniority labels.
  - `department` (string[], optional) — Filter by department labels.
  - `required_field` (string[], optional) — Require specific returned fields.

### Hunter Email Finder

`hunter_email_finder`

Find the most likely work email from name + domain.

  - `domain` (string, **required**) — Company domain (for example reddit.com).
  - `first_name` (string, **required**) — First name of the contact.
  - `last_name` (string, **required**) — Last name of the contact.
  - `full_name` (string, optional) — Optional full name alias for first + last.
  - `company` (string, optional) — Company name hint when multiple domains exist.
  - `max_duration` (number, optional) — Lookup timeout in seconds.

### LeadMagic Role Finder

`leadmagic_role_finder`

Find people by job title at a company.

  - `company_domain` (string, optional) — Company domain (e.g. acme.com).
  - `company_name` (string, optional) — Company name.
  - `job_title` (string, **required**) — Target job title (e.g. VP Sales).

### LeadMagic Company Search

`leadmagic_company_search`

Search for companies by attributes.

  - `company_domain` (string, optional) — Company domain to match.
  - `company_name` (string, optional) — Company name to match.
  - `profile_url` (string, optional) — LinkedIn/company profile URL.
  - `domain` (string, optional) — Legacy alias for company_domain.
  - `name` (string, optional) — Legacy alias for company_name.

### LeadMagic Profile Search

`leadmagic_profile_search`

Fetch a detailed professional profile by LinkedIn URL.

  - `profile_url` (string, **required**) — LinkedIn profile URL.

### LeadMagic Competitors Search

`leadmagic_competitors_search`

Find competitors for a company.

  - `company_domain` (string, **required**) — Company domain to analyze.

### LeadMagic B2B Ads Search

`leadmagic_b2b_ads_search`

Find B2B ads by company domain.

  - `company_domain` (string, optional) — Company domain to analyze.
  - `company_name` (string, optional) — Company name to analyze.
  - `domain` (string, optional) — Legacy alias for company_domain.

### Adyntel Facebook Ad Search

`adyntel_facebook_ad_search`

Meta keyword ad search across the ad library for advertiser and creative discovery.

  - `keyword` (string, **required**) — Keyword to search in Meta ad library.
  - `country_code` (string, optional) — Optional country filter code.

### Google Search

`google_search`

Run a Google Custom Search JSON API query. Best for broad B2B recall (contact, company, and domain discovery) before enrichment.

  - `query` (string, **required**) — Search query string. B2B patterns: contact LinkedIn (`site:linkedin.com/in "First Last" "Company"`), company LinkedIn (`site:linkedin.com/company "Company"`), email/domain validation (`"First Last" "company.com"`).
  - `cx` (string, optional) — Custom Search Engine ID. Defaults to GOOGLE_SEARCH_ENGINE_ID.
  - `num` (number, optional) — Results per page (1-10).
  - `start` (number, optional) — 1-indexed start result position.
  - `gl` (string, optional) — Country code (e.g. us).
  - `lr` (string, optional) — Language restrict (e.g. lang_en).
  - `dateRestrict` (string, optional) — Date restriction (e.g. d7, w2, m6).
  - `siteSearch` (string, optional) — Restrict results to a domain.
  - `siteSearchFilter` ("i" | "e", optional) — Include (i) or exclude (e) siteSearch domain.
  - `safe` ("off" | "active", optional) — SafeSearch mode.

### Parallel Search

`parallel_search`

Parallel search input. Requires objective or search_queries.

No documented fields.

