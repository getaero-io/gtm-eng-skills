---
name: deepline-org-chart
description: 'Build an interactive account org chart, leadership map, buying committee, or manager/report neighborhood around a person. Use for decision makers, reporting-line candidates, stakeholder mapping, and warm intro paths. Skip standalone email lookup and unrelated cross-company prospecting.'
---

# Account Org Chart Builder

Build an interactive HTML org chart for account mapping: find decision makers, map reporting structures, identify the buying committee, and surface warm intro paths.

## Contents

- [Inputs and deal context](#inputs)
- [Mapping modes and reporting evidence](#two-modes---pick-before-you-start)
- [Discovery pipeline](#pipeline)
- [HTML chart and data contract](#4-generate-html-org-chart)
- [Priority scoring](#priority-scoring)
- [Manager prediction](#manager-prediction-scoring)

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

Capture product, deal stage, existing CRM relationships, target function, company size, and known champions/blockers/buyers. Reuse supplied context; ask at most 1-2 questions that change execution.

Target 2-3 committee members for SMB, 4-6 for mid-market, and 6-12 for enterprise. These are committee sizes, not roster limits.

## Two modes - pick before you start

- **Company-wide:** a domain or request for the account's GTM org/decision makers. Use Section 2 within the agreed scope and fill coverage gaps.
- **Person-centric:** a person, LinkedIn URL, or manager/report request. Use **§2-person** for a focused 2-up/2-down neighborhood; do not run the full company waterfall.

### The hard truth about reporting chains

People search usually establishes employment and titles, not reporting chains. Treat title/team/location-based edges as hypotheses. A dated official announcement, explicit manager field with provenance, or user-supplied org chart can support a sourced edge; record that evidence instead of claiming all edges are necessarily inferred.

Label every edge as `inferred`, `sourced`, or `manual`, with its basis and qualitative confidence. Confidence describes evidence strength, not a calibrated probability. Keep ambiguous people in **Needs review** with `parent_id: null`; never attach them to the CEO just to make a connected tree. Manual corrections are user assertions, not independently verified facts.

## Quick reference

| Step | What             | Source                                                              |
| ---- | ---------------- | ------------------------------------------------------------------- |
| 1    | Resolve target   | A profile lookup tool, found with `deepline search`                 |
| 2    | Find employees   | `prebuilt/company-to-contact`, then people-search tools from search |
| 3    | Classify + infer | Title-based seniority + tenure + recency signals + Claude reasoning |
| 4    | Generate output  | HTML org chart file                                                 |

When the user asks about spend, show only Deepline-facing credits or estimates from the tool catalog. Do not discuss supplier-side cost structure.

**Spend-safe order:** CRM first, then free sources, then broad paid sources, then surgical paid gap-fill for missing senior people only. Each step deduplicates against prior results so you do not pay to rediscover data the customer already owns. `deepline tools describe <tool> --pricing-only` shows what each tool costs.

**Before running any paid source:** check your CRM for contacts already at this company. If HubSpot, Salesforce, or another CRM is connected, discover the live CRM tool contract first instead of guessing operation names:

```bash
deepline search "company domain -> CRM account and its contacts" --categories crm
deepline tools describe TOOL_ID_FROM_SEARCH
```

Then execute the discovered CRM contact/account query with the exact schema from `tools describe`. Pull name, title, email, phone, LinkedIn URL, account/company, owner, lifecycle or stage, and last activity when the CRM exposes them.

Merge CRM results first. In the org chart, give CRM contacts a **CRM badge** and `+50` priority score, because you have verified data and a relationship. No need to re-enrich them. If no CRM is connected or no contact-search operation is available, skip this and start at Source 1.

## Pipeline

### 1. Resolve target identity

Resolve the target company to its official domain and stable company identity (provider ID and canonical LinkedIn company URL when available). A shared domain, similar company name, or acquisition alone does not prove the same employer. Keep parent, subsidiary, franchise, region, and business-unit scopes separate unless the user requests a combined map. Ask only when multiple plausible entities would change the roster.

Preserve each source record and retrieval time. Prefer the experience/current-position record tied to the resolved employer over a headline or stale CRM title. Keep conflicting current roles visible for review. Normalize LinkedIn URLs by removing tracking parameters/trailing slashes, without changing profile identity.

Agree on the requested function/seniority and a bounded first pass (default up to 30 people for a leadership map). An all-employee request can use a larger stated bound. Inspect a small first page before scaling. Stop once the requested coverage is met; a waterfall is a set of gap-fill options, not an instruction to exhaust every provider. Save provider cursors/session IDs and query scope so an “add more” request resumes instead of repurchasing the same pages.

This recipe orchestrates ONE account (or one person). Run the calls below
directly with real values. Building org charts across a LIST of accounts, or
rerunning this weekly? Author the pipeline once as a custom play
(`deepline plays --help`) — each step below becomes one column,
and the tier pulls become `ctx.runPlay('prebuilt/company-to-contact', ...)`.

**If LinkedIn URL given:** find a profile lookup tool and read the target's
identity off its result, using the getters `tools describe` documents:

```bash
deepline search "a person's LinkedIn profile URL -> their name, title, company and location"
```

Name, title, company, and location drive every matching signal downstream. If
the company domain is missing, resolve it with a search for the company's
website, and prefer the domain a later enrichment result reports over one you
inferred.

Verify the candidate is the official company website before taking its domain; the first search result alone is not identity evidence.

**If name + company given:** resolve the LinkedIn URL first
(`deepline search "person name and company -> LinkedIn profile URL"` lists the prebuilt for it), or
go straight to the company-wide search with the domain.

### §2-person. Person-centric flow (2-up / 2-down around one person)

Use this instead of the company-wide search when the request centers on one individual. The goal is a tight neighborhood, not a roster.

1. **Resolve and verify the anchor.** Confirm the person currently works where the request claims by fetching their live profile and reading the current position. This live-verification step catches stale data. Capture their exact team/sub-function, title, location, and tenure; these are the matching signals for the rest of the flow.

2. **Find ±1 / ±2 candidates by constrained search, not full-company scrape.** Search for people at the same company filtered to the anchor's function + location + the adjacent title tiers:
   - **+1 (manager):** one tier up, same team, same metro. e.g. anchor is "Principal Engineer, Austin" then search "Engineering Manager" / "Senior Manager Engineering" at that company in Austin.
   - **+2 (director):** two tiers up, same function.
   - **−1 (reports):** one tier down, same team + a shared specialty signal if you have one (e.g. same sub-discipline).

   Use people-search tools with title filters, free ones first; fall back to web search for enterprises that index poorly. Keep each search scoped. You want ~3-8 candidates per tier, not hundreds.

   **Resolving a candidate's LinkedIn URL from a name:** a profile lookup tool goes the other way (URL to profile). For name to URL, search for a LinkedIn URL lookup and check that the name on the returned profile matches before using it.

3. **Rank the inferred edges, don't assert them.** For each candidate, rank the manager/report candidates using the Manager prediction scoring table below (seniority gap + team match + geo + experience delta + tenure overlap). Surface the top 1-2 per tier _with the ranking score separate from evidence confidence_. When several same-title managers tie (common at big enterprises), show them as parallel candidates rather than picking one. The rep can disambiguate.

4. **Enrich the neighborhood when requested.** Run emails/phones only on the approved final shortlist via the `prebuilt/person-linkedin-to-email` play. Watch for non-obvious corporate domains (e.g. a company named "Acme Corporation" may use `@acme.io`, not `@acmecorporation.com`); take the domain from the enrichment result, don't assume it.

5. **Render** the same HTML chart as §4, but centered on the anchor with the inferred edges badged by confidence and the §"hard truth" disclaimer shown prominently.

**Honest expectation:** validate identity and contact results before outreach. A manager ranking is a heuristic, not a measured probability; ties and missing team evidence remain unresolved.

### 2. Find people within the agreed scope

> Company-wide mode only. For a single-person 2-up/2-down, use **§2-person** above instead. Running this full search on a 100k-employee company buries the one neighborhood you care about.

Run sources cheapest-first. Each step deduplicates against prior results - only net-new people advance.

Use a descriptive, task-named working directory under `deepline/data/` so the user can find the outputs later, not a timestamped or random path:

```bash
WORK_DIR="deepline/data/${COMPANY_SLUG}-orgchart"   # e.g. deepline/data/ramp-orgchart
mkdir -p "$WORK_DIR"
echo "company_domain,company_name" > "$WORK_DIR/accounts.csv"
echo "\"$DOMAIN\",\"$COMPANY\"" >> "$WORK_DIR/accounts.csv"
```

**Source 1: role-targeted contact discovery.** The prebuilt covers this step, one call per seniority tier:

```bash
deepline plays run prebuilt/company-to-contact --input '{"domain": "'"$DOMAIN"'", "roles": ["CEO", "CTO", "CFO", "COO", "CMO", "CRO", "Founder"], "seniority": "C-Level"}'
deepline plays run prebuilt/company-to-contact --input '{"domain": "'"$DOMAIN"'", "roles": ["VP", "SVP"], "seniority": "VP"}'
```

Expected: ~25-35 people.

**Source 2: the wider roster.** Find the people-search and employee-list tools and prebuilts for a company, and confirm each one's current Deepline credits before running it:

```bash
deepline search "a company domain -> the people who work there, with titles and LinkedIn URLs"
```

Each tool's `tools describe` output carries its paging and billing notes; read them before requesting large pages.

**Source 3: surgical gap-fill, ONLY for missing senior people.** After building the initial hierarchy, identify gaps (e.g., "5 Sales Directors but no VP Sales") and search for that seniority at that company with a small limit. Fetch another small page only if the specific gap remains: a broad page followed by deduplication still spends credits on duplicates.

Merge by stable provider ID within a provider, then canonical LinkedIn URL across providers. Name plus employer is only a candidate match: retain same-name people separately until another signal confirms identity. Keep all merged source IDs and field provenance.

Record counts for retrieved rows, duplicate rows merged, out-of-scope exclusions (with reasons), and retained unique people. Show whether pagination is exhausted or coverage is partial; retained is not total company headcount. Unknown-employer records stay in a review set. A sparse result is valid, not permission to invent people.

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

**Title scope and tenure:**

Classify the exact current title and its scope. Field/deputy/fractional CTO, regional President, board member, and former executive do not establish global C-suite authority. Principal/Staff roles do not by themselves establish people-management responsibility. Preserve the title; use function lanes only for navigation.

Store `role_start_date` separately from `company_start_date`, each nullable and sourced. A promotion resets role tenure, not company tenure. Label a recent role as “new in role”; call someone a new hire only when company-start evidence supports it. Do not change their hierarchy rank because of tenure. Long company tenure can inform an influence hypothesis without changing their title.

**For display, simplify title tiers to 4 levels:**

- **exec**: ceo, c-level, evp, svp, vp -> color #a78bfa
- **director**: sr-director, director -> color #60a5fa
- **manager**: sr-manager, manager -> color #34d399
- **ic**: principal, staff, lead (unless management is evidenced), senior, ic -> color #525252

**Team consolidation (if >8 teams):**

| Original                             | Simplified       |
| ------------------------------------ | ---------------- |
| Executive Leadership, Office of CEO  | Leadership       |
| Sales, GTM, Business Development     | Sales            |
| Revenue Operations, Sales Operations | Revenue Ops      |
| Sales Enablement                     | Enablement       |
| Marketing, Demand Gen                | Marketing        |
| Customer Success, Support            | Customer Success |
| AI, Product, Engineering, Data       | Product & Eng    |
| HR, People, Finance, Legal           | Other            |

Infer teams from title patterns (text after comma).

### 3b. Freshness and company context

Show `checked_at` and source dates for the roster. Count verified recent company starts separately from recent role starts. Show unknown dates and the number of records with usable dates; a partial leadership sample cannot establish company hiring velocity or growth. Recent changes can justify a targeted refresh, not a claim that the chart is a fixed number of days stale.

When news is requested, use a stated date window (default three months), verify publication dates and article URLs, and deduplicate syndicated coverage. Keep company news separate from reporting evidence; connect an article to a person by stable node ID only when it names them. Preserve an empty result with `checked_at` when no relevant news is found.

### 3c. Map the buying committee (what makes the chart actually sell)

A static org chart of titles ages out quickly and rarely tells a rep who to call. What closes deals is a **buying-committee map**: the cluster of people involved in a purchase, each tagged with their _role in the deal_, not just their title. After classifying seniority, assign committee roles using the deal context from the intake section.

**Title to committee-role mapping.** Titles are a starting signal, not proof. Assign a role to each relevant contact, then verify behavior where you can. A "champion" is defined by behavior, not title.

| Role                            | Maps from these titles                                                                           | Why they matter                                                                   |
| ------------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| **Economic buyer**              | CFO, VP Finance, CRO, GM/BU owner, P&L-owning Director; for smaller deals the owning-function VP | Approves the spend. Not always the most senior person.                            |
| **Champion**                    | RevOps/Sales Ops, Enablement, Demand Gen lead, the Director closest to the pain                  | Sells internally for you. Title matters least here.                               |
| **Coach**                       | Friendly former user, partner contact, customer success lead, IC with strong access              | Gives process guidance but may not sell internally. Do not confuse with champion. |
| **Technical buyer / evaluator** | VP/Director Engineering, Architect, Director of IT, CISO, Data Privacy Officer                   | Can kill the deal on technical, security, or integration grounds.                 |
| **Procurement / legal**         | Procurement, Vendor Management, Legal, Privacy, Compliance                                       | Owns commercial and policy friction late in the process. Surface early.           |
| **Blocker / final authority**   | CISO, Head of Compliance, General Counsel, Procurement/Vendor Mgmt                               | Quiet, risk-driven veto. Surface early.                                           |
| **End user / influencer**       | ICs in the owning function; Staff/Principal/Senior Architect                                     | Adoption sign-off and peer consensus.                                             |
| **Executive sponsor**           | Relevant C-suite/SVP (CRO, CMO, CTO, CEO)                                                        | Ties the purchase to strategy.                                                    |

Example: a security sale where the **CISO champions**, the **CFO is economic buyer**, the **CTO evaluates**, and the **CEO sponsors**. Four titles, four roles, one deal.

**Signals that reveal who's actually on the committee** beyond title: open **job postings** (who owns the function + current tooling pain), **recent exec hires/promotions** (new budget + mandate to switch), **technographics ownership** (who lists the tool on LinkedIn can be the real technical evaluator), **content/intent engagement**, prior CRM conversations, and discovery-call mentions ("who else is involved, who signs, who could quietly stop this"). Note in the output where the rep should confirm the committee by asking.

**Hidden influencer and champion-potential signals:**

| Signal                                                                            | Why it matters                                                      |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Staff, Principal, Lead, Architect, Admin, or EA title                             | May control technical consensus, executive access, or calendar flow |
| Recently joined or promoted in the owning function                                | Likely to have a mandate and lower attachment to incumbent tools    |
| Former user, former customer employee, or prior company used the product category | Higher odds they understand the pain and can coach the process      |
| Long-tenured IC in the buying function                                            | Often trusted informally even without a manager title               |
| Mutual investor, customer, partner, alumni, or coworker path                      | Raises access quality and reply probability                         |
| Public content about the problem area                                             | Indicates personal stake or active evaluation                       |

Classify each committee member with these output fields:

| Field             | Allowed values or shape                                                                                                                  |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `committee_role`  | `economic_buyer`, `champion`, `coach`, `technical_evaluator`, `procurement_legal`, `blocker`, `end_user`, `executive_sponsor`, `unknown` |
| `disposition`     | `champion`, `supportive`, `neutral`, `skeptical`, `detractor`, `unknown`                                                                 |
| `access_level`    | `direct`, `warm_path`, `crm_relationship`, `indirect`, `none`                                                                            |
| `influence_level` | `high`, `medium`, `low`, `unknown`                                                                                                       |
| `key_concern`     | One short phrase tied to title, team, job post, CRM note, or public signal                                                               |
| `how_to_win`      | One recommended engagement angle                                                                                                         |
| `risk_if_ignored` | One concrete risk if this person is not engaged                                                                                          |
| `next_action`     | `contact_now`, `warm_intro`, `monitor`, `ask_champion`, `do_not_contact_yet`                                                             |
| `evidence`        | Source names and short reason, never a bare assertion                                                                                    |

### 3d. Multi-threading sequence

Do not tell the rep to "contact everyone." Pick a sequencing strategy based on deal context and account size.

| Situation                   | Strategy          | First contacts                                                                | Notes                                                          |
| --------------------------- | ----------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------- |
| No known contacts           | Access line       | Coach or warm path, then champion, then economic buyer                        | Start where access is strongest, not necessarily highest title |
| Active single-threaded deal | Dual track        | Champion plus one technical evaluator or end user                             | Add coverage without surprising the champion                   |
| Stuck deal                  | Power line        | Executive sponsor or economic buyer plus blocker/procurement                  | Use when the current path cannot unblock budget or risk        |
| Small account               | Thin committee    | 2-3 people max                                                                | Avoid over-threading and creating internal noise               |
| Enterprise account          | Layered committee | 6-12 people across owning function, technical, finance, and legal/procurement | Sequence over time, do not blast all contacts at once          |

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
- **Team sidebar** (left): collapsed function lanes with counts, click to filter; lanes are not reporting relationships
- **Hierarchy view**: readable top-down chart, leadership-only toggle, and person focus showing manager candidates and reports; keep the table as an alternate view
- **Needs review**: visible unplaced people and ambiguous manager candidates; filters must not make unresolved people disappear from coverage counts
- **Corrections**: editable manager with keyboard-accessible selection, optional drag/drop, cycle/self-link rejection, and exportable manual overrides keyed by stable person IDs
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
  seniority_level: 'exec' | 'director' | 'manager' | 'ic';
  committee_role:
    | 'economic_buyer'
    | 'champion'
    | 'coach'
    | 'technical_evaluator'
    | 'procurement_legal'
    | 'blocker'
    | 'end_user'
    | 'executive_sponsor'
    | 'unknown';
  disposition:
    | 'champion'
    | 'supportive'
    | 'neutral'
    | 'skeptical'
    | 'detractor'
    | 'unknown';
  access_level:
    | 'direct'
    | 'warm_path'
    | 'crm_relationship'
    | 'indirect'
    | 'none';
  influence_level: 'high' | 'medium' | 'low' | 'unknown';
  priority_score: number;
  champion_potential_score: number;
  next_action:
    | 'contact_now'
    | 'warm_intro'
    | 'monitor'
    | 'ask_champion'
    | 'do_not_contact_yet';
  key_concern: string | null;
  how_to_win: string | null;
  risk_if_ignored: string | null;
  contact: {
    linkedin_url?: string;
    email?: string;
    phone?: string;
    crm_badge?: boolean;
  };
  source_ids: string[];
  checked_at: string;
  role_start_date: string | null;
  company_start_date: string | null;
  reporting_edge: {
    inferred: boolean; // Retain for existing chart consumers.
    basis: 'inferred' | 'sourced' | 'manual';
    confidence: 'high' | 'medium' | 'low';
    evidence: string[];
  } | null;
  role_evidence: string[];
};
```

Keep `reporting_edge` separate from `committee_role`. Set `inferred` to true only for `basis: inferred`; sourced and manual edges carry their distinct evidence. A null parent has no selected reporting edge, even when candidates exist. Committee roles are deal hypotheses based on title, context, CRM, and signal evidence.

**Incremental updates and verification:**

Save the normalized dataset, scope, cursors, exclusion reasons, candidate edges, and manual overrides beside the HTML. Refresh by stable identity and preserve overrides; flag a departed/missing manager instead of silently rewiring. Export edits because browser-local storage does not follow a shared file. Build the chart from saved data without repeating paid discovery.

Escape provider strings and allow only safe HTTP(S) links when generating HTML; render titles/names as text. Keep credentials out of the artifact. Contact enrichment is optional and requires a real authenticated action with the selected person and Deepline credit estimate visible. A standalone HTML file should export selected IDs or provide a follow-up prompt, not pretend it can run a connector.

Before delivery, verify no duplicate node IDs, dangling selected parents, self-links, or cycles; every visible edge has a basis; every retained person is placed or in review; counts reconcile. Exercise search, filters, focus, empty states, correction persistence/export, and a refresh that preserves manual edits. Use fixtures with same-name people, a promotion, a subsidiary employee, a scoped CTO, and tied manager candidates. Report what was actually exercised; a skill description alone does not prove a working viewer.

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

| Factor                 | Condition                                                     | Score                             |
| ---------------------- | ------------------------------------------------------------- | --------------------------------- |
| Title                  | exec level                                                    | +40                               |
| Title                  | director level                                                | +25                               |
| Title                  | manager level                                                 | +10                               |
| Contact                | has email                                                     | +25                               |
| Contact                | has phone                                                     | +10                               |
| Warm                   | warm connection                                               | +30                               |
| **Job change recency** | exec with verified company start < 90 days                    | **+20 bonus**                     |
| **Job change recency** | verified company start < 30 days                              | **+10 bonus**                     |
| Champion potential     | champion_potential_score >= 45                                | +15                               |
| Champion potential     | champion_potential_score >= 30                                | +8                                |
| Tenure (negative)      | verified company tenure < 6 months AND manager/director level | -5 (lower influence, less stable) |

**Why prioritize recent hires:** a new executive may be reviewing vendors. Treat this as an outreach hypothesis to validate, not proof of budget or intent.

Display a “New hire” badge only for verified company starts within 90 days; display “New in role” separately for recent role starts. Leave unknown tenure unscored. Clamp priority scores to 0–100 and champion-potential scores to 0–60; these are ranking aids, not verified authority.

## Champion and hidden influencer scoring

Compute `champion_potential_score` on a 0-60 scale. This score is not a claim that someone is already a champion. It tells the rep who is worth testing for champion behavior.

| Factor               | Condition                                                        | Score |
| -------------------- | ---------------------------------------------------------------- | ----- |
| Role relevance       | In owning function for the deal context                          | +12   |
| Role relevance       | Adjacent function with clear stake                               | +6    |
| Influence            | Director+ in owning function                                     | +12   |
| Influence            | Staff, Principal, Lead, Architect, Admin, EA, or long-tenured IC | +8    |
| Accessibility        | Direct CRM relationship or prior conversation                    | +12   |
| Accessibility        | Warm path through customer, investor, partner, or coworker       | +8    |
| Change agent         | Joined or promoted in last 180 days                              | +8    |
| Change agent         | Prior company used the product category or competitor            | +6    |
| Personal stake       | Public content, job post ownership, or CRM note tied to the pain | +8    |
| Engagement potential | Has email or LinkedIn plus a specific reason to reach out        | +8    |

Classify score bands:

| Score | Label                     | Action                                             |
| ----- | ------------------------- | -------------------------------------------------- |
| 45-60 | High champion potential   | Contact or warm-intro early                        |
| 30-44 | Medium champion potential | Use as access line or ask current champion         |
| 15-29 | Low champion potential    | Monitor unless they fill a required committee role |
| 0-14  | Unknown                   | Do not over-prioritize without more evidence       |

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

Use this score only to order candidates, never as a probability or automatic edge threshold. Require compatible employer scope, plausible seniority, and affirmative team evidence before selecting an inferred parent. Ties, missing team evidence, or conflicting sources stay in Needs review with the candidates visible. Neither a matching city nor a title tier alone establishes a manager. Reject self-links and cycles before saving any inferred or manually edited edge.

## When NOT to use

- User already has a CSV and wants enrichment -> run the matching prebuilt play from `deepline search`
- User needs email/phone for outreach -> this recipe maps orgs, use enrichment recipes for contact info after
