Use Apollo as the default high-recall people/company prospector.

People search split:

- `apollo_search_people` maps to Apollo `mixed_people/api_search` (preview, no Apollo credits, obfuscated names/contact gaps).
- `apollo_people_search_paid` maps to Apollo `mixed_people/search` (paid, billed per request in Deepline).
- Use `apollo_search_people` first for cheap discovery and shortlist building; switch to `apollo_people_search_paid` when you need paid Apollo search coverage/filters.

- Keep `include_similar_titles=true` unless the user explicitly asks for strict title matching.
- For broad discovery, start with `person_seniorities` + `q_keywords` and only tighten after you inspect totals.
- Prefer keyword-style constraints in `q_keywords` and `q_organization_name` over overly narrow exact strings.
- Use `apollo_company_search` to resolve account identity first; when running company-targeted `apollo_people_search`, pass `q_organization_domains_list` or `organization_ids` (avoid name-only keyword targeting).
- Use low `per_page` for pilot checks, then scale once payload shape and match quality are confirmed.
- For changed-company email recovery specifically, do not force Apollo first; prefer the scenario default order from the GTM meta skill.

Response-shape contract (critical):

- Apollo's native people-search payload shape is top-level: `{ total_entries, people, pagination }`.
- Deepline wraps provider payloads in a standard result envelope: `{ data, meta }`.
- Therefore:
  - In `deepline tools execute ... --json`, read people at `result.data.people`.
  - In `deepline enrich` row expressions, read people at `<column>.data.people`.
  - Do not assume `data.people` exists inside Apollo's native payload itself.

Company search shape gotcha (critical):

- Apollo company search is canonical at `organizations` (not `accounts`).
- In Deepline output, prefer `result.data.organizations` (or `<column>.data.organizations` in enrich columns).
- Compatibility fallback: if `organizations` is empty or absent, read `data.accounts`.
- Recommended extractor pattern:

```javascript
const q = (row["Company"] || "").trim().toLowerCase();
const d = row["apollo_company"]?.data || {};
const orgs =
  d.organizations && d.organizations.length > 0
    ? d.organizations
    : d.accounts || [];
const match =
  orgs.find((x) => (x?.name || "").trim().toLowerCase() === q) ||
  orgs[0] ||
  null;
if (!match) return null;
return {
  company_name: match.name || null,
  company_domain: match.primary_domain || match.domain || null,
  company_linkedin: match.linkedin_url || null,
};
```

Quick shape check command:

```bash
deepline tools execute apollo_company_search --payload '{"q_organization_name":"Langfuse","per_page":3,"page":1}' --json
```

Obfuscated last-name handling (for email pattern workflows):

- Detect redacted/obfuscated last names early (for example: `S****`, `K.`, `-`, `N/A`, `redacted`, masked punctuation-heavy strings).
- Treat `last_name_obfuscated` from `apollo_search_people` as non-authoritative for name-based email finding.
- Do not pass obfuscated last names into `leadmagic_email_finder` or pattern generators.
- Required bridge step: `apollo_search_people` -> `apollo_people_match` (by Apollo `id`) -> use `person.last_name` for name-dependent flows.
- If last name is obfuscated, do not rely on `first.last` / `first.lastInitial` / `firstInitial.lastInitial` patterns as primary candidates.
- Prefer fallback order: direct provider email fields and enrichment lookups first (Apollo/person enrichment/LinkedIn-based enrichment), then emit pattern candidates only when confidence is acceptable.
- Persist deterministic flags for downstream branching, for example `last_name_obfuscated=true` and `name_quality=low|medium|high`.
- Keep recall-first behavior: obfuscation checks should gate pattern generation quality, not force strict matching globally.

```bash
deepline tools get apollo_search_people --json
deepline tools get apollo_people_search_paid --json
```
