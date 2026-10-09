Use People Data Labs when you need explicit, auditable structured filters.

## Reading results

Use the exact declared getters from `tools describe <tool-id> --json` or
`tools get`: company enrichment declares `company_name` and `company_domain`;
contact enrichment declares contact getters; search actions declare list
getters. Do not invent getters for other profile fields.

`toolResponse.rawV2` preserves the complete parsed and scrubbed provider/tool
adapter envelope. The checked-in company enrichment sample is
`{ data: { status: 200, data: { name, website, ... } } }`, so that sample's
company is at `rawV2.data.data`. Other responses or execution surfaces can have
a different wrapper. Inspect the original retained response, then assert the
exact field path and type before bulk execution. Missing an expected profile
field at a guessed path is an extraction error, not proof PDL returned no data.
`view: "data"` does not flatten rawV2; schema and extractor provenance do not
establish its observed nesting.

## Choosing and calling tools

- Normalize noisy input first with clean helpers before running expensive search/enrich operations.
- Use autocomplete and narrow incrementally to avoid over-constraining initial queries.
- Treat Person Search `size` as a spend cap: every returned profile is billed. Start with `size: 1`, inspect `total` and field coverage, then request only the number of profiles the user can use.
- For surgical gap-fill, prefer `size: 3-5`. Do not default to pages of 30, 40, or 100 after earlier providers have already returned candidates; post-response deduplication cannot recover the PDL spend.
- Put must-have fields into the search itself, for example `work_email IS NOT NULL`, `personal_emails IS NOT NULL`, `mobile_phone IS NOT NULL`, or an Elasticsearch `exists` clause. Use the matching `dataset` slice where appropriate.
- For `peopledatalabs_person_search` / `peopledatalabs_company_search` SQL: use `SELECT *` only and DO NOT include a `LIMIT` clause — PDL rejects any SQL with `LIMIT` as HTTP 400. Pass the `size` input parameter (1–100) to control how many records come back.
- `required` and `min_likelihood` are Person Enrichment controls, not Person Search inputs. Use `peopledatalabs_enrich_contact` when you already know the approximate person and need one strict match.
- Enrichment also accepts `data_include`: comma-separated fields include data and a leading `-` excludes data. Suppressing the data payload requires the literal two-character value `""` (a quote pair) — passing a bare empty value is silently ignored and returns the full record. Projection does not lower credits either way; use `required` and `min_likelihood` to control which matches are billable.
- Bulk person and company enrichment preserve these controls. Person bulk details may override shared controls per request. Company bulk controls apply to every domain in the batch.
- De-duplicate and normalize the input list before any bulk enrichment. `peopledatalabs_bulk_people_enrichment` and `peopledatalabs_bulk_organization_enrichment` bill per matched row, and PDL does not collapse repeats: two rows for the same person cost 2 credits, and `stripe.com`, `www.stripe.com`, and `name: stripe` were each billed even though all three resolved to the same PDL company id. Exact-string de-duplication is not enough — strip URL schemes, `www.`, and trailing slashes, and reconcile name-vs-domain rows to one identifier per entity first. Deepline's batch item keys do not collapse these variants for you, and rows are matched to responses by position, so the batch cannot de-duplicate them safely on your behalf.
- For personal-email-only use cases, require `personal_emails` before billing by passing PDL's `required=personal_emails` parameter. The default Person Enrichment API bills per matched person profile, even if no personal email is present.
- PDL documents `x-call-credits-spent` as the per-call charge response header.
  Deepline parses that header into `meta.creditsSpent` and prefers it for billing
  before any fallback estimate.
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
