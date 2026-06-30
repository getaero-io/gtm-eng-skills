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

## Play Path

Confirm the play surface first:

```bash
deepline --help
deepline plays --help
```

If `deepline plays` is unavailable, stop and ask for the Deepline SDK CLI to be installed or updated. Do not replace this recipe with older enrichment or tool-execution command paths.

Build baseline and enriched objects:

```bash
deepline plays check .skills/deepline-ads-audiences/plays/build-hash-only-audience.play.ts
deepline plays run --file .skills/deepline-ads-audiences/plays/build-hash-only-audience.play.ts --input '{"file":"'"$WORKDIR"'/source.csv"}' --watch
```

Export the datasets from the build run:

```bash
deepline runs export <build-run-id> --dataset baseline_hash_only_audience --out "$WORKDIR/unenriched_hash_only.csv"
deepline runs export <build-run-id> --dataset enriched_hash_only_audience --out "$WORKDIR/enriched_hash_only.csv"
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

## Acceptance Criteria

The run is complete only when:

- The play run IDs and exported files are reported.
- The source count, LinkedIn URL count, baseline work-email count, and provider coverage counts are reported.
- Provider hashes are passed through as lowercase 64-character SHA-256 values.
- Raw personal emails, if any, are normalized and hashed exactly once.
- The no-double-hash audit passes before live upload.
- Enriched and unenriched objects are uploaded separately.
- Google and Meta account names and IDs are shown in the final report.
- Match-rate fields are reported only when the platforms return them.
