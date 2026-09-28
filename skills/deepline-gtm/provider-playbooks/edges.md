# LinkedIn Scraper Provider Guidance

Use this provider only for LinkedIn, Sales Navigator, or Recruiter Lite actions whose account-execution policy is controlled by Deepline.

Public actions run through Deepline-managed LinkedIn identities. Do not ask users or agents to provide `identity_ids` or `identity_mode`; public schemas intentionally hide those fields and the runtime forces managed execution.

Actions that cannot be forced to managed execution are internal-only. Treat internal actions as account-sensitive because they may require a caller-owned LinkedIn, Sales Navigator, or Recruiter Lite identity.

Engagement actions such as message, InMail, connect, follow, like, comment, invite, accept, withdraw, and visit can change account-visible LinkedIn state. Keep them out of public discovery unless a separate safety review approves limits and user confirmation.
