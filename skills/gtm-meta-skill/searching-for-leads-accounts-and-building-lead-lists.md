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

{provider_search_filters_interpolated}
