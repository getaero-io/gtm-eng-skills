# Finding companies and contacts

List-building from scratch: turning a description ("US fintech, Series A/B, 50-500 employees, hiring fraud roles") into a CSV of companies, contacts, or both. Covers TAM construction, ICP-matching, portfolio extraction, hiring-signal sourcing, and contact discovery at known companies.

This doc does **not** cover row-level enrichment of an existing list. Once you have rows, the next step is `jobs/enriching-and-researching.md`.

## When you are in this doc

You do not yet have rows. The user phrasing is something like:

- "build a list of 25 Series A/B US fintech companies hiring fraud roles"
- "find 5 VP-level marketing contacts at US fintech companies"
- "give me a list of YC W24 companies with at least 20 employees"
- "find companies that recently raised in identity verification"
- "find the contacts I should reach at these 50 accounts"

If the user already has a CSV of companies or contacts and wants columns filled in, you are in `jobs/enriching-and-researching.md`.

## Choose your approach

Route by what data the user actually needs. Tool IDs below are starting hints — confirm with `deepline tools search` and `deepline tools describe` before invoking.

| You need | Pattern category | Discovery |
|---|---|---|
| Companies filtered by funding round / headcount / HQ / industry / category | structured firmographic company search | `deepline tools search "company search" --json` |
| Companies hiring for a specific role / function | hiring-signal search (job listings) | `deepline tools search "job search" --json` |
| Companies hiring (cheap signal, no role specificity) | growth metric on a firmographic search response | (read response from structured search) |
| Companies in a portfolio (YC, a16z, Tiger, an accelerator cohort) | portfolio-source-aware company search | `deepline tools search portfolio --json` |
| The canonical domain for a company name | semantic web search | `deepline tools search search --json` |
| People at a known company by role and seniority | role-based contact waterfall (play) | `deepline plays search contact --json` |
| People matching a title and function across many companies | structured people search | `deepline tools search "people search" --json` |
| Reactors / commenters on a LinkedIn post | post-engagers play | `deepline plays search engagers --json` |
| Employees of a company when structured search is thin | Apify employee scraper actor | `deepline tools search apify --json` |

The right tool depends on what fact the user actually wants. If the user asks for "fintech companies hiring fraud engineers," the data needed is *funding round + headcount + HQ + active hiring evidence*, and the right primary source is a structured company search that returns growth metrics — not a generic web search and not a speculative AI-generated list.

## Durable rules

These rules apply across discovery work and are the difference between "agent built the list from real data" and "agent fell back to training-data names after tool friction."

### Discovery belongs in the play

Use `deepline tools execute` only to probe the live contract, count, or one sample row. The first provider call that contributes candidate companies or contacts should move into a play before you scale it. Discovery often needs supplementing, filtering, deduping, and downstream enrichment; putting those stages in one scratchpad play gives the run a replayable source of truth and lets the next run reuse completed steps instead of reparsing terminal JSON.

When `tools execute --json` returns `starter_script`, use it as the first draft of the discovery play. Keep the durable names stable as you add stages: candidate pull, evidence attachment, contact lookup, email waterfall, and final export.

### Companies first, then people

When a task requires finding contacts at companies that match an ICP, build the company set first, then find people at each company. Going straight to a broad people-search ("VPs of Marketing at fintechs") returns lower-quality candidates because the people-search filters are coarser than firmographic ones, and the people you get are scattered across companies you have not validated. The exception is when the user provides a specific named company list and only needs contacts.

### Pick the primary source by what data the user actually needs

This is the rule the v1 GTM workflow encoded and the v2 SDK skill missed. Map the user's data need to a primary source before reaching for tools. For "Series A/B US fintech, 50-500 employees, hiring fraud engineers":

- *Funding, headcount, HQ, industry/category* → structured company search (find one with `deepline tools search "company search" --json`).
- *Active hiring* → either a job-listing search (`deepline tools search "job search" --json`) or the growth metric on the structured search response (often a `growth_6m_percent`-style field, returned for free).

Trying every tool that mentions "company" in its name burns credits and produces inconsistent results across runs. Pick the primary source first, supplement gaps deliberately.

### Count before pulling

Before pulling pages of results, ask the source how many it has. Many providers expose a count endpoint or accept `limit: 1` as a cheap shape-and-size probe. *Failure mode:* pulling 100 results when the source only has 18 inflates cost without value, and pulling 25 when the source has 4,000 silently truncates without telling the user the breadth available. A count tells you whether your filter is in the right ballpark.

### Validate enum-like filters before the full pull

Filters that look like free text often validate against a closed enum on the provider side: industry codes, category strings, country codes, funding round labels. Sending `"financial services"` to a provider that expects `"Financial Services"` (or `54`, or `industry:financial-services`) silently returns zero results without an error. When the provider has an autocomplete or enum endpoint, use it on a sample value before the full search:

```bash
deepline tools search autocomplete --json
```

Confirm the relevant filter values resolve, then run the full query.

### ISO 3-letter country codes for HQ filters

Most structured company search providers want `USA`, `GBR`, `DEU`, not `"United States"`. The country filter is a particularly common silent-failure mode — the request succeeds, the result count is zero, the agent assumes "no companies match" instead of "the filter shape was wrong."

### Broad function + seniority for people search; exact titles for persona lookup at a known company

Two different patterns:

- **People search across many companies** ("VPs of Marketing at US fintechs"): use a broad functional category plus seniority, e.g. `function: ["Marketing"]` plus `seniority: ["VP", "Director"]`. Exact title arrays like `["VP of Marketing", "Vice President, Marketing", "VP Marketing"]` miss real titles because title spelling varies wildly.
- **Persona lookup at one known company** (`prebuilt/company-to-contact-by-role-waterfall`): exact title tokens are stronger when the user intent is specific (`CEO`, `CTO`, `Head of Security`). The play handles the small set of variants internally.

If you are calling a people-search tool directly across companies, lean broad-function. If you are calling a contact waterfall scoped to a single domain, lean exact-token.

### Over-provision then filter; do not restart on misses

Pull ~1.4× the target rows from the primary source. Each downstream stage (people-finding, email recovery, validation) has natural falloff (~15-20% per stage), so a 25-row target wants ~35 candidate rows in the first pull. When you have more than enough valid rows after filtering, stop. Restarting discovery to chase the last row almost never helps — the rows you cannot find usually have zero coverage across all providers, and the cost of restarting exceeds the value of one extra row.

### Filter, then supplement; do not re-discover

When a discovery pass returns mostly good rows and a few bad ones, drop the bad and supplement gaps from a second source. Do not throw out the result and re-run the primary search with different filters in the hope of getting a cleaner set — the noise is in the data, not the query.

### Source from API tools, not from training data

If the primary source returns nothing, the answer is *not* "I'll list the fintech companies I know." The answer is to widen the filter, switch the primary source, or tell the user the criteria returned zero. Pattern-completing companies from memory looks like a successful run and produces unverifiable rows.

### Do not salvage company discovery with domain-by-domain enrichment loops

For "build a list of N companies matching criteria" tasks, domain-by-domain enrichment is a verification or gap-fill step after you already have a candidate set. It is not a discovery strategy. If you catch yourself running repeated loops over hand-picked domains, stop and return to a provider-native company or job search with broader filters. This failure mode is slow, expensive, and tends to smuggle in companies from memory rather than from the requested filter set.

Hard stop: after two provider searches and one supplement pass, either write the valid rows you have with source evidence, broaden one filter and rerun the primary search, or report that the criteria were too narrow. Do not continue with ad-hoc domain lists.

## Patterns

### Fast path: constrained ICP company list

Use this path for prompts like "Build a list of 25 Series A/B US fintech and identity verification companies, 50-500 employees, actively hiring fraud/identity roles."

1. Use a structured company search as the primary candidate source. Prefer a provider that can filter by funding stage, headcount, country, and category in one call.
2. Pull about 1.4x the requested count, not dozens of pages.
3. Use a job search only to attach hiring evidence or supplement gaps. Group jobs by company; do not enrich arbitrary domains one at a time.
4. Write the CSV from provider rows, preserving `name`, `domain`, `headcount`, `funding_round`, `hq`, and a `hiring_evidence` field.

Example shape:

```bash
deepline tools search "company search funding headcount hq category" --json
deepline tools search "job search hiring role company domain" --json
deepline tools describe <company-tool-id> --json
deepline tools execute <company-tool-id> --payload '{"hq_country":"USA","funding_round":["Series A","Series B"],"employee_count":{"min":50,"max":500},"categories":["fintech","identity verification","fraud detection"],"limit":1}' --json
deepline plays check ./target-company-list.play.ts
deepline plays run ./target-company-list.play.ts --input '{"target_count":25}' --watch --out target_companies.csv
```

If the exact provider uses different field names, adapt the play payload to the described schema. Keep the strategy fixed: one primary company pull, one hiring-evidence pass, then CSV. The `limit: 1` call is only the shape probe; the 1.4x candidate pull belongs in the play.

### Companies by structured firmographic filters

The default for any "find me companies that match X criteria" request when X is firmographic (funding, headcount, HQ, industry).

```bash
# Find the live tool.
deepline tools search "company search" --json

# Confirm the input contract — what fields it accepts, what enums look like,
# what evidence columns it returns.
deepline tools describe <tool-id> --json

# Validate enum-like filters first (industry codes, country codes, etc.).
deepline tools execute <autocomplete-tool> --payload '{"field":"industry","query":"fintech"}' --json

# Probe count.
deepline tools execute <tool-id> --payload '{"hq_country":"USA","funding_round":["Series A","Series B"],"employee_count":{"min":50,"max":500},"limit":1}' --json

# Put the real pull (~1.4x target), filtering, and export in a play.
deepline plays check ./company-discovery.play.ts
deepline plays run ./company-discovery.play.ts --input '{"target_count":25}' --watch --out target_companies.csv
```

Preserve the response's evidence columns when writing the CSV. If the response includes `funding_round`, `last_funding_at`, `employee_count`, `growth_6m_percent`, `hq_city`, `hq_country`, `industry_codes`, `description`, keep them — they are the proof that justifies why each row is in the list.

### Companies hiring for a role

When the user wants "companies hiring fraud engineers" or similar role-specific hiring evidence, a job-listing search is the primary source.

```bash
deepline tools search "job search" --json
deepline tools describe <tool-id> --json
deepline tools execute <tool-id> --payload '{"job_title":"fraud engineer","company_size":{"min":50,"max":500},"hq_country":"USA","limit":1}' --json
deepline plays check ./hiring-signal-discovery.play.ts
deepline plays run ./hiring-signal-discovery.play.ts --input '{"target_count":25}' --watch --out companies_hiring.csv
```

Pull job listings, then group by company. Preserve the listing-level evidence (`hiring_role`, `hiring_url`, `hiring_posted_at`, `hiring_count`) because that is the proof.

When the user only needs *whether* a company is hiring (not for what role), the cheaper path is the growth metric on a firmographic search — many structured company-search providers return a `growth_6m_percent`-style field for free in the same response.

### Companies in a portfolio

When the source is a YC batch, an accelerator cohort, an investor's portfolio, or a curated list, the primary source is a portfolio-aware tool, not a firmographic search.

```bash
deepline tools search portfolio --json
deepline tools search "yc batch" --json
```

After pulling the portfolio list, hand off to a firmographic enrichment tool to add headcount / funding / industry to each row.

### Resolving a domain from a company name

A common helper. Domain lookup is mechanical — use a search tool, not `deeplineagent`.

```bash
deepline tools search search --json
deepline tools execute <search-tool-id> --payload '{"query":"\"Acme Corp\" official site","numResults":1}' --json
```

Extract the domain from the first result. For batch resolution inside a play, this is the rare case where a one-step `ctx.map` over `ctx.tool` is cleaner than a CLI script.

### People at known companies (persona lookup)

When you have a domain and want contacts at a specific role:

```bash
deepline plays search contact --json
deepline plays describe <play-name> --json
deepline plays run <play-name> --input '{"company_name":"Acme","domain":"acme.com","roles":"VP Marketing","seniority":"VP"}' --watch
```

For a list of companies → contacts, this is one of the cleanest cases for a small custom play with a single `ctx.map` stage. Read `jobs/enriching-and-researching.md` for the role-waterfall pattern.

### People search across companies

When you do not yet have a company list and want people directly:

```bash
deepline tools search "people search" --json
deepline tools describe <tool-id> --json
deepline tools execute <tool-id> --payload '{"function":"Marketing","seniority":["VP","Director"],"hq_country":"USA","limit":1}' --json
deepline plays check ./people-discovery.play.ts
deepline plays run ./people-discovery.play.ts --input '{"target_count":5}' --watch --out contacts.csv
```

Use broad function plus seniority, not exact titles. Companies-first is still preferred when ICP fit matters — broad people search lacks the firmographic filters to validate the ICP. If people search is the right primary source, make it the first stage of the scratchpad play, then add email enrichment and final export as later stages in the same play.

### Engagers on a LinkedIn post

When the user wants to qualify reactors on a post (a common inbound signal):

```bash
deepline plays search engagers --json
deepline plays describe <play-name> --json
deepline plays run <play-name> --input '{"post_url":"https://www.linkedin.com/posts/...","max_items":1000}' --watch
```

The output is a list of people — hand off to `jobs/enriching-and-researching.md` for ICP qualification (`deeplineagent` with a tier `jsonSchema`).

### Apify fallback for thin coverage

Structured providers can have sparse coverage for very small companies (<50 employees), niche verticals, or recent batches. When the primary source returns thin results and you have specific named companies, an Apify employee scraper or company scraper actor is the next step.

```bash
deepline tools search apify --json
deepline tools describe <tool-id> --json
```

Apify actors are slower than structured providers, which is why they are a fallback rather than the default first pass. Pull the full employee list for a target company, then filter for the persona — do not iterate through queries trying to coax more out of a structured provider that is genuinely empty for that target.

## Convergence and validation

### Stop at "good enough"

Define the target row count up front (usually from the user's ask). Pull ~1.4× that, filter, and stop when the filtered set hits the target. Past ~80% of target after filtering, marginal returns drop sharply — extra time spent chasing the last 20% almost never produces real rows.

### Dedup

Deduplicate by canonical key (domain for companies, LinkedIn URL or email for people). Run dedup *after* filtering, not before — filtering by canonical key first can drop valid rows whose key is missing from one of the merge sources.

### Verify with a second source for high-stakes signals

For job changes, recent funding, recent leadership moves, or other claims that decay quickly, verify with a second source before tagging confidence as `HIGH`. A single-source signal is `MEDIUM`; conflicting sources are `LOW`.

## Exit

- Discovery yielded a list of companies or contacts → `jobs/enriching-and-researching.md` to fill emails, phones, LinkedIn URLs, research columns.
- Discovery shape is right but the company set is wrong → re-pick the primary source above and re-run; do not rely on training data.
- A custom discovery play is failing replay-safety or has a stale set-live mismatch → `references/debugging.md`.
