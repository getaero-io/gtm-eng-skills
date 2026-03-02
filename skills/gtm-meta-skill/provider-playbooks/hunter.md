# Hunter Workflow Guidance

- Start with `hunter_discover` and `hunter_email_count` to shape ICP and estimate reachable volume at zero credit cost.
- Prefer `hunter_domain_search` when you need multiple contacts from one account; add `department`/`seniority` filters to keep recall high but usable.
- Use `hunter_email_finder` for one named person after domain-level search is exhausted or too broad.
- Always run `hunter_email_verifier` immediately before outbound send decisions; treat `invalid`, `accept_all`, `webmail`, and `disposable` as non-send states by default.
- Use `hunter_people_find` and `hunter_companies_find` for enrichment context, not as your first discovery step.
- Use `hunter_combined_find` only when person + company enrichment are both needed in one call and you already have a strong identity seed (email/LinkedIn/domain).
