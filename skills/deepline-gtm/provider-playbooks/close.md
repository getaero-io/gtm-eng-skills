# Close CRM

- Connect your own Close API key from Close Settings → Developer → API Keys.
- Read, create and update leads (companies), contacts (people) and opportunities (deals). Read lead statuses and opportunity pipeline stages to choose the right status id.
- Start with a list action, then use a returned `id` for the matching get action. Contact lists accept `lead_id`; opportunity lists accept the documented lead, owner, status and date filters.
- A list call returns one page. Pass `_limit` and `_skip`, inspect `has_more`, and request the next page explicitly. Close enforces resource-specific maximum limits and offsets; this connector is not an unlimited bulk export.
- In the V2 SDK, read the full page from `toolResponse.rawV2`, including `data`, `has_more`, and any totals. The older flattened result view does not preserve pagination fields.
- `_fields` selects response fields. Selected fields can omit ids or other data you need for the next step.
- Preserve contact email and phone arrays. Opportunity monetary values are cents, with `value_currency` describing the currency.
- Updates are patches: send only fields to change. Supply the complete email, phone and URL lists you intend to store. Update nested contacts with the contact action, not the lead action.
- Lead writes expose name, description, URL, status, addresses and custom fields. Choose either `status` or `status_id`, never both. Add contacts separately after creating the company lead.
- Set custom fields with `custom_fields: { "cf_abc123": "value" }`. Use Close field ids, not labels; `null` clears a value. Updates also accept suffixes such as `"cf_abc123.add": "Wednesday"` or `"cf_abc123.remove": "Friday"` for multi-value fields.
- Pass `lead_id` when creating a contact or opportunity for an existing company. Without it, Close creates another lead: named after the contact, or Untitled for an opportunity.
- Each create or update writes CRM data. Use one stable Deepline idempotency key per intended write and keep it for recovery. After a timeout or unknown outcome, inspect the saved execution and CRM record before starting a new write. New keys or new runs can repeat the change. Do not opt writes into automatic error retries.
- Close does not document an upstream idempotency key for these endpoints. Deepline's execution key supports recovery; it does not make separate Close writes exactly-once.
- Deepline does not bill provider usage for these BYOK actions. The connected Close account's subscription, permissions and API limits apply.
- Event polling, messaging, deletion, merge operations and export jobs are not exposed.
