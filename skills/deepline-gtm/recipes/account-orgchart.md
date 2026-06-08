# Account Org Chart Builder

Build an interactive HTML org chart for account mapping: find decision makers, map reporting structures, identify the buying committee, and surface warm intro paths.

## When to use

- User asks to "map an account" or "build an org chart"
- User wants to find "who reports to X" or "decision makers at Y"
- User wants to map the **buying committee / buying group / decision-making unit** (economic buyer, champion, technical evaluator, blocker)
- User has a warm connection and wants to find paths through the org

## Inputs

One of:

- LinkedIn URL (+ optional company/domain)
- Name + company name or domain
- Just a company domain (maps the full GTM org)

If only a name is given with no company context, ask before proceeding.

### Deal context intake

Before running the waterfall, capture the deal context that changes who matters. If the user already gave enough context, proceed and do not interrogate them. If key context is missing, ask at most 1-2 critical questions before execution.

| Context field | Why it matters |
| ------------- | -------------- |
| Product or service being sold | Changes the owning function, technical evaluator, and likely blocker |
| Deal stage | Prospecting, single-threaded, active evaluation, or stuck deal changes the entry strategy |
| Existing contacts or CRM relationships | Preserves warm paths and avoids buying data already owned |
| Target function | Keeps the committee focused instead of mapping every executive |
| Company size or account segment | Right-sizes the committee and prevents over-threading small accounts |
| Known champion, blocker, or economic buyer | Anchors the output around real deal evidence, not title guesses |

Right-size the target committee:

| Segment | Target committee size |
| ------- | --------------------- |
| SMB | 2-3 people |
| Mid-market | 4-6 people |
| Enterprise | 6-12 people |

## Two modes - pick before you start

The waterfall below defaults to **company-wide mapping** (domain to every employee). But a lot of requests are actually **person-centric** ("build a 2-up / 2-down around this person"). They need different handling, and confusing them spends user budget and produces a worse chart.

| Signal in the request                                                                                | Mode               | What changes                                                                                                                                                        |
| ---------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "map the GTM org at Acme", "who are the decision makers at Acme", a bare domain                      | **company-wide**   | Run the full Section 2 waterfall. Hierarchy is inferred org-wide from title tiers.                                                                                  |
| "build an org chart around Jane Doe", "Jane's manager and her reports", a single LinkedIn URL/person | **person-centric** | Do NOT run the full company waterfall. At a 100k-person enterprise it floods you with thousands of irrelevant people. Use the focused flow in **§2-person** below. |

**Why this matters:** the company-wide waterfall is built to maximize coverage. Person-centric work needs the opposite: a tight neighborhood around one node. Running the wrong mode is the single most common way this recipe disappoints.

### The hard truth about reporting chains

No data source Deepline can reach, including Apollo, PDL, Dropleads, Apify, the `linkedin_scraper` family, or Sales Navigator, exposes a real "reports to" / manager field. LinkedIn does not publish reporting chains, and neither does Sales Nav. It improves _who you can find_, not _who reports to whom_. So **every reporting edge in any org chart this recipe produces is inferred, not retrieved.**

That means:

- The names, titles, LinkedIn URLs, and emails can be high-confidence (they come from real lookups).
- The _edges between them_ are a best guess from title tier + team + location + tenure overlap. At a small startup this guess is usually right. At a 100k-person enterprise it can be ~10-20% confident, because dozens of same-title managers exist in the same city.
- **Be honest about this in the output.** Put a confidence badge on every inferred edge and a one-line disclaimer ("reporting lines inferred from title/team/location, not from LinkedIn data"). Never present an inferred chain as if it were verified. A rep who trusts a wrong chain and name-drops the wrong manager on a call burns the account.

## Quick reference

| Step | What                    | Source                                                              | Spend posture |
| ---- | ----------------------- | ------------------------------------------------------------------- | ------------- |
| 1    | Resolve target          | `leadmagic_profile_search` or `prebuilt/person-linkedin-to-email`   | Metered Deepline action |
| 2a   | Deepline Native search  | `deepline_native_search_contact` (4 title tiers)                    | Metered Deepline action |
| 2b   | Dropleads search        | `dropleads_search_people`                                           | Free or bundled when available |
| 2c   | Apify LinkedIn scrape   | `apify_run_actor_sync` with `harvestapi/linkedin-company-employees` | Metered Deepline action |
| 2d   | Apollo paid search      | `apollo_people_search_paid` (2 pages)                               | Metered Deepline action |
| 2e   | PDL gap-fill (optional) | `peopledatalabs_person_search` CXO+VP only                          | Metered Deepline action |
| 3    | Classify + infer        | Title-based seniority + tenure + recency signals + Claude reasoning | No provider action |
| 4    | Generate output         | HTML org chart file                                                 | No provider action |

Typical run: 150-250 people found, 3-8 minutes. When the user asks about spend, show only Deepline-facing credits or estimates from the tool catalog. Do not discuss supplier-side cost structure.

**Spend-safe order:** CRM first, then bundled/free sources, then broad paid sources, then surgical paid gap-fill for missing senior people only. Each step deduplicates against prior results so you do not pay to rediscover data the customer already owns.

**Before running any paid source:** check your CRM for contacts already at this company. If HubSpot, Salesforce, or another CRM is connected, discover the live CRM tool contract first instead of guessing operation names:

```bash
deepline tools search --categories crm --search_terms "contacts,account,company"
deepline tools describe TOOL_ID_FROM_SEARCH
```

Then execute the discovered CRM contact/account query with the exact schema from `tools describe`. Pull name, title, email, phone, LinkedIn URL, account/company, owner, lifecycle or stage, and last activity when the CRM exposes them.

Merge CRM results first. In the org chart, give CRM contacts a **CRM badge** and `+50` priority score, because you have verified data and a relationship. No need to re-enrich them. If no CRM is connected or no contact-search operation is available, skip this and start at Source 1.

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
  --with '{"alias":"domain","tool":"run_javascript","payload":{"code":"const r=row.domain_search;const url=((r?.results||[])[0]?.url)||\"\";const m=url.match(/^https?:\\/\\/(www\\.)?([^\\/]+)/);return m?m[2]:null;"}}'
```

**If name + company given:**
Create seed CSV with columns: `name`, `company_name`, `domain`. If no domain, resolve with exa_search as above.

### §2-person. Person-centric flow (2-up / 2-down around one person)

Use this instead of the company-wide waterfall when the request centers on one individual. The goal is a tight neighborhood, not a roster.

1. **Resolve and verify the anchor.** Confirm the person currently works where the request claims by scraping their live profile with `apify_run_actor_sync` + `apimaestro/linkedin-profile-detail` (`{"username":"<handle>"}`) and reading the `experience[]` entry with `is_current: true`. This is the same live-verification pattern that catches stale data. Capture their exact team/sub-function, title, location, and tenure. These are your matching signals for the rest of the flow.

2. **Find ±1 / ±2 candidates by constrained search, not full-company scrape.** Search for people at the same company filtered to the anchor's function + location + the adjacent title tiers:
   - **+1 (manager):** one tier up, same team, same metro. e.g. anchor is "Principal Engineer, Austin" then search "Engineering Manager" / "Senior Manager Engineering" at that company in Austin.
   - **+2 (director):** two tiers up, same function.
   - **−1 (reports):** one tier down, same team + a shared specialty signal if you have one (e.g. same sub-discipline).

   Use `dropleads_search_people` (free when available) and `deepline_native_search_contact` with title filters first; fall back to `exa_search` / Google-style queries for enterprises that index poorly. Keep each search scoped. You want ~3-8 candidates per tier, not hundreds.

   **Resolving a candidate's LinkedIn URL from a name:** don't reach for `leadmagic_profile_search` because it is for the reverse direction, hydrating a profile when you already have the URL. For name to LinkedIn URL, use the **Serper to Apify validate** pattern from the sibling [`linkedin-url-lookup`](linkedin-url-lookup.md) recipe: `serper_google_search` with a `site:linkedin.com/in` query, then validate the top hit with an Apify profile scrape and a mandatory name-match gate. Or call the canonical play `prebuilt/person-to-linkedin` (aliases `name_to_linkedin_url_waterfall`, `name-to-linkedin-url`), which wraps this waterfall.

3. **Rank the inferred edges, don't assert them.** For each candidate, score the likelihood they're the actual manager/report using the Manager prediction scoring table below (seniority gap + team match + geo + experience delta + tenure overlap). Surface the top 1-2 per tier _with their score shown as a confidence badge_. When several same-title managers tie (common at big enterprises), show them as parallel candidates rather than picking one. The rep can disambiguate.

4. **Enrich the neighborhood.** Run emails/phones only on the final shortlist via the `prebuilt/person-linkedin-to-email` play (alias `person_linkedin_to_email_waterfall`), using verified providers like Prospeo. Watch for non-obvious corporate domains (e.g. a company named "Acme Corporation" may use `@acme.io`, not `@acmecorporation.com`); take the domain from the enrichment result, don't assume it.

5. **Render** the same HTML chart as §4, but centered on the anchor with the inferred edges badged by confidence and the §"hard truth" disclaimer shown prominently.

**Honest expectation:** emails and LinkedIn URLs from this flow are solid; the reporting edges at a large enterprise are a ranked guess (~10-20% on any single edge). That's the ceiling of title+geo inference without privileged data. Set the rep's expectation accordingly rather than over-claiming.

### 2. Find ALL employees (cost-optimal waterfall)

> Company-wide mode only. For a single-person 2-up/2-down, use **§2-person** above instead. Running this full waterfall on a 100k-employee company buries the one neighborhood you care about.

Run sources cheapest-first. Each step deduplicates against prior results - only net-new people advance.

Use a descriptive, task-named working directory under `deepline/data/` so the user can find the outputs later, not a timestamped or random path:

```bash
WORK_DIR="deepline/data/${COMPANY_SLUG}-orgchart"   # e.g. deepline/data/ramp-orgchart
mkdir -p "$WORK_DIR"
echo "company_domain,company_name" > "$WORK_DIR/accounts.csv"
echo "\"$DOMAIN\",\"$COMPANY\"" >> "$WORK_DIR/accounts.csv"
```

**Source 1: Deepline Native**

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

**Source 3: LinkedIn employee scrape**

Prefer `deepline enrich` for repeatable roster enrichment and use a direct actor call only as a probe. Resolve the company's LinkedIn page from the domain first, then run the current company-employees actor after confirming the contract:

```bash
deepline tools describe apify_run_actor_sync
deepline tools execute apify_run_actor_sync --payload '{"actorId":"harvestapi/linkedin-company-employees","input":{"companyLinkedinUrls":["LINKEDIN_COMPANY_URL"],"maxItems":25},"timeoutMs":300000}'
```

Pilot with a small `maxItems` first, then write the final roster into `"$WORK_DIR/li-employees.csv"` or add it as an enrichment pass. Expected: +15-25 net new.

> If you genuinely need a raw actor call (e.g. a different roster actor), the current company-roster actor is `harvestapi/linkedin-company-employees` (input: `companyLinkedinUrls` string[] required, optional `maxItems`/`profileDepth`), and the per-profile actor is `apimaestro/linkedin-profile-detail` (input `{"username":"<handle>"}`, returns an `experience[]` array where the live role has `is_current: true`, the cleanest "where do they work today" signal). Actor ids and input keys drift; confirm with `deepline tools describe apify_run_actor_sync` (its `apifyKnownActors` list) before relying on any of them.

**Source 4: Apollo paid search**

```bash
deepline tools execute apollo_people_search_paid --payload '{"q_organization_domains_list":["DOMAIN"],"per_page":100,"page":1}'
deepline tools execute apollo_people_search_paid --payload '{"q_organization_domains_list":["DOMAIN"],"per_page":100,"page":2}'
```

Expected: +80-100 net new.

**Source 5: PDL surgical gap-fill - ONLY for missing senior people**

After building initial hierarchy, identify gaps (e.g., "5 Sales Directors but no VP Sales"):

```bash
deepline tools execute peopledatalabs_person_search --payload '{"size":30,"sql":"SELECT * FROM person WHERE job_company_website = \"DOMAIN\" AND (job_title_levels = \"cxo\" OR job_title_levels = \"vp\")"}'
```

Pull CXO+VP only, then dedupe. Keep this surgical so the user does not pay for broad duplicate coverage.

Merge all results, deduplicate by slugified name.

### 3. Classify seniority + infer hierarchy

**Seniority classification (check in order, first match wins):**

| Rank | Level       | Patterns                                      |
| ---- | ----------- | --------------------------------------------- |
| 0    | ceo         | "ceo", "chief executive"                      |
| 1    | c-level     | "chief" + any (cto, cfo, coo, cmo, cro)       |
| 2    | evp         | "evp", "executive vice president"             |
| 3    | svp         | "svp", "senior vice president"                |
| 4    | vp          | "vice president", "vp", "area vice president" |
| 5    | sr-director | "senior director"                             |
| 6    | director    | "head of", "director"                         |
| 7    | sr-manager  | "senior manager"                              |
| 8    | manager     | "manager"                                     |
| 9    | principal   | "principal", "staff"                          |
| 10   | lead        | "lead"                                        |
| 11   | senior      | "senior", "sr."                               |
| 12   | ic          | everything else                               |

**Tenure-weighted seniority adjustment:**

A title alone is a weak signal. Adjust effective influence after initial classification:

| Condition                           | Adjustment                                                          |
| ----------------------------------- | ------------------------------------------------------------------- |
| Manager/Director, tenure < 6 months | -1 effective rank (treat as 1 level below)                          |
| Manager/Director, tenure >= 2 years | +1 effective rank (treat as 1 level above)                          |
| VP/C-level, tenure < 3 months       | flag as `newly_hired_exec = true` (see priority scoring)            |
| IC/Senior, tenure >= 5 years        | flag as `long_tenured_ic = true` (informal influence, worth noting) |

Tenure = months since `start_date` at current company. If `start_date` is unavailable, skip adjustment (don't guess).

**For display, simplify to 4 levels** (use effective rank after tenure adjustment):

- **exec**: ceo, c-level, evp, svp, vp -> color #a78bfa
- **director**: sr-director, director -> color #60a5fa
- **manager**: sr-manager, manager, principal, lead -> color #34d399
- **ic**: senior, ic -> color #525252

**Team consolidation (if >8 teams):**
| Original | Simplified |
|----------|------------|
| Executive Leadership, Office of CEO | Leadership |
| Sales, GTM, Business Development | Sales |
| Revenue Operations, Sales Operations | Revenue Ops |
| Sales Enablement | Enablement |
| Marketing, Demand Gen | Marketing |
| Customer Success, Support | Customer Success |
| AI, Product, Engineering, Data | Product & Eng |
| HR, People, Finance, Legal | Other |

Infer teams from title patterns (text after comma).

### 3b. Hiring velocity & staleness risk

After classifying all people, compute per-department hiring velocity to flag stale sections of the chart:

```
For each team/department:
  recent_hires = count of people with tenure < 90 days
  total_headcount = count of people in team
  velocity_ratio = recent_hires / total_headcount
```

| velocity_ratio | Staleness risk               | Display                                       |
| -------------- | ---------------------------- | --------------------------------------------- |
| >= 0.30        | HIGH, chart may be outdated | amber `⚡ Growing fast` badge on team sidebar |
| 0.15 - 0.29    | MEDIUM, some churn expected | no badge                                      |
| < 0.15         | LOW                          | no badge                                      |

**Surfacing this in the UI:**

- Add a `⚡ Growing fast` amber badge next to any team in the left sidebar with HIGH velocity
- In the warm path banner (if shown), append: _"Note: [Team] is growing fast, contacts may have changed recently."_
- In the stats bar, add a clickable chip: `"N new hires (<90 days)"` that filters to recently-joined people

This tells the rep: if Sales has 35% new hires, the org chart you're looking at is probably 30-60 days stale for that team. Re-verify before a big send.

### 3c. Map the buying committee (what makes the chart actually sell)

A static org chart of titles ages out quickly and rarely tells a rep who to call. What closes deals is a **buying-committee map**: the cluster of people involved in a purchase, each tagged with their _role in the deal_, not just their title. After classifying seniority, assign committee roles using the deal context from the intake section.

**Title to committee-role mapping.** Titles are a starting signal, not proof. Assign a role to each relevant contact, then verify behavior where you can. A "champion" is defined by behavior, not title.

| Role                            | Maps from these titles                                                                           | Why they matter |
| ------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------- |
| **Economic buyer**              | CFO, VP Finance, CRO, GM/BU owner, P&L-owning Director; for smaller deals the owning-function VP | Approves the spend. Not always the most senior person. |
| **Champion**                    | RevOps/Sales Ops, Enablement, Demand Gen lead, the Director closest to the pain                  | Sells internally for you. Title matters least here. |
| **Coach**                       | Friendly former user, partner contact, customer success lead, IC with strong access              | Gives process guidance but may not sell internally. Do not confuse with champion. |
| **Technical buyer / evaluator** | VP/Director Engineering, Architect, Director of IT, CISO, Data Privacy Officer                   | Can kill the deal on technical, security, or integration grounds. |
| **Procurement / legal**         | Procurement, Vendor Management, Legal, Privacy, Compliance                                      | Owns commercial and policy friction late in the process. Surface early. |
| **Blocker / final authority**   | CISO, Head of Compliance, General Counsel, Procurement/Vendor Mgmt                               | Quiet, risk-driven veto. Surface early. |
| **End user / influencer**       | ICs in the owning function; Staff/Principal/Senior Architect                                     | Adoption sign-off and peer consensus. |
| **Executive sponsor**           | Relevant C-suite/SVP (CRO, CMO, CTO, CEO)                                                        | Ties the purchase to strategy. |

Example: a security sale where the **CISO champions**, the **CFO is economic buyer**, the **CTO evaluates**, and the **CEO sponsors**. Four titles, four roles, one deal.

**Signals that reveal who's actually on the committee** beyond title: open **job postings** (who owns the function + current tooling pain), **recent exec hires/promotions** (new budget + mandate to switch), **technographics ownership** (who lists the tool on LinkedIn can be the real technical evaluator), **content/intent engagement**, prior CRM conversations, and discovery-call mentions ("who else is involved, who signs, who could quietly stop this"). Note in the output where the rep should confirm the committee by asking.

**Hidden influencer and champion-potential signals:**

| Signal | Why it matters |
| ------ | -------------- |
| Staff, Principal, Lead, Architect, Admin, or EA title | May control technical consensus, executive access, or calendar flow |
| Recently joined or promoted in the owning function | Likely to have a mandate and lower attachment to incumbent tools |
| Former user, former customer employee, or prior company used the product category | Higher odds they understand the pain and can coach the process |
| Long-tenured IC in the buying function | Often trusted informally even without a manager title |
| Mutual investor, customer, partner, alumni, or coworker path | Raises access quality and reply probability |
| Public content about the problem area | Indicates personal stake or active evaluation |

Classify each committee member with these output fields:

| Field | Allowed values or shape |
| ----- | ----------------------- |
| `committee_role` | `economic_buyer`, `champion`, `coach`, `technical_evaluator`, `procurement_legal`, `blocker`, `end_user`, `executive_sponsor`, `unknown` |
| `disposition` | `champion`, `supportive`, `neutral`, `skeptical`, `detractor`, `unknown` |
| `access_level` | `direct`, `warm_path`, `crm_relationship`, `indirect`, `none` |
| `influence_level` | `high`, `medium`, `low`, `unknown` |
| `key_concern` | One short phrase tied to title, team, job post, CRM note, or public signal |
| `how_to_win` | One recommended engagement angle |
| `risk_if_ignored` | One concrete risk if this person is not engaged |
| `next_action` | `contact_now`, `warm_intro`, `monitor`, `ask_champion`, `do_not_contact_yet` |
| `evidence` | Source names and short reason, never a bare assertion |

### 3d. Multi-threading sequence

Do not tell the rep to "contact everyone." Pick a sequencing strategy based on deal context and account size.

| Situation | Strategy | First contacts | Notes |
| --------- | -------- | -------------- | ----- |
| No known contacts | Access line | Coach or warm path, then champion, then economic buyer | Start where access is strongest, not necessarily highest title |
| Active single-threaded deal | Dual track | Champion plus one technical evaluator or end user | Add coverage without surprising the champion |
| Stuck deal | Power line | Executive sponsor or economic buyer plus blocker/procurement | Use when the current path cannot unblock budget or risk |
| Small account | Thin committee | 2-3 people max | Avoid over-threading and creating internal noise |
| Enterprise account | Layered committee | 6-12 people across owning function, technical, finance, and legal/procurement | Sequence over time, do not blast all contacts at once |

Reflect this in the chart (§4): show `committee_role`, `disposition`, `access_level`, `influence_level`, and `next_action` on every relevant contact. Prioritize 3-5 immediate contacts for a normal mid-market account, then list additional people as monitor or ask-champion targets.

### 4. Generate HTML org chart

**Design system (avoid AI slop):**

- Dark mode: `--bg: #0a0a0a`, `--surface: #141414`, `--border: #262626`
- Text: `--text: #e5e5e5`, `--text-muted: #a3a3a3`
- Warm path: `--warm: #f59e0b` with `rgba(245, 158, 11, 0.15)` glow
- Inter font only

**Critical UX elements:**

- **Warm path banner** at top if user has a connection (amber highlight, "Show warm connections" CTA)
- **Priority score column** (0-100): see scoring below
- **Clickable stats bar**: "234 with email (18%)" filters to email=true on click; "N new hires (<90 days)" filters to recently joined
- **Team sidebar** (left): collapsed teams with counts + `⚡ Growing fast` badges where applicable, click to filter
- **Table layout**: sortable by priority, columns = Priority | Name/Title | Committee Role | Disposition | Access | Team | Level | Tenure | Contact | Next Action
- **Committee coverage panel**: immediate contacts, monitor contacts, and ask-champion questions
- **Evidence drawer**: click a role or edge to see the source and why Deepline inferred it
- **Empty state with clear action**: "No contacts match - Clear all filters" button
- Keyboard: `/` to focus search, `Esc` to close modal

**Data contract for the generated chart:**

```ts
type OrgChartNode = {
  id: string;
  parent_id: string | null;
  name: string;
  title: string;
  team: string;
  seniority_level: "exec" | "director" | "manager" | "ic";
  committee_role:
    | "economic_buyer"
    | "champion"
    | "coach"
    | "technical_evaluator"
    | "procurement_legal"
    | "blocker"
    | "end_user"
    | "executive_sponsor"
    | "unknown";
  disposition: "champion" | "supportive" | "neutral" | "skeptical" | "detractor" | "unknown";
  access_level: "direct" | "warm_path" | "crm_relationship" | "indirect" | "none";
  influence_level: "high" | "medium" | "low" | "unknown";
  priority_score: number;
  champion_potential_score: number;
  next_action: "contact_now" | "warm_intro" | "monitor" | "ask_champion" | "do_not_contact_yet";
  key_concern: string | null;
  how_to_win: string | null;
  risk_if_ignored: string | null;
  contact: {
    linkedin_url?: string;
    email?: string;
    phone?: string;
    crm_badge?: boolean;
  };
  reporting_edge: {
    inferred: true;
    confidence: "high" | "medium" | "low";
    evidence: string[];
  } | null;
  role_evidence: string[];
};
```

Keep `reporting_edge` separate from `committee_role`. Reporting lines are inferred hierarchy guesses. Committee roles are deal hypotheses based on title, context, CRM, and signal evidence.

**What to avoid (AI slop tells):**

- Rainbow of 13+ seniority badge colors
- 14+ teams without grouping
- Stats that just count things (show percentages, make clickable)
- Gray text below 4.5:1 contrast ratio
- Jargon badges like "ZoomInfo Likely"
- Hero metrics layout with identical cards

Save to `deepline/data/{company-slug}-orgchart/{company}-orgchart.html` (same descriptive working dir as the data, so the chart and its backing CSVs live together and the user can find them).

## Priority scoring

```
score = title_score + contact_score + warm_score + recency_bonus + champion_potential_bonus
```

| Factor                 | Condition                                        | Score                             |
| ---------------------- | ------------------------------------------------ | --------------------------------- |
| Title                  | exec level                                       | +40                               |
| Title                  | director level                                   | +25                               |
| Title                  | manager level                                    | +10                               |
| Contact                | has email                                        | +25                               |
| Contact                | has phone                                        | +10                               |
| Warm                   | warm connection                                  | +30                               |
| **Job change recency** | newly_hired_exec = true (exec, tenure < 90 days) | **+20 bonus**                     |
| **Job change recency** | any level, tenure < 30 days                      | **+10 bonus**                     |
| Champion potential     | champion_potential_score >= 45                   | +15                               |
| Champion potential     | champion_potential_score >= 30                   | +8                                |
| Tenure (negative)      | tenure < 6 months AND manager/director level     | -5 (lower influence, less stable) |

**Why newly-hired execs get a +20 bonus:** A new VP of Sales or CTO is actively remapping their vendor stack in the first 90 days. They have the most buying authority and the lowest incumbent loyalty. This is the highest-value outreach window in the sales cycle.

Display `🆕` badge in the Name column for anyone with tenure < 90 days so reps can spot them instantly without sorting.

## Champion and hidden influencer scoring

Compute `champion_potential_score` on a 0-60 scale. This score is not a claim that someone is already a champion. It tells the rep who is worth testing for champion behavior.

| Factor | Condition | Score |
| ------ | --------- | ----- |
| Role relevance | In owning function for the deal context | +12 |
| Role relevance | Adjacent function with clear stake | +6 |
| Influence | Director+ in owning function | +12 |
| Influence | Staff, Principal, Lead, Architect, Admin, EA, or long-tenured IC | +8 |
| Accessibility | Direct CRM relationship or prior conversation | +12 |
| Accessibility | Warm path through customer, investor, partner, or coworker | +8 |
| Change agent | Joined or promoted in last 180 days | +8 |
| Change agent | Prior company used the product category or competitor | +6 |
| Personal stake | Public content, job post ownership, or CRM note tied to the pain | +8 |
| Engagement potential | Has email or LinkedIn plus a specific reason to reach out | +8 |

Classify score bands:

| Score | Label | Action |
| ----- | ----- | ------ |
| 45-60 | High champion potential | Contact or warm-intro early |
| 30-44 | Medium champion potential | Use as access line or ask current champion |
| 15-29 | Low champion potential | Monitor unless they fill a required committee role |
| 0-14 | Unknown | Do not over-prioritize without more evidence |

Keep Coach and Champion separate. A coach can explain the process but may not have political capital. A champion has pain, influence, access, and willingness to sell internally. Mark `disposition = champion` only when evidence supports behavior, not just score.

## Manager prediction scoring

```
score = seniority_gap + team_match + geo + experience_delta
```

| Factor        | Condition             | Score |
| ------------- | --------------------- | ----- |
| Seniority gap | Exactly 1 level above | +10   |
| Seniority gap | 2 levels above        | +5    |
| Team match    | Same team             | +8    |
| Team match    | Related (substring)   | +3    |
| Geo           | Same city             | +2    |
| Experience    | 3+ more years         | +2    |

Highest score wins. Min threshold: 5.

## When NOT to use

- User already has a CSV and wants enrichment -> use enriching-and-researching.md
- User needs email/phone for outreach -> this recipe maps orgs, use enrichment recipes for contact info after
