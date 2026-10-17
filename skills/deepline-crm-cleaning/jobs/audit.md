# Audit

**Input:** approved read scope, record set, account unit, required fields, and source history.

1. Read the supplied export or approved CRM source.
2. Record schema, permissions, snapshot time, pages, and inaccessible records.
3. Normalize a copy.
4. Keep raw values.
5. Use null for observed blanks; omit fields the source did not expose.
6. Measure defects.
7. Separate candidate duplicates from confirmed duplicates, and field presence from valid current values.
8. Include unknowns in coverage.
9. Group defects by writer, import, version, account unit, and age.
10. Compare defects per write with write volume.
11. Confirm causes from events or a controlled reproduction; label other causes as hypotheses.
12. Produce a repair list with affected records, evidence, proposed values, dependencies, and unresolved reasons.

**Output:** snapshot manifest, normalized records, metrics, issues, and `audit` receipts. Complete when every scoped input has a result or an explicit gap.

## Snapshot Play

Use `audit-crm-snapshot.play.ts`; see the Play contracts for file input. It maps HubSpot and Salesforce company/contact fields. For another source, map canonical fields and set `source.adapter` to `canonical.v1`; retain the actual CRM in `source.system`.

Pass the agreed field policy in `required_fields_json`: `company` and `contact` arrays of supported names. Empty arrays are valid. Defaults need explicit adoption for the run. Keep the resolved policy and hash.

Supply `company_ids` only for a complete association list. Required `company_id` means the primary company; `company_ids` means any company link. Do not infer the primary company from secondary links. Read field-policy counts from `<object>_required_missing_<field>`. `company_missing_domain` instead measures combined domain or website availability.

The Play cannot verify live domains, ownership, enrichment accuracy, employment, Leads, or Person Account semantics. Keep observation counts in evidence. Convert unavailable receipt metrics to `not_measured` with null values.

## Live-source limits

The two HubSpot Plays collect an inventory, then sample companies and their associated contacts. Specify the deployment workspace and expected portal. The contact sample cannot estimate unlinked-contact prevalence. Keep its inventory CSV and manifest together. A completeness flag is an operator claim, not independent proof.

For warehouse input, verify read identity, schema, replication time, and native ID normalization. A prefix sample can be biased. Keep source-read scope separate from the workspace that pays for any approved enrichment.

Keep native merge targets, proposed targets, deletion markers, and hierarchy separate. Verify historical operations from events. Report incomplete pages, concurrent scan changes, and missing permissions.
