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
  `wizleads_scrape_salesnav` is only for a supplied Sales Navigator URL.

Use `wizleads_find_email`, `wizleads_verify_email`, and
`wizleads_get_company_linkedin_id` only within those endpoint-specific
boundaries.

WizLeads allows 10 requests per second across the provider account. Treat that as queue guidance when planning multi-step runs, especially SalesNav scrape + polling workflows.

Use `wizleads_scrape_salesnav` for Sales Navigator scraping. By default Deepline waits briefly for the task to finish and returns task detail if ready. If it returns `status: "running"`, keep the returned `task_id` and poll `wizleads_get_task` until status is terminal. The scrape call opens async billing and reconciliation uses task detail counts, so do not charge polling reads separately.

Use the public Deepline pricing summary returned by tools metadata when explaining cost. Relevant task flags are `inputs.useAccountless` and, for `salesnav-profile` only, `inputs.enrichEmails`. The public UI mentions Company Followers and Group Members, but the current OpenAPI snapshot does not expose those as API operations.

The batch CSV endpoints are registered but disabled until shared multipart upload support exists.
