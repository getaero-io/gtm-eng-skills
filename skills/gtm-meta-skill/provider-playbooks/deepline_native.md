# Deepline Native Workflow Guidance

- Use `prospector` for initial person discovery; it waits for completion and returns final results with `job_id`.
- For firmographic enrichment, use `enrich_company`; it waits for completion and returns final results with `job_id`.
- For identity enrichment, use `enrich_contact`; it waits for completion and returns final results with `job_id`.
- Use finder endpoints (`*_finder`) when you need explicit follow-up polling by `job_id`.
- Keep `title_filter` compact and specific (for example `vp`, `cofounder`, `sales director`) to control result size.
