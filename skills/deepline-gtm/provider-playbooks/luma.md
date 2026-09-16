# Luma Provider Agent Guidance

## Overview

Luma is an event platform API for managing calendars, events, guests, tickets, memberships, and webhooks. All operations require a user-owned Luma API key.

## Authentication

- **Required**: User-owned Luma API key
- **Header**: `x-luma-api-key`
- **Rate Limits**:
  - Calendar API keys: 200 requests/minute per calendar
  - Organization API keys: 500 requests/minute per organization
  - Luma shares each account's quota across GET and POST. Deepline does not apply a provider-wide bucket across customer keys. Honor Luma's `Retry-After` header on 429 responses.

## Priority Operations for GTM Workflows

For event workflows, use these operations:

1. **`luma_get_v1_users_get_self`** - Auth check / verify API key
2. **`luma_get_v1_events_get`** - Get event details by event_id
3. **`luma_get_v1_events_guests_list`** - List guests for an event (with filtering by approval_status)
4. **`luma_post_v1_events_guests_update_status`** - Update guest status (approve, waitlist, decline, etc.)

## Common Workflows

### Event Management

- Create events: `luma_post_v1_events_create`
- Update events: `luma_post_v1_events_update`
- List calendar events: `luma_get_v1_calendars_events_list`
- Cancel events: `luma_post_v1_events_cancel`

### Guest Management

- List guests: `luma_get_v1_events_guests_list` (filter by `approval_status`: approved, session, pending_approval, invited, declined, waitlist)
- Get guest details: `luma_get_v1_events_guests_get`
- Add guests: `luma_post_v1_events_guests_add`
- Update status: `luma_post_v1_events_guests_update_status` with `event_id`, `guest_id`, and `status` (`approved`, `declined`, `pending_approval`, or `waitlist`)
- Send invites: `luma_post_v1_events_guests_send_invites`

### Contact Management

- List contacts: `luma_get_v1_calendars_contacts_list`
- Import contacts: `luma_post_v1_calendars_contacts_import`
- Tag contacts: `luma_post_v1_calendars_contact_tags_apply`

## Billing

All Luma operations are **no-bill** for Deepline. Access is gated by the caller's Luma API key subscription. Deepline does not purchase or meter Luma provider credits.

## Notes

- Event IDs typically start with `evt-`
- Use pagination with `pagination_cursor` and `pagination_limit` for list operations
- Guest list supports sorting by name, email, created_at, registered_at, checked_in_at
- Approval statuses: approved, session, pending_approval, invited, declined, waitlist

## Contract examples

The checked-in request fixtures and response examples are synthetic schema examples, not live account data or captured provider responses. Every operation has a request fixture for local validation, including writes. Do not execute these fixtures against an account. Supply real identifiers and review the operation's side effects before calling it.

Response examples use the Deepline `data` envelope and preserve Luma field names, such as guest `id`, `user_email`, and `user_name`. Updating a guest's status returns an empty object in `data`.

The five response samples pass the checked-in Luma OpenAPI response schemas after removing the outer Deepline `data` envelope. This is schema validation, not live-response verification. See `docs.txt` for the official endpoint references and response evidence limitations.
