# Clay internal API surface

Clay has no public API for table config. Everything below is the **internal v3 API** the web app itself calls, recovered from 82MB of recorded HAR traffic across 5 workspaces and re-verified live. Host is `https://api.clay.com`. Auth is the browser session cookie, so `credentials: 'include'` from an `app.clay.com` tab is all you need - never copy the cookie into a script.

Treat this as observed behavior, not a contract. Clay can change it without notice. Re-run the miner (below) when something breaks.

## The three you almost always want

| Need | Endpoint |
| --- | --- |
| Every action Clay offers, with input/output schemas | `GET /v3/actions?workspaceId={WS}` |
| A workbook's child tables | `GET /v3/workbooks/{WORKBOOK_ID}/tables` |
| A workbook's dependency graph | `GET /v3/{WS}/workbooks/{WORKBOOK_ID}/overview` -> `{nodes, edges}` |

`/v3/actions` is ~25MB and returns `{actions: [...]}` - 1398 entries in the workspace it was captured from. Each carries `key`, `displayName`, `package`, `categories`, `description`, `inputParameterSchema`, `outputParameterSchema`, `auth`. This is the authoritative answer to "what does Clay action `X` actually take", and it is how you map an unfamiliar `actionKey` instead of guessing.

`/overview` returns the workbook's real node/edge graph. Prefer it over hand-deriving a dependency diagram from field configs.

## Tables and records

| Method | Path | Query | Notes |
| --- | --- | --- | --- |
| `GET` | `/v3/tables/{TABLE_ID}` | `includeExtraData`, `extraDataViewId` | Config. Fields are at `.table.fields`, NOT `.fields`. `firstViewId` is at `.table.firstViewId`. |
| `GET` | `/v3/tables/{TABLE_ID}/count` | - | `{tableTotalRecordsCount}`. True size. |
| `GET` | `/v3/tables/{TABLE_ID}/views/{VIEW_ID}/table-schema-v2` | - | `{tableSchema, exampleRecords}`. exampleRecords carry RENDERED formula/action values - richest prompt source. Capped by Clay (~25-55 rows). |
| `GET` | `/v3/tables/{TABLE_ID}/views/{VIEW_ID}/records/ids` | - | `{results: [r_xxx]}`. All ids, no pagination. |
| `POST` | `/v3/tables/{TABLE_ID}/bulk-fetch-records` | - | Body `{recordIds: [...], includeExternalContentFieldIds: []}`. Returns `{results}`. Batch ~50. |
| `GET` | `/v3/tables/{TABLE_ID}/fieldrun` | - | `{fieldIds}` - which fields have run. |
| `GET` | `/v3/workspaces/{WS}/tables/{TABLE_ID}/fields/runstatus` | - | `{statusCountsByField}` - per-field run state. Better than inferring "did this column fire" from cells. |
| `GET` | `/v3/tables/{TABLE_ID}/has-overflow-csvs/` | - | Whether the table spilled to CSV. |

## Workbooks

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/v3/workbooks/{WORKBOOK_ID}/tables` | Array of child tables (`id`, `name`, `type`, `workbookId`). The entry point for a whole-workbook extract. |
| `GET` | `/v3/{WS}/workbooks/{WORKBOOK_ID}` | Workbook metadata. |
| `GET` | `/v3/{WS}/workbooks/{WORKBOOK_ID}/overview` | `{nodes, edges}` dependency graph. |

Note the inconsistency: `/tables` has no workspace segment, the other two do. That is Clay's shape, not a typo.

## Sources

| Method | Path | Query | Notes |
| --- | --- | --- | --- |
| `GET` | `/v3/sources` | `tableId` | Source config for a table. Recovers filter criteria that a table-config extract does NOT include. |
| `GET` | `/v3/sources/{SOURCE_ID}` | - | One source. |
| `GET` | `/v3/sources/{SOURCE_ID}/runs` | `limit` | Run history. |

If a migration needs to know "what population did this table source", `/v3/sources?tableId=` is the only place that answers it.

## Actions and integrations

| Method | Path | Query | Notes |
| --- | --- | --- | --- |
| `GET` | `/v3/actions` | `workspaceId` | Full catalog, ~25MB. |
| `POST` | `/v3/actions/dynamicFields` | - | Resolves fields that depend on a connected account (e.g. HubSpot property lists). |
| `GET` | `/v3/app-accounts/types` | - | Every integration type. |
| `GET` | `/v3/app-accounts/type/{TYPE}` | - | One integration type. |
| `GET` | `/v3/workspaces/{WS}/app-accounts` | - | Connected accounts. |
| `GET` | `/v3/workspaces/{WS}/app-accounts/accounts/type/{TYPE}` | `resourceId`, `resourceType` | Connected accounts of one type. |

## Workspace, account, billing

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/v3/me` | Current user. |
| `GET` | `/v3/my-workspaces` | Workspaces you can reach. |
| `GET` | `/v3/workspaces/{WS}` | Workspace metadata. |
| `GET` | `/v3/workspaces/{WS}/users` | Members. |
| `GET` | `/v3/workspaces/{WS}/permissions` | Your permissions. |
| `GET` | `/v3/workspaces/{WS}/subroutines` | Saved subroutines. |
| `GET` | `/v3/workspaces/{WS}/trigger-definitions-with-schedule` | Scheduled triggers. Use this to spot tables that need a play with a `cron` binding rather than a plain enrich. |
| `GET` | `/v3/workspaces/{WS}/resources/{RESOURCE_ID}` | Resource metadata (`resourceType` query). |
| `GET` | `/v3/billingplans/{ID}` | Plan. |
| `GET` | `/v3/subscriptions/{ID}` | Subscription. |
| `GET` | `/v3/credit-accrual` | Credit accrual. |
| `GET` | `/v3/model-pricing/{WS}/base-costs` | Per-model base costs. |
| `GET` | `/v3/clayback-analytics` | Usage analytics. |

## CRM read and write

`clay-action-mappings.md` covers enrichment actions. CRM actions live here. Clay ships 27 HubSpot actions plus a Salesforce package; these are the keys that show up in real tables. Confirm the Deepline side with `deepline tools describe <tool_id>` before writing a pass.

| Clay action | Deepline tool |
| --- | --- |
| `hubspot-lookup-object`, `hubspot-lookup-contact-v2` | `hubspot_search_objects` |
| `hubspot-create-object`, `hubspot-create-company` | `hubspot_create_object` |
| `hubspot-update-object` | `hubspot_update_object` |
| `hubspot-get-properties` | `hubspot_fetch_properties` |
| `hubspot-find-owner` | `hubspot_list_owners` |
| `hubspot-retrieve-associations` | `hubspot_batch_read_associations` |
| `hubspot-enroll-contact` | Sequencer step, not an enrich column |
| `hubspot-crm-objects-source` | Seed the CSV from HubSpot, then enrich |

`hubspot-lookup-object` inputs are `objectTypeId`, `fields`, `removeBlankValues`, `limit`. A lookup returning a list interpolates by full path: `{{hs_lookup.results[0].id}}`.

### Clay-native table actions

**`lookup-row-in-other-table`** - inputs `tableId`, `fields|targetColumn`, `fields|filterOperator`, `fields|rowValue`. Not a provider call. Export the referenced table to CSV and join in a `run_javascript` pass, or query `customer_db` if the data already lives there.

**`route-row`** ("Send table data", Clay Labs) - inputs `type`, `tableId`, `rowData`, `nestedData`, `listData`, `isUpsertDisabled`. Writes rows into a different table, so it is not replicable as an enrich column. Produce a filtered output CSV per destination, or model the fan-out as a play.

## Map by job, not by provider name

287 distinct `actionKey` values show up across real Clay tables, but they collapse into about ten jobs. Clay names an action per provider (19 different phone finders, 15 work-email finders); Deepline expresses the same job as one waterfall that tries providers in order and stops when it finds a value. So do NOT hunt for a one-to-one tool per Clay action. Identify the job, use the waterfall, and let it handle provider order.

| Clay actions matching | Job | Deepline |
| --- | --- | --- |
| anything matching `phone` or `mobile` - `*-find-phone`, `*-find-mobile`, `*-find-phone-number`, `clearout-validate-phone` (21 keys) | mobile phone | `prebuilt/person-to-phone` |
| `*-find-work-email`, `find-email-v2`, `icypeas-find-email-v2` (15 keys) | work email | `prebuilt/name-and-domain-to-email-waterfall`, or `prebuilt/person-linkedin-to-email` when you have a LinkedIn URL |
| `*-find-personal-email`, `*-personal-email-from-linkedin` (14 keys) | personal email | `prebuilt/personal-email` |
| `validate-email`, `*-verify-email`, `*-validate-email` (14 keys) | email validation | `leadmagic_email_validation` or `zerobounce_validate`. Accept `valid`, `valid_catch_all`, `catch_all`; reject `unknown` |
| `*-find-linkedin-profile`, `contactout-social-url-from-email` (10 keys) | resolve LinkedIn URL | `prebuilt/person-to-linkedin`, or `prebuilt/personal-email-to-linkedin` from an email |
| `enrich-person`, `enrich-person-with-mixrank-v2`, `*-enrich-person` (10 keys) | person enrichment | `leadmagic_profile_search` then `crustdata_person_enrichment` |
| `enrich-company`, `*-enrich-company`, `crunchbase-enrich-*` (22 keys) | company enrichment | `prospeo_enrich_company` or `crustdata_companydb_search` |
| `use-ai`, claygent variants | AI generation | `deeplineagent` with a `jsonSchema` |
| `find-lists-of-*-with-mixrank`, `search-person` | sourcing a new list | `crustdata_companydb_search`, `dropleads_search_people`, or `prebuilt/company-to-contact` |
| `add-lead-to-campaign`, sequencer keys | campaign push | `instantly_add_to_campaign`, `smartlead_api_request` |

Keys ending `-validate-auth` are Clay's connection health checks. They are not data columns - ignore them during migration.

**Read the column's config, not just its name.** A generic key like `enrich-person` or `*-enrich-person` is often wired as a phone or email finder: check `typeSettings.inputsBinding` for a flag such as `requirePhone`, and check what downstream columns actually consume. Map by what the column produces in that table, not by what its key is called. Clay also chains finders with `conditionalRunFormulaText` so each fires only when the previous missed - that is a waterfall, and it becomes ONE Deepline waterfall play, not one pass per provider.

Expect providers with no Deepline equivalent (surfe, zeliq, smarte, lyne, bytemine, clearout all lack one). That is fine and is the reason to map by job: the waterfall covers the outcome with the providers Deepline does have.

Those patterns cover about 85% of real-table action usage. The rest is genuine long tail - funding data (`intellizence-`, `harmonic-`, `dealroom-`, `cb-insights-`), web/traffic (`semrush-`, `similarweb-`, `capterra-scrape`), and one-off scrapers. For those, pull the schema from the catalog (below), then `deepline tools search "<what it does>"`. If nothing fits, `deeplineagent` with a `jsonSchema` is the fallback, and `generic_http_request` covers a provider Deepline does not wrap.

## Mapping an unknown Clay action

When a table uses an `actionKey` that `clay-action-mappings.md` does not cover, do NOT guess. Pull the catalog and read its schema:

```bash
# from an app.clay.com tab, via the bookmarklet console or javascript_tool
fetch('https://api.clay.com/v3/actions?workspaceId=' + WS, {credentials:'include'})
  .then(r => r.json())
  .then(d => d.actions.filter(a => a.key === 'hubspot-lookup-object')
                      .map(a => ({key:a.key, inputs:a.inputParameterSchema})));
```

Then find the Deepline equivalent with `deepline tools search "<what it does>"` and confirm with `deepline tools describe <tool_id>`.

## Re-mining when Clay changes

The endpoint list above came from HAR captures. To regenerate after a Clay update:

1. In Chrome DevTools -> Network, record while you exercise the Clay UI (open a workbook, a table, run a column, open the action picker).
2. Right-click -> "Save all as HAR with content".
3. Run the miner in `scripts/clay-har-miner.py` against the HAR. It normalizes ids into placeholders and emits one row per distinct route with methods, statuses, query params, and payload shapes.

Large responses (`/v3/actions` in particular) are often recorded without bodies because of DevTools size limits. Fetch those live from a logged-in tab instead of expecting them in the HAR.
