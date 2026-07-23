# Finding companies and contacts

Turn an ICP into a company set, then contacts at those companies. No rows exist yet; the moment you have row-shaped output, hand off to `enriching.md`. Cross-cutting rules (pilot, over-provision, null-on-empty, evidence) live in `../SKILL.md`.

## Companies first, then people

When a task needs contacts at ICP-matching companies, build the company set first, then find people at each company. Going straight to broad people search ("VPs of Marketing at fintechs") returns lower-quality candidates: people-search filters are coarser than firmographic ones, and the people scatter across companies you never validated. The exception is a named company list where the user only needs contacts.

Route by the fact the user actually wants, not by tool name. "Fintechs hiring fraud engineers" is _funding round + headcount + HQ + hiring evidence_ — start from a structured company provider and join job-listing evidence. Trying every tool that mentions "company" burns credits and gives inconsistent runs. Do not use generic web search or a speculative AI-generated list as the primary source.

## Finding companies

You do not have rows yet. Search a listed play for the workflow first; if none fits, use `deepline tools search` for the provider contract, then put the pull into a scratchpad play before scaling. The generic structured-company and company-to-contact plays are hidden until their evals pass, so company discovery and company-scoped persona lookup run through direct provider tools for now.

| You need                                                          | Route                                                                   |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Companies by funding round, headcount, HQ, category               | structured company search (Crustdata, free company search, Exa, extractors) |
| Companies hiring for a role                                       | job-listing/search tool joined to the company set                       |
| Companies in a portfolio / accelerator batch / curated source     | `deepline plays search "<source> company list" --json` first            |
| Reactors/commenters on a LinkedIn post                            | `deepline plays search engagers --json`                                 |

```bash
deepline tools search "company search funding headcount category hq" --json
deepline tools describe <tool-id> --json
deepline tools execute <tool-id> --payload '{"hq_country":"USA","funding_round":["Series A","Series B"],"employee_count":{"min":50,"max":500},"limit":1}' --json
deepline plays check ./company-discovery.play.ts
deepline plays run ./company-discovery.play.ts --input '{"target_count":25}' --watch
```

Tools are the live provider catalog; plays are the workflow surface. Use tools to discover the missing ingredient, then put the ingredient in the play — the first provider call that contributes candidates should move into a play before you scale it, so the run has a replayable source of truth and the next run reuses completed steps instead of reparsing terminal JSON. When `tools execute --json` returns a `starter_script`, use it as the first draft. Keep durable stage names stable: candidate pull, evidence attachment, contact lookup, email waterfall, export.

**Durable discovery rules** (the difference between "built the list from real data" and "fell back to training-data names after tool friction"):

- **Count before pulling.** Ask the source how many it has (a count endpoint, or `limit: 1` as a shape-and-size probe) before pulling pages. Pulling 100 when the source has 18 inflates cost; pulling 25 when it has 4,000 silently truncates the breadth without telling the user.
- **Validate enum-like filters first.** Industry codes, category strings, country codes, and funding-round labels often validate against a closed enum. Sending `"financial services"` where the provider wants `"Financial Services"` (or `54`) returns zero results with no error. Use the provider's autocomplete/enum endpoint on a sample value (`deepline tools search autocomplete --json`) before the full search.
- **ISO 3-letter country codes for HQ filters.** Most structured company providers want `USA`, `GBR`, `DEU`, not `"United States"`. The country filter is the most common silent-failure mode — the request succeeds, the count is zero, and the agent wrongly concludes "no companies match."
- **Filter, then supplement; do not re-discover.** When a pass returns mostly good rows and a few bad ones, drop the bad and supplement gaps from a second source. The noise is in the data, not the query — re-running the primary search with new filters chasing a cleaner set rarely helps.
- **Do not salvage discovery with domain-by-domain enrichment loops.** For "build a list of N companies matching criteria," domain-by-domain enrichment is a gap-fill step after you have a candidate set, not a discovery strategy. If you catch yourself looping over hand-picked domains, return to a provider-native company/job search with broader filters. **Hard stop:** after two provider searches and one supplement pass, write the valid rows with evidence, broaden one filter and rerun, or report the criteria were too narrow.

Preserve the response's evidence columns when writing the CSV: `funding_round`, `last_funding_at`, `employee_count`, `growth_6m_percent`, `hq_city`, `hq_country`, `industry_codes`, `description` — the proof that justifies each row.

For "companies hiring fraud engineers," pull job listings and group by company; preserve `hiring_role`, `hiring_url`, `hiring_posted_at`, `hiring_count`. When the user only needs _whether_ a company is hiring (not for what role), the cheaper path is the `growth_6m_percent`-style field many firmographic searches return for free.

For thin coverage (<50-employee companies, niche verticals, recent batches), an Apify employee/company scraper actor is the fallback once you have specific named companies. Actors are slower than structured providers — pull the full employee list for a target, then filter for the persona; do not iterate queries trying to coax more out of a structured provider that is genuinely empty for that target.

## Finding contacts

**Broad function + seniority across companies; exact titles at one known company.** People search across many companies ("VPs of Marketing at US fintechs") uses a broad functional category plus seniority — `function: ["Marketing"]`, `seniority: ["VP", "Director"]`. Exact title arrays (`["VP of Marketing", "Vice President, Marketing"]`) miss real titles because title spelling varies wildly. Persona lookup at one known company is the opposite: exact title tokens (`CEO`, `CTO`, `Head of Security`) are stronger when intent is specific.

```bash
# People across companies
deepline tools search "people search" --json
deepline tools execute <tool-id> --payload '{"function":"Marketing","seniority":["VP","Director"],"hq_country":"USA","limit":1}' --json

# People at a known company
deepline plays search contact --json
deepline plays run <play-name> --input '{"company_name":"Acme","domain":"acme.com","roles":"VP Marketing","seniority":"VP"}' --watch
```

For a company list → contacts, this is a clean case for a small custom play with one `ctx.dataset` stage doing company-scoped people search per row. Resolving a domain from a company name is mechanical — use a search tool (`deepline tools search search --json`), not `deeplineagent`. Engagers on a post output a list of people — hand off to the qualification section (`deeplineagent` with a tier `jsonSchema`).

## When databases come up thin: keep searching, change the route

Niche, local, and public-sector personas — city clerks, school administrators, practice managers, SMB owners — live in directories and public websites, not B2B databases. A zero from the database rung is a routing signal, not an answer: the people verifiably exist online, so keep searching until the route matches where they live.

The discovery ladder: structured provider search → maps/local search → web search with `site:` and directory patterns (the state municipal league, the county site, the association member roster) → **known-source extraction**: when a page lists them, scrape that page (a search tool with contents, a firecrawl-class extractor, or an Apify actor for the specific site) and assemble rows from it with the source URL as the evidence column. An official roster beats any provider for accuracy, and public-sector data is public.

Persistence is not thrash. The anti-pattern the hard stop above guards against is re-running the *same* provider with reshuffled filters; the discipline here is escalating to the *next independent route*. The hard stop applies per route — never to the mission.

## Convergence and dedup

Define the target row count up front (usually the user's ask). Over-provision per `../SKILL.md` (each downstream stage has ~15-20% falloff), filter, and stop when the filtered set hits target — past ~80% of target, marginal returns drop sharply and chasing the last 20% almost never produces real rows. Deduplicate by canonical key (domain for companies, LinkedIn URL or email for people) **after** filtering, not before — keying first can drop valid rows whose key is missing from one merge source. For high-stakes signals (job changes, recent funding, leadership moves), verify with a second source before tagging `HIGH`: single-source is `MEDIUM`, conflicting sources are `LOW`.

## Exit

- Rows exist and need columns filled → `enriching.md`.
- Company set is wrong (shape right, rows wrong) → re-pick the primary source; do not fall back to training data.
- Discovery run errored, stalled, or returned zero rows → `../references/debugging.md` ("provider returns nothing").
