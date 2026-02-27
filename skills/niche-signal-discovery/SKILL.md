---
name: niche-signal-discovery
description: "Discover niche first-party signals that differentiate Closed Won vs Closed Lost accounts for ICP analysis. Use when the user provides won/lost customer domain lists and wants differential signals (website content, job listings, tech stack, maturity markers) to build account scoring models and prospecting criteria. Triggers: ICP analysis, niche signals, won vs lost analysis, differential signals, signal discovery, ICP signal report, account scoring signals, lead scoring, first-party signals, buyer signals."
---

# Niche Signal Discovery

Discover differential signals between Closed Won and Closed Lost accounts by extracting multi-page website content and job listings, then computing Laplace-smoothed lift scores to identify what distinguishes buyers from non-buyers.

## Prerequisites

**Required:**

- **Deepline CLI** — All enrichment runs through `deepline enrich` (no separate API keys for exa, crustdata, etc.)
- **Python 3** — Analysis script uses standard library only (csv, json, re, argparse — no pip packages)

**NOT required:**

- ❌ No exa API key (accessed via Deepline)
- ❌ No crustdata API key (accessed via Deepline)
- ❌ No external Python packages (no pip install needed)
- ❌ No OpenAI/Anthropic API keys (deterministic analysis, no LLM calls)

**Credits:** Enrichment consumes Deepline credits (~6 credits/company for exa + crustdata). Always get user approval before running paid enrichment.

## Deepline-First Principle

**Always use Deepline CLI (`deepline enrich`, `deepline tools`, `deepline playground`) for enrichment, data extraction, and batch operations.** Deepline provides:
- Batch enrichment with automatic CSV column management
- Built-in tool integrations (exa_search, crustdata, apollo, etc.)
- Playground UI for inspecting and iterating on enrichment results
- Idempotent reruns — re-running updates existing columns instead of duplicating

Use `deepline enrich` for all enrichment steps. Use `deepline tools execute` for one-off tool calls. Use `deepline playground` for inspecting results. Refer to the `gtm-meta-skill` for Deepline command patterns and provider playbooks.

## Input Requirements

- Won and lost customer domain lists (minimum 20 won + 10 lost for statistical significance)
- **Target company context** — What they sell, who they sell to, key personas (discovered in Step 0)

## Pipeline

```
0. Discover target company (what they sell, who they sell to, differentiation)
0.5. Discover ecosystem (competitors, tech stack category, buyer personas)
1. Prepare input CSV (domain, status) — deduplicate domains that appear in both won and lost
1.5. Generate vertical-specific configs (keywords, tools, job roles)
2. Multi-page website extraction + job listings (Deepline enrichment)
3. Quality gate — verify file completeness + coverage (>80% with content)
3.5. Review generated configs (validate against enriched data)
4. Run differential analysis (scripts/analyze_signals.py)
5. Generate report (using references/report-template.md)
6. Review with signal interpretation rules (references/signal-interpretation.md)
```

## Signal Reliability Hierarchy

Not all signals are equal. From actual runs across Air Inc, Mixmax, Lunos.ai, and others, signals follow a clear reliability order:

| Rank | Signal Source | Reliability | Why |
|------|---|---|---|
| 1 | **Job listings** (hiring for domain-related roles) | Highest | Active budget + acknowledged pain. A company hiring 3 AEs is a stronger signal than "sales" on their website. |
| 2 | **Analyst validation** (Gartner, Forrester mentions) | Very High | Enterprise maturity + category awareness. 6.5x lift in Mixmax analysis, 0% false positive rate in lost group. |
| 3 | **Compliance infrastructure** (SOC2, GDPR, ISO) | High | Procurement maturity + enterprise readiness. Companies with compliance pages have formal approval processes. |
| 4 | **Buyer pain language** (on careers/blog pages) | High | Operational awareness of the problem — e.g., "fragmented tools" at 5.2x lift for Air Inc. |
| 5 | **Tech stack tools** (niche SaaS specific to persona) | Medium | Infrastructure readiness — Figma + Adobe CC at 3.2x lift for creative ops buyers. |
| 6 | **Website product/marketing content** | Variable | Can indicate buyer OR competitor — source context is everything. |

**When website signals fail:** For B2B infrastructure tools (AR automation, billing, compliance), buyers DON'T publish their pain on public websites. A company like McPherson Oil (energy distribution) talks about oil products, not accounts receivable challenges. For these verticals, prioritize job listings, tech stack, and firmographic signals over website keyword matching.

## Step 0: Target Company Discovery

**CRITICAL: Do this FIRST before any enrichment or config generation.**

Use web search to understand what the target company sells and who they sell to:

```bash
# Example for Air Inc
WebSearch: "air.inc product what do they sell"
WebSearch: "air.inc customers use cases who uses"
WebFetch: https://air.inc/ "What does Air.inc sell? Who are their target customers?"
```

**Document the following:**

1. **Product category** — e.g., "Creative Operations & DAM platform", "AR automation software", "Sales engagement platform"
2. **Target buyer persona** — e.g., "Marketing and creative teams", "Finance/AR teams", "Sales Development Reps"
3. **Key differentiation** — What makes them unique vs competitors
4. **Example customers** (if available) — Who currently uses the product

**Why this matters:** The entire pipeline (exa query, keywords, tech stack, job roles) adapts based on this discovery. Skipping this step results in generic/irrelevant signals.

## Step 0.5: Ecosystem Discovery

Use web search to discover the competitive landscape and buyer ecosystem:

**Competitor Discovery:**
```bash
WebSearch: "{product category} software companies"
WebSearch: "{product category} alternatives competitors"
```

Example for Air Inc (creative ops/DAM):
```bash
WebSearch: "creative operations software digital asset management platforms"
WebSearch: "DAM software alternatives Bynder Widen competitors"
```

**Tech Stack Discovery:**
```bash
WebSearch: "{buyer persona} common tools tech stack"
WebSearch: "{industry} companies use what software"
```

Example for Air Inc (marketing/creative teams):
```bash
WebSearch: "marketing teams creative teams common tools software stack"
WebSearch: "creative operations teams use Figma Adobe tools integrations"
```

**Job Role Discovery:**
```bash
WebSearch: "{buyer persona} job titles roles responsibilities"
WebSearch: "companies hiring {buyer persona} job listings"
```

Example for Air Inc:
```bash
WebSearch: "creative operations job titles creative director content manager roles"
WebSearch: "companies hiring creative operations manager brand manager"
```

**Document findings:**

- Competitor products (3-5 names) — Used to identify migration opportunities (companies currently using these tools)
- Common tech stack tools (10-15 by category) — Used for infrastructure signals
- Buyer job titles (10-15 variations) — Used for hiring intent signals

## Step 1: Prepare Input CSV

Create `output/{company}-icp-input.csv`:

```csv
domain,status
customer1.com,won
customer2.com,won
non-customer1.com,lost
non-customer2.com,lost
```

**CRITICAL — Deduplicate before enrichment.** If the same domain appears in both won and lost groups (same company, multiple CRM deals), Deepline may only fetch job listings once (for the first row). The duplicate domain's content is identical in both groups — including it pollutes lift scores and causes `won_with_jobs` to be undercounted. Always check and remove duplicate domains before running enrichment:

```python
# Check for duplicates after building the input CSV
from collections import Counter
domain_counts = Counter(r['domain'] for r in rows)
duplicate_domains = {d for d, c in domain_counts.items() if c > 1}
if duplicate_domains:
    print(f"WARNING: {len(duplicate_domains)} domains appear in both won and lost:")
    for d in sorted(duplicate_domains):
        print(f"  {d}")
    print("Remove these rows before enrichment — they pollute lift scores.")
```

If duplicates exist, remove ALL rows for those domains (not just one copy). The same company with different deal outcomes tells us nothing about what distinguishes buyers from non-buyers.

## Step 1.5: Generate Vertical-Specific Configs

**Using the discovery from Steps 0 and 0.5**, create three JSON config files.

See `references/keyword-catalog.md` for JSON format and generation guidance.

```bash
# Create config files in output/{company}/
output/{company}-keywords.json    # keyword categories
output/{company}-tools.json       # tech stack tools by category
output/{company}-job-roles.json   # job role categories
```

**Generation approach:**

1. **Keywords** — Mix of:
   - Product category terms (e.g., "creative ops", "asset management" for Air Inc)
   - Buyer pain points (e.g., "fragmented tools", "content discovery")
   - Competitor names for migration segment (e.g., "bynder", "widen") — companies using these are migration opportunities, not excluded
   - Generic business maturity (e.g., "security", "compliance", "integrations")

2. **Tech Stack** — Tools from ecosystem discovery:
   - Infrastructure tools buyer persona uses (e.g., "figma", "adobe creative cloud")
   - Adjacent tools in buyer workflow (e.g., "contentful", "monday.com")
   - Competitor tools for migration segment — companies using these represent displacement opportunities

3. **Job Roles** — Titles from role discovery:
   - Buyer persona variations (e.g., "creative director", "content manager", "brand manager")
   - Adjacent roles (e.g., "marketing operations", "brand designer")
   - Generic growth roles (e.g., "product", "engineering")

**Example generation for Air Inc** (creative ops/DAM):

```json
// keywords.json
{
  "creative_operations": [
    "creative ops", "creative operations", "asset management", "DAM",
    "content library", "brand guidelines", "creative workflow", "creative review"
  ],
  "buyer_pain_points": [
    "fragmented tools", "content discovery", "version control",
    "creative approval", "asset organization", "brand consistency"
  ],
  "business_model": [
    "contact sales", "plan", "enterprise", "pricing", "demo",
    "subscription", "free trial"
  ],
  "company_maturity": [
    "compliance", "security", "integration", "api", "sso", "soc 2"
  ],
  "anti_fit": [
    "bynder", "widen", "brandfolder", "canto", "dam platform"
  ]
}
```

```json
// tools.json
{
  "creative_design": [
    "figma", "sketch", "adobe creative cloud", "canva", "invision"
  ],
  "marketing_ops": [
    "hubspot", "marketo", "contentful", "wordpress", "webflow"
  ],
  "project_management": [
    "monday.com", "asana", "jira", "clickup", "notion"
  ],
  "video_production": [
    "frame.io", "vimeo", "wistia", "loom"
  ]
}
```

```json
// job-roles.json
{
  "creative_leadership": ["creative director", "head of creative", "vp creative"],
  "content_management": ["content manager", "content director", "brand manager"],
  "creative_ops": ["creative operations", "creative ops manager", "brand operations"],
  "marketing_ops": ["marketing operations", "marops", "marketing ops manager"],
  "design": ["product designer", "brand designer", "visual designer"],
  "marketing_general": ["marketing manager", "demand gen", "growth marketing"]
}
```

**Validation:** Do the generated configs match the target's vertical and buyer persona? If not, refine based on Step 0/0.5 findings.

## Step 2: Deepline Enrichment

**CRITICAL: Never scrape just the homepage.** Use `exa_search` with `contents.text` to discover AND scrape ~8 pages per domain in a single API call.

**Generate exa query dynamically based on target's product category:**

```bash
# Generic query (works for most B2B SaaS selling to marketing/sales/product teams)
QUERY="company product features integrations customers security pricing careers about case-studies"

# For tools selling to back-office teams (finance, HR, legal):
# Buyers don't publish pain on marketing pages — add compliance/audit pages where signals live
QUERY="company product features integrations customers security pricing careers compliance audit regulatory about"

# For developer tools:
# Add documentation/API pages — these reveal infrastructure maturity and integration readiness
QUERY="company product features documentation api changelog github integrations security pricing careers about"

# For creative/marketing tools:
QUERY="company product features portfolio use cases creative workflow customers integrations security pricing careers about"

# For sales tools:
QUERY="company product features playbooks outbound pipeline customers integrations security pricing careers about"
```

**Example for Air Inc (creative ops):**

```bash
deepline enrich \
  --input output/air-inc-icp-input.csv \
  --output output/air-inc-enriched.csv \
  --with 'website=exa_search:{"query":"company product features portfolio use cases creative workflow customers integrations security pricing careers about","numResults":8,"type":"auto","includeDomains":["{{domain}}"],"contents":{"text":{"maxCharacters":3000,"verbosity":"compact","includeSections":["body"]}}}' \
  --with 'jobs=crustdata_job_listings:{"companyDomains":"{{domain}}","limit":50}' \
  --json
```

**Why exa_search with contents (not parallel_extract)?**
- Discovers pages AND returns content in one call — no separate page discovery step
- ~8 pages per domain, ~3K chars each = ~24K chars per company
- Cost: ~5 credits/company (exa) + ~1 credit (crustdata jobs) = ~6 credits/company

Get user credit approval before running. Example: "60 companies x 6 credits = ~360 credits."

## Step 3: Quality Gate

**CRITICAL — Verify file completeness BEFORE running analysis.** `deepline enrich` returns control to the terminal before OS buffers fully flush to disk. Running the analysis script immediately after enrichment completes can read a partially-written file where job columns for the last N rows haven't synced yet — resulting in `won_with_jobs: 0` or severely undercounted job data. Always verify:

```bash
# 1. Check row count matches input
INPUT_ROWS=$(wc -l < output/{company}-icp-input.csv)
OUTPUT_ROWS=$(wc -l < output/{company}-enriched.csv)
echo "Input: $INPUT_ROWS rows, Output: $OUTPUT_ROWS rows"
# Output should equal input (both include header)

# 2. Spot-check job data for a known won account with job listings
python3 -c "
import csv, json, sys
csv.field_size_limit(sys.maxsize)
with open('output/{company}-enriched.csv') as f:
    rows = list(csv.DictReader(f))
won_rows = [r for r in rows if r.get('status') == 'won']
jobs_col = 'jobs'  # or use column index
has_jobs = sum(1 for r in won_rows if r.get(jobs_col, '').strip() not in ('', '{}', 'null'))
print(f'Won rows with job data: {has_jobs}/{len(won_rows)}')
# If this is 0 and you know won accounts should have listings, wait and re-run
"
```

If `won_with_jobs` is 0 but you expect job data:

1. Wait 5-10 seconds (OS buffer flush)
2. Re-run the verification check
3. If still 0, check column indices — the enriched CSV uses `website` and `jobs` column names, NOT `__dl_full_result__`. Use `--website-col N --jobs-col N` overrides.

After file verification, check coverage:
- **Coverage**: >80% of companies should have website content. If <80%, check domain spelling and retry failed rows.
- **Content depth**: Average should be 6-8 pages per company, 12-20K chars.
- **Job listings**: Won companies should have more job data than lost (expected — larger/scaling companies win more).

If coverage is poor, re-run failed domains with `--rows` targeting specific rows.

### Domain Validation (if using auto-extracted customer lists)

If customer domains came from automated extraction (CRM exports, Exa API, case study scraping) rather than a manually verified list, validate that domains actually belong to the named companies. From the Lunos.ai run: **53% of auto-extracted customers were false positives** — competitors selling the same product, domain mismatches (Harvey → anthropic.com), and unrelated companies.

```bash
# Check for suspicious domain patterns
python3 -c "
import csv, sys
csv.field_size_limit(sys.maxsize)
with open('output/{company}-enriched.csv') as f:
    rows = list(csv.DictReader(f))
for r in rows:
    domain = r.get('domain', '')
    # Flag content platforms used as source URLs, not company domains
    if any(x in domain for x in ['blog.', 'medium.com', 'substack.', 'wordpress.']):
        print(f'WARNING: {domain} looks like a content platform, not a company domain')
    # Flag very short domains that might be generic
    if len(domain.split('.')[0]) <= 2:
        print(f'CHECK: {domain} — very short domain, verify it belongs to the expected company')
"
```

**Red flags for false positives:**
- Domain is a subdomain of the target company (blog.target.com)
- Domain belongs to a well-known AI/tech company but the "customer" is a different firm (domain resolution failed)
- Company appears in competitor case studies, not target's own customer list
- Company is itself a vendor in the same product category (they SELL the solution, they don't BUY it)

## Step 3.5: Review Generated Configs

**Before running analysis**, spot-check the generated configs against enriched data:

```bash
# Sample a few enriched companies
deepline playground output/{company}-enriched.csv

# In playground UI, check:
# - Do website pages mention the keywords in keywords.json?
# - Do job listings mention the roles in job-roles.json?
# - Do integrations/tech stack pages mention the tools in tools.json?
```

**Red flags:**

- Keywords appear in <10% of enriched companies → too niche, broaden
- Keywords appear in >90% of companies → too generic, refine
- Product category keywords (what the target SELLS) appear frequently in Won companies → wrong product category, these companies are competitors not buyers
- Job roles missing from actual job listings → wrong buyer persona, revise

**Fix and re-generate configs if needed.**

## Step 4: Differential Analysis

Run the analysis script with the config files:

```bash
python3 scripts/analyze_signals.py \
  --input output/{company}-enriched.csv \
  --keywords output/{company}-keywords.json \
  --tools output/{company}-tools.json \
  --job-roles output/{company}-job-roles.json \
  --output output/{company}-analysis.json
```

The script auto-detects `__dl_full_result__` columns for website and jobs data. Override with `--website-col N --jobs-col N` if needed.

**What the script computes:**

- Substring-match presence per company per keyword (NOT exact-token TF-IDF)
- Laplace-smoothed lift: `((won + 0.5) / (won_total + 1)) / ((lost + 0.5) / (lost_total + 1))`
- Source breakdown per keyword (website only / jobs only / both)
- Tech stack tool mentions across categories
- Job role prevalence in won vs lost
- Anti-fit signals (lift < 0.5x)
- Source evidence: exact quotes (±40 chars) with page URLs and job listing URLs per keyword

## Step 5: Report Generation

Read `references/report-template.md` for the full report structure and quality rules.

**Report structure overview:**

1. **Section 0: Quick Reference Dashboard** ← Start here. Required before all other sections.
   - **0.1 TLDR** — 5 bullets: #1 signal, best-fit archetype, fastest path to pipeline, hard skip flags, scoring summary
   - **0.2 Signal Strength at a Glance** — Two visual tables (positive + anti-fit) with 🟩🟥 emoji lift bars sorted by lift
   - **0.3 Platform Search Recipes** — Pre-built Apollo URLs (people + company searches) and Google operators
   - **0.4 Buyer Persona Quick Reference** — 3–5 personas with titles, pain points, signals, and Apollo links
   - **0.5 Lead Scoring Cheatsheet** — All scoring signals in one table with "How to Check" column
2. Sections 1–9: Full data and methodology (existing format, unchanged)

**Signal Strength Bar scale** (use in Section 0.2):
```
≥10x → 🟩🟩🟩🟩🟩🟩   ≥4x  → 🟩🟩🟩🟩🟩   ≥2.5x → 🟩🟩🟩🟩
≥2.0x → 🟩🟩🟩         ≥1.5x → 🟩🟩         ≥1.0x → 🟩
≥0.4x → 🟥🟥           ≥0.25x → 🟥🟥🟥       ≥0.15x → 🟥🟥🟥🟥
≥0.07x → 🟥🟥🟥🟥🟥    <0.07x → 🟥🟥🟥🟥🟥🟥
```

**Apollo URL format** (use in Section 0.3 and 0.4):
```
People: https://app.apollo.io/#/people?personTitles[]=Title+One&personTitles[]=Title+Two&personSeniorities[]=vp&personSeniorities[]=director&qOrganizationKeywordTags[]=vertical&organizationLocations[]=United+States&page=1
Companies: https://app.apollo.io/#/companies?qOrganizationKeywordTags[]=keyword&organizationLocations[]=United+States&organizationNumEmployeesRanges[]=201-500&page=1
```
Use `qOrganizationKeywordTags[]` for keyword filters (not hardcoded industry tag IDs).

Key quality rules for all sections:
- **Raw counts always**: `15% (6)` not just `15%`
- **Sample sizes in headers**: `Won (n=37)`, `Lost (n=18)`
- **Bold only lift > 2x AND count >= 3 companies** — a signal in 1 company with 10x lift is less reliable than a signal in 4 companies with 3x lift
- **Flag n=1 signals**: If a signal appears in only 1 won company, add a note: `*(single company — verify before using in scoring)*`. In the scoring model, give n=1 signals 0.3x weight vs n=3+ signals.
- **Source breakdown for ALL keyword tables**: Add a Source column showing `3w / 20j / 2both` format (3 website-only, 20 jobs-only, 2 from both). This is critical for distinguishing website-only signals (lower confidence) from job-listing signals (higher confidence).
  ```markdown
  | Keyword | Won (n=X) | Lost (n=Y) | Lift | Source (w/j/both) | Interpretation |
  ```
- **Source evidence required**: After each keyword table, add exact quotes with linked sources for top 3 keywords. The analysis script outputs `evidence` per keyword with `company`, `source_type`, `quote`, `url`, and `page_title`/`job_title`. Format:
  ```
  > **Evidence — "keyword":**
  > - [company.com](url) (page title): "...exact quote with keyword..."
  > - [company.com](url) (job: "Job Title"): "...exact quote from listing..."
  ```
- **Niche tech stack tools**: Report specific SaaS tools by category, not generic keywords. "AWS", "GitHub", "Slack" appear on most B2B sites — these aren't differentiating.
- **Anti-fit signals in separate section**
- **Interpretation column required**: Explains WHY each signal matters for the target company

## Step 6: Signal Interpretation Review

Read `references/signal-interpretation.md` before writing interpretation columns. Key rules:
- Website content mentioning what the target sells = competitor signal (NOT buyer)
- Job listings = highest-intent buyer signal
- Same keyword means different things on product page vs careers page vs blog
- Tech stack tools need context — do they create or solve the target's problem?

## Enrichment Data Structure

Website data: `__dl_full_result__` column containing exa_search response.
```
data.results[].text — page content
data.results[].url — page URL
data.results[].title — page title
```

Job listings: `__dl_full_result__` column containing crustdata response.
```
data.listings[].title — job title (NOT "job_title")
data.listings[].description — job description (NOT "job_description")
data.listings[].category — job category
data.listings[].url — listing URL
```

## Credit Estimation

| Step | Credits per row | Total (60 companies) |
|------|----------------|---------------------|
| exa_search with contents | ~5 | ~300 |
| crustdata_job_listings | ~1 | ~60 |
| **Total** | **~6** | **~360** |

Always get user approval before running paid enrichment steps.

## Common Pitfalls

1. **Skipping target discovery (Step 0)** — Without understanding what the target sells, you'll generate generic/irrelevant configs.
2. **Homepage-only scraping** — Always use multi-page discovery. Homepage alone misses pricing, integrations, security, careers.
3. **Using hardcoded examples** — Don't copy sales-focused keywords for a creative-ops tool. Generate configs per vertical.
4. **Generic tech stack** — "AWS", "GitHub", "Slack" appear on most B2B sites and aren't differentiating. Search for niche SaaS tools specific to the buyer persona (e.g., Figma for creative teams, NetSuite for finance teams).
5. **Ignoring source context** — "prospect" on a product page = seller signal. "prospect" in a job listing = buyer signal. Same keyword, opposite meaning.
6. **Missing lost data** — Verify lost companies have content before analysis. Empty lost = meaningless lift scores.
7. **Substring false positives** — "sequenc" matches "consequences". Spot-check high-lift keywords for false matches.
8. **Skipping config review (Step 3.5)** — Always validate generated configs against enriched data before analysis.
9. **Duplicate domains in input** — CRM exports often have the same company in both won and lost (multiple deals). Deepline only fetches job listings once per domain, so the duplicate's job data lands on one row only — silently undercounting `won_with_jobs`. Always deduplicate in Step 1.
10. **Running analysis immediately after enrichment** — `deepline enrich` returns to terminal before OS buffers flush. Run the file completeness check in Step 3 before executing `analyze_signals.py`. A `won_with_jobs: 0` result when you expect data is the symptom; re-running the analysis (without re-enriching) fixes it.
11. **Domain mismatches in auto-extracted lists** — When using CRM exports or automated customer discovery, domain → company name mapping can be wrong. In the Lunos.ai run, 53% of auto-extracted domains were false positives. Always validate domains against expected company names before enrichment.
12. **Treating vendor signals as buyer signals** — "accounts receivable automation" on a company's product page means they SELL AR tools (competitor). The same phrase in a job listing means they NEED AR tools (buyer). Source context is everything — see `references/signal-interpretation.md`.
13. **Trusting n=1 signals** — A signal in 1 won company with 0 lost = mathematically high lift but statistically meaningless. Require 3+ companies for Tier 1 scoring signals. Flag single-company signals in the report with a verification note.
14. **Expecting website signals for back-office tools** — Companies buying AR automation, billing, or compliance tools don't discuss these needs on their marketing websites. For these verticals, rely on job listings (hiring AR Manager = budget + pain), tech stack (NetSuite, Salesforce in jobs), and firmographics (wholesale/distribution/manufacturing) instead.
15. **Including generic business words as signals** — "platform", "automat*", "integrat*" appear at near-identical rates in won and lost (1.0-1.1x lift). These are baseline terms, not differentiators. Focus on signals with lift > 1.5x that are specific to the target's vertical.

## Proven Signal Patterns (from actual runs)

These patterns have been validated across multiple customer analyses (Air Inc, Mixmax, Lunos.ai, Prove, Legal.io). Use them as a starting point when interpreting results — but always validate against the specific target's vertical.

### High-Confidence Positive Signals

| Signal Pattern | Typical Lift | Validated For | What It Means |
|---|---|---|---|
| Analyst validation (Gartner, Forrester) | 4.5x-6.5x | Enterprise B2B SaaS | Company has evaluated the category, has enterprise procurement process |
| Hiring for ICP-related roles | 3.8x-5.5x | All verticals | Active budget + acknowledged pain — highest-intent signal |
| Published case studies | 3.7x | Product-led + sales-assist | Mature marketing org, values proof points, vendor-friendly |
| Compliance infrastructure (GDPR, SOC2, ISO) | 2.1x-6.5x | Enterprise tools | Formal approval processes, security reviews, higher close rates |
| Buyer pain language (e.g., "fragmented tools") | 2.9x-5.2x | Creative ops, MarTech | Operational awareness of the specific problem the target solves |
| SDK/webhook/API presence | 2.5x-3.5x | Developer-adjacent tools | Developer culture, integrates tools programmatically |
| Contact sales / sales-led GTM | 2.2x-5.5x | Enterprise sales tools | Human-led sales motion = AE-dependent = Mixmax buyer |
| Niche tech stack (Figma, Frame.io, NetSuite) | 1.5x-5.5x | Vertical-specific | Infrastructure readiness for the target's integration ecosystem |

### High-Confidence Anti-Fit Signals

| Signal Pattern | Typical Lift | What It Means |
|---|---|---|
| Consumer signals (shopper, checkout, cancel, debit) | 0.2x | B2C company, not B2B sales org |
| Retention/churn language | 0.2x-0.4x | Consumer subscription model, not enterprise buying |
| Selling same product category | 0.1x-0.3x | Competitor, not buyer — they SELL the solution |
| No job listings in 12+ months | N/A | Not growing, no hiring budget |

### Scoring Model Guidance

From actual runs, a 0-100 point model with three tiers works well:
- **Tier 1: Core Fit (0-40 pts)** — Compliance, analyst validation, structural signals
- **Tier 2: Buying Intent (0-30 pts)** — Hiring for domain roles, pain language, tech stack
- **Tier 3: Infrastructure Readiness (0-30 pts)** — API presence, integration maturity, case studies

Score thresholds: 60+ = Tier 1 immediate outreach, 35-59 = Tier 2 trigger-based, <35 = nurture or skip.

## References

- **[keyword-catalog.md](references/keyword-catalog.md)**: Read when generating configs (Step 1.5). Contains JSON format, generation patterns, and multi-vertical examples.
- **[report-template.md](references/report-template.md)**: Read when generating the report (Step 5). Full section structure, table formats, inline example format, quality rules.
- **[signal-interpretation.md](references/signal-interpretation.md)**: Read when writing interpretation columns or reviewing signal quality. Buyer vs seller vs competitor rules.
- **[scripts/analyze_signals.py](scripts/analyze_signals.py)**: Deterministic analysis script. Run in Step 4. Auto-detects columns, accepts custom keywords/tools via JSON.
