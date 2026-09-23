<!-- GENERATED FROM ProviderMonitorCapabilityDefinition; content-sha256: 0f5ed34c2f82531bc981d7ee93b7ae7612702f0aedd7efd09305b2c319bd98f6; run bun run docs:monitor-contract -->

# Monitor Contract Reference

This factual reference is generated from the same monitor capability contracts used by validation and the live `tools get` / `monitors available` surfaces. Keep rationale and workflows in hand-written guides.

## Shared lifecycle

- monitors check validates a definition locally and does not deploy, spend credits, or prove a future event will arrive.
- monitors deploy is a full desired definition. Use deploy --dry-run to inspect provider and Deepline-credit effects; use monitors update for a patch.
- monitors get returns the stored deployed definition plus monitor_spec, whose fields list the deployable payload paths, descriptions, constraints, and provider-specific semantics for that monitor type.

## Shared errors

- Validation errors name the payload path and expected contract value; correct the definition and rerun monitors check.
- A paused monitor needs a balance or entitlement correction before reactivation. Deepline exposes Deepline pricing only.

## `deepline_native.company_radar`

Creates a Deepline Native company radar data pipe and writes Deepline Native company event rows into Customer DB output tables.

### Executable examples

#### Track company job openings

```json
{
  "key": "job-openings",
  "tool": "deepline_native.company_radar",
  "payload": {
    "domain": "stripe.com",
    "radar_type": "company_job_openings"
  }
}
```

#### Filter new-hire tracking by title and department

```json
{
  "key": "exec-hires",
  "tool": "deepline_native.company_radar",
  "payload": {
    "domain": "stripe.com",
    "radar_type": "company_new_hires",
    "departments": ["Engineering"],
    "seniorities": ["Director", "Vice President"],
    "job_titles": "\"VP Engineering\" OR \"Head of Product\""
  }
}
```

### Outputs

| Stream                       | Customer DB table                                            | Meaning                                                                                       |
| ---------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `company_job_openings`       | `deepline_native.deepline_native_company_job_openings`       | Streams new job postings at a company into your warehouse and triggers plays.                 |
| `company_promotions`         | `deepline_native.deepline_native_company_promotions`         | Streams internal promotions at a company into your warehouse and triggers plays.              |
| `company_mentions`           | `deepline_native.deepline_native_company_mentions`           | Streams news and web mentions of a company into your warehouse and triggers plays.            |
| `company_new_hires`          | `deepline_native.deepline_native_company_new_hires`          | Streams new hires at a company into your warehouse and triggers plays.                        |
| `company_reviews`            | `deepline_native.deepline_native_company_reviews`            | Streams new employer and product reviews of a company into your warehouse and triggers plays. |
| `company_social_posts`       | `deepline_native.deepline_native_company_social_posts`       | Streams new social posts from a company into your warehouse and triggers plays.               |
| `company_social_engagements` | `deepline_native.deepline_native_company_social_engagements` | Streams social engagements on a company into your warehouse and triggers plays.               |

#### Fields

| Field             | Semantics                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `job_titles`      | Provider-facing title expression. Deepline validates its grammar and forwards it unchanged; it overrides departments and seniorities when present. Stored readback does not prove upstream matching or billing semantics.                                                                                                                                                                                                                                                                                                                                       |
| ↳ applies         | Only company_new_hires, company_job_openings, company_promotions, and company_social_posts_cxo.                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ↳ precedence      | job_titles overrides departments and seniorities.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ↳ grammar         | Double-quoted title terms joined with uppercase AND, OR, and NOT. Parentheses are not part of the documented grammar.                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ↳ grammar example | `"VP" OR "Head of Sales"`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `departments`     | Persona department filter.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ↳ applies         | Only company_new_hires, company_job_openings, company_promotions, and company_social_posts_cxo; ignored when job_titles is present.                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `seniorities`     | Persona seniority filter.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ↳ applies         | Only company_new_hires, company_job_openings, company_promotions, and company_social_posts_cxo; ignored when job_titles is present.                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `updates_since`   | Use this only to request historical findings; it is not a query-time date filter. Omit it for a future-only start at provider creation. For new-hire and promotion radars, source dates are evaluated at calendar-month precision even though the exact submitted timestamp is preserved in the radar response, so Deepline rejects current-month values for those radar types. During initial engagement history, the parent post’s publication time sets eligibility; recurring engagement delivery uses when Deepline Native first discovers the engagement. |
| ↳ applies         | Calendar-month source-date precision applies to company_new_hires and company_promotions. The engagement timing rule applies to initial and recurring social-engagement delivery.                                                                                                                                                                                                                                                                                                                                                                               |
| ↳ grammar         | RFC3339 timestamp with Z or a numeric UTC offset; now or earlier and within five calendar years.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

#### Pricing, identity, and updates

- Pricing: Deepline pricing is selected by radar_type and returned by the live monitor contract. Provider spend is not exposed.
- Identity: One Deepline monitor identity is radar_type plus domain per organization.
- Update: A filter change replaces the upstream radar under the same Deepline monitor key and retains Customer DB rows.
- Backfill: Historical matching can arrive during the first 24 hours. A filter update does not request historical findings that would newly match.

#### Troubleshooting

- **job_titles is rejected:** Use "VP" OR "Head of Sales"; operators must be uppercase.

## `deepline_native.contact_radar`

Creates a Deepline-managed contact radar data pipe and writes provider-native contact event rows into Customer DB output tables.

### Executable examples

#### Track contact job changes

```json
{
  "key": "contact-job-changes",
  "tool": "deepline_native.contact_radar",
  "payload": {
    "profile_url": "https://www.linkedin.com/in/example",
    "domain": "stripe.com",
    "radar_type": "contact_job_changes"
  }
}
```

### Outputs

| Stream                       | Customer DB table                                            | Meaning                                                                                 |
| ---------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `contact_job_changes`        | `deepline_native.deepline_native_contact_job_changes`        | Streams job changes for a tracked contact into your warehouse and triggers plays.       |
| `contact_social_posts`       | `deepline_native.deepline_native_contact_social_posts`       | Streams new social posts from a tracked contact into your warehouse and triggers plays. |
| `contact_social_engagements` | `deepline_native.deepline_native_contact_social_engagements` | Streams social engagements by a tracked contact into your warehouse and triggers plays. |

#### Fields

| Field           | Semantics                                                                                                                                                                                                                                                                                                     |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `radar_type`    | Deepline contact radar output family. The selected value determines the derived output table.                                                                                                                                                                                                                 |
| `profile_url`   | Contact profile URL used to create or seed the upstream radar.                                                                                                                                                                                                                                                |
| `domain`        | Company domain where the contact works. Required for contact_job_changes (the company the contact is tracked at).                                                                                                                                                                                             |
| `email`         | Contact email address, used alongside profile_url/full_name to seed contact_job_changes tracking.                                                                                                                                                                                                             |
| `full_name`     | Contact full name, used alongside profile_url/email to seed contact_job_changes tracking.                                                                                                                                                                                                                     |
| `updates_since` | Optional permanent radar starting point. Use an RFC3339 timestamp with a time zone to receive qualifying historical findings from that instant. Omit to start at radar creation. The timestamp must be in the past and within five calendar years. Historical processing can continue for the first 24 hours. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: One monitor identity uses radar_type, profile_url.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `deepline_native.industry_radar`

Creates a Deepline-managed industry radar data pipe and writes provider-native industry event rows into Customer DB output tables.

### Executable examples

#### Track industry mentions

```json
{
  "key": "ai-industry-mentions",
  "tool": "deepline_native.industry_radar",
  "payload": {
    "industry": "artificial intelligence",
    "radar_type": "industry_mentions"
  }
}
```

### Outputs

| Stream                        | Customer DB table                                             | Meaning                                                                                  |
| ----------------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `industry_mentions`           | `deepline_native.deepline_native_industry_mentions`           | Streams news and web mentions across an industry into your warehouse and triggers plays. |
| `industry_job_openings`       | `deepline_native.deepline_native_industry_job_openings`       | Streams new job postings across an industry into your warehouse and triggers plays.      |
| `industry_funding_rounds`     | `deepline_native.deepline_native_industry_funding_rounds`     | DeeplineNativeIndustryFundingRoundsRow                                                   |
| `industry_funding_references` | `deepline_native.deepline_native_industry_funding_references` | DeeplineNativeIndustryFundingReferencesRow                                               |

#### Fields

| Field           | Semantics                                                                                                                                                                                                                                                                                                     |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `radar_type`    | Deepline industry radar output family. The selected value determines the derived output tables.                                                                                                                                                                                                               |
| `industry`      | Industry or market segment used to create or seed the upstream radar.                                                                                                                                                                                                                                         |
| `countries`     | Optional for 'industry_job_openings' only. Array of country names to filter job postings by location. Maximum 5 countries allowed. Examples: 'United States', 'Canada', 'United Kingdom'.                                                                                                                     |
| `updates_since` | Optional permanent radar starting point. Use an RFC3339 timestamp with a time zone to receive qualifying historical findings from that instant. Omit to start at radar creation. The timestamp must be in the past and within five calendar years. Historical processing can continue for the first 24 hours. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: One monitor identity uses radar_type, industry.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.
