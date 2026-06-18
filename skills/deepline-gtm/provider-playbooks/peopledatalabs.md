Use People Data Labs when you need explicit, auditable structured filters.

- Normalize noisy input first with clean helpers before running expensive search/enrich operations.
- Use autocomplete and narrow incrementally to avoid over-constraining initial queries.
- Prefer small pilot `size` runs and inspect returned fields before batch execution.
- For `peopledatalabs_person_search` / `peopledatalabs_company_search` SQL: use `SELECT *` only and DO NOT include a `LIMIT` clause — PDL rejects any SQL with `LIMIT` as HTTP 400. Pass the `size` input parameter (1–100) to control how many records come back.
- In changed-company email recovery, treat PDL as the fallback after LeadMagic and Crust.
- If earlier, cheaper steps already returned a usable email, skip PDL for that row.

```bash
deepline tools execute peopledatalabs_company_clean --payload '{"name":"Open AI Inc"}'
```

```bash
deepline tools execute peopledatalabs_person_search --payload '{"query":{"bool":{"must":[{"term":{"location_country":"united states"}},{"term":{"job_title_role":"marketing"}}]}},"size":5}'
```

```bash
deepline tools execute peopledatalabs_autocomplete --payload '{"field":"title","text":"growth"}'
```
