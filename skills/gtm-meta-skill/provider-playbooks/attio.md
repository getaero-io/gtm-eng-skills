# Attio CRM — Agent Guidance

## Quick Reference

| Goal                     | Operation                                                                       | Notes                                                                     |
| ------------------------ | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Upsert person by email   | `attio_assert_record` (object: `people`, matching_attribute: `email_addresses`) | Preferred over `create_record` — no conflict errors.                      |
| Upsert company by domain | `attio_assert_record` (object: `companies`, matching_attribute: `domains`)      | Attio auto-enriches when domain is provided.                              |
| Search by name/keyword   | `attio_search_records`                                                          | Fuzzy, max 25 results. Not real-time.                                     |
| Filter records precisely | `attio_query_records`                                                           | Structured filters, pagination, sorting. Use this for production queries. |
| Add to pipeline          | `attio_create_entry` or `attio_assert_entry`                                    | Use assert for upsert behavior.                                           |
| Query pipeline entries   | `attio_query_entries`                                                           | Supports same filter syntax as record queries.                            |
| Log activity             | `attio_create_note`                                                             | Supports markdown format.                                                 |
| Assign follow-up         | `attio_create_task`                                                             | Link to records, set deadline, assign workspace member.                   |
| Discover schema          | `attio_list_attributes`                                                         | Always check available attributes before writing unfamiliar values.       |
| Verify API key           | `attio_identify`                                                                | Free. Returns workspace info and scopes.                                  |

## Playbooks

### Playbook 1: Enrichment Roundtrip

The most common workflow. Attio auto-enriches records when email (people) or domain (companies) is provided.

```
1. attio_assert_record  -> upsert person/company by email/domain
2. Attio auto-enriches  -> job titles, social profiles, company data
3. attio_create_webhook -> subscribe to record.updated for enrichment-complete signal
4. Webhook fires        -> receiver triggers downstream enrichment or sync
```

### Playbook 2: Pipeline Qualification

```
1. attio_query_records  -> filter by enrichment criteria (employee_count > 50, funding stage)
2. attio_create_entry   -> add qualified records to "Sales Pipeline" list
3. attio_create_task    -> assign follow-up to rep (round-robin)
4. attio_create_note    -> log qualification reasoning
```

### Playbook 3: Meeting Follow-Up

```
1. attio_assert_record  -> upsert contact by email
2. attio_assert_record  -> upsert company by domain
3. attio_create_note    -> meeting summary (markdown format)
4. attio_create_task    -> action items with deadline
5. attio_assert_entry   -> create/update deal in pipeline
```

### Playbook 4: Batch Import

```
1. Loop: attio_assert_record -> upsert each record (respect 25 writes/sec)
2. Loop: attio_create_entry  -> add to pipeline (respect 25 writes/sec)
3. attio_create_webhook      -> subscribe to record.updated for enrichment tracking
```

## Common Mistakes

- **Use `assert_record` (PUT) not `create_record` (POST) for upserts.** POST fails with 409 on unique attribute conflicts. Assert always succeeds — creates if missing, updates if found.
- **Multiselect append behavior on assert:** When the matching attribute is multiselect, new values are appended (existing preserved). Non-matching multiselect attributes are fully replaced. Plan accordingly.
- **`search_records` is fuzzy and eventual.** It caps at 25 results and is not real-time. Use `query_records` with structured filters for precise, paginated queries.
- **No bulk API.** Each record is created or updated individually. Stay within rate limits.
- **Note event gotcha:** `note.updated` only fires for title changes. Use `note-content.updated` to track body edits.
- **Enrichment is automatic.** Attio enriches records when email (people) or domain (companies) is provided. There is no explicit enrichment API call.
- **Always check schema first.** Before writing to an unfamiliar object, call `attio_list_attributes` to discover available attribute slugs and types.

## Rate Limits

| Type             | Limit                 |
| ---------------- | --------------------- |
| Read requests    | 100/sec               |
| Write requests   | 25/sec                |
| Webhook delivery | 25/sec per target URL |

All actions handle `429` responses by respecting the `Retry-After` header. For batch imports, pace writes to stay under the 25/sec write limit.
