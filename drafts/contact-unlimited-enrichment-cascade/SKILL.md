---
name: contact-unlimited-enrichment-cascade
description: |
  Build a reusable contact enrichment cascade on Deepline — a config-driven runner that takes a
  person and returns them with whatever contact details were missing filled in (company domain,
  company LinkedIn, contact LinkedIn, work email, mobile phone, email verification), each
  stamped with which provider found it. It tries your flat-rate providers first — the ones you
  pay monthly rather than per lookup, like BlitzAPI, Huntr, MoltSets, GetLeads or QuickEnrich,
  or whatever you hold — and only falls through to Deepline's credit-billed waterfall plays when
  every free attempt came back empty. Run it again later to add a provider without a rebuild.
  Use whenever someone asks: build a contact enrichment waterfall, set up enrichment for our
  workspace, find emails and phones for this list, fill in missing contact details, use my own
  API keys before spending Deepline credits, add a provider to my enrichment waterfall, or stop
  burning credits on data I already pay for. Do NOT use it to look up one person's details right
  now in conversation, to clean or re-verify contact data you already hold, to source net-new
  people by persona or title, to identify who someone is from an email alone, to edit a Deepline
  play you wrote by hand, or to write contacts into a CRM or enroll anyone in a sequence. It
  never asks for or stores an API key — a flat-rate provider's key lives in an environment
  variable the installer sets themselves.
category: enrich
personas: [gtm-engineer, revops]
mechanism: workflow
touches: writes-records
keywords: [waterfall]
ported_from: clay-run/clay-skill-creator/skills/shy-rahnama/contact-unlimited-enrichment-cascade
---

# Contact unlimited enrichment cascade (measure the reach rate, not the call count)

**A cascade's cost is not the sum of its calls — it is set by one field: the contact LinkedIn
URL.** Flat-rate providers bill a monthly subscription and nothing per request, so every
lookup before the credit-billed tier is free and the call count is not the bill. What decides
spend is how often a run *reaches* the paid tier. And most flat-rate email and phone endpoints
key off a person's profile URL and nothing else — so a miss on that one field does not degrade
a run, it routes the entire remainder into the billed waterfalls.

Two measurements, both from one workspace and neither a promise about yours. Adding a **second**
profile finder after the first one missed took a run from **one field filled to three**, because
the pivot unlocked both email and phone behind it. And moving the phone lookup from a credit-
billed cascade onto a flat-rate provider took the same contact from **28 data credits and 12
action credits in 1m35s to 5 and 6 in 10s** (measured on Clay's native cascades, 2026-08) — the
paid phone cascade had been the single largest cost in that graph. Phone waterfalls are the dearest
leg on Deepline too; price yours from `deepline tools describe` before quoting anything.

**Which turns the obvious move on its head: buying the pivot is usually the cheapest thing you
can do.** If a credit-billed lookup is the only way to get a profile URL, pay for it — because
it converts the email and phone legs behind it from billed to free. One paid lookup that unlocks
two free ones beats three billed ones, and a cascade that refuses to spend anywhere ends up
spending everywhere.

So this skill is built to measure the reach rate rather than the call count: every step stamps
the record with which provider filled the field, and the cost estimate is that histogram rather
than an arithmetic guess. Everything else follows — several finders on the pivot, a precondition
on every leg that needs it, and provenance that four different outcomes cannot collapse into.

> Do not start a step before the steps above it have their answers. If a declared input is
> missing, ask for it — never assume a default and continue.

> **The config is field-complete. What gets ATTEMPTED is decided at run time, by the skip flags
> on the record — never in the config.** Write a leg for every field every provider they hold
> can reach, and let each record choose. A field has no leg for exactly one reason: nothing they
> have can fill it. "They only want email" is not that reason — they set `skip_phone` and
> `skip_linkedin` on the records where that is true, and change their mind next week without
> touching the config.

> **This skill is not finished when the plan is agreed, or when the config is written.** It is
> finished when the config is validated against live Deepline schemas, smoke-tested on a real
> record, and run on their list or handed over with the exact command that runs it. Writing a
> config and stopping leaves them with a file and no enrichment, which is worse than not
> starting. If you do have to stop early — a missing environment variable, an unanswered gate —
> say which step you stopped at, what remains, and the exact command that resumes it.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing. Where a default IS defensible it is named below, and using it
means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Which providers they hold** | the flat-rate providers they already pay for, and **which plan** — several sell unlimited only on a top tier, so "flat-rate" is a property of the plan, not the vendor | with none, there is no flat-rate tier: every request goes straight to Deepline's credit-billed waterfalls, and the estimate must be quoted at that rate before running, not after |
| **The environment variable per provider** | the NAME of the environment variable they will export holding that provider's key (`BLITZ_API_KEY`) — **the name only** | that provider's legs are not written, and the skill says which fields lost a tier. **Never ask for the key itself**, and if one is offered, decline and point at the environment variable |
| **Provider terms** | confirmation their provider agreements permit sending these identities | ask once and record the answer. The cascade sends contact identities to third parties on every row and cannot read a contract |
| **Existing config (extend only)** | the config of a cascade this skill already wrote | absent means a new config. The runner is stateless, so an existing config is all an extend needs |

**And these are derived, not asked. Each one has been tried as a question and each is
noise — the answer is shown in the plan at Step 4, where they can change it:**

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Where finished records are sent** | **nothing — do not ask.** The output CSV (or the JSON printed for one record) always carries the result. `callback_url` is a per-record input, like the skips: a record carrying a URL is also POSTed there, one without is not sent anywhere | so the destination is the caller's, chosen per record, and blank means nothing is sent. Disclose the behaviour at the Step 7 gate; never ask for a destination up front |
| **Which fields get filled** | **nothing — do not ask.** Derived from what their providers can reach, then governed per record by the skip flags | write every leg the providers support. The plan shows them, and a leg is cut there only when it adds no reach over one ahead of it — **never to switch a field off**, which is a skip flag on a record |
| **Whether the credit-billed tier runs** | **nothing — do not ask.** Every billed leg appears in the plan with its cost, and cutting one is an edit to the plan | every billed leg is written regardless; whether it fires on a record is a skip flag. The plan shows the cost so they can see it, not so they can switch a field off |
| **Leg order within a tier** | **nothing — do not ask.** Ordered by measured hit rate, shown in the plan, correctable there | ordering inside the flat-rate tier saves no money — every call costs the same zero — it only shortens the path to an answer. Say the order was measured, not chosen |

### The input contract — prescribed, and there is nothing to ask

**Never ask what their list looks like, and never ask for column names up front.** The runner
takes a fixed interface and two entry points, and neither needs anything from the installer:

- **One record** — `--record '{"contact_name":"..","company_name":".."}'`, JSON in, JSON out.
- **A CSV** — `--csv in.csv --out out.csv`. When the columns are called something else, a
  `--columns` file maps interface fields onto them (`{"contact_name": "Full Name"}`) — **the
  column names do not have to match**, that is what the map is for.

So a cascade can be configured before any list exists, and the same config serves any number of
lists later. Asking to "inspect the columns" first is asking for something the interface
already settles — the columns get mapped onto a fixed shape, not the other way round.

| Input | | |
|---|---|---|
| `contact_name` | **required** | a record without it is rejected at intake |
| `company_name` | **required** | same |
| `contact_email` | optional | supplied means no lookup, and it is kept, never overwritten |
| `contact_linkedin` | optional | the pivot — supplying it is the single biggest cost saving |
| `contact_phone` | optional | as above |
| `skip_email`, `skip_linkedin`, `skip_phone` | optional | **absent means false — do the work.** Present and true switches that field off for that record |
| `want_company_domain`, `want_company_linkedin` | optional | **absent means false — do not go looking.** These are enabling lookups: they fire anyway whenever a leg downstream requires them, and this flag is how you ask for one *as an output* when nothing else needs it |
| `company_domain`, `job_title` | accepted, never required | a domain is the cheapest lever there is; a title sharpens a profile search |
| `source_ref` | accepted | echoed back unchanged so a caller can join the result |
| `callback_url` | accepted | where the finished record is POSTed, if anywhere |

First and last name are **derived** from `contact_name`; a caller supplies one name, not three.

**A value that arrives is never looked up again, and that is a cost guarantee, not just a
courtesy.** Send an email and no email leg runs — not the flat-rate one, not the billed one. The
field resolves as `supplied` and every provider in that chain is skipped entirely. The same holds
for a phone and a LinkedIn URL.

Two consequences worth saying to the installer in these words:

- **Supplying a field is the cheapest thing they can do**, and supplying the contact LinkedIn URL
  is the cheapest of all — it is the pivot, so it also converts the email and phone legs behind it
  from billed to free.
- **A supplied value is never corrected.** If they send a stale email, they get that stale email
  back marked `supplied`. This skill fills gaps; it does not audit what it was given. Re-verifying
  data they already hold is a different job.

**The skips are runtime, not config-time, and that is the point.** Write every leg the providers
can support; let each record decide what it wants. The same config then serves a cheap pass
and a full pass without an edit, and "what will this cost" becomes a property of the call
rather than of the config. Never bake a field being off into the config — that is an edit every
time somebody changes their mind.

**Absent defaults to false on purpose, and the two families read the same way for different
reasons.** A `skip_` flag is an opt-OUT on a field the cascade exists to fill, so absent means do
the work — a caller who has never heard of these gets the full cascade, and a flag defaulting to
"skip" would silently return empty fields to anyone who did not know to set it.

A `want_` flag is an opt-IN on a field nobody asks for on its own. A company domain exists so the
email leg can run; it fires whenever something downstream needs it, flag or no flag. The flag only
answers a different question — *"fetch one even though nothing needs it, because I want it in the
output"* — and it defaults off because the other polarity would fire it on every record where the
field happened to be missing, adding cost nobody asked for. A field with no flag at all cannot be
requested, only inherited, which is the gap these close.

### The output contract — every key, named

The same shape every time, so a consumer written against one cascade works against all of them.
`record_json` (and each row of the output CSV) carries exactly this and nothing else; it is the
deliverable, and the request bodies and gate flags the record uses in transit are **not** in it.

**Six keys are guaranteed on every record**, present even when empty, so a consumer never has
to test whether a key exists before reading it. **Blank means skipped or not found — that is a
value, not an absence.** Everything the caller sent passes through unchanged alongside them.

| Guaranteed | |
|---|---|
| `contact_name`, `company_name` | as supplied, never enriched, never overwritten |
| `contact_email`, `contact_linkedin`, `contact_phone` | filled, or blank |
| `contact_email_verified` | `"true"` / `"false"` |

Then everything else, which is detail rather than contract:

| Key | | |
|---|---|---|
| `first_name`, `last_name`, `job_title` | derived or passed through | not part of the guarantee |
| `company_domain`, `company_linkedin` | filled when something needed them, or when asked for with `want_company_domain` / `want_company_linkedin` | enabling lookups that can also be requested; `not_needed` when neither applied |
| `contact_email_verify_status` | the verifier's verdict, lowercased | `not_checked` when no verification leg ran |
| **`<field>_source`** | one per field the cascade can fill | the closed six below. **Nothing else carries a source**, so a source key existing tells you a leg for that field exists |
| `contact_email_verified_only` | the address, or **blank** | **this is what downstream automation should consume.** Blank unless a verifier actually passed it |
| `contact_email_domain_match` | `"true"` / `"false"` / `"unknown"` | whether the address sits on the company's own domain |
| `filled_fields`, `filled_count` | what this run actually added | excludes anything that arrived supplied |
| `captured_fields` | extra data a provider returned beyond its own field | a comma list of the keys, which are present alongside |
| the five flags | echoed back | so a `skipped` or `not_needed` source is explainable without the original request |
| `source_ref` | echoed back unchanged | the caller's own row id, for joining |
| `callback_url`, `has_callback` | where it was sent, if anywhere | |

Beside the contract, each CSV row also carries two diagnostic columns that are **not** part of
it: `leg_errors` (a failed provider call — a `401`, a timeout — per leg) and `callback_status`.

**`<field>_source` is one of six, and they are not interchangeable:**

| | |
|---|---|
| `supplied` | it arrived populated; nothing was looked up |
| *a provider's label* | that provider found it |
| `not_found` | a leg ran and came back empty |
| `skipped` | the caller switched the field off |
| `blocked_missing_input` | an input the leg needed never arrived, so it never ran |
| `not_needed` | an enabling lookup nothing downstream needed and nobody requested; it cost nothing |

Four of those mean "no value" and they mean completely different things. **Report them
separately** — collapsing them makes every provider hit rate meaningless, which is the only
reason to run a waterfall instead of one call. And read `leg_errors` before trusting a
`not_found`: a failed call resolves as `not_found` in the record, and the error is kept beside
it so a wrong key is not mistaken for a provider miss.

**If an answer sheet is present beside this skill, load it and ask only for what it does not
cover.** A partial sheet is normal; a value it is missing gets asked for on its own rather than
restarting the interview. **Say which values came from the sheet** before using them — a sheet
applied silently is a wrong field nobody catches. **If there is no sheet, say nothing about
sheets** — the check is a file lookup, not a question, so run the interview as though the
feature did not exist rather than reporting an absence. At delivery, offer to save the answers
back (identifiers and environment variable names only — never a token or a password), private
and never published, and phrase the offer so it explains itself: *"want me to save your answers
to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the Deepline tool and play catalog (`deepline tools describe`, `deepline plays
  describe`, both free); each provider's published API documentation; the input CSV you point it
  at; and, at run time only, the environment variables named in the config. **It never reads a
  key into the conversation or a file.**
- **Writes** — two things, and they are different in kind. It **writes an output CSV** (one row
  per input row, the contract above) to a path you name, and refuses to overwrite an existing
  one. And where a record carries a callback URL it **POSTs that finished record, email and phone
  included, to that URL**. It also writes the config file itself, beside your working files.
- **Never** — asks for, receives, stores or transmits an API key outside the provider call it
  authenticates; puts a credential in the config, a record or any output; overwrites a contact
  value you supplied; blanks or clears a populated field; sends your data anywhere but the
  providers in the config, Deepline, and the `callback_url` carried on each record; contacts
  anyone; or writes to a CRM or a sending tool.
- **Halts** — Step 4 other, Step 6 spend-approval (smoke test), Step 7 spend-approval (full run).
  Step 4 is the plan gate: the cascade is agreed before any environment variable is set up or
  any paid call made.

## Representative output

### Provider capability map

Derived from each provider's own spec at Step 3, and shown back before anything runs.
Placeholder providers; the shape is the contract.

| Provider | Fills | Needs | Lands as |
|---|---|---|---|
| flat-rate A | contact LinkedIn | name + company | finder, **before the pivot** |
| flat-rate A | work email · mobile phone | contact LinkedIn | primary, after the pivot |
| flat-rate B | work email | name + domain | second email leg, still free |
| flat-rate B | contact LinkedIn | name + domain | second finder on the pivot |
| `zerobounce_validate` | email verification | an email address | reporting leg, last |
| Deepline waterfall plays | work email · mobile phone · contact LinkedIn | name + domain | **fallback, credit-billed** |

### Proposed cascade plan

What Step 4 puts in front of them, before any environment variable is set up. Placeholder
providers; Deepline prices read from `deepline tools describe` on 2026-10-01.

```
1  company domain      crustdata_v3_company_enrich                  needs company name     0.8 cr     ENABLER
2  contact LinkedIn    flat-rate A                                  needs name + company   free
3  contact LinkedIn    prebuilt/person-to-linkedin-harvestapi       needs name + domain    billed     ENABLER
4  work email          flat-rate A                                  needs contact LinkedIn free
5  work email          prebuilt/name-and-domain-to-email-waterfall  needs name + domain    billed  <- fallback
6  mobile phone        flat-rate A                                  needs contact LinkedIn free
7  mobile phone        prebuilt/person-to-phone                     needs name             billed  <- fallback
8  email verification  zerobounce_validate                          needs an email         0.28 cr

A waterfall play's cost is the providers it reaches before one hits; each step's price is in
`deepline tools describe <tool>` for the tools listed in its staticPipeline.

Why leg 3 is billed on purpose: your flat-rate providers can only find a profile URL from name
+ company, which fails on about a third of records. When it does, paying for the URL turns
legs 4 and 6 from billed back into free — instead of the email and phone waterfalls. It pays
for itself on any record that wants a phone number.

Every leg above gets written, leg 7 included — the dearest call in the cascade. That is not a
commitment to spend it: it fires only on a record that wants a phone and whose free lookup
missed, and `skip_phone` stops it entirely. **Nothing is switched off in the config**, so
changing your mind about phone next week is a flag on a record, not an edit.

Enablers have no opt-out either: they run when something downstream needs them and not
otherwise. A record with every skip set costs nothing at all.

Not filled:  company LinkedIn — no provider in the plan offers it, and nothing needs it as input.
Left out:    flat-rate B's phone endpoint — same input and position as leg 6, no added reach.
You need to export: 1 environment variable (FLAT_PROVIDER_A_KEY).
```

### Enriched record

| source_ref | contact_linkedin | linkedin source | contact_email | email source | contact_phone | phone source | verified |
|---|---|---|---|---|---|---|---|
| row-1041 | /in/a-lovelace | flat-rate A | ada@engines.example | flat-rate A | +1555…0142 | flat-rate A | true |
| row-1042 | /in/c-babbage | flat-rate B | charles@engines.example | deepline_waterfall | *(none)* | not_found | true |
| row-1043 | *(supplied)* | supplied | grace@navy.example | supplied | *(none)* | skipped | not_checked |
| row-1044 | /in/g-hopper | deepline_waterfall | grace@navy.example | flat-rate A | +1555…0198 | flat-rate A | true |

### Reach-rate report

```
48 records · 46 enriched · 2 rejected at intake (no company name)

contact_linkedin   flat-rate A 31 · flat-rate B 9 · supplied 4 · not_found 2
contact_email      flat-rate A 27 · flat-rate B 6 · deepline_waterfall 7 · supplied 3 · not_found 3
contact_phone      flat-rate A 19 · skipped 22 · blocked_missing_input 2 · not_found 3
company_domain     supplied 44 · crustdata 1 · not_needed 1   (enabler, no opt-out)
records with a leg error: 0

Reached the credit-billed tier: 7 of 46 (15%) · 7 paid calls · 0 on phone — skip_phone was set
on every record that got that far, so the dearest leg in the cascade never fired once.
Paid enabling lookups: 6 profile URLs, which kept 6 phone lookups off the billed waterfall.
Email addresses on a domain other than the company's: 1 — verified true, and suspect anyway.
```

## Files in this skill

| | |
|---|---|
| `references/provider-adapters.md` | How to turn a provider's API spec into legs: find the spec, classify each endpoint by what it produces and requires, place it, verify it. Also how the key reaches the call without reaching the conversation. **Read before writing a leg for any provider.** |
| `references/cascade-config.md` | The config schema — every top-level key, every leg field, the three provider types, the record contract, and what the cascade emits. |
| `references/runner-shape.md` | How one record moves through the legs and why it is shaped that way, plus every trap the runner encodes. Read it before changing `cascade.py` or debugging a run that completes and returns nothing. |
| `scripts/cascade.py` | The runner. Reads a config, validates it against live Deepline schemas (`--dry-run`, free), then runs one record (`--record`) or a CSV (`--csv --out`), and prints the reach-rate report (`--report`). |
| `scripts/cascade-config.example.json` | A complete config at placeholder values, covering all three provider types with real Deepline tool and play IDs. Start here. |
| `scripts/test_codegen.py` | Generates every handler the runner executes, parses it, runs the handlers against a fake context, then runs whole records through the runner against a fake Deepline. No credentials, no network, no cost. |

## Step 0 — State the posture, then confirm the platform

Say this before anything else, in one short message: **this writes a config and an output CSV
beside your files; it calls Deepline (credit-billed) and your own flat-rate providers (your
subscription) for each record; and any record that carries a `callback_url` gets POSTed there.
It never asks for or stores an API key.** And say plainly that **no list is needed to configure
it** — one gets run through it afterwards, whenever they like.

Then say where the cost lives, because that is a design property and not a footnote: calls to
your flat-rate providers go through Deepline's `generic_http_request` tool, which is priced
**Free** in Deepline — they bill against subscriptions you already pay for. Deepline's own tools
and waterfall plays bill Deepline credits per call. Everything the agent works out in
conversation, and every `describe`, is free.

```
deepline preflight; echo "exit=$?"
```

`0` and a signed-in workspace means go. Anything else: **say which component is wrong and the
one command that fixes it — then stop.** Missing CLI: `npm install -g deepline && deepline auth
register --wait auto`. Do not install, upgrade or fetch anything else to repair it. An environment
the installer has to fix is not this skill's job, and a skill that starts rebuilding its own
prerequisites reads as a hang. `deepline billing` shows the credit balance for Step 6.

## Step 1 — Route on what you have: a new cascade, or a provider to add

**The opening request usually settles this — read it before asking.** "Build me a cascade" is a
new config; "add this provider to my cascade" is an extend. Ask only when it is genuinely
ambiguous, and branch on the request rather than on what a lookup returns, so two installers with
the same inputs take the same path:

- **No existing config** → new cascade. Continue to Step 2.
- **An existing config** → adding a provider. Skip to Step 3, derive the new provider, append its
  legs in placement order, and re-run the same checks. The runner is stateless — there is nothing
  to migrate and no separate upgrade path; the next run simply has more legs.
- **A hand-written Deepline play doing the same job** → this skill does not edit it. Say so, and
  offer to write a fresh config beside it.

## Step 2 — Ask only what nothing can derive, which is very little

**Almost nothing here is an interview.** The interface is prescribed, the fields follow from what
their providers can reach, and the ordering follows from measured hit rates. Everything with a
shape is derived and then shown in the plan for correction — which is a better question than an
abstract one, because they are correcting a document rather than guessing at a form.

**Do not ask any of these. Each has been tried and each is noise:**

| Do not ask | Because |
|---|---|
| what their list looks like | the interface is fixed; columns map onto it with `--columns` at run time |
| for column names up front | same |
| which fields to fill | it follows from what their providers can reach, and the skip flags decide per record |
| whether the billed tier may run | every billed leg is in the plan with its cost and gets written regardless; whether it fires on a record is a skip flag |
| which provider goes first | ordered by measured hit rate, shown in the plan |
| where finished records should go | the output CSV always has them; `callback_url` is a per-record input |
| for an API key, ever | it lives in an environment variable they export |

**One thing genuinely needs asking here, because no amount of reading produces it:**

> **Do their provider agreements permit sending these contact identities?** Ask once, record the
> answer. The cascade sends contact details to third parties on every row and cannot read a
> contract.

That is the whole of Step 2, and it is short by design rather than by omission. Everything else
someone might reach for — the destination, the fields, the ordering, the columns — is either
fixed by the interface, derived from what they hold, or decided per record at run time.

Then go to Step 3 and ask which providers they hold. That is the substantive question, and the
last one before they get a plan.

## Step 3 — Ask which providers they hold, then derive what each can actually do

**Do not assume a provider's shape and do not ship a list of known ones.** Ask what they pay
for, then follow `references/provider-adapters.md` for each: check whether Deepline already
integrates it (`deepline tools search "<provider>" --json`), find the spec, enumerate the
endpoints, classify each by what it produces and what it requires, and place it.

The placement rule is where the value is, and it is easy to miss: an endpoint needing a profile
URL lands after the finders, but **an endpoint that works from name + company can also be a
finder for the pivot itself** — and the pivot gates everything behind it. One provider
legitimately produces four or five legs in different positions. That is the point.

Then show the capability map and invite corrections. **Name a provider that turns out to add
nothing** rather than wiring it in for completeness: a leg that can never fire is config to
maintain and a line in the plan that misleads the next reader.

If a provider's documentation cannot be read, **say so and ask them to paste the endpoint list
or spec.** Never infer an endpoint path — a fabricated URL writes a leg that fails on every row
while the config looks correct.

### Then close the input gaps — this is where the money is

**A free endpoint is only free if you can satisfy its inputs.** Most flat-rate email and phone
endpoints want a profile URL and nothing else, so "we have a free email provider" and "email is
free" are different claims. Before pricing anything, walk every free-tier endpoint's required
inputs and solve for each one, in this order:

1. **Is it always supplied?** Then there is no gap.
2. **Can a free provider produce it?** Check *the same provider first* — a vendor whose email
   endpoint needs a profile URL very often sells a finder for that profile URL too, on the same
   flat-rate plan. Then check every other free provider. This is the outcome most often missed,
   because the natural reading of a capability map is "this provider does email" rather than
   "this provider can also produce the thing its own email endpoint requires".
3. **If no free provider can, use a credit-billed Deepline tool or play — and show why that is
   the cheap move.** This is not a concession. One paid lookup that resolves a profile URL
   converts the email and phone legs behind it from billed to free. **Put the arithmetic in the
   plan**: one lookup at roughly N credits, replacing the billed email and phone waterfalls at
   roughly X and Y, every number read from `deepline tools describe`. If the numbers do not favour
   it, say that too and leave the field unreachable.
4. **If nothing can produce it, say which fields are unreachable** — plainly, at the plan.
   Writing legs that will always report `blocked_missing_input` is worse than not writing
   them: it looks like coverage and delivers nothing.

The Deepline candidates for the billed tier, each confirmed with `describe` on 2026-10-01:

| Field | Deepline route | Needs |
|---|---|---|
| company domain | `crustdata_v3_company_enrich` (0.8 credits/result) | company name (`names`, an array) |
| contact LinkedIn | `prebuilt/person-to-linkedin-harvestapi` (play) | first + last name; domain and company sharpen it |
| work email | `prebuilt/name-and-domain-to-email-waterfall` (play) | first + last name + domain |
| mobile phone | `prebuilt/person-to-phone` (play) | first + last name; domain, email, LinkedIn URL sharpen it |
| email verification | `zerobounce_validate` (0.28 credits/result) | an email |

Run `deepline plays search email --json` / `deepline plays search phone --json` for others;
never write a play ID you have not described.

An enabling lookup is a leg like any other, placed before the legs that need it. It carries an
**opt-IN** flag rather than an opt-out: nobody asks for a company domain for its own sake, so it
runs when something downstream needs it, runs when a caller explicitly sets `want_company_domain`,
and reports `not_needed` otherwise. That is what stops it spending on a record where every field
it feeds was skipped — and it is also why a field that a provider can reach for free is still
worth a leg, because there is now a way to ask for it.

## Step 4 — Propose the cascade plan, get it approved, then set up the keys

**Nothing runs and no key is set up until they have seen the whole cascade and said yes.** A
capability map says what each provider *could* do; the plan says what you intend to actually
run, in order. They are different documents and only the second is approvable.

Show one plan, in their words, not in config syntax:

- **The cascade in order** — every leg, which provider fills it, what it needs to run, and
  where the free tier ends and the credit-billed tier begins.
- **What each field costs when it falls all the way through**, read from `deepline tools
  describe`.
- **What will NOT be filled** — and there is exactly one reason: no provider they hold, and no
  Deepline route, can reach it. Say which, plainly, rather than letting them find out from the
  output. **Never present a field as off because they said they did not want it** — that is a
  skip flag on a record, and the leg gets written regardless.
- **Which providers you are deliberately leaving out, and why** — an endpoint that duplicates
  one already ahead of it, or one whose input nothing upstream produces.
- **The environment variables they will need to export**, one line each, so the setup cost is
  visible before they agree rather than after.

Then stop and wait. **Ask them to change the plan, not to approve it** — "anything wrong with
this order, or any provider you'd rather not use for a field?" invites the correction that a
bare yes/no does not. Rework and re-show as many times as it takes; this is the cheapest point
in the whole run to change your mind, and the last one before their time gets spent.

**Only once the plan is agreed, walk them through the keys it needs.** Deepline-managed legs
(`deepline_tool`, `deepline_play`) need no key at all — Deepline holds those provider
credentials and bills credits. Only an `http` leg to their own flat-rate provider needs one, and
it reaches the call through an environment variable **they** export in their own shell, so the
agent only ever learns a name. Follow the credential section of `references/provider-adapters.md`.

**Give them the exact header, not a generic instruction.** You read the provider's spec at
Step 3, so you already know whether it wants `x-api-key: <key>` or `Authorization: Bearer <key>`
or something else — and those are not interchangeable; a provider handed the wrong one answers as
though no auth was sent. That goes in the leg as `key_header` (and `key_prefix: "Bearer "` where
needed); the installer supplies only the value, into the variable:

```
# in their own terminal or shell profile, never pasted into chat
export FLAT_PROVIDER_A_KEY=...
```

**Then confirm it is set without reading it**: `test -n "$FLAT_PROVIDER_A_KEY" && echo set`.
The runner refuses an http leg whose variable is empty, naming the variable. Whether the key is
*right* is unverified until a call runs — **say that out loud, and confirm it at the smoke test
in Step 6.**

A provider whose variable never gets set is a provider whose legs are not written; say which
field lost a tier rather than writing a leg that cannot authenticate.

**Never ask for a key in chat. If one is offered, decline and point back at the environment
variable.** Anything pasted into the conversation is in the transcript.

## Step 5 — Write the config, then prove it without spending anything

Write the legs in placement order per `references/cascade-config.md`, starting from
`scripts/cascade-config.example.json`. Show the resulting cascade as an ordered list so they can
see what runs before what, and where the free tier ends and the billed tier begins.

Then two checks, both free:

```
python3 scripts/test_codegen.py <your config>
python3 scripts/cascade.py --config <your config> --dry-run
```

The first generates every handler the runner would execute, parses it, and runs it against a
fake context — no credentials, no network. The second validates every `deepline_tool` and
`deepline_play` leg against the live Deepline schema via `describe` (free) — an unknown ID,
an unknown input name, an unmapped required input, or a required input missing from `requires`
fails loudly — and refuses any credential-shaped config field, **calling nothing paid**.

Do not skip either. A parameter name guessed wrong fails at run time, which is *after* money was
spent on the legs above it, and a wrong response path reads as "not found" forever.

## Step 6 — Run one real record, twice

Price the smoke test first — at most one call per leg per record, at the prices in the plan —
and check the balance with `deepline billing`. **This spends credits. Say so, in the word, and
wait.**

Then two runs, and **read the output rather than the status**. **Gate on non-empty values, never
on completion** — a provider call can succeed and return nothing, and a wrong response path
returns null while reporting success.

**Run A — nothing supplied.** Everything has to be found, so this exercises the whole cascade:

```
python3 scripts/cascade.py --config <your config> \
  --record '{"contact_name":"<installer name>","company_name":"<their company>"}'
```

Use a contact whose answers the installer can eyeball. **The installer themselves is the
default** — they can check their own email and phone in seconds; swap in someone of theirs if
they would rather.

**Run B — one field supplied.** Take the contact LinkedIn URL that run A returned and send it
back in, with everything else identical:

```
python3 scripts/cascade.py --config <your config> \
  --record '{"contact_name":"<same>","company_name":"<same>","contact_linkedin":"<the URL run A found>"}'
```

This is the one case that proves the no-re-enrichment guarantee, and it is worth doing
deliberately rather than trusting the code: `contact_linkedin_source` must read `supplied`, **no
LinkedIn leg may have run at all**, and the email and phone legs must still fire using the URL
that was handed to them. A cascade that re-looks-up a supplied value works perfectly and quietly
charges for every field the caller already had.

Reusing run A's output rather than a hardcoded URL also means the fixture cannot rot.

Six things to confirm, because each is a distinct failure that looks like another:

1. A field that arrived populated reads `supplied`, and **no leg for it ran** — run B above.
   Reading `supplied` alone is not enough; that could be a label on a lookup that happened anyway.
2. A flat-rate hit is attributed to **that provider**, not to `supplied` — if a later leg on the
   same field relabels an earlier leg's find, provider hit rates become unmeasurable.
3. A miss on the pivot makes the legs behind it read `blocked_missing_input`, not `not_found`.
4. A record sent with `skip_phone` set reads `skipped` on phone AND no phone leg ran — which is
   what proves the flag governs spend rather than just labelling the output.
5. **A record with a skip set costs nothing on that field**, and an enabler nobody needs reads
   `not_needed` rather than firing. Send a second record with every skip set and confirm no leg
   ran — that is the cheapest proof that the opt-outs actually govern spend.
6. **Every HTTP leg actually authenticated.** This is the first moment a wrong key can surface,
   because nothing before it can check one. Read `leg_errors`: a `401` or `403` there means the
   key or the header is wrong. An unexpectedly empty result from a provider you expect to hit
   means the same thing until you have ruled it out.

Fix `tool_inputs` and `out_paths` here, where it is cheap.

## Step 7 — Run the list

One message, then stop and wait. It carries four things, and the last two are the ones a
cost-only gate would miss:

1. **The credit estimate, from the measured reach rate** — how many of the sample rows reached a
   billed leg, and the per-call prices from `describe`. **Quote it as a unit rate — per record,
   and per hundred records — and apply a volume only if they offer one.** Their CSV's row count
   is the volume when they have handed one over; otherwise ask for nothing. Say it is a rate
   measured on a handful of rows, not a forecast.
2. **The zero that is not a zero** — the flat-rate calls cost no Deepline credits, and they are
   not free: they bill against their own subscriptions, and they send each person's name, company
   and identifiers to those providers on every row.
3. **The write, in the word** — this writes one output CSV with the named fields per row, at the
   path they choose. It never modifies the input file.
4. **The destination, which the caller sets per record** — any row carrying a `callback_url`
   is POSTed there, email and phone included; one without it is not sent anywhere. Disclose that
   this is how it works rather than naming a URL, because there is no single destination — and
   nothing goes anywhere else.

On yes, run a small slice first, then the rest:

```
python3 scripts/cascade.py --config <cfg> --csv in.csv --columns map.json --out out.csv --limit 10
python3 scripts/cascade.py --config <cfg> --csv in.csv --columns map.json --out out_full.csv
```

Records run one at a time, so a large list takes a while; run it in the background and say so.
For a list in the thousands, the same legs can be written as a Deepline play (`.withColumn` per
leg, a prebuilt waterfall via `ctx.runPlay`) so Deepline runs rows concurrently — see the
deepline-plays skill. Keep the leg order, the `requires` gates and the provenance labels; they are
the design, the runner is just one host for it.

## Step 8 — Deliver, and say what was not covered

```
python3 scripts/cascade.py --report out_full.csv
```

The reach-rate report above: source histogram per field, records rejected at intake, records with
a leg error, fields that never resolved, and actual spend against the estimate (`deepline
billing` before and after). Then three things worth saying out loud:

- **A provider that never produced a hit is a leg to remove.** Name it.
- **A field that read `blocked_missing_input` more often than `not_found`** is a pivot problem,
  not a provider problem — the answer is another finder, not another email source.
- **`verified: true` with a domain mismatch is suspect, not clean.** Say how many.

### Then tell them how to actually use it — all three ways

**This is the step most likely to be left out.** A cascade nobody knows how to call is not
finished. There are three entry points and they suit different jobs; name all three.

**1. A CSV** — the common case, for a list they already hold.

> `python3 scripts/cascade.py --config <cfg> --csv <list> --columns <map> --out <result>`. Map
> your columns onto the interface in the `--columns` file — **your column names do not have to
> match**. The same config serves any number of lists.

**2. One record** — from a script, a job, another system.

> `python3 scripts/cascade.py --config <cfg> --record '<json>'` prints the finished record. Supply
> `callback_url` to have it POSTed onward as well; `source_ref` is echoed back unchanged for
> joining.

**3. As one stage of a pipeline** — where enrichment is one stage of several.

> Run the CSV form, then feed `out.csv` to the next stage — scoring, copywriting, routing — that
> needs a contactable person before it can run. Consume `contact_email_verified_only`, not
> `contact_email`.

**Say the two things that decide cost, whichever path they pick:** send any field they already
have and its lookups are skipped entirely, and set `skip_email` / `skip_linkedin` / `skip_phone`
per record for anything they do not want — neither needs a config change, and phone is the
dearest field in the cascade.

Then offer the answer sheet.

## What this skill does not claim

- The two credit figures in the opening claim were measured on **one contact, in one workspace,
  on two dates, on Clay's native cascades**. They show that the paid phone cascade dominated that
  graph's cost. They are not a benchmark, not a Deepline price, and not a yield you should expect.
- No hit rate is claimed for any provider. The whole point of the source histogram is that hit
  rates are a property of the installer's data and have to be measured, not quoted.
- Nothing is claimed about a provider's coverage, accuracy, or geography. Several flat-rate
  phone products are region-limited, which shows up as fall-through to the billed tier rather
  than as an error.
- Verification proves a mailbox is deliverable. It does **not** prove the address belongs to the
  person, which is why the domain comparison is reported separately and why a mismatch is
  flagged rather than resolved.
- The skill has not been run against every provider it names in its description. The derivation
  procedure is general; a specific provider's spec may be unreadable or may have changed.
- The `generic_http_request` response envelope (provider body under `data`) is taken from the
  runner's design, not from a live call recorded here. `out_paths` lists both `data.<x>` and the
  bare path so a different envelope still resolves; confirm on the first smoke-test record.
- It does not measure latency. Find-email lookups are known to be asymmetric — a miss can take
  far longer than a hit — so a batch's wall time is not the per-record time times the rows.

## What good looks like

A good run ends with **every filled field naming the provider that filled it**, and with the
four non-hit outcomes distinguishable: `supplied`, `skipped`, `blocked_missing_input` and
`not_found` are four different facts, and a run that reports them as one is a failed run even if
every field is populated — the numbers it produces cannot be acted on.

The reach-rate report should let a reader see the *shape of what is missing*: how many records
never reached a tier at all, which field blocked the rest, and what it cost. A good report often
recommends removing a leg.

A thin run looks different and should be said out loud rather than dressed up: most fields
`not_found` with the pivot empty means one missing finder is starving the whole cascade, and the
fix is upstream. Most fields `blocked_missing_input` means a precondition is never satisfied —
usually a company domain the caller was expected to supply. A run where everything reads
`supplied` did no work and cost nothing, which is a correct outcome and worth stating plainly.
Many `leg_errors` means a key or a header is wrong, not that the provider has no data.

A failed run is one that returns values with no provenance, or that reports a credit estimate
without naming the output and the callback. Both are unreviewable.

## Rules

- **NEVER ask for, accept, or handle an API key.** A flat-rate provider's key lives in an
  environment variable the installer exports; a leg names the variable in `key_env`. There is no
  code path that takes a key as an argument or a config value, and the runner refuses a
  credential-shaped config field.
- **NEVER print, echo or log a key to check it.** `test -n "$VAR" && echo set` proves it exists;
  only a smoke-test call proves it works.
- **NEVER report a key as working before a leg using it has run.** "Set" and "authenticating" are
  different claims and only the smoke test can make the second one.
- **Say which things were checked and which were taken on trust.** Deepline tool and play IDs and
  their inputs are validated against live schemas by `--dry-run` — those are verified. An http
  leg's URL, body and key are not checked until a call runs. An installer who thinks both were
  verified will not look at the one that was not.
- **NEVER write a tool or play ID you have not described.** `deepline tools describe` /
  `deepline plays describe` are free; a guessed ID fails at `--dry-run` at best.
- **Prefer a Deepline-native tool over an http leg when Deepline already integrates the
  provider** (`deepline tools search "<provider>"`). It needs no key handling — but it bills
  Deepline credits, not their flat-rate plan, so say which tier it lands in.
- **NEVER ask for column names up front.** The interface is prescribed; a list's columns map onto
  it with `--columns` at run time, and one config serves many lists.
- **NEVER ask anyone to set up a key before the plan is agreed.** Getting a key out of a vendor
  dashboard is their work, and work spent on a leg that gets cut is work wasted.
- **NEVER decide in the config what a caller can decide per record.** Write a leg for every
  field every provider they hold can reach. The ONLY reason a field has no leg is that nothing
  they have can fill it. The skip flags decide what is attempted, per record, at run time.
- **An enabling lookup that is worth paying for IS the cheap option.** Do not refuse to spend on
  a profile URL and then let the email and phone legs fall through to the billed waterfalls. Show
  the arithmetic and let the installer decide.
- **NEVER stop at the config.** The run is finished when the config is validated and
  smoke-tested, and the list is run or the command handed over. Stopping earlier leaves a file and
  no enrichment.
- **NEVER run from a plan nobody saw.** The capability map is what a provider could do; the
  plan is what you intend to run. Only the second is approvable, and it is approved in their
  words rather than in config syntax.
- **NEVER overwrite a supplied value, and never blank a populated field.** This skill fills gaps.
- **NEVER POST a record anywhere but the `callback_url` that record itself carried.** The
  installer names no destination; each record chooses, and a blank field means nothing is sent.
- **The credit estimate is computed on rows that REACH the paid tier, not rows that get an
  answer.** A miss can still bill; a waterfall play pays for every provider it tries before one
  hits. Estimating on hits is the most likely way this comes in low.
- **Name the job, not the vendor, in every step.** Which providers are in play is a declared
  input: ask which ones they hold, then read each one's spec.
- **Read the documentation before probing, and verify with a probe before relying on it.** One
  provider's published request property was simply wrong; the live API named a different one.
- **Judgment lives in deterministic code, never an LLM call.** Every decision here is
  deterministic.
- **NEVER run `deepline tools execute` or `deepline plays run` to "check" something.** Those
  spend; `describe` and `--dry-run` do not.

## Worked example

*Placeholder names throughout.*

An installer pays for two flat-rate providers and wants a cascade. They have no list ready yet;
that turns out not to matter.

**Step 0** states the posture: a config and an output CSV get written, Deepline and their own
providers get called per record, records carrying a `callback_url` get POSTed there, no API key is
ever handled — and no list is needed to configure any of it. `deepline preflight` returns cleanly.

**Step 1** routes: no existing config, so a new cascade.

**Step 2** asks one question — whether their provider agreements permit sending contact
identities. They confirm. Nothing else is asked, because nothing else changes what gets written.

**Step 3** asks which providers they hold and on what plan, then reads both specs. Provider A does
email and phone, both keyed off a profile URL, and *also* resolves a profile URL from name +
company. Provider B does email from name + domain, and a profile URL too. Neither turns up in
`deepline tools search`, so both are http legs. Closing the input gaps is what the map makes
obvious: **two legs land on the pivot before any email leg runs**, because without a profile URL
provider A's two best endpoints cannot fire at all. Deepline's
`prebuilt/person-to-linkedin-harvestapi` play can also resolve a profile URL from name + domain,
which matters in a moment.

**Step 4** puts the plan in front of them: nine legs in order, the free tiers, the billed email
and phone waterfall plays, the billed profile-URL enabler, and a note that company LinkedIn will
not be filled because nothing in the plan offers it. The arithmetic for the enabler is shown from
`describe` prices. They cut provider B's email leg, which sits behind provider A at the same cost
and adds no reach, taking it to eight. **Nothing is cut for being unwanted** — the billed phone
leg stays, because a record that does not want a phone sends `skip_phone` rather than needing a
different config. Only then are they asked to export two environment variables, and `test -n`
confirms both are set.

**Step 5** writes the config and runs both free checks. The dry run rejects the first version —
`prebuilt/person-to-phone` requires `first_name` and `last_name`, and the config mapped
`first_name` without listing it in `requires` — caught before anything was spent. Fixed, both
pass.

**Step 6** runs the two records. Run A sends the installer with nothing else: the pivot resolves
via provider A, then email and phone via provider A, verification `valid` with a matching domain.
Run B sends the same contact with the LinkedIn URL run A found — it reads `supplied`, **no LinkedIn
leg runs at all**, and email and phone still fire off the supplied URL. Then a ten-record slice,
one of which carries `skip_phone`: phone reads `skipped` and neither phone leg fires. `leg_errors`
is empty on every row, so both keys authenticated.

**Step 7** reports: 3 of the 12 records run so far reached a billed leg, so roughly 0.25 paid calls
per record, priced per hundred at the `describe` rates. Their list has 480 rows, so that is the
volume. The flat-rate calls cost no Deepline credits but send every contact's identifiers to both
providers on every row; one output CSV is written; any row carrying a `callback_url` is POSTed
there with email and phone included. They approve, and the full run goes in the background.

**Step 8**, over the first 48 records: 46 enriched, 2 rejected at intake for no company name. The
pivot resolved 40 times — 31 on provider A, 9 on provider B, which is the argument for having kept
both. Seven records fell through to the billed email waterfall. 22 records carried `skip_phone`,
so the dearest leg in the cascade never ran on them. One address verified true on a domain that
was not the company's, flagged as suspect. The recommendation: provider B never once won an email,
only the pivot — so drop its email leg and keep its finder.

Then the handoff, all three ways: the CSV command with their column map; the single-record
command for scripts; and the output CSV as the input to whatever stage comes next. With the
reminder that sending a field they already have skips its lookups, and the skip flags cost nothing
to change.
