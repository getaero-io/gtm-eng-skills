# Entity model

Define the account unit before matching. Preserve raw values, source, observation time, effective time, and verification state.

| Object        | Identity                                      | Changing facts                     |
| ------------- | --------------------------------------------- | ---------------------------------- |
| CRM record    | CRM account, object type, native ID           | Fields, links, merge result ID     |
| Person        | Supported individual identity                 | Name, email, employer, title       |
| Employment    | Person, organization, role interval           | Title, status, dates               |
| Legal entity  | Registry, jurisdiction, registration ID       | Name, status, ownership            |
| Brand         | Stable ID with source evidence                | Name, owner, licensee, operator    |
| Business unit | Stable ID within its organization             | Name, scope, reporting line        |
| Location      | Stable ID with site evidence                  | Address, operator, status          |
| Account       | CRM ID for the defined buying or selling unit | Owner, territory, lifecycle        |
| Domain        | Normalized host                               | DNS, website, mail route, operator |
| Transaction   | Stable ID with transaction references         | Parties, scope, stage, dates       |

Use an internal ID when no public ID exists. Do not invent a public ID. Keep aliases dated and unknown dates null.

## Relationships

Record source, target, type, direction, valid interval, evidence, and uncertainty for each relationship. Observation time does not establish effective time.

| Type ID             | Direction and meaning                                                        |
| ------------------- | ---------------------------------------------------------------------------- |
| `legal_parent`      | Controlled entity to controlling legal parent; retain control basis          |
| `accounting_parent` | Consolidated entity to consolidating parent; retain direct or ultimate level |
| `brand_of`          | Brand to owner                                                               |
| `business_unit_of`  | Unit to organization                                                         |
| `equity_interest`   | Interest holder to entity held; retain percentage and voting rights          |
| `licensed_to`       | Brand or asset to licensee                                                   |
| `operated_by`       | Brand, unit, or location to operator                                         |
| `franchise_of`      | Franchise operation to franchisor; no ownership claim                        |
| `located_at`        | Organization or operation to location                                        |
| `commercial_parent` | Account to its policy-defined parent account                                 |
| `account_covers`    | Account to covered entity, unit, brand, or location                          |
| `employed_by`       | Person to employer, qualified by interval                                    |

Use the visible response contract's vocabulary when it differs. Record the mapping. Keep joint control, sole control, equity, consolidation, and operational reporting separate. Derive an ultimate parent only through a complete verified path of one type.

Technical links remain evidence. Common certificates, tags, DNS, or services do not prove ownership.

## Preserve account boundaries

Keep corporate relationships separate from buying units, territory, owner, routing, and rollups. An acquisition need not change sales coverage.

Map only the selected relationship type to a native parent field. Retain unsupported types and dates in supported associations or a neutral graph. Record mapping gaps.

An incomplete search does not justify clearing a parent. Preserve dated employment separately from a current-employer field. Preserve prior reviewed decisions until their policy-defined expiry.

## Decide identity

Use four states: same entity, distinct entities, related entities, and unresolved. Check every member of a proposed group for conflicts.

Different legal IDs, incompatible account units, and proven parent-child relationships can prohibit merging. Shared names, mailboxes, phones, and domains do not prove identity.

Record the supported facts, required CRM representation, and available CRM capability separately. Leave conflicts in review.
