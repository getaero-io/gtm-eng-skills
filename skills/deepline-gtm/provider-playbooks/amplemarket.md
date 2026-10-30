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

## Billing and availability

Amplemarket uses the customer's connected workspace credential. Inspect the
exact action's Deepline pricing before a batch and use `deepline billing balance`
for the Deepline balance. A connected Amplemarket subscription may impose its
own limits. Treat `insufficient_credits` as an exhausted connected account limit.

Some upstream actions are unavailable in Deepline. Inspect the current catalog
availability and reason before building a workflow around call recordings,
phone review, or task completion/skip. An upstream API operation is not proof
that a public Deepline action exists.

`amplemarket_post_sequences_id_leads` adds leads to a sequence.

## Tasks

The Amplemarket API has no action that creates a task. A sequence creates the
tasks. A draft sequence creates no tasks. The API has no action that starts a
sequence. Start a sequence in the Amplemarket user interface.
