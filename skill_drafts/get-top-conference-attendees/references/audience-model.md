# What lands in the customer DB, and why each column has the type it has

## The shape

Two tables in the Deepline customer DB (Postgres), both under the `storage` schema — the only
schema `deepline db query` lets an agent write:

- **`storage.conference_attendees`** — one row per attendee per campaign, primary key
  `(campaign_id, person_key)`. `person_key` is the LinkedIn URL, else `email:` plus the
  lower-cased email.
- **`storage.conference_companies`** — one row per company domain, primary key `domain`.

An attendee is linked to their company by `company_domain` on their own row. Not a table to
look at once: real typed columns, so the list can be filtered, segmented, joined to anything
else in the customer DB, and re-used after the conference is over.

## People

Identity columns, all text: `campaign_id`, `person_key`, `match_key` (`linkedin_url` or
`email`), `name`, `first_name`, `last_name`, `title`, `email`, `linkedin_url`, `phone`,
`company_name`, `company_domain`. Plus these — the column name is the snake_case source key in
`scripts/audience_lib.py` (`PEOPLE_FIELDS`), and the display name is what the report prints:

| Display name | Type | Holds |
|---|---|---|
| Conference | text | the event's name, as the lookup verified it |
| Conference start | date | first day, ISO |
| Conference location | text | city as given |
| Conference campaign id | text | which run produced this record |
| Attendee record id | text | the service's own id for this person |
| Attendee tier | text | S / A / B / C / F — **read from the flat response format, not the dossier** |
| Attendee score | numeric | the rubric score |
| Attendee rank | numeric | position in the ranked list |
| Attendance confidence | text | confirmed, or likely |
| Attendance evidence | text | why they are believed to be going |
| Attendance source | text | the page that evidence came from |
| Dossier state | text | enriched / ranked_only / queued / failed / unranked |
| Dossier headline | text | the one-line read on them |
| Dossier summary | text | the paragraph on the person |
| Their company | text | the paragraph on the company |
| Why they score | text | the rubric's own rationale |
| Buying signals | text | the list, joined |
| Conversation openers | text | the list, joined |
| Value prop | text | what to lead with |
| Dossier written at | date | when this skill wrote the row |

**Tier is the one column that cannot be read from the same response as the rest.** Measured
against a live campaign: no contact in the rich format carries a tier under any key, while the
flat projection has one for every contact (S 17, A 15, B 18, C 73, F 21 across 144 people —
reconciling exactly with the campaign's own locked block). So both formats are read and merged
on identity. A client that reads only the documented one writes a permanently empty tier
column and reports success.

## Companies

`domain` and `org_name`, plus `conference_name`, `campaign_id`, `attending_flag` (text,
`yes`) and `written_at`. A company seen at two conferences is one row; its conference columns
carry the latest campaign written.

## Why the types are what they are

**`score` and `rank` are the only numbers, and they are validated before they are sent.** A
Postgres `numeric` column refuses `80-90` — and refuses it for the whole multi-row statement,
so one bad score would unsettle a hundred attendees. So a score that arrives as a range or as
prose is **dropped and named as dropped**, and the rest of the row is written. (In Clay
Audiences, where this skill was first built, the same value was worse: accepted, echoed back,
and invisible to every filter. The check is the same either way.)

**Nothing is a boolean, and `attending_flag` is text holding `yes`.** A boolean invites
`= false` queries that quietly conflate "explicitly false" with "never set"; text with
explicit values keeps the difference visible.

**`Dossier state` is text with five values rather than a flag.** `enriched`, `ranked_only`,
`queued`, `failed`, `unranked` are five different facts, and only one of them means "we have
their dossier". Collapsing them into "has a dossier: no" makes every rate you would want —
what the free allowance actually covered, what failed, what is still running — impossible to
compute after the fact.

**Both date fields are real `date` columns.** So "everyone we researched in the last 30
days" is `written_at >= current_date - 30`, not string surgery. A date that does not parse
(`2026-13-45`, `Q3 2026`) is dropped and named before the write, for the same reason as the
score.

**Every one of those columns is filled from a key the service actually returns, which is not
the key its documentation names.** Measured: the real dossier shares exactly ONE key
(`buying_signals`) with the published shape. `summary` is `contact_summary`, `openers` is
`conversation_openers`, `value_prop` is `value_prop_framing`, `company_history` is
`company_summary`, and `headline`, `fit_rationale`, `fit_score` and `attending_status` are in
no documentation at all. Every read here scans the real name first and the documented name
second, so a deployment using either shape works — but a client built from the documentation
alone writes a row of empty columns and reports success.

**Columns are adopted by name, never recreated.** The build runs `CREATE TABLE IF NOT
EXISTS` and then `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` per column, so a re-run adds only
the gap and a column added to the plan later reaches a table built before it. When an existing
column has a different type than the plan wants (somebody altered it by hand), the build says
so and the driver validates against the column's REAL type — so a value that does not fit is
dropped and named rather than failing the batch.

## The company domain has to be derived

Measured: this provider returns **no company domain on any contact**. The enrichment block
carries an email, a phone, a profile URL and an avatar — nothing else. Taken literally that
means no company row can ever be created and every attendee is written unlinked.

The work email is the evidence available, and for a work address it is strong: the domain on
a work address identifies the employer as well as any field would. So when nothing supplies a domain, one is
derived from the email — **except at a mailbox provider**, where it is refused outright. A
company row keyed on `gmail.com` would gather every unrelated attendee into one fictional company,
which is worse than leaving them unlinked.

Measured when this skill wrote to Clay Audiences: 5 of 5 attendees linked to the right
company — one person at each of five distinct employer domains, and zero at a control domain
nothing wrote. The derivation is the same code here.

## A changed company overwrites; it does not accumulate

The link is the `company_domain` value on the attendee's row, so rewriting an attendee whose
company changed (an acquisition, a corrected domain) simply replaces it. The old company row
stays in `storage.conference_companies` — nothing deletes a row — but no attendee points at it
any more.

## Matching

People match on **LinkedIn URL first, email second**, through `person_key`. For a conference
attendee the profile is the more stable identity, and two people at one company can share an
inbox alias while never sharing a profile. Both are normalised before the write, and a profile
URL pointing at a company website is discarded rather than sent.

An attendee whose company has no domain is written **unlinked** (`company_domain` NULL),
never dropped. An attendee with neither a LinkedIn URL nor an email has no key and is reported
as unwritable — with their name, so the person running it can decide.

Two contacts in one batch resolving to the same `person_key` are folded into one row before
the statement, because Postgres refuses an upsert that touches the same row twice.

## The blank that overwrites

Every write is `ON CONFLICT DO UPDATE SET col = COALESCE(EXCLUDED.col, col)`, and every blank
is sent as NULL, never `""`. So a second campaign touching a person the table already holds
fills in what it knows and leaves everything else alone. An empty string would not be NULL,
would win the COALESCE, and would clear the column — which is why the driver never sends one.
