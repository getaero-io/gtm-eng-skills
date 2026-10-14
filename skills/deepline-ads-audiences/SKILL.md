---
name: deepline-ads-audiences
description: "Use this skill when building, enriching, auditing, or uploading B2B paid ads audiences to Google Customer Match, Meta/Facebook Custom Audiences, or LinkedIn Matched Audiences. Triggers on phrases like '/deepline-ads-audience', '/deepline-ads-audiences', 'upload this audience', 'create custom audiences', 'personal email hashes', 'increase Facebook match rate', 'Google ads audience', 'Meta audience', 'FB audience', or any workflow that turns CRM/customer/contact data into paid ads upload lists. Skip for outbound prospecting sequences, cold email, or pure campaign copywriting."
---

# Deepline Ads Audiences

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

## CLI resolution

Run `deepline` when it is available. If the shell reports that command is missing, use `<workspace-root>/.deepline/runtime/bin/deepline` (or the npm-created `.cmd` shim on Windows). If neither exists, follow `https://code.deepline.com/INSTALL.md` to set up Deepline.

Build high-quality ABM paid ads audiences from first-party customer or prospect lists. This skill is for paid ads audience upload and evaluation, not outbound.

Names in this skill are starting hints. Run `deepline search "contact list -> ad platform custom audience" --type tools` and `deepline describe <tool_id>` before executing because tool names and payload shapes can change. Tool search takes a task: one sentence stating the input you have -> the result you need, not keywords. There is no `--prefix` flag.

## Before You Start

Match the request to a row in the decision matrix and read the linked file before acting. This skill is not for cold outbound, sequencing, or copywriting: personal emails here are used to improve paid ads matching, not to contact people directly.

## Decision Matrix

| User says                                                                                                                                                   | Do this                                                                      | Read                                                      |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------- |
| "max coverage", "highest match rate", "maximum match rate", "keep increasing coverage", "get to 75% coverage", exhaust LinkedIn/personal-email/hash options | Run the explicit max-coverage ladder with budget gates.                      | `recipes/max-coverage-audience.md`                        |
| `/deepline-ads-audience`, "enrich and upload to FB/Google"                                                                                                  | Run the full paid ads audience recipe.                                       | `recipes/enrich-and-upload-facebook-google.md`            |
| "sample ABM segment", "do the example workflow"                                                                                                             | Follow the reusable high-priority ABM segment recipe.                        | `recipes/sample-abm-segment-example.md`                   |
| "use ContactOut hashes", "hashed identifiers", "LinkedIn URLs to hashes"                                                                                    | Plan a bulk pass beside the ladder, not a waterfall step.                    | `shared/contactout-hash-pool.md`                          |
| "what is a hash", "why is my match rate low", first-time user                                                                                               | Explain the mechanic before quoting a plan.                                  | `shared/audience-basics.md`                               |
| encoded/internal-identifier LinkedIn URLs (`/in/ACwAA…`), "API rejected my LinkedIn URLs", "convert LinkedIn URLs"                                          | Normalize `person_linkedin_url` before upload: drop encoded, recover vanity. | Step 4 → "Normalize LinkedIn URLs" (this file)            |
| "Make sure hashes are not double hashed"                                                                                                                    | Run the no-double-hash audit play before upload.                             | `plays/audit-no-double-hash.play.ts`                      |
| "enrich this list", "buy personal emails/hashes", "run the ladder"                                                                                          | Run the waterfall. Each layer only sees rows still missing a hash.           | `plays/enrich-audience-waterfall.play.ts`                 |
| "Compare enriched versus unenriched"                                                                                                                        | Build both hash-only datasets and report lift.                               | `plays/enrich-audience-waterfall.play.ts`                 |
| "include phone numbers", "add phones"                                                                                                                       | Hash existing phones digits-only with country code.                          | `shared/upload-failure-modes.md`                          |
| "what was the match rate", "did it match"                                                                                                                   | Read `contactIdInfo.matchRatePercentage`, not the range enum.                | `shared/upload-failure-modes.md`                          |
| "put it in a sheet", "customer will upload"                                                                                                                 | Publish the validated file to Sheets; verify by row count.                   | `shared/upload-failure-modes.md`                          |
| "connect Meta", "Meta not connected", "(#100)", "business_management"                                                                                       | Connect Meta with a system user token; Meta login is not offered.            | `shared/meta-connection.md`                               |
| "upload keeps failing", "422", "audience is locked"                                                                                                         | Meta locks on write. Send the audience in one call.                          | `shared/upload-failure-modes.md`                          |
| "Upload to Google"                                                                                                                                          | Validate hash-only rows, create Google audience, sync, readback.             | `plays/upload-google-hash-only-audience.play.ts`          |
| "Upload to Facebook and Google", "upload to FB/Google", "Meta + GAds"                                                                                       | Validate once, then upload to Google and Meta.                               | `plays/upload-facebook-google-hash-only-audience.play.ts` |

## Default Workflow

1. Confirm rights, use case, and geography.
2. Discover uploadable ad accounts.
3. Build baseline and enriched audience objects.
4. Validate identifiers and expected match-rate lift.
5. Create separate platform audiences.
6. Upload rows.
7. Check status and report IDs, uploaded counts, invalid rows, and current build state.

## Ask about suppression before targeting

Ask explicitly for the suppression list: the people who should never see the ad (current customers, closed-lost accounts, active opportunities, employees, recent converters). Users rarely volunteer it, and a list that was never built or silently failed to sync spends budget on people who already bought.

- When unsure whether someone belongs on it, include them. An extra suppressed person costs a few unserved impressions; a missing one costs real money and can annoy a customer.
- Enrich it with the same ladder. Suppression matches on the same identifiers as targeting, so a work-email-only suppression list suppresses almost nobody.

## Expect different lift per platform

Set this expectation before spending: Meta gains the most from personal-email enrichment, because people register there with personal addresses. Google gains less, since a Workspace address is already a Google account and often matches from the baseline. A modest Google result is the expected shape, not a failed run.

## Explain the shape before you spend

Before running the ladder, state the mechanic in one or two sentences so the user can judge the plan rather than approve it blindly:

> Ad platforms can only match people on identifiers those people gave the platform. Your CRM holds work emails; almost nobody signs up to Meta with a work address. These layers buy the personal identifiers that do match, cheapest first.

Say what each layer costs in Deepline credits and what it is expected to add, then ask for approval before the first paid layer. Point first-time users, or anyone who asks, to `shared/audience-basics.md` for what a hash is and why it is safe to send.

## Coverage Modes

Choose the coverage mode before spending credits and record it in the run notes. Never silently downgrade a `max_coverage` request to `cost_effective`: if a provider or credential is unavailable, report the gap and continue with the next approved provider rather than stopping early.

| Mode             | Use when                                                                        | Waterfall                                                                                                                                                                                                                                                                                | Stop condition                                                                                                                                |
| ---------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `cost_effective` | User asks for the default, low-cost, or first-pass enrichment.                  | Work-email baseline → Aviato personal hashes on all eligible rows → LimaData personal hashes on remaining personal-hash misses. Optionally a ContactOut bulk pass over rows that still lack a personal hash and have a LinkedIn URL, which runs beside the ladder rather than inside it. | Stop after the hash providers, report contacts still missing personal hashes, then ask before expanded fallback.                              |
| `max_coverage`   | User asks for highest match rate, max coverage, or to keep increasing coverage. | Work-email baseline → phone hashes already present → LinkedIn repair → Aviato personal hashes for all eligible rows → LimaData personal hashes → ContactOut bulk pass beside the ladder → raw personal-email waterfall → platform upload variants.                                       | Stop when no approved provider remains, budget cap is hit, marginal lift is below threshold, or rights/geo constraints block more enrichment. |

## Shareable Plays

`plays/` holds copyable play templates. Use them when the user asks for a repeatable or shareable workflow, not just a one-off CLI run. Run them with `deepline plays`; check `deepline --help` and `deepline plays --help` when the installed surface is unclear. If `deepline plays` is unavailable, stop and ask for the Deepline SDK CLI to be installed or updated instead of approximating the upload through older command paths.

| Play                                                      | Purpose                                                                                                                                                        | Input                                                                                                                                                                     |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plays/build-hash-only-audience.play.ts`                  | Build baseline and enriched hash-only datasets from source CSV rows. Raw emails are normalized and hashed once. Provider hashes pass through as lowercase hex. | `{ "file": "input.csv" }`                                                                                                                                                 |
| `plays/audit-no-double-hash.play.ts`                      | Verify the final upload payload is hash-only, deduped, populated, includes provider hashes as-is, and does not contain hash-of-hash mistakes.                  | `{ "payloadFile": "upload.csv", "providerHashFile": "provider-hashes.csv", "providerHashColumns": ["aviato_hash", "limadata_hash"] }`                                     |
| `plays/build-contactout-hash-pool.play.ts`                | Batch LinkedIn URLs through ContactOut hashed identifiers into a deduped hash pool. Reports matched profiles, net-new hashes, and per-chunk results.           | `{ "file": "contacts.csv", "limit": 100 }`                                                                                                                                |
| `plays/upload-google-hash-only-audience.play.ts`          | Create a Google Customer Match list, upload hash-only rows, and read status back.                                                                              | `{ "file": "upload.csv", "account_id": "1234567890", "audience_name": "Segment enriched 2026-06-09" }`                                                                    |
| `plays/upload-facebook-google-hash-only-audience.play.ts` | Upload the same validated hash-only rows to Google and an existing Meta/Facebook Custom Audience.                                                              | `{ "file": "upload.csv", "google_account_id": "1234567890", "meta_ad_account_id": "act_123", "meta_audience_id": "456", "audience_name": "Segment enriched 2026-06-09" }` |
| `plays/report-google-coverage-lift.play.ts`               | After Google match rates populate, calculate coverage lift, estimated matched identifiers, spend efficiency, and a follow-up note.                             | Full shape in the example below.                                                                                                                                          |

Recommended sequence: build, audit, upload (Google, or Facebook and Google), then the coverage report. Before using an upload play, run account discovery from Step 2 and confirm the selected Google Ads account name and ID with the user. Run `check` before `run` for each play, pass the input from the table, and export dataset outputs after a run:

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

deepline runs export <run-id> --out audience-output.csv
```

## Step 1: Confirm Rights

Ask for explicit confirmation when the source data belongs to a customer workspace or third party. The minimum confirmation is:

- The source list can be used for paid ads audience creation.
- Any enrichment identifiers can be used for paid ads matching.
- The requested platforms are allowed for this use case.
- Geography is in scope. Default to US-only when personal identifiers are being enriched unless the user specifies otherwise and confirms compliance.

## Step 2: Discover Uploadable Accounts

Run account discovery before every live upload. Do not guess account IDs from prior context, app IDs, or UI labels: a wrong guess creates audiences in the wrong account or fails after enrichment spend has already happened.

1. Search for live account tools:

```bash
deepline search "connected ad platform logins -> ad account IDs" --type tools
deepline tools list | grep -Ei "account|audience"
```

2. If a platform exposes a direct account discovery tool or endpoint, use it first. Record account name, account ID, platform, permission status, and whether customer list upload is supported.

   Meta uses the new token-based connection: the customer's long-lived system-user access token is stored in Dashboard → Integrations → Meta Audiences and is used server-side for discovery and writes. Call `meta_audiences_list_ad_accounts` to discover live accounts through that saved token and confirm the account by `name`. Use a row with `enabled: true`; `is_default: true` marks the workspace default, and `custom_audience_terms_accepted: false` means creation will fail until someone accepts Meta's terms. Then either pass that row's `id` as `ad_account_id`, or omit `ad_account_id` to use the workspace default and read the account the call used back from `data.ad_account_id` in the create, list, status, or sync response. Never put the Meta token in a CLI payload or chat, and never grep old runs, CSVs, or notes for Meta account IDs: they can belong to customers.

```bash
deepline tools execute meta_audiences_list_ad_accounts --payload '{}' --json
```

3. If no direct discovery tool is exposed, ask the user for the account ID and name, then validate it before upload:

```bash
deepline tools execute google_ads_audiences_list_audiences --payload '{"account_id":"1234567890","page_size":10}' --json
deepline tools execute meta_audiences_list_audiences --payload '{"ad_account_id":"1234567890"}' --json
deepline tools execute linkedin_ads_audiences_list_audiences --payload '{"account_id":"urn:li:sponsoredAccount:123456789"}' --json
```

4. Show the discovered choices back to the user as `Account Name (Account ID)`, grouped by platform. If there is more than one plausible account, ask which one to use before creating audiences.

5. Keep the selected account IDs in the run notes and final answer. A Meta app ID is not an ad account ID; never substitute one for the other. Meta upload IDs look like `act_123...` or a numeric ad account ID that Deepline can prefix.

## Step 3: Build Baseline and Enriched Objects

Create two separate objects when evaluating lift:

- `unenriched`: first-party source identifiers only, usually work email plus name, company, country, postal code, and LinkedIn URL context.
- `enriched`: source identifiers plus paid-ads-safe enrichment. Prefer hashed personal email providers first, then raw personal-email providers that can be normalized and hashed locally.

Run this as a waterfall, not a fan-out: every layer below runs only on rows that still have no usable hash. A fan-out pays several providers for one identifier and still reads as healthy, because every call returns 200. `plays/enrich-audience-waterfall.play.ts` enforces the skipping and reports attempted, hits, and skipped per layer.

Default personal-email waterfall for B2B paid ads:

1. Baseline first-party identifiers: valid work emails, names, company, country, postal code, LinkedIn URLs, and stable external IDs.
2. Aviato `aviato_pull_email_hash`: run on all eligible rows with enough identity context, including rows that already have work emails. If the output cell is a JSON object, extract the scalar hash from `matched_result`, `result.data.hashedEmails[0]`, `result.data.hashed_email`, or equivalent hash fields. Do not treat the JSON object string as the upload value.
3. LimaData `limadata_find_audience_identifiers`: run on rows still missing a personal hash after Aviato, or run it first when the user asks for the most cost-effective expansion pass. Extract only normalized 64-character SHA-256 hashes from `matched_result`, `result.data.hashed_emails[].normalized_hash`, `hash`, or `sha256` fields.

### ContactOut hashed identifiers (quick reference)

ContactOut converts LinkedIn URLs straight into hashed emails, but it does not waterfall: the response is an unattributed pool, so it cannot skip rows another provider covered and later providers cannot skip rows it covered. Run it as a bulk pass beside the ladder.

- Send set: rows with a verified LinkedIn URL. Exclude rows that already have a hash for `cost_effective`, include them for `max_coverage`.
- Batch 5 to 100 per call. A zero-match chunk returns HTTP 404 and is not billed.
- Bill and report from `matches_found`, never the hash-list length.
- Merge into the audience-level hash pool, not per-row `email_sha256` cells.
- Read `shared/contactout-hash-pool.md` before planning or running a pass.

### A work email is not a personal hash

Scope the waterfall on whether a row has a usable personal identifier, not on whether it has any email. A work email is the L0 baseline, so a work-email-only contact must run through every layer. A corporate address in a `personal_email` column is still a work email: check the domain, not the column name, or that contact is wrongly exempted from enrichment.

### Order the ladder by what a miss costs

Providers at similar prices bill differently on a miss:

- Per call, hit or miss (LimaData, Aviato): every attempted row costs the same.
- Per result or match (LeadMagic, ContactOut): misses are free, so they suit a thin remainder.

Run the cheapest per-call provider first so it absorbs the easy hits. A low hit rate on the remainder means the pool is exhausted, and a per-result provider is the cheap way to establish that.

Stop after the hash providers by default. Report attempted rows, row hits, unique hashes added, contacts still missing personal hashes, and Deepline spend. Then ask whether the user wants to spend more on broader raw personal-email providers, quoting the current per-contact cost from `deepline describe <tool_id>` rather than a remembered figure.

Only run the expanded coverage pass after explicit approval. In that pass, try providers such as LeadMagic, ContactOut, Wiza, Datagma, Crustdata, Prospeo, FullEnrich, PDL, or Deepline native personal-email waterfalls on rows still missing personal hashes. Normalize and SHA-256 hash raw personal emails exactly once, record provider-level lift and Deepline spend, and keep the default upload payload hash-only.

For native waterfall outputs, include only provider-specific fields that are confirmed personal-email responses, such as `first_personal_email`, `personal_email`, `personal_emails[]`, or Wiza email values where `email_type` is personal. Do not include an untyped final scalar just because it contains an email address; it can be a work email.

For `max_coverage`, the user has approved the goal but not unlimited spend. Ask for or infer a budget cap before any paid fallback past the hash layer, then run the expanded pass until the cap or marginal-lift stop condition is reached.

Leave mobile phones out unless the user explicitly asks for them. They cost considerably more per contact than hashed emails and can consume most of a test budget before the cheap email layers finish. Add them as a second identifier alongside email, not as a substitute for it.

Keep row lineage in both objects, so lift can be evaluated without losing the source list: `external_id`, `source_row_number`, `person_linkedin_url`, `company_name`, `company_domain`, `provider_used`, `identifier_type`.

### LinkedIn URL Backfill for Audience Enrichment

When LinkedIn URLs are needed before personal-email/hash enrichment, use a query ladder instead of one exact-company query. Discover an available people-search or public-search API and inspect its contract.

Normalize noisy company names before searching, for example `RTX Corporation` → `RTX`, `L3Harris (formerly Aerojet Rocketdyne)` → `L3Harris`, `Airbus EMEA` → `Airbus`, and `NASA - National Aeronautics and Space Administration` → `NASA` plus a secondary long-form alias.

The first Serper query should use those cleaned account/LinkedIn company aliases. Use the two follow-up queries only after the first pass misses:

```text
"{{full_name}}" ("{{account_name}}" OR "{{linkedin_company_name}}") site:linkedin.com/in -inurl:dir -inurl:pub
"{{full_name}}" "{{title}}" "{{linkedin_company_name}}" site:linkedin.com/in -inurl:dir -inurl:pub
"{{full_name}}" "{{account_name}}" site:linkedin.com/in -inurl:dir -inurl:pub
```

Do not make quoted domain (`"{{domain}}"`) the first query. It helps occasional rows but lowers recall and causes more provider failures.

Validate candidates before using them:

1. Keep only `linkedin.com/in/` URLs and strip query params/trailing slashes.
2. Reject search results where the profile title does not contain a first-name match and a last-name match. Allow common nicknames and meaningful first-name prefixes; do not accept single-letter last-name initials as validated.
3. Use company/title evidence as supporting evidence, not as identity proof.
4. For ambiguous candidates, validate first name, last name, current company, and headline against an authorized source or user-provided export before merging. If the evidence is insufficient, leave the identity unresolved.

## Step 4: Validate Identifiers

Before upload, remove empty strings and malformed hashes from the payload. Deepline platform validators reject empty `email` fields and non-64-character `email_sha256` values.

Valid upload row fields: `email`, `email_sha256`, `phone`, `phone_sha256`, `first_name`, `last_name`, `country_code`, `postal_code`, `company_name`, `title`, `company_domain`, `person_linkedin_url`, `external_id`.

Prefer `email_sha256` when a provider returns a paid-ads-ready hash. Provider hashes must pass through exactly as lowercase 64-character hex. Do not double-hash provider hashes. When a provider returns raw personal email: trim whitespace, lowercase it, validate it with a normal email pattern, hash the normalized email with SHA-256 exactly once, and upload only `email_sha256` unless the user explicitly asked to upload raw email fields.

### Standard upload file shape

Use one shape for every run, so the audit, the Sheets export and both platform uploads read the same file:

```
email,phone,fn,ln,country
```

- `email` and `phone` hold 64-character lowercase SHA-256 digests, or nothing. Blank cells are deliberate: a ContactOut-pool row has no name, a phone-only row has no email.
- Every row carries at least one of the two. Drop rows with neither.
- `fn` and `ln` are lowercase `a-z` only. `country` is a two-letter code.
- Keep a parallel `..._lineage.csv` with a `source` column naming the layer that produced each hash.

Before uploading, assert that each column holds one identifier type and that no value is the SHA-256 of another value in the file. Both failures upload cleanly and match nothing. → Read `shared/upload-failure-modes.md`.

### Normalize LinkedIn URLs (drop encoded internal-identifier URLs)

The Ad Audiences APIs (batch and live) accept only **vanity** LinkedIn URLs, `linkedin.com/in/<username>`. **Encoded internal-identifier** URLs, where the slug is an opaque member-identity token such as `https://www.linkedin.com/in/ACwAAA3jFR0B90FE7rqSIhnof5R9h57ZrfgYR7w`, come from Sales Navigator exports and some enrichment providers. The endpoint tolerates them today but **will return `400` for that input soon**, so treat an encoded URL as invalid `person_linkedin_url` before upload.

Handle every `person_linkedin_url` cell:

1. **Detect encoded**: the slug after `/in/` starts with `ACwAA` / `ACoAA`, or is a long single-token Base64URL-ish string (~30+ chars of `[A-Za-z0-9_-]` with no hyphenated name and no digits-as-suffix).
2. **Do not upload it as-is.** Drop the encoded value from `person_linkedin_url` for that row so the platform validator does not reject the whole payload.
3. **Recover the vanity URL when the row still needs LinkedIn coverage**: run the LinkedIn URL Backfill ladder from Step 3 (native `person-to-linkedin`, then the Serper name + company query) to resolve the real `linkedin.com/in/<username>`.
4. **Keep vanity URLs**: strip query params and trailing slashes, lowercase the host, and upload.

Before live upload, write a small audit with:

- source row count
- valid baseline work-email count
- per provider: row hits, hashes seen, unique hashes added
- invalid hash rows
- whether any raw `email` field remains in the upload payload
- LinkedIn URLs: encoded (dropped), recovered to vanity, already valid

## Step 5: Create and Upload

Create one audience per platform per object, named so the account UI makes the test clear: `<customer or segment> enriched <date>` and `<customer or segment> unenriched <date>`. Then upload each object separately. Current starting hints:

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

Meta locks an audience on write and rejects later writes with HTTP 422 until ingestion finishes, so a batched loop leaves the audience holding part of the list. Send every row in one `sync_audience_members` call, and pass the payload as `--payload @file.json` because inline JSON exceeds the shell argument limit.

Omit blank string fields rather than sending `""`; the schema declares `minLength: 1` and an empty value fails the whole batch. → Read `shared/upload-failure-modes.md`.

## Step 6: Verify and Report

Read Google's match rate from `ingestedUserListInfo.contactIdInfo.matchRatePercentage`. The `matchRateRange` enum beside it stays unset, so reading the enum alone reports `null` for an audience with a real rate. Never render `null` as 0%. Meta exposes no per-audience match rate.

`uploaded_count` and `invalid_count` describe whether rows parsed, not whether people matched. Report acceptance and match rate separately. → Read `shared/upload-failure-modes.md`.

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
- Uploaded count and invalid count.
- Request IDs or session IDs.
- Current status. Note that match size and match-rate ranges may stay null while platforms process the audience. For Meta, `approximate_count_is_minimum_bucket: true` means Meta is showing its 1,000-person floor: report "under about 1,000, not yet measurable", not 1,000 matched people.

If upload fails, report the provider error category and request ID. Do not say the audience worked unless create, sync, and readback status all succeeded.

### Google Coverage Follow-Up Reporting

After Google match rates populate, run `plays/report-google-coverage-lift.play.ts` from the same match-rate readback that listed the Google account name and ID, rather than calculating by hand. It calculates percentage-point and relative lift versus baseline, estimated and incremental matched identifiers, Deepline spend and blended cost per incremental matched identifier when spend is provided, and a ready-to-send follow-up note.

Use anonymized or customer-approved values in customer-facing follow-up notes. Keep account IDs, audience IDs, match rates, spend, and provider-layer labels tied to the current run artifact rather than copying old example values. Do not expose provider-side unit costs in customer-facing messages. Report Deepline spend only.

## Reading guide

| If you're about to…                                                 | Read                                           |
| ------------------------------------------------------------------- | ---------------------------------------------- |
| Explain hashing, match rate, or platform rules to a first-time user | `shared/audience-basics.md`                    |
| Plan or run a ContactOut hashed-identifier pass                     | `shared/contactout-hash-pool.md`               |
| Enrich and upload to Meta and Google end to end                     | `recipes/enrich-and-upload-facebook-google.md` |
| Push a list as far as the budget allows                             | `recipes/max-coverage-audience.md`             |
| Follow the worked ABM example                                       | `recipes/sample-abm-segment-example.md`        |
