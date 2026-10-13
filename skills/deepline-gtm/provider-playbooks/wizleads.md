WizLeads is opt-in and fallback-only. Do not add it to a workflow unless the
user explicitly requests WizLeads or a preceding provider-specific step already
created a WizLeads task.

Preferred alternatives:

- Work-email recovery: use the name + domain work-email play.
- Email verification: use `leadmagic_email_validation`, then
  `zerobounce_validate`.
- LinkedIn company URL lookup: use a company identity resolver. Use
  `wizleads_get_company_linkedin_id` only when a downstream API needs the
  numeric LinkedIn company ID.
- Ordinary people or company discovery: use the dedicated discovery tools.

Use `wizleads_find_email`, `wizleads_verify_email`, and
`wizleads_get_company_linkedin_id` only within those endpoint-specific
boundaries.

WizLeads allows 10 requests per second across the provider account. Treat that as queue guidance when planning multi-step runs.

Use the public Deepline pricing summary returned by tools metadata when explaining cost.

The batch CSV endpoints are registered but disabled until shared multipart upload support exists.
