# Amplemarket

Call `amplemarket_get_account_details` to verify a connection.

Call capability-specific actions directly. Use people search or company search
to find prospects. Use contacts and accounts to read and write CRM records. Use
sequences and lead lists to start outbound work. Use tasks and calls to read
workflow activity. Do not send REST work to the separate Amplemarket OAuth MCP
server.

All read actions and write actions use the Amplemarket workspace credential of
the caller. Call a write action only when the user asks for that workspace
change.

## Pagination

Supply the page size in a `page` object. Do not supply an integer.

```json
{ "page": { "size": 25 } }
```

Amplemarket declares the page size as a string on 15 operations and as an
integer on 2 operations. Deepline accepts both forms on every operation.

Read the next-page cursor from `_links.next` in the response. Supply that
cursor as `page.after`.

## Contact filters

`amplemarket_get_contacts` needs a minimum of one filter. Supply `name`,
`account_id`, or `ids`. Amplemarket rejects a request that has no filter.

## Contact creation

`amplemarket_post_contacts` associates a contact with an account when you
supply `company_domain` or `company_name`. The domain must match an active
Prospect Hub account. Omit both fields when no account exists. Call
`amplemarket_get_accounts` first to see the available accounts.

An excluded domain does not prevent contact creation. Amplemarket applies the
exclusion list to outbound sending only. Examine `amplemarket_get_excluded_domains`
before you create contacts for a compliance-sensitive workflow.

## Phone numbers

Amplemarket changes the format of a supplied phone number. The provider
returned `+1 202-555-0123` for the supplied value `+12025550123`. Do not
compare a returned number with a supplied number as a text string.

A phone number that a caller supplies has the source `uploaded_by_user`. A
phone number record also contains `kind` and `uploaded_id`.

## Disabled actions

Deepline disables 9 actions. Each disabled action returns HTTP 403 with the
code `INTEGRATION_PREREQUISITE_REQUIRED`. Deepline refuses the action before it
calls the provider. A disabled action consumes no credits.

Deepline disables these 5 actions because it does not have the exact purchased
USD rates for EMAIL_CREDITS and PHONE_CREDITS:

- `amplemarket_post_email_validations`
- `amplemarket_post_people_enrichment_requests`
- `amplemarket_get_people_find`
- `amplemarket_post_lead_lists`
- `amplemarket_post_lead_lists_id_leads`

Deepline disables these 4 actions because the official OpenAPI document has no
2xx JSON response example:

- `amplemarket_get_calls_id_recording`
- `amplemarket_post_phone_numbers_id_review`
- `amplemarket_post_tasks_id_complete`
- `amplemarket_post_tasks_id_skip`

`amplemarket_post_sequences_id_leads` is enabled. Use that action to add leads
to a sequence.

## Tasks

The Amplemarket API has no action that creates a task. A sequence creates the
tasks. A draft sequence creates no tasks. The API has no action that starts a
sequence. Start a sequence in the Amplemarket user interface.
