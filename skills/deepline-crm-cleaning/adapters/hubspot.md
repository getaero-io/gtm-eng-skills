# HubSpot adapter

Verify portal schema, permissions, app version, and the live connection contract. This guide does not certify a write adapter. Apply the safety rule before any external action.

| Area       | Check                                                                                        |
| ---------- | -------------------------------------------------------------------------------------------- |
| Schema     | Writable properties, directional association labels, limits, and schema hash                 |
| Identity   | Separate Contact, Company, and Lead objects; lifecycle stage is not a Lead object            |
| Reads      | Complete object and association pages; reconcile totals and concurrent changes               |
| Prevention | Verified custom unique keys; company creation through the API does not deduplicate by domain |
| Aliases    | Primary and additional emails and domains; resulting-ID mappings                             |
| Hierarchy  | Native one-parent-per-child limit; separate richer types and dates                           |
| Merge      | Actual resulting ID, portal behavior, fields, associations, and integration effects          |
| Recovery   | Compensating options; no native unmerge                                                      |

Use the portal's actual properties and association IDs. Check email upsert and custom-key upsert behavior separately. A trace ID is not an idempotency guarantee.

A read before a write cannot prevent a concurrent edit without supported conditional writes. Report that limit.

Check Lead effects before removing links. Removing all primary associations can delete the Lead. Preserve the required associated contact.

Keep additional-domain evidence outside property history. Additional domains affect automatic association but are not fully represented in domain history. Preview those effects before proposing domain changes.

Keep unverified domains outside aliases and parent-child fields. Preserve unsupported relationship types and dates in a configured representation.

Verify the change-capture contract. Push subscriptions and the webhook journal differ. Retain delivery IDs, merge aliases, and event-gap recovery. Read limits from the current app and endpoint.

**Complete when:** each required capability is passed, failed, not run, or unsupported. Test unique-key races, result IDs, preservation, stale writes, unknown responses, repeated events, and pagination.

Official sources: [properties](https://developers.hubspot.com/docs/api-reference/legacy/crm/properties/guide), [associations](https://developers.hubspot.com/docs/api-reference/latest/crm/associations/associate-records/guide), [deduplication](https://knowledge.hubspot.com/records/deduplication-of-records), [contacts](https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/contacts/guide), [Leads](https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/leads/guide), [additional domains](https://knowledge.hubspot.com/records/add-multiple-domain-names-to-a-company-record), [parent/child](https://knowledge.hubspot.com/records/add-a-parent-or-child-company), [merge behavior](https://knowledge.hubspot.com/records/merge-records), [webhooks](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/features/configure-webhooks), [journal](https://developers.hubspot.com/docs/api-reference/legacy/webhooks/webhooks-journal), [limits](https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines).
