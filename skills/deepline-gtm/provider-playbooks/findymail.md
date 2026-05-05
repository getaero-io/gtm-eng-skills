# Findymail

Use Findymail for verified B2B email lookup, email verification, phone lookup, company enrichment, similar-company discovery, technology lookup, and Intellimatch lead-list workflows.

- Prefer `findymail_find_from_name` when you have a person name plus company domain.
- Prefer `findymail_find_from_business_profile` or `findymail_reverse_email_lookup` when the input is a LinkedIn/profile URL or an existing email.
- Use `findymail_search_technologies` before `findymail_lookup_technologies_by_domain` when the caller wants to filter by a technology name.
- Intellimatch is asynchronous: call `findymail_search_leads`, poll `findymail_get_export_status`, then retrieve rows with `findymail_get_results`.
- Mutating list, exclusion-list, and signal-monitor operations require the caller's own Findymail credential so agents do not mutate the shared provider account.
