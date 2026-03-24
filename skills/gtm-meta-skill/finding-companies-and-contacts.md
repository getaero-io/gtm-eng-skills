# Finding Companies and Contacts (JTBD Draft)

Use this doc for discovery, sourcing, TAM/list building, known-source extraction, contact discovery, and hiring-qualified company search before any row-level enrichment.

This doc does **not** cover email waterfalls, row-level `deepline enrich` mechanics, coalescing, validation, or personalization columns. If you already have rows and need to fill or transform columns, stop and use `enriching-and-researching.md`.

## Core rules

Default to discovery/search here. The moment the work becomes per-row enrichment, hand off to `enriching-and-researching.md`.

**Companies first, then people.** When the task involves finding contacts at companies matching criteria (ICP, portfolio, accelerator, hiring signal), always discover the company set first, then search for people at those companies. Do not start with people-search tools (`exa_people_search`, `dropleads_search_people`, etc.) using broad title+industry queries — you will get noisy, unaffiliated results. The only exception is when the user provides a specific named company list and only needs contacts.

Use a list-building/search subagent when discovery is genuinely multi-provider and non-trivial. Tell subagents to read this file. Only use the parent agent inline for small, obvious lookups.

Subagent output contract:
- return a seed CSV or structured list only
- preserve source lineage
- stop before row-level enrichment
- recommend the next step

Search-to-enrichment handoff rules:
- stop adding ad-hoc row-level scripts once you have a seed list
- move per-column work into `deepline enrich --with ...`
- keep lineage in-sheet with `_metadata`

## Tool discovery

Use `deepline tools search` once near the top when the scenario is clear but the exact tool family is not.

Prefer category-constrained searches. More search terms helps with recall. Then inspect the strongest candidates.

```bash
deepline tools search --categories company_search --search_terms "structured filters,firmographics" &
deepline tools search --categories people_search --search_terms "title filters,linkedin" &
deepline tools search --categories company_search --search_terms "investors,funding" &
deepline tools search --categories research --search_terms "ads,technographics" &
wait

deepline tools get crustdata_companydb_search &
deepline tools get dropleads_search_people &
deepline tools get apify_run_actor_sync &
wait
```

After tool discovery, do not jump straight into broad execution. Shortlist 1-2 realistic candidates, inspect their schemas with `deepline tools get`, validate enum-like inputs where needed, then run a narrow first pass.

## Discovery workflow

| Step | What to do | Why |
|---|---|---|
| 0 | Check if the data already exists or has a known source URL | Avoid unnecessary provider calls |
| 1 | Shortlist 1-2 providers from the reference table | Prevent random provider thrash |
| 2 | Inspect the schema with `deepline tools get` | Avoid guessed field names and bad payloads |
| 3 | Validate enum-like values with autocomplete tools | Prevent silent empty searches |
| 4 | Execute a count-like or narrow first pass | Cheaply confirm fit before full pull |

Anti-patterns:
- **jumping to people-search first** — searching for "GTM Engineer at YC startup" via `exa_people_search` or `dropleads_search_people` before having a company list. Find companies first, then find people at each.
- reconstructing a known directory with repeated search queries
- firing all providers in parallel before routing
- guessing filter names or enum values
- using `deeplineagent` as the default discovery path here.
- continuing row-level logic / enrichment/research here after a seed list exists

## Scenario table

| Scenario | Read Section | Why |
|---|---|---|
| Need to size an audience or validate whether a market is worth pulling | `Search audiences` | Read this when the real question is reachability, volume, or whether a search path can support the target list size. |
| Need to find companies that match a crisp ICP or match various filters | `Structured company search` | Read this when the work is filter-driven and you need the right structured-company path instead of broad web discovery. |
| Need to pull companies from a known portfolio, directory, or public list | `Known-source extraction` | Read this when the source page is already known and direct extraction should beat rebuilding the list through search. |
| Need contacts for a CSV or an existing company list | `Handoff to enrichment` | Read this when the task is already row-based. This doc should stop and send the work to `enriching-and-researching.md`. |
| Need contacts for a few companies named in the prompt | `People search at known companies` | Read this when discovery still needs to turn a handful of named companies into a candidate contact list before handing off to enrichment. |
| Need to find companies hiring for a role or function | `Hiring-qualified search` | Read this when hiring is the qualification signal and you need the best discovery path before enrichment starts. |
| Need to recover a LinkedIn URL or company page | `URL recovery` | Read this when the identity is known but the URL is missing and precision matters more than recall. |
| Need to scrape a known public page or directory | `Online scraping and public web extraction` | Read this when the answer is likely sitting on a public page and extraction should come before search. |
| Need investor-backed or registry-backed companies | `Investor, portfolio, and registry search` | Read this when official portfolio pages or registries are the strongest source of truth. |
| Need a particular source such as LinkedIn, Crunchbase, Reddit, Twitter/X or others | `Custom sources with Apify` | Read this when the source itself is part of the task and you need the custom-source pattern rather than generic search. |
| Need a niche or custom search path | `Custom tool and provider discovery` | Read this when the default routes do not fit and you need to discover one or two realistic alternatives. |

## Search audiences

Use this section when the user asks:
- "how many people can we reach?"
- "how big is this audience?"
- "is this market big enough to go after?"
- "can this provider support the volume we need?"
- "pull 100k leads" and you need to validate whether the audience is actually there

Recommended course of action:
1. Start with the audience you actually care about: people, companies, jobs, or a rough domain-level signal.
2. Prefer a dedicated count endpoint when one exists.
3. Otherwise run the likely retrieval path with `limit:1`, `per_page:1`, or `size:1`.
4. Read totals from the inline output (counts render directly, rows auto-extract to CSV with preview).
5. If the first path is weak, switch to a closer retrieval path or a better-matched count path.
6. Only pull full pages after the audience shape and size look right.

### Trying to size a people audience

Use this when the user wants reachable contacts, not just companies.

Start here:
- dedicated people-count endpoints
- otherwise the likely people retrieval path with a tiny page size

Good first paths:
- Dropleads count or `dropleads_search_people` with `limit:1`
- Apollo first-page people search
- Forager person-role totals
- Icypeas people counts
- Prospeo person search with `page:1`
- PDL person search with `size:1`

```bash
deepline tools execute dropleads_get_lead_count --payload '{"filters":{"jobTitles":["CEO"],"industries":["Technology"]}}'
deepline tools execute dropleads_search_people --payload '{"filters":{"jobTitles":["VP Sales"],"industries":["Technology"]},"pagination":{"page":1,"limit":1}}'
deepline tools execute apollo_search_people --payload '{"page":1,"per_page":1}'
deepline tools execute apollo_people_search_paid --payload '{"q_keywords":"sales","per_page":1,"page":1}'
deepline tools execute forager_person_role_search_totals --payload '{"role_title":"\"Software Engineer\""}'
deepline tools execute icypeas_count_people --payload '{"query":{"currentJobTitle":{"include":["CTO"]}}}'
deepline tools execute prospeo_search_person --payload '{"person_job_title":{"include":["VP Sales"]},"page":1}'
deepline tools execute peopledatalabs_person_search --payload '{"query":{"bool":{"must":[{"term":{"location_country":"United States"}},{"term":{"job_title_role":"marketing"}}]}},"size":1}'
```

Default to Dropleads first for people-audience sizing. It is usually the strongest free first pass here and gives you LinkedIn-rich retrieval if you continue.

If that path is weak, switch to a retrieval path that matches the real search more closely.

When you move from sizing to actually pulling rows, rerun the chosen retrieval path in normal output mode.

### Company-audience paths

Use this when the user wants to know how many accounts match the ICP.

Start with a structured company path at `limit:1`, then move to dedicated totals only if they fit better.

```bash
deepline tools execute crustdata_companydb_search --payload '{"filters":[{"filter_type":"crunchbase_categories","type":"in","value":["Identity Management","Fraud Detection"]},{"filter_type":"hq_country","type":"=","value":"USA"},{"filter_type":"employee_count_range","type":"in","value":["51-200","201-500"]},{"filter_type":"last_funding_round_type","type":"in","value":["Series A","Series B"]}],"limit":1}'
deepline tools execute forager_organization_search_totals --payload '{"industries":[1]}'
deepline tools execute prospeo_search_company --payload '{"company":{"names":{"include":["Intercom"]},"websites":{"include":["intercom.com"]}},"page":1}'
```

When the sizing path looks right, rerun the chosen pull path in normal output mode.

### Trying to size hiring demand

Use this when the user really means:
- how many companies are hiring for this role?
- how large is the job market?

Start here:
- job totals if the job market itself is the thing being sized
- hiring evidence on known companies if you already have the company set

```bash
deepline tools execute forager_job_search_totals --payload '{"title":"\"Sales Engineer\""}'
deepline tools execute hunter_discover --payload '{"query":"B2B SaaS companies","limit":1}'
```

### Trying to get a rough domain-level signal

Use this when the user wants a quick directional answer about a company or domain, not a true people-audience estimate.

Start here:
- domain-level count endpoints

```bash
deepline tools execute hunter_email_count --payload '{"domain":"stripe.com"}'
```

Watch out for:
- domain email volume is not the same as reachable persona-level audience size
- use this for rough planning, not as the final answer for a people-search question

### Trying to validate whether a retrieval path fits

Use this when you care more about whether the retrieval path is viable than about the count itself.

Start here:
- run the likely retrieval path with `limit:1`
- inspect the response shape and any returned total metadata

Representative command:

```bash
deepline tools execute crustdata_people_search --payload '{"companyDomain":"notion.so","titleKeywords":["VP","Head"],"limit":1}'
```

Watch out for:
- some tools are good retrieval paths but weak sizing sources
- CrustData people retrieval is useful for fit testing, not as your source of truth for audience size

## Structured company search

Use this section when the user has a crisp ICP, such as:
- funding stage
- headcount range
- geography
- vertical/category
- investor
- hiring proxy or company maturity

Recommended course of action:
1. Use structured company search first.
2. Validate enum-like values before committing to a full search.
3. Run a count-like first pass with `limit:1` when appropriate.
4. Pull more rows than the final target if downstream attrition is expected.
5. If the exact filter set is unclear, use the tool-discovery pattern above instead of hardcoding a provider guess.

### Canonical value validation

```bash
deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"crunchbase_categories","query":"identity","limit":5}'
```

### Count-first structured company search

```bash
deepline tools execute crustdata_companydb_search --payload '{"filters":[{"filter_type":"crunchbase_categories","type":"in","value":["Identity Management","Fraud Detection"]},{"filter_type":"hq_country","type":"=","value":"USA"},{"filter_type":"employee_count_range","type":"in","value":["51-200","201-500"]},{"filter_type":"last_funding_round_type","type":"in","value":["Series A","Series B"]}],"limit":1}'
```

### Full structured company pull

```bash
deepline tools execute crustdata_companydb_search --payload '{"filters":[{"filter_type":"crunchbase_categories","type":"in","value":["Identity Management","Fraud Detection"]},{"filter_type":"hq_country","type":"=","value":"USA"},{"filter_type":"employee_count_range","type":"in","value":["51-200","201-500"]},{"filter_type":"last_funding_round_type","type":"in","value":["Series A","Series B"]}],"sorts":[{"column":"employee_metrics.latest_count","order":"desc"}],"limit":35}'
```

Structured company search is the wrong choice when:
- the user gave you a known source page
- the target is too fuzzy/conceptual for structured filters
- you need semantic discovery first, not a precise market pull

## Known-source extraction

Use this section when the user points to a VC portfolio, accelerator batch, conference site, partner directory, or similar public page.

Recommended course of action:
1. Fetch/extract the source directly.
2. Use search only if the source itself is unknown.
3. Prefer `parallel_extract` when the page is JS-rendered.
4. Prefer official pages over reconstructed lists whenever you can.

### Direct extraction from a known URL

```bash
deepline tools execute parallel_extract --payload '{"urls":["https://www.ycombinator.com/companies?batch=W26"],"objective":"Extract all company names, domains, and one-line descriptions from this page","full_content":true}'
```

## People search at known companies

Use this section when the user already has target companies and needs candidate contacts or role owners.

Recommended course of action:
1. Use broad function keywords plus seniority.
2. Prefer company domains over company names when you know them.
3. For tiny startups, switch away from classic people DBs sooner.
4. Stop at candidate contacts here.
5. If the task becomes "fill in emails or enrich these rows", hand off to `enriching-and-researching.md`.

### Mid/large company people search

```bash
deepline tools execute dropleads_search_people --payload '{"filters":{"companyDomains":["stripe.com"],"jobTitles":["Growth","Sales","Revenue"],"seniority":["VP","Director","C-Level"],"personalCountries":{"include":["United States"]}},"pagination":{"page":1,"limit":5}}'
```

### Count-first people search

```bash
deepline tools execute dropleads_search_people --payload '{"filters":{"jobTitles":["Marketing"],"seniority":["VP","Director","C-Level"],"personalCountries":{"include":["United States"]}},"pagination":{"page":1,"limit":1}}'
```

### Tiny-startup fallback

exa_people_search returns keyword-matched LinkedIn profiles, not verified employees. For startups <50 people, expect freelancers and consultants matching across multiple companies. Check each result's title for the correct company name before using it; if >30% are unaffiliated, switch to `deeplineagent` as a tool-backed fallback.

**Disambiguate common company names.** If the company name is a common word (e.g. "Ergo", "Bloom", "Newton"), add disambiguating context to the query — accelerator batch (`YC W25`), domain (`joinergo.com`), or product description. Without this, Exa returns people from unrelated companies with the same name.

```bash
# Bad — "Ergo" matches ERGO Direkt AG, ErgoPack, THE ERGO CORP, etc.
deepline tools execute exa_people_search --payload '{"query":"GTM engineer at Ergo","numResults":5}'

# Good — YC batch + domain disambiguates
deepline tools execute exa_people_search --payload '{"query":"GTM engineer at Ergo joinergo.com YC W25","company_name":"Ergo","numResults":5}'
```

Use `company_name` to pass the target company as structured input — it appends to the query if not already present and tags the response meta for downstream validation.

## Role-based contact search

Never use exact job titles as the primary filter. Use broad functional keywords plus seniority instead.

| Bad | Better |
|---|---|
| exact titles like `Head of Growth`, `VP RevOps`, `GTM Engineer` only | `jobTitles:["Growth"]` + `seniority:["C-Level","VP","Director"]` |

For small companies, switch to `exa_people_search` sooner.

## Hiring-qualified search

Use this section when the user wants companies that are actively hiring for a specific role or likely need a specific function.

Recommended course of action:
1. Discover the plausible company set first. If companies come from a known portfolio or accelerator (YC, a16z, etc.), extract the portfolio first via `Known-source extraction` — you'll get domains for free and skip domain-resolution.
2. Then qualify that set with hiring evidence.
3. Use public-job or semantic evidence only when structured hiring coverage is thin.
4. Treat hiring as a qualification layer, not the only discovery step.

### Structured hiring evidence for known companies

```bash
deepline tools execute crustdata_job_listings --payload '{"companyDomains":["stripe.com","persona.id","sardine.ai"]}'
```

### Public hiring evidence

```bash
deepline tools execute exa_search --payload '{"query":"site:ycombinator.com \"GTM engineer\"","numResults":20,"type":"auto"}'
```

## URL recovery

Use this section when you already know the company or person identity and need the URL.

Recommended course of action:
1. Use a highly specific query.
2. Include company and role context for people.
3. Leave null when the identity is not specific enough.
4. Only move to scraping once you already have the correct URL.

### Company LinkedIn URL lookup

```bash
deepline tools execute serper_google_search --payload '{"query":"\"{{Company}}\" site:linkedin.com/company","num":3}'
```

### Person LinkedIn URL lookup

```bash
deepline tools execute serper_google_search --payload '{"query":"\"Jane Smith\" \"Acme\" \"sales ops\" site:linkedin.com/in","num":5}'
```

## Convergence rules

| Rule | Guidance |
|---|---|
| Filter, don't restart | Filter out bad matches and supplement gaps instead of restarting discovery |
| Stop at good enough | If you have about 80% of the target after filtering, ship it |
| Extract from search responses | Use provider-returned firmographics directly instead of re-enriching them |

## Online scraping and public web extraction

Use this section when:
- the value is on a public page you can fetch directly
- the user gives you a website, directory, conference page, Reddit thread, or social page
- the task is extractive, not broad discovery

Recommended course of action:
1. If the page is known, scrape or extract it directly.
2. Use semantic search only to find candidate pages when the source itself is unknown.
3. Prefer direct extraction for official pages, registries, portfolios, and structured public lists.

Good fits:
- public company directories
- investor portfolio pages
- conference speaker pages
- careers pages
- Reddit threads or public discussion pages
- social profile pages when you already know the profile URL
- registry pages
- public company filings or official records

Direct extraction example:

```bash
deepline tools execute parallel_extract --payload '{"urls":["https://www.ycombinator.com/companies?batch=W26"],"objective":"Extract all company names, domains, and one-line descriptions from this page","full_content":true}'
```

## Investor, portfolio, and registry search

Use this section when:
- the user wants investor-backed companies
- the user mentions YC, a16z, Sequoia, Greylock, Benchmark, or another investor/accelerator
- the strongest source is an official portfolio page or public registry

Recommended course of action:
1. Start with the official portfolio or registry source if you know it.
2. Use search only to find the official source when you do not have it yet.
3. Prefer direct extraction from the official page over reconstructing the list from search results.
4. If the portfolio page is weak or incomplete, supplement with structured company search afterward.

Good source types:
- investor portfolio pages ([`portfolio-prospecting.md`](/recipes/portfolio-prospecting.md))
- accelerator batch directories
- SEC / EDGAR pages
- government or jurisdictional company registries
- official firm websites listing portfolio companies

If the user cares about “investor-backed” as a filter rather than a named portfolio, use the tool-discovery pattern near the top with company-search terms like `investors,funding`.

## Custom sources with Apify

Use this section when the user wants a particular source or platform, for example:
- LinkedIn
- Reddit
- Twitter / X
- Similarweb
- a source-specific website or public page

Recommended course of action:
1. If you already know the page or profile URL, use the source-specific Apify actor directly.
2. Use apify search to find the right actor

Known actors:
- `dev_fusion/linkedin-profile-scraper`
- `apimaestro/linkedin-profile-detail`
- `harvestapi/linkedin-company-employees`
- `radeance/similarweb-scraper`

See:
- [`actor-contracts.md`](/recipes/actor-contracts.md)

Generic Apify call shape:

```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"apimaestro/linkedin-profile-detail","input":{"profileUrl":"https://www.linkedin.com/in/someone/"},"timeoutMs":300000}'
```

For LinkedIn URL recovery, stay in `URL recovery`. For source-specific scraping after you already know the source, use Apify here.

## Custom tool and provider discovery

Use this section when the default path does not fit and you need one or two realistic alternatives.

Do the tool search once near the top, inspect the shortlisted tools, then pick the closest match.

## Provider reference

| Tool | Best for | Server-side filters | Cost | Gotchas |
|---|---|---|---|---|
| `curl` / `parallel_extract` / `WebFetch` | Data at known URLs: VC portfolios, accelerator directories, job boards, team pages, conference speaker lists | URL + optional CSS/objective | free (`curl`) or ~1 cr (`parallel_extract`) | Use `curl` for static HTML, `parallel_extract` for JS-rendered pages. A single fetch returns the complete dataset — search tools return fragments requiring 10+ calls to piece together. |
| `crustdata_companydb_search` | Company lists with ICP constraints (funding, headcount, geography, industry) | funding stage, headcount range, hq_country, crunchbase_categories, linkedin_industries, employee growth, investor | ~1 cr/search | `hq_country` = ISO 3-letter codes (`USA` not `United States`) — silent empty on wrong format. Use `crunchbase_categories` for niche verticals (Fraud Detection, Identity Management), not `linkedin_industries` (too broad). Response includes headcount + funding — don't re-enrich with `deeplineagent` for data already present. `employee_metrics.growth_6m_percent` is a free hiring proxy. |
| `crustdata_companydb_autocomplete` | Get canonical filter values before searching | — | free | Always run before `companydb_search` for fields like `crunchbase_categories`, `linkedin_industries`, `last_funding_round_type`. Requires non-empty `query` (≥1 char). |
| `crustdata_job_listings` | Hiring signals at known companies | company domains | ~0.4 cr/result | Batch domains in one call. Spotty coverage on <200 emp companies — only ~25% have listings. No server-side title filter — filter client-side. |
| `crustdata_people_search` | LinkedIn-oriented person discovery | company domain, title keywords | ~1 cr | — |
| `exa_search` | Concept-driven company/people discovery, gap-filling | semantic query only (no ICP filters) | ~5 cr with contents | Returns unfiltered results — expect to discard 30-50%. `category:"company"` incompatible with `includeDomains`/`includeText`. |
| `exa_people_search` | Contacts at small startups (<50 emp) | query string | ~0.1 cr/result | Returns structured entities. Use via `deepline enrich`. |
| `exa_research` | Deep multi-source synthesis | outputSchema, multi-query | ~10 cr | Slow. Use for research, not list building. |
| `dropleads_search_people` | People discovery + segmentation with structured filters | job titles, seniority, headcount, geography, keywords | free | Near-zero coverage for <50 emp startups. `keywords` must be split: `["GTM","Engineer"]` not `["GTM Engineer"]`. |
| `dropleads_get_lead_count` | Sizing before full pull | same as search_people | free | — |
| `serper_google_search` | URL discovery, `site:` scoped searches | query string | low-cost | Defaults `gl=us` and `hl=en`. Keyword soup without `site:` = noisy. Use `site:` + quoted phrases for precision. |
| `parallel_search` | Broad discovery when you don't know which domains hold the data | objective string | ~1 cr | Lower precision than domain-scoped search. |
| `parallel_extract` | URL-bound extraction, JS-rendered pages | URLs + objective | ~1 cr | Slow. Good for portfolio pages, job boards. |
| `apollo_people_search` | People fallback when dropleads returns 0 | title, domain, location | ~0.2 cr | Mixed quality. Fallback only. |
| `apollo_people_search_paid` | Large company contact pull with email | domain, title keywords | 1 cr/result | Expensive. Good coverage for large cos. |
| `hunter_email_finder` | Email finding in waterfall | domain, first/last name | ~0.3 cr | Poor coverage for <50 emp companies. |
| `peopledatalabs_company_search` | SQL-based company search | SQL (industry, size, funding, location) | expensive | Last resort. Exhaust others first. |
| `crustdata_person_enrichment` | LinkedIn profile enrichment | LinkedIn URL | ~1 cr | — |
| `apify_run_actor_sync` | LinkedIn scraping (profiles, company employees) | actor-specific | varies | Structured data, faster than `deeplineagent` for source-specific scraping. |
| `adyntel_facebook_ad_search` | Meta keyword-based ad search | keyword | ~1 cr | Additional channel coverage. |
| `deeplineagent` | Tool-backed fallback research and ambiguity resolution | prompt + row context | varies | Use only after direct discovery paths fail or when you need guided synthesis over web findings. Ask for structured output with `jsonSchema`. |

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
| `deeplineagent` | varies | company name/domain | Structured if you pass `jsonSchema` | Fallback when providers return 0 | Slower than direct providers; use only after the normal search path is exhausted |
| `apollo_people_search_paid` | 1 cr/result | domain, title keywords | Name, title, email, LinkedIn | Large companies with good Apollo coverage | Expensive, poor for small startups |

**Default: `exa_people_search` via `deepline enrich`.** Returns structured person entities (name, title, LinkedIn, work history) — no parsing needed. Works across company sizes.

```bash
deepline enrich --input seed.csv --in-place --rows 0:1 \
  --with '{"alias":"contact","tool":"exa_people_search","payload":{"query":"{{role}} at {{Company}}","numResults":3}}'
```

**Fallback: `dropleads_search_people`** when you need structured filters (seniority, geography, headcount) and companies are >50 employees. Then `deeplineagent` as the last resort.

## Sample calls by provider

### Serper Google Search

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
deepline tools execute serper_google_search --payload '{"query":"site:ycombinator.com \"GTM engineer\" \"Series B\"","num":10}'

# Company LinkedIn URL discovery
deepline tools execute serper_google_search --payload '{"query":"\"{{Company}}\" site:linkedin.com/company","num":3}'
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
- **Search responses include firmographic data** — headcount (`employee_metrics.latest_count`), funding (`last_funding_round_type`), HQ (`hq_country`), categories, and employee growth (`employee_metrics.growth_6m_percent`). Extract these fields directly into your seed CSV. Do not re-enrich with `deeplineagent` for data already in the response.
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
      "employeeRanges": ["51-200", "201-500", "501-1000"],
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
