Use `wizleads_find_email`, `wizleads_verify_email`, and `wizleads_get_company_linkedin_id` for synchronous enrichment.

WizLeads allows 10 requests per second across the provider account. Treat that as queue guidance when planning multi-step runs, especially SalesNav scrape + polling workflows.

Use `wizleads_scrape_salesnav` for Sales Navigator scraping. By default Deepline waits briefly for the task to finish and returns task detail if ready. If it returns `status: "running"`, keep the returned `task_id` and poll `wizleads_get_task` until status is terminal. The scrape call opens async billing and reconciliation uses task detail counts, so do not charge polling reads separately.

Use the public Deepline pricing summary returned by tools metadata when explaining cost. Relevant task flags are `inputs.useAccountless` and, for `salesnav-profile` only, `inputs.enrichEmails`. The public UI mentions Company Followers and Group Members, but the current OpenAPI snapshot does not expose those as API operations.

The batch CSV endpoints are registered but disabled until shared multipart upload support exists.
