---
name: build-tam
description: |
  Build a Total Addressable Market (TAM) list using ICP filters. Find all companies
  and contacts that match your ideal customer profile across multiple data providers.
  Can translate niche-signal-discovery report output directly into Apollo search criteria.

  Triggers:
  - "build my TAM"
  - "total addressable market"
  - "find all companies that match my ICP"
  - "how many companies fit my criteria"
  - "build a prospect list from scratch"
  - "turn this ICP report into a lead list"
  - "find leads matching these signals"

  Requires: Deepline CLI — https://code.deepline.com
---

# Build TAM

Use this skill to size and build your total addressable market from ICP filters. Start with a count (virtually free), then pull the actual list.

**If you have a niche-signal-discovery report**, jump to [Signal-Driven TAM](#signal-driven-tam-from-niche-signal-discovery-report) — every signal type maps directly to Apollo search parameters.

## Step 1: Size your TAM first (virtually free)

Set `per_page: 1` — most providers return the total count but only charge for 1 result. This lets you validate your filters before spending credits on a full pull.

```bash
deepline tools execute apollo_people_search \
  --payload '{
    "person_titles": ["VP Sales", "Head of Revenue"],
    "include_similar_titles": true,
    "organization_num_employees_ranges": ["51,200", "201,500"],
    "qOrganizationKeywordTags": ["technology"],
    "per_page": 1,
    "page": 1
  }' --json
```

Look for `total_people` in the response to see your TAM size before pulling.

## Step 2: Company-first TAM

```bash
# Size first
deepline tools execute apollo_company_search \
  --payload '{
    "qOrganizationKeywordTags": ["technology"],
    "organization_num_employees_ranges": ["51,200"],
    "per_page": 1,
    "page": 1
  }' --json

# Pull list (100 per page)
deepline tools execute apollo_company_search \
  --payload '{
    "qOrganizationKeywordTags": ["technology"],
    "organization_num_employees_ranges": ["51,200"],
    "per_page": 100,
    "page": 1
  }' --json
```

## Step 3: Contact-first TAM

```bash
deepline tools execute apollo_people_search \
  --payload '{
    "person_titles": ["VP Sales", "CRO", "Head of Revenue Operations"],
    "include_similar_titles": true,
    "organization_num_employees_ranges": ["51,200", "201,1000"],
    "qOrganizationKeywordTags": ["technology"],
    "person_locations": ["United States"],
    "per_page": 100,
    "page": 1
  }' --json
```

## Step 4: Prioritize your TAM with signals

Don't outreach to the entire TAM — prioritize with real signals first. Use the `niche-signal-discovery` skill if you have won/lost data to build a scoring model. Otherwise, enrich with first-party signals:

```bash
# Job listings (hiring = budget + pain)
deepline enrich --input tam.csv --in-place --rows 0:1 \
  --with 'jobs=crustdata_job_listings:{"companyDomains":"{{Domain}}","limit":20}'

# Website content (multi-page discovery)
deepline enrich --input tam.csv --in-place --rows 0:1 \
  --with 'website=exa_search:{"query":"company product features integrations pricing careers about","numResults":5,"type":"auto","includeDomains":["{{Domain}}"],"contents":{"text":{"maxCharacters":2000,"verbosity":"compact","includeSections":["body"]}}}'
```

Then score using signals from job listings (hiring relevant roles), tech stack (integration readiness), and website content (pain language, compliance maturity).

---

## Signal-Driven TAM (from niche-signal-discovery report)

When you have a completed `niche-signal-discovery` report, every signal type translates directly into search criteria. The report provides:

- **Job title signals** → Apollo `person_titles`
- **Keyword signals** → Apollo `qOrganizationKeywordTags`
- **Tech stack signals** → Apollo `qOrganizationKeywordTags` or tech stack filters
- **Firmographic signals** → Apollo `organization_num_employees_ranges`, `person_locations`
- **Anti-fit signals** → Exclusion criteria (skip companies matching these)
- **Job listing keywords** → Crustdata `job_listings` search for post-pull verification

### Critical: Widen Filters to Avoid Missing Won Companies

**Tested against 3 known Closed Won customers — all 3 were missed with narrow filters.** Root causes and fixes:

1. **Employee range too narrow** — Won customers ranged from 40 to 400 employees. Use the widest range from your won data, not just the report median. Include `"11,50"` and `"51,200"` alongside larger ranges.
2. **"Free trial" anti-fit is too aggressive** — Many B2B SaaS companies use hybrid PLG + sales-led models (free trial for self-serve, contact sales for enterprise). A "free trial" on the pricing page does NOT mean they don't need GTM tooling. Remove from anti-fit or reduce penalty significantly.
3. **Competitor mentions ≠ tool usage** — If a company COMPETES with an anti-fit tool (e.g., Mixmax mentions "Salesloft" on comparison pages), that's competitive positioning, not tech stack adoption. Anti-fit signals should only apply to companies that USE the tool, not companies that sell against it. Always check the page context.
4. **Seller signals ≠ buyer signals** — When a company's website mentions keywords like "ABM", "ICP", "RevOps" on product/feature pages, they're SELLING to that persona, not buying. Only count keywords from job listings and operational content (careers, blog posts about internal challenges) as buyer signals.
5. **Job listing signals favor larger companies** — Smaller won companies (40-150 employees) have fewer/different job listings, so they score low on job-keyword scoring. Use website signals (SOC 2, contact sales CTA, tech stack) alongside job signals for balanced scoring.

### Signal → Search Parameter Mapping

| Report Signal Type | Apollo Parameter | How to Extract | Example |
|--------------------|-----------------|----------------|---------|
| Job titles with lift > 2x | `person_titles` | Use title patterns from Section 4 (Job Role Analysis) | "RevOps" at 2.56x → `["Revenue Operations", "RevOps", "Head of RevOps"]` |
| Keywords with lift > 2x | `qOrganizationKeywordTags` | Use keywords from Section 2 (Website Keyword Differential) | "ABM" at 3.67x → `["account based marketing", "ABM"]` |
| Tech stack tools with lift > 2x | `qOrganizationKeywordTags` | Use tool names from Section 3 (Tech Stack Analysis) | Gainsight at 3.0x → `["gainsight"]` |
| Employee headcount ranges | `organization_num_employees_ranges` | Use FULL range from won data, not just median | Won from 40-2300 → `["11,50", "51,200", "201,500", "501,1000", "1001,5000"]` |
| Geography | `person_locations` | If report mentions geo patterns | US-focused → `["United States"]` |
| Anti-fit tech stack | Post-pull exclusion | Tech with lift < 0.5x — verify USAGE not competitor mentions | Salesloft at 0.33x → check if company USES it (integrations page), not just mentions it (comparison pages) |

### Step-by-step: Report → Lead List

**1. Extract buyer personas from Section 0.4:**

The report's "Buyer Persona Quick Reference" table gives you ready-to-use title patterns with lift data. Map each persona to an Apollo search:

```bash
# Example: RevOps Leader persona (2.56x lift, 55% of won companies)
# NOTE: Use wide employee range — won customers ranged from 40 to 2300+
deepline tools execute apollo_people_search \
  --payload '{
    "person_titles": ["Revenue Operations", "RevOps", "Head of Revenue Operations"],
    "include_similar_titles": true,
    "person_seniorities": ["vp", "director", "manager"],
    "qOrganizationKeywordTags": ["b2b saas"],
    "organization_num_employees_ranges": ["11,50", "51,200", "201,500", "501,1000", "1001,5000"],
    "person_locations": ["United States"],
    "per_page": 1,
    "page": 1
  }' --json
```

**2. Extract keyword-based company searches from Section 2:**

High-lift keywords from the report become `qOrganizationKeywordTags`:

```bash
# Example: Companies tagged with ABM (3.67x lift)
deepline tools execute apollo_company_search \
  --payload '{
    "qOrganizationKeywordTags": ["account based marketing", "b2b saas"],
    "organization_num_employees_ranges": ["11,50", "51,200", "201,500", "501,1000", "1001,5000"],
    "per_page": 1,
    "page": 1
  }' --json
```

**3. Search by tech stack signals from Section 3:**

Tech stack tools with high lift → find companies using those tools:

```bash
# Example: Companies using Gainsight (3.0x lift)
deepline tools execute apollo_company_search \
  --payload '{
    "qOrganizationKeywordTags": ["gainsight", "b2b saas"],
    "organization_num_employees_ranges": ["11,50", "51,200", "201,500", "501,1000"],
    "per_page": 1,
    "page": 1
  }' --json
```

**4. Verify with job listing keywords (post-pull enrichment):**

The highest-lift signals are often job-specific keywords (e.g., "fragmented" at 13x, "ICP" at 9x, "intent data" at 9x). These can't be used as Apollo filters — use them for post-pull verification via Crustdata:

```bash
deepline enrich --input tam.csv --in-place --rows 0:1 \
  --with 'jobs=crustdata_job_listings:{"companyDomains":"{{Domain}}","limit":50}'
```

Then search job listing text for high-lift keywords:

```python
# Score each company using BOTH job listing keywords AND website signals
# Tested against known won customers — job-only scoring misses smaller companies
import csv, json, sys
csv.field_size_limit(sys.maxsize)

# Job listing keywords (highest intent — company is actively hiring for these)
JOB_KEYWORDS = {
    "fragmented": 15,           # 13x lift
    "ICP": 12,                  # 9x lift
    "intent data": 12,          # 9x lift
    "data hygiene": 7,          # 7x lift
    "ABM": 8,                   # 3.67x lift
    "data infrastructure": 7,   # 3.29x lift
    "revenue operations": 8,    # 2.45x lift
}

# Website signals (check pricing/security pages — works for companies of ALL sizes)
WEBSITE_KEYWORDS = {
    "contact sales": 8,     # 3.67x lift — enterprise sales motion
    "SOC 2": 5,             # 2.6x lift — security maturity
    "SAML": 5,              # 2.6x lift — enterprise readiness
}

# Anti-fit: ONLY apply to companies that USE these tools (check integrations page),
# NOT companies that COMPETE with them (comparison/vs pages).
# Reduced "free trial" penalty — many B2B SaaS use hybrid PLG+sales models.
ANTI_FIT_JOBS = {
    "data cleansing": -5,   # 0.33x lift — different pain point
}

with open('tam.csv') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    jobs_text = (row.get('jobs', '') or '').lower()
    website_text = (row.get('website', '') or '').lower()

    # Job signals (strongest — hiring = budget + active pain)
    score = sum(pts for kw, pts in JOB_KEYWORDS.items() if kw.lower() in jobs_text)

    # Website signals (works for small companies without many job listings)
    score += sum(pts for kw, pts in WEBSITE_KEYWORDS.items() if kw.lower() in website_text)

    # Anti-fit (jobs only — website anti-fit requires page-context checking)
    score += sum(pts for kw, pts in ANTI_FIT_JOBS.items() if kw.lower() in jobs_text)

    row['signal_score'] = score

# Filter to Tier 1 (score >= 30) and Tier 2 (15-29)
# Thresholds lowered from 60/35 — smaller won companies score 15-25 on website signals alone
tier1 = [r for r in rows if int(r.get('signal_score', 0)) >= 30]
tier2 = [r for r in rows if 15 <= int(r.get('signal_score', 0)) < 30]
```

**5. Apply anti-fit exclusions (with context checking):**

Check the report's anti-fit signals (Section 0.2, lift < 0.5x), but **always verify the context** before excluding:

```bash
# Anti-fit check 1: "free trial" (0.33x lift)
# IMPORTANT: Many B2B SaaS use hybrid PLG + sales-led models.
# Only exclude if the company is PURELY PLG with no enterprise motion.
# If they also have "contact sales" or enterprise pricing → NOT anti-fit.
site:domain.com "free trial"
site:domain.com "contact sales" OR "enterprise"  # Check for enterprise motion

# Anti-fit check 2: "salesloft" (0.33x lift)
# CRITICAL: Distinguish USAGE from COMPETITION.
# - Integrations page or tech stack: company USES Salesloft → anti-fit
# - Comparison page, "vs", "alternative": company COMPETES with Salesloft → NOT anti-fit
# - Case study about switching FROM Salesloft → NOT anti-fit (actually positive)
site:domain.com "salesloft" -inurl:vs -inurl:alternative -inurl:comparison
```

**Anti-fit false positive checklist:**

| Context | Is it anti-fit? | Example |
|---------|----------------|---------|
| Tool listed on integrations/tech stack page | **Yes** — company USES this tool | "We integrate with Salesloft" |
| Tool on a "vs" or comparison page | **No** — company COMPETES with this tool | "Mixmax vs Salesloft" |
| Tool in a case study about switching away | **No** — company LEFT this tool | "We switched from Salesloft to..." |
| "Free trial" + "Contact sales" both present | **No** — hybrid PLG model, enterprise motion exists | Air has free trial AND enterprise tier |
| "Free trial" only, no enterprise pricing | **Likely yes** — purely PLG, less need for GTM tooling | Consumer SaaS with only self-serve |

### Building a combined TAM from multiple signal searches

Run one search per buyer persona, deduplicate, then score:

```bash
# Search 1: RevOps buyers
# Wide employee range — won customers ranged from 40 to 2300+ employees
deepline tools execute apollo_people_search \
  --payload '{"person_titles":["Revenue Operations","RevOps"],"include_similar_titles":true,"person_seniorities":["vp","director","manager"],"qOrganizationKeywordTags":["b2b saas"],"organization_num_employees_ranges":["11,50","51,200","201,500","501,1000","1001,5000"],"per_page":100,"page":1}' --json > tam-revops.json

# Search 2: BizOps buyers
deepline tools execute apollo_people_search \
  --payload '{"person_titles":["Business Operations","BizOps","Head of Operations"],"include_similar_titles":true,"person_seniorities":["vp","director","manager"],"qOrganizationKeywordTags":["b2b saas"],"organization_num_employees_ranges":["11,50","51,200","201,500","501,1000","1001,5000"],"per_page":100,"page":1}' --json > tam-bizops.json

# Search 3: Data/Analytics buyers
deepline tools execute apollo_people_search \
  --payload '{"person_titles":["Head of Data","VP Analytics","Analytics Engineering"],"include_similar_titles":true,"person_seniorities":["vp","director","manager"],"qOrganizationKeywordTags":["b2b saas","data infrastructure"],"organization_num_employees_ranges":["11,50","51,200","201,500","501,1000","1001,5000"],"per_page":100,"page":1}' --json > tam-data.json
```

Merge the JSON outputs into a single CSV, deduplicate by company domain, then run the job listing enrichment + scoring pipeline above.

---

## Common ICP filter parameters (Apollo)

| Filter | Parameter | Example values |
|---|---|---|
| Job title | `person_titles` | `["VP Sales", "Head of GTM"]` |
| Similar titles | `include_similar_titles` | `true` |
| Headcount | `organization_num_employees_ranges` | `["51,200", "201,500"]` |
| Industry/keywords | `qOrganizationKeywordTags` | `["technology", "SaaS", "fintech"]` |
| Geography | `person_locations` | `["United States", "Canada"]` |
| Revenue | `revenue_range` | `{"min": 1000000, "max": 50000000}` |
| Seniority | `person_seniorities` | `["c_suite", "vp", "director", "manager"]` |

Valid seniority values: `c_suite`, `vp`, `director`, `manager`, `senior`, `entry`, `owner`, `partner`

## Pagination

Apollo returns up to 100 results per page. For large TAMs:

```bash
# Page 1
deepline tools execute apollo_people_search --payload '{"per_page": 100, "page": 1, ...}' --json

# Page 2
deepline tools execute apollo_people_search --payload '{"per_page": 100, "page": 2, ...}' --json
```

## Cost estimation

| Operation | Credits per call | Notes |
|-----------|-----------------|-------|
| `apollo_people_search` (per_page: 1) | ~0.01 | Sizing — nearly free |
| `apollo_people_search` (per_page: 100) | ~1 | Full pull |
| `apollo_company_search` (per_page: 100) | ~1 | Full pull |
| `crustdata_job_listings` | ~1 | Per company |
| `exa_search` with contents | ~5 | Per company |

Size first with `per_page: 1`, then calculate: `total_pages x credits_per_page`.

## Tips

- Always check `total_people` or `total_entries` with `per_page: 1` before pulling
- Start narrow (tight ICP), validate quality, then widen filters
- Use `person_locations` to segment by geo for personalized campaigns
- Spot-check 5-10 results after pulling to verify filter quality before scaling
- After pulling, prioritize with signal discovery before email enrichment
- Add `person_seniorities` to avoid noisy results from individual contributors

## Pipeline next steps

After building your TAM:

1. **Score accounts** → Use `niche-signal-discovery` skill if you have won/lost data
2. **Find contacts** → Use `get-leads-at-company` skill to find decision-makers
3. **Get emails** → Use `contact-to-email` skill to enrich with verified emails
4. **Resolve LinkedIn** → Use `linkedin-url-lookup` skill for LinkedIn URLs

## Get started

Sign up and get your API key at [code.deepline.com](https://code.deepline.com).

```bash
npm install -g @deepline/cli
deepline auth login
```
