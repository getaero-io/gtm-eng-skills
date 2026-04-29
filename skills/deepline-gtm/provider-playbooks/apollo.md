Use Apollo as the default high-recall people/company prospector.

Company vs CRM split:

- `apollo_company_search` maps to Apollo Organization Search (`mixed_companies/search`).
- Use `apollo_company_search` when you want Apollo's broad company database, including companies that are not in your team's CRM yet.
- `crm_search_for_accounts` maps to Apollo CRM Account Search (`accounts/search`).
- Use `crm_search_for_accounts` only when you specifically want accounts your team already added to Apollo CRM.
- If the task is "find companies," "resolve a company," or "search non-CRM companies," use `apollo_company_search`.
- If the task is "search my Apollo accounts" or depends on CRM stages/ownership/workflow state, use `crm_search_for_accounts`.

People search split:

- `apollo_search_people` maps to Apollo `mixed_people/api_search` (preview, no Apollo credits, obfuscated names/contact gaps).
- `apollo_people_search_paid` maps to Apollo `mixed_people/search` (paid, billed per request in Deepline).
- `apollo_search_people_with_match` runs free preview search and then paid enrichment for discovered IDs, returning enriched `people` rows directly.
- Use `apollo_search_people` first for cheap discovery and shortlist building; switch to `apollo_people_search_paid` when you need paid Apollo search coverage/filters.
- `q_keywords` is useful for broad text discovery, but it is not the only way to search non-CRM companies or people. If you already know the company, prefer `q_organization_domains_list` or `organization_ids`.

- Keep `include_similar_titles=true` unless the user explicitly asks for strict title matching.
- For broad discovery, start with `person_seniorities` + `q_keywords` and only tighten after you inspect totals.
- Prefer keyword-style constraints in `q_keywords` and `q_organization_name` over overly narrow exact strings.
- Use `apollo_company_search` to resolve account identity first; when running company-targeted `apollo_people_search`, pass `q_organization_domains_list` or `organization_ids` (avoid name-only keyword targeting).
- Use low `per_page` for pilot checks, then scale once payload shape and match quality are confirmed.
- For changed-company email recovery specifically, do not force Apollo first; prefer the scenario default order from the GTM meta skill.

Company-search planning guardrails:

- Start with a pilot query: `per_page=1..3`, plus either `q_organization_name` or exact domains, before broad pagination.
- Treat `organization_num_employees_ranges` as contract-sensitive. Use the exact format shown by `deepline tools get apollo_company_search`, and update stale local examples when the live contract changes.
- For broad discovery, `q_organization_keyword_tags` is often a better first-pass search constraint than structural-only filters.
- Inspect `result.data.organizations` first. If that array is empty, then check `result.data.accounts` as a compatibility fallback.
- Do not trust `pagination.total_entries` alone when planning a large pull. Verify that retrieved rows, returned shape, and deduped output all look sane on a pilot before fanning out.

Response-shape contract (critical):

- Apollo's native people-search payload shape is top-level: `{ total_entries, people, pagination }`.
- Deepline wraps provider payloads in a standard result envelope: `{ data, meta }`.
- Therefore:
  - In `deepline tools execute ... `, read people at `result.data.people`.
  - In `deepline enrich` row expressions, read people at `<column>.result.data.people`.
  - Do not insert an extra wrapper layer when reading Apollo's native top-level `people` list.

Company search shape gotcha (critical):

- Apollo company search is canonical at `organizations` (not `accounts`).
- In Deepline output, prefer `result.data.organizations` (or `<column>.result.data.organizations` in enrich columns).
- Compatibility fallback: if `organizations` is empty or absent, read `result.data.accounts`.
- Recommended extractor pattern:

```javascript
const q = (row["Company"] || "").trim().toLowerCase();
const d = row["apollo_company"]?.result?.data || {};
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
deepline tools execute apollo_company_search --payload '{"q_organization_name":"Langfuse","per_page":3,"page":1}'
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
deepline tools get apollo_search_people
deepline tools get apollo_people_search_paid
```
