---
name: account-orgchart
description: "Build an interactive org chart around a target person or company using Deepline CLI. Maps reporting structures, identifies decision makers, and highlights warm intro paths."
---

# Account Org Chart Builder

Build an interactive HTML org chart for account mapping - find decision makers, map reporting structures, and identify warm intro paths.

This is a **recipe** (not auto-invoked). Reference it when:
- User asks to "map an account" or "build an org chart"
- User wants to find "who reports to X" or "decision makers at Y"
- User has a warm connection and wants to find paths through the org

## Inputs

One of:
- LinkedIn URL (+ optional company/domain)
- Name + company name or domain
- Just a company domain (maps the full GTM org)

If only a name is given with no company context, ask before proceeding.

## Quick reference

| Step | What | Source | Cost |
|------|------|--------|------|
| 1 | Resolve target | `leadmagic_profile_search` or `person_enrichment_from_email_waterfall` | 1 credit |
| 2a | Deepline Native search | `deepline_native_search_contact` (4 title tiers) | $0.04/req |
| 2b | Dropleads search | `dropleads_search_people` | FREE |
| 2c | Apify LinkedIn scrape | `apimaestro/linkedin-company-employees-scraper-no-cookies` | ~$0.25 |
| 2d | Apollo paid search | `apollo_people_search_paid` (2 pages) | ~$5 |
| 2e | PDL gap-fill (optional) | `peopledatalabs_person_search` CXO+VP only | ~$2-11 |
| 3 | Classify + infer | Title-based seniority + Claude reasoning for hierarchy | 0 |
| 4 | Generate output | HTML org chart file | 0 |

Typical run: 150-250 people found, ~$7-16 total, 3-8 minutes.

**Cost-optimal order:** Free first (DN + Dropleads), then cheap (Apify), then paid (Apollo), then surgical (PDL for missing execs only). Each step deduplicates against prior results.

## Pipeline

### 1. Resolve target identity

**If LinkedIn URL given:**
```bash
deepline enrich --input seed.csv --in-place \
  --with '{"alias":"target_profile","tool":"leadmagic_profile_search","payload":{"profile_url":"{{linkedin_url}}"},"extract_js":"(data) => ({ name: (data?.first_name || \"\") + \" \" + (data?.last_name || \"\"), title: data?.current_position || data?.headline || \"\", company_name: data?.current_company || \"\", location: data?.location || \"\" })"}'
```

Then resolve domain if missing:
```bash
deepline enrich --input seed.csv --in-place \
  --with '{"alias":"domain_search","tool":"exa_search","payload":{"query":"{{company_name}} official website","numResults":1}}'
deepline enrich --input seed.csv --in-place \
  --with '{"alias":"domain","tool":"run_javascript","payload":{"code":"const r=row.domain_search;const url=(((r&&r.data&&r.data.results||[])[0])||{}).url||\"\";const m=url.match(/^https?:\\/\\/(www\\.)?([^\\/]+)/);return m?m[2]:null;"}}'
```

**If name + company given:**
Create seed CSV with columns: `name`, `company_name`, `domain`. If no domain, resolve with exa_search as above.

### 2. Find ALL employees (cost-optimal waterfall)

Run sources cheapest-first. Each step deduplicates against prior results - only net-new people advance.

```bash
WORK_DIR="output/orgchart/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WORK_DIR"
echo "company_domain,company_name" > "$WORK_DIR/accounts.csv"
echo "\"$DOMAIN\",\"$COMPANY\"" >> "$WORK_DIR/accounts.csv"
```

**Source 1: Deepline Native ($0.04/request)**
```bash
deepline enrich --input "$WORK_DIR/accounts.csv" --output "$WORK_DIR/dn-csuite.csv" \
  --with '{"alias":"people","tool":"deepline_native_search_contact","payload":{"domain":"{{company_domain}}","title_filters":[{"name":"csuite","filter":"CEO OR CTO OR CFO OR COO OR CMO OR CRO OR Founder"}]}}'
deepline enrich --input "$WORK_DIR/accounts.csv" --output "$WORK_DIR/dn-vp.csv" \
  --with '{"alias":"people","tool":"deepline_native_search_contact","payload":{"domain":"{{company_domain}}","title_filters":[{"name":"vp","filter":"VP OR Vice President OR SVP"}]}}'
deepline enrich --input "$WORK_DIR/accounts.csv" --output "$WORK_DIR/dn-dir.csv" \
  --with '{"alias":"people","tool":"deepline_native_search_contact","payload":{"domain":"{{company_domain}}","title_filters":[{"name":"dir","filter":"Head OR Director OR Senior Director"}]}}'
deepline enrich --input "$WORK_DIR/accounts.csv" --output "$WORK_DIR/dn-mgr.csv" \
  --with '{"alias":"people","tool":"deepline_native_search_contact","payload":{"domain":"{{company_domain}}","title_filters":[{"name":"mgr","filter":"Manager OR Senior Manager"}]}}'
```
Expected: ~25-35 people.

**Source 2: Dropleads (FREE)**
```bash
deepline enrich --input "$WORK_DIR/accounts.csv" --output "$WORK_DIR/dropleads.csv" \
  --with '{"alias":"people","tool":"dropleads_search_people","payload":{"filters":{"companyDomains":["{{company_domain}}"]},"pagination":{"page":1,"limit":100}}}'
```
Expected: +60-80 net new.

**Source 3: Apify LinkedIn scrape (~$0.25)**

First resolve the LinkedIn company slug:
```bash
deepline tools execute exa_search --payload '{"query":"COMPANY_NAME LinkedIn company page site:linkedin.com/company","numResults":1,"type":"auto"}'
```
Then scrape employees:
```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"apimaestro/linkedin-company-employees-scraper-no-cookies","input":{"identifier":"https://www.linkedin.com/company/SLUG/","max_employees":500}}'
```
Results use `fullname` (not `fullName`), `headline` (not `title`), `profile_url`. Expected: +15-25 net new.

**Source 4: Apollo paid search (~$5)**
```bash
deepline tools execute apollo_people_search_paid --payload '{"q_organization_domains_list":["DOMAIN"],"per_page":100,"page":1}'
deepline tools execute apollo_people_search_paid --payload '{"q_organization_domains_list":["DOMAIN"],"per_page":100,"page":2}'
```
Expected: +80-100 net new.

**Source 5: PDL surgical gap-fill - ONLY for missing senior people**

After building initial hierarchy, identify gaps (e.g., "5 Sales Directors but no VP Sales"):
```bash
deepline tools execute peopledatalabs_person_search --payload '{"size":30,"sql":"SELECT * FROM person WHERE job_company_website = '\''DOMAIN'\'' AND (job_title_levels = '\''cxo'\'' OR job_title_levels = '\''vp'\'')"}'
```
PDL costs 3.92 credits/result. Pull CXO+VP only (~29 people, ~$11) then dedupe.

Merge all results, deduplicate by slugified name.

### 3. Classify seniority + infer hierarchy

Apply seniority classification from `references/hierarchy-rules.md`:

| Rank | Level | Patterns |
|------|-------|----------|
| 0 | ceo | "ceo", "chief executive" |
| 1 | c-level | "chief" + any (cto, cfo, coo, cmo, cro) |
| 2 | evp | "evp", "executive vice president" |
| 3 | svp | "svp", "senior vice president" |
| 4 | vp | "vice president", "vp", "area vice president" |
| 5 | sr-director | "senior director" |
| 6 | director | "head of", "director" |
| 7 | sr-manager | "senior manager" |
| 8 | manager | "manager" |
| 9 | principal | "principal", "staff" |
| 10 | lead | "lead" |
| 11 | senior | "senior", "sr." |
| 12 | ic | everything else |

For display, simplify to 4 levels:
- **exec**: ceo, c-level, evp, svp, vp
- **director**: sr-director, director
- **manager**: sr-manager, manager, principal, lead
- **ic**: senior, ic

Infer teams from title patterns (text after comma).

### 4. Generate HTML org chart

Use the template at `references/orgchart-template.html`. Key design elements:

**Design system (avoid AI slop):**
- Dark mode: `--bg: #0a0a0a`, `--surface: #141414`, `--border: #262626`
- Text: `--text: #e5e5e5`, `--text-muted: #a3a3a3`
- Warm path: `--warm: #f59e0b` with amber glow
- Seniority colors: Exec=#a78bfa, Director=#60a5fa, Manager=#34d399, IC=#525252

**Critical UX elements:**
- **Warm path banner** at top if user has a connection
- **Priority score column** (0-100): +40 exec, +25 director, +10 manager, +25 email, +10 phone, +30 warm
- **Clickable stats bar** with percentages that filter on click
- **Team sidebar** (left): collapsed teams with counts
- **Table layout**: sortable by priority
- **Empty state** with "Clear all filters" button
- Keyboard: `/` to focus search, `Esc` to close modal

**What to avoid:**
- Rainbow of 13+ seniority badge colors
- 14+ teams without grouping
- Stats that just count things (show percentages)
- Gray text below 4.5:1 contrast
- Jargon badges like "ZoomInfo Likely"

Save to `output/orgchart/{company}-{target}-{date}.html`.

## Manager prediction scoring

```
score = seniority_gap + team_match + geo + experience_delta
```

| Factor | Condition | Score |
|--------|-----------|-------|
| Seniority gap | Exactly 1 level above | +10 |
| Seniority gap | 2 levels above | +5 |
| Team match | Same team | +8 |
| Team match | Related (substring) | +3 |
| Geo | Same city | +2 |
| Experience | 3+ more years | +2 |

Highest score wins. Min threshold: 5.

## When NOT to use

- User already has a CSV and wants enrichment -> use gtm-meta-skill
- User needs email/phone for outreach -> this skill maps orgs, use gtm-meta-skill for contact info after
