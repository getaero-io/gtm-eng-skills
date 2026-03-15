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
- using `call_ai` here for search.
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

exa_people_search returns keyword-matched LinkedIn profiles, not verified employees. For startups <50 people, expect freelancers and consultants matching across multiple companies. Check each result's title for the correct company name before using it; if >30% are unaffiliated, switch to `call_ai` with `WebSearch`.

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
deepline tools execute google_search_google_search --payload '{"query":"\"{{Company}}\" site:linkedin.com/company","num":3}'
```

### Person LinkedIn URL lookup

```bash
deepline tools execute google_search_google_search --payload '{"query":"\"Jane Smith\" \"Acme\" \"sales ops\" site:linkedin.com/in","num":5}'
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
| `curl` / `parallel_extract` / `WebFetch` | Known URLs like VC portfolios, job boards, team pages | URL + optional CSS/objective | free or ~1 cr | Prefer direct fetch over reconstructing known pages via search. One fetch often returns the complete dataset; search tools usually return fragments. Use `parallel_extract` for JS-rendered pages. |
| `crustdata_companydb_search` | Company lists with ICP constraints | funding, headcount, geography, industry, investor, growth | ~1 cr/search | `hq_country` must use ISO 3-letter codes like `USA`, not full country names. Use `employee_count_range` for filtering, not `employee_metrics.latest_count`. Prefer `crunchbase_categories` over `linkedin_industries` for niche verticals. Response already includes firmographics and `employee_metrics.growth_6m_percent`; extract them directly instead of re-enriching. |
| `crustdata_companydb_autocomplete` | Canonical filter value lookup | — | free | Run before `companydb_search` for enums like `crunchbase_categories`, `linkedin_industries`, and funding stages. Requires a non-empty query. |
| `crustdata_job_listings` | Hiring signals at known companies | company domains | ~0.4 cr/result | Spotty coverage on smaller companies; no server-side title filter. Missing jobs is not strong negative evidence on small accounts. |
| `crustdata_people_search` | LinkedIn-oriented person discovery | company domain, title keywords | ~1 cr | Better as structured fallback than TAM source of truth. Useful for retrieval fit checks, but weak as a source-of-truth sizing path. |
| `exa_search` | Concept-driven company/people discovery | semantic query | ~5 cr with contents | Expect noisy discard rate; not ideal for crisp ICP filtering. When searching for companies associated with an accelerator/investor, top results tend to be the accelerator's directory page (e.g. `ycombinator.com/companies/X`), not the company's own domain — use `parallel_extract` on the portfolio page instead. `category:"company"` cannot be combined with `includeDomains`/`includeText`; use plain search plus domain scoping when you need source-bounded discovery. |
| `exa_people_search` | Contacts at small startups | query string | ~0.1 cr/result | Returns keyword-matched profiles, not verified employees — expect freelancers for <50-person companies. Filter by company name before handoff. |
| `exa_research` | Deep multi-source synthesis | outputSchema, multi-query | ~10 cr | Use for research, not list building |
| `dropleads_search_people` | Free structured people discovery | titles, seniority, headcount, geography, keywords | free | Poor startup coverage under ~50 employees. Split keyword phrases into separate tokens. Prefer `companyDomains` over `companyNames`. `jobTitles` already does fuzzy/substring matching; `jobTitlesExactMatch` is not useful. Start with `limit:1` when exploring. |
| `dropleads_get_lead_count` | Sizing before full pull | same as search_people | free | Best cheap sizing path for Dropleads. Use before paging through full people-search pulls. |
| `google_search_google_search` | URL discovery and `site:`-scoped searches | query string | free | Without `site:` and quotes it gets noisy fast |
| `parallel_search` | Broad discovery when source domains are unknown | objective string | ~1 cr | Lower precision than domain-scoped search |
| `parallel_extract` | JS-rendered page extraction | URLs + objective | ~1 cr | Slower, but ideal for portfolio pages and job boards |
| `apollo_people_search` | People fallback when Dropleads returns 0 | title, domain, location | ~0.2 cr | Fallback only |
| `apollo_people_search_paid` | Large-company contact pull with email | domain, title keywords | 1 cr/result | Expensive, but useful for large companies |
| `hunter_email_finder` | Email finding in waterfalls | domain, first/last name | ~0.3 cr | Weak on small startups |
| `peopledatalabs_company_search` | SQL-heavy company search | SQL | expensive | Last resort after easier providers. Be careful with shell quoting for SQL payloads; prefer heredocs or payload files instead of brittle inline escaping. |
| `crustdata_person_enrichment` | LinkedIn profile enrichment | LinkedIn URL | ~1 cr | Better for enrichment than discovery |
| `apify_run_actor_sync` | LinkedIn scraping | actor-specific | varies | Faster and more structured than `call_ai` for LinkedIn tasks. Prefer this over LLM-driven scraping when the source is already known. |
| `adyntel_facebook_ad_search` | Meta keyword ad search | keyword | ~1 cr | Extra channel coverage, not default discovery |
| WebSearch/WebFetch | General web research | query string | free | Good for discovery and quick verification |

## Handoff to enrichment

The moment the task becomes "fill columns on these rows", route out.

Trigger phrases:
- "find work emails"
- "validate these emails"
- "research each company"
- "add a personalization column"
- "coalesce providers"
- "run a waterfall"

At that point, stop discovery work and use `enriching-and-researching.md`.
