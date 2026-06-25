# Max Coverage Paid Ads Audience

Use this recipe when the user asks for maximum B2B paid-audience coverage, highest match rate, or to keep increasing coverage. The output is still paid ads audience upload data, not outbound contact data.

This recipe extends the default cost-effective pass. It should not skip validation, account discovery, consent checks, or holdouts.

## Success Metric

Optimize for incremental matched audience coverage, not raw enrichment coverage.

Primary metric:

```text
cost per incremental matched person =
  Deepline spend / additional matched people versus baseline
```

Report these values for every coverage layer:

- attempted rows
- row hits
- unique contacts with at least one uploadable hash
- unique hashes added
- remaining no-personal-hash contacts
- Deepline spend
- estimated incremental matched people after platform readback
- cost per incremental matched person after platform readback

## Required Preflight

Before enrichment spend:

1. Confirm the list can be used for paid ads audience creation.
2. Confirm enriched identifiers can be used for paid ads matching.
3. Confirm geography. Default to US-only for personal-identifier enrichment unless the user confirms broader rights.
4. Discover uploadable ad accounts and show `Account Name (Account ID)`.
5. Confirm platform credentials can create, sync, and read back audiences.
6. Create a holdout/control group before enrichment.
7. Set a budget cap for fallback beyond Aviato/LimaData.

Do not proceed to paid fallback if the ad account cannot be discovered or validated. Fix the activation path first, otherwise enrichment spend may create a list that cannot be uploaded.

## Coverage Ladder

Run the ladder in this order, but do not stop personal-email hash enrichment just because a contact already has a work email. Work-email hashes are the baseline and holdout; personal email hashes are additive identifiers that should be collected for as many eligible contacts as possible.

Use these scopes:

- Baseline scope: all rows with first-party uploadable identifiers.
- Personal-hash scope: all eligible rows with enough identity context for the provider, including rows that already have work-email hashes.
- Provider-dedup scope: for a given paid provider, skip only rows that already have a usable personal email hash from an earlier personal-hash provider, unless the user explicitly asks to test overlap.
- Expanded fallback scope: rows still missing a personal email hash after Aviato/LimaData, not rows missing any uploadable identifier.

### L0: Source And Baseline

Build a baseline object from first-party identifiers:

- work email normalized and SHA-256 hashed once
- phone SHA-256 only if already present and permitted
- first name, last name, country, postal code where supported
- LinkedIn URL, company domain, company name, title for lineage and QA

Upload baseline separately. This is the denominator for lift.

### L1: Existing Hashes And Warehouse Edges

Use any existing paid-ads-safe hashes already present in the source system or warehouse.

Validation:

- accept only lowercase 64-character SHA-256 hex hashes;
- reject placeholders and malformed hashes;
- do not hash a provided hash again;
- record source columns used.

### L2: LinkedIn Repair

For rows missing verified LinkedIn profile URLs, run the LinkedIn URL lookup ladder before LinkedIn-dependent hash providers. Include rows that already have work emails; LinkedIn repair is meant to unlock personal-hash providers and improve match coverage beyond the work-email baseline.

Use cleaned account/company aliases and validate identity before merging:

```text
"{{full_name}}" ("{{account_name}}" OR "{{linkedin_company_name}}") site:linkedin.com/in -inurl:dir -inurl:pub
"{{full_name}}" "{{title}}" "{{linkedin_company_name}}" site:linkedin.com/in -inurl:dir -inurl:pub
"{{full_name}}" "{{account_name}}" site:linkedin.com/in -inurl:dir -inurl:pub
```

Accept a candidate only when:

- URL is `linkedin.com/in/`;
- first and last name match, allowing common nicknames;
- company/title evidence supports the match;
- ambiguous results are profile-scraped and revalidated before merge.

Do not spend heavily on LinkedIn repair when coverage is already high. Report attempted rows and recovered verified URLs.

### L3: Cost-Effective Hash Providers

Run Aviato and LimaData before broader fallback.

Use provider hashes as-is when they are valid SHA-256:

- Aviato hash provider on all eligible rows with LinkedIn/profile context, including rows that already have work-email hashes.
- LimaData audience identifier hashes on rows still missing a personal hash after Aviato, or as first provider when that is more cost-effective for the available inputs.

Extract hashes only from explicit hash fields such as:

- `matched_result`
- `result.data.hashedEmails[]`
- `result.data.hashed_email`
- `result.data.hashed_emails[].normalized_hash`
- `hash`
- `sha256`

Never upload a JSON object string as a hash value.

### L4: Raw Personal-Email Waterfall

Run this only when max coverage is requested and the budget cap covers it.

Try raw personal-email providers on rows still missing a personal email hash after the cost-effective hash pass. Do not exclude a row merely because it has a work email hash.

1. LeadMagic personal email
2. ContactOut pre-check, then paid reveal only for true rows
3. Wiza
4. Datagma
5. Crustdata
6. Prospeo
7. FullEnrich
8. People Data Labs or Deepline native personal-email waterfall

Provider output rules:

- include only fields explicitly typed as personal email;
- reject untyped scalar emails when they may be work emails;
- normalize raw personal emails with trim + lowercase;
- validate email syntax;
- SHA-256 hash exactly once;
- upload only `email_sha256` by default.

### L5: Phone Hashes

Do not buy mobile phones by default.

Use phone hashes only when:

- phones are already present and permitted; or
- the user explicitly approves mobile-phone enrichment and the budget cap.

Normalize phones consistently before hashing. Report phone-derived lift separately from email-derived lift.

### L6: Upload Variants

Create separate upload objects:

- baseline work identifiers
- baseline plus existing personal hashes
- baseline plus Aviato/LimaData personal hashes
- baseline plus max-coverage personal-email fallback
- phone-hash variant if used
- geo or account-tier cuts when relevant

Do not overwrite variants during experimentation. Separate audiences are required to calculate lift.

### L7: Platform Readback

After upload, poll platform status:

```bash
deepline tools execute google_ads_audiences_get_audience_status --payload '{"account_id":"<google_customer_id>","audience_id":"<audience_id>"}' --json
deepline tools execute meta_audiences_get_audience_status --payload '{"ad_account_id":"act_<meta_ad_account_id>","audience_id":"<audience_id>"}' --json
deepline tools execute linkedin_ads_audiences_get_audience_status --payload '{"account_id":"<linkedin_account_id>","audience_id":"<audience_id>"}' --json
```

Do not claim success from upload receipt alone. Success requires create, sync, and readback.

## Stop Conditions

Stop expanding coverage when any of these are true:

- budget cap is reached;
- remaining rows lack enough identity context for reliable lookup;
- provider returns are mostly work emails or invalid hashes;
- marginal unique-hash lift is below the user-defined threshold;
- platform match-rate lift does not justify another fallback layer;
- geography/rights constraints block further enrichment;
- account credential preflight fails.

When stopping, report the exact blocker and the next highest-value option.

## Reliability Checks

Before upload:

- `malformed_hashes = 0`
- `raw_email_fields_in_hash_only_payload = false`
- `double_hashed_provider_hashes = 0`
- `holdout_leaks = 0`
- `duplicate_hashes` are deduped before upload
- account name and ID are confirmed
- upload permission is confirmed

After upload:

- audience exists in the right account
- membership status is open or processing
- upload key type is correct
- invalid rows are reported
- match rate is reported only after platform returns it

## Final Report Shape

Use this structure:

```text
Coverage mode: max_coverage
Source rows:
Holdout rows:
Uploadable baseline rows:
Final uploadable rows:
Unique hashes by layer:
Remaining no-personal-hash rows:
Deepline spend:
Audience IDs by platform:
Current platform match rates:
Incremental matched people:
Cost per incremental matched person:
Recommended activation audience:
Remaining blockers:
```

The recommendation should be based on platform match-rate readback and economics, not on the file with the most enriched columns.
