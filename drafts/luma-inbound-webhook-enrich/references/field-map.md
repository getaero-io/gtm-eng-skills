# CRM Field Mapping Reference

## Standard fields (typical CRM/DB schema)

| Luma field | CRM field | Notes |
| --- | --- | --- |
| `guest.email` | `email` | Primary key for upsert |
| `guest.name` | `full_name` or split to `first_name` + `last_name` | Normalize capitalization |
| `event.name` | `event_registered` | Store event name or ID |
| `registration.timestamp` | `event_registration_date` | ISO 8601 |
| `registration.status` | `event_status` | pending / approved / waitlist / cancelled |

## Enriched fields (from Deepline or other providers)

| Enrichment | CRM field | Provider |
| --- | --- | --- |
| LinkedIn profile URL | `linkedin_url` | Deepline, PDL, LeadMagic |
| Job title | `title` | LinkedIn via Deepline |
| Company name | `company` | LinkedIn via Deepline |
| Company domain | `company_domain` | Enrichment or normalized from email |
| Company size | `company_employee_count` | Crustdata, PDL |
| Company industry | `company_industry` | Crustdata, PDL |
| Email validation | `email_valid` | Hunter, ZeroBounce, Prospeo |
| Email deliverability | `email_deliverable` | Hunter, ZeroBounce |

## Segment/scoring fields

| Field | Type | Notes |
| --- | --- | --- |
| `icp_segment` | hot / warm / low / skip | From scoring logic |
| `tal_match` | boolean | True if company in target account list |
| `icp_score` | 0-100 | Composite score |

## Event-specific fields

| Field | Type | Notes |
| --- | --- | --- |
| `event_checked_in` | boolean | Updated day-of or via webhook |
| `event_no_show` | boolean | Updated post-event |
| `event_feedback_submitted` | boolean | If post-event survey exists |

## Optional: lifecycle tracking

| Field | Type | Notes |
| --- | --- | --- |
| `first_event_date` | date | First event registration |
| `total_events_registered` | integer | Count of registrations |
| `total_events_attended` | integer | Count of check-ins |

## Webhook versioning

When updating field mappings:

1. Bump workflow/play version (e.g. `v1` → `v2`)
2. Document changes in a `CHANGELOG.md`
3. Test on a dry-run branch before deploying to prod
4. Consider backfilling historical records if critical fields changed

## Secrets / env vars

Never hardcode in SKILL.md or public repos. Keep these references in tracked JSON; bind values through deployment tooling and a secret store in the private apply payload, and never commit that rendered payload. Use:

- `${HUBSPOT_PORTAL_ID}` — HubSpot portal ID
- `${HUBSPOT_API_KEY}` — HubSpot private app token
- `${ATTIO_WORKSPACE_ID}` — Attio workspace ID
- `${ATTIO_API_KEY}` — Attio API key
- `${LUMA_WEBHOOK_SECRET}` — Luma webhook signing secret
- `${SLACK_WEBHOOK_URL}` — Slack incoming webhook for notifications
