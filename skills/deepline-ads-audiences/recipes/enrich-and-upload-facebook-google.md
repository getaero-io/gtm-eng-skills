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

Keep work-email rows in the enrichment pool until they receive a personal hash or the provider ladder is exhausted.

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

Confirm the play surface before building files:

```bash
deepline --help
deepline plays --help
```

If `deepline plays` is unavailable, stop and ask for the Deepline SDK CLI to be installed or updated. Do not build upload payloads through older command paths.

Use the bundled play when the CSV already contains first-party emails plus provider hash or personal email columns:

```bash
deepline plays run --file .skills/deepline-ads-audiences/plays/build-hash-only-audience.play.ts --input '{"file":"'"$WORKDIR"'/source.csv"}' --watch
```

Export both datasets after the run:

```bash
deepline runs export <run-id> --dataset baseline_hash_only_audience --out "$WORKDIR/baseline_hash_only.csv"
deepline runs export <run-id> --dataset enriched_hash_only_audience --out "$WORKDIR/enriched_hash_only.csv"
```

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

A live upload without a no-double-hash audit is not acceptable for this workflow.

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
