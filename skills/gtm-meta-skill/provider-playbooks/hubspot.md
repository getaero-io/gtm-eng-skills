# HubSpot CRM - Agent Guidance

## Quick Reference

| Goal | Operation | Notes |
| --- | --- | --- |
| Create a company | `hubspot_create_company` | Use `website_url` when you want HubSpot to infer the domain. |
| Create a contact | `hubspot_create_contact` | Prefer `email` for stable identity matching. |
| Create a deal | `hubspot_create_deal` | Use `deal_stage` and `deal_probability` only when you know the pipeline. |
| Create a note | `hubspot_create_note` | `time_stamp` is required. Add associations to place it on a record timeline. |
| Create a task | `hubspot_create_task` | `task_type` should usually be `TODO`. |
| Update a record | `hubspot_update_*` | Always include `id` and only the fields you want to change. |
| Delete a record | `hubspot_delete_*` | Hard delete only when the target should disappear from HubSpot. |
| Browse records | `hubspot_list_*` | Use for paging and record inspection. |
| Fetch one record | `hubspot_get_object` | Best when you already have the record ID. |
| Search records | `hubspot_search_objects` | Best for fuzzy lookups and filters. |

## Practical Notes

- HubSpot normalizes most writes to CRM property names such as `firstname`, `lastname`, `hubspot_owner_id`, and `dealstage`.
- For object-heavy workflows, prefer `search_objects` over broad listing when you need filters or quick lookup by email/domain.
- The `list_objects` and `get_object` helpers work for standard objects and custom objects when you know the object type.
- When using notes or tasks, add associations up front so the activity lands on the right record timeline.
