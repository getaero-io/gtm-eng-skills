# PredictLeads Guidance

Use PredictLeads for company-level signals: hiring, technology detections, news events, financing events, connections, products, GitHub repositories, and similar companies.

Prefer direct company endpoints when you already have a domain. They cost one API credit per request and can return up to 1,000 records on list endpoints. Use discovery endpoints only when you need broad search, because they bill per returned result.

Avoid follow/unfollow workflows for now. PredictLeads followed-company APIs are designed for webhook delivery and recurring monthly billing, not one-shot agent execution.
