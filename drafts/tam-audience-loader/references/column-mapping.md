# Columns, types, and the value that cannot land

## Where the data can live

Two tables are needed, one of companies and one of people. **A table is not necessarily a CSV**, and
every command takes `FILE` or `FILE#TAB`:

| Shape | How to point at it |
|---|---|
| Two CSV or TSV files | `--companies companies.csv --contacts contacts.csv` |
| One `.xlsx` workbook, a tab each | `--companies 'book.xlsx#Companies' --contacts 'book.xlsx#People'` |
| A Google Sheet | not readable from here — it needs credentials this skill does not take and must never ask for. File → Download → Comma-separated values, once per tab. An agent with a Drive connector can fetch them instead |
| An old `.xls` | Save As `.xlsx` first, or export each tab |

`loader_lib.py sheets --companies <book.xlsx>` lists the tabs and proposes which is which, so a
workbook is shown mapped rather than interrogated.

**The `.xlsx` reader uses only the standard library** — an `.xlsx` is a zip of XML — because the
installer may have neither openpyxl nor pandas, and a loader that cannot open the file it was
pointed at is no loader.

**A spreadsheet stores a date as a number of days since 1899-12-30.** Read without its cell format
it is a plausible five-digit integer: `2011-04-02` arrives as `40635`, passes a numeric check, and
lands in the table as nonsense — the same silent wrongness as a band in a number field, through a new
door. Date-formatted cells are converted to ISO on read. If a date column ever shows a bare
five-digit number, that conversion did not happen and the load should stop rather than continue.

## The six types, and what each is stored as

Each confirmed column becomes a column on `storage.<prefix>_companies` or
`storage.<prefix>_contacts` in the Deepline customer DB (Postgres), added by `build_loader.py build`
with `ALTER TABLE … ADD COLUMN IF NOT EXISTS`.

| Loader type | Stored as | The loader also checks |
|---|---|---|
| `text` | `text` | nothing |
| `number` | `numeric` | it is a plain number once thousands separators are stripped |
| `email` | `text` | exactly one `@`, a dot after it, no spaces |
| `url` | `text` | it starts `http://` or `https://` |
| `date` | `date` | it is a real calendar day as ISO, `M/D/YYYY` or `YYYY/M/D`; written as ISO |
| `boolean` | `boolean` | it is one of a recognised true/false pair; written as `true` / `false` |

**There is no list type worth using here.** A column holding `SaaS; Fintech; Payments` becomes one
`text` column. It can be matched with `LIKE` or `ILIKE`; it cannot be counted or faceted without
splitting it in SQL. Say that while the mapping is on screen, not afterwards — an installer who knows
will often split the column into three booleans instead, and that decision is cheapest before the
columns exist.

**Column names come from the mapping**: the `field_id` when it names an existing column, else the
`field_name` folded to snake case (`TAM ICP tier` → `tam_icp_tier`). Anything that is not a plain
lower-case identifier is refused, because a mapping file is input.

## The failure this whole page exists for

**On Clay Audiences** (measured on one workspace, 2026), a value the field's declared type could not
parse was **accepted, acknowledged, stored verbatim, and invisible to every query**: `1,001-5,000` in
a number field and `Q3 2017` in a date field both wrote `✅ Success` and then matched no filter.

**On the customer DB the same value fails the other way, loudly.** A typed Postgres column refuses a
value it cannot parse, and it refuses the whole statement: one `1,001-5,000` in a `numeric` column
and every row in that batch's INSERT fails with it. Loud is better than silent, but it has its own
quiet failure, and it is the one people reach for to make the error go away:

| What you do | What happens | What the table says afterwards |
|---|---|---|
| send `1,001-5,000` into `numeric` | the whole batch fails | nothing from that batch landed |
| retype the column `text` so it loads | every value loads | `employee_count > '100'` compares strings: `'88'` sorts above `'512'`, and `> 100` without quotes is a type error |
| drop the bad value and keep `numeric` | the row loads without it | the column is filterable and the gap is named in the ledger |

### What follows

- **Check every value against its column's type before the load**, and report per column: how many
  values fail, and two of them. That is the only cheap moment.
- **A column where many values fail is usually a bad inference, not bad data.** Offer `text`, and say
  what it costs: no numeric comparison on that column.
- **A value that still fails at load time is dropped and named** in the row's `dropped_fields`, never
  sent — sent, it would take its whole batch down with it.
- **After the load, ask the table for the populated count per field**, scoped to the ids this load
  wrote, and hold it against the count the file carried. That is the completion test, and the reason
  Step 8 exists.

## Inferring a type from a column

The inference is a proposal, and the two sample values shown beside it are what makes it
correctable. It is deliberately conservative — **`text` is the fallback, and falling back is not a
failure.** A text field that holds everything beats a number field that silently holds nothing.

| Proposed | When | The trap it walks into |
|---|---|---|
| `number` | every non-blank value parses as a number after stripping thousands separators | a band (`1,001-5,000`), an approximation (`~250`), a range, or a trailing unit further down the file |
| `date` | every non-blank value parses as a date | a quarter (`Q3 2017`), a year alone, `TBD`, or two formats mixed in one column |
| `email` | every non-blank value contains exactly one `@` | several addresses in one cell |
| `url` | every non-blank value starts `http://` or `https://` | a bare domain with no scheme, which is a fine `text` value and a bad `url` one |
| `boolean` | every non-blank value is in one recognised pair | a third value — `unknown`, `n/a` — turning a boolean into a three-state column |
| `text` | anything else | nothing. This is the safe one |

**Sample from the whole file, never from the first rows.** Export order is rarely random and the
well-formed rows are usually at the top. The inference in `scripts/loader_lib.py` reads every
non-blank value in the column, because reading the whole file is cheap and being wrong is not.

**Every value is sent as a quoted literal and the column does the cast.** `'512'` into a `numeric`
column is the number 512. The loader only has to make sure the value is one the column can parse,
and write it in that column's form: separators stripped, dates as ISO, booleans as `true`/`false`.

## A boolean is fine here

On Clay Audiences (measured 2026) a boolean could not be coverage-checked: `= false` also matched
every record the field was never set on. Postgres keeps `false` and `NULL` apart, so on the customer
DB `count(col)` counts the rows that carry a value and `col is false` counts the explicit falses. A
boolean is checked at Step 8 like every other column.

## Blank is a value, and which kind of blank matters

| | Blank **match key** | Blank **field** |
|---|---|---|
| What happens | the row cannot be loaded; it is screened out as `rejected_no_match_key` and never sent | the column is left out of that row's INSERT; on a new record it is NULL, on an existing one the upsert keeps the value already there (`COALESCE(EXCLUDED.c, t.c)`) |
| So | count these at Step 3, before anything is written | a sparse column is harmless, and a re-load never empties a field |

**And a match key is checked for being that KIND of thing, not merely for being non-empty.** A
malformed email, a phone with no digits, and a LinkedIn URL whose host is not `linkedin.com` are
refused locally (the same three were measured as refused by Clay Audiences' upsert, 2026). A
`.example` domain and a `.example` email address are both accepted, so this is not a check on whether
the thing is real. Screen the shape before writing, and fall through to the next key rather than
losing the row.

## The row key, and minting one

The row key identifies a row in your file and in the ledger, and joins a contact to its company. It
is **not** the key the upsert matches on (`match_key`), and it never can be.

Prefer, in order:

1. **A stable id column the file already carries** — a CRM id, an internal account id. Best, because
   it survives re-exports that reorder or reword everything else.
2. **The domain**, normalised: lowercased, scheme and `www.` stripped, trailing slash removed.
3. **A minted slug of the company name**, normalised: lowercased, accents folded, punctuation and
   legal suffixes removed, whitespace collapsed to single hyphens.

Minting from the name is a real answer for a file that has nothing else, and it has a real cost
worth stating when you use it: two genuinely different companies with the same name collapse, and a
company that gets renamed between exports becomes a new row. **Say which rule produced the key**, so
that a re-run with a differently-shaped export is recognisable as the different thing it is.

**Row keys must be unique within a file.** Two rows with the same row key is a file problem, not a
match-key problem, and the check reports it as its own count rather than folding it in with the match-key
collisions — they have different causes and different fixes.
