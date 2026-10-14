---
name: portfolio-prospecting
description: 'Find companies backed by a specific investor or accelerator, then find contacts and build personalized outbound.'
---

# Portfolio/VC Prospecting

Find companies backed by a specific investor or accelerator (YC, a16z, Sequoia, etc.), then find contacts and build personalized outbound.

## Core insight: VC portfolio data is public

Every major VC and accelerator publishes their portfolio online. **Do NOT waste turns trying to discover portfolio companies through Deepline search tools.** Instead, fetch the public portfolio page directly and extract company names from it. This is faster, cheaper, and more complete than any provider-based approach.

## What NOT to do

Tested and failed: provider-side investor filtering on generic prospecting databases (irrelevant results), people-first then verify investor (~7-9% hit rate, wastes 60-80% of turns), `deeplineagent` per-row investor verification (~5-10s/row, unacceptable at scale)

## Proven approach

**Step 1: Get the company list from the VC's public portfolio.** Common URLs: YC (`ycombinator.com/companies`), a16z (`a16z.com/portfolio`), Sequoia (`sequoiacap.com/our-companies`), Greylock/Benchmark (`/portfolio`).

```bash
curl -sS "https://www.ycombinator.com/companies" -H "Accept: text/html" -o $WORKDIR/yc_page.html
```

If the page is JavaScript-rendered, find a page-extraction tool and give it the URL and what to extract:

```bash
deepline search "JavaScript-rendered portfolio page URL -> company names and website domains"
```

**Step 2: Filter to companies hiring your target role (optional).**

Search the accelerator's job board for the role with a web search tool
(`deepline search "search query -> web results"`), for example `GTM Engineer site:ycombinator.com`.

For per-company filtering across the whole list, add this as a column in a custom play (`deepline plays --help`).

**Step 3: Find contacts at each company.**

Put the companies in a CSV and run `prebuilt/company-to-contact-batch` over it for the
target role; `deepline describe prebuilt/company-to-contact-batch` shows its columns.

**Step 4: Find emails via waterfall.**

Run `prebuilt/person-to-email-batch` over the contacts: each row tries its LinkedIn profile
first, then name and company domain.

**Step 5: Generate personalized email copy** with `deeplineagent` and `jsonSchema`. If the row still needs fresh web lookup, do that in the same `deeplineagent` step or in a separate research pass first, within the authorized scope. For a new large batch, use a CSV-aware 2-3-row pilot before scaling; do not duplicate a small supplied Play.

Use guidance in [writing-outreach.md](../writing-outreach.md)

## Common pitfalls

| Pitfall                                                   | What happens                                                            | Fix                                                     |
| --------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------- |
| Trying to discover portfolio companies via Deepline tools | Wastes 60-80% of turn budget on company discovery                       | Fetch the public portfolio page directly                |
| Using old `json_mode` fields from retired local AI docs   | New AI tools ignore that contract and structured output drifts or fails | Pass a `jsonSchema` object to `deeplineagent`           |
| Searching with strict titles at small startups            | 0 results — person hasn't been hired yet                                | Remove title filter, get broader roles, pick best match |
