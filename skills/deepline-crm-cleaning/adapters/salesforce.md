# Salesforce adapter

Verify the Salesforce organization, API version, permissions, record types, validation rules, duplicate rules, and connection contract. Apply the safety rule before external actions.

| Area       | Check                                                                                  |
| ---------- | -------------------------------------------------------------------------------------- |
| Schema     | Required sObjects, field access, custom fields, record types, and package constraints  |
| Identity   | Keep Lead, Contact, Account, and Person Account representations separate               |
| Reads      | Complete query locators and permitted links; inaccessible records remain unknown       |
| Prevention | Both External ID and Unique for same-object uniqueness; define case behavior           |
| Aliases    | Website and Email are scalar; preserve aliases and history separately                  |
| Hierarchy  | Map the selected type to `Account.ParentId`; preserve richer types and dates elsewhere |
| Merge      | Supported native operation, master, losing records, and returned IDs                   |
| Conversion | Separate Lead conversion; prevent unintended opportunities                             |

For cleaning-only conversion, select no opportunity creation. Verify Account and Contact targets, queue ownership, and Person Account behavior. Identity does not define lifecycle policy.

Preserve master and losing-record aliases. Reconcile returned links with the permitted inventory. Report checks prevented by access limits. Restoring a Contact does not restore the master's previous state.

Use conditional writes only when the operation and connection support them. Do not extend Account ETag behavior to other objects. Keep stale-write errors as conflicts.

Keep candidate domains outside Website and ParentId until their roles are verified. Apply native-ID, field-access, and stale-write checks to warehouse records too.

Keep `MasterRecordId` history separate from duplicate labels, deletion flags, proposed targets, and `ParentId`. Verify historical losing IDs and event times. Check related masters outside the sample before declaring broken links or splitting evaluation families.

Check history fields, access, and retention. An empty history result does not prove no change. Configure approved event capture for the selected objects only. Record cursor and gap-recovery rules.

**Complete when:** each required capability is passed, failed, not run, or unsupported. Test uniqueness races, conversion, aliases, links, result IDs, conditional writes, unknown responses, and event gaps.

Official sources: [describe](https://developer.salesforce.com/docs/platform/api-rest/guide/resources-sobject-describe.html), [upsert](https://developer.salesforce.com/docs/platform/api/guide/sforce-api-calls-upsert.html), [Lead conversion](https://developer.salesforce.com/docs/platform/api/guide/sforce-api-calls-convertlead.html), [merge](https://developer.salesforce.com/docs/platform/api/guide/sforce-api-calls-merge.html), [MergeResult](https://developer.salesforce.com/docs/platform/api/guide/sforce-api-calls-merge-mergeresult.html), [Contact recovery](https://help.salesforce.com/s/articleView?id=000386067&language=en_US&type=1), [conditional requests](https://developer.salesforce.com/docs/platform/api-rest/guide/intro-rest-conditional-requests.html), [history](https://help.salesforce.com/s/articleView?id=tracking_field_history.htm&language=en_US), [CDC recovery](https://developer.salesforce.com/docs/platform/change-data-capture/guide/cdc-replication-steps.html), [event durability](https://developer.salesforce.com/docs/platform/pub-sub-api/guide/event-message-durability.html), [limits](https://developer.salesforce.com/docs/platform/api-rest/guide/resources-limits.html).
