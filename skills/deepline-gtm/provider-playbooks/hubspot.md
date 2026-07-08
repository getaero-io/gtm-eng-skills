# HubSpot CRM - Agent Guidance

## Quick Reference

| Goal             | Operation                | Notes                                                                        |
| ---------------- | ------------------------ | ---------------------------------------------------------------------------- |
| Create a company | `hubspot_create_company` | Use `website_url` when you want HubSpot to infer the domain.                 |
| Create a contact | `hubspot_create_contact` | Prefer `email` for stable identity matching.                                 |
| Create a deal    | `hubspot_create_deal`    | Use `deal_stage` and `deal_probability` only when you know the pipeline.     |
| Create a ticket  | `hubspot_create_ticket`  | Use `hubspot_list_ticket_pipelines` first when you do not know stage IDs.    |
| Create a note    | `hubspot_create_note`    | `time_stamp` is required. Add associations to place it on a record timeline. |
| Create a task    | `hubspot_create_task`    | `task_type` should usually be `TODO`.                                        |
| Update a record  | `hubspot_update_*`       | Always include `id` and only the fields you want to change.                  |
| Delete a record  | `hubspot_delete_*`       | Hard delete only when the target should disappear from HubSpot.              |
| Browse records   | `hubspot_list_*`         | Use for paging and record inspection.                                        |
| Fetch one record | `hubspot_get_object`     | Best when you already have the record ID.                                    |
| Search records   | `hubspot_search_objects` | Best for fuzzy lookups and filters.                                          |

## Practical Notes

- HubSpot normalizes most writes to CRM property names such as `firstname`, `lastname`, `hubspot_owner_id`, and `dealstage`.
- For object-heavy workflows, prefer `search_objects` over broad listing when you need filters or quick lookup by email/domain.
- The `list_objects` and `get_object` helpers work for standard objects and custom objects when you know the object type.
- When using notes or tasks, add associations up front so the activity lands on the right record timeline.
- For support workflows, prefer the ticket-specific tools over generic object calls: `hubspot_search_tickets`/`hubspot_list_tickets` for dedupe and SLA sweeps, batch ticket tools for backfills and sync repairs, `hubspot_transition_ticket_stage` for status moves, `hubspot_associate_ticket`/`hubspot_remove_ticket_association` for contact/company/GitHub-sync linkage, and `hubspot_add_ticket_note`/`hubspot_pin_ticket_activity` for timeline updates.
