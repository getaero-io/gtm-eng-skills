# Enrich And Upload Paid Ads Audiences

Use this recipe when the user wants a B2B audience enriched with personal identifiers and uploaded to Meta/Facebook and Google. The output is paid ads audiences, not outbound contacts.

## When To Use

Use this recipe for:

- ABM audiences from CRM, Snowflake, Salesforce, HubSpot, or customer uploads.
- "Increase match rate on Facebook/Google" requests.
- "Use personal emails for ads, not outbound" requests.
- Enriched versus unenriched audience tests.

Skip this recipe for:

- Cold outbound sequences.
- One-off consumer targeting without source-list rights.
- Mobile-phone buying unless the user explicitly asks and approves cost.

## Inputs

Start with a project-local working directory because enrichment outputs are paid artifacts:

```bash
WORKDIR="deepline/data/<customer>-ads-audience" && mkdir -p "$WORKDIR" && echo "$WORKDIR"
```

The source CSV should preserve lineage fields:

| Field                       | Why                                                           |
| --------------------------- | ------------------------------------------------------------- |
| `source_row` or `person_id` | Reconcile rows after enrichment and upload.                   |
| `work_email`                | Baseline Google and Meta hash input.                          |
| `linkedin_url`              | Personal-email fallback providers usually need it.            |
| `first_name`, `last_name`   | Identity checks and fallback providers.                       |
| `company`, `domain`         | ABM review and provider context.                              |
| `country_code`              | Keep US-only default unless the user confirms broader rights. |

## Waterfall

Start with the cost-effective hash-provider pass:

1. Work-email baseline, normalized and SHA-256 hashed.
2. Aviato hash provider on all eligible rows with LinkedIn/profile context, including rows that already have work emails. Pass through 64-character personal email hashes as-is.
3. LimaData audience identifier hashes on rows still missing a personal hash after Aviato, or on all eligible rows first when that is more cost-effective.

Stop there by default. Report coverage lift, unique hashes added, contacts still missing personal hashes, and Deepline spend.

Then ask the user whether they want to pay about 0.08 USD/contact in additional Deepline spend to increase coverage with broader raw personal-email providers. Only after explicit approval, run the expanded pass:

4. LeadMagic personal email on rows still missing personal hashes, then normalize and hash once.
5. ContactOut free personal-email pre-check, then paid reveal only for true rows.
6. Optional later fallbacks: Wiza, Datagma, Crustdata, Prospeo, FullEnrich, PDL.

Every provider layer should report:

- attempted rows
- row hits
- hashes seen
- unique hashes added
- failures
- estimated and actual cost

If the user asks for "max coverage", "highest match rate", "keep increasing coverage", or a target such as "get closer to 75% coverage", switch to `recipes/max-coverage-audience.md` before spending beyond Aviato/LimaData. The max-coverage recipe adds explicit stop conditions, LinkedIn repair, broader personal-email fallback, optional phone hashes, and platform-readback economics.

## Build Hash-Only Payload

Choose the execution surface before building files:

```bash
deepline --help
deepline plays --help
```

If `deepline plays` is available, use the V2 path. If it is not available but `deepline enrich` and `deepline tools` are available, use the V1 path. Report the selected path in the run notes so later agents know which surface produced the files.

### V2 path

Use the bundled play when the CSV already contains first-party emails plus provider hash or personal email columns:

```bash
deepline plays run --file .skills/deepline-ads-audiences/plays/build-hash-only-audience.play.ts --input '{"file":"'"$WORKDIR"'/source.csv"}' --watch
```

Export both datasets after the run:

```bash
deepline runs export <run-id> --dataset baseline_hash_only_audience --out "$WORKDIR/baseline_hash_only.csv"
deepline runs export <run-id> --dataset enriched_hash_only_audience --out "$WORKDIR/enriched_hash_only.csv"
```

### V1 path

Use V1 when the installed CLI does not expose `deepline plays`. The V1 path is less compact, but it should still produce the same artifacts: baseline hash-only CSV, enriched hash-only CSV, provider coverage report, and no-double-hash audit.

Discover current tool names before invoking provider work:

```bash
deepline tools search "aviato email hash" --json
deepline tools search "limadata audience identifiers" --json
deepline tools search "personal email linkedin" --json
deepline tools search "google ads audiences" --json
deepline tools search "meta audiences" --json
```

Run a free baseline transform first. Use the local command shape exposed by `deepline enrich --help`; this template shows the required intent, not a frozen parser contract:

```bash
deepline enrich --input "$WORKDIR/source.csv" --output "$WORKDIR/baseline_hash_only.csv" --rows 0:2 --with 'email_sha256=hash_email:{"input":"work_email"}'
```

Then run provider layers in bounded batches. Keep each provider output as its own CSV so coverage and cost are auditable:

```bash
deepline enrich --input "$WORKDIR/source.csv" --output "$WORKDIR/aviato_hashes.csv" --rows 0:50 --with 'aviato_email_sha256=<current_aviato_hash_tool>:{"linkedin_url":"{{linkedin_url}}","email":"{{work_email}}"}'
deepline enrich --input "$WORKDIR/aviato_misses.csv" --output "$WORKDIR/limadata_hashes.csv" --rows 0:50 --with 'limadata_email_sha256=<current_limadata_hash_tool>:{"linkedin_url":"{{linkedin_url}}","email":"{{work_email}}"}'
```

`aviato_misses.csv` means rows missing an Aviato personal hash, not rows missing a work-email hash. Keep work-email rows in the enrichment pool until they receive a personal hash or the provider ladder is exhausted.

For raw personal-email fallbacks, normalize and hash once before upload. Do not upload raw personal emails unless the user explicitly asked for raw-email upload and platform consent terms are accepted:

```bash
deepline enrich --input "$WORKDIR/hash_provider_misses.csv" --output "$WORKDIR/personal_email_fallbacks.csv" --rows 0:25 --with 'personal_email=<current_personal_email_tool>:{"linkedin_url":"{{linkedin_url}}","first_name":"{{first_name}}","last_name":"{{last_name}}","company":"{{company}}"}'
deepline enrich --input "$WORKDIR/personal_email_fallbacks.csv" --output "$WORKDIR/enriched_hash_only.csv" --with 'email_sha256=hash_email:{"input":"personal_email"}'
```

`hash_provider_misses.csv` means rows still missing a personal email hash after Aviato/LimaData. It should include contacts with work-email hashes when they still lack a personal hash.

If the V1 CLI has no built-in hash helper in the current install, stop and use the V2 play. Do not paste raw emails into upload rows as a shortcut.

## Audit Before Upload

Run the no-double-hash audit. This catches the most expensive silent failure: hashing a provider hash again and uploading a valid-looking but useless identifier.

```bash
deepline plays run --file .skills/deepline-ads-audiences/plays/audit-no-double-hash.play.ts --input '{"payloadFile":"'"$WORKDIR"'/enriched_hash_only.csv","providerHashFile":"'"$WORKDIR"'/provider_hashes.csv","providerHashColumns":["aviato_hash","limadata_hash","email_sha256","hashed_personal_email_sha256"]}' --watch
```

Pass criteria:

- malformed hashes: 0
- duplicate hashes: 0 after dedupe
- raw email fields in upload payload: false
- provider hashes missing from payload: 0
- double-hashed provider hashes present: 0

On V1, run the same audit using the current validation or tool execution surface:

```bash
deepline tools search "audience hash validation" --json
deepline tools execute <current_hash_audit_tool> --payload '{"payload_file":"'"$WORKDIR"'/enriched_hash_only.csv","provider_hash_file":"'"$WORKDIR"'/provider_hashes.csv","provider_hash_columns":["aviato_hash","limadata_hash","email_sha256","hashed_personal_email_sha256"]}' --json
```

If no validation tool is exposed, use the V2 audit play before upload. A live upload without a no-double-hash audit is not acceptable for this workflow.

## Upload To Facebook And Google

Discover accounts first. Show account name and ID to the user before upload.

```bash
deepline tools search "google ads audiences accounts" --json
deepline tools search "meta audiences custom audience upload" --json
```

Use the combined play when both channel IDs are ready:

```bash
deepline plays run --file .skills/deepline-ads-audiences/plays/upload-facebook-google-hash-only-audience.play.ts --input '{"file":"'"$WORKDIR"'/enriched_hash_only.csv","audience_name":"<segment> enriched hash-only <date>","google_account_id":"<google_customer_id_without_dashes>","meta_ad_account_id":"act_<meta_ad_account_id>","meta_audience_id":"<existing_meta_custom_audience_id>"}' --watch
```

Notes:

- Google play path creates a new Customer Match audience, uploads rows, and reads status back.
- Meta path syncs rows into an existing Custom Audience because the live tool surface may expose sync without create. If a create tool exists in the current catalog, create the Meta audience first, then pass its ID to the play.
- Use `append` for Google on a newly created list.
- Use `replace` for Meta so the custom audience mirrors the hash-only payload.

For V1, use the current tool execution surface after account discovery. Keep enriched and unenriched as separate objects:

```bash
deepline tools execute google_ads_audiences_create_audience --payload '{"account_id":"<google_customer_id>","name":"<segment> unenriched hash-only <date>","membership_life_span_days":540,"upload_key_types":["CONTACT_ID"]}' --json
deepline tools execute google_ads_audiences_sync_audience_members --payload '{"account_id":"<google_customer_id>","audience_id":"<unenriched_audience_id>","mode":"append","terms_of_service_accepted":true,"consent":{"ad_user_data":"GRANTED","ad_personalization":"GRANTED"},"rows":[...]}' --json
deepline tools execute google_ads_audiences_create_audience --payload '{"account_id":"<google_customer_id>","name":"<segment> enriched hash-only <date>","membership_life_span_days":540,"upload_key_types":["CONTACT_ID"]}' --json
deepline tools execute google_ads_audiences_sync_audience_members --payload '{"account_id":"<google_customer_id>","audience_id":"<enriched_audience_id>","mode":"append","terms_of_service_accepted":true,"consent":{"ad_user_data":"GRANTED","ad_personalization":"GRANTED"},"rows":[...]}' --json
```

Use the same create/sync/readback pattern for Meta with the current `meta_audiences` tools. If Meta create is not exposed, ask for an existing Custom Audience ID and sync into that audience only after the user confirms the account name and ID.

## Report

Final report should include:

- Source list name and row count.
- Baseline hash count.
- Enriched hash count.
- Provider lift by layer.
- Audit pass/fail values.
- Google account name and ID, audience ID, uploaded count, invalid count, readback status.
- Meta ad account name and ID, audience ID, uploaded count, invalid count, readback status if available.
- Match-rate caveat: Meta may take about 1 hour to populate; Google may take 24 to 48 hours.

Do not claim a match rate until the platform returns it. Report `null` as processing, not as zero.
