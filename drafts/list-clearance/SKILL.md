---
name: list-clearance
description: |
  Check a lead list before it goes anywhere near a sequencer, and return one verdict for the
  whole list: go, fix, or no-go. Seven gates, each pass or fail on its own: buyer title, firm
  fit, verified email, no block-list or suppression hit, not already in a live campaign,
  required fields present, and contacts per company under the cap. The worst gate decides, never
  the average. It also cuts the usable subset out of any list, go or not, and hands back every
  rejected row with its reason. Reads a CSV export, a Deepline customer-DB table, or free CRM and
  sequencer reads through Deepline; spends no credits; uploads, edits and deletes nothing. Use whenever someone asks: is this list ready to send, check my list
  before I upload it, how much of this list is actually usable, why did my last list bounce, are
  the right people on this list, is anyone here already in a sequence, clear this list. Do NOT
  use it to find or verify emails (find-work-email, verify-email-deliverability,
  clean-email-list), to merge duplicate records (dedupe-contacts), to build the list in the
  first place (build-prospect-list), or to judge a campaign that has already sent (kill-or-keep).
ported_from: clay-run/clay-skill-creator/skills/matteo-fois/list-clearance
---

# List clearance (a list ships when every gate passes, not when the average looks fine)

The insight: **a list fails on its worst gate, not on its average.** A list that is 100% verified
and 62% the wrong person still burns the sending domain for nothing, and a score that averages
the two reads as a B. The domain does not average. Every wrong row bounces or gets ignored on its
own.

The evidence is the author's own client work. One agency audited 6 lead lists it had built for 6
clients against the 7 requirements below. 0 of 6 met all 7. On 4 of 6 the company was right and
the person was wrong: customer success managers on a list meant for whoever owns hiring; 37% of
rows with no title at all on another. Only 2 of the 6 carried any validation columns, and both
shipped anyway with the flags ignored; on one of them every row had failed every check. Later,
the same agency measured one of its own builds: 1,264 leads built, 368 usable, 29%. The 368 were
a better list than the 1,264.

What follows from it: this skill runs seven gates and reports each one on its own. It never
combines them into a score. Any list, cleared or not, comes back with its usable subset cut out
and every rejected row carrying the reason, so the next move is filtering and enrichment, not
another build.

**It reads and reports; it does not act.** It spends no credits, runs no verifier, edits no table,
and uploads nothing. Verifying emails, finding missing ones and merging duplicates are other
skills' jobs; this one reads what those jobs left behind and says whether the list is ready.

**It needs a list it can read,** as a CSV or export file, as a table in the Deepline customer
database (read with `deepline db query`), or as CRM records read through Deepline's free CRM tools.
The live-campaign gate additionally needs the contacts currently enrolled in live sequences, as an
export from the sending tool or read through Deepline's free sequencer tools; without it that gate
is reported as not checked and the list cannot be cleared to go.

Do not start a step before the steps above it have their answers. If a declared input is
missing, ask for it. Never assume a default and continue.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's. Ask for it, and where a default
is named below, using it means saying so in the output.

| Input | What it is | If absent |
|---|---|---|
| **List source** | a CSV or export file, a Deepline customer-DB table name (for example `storage.<table>`, the table a batch play persisted), or a CRM object plus filter | ask. Never assume a table exists |
| **Buyer definition** | the titles that are the buyer of this product: title families with synonyms (for example Owner, Founder, President, Managing Partner), the seniority floor, and the disqualifying titles (analyst, associate, coordinator, assistant, intern, student, and any adjacent role that does not sign) | no default. Never inferred from the list. Without it the buyer-title gate cannot run and the list cannot pass |
| **Firm definition** | what makes a company in scope: industries or verticals, the size band (employee count or revenue), the serviceable geography, and firm exclusions (competitors, the wrong side of the market, categories the product does not fit) | no default. Without it the firm-fit gate is unmeasured and the list cannot pass |
| **Firm keywords** | optional: terms that mark a firm as in scope when they appear in its name, domain or a description column (for example advisory, brokerage, wealth). Used only when the list has no usable industry column | no default. Without them, a list with no industry column has its firm-fit gate unmeasured and every firm is unconfirmed until enriched |
| **Column map** | which columns hold: first and last name, title, company, domain, email, email verification status, LinkedIn URL, industry, size, country, block-list or do-not-contact flag, employment check, title-match check | detected from headers and shown at Step 2, then confirmed. A column that does not exist is **absent**, never "all pass" |
| **Suppression sets** | current customers, competitors, open pipeline, recent closed-lost, do-not-contact, and anyone in a prior send, as files, customer-DB tables or CRM reads, each with a domain or email column | any set not supplied is reported as **not checked**. With none supplied the suppression gate is unmeasured and the list cannot be cleared to go |
| **Live campaign contacts** | the emails, or names plus domains, currently enrolled in live sequences, exported from the sending tool or read per campaign through Deepline's sequencer tools (Step 0) | reported as **not checked**; the list cannot be cleared to go |
| **Gate thresholds** | the lines each gate is held to | the author's lines below; say they are borrowed |
| **Contacts per company cap** | the most rows one company may carry | 3, the author's line; say so |
| **Sample size** | rows read by eye at Step 5 | 50, the author's line |
| **Volume target** | how many rows the campaign wanted, if a number exists | optional. Used only to say plainly when the usable cut is under it. Never used to loosen a gate |

The author's thresholds, offered as a starting point and never applied silently. Rates are over
all rows read, before any cut.

| Gate | Passes when | Reasoning |
|---|---|---|
| 1. Buyer title | 80% or more of rows carry a buyer title and no disqualifying title | the person on the row is the one who can say yes |
| 2. Firm fit | 80% or more of rows are inside the firm definition on every field that exists, and no row hits a firm exclusion | the company is the one the product is for |
| 3. Verified email | 70% or more of rows carry an email marked deliverable by a verifier; catch-all, accept-all, risky and unknown do not count | unverified rows are the bounces |
| 4. Suppression | 0 rows on any supplied set | one email to a customer costs more than the whole campaign earns |
| 5. Live overlap | 0 rows already enrolled in a live sequence | two sequences to one person reads as spam |
| 6. Required fields | 90% or more of rows carry name, title, company, domain, and email or LinkedIn URL; and the industry, size and country columns exist | a field that is missing cannot be filtered on, so the ICP cannot be enforced |
| 7. Cap and junk | no company over the cap after ranking, and under 5% of rows are junk (blank title, role address, personal domain, failed employment or title-match check) | junk is the part of the list nobody decided to send to |

The verdict tiers, from the same audit:

| Verdict | Meaning | Next move |
|---|---|---|
| **Go** | every gate passes | ship it, minus the over-cap rows listed |
| **Fix** | gates 3 to 7 fail, or gate 1 sits between 40% and 80%: the list is the right list with removable or enrichable rows | ship the usable cut now; send the rest back to enrichment or remove them |
| **No-go** | gate 1 under 40%, gate 2 under 50%, junk at 50% or more, or a hard gate that could not be measured: the list as built is the wrong list, and filtering will not recover it | ship the usable cut if it is worth sending, and rebuild the rest from the firm side, with the buyer definition applied at the source |

## What this skill touches

- **Reads** - the list (a supplied file, a customer-DB table through `deepline db query` with
  SELECT only, or CRM records through free Deepline CRM read tools), any suppression files or
  tables, and the live-campaign contacts. A supplied file is read only; it is never modified. A
  customer-DB table or CRM is never written to.
- **Writes** - three files in your working directory: the clearance report, the usable cut, and
  the reject list with a reason per row. Nothing else.
- **Never** - deletes or edits a row in the source, edits a customer-DB table or column, runs an
  enrichment, verifier or paid tool or play, spends a credit, uploads a row to a sequencer, writes to a
  CRM, widens the buyer or firm definition to reach a volume number, infers the buyer titles from
  what is on the list, or sends an email.
- **Halts** - Step 2 `sample-review`, Step 5 `sample-review`.

## Step 0 - Check the platform works, and say where the work runs

Find out which list source is in play, and tell the installer before anything else:

- **A file:** no Deepline call is needed. Confirm the path and that it opens.
- **A customer-DB table, a CRM, or a sequencer read:** run `deepline preflight --json` once and
  name the org it reports. If `deepline` is missing, the install is
  `npm install -g deepline && deepline auth register --wait auto`; say so and let the installer
  run it. Then confirm the source is reachable for free:
  - customer DB: `deepline db query --sql "select count(*) from storage.<table>" --json`;
  - CRM: `hubspot_search_objects`, `salesforce_list_contacts` / `salesforce_list_leads`, or
    `attio_query_person_records` (all free through Deepline with the installer's own CRM
    connection; check with `deepline tools describe <id> --json`, which also shows whether the
    connection is live);
  - live campaigns: `smartlead_export_campaign_leads`, `lemlist_export_campaign_leads`,
    `instantly_list_leads`, or `heyreach_get_leads_from_list`, one call per live campaign
    (free; list the campaigns first with `smartlead_list_campaigns` / `instantly_list_campaigns`).
  A connection error means this source has to be an export instead. Do not connect, install or
  upgrade anything yourself.

If neither is available, stop and say this skill needs a list it can read, as a file, a
customer-DB table or a CRM read, and what each takes.

Then tell the installer, in one sentence: this skill reads the list and does its checks in the
agent; it runs no enrichment, spends no credits, and changes nothing in the source, in the
customer DB, in a CRM or in a sequencer. Its output is three files.

## Step 1 - Collect the definitions before reading a row (interview; do not guess)

This order is the whole skill. The buyer definition and the firm definition are written down
before any row is seen, and they do not change after the numbers arrive. If the installer asks to
see the list first, say why not: a definition written after the rows are known describes the
list instead of the buyer, and every list passes a definition written from itself.

Collect, in this order:

1. List source: the file, the customer-DB table, or the CRM object and filter. Rows in scope: the whole list, or a filter.
2. Buyer definition: title families and synonyms, the seniority floor, the disqualifying titles.
   Ask for the disqualifiers separately; people name the buyer readily and forget the roles that
   sit next to it. Matching is on words, not meanings, so ask for every spelling that counts: CEO
   and Chief Executive Officer are two families to this skill until both are listed.
3. Firm definition: verticals, size band, geography, firm exclusions. Ask what the size band is
   measured in, employees or revenue, and which column carries it.
4. Suppression sets, one by one: customers, competitors, open pipeline, recent closed-lost,
   do-not-contact, prior sends. Record each as supplied or not supplied.
5. Live campaign contacts: the export or table, and which field names a person (email, or
   name plus domain).
6. Thresholds and the cap: theirs, or the author's, labelled borrowed. Sample size. Volume
   target, if one exists.

Write all of it into the report header before Step 2 runs.

## Step 2 - Map the columns, then show the map (halt)

Read the headers, or for a customer-DB table run
`deepline db query --sql "select * from storage.<table> limit 1" --json` and read the column names
(for a batch-play table, skip the per-provider audit columns such as `email_result__<provider>`;
the coalesced column is the one to map). Match each declared field to a column by header name. Show the map as a
table: declared field, column found, or **absent**. Ask the installer to confirm or correct it.
This is the first `sample-review` halt.

A field with no column is absent for every row. Absent is not blank, and it is never a pass: an
absent verification column means no row is verified; an absent block-list column means the
block-list check did not run inside the source and this skill can only check the sets supplied
at Step 1; an absent industry, size or country column means the firm-fit gate is unmeasured on
that field and gate 6 fails on it.

A column that exists but is blank on more than half of the rows is **present but empty**: show it
in the map with its blank share, and treat it as absent from there on. Rows are not rejected for
a blank in a column that is blank everywhere; the gate that column feeds is unmeasured instead,
and the report says the fix is enrichment. An empty ICP column is the commonest reason a list
cannot be cleared, and the right answer to it is "fill the column", not "drop 95% of the rows".

For a table a play is still writing, check the run first (`deepline runs get <run-id> --json`). A
table whose run has not finished cannot be judged; say so and stop until it has, since a row read
mid-run reports a value that will change.

## Step 3 - Read every row, every page

For a file, read it whole. For a customer-DB table, take `select count(*)` first, then export the
whole table with `deepline db query --sql "select * from storage.<table>" --format csv --out
list.csv` and check the exported row count equals the count; query results are bounded by the
server and `--max-rows`, so a short export is a sample, not the list. Page with `order by` plus
`limit`/`offset` until the count is reached, and say how many pages were read. For a CRM read,
follow the tool's cursor (`after`, `next_records_url`, `offset`) until it is absent. Never judge
a sample as if it were the whole.

A blank cell in a play-written table is not always blank data: a step that errored or never ran
leaves the cell empty too. Where the table carries per-step outcome or `miss_reason` columns, a
row whose step errored or was skipped is **unmeasured** for that field, never blank and never a
pass; if any appear, count them and say so in the report.

**Check every value before using it.** Trim whitespace. Read "1,480" as 1480 and "12%" as 12. A
blank title is a blank title, not a junior one. A flag column holds true, false, or nothing, and
nothing means the check did not run on that row, which is not a pass. A verification column is
read by its values, not its name: only values that mean deliverable count (for example valid,
deliverable, ok, safe); catch-all, accept-all, risky, unknown and blank are not verified;
invalid and undeliverable are failed. Show the installer the distinct values found and which
bucket each landed in.

Parse the suppression sets and the live-campaign export the same way. Normalize every domain
(lowercase, strip protocol, `www.` and paths) and every email (lowercase, trim) before comparing.

## Step 4 - Row checks, deterministic, every reason recorded

Run every check on every row. A row collects every reason that applies; the first reason never
stops the rest. Nothing is deleted. The checks:

1. **Title.** A blank title is `no title`. A title containing a disqualifying term is
   `disqualified: <term>`. A title that contains no buyer family or synonym is `not the buyer`.
   Matching is case-insensitive on whole words, so "VP of Partnerships" does not match a
   "Partner" family. A row with two readings (a buyer word and a disqualifier) is disqualified;
   the disqualifier wins.
2. **Firm.** On every firm field that has a column: industry outside the verticals is
   `off-vertical: <value>`; size outside the band is `off-size: <value>`; country outside the
   geography is `off-geo: <value>`. A company name or domain containing a firm-exclusion term is
   `excluded firm: <term>`. A firm field with a column but a blank value is `firm unmeasured:
   <field>`, which fails the row for the usable cut and is counted separately from off-ICP. When
   the list has no usable industry column and firm keywords were supplied, a row whose company
   name, domain and description carry none of them is `firm unconfirmed`: not wrong, not
   confirmed, out of the usable cut until the sample or an enrichment confirms it.
3. **Email.** No email is `no email`. An email in the failed bucket is `email invalid`. An email
   in the not-verified bucket, or any email when the verification column is absent, is `email
   unverified`. Unverified is not invalid; it is reported on its own line so the installer can
   send those rows to a verifier rather than drop them.
4. **Suppression.** A domain or email matching any supplied set is `suppressed: <set>`. Match on
   normalized domain and on normalized email; never compare one row's domain to another set's
   company name.
5. **Live overlap.** A row whose email, or name plus domain, appears in the live-campaign
   contacts is `in live campaign`.
6. **Fields.** A row missing first name, last name, company, or domain is `missing: <field>`. A
   row with neither an email nor a LinkedIn URL is `no channel`.
7. **Junk.** A role address (info@, sales@, contact@, hello@, admin@, support@, office@) is
   `role address`. A personal mail domain (gmail, yahoo, hotmail, outlook.com, icloud, aol,
   proton) is `personal domain`. An employment-check column reading false is `not currently
   employed`. A title-match column reading false is `failed title check`. A LinkedIn-check column
   reading false is `failed profile check`. A row with the same normalized email as an earlier
   row is `duplicate of row <n>`.

**Then the cap.** Group rows by normalized domain. Within a company, rank rows: no reasons first,
then buyer title, then verified email, then the earlier row. Rows past the cap are `over cap`,
which excludes them from the usable cut but does not count against gates 1 to 6, since they are
not wrong, only surplus.

**The usable cut** is every row with no reason at all after the cap. Everything else is a reject
row with its reasons, in the order above.

## Step 5 - Gates on the whole list, then the sample (halt)

Compute each gate over all rows read:

- Gate 1: share of rows with none of `no title`, `disqualified`, `not the buyer`.
- Gate 2: share of rows with none of `off-vertical`, `off-size`, `off-geo`, `excluded firm`,
  measured only over rows where every firm field with a column has a value; report the
  unmeasured share and the `firm unconfirmed` count beside it. If any firm field (industry,
  size, country) has no usable column, the gate is **unmeasured** on that field, and the share
  on the fields that exist is reported beside it.
- Gate 3: share of rows with a verified email. If the verification column is absent, the gate
  reads 0% and says why.
- Gate 4: count of `suppressed` rows, and the list of sets not checked.
- Gate 5: count of `in live campaign` rows, or **not checked**.
- Gate 6: share of rows with no `missing`, no `no channel`; and whether the industry, size and
  country columns exist and are not present-but-empty.
- Gate 7: count of companies over the cap, and the junk share (`no title`, `role address`,
  `personal domain`, `not currently employed`, `failed title check`, `failed profile check`,
  `duplicate`).

Each gate is pass, fail, or unmeasured, with the number beside it. Never combine them.

Then draw the sample: the sample size in rows, half at random from the usable cut and half at
random from the rejects with their reasons, and show them. Ask the installer the one question
that matters: would you be comfortable if the client, or the buyer, saw this list? If a sampled
row is judged wrong by eye, the fix is to the buyer or firm definition at Step 1, then Steps 4
and 5 run again; never a hand edit to one row, since the row that was wrong by eye has siblings
the eye did not see. This is the second `sample-review` halt.

## Step 6 - Verdict, single-valued, first match wins

1. **No-go, unmeasured** - the title column or the email column is absent, or the source could
   not be read whole. A gate that cannot run is not a pass.
2. **No-go, wrong list** - gate 1 under 40%, or gate 2 under 50% of measured rows, or junk at 50%
   or more. The source pulled the wrong people or the wrong firms, and filtering leaves too
   little to call it the same list. Say which one, and name the usable cut anyway.
3. **Fix** - any gate fails and rule 2 did not fire. Name each failed gate with its number and
   the rows that caused it, and say which rows go back to enrichment (unverified, missing
   fields) and which are removed (suppressed, in live campaign, disqualified, junk, over cap).
4. **Go** - every gate passes and none is unmeasured. The over-cap rows are listed and left out.

A verdict of go is impossible while gate 4 has a set not checked or gate 5 is not checked; those
lists stop at fix with that named as the only open item, which is the intended reading: cleared
except for the check nobody ran.

## Step 7 - Deliver

Write three files to the working directory and show the report:

- `list-clearance-<YYYY-MM-DD>.md`: the header (definitions, thresholds with borrowed ones
  labelled, sets supplied and not), the gate board, the verdict with its rule, the reason counts,
  the sample, and the coverage line.
- `list-clearance-<YYYY-MM-DD>-usable.csv`: the usable cut, every source column kept as it was.
- `list-clearance-<YYYY-MM-DD>-rejects.csv`: every other row, every source column, plus one
  `reasons` column.

Lead with the verdict and the usable count. Then the gate board. Then the reason counts, largest
first. If a volume target was given and the usable cut is under it, say so in one line and do not
soften it: the gap is closed by enrichment or a rebuild from the firm side, not by a wider
definition. End with the coverage line: rows read, pages read, rows usable, rows rejected by
reason, cells unmeasured, sets not checked.

The report is an assessment. Nothing in the source, in the customer DB, in the CRM or in the
sequencer has changed.

## Representative output

### Verdict

**Fix.** 2,140 rows read; **612 usable (29%)**. Gate 1 at 71% (line 80%), gate 3 at 58% (line
70%), gate 4 with 3 suppressed rows still in, gate 5 not checked. Gates 2, 6 and 7 pass.

### Gate board

| Gate | Line | Measured | Verdict |
|---|---|---|---|
| 1. Buyer title | 80% or more | 71% (1,519 of 2,140) | fail |
| 2. Firm fit | 80% or more, measured rows | 91% (1,780 of 1,956 measured; 184 unmeasured on size) | pass |
| 3. Verified email | 70% or more | 58% (1,241 of 2,140); 640 unverified, 259 invalid | fail |
| 4. Suppression | 0 | 3 (customers); not checked: closed-lost | fail |
| 5. Live overlap | 0 | not checked | unmeasured |
| 6. Required fields | 90% or more, columns present | 96%; industry, size, country present | pass |
| 7. Cap and junk | 0 over cap, junk under 5% | 41 over cap; junk 3.2% | pass |

### Reason counts (a row can carry several)

| Reason | Rows |
|---|---|
| email unverified | 640 |
| not the buyer | 512 |
| email invalid | 259 |
| firm unmeasured: size | 184 |
| disqualified: associate | 74 |
| over cap | 41 |
| no title | 35 |
| personal domain | 22 |
| role address | 12 |
| suppressed: customers | 3 |

### Sample (25 usable, 25 rejected; 4 shown)

| Row | Title | Company | Email status | Reasons |
|---|---|---|---|---|
| 118 | Managing Partner | Contoso Advisors | deliverable | usable |
| 902 | Founder | Fabrikam Brokerage | deliverable | usable |
| 233 | Senior Associate | Northwind M&A | deliverable | disqualified: associate |
| 1,471 | Owner | Litware Partners | catch-all | email unverified |

### Coverage line

2,140 rows read in 22 pages · 612 usable · 1,528 rejected · 0 cells unmeasured · sets not
checked: closed-lost, live campaigns.

## What this skill does not claim

- It does not verify an email. It reads the verdict a verifier already wrote. A list with no
  verification column is unverified, however good it looks.
- It does not know whether a firm is in the ICP beyond the columns it can read. A firm with the
  right industry code and the wrong business is invisible to it, and a firm keyword is a floor,
  not a verdict: it keeps some wrong firms and holds back some right ones with neutral names.
  The sample at Step 5 exists for that reason.
- Title matching is on words, so it is a floor. It keeps some wrong rows and rejects some right
  ones; the disqualifier list and the sample are where the installer corrects it.
- It cannot see live campaigns without the export or the per-campaign reads. No single Deepline
  call lists every contact enrolled in every sequence across every sending tool; a campaign not
  read is a campaign not checked.
- The default thresholds are one agency's lines from its own client audits. They are a starting
  point, not a law of outbound.

## What good looks like

A good run has the buyer and firm definitions written at the top of the report, with borrowed
thresholds labelled, before a single row is described. Every gate carries its number and its
rule, so anyone can check the verdict by hand. The usable cut is smaller than the list, often
much smaller, and the report says so without apology, because the rows it removed were never
going to reply. The reject file lets the installer send the unverified rows to a verifier and
the not-the-buyer rows back to sourcing without reading the list again.

A thin run looks like a single percentage score, a pass on a gate whose column does not exist,
a buyer definition that happens to match every title on the list, a "go" while a suppression
set was never supplied, or a usable cut that equals the whole list. A list on which every row
passes every gate is rarer than a list on which none does; a report with no rejects is more
likely wrong than tidy.

## Rules

- The buyer and firm definitions are fixed at Step 1, before any row is read. Never adjust a
  definition after seeing the rows in the same run, except by re-running from Step 4 after the
  sample and saying so.
- Seven gates, each reported alone. Never a combined score, never a letter grade.
- Absent is not a pass. A missing column makes its gate unmeasured, and an unmeasured hard gate
  makes the verdict no-go. A column blank on more than half of the rows is absent, and rows are
  never rejected for a blank in it.
- Unverified is not invalid. Report them on separate lines.
- Never infer the buyer titles from the list, and never widen a definition to reach a volume
  target.
- Nothing is deleted. Every rejected row is returned with every reason that applied.
- A sampled row judged wrong changes the definition, never the row.
- Never run a verifier, an enrichment or a paid tool or play, and never spend a credit. Never
  write to the source, to the customer DB, to a CRM or to a sequencer.
- Never judge a sample as the whole list. A bulk enrichment or archive table is read from its
  export.

## Worked example

Fabrikam sells a staffing service to education software companies. The installer supplies a
2,140-row export of "EdTech companies, $15M to $100M" with a buyer definition of COO, VP
Operations, VP People, Head of Talent, CEO or Founder; disqualifiers analyst, associate,
coordinator, assistant, customer success, sales; and a firm definition of education software,
50 to 800 employees, US. Suppression: a customer file. Not supplied: closed-lost, and the live
campaign export.

Step 2 finds title, company, domain, email, a verification column with the values valid,
catch-all, invalid and blank, an industry column, an employee-count column, and a country
column. No employment-check column. The map is confirmed.

Step 4 finds 512 rows whose title is customer success, sales or support, which fail as not the
buyer, and 74 senior associates, disqualified. The verification column reads valid on 1,241
rows, catch-all or blank on 640, invalid on 259. Three rows match the customer file by domain.
184 rows have a blank employee count. One company, a large publisher, carries 19 rows; 16 are
over the cap.

Step 5 puts gate 1 at 71%, under the 80% line but over 40%, so the list is the right list with
the wrong people mixed in, not a wrong list. Gate 3 at 58%. Gate 4 fails on the 3 customers and
names closed-lost as not checked. Gate 5 is not checked. The sample shows 25 usable rows the
installer would happily be seen sending to, and 25 rejects whose reasons hold by eye.

The verdict is **fix**: 612 rows usable now. The 640 unverified rows go to a verifier, the 3
customers and the 586 wrong-person rows are removed, and the report says in one line that the
1,000-row target is not met and that the gap is closed at the source, by pulling the buyer
titles at the education software companies rather than everyone at them.
