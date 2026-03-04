---
name: build-tam
disable-model-invocation: true
description: |
  Build a Total Addressable Market (TAM) list using ICP filters. Find all companies
  and contacts that match your ideal customer profile across multiple data providers.
  Can translate niche-signal-discovery report output directly into provider search criteria.

  Read gtm-meta-skill to guide how to use this skill. If you don't you will get this question wrong. 
---


!!! important!!!
> Start here first: read `gtm-meta-skill` before running this skill.
> On completion, follow `gtm-meta-skill` Section 7 for proactive issue feedback and the session-sharing Yes/No consent step.

You will likely fail before reading gtm-meta-skill, because that skill has all the specifications for the providers + wayyy more filters and how to trigger them using the deepline cli, which you are already connected to. 

> Start here first: read `gtm-meta-skill` before running this skill.
> On completion, follow `gtm-meta-skill` Section 7 for proactive issue feedback and the session-sharing Yes/No consent step.

You will likely fail before reading gtm-meta-skill, because that skill has all the specifications for the providers + wayyy more filters and how to trigger them using the deepline cli, which you are already connected to. 


# Build TAM

Use this skill to size and build your total addressable market from ICP filters. Start with a count (virtually free), then pull the actual list.

**If you have a niche-signal-discovery report**, jump to [Signal-Driven TAM](#signal-driven-tam-from-niche-signal-discovery-report) — every signal type maps directly to Dropleads search parameters.

## Step 1: Size your TAM first (virtually free)

Use `json_file` output for sizing so totals are extractable with the same pattern:

```bash
JSON_OUTPUT=$(deepline tools execute <tool> --payload '<payload>' --payload-output-format json_file)
PAYLOAD_FILE=$(printf '%s' "$JSON_OUTPUT" | jq -r '.payload_file')
jq '<total_path>' "$PAYLOAD_FILE"
```

## Count-capable providers (verified; all have a direct total path)

Use these when you want fast sizing before doing the full list pull.

| Provider | Tool | Executable command (query + total extraction) |
|---|---|---|
| Apollo | `apollo_search_people` | `JSON=$(deepline tools execute apollo_search_people --payload '{"page":1,"per_page":1}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.total_entries' "$FILE"` |
| Apollo | `apollo_people_search_paid` | `JSON=$(deepline tools execute apollo_people_search_paid --payload '{"q_keywords":"sales","per_page":1,"page":1}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.pagination.total_entries' "$FILE"` |
| Dropleads | `dropleads_get_lead_count` | `JSON=$(deepline tools execute dropleads_get_lead_count --payload '{"filters":{"jobTitles":["CEO"],"industries":["Technology"]}}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.count' "$FILE"` |
| Dropleads | `dropleads_search_people` | `JSON=$(deepline tools execute dropleads_search_people --payload '{"filters":{"jobTitles":["VP Sales"],"industries":["Technology"]},"pagination":{"page":1,"limit":1}}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.pagination.total // .result.data.total' "$FILE"` |
| Forager | `forager_organization_search_totals` | `JSON=$(deepline tools execute forager_organization_search_totals --payload '{"industries":[1]}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.total_search_results' "$FILE"` |
| Forager | `forager_job_search_totals` | `JSON=$(deepline tools execute forager_job_search_totals --payload '{"title":"\"Sales Engineer\""}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.total_search_results' "$FILE"` |
| Forager | `forager_person_role_search_totals` | `JSON=$(deepline tools execute forager_person_role_search_totals --payload '{"role_title":"\"Software Engineer\""}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.total_search_results' "$FILE"` |
| Icypeas | `icypeas_count_people` | `JSON=$(deepline tools execute icypeas_count_people --payload '{"query":{"currentJobTitle":{"include":["CTO"]}}}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.total' "$FILE"` |
| Prospeo | `prospeo_search_person` | `JSON=$(deepline tools execute prospeo_search_person --payload '{"person_job_title":{"include":["VP Sales"]},"page":1}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.pagination.total_count' "$FILE"` |
| Prospeo | `prospeo_search_company` | `JSON=$(deepline tools execute prospeo_search_company --payload '{"company":{"names":{"include":["Intercom"]},"websites":{"include":["intercom.com"]}},"page":1}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.pagination.total_count' "$FILE"` |
| Hunter | `hunter_email_count` | `JSON=$(deepline tools execute hunter_email_count --payload '{"domain":"stripe.com"}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.total' "$FILE"` |
| Hunter | `hunter_discover` | `JSON=$(deepline tools execute hunter_discover --payload '{"query":"B2B SaaS companies","limit":1}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data[0].emails_count.total' "$FILE"` |
| People Data Labs | `peopledatalabs_person_search` | `JSON=$(deepline tools execute peopledatalabs_person_search --payload '{"query":{"bool":{"must":[{"term":{"location_country":"United States"}},{"term":{"job_title_role":"marketing"}}]},"size":1}}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.total' "$FILE"` |
| CrustData | `crustdata_people_search` | `JSON=$(deepline tools execute crustdata_people_search --payload '{"companyDomain":"notion.so","titleKeywords":["VP","Head"],"limit":1}' --payload-output-format json_file); FILE=$(printf '%s' "$JSON" | jq -r '.payload_file'); jq '.result.data.meta.totalCount' "$FILE"` |

Optional ad-hoc CSV output for quick visual checks:

```bash
deepline tools execute apollo_search_people \
  --payload '{"q_keywords":"engineering","page":1,"per_page":1}' \
  --payload-output-format csv_file
```

Notes:

- Some providers need an actual page pull (`prospeo`, `dropleads` people/search-style) instead of dedicated count tools; still run with very small `page/per_page` first.
- CrustData `companydb_search` / `persondb_search` currently did not surface a reliable top-level total in successful probes, so use those for retrieval and not total sizing.
- For budget safety, always compare `total_count`/`total` with your filter set and stop early when a slice is enough for validation.

## Step 2: Company-first TAM

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

## Step 3: Contact-first TAM

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

- **Job title signals** → Dropleads `jobTitles`
- **Keyword signals** → Dropleads `keywords` and `industries`
- **Tech stack signals** → Dropleads `technologies` and `keywords`
- **Firmographic signals** → Dropleads `employeeRanges`, `personalCountries`
- **Anti-fit signals** → Exclusion criteria (skip companies matching these)
- **Job listing keywords** → Crustdata `job_listings` search for post-pull verification

### Signal → Search Parameter Mapping

| Report Signal Type | Dropleads Parameter | How to Extract | Example |
|--------------------|-----------------|----------------|---------|
| Job titles with lift > 2x | `jobTitles` | Use title patterns from Section 4 (Job Role Analysis) | "RevOps" at 2.56x → `["Revenue Operations", "RevOps", "Head of RevOps"]` |
| Keywords with lift > 2x | `q_organization_keyword_tags` | Use keywords from Section 2 (Website Keyword Differential) | "ABM" at 3.67x → `["account based marketing", "ABM"]` |
| Tech stack tools with lift > 2x | `q_organization_keyword_tags` | Use tool names from Section 3 (Tech Stack Analysis) | Gainsight at 3.0x → `["gainsight"]` |
| Employee headcount ranges | `employeeRanges` | From Section 0.1 TLDR or Section 1 Executive Summary | "200-1,500 employees" → `["201-500", "501-1000", "1001-5000"]` |
| Geography | `personalCountries` | If report mentions geo patterns | US-focused → `{"include": ["United States"]}` |
| Anti-fit tech stack | Exclude from results | Tech stack with lift < 0.5x | Salesloft at 0.33x → skip companies using Salesloft |

### Step-by-step: Report → Lead List

**1. Extract buyer personas from Section 0.4:**

The report's "Buyer Persona Quick Reference" table gives you ready-to-use title patterns with lift data. Map each persona to a Dropleads search:

```bash
# Example: RevOps Leader persona (2.56x lift, 55% of won companies)
deepline tools execute dropleads_search_people \
  --payload '{
    "filters": {
      "jobTitles": ["Revenue Operations", "RevOps", "Head of Revenue Operations"],
      "seniority": ["VP", "Director", "Manager"],
      "keywords": ["b2b saas"],
      "employeeRanges": ["201-500", "501-1000", "1001-5000"],
      "personalCountries": {"include": ["United States"]}
    },
    "pagination": {"page": 1, "limit": 1}
  }'
```

**2. Extract keyword-based company searches from Section 2:**

High-lift keywords from the report become `q_organization_keyword_tags`:

```bash
# Example: ABM-lift role/title filters with matching people slice
deepline tools execute dropleads_search_people \
  --payload '{
    "filters": {
      "keywords": ["account based marketing", "b2b saas"],
      "jobTitles": ["Revenue Operations", "Head of GTM", "VP Sales"],
      "employeeRanges": ["201-500", "501-1000", "1001-5000"]
    },
    "pagination": {"page": 1, "limit": 1}
  }'
```

**3. Search by tech stack signals from Section 3:**

Tech stack tools with high lift → find companies using those tools:

```bash
# Example: Tech-stack-lift filter with people retrieval
deepline tools execute dropleads_search_people \
  --payload '{
    "filters": {
      "keywords": ["gainsight", "b2b saas"],
      "jobTitles": ["VP Engineering", "Head of RevOps", "Head of Operations"],
      "employeeRanges": ["201-500", "501-1000"]
    },
    "pagination": {"page": 1, "limit": 1}
  }'
```

**4. Verify with job listing keywords (post-pull enrichment):**

The highest-lift signals are often job-specific keywords (e.g., "fragmented" at 13x, "ICP" at 9x, "intent data" at 9x). These can't be used as person-search filters — use them for post-pull verification via Crustdata:

```bash
deepline enrich --input tam.csv --in-place --rows 0:1 \
  --with 'jobs=crustdata_job_listings:{"companyDomains":"{{Domain}}","limit":50}'
```

Then search job listing text for high-lift keywords:

```python
# Score each company based on job listing keywords from the niche-signal report
import csv, json, sys
csv.field_size_limit(sys.maxsize)

SIGNAL_KEYWORDS = {
    "fragmented": 15,     # 13x lift
    "ICP": 12,            # 9x lift
    "intent data": 12,    # 9x lift
    "data hygiene": 7,    # 7x lift
    "ABM": 8,             # 3.67x lift
    "data infrastructure": 7,  # 3.29x lift
    "revenue operations": 8,   # 2.45x lift
}
ANTI_FIT = {
    "free trial": -15,
    "salesloft": -10,
}

with open('tam.csv') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    jobs_text = (row.get('jobs', '') or '').lower()
    score = sum(pts for kw, pts in SIGNAL_KEYWORDS.items() if kw.lower() in jobs_text)
    score += sum(pts for kw, pts in ANTI_FIT.items() if kw.lower() in jobs_text)
    row['signal_score'] = score

# Filter to Tier 1 (score >= 60) and Tier 2 (35-59)
tier1 = [r for r in rows if int(r.get('signal_score', 0)) >= 60]
tier2 = [r for r in rows if 35 <= int(r.get('signal_score', 0)) < 60]
```

**5. Apply anti-fit exclusions:**

Check the report's anti-fit signals (Section 0.2, lift < 0.5x) and skip companies matching them:

```bash
# Verify a specific company doesn't have anti-fit signals
# Check website for "free trial" (0.33x lift — PLG-first, less need for GTM tooling)
site:domain.com "free trial"

# Check tech stack for Salesloft (0.33x lift — point-solution approach)
site:domain.com "salesloft"
```

### Building a combined TAM from multiple signal searches

Run one search per buyer persona, deduplicate, then score:

```bash
# Search 1: RevOps buyers
deepline tools execute dropleads_search_people \
  --payload '{"filters":{"jobTitles":["Revenue Operations","RevOps"],"seniority":["VP","Director","Manager"],"keywords":["b2b saas"],"employeeRanges":["201-500","501-1000","1001-5000"]},"pagination":{"page":1,"limit":100}}'

# Search 2: BizOps buyers
deepline tools execute dropleads_search_people \
  --payload '{"filters":{"jobTitles":["Business Operations","BizOps","Head of Operations"],"seniority":["VP","Director","Manager"],"keywords":["b2b saas"],"employeeRanges":["201-500","501-1000","1001-5000"]},"pagination":{"page":1,"limit":100}}' 

# Search 3: Data/Analytics buyers
deepline tools execute dropleads_search_people \
  --payload '{"filters":{"jobTitles":["Head of Data","VP Analytics","Analytics Engineering"],"seniority":["VP","Director","Manager"],"keywords":["b2b saas data infrastructure"],"employeeRanges":["201-500","501-1000","1001-5000"]},"pagination":{"page":1,"limit":100}}' 
```

Merge the JSON outputs into a single CSV, deduplicate by company domain, then run the job listing enrichment + scoring pipeline above.

---

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

Dropleads returns up to 100 results per page. For large TAMs:

```bash
# Page 1
deepline tools execute dropleads_search_people --payload '{"pagination":{"page":1,"limit":100}, ...}'

# Page 2
deepline tools execute dropleads_search_people --payload '{"pagination":{"page":2,"limit":100}, ...}'
```

## Cost estimation

| Operation | Credits per call | Notes |
|-----------|-----------------|-------|
| `dropleads_search_people` (limit: 1) | ~0.01 | Sizing — nearly free |
| `dropleads_search_people` (limit: 100) | ~1 | Full pull |
| `dropleads_search_people` (limit: 100) | ~1 | Full pull |
| `crustdata_job_listings` | ~1 | Per company |
| `exa_search` with contents | ~5 | Per company |

Size first with `pagination.limit: 1`, then calculate: `total_pages x credits_per_page`.

## Tips

- Always check `total_people` or `total_entries` with `pagination.limit: 1` before pulling
- Start narrow (tight ICP), validate quality, then widen filters
- Use `personalCountries` to segment by geo for personalized campaigns
- Spot-check 5-10 results after pulling to verify filter quality before scaling
- After pulling, prioritize with signal discovery before email enrichment
- Add `seniority` to avoid noisy results from individual contributors

## Pipeline next steps

After building your TAM:

1. **Score accounts** → Use `niche-signal-discovery` skill if you have won/lost data
2. **Find contacts** → Use `get-leads-at-company` skill to find decision-makers
3. **Get emails** → Use `contact-to-email` skill to enrich with verified emails
4. **Resolve LinkedIn** → Use `linkedin-url-lookup` skill for LinkedIn URLs

## Get started

Sign up and get your API key at [code.deepline.com](https://code.deepline.com).

```bash
curl -s "https://code.deepline.com/api/v2/cli/install" | bash
deepline auth register
```
