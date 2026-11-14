---
name: org-chart-builder
description: |
  Build an interactive org chart of a target account's current C-Suite and VP leaders from Deepline
  people search (CrustData), with reporting lines inferred from titles and always labeled as inferred, a Needs
  review tray for anyone with no evidence of a manager, drag-and-drop manager corrections, focus
  mode, "new in role" badges from each leader's role start date, a recent-news section, per-person
  email and mobile lookup commands for Deepline's waterfall plays, and optional styling in the
  seller's own brand. Use whenever someone asks: org chart for this company, map the leaders at X,
  who runs what at this account, build an account map, show me the exec team at X, who reports to
  the CTO there, which leaders are new in their role, add more people to the X org chart. Works from
  a company name or domain. Do NOT use it to find one named person's email or profile, to build a
  prospect list across many companies, to enrich or score a whole account list, or to write
  anything to a CRM or sequence.
mechanism: functions
touches: writes-own-output
ported_from: clay-run/clay-skill-creator/skills/alex-lindahl/clay-org-chart-builder
---

# Org Chart Builder (titles come from people search; reporting lines are inferred and labeled)

The insight: **people search returns titles, locations and role start dates, and never who reports
to whom.** Checked on Clay's live response for a 1,500-person software company (2026-08): every
leader record carried a current title and a start date for that title, and none carried a manager.
Deepline's `crustdata_v3_person_search` has the same shape: its profile schema has a current title,
seniority, function and `start_date` per current employment, and no manager field. So an org chart
built from it has two kinds of fact in it, and the whole design keeps them apart: the people and
titles come from the search, and every line between them is an inference from titles and functions
that the page labels as inferred, gives a reason for, and lets the viewer correct. People with no
evidence for a manager are not parked under the CEO to make the chart look complete; they wait in a
Needs review tray.

The output is one self-contained page with two views:

- **Org chart:** the top executive, with their reports grouped into function lanes. Lines are dashed
  when inferred, dotted amber when low confidence, and solid when the viewer set them. Anyone can be
  dragged onto someone else's tile to change who they report to.
- **By level:** C-Suite and VP Leadership groups.

Each tile opens a side panel with the reason for its line, the buying role and level (editable), source
details, recent news, and "Find email / Find mobile with Deepline" buttons that show the exact Deepline
command for that person; the page itself calls nothing. `references/page-behavior.md` describes every control on the page.

Do not start a step before the steps above it have their answers. If a declared input is missing, ask
for it — never assume a default and continue.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Target company** | a company name, or better a website domain | no default — ask. A bare name is resolved and confirmed before any people search (Step 4) |
| **Branding choice** | yes or no: style the page in their own company's brand | ask. No means the default style (off-white page, purple accents) |
| **Their website** | the seller's own site, only if they chose branding | no brand is extracted; the default style is used and the reply says so |
| **First-build size** | how many leader records to pull on the first build | **30 is the author's default and must be stated**; never more than 50 on a first build |
| **News window** | how far back the news section looks | **3 months is the author's default and must be stated** |
| **Deepline workspace** | whichever workspace the Deepline CLI is signed in to | confirmed at Step 0, never assumed |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question. At delivery, offer to save the durable answers back (brand website, build size,
news window; identifiers only, never a token or a password), private and
never published — and phrase the offer so it explains itself: *"want me to save these settings to a
file, so the next chart you or a teammate builds doesn't ask them again?"* The target company changes
every run, so it is never saved.

## What this skill touches

- **Reads** — Deepline company identification (`crustdata_v3_company_identify`, free) and people
  search (`crustdata_v3_person_search`) for the one company you name (current title, seniority,
  location, LinkedIn URL, role start date); the computed styles of your own website, if you chose branding; public news pages, through
  web search, for the news section.
- **Writes** — its own output only: one self-contained HTML page (published as a private page where the
  host can publish pages, otherwise saved as a file). Nothing in Deepline, a CRM, a table or a sequence.
- **Never** — runs email, phone or work-history enrichment while building; writes to a CRM, table or
  sequence; contacts anyone on the chart; uses any CRM record fields for anyone; puts Deepline
  credentials in the page, a log or a URL.
- **Halts** — Step 2 spend-approval, Step 4 other, Step 10 spend-approval.

Contact lookups are a separate, explicit action: the page shows the viewer a Deepline command to run
themselves (their credits), or the viewer asks the agent to run lookups for named people (Step 10),
which is priced and confirmed before it runs.

## Step 0 — Check the platform, say where the work runs

1. Run `deepline preflight` and tell the user which Deepline workspace the search will run in, in one
   line (`deepline auth status --json` shows it).
2. Confirm the tools resolve, free: `deepline tools describe crustdata_v3_company_identify --json` and
   `deepline tools describe crustdata_v3_person_search --json`. Read the person-search filter grammar
   and the profile fields from the second.
3. Check that `python3` runs; the page is built by `scripts/orgatlas.py`, which needs only the standard
   library.

If any check fails, say which component is missing and the one thing that fixes it (missing CLI:
`npm install -g deepline && deepline auth register --wait auto`), then stop. Do not install, upgrade or
fetch anything else to repair it, and never continue with other data.

Say the posture in two sentences before Step 1: *"This reads Deepline people-search results for one
company and writes one org chart page. It never writes to Deepline or a CRM, and it runs no email or
phone lookups while building."* All classification, deduping and line inference runs locally in the
script, so it costs nothing; only the people search uses credits.

## Step 1 — Ask which company

If the user has not named the target company, ask: "Which company do you want to build the org chart
for? A website domain helps me find the right one." Wait for the answer.

## Step 2 — Set expectations and ask about branding (the spend gate)

Send this notice, filled in, **together with** the branding question, as one message:

> I'll search Deepline (CrustData) for current C-Suite and VP leaders at **{Company}**: CEOs and other chiefs,
> presidents, EVPs, SVPs and VPs. Former employees, directors, advisors, consultants and board-only
> seats are left out. **The first build includes up to {first-build size, default 30} people**, and you
> can add more later. The search costs 0.02 Deepline credits per returned result (about 0.6 credits for
> 30), and it runs as soon as you answer below. It writes nothing anywhere except the org chart page.

Question: **"Do you want the org chart styled with your company's brand?"**

- **Yes, use my brand** — then ask for their company website.
- **No, use the default style**.

Answering this question is the go-ahead for the search. No search runs before it.

## Step 3 — Extract the seller's brand (only if they said yes)

The brand is the **user's** company (the seller), not the target account.

1. Open the homepage with a browser tool that can run JavaScript and read computed styles: the main
   call-to-action buttons' `backgroundColor`, the `fontFamily` of `h1` and `body`, hex custom properties
   on `:root`, Google Fonts `<link>` tags and the header logo. A page-to-markdown fetch drops the CSS,
   so use one only when no browser is available. Take only what is present:
   - **Brand name:** `og:site_name`, the `<title>` prefix, or the logo `alt` text.
   - **Primary color,** in order: the main call-to-action background when it has a hue; custom
     properties that name the brand (`--primary`, `--brand`, a named swatch); `<meta name="theme-color">`.
     Ignore black, white, greys and pale tints; if the only colored button is a pale tint, take the
     strongest saturated brand swatch instead.
   - **Fonts:** the `family=` values of Google Fonts links, else the first family in the heading and
     body declarations.
   - **Logo:** only inline `<svg>` markup or a small SVG file returned as text, base64-encoded as a
     `data:image/svg+xml;base64,...` URI. Otherwise leave it empty and the page shows the brand name as
     a wordmark. Do not download binary images.
2. Fonts must come from Google Fonts. If the brand font is not there, pick the closest Google font and
   say you substituted it.
3. Write `theme.json`:
   ```json
   {"brandName":"Acme","primary":"#0A66FF","fontHeading":"Space Grotesk","fontBody":"Inter",
    "googleFontsUrl":"https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500;600;700&display=swap",
    "logoDataUri":null,"source":"acme.com"}
   ```
   The renderer adjusts the primary color so text meets WCAG AA contrast in light and dark mode; mention
   it if the adjustment is visible.
4. If the site cannot be read or yields no usable color, say so in one line and continue with the
   default style. Branding never blocks the build.

## Step 4 — Resolve the target company

1. **Domain known:** `deepline tools execute crustdata_v3_company_identify --input '{"domains":["<domain>"]}' --json`
   (free).
2. **Only a name:** the same tool with `{"names":["<name>"]}`. Name-only results are **candidates**, not
   verified identities, even at a confidence score of 1.0.
3. **One clear match on a domain:** use it.
4. **Several, or any name-only match:** show up to 5 choices with name, domain, industry and location
   (whatever came back) and ask the user to pick. Never auto-pick between plausible matches. This is the
   Step 4 halt.
5. **None:** say so and ask for the domain. Never guess a domain.
   - A domain can return the parent plus an acquired unit that shares it (for example "Initech
     Analytics (acq. by Initech)"). When the extra record is clearly labeled as acquired or a
     subsidiary, use the parent and say so in one line. Otherwise ask.
6. Save `company.json` with only values the response carried, from `matches[].company_data.basic_info`:
   `{"name": name, "domain": primary_domain, "companyId": crustdata_company_id, "industry": ...,
   "location": ..., "linkedinUrl": professional_network_url}`. From here on filter people by the
   **CrustData company ID**, never the bare name, because a shared domain pulls in the subsidiary's
   people. Use the LinkedIn company URL only if no ID came back.

## Step 5 — Search current leaders

1. **Check filter values first, free:** `crustdata_v3_person_search_autocomplete` with
   `{"field":"experience.employment_details.current.seniority_level","query":""}` returns the exact
   seniority values. Never write a filter value you have not seen there or in the schema.
2. **Search** with `crustdata_v3_person_search`. Start from this shape, then adjust to what the
   describe output and autocomplete showed:

   ```json
   {"filters": {"op": "and", "conditions": [
      {"field": "experience.employment_details.current.crustdata_company_id", "type": "=", "value": <companyId>},
      {"op": "or", "conditions": [
        {"field": "experience.employment_details.current.seniority_level", "type": "in", "value": ["<CXO value>", "<VP value>", "<Owner/Partner value>"]},
        {"field": "experience.employment_details.current.title", "type": "contains", "value": "chief"},
        {"field": "experience.employment_details.current.title", "type": "contains", "value": "president"}
      ]}]},
    "fields": ["crustdata_person_id", "basic_profile", "social_handles", "experience.employment_details.current"],
    "limit": 30}
   ```

   - **`in` takes at most 5 values**; CrustData can silently ignore a longer array. Split a longer list
     into more OR conditions.
   - Record each person's seniority so "Head of" titles can qualify as VP.
3. **First build:** the declared first-build size (default 30), as `limit`. While `next_cursor` is set
   and the build is under size, pass it as `cursor` for the next page. Never fetch more than 50 records on
   a first build. Search is billed per returned row, so the limit is the spend cap.
4. **Errors:** report the CLI's message in plain words, with no raw payload or credential. Auth: re-run
   `deepline auth register --wait auto`. Out of credits: `deepline billing` shows the balance. Rate
   limited: wait a minute and ask again. Anything else: a general Deepline error. Never retry in a loop
   and never substitute other data.

No phone-function setup is needed: the page's lookup commands use Deepline's prebuilt waterfall plays
(`prebuilt/person-linkedin-to-email`, `prebuilt/name-and-domain-to-email-waterfall`,
`prebuilt/person-to-phone`), each confirmed with `deepline plays describe`.

## Step 6 — Normalize, classify and infer lines

1. Convert each returned profile into this shape, **copying only fields the response actually
   carried**:
   - `crustdata_person_id` → `personId`, `basic_profile.name` → `name`,
     `social_handles.professional_network_identifier.profile_url` → `linkedinUrl`,
     `basic_profile.location.raw` → `location`, the current employment's `seniority_level` → `seniority`.
   - Take the entry in `experience.employment_details.current` whose `crustdata_company_id` matches the
     resolved company: its `title` → `title`, its `start_date` → `roleStartDate`. The start date is when
     the person started their **current title**, so it can be a promotion rather than a new hire. Keep it
     only when present; never estimate it. The script keeps `YYYY-MM`.
   - `isCurrent: true` when such an entry exists; `false` when the only current employment names another
     company. Use the current title **at the resolved company**, not the headline.
   - Never copy `contact.*` availability flags as if they were contact data. They say an email or phone
     exists, not what it is.

   ```json
   {"personId":"...", "name":"...", "title":"<current title at this company>", "linkedinUrl":"...",
    "location":"...", "roleStartDate":"YYYY-MM", "seniority":"<only if returned>", "isCurrent": true}
   ```
   Save the list as `raw.json`.
2. Run `python3 scripts/orgatlas.py normalize --raw raw.json --company company.json --out people.json --limit 30`
   (the limit is the declared first-build size). It is deterministic and free:
   - **Excludes** former employees, directors and below, advisors, consultants, assistants and
     board-only seats, "Head of" titles without VP seniority, and field or deputy C-titles such as
     "Field CTO", which are not the company's C-Suite seat.
   - **Classifies level:** "Chief … Officer", C-level acronyms and President are C-Suite; EVP, SVP, VP
     and Global VP are VP.
   - **Maps function** from the title to one of: Executive, Revenue, Sales, Marketing, Finance, Product,
     Engineering, People, Legal, Operations, Strategy, Customer, Other.
   - **Dedupes** by person ID, then normalized LinkedIn URL, then normalized name plus company domain.
   - **Infers reporting lines** as `reportsTo: {id, basis, confidence}`, in this order, first match
     wins:
     1. The CEO, or else the President, is the top of the chart.
     2. A Chief Accounting Officer reports to the CFO; a CISO to the CIO, or else the CTO. Medium.
     3. Other C-Suite report to the top executive. Medium.
     4. A VP reports to the closest more-senior VP in the same function (EVP, then SVP, then VP), or
        else to that function's C-level head. Medium.
     5. An EVP with no same-function leader goes under the top executive. Low.
     6. Anyone else is `unplaced` and goes to the Needs review tray.

     Every line points to someone more senior, so the chart cannot contain a cycle.
   - Prints a report of counts, exclusion reasons and line confidence. Keep it for the reply.

## Step 7 — Recent news about these leaders

Find recent news that names the charted leaders. This is web search only, not people search, so it
costs no Deepline credits (unless you use a Deepline search tool such as `serper_google_search` for it,
which is priced in `describe`). It is the one web-sourced section, it is labeled as such on the page, and nothing in it
ever changes a person, title or line.

1. **Search** with the host's web search, in one turn where possible: the company plus "news" with the
   current and previous two months; the top executive by name; each other C-Suite leader by name with
   the company; any VP whose name is distinctive enough to search reliably. Prefer the most recent
   results the search offers.
2. **Verify every item** by fetching it: read its publication date and which charted leaders it
   actually names or quotes. Keep an item only when its date is inside the declared news window
   (drop undated items), it names at least one charted person as the same person, and it is a news
   article, a company press release or newsroom post, or a byline the leader wrote. Skip people-search
   and profile sites and job posts. For a syndicated press release, keep the original and list copies
   under `alsoAt`.
3. **Write `news.json`.** Summaries are one or two sentences in your own words: never copy article text
   beyond a few words, and never put words in a leader's mouth.
   ```json
   {"checkedAt":"YYYY-MM-DD","windowMonths":3,"items":[
     {"date":"YYYY-MM-DD","title":"<headline>","url":"https://...","source":"<outlet>",
      "kind":"News | Press release | Byline","summary":"<your words>",
      "people":["<people.json id>"],"alsoAt":[{"source":"<outlet>","url":"https://..."}]}]}
   ```
   The renderer drops any item with no date, no https link, no title, or no one on the chart.
4. If nothing qualifies, write `news.json` with an empty `items` list; the page says no news named these
   leaders.

## Step 8 — Build and deliver the page

1. Run `python3 scripts/orgatlas.py render --people people.json --company company.json [--theme theme.json] --news news.json --out "<Company> Org Chart.html"`.
   The template is `scripts/orgchart_template.html`. The default output is a page body with no
   doctype, html, head or body tags, for hosts that publish pages; add `--full-document` for a
   standalone file. `--enrich enrich.json` is optional and only overrides which play IDs the page's
   lookup commands name (`emailPlay`, `emailByNamePlay`, `phonePlay`).
2. **Where the host can publish a private page,** publish it with a chart icon and a one-sentence
   description. It needs no runtime capability: the page calls nothing.
3. **Otherwise** save the full-document file to the user's outputs or connected folder. Everything on
   the page works the same way.
4. Reply briefly: leaders found (C-Suite and VP counts); what was excluded, from the report; the
   workspace searched; how many people are in Needs review and how many lines are low confidence; news
   items found and whom they mention; that lines are inferred from titles, not supplied by the search;
   that dragging a tile changes a manager and edits are saved in the viewer's browser; that the lookup
   buttons show a Deepline command that uses the viewer's credits, or the agent can run lookups for
   named people; and that they can say "add 20 more to the {Company} org chart". Then offer to save the
   durable settings (see Declared inputs).

## Step 9 — Adding more people later

1. Recover the dataset: reuse `people.json`, `company.json` and `theme.json` from the same session, or
   read the published page back and run `python3 scripts/orgatlas.py extract --html <file> --outdir .`,
   which recovers all three.
2. Get the next batch: pass the last `next_cursor` from this session if you still have it; otherwise
   re-run the Step 5 query with a limit of current total plus the requested amount, and deduping drops
   the people already charted. Default to 20 more if no number is given, and say what it costs in
   Deepline credits (0.02 per returned result) before running it.
3. Merge: `python3 scripts/orgatlas.py normalize --raw raw_more.json --company company.json --existing people.json --out people.json --limit <N more>`.
4. Re-run Step 7 so the news covers the new people, re-render with the same theme, and republish to
   the same page so the link is unchanged. Viewer edits carry over, including manual manager changes.
5. Report how many were added, and say plainly if the search had no more qualifying leaders.

## Step 10 — Contact lookups for named people (only when asked)

Only when the user asks ("find emails for the C-Suite on the Northwind chart"):

1. Price it first and wait for a yes: one waterfall play per person per field. A waterfall pays for each
   provider it tries before one hits; list the providers from `deepline plays describe <play> --json`
   (`staticPipeline`) and their prices from `deepline tools describe`.
2. Email: `deepline plays run prebuilt/person-linkedin-to-email --input '{"linkedin_url":"..."}' --json`
   (output `email`, `email_validated`, `email_found_and_valid`); without a LinkedIn URL,
   `prebuilt/name-and-domain-to-email-waterfall` with `first_name`, `last_name`, `domain`. Mobile:
   `prebuilt/person-to-phone` with `first_name`, `last_name` and any of `domain`, `email`,
   `linkedin_url` (output `phone`, `phone_line_type`, `phone_validated`).
3. Write each value found into that person's `email` / `phone` in `people.json`, re-render with the
   same theme and news, and republish to the same page. A miss is reported, never filled with a guess.

## Representative output

### Reply after a first build

> Built the Northwind Robotics org chart from Deepline people search (workspace: Acme GTM): **25 leaders — 7 C-Suite,
> 18 VP.** Left out 5: 2 field CTO titles, 1 former employee, 1 executive assistant, 1 non-VP title.
> 10 people are in **Needs review** because the search data has no same-function leader for them, and 1 line
> is low confidence. The news section has 6 items from the last 3 months, naming 4 leaders. Reporting
> lines are inferred from titles, not supplied by the search. First build size 30 and news window 3 months are
> the defaults.

### Coverage strip on the page

| Leaders | Champions | Exec buyers | Not yet classified | Contacts found | Need a manager | Lines you set | New in role (6 mo) |
|---|---|---|---|---|---|---|---|
| 25 · 7 C-Suite · 18 VP | 0 | 0 | 25 | 0 | 10 | 0 | 7 |

### Tiles and their lines

| Person | Title | Lane | Reports to | Line | Why |
|---|---|---|---|---|---|
| Dana Whitfield | Chief Executive Officer | top of chart | — | — | most senior title in the search results |
| Omar Reyes | Chief Technology Officer · New · 4 mo | Engineering & Security | Dana Whitfield | inferred, medium | C-Suite executives usually report to the CEO |
| Lena Park | VP, Platform Engineering | Engineering & Security | Omar Reyes | inferred, medium | same function (Engineering) as the Chief Technology Officer |
| Priya Nair | VP, Demand Marketing | Needs review | — | none | no same-function leader in this dataset |

### A news card

| Date | Outlet | Type | Headline | Names |
|---|---|---|---|---|
| Aug 4, 2026 | Northwind newsroom | Press release | Northwind launches autonomous fleet monitoring | Omar Reyes |

## What this skill does not claim

- It does not claim any reporting line is true. Every line is inferred from titles and functions,
  people search supplies no manager data, and the page labels each line with its reason and confidence.
- It does not claim to find every leader. A first build is capped (30 by default), and in the one
  company it was tested on (with Clay's people search), a later search found three current VP-and-above leaders the first 30
  records did not include.
- It does not claim the page can run lookups. It shows a command; running it, or asking the agent to,
  is a separate step that spends the viewer's Deepline credits.
- It does not claim the field mapping in Step 6 is complete for every CrustData response. It is taken
  from `crustdata_v3_person_search`'s output schema, not from a recorded live response; check the first
  page of results against it.
- It does not claim a "new in role" badge means a new hire. It uses the start date of the current
  title, so a recent promotion also counts.
- It does not claim the news section is current after the build. It is searched once at build time,
  shows the date it was checked, and is refreshed only by rebuilding.
- It has no measured run time on Deepline. The original was run end to end on one company with one brand
  on Clay; this Deepline version has been exercised offline (normalize and render on fixtures), not end
  to end.

## What good looks like

- **Every line on the chart carries its basis.** Opening any tile shows why its line exists and at what
  confidence, and nothing without evidence sits under the CEO; it is in Needs review instead. A chart
  where every VP hangs off the CEO with no tray is the failure this skill exists to avoid.
- **Counts reconcile.** Leaders shown plus exclusions equals records returned, and the reply names each
  exclusion reason. A good run on a mid-size company typically shows most C-Suite placed, VPs grouped
  into lanes, and a Needs review tray that is honest rather than empty.
- **Titles are current and at the right company.** No former employees, no subsidiary's people, no
  field or deputy C-titles counted as the company's C-Suite.
- **The news is dated and linked.** Every card has a date inside the window, an outlet and a link, and
  names someone on the chart. Zero items is a valid result and the page says so.
- **A thin run is visible as thin.** Few leaders, many exclusions or a large tray mean the search data for
  this company is sparse; the reply says that plainly rather than padding the chart.

## Rules

- **NEVER** state a reporting line as fact, as search data, or as confirmed. Never "improve" the
  inference with web search or memory.
- **NEVER** run email, phone or work-history enrichment while building the chart. Contact lookups happen
  only when the viewer runs a command from the page, or asks for them (Step 10) and confirms the cost.
- **NEVER** search before the user has answered the Step 2 message, and never re-run a search just to
  check.
- **NEVER** fill a gap with a guess: every person, title, location, start date and email comes from
  the search results, and a missing field is shown as "Not returned by Deepline".
- **NEVER** use CRM-record data for a person.
- **NEVER** auto-pick between plausible company matches.
- **NEVER** put Deepline credentials in the page, a log or a URL.
- **NEVER** present demo data as search results. `--demo` exists only for testing the page, labels every
  record Demo, and is never a fallback when the search fails.
- **NEVER** write a tool or play ID you have not described (`deepline tools describe`, `deepline plays
  describe`, both free).
- **ALWAYS** keep the news section labeled as web-sourced, dated and linked, and never let it change a
  person, title or line.

## Worked example

Ask: "Org chart for northwind-robotics.example, styled in our brand, acme.example."
Step 0 confirms the Deepline workspace. Step 2 sends the notice and branding question; the user says yes and
names their site. Step 3 reads the site's computed styles: primary `#3859F9`, a geometric sans heading
font available on Google Fonts, no inline logo, so the wordmark is used. Step 4 resolves the domain to one
company and saves its CrustData company ID. Step 5 checks seniority values with autocomplete, then
returns 30 records (0.6 credits). Step 6: 30
records → 25 leaders (7 C-Suite, 18 VP), 5 excluded (2 field CTOs, 1 former employee, 1 assistant, 1
non-VP title); lines: 13 medium, 1 low (an EVP with no same-function leader), 10 unplaced. Step 7 finds 6
dated, verified items naming 4 leaders and drops 2 undated ones. Step 8 publishes the page privately and
replies with the counts above.
