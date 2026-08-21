<!-- GENERATED FROM ProviderMonitorCapabilityDefinition; content-sha256: 90dec2d80c2d1ff720eba3567dd8ac57f140ab6c1468d11f0a3fb68188197057; run bun run docs:monitor-contract -->

# Monitor Contract Reference

This factual reference is generated from the same monitor capability contracts used by validation and the live `tools get` / `monitors available` surfaces. Keep rationale and workflows in hand-written guides.

## Shared lifecycle

- monitors check validates a definition locally and does not deploy, spend credits, or prove a future event will arrive.
- monitors deploy is a full desired definition. Use deploy --dry-run to inspect replacement and Deepline-credit effects; use monitors update for a patch.
- monitors get returns the stored deployed definition plus monitor_spec, whose fields list the deployable payload paths, descriptions, constraints, and provider-specific semantics for that monitor type.

## Shared errors

- Validation errors name the payload path and expected contract value; correct the definition and rerun monitors check.
- A paused monitor needs a balance or entitlement correction before reactivation. Deepline exposes Deepline pricing only.

## `attio.crm_events`

Managed Attio CRM event ingestion via a Deepline-owned webhook subscription.
### Executable examples

#### Record changes

```json
{
  "key": "attio-record-events",
  "tool": "attio.crm_events",
  "payload": {
    "event_types": [
      "record.created",
      "record.updated"
    ]
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `webhook` | `attio.attio_webhooks` | Managed Attio webhook binding metadata. |
| `subscriptions` | `attio.attio_webhook_subscriptions` | Attio event subscriptions configured by this monitor. |
| `events` | `attio.attio_events` | Attio CRM webhook events delivered to Deepline. |

#### Fields

| Field | Semantics |
| --- | --- |
| `event_types` | Attio webhook event types to ingest. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `findymail.signal_monitor`

Creates a Deepline-managed Findymail signal monitor data pipe and writes provider-native signal rows into Customer DB output tables.
### Executable examples

#### Track hiring keywords

```json
{
  "key": "job-change-signals",
  "tool": "findymail.signal_monitor",
  "payload": {
    "name": "Job change signals",
    "signal_type": "keyword_mention",
    "keywords": [
      "hiring",
      "job change"
    ],
    "enrichment_level": "email"
  }
}
```

#### Track target company job changes

```json
{
  "key": "target-company-job-changes",
  "tool": "findymail.signal_monitor",
  "payload": {
    "name": "Target company job changes",
    "signal_type": "job_change",
    "target_companies": [
      "stripe.com",
      "OpenAI"
    ],
    "icp_filters": {
      "countries": [
        "US"
      ],
      "employee_count_ranges": [
        "51-200",
        "201-500"
      ]
    }
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `signals` | `findymail.findymail_signals` | Detected Findymail signal rows emitted by the upstream signal monitor. |
| `monitor` | `findymail.findymail_signal_monitors` | Upstream Findymail signal monitor metadata persisted after deploy. |

#### Fields

| Field | Semantics |
| --- | --- |
| `name` | The upstream Findymail signal monitor name. |
| `signal_type` | Findymail signal family to monitor. Accepted values match the createAMonitor OpenAPI schema. |
| `keywords` | Keywords to track for keyword_mention, or for post_engagement when no post_url is provided. |
| `post_url` | LinkedIn post URL to monitor for post_engagement signals. |
| `profile_url` | LinkedIn profile URL to monitor as an alternative post_engagement source. |
| `engagement_types` | Engagement types to track for post_engagement monitors. |
| `enrichment_level` | Optional Findymail contact enrichment level for matched contacts. |
| `lead_list_id` | Optional Findymail lead list id for automatically saving matched contacts. |
| `ai_relevance_prompt` | Optional custom prompt used by Findymail to score AI relevance. |
| `target_companies` | Company names or domains used to narrow new_hire and job_change signals. |
| `is_shared` | Optional opt-in flag to share the monitor with the user's current Findymail team. |
| `icp_filters` | Optional ICP criteria used to narrow Findymail signal matching. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `heyreach.campaign_events`

Managed HeyReach campaign event ingestion via a Deepline-owned webhook subscription.
### Executable examples

#### Reply events

```json
{
  "key": "heyreach-replies",
  "tool": "heyreach.campaign_events",
  "payload": {
    "event_type": "MESSAGE_REPLY_RECEIVED",
    "campaign_ids": [
      23501,
      23502
    ]
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `webhook` | `heyreach.heyreach_webhooks` | Managed HeyReach webhook binding metadata. |
| `campaigns` | `heyreach.heyreach_webhook_campaigns` | HeyReach campaign scopes configured by this monitor. |
| `events` | `heyreach.heyreach_events` | HeyReach webhook events delivered to Deepline. |

#### Fields

| Field | Semantics |
| --- | --- |
| `event_type` | HeyReach webhook event type to ingest. |
| `campaign_ids` | Optional HeyReach campaign ids to scope this monitor. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `instantly.campaign_events`

Managed Instantly campaign event ingestion via a Deepline-owned webhook subscription.
### Executable examples

#### Interested leads

```json
{
  "key": "instantly-interested-leads",
  "tool": "instantly.campaign_events",
  "payload": {
    "event_type": "lead_interested",
    "campaign_id": "camp_123"
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `webhook` | `instantly.instantly_webhooks` | Managed Instantly webhook binding metadata. |
| `webhook_events` | `instantly.instantly_webhook_events` | Instantly webhook events delivered to Deepline. |

#### Fields

| Field | Semantics |
| --- | --- |
| `event_type` | Instantly webhook event type to ingest. |
| `campaign_id` | Optional Instantly campaign id to scope the webhook. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `lemlist.campaign_events`

Managed Lemlist campaign event ingestion via a Deepline-owned webhook subscription.
### Executable examples

#### Campaign replies

```json
{
  "key": "lemlist-replies",
  "tool": "lemlist.campaign_events",
  "payload": {
    "event_type": "emailsReplied",
    "campaign_id": "cam_123"
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `webhook` | `lemlist.lemlist_webhooks` | Managed Lemlist webhook binding metadata. |
| `campaign_events` | `lemlist.lemlist_campaign_events` | Lemlist campaign events delivered to Deepline. |

#### Fields

| Field | Semantics |
| --- | --- |
| `event_type` | Lemlist campaign webhook event type to ingest. |
| `campaign_id` | Optional Lemlist campaign id to scope the webhook. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `rb2b.visitor_events`

Ingest RB2B identified-visitor webhook events after you add the Deepline endpoint in RB2B.
### Executable examples

#### Website visitors

```json
{
  "key": "rb2b-website-visitors",
  "tool": "rb2b.visitor_events",
  "payload": {}
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `events` | `rb2b.visitor_events` | RB2B identified visitor webhook events delivered to Deepline. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `snitcher.website_sessions`

Capture signed, session-based Radar website activity from the Deepline Analytics tracker.
### Executable examples

#### Website sessions

```json
{
  "key": "deepline-analytics-sessions",
  "tool": "snitcher.website_sessions",
  "payload": {
    "domains": [
      "example.com"
    ]
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `sessions` | `deepline_analytics.sessions` | Signed, session-based Deepline Analytics events. |

#### Fields

| Field | Semantics |
| --- | --- |
| `domains` | Provider-specific domains monitor filter. |
| `formTracking` | Provider-specific formTracking monitor filter. |
| `clickTracking` | Provider-specific clickTracking monitor filter. |
| `customEvents` | Provider-specific customEvents monitor filter. |
| `waitForConsent` | Provider-specific waitForConsent monitor filter. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `smartlead.campaign_events`

Managed Smartlead campaign event ingestion via a Deepline-owned campaign webhook subscription.
### Executable examples

#### Campaign replies

```json
{
  "key": "smartlead-replies",
  "tool": "smartlead.campaign_events",
  "payload": {
    "campaign_id": 372,
    "event_types": [
      "EMAIL_REPLY"
    ]
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `webhook` | `smartlead.smartlead_webhooks` | Managed Smartlead webhook binding metadata. |
| `subscriptions` | `smartlead.smartlead_webhook_event_subscriptions` | Smartlead event subscriptions configured by this monitor. |
| `outreach_events` | `smartlead.smartlead_outreach_events` | Smartlead outreach events delivered to Deepline. |

#### Fields

| Field | Semantics |
| --- | --- |
| `campaign_id` | Smartlead campaign id to scope this webhook monitor. |
| `event_types` | Smartlead campaign webhook event types to ingest. |
| `categories` | Optional Smartlead categories for category-based webhook events. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

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
    "departments": [
      "Engineering"
    ],
    "seniorities": [
      "Director",
      "Vice President"
    ],
    "job_titles": "\"VP Engineering\" OR \"Head of Product\""
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `company_job_openings` | `deepline_native.deepline_native_company_job_openings` | Streams new job postings at a company into your warehouse and triggers plays. |
| `company_promotions` | `deepline_native.deepline_native_company_promotions` | Streams internal promotions at a company into your warehouse and triggers plays. |
| `company_mentions` | `deepline_native.deepline_native_company_mentions` | Streams news and web mentions of a company into your warehouse and triggers plays. |
| `company_new_hires` | `deepline_native.deepline_native_company_new_hires` | Streams new hires at a company into your warehouse and triggers plays. |
| `company_reviews` | `deepline_native.deepline_native_company_reviews` | Streams new employer and product reviews of a company into your warehouse and triggers plays. |
| `company_social_posts` | `deepline_native.deepline_native_company_social_posts` | Streams new social posts from a company into your warehouse and triggers plays. |
| `company_social_engagements` | `deepline_native.deepline_native_company_social_engagements` | Streams social engagements on a company into your warehouse and triggers plays. |

#### Fields

| Field | Semantics |
| --- | --- |
| `job_titles` | Provider-facing title expression. Deepline validates its grammar and forwards it unchanged; it overrides departments and seniorities when present. Stored readback does not prove upstream matching or billing semantics. |
| ↳ applies | Only company_new_hires, company_job_openings, company_promotions, and company_social_posts_cxo. |
| ↳ precedence | job_titles overrides departments and seniorities. |
| ↳ grammar | Bare single-word terms and double-quoted multi-word phrases joined with uppercase AND, OR, and NOT. Parentheses group expressions. |
| ↳ grammar precedence | NOT > AND > OR |
| ↳ grammar example | `("VP Sales" OR "Head of Product") AND NOT (Coordinator OR Aide OR DSP)` |
| `departments` | Persona department filter. |
| ↳ applies | Only company_new_hires, company_job_openings, company_promotions, and company_social_posts_cxo; ignored when job_titles is present. |
| `seniorities` | Persona seniority filter. |
| ↳ applies | Only company_new_hires, company_job_openings, company_promotions, and company_social_posts_cxo; ignored when job_titles is present. |
| `updates_since` | Permanent historical eligibility boundary for a new radar, not a query-time date filter. |
| ↳ grammar | RFC3339 timestamp with Z or a numeric UTC offset; now or earlier and within five calendar years. |

#### Pricing, identity, and updates

- Pricing: Deepline pricing is selected by radar_type and returned by the live monitor contract. Provider spend is not exposed.
- Identity: One Deepline monitor identity is radar_type plus domain per organization.
- Update: A filter change replaces the upstream radar under the same Deepline monitor key and retains Customer DB rows.
- Backfill: Historical matching can arrive during the first 24 hours. A filter update does not request historical findings that would newly match.

#### Troubleshooting

- **job_titles is rejected:** Use ("VP Sales" OR "Head of Product") AND NOT (Coordinator OR Aide OR DSP); operators must be uppercase.

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

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `contact_job_changes` | `deepline_native.deepline_native_contact_job_changes` | Streams job changes for a tracked contact into your warehouse and triggers plays. |
| `contact_social_posts` | `deepline_native.deepline_native_contact_social_posts` | Streams new social posts from a tracked contact into your warehouse and triggers plays. |
| `contact_social_engagements` | `deepline_native.deepline_native_contact_social_engagements` | Streams social engagements by a tracked contact into your warehouse and triggers plays. |

#### Fields

| Field | Semantics |
| --- | --- |
| `radar_type` | Deepline contact radar output family. The selected value determines the derived output table. |
| `profile_url` | Contact profile URL used to create or seed the upstream radar. |
| `domain` | Company domain where the contact works. Required for contact_job_changes (the company the contact is tracked at). |
| `email` | Contact email address, used alongside profile_url/full_name to seed contact_job_changes tracking. |
| `full_name` | Contact full name, used alongside profile_url/email to seed contact_job_changes tracking. |
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

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `industry_mentions` | `deepline_native.deepline_native_industry_mentions` | Streams news and web mentions across an industry into your warehouse and triggers plays. |
| `industry_job_openings` | `deepline_native.deepline_native_industry_job_openings` | Streams new job postings across an industry into your warehouse and triggers plays. |
| `industry_funding_rounds` | `deepline_native.deepline_native_industry_funding_rounds` | DeeplineNativeIndustryFundingRoundsRow |
| `industry_funding_references` | `deepline_native.deepline_native_industry_funding_references` | DeeplineNativeIndustryFundingReferencesRow |

#### Fields

| Field | Semantics |
| --- | --- |
| `radar_type` | Deepline industry radar output family. The selected value determines the derived output tables. |
| `industry` | Industry or market segment used to create or seed the upstream radar. |
| `countries` | Optional for 'industry_job_openings' only. Array of country names to filter job postings by location. Maximum 5 countries allowed. Examples: 'United States', 'Canada', 'United Kingdom'. |
| `updates_since` | Optional permanent radar starting point. Use an RFC3339 timestamp with a time zone to receive qualifying historical findings from that instant. Omit to start at radar creation. The timestamp must be in the past and within five calendar years. Historical processing can continue for the first 24 hours. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: One monitor identity uses radar_type, industry.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `theirstack.saved_search_webhook`

Creates a Deepline-managed TheirStack saved search and webhook data pipe, then writes provider-native saved search, webhook, and event rows into Customer DB output tables.
### Executable examples

#### Track new sales engineering jobs

```json
{
  "key": "their-stack-sales-engineering-jobs",
  "tool": "theirstack.saved_search_webhook",
  "payload": {
    "type": "jobs",
    "name": "Sales engineering jobs",
    "body": {
      "job_title_or": [
        "Sales Engineer"
      ],
      "job_country_code_or": [
        "US"
      ],
      "posted_at_max_age_days": 7,
      "include_total_results": false
    }
  }
}
```

#### Track companies matching hiring filters

```json
{
  "key": "their-stack-hiring-companies",
  "tool": "theirstack.saved_search_webhook",
  "payload": {
    "type": "companies",
    "name": "Hiring companies",
    "body": {
      "company_country_code_or": [
        "US"
      ],
      "job_title_or": [
        "Account Executive"
      ],
      "include_total_results": false
    }
  }
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `saved_search` | `theirstack.theirstack_saved_searches` | Managed TheirStack saved search metadata persisted after deploy. |
| `webhook` | `theirstack.theirstack_webhooks` | Managed TheirStack webhook binding metadata persisted after deploy. |
| `job_events` | `theirstack.theirstack_job_events` | TheirStack job webhook events delivered to Deepline. |
| `company_events` | `theirstack.theirstack_company_events` | TheirStack company webhook events delivered to Deepline. |

#### Fields

| Field | Semantics |
| --- | --- |
| `type` | TheirStack saved search type. Jobs produce job event rows; companies produce company event rows. |
| `body` | TheirStack saved search filter body. For type "jobs", use job search filters. For type "companies", use company search filters. |
| `name` | Optional upstream saved search name. Deepline generates one from the monitor key when omitted. |
| `description` | Optional upstream webhook description. Deepline generates one from the monitor key when omitted. |
| `is_alert_active` | Whether TheirStack email alerts are active for the saved search. Defaults to false for Deepline data-pipe monitors. |
| `listening_start_time` | Optional ISO timestamp for when the webhook should start listening. Omit to let TheirStack use its default behavior. |
| `trigger_once_per_company` | For job saved searches, collapse multiple matching jobs from the same company into one webhook event when true. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.

## `vector.visitor_events`

Ingest Vector contact.visited events after you add the Deepline callback URL to a live Vector segment.
### Executable examples

#### High-intent website visitors

```json
{
  "key": "vector-high-intent-visitors",
  "tool": "vector.visitor_events",
  "payload": {}
}
```

### Outputs

| Stream | Customer DB table | Meaning |
| --- | --- | --- |
| `events` | `vector.visitor_events` | Vector contact.visited events delivered to Deepline. |

#### Pricing, identity, and updates

- Pricing: Use the Deepline pricing returned by tools get, monitors available, check, or deploy --dry-run. Provider spend is not exposed.
- Identity: This monitor uses the provider capability identity declared by Deepline.
- Update: Use monitors update for a patch or deploy for a complete desired definition.
- Backfill: Existing Customer DB rows are retained; this capability does not promise provider backfill unless its provider documentation says otherwise.

#### Troubleshooting

- **Validation failed:** Correct the reported payload path, then run monitors check again.
