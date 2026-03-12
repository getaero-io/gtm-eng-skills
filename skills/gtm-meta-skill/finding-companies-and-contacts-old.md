# Finding Companies and Contacts

Use this doc for discovery, prospecting, contact finding, coverage completion, and portfolio/VC prospecting. Covers the full journey from net-new search through at-scale sourcing and investor-portfolio outbound.

## Search-to-enrichment handoff (mandatory)

This doc governs **discovery/search only**. The moment the workflow shifts to per-row or per-column enrichment, route to [enriching-and-researching.md](enriching-and-researching.md) and execute there.

Use this handoff trigger:
- You now have a seed list (or can create one) and need contact fill, email finding/validation, signal scoring, personalization, coalescing, or any other column-level transforms.
- You need repeatable, inspectable row-level lineage in Playground.

Required behavior after trigger:
- Stop adding ad-hoc shell/python/node scripts for row stitching, coalescing, ranking, or enrichment.
- Move all per-column operations into `deepline enrich --with ...` columns.
- Keep lineage in-sheet (`_metadata`) and iterate in Playground per [enriching-and-researching.md](enriching-and-researching.md).

Hard rule:
- **Do not use custom scripts for per-row/per-column enrichment pipelines when `deepline enrich` can express the step.**
- Scripts are allowed only for minimal file hygiene outside enrichment semantics (for example: creating a tiny seed CSV), not for enrichment logic.

## Simple lead-count query

Use this when someone asks for a lead count. Default output shows totals inline -- just run the command and read the result:

```bash
# Get match count -- total is visible in the default output
deepline tools execute dropleads_search_people --payload '{"pagination":{"page":1,"limit":1},"filters":{"jobTitles":["Software"],"personalCountries":{"include":["United States"]}}}'
```

Operator sequence and payload shape are documented in the Dropleads agent-guidance doc (`src/lib/integrations/dropleads/agent-guidance.md` in the repo).

How to use it:
- If you want a rough idea of effort, call this once and check the total.
- If you need exact N leads, pull pages (e.g., 1 page = 100 leads, 2 pages = 200 leads) only for the final run.
- If this is too low, broaden the title filter (`Engineering`, `Growth`, `Sales`) and rerun.
- For company precision, prefer `companyDomains` over `companyNames` when you know the domain.
- In tests on this tool: `jobTitles:["SWE"]` is much narrower than `jobTitles:["Software"]`; keyword phrases should be split (`keywords:["GTM","Engineer"]`, not `["GTM Engineer"]`).

Fallback examples:

```bash
deepline tools execute dropleads_search_people --payload '{"pagination":{"page":1,"limit":1},"filters":{"keywords":["GTM","Engineer"],"personalCountries":{"include":["United States"]}}}'

deepline tools execute dropleads_search_people --payload '{"pagination":{"page":1,"limit":1},"filters":{"companyDomains":["stripe.com"],"jobTitles":["Growth","Sales","Revenue"],"personalCountries":{"include":["United States"]}}}'
```

## Provider selection

**Shortlist → Inspect → Validate → Execute.** Don't guess params or fire everything in parallel.

### Step 0: Check if you already have the data or know where it lives

Before reaching for API providers, check these (in order):

| Source | When to use | How |
|---|---|---|
| User-provided files | User gave you a CSV, list, or URL | Read it directly. Skip to enriching-and-researching.md for per-row work. |
| Previous API responses | You already called a provider that returned the data | Extract fields from existing response. Don't re-enrich with `call_ai` for data you already have. |
| Known public directories | The entity has a public listing page (VC portfolios, accelerator batches, conference speakers, industry associations, open-source contributor lists) | Fetch directly with `curl`, `parallel_extract`, or `WebFetch`. **A single page fetch returns the complete dataset; search tools return fragments that require many calls to piece together.** Always prefer direct fetch over indirect search when you know the URL. |
| The company's own website | Need hiring signals, product info, team pages | `exa_search` with `includeDomains:["{{domain}}"]` or `parallel_extract` on the URL. |

If none of these apply — you need to *discover* entities matching criteria — continue to Step 1.

### Step 1: Shortlist — scan the provider reference table below, pick 1-2 tools based on "Best for"

Website research is underrated and often the best way to get lists, esp < 200 leads — don't overlook WebSearch/WebFetch and `google_search`.

### Step 2: Inspect — read the tool schema before building payloads

```bash
# Free, instant — shows all available fields, valid values, and gotchas
deepline tools get <tool_id>
```

Run this on each shortlisted tool. Look at available filter fields, operators, and value formats. This prevents picking the wrong field (e.g. `linkedin_industries` when `crunchbase_categories` is more specific for your vertical).

### Step 3: Validate — autocomplete enum fields

For providers with enum filters (crustdata, dropleads), validate values before searching:

```bash
# Free, no credits — get canonical values for the field you plan to filter on
deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"crunchbase_categories","query":"fraud","limit":5}'
```

Compare multiple fields if unsure which is more specific (e.g. autocomplete both `crunchbase_categories` and `linkedin_industries` — use whichever returns tighter matches for your vertical).

### Step 4: Execute — build the query with validated fields and values

Now build the payload using the exact field names and values from steps 2-3. Extract all available data from the response (headcount, funding, HQ, growth) — don't re-enrich with `call_ai` for data already in the response.

**Anti-patterns:**
- **Using search tools to find data at a known URL.** If you know the data lives at `ycombinator.com/companies`, `a16z.com/portfolio`, or any public directory — fetch the page directly with `curl`/`parallel_extract`. Running 10+ exa searches to reconstruct a list that exists on one page wastes turns and credits.
- Firing all providers in parallel for company list building — wastes credits on providers that can't filter your ICP constraints.
- Skipping inspect/validate and guessing filter field names or values — causes silent empty results or broad/noisy results.
- Trusting provider responses blindly — providers often return garbage. Validate and fallback.
- Using `call_ai` when a direct provider tool or Apify actor would work — for LinkedIn work history, profile signals, company employees, prefer `apify_run_actor_sync` first.
- After discovery, continuing in shell/python scripts for per-column enrichment instead of handing off to [enriching-and-researching.md](enriching-and-researching.md).

## Convergence rules (critical)

When building lists iteratively, follow these rules to avoid wasting time:

- **Filter, don't restart.** If enrichment reveals some rows don't match ICP, filter them out and supplement the gap with additional targeted searches. Never restart discovery from scratch — your existing valid rows are sunk cost you've already paid for.
- **Stop at good enough.** If you have >= 80% of the target count after filtering, output what you have. Don't over-optimize for the last few rows.
- **Extract fields from search responses.** `crustdata_companydb_search` responses include headcount (`employee_metrics`), funding (`last_funding_round_type`), HQ (`hq_country`), growth (`employee_metrics.growth_6m_percent`), and categories. Extract these directly into your seed CSV — don't re-enrich with `call_ai` for data you already have.

## Provider reference

| Tool | Best for | Server-side filters | Cost | Gotchas |
|---|---|---|---|---|
| `curl` / `parallel_extract` / `WebFetch` | Data at known URLs: VC portfolios, accelerator directories, job boards, team pages, conference speaker lists | URL + optional CSS/objective | free (`curl`) or ~1 cr (`parallel_extract`) | Use `curl` for static HTML, `parallel_extract` for JS-rendered pages. A single fetch returns the complete dataset — search tools return fragments requiring 10+ calls to piece together. |
| `crustdata_companydb_search` | Company lists with ICP constraints (funding, headcount, geography, industry) | funding stage, headcount range, hq_country, crunchbase_categories, linkedin_industries, employee growth, investor | ~1 cr/search | `hq_country` = ISO 3-letter codes (`USA` not `United States`) — silent empty on wrong format. Use `crunchbase_categories` for niche verticals (Fraud Detection, Identity Management), not `linkedin_industries` (too broad). Response includes headcount + funding — don't re-enrich with `call_ai`. `employee_metrics.growth_6m_percent` is a free hiring proxy. |
| `crustdata_companydb_autocomplete` | Get canonical filter values before searching | — | free | Always run before `companydb_search` for fields like `crunchbase_categories`, `linkedin_industries`, `last_funding_round_type`. Requires non-empty `query` (≥1 char). |
| `crustdata_job_listings` | Hiring signals at known companies | company domains | ~0.4 cr/result | Batch domains in one call. Spotty coverage on <200 emp companies — only ~25% have listings. No server-side title filter — filter client-side. |
| `crustdata_people_search` | LinkedIn-oriented person discovery | company domain, title keywords | ~1 cr | — |
| `exa_search` | Concept-driven company/people discovery, gap-filling | semantic query only (no ICP filters) | ~5 cr with contents | Returns unfiltered results — expect to discard 30-50%. `category:"company"` incompatible with `includeDomains`/`includeText`. |
| `exa_people_search` | Contacts at small startups (<50 emp) | query string | ~0.1 cr/result | Returns structured entities. Use via `deepline enrich`. |
| `exa_research` | Deep multi-source synthesis | outputSchema, multi-query | ~10 cr | Slow. Use for research, not list building. |
| `dropleads_search_people` | People discovery + segmentation with structured filters | job titles, seniority, headcount, geography, keywords | free | Near-zero coverage for <50 emp startups. `keywords` must be split: `["GTM","Engineer"]` not `["GTM Engineer"]`. |
| `dropleads_get_lead_count` | Sizing before full pull | same as search_people | free | — |
| `google_search_google_search` | URL discovery, `site:` scoped searches | query string | free | Keyword soup without `site:` = noisy. Use `site:` + quoted phrases for precision. |
| `parallel_search` | Broad discovery when you don't know which domains hold the data | objective string | ~1 cr | Lower precision than domain-scoped search. |
| `parallel_extract` | URL-bound extraction, JS-rendered pages | URLs + objective | ~1 cr | Slow. Good for portfolio pages, job boards. |
| `apollo_people_search` | People fallback when dropleads returns 0 | title, domain, location | ~0.2 cr | Mixed quality. Fallback only. |
| `apollo_people_search_paid` | Large company contact pull with email | domain, title keywords | 1 cr/result | Expensive. Good coverage for large cos. |
| `hunter_email_finder` | Email finding in waterfall | domain, first/last name | ~0.3 cr | Poor coverage for <50 emp companies. |
| `peopledatalabs_company_search` | SQL-based company search | SQL (industry, size, funding, location) | expensive | Last resort. Exhaust others first. |
| `crustdata_person_enrichment` | LinkedIn profile enrichment | LinkedIn URL | ~1 cr | — |
| `apify_run_actor_sync` | LinkedIn scraping (profiles, company employees) | actor-specific | varies | Structured data, faster than `call_ai` + WebSearch. |
| `adyntel_facebook_ad_search` | Meta keyword-based ad search | keyword | ~1 cr | Additional channel coverage. |
| WebSearch/WebFetch | General web research, quick lookups | query string | free | Great for discovery and list building. |

## Subagent orchestration

When the `deepline-list-builder` subagent is available, use it to fan out searches across providers in parallel. Each provider search runs in an isolated context (no context pollution), results can be compared side-by-side, and the main agent stays clean for merging/dedup.

**When to use:** Large multi-provider searches where you genuinely want to compare results across 3+ sources. Spawn one subagent per provider in a single tool call.

**When NOT to use:** Single-provider lookups, enrichment tasks (use `deepline enrich`), or when provider selection routing above points to one clear primary provider.

## Role-based contact search (critical)

**Never use exact job titles for people search filters.** Titles are too nuanced and vary wildly across companies (especially startups). Instead use broad keyword + seniority:

- **Bad:** `person_titles: ["Head of Growth", "VP RevOps", "GTM Engineer"]` -- misses "Director of Growth Marketing", "Revenue Operations Lead", etc.
- **Good:** `jobTitles: ["Growth"]` + `seniority: ["C-Level", "VP", "Director"]` -- catches all growth-related senior roles via fuzzy matching

The pattern: use 1-2 broad keywords for the *function* (Growth, Sales, Revenue, Security, Fraud, Identity, RevOps, Marketing) and let seniority filters handle the level. This works across dropleads and crustdata.

For small companies (<500 employees), people search often returns 0 with narrow title filters. Use broad keyword + seniority filters. Dropleads is free for people discovery but has near-zero coverage for tiny startups (<50 people). For small startups, use `exa_people_search` instead (see next section).

## Finding contacts at known companies

Pick the right tool based on what you have and what you need:

| Tool | Cost | Input needed | Returns | Best for | Limitation |
|---|---|---|---|---|---|
| `exa_people_search` | 0.1 cr/result | company name + role keyword | Structured entities: name, title, LinkedIn, work history | Any company size, especially small startups | Finds *associated* people, not guaranteed exact role match |
| `dropleads_search_people` | free | company domain or keyword filters | Name, title, email (sometimes), company | Mid/large companies (>50 employees) | Near-zero coverage for tiny startups (<50 people) |
| `call_ai` + WebSearch | free (LLM cost only) | company name/domain | Unstructured — needs json_mode for parsing | Fallback when providers return 0 | Slow (~10s/row), prone to timeouts |
| `apollo_people_search_paid` | 1 cr/result | domain, title keywords | Name, title, email, LinkedIn | Large companies with good Apollo coverage | Expensive, poor for small startups |

**Default: `exa_people_search` via `deepline enrich`.** Returns structured person entities (name, title, LinkedIn, work history) — no parsing needed. Works across company sizes.

```bash
deepline enrich --input seed.csv --in-place --rows 0:1 \
  --with '{"alias":"contact","tool":"exa_people_search","payload":{"query":"{{role}} at {{Company}}","numResults":3}}'
```

**Fallback: `dropleads_search_people`** when you need structured filters (seniority, geography, headcount) and companies are >50 employees. Then `call_ai` + WebSearch as last resort.

## Sample calls by provider

### Google Search

**Query structuring:**
- `site:` scoping to an authoritative domain is the highest-signal pattern -- use it whenever you know where the data lives.
  - `site:ycombinator.com` -- YC company/job data.
  - `site:crunchbase.com` -- funding and firmographic lookup.
  - `site:linkedin.com/company` -- indexes company **tagline/description only**, not employee data.
  - `site:linkedin.com` (broad) -- also surfaces **posts** (`/posts/...`). Useful for signal extraction.
- Keyword soup without `site:` = noisy. Expect Reddit, newsletters, LinkedIn profiles, tangentially related content.
- Use quoted phrases for exact match: `"Series B"`, `"GTM engineer"`. Combine with `site:` for high precision.

```bash
# YC job listings for a specific role
deepline tools execute google_search_google_search --payload '{"query":"site:ycombinator.com \"GTM engineer\" \"Series B\"","num":10}'

# Company LinkedIn URL discovery
deepline tools execute google_search_google_search --payload '{"query":"\"{{Company}}\" site:linkedin.com/company","num":3}'
```

### Dropleads (people search)

Default to `dropleads_search_people` for people discovery when you need structured filters. Use Apollo only when you need a fallback source.

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with '{"alias":"people_search","tool":"dropleads_search_people","payload":{"filters":{"jobTitles":["Sales","Growth"],"seniority":["VP","Director","C-Level"],"personalCountries":{"include":["United States"]}},"pagination":{"page":1,"limit":5}}}'
```

Dropleads note: keep title filters broad (`jobTitles`) and allow seniority to do the heavy lifting.

**Dropleads query gotchas:**
- `keywords`: multi-word strings return 0 -- use `["GTM","engineer"]` not `["GTM Engineer"]`.
- `jobTitles`: substring match, OR'd. Niche titles work (`"GTM Engineer"` = ~20 results).
- `jobTitlesExactMatch`: no observable effect -- ignore it.
- `companyNames`: fuzzy -- prefer `companyDomains` for precision.
- `departments`/`seniority`: enum-only (see schema).
- Use `limit:1` first to check `data.pagination.total`, then pull full pages. Don't iterate exploratory queries.

### CrustData (company + person search, autocomplete)

**Always read the crustdata integration docs (`src/lib/integrations/crustdata/`) before building filter payloads.** Filter field names, valid enum values, and operator behavior are non-obvious -- guessing wastes rounds.

**Key rules:**
- Run `crustdata_companydb_autocomplete` for any field where you don't know the exact canonical value. Autocomplete requires a non-empty `query` string (at least 1 character).
- `employee_metrics.latest_count` is valid for `sorts` but NOT as a `filter_type` -- use `employee_count_range` (string enum like `"51-200"`, `"201-500"`) for headcount filters.
- **`hq_country` uses ISO 3-letter codes**: `USA`, `GBR`, `IND`, `DEU`, etc. — NOT full country names. Passing `"United States"` returns 0 results with no error (silent failure).
- **For niche verticals** (fraud, identity, compliance, fintech sub-segments), prefer `crunchbase_categories` over `linkedin_industries`. LinkedIn industries are broad buckets (`"Financial Services"`); crunchbase categories map to specific business functions (`"Fraud Detection"`, `"Identity Management"`). Always autocomplete both to compare specificity.
- **Search responses include firmographic data** — headcount (`employee_metrics.latest_count`), funding (`last_funding_round_type`), HQ (`hq_country`), categories, and employee growth (`employee_metrics.growth_6m_percent`). Extract these fields directly into your seed CSV. Do not re-enrich with `call_ai` for data already in the response.
- **`employee_metrics.growth_6m_percent`** is a free hiring proxy already in every search response. Positive 6-month growth suggests active hiring. Use this before spending credits on `crustdata_job_listings`, especially for smaller companies where job listing coverage is thin.

**Operators**: `(.)` = fuzzy contains (default), `[.]` = substring, `=`, `!=`, `in`, `not_in`, `>`, `<`, `=>`, `=<`.

```bash
# Always autocomplete first — compare crunchbase_categories vs linkedin_industries for your vertical
deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"crunchbase_categories","query":"fraud","limit":5}'
deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"linkedin_industries","query":"financial","limit":5}'
```

```bash
# Use crunchbase_categories for niche verticals, hq_country with ISO codes
deepline tools execute crustdata_companydb_search --payload '{"filters":[{"filter_type":"crunchbase_categories","type":"in","value":["Fraud Detection","Identity Management"]},{"filter_type":"hq_country","type":"=","value":"USA"},{"filter_type":"employee_count_range","type":"in","value":["51-200","201-500"]},{"filter_type":"last_funding_round_type","type":"in","value":["Series A","Series B"]}],"sorts":[{"column":"employee_metrics.latest_count","order":"desc"}],"limit":50}'
```

### People Data Labs

**PDL is expensive -- use it as a last resort.** Exhaust Exa, Google, Apollo, and Crustdata first.

**Shell quoting with PDL SQL:** PDL takes a raw SQL string. Avoid inline single-quote escaping in bash -- it breaks silently. Instead write the payload to a temp file and pass it with `--payload-file`, or use a bash heredoc:

```bash
PAYLOAD=$(cat <<'EOF'
{"sql": "SELECT * FROM company WHERE industry = 'financial services' AND location.country = 'united states' AND size IN ('51-200','201-500') AND latest_funding_stage IN ('series_a','series_b')", "size": 20}
EOF
)
deepline tools execute peopledatalabs_company_search --payload "$PAYLOAD"
```

### Exa (search, answer, research)

Exa is a semantic web index -- it finds pages by meaning, not just keywords.

**Query rules:** Write natural-language descriptions, not keyword soup (`"B2B SaaS companies that sell sales automation tools"` not `"SaaS B2B sales tools 2025"`). Use `type: "neural"` (default) for concept-driven queries, `"deep"` with `additionalQueries` for broad coverage. Use `startPublishedDate`/`endPublishedDate` for recency. Use `contents.summary` for per-result LLM summaries, `contents.highlights` for snippets.

**Critical: `category` vs `includeDomains` -- NOT interchangeable:**
- `category: "company"` / `"people"` uses Exa's entity index. **`includeDomains`, `excludeDomains`, `includeText`, `excludeText` are NOT supported with `category`** -- throws an error. Use for "companies that *are* X" (concept-driven), NOT "companies that *have* X" (attribute-based).
- `includeDomains` / `excludeDomains` -- scope a regular web search (no category) to specific sites.

**"Companies that hire X role" -- use `includeDomains` on job boards, NOT `category:"company"`:**
```bash
deepline tools execute exa_search --payload '{"query":"GTM engineer job opening at Y Combinator startup","numResults":15,"type":"neural","includeDomains":["ycombinator.com"],"contents":{"highlights":{"numSentences":2,"highlightsPerUrl":1}}}'
```

**Tool selection:** `exa_search` (general-purpose, start here), `exa_company_search` (category:"company" shorthand), `exa_people_search` (structured person entities via `deepline enrich`), `exa_answer` (fact-checking only, low recall), `exa_research` (deep multi-source, supports `outputSchema`).

```bash
# Concept-based company search (category OK here)
deepline tools execute exa_search --payload '{"query":"B2B SaaS companies building AI-powered sales tools","category":"company","numResults":10,"type":"neural","contents":{"summary":{"query":"What does this company do and what funding stage are they?"}}}'

# Attribute + domain-scoped search (NO category -- use includeDomains instead)
deepline tools execute exa_search --payload '{"query":"Series B fintech startups in New York","type":"neural","additionalQueries":["fintech companies Series B NYC"],"numResults":20,"includeDomains":["techcrunch.com","crunchbase.com"],"startPublishedDate":"2024-01-01T00:00:00Z","contents":{"summary":{"query":"What does this company do and what stage are they?"}}}'
```

### Parallel (managed research)

Good for broad discovery when you don't know which domains hold the data. Lower precision than domain-scoped Exa/Google but finds things others miss. Set `max_chars_total` > 10000 for 5+ results.

```bash
deepline tools execute parallel_search --payload '{"mode":"agentic","objective":"Find recent hiring and launch signals for OpenAI","max_results":5,"excerpts":{"max_chars_per_result":1200,"max_chars_total":12000}}'
```

## At-scale coverage completion

Use this section when the job is coverage completion -- you already have target accounts/segments and need to backfill missing contacts/emails.

### Count-capable providers (verified)

Use these when you want fast sizing before doing the full list pull.

| Provider | Tool | Command |
|---|---|---|
| Apollo | `apollo_search_people` | `deepline tools execute apollo_search_people --payload '{"page":1,"per_page":1}'` |
| Apollo | `apollo_people_search_paid` | `deepline tools execute apollo_people_search_paid --payload '{"q_keywords":"sales","per_page":1,"page":1}'` |
| Dropleads | `dropleads_get_lead_count` | `deepline tools execute dropleads_get_lead_count --payload '{"filters":{"jobTitles":["CEO"],"industries":["Technology"]}}'` |
| Dropleads | `dropleads_search_people` | `deepline tools execute dropleads_search_people --payload '{"filters":{"jobTitles":["VP Sales"],"industries":["Technology"]},"pagination":{"page":1,"limit":1}}'` |
| Forager | `forager_organization_search_totals` | `deepline tools execute forager_organization_search_totals --payload '{"industries":[1]}'` |
| Forager | `forager_job_search_totals` | `deepline tools execute forager_job_search_totals --payload '{"title":"\"Sales Engineer\""}'` |
| Forager | `forager_person_role_search_totals` | `deepline tools execute forager_person_role_search_totals --payload '{"role_title":"\"Software Engineer\""}'` |
| Icypeas | `icypeas_count_people` | `deepline tools execute icypeas_count_people --payload '{"query":{"currentJobTitle":{"include":["CTO"]}}}'` |
| Prospeo | `prospeo_search_person` | `deepline tools execute prospeo_search_person --payload '{"person_job_title":{"include":["VP Sales"]},"page":1}'` |
| Prospeo | `prospeo_search_company` | `deepline tools execute prospeo_search_company --payload '{"company":{"names":{"include":["Intercom"]},"websites":{"include":["intercom.com"]}},"page":1}'` |
| Hunter | `hunter_email_count` | `deepline tools execute hunter_email_count --payload '{"domain":"stripe.com"}'` |
| Hunter | `hunter_discover` | `deepline tools execute hunter_discover --payload '{"query":"B2B SaaS companies","limit":1}'` |
| People Data Labs | `peopledatalabs_person_search` | `deepline tools execute peopledatalabs_person_search --payload '{"query":{"bool":{"must":[{"term":{"location_country":"United States"}},{"term":{"job_title_role":"marketing"}}]}},"size":1}'` |
| CrustData | `crustdata_people_search` | `deepline tools execute crustdata_people_search --payload '{"companyDomain":"notion.so","titleKeywords":["VP","Head"],"limit":1}'` |

Notes: Some providers need an actual page pull (small `limit`/`per_page`) instead of dedicated count tools. CrustData `companydb_search`/`persondb_search` don't surface reliable totals -- use for retrieval, not sizing. Always compare `total_count`/`total` with your filter set and stop early when a slice suffices.

### Company-first sourcing

```bash
# Size first
deepline tools execute dropleads_get_lead_count \
  --payload '{
    "filters": {
      "keywords": ["technology"],
      "employeeRanges": ["51-200"]
    }
  }'

# Pull list (100 per page)
deepline tools execute dropleads_search_people \
  --payload '{
    "filters": {
      "keywords": ["technology"],
      "employeeRanges": ["51-200"]
    },
    "pagination": {"page": 1, "limit": 100}
  }'
```

### Contact-first sourcing

```bash
deepline tools execute dropleads_search_people \
  --payload '{
    "filters": {
      "jobTitles": ["VP Sales", "CRO", "Head of Revenue Operations"],
      "employeeRanges": ["51-200", "201-1000"],
      "keywords": ["technology"],
      "personalCountries": {"include": ["United States"]}
    },
    "pagination": {"page": 1, "limit": 100}
  }'
```

### Signal prioritization

Don't outreach to the full sourced list. Prioritize with real signals first. Use the `niche-signal-discovery` skill if you have won/lost data to build a scoring model. Otherwise, enrich with first-party signals:

```bash
# Job listings (hiring = budget + pain)
deepline enrich --input tam.csv --in-place --rows 0:1 \
  --with '{"alias":"jobs","tool":"crustdata_job_listings","payload":{"companyDomains":"{{Domain}}","limit":20}}'

# Website content (multi-page discovery)
deepline enrich --input tam.csv --in-place --rows 0:1 \
  --with '{"alias":"website","tool":"exa_search","payload":{"query":"company product features integrations pricing careers about","numResults":5,"type":"auto","includeDomains":["{{Domain}}"],"contents":{"text":{"maxCharacters":2000,"verbosity":"compact","includeSections":["body"]}}}}'
```

Then score using signals from job listings (hiring relevant roles), tech stack (integration readiness), and website content (pain language, compliance maturity).

## Signal-driven lead sourcing

When you have a completed `niche-signal-discovery` report, every signal type translates directly into search criteria.

### Signal -> Search Parameter Mapping

| Report Signal Type | Dropleads Parameter | How to Extract | Example |
|--------------------|-----------------|----------------|---------|
| Job titles with lift > 2x | `jobTitles` | Use title patterns from Section 4 (Job Role Analysis) | "RevOps" at 2.56x -> `["Revenue Operations", "RevOps", "Head of RevOps"]` |
| Keywords with lift > 2x | `q_organization_keyword_tags` | Use keywords from Section 2 (Website Keyword Differential) | "ABM" at 3.67x -> `["account based marketing", "ABM"]` |
| Tech stack tools with lift > 2x | `q_organization_keyword_tags` | Use tool names from Section 3 (Tech Stack Analysis) | Gainsight at 3.0x -> `["gainsight"]` |
| Employee headcount ranges | `employeeRanges` | From Section 0.1 TLDR or Section 1 Executive Summary | "200-1,500 employees" -> `["201-500", "501-1000", "1001-5000"]` |
| Geography | `personalCountries` | If report mentions geo patterns | US-focused -> `{"include": ["United States"]}` |
| Anti-fit tech stack | Exclude from results | Tech stack with lift < 0.5x | Salesloft at 0.33x -> skip companies using Salesloft |

### Example: Report -> Lead List

**1. Map buyer personas to Dropleads searches** using the report's "Buyer Persona Quick Reference" table:

```bash
# RevOps Leader persona (2.56x lift, 55% of won companies)
deepline tools execute dropleads_search_people \
  --payload '{"filters":{"jobTitles":["Revenue Operations","RevOps","Head of Revenue Operations"],"seniority":["VP","Director","Manager"],"keywords":["b2b saas"],"employeeRanges":["201-500","501-1000","1001-5000"],"personalCountries":{"include":["United States"]}},"pagination":{"page":1,"limit":1}}'
```

**2. Verify with job listing keywords (post-pull).** High-lift keywords like "fragmented" (13x), "ICP" (9x) can't be person-search filters -- use Crustdata for post-pull verification:

```bash
deepline enrich --input tam.csv --in-place --rows 0:1 \
  --with '{"alias":"jobs","tool":"crustdata_job_listings","payload":{"companyDomains":"{{Domain}}","limit":50}}'
```

**3. Build combined list:** Run one search per buyer persona, deduplicate by company domain, then run the job listing enrichment + scoring pipeline above.

## Portfolio/VC prospecting

### Core insight: VC portfolio data is public

Every major VC and accelerator publishes their portfolio online. **Do NOT waste turns trying to discover portfolio companies through Deepline search tools.** Instead, fetch the public portfolio page directly and extract company names from it. This is faster, cheaper, and more complete than any provider-based approach.

### What NOT to do

Tested and failed: Apollo investor filtering (irrelevant results), people-first then verify investor (~7-9% hit rate, wastes 60-80% of turns), Crustdata `crunchbase_investors` (inconsistent), `call_ai` per-row investor verification (~5-10s/row, unacceptable at scale).

### Proven approach

**Step 1: Get the company list from the VC's public portfolio.** Common URLs: YC (`ycombinator.com/companies`), a16z (`a16z.com/portfolio`), Sequoia (`sequoiacap.com/our-companies`), Greylock/Benchmark (`/portfolio`).

```bash
# Fetch YC companies page (or use parallel_extract if JS-rendered)
curl -sS "https://www.ycombinator.com/companies" -H "Accept: text/html" -o /tmp/yc_page.html

deepline tools execute parallel_extract --payload '{"urls":["https://www.ycombinator.com/companies?batch=W26"],"objective":"Extract all company names, website domains, and one-line descriptions from this YC batch directory page","full_content":true}'
```

**Step 2: Filter to companies hiring your target role (optional).**

```bash
deepline enrich --input yc_companies.csv --in-place --rows 0:2 \
  --with '{"alias":"exa_jobs","tool":"exa_search","payload":{"query":"GTM Engineer site:ycombinator.com","numResults":50,"type":"auto"}}'
```

**Step 3: Find contacts at each company.**

For small startups (5-50 people), dropleads has near-zero coverage. Use `exa_people_search` — it returns structured person entities (name, title, LinkedIn, work history) and works well for startups:

```bash
deepline enrich --input yc_companies.csv --output yc_with_contacts.csv \
  --rows 0:2 \
  --with '{"alias":"contact","tool":"exa_people_search","payload":{"query":"GTM Engineer at {{company_name}}","numResults":3}}'
```

Write a `run_javascript` step to extract the best contact from exa entities (walk `results[].entities[].properties.workHistory[]` for title keywords). If exa returns 0 for a company, fall back to `call_ai` with WebSearch:

```bash
deepline enrich --input yc_missing.csv --in-place \
  --with '{"alias":"contact_lookup","tool":"call_ai","payload":{"prompt":"Find the founder, CEO, or GTM/growth lead at {{company_name}} ({{domain}}). Return their full name, title, and LinkedIn URL.","json_mode":{"type":"object","properties":{"name":{"type":"string"},"title":{"type":"string"},"linkedin_url":{"type":"string"}},"required":["name","title"]},"tools":["WebSearch"]}}'
```

**Step 4: Find emails via waterfall.**

For small startups, use LeadMagic as primary (not Hunter -- Hunter has poor coverage for <50 person companies):

```bash
deepline enrich --input yc_with_contacts.csv --in-place --rows 0:2 \
  --with-waterfall "email" \
  --with '{"alias":"leadmagic","tool":"leadmagic_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"dropleads","tool":"dropleads_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_domain":"{{domain}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"hunter","tool":"hunter_email_finder","payload":{"domain":"{{domain}}","first_name":"{{first_name}}","last_name":"{{last_name}}"},"extract_js":"extract(\"email\")"}' \
  --end-waterfall
```

**Step 5: Generate personalized email copy** using `call_ai` with `json_mode` for subject/body. Pilot on rows 0:2, then run full batch.

## LinkedIn profile lookup and validation

LinkedIn URLs from providers are often stale. Two phases: find then validate.

**Find** -- waterfall, stop on first hit:
1. Dropleads (`dropleads_search_people`, free)
2. Google CSE (`"First Last" "Company" site:linkedin.com/in/`)
3. Exa (`exa_search` with `category: "people"`)
4. Apollo (`apollo_people_match`) -- **fallback only**
5. Crustdata (`crustdata_person_enrichment`)

**Validate (mandatory)** -- scrape the profile with Apify (`dev_fusion/linkedin-profile-scraper`):
- Name + company match -> confirmed, update row with fresh data
- Name matches, company doesn't -> job change, update with new company/title
- Neither matches -> wrong profile, try next provider

Normalize company names first (JPM -> JPMorgan Chase). Try nickname variants on failure (Robert<->Bob, William<->Bill, Michael<->Mike, etc.).

## Common ICP filter parameters (Dropleads)

| Filter | Parameter | Example values |
|---|---|---|
| Job title | `jobTitles` | `["VP Sales", "Head of GTM"]` |
| Similar titles | use `jobTitles` variants in title list | `true` |
| Headcount | `employeeRanges` | `["51-200", "201-500"]` |
| Industry/keywords | `keywords`/`industries` | `["technology", "SaaS", "fintech"]` |
| Geography | `personalCountries` | `{"include": ["United States", "Canada"]}` |
| Revenue | `revenueRange` | `{"min": 1000000, "max": 50000000}` |
| Seniority | `seniority` | `["C-Level", "VP", "Director", "Manager"]` |

Valid seniority values: `C-Level`, `VP`, `Director`, `Manager`, `Senior`, `Entry`, `Intern`

## Pagination

Dropleads returns up to 100 results per page. For large sourcing runs/backfills:

```bash
# Page 1
deepline tools execute dropleads_search_people --payload '{"pagination":{"page":1,"limit":100}, ...}'

# Page 2
deepline tools execute dropleads_search_people --payload '{"pagination":{"page":2,"limit":100}, ...}'
```

## Cost estimation

| Operation | Credits | Notes |
|-----------|---------|-------|
| `dropleads_search_people` (limit: 1) | ~0.01 | Sizing -- nearly free |
| `dropleads_search_people` (limit: 100) | ~1 | Full pull |
| `crustdata_job_listings` | ~1 | Per company |
| `exa_search` with contents | ~5 | Per company |
| Portfolio page fetch (curl) | 0 | Free |
| LeadMagic email finder | ~0.3 | Per contact |

Size first with `pagination.limit: 1`, then calculate: `total_pages x credits_per_page`.

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

  - `filters` (unknown, **required**) — Array of filter conditions (AND-combined). Each: {filter_type, type, value} or {filter_name, type, value}. filter_name is syntactic sugar for filter_type (e.g. company_investors → crunchbase_investors, company_funding_stage → last_funding_round_type). Single object is accepted. Nested {op,conditions} groups supported for OR logic.
  - `limit` (number, optional)
  - `cursor` (string, optional) — Pagination cursor.
  - `sorts` (array, optional) — Sort criteria array.
  - `sorts[].column` (string, optional) — Field to sort by (e.g. employee_metrics.latest_count).
  - `sorts[].order` ("asc" | "desc", optional) — Sort order: asc or desc.

### CrustData Person Search

`crustdata_persondb_search`

Searches PersonDB using /screener/persondb/search with filters.

  - `filters` (unknown, **required**) — Array of filter conditions (AND-combined). Each: {filter_type, type, value} or {filter_name, type, value}. filter_name is syntactic sugar for filter_type. Single object is accepted. Nested {op,conditions} groups supported for OR logic.
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

  - `field` (unknown, **required**) — Field name to autocomplete. Must be one of: acquisition_status, company_name, company_type, company_website_domain, competitor_ids, competitor_websites, crunchbase_categories, crunchbase_investors, crunchbase_total_investment_usd, employee_count_range, employee_metrics.growth_12m, employee_metrics.growth_12m_percent, employee_metrics.growth_6m_percent, employee_metrics.latest_count, estimated_revenue_higher_bound_usd, estimated_revenue_lower_bound_usd, follower_metrics.growth_6m_percent, follower_metrics.latest_count, hq_country, hq_location, ipo_date, largest_headcount_country, last_funding_date, last_funding_round_type, linkedin_id, linkedin_industries, linkedin_profile_url, markets, region, tracxn_investors, year_founded. Key mappings: funding stage/round → last_funding_round_type, headcount/size → employee_count_range, industry → linkedin_industries, location → hq_country (ISO alpha-3) or hq_location. Note: hq_country uses 3-letter ISO codes (USA, GBR, CAN), not country names.
  - `query` (string, **required**) — Partial text to match. For hq_country, use ISO code patterns (e.g. "US", "USA", "GBR") rather than country names.
  - `limit` (number, optional)

### CrustData Person Autocomplete

`crustdata_persondb_autocomplete`

Fetches exact filter values using /screener/persondb/autocomplete. Free, no credits consumed.

  - `field` (unknown, **required**) — Field name to autocomplete. Must be one of: current_employers.company_website_domain, current_employers.seniority_level, current_employers.title, headline, num_of_connections, region, years_of_experience_raw. Key mappings: job title → current_employers.title, seniority → current_employers.seniority_level, location → region, company/employer → current_employers.company_website_domain, experience → years_of_experience_raw, bio/summary → headline.
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
  - `linkedin_handle` (string, optional) — LinkedIn profile handle used by Hunter enrichment.

### Hunter Companies Find

`hunter_companies_find`

Enrich one company profile by domain.

  - `domain` (string, **required**) — Company domain to enrich.

### Hunter Combined Find

`hunter_combined_find`

Fetch person and company enrichment in one response envelope.

  - `email` (string, optional) — Email for combined person+company enrichment.
  - `linkedin_handle` (string, optional) — LinkedIn profile handle used by Hunter enrichment.
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
  - `job_titles` (string[], optional) — Filter by job title labels.
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

  - `mode` ("one-shot" | "agentic", optional)
  - `objective` (string, optional) — Required unless search_queries is provided.
  - `search_queries` (string[], optional) — Required unless objective is provided.
  - `max_results` (number, optional)
  - `excerpts.max_chars_per_result` (number, optional)
  - `excerpts.max_chars_total` (number, optional)
  - `source_policy.include_domains` (string[], optional)
  - `source_policy.exclude_domains` (string[], optional)
  - `source_policy.after_date` (string, optional)
  - `fetch_policy.max_age_seconds` (number, optional)
  - `fetch_policy.timeout_seconds` (number, optional)
  - `fetch_policy.disable_cache_fallback` (boolean, optional)
  - `betas` (string | string[], optional)

