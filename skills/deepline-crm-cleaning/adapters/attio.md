# Attio adapter

Verify objects, attributes, plan, permissions, and the live connection contract. A documented beta endpoint does not prove support. Apply the safety rule before external actions.

| Area           | Check                                                                              |
| -------------- | ---------------------------------------------------------------------------------- |
| Schema         | Object and list attributes; writable, unique, multivalue, and reference settings   |
| Identity       | Separate People and Companies from list entries and workflow state                 |
| Prevention     | Actual unique matching attribute, canonical key, and collision policy              |
| Shared domains | Preserve separate companies when Domains uniqueness conflicts with shared websites |
| Values         | Append, replace, omit, and clear behavior                                          |
| Hierarchy      | Reference direction, target existence, and allowed link count                      |
| Merge          | New result ID, asynchronous completion, and non-idempotent beta operation          |
| Events         | One source-to-result alias for each original record's merge event                  |

Do not force shared websites into unique Domains attributes. Keep legal identity and website evidence separate. Report unsupported mappings.

Upsert retains or appends matching-attribute values but replaces other supplied multivalue attributes. Read the operation contract before proposing edits. Keep object updates separate from list-entry state.

Keep custom-object merge behavior unverified until tested in approved disposable records. Reconcile status after timeouts or asynchronous responses. Deleting a merge result does not restore the originals.

Keep candidate domains outside unique fields and references until verified. Retain unsupported relationship types and dates separately.

Verify webhook signatures and deduplicate by delivery identity. Deduplicating only by result ID loses a source alias. Check history restrictions and changes during offset pagination.

**Complete when:** each required capability is passed, failed, not run, or unsupported. Test unique-key races, multivalue changes, result IDs, both aliases, unknown responses, and pagination.

Official sources: [objects](https://docs.attio.com/rest-api/endpoint-reference/objects/list-objects), [attributes](https://docs.attio.com/rest-api/endpoint-reference/attributes/list-attributes), [unique imports](https://attio.com/help/reference/imports-exports/csv-imports/bulk-update-records-via-csv-import), [upsert](https://docs.attio.com/rest-api/endpoint-reference/records/upsert-a-record), [merge API](https://docs.attio.com/rest-api/endpoint-reference/records/merge-two-records), [merge/delete behavior](https://attio.com/help/reference/managing-your-data/records/merge-and-delete-records), [merge event](https://docs.attio.com/rest-api/webhook-reference/record-events/recordmerged), [webhooks](https://docs.attio.com/rest-api/guides/webhooks), [history](https://docs.attio.com/rest-api/endpoint-reference/records/list-record-attribute-values), [pagination](https://docs.attio.com/rest-api/guides/pagination), [record references](https://docs.attio.com/rest-api/attribute-types/attribute-types-record-reference).
