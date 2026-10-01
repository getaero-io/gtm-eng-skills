---
name: tam-audience-loader
description: |
  Load a list of companies and a list of people into the Deepline customer database — a target
  account list, a TAM you built in a model conversation, a spreadsheet, a CRM export — as something
  you can actually use: your own attributes as real typed columns you can filter and segment on, and
  every contact attached to its company by a real foreign key rather than merely sharing a domain
  with it. Hand it one table or both, as CSVs, as tabs of an Excel workbook, or as a Google Sheet you
  export, and you keep a loader you can run again next quarter. The failure it exists to prevent is
  the quiet one — a column that loads but cannot be filtered the way its values mean — so it checks
  every value before writing, and afterwards tells you what the table actually holds. Use whenever
  someone asks: get my spreadsheet of companies and contacts into Deepline, load a list of companies
  and a list of people into the customer DB, put my accounts and their people into Deepline, load my
  TAM into Deepline, import a companies and contacts CSV, upload my spreadsheet of accounts, get my
  target account list out of Excel or Google Sheets and into Deepline, bulk load accounts and people,
  link contacts to their companies, import a list with custom columns, or resume a load that died
  halfway. Do NOT use it to source net-new companies or people, to enrich or verify records once
  they are in, to merge or dedupe against records the tables already hold, to build a segment or
  filter over records that are already loaded, to push anything into a CRM or a sequencer, or to
  move records out of Deepline.
category: build-lists
personas: [gtm-engineer, revops]
mechanism: workflow
touches: writes-records
keywords: [csv]
ported_from: clay-run/clay-skill-creator/skills/shy-rahnama-2/tam-audience-loader
---

# TAM audience loader (load for the query, not for the row count)

**A loaded row is not a queryable row, and the load itself does not tell you which one you got.**
Measured on Clay Audiences, one workspace, 2026: a company was written with `1,001-5,000` in a field
declared as a number. The write returned `✅ Success`, the record read back showed the value, and
the audience said that field was populated on one of two companies that both carried a value. A
date field given `Q3 2017` behaved the same way.

The Deepline customer DB is Postgres, and it fails the other way: **loudly**. A typed column refuses a
value it cannot parse, and it refuses the whole statement — one `1,001-5,000` in a `numeric` column
and every row in that INSERT fails with it. Loud is better than silent, and it has its own quiet
failure, which is the fix people reach for: type the column `text` so the error goes away. Every
value then loads, every row reports success, and `employee_count > 100` no longer works — compared
as text, `'88'` sorts above `'512'`. A TAM exists to be sliced — by headcount, by tier, by founded
year — and this is the failure where you slice it, get a wrong list, and have no reason to doubt it.

**The second half is the same problem wearing a different face: the company link is not implied.**
A contact carrying `northwind.example` is not thereby attached to the company row whose domain is
`northwind.example` — a matching domain establishes nothing. The link is `company_id`, a foreign key
to the companies table, and it is an `id` that does not exist until the company has been loaded.

Both facts point the same way, and it is the shape of this whole skill: **everything that decides
whether the load worked is checkable before a single row is written.** So the types get checked
against the file, the match keys get counted, the collisions get counted, all of it free — and then,
after the load, the skill asks the table how many of this load's rows have each column populated and
holds that number against the one the file carried. A column where those two disagree did not land,
whatever the ledger says.

> Do not start a step before the steps above it have their answers. If a declared input is missing,
> ask for it — never assume a default and continue.

> **If an answer sheet is present beside this skill, load it and ask only for what it does not
> cover.** A partial sheet is normal; a value it is missing gets asked for on its own rather than
> restarting. **Say which values came from the sheet** before using them. **If there is no sheet,
> say nothing about sheets.** It skips questions; it never skips the gate at Step 4.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing. Where a default IS defensible it is named below, and using it
means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The two tables** | one of companies, one of people, each with a header row. **Two CSVs, two tabs of an `.xlsx`, or a Google Sheet they export to CSV** — everything downstream takes `FILE` or `FILE#TAB` | no default — there is nothing to load. **State the minimum requirements, ask where the data lives, and stop until you have it.** One table alone is a valid run: load companies and say the people phase did not run |
| **The company key, and the column on the contacts file that points at it** | which column names a company, and which contacts column carries that same value | **derive it from the headers and show it** — do not ask them to recite. If no company key column exists, mint one (domain, else a slug of the name) and say you minted it and from what |
| **Which attribute columns to load, and the type for each** | a yes to the mapping you show, or corrections | show every column with its inferred type, two real values from the file, **and whether the table already has a column for it** — then take corrections. A column nobody confirms is not created and not loaded |
| **Whether a column reuses an existing table column or gets a new one** | a yes to the matches you propose | **read the live tables and match it yourself** — the script prints both lists and asserts only same-label matches, because everything else is judgment. Never add a column beside one that already means the same thing: a duplicate splits every later filter. Where the existing column stores a different type that is not a match at all; say so and make them choose |
| **The table prefix** | a short name, so the tables are `storage.<prefix>_companies` and `storage.<prefix>_contacts` | **`tam` is a stated default.** A second, unrelated TAM gets its own prefix; reusing one merges two loads into one pair of tables |
| **Match-key order** | the order to try the match keys | **`domain` then `linkedin_url`** for companies, **`email` then `linkedin_url` then `phone`** for people. Defensible and borrowed — say so. It is a run flag, not a build choice, so changing it never rebuilds anything |
| **A contact whose company did not load** | load it with no company link, or hold it | **default: load it, unlinked (`company_id` NULL), stamped `associated: false`.** Say which you used and how many it covered |
| **Whether to create companies that are in neither the file nor the table** | yes or no, asked at the Step 4 gate | **no default — it writes records nobody listed.** Say what they get: a bare row with a match key and a name, none of the attributes a companies table would carry. On a people-only run this decides whether the run does anything at all |
| **Where a contact's company key comes from** | a company-domain column, a company-LinkedIn column, or neither | derive it and show it. Failing both, the work email's domain is used, **excluding free mailboxes**. A company name is never a source: nothing can be keyed on one, and matching on it attaches contacts to the wrong company |
| **Batch size and pace** | how hard to push | **200 rows per INSERT, half a second between batches.** Not measured — say so. A batch is one statement, so a smaller one loses less to a single failure |

**And these are derived, not asked. Each is settled by something already on screen:**

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Which database** | **nothing — do not ask.** The active Deepline workspace has one customer DB, and `deepline db query` writes only to schema-qualified `storage.*` tables in it | there is no choice to offer. Name the workspace instead |
| **Which match key each row uses** | **nothing — do not ask.** The match keys are fixed and the row either carries one or does not | the driver picks per row, in the declared order. The Step 3 report says how many rows each key claimed |
| **The table shape** | **nothing — do not ask.** `id bigserial`, a UNIQUE `match_key`, the base key columns, one column per confirmed field, and `company_id` on contacts | see `references/column-mapping.md` |

### The two keys, and why there are two

**The key you built your TAM on and the key the upsert matches on are different keys, and every
duplicate this load can produce lives in the gap between them.** Say this once, plainly, at Step 2 —
it is the single thing an installer most needs and least expects.

| | What it is | Who chooses it |
|---|---|---|
| **Row key** | identifies a row in your file and in the ledger, and joins a contact to its company | **yours.** Any stable column; minted from stable fields when the file has none |
| **Match key** | what the upsert matches an existing row on: the `match_key` column, `<key>:<value>` | **not yours.** Companies: `domain` or `linkedin_url`. People: `email`, `linkedin_url` or `phone`. Nothing else, including a column you add |

Two consequences, both counted at Step 3 rather than explained:

- **Two rows sharing a match key become one row in the table.** Distinct row keys, one record, and
  the second write fills in what the first left blank. The ledger will say two loaded.
- **A row carrying no match key cannot be loaded at all**, however complete it otherwise is.

## What this skill touches

- **Reads** — the tables you point it at (CSV, TSV, or tabs of an Excel workbook); the columns the
  two `storage.<prefix>_*` tables already hold, including how many rows carry each and one value it
  holds; and after loading, which of the rows it wrote carry each column.
- **Writes** — two tables in the workspace's Deepline customer DB, `storage.<prefix>_companies` and
  `storage.<prefix>_contacts`, created if missing; one column per field confirmed at Step 1; one row
  per row it loads, plus `company_id` on contacts. **And, only on an explicit yes at Step 4, a
  company row for a contact whose employer is in neither your file nor the table** — a row nothing
  in your file asked for, carrying a match key and a name.
- **Never** — deletes a row, empties a populated column, or writes a column outside the confirmed
  list. **It never decides that two records are the same thing.** The only matching it does is the
  exact match on `match_key`, plus an exact lookup of a company by domain or LinkedIn URL — no fuzzy
  matching, no merging two existing rows, no reconciling your file against what the table already
  holds. Nothing leaves the workspace, and nothing touches the CRM-synced tables.
- **Halts** — Step 0 `other`, Step 1 `sample-review`, Step 4 `write-approval`.

## Try it on the shipped sample before pointing it at real data

A small TAM ships with this skill so the whole flow can be exercised on data nobody minds:
`references/sample-companies.csv` (18 rows, 27 columns), `references/sample-contacts.csv` (32 rows,
21 columns) and `references/sample-mapping.json`. It is shaped like a TAM a model actually
produces — a few columns that land in standard columns, a pile of research columns that need their
own, and values that are *nearly* well-formed — and **every defect in it is deliberate**, each
caught at a different step by a different check.

Steps 1 and 3 on it cost nothing and write nothing:

```
python3 scripts/loader_lib.py inspect --companies references/sample-companies.csv --contacts references/sample-contacts.csv
python3 scripts/loader_lib.py check   --companies references/sample-companies.csv --contacts references/sample-contacts.csv --map references/sample-mapping.json
```

`references/sample-dataset.md` walks the whole thing through with real output and lists what each
planted defect teaches. **Use a throwaway prefix** (`--prefix tamtrial`) for a trial load, so that
the two tables it leaves can be dropped without going near a real one.

## Step 0 — Say what is about to happen, get the data, check the platform `other`

### First: orient them. Plain words, before anything else happens.

**Say this in your own words, but say all of it.** Someone who just triggered this skill has no idea
what is about to happen in their Deepline workspace, and the two things it creates are things they
did not ask for by name:

> "I'll load your companies and your people into your Deepline customer database, with each contact
> attached to its company. `<one clause on what they actually handed you>`
>
> **How it goes:**
>
> 1. I read both tables and show you every column — the type I think it is, two real values, and
>    whether the table already has a column for it. You fix anything I got wrong and pick what to
>    bring in.
> 2. I count what can't load, before anything is written.
> 3. **One approval** — the counts, the columns, the writes. Nothing touches your workspace until
>    you say go.
> 4. Companies load, then contacts against them.
> 5. I ask the database what it actually holds and hold that against what your file carried.
>
> **What you end up with:** two tables, `storage.<prefix>_companies` and
> `storage.<prefix>_contacts`, that you can query with `deepline db query` and join to anything else
> in the workspace. The scripts and the ledger are the loader — run them again next quarter and
> only the new rows and any new columns are added.
>
> Nothing gets deleted, no field gets emptied, and rows already in there keep their values."

**Keep it this short.** Two sentences, five numbered lines, two short paragraphs — then get on with
it. This is orientation, not a gate, and nothing waits on it.

### Then: say what the data has to contain, ask where it lives, and stop until you have it

**One table or two — companies, people, or both — and "a table" does not mean "a CSV".** Say what
is required before asking for anything, so they can check their own data rather than find out four
steps later:

| What they have | What happens |
|---|---|
| **Both tables** | companies load first, then people against them. The normal case |
| **Companies only** | load them and say the people phase did not run |
| **People only** | every company has to be found in the table or created from the contact, so the question at Step 4 is not optional — it decides whether the run does anything at all |


> **What this needs, per table:**
>
> - **A header row**, and one row per company or per person.
> - **Something that identifies each company: a website domain or a LinkedIn company URL.** A row
>   with neither cannot be loaded at all — those two are the only company match keys.
> - **Something that identifies each person: a work email, a LinkedIn profile URL, or a phone.**
>   Same rule; any one of the three is enough.
> - **A column on the people table naming which company they belong to** — an id, a domain, whatever
>   the companies table is keyed on — and **the same value has to appear on both sides.** This is the
>   one that quietly breaks: if the companies table says `ACME-01` and the people table says
>   `Acme Corp`, nothing links up.
> - Everything else is optional, and you choose which of it to bring across.

**Then ask where it lives, and name the shapes that work**, because most TAMs are not two loose CSVs:

> "Where is the data? Any of these work:
>
> - **Two CSV files** — one companies, one contacts.
> - **One Excel workbook** with a tab for each. Tell me the file and I'll list the tabs.
> - **A Google Sheet** — I can't read it directly, since that needs credentials I don't take and
>   won't ask for. In the sheet: File → Download → Comma-separated values, once per tab, then point
>   me at the two files. If you have a Google Drive connector set up, it can fetch them instead.
>
> One table alone is fine too — I'll load the companies and skip the people."

For a workbook, list the tabs and show which one you think is which rather than asking them to
recite tab names:

```
python3 scripts/loader_lib.py sheets --companies <book.xlsx>
```

Everything downstream takes `FILE` or `FILE#TAB`, so a workbook needs no conversion step:

```
--companies 'book.xlsx#Target Companies'   --contacts 'book.xlsx#People'
```

**A spreadsheet stores a date as a number**, and read raw it is a plausible five-digit integer that
survives a numeric check and lands in the table as nonsense. The reader converts date-formatted
cells to ISO dates; say nothing about it unless something looks wrong, but know that a `founded`
column reading `40635` anywhere means this went wrong and the load should stop.

**If they named the files in their opening message, do not ask** — take the paths and say which two
you are using, in one line, so a wrong guess is correctable by reading.

**Never ask for a credential, a login, or a sharing change** to reach data. Not a Google account,
not a "publish to the web" link, not an API key. If it cannot be read from disk, say so and name
the export that makes it readable.

Ask for nothing else here. Every other decision has a step that needs it and a screen to show
alongside it, and front-loading them produces the interrogation this flow exists to avoid.

### Then: the platform

```
deepline preflight --json
```

It must report `auth: claimed` and a workspace. **Say the workspace name out loud, as a statement
with a handle on it** — *"loading into Northwind GTM; say so if that is the wrong one"* — because a
load into the wrong workspace is the one mistake here with no undo. Do not stop for an answer: the
workspace is named again at the Step 4 gate, which is where the stop belongs.

**If the platform check fails, say which component is wrong and the one command that fixes it —
then stop.** A missing CLI is `npm install -g deepline && deepline auth register --wait auto`. Do not
install, upgrade, clone or fetch anything else to repair it.

Then confirm the database answers at all — a read, free:

```
deepline db query --sql "select 1 as ok" --json
```

A failure here is a workspace answer for the installer (no customer DB, or no permission on it), not
something to retry or work around — say so and stop. `deepline db repair` exists, but it is
admin-only and it is the installer's call, not this skill's.

## Step 1 — Read the tables and show the mapping you found `sample-review`

**Read the headers, infer a type per column, and show it. Never ask anyone to recite their own
column names.**

```
python3 scripts/loader_lib.py inspect --companies <path> --contacts <path>
```

That prints, per file: every column, the type it infers, two real values, how many rows are blank,
and which columns it proposes as the row key and the company-reference column. Type inference and
what each type is stored as are in `references/column-mapping.md`.

Show the table. Then **one message, covering the whole mapping at once**: which columns to load, and
any corrections — to a type, to the proposed row key, or to the column that points a contact at its
company. All of it is on screen together, so all of it gets answered together.

Columns nobody confirms are not created and not loaded — a TAM CSV usually carries far more than
belongs in the table, and the default is to leave a column out rather than to bring it in.

**One of those corrections matters more than the rest and must not be waved through: the column on
the contacts file that says which company each contact belongs to.** It is joined to the company
row key by string equality and nothing else, so if the two name different things, every contact
loads with no company attached and every row still reports success. Show the proposal with two real
values from each side, so a mismatch is visible rather than assumed:

```
company row key     company_id   e.g. NW-001, CT-002
contact references  company_id   e.g. NW-001, CT-002     <- these must be the SAME key
```

### Before settling the mapping, lay it beside what the tables already have

```
python3 scripts/build_loader.py match --prefix <prefix> --companies <file[#tab]> --contacts <file[#tab]>
```

That prints two lists and asserts almost nothing: every column `storage.<prefix>_companies` and
`_contacts` already hold, with the type each stores, how many rows carry it and one value, and every
column in the file, with what its values read as and two real examples. On a first load the tables
do not exist yet and it says so. **The matching is yours to do** — you can see a column called
`staff_count` with values `512` and `88`, and a table column `employee_count` that stores a number,
and draw the obvious conclusion. A lookup table cannot; it was tried, and it could not see
`# of employees`, a header in another language, or anything its author had not thought of, while
printing "no field yet" in a way that read as an answer rather than as nobody having looked.

The only matches the script asserts are **same-label** ones, where case and punctuation are the
only difference. Those are facts. Everything else is a judgment, and judgment is what you are for.

**Why it matters here rather than at Step 5.** A file column that quietly gets its own table column
beside one that already means the same thing splits every later filter — half the rows under one
name, half under the other, and neither total is right.

For each column, decide one of three things, and **say why for every match that is not a
same-label one**:

| | Put in the mapping |
|---|---|
| it belongs in a column that already exists | that column name as `field_id` |
| it is genuinely new | a `field_name` (it becomes a snake_case column) and a type |
| it does not belong in the table at all | nothing — leave the column out |

**A `TYPE CONFLICT` line is not a match.** It means a column of that name exists and stores a
*different* type than the file column reads as:

```
  employee_count  text  512 | 1,001-5,000 | 88   employee_count -- TYPE CONFLICT, stores numeric
```

Reuse that and every `1,001-5,000` fails its batch. Retype the column or give it a column of its own.
**The build refuses that reuse**, so it cannot be waved through by accident, but it is far cheaper to
settle here.

**Two guards on your own judgment.** Do not match on words that overlap when the meaning does not —
a `revenue` column is not `net_new_arr_potential`, and a TAM's `location` is not necessarily the
headquarters column. And **when you are unsure, propose a new column**: a wrong reuse writes real
values into the wrong place and is tedious to unpick, while an extra column is a line in a list.

**One more thing to say while they look at it**, because it bites later and is not visible in a
header row: **a column holding several values per row is one text column.** It can be matched with
`ILIKE`; it cannot be counted or split without SQL nobody will write later.

## Step 2 — Say which key is yours and which one is the table's

**Nothing is asked here.** The row key and the contacts column that points at it were shown in the
Step 1 table and corrected there; asking again is two messages for one answer.

What this step owes the installer is a disclosure. **If the file had no stable key and one was
minted** — a deterministic slug, from the domain where there is one and from a normalised company
name where there is not — say so, say which columns it came from, and say that re-running with the
same file produces the same keys. Minting is a legitimate answer; minting silently is not, and the
cost is real: two different companies with the same name collapse into one row.

Then state the two keys, as the table above states them. One short paragraph, no question attached —
the installer is not being asked to choose the match key, because they cannot.

## Step 3 — Count what cannot load, before anything is written

Everything in this step is free and reads nothing but the files.

```
python3 scripts/loader_lib.py check --companies <path> --contacts <path> --map <mapping.json>
```

It produces the coverage report shown under `## Representative output`, and it is the evidence the
gate is built on. Five counts, and each has a different remedy:

| Count | What it means | What the installer can do |
|---|---|---|
| **rows with no match key** | cannot be loaded, at all | supply a domain, LinkedIn URL, email or phone — or accept the loss with the number in front of them |
| **values that are not that kind of key** | present, and refused exactly like a blank | fix the value. A match key is checked for being *that kind of thing*, not merely non-empty — `linkedin_url` must be a `linkedin.com` URL, an email must parse, a phone must have digits. The loader falls through to the next key, so this only loses a row that had no other |
| **rows sharing a match key** | will collapse into one row | split them, or accept the merge knowing which rows merge |
| **contacts whose company key is not in the companies file** | will load without a company link | fix the reference, or accept unlinked contacts |
| **values a column's type will not parse** | dropped and named per row — sent, each would fail its whole batch | change the column's type to text (and lose numeric filtering on it), or fix the values |

**The last one is the one to lead with**, because it is the one whose fix is tempting and wrong. The
report names the column, the count and two offending values. A column where most values fail is
usually a type inference that should have been `text`; a column where two of four thousand fail is
usually a column that should stay numeric with two values dropped.

## Step 4 — One gate: the rows, the columns, the writes, the ask `write-approval`

Everything free has now run. One message, then stop and wait:

- **the workspace**, by name, because this is the last point before anything in it changes;
- how many companies and how many contacts will be loaded, and how many will not, by reason;
- **how many contacts will get a company attached, and how many will not** — the single number
  most likely to be quietly wrong, so it is said out loud before anything is written;
- **the question about companies the contacts reference but the companies file does not have**,
  which has to be asked here because it decides whether rows get written that nobody listed:

  > "N of your contacts work at companies that aren't in your companies list. M of those companies
  > are already in the table, so I'll just attach the contacts to them. The other K aren't in there
  > at all. Do you want me to create them?
  >
  > If yes: they'll be created from the contact's company domain or LinkedIn URL, and they'll be
  > **bare rows** — a domain and a name, nothing else. None of the attributes your companies table
  > would have given them: no tier, no fit score, no research. They'll sit in the table looking
  > thinner than everything else, and I'll hand you the list so you can load them properly when you
  > have data for them.
  >
  > If no: those contacts load without a company attached, and I'll tell you how many."

  **Say the bare-row part every time, even when they sound keen.** A company row with a domain and
  nothing else is indistinguishable from a real one in a list, and someone filtering on tier next
  week will quietly miss every one of them.
- the two tables and the columns about to be **created**, by name and type — `build_loader.py build
  --dry-run` prints every statement and runs none;
- that this **writes rows into their customer DB** — a mutation, not a read — naming both tables;
- what it costs. **Say the honest thing: `query_customer_db`, the tool behind `deepline db query`,
  is priced `Free` per call in `deepline tools describe query_customer_db --json`.** That is the
  catalogue's price, not a measurement of this load, so **take the balance before the load and again
  after and report the real movement**:

```
deepline billing balance
```

**Never fold away this ask, and never split it into three.** Table creation, column creation and the
load are one decision and they happen in one order.

## Step 5 — Create the tables and the columns

**Say what is about to appear in their workspace, in plain words, before it appears:**

> "I'm creating two tables in your customer database, `storage.<prefix>_companies` and
> `storage.<prefix>_contacts`, with one column for each field you confirmed. Contacts get a
> `company_id` column that points at the companies table. If the tables are already there from a
> previous load, only the missing columns are added."

Before writing anything, run the offline checks — no database, no network, no credentials, a few
seconds — because the failures they cover are the ones that build perfect tables and then fail
every batch:

```
python3 scripts/test_loader.py
```

A non-zero exit means the SQL and values this load would produce are wrong, and the right response is
to stop rather than to build and find out on row four thousand. Then:

```
python3 scripts/build_loader.py build --prefix <prefix> --map <mapping.json> --out build-state.json
```

It reads `information_schema.columns` for both tables first, **adopts every column that already
exists under the same name, and refuses — before running anything — to reuse one whose stored type
disagrees with the mapping.** That is the last guard against the back door: a `text` column fed
numbers, or a `numeric` column fed bands. The fix is at Step 1 — retype the column, or give it a
column of its own.

Then, in order, one statement per call through `deepline db query`:

| | Statement | Why |
|---|---|---|
| 1 | `CREATE TABLE IF NOT EXISTS storage.<prefix>_companies (id bigserial PRIMARY KEY, match_key text NOT NULL UNIQUE, row_key, domain, linkedin_url, org_name …)` | the UNIQUE `match_key` is what the upsert matches on |
| 2 | `ALTER TABLE … ADD COLUMN IF NOT EXISTS "<column>" <type>` per new company field | typed, so a filter means what it says |
| 3 | `CREATE TABLE IF NOT EXISTS storage.<prefix>_contacts (…, company_id bigint REFERENCES storage.<prefix>_companies(id))` | the company link is a value the database enforces |
| 4 | `ALTER TABLE … ADD COLUMN IF NOT EXISTS` per new contact field | |

**Every statement is idempotent.** A second build over the same prefix adds only the gap, and a lost
`build-state.json` strands nothing: build again with the same `--prefix` and it is rewritten.
Writes are only allowed to schema-qualified `storage.*` tables; the CLI refuses anything else.

## Step 6 — Load the companies, ten first

```
python3 scripts/load_drive.py --entity companies --state build-state.json \
        --csv <path> --map <mapping.json> --ledger ledger/companies.jsonl --limit 10
```

Ten rows run. Then, before the rest: run Step 8's verification on what has loaded and show, per
column, how many of the ten have it populated against how many carried a value in the file. **Stop
and ask only if those numbers disagree.** If they agree, say so in a line and keep going:

```
python3 scripts/load_drive.py --entity companies --state build-state.json \
        --csv <path> --map <mapping.json> --ledger ledger/companies.jsonl
```

Rows go in batches — one `INSERT … ON CONFLICT (match_key) DO UPDATE … RETURNING id, match_key` per
batch — and **every row's verdict is appended to the ledger the moment its batch returns**, carrying
the `id` that came back for its match key. A row whose key did not come back is `failed`, not
`completed`: settling needs positive evidence. On a match the upsert fills only what the row
carried (`COALESCE(EXCLUDED.c, t.c)`), so a re-load never empties a column. Re-running recomputes
the remaining work from the ledger, so a load that dies resumes and a completed row is never written
twice. `references/ledger-and-resume.md` carries the record shape, the settled-versus-retryable rule
and the resume breadcrumb the driver writes.

**Do not "fix" a transient failure before retrying it.** Only `completed` and the `rejected_*`
verdicts are settled; a `failed` stays in the work set and the next pass picks it up. A statement
that timed out fails its whole batch at once and clears on its own. **Read the `reason` first,
though**: a type error names the column and the value, and that one is a Step 3 fix, not a retry.

**And a failure that repeats is still not proof of a rule.** Watched on a real run (on Clay
Audiences, 2026): one contact failed twice, two minutes apart; the run noticed she was the only
contact without an email, concluded an email was required, and reported that as a finding. The
identical payload succeeded later untouched. **Two samples and a plausible story is how a load ends
up inventing email addresses to satisfy a rule that does not exist.** Before claiming the platform
behaves a certain way, bisect it — one variable at a time — and if you cannot, report the failure
and say you could not explain it.

## Step 6b — Resolve the companies the contacts reference but the file does not have

**Only when there are contacts, and only after the companies have settled.** A contact's company
can be in three places, and this step is where the second and third are settled — before any
contact is written, so the counts at Step 4 were true.

```
python3 scripts/load_drive.py prepass --state build-state.json --map <mapping.json> \
        --contacts-csv <file[#tab]> --ledger ledger/companies.jsonl --dry-run [--create]
```

Run it `--dry-run` first: it resolves and reports, and writes nothing.

| Where the company is | What happens |
|---|---|
| In the companies file | already in the ledger from Step 6. Nothing to do |
| **Already in the table** | found by its match key and used. **Always on** — it is a free read, nothing about the company is modified, and the only write is `company_id` on the contact |
| **In neither** | created **only if they said yes at Step 4**, from the contact's own match key |
| Nothing to identify it by | the contact loads unlinked, and the count is reported |

**The key is not necessarily a domain.** A company matches on `domain` *or* `linkedin_url`, so this
resolves whichever the contact can supply, in that order: a company-domain column, a
company-LinkedIn column, then the work email's domain. **A free mailbox is never a company** — a
contact at a personal address yields nothing, because it says nothing about where they work, and one
webmail "company" with forty contacts hanging off it is worse than forty unlinked contacts, since it
looks like it worked.

**A company name is deliberately not a source.** Nothing can be keyed on one, and matching on a name
that is not unique attaches a contact to the wrong company, which is the silent wrongness this whole
skill refuses.

**One read for every distinct company, never one per contact.** A thousand contacts at one company
cost nothing extra.

Everything it resolves is appended to the **company ledger**, under the key the contacts load looks
up, and stamped `created_from`: `table` when it was already there, `contact` when this step made it.
So the contacts phase needs no new logic, a re-run never repeats the work, and the delivery report
can say exactly which companies are thin and why. A company created here is always named — with the
contact's company name where there is one, else its match key.

## Step 7 — Load the contacts against the company ids

**This is the step the whole skill exists for, so here is exactly what happens, in order.** It is
spelled out because every part of it is invisible when it goes wrong: a misconfigured link loads
every contact successfully, with no company attached, and reports success end to end.

1. **Read the company ledger.** Every company line carries the `id` its upsert returned, in
   `entity_id`. Fold the file into a map of **company row key → company `id`**, keeping only
   `completed` lines. This is a local file read — nothing is looked up again.
2. **For each contact, take the value in the company-reference column** — the contacts column
   confirmed at Step 1 as `company_ref_column` — and look it up in that map.
3. **That lookup returns the company's `id`**, an integer like `42`. It is not a domain, not a name,
   and not the company's row key.
4. **Put that id in `company_id`** on the contact's row. That single column is the entire company
   link, and the foreign key means it can only ever point at a company that exists.
5. **A contact whose lookup returned nothing gets `company_id` NULL**, stamped `associated: false` in
   the ledger with the reason. The link's absence is explicit and queryable — `where company_id is
   null` — rather than inferred.

```
company ledger        {"row_key": "NW-001", "status": "completed", "entity_id": 42}
                                  │
contacts CSV          company_id = "NW-001"  ─────┘
                                  │
contact row           company_id = 42   (REFERENCES storage.<prefix>_companies(id))
```

**The two keys either side of that lookup have to be the same key.** The company row key and the
contacts company-reference column are joined by string equality and nothing else — no normalising,
no fuzzy match. If the companies file is keyed on `company_id` and the contacts file references
companies by name, **nothing resolves and every contact loads unlinked.**

So the driver counts the resolution before it writes anything and prints it:

```
company ids folded from the ledger: 16 of 17 settled company rows
contacts in this pass that resolve to a company: 28 of 29, via 'company_id'
```

**If that second number is zero it stops**, shows both key spaces side by side, and refuses to
load — because loading a whole file unlinked is not a mistake worth making quietly. Continue only
with `--allow-all-unlinked`, and only for a TAM that genuinely has no company links.

There is no second file to build and no join step: a company that settled since the last pass is
picked up by the next one.

```
python3 scripts/load_drive.py --entity contacts --state build-state.json \
        --csv <path> --map <mapping.json> --ledger ledger/contacts.jsonl \
        --company-ledger ledger/companies.jsonl
```

## Step 8 — Verify against the table, not against the ledger

The ledger says what was sent. This step asks the table what it holds.

```
python3 scripts/load_drive.py verify --state build-state.json --map <mapping.json> \
        --csv <companies file[#tab]>          --ledger ledger/companies.jsonl \
        --contacts-csv <contacts file[#tab]>  --contacts-ledger ledger/contacts.jsonl
```

Per column, what should have landed against what the table says this load's own rows hold:
`select count("<column>") from storage.<prefix>_<entity> where id = any(<the ids in the ledger>)`.

**Each ledger needs its file too** — the command takes `--csv` with `--ledger` and `--contacts-csv`
with `--contacts-ledger`, because the expected count is derived from the file. Passing a ledger
alone verifies nothing, and the step refuses rather than printing a pass.

**Scoped to the ids in the ledger, never to the table.** This is the correction that matters most in
the whole step, and it shipped wrong in the version this was ported from: a store-wide count returned
17 where the load had written 5, the pass test was `got >= want`, and every field passed — including
fields the load had not written at all. On an empty table it looks right, which is how it survived.
**A row of the verification table where the two numbers differ is a column that did not land.**
Report it as a discrepancy with the column and both numbers; never reconcile it by preferring the
ledger. On Postgres the usual causes are a value dropped at load time that Step 3 should have caught,
or a row that matched an existing one and kept that row's older value.

**Booleans are checked like everything else.** Postgres keeps `false` and NULL apart, so
`count(col)` counts the rows that carry a value. (On Clay Audiences, measured 2026, they could not
be told apart — that caveat does not apply here.)

**The company link is checked as `count(company_id)`** over this load's contacts, against how many
the ledger says were associated.

## Step 9 — Deliver

Hand over three things and say what each is for: the coverage report from Step 3, the verification
table from Step 8, and the ledger files. Say plainly what was loaded, what was refused and why, how
many contacts are unlinked, and the exact command that resumes if anything is still outstanding.

**If any companies were created from a contact, hand back that list too** — they carry a match key
and a name and none of the attributes the companies file would have given them, and they are
indistinguishable from the rest in a list. The ledger has them under `created_from: contact`, and
the table has them as `select * from storage.<prefix>_companies where id = any(…)`.

**Then the loader, as something to keep.** The two tables, `build-state.json`, the mapping and the
ledgers are a working loader for this TAM: next quarter's file is a `build` (which adds only new
columns) and two driver runs, and every row already settled is skipped. Show one query they can run
straight away, so the table is something they use rather than something they were told about:

```
deepline db query --sql "select c.org_name, count(p.id) as contacts from storage.<prefix>_companies c left join storage.<prefix>_contacts p on p.company_id = c.id group by 1 order by 2 desc limit 20" --format markdown
```

## Representative output

### Pre-load coverage report

| | Companies | Contacts |
|---|---|---|
| Rows in file | 4,180 | 26,402 |
| Loadable | 4,061 | 24,918 |
| No match key | 119 | 1,484 |
| Duplicate row key | 0 | 12 |
| Sharing a match key with another row | 46 rows -> 21 records | 8 rows -> 4 records |
| Values that are not that kind of key | `linkedin_url` 7 | `email` 31 |
| **Company link** | — | **ok — 24,306 of 24,918 resolve via `company_id`** |
| Company reference not in the companies file | — | 612, of which 588 carry a domain to go on |
| Values their column's type will not parse | `employee_count` 338 of 4,180 (`1,001-5,000`, `~250`) | `tenure_years` 0 |

**The company-link row is the one to read twice.** `NOT CONFIGURED`, `COLUMN NOT IN FILE` or
`NOTHING RESOLVES` there means every contact would load with no company attached while every row
reported success, and the load refuses to start.

### Resolving the companies contacts reference but the file does not have

```
contacts referencing a company not in the companies table: 612, across 74 distinct companies
contacts with nothing to identify a company by: 24
  domain         northwind.example                             42
  domain         contoso.example                               would create
  linkedin_url   linkedin.com/company/fabrikam                 would create

already in the table: 41   would be created: 33
```

### Post-load verification

`Expected` is the number of distinct rows that should carry the column: rows that settled, minus
values dropped at load time, and counting rows that collapsed onto one record once.

| Field | Entity | Type | Expected | In your load | |
|---|---|---|---|---|---|
| `company_name` | companies | text | 4,040 | 4,040 | ok |
| `website` | companies | url | 4,040 | 4,040 | ok |
| `employee_count` | companies | text | 4,040 | 4,040 | ok |
| `founded` | companies | date | 2,904 | 2,821 | **SHORT BY 83** |
| `expansion_signal` | companies | boolean | 2,904 | 2,904 | ok |
| `title` | contacts | text | 24,918 | 24,918 | ok |
| Linked to a company | contacts | — | 24,882 | 24,882 | ok |

A short row is the whole reason this table exists. It does not mean rows went missing — the ledger
already accounted for those. It means rows settled without that column's value: usually a row that
matched one already in the table and kept its older value, or a value dropped at load time. Name the
column and both numbers, and look at the ledger's `dropped_fields` for those rows before acting.

### Refused, by reason

| | Companies | Contacts |
|---|---|---|
| `rejected_no_match_key` | 119 | 1,484 |
| `rejected_duplicate_row_key` | 0 | 12 |
| Loaded without a company attached | — | 36 (`no_company_reference` 24, `company_not_in_company_ledger` 12) |
| Created from a contact, carrying only a match key and a name | 31 | — |

### Ledger line

```
{"row_key":"northwind","status":"completed","entity_id":42,
 "match_key":"domain","match_value":"northwind.example","associated":null,
 "link_source":null,"unlinked_reason":null,"dropped_fields":["employee_count"],
 "reason":"","at":"2026-05-04T11:02:19Z"}
```

`link_source` is where the contact's company came from — `company_table`, `already_in_table` or
`created_from_contact` — and on a company line the pre-pass writes `created_from` instead, either
`table` or `contact`. Between them, "why does this contact have no company" and "which of these
companies are thin" are both answerable from the ledger alone.

## What this skill does not claim

- The silent-write behaviour that motivates it was measured on Clay Audiences, on one workspace on
  one day, across a number field and a date field. On the Deepline customer DB a typed column refuses
  an unparseable value instead; that is Postgres behaviour, verified only in that the customer DB
  reports PostgreSQL 16 with `standard_conforming_strings = on`.
- **No write against the customer DB has been run by this port.** The upsert, `RETURNING`, the
  foreign key and `ADD COLUMN IF NOT EXISTS` are standard Postgres and the CLI documents that it
  accepts CREATE, INSERT and ALTER on `storage.*` tables; whether `RETURNING` rows come back through
  `deepline db query` is untested. If they do not, nothing settles and every row stays `failed` —
  safe, and the first ten-row batch shows it.
- Nothing here has been run at TAM scale. The batch size and pace are unmeasured defaults.
- `query_customer_db` is listed as `Free` per call in the tool catalogue. That is not a claim that a
  large load is free; it is why the skill reads the balance itself rather than quoting that line.
- The match-key shape rules (a `linkedin.com` host, a parseable email, a phone with digits) were
  established on Clay Audiences by reading its refusals. A Postgres table would accept any of them;
  the loader keeps the screen so `match_key` means what it says, and may refuse a value some other
  system would take.
- The verification counts a column as landed if one of this load's rows carries it. Where a row
  already existed and already had that column, it is counted even if this load's value was dropped —
  so the check is a floor on what landed, not proof that every value did.
- Whether two rows genuinely are the same company is not something this skill decides. It counts the
  collisions its match key produces and shows them; the judgement is the installer's.

## What good looks like

Every row in every table you were given reaches one of six verdicts and none is `unknown`: loaded;
loaded without a company attached; refused for carrying no match key; refused as a second row with a
row key already seen; held because its company never loaded; or still outstanding with a named
reason. The counts add up to the row count of the table — a run where they do not has lost rows
somewhere and the load is not finished.

The verification table at Step 8 is the actual test, and a good run is one where every row of it
matches. **A run that loads every record and comes back with two columns short is a failed run that
looks like a successful one** — which is the whole reason that table exists and the reason it is
built from the table's counts rather than the loader's.

A second run over the same files writes nothing new, reports every row already settled, and the row
counts in the tables do not move. If a re-run creates rows, the row key and the match key have come
apart and the load should stop until that is understood.

A thin run states its thinness: if most of a file carries no match key, the honest outcome is to say
so with the number and stop, not to load the remainder quietly and report a success.

## Rules

- **NEVER** write into a column the installer did not confirm at Step 1.
- **NEVER** send a value its column cannot parse. One such value fails every row in its batch; drop
  it, name it in `dropped_fields`, and report it.
- **NEVER** retype a column to `text` to make a load error go away without saying what it costs:
  numeric and date filters on that column stop meaning anything.
- **NEVER** splice a value into SQL except through the loader's literal escaping. Every value in a
  TAM file is somebody else's text; quotes are doubled, NUL bytes refused, identifiers checked.
- **NEVER** write a row whose match value is not that kind of key. Screen locally and fall through to
  the next key in the order.
- **NEVER** treat `failed` as settled, and never edit anything before retrying one — unless its
  `reason` names a type error, which is a Step 3 fix.
- **NEVER** hold verdicts past their batch. A batch returns, its lines are appended, then the next.
- **NEVER** merge two existing rows, delete one, or empty a column. Attaching a contact to a company
  already in the table is not merging — it is an exact lookup on `match_key` — but deciding two rows
  are "probably the same" is, and this skill does not do it. Where the load would collapse two of
  your rows onto one, say so before writing.
- **NEVER** infer that a contact belongs to a company because it carries the company's domain. The
  link is `company_id` and nothing else establishes it.
- **NEVER** load a contacts file when nothing in it resolves to a company. That is a misconfigured
  join, not a TAM without companies, and it is indistinguishable from success afterwards. Stop, show
  both key spaces, and let the installer say which is wrong.
- **NEVER** report a load as complete on the ledger alone. The ledger says what was sent; only the
  table says what it holds. And **never report a verification that compared nothing, or that
  compared the wrong population** — both have shipped. Scope to the ids the ledger recorded.
- **NEVER** turn a repeated failure into a claim about how the platform works without bisecting it
  first. Report it unexplained instead; an invented rule sends the next person to fabricate data.
- **NEVER** write outside `storage.<prefix>_companies` and `storage.<prefix>_contacts`, and never
  drop a table except a trial prefix the installer named as one.
- **NEVER** ask for a credential, a login, or a sharing change to reach the data. If it cannot be
  read from disk, name the export that makes it readable and stop.
- **NEVER** pass a spreadsheet's raw date serial through as a value. A date cell read without its
  format is a five-digit integer that passes a numeric check and means nothing in the table.
- **NEVER** add a column for a file column the table already has a column for, without showing the
  match first. Read both lists and match them yourself; do not wait for a script to assert a
  similarity it cannot see. And **never reuse a column whose stored type disagrees with the mapping**.
- **ALWAYS** state which values came from a default and that the default is borrowed.

## Worked example

Someone opens with *"load my TAM into Deepline"* and nothing else. Step 0 says what the next few
minutes look like in four short paragraphs — read the files, show the columns, count what cannot
load, one approval, then the load and a check at the end — names the two tables it will create, and
then asks for the files, because none were given. They point at two exports from a TAM built in a
model conversation: 4,180 companies and 26,402 contacts.

They are one Excel workbook with a tab each, so Step 1 lists the tabs, proposes which is which,
reads both, and proposes eleven of the forty-three company columns — `company_id` as the row key,
`company_key` as the column pointing a contact at its company, and `headcount` as **text**, because
one value two thousand rows down reads `1,001-5,000` and one bad value demotes the whole column.

Then it lays those columns beside what `storage.tam_companies` already holds from last quarter's
load. `company_name` is the same label as `company_name`, so that one is asserted. The rest are
matched by reading them: `website` carries `https://` values and belongs in `domain`, `hq_city`
belongs in `location_city`, `job_title` belongs in `title`. Each is shown with its reasoning and
none is applied until the installer says so, so eleven columns become five reused and six new ones
rather than eleven new columns beside the ones that already meant the same thing.

The installer overrides `headcount` to `number`, which is the reasonable thing to think: a headcount
is a number. Step 3 is what makes that survivable. It reports 338 values a numeric column will not
parse, shows two of them, and the installer chooses: keep it numeric and let those 338 be dropped
and named, so `> 100` works on the other 3,842 — or text, and give up numeric filtering. They keep
it numeric. Nobody finds out on batch nine that one band failed two hundred rows.

Step 3 also reports 119 companies with neither a domain nor a LinkedIn URL, which cannot be loaded
at all, and 46 rows sharing a domain with another row, which will become 21 records. The installer
accepts both with the numbers in front of them.

The gate names the workspace, 4,061 companies, 24,918 contacts, the eight new company columns and
two new contact columns to be added, that this writes rows into the customer DB, and the balance
before. Yes. The columns are added, ten companies load, and their verification matches on every
column, so the rest follow without a second stop.

Companies settle into the ledger with their ids. Before the contacts run, the pre-pass takes the 612
contacts whose company is not in the companies file and resolves the 74 distinct companies behind
them: 41 are already in the table and get used, 31 are nowhere and get created because the installer
said yes at the gate, and 2 cannot be identified at all. The 31 created carry a domain and a name and
nothing else, and the delivery report says so and hands back the list.

The contact phase then folds that ledger into a map and links 24,882 of 24,918. Step 8 asks the
table for the populated count per column, one row comes back 83 short and is reported as a
discrepancy rather than reconciled away, and the run is finished — 119 companies and 1,484 contacts
refused, each with its reason and its count, and the balance after beside the balance before.
