WizLeads actions are deprecated and omitted from public discovery. Existing stored integrations retain their compatibility path. For new work, discover an available action for the required result with `deepline search`.

WizLeads is opt-in and fallback-only. Do not add it to a workflow unless the
user explicitly requests WizLeads or a preceding provider-specific step already
created a WizLeads task.

Preferred alternatives:

- Work-email recovery: use the name + domain work-email play.
- Email verification: use `leadmagic_email_validation`, then
  `zerobounce_validate`.
- LinkedIn company URL lookup: use a company identity resolver. Confirm whether the downstream API needs a numeric company ID or a profile URL.
- Ordinary people or company discovery: use the dedicated discovery tools.

WizLeads allows 10 requests per second across the provider account. Treat that as queue guidance when planning multi-step runs.

Use the public Deepline pricing summary returned by tools metadata when explaining cost.

The batch CSV endpoints are registered but disabled until shared multipart upload support exists.
