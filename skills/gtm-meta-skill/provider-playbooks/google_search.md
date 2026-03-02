# Google Integration Agent Guidance

- Prefer `google_search` when you need broad, high-recall web discovery.
- For B2B person lookups, prefer `site:linkedin.com/in "First Last" "Company"` and keep `num` low.
- For company LinkedIn pages, use `site:linkedin.com/company "Company Name"`.
- For email/domain verification context, include both person + domain tokens (for example `"First Last" "company.com"`).
- Keep queries specific and add `siteSearch` when validating a company domain.
- Set `num` to a small value (3-5) for lightweight exploratory runs.
- Use `dateRestrict` for recency-sensitive tasks (for example, `w1` or `m1`).
- Follow this with extraction/enrichment providers when structured fields are required.
