# Kaspr

Use `kaspr_get_linkedin_profile` when you have a LinkedIn profile URL or slug and the person’s full name.

Set `dataToGet` to the smallest set the workflow needs:

- `workEmail` for professional email addresses
- `directEmail` for personal email addresses
- `phone` for phone numbers

Use `requiredData` only when the workflow should reject a partial match. Every value in `requiredData` must also appear in `dataToGet`.

Kaspr does not accept Sales Navigator URLs. Convert them to standard LinkedIn profile URLs first.

Deepline bills Kaspr profile lookups by the contact fields requested in `dataToGet`. Phone and
direct email are the metered pools; work email is unlimited on the plan and carries only a
nominal charge. Request only the fields the workflow needs. Key, rate-limit, and credit reads
are free.
