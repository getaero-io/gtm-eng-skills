# Workflow Sketches (Drafts)

> **Status: PLACEHOLDERS.** These workflow sketches are NOT ready to deploy.
> They contain placeholder IDs and secrets as `${...}` environment variables only.
> Use them as starting points for building real Deepline cloud workflows.

## What's here

| Sketch | Purpose |
| --- | --- |
| [`luma-registration-enrich.sketch.json`](luma-registration-enrich.sketch.json) | Standing Luma webhook → enrich → CRM upsert |

## How to use

1. Copy a sketch file
2. Keep `${...}` references in tracked JSON. Bind their values through your deployment tooling and secret store when building the private apply payload; never paste real keys, webhook URLs, or account IDs into repo files or commit the rendered payload. These sketches do not establish automatic environment-variable expansion by the CLI.
3. Update field mappings to match your CRM schema
4. Test with `dry_run: true` or a pilot event first
5. Deploy with `deepline workflows apply` (if using Deepline CLI)
6. Monitor logs and dead-letter queue for failures

## Placeholder conventions

All sketches use these placeholder patterns:

- `${HUBSPOT_PORTAL_ID}` — HubSpot portal ID
- `${HUBSPOT_API_KEY}` — HubSpot private app token
- `${ATTIO_WORKSPACE_ID}` — Attio workspace ID
- `${ATTIO_API_KEY}` — Attio API key
- `${LUMA_WEBHOOK_SECRET}` — Luma webhook signing secret
- `${SLACK_EVENT_OPS_CHANNEL}` — Slack incoming webhook URL
- `${DEEPLINE_API_KEY}` — Deepline API key (for enrichment)

## Field path conventions

Field references like `{{guest.name}}` or `{{enriched.linkedin_url}}` are schematic only.
Actual Luma webhook payloads or CRM field names will differ.

Consult:
- Luma webhook documentation for exact payload structure
- Your CRM's API documentation for field names and types
- `../luma-inbound-webhook-enrich/references/field-map.md` for common mappings

## Safety

- Never commit real API keys, portal IDs, or webhook URLs to public repos
- Use secret stores (environment variables, Deepline workflow secrets, etc.)
- Test workflows in a staging environment before production
- Set up monitoring and alerting for webhook failures
- Keep dead-letter queues for failed payloads so you can backfill later
