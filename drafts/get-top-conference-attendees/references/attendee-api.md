# The attendee service's API, as measured

Lanyard's public API, base `https://lanyard.redlinegrowth.com/api/public/v1`. It publishes an
OpenAPI document at `/openapi.json` on that same base — read it before trusting anything here,
because a running service moves and a note does not.

**Send a named `User-Agent` on every request.** Measured 2026-09-16: the service sits behind
an edge that rejects Python's default agent outright — `Python-urllib/3.x` gets `403` with an
HTML error page (a Cloudflare 1010) *before the request reaches the API*, while the identical
request with the identical key and any named agent gets `200`. Nothing about that failure
looks like what it is: it arrives as a 403, the same status a revoked key returns, so a client
that omits the header tells the installer their key is bad and sends them round the sign-in
loop for ever. The rule that follows: **a non-JSON body did not come from the API**, and an
edge refusal must be reported as one.

Authentication is a bearer token in the `Authorization` header on every call except the two
sign-in calls. The token is issued once by `auth/verify` and never shown again. **This skill
never asks for it, never prints it and never puts it on a command line** — a value in an
argument is visible in `ps` to every other process on the machine. It reads the
`LANYARD_API_KEY` environment variable, or a file of `KEY=value` lines named by the config.

## The nine endpoints

| Call | Auth | What it is for |
|---|---|---|
| `POST /auth/start` | none | emails a numeric sign-in code — never assume its length, see below |
| `POST /auth/verify` | none | exchanges the code for an API key, shown once |
| `GET /me` | bearer | the account, its credit balance, its free allowance |
| `POST /conferences/lookup` | bearer | resolves a name to one verified edition |
| `POST /campaigns` | bearer | starts a run; returns immediately |
| `GET /campaigns/{id}` | bearer | status, counts, share link |
| `GET /campaigns/{id}/contacts` | bearer | the ranked people, paginated |
| `GET /campaigns` | bearer | every campaign the key can see — how a lost id is recovered |
| `POST /campaigns/{id}/unlock` | bearer | spends credits to enrich locked contacts |

One account, one login: the key is tied to the same account used on the website, not to a
separate "API account". Re-verifying issues an additional key and leaves existing keys alone.

**Never validate the sign-in code's length, and never tell anyone how many digits to expect.**
`auth/start` describes "a 6-digit code" and `auth/verify` shows `"123456"`; a code observed
from a real sign-in was longer than that. The number is not a contract either way, so a client
that enforces one rejects real codes and leaves the person assuming they mistyped. Take
whatever arrived and send it.

## The error envelope, and which field carries what

A failure returns `{"error": "<a human sentence>", "code": "<a slug>"}`. The published schema
describes the opposite — a slug in `error` and a sentence in `message`. **Branch on `code` and
print `error`.** Reading `message` prints nothing and reading `error` as a slug never matches.

Confirmed by probe: a bogus key returns `401 {"error": "Invalid or revoked API key", "code":
"unauthorized"}`, and an empty sign-in body returns `422 {"error": "A valid email is
required", "code": "invalid_input"}`.

## What `/me` actually returns

Measured against a fresh self-serve account:

```
account: {email, user_id, client, key_label, key_prefix, source}
credits: 0
free_dossiers_per_campaign: 5
unlimited: false
campaigns_url: <the account's campaigns page>
```

`campaigns_url` is present — the published spec example omits it. `key_label` and `key_prefix`
are in neither the spec nor the brief: the account echoes back the label the key was created
with and a short prefix identifying it, which is how you tell two keys apart without holding
either. **Never print the prefix** — it is not the key, but it is key-shaped, and key-shaped
strings in a package are a rejection.

A brand-new self-serve account has **0 credits and 5 free dossiers per campaign**. That is the
baseline every first run hits, and it is why the allowance has to be stated before the run
rather than discovered in the results.

## Creating a campaign

Required: `domain` (your own site — what the scoring calibrates against), `conference`, and
`goals`. Two of those three accept either a string or an object, which is worth knowing
because the shapes are not interchangeable in what they buy you:

- `conference` — a bare name, or `{name, city, start_date, end_date, website}`. Use the
  looked-up edition rather than a bare name: a bare name makes the service guess the edition
  again, and a conference that runs annually in three cities has no single right answer.
  **But do not forward the lookup's object verbatim.** Measured: the lookup returns `edition`,
  `summary`, `likely_app` and `confidence` as well, none of which the create call documents
  accepting — an undocumented key is a 422 at best and silently dropped at worst, and neither
  is worth risking on the one call that costs a campaign. Narrow it to the five documented
  keys, and fold `edition` into the name so the edition you just resolved is not thrown away.
- `goals` — free text, or `{categories[], freeform}`.
- `context` — free text, or `{client, conference}`. Fed into the scoring rubric and the
  dossiers.

Also accepted: `team[]` (who is going from your side, `name` required), `attendees[]` (people
you already know are going, up to 500, `name` required), `enrich_count` (1–100, default 10),
`label`, `callback_url`, `client_id`.

The response is a `202` carrying `campaign_id`, `poll_url` and `contacts_url`. It is not a
result.

## Polling

`status` is a single enum that carries the stage: `queued`, `researching`, `discovering`,
`ranking`, `enriching`, `dossiers`, `complete`, `failed`. There is no separate `stage` field.
`progress[]` carries a human line per stage change, which is what to show a person.

**Settle only on `complete` or `failed`.** Never on a count: `counts.dossiers` moves while the
last dossiers are still being written, so a run that looks finished by its numbers is not.

## Reading the people

`GET /campaigns/{id}/contacts` takes `limit` (default 100, max 500), `offset`, `top`
(only the enriched ones) and `format` (`default` or `clay` — the second is Lanyard's own
parameter value for its flat projection, named after the tool it was first built for).

### Two formats, and why both are read

**`format=default` for the content, `format=clay` for the tier.** They are not the same data
in two shapes — each carries something the other does not.

The rich format has the dossier as an object; the flat one has `tier`, and the rich one has no
tier under any key on any contact. Measured across 144 live contacts: the flat projection
tiers every one of them (S 17, A 15, B 18, C 73, F 21), reconciling exactly with the
campaign's own locked block. The flat format in turn drops `buying_signals`,
`conversation_openers`, `value_prop_framing`, `company_summary` and `headline` entirely.

So both are read and merged. Reads moved no credit meter, so the second pass is free, and
"who are the S-tiers" is the first question anybody asks of a conference list. **The flat rows
carry no `id`**, so the merge joins on identity — LinkedIn URL, then email, then name plus
company.

### The dossier keys, as the service returns them today

Worth reading carefully, because getting it wrong looks like success rather than failure.
Measured against a live campaign, the dossier object holds:

```
attending_status · buying_signals · company_summary · contact_summary
conversation_openers · fit_rationale · fit_score · headline · rapport_match
value_prop_framing
```

An earlier revision of the spec described these under different names — `summary`,
`contact_history`, `company_history`, `openers`, `value_prop` — and a client written against
that revision populates one column and leaves eight blank without erroring. The spec has since
been corrected; the defensive read stays because it costs nothing and covers both.

So each read scans the current name first and the older name second: `contact_summary` then
`summary`, `conversation_openers` then `openers`, `value_prop_framing` then `value_prop`,
`company_summary` then `company_history`, `fit_rationale` then `score_rationale`. And
`headline`, `fit_score`, `attending_status` and `rapport_match` appear in no documentation at
all.

### Where the company domain comes from

`company_domain` is returned on the contact and is authoritative — use it. It resolves the
employer properly rather than by inference, which matters more than it sounds: on a live run
it correctly placed someone at their real employer when their address was still at a company
that had been acquired, where a guess from the email would have filed them under the old one.

It is not populated for every contact. When it is absent, the client falls back to the work
email's domain and refuses mailbox providers — a company row keyed on `gmail.com` would merge
unrelated attendees into one fictional company. The fallback is a backstop, not the primary
path.

**Use `format=default`.** The flat format exists to be poured straight into a spreadsheet-like
table, and flattening is exactly what you do not want on the way to typed columns: the dossier's
`buying_signals`, `openers`, `contact_history` and `company_history` are lists, and this skill
decides itself which of them become filterable columns and which become prose. The default
format keeps the dossier as an object. Both envelopes are read anyway — the default keys its
rows under `contacts`, the flat one under `rows` — because reading only one turns the other
into an empty campaign.

**Paginate.** A single unpaginated read silently truncates a large conference at the first
page, and a truncated list looks exactly like a small event.

Per-contact, the fields that decide anything:

- `dossier` — nullable. `tier`, `summary`, `buying_signals[]`, `contact_history[]`,
  `company_history[]`, `openers[]`, `value_prop`. **Its presence is what makes a contact
  deliverable.**
- `enrichment_status` — `none` | `queued` | `enriched` | `failed`.
- `attendance` — `{confidence, evidence, year_context}`: why the service believes this person
  is going. `evidence` is the single most useful line in the whole payload for a human, and
  **`year_context` is `this_year` | `last_year` | `prior`** — a documented enum, so a filter
  on it is safe to write. It is also the field that decides whether this is a list of people
  who will be in the building: measured, only 2 of 5 contacts returned as attending carried
  `this_year`.
- `score`, `rank`, `score_rationale`, `confidence`, `is_top`.
- `enrichment` — an open object. The company domain lives here when it is known at all.
- identity: `id`, `name`, `title`, `company`, `linkedin_url`, `email`, `phone`.

## What the lookup returns

Measured. Richer than either source documents:

```
query:      the string that was searched
conference: {name, edition, start_date, end_date, location, website,
             likely_app, summary, confidence}
```

`edition` and `summary` appear in neither the spec nor the brief. `confidence` is the field to
show a person before committing: it is the service's own view of whether it found the right
event, and it is the cheapest thing in the whole flow to get wrong expensively.

## Unlocking, and the two shapes it answers in

`POST /campaigns/{id}/unlock` spends credits (5 per contact) to enrich locked contacts.
Select with `contact_ids` (up to 500), `tier`, `tiers[]`, or `top` N. **`dry_run` prices it
without spending** — send it first, always.

**The dry run answers in a different shape from the real call, and only the real one is
documented.** Measured:

```
dry_run: {dry_run: true, matched, credits_required, credits_available, payment_url}
real:    {unlocked, credits_spent, credits_remaining, dossiers_generated,
          dossiers_pending, contacts_url}
```

Read both. A client that pins the documented names gets `None` for every number on a quote,
which is how a price of "None credits" ends up in front of a person.

Two things the dry run gives you that matter more than the price:

- **`payment_url` comes back on the quote**, not only on a `402`. So a shortfall can be
  reported before anything is attempted — there is no need to fail a call to discover the
  account cannot afford it.
- **`credits_available`** makes the affordability check local. Quote, compare, and either
  offer to spend or hand over the link.

A `402` carries `required`, `available`, `shortfall` and `payment_url`. **It is a price, not a
transient failure** — never retry it, never attempt a payment, and hand the link to a person.

`dossiers_pending` on a successful unlock means dossiers are still being written. Those
contacts have no dossier yet, so a load immediately afterwards skips them. Wait and re-load
rather than reporting a short count.

Comped campaigns and the vendor's own keys unlock for free, so a quote of 0 credits is
possible and is not a bug.

## Three campaign links, and they are not interchangeable

- **`lanyard.redlinegrowth.com/campaign/<id>`** — the page a signed-in person opens to read
  their own results, and the only one worth putting in front of them. Not returned by the
  API; build it from the id.
- **`share_url`** — a `/claim?t=<token>` link. The token IS the access, so anyone holding the
  link can see the campaign without an account. Useful for handing results to a colleague;
  wrong as a default, and not worth pasting anywhere it will outlive the conversation.
- **`dashboard_url`** — an `/admin/<id>` view. Not the customer's page.

`locked.unlock_url` is the claim link again rather than a separate payment page, so do not
treat it as one; a quote's `payment_url` is the authoritative place to add credits.

## `GET /campaigns` — the recovery path

Every campaign the key can see, newest first, including ones started in the web app. Carries
`campaign_id`, `label`, `status`, `created_at`, `client_url`, `conference`, `counts`,
`poll_url`, `contacts_url`. Pages on `limit` (default 25, max 100) and `offset`.

This is what makes the skill recoverable from nothing but the key. The campaign id is the
whole of its state, and before this existed it lived only in a local file.

## The thing that still shapes this skill: there is no unlock NOTIFICATION

A free account gets a small number of fully written dossiers per campaign. Everything else is
ranked and waiting. Unlocking can now be done through the API — but it can also still be done
**in a browser, against the share link**, by whoever holds it. And:

- there is no `since` or `updated_after` parameter on any call,
- there is no webhook for an unlock (the `callback_url` fires once, when the campaign
  completes),
- nothing in any response says when a contact's dossier appeared.

So **nothing can tell this skill what changed**, and having an unlock endpoint does not fix
that — it only means the skill is sometimes the cause. A top-up cannot be a notification and
cannot be a diff against a remembered timestamp. It can only be a re-read: ask for every
contact again, take everything that now carries a dossier, and subtract what has already been
written.

That is why the load and the top-up are the same command, and why it does not matter whether
the skill spent the credits or a person clicked a link last Tuesday.

## The published schema and the service now agree

Re-checked 2026-09-18 after two rounds of corrections. Everything this file used to list as a
disagreement is fixed: the dossier names its real keys, `locked` and the create `enrichment`
block are documented, `/me` is complete, the `Error` schema names `code`, both new endpoints
are described, the `dry_run` response has its own example, `year_context` is an enum, and an
unknown route now returns a clean `404` with the normal envelope instead of a `500`.

**So the defensive reads below are no longer compensating for a wrong spec.** They stay
anyway, and that is a deliberate choice rather than laziness: this spec was wrong by eight
dossier keys out of nine as recently as two days ago, and a client that scans
real-name-then-documented-name costs nothing while a client that pins one costs a silent
column of blanks. The history is kept below so the habit has a reason attached.

**One open item, and it is about data rather than the schema:**
`company_linkedin_url` is documented and was populated on 0 of 144 contacts, against 61
carrying a `company_domain`. A populated one could key a company row for an attendee whose
employer has no resolvable domain. The client
reads it wherever it appears and never depends on it.

## Historical: how the spec and the service have converged

Checked against a live campaign, 2026-09-16. The build brief documents three blocks the
published OpenAPI does not carry. **Two are real; the schema is simply behind the service.**

**`locked` on `GET /campaigns/{id}` — confirmed present.** Exactly the brief's shape:

```
locked: {total, tiers: [{tier, count}, …], credits_per_contact, unlock_url}
```

`credits_per_contact` measured as `5`, and the tier list carries every tier (S, A, B, C, F)
including the ones at zero. `unlock_url` embeds a share token — **treat it as a secret**: it
is what grants access to the campaign, so never commit it and never put it in a package.

**`enrichment` on the create `202` — confirmed present.** `{requested, allowed,
free_limit_applied}`. Measured on a fresh self-serve account asking for 25: `requested 25`,
`allowed 5`, `free_limit_applied true`. This is what makes the free-tier disclosure a stated
figure rather than a derived one, and it is available **before** the campaign runs, which is
the only moment the disclosure is worth anything.

Note the service also **clamps server-side**: the campaign that comes back reports
`counts.requested_enrichment: 5`, not the 25 that was asked for. So the create response and
the campaign disagree about what "requested" means — the create response remembers the ask,
the campaign records the clamp. Read the allowance from the create response where possible.

Two further fields appear on the campaign that neither source documents: `discovery` and
`remaining_by_tier`.

**`format=clay` — confirmed, and it is not merely a flattening.** It returns a different
envelope (`rows`, not `contacts`) carrying exactly the brief's keys: `tier`, `has_dossier`,
`why_attending`, `attendance_confidence`, `source_url`, `source_title`, `dossier_summary`,
plus the identity fields. See "Two formats, and why both are read" below — **`tier` exists
only here**, which is the reason this format cannot simply be ignored.

**Even so, none of the three is depended on**, because a block that exists today is not a
contract and the schema that omits them is the published one. Each is read when present and
derived when absent:

- the allowance comes from the create response, then the campaign, then `counts.enriched`
  against `counts.requested_enrichment`, then the account's own
  `free_dossiers_per_campaign` — and reports which of those answered;
- the locked summary is read from a published block when there is one, and otherwise counted
  directly off the contact list, which is always available and always agrees with what will
  actually be written. **The two answer different questions and must not be presented as the
  same one.** A published block breaks the locked contacts down by tier; a local count
  cannot, because tier is written *into the dossier* and a locked contact is precisely one
  whose dossier was never written. Bucketing a local count by tier would put every locked
  contact into a single meaningless pile and label it a tier breakdown. So the local count
  breaks down by state instead — how many were simply never enriched, how many are still
  queued, how many failed — and the result says which of the two you are looking at.

A number that was derived says so. Presenting a counted figure as though the service had
stated it is how a disclosure about money stops being trustworthy.
