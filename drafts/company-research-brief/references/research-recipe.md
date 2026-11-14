# The research recipe — phases, entity edge cases, schema, arms

Distilled from production company-overview builds (domain-anchored agent research
with structured output). Deepline tool IDs and prices confirmed
with `deepline tools describe` on 2026-09-30 — they drift, re-check before quoting.

## The three research phases (order is load-bearing)

1. **Domain anchoring — visit the domain first. Always. No exceptions.** Homepage,
   then /about, /product(s), /customers or /case-studies if linked. Non-English
   content gets translated, not abandoned. Only if the homepage fails to load fall
   back to `site:<domain>` searches. Everything in the brief keys off what this
   phase establishes.
2. **Third-party expansion** — only after phase 1 anchors the entity: the enrichment
   payload, LinkedIn company page, press/news (date-windowed), registries where
   relevant. Third-party facts that contradict the site are flags to surface, not
   silent overrides.
3. **Assembly** — structured output; empty strings for indeterminable fields (never
   "N/A" or prose filler); an anti-fabrication pass: is every filled field traceable
   to phase-1 or phase-2 evidence gathered THIS run?

## Pre-gate the anchor (free, before any paid fetch)

An unknown or suspect domain gets a free existence check BEFORE the first scrape: a
DNS resolution (any DNS tool) or a free `generic_http_request` GET (real HTTP
status, set a User-Agent). Observed on Clay's scrape action (2026-08): scraping a
nonexistent domain did not fail fast — the vendor waterfall ground past a 60-second
timeout, while the dead-anchor verdict was available for free in under a second.
NXDOMAIN / no-resolve → dead anchor, report, stop.

## Entity edge cases (the wrong-entity traps)

| Shape | Trap | Handling |
|---|---|---|
| Name collision | three companies share the name | domain wins; given only a name, present candidates before spend |
| Holding vs operating co | brief describes the parent, user means the operator | say which entity the domain hosts; note the hierarchy if visible |
| Franchise / regional clone | site is a local franchisee | brand vs operator called out explicitly |
| Rebrand / acquisition | old name redirects, memory says the old story | report the rebrand as a finding; brief the CURRENT entity |
| Parked / for-sale / dead domain | scrape returns bytes that aren't a company | dead anchor — report it, stop; never brief a parking page |
| Solo practitioner / tiny co | thin site, thin data | brief what exists; open-questions carries the rest — small ≠ fabricate |
| Name-boundary collisions | "Asana Partners" (real-estate firm), "MT Asana" (a ship) surfacing for account "Asana" — live-verified | exact-name boundary: the account name must not be a prefix of a longer org name or a vessel/product name; org-suffix tokens (Partners/Group/Capital/Holdings) after the name = different entity |
| Aggregator/database pages | funding-directory, stock-forecast, stock-roundup pages date-stamped like news | NOT events and NOT developments — a page about the company's history is not something that happened; exclude from developments, usable only as lookup leads |

## Brief schema (structured output)

```
identity:      cleaned_name · domain · entity_type · anchor_evidence
what_they_do:  description · primary_products_or_services · value_prop      [source: their site]
who_they_sell_to: icp · target_personas · target_industries                 [labeled inference]
firmographics: industry · headcount_band · hq · founded · company_type      [source: enrichment payload]
developments:  [{date · event · classification · source_url}]               [date-windowed]
open_questions: [what could not be established, and where it was looked for]
```

Empty string = looked, not found. Every filled field names its source class.

## Arms + mechanics

| Arm | Deepline price (describe, 2026-09-30) | Notes |
|---|---|---|
| Own web access / `firecrawl_scrape` | free / 0.02 credits per page base | `formats: ["markdown"]`, `onlyMainContent: true`. A scrape that returns content does not prove the page exists — check status with `generic_http_request` (free) when it matters; a 404 can render as content |
| `crustdata_v3_company_identify` | free | name/domain → candidate companies; use it to surface collisions before spend |
| `crustdata_v3_company_enrich` | 0.8 per result | `domains: ["<domain>"]`, `fields: ["basic_info","headcount","funding","locations"]` (omitted `fields` returns only `basic_info`). `basic_info.employee_count_range` is a band string; match identity on `basic_info.website` / `primary_domain` / `all_domains`. `funding.last_round_type`, `last_fundraise_date`, `total_investment_usd`; `locations.headquarters`. The `news` field group returns dated articles (`article_publish_date`, `article_url`) at no extra tool |
| News: `predictleads_company_news_events` | 0.56 per call | `company_id_or_domain`, `found_at_from` / `found_at_until` as absolute dates, optional `categories`; events are pre-classified (launches, hires, expansions, partnerships, funding). Route events with no effective date out of the dated list |
| News fallback: `serper_google_search` with `tbs: "qdr:m"` | 0.02 per result | relative-bucket windows and RELATIVE date strings ("3 weeks ago") — parse to absolute, post-filter to the window; a quiet company returns organic noise, not news |

Standard brief = anchor (free to a few cents) + company enrich (0.8) + news (0.56)
≈ 1.5 Deepline credits; state before running. Read actual charges from
`deepline billing usage` after the run.
