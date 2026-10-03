# Finding Companies and Contacts (JTBD Draft)

Use this doc for discovery, sourcing, TAM/list building, known-source extraction, contact discovery, and hiring-qualified company search before any row-level enrichment.

This doc does **not** cover email waterfalls, row-level play mechanics, coalescing, validation, or personalization columns. If you already have rows and need to fill or transform columns, stop and use `enriching-and-researching.md`.

## Core rules

Default to discovery/search here. The moment the work becomes per-row enrichment, hand off to `enriching-and-researching.md`.

**Companies first, then people.** When the task involves finding contacts at companies matching criteria (ICP, portfolio, accelerator, hiring signal), always discover the company set first, then search for people at those companies. Do not start with people-search tools using broad title+industry queries — you will get noisy, unaffiliated results. The only exception is when the user provides a specific named company list and only needs contacts.

Use a list-building/search subagent for non-trivial multi-provider discovery. Tell subagents to read this file; keep small obvious lookups inline.

Subagent output contract:

- return a seed CSV or structured list only
- preserve source lineage
- stop before row-level enrichment
- recommend the next step

Search-to-enrichment handoff rules:

- stop adding ad-hoc row-level scripts once you have a seed list
- move per-column work to a play per `enriching-and-researching.md`
- keep lineage in-sheet with `_metadata`

## Tool discovery

This doc does not rank providers. Run `deepline tools search` for the job at hand and choose from what it returns: results carry each tool's filters, cost, and availability, and they stay current when a provider is added, repriced, or down. Provide an intent query, or omit it only when `--categories` or `--search_terms` supplies the structured search; both filters accept comma-separated values. Always pass `--task` with the input you have and the result you need. Provider names belong in the query, not in a `--prefix` flag.

Syntax: `deepline tools search [query] [--categories <categories>]
[--search_terms <terms>] [--json]`. Supply a query or at least one structured
filter. Search 2-4 synonyms when the first query is ambiguous. Inspection of a
supplied Play or existing run does not require new provider discovery.

Prefer category-constrained searches. More search terms helps with recall. Then inspect the strongest candidates.

```bash
deepline tools search --categories company_search --search_terms "structured filters,firmographics" --task "<input you have -> result you need>"
deepline tools search --categories people_search --search_terms "title filters,location" --task "<input you have -> result you need>"
deepline tools describe <tool_id>
```

These commands are serial examples. For parallel discovery, first finish the
standalone preflight and retain each exit status and complete response.
Do not let a final successful `wait` hide another command's failure.

After tool discovery, shortlist 1-2 candidates, inspect schemas, validate enum-like inputs, then run an authorized narrow first pass. Prefer free or per-result-priced tools when coverage is uncertain. If a tool times out or is flagged unavailable, do not retry it; take the next candidate from the search results within the authorized scope. Use
[execution mechanics](references/plays-run-export-inspect-repair.md) for pilot,
spend, fixed-cohort, and output-retrieval boundaries. A planning request alone
does not authorize provider execution or changing routes after a miss.

When database-style tools return 0 (pre-revenue startups, niche verticals, non-US), search again for semantic/web search, known-URL extraction, or local-business tools.

## Discovery workflow

| Step | What to do                                                 | Why                                             |
| ---- | ---------------------------------------------------------- | ----------------------------------------------- |
| 0    | Check if the data already exists or has a known source URL | Avoid unnecessary provider calls                |
| 1    | Shortlist 1-2 tools from `deepline tools search` results   | Prevent random provider thrash                  |
| 2    | Inspect the schema with `deepline tools describe`          | Avoid guessed field names and bad payloads      |
| 3    | Validate enum-like values with autocomplete tools          | Prevent silent empty searches                   |
| 4    | Execute a count-like or narrow first pass                  | Cheaply confirm fit before full pull            |
| 5    | Prefer result-priced routes when coverage is uncertain     | Avoid paying per miss during exploratory fanout |

Anti-patterns:

- **jumping to people-search first** — searching for "GTM Engineer at YC startup" with a people-search tool before having a company list. Find companies first, then find people at each.
- reconstructing a known directory with repeated search queries
- firing all providers in parallel before routing
- guessing filter names or enum values
- using `deeplineagent` as the default discovery path here.
- continuing row-level logic / enrichment/research here after a seed list exists

## Scenario table

| Scenario                                                                                         | Read Section                                   |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| Sizing an audience or validating market volume                                                   | `Search audiences`                             |
| Companies matching a crisp ICP (funding, headcount, geo, vertical)                               | `Structured company search`                    |
| Pulling from a known URL — portfolio, directory, registry, LinkedIn/Reddit/X, conference, filing | `Known-source extraction`                      |
| Contacts for a CSV or existing company list (row-based)                                          | Stop — route to `enriching-and-researching.md` |
| Contacts for a few companies named in the prompt                                                 | `People search at known companies`             |
| Companies hiring for a role or function                                                          | `Hiring-qualified search`                      |
| LinkedIn URL or company page recovery                                                            | `URL recovery`                                 |
| Niche path the default routes don't cover                                                        | `Tool discovery` (top of doc)                  |

## Search audiences

Use when sizing reachability, volume, or market fit — "how many people can we reach?", "is this market big enough?", "pull 100k leads".

**Count-first invariant:** prefer a dedicated count endpoint. Otherwise run with `limit:1` / `per_page:1` / `size:1` and read totals. Pull full pages only after shape + size look right.

For large payloads or Windows/PowerShell quoting trouble, write the JSON to a file and pass `--payload @path/to/payload.json`; generated payloads can use `--payload-stdin`.

Search for a count or totals tool for the audience (people, companies, or open jobs) before pulling rows. A single-domain email count is a rough signal about one company, not a persona-level audience estimate.

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
6. Stop after a tiny pilot when usable rows are sparse, domains are missing, taxonomy is broad, or cost per usable row is high. Change source route before scaling.

Structured company search is the wrong choice when:

- the user gave you a known source page
- the target is too fuzzy/conceptual for structured filters
- you need semantic discovery first, not a precise market pull

## Known-source extraction (web and provider APIs)

Use when the value lives on a public page you can fetch directly — VC portfolios, accelerator batches, conference sites, partner directories, SEC/EDGAR, registries, team pages, Reddit threads, LinkedIn/X profiles. Extractive, not discovery.

Rule: if you have the URL, scrape it directly. Use search only to find the URL when the source itself is unknown. Prefer official pages over reconstructed lists. For investor-backed targeting ("companies backed by a16z", "YC W26"), official portfolio pages beat structured search.

Source-type routing:

- **Static HTML pages, registries, official filings** → `curl` or `WebFetch` (free).
- **JS-rendered portfolios, directories, job boards** → `parallel_extract` (~1 cr).
- **LinkedIn profiles, employees, posts, and reactions** → Native HarvestAPI operations. Search and describe the relevant `harvestapi_*` tool before execution.
- **Reddit, X, Similarweb, or a LinkedIn surface HarvestAPI does not expose** → Apify actors. See [`portfolio-prospecting.md`](recipes/portfolio-prospecting.md) for investor/accelerator flow.

Direct extraction example:

```bash
deepline tools execute parallel_extract --payload '{"urls":["https://www.ycombinator.com/companies?batch=W26"],"objective":"Extract all company names, domains, and one-line descriptions from this page","full_content":true}'
```

For LinkedIn, prefer the native HarvestAPI provider: `harvestapi_get_profile` for one profile, `harvestapi_search_leads` for company employees, `harvestapi_get_profile_posts` for a profile's posts, and both `harvestapi_get_post_reactions` and `harvestapi_get_post_comments` for post engagers. Treat these names as starting hints. Tool search is broad and can be noisy, so confirm the exact operation with `deepline tools describe <operation> --schema-only` before execution.

```bash
deepline tools describe harvestapi_get_profile --schema-only
deepline tools execute harvestapi_get_profile --payload '{"url":"https://www.linkedin.com/in/someone/"}' --json
```

Use `--json` for single-object operations such as profile, company, and post
lookups. Use `--out results.csv` for list operations such as employee, post,
reaction, and comment searches; using `--out` on a single-object response can
select an unrelated nested list for CSV preview. For post discovery, prefer a
known `company`, `companyId`, `profile`, or `profileId` filter when available;
broad keyword `search` is fuzzy and can include similarly named terms.

Use Apify for source-specific scraping that HarvestAPI does not cover. Known non-HarvestAPI actors include `supreme_coder/linkedin-post` and `radeance/similarweb-scraper`; discover and inspect the current actor contract before execution.

For LinkedIn URL recovery itself (not scraping after you have the URL), use `URL recovery` below.

## People search at known companies

Use this section when the user already has target companies and needs candidate contacts.

### Resolve missing domains; do not make the user do it

Company names are sufficient input for a known-company task. Before a
domain-scoped contact or enrichment call, resolve the canonical domain for each
named company yourself. Do not interrupt the task with a request for an
"exact," "definitive," or comma-separated domain list.

1. Search the live catalog for a company/domain-resolution or web-search
   capability, then inspect its contract. Use a free or no-credit route for the
   first pass when one is available.
2. Search the company name with any supplied context (location, product,
   investor, LinkedIn URL, or person). Select a candidate only when its official
   page identifies the same organization. Do not use a directory, social
   profile, marketplace, or a search-result host as the company domain.
3. Normalize the resulting hostname, retain the official-page URL as
   `domain_evidence_url`, and carry `company_name`, `domain`, and
   `domain_confidence` into the next stage.
4. If the first route misses, try an independent company-search or web-search
   route before leaving the domain unresolved. Record the attempted routes and
   an explicit `domain_miss_reason`; never guess from the spelling of the name.

For a common or ambiguous name, use the context already in the request and
report the candidate and confidence in the normal output. Do not stop to ask
the user to identify a domain unless choosing among live candidates would cause
a material paid or external action. If no candidate can be verified, preserve
that row as unresolved and continue with every other named company.

Recommended course of action:

1. For nuanced roles or real titles at named companies, follow [`recipes/find-qualified-titles.md`](recipes/find-qualified-titles.md).
2. Otherwise run `deepline tools search --categories people_search` with a `--task` that names the companies and roles, and pick a company-scoped tool from the results.
3. Use broad function keywords plus seniority when no roster exists or the user wants broad audience sizing. Broad title filters can miss titles such as "Director, Mount Sinai AI Assurance Lab."
4. Prefer company domains over company names when you know them.
5. For startups under 50 people, database coverage is thin. Check each returned title for the correct company, and add batch, domain, or product context to disambiguate common names like "Ergo" or "Bloom".
6. Stop at candidate contacts here. If the task becomes "fill in emails or enrich these rows", hand off to `enriching-and-researching.md`.

## Role-based contact search

**Do not guess exact job titles for broad people-search filters.** Titles vary wildly across companies, especially startups, so guessed exact-match filters miss adjacent real titles.

- **Bad:** `jobTitles: ["Head of Growth", "VP RevOps", "GTM Engineer"]` — misses "Director of Growth Marketing", "Revenue Operations Lead", etc.
- **Good:** `jobTitles: ["Growth"]` + `seniority: ["VP", "Director"]` — catches all growth-related senior roles via fuzzy matching.
- **Best for known companies:** obtain verbatim titles from `company_titles`, qualify that roster, then pass the selected exact strings through `title_lists`.

For broad searches without a roster, use 1-2 function keywords (Growth, Sales, Revenue, Security, Fraud, Identity, RevOps, Marketing) plus seniority.

For <500-employee companies, narrow title filters often return 0; use broad keyword + seniority.

## Hiring-qualified search

Use this section when the user wants companies that are actively hiring for a specific role or likely need a specific function.

Recommended course of action:

1. Discover the plausible company set first. If companies come from a known portfolio or accelerator (YC, a16z, etc.), extract the portfolio first via `Known-source extraction` — you'll get domains for free and skip domain-resolution.
2. Then qualify that set with hiring evidence.
3. Use public-job or semantic evidence only when structured hiring coverage is thin.
4. Treat hiring as a qualification layer, not the only discovery step.

## URL recovery

Use this section when you already know the company or person identity and need the URL.

Recommended course of action:

1. Use a highly specific query.
2. Include company and role context for people.
3. Leave null when the identity is not specific enough.
4. Only move to scraping once you already have the correct URL.

Query patterns for a web-search tool: `"OpenAI" site:linkedin.com/company` for a company page, `"Jane Smith" "Acme" "sales ops" site:linkedin.com/in` for a person.

## Convergence rules

| Rule                          | Guidance                                                                   |
| ----------------------------- | -------------------------------------------------------------------------- |
| Filter, don't restart         | Filter out bad matches and supplement gaps instead of restarting discovery |
| Stop at good enough           | If you have about 80% of the target after filtering, ship it               |
| Extract from search responses | Use provider-returned firmographics directly instead of re-enriching them  |
