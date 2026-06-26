# Sample ABM Segment Ads Audience Example

Use this recipe for a concrete ABM audience pattern from a high-priority title or account segment. It is intentionally written as a reusable example, not as a customer-specific runbook.

## Scenario

The source audience is a high-priority B2B segment from CRM or Salesforce title segmentation:

- about 2,000 source people.
- most rows have LinkedIn URLs.
- about half of rows have uploadable work emails.
- US-only by default for personal identifier enrichment.
- Mobile phones skipped because they are too expensive for this audience test.

Observed provider planning numbers from the example run:

| Layer                               | Example result                  |
| ----------------------------------- | ------------------------------- |
| LimaData hashed personal-email hits | low double-digit row lift       |
| Aviato hashed personal-email hits   | low-to-mid double-digit lift    |
| Raw personal-email fallback         | run only after explicit budget approval |

Do not treat these as Deepline benchmarks. They are example-run planning numbers that help agents preserve the intended shape of the workflow.

## Goal

Create separate enriched and unenriched hash-only audiences for Google Customer Match and Meta Custom Audiences so the user can compare actual platform match behavior.

The output should include:

- `unenriched_hash_only.csv`, built from first-party work emails and allowed source identifiers.
- `enriched_hash_only.csv`, built from source identifiers plus provider hashes and raw personal-email fallbacks hashed once.
- `provider_coverage.csv`, showing attempted rows, hits, unique hashes added, failures, and cost by provider layer.
- `no_double_hash_audit.md`, proving provider hashes were not hashed again.
- `upload_report.md`, listing platform account name and ID, audience name and ID, uploaded count, invalid count, request IDs, and readback status.

## Rights Gate

Before enrichment or upload, confirm:

- The CRM or Salesforce segment can be used for paid ads audience creation.
- Enriched personal identifiers can be used for paid ads matching.
- The audience is US-only, or the user has confirmed broader geography rights.
- The workflow is for ABM paid ads only, not outbound.
- Google and Meta account selection has been confirmed by account name and ID.

## V2 Path

Use this path when `deepline plays --help` is available.

Build baseline and enriched objects:

```bash
deepline plays check .skills/deepline-ads-audiences/plays/build-hash-only-audience.play.ts
deepline plays run --file .skills/deepline-ads-audiences/plays/build-hash-only-audience.play.ts --input '{"file":"'"$WORKDIR"'/source.csv"}' --watch
```

Audit the enriched payload:

```bash
deepline plays check .skills/deepline-ads-audiences/plays/audit-no-double-hash.play.ts
deepline plays run --file .skills/deepline-ads-audiences/plays/audit-no-double-hash.play.ts --input '{"payloadFile":"'"$WORKDIR"'/enriched_hash_only.csv","providerHashFile":"'"$WORKDIR"'/provider_hashes.csv","providerHashColumns":["aviato_hash","limadata_hash","email_sha256","hashed_personal_email_sha256"]}' --watch
```

Upload enriched and unenriched as separate objects. Use the Google-only play for the Google comparison and the combined play when a Meta Custom Audience ID is available:

```bash
deepline plays check .skills/deepline-ads-audiences/plays/upload-google-hash-only-audience.play.ts
deepline plays run --file .skills/deepline-ads-audiences/plays/upload-google-hash-only-audience.play.ts --input '{"file":"'"$WORKDIR"'/unenriched_hash_only.csv","account_id":"<google_customer_id_without_dashes>","audience_name":"High-priority segment unenriched hash-only <date>"}' --watch
deepline plays run --file .skills/deepline-ads-audiences/plays/upload-google-hash-only-audience.play.ts --input '{"file":"'"$WORKDIR"'/enriched_hash_only.csv","account_id":"<google_customer_id_without_dashes>","audience_name":"High-priority segment enriched hash-only <date>"}' --watch
```

## V1 Path

Use this path when the installed CLI does not expose `deepline plays`, but does expose `deepline enrich` and `deepline tools`.

Start with discovery:

```bash
deepline --help
deepline enrich --help
deepline tools search "aviato email hash" --json
deepline tools search "limadata audience identifiers" --json
deepline tools search "contactout personal email" --json
deepline tools search "google ads audiences" --json
deepline tools search "meta audiences" --json
```

Run the provider waterfall in bounded batches:

```bash
deepline enrich --input "$WORKDIR/source.csv" --output "$WORKDIR/aviato_hashes.csv" --rows 0:50 --with 'aviato_hash=<current_aviato_hash_tool>:{"linkedin_url":"{{linkedin_url}}","email":"{{work_email}}"}'
deepline enrich --input "$WORKDIR/aviato_misses.csv" --output "$WORKDIR/limadata_hashes.csv" --rows 0:50 --with 'limadata_hash=<current_limadata_hash_tool>:{"linkedin_url":"{{linkedin_url}}","email":"{{work_email}}"}'
```

Stop after Aviato and LimaData by default. Report coverage lift, unique hashes added, contacts still missing personal hashes, and Deepline spend.

Then ask whether the user wants to pay about 0.08 USD/contact in additional Deepline spend to increase coverage. Only after explicit approval, run the broader fallback pass. For ContactOut specifically, run the free pre-check first and only run paid reveal for rows where the pre-check is true and no hashed provider already returned a usable hash.

Build and audit the hash-only payloads using the current V1 hash helper or validation tool. If the current V1 install cannot hash normalized raw personal emails and cannot audit provided SHA-256 values, stop and use the V2 plays. Do not upload raw personal emails as a workaround.

Upload with current account tools only after showing the account choices back as `Account Name (Account ID)`. Create four separate audiences when both platforms are connected:

- Google unenriched.
- Google enriched.
- Meta unenriched.
- Meta enriched.

## Acceptance Criteria

The run is complete only when:

- The chosen surface is named as V1 or V2.
- The source count, LinkedIn URL count, baseline work-email count, and provider coverage counts are reported.
- Provider hashes are passed through as lowercase 64-character SHA-256 values.
- Raw personal emails, if any, are normalized and hashed exactly once.
- The no-double-hash audit passes before live upload.
- Enriched and unenriched objects are uploaded separately.
- Google and Meta account names and IDs are shown in the final report.
- Match-rate fields are reported only when the platforms return them.
