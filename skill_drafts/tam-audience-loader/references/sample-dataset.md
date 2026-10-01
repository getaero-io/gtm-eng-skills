# The shipped sample, end to end

Three files ship beside this one so the skill can be exercised before anyone points it at real
data: `references/sample-companies.csv` (18 rows), `references/sample-contacts.csv` (32 rows) and
`references/sample-mapping.json`.

They are shaped like a TAM a model actually produces: a handful of columns that land in the tables' base
columns, a pile of research columns that become new ones, and values that are *nearly* well-formed. **Every
defect in them is deliberate**, and the point of the walkthrough below is that each one is caught
at a different step, by a different check, with a different remedy.

Nothing here resolves to a real company. Every domain is under `.example`. The LinkedIn URLs use
the real `linkedin.com` host because the loader will not accept anything else as a match key — see
below, it is one of the findings.

## What is in the files

**Companies — 27 columns.** Six map onto standard columns (`company_name`, `website`,
`linkedin_company_url`, `hq_city`, `hq_country`, `employee_count`). Ten are research columns that
get a `tam_` column of their own (`icp_tier`, `fit_score`, `why_now`, `buying_trigger`, `tech_stack_detected`,
`last_funding_stage`, `last_funding_date`, `funding_raised_usd`, `net_new_arr_potential`,
`expansion_signal`). **Eleven are left out of the mapping entirely** — `compliance_regime`,
`procurement_model`, `pricing_page_url`, `renewal_month`, `owner_email`, `confidence`,
`sourced_from`, `research_notes`, `analyst_coverage`, `founded`, `hq_*` duplicates — because a TAM
export carries far more than belongs in the table and the default is to leave a column out.

**Contacts — 21 columns.** Eight map onto standard columns, six get new ones, seven are left out.

## The nine planted defects, and where each one is caught

| # | Where | What | Caught by |
|---|---|---|---|
| 1 | `CT-002`, `VC-013` | `1,001-5,000` and `~2,500` in a headcount column | Step 1 infers `text`; Step 3 counts them if you override to `number` |
| 2 | `TS-004` | `Q3 2024` where every other funding date is ISO | same |
| 3 | `FB-003` | `03/15/2024` — one US-format date in an ISO column | Step 1 infers `text` |
| 4 | `FB-003`, `PS-009` | `$8,500,000` and `€8.5M` in a funding amount | Step 3 coercion count |
| 5 | `TS-004` | `unknown` in an otherwise true/false column | Step 3 coercion count |
| 6 | `LW-006` | no website and no LinkedIn URL | Step 3 `no match key` — cannot be loaded at all |
| 7 | `FC-010` | a LinkedIn URL whose host is not `linkedin.com` | Step 3 `values that are not that kind of key`; falls through to its domain and still loads |
| 8 | `NW-001` / `NW-007` | two rows, one domain in different case with a trailing slash | Step 3 collision count — two rows, one record |
| 9 | `NW-001` twice, `P-0001` twice | the same row key exported twice | Step 3 `duplicate row key` |

On the contacts side: `P-0005` carries no email, LinkedIn or phone; `P-0010` carries a LinkedIn URL
on the wrong host and nothing else, so he is unloadable **for a different reason**; `P-0004` points
at a company id that is not in the companies file; `P-0023` and `P-0032` are distinct people the
research pass gave the same email, so they collapse onto one record; `~3` sits in a years-in-role
column and `Q1 2025` in a job-change column; `mobile_phone` is blank on every row, so the phone
match key never claims anything.

`tech_stack_detected` and `conferences_attended` hold several values per cell. **There is no list
type**, so they land as one text column each — matchable with `ILIKE`, never countable without splitting.

## Step 1 — what `inspect` says

```
python3 scripts/loader_lib.py inspect --companies references/sample-companies.csv \
                                      --contacts references/sample-contacts.csv
```

The interesting rows, and every one of them is the inference refusing to be clever:

```
column                       type      blank   two values
website                      url       2       https://northwind.example | https://contoso.example
employee_count               text      0       512 | 1,001-5,000
fit_score                    number    0       92 | 88
last_funding_date            text      6       2024-03-01 | 03/15/2024
funding_raised_usd           text      6       48000000 | $8,500,000
expansion_signal             text      0       true | true
analyst_coverage             boolean   0       yes | yes
  proposed, correct any of these:
    row_key_column       company_id
    domain_column        website
    name_column          company_name
```

**`employee_count` comes back as `text` and that is the whole lesson.** The first value is `512`
and the fifty-first is a band; reading the column rather than its first rows is what keeps it out
of a numeric column. Same for `last_funding_date` and `funding_raised_usd`. Note `expansion_signal`
reads as `text` — because one row says `unknown` — while `analyst_coverage` beside it is a clean
`boolean`.

The three proposals are worth reading closely, because each had to be taught not to guess
confidently: `pricing_page_url` beat `website` for "the domain" on the token `url`; `company_id`
beat `company_name` for "the name" on `company`; and on the contacts side `contact_id` beat
`company_key` for "the company this contact belongs to" on `id`. All three were wrong and all three
read as if the file had been understood.

## Step 3 — what `check` says, on the shipped mapping

**`sample-mapping.json` is deliberately the installer's FIRST attempt, not the corrected one.**
Four columns in it are typed the way a reasonable person types them on sight — a headcount is a
number, a funding date is a date — rather than the way the data actually reads. So the report has
something to say:

```
python3 scripts/loader_lib.py check --companies references/sample-companies.csv \
        --contacts references/sample-contacts.csv --map references/sample-mapping.json
```

```
companies — 18 rows, 16 loadable
  no match key ............. 1
  duplicate row key ........ 1
  sharing a match key ...... 2 rows into 1 records
  matched by ............... {'domain': 15, 'linkedin_url': 1}
  values that are not that kind of key — present, and refused like a blank:
    linkedin_url             1   e.g. https://www.linkedin.example/company/fourth-coffee
  values their type cannot parse — sent, each one fails its whole batch:
    employee_count           number  2 of 16 carried   e.g. 1,001-5,000, ~2,500
    last_funding_date        date  1 of 10 carried   e.g. Q3 2024
    funding_raised_usd       number  2 of 10 carried   e.g. $8,500,000, €8.5M
    expansion_signal         boolean  1 of 16 carried   e.g. unknown
```

Four counts, four different remedies, and the last block is the one to act on: move those columns
to `text` (and lose numeric comparison on them), or keep the type and let those values be dropped
and named. Sent as they are, each one would fail the whole batch it rode in.

## Step 5 — creating the tables and columns

**Dry run first.** It runs nothing and prints every statement it would run:

```
python3 scripts/build_loader.py build --prefix tam --map references/sample-mapping.json --dry-run
```

```
storage.tam_companies: 13 column(s) would be added, 3 already there
storage.tam_contacts: 12 column(s) would be added, 2 already there
  CREATE TABLE IF NOT EXISTS storage.tam_companies (id bigserial PRIMARY KEY, match_key text NOT NULL UNIQUE, "row_key" text, "domain" text, "linkedin_url" text, "org_name" text)
  ALTER TABLE storage.tam_companies ADD COLUMN IF NOT EXISTS "employee_count" numeric
  ALTER TABLE storage.tam_companies ADD COLUMN IF NOT EXISTS "tam_icp_tier" text
  …
  CREATE TABLE IF NOT EXISTS storage.tam_contacts (id bigserial PRIMARY KEY, match_key text NOT NULL UNIQUE, "row_key" text, "email" text, "linkedin_url" text, "phone" text, company_id bigint REFERENCES storage.tam_companies(id))
  ALTER TABLE storage.tam_contacts ADD COLUMN IF NOT EXISTS "tam_persona" text
  …
```

**"Already there" on a dry run counts only the base columns** (`domain`, `linkedin_url`, `org_name`
on companies; `email`, `linkedin_url` on contacts), because a dry run reads nothing. The real build
reads `information_schema.columns` first, adopts every same-named column, and refuses one whose
stored type disagrees with the mapping.

Note `employee_count numeric` above: the shipped mapping is the first attempt, and that is the
mistyping Step 3 flagged. Fix the mapping before the real build, or the column is created numeric
and the two bands are dropped at load time.

Then, for real, on a copy of the mapping:

```
python3 scripts/build_loader.py build --prefix tam --map <your copy> --out build-state.json
```

## What a full load of this sample does

18 companies: **16 load**, 1 is refused for carrying no match key, 1 for a duplicate row key. Two of
the 16 — `NW-001` and `NW-007` — come back with **the same `id`**, which is the domain
collision the report predicted, visible in the ledger rather than inferred.

32 contacts: **29 load**, 2 refused for no usable match key, 1 for a duplicate row key. `P-0032`
comes back with `P-0023`'s `id`. 15 company ids are folded out of the company ledger, and the
contacts whose company never loaded — `P-0007`, whose employer is `LW-006` — load with no company
attached and are stamped `associated: false`.

## Three things this sample taught that nothing else did

**A match key is validated for shape, not just for being non-empty.** `WG-005` has no website, so
it must match on its LinkedIn URL — and with a `.example` host, Clay Audiences' upsert refused it
(measured 2026) with *"None of the selected lookup fields contained a valid value to match on"*,
which reads exactly like the field was blank. A malformed email and a phone with no digits failed
identically, while a `.example` **domain** and a `.example` **email address** were both accepted. A
Postgres table would store any of them; the loader keeps the same screen so that `match_key` means
what it says, and falls through to the next key, which is why `FC-010` still loads on its domain.

**A boolean that is really three-valued is text.** `expansion_signal` carries `unknown` on one row.
Postgres keeps `false` and NULL apart, so a boolean column is checkable here — but `unknown` is
neither, and dropping it loses the one thing the research pass was trying to say. Text with explicit
values keeps all three.

**A day-first date is not a date here.** `03/15/2024` reads as March 15 under the database's
month-first default; `15/03/2024` would fail the whole batch. The loader parses slashed dates
month-first and refuses anything that is not a real day under that reading, before the INSERT.

## Cleaning up after a trial run

Everything a trial creates lives in two tables, and the customer DB lets you drop them:

```
deepline db query --sql "drop table storage.tam_contacts"
deepline db query --sql "drop table storage.tam_companies"
```

Contacts first, because of the foreign key. Use a throwaway `--prefix` for the trial
(`--prefix tamtrial`) so that dropping it can never touch a real load, and prefer `--limit 10` on
the first pass.
