---
name: deepline-ads-audiences
description: "Use this skill when building, enriching, auditing, or uploading B2B paid ads audiences to Google Customer Match, Meta/Facebook Custom Audiences, or LinkedIn Matched Audiences. Triggers on phrases like '/deepline-ads-audience', '/deepline-ads-audiences', 'upload this audience', 'create custom audiences', 'personal email hashes', 'increase Facebook match rate', 'Google ads audience', 'Meta audience', 'FB audience', or any workflow that turns CRM/customer/contact data into paid ads upload lists. Skip for outbound prospecting sequences, cold email, or pure campaign copywriting."
---

# Deepline Ads Audiences

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

## CLI resolution

Run `deepline` when it is available. If the shell reports that command is missing, use `<workspace-root>/.deepline/runtime/bin/deepline` (or the npm-created `.cmd` shim on Windows). If neither exists, follow `https://code.deepline.com/INSTALL.md` to set up Deepline.

Build high-quality ABM paid ads audiences from first-party customer or prospect lists. This skill is for paid ads audience upload and evaluation, not outbound.

Names in this skill are starting hints. Run `deepline tools search audience --json` and `deepline tools describe <tool_id> --json` before executing because tool names and payload shapes can change. Tool search accepts an intent query or, for structured filtering, `--categories` and/or `--search_terms`; a filter-only search needs at least one of those flags. Use commas for multiple filter values, and put provider names in the query rather than using a `--prefix` flag.

## Before You Start

Use the full recipe when the user asks to enrich and upload audiences to Facebook/Meta and Google:

→ Read `recipes/enrich-and-upload-facebook-google.md`.

Use the max-coverage recipe when the user asks for "max coverage", "maximum match rate", "keep increasing coverage", "get to 75% coverage", or asks to exhaust LinkedIn/personal-email/hash options:

→ Read `recipes/max-coverage-audience.md`.

This skill is not for cold outbound, sequencing, or copywriting. Personal emails here are used to improve paid ads matching, not to contact people directly.

## Decision Matrix

| User says                                                                | Do this                                                            | Read                                                      |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------ | --------------------------------------------------------- |
| "max coverage", "highest match rate", "keep increasing coverage"         | Run the explicit max-coverage ladder with budget gates.            | `recipes/max-coverage-audience.md`                        |
| `/deepline-ads-audience`, "enrich and upload to FB/Google"               | Run the full paid ads audience recipe.                             | `recipes/enrich-and-upload-facebook-google.md`            |
| "sample ABM segment", "do the example workflow"                          | Follow the reusable high-priority ABM segment recipe.              | `recipes/sample-abm-segment-example.md`                   |
| "use ContactOut hashes", "hashed identifiers", "LinkedIn URLs to hashes" | Plan a bulk pass beside the ladder, not a waterfall step.          | `shared/contactout-hash-pool.md`                          |
| "what is a hash", "why is my match rate low", first-time user            | Explain the mechanic before quoting a plan.                        | `shared/audience-basics.md`                               |
| encoded/internal-identifier LinkedIn URLs (`/in/ACwAA…`), "API rejected my LinkedIn URLs", "convert LinkedIn URLs" | Normalize `person_linkedin_url` before upload: drop encoded, recover vanity. | Step 4 → "Normalize LinkedIn URLs" (this file)            |
| "Make sure hashes are not double hashed"                                 | Run the no-double-hash audit play before upload.                   | `plays/audit-no-double-hash.play.ts`                      |
| "enrich this list", "buy personal emails/hashes", "run the ladder"       | Run the waterfall. Each layer only sees rows still missing a hash. | `plays/enrich-audience-waterfall.play.ts`                 |
| "Compare enriched versus unenriched"                                     | Build both hash-only datasets and report lift.                     | `plays/enrich-audience-waterfall.play.ts`                 |
| "include phone numbers", "add phones"                                    | Hash existing phones digits-only with country code.                | `shared/upload-failure-modes.md`                          |
| "what was the match rate", "did it match"                                | Read `contactIdInfo.matchRatePercentage`, not the range enum.      | `shared/upload-failure-modes.md`                          |
| "put it in a sheet", "customer will upload"                              | Publish the validated file to Sheets; verify by row count.         | `shared/upload-failure-modes.md`                          |
| "upload keeps failing", "422", "audience is locked"                      | Meta locks on write. Send the audience in one call.                | `shared/upload-failure-modes.md`                          |
| "Upload to Google"                                                       | Validate hash-only rows, create Google audience, sync, readback.   | `plays/upload-google-hash-only-audience.play.ts`          |
| "Upload to Facebook and Google", "upload to FB/Google", "Meta + GAds"    | Validate once, then upload to Google and Meta.                     | `plays/upload-facebook-google-hash-only-audience.play.ts` |

## Default Workflow

1. Confirm rights, use case, and geography.
2. Discover uploadable ad accounts.
3. Build baseline and enriched audience objects.
4. Validate identifiers and expected match-rate lift.
5. Create separate platform audiences.
6. Upload rows.
7. Check status and report IDs, uploaded counts, invalid rows, and current build state.

## Ask about suppression before targeting

Every audience run has a second list hiding in it: the people who should never see the ad. Current customers, closed-lost accounts, active opportunities, employees, and recent converters.

Ask for it explicitly, because users rarely volunteer it and the failure is invisible. A suppression list that was never built, or that silently failed to sync, spends budget advertising to people who already bought.

The risk is asymmetric, which decides how to handle edge cases: an extra person on a suppression list costs a few unserved impressions, while a missing one costs real money and can annoy a customer. When you are unsure whether someone belongs on it, include them.

Suppression lists match on the same identifiers as targeting lists, so a work-email-only suppression list suppresses almost nobody. Enrich it with the same ladder, or it will not do its job.

## Expect different lift per platform

Enrichment does not pay off evenly. Meta gains the most from personal-email enrichment, because personal addresses are what people register with there. Google gains less, since a Workspace address is already a Google account and often matches from the baseline.

Set that expectation before spending. A user who was promised uniform lift reads a modest Google result as a failed run, when it is the expected shape.

## Explain the shape before you spend

Users new to paid ads usually have not met hashed identifiers before, and a plan that opens with provider names reads as an opaque menu. Before running the ladder, state the mechanic in one or two sentences so the user can judge the plan rather than approve it blindly:

> Ad platforms can only match people on identifiers those people gave the platform. Your CRM holds work emails; almost nobody signs up to Meta with a work address. These layers buy the personal identifiers that do match, cheapest first.

Say what each layer costs in Deepline credits and what it is expected to add, then ask for approval before the first paid layer. A user who understands the mechanic will make a better call on where to stop, which is the only decision that controls spend here.

`shared/audience-basics.md` holds the longer explanation, including what a hash is and why it is safe to send. Point the user there when they ask, or when the run is their first.

## Coverage Modes

Choose the coverage mode before spending credits. Record it in the run notes.

| Mode             | Use when                                                                        | Waterfall                                                                                                                                                                                                                                                                                | Stop condition                                                                                                                                |
| ---------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `cost_effective` | User asks for the default, low-cost, or first-pass enrichment.                  | Work-email baseline → Aviato personal hashes on all eligible rows → LimaData personal hashes on remaining personal-hash misses. Optionally a ContactOut bulk pass over rows that still lack a personal hash and have a LinkedIn URL, which runs beside the ladder rather than inside it. | Stop after the hash providers, report contacts still missing personal hashes, then ask before expanded fallback.                              |
| `max_coverage`   | User asks for highest match rate, max coverage, or to keep increasing coverage. | Work-email baseline → phone hashes already present → LinkedIn repair → Aviato personal hashes for all eligible rows → LimaData personal hashes → ContactOut bulk pass beside the ladder → raw personal-email waterfall → platform upload variants.                                       | Stop when no approved provider remains, budget cap is hit, marginal lift is below threshold, or rights/geo constraints block more enrichment. |

Never silently downgrade a `max_coverage` request to `cost_effective`. If a provider or credential is unavailable, report the gap and continue with the next approved provider rather than stopping early.

## Shareable Plays

This skill includes copyable play templates under `plays/`. Use them when the user asks for a repeatable or shareable workflow, not just a one-off CLI run.

Before running a template, check the installed surface when it is unclear:

```bash
deepline --help
deepline plays --help
```

Use `deepline plays` for the bundled templates. If `deepline plays` is unavailable, stop and ask for the Deepline SDK CLI to be installed or updated instead of approximating the upload through older command paths.

| Play                                                      | Purpose                                                                                                                                                        | Input                                                                                                                                                                     |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plays/build-hash-only-audience.play.ts`                  | Build baseline and enriched hash-only datasets from source CSV rows. Raw emails are normalized and hashed once. Provider hashes pass through as lowercase hex. | `{ "file": "input.csv" }`                                                                                                                                                 |
| `plays/audit-no-double-hash.play.ts`                      | Verify the final upload payload is hash-only, deduped, populated, includes provider hashes as-is, and does not contain hash-of-hash mistakes.                  | `{ "payloadFile": "upload.csv", "providerHashFile": "provider-hashes.csv", "providerHashColumns": ["aviato_hash", "limadata_hash"] }`                                     |
| `plays/build-contactout-hash-pool.play.ts`                | Batch LinkedIn URLs through ContactOut hashed identifiers into a deduped hash pool. Reports matched profiles, net-new hashes, and per-chunk results.           | `{ "file": "contacts.csv", "limit": 100 }`                                                                                                                                |
| `plays/upload-google-hash-only-audience.play.ts`          | Create a Google Customer Match list, upload hash-only rows, and read status back.                                                                              | `{ "file": "upload.csv", "account_id": "1234567890", "audience_name": "Segment enriched 2026-06-09" }`                                                                    |
| `plays/upload-facebook-google-hash-only-audience.play.ts` | Upload the same validated hash-only rows to Google and an existing Meta/Facebook Custom Audience.                                                              | `{ "file": "upload.csv", "google_account_id": "1234567890", "meta_ad_account_id": "act_123", "meta_audience_id": "456", "audience_name": "Segment enriched 2026-06-09" }` |
| `plays/report-google-coverage-lift.play.ts`               | After Google match rates populate, calculate coverage lift, estimated matched identifiers, spend efficiency, and a follow-up note.                             | `{ "account_name": "Customer Google Ads", "account_id": "1234567890", "baseline": {...}, "comparisons": [...] }`                                                          |

Recommended sequence:

```bash
deepline plays check ./plays/build-hash-only-audience.play.ts
deepline plays run --file ./plays/build-hash-only-audience.play.ts --input '{"file":"source.csv"}' --watch

deepline plays check ./plays/audit-no-double-hash.play.ts
deepline plays run --file ./plays/audit-no-double-hash.play.ts --input '{"payloadFile":"enriched_hash_only.csv","providerHashFile":"provider_hashes.csv","providerHashColumns":["aviato_hash","limadata_hash"]}' --watch

deepline plays check ./plays/upload-google-hash-only-audience.play.ts
deepline plays run --file ./plays/upload-google-hash-only-audience.play.ts --input '{"file":"enriched_hash_only.csv","account_id":"1234567890","audience_name":"ABM enriched hash-only 2026-06-09"}' --watch

deepline plays check ./plays/upload-facebook-google-hash-only-audience.play.ts
deepline plays run --file ./plays/upload-facebook-google-hash-only-audience.play.ts --input '{"file":"enriched_hash_only.csv","audience_name":"ABM enriched hash-only 2026-06-09","google_account_id":"1234567890","meta_ad_account_id":"act_123","meta_audience_id":"456"}' --watch

deepline plays check ./plays/report-google-coverage-lift.play.ts
deepline plays run --file ./plays/report-google-coverage-lift.play.ts --input '{"account_name":"Customer Google Ads","account_id":"1234567890","segment_name":"High-priority target-account audience","source_rows":20000,"baseline":{"label":"L1 work hash-only","audience_id":"1111111111","match_rate_pct":23,"uploaded_rows":13935},"comparisons":[{"label":"L2 Lima+Aviato hash-only","audience_id":"2222222222","match_rate_pct":35,"uploaded_rows":18386,"deepline_spend_usd":51.47},{"label":"L3 all hashes only","audience_id":"3333333333","match_rate_pct":43,"uploaded_rows":24787},{"label":"L4 all hashes + details","audience_id":"4444444444","match_rate_pct":42,"uploaded_rows":24787},{"label":"L5 LeadMagic top100 fallback","audience_id":"5555555555","match_rate_pct":44,"uploaded_rows":17016},{"label":"L6 GTM LinkedIn + Lima/Aviato","audience_id":"6666666666","match_rate_pct":45,"uploaded_rows":17064}],"spend":{"low_cost_hash_usd":51.47,"contact_fallback_usd":218.37,"total_usd":269.84},"recommendation_label":"L6 GTM LinkedIn + Lima/Aviato"}' --watch
```

Export dataset outputs after a run with:

```bash
deepline runs export <run-id> --out audience-output.csv
```

Before using the upload play, run account discovery from Step 2 and confirm the selected Google Ads account name and ID with the user.

## Step 1: Confirm Rights

Ask for explicit confirmation when the source data belongs to a customer workspace or third party. The minimum confirmation is:

- The source list can be used for paid ads audience creation.
- Any enrichment identifiers can be used for paid ads matching.
- The requested platforms are allowed for this use case.
- Geography is in scope. Default to US-only when personal identifiers are being enriched unless the user specifies otherwise and confirms compliance.

Do not use this skill for outbound email, phone, or sequencing. The output is audience upload data and platform audience IDs.

## Step 2: Discover Uploadable Accounts

Run account discovery before every live upload. Agents often guess account IDs from prior context, app IDs, or UI labels. That creates audiences in the wrong account or fails after enrichment spend has already happened.

Use this discovery ladder:

1. Search for live account tools:

```bash
deepline tools search "ads audience account discovery google meta linkedin" --json
deepline tools list | grep -Ei "account|audience"
```

2. If a platform exposes a direct account discovery tool or endpoint, use it first. Record account name, account ID, platform, permission status, and whether customer list upload is supported.

3. If no direct discovery tool is exposed, ask the user for the account ID and name, then validate it before upload:

```bash
deepline tools execute google_ads_audiences_list_audiences --payload '{"account_id":"1234567890","page_size":10}' --json
deepline tools execute meta_audiences_list_audiences --payload '{"ad_account_id":"1234567890"}' --json
deepline tools execute linkedin_ads_audiences_list_audiences --payload '{"account_id":"urn:li:sponsoredAccount:123456789"}' --json
```

4. Show the discovered choices back to the user as `Account Name (Account ID)`, grouped by platform. If there is more than one plausible account, ask which one to use before creating audiences.

5. Keep the selected account IDs in the run notes and final answer. A Meta app ID is not an ad account ID; the two look similar enough that agents substitute one for the other, and the upload then fails or lands in the wrong account after enrichment has already been paid for. Meta upload IDs look like `act_123...` or a numeric ad account ID that Deepline can prefix.

## Step 3: Build Baseline and Enriched Objects

Create two separate objects when evaluating lift:

- `unenriched`: first-party source identifiers only, usually work email plus name, company, country, postal code, and LinkedIn URL context.
- `enriched`: source identifiers plus paid-ads-safe enrichment. Prefer hashed personal email providers first, then raw personal-email providers that can be normalized and hashed locally.

Run this as a waterfall, not a fan-out. Every layer below runs only on rows that still have no usable hash. Sending the same row to several providers costs several times over for one identifier, and it hides: every call returns 200, so the run reads as healthy while the bill multiplies. `plays/enrich-audience-waterfall.play.ts` enforces the skipping and reports attempted, hits, and skipped per layer, so a fan-out is visible in the output.

Default personal-email waterfall for B2B paid ads:

1. Baseline first-party identifiers: valid work emails, names, company, country, postal code, LinkedIn URLs, and stable external IDs.
2. Aviato `aviato_pull_email_hash`: run on all eligible rows with enough identity context, including rows that already have work emails. Use it when the goal is ad upload and the provider returns paid-ads-ready personal email hashes. If the output cell is a JSON object, extract the scalar hash from `matched_result`, `result.data.hashedEmails[0]`, `result.data.hashed_email`, or equivalent hash fields. Do not treat the JSON object string as the upload value.
3. LimaData `limadata_find_audience_identifiers`: run on rows still missing a personal hash after Aviato, or run it first when the user asks for the most cost-effective expansion pass. Extract only normalized 64-character SHA-256 hashes from `matched_result`, `result.data.hashed_emails[].normalized_hash`, `hash`, or `sha256` fields.
   ContactOut hashed identifiers do not belong in this numbered list, because they cannot waterfall. Run them as a separate bulk pass. See the section below.

### ContactOut hashed identifiers (quick reference)

ContactOut converts LinkedIn URLs straight into hashed emails, but it does not waterfall: the response is an unattributed pool, so it cannot skip rows another provider covered and later providers cannot skip rows it covered. Run it as a bulk pass beside the ladder.

- Send set: rows with a verified LinkedIn URL. Exclude rows that already have a hash for `cost_effective`, include them for `max_coverage`.
- Batch 5 to 100 per call. A zero-match chunk returns HTTP 404 and is not billed.
- Bill and report from `matches_found`, never the hash-list length.
- Merge into the audience-level hash pool, not per-row `email_sha256` cells.

→ Read `shared/contactout-hash-pool.md` before planning or running a pass. It covers why attribution cannot be recovered, the measured overlap and multi-address rates, and the Meta result.

### A work email is not a personal hash

Scope the waterfall on whether a row has a usable personal identifier, not on
whether it has any email. A work-email-only contact must run through every layer;
a work email is the L0 baseline.

The same mistake hides inside a `personal_email` column. In one run 151 rows held
a corporate address there, and each one exempted a contact from enrichment.
Re-running only those rows hit 64.9%, against 27.5% on the main pass, for 4.23
USD. Check the domain, not the column name.

### Order the ladder by what a miss costs

Two providers at similar prices are not equivalent, because they bill differently
on a miss:

| Billing               | Providers             | Consequence                                    |
| --------------------- | --------------------- | ---------------------------------------------- |
| Per call, hit or miss | LimaData, Aviato      | Every attempted row costs the same             |
| Per result or match   | LeadMagic, ContactOut | Misses are free, so they suit a thin remainder |

Measured on one 5,549-row list, cheapest first:

| Layer                             | Attempted | Hit rate | Spend     |
| --------------------------------- | --------- | -------- | --------- |
| LimaData                          | 1,775     | 27.5%    | 49.70 USD |
| LimaData, corporate-personal redo | 151       | 64.9%    | 4.23 USD  |
| ContactOut bulk                   | 1,772     | 53.0%    | 52.64 USD |
| LeadMagic                         | 1,285     | 5.4%     | 4.76 USD  |

Run the cheapest per-call provider first so it absorbs the easy hits. A low hit
rate on the remainder means the pool is exhausted: LeadMagic cost 4.76 USD to
establish that, where a per-call provider bills the same for the same answer.

Stop after the hash providers by default. Report attempted rows, row hits, unique hashes added, contacts still missing personal hashes, and Deepline spend. Then ask whether the user wants to spend more on broader raw personal-email providers, quoting the current per-contact cost from `deepline tools describe <tool_id> --json` rather than a remembered figure. Rates change, and a stale quote in an approval gate is how users end up agreeing to a number that no longer holds.

Only run the expanded coverage pass after explicit approval. In that pass, try providers such as LeadMagic, ContactOut, Wiza, Datagma, Crustdata, Prospeo, FullEnrich, PDL, or Deepline native personal-email waterfalls on rows still missing personal hashes. Normalize and SHA-256 hash raw personal emails exactly once, record provider-level lift and Deepline spend, and keep the default upload payload hash-only.

Leave mobile phones out unless the user explicitly asks for them. They cost considerably more per contact than hashed emails, and a phone layer can consume most of a test budget before the cheap email layers have finished proving what the list can reach. Phones are worth adding as a second identifier alongside email, not as a substitute for it.

For `max_coverage`, the user has already approved the goal but not unlimited spend. Ask for or infer a budget cap before any paid fallback past the hash layer. If the user gave a cap, run the expanded pass until the cap or marginal-lift stop condition is reached.

For native waterfall outputs, include only provider-specific fields that are confirmed personal-email responses, such as `first_personal_email`, `personal_email`, `personal_emails[]`, or Wiza email values where `email_type` is personal. Do not include an untyped final scalar just because it contains an email address. Untyped final values can be work emails.

Keep row lineage in both objects:

- `external_id`
- `source_row_number`
- `person_linkedin_url`
- `company_name`
- `company_domain`
- `provider_used`
- `identifier_type`

This lets the user evaluate whether enrichment improved upload coverage without losing the source list.

### LinkedIn URL Backfill for Audience Enrichment

When LinkedIn URLs are needed before personal-email/hash enrichment, use a measured query ladder instead of one exact-company query. In a high-priority ABM eval sample, exact account-name search recovered the known URL in the top five for `51.7%` of rows, while the account-or-LinkedIn-company query recovered `65.8%`. Quoted domain search was much worse (`5.8%`) and should not be a first-pass default.

Start with the native `person-to-linkedin` play when available. It cleans company anchors with the same helper used by the API:

- `RTX Corporation` → `RTX`
- `Lockheed Martin Corporation` → `Lockheed Martin`
- `NASA - National Aeronautics and Space Administration` → `NASA` plus a secondary long-form alias
- `L3Harris (formerly Aerojet Rocketdyne)` → `L3Harris`
- `Siemens Energy Global GmbH & Co. KG` → `Siemens Energy`
- `Airbus EMEA` → `Airbus`

The first Serper query should use the cleaned account/LinkedIn company aliases:

```text
"{{full_name}}" ("{{account_name}}" OR "{{linkedin_company_name}}") site:linkedin.com/in -inurl:dir -inurl:pub
```

Then validate candidates before using them:

1. Keep only `linkedin.com/in/` URLs and strip query params/trailing slashes.
2. Reject search results where the profile title does not contain a first-name match and a last-name match. Allow common nicknames and meaningful first-name prefixes; do not accept single-letter last-name initials as validated.
3. Use company/title evidence as supporting evidence, not as identity proof.
4. For ambiguous candidates, retrieve the profile with `harvestapi_get_profile` and validate `element.firstName`, `element.lastName`, current company, and headline before merging. This catches snippet false positives such as a search result mentioning the target name in another person's experience section.

Use follow-up queries only after the first pass misses:

```text
"{{full_name}}" "{{title}}" "{{linkedin_company_name}}" site:linkedin.com/in -inurl:dir -inurl:pub
"{{full_name}}" "{{account_name}}" site:linkedin.com/in -inurl:dir -inurl:pub
```

Do not make quoted domain (`"{{domain}}"`) the first query. It can help occasional rows, but in the eval sample it reduced recall and caused more provider failures.

## Step 4: Validate Identifiers

Before upload, remove empty strings and malformed hashes from the payload. Deepline platform validators reject empty `email` fields and non-64-character `email_sha256` values.

Valid upload row fields include:

- `email`
- `email_sha256`
- `phone`
- `phone_sha256`
- `first_name`
- `last_name`
- `country_code`
- `postal_code`
- `company_name`
- `title`
- `company_domain`
- `person_linkedin_url`
- `external_id`

Prefer `email_sha256` when a provider returns a paid-ads-ready hash. Provider hashes must pass through exactly as lowercase 64-character hex. Do not double-hash provider hashes.

### Standard upload file shape

Use one shape for every run, so the audit, the Sheets export and both platform
uploads read the same file:

```
email,phone,fn,ln,country
```

- `email` and `phone` hold 64-character lowercase SHA-256 digests, or nothing.
- Every row carries at least one of the two. Drop rows with neither.
- `fn` and `ln` are lowercase `a-z` only. `country` is a two-letter code.
- Keep a parallel `..._lineage.csv` with a `source` column naming the layer that
  produced each hash.

Blank cells are deliberate: a ContactOut-pool row has no name, a phone-only row
has no email.

Before uploading, assert that each column holds one identifier type and that no
value is the SHA-256 of another value in the file. Both failures upload cleanly
and match nothing.
→ Read `shared/upload-failure-modes.md`.

When a provider returns raw personal email:

1. Trim whitespace.
2. Lowercase the email.
3. Validate it with a normal email pattern.
4. Hash the normalized email with SHA-256 exactly once.
5. Upload only `email_sha256` unless the user explicitly asked to upload raw email fields.

### Normalize LinkedIn URLs (drop encoded internal-identifier URLs)

The Ad Audiences APIs (batch and live) accept only **vanity** LinkedIn URLs —
`linkedin.com/in/<username>` (e.g. `linkedin.com/in/scott`). They do **not**
accept **encoded internal-identifier** URLs, where the slug is an opaque
member-identity token — e.g.
`https://www.linkedin.com/in/ACwAAA3jFR0B90FE7rqSIhnof5R9h57ZrfgYR7w`. These come
from Sales Navigator exports and some enrichment providers. The endpoint tolerates
them today but **will return `400` for that input soon**, so treat an encoded URL
as invalid `person_linkedin_url` before upload.

Detect and handle every `person_linkedin_url` cell:

1. **Detect encoded** — the slug after `/in/` starts with `ACwAA` / `ACoAA` (or is
   a long single-token Base64URL-ish string, ~30+ chars of `[A-Za-z0-9_-]` with no
   hyphenated name and no digits-as-suffix). That is an internal identifier, not a
   username.
2. **Do not upload it as-is.** Drop the encoded value from `person_linkedin_url`
   for that row so the platform validator does not reject the whole payload.
3. **Recover the vanity URL when the row still needs LinkedIn coverage** — run the
   LinkedIn URL Backfill ladder from Step 3 (native `person-to-linkedin`, then the
   Serper name + company query) to resolve the real `linkedin.com/in/<username>`.
   This is the same helper that produces upload-ready vanity URLs elsewhere in this
   skill.
4. **Keep vanity URLs as-is** — `linkedin.com/in/<username>`: strip query params and
   trailing slashes, lowercase the host, and upload.

Report, in the Step 4 audit, how many `person_linkedin_url` rows were encoded
(dropped), how many were recovered to a vanity URL, and how many were already
valid — an all-encoded input silently uploading zero LinkedIn identifiers is the
failure this step exists to prevent.

Before live upload, write a small audit with:

- source row count
- valid baseline work-email count
- provider row hits
- hashes seen by provider
- unique hashes added by provider
- invalid hash rows
- whether any raw `email` field remains in the upload payload
- LinkedIn URLs: encoded (dropped), recovered to vanity, already valid

## Step 5: Create and Upload

Create one audience per platform per object. Name them so the account UI makes the test clear:

- `<customer or segment> enriched <date>`
- `<customer or segment> unenriched <date>`

Then upload each object separately.

Current starting hints:

```bash
deepline tools execute google_ads_audiences_create_audience --payload '{"account_id":"1234567890","name":"Example enriched hash-only","membership_life_span_days":540,"upload_key_types":["CONTACT_ID"]}' --json
deepline tools execute google_ads_audiences_sync_audience_members --payload '{"account_id":"1234567890","audience_id":"1111111111","mode":"append","terms_of_service_accepted":true,"consent":{"ad_user_data":"GRANTED","ad_personalization":"GRANTED"},"rows":[{"email_sha256":"973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b"}]}' --json

deepline tools execute meta_audiences_create_audience --payload '{"ad_account_id":"1234567890","name":"Example enriched hash-only","customer_file_source":"BOTH_USER_AND_PARTNER_PROVIDED"}' --json
deepline tools execute meta_audiences_sync_audience_members --payload '{"ad_account_id":"1234567890","audience_id":"1111111111","mode":"replace","rows":[{"email_sha256":"973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b"}]}' --json

deepline tools execute linkedin_ads_audiences_create_audience --payload '{"account_id":"urn:li:sponsoredAccount:123456789","name":"Example enriched hash-only","audience_kind":"contacts"}' --json
deepline tools execute linkedin_ads_audiences_sync_audience_members --payload '{"account_id":"urn:li:sponsoredAccount:123456789","audience_id":"1111111111","mode":"replace","rows":[{"email_sha256":"973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b"}]}' --json
```

Use `append` for Google when uploading into a newly created empty audience if `replace` returns provider-side Data Manager payload errors. Report that clearly because it indicates connector behavior that should be fixed.

### Upload the whole audience in one call

Meta locks an audience on write and rejects later writes with HTTP 422 until
ingestion finishes, so a batched loop leaves the audience holding part of the
list. Send every row in one `sync_audience_members` call, and pass the payload as
`--payload @file.json` because inline JSON exceeds the shell argument limit.

Omit blank string fields rather than sending `""`; the schema declares
`minLength: 1` and an empty value fails the whole batch.
→ Read `shared/upload-failure-modes.md`.

## Step 6: Verify and Report

Read Google's match rate from
`ingestedUserListInfo.contactIdInfo.matchRatePercentage`. The `matchRateRange`
enum beside it stays unset, so reading the enum alone reports `null` for an
audience with a real rate, and a report that renders `null` as 0% turns a good
run into an apparent failure. Meta exposes no per-audience match rate.

`uploaded_count` and `invalid_count` describe whether rows parsed, not whether
people matched. Report acceptance and match rate separately.
→ Read `shared/upload-failure-modes.md`.

Run status checks after upload:

```bash
deepline tools execute google_ads_audiences_get_audience_status --payload '{"account_id":"1234567890","audience_id":"1111111111"}' --json
deepline tools execute meta_audiences_get_audience_status --payload '{"ad_account_id":"1234567890","audience_id":"1111111111"}' --json
deepline tools execute linkedin_ads_audiences_get_audience_status --payload '{"account_id":"urn:li:sponsoredAccount:123456789","audience_id":"1111111111"}' --json
```

Final answer format:

- Platform and account name plus ID.
- Audience name and audience ID.
- Object type: enriched or unenriched.
- Uploaded count.
- Invalid count.
- Request IDs or session IDs.
- Current status. Note that match size and match-rate ranges may stay null while platforms process the audience.

If upload fails, report the provider error category and request ID. Do not say the audience worked unless create, sync, and readback status all succeeded.

### Google Coverage Follow-Up Reporting

After Google match rates populate, use `plays/report-google-coverage-lift.play.ts` to prevent hand-calculation drift. The play should be run from the same match-rate readback that listed the Google account name and ID. It calculates:

- percentage-point lift versus baseline
- relative lift versus baseline
- estimated matched identifiers from uploaded rows and match rate
- incremental matched identifiers versus baseline
- Deepline spend and blended cost per incremental matched identifier when spend is provided
- a ready-to-send follow-up note

Use anonymized or customer-approved values in customer-facing follow-up notes. Keep account IDs, audience IDs, match rates, spend, and provider-layer labels tied to the current run artifact rather than copying old example values.

Do not expose provider-side unit costs in customer-facing messages. Report Deepline spend only.

## Reading guide

| If you're about to…                                                 | Read                                           |
| ------------------------------------------------------------------- | ---------------------------------------------- |
| Explain hashing, match rate, or platform rules to a first-time user | `shared/audience-basics.md`                    |
| Plan or run a ContactOut hashed-identifier pass                     | `shared/contactout-hash-pool.md`               |
| Enrich and upload to Meta and Google end to end                     | `recipes/enrich-and-upload-facebook-google.md` |
| Push a list as far as the budget allows                             | `recipes/max-coverage-audience.md`             |
| Follow the worked ABM example                                       | `recipes/sample-abm-segment-example.md`        |
