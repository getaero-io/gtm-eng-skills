---
name: prospect-one-account
description: |
  Turn one company domain into a ready-to-review outbound package: what your CRM already knows
  about the account (recent activity, past opportunities, an engagement level), what public
  third-party signals say about timing (hiring, funding, leadership changes), the 3-4 director-plus
  people who own the buying decision, verified work emails found through a multi-provider
  waterfall, and a personalized three-email sequence per contact. Drafts only - nothing is sent.
  Works whether or not the account exists in your CRM. Use whenever someone asks: prospect this
  account, prep outreach for company X, who should I contact at this domain and what do I say,
  build me cold emails for this target account, research plus emails for one company. Do NOT use
  it for: building or scoring a list of target accounts, running many accounts in bulk or on a
  schedule, finding emails for a contact list you already have, sending emails or enrolling anyone
  in a sequencer, or auditing CRM data quality. Built on Deepline: company enrichment, people
  search, the work-email waterfall play, and the CRM tools connected in Deepline.
category: personalize-outbound
personas: [sales-development, gtm-engineer]
mechanism: functions
touches: read-only
keywords: [cold-email, waterfall]
ported_from: clay-run/clay-skill-creator/skills/luca-prando/prospect-one-account
---

# Prospect one account

Give it a domain. It answers the three questions a first touch depends on - what do we already know
(your CRM), why now (public signals), who decides (director-plus people in the buying functions) -
and then writes the emails from those answers. Decision authority picks the people; the email
waterfall exists so picking senior people doesn't cost you findable addresses. Reachability never
picks the person.

This skill reads your CRM and public data sources and writes nothing anywhere: its entire output is
a package of drafts delivered in the conversation. It never sends an email, never enrolls anyone,
and never modifies a record.

## What this skill touches

- **Reads** — one account and its activities and opportunities in your CRM; public company data via
  Deepline company enrichment; public people data via Deepline people search; email finder and
  validator providers.
- **Writes** — nothing. The output is a package of drafts for you to review.
- **Never** — sends an email, enrolls a contact in a sequence, creates or updates or deletes a CRM
  record, or moves your data anywhere you did not name.
- **Halts** — Step 3 spend-approval.

## Declared inputs

| Input | What you supply | If missing |
|---|---|---|
| Company domain | The domain to prospect, e.g. `acme.com` (per run) | Required — nothing runs without it. |
| Product context | Your product's name, a one-line value proposition, and 2–3 canonical use cases teams buy it for | Required — the emails cannot be written. The research still runs if you only want the brief. |
| Buyer functions | Which functions buy or own your product, e.g. Revenue, Sales, Marketing, RevOps | Defaults to Revenue/Sales/Marketing/RevOps/Growth, and the package says the default was used. |
| Title keywords | The job-title keywords for people search, matched with "contains" | Defaults to a C-level → VP → Head of → Director ladder across the buyer functions (listed in Step 8). |
| Title exclusions | Title words that disqualify, e.g. junior, assistant, intern | Defaults to the Step 8 exclusion list. |
| Seniority floor | The lowest seniority worth contacting | Defaults to director. |
| Regions | Which regions to search for people in, if you want a region filter at all | No filter is applied — people are searched worldwide. There is deliberately no default: the source's EMEA/NAM filter was demo scoping, not a rule of the play. |
| CRM connection | Which CRM you run, connected in Deepline (`deepline tools search <crm> --json` lists its tools) | The CRM half is skipped: engagement is reported as nonexistent and the emails lean on public signals only. |
| CRM account fields | Which fields on your account object carry account fit, owner, and engagement summaries (if you track them) | Those lines drop from the account context; the core lookup still works on standard fields. |
| Email providers | A preferred finder order and validator, if you have one | Defaults to Deepline's `prebuilt/name-and-domain-to-email-waterfall` play (multi-provider, mailbox-verified); a custom order is Findymail → Prospeo → Wiza with Findymail validation. |
| Sender name | The name to sign the emails with | Emails end with just the sign-off word ("Thanks," / "Best,"). |
| Spending cap | The most you want this run to spend, in credits or dollars | You are asked at the gate in Step 3; there is no silent default. |

## Representative output

| Contact | Title | Work email | Provider | Why picked | Subject | Email 1 | Email 2 | Email 3 |
|---|---|---|---|---|---|---|---|---|
| Avery North | VP Revenue Operations | avery@northwind.example | Findymail | Owns the RevOps function; CRM shows a stalled 2025 opp | Scaling outbound after the raise | (90–120 word intro draft) | (80–110 word use-case draft) | (under-40-word bump) |
| Jordan Cole | Director Sales Development | jordan@northwind.example | Prospeo | Runs the SDR team the hiring signals point to | Your five new SDR openings | (draft) | (draft) | (draft) |

Plus an account context block: domain, the CRM account it matched (ID and owner), engagement level
and summary, and the third-party signal analysis and tier.

## Step 0 — Check the platform, and say where the work runs

Say the posture out loud before anything runs: this skill reads your CRM and public data, writes
nothing anywhere, and its output is drafts in this conversation. Then check the platform:
`deepline preflight --json` must report the CLI connected and authenticated to the org holding your
CRM connection. If a component is missing or signed out, name the component, the one command that
fixes it (`npm install -g deepline` for a missing CLI, `deepline auth register --wait auto` for
auth), and stop — a broken environment is yours to fix, and this skill never installs, upgrades, or
fetches anything to repair its own prerequisites.

## Step 1 — Collect the definition (interview; do not guess)

**If an answer sheet is present beside this skill, load it and ask only for what it does not
cover.** A partial sheet is normal; a value it is missing gets asked for on its own rather than
restarting the interview. Say which values came from the sheet before using them. If there is no
sheet, say nothing about sheets — run the interview as though the feature did not exist.

Ask for, in this order, skipping anything already supplied:

1. The domain to prospect.
2. Product context: name, one-line value prop, 2–3 canonical use cases. This is what the emails
   pitch; without it, offer the research-only brief.
3. Which CRM they run (connected in Deepline), and — if they track them — which fields on the
   account object carry fit score, owner, and engagement summaries.
4. Buyer functions, title keywords, exclusions, seniority floor, and regions — offer the defaults
   from this file and take corrections rather than asking open-ended.
5. Which email finder/validator providers are connected, and the sender name for sign-offs.

## Step 2 — Normalize the domain (free)

Strip protocol and `www.`, lowercase, cut anything after the first `/`. If what remains is empty or
contains no dot, stop and say the domain is invalid — do not guess a correction. This is the
source's own rule: fail loudly on bad input rather than enriching a typo.

## Step 3 — Price the run and get one yes (spend-approval)

Everything before this point is free. Before the first paid call, fetch the live price of each tool
this run will use — `deepline tools describe <tool_id> --json` (`pricing`) for
`crustdata_v3_company_enrich`, `crustdata_v3_person_search`, and the email finders and validator,
and `deepline plays describe prebuilt/name-and-domain-to-email-waterfall --json` for the play — and
put one message in front of the installer: what will
run, what it costs, and the ask. Two of the numbers need plain words:

- People search charges for each person it returns, up to the cap of 10 — say "this one charges per
  person found; it's capped at 10, so at most 10 × the per-person price."
- The email waterfall's call count depends on how many of the 3–4 picked contacts each provider
  finds — give the worst case (every picked contact through every provider stage) as the bound.

Ask for their cap in the unit they think in — "what's the most you'd want this run to spend?" — and
never present the per-result step as the cheap path. One gate, one yes. After the run, if actual
spend differed from the estimate, say the real figure and what was different.

## Step 4 — Enrich the company

- **What runs:** `crustdata_v3_company_enrich`, with `fields: ["basic_info","headcount","funding",
  "locations"]` (omit `fields` and only `basic_info` comes back).
- **What goes in:** `domains: ["<normalized domain>"]`.
- **What to verify:** a company name at `[0].matches[0].company_data.basic_info.name` and a company
  LinkedIn URL at `...basic_info.professional_network_url`; check that `basic_info.website` /
  `all_domains` agree with the input domain. Step 8 keys on the domain, with the LinkedIn URL as the
  stronger identifier when present; an empty `matches` array means the company is unknown to the
  source — say so rather than guessing an identifier. Firmographics for Step 7 come from the same
  `company_data` object.
- **What it costs:** the price fetched at Step 3.

## Step 5 — Read the CRM (three lookups, read-only)

Ask the CRM questions in the installer's own system via their connected account. On Salesforce —
the system the source ran on — the three reads are, with the installer's field names substituted
for the bracketed ones:

1. **Account:** `SELECT Id, Name, Website, Industry, NumberOfEmployees, Type, [your fit-score,
   owner, engagement-summary, and subscription fields] FROM Account WHERE Website LIKE '%<domain>%'
   ORDER BY [your ARR field] DESC NULLS LAST LIMIT 5` — then take the first record. This is a
   contains-match on the website field, ordered so that when several accounts match, the one with
   the largest active revenue wins. Say which record was picked; a subsidiary or lookalike domain
   can match here, and showing the pick is the guard.
2. **Activities:** the 50 most recent events for that account ID, newest first (Subject, Type,
   ActivityDate, CreatedDate, Owner).
3. **Opportunities:** the 25 most recent opportunities for that account ID, newest first (Name,
   Stage, Amount, CloseDate, Created/LastModified, IsClosed, IsWon, LeadSource, loss reason if
   tracked).

**Run SOQL through `salesforce_api_request`** (free, the installer's connected org):
`method: GET`, `path: /services/data/v60.0/query`, `query: {q: "<SOQL>"}`. Match the account with
`SELECT Id, Name, Website, OwnerId FROM Account WHERE Website LIKE '%<domain>%'`, then pull its
opportunities (`... FROM Opportunity WHERE AccountId = '<id>'`) and recent activity (`... FROM Task
WHERE AccountId = '<id>' ORDER BY ActivityDate DESC LIMIT 50`, same for `Event`). Escape quotes in
any value you interpolate. Results over 2,000 rows return a `nextRecordsUrl`; GET that path for the
next page. The typed list tools (`salesforce_list_accounts`, `salesforce_list_opportunities`) have no
`WHERE` clause, so prefer SOQL for anything filtered.

On HubSpot: `hubspot_search_objects` (`object_type: "companies"`, a `filter_groups` filter on
`domain`), then `hubspot_batch_read_associations` from the company to `deals` and to the engagement
objects (calls, emails, meetings, notes), read with `hubspot_batch_read_objects`. On Attio:
`attio_query_company_records` filtered on domain. **What to verify:** a matched record ID — an empty
result is a real answer ("not in the CRM"), not a failure; the run continues, and Step 6 will report
engagement as nonexistent. That is by design: net-new accounts are in scope.

## Step 6 — Judge first-party engagement (no external lookups)

From the CRM data only, produce four fields: `engagementSummary` (1–2 sentences),
`recentEngagementWithin30Days` (boolean), `mostRecentEngagementDate` (ISO or empty), and
`engagementLevel`. The rules, verbatim from the source:

- The most recent engagement date is taken across CRM activity rows, engagement rows, email
  activity if present, and any timestamped opportunity update (created, closed, stage change,
  reopened).
- An opportunity counts as "recent" if it had meaningful activity within 180 days.
- Strong signals: inbound replies, meetings held, demo attendance, product usage, webinar
  attendance, active subscription, open or recently progressing opportunity, pricing/procurement/
  legal/security activity. Medium: email opens, multiple outbound touches, site activity, old but
  meaningful opp activity. Weak: outbound-only, stale opps, no replies, bounces, very old activity.
- `engagementLevel` is exactly one of: **high** = multiple strong signals in the last 30 days, or
  active/recent opp activity within 6 months with meaningful engagement, or active
  subscription/customer activity; **medium** = meaningful engagement within 60–180 days,
  recent-but-stalled opp activity, or moderate account-level engagement; **low** = sparse or weak
  engagement, outbound-only, or nothing meaningful in the last 90 days; **nonexistent** = no
  credible engagement, no opportunity history, no supportive indicators.
- Empty CRM result → `false`, empty date, nonexistent. Never invent details.

## Step 7 — Research third-party signals (budgeted web research)

Research public signals that the company may need the installer's product now. The budget is a hard
limit from the source, and it is the reason this step finishes: **at most 5 web searches, at most 2
pages opened per search; spend the first 3 searches on hiring, funding/financial events, and
leadership changes; if those 3 surface nothing credible and recent, stop and score "none"; once the
budget is spent, classify with what you have — no re-verifying, no broadening.**

Signal categories in priority order: (1) relevant hiring — roles that suggest need for the product,
drawn from the installer's buyer functions; (2) funding/financial events; (3) leadership changes in
the buying functions; (4) technology/transformation statements; (5) growth or contraction; (6)
competitive/market moves. Only signals with a credible public source count; firmographics are
context, never signals; conflicts between sources are noted, not silently resolved.

Output: `analysis` (2–4 sentences: strongest signals, trajectory, likely buyer team, and a point of
view on prospecting now vs premature) and `score`, exactly one of: **high** = 2+ strong signals
within ~90 days, especially hiring plus funding/tech investment; **medium** = 1 strong signal or
several medium/older ones pointing the same way; **low** = only weak, ambiguous, or 12-plus-month
stale signals; **none** = nothing credible found, said explicitly.

## Step 8 — Find the people

- **What runs:** `crustdata_v3_person_search` (0.02 credits per returned person). The alternative
  is `search_contact` (`domain`, `title_filters`, `seniorities`; 0.56 per result) — same job at
  roughly 28× the per-person price, so it is the fallback when Crustdata comes back thin.
- **What goes in:** a `filters` group: `experience.employment_details.current.company_website_domain`
  `=` the domain (or `...current.company_professional_network_profile_url` `=` the Step 4 LinkedIn
  URL); an `or` group of `experience.employment_details.current.title` `contains` each title keyword
  (default: Chief Revenue Officer, CRO, Chief Marketing Officer, CMO, Chief Sales Officer, Chief
  Growth Officer, VP Sales, VP Revenue, VP Marketing, VP Revenue Operations, VP Growth, VP GTM, SVP
  Sales, SVP Marketing, Head of Sales, Head of Revenue, Head of Revenue Operations, Head of GTM,
  Head of Marketing, Head of Growth, Head of Sales Development, Director Revenue Operations,
  Director Sales Operations, Director GTM, Director Sales Development, Director Demand Generation,
  Director Growth, Director Marketing Operations, Director Sales); exclusions (default: Admin,
  junior, assistant, consultant, interim, coordinator, risk, merchandising, Engineer, Analyst,
  Specialist, Representative, Associate, Intern, SDR, BDR, Account Executive — applied in code to
  the returned titles, since the filter has no "does not contain"); seniority floor (default
  director; `...current.seniority_level`, exact values from the free
  `crustdata_v3_person_search_autocomplete`); the installer's regions, if any, on
  `basic_profile.location.country` (no default — the source's EMEA/NAM value was demo scoping);
  `limit: 10`.
- **What to verify:** people with `basic_profile.name`, the current title, and a LinkedIn profile
  URL — check the field paths in the first response. Zero people is a real answer; report it and
  stop the outreach half rather than widening the filters silently.
- **What it costs:** charged per person returned, capped at 10 — the count is unknown until it runs.

## Step 9 — Pick the 3–4 people to prospect (no external lookups)

From the found people plus the Step 6 engagement analysis, pick 3–4 (fewer only if fewer exist),
ranked strictly by decision-making authority within the buyer functions. The ladder, verbatim:
Tier 1 C-level (CRO, CMO, CSO, CGO); Tier 2 SVP/VP of the buyer functions; Tier 3 Head of; Tier 4
Director of. Below director is not a decision maker and is selected only when the list holds fewer
than 3 director-plus people — and then each such pick's reason starts with "Fallback (no senior
alternative): ". Within a tier, prefer the function most likely to own the buying decision, then
relevance to the engagement analysis. Never more than 4; irrelevant functions (facilities, legal,
finance-only) only when nothing else exists; empty list in, empty list out. Each pick carries one
`reasonWhy` sentence tied to title/function and, where real, a specific engagement data point —
never an invented connection.

## Step 10 — Find and verify emails (waterfall)

Default: run `prebuilt/name-and-domain-to-email-waterfall` once per picked contact (`first_name`,
`last_name`, `domain`, plus `linkedin_url` when Step 8 returned one). It cascades across providers
and returns only a mailbox-verified address; record the provider it reports. For a custom provider
order, the same three steps by hand, per picked contact:

1. **Find:** in order, `findymail_find_from_name` (full name + domain), `prospeo_enrich_person`
   (`linkedin_url` or name + `company_domain`, `only_verified_email: true`), `wiza_reveal_person`
   (`linkedin_url`). Check the email field path in the first response before calling anything a
   miss.
2. **Validate:** `findymail_verify_email` (0.28 per call) on each found address; keep it only if
   the response says it is verified.
3. **Attribute and pass on:** a verified contact is done (email + provider recorded); everyone else
   flows to the next provider. After the last provider, unverified contacts stay in the package
   with an empty email — visibly, not dropped.

Each find and each validate is paid, priced at Step 3 and bounded by the picked count; a contact
verified early is never re-queried later.

## Step 11 — Write the emails (no external lookups)

For each contact with the account research as the only source of facts — never invented ones —
write four pieces: **subject** (under 7 words, sentence case, specific to the account's situation
and the contact's function, no clickbait); **email 1**, the intro (90–120 words: open with a
specific timely observation from the research relevant to this contact's role, connect it to the
pressure their role faces, one or two sentences on how teams in their position use the product —
from the installer's use cases — and a low-friction CTA for a 20-minute call); **email 2**, the
use-case follow-up (80–110 words: one concrete use case tied to one specific signal, what the
workflow does and the outcome, soft CTA to show an example); **email 3**, a bump (2–3 sentences,
under 40 words). Greet by first name. Tone: direct, peer-to-peer, concrete; no hype words, no
exclamation marks, no "I hope this finds you well". Sign off "Thanks," (or "Best," for email 2)
with the sender name on the next line, or just the sign-off word if no name was given.

## Step 12 — Deliver the package

Deliver the Representative-output table plus the account context block in the conversation, saying
which CRM record was matched, which defaults were used, and what the run actually spent against the
Step 3 estimate. Then offer, once: "Want me to save your answers to a file alongside this? It isn't
part of the skill — it's a short note of what you told me: your product pitch, your CRM and field
names, your buyer profile. You never answer these again on a re-run, and a teammate you send it to
gets asked only what it doesn't cover. It stays with you: never submitted, never published, and it
holds no passwords or API keys."

## What good looks like

The rep reads the package and recognizes the account: the engagement summary matches what they
half-remembered, the signal analysis names something they can verify in one click, the 3–4 people
are ones they'd have picked with an hour of research, and at least the emails for the verified
contacts are sendable after light edits. A run on an account with nothing — no CRM record, no
signals, no findable people — says so plainly at each step instead of padding.

## What this skill does not claim

- The thresholds — the 30/60–180/90-day engagement bands, the 180-day opportunity window, the
  ~90-day and 12-month signal cutoffs, the 5-search research budget, the 3–4 contact count, and the
  email word counts — come from the source workflow's prompts as its author set them. Nobody has
  validated them against outcomes such as reply or meeting rates.
- No suppression: it does not check whether a contact was recently contacted, sits in an open
  sequence, or has opted out. Your sequencer and CRM own that, and the drafts must pass through
  them.
- The CRM match is a contains-match on the website field with the largest-revenue record winning.
  A subsidiary or lookalike domain can be picked; the skill shows its pick rather than guaranteeing
  it.
- "Verified" for an email means the validator said so, nothing more. Deliverability, catch-all
  behavior, and sender reputation are not claimed.
- The source workflow's region filter (EMEA, NAM) was scoping for a demo, not a rule of the play
  — its author said so — which is why regions ship with no default here.
- Few cost figures appear in this file on purpose: prices change and are read live at Step 3.
- This skill was derived from a read of the source workflow's configuration on 2026-09-02 — its
  agent prompts verbatim, its code and wiring as ground truth. No run of this skill has been
  compared against the source workflow's outputs, so the derivation is checked against the
  configuration, not against behavior.
