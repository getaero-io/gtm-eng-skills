---
name: portfolio-prospecting
description: "Find companies backed by a specific investor or accelerator, then find contacts and build personalized outbound."
---

# Portfolio/VC Prospecting

Find companies backed by a specific investor or accelerator (YC, a16z, Sequoia, etc.), then find contacts and build personalized outbound.

## Core insight: VC portfolio data is public

Every major VC and accelerator publishes their portfolio online. **Do NOT waste turns trying to discover portfolio companies through Deepline search tools.** Instead, fetch the public portfolio page directly and extract company names from it. This is faster, cheaper, and more complete than any provider-based approach.

## What NOT to do

Tested and failed: Apollo investor filtering (irrelevant results), people-first then verify investor (~7-9% hit rate, wastes 60-80% of turns), Crustdata `crunchbase_investors` (inconsistent), `deeplineagent` per-row investor verification (~5-10s/row, unacceptable at scale)

## Proven approach

**Step 1: Get the company list from the VC's public portfolio.** Common URLs: YC (`ycombinator.com/companies`), a16z (`a16z.com/portfolio`), Sequoia (`sequoiacap.com/our-companies`), Greylock/Benchmark (`/portfolio`).

```bash
# Fetch YC companies page (or use parallel_extract if JS-rendered)
curl -sS "https://www.ycombinator.com/companies" -H "Accept: text/html" -o $WORKDIR/yc_page.html

deepline tools execute parallel_extract --payload '{"urls":["https://www.ycombinator.com/companies?batch=W26"],"objective":"Extract all company names, website domains, and one-line descriptions from this YC batch directory page","full_content":true}'
```

**Step 2: Filter to companies hiring your target role (optional).**

```bash
deepline enrich --input yc_companies.csv --in-place --rows 0:2 \
  --with '{"alias":"exa_jobs","tool":"exa_search","payload":{"query":"GTM Engineer site:ycombinator.com","numResults":50,"type":"auto"}}'
```

**Step 3: Find contacts at each company.**

Use guidance in [enriching-and-researching.md](../enriching-and-researching.md) for this

**Step 4: Find emails via waterfall.**

Use guidance in [enriching-and-researching.md](../enriching-and-researching.md) for this

**Step 5: Generate personalized email copy** with `deeplineagent` and `jsonSchema`. If the row still needs fresh web lookup, do that in the same `deeplineagent` step or in a separate research pass first. Pilot on rows `0:2`, then run the full batch.

Use guidance in [writing-outreach.md](../writing-outreach.md)

## Common pitfalls

| Pitfall                                                       | What happens                                                            | Fix                                                     |
| ------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------- |
| Trying to discover portfolio companies via Deepline tools     | Wastes 60-80% of turn budget on company discovery                       | Fetch the public portfolio page directly                |
| Using old `json_mode` fields from retired local AI docs       | New AI tools ignore that contract and structured output drifts or fails | Pass a `jsonSchema` object to `deeplineagent`           |
| Searching with strict titles at small startups                | 0 results — person hasn't been hired yet                                | Remove title filter, get broader roles, pick best match |
| Using Hunter as primary email finder for <50 person companies | 0/25 fill rate                                                          | Use LeadMagic first — better small-company coverage     |
