# The config schema

One JSON file describes the whole cascade. `scripts/cascade-config.example.json` is a working
copy of everything below, at placeholder values.

The runner is stateless: there is no state file beside the config, and adding a provider is
appending legs and running again. The config never holds a credential.

## Top level

| Key | Required | What it is |
|---|---|---|
| `name` | no | A label for the cascade. Informational. |
| `verified_statuses` | no | Which verifier verdicts count as verified. Default `["deliverable","valid"]`. A catch-all or risky verdict (`zerobounce_validate` returns `catch-all`) is deliberately **not** in the default — add one only as a declared decision. |
| `capture_prefix` | no | The prefix marking fields a leg captured beyond its own. Default `person_`. Emit lists them in `captured_fields`. Never end a capture key in `_source`: that suffix is reserved for provenance. |
| `sentinels` | no | Response values that mean "nothing", not a value. Default `["n/a","none","null"]`. |
| `callback` | no | `{"enabled": true}` by default, and **leave it that way** — `callback_url` is a **per-record** input, so the caller decides per record whether anything is sent. A record without one is not POSTed. `{"enabled": false}` exists for a setup that must never POST anywhere; it is not how you say "we do not use callbacks". |
| `legs` | yes | The cascade, in order. |

Retired keys that once carried credentials (`http_secrets`, `http_secret_header`, `client_env`)
are a hard failure with a migration message, never a silent downgrade.

## A leg

| Key | Required | What it is |
|---|---|---|
| `key` | yes | Unique. Names this leg's resolve handler, its `need_<key>` flag and its entry in `leg_errors`. |
| `field` | yes | Which record field this leg fills. Must be in the record contract below. **Several legs may share a field — that is how a waterfall is expressed.** |
| `want` | no | Which caller opt-IN asks for this leg's field as an output, from the list below. For an enabling lookup — a field nobody asks for on its own — this is the right flag: the leg fires whenever a downstream leg requires its field, and otherwise only when the caller sets this. A leg carries `skip` or `want`, never both. |
| `skip` | no | Which caller opt-out switches this leg off, from the list below. **Omit both for a pure enabling lookup** — a field nobody asks for that exists because legs after it cannot run without it. An enabler fires only when a leg requiring its field is still wanted and still empty, and reports `not_needed` otherwise. That is what stops it spending on a record whose consumers were all skipped. |
| `source` | yes | The provenance label written to `<field>_source` on a hit. Give each provider its own — this is what makes hit rates measurable. |
| `tool_name` | yes | Human label for the leg, shown in plans and the dry-run listing. |
| `requires` | no | Record fields that must be populated before this leg may run. Missing one means the leg **skips** and reports `blocked_missing_input`, rather than firing with an empty required input and killing the run. |
| `provider` | yes | How the call is made. Three types plus `none`, below. |
| `tool_inputs` | for `deepline_tool` / `deepline_play` | `{provider's parameter name: record field}`. A list value (`["company_name"]`) sends a one-item array, for inputs like `names`. An empty field is omitted. Validated against the live Deepline schema by `--dry-run`. |
| `input_static` | no | Literal inputs merged into the payload (`{"exact_match": true}`). Also validated. |
| `out_paths` | yes | Ordered candidate response paths, scanned until one yields a value. Dotted; a list is indexed at `[0]`. |
| `capture` | no | `{record field: response path}` for data the provider returned beyond this leg's own field. Keeps what has already been paid for. |

## Provider types

**`deepline_tool`** — one Deepline tool call, billed in Deepline credits.

```json
{ "type": "deepline_tool", "tool": "zerobounce_validate" }
```

Runs `deepline tools execute <tool>`. Find candidates with `deepline tools search "<intent>"
--json`, confirm with `deepline tools describe <tool> --json` (input fields, `pricing`). The
response is read from the tool's raw provider payload, so `out_paths` are the provider's own
field names (`status`, not `result.status`).

**`deepline_play`** — a Deepline play, usually a prebuilt waterfall, billed per provider it
reaches.

```json
{ "type": "deepline_play", "play": "prebuilt/name-and-domain-to-email-waterfall" }
```

Runs `deepline plays run <play>` and waits. The runner finds the play's output object by the
`required` keys of its `outputSchema`, so `out_paths` are output-schema names (`email`, `phone`,
`linkedin_url`). Confirm with `deepline plays describe <play> --json`; list candidates with
`deepline plays search email --json`.

**`http`** — your own flat-rate provider, through Deepline's `generic_http_request` tool (priced
Free; the provider bills your subscription).

```json
{ "type": "http", "method": "POST",
  "url": "https://api.example.test/v1/person-email",
  "key_env": "FLAT_PROVIDER_A_KEY",
  "key_header": "x-api-key",
  "body": { "person_linkedin_url": "contact_linkedin" },
  "body_static": { "country": "US" },
  "query": { "full_name": "contact_name" },
  "query_static": {},
  "headers": { "Accept": "application/json" } }
```

| Field | Notes |
|---|---|
| `url` | **Required, `https://`.** `generic_http_request` refuses auth-like headers over plain http, and blocks private and localhost targets. |
| `key_env` | **Required.** The NAME of the environment variable holding the key, UPPER_CASE. Read at call time, sent only in `key_header`, never written to the config, a record or any output. An empty variable is a loud failure naming it. |
| `key_header` | **Required.** The provider's auth header, from its spec: `x-api-key`, `Authorization`, ... |
| `key_prefix` | Optional. `"Bearer "` for a bearer-token provider. |
| `method` | Defaults to `POST`. |
| `body` / `body_static` | `body` maps provider property → record field; `body_static` adds literals. The JSON body is rebuilt after every leg, so a leg can reference a field an earlier leg resolved. If any mapped field is empty the body is empty, which is why `requires` matters. |
| `query` / `query_static` | Same, for `GET` endpoints. |
| `headers` | Static, non-auth headers only, merged over `Content-Type: application/json`. **Auth never goes here** — a credential-shaped header name is refused. |

`generic_http_request` returns the provider's body under `data`, so a top-level provider field is
usually at `data.<name>` — list both spellings in `out_paths` and let the scan decide.

**`none`** — the leg is skipped entirely. **This means "no provider is available for this", not
"a field the installer does not want".** Keeping the leg in the file with `"type": "none"`
documents a provider that could be bound later.

Never reach for `none` to switch a field off. What gets attempted is a **run-time** decision made
by the skip flags on each record, so a field nobody is interested in this week still gets its leg
and they simply set its flag. Using `none` for that forces a config edit the moment they change
their mind, and it hides from the plan that a provider for that field exists at all.

## The record contract

Fixed, not a per-config knob. This is a *contact* cascade, and these are what a contact is.

**The interface** — what `--record` takes and what a CSV's columns map onto with `--columns`:
`contact_name` and `company_name` (required) · `contact_email` · `contact_linkedin` ·
`contact_phone` · `company_domain` · `job_title` · the three skip flags · the two want flags ·
`source_ref` ·
`callback_url`.

**The record** adds what the cascade derives and fills internally: `first_name` · `last_name` ·
`company_linkedin` · `contact_email_verify_status`.

A list needs nothing up front. `--columns map.json` (`{"contact_name": "Full Name", ...}`)
maps its columns onto the interface at run time, so one config serves many lists.

Opt-out flags: `skip_linkedin` · `skip_email` · `skip_phone` — **absent means false, so the work
happens.**

Opt-in flags: `want_company_domain` · `want_company_linkedin` — **absent means false, so nothing
is fetched for its own sake.** These fields still fire whenever a leg downstream requires them;
the flag only asks for one when nothing else needs it. Only an explicit `true`/`1`/`yes`/`on` switches a field off, which means a caller who
has never heard of these gets the full cascade rather than silent empty fields.

The three contact fields are what the cascade exists to fill, so they are opt-out. The two
company fields are plumbing that can also be requested, so they are opt-in — the opposite
polarity would fetch a domain on every record where one happened to be missing.

**A skipped field is still fetched when a non-skipped field requires it.** `skip_linkedin` means
"do not fill this for its own sake"; if email is wanted and the email provider needs a profile
URL, the URL is still resolved, because the alternative is that email silently cannot run. To
stop every LinkedIn lookup, skip the fields that depend on one too. Say this at the plan rather
than letting someone discover it in a bill.

`contact_name` and `company_name` are required on every record; first and last name are derived
from the one name. Everything else supplied is one lookup not made.

## What comes out

Every field at its final value, plus `<field>_source` for each. **The source is a closed
set, and every value means something different:**

| Value | Means |
|---|---|
| `supplied` | it arrived populated; nothing was looked up |
| *a provider's label* | that provider found it |
| `not_found` | a leg ran and came back empty |
| `skipped` | the caller switched the leg off |
| `blocked_missing_input` | a field the leg depends on was never found, so it never ran |
| `not_needed` | an enabling lookup nothing downstream asked for — it cost nothing |

A seventh value, `unknown`, exists **inside the runner only**: intake stamps it on any field
that arrived empty, and each leg's resolve overwrites it. It never reaches the output contract,
because a field with no leg has its source stripped on the way out — so a source key existing in
the output tells you a leg for that field exists. Verified by running the generated code.

**`supplied`, `skipped`, `blocked_missing_input`, `not_needed` and `not_found` must never be
conflated.** "We already had it", "you told us not to look", "we could not even try", "nothing
wanted it" and "we looked and found nothing" are five different facts, and folding any of them
together makes every provider hit rate downstream meaningless — which is the whole reason for
running a waterfall rather than one call.

Plus, from emit: `contact_email_verified` · `contact_email_verified_only` (blank unless
actually verified — **this is what downstream automation should consume**) ·
`contact_email_domain_match` · `captured_fields` · `filled_fields` · `filled_count` ·
`record_json` · `source_ref` echoed back so a caller can join the result. Beside the contract,
not in it: `leg_errors` (per-leg call failures) and `callback_status`.
