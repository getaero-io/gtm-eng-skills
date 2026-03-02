Use People Data Labs when you need explicit, auditable structured filters.

- Normalize noisy input first with clean helpers before running expensive search/enrich operations.
- Use autocomplete and narrow incrementally to avoid over-constraining initial queries.
- Prefer small pilot `size` runs and inspect returned fields before batch execution.
- In changed-company email recovery, treat PDL as the fallback after LeadMagic and Crust.
- If earlier, cheaper steps already returned a usable email, skip PDL for that row.

```bash
deepline tools execute peopledatalabs_company_clean --payload '{"name":"Open AI Inc"}' --json
```

```bash
deepline tools execute peopledatalabs_person_search --payload '{"query":{"bool":{"must":[{"term":{"location_country":"united states"}},{"term":{"job_title_role":"marketing"}}]}},"size":5}' --json
```

```bash
deepline tools execute peopledatalabs_autocomplete --payload '{"field":"job_title","text":"growth"}' --json
```
