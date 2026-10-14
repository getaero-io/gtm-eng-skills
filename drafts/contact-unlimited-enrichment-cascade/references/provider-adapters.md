# Adding a provider — derive the adapter from its own spec

**Read this before writing a single leg for a provider.** A leg written from memory of what
an API "probably" looks like builds a cascade that runs and returns nothing, and a `not_found`
caused by a wrong request field is indistinguishable from a genuine miss.

The procedure is seven steps. The first five cost nothing and touch no credential.

---

## 0. Is the provider already in Deepline?

`deepline tools search "<provider>" --json`, then `deepline tools describe <tool> --json`.
Deepline integrates many enrichment vendors natively (e.g. `quickenrich_employee_email_enrich`,
`quickenrich_employee_phone_enrich`). A native tool is a `deepline_tool` leg: no key handling,
inputs validated by `--dry-run`, and the provider's raw payload as the response. **But it bills
Deepline credits, not their flat-rate plan** — so it lands in the billed tier, priced from
`describe`. If what they hold is a flat-rate plan with that vendor, the http route below is what
keeps it free; say which, and let them choose at the plan.

## 1. Find the spec, in this order

| Try | Why it is first |
|---|---|
| `llms.txt` / `llms-full.txt` on the docs host | Written to be read by a machine; usually complete and current |
| An OpenAPI document (`/openapi.json`, `/api-reference/*.openapi.json`) | Authoritative on required-vs-optional and exact property names |
| The docs pages themselves | Fine, but watch for pages describing an older version |

**Documentation before probing.** Do not discover an API by firing requests at paths that
might exist. Probing comes at step 6, to *verify* what the docs said — not to find it.

**If the spec cannot be read, say so and stop.** Some docs sites render entirely in the
browser and return nothing useful to a fetch. That is a real outcome: ask the installer to
paste the endpoint list or the OpenAPI file. **Never infer an endpoint path.** A fabricated
URL produces a leg that fails on every row, and the config will look correct.

## 2. Enumerate the endpoints

For each one, record: method · path · auth header name and format · request shape (which
properties, which required) · response shape (where the value actually sits).

## 3. Classify each endpoint by what it PRODUCES

Map it onto the record contract. An endpoint that produces nothing in this list is not part
of this cascade, however useful it is elsewhere:

| Record field | What counts |
|---|---|
| `company_domain` | a company's web domain from its name |
| `company_linkedin` | a company's LinkedIn URL |
| `contact_linkedin` | a person's profile URL — **the pivot** |
| `contact_email` | a work email address |
| `contact_phone` | a mobile or direct number |
| `contact_email_verify_status` | a deliverability verdict on an address you already hold |

Note the **response path** the value arrives on, and note more than one where the shape
varies. That list becomes the leg's `out_paths`, which is scanned rather than pinned.

## 4. Classify each endpoint by what it REQUIRES

This is the half that decides placement, and it is the half most easily skipped:

- a person's LinkedIn URL
- name + company name
- name + company domain
- an email address
- a bare domain

Whatever it requires becomes the leg's `requires` list, in record-field terms. `requires` is
what makes a leg **skip** rather than fire and die: provider inputs marked required reject an
empty value outright, so a leg whose input was never found must not run at all.

## 5. Place the leg

Two rules, and the second is where the value is:

**An endpoint that needs the pivot lands after the pivot finders**, with
`requires: ["contact_linkedin"]`. Most flat-rate email and phone endpoints are this shape.

**An endpoint that works from name + company can ALSO be a pivot finder.** Add it a second
time, with `field: "contact_linkedin"`. This is the case worth hunting for: the pivot gates
everything downstream of it, so a provider that can fill the pivot itself is worth more than
its own email endpoint. One provider legitimately produces four or five legs in different
positions — that is the point, not duplication.

**Then order by the one boundary that costs money.** Every flat-rate leg goes above every
credit-billed leg. Inside the flat-rate tier, ordering saves nothing at all — every call
costs the same zero — so order by measured hit rate and say that the order was measured
rather than chosen. Claiming a cost saving from ordering free calls is a claim the installer
cannot check and that is not true.

## 6. Verify with one probe per endpoint — because docs lie

Measured, and not an edge case: one provider's published docs named the request property
`linkedin_url`; the live API rejects that and names `person_linkedin_url`. The docs were
simply wrong, and the failure mode was an empty result rather than an error.

So probe each endpoint once with an identity whose answer you already know, then:

- confirm the request shape the docs claimed
- read the **raw** response and confirm or extend `out_paths` from what actually came back
- check a miss as well as a hit — some providers return `200` with a `not_found` status
  rather than an error, and the leg must read that as empty, not as a value

**The probe runs through the runner, never as a hand-built request.** Write a config holding
just that one leg and run `cascade.py --record` on the known identity: the key is read from the
environment variable inside the runner and never reaches this conversation, a file, or a
process listing. Read `leg_errors` and the raw result. Never paste a key into a `curl` or a
`deepline tools execute generic_http_request --input` — that puts it in the transcript and the
shell history. If the probe cannot be run that way, the first smoke-test record is the
verification instead — one step later, same purpose. Either way it is verified before anyone
relies on it.

## 6b. Close the input gaps — solve for the free tier's preconditions

Steps 3 and 4 give you, per endpoint, what it produces and what it needs. Now solve the needs,
because **a free endpoint whose input you cannot get is not free — it is absent.**

For every required input that is not always supplied, in order:

| Try | Outcome |
|---|---|
| **The same provider's other endpoints** | Best, and the one most often missed. A vendor whose email endpoint wants a profile URL usually sells a finder for that URL on the same flat plan. Check its whole endpoint list, not just the one you came for. |
| **Any other free provider** | Still free. Add it as an extra leg on that field — several legs on one field is how a waterfall is expressed and costs nothing extra when they are all flat-rate. |
| **A credit-billed Deepline tool or waterfall play** | Acceptable, and frequently the *cheapest* option overall. Price it from `describe`: one paid lookup that yields a profile URL can convert the email and phone legs behind it from billed to free. Put that arithmetic in the plan. |
| **Nothing can produce it** | Say which fields become unreachable. Do not build legs that will always report `blocked_missing_input`. |

**The arithmetic to show, every time:** cost of the enabling lookup, against the cost of the
billed legs it displaces, every number from `describe`. A profile URL that saves a billed email
and a billed phone waterfall is a clear win on any record wanting a phone number, and a marginal
one on a record wanting only an email. Those are different recommendations — make them separately rather than
quoting one number.

**An enabling leg carries no caller opt-out.** Nobody asks for a company domain. It runs when a
leg requiring it is still wanted and still empty, and reports `not_needed` otherwise — which is
what keeps it from spending on a record whose dependent fields were all skipped.

## 7. Emit the leg

See `references/cascade-config.md` for every field. The shape of an HTTP leg:

```json
{
  "key": "email_flat_c",
  "field": "contact_email",
  "skip": "skip_email",
  "source": "<short provider label>",
  "tool_name": "Work email (<provider>)",
  "requires": ["contact_linkedin"],
  "provider": {
    "type": "http",
    "method": "POST",
    "url": "<exact endpoint from the spec>",
    "key_env": "<PROVIDER>_API_KEY",
    "key_header": "<the provider's auth header, from its spec>",
    "body": { "<provider's property name>": "<record field>" }
  },
  "out_paths": ["data.email", "email"]
}
```

`source` is a label, and it is how hit rates become measurable — give each provider its own.

---

## Getting the key to the call — the installer's shell, not the conversation

A Deepline-native leg needs no key: Deepline holds those provider credentials. Only an `http`
leg to the installer's own provider does, and the runner reads it from an **environment
variable** named in the leg's `key_env`. The agent only ever learns that name.

### What they do

1. **Name the variable after the provider** — `BLITZ_API_KEY`, `HUNTR_API_KEY`. UPPER_CASE, one
   per provider. That name goes in the config; the value never does.
2. **Export it in their own terminal**, or in a shell profile / `.env` file they `source` and
   keep out of version control:
   ```
   export BLITZ_API_KEY=...
   ```
   The runner inherits it from whatever shell launches it, so it must be set in the shell the
   agent's commands run in. If they keep keys in a dotenv file, `source` that file in the same
   command that runs `cascade.py`.
3. **Confirm it exists without printing it**: `test -n "$BLITZ_API_KEY" && echo set`.

### The header differs per provider — read the spec, do not guess

**Give them nothing to configure but the value.** You read the provider's spec at step 1, so
you write `key_header` (`x-api-key`, `Authorization`, ...) and `key_prefix` (`"Bearer "` where the
spec says so) into the leg yourself.

Four observed on 2026-09-11, as illustrations of the *shapes* you will meet rather than a list
to consult instead of the spec. **Any of these can change, and one is unverified:**

| Provider | Header observed |
|---|---|
| BlitzAPI | `x-api-key` — also confirmed against a live call |
| Huntr (tryhuntr.com) | `x-api-key`, with a vendor-prefixed token as the value |
| MoltSets | `Authorization`, with a `Bearer ` + vendor-prefixed token as the value |
| QuickEnrich | `Authorization`, with a `Bearer ` + token as the value (also native in Deepline — see step 0) |
| GetLeads | **could not confirm** — its docs render client-side and returned nothing readable |

Header names only, deliberately. **Never write an example token into a file** — not even a
fake one shaped like a real prefix. Anything token-shaped in a package gets flagged by a
credential scanner, and a reader who copies a plausible-looking placeholder into a real
variable has a key that silently does not authenticate.

The point of the table is that the two shapes are not interchangeable and a provider will simply
answer as though no auth was sent if you pick the wrong one. Always take the header from the spec
you read for *that* provider.

### If the provider needs a token exchange rather than a static header

The runner sends one static header. A provider whose spec describes a login call returning a
short-lived token does not fit an `http` leg as written; say so at the plan. The nearest routes
are a Deepline play that does the exchange with `ctx.fetch` and reads the credentials from
`deepline secrets` (`deepline secrets set NAME --from-env NAME`, values never in argv), or
leaving that provider out.

### The key cannot be verified before a call — plan around it

The runner checks only that the variable is non-empty. Whether the key is valid, and whether the
header is the one the provider wants, surfaces at the first call. So state plainly that the key
is unverified until the smoke test, and at the smoke test read `leg_errors` for each http leg. A
`401` or `403` is a wrong key or header. A provider you expect to hit returning nothing is the
same suspect until ruled out.

### What CAN be detected, and what cannot

Be precise about this with the installer — assuming the wrong half was checked is how a broken
key ships:

| | Detected? |
|---|---|
| Deepline tool and play IDs | **Yes** — `--dry-run` describes each one; an unknown ID fails |
| Their declared inputs | **Yes** — validated against the live schema, including required inputs |
| An http leg's variable being set | **Yes** — an empty variable is a loud failure naming it |
| **An http leg's URL, body, header and key being right** | **No.** Taken on trust until a row runs |

**Three rules, and they are not negotiable.**

- **Never ask for a key in chat, and never accept one.** If a key is offered, it goes into
  their environment variable instead. The runner has no code path that takes one.
- **Never put a key in the config, a header literal, or a command line.** The runner refuses a
  credential-shaped config field for this reason.
- **Never print a key to check it.** `test -n` proves it is set; only a call proves it works.

## What to tell the installer when a provider adds nothing

A provider whose endpoints all need the pivot, on a workspace that has no pivot finder, adds
nothing until a finder exists. **Say that rather than wiring it in for completeness** — a
leg that can never fire is config to maintain and a line in the plan that misleads whoever
reads it next. The same goes for a provider whose only endpoint duplicates one already
ahead of it in the same tier at the same hit rate.
