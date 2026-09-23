# External evidence

Use external data to fill specific gaps. Do not add points because a provider returned more fields.

## Select a source

| Need | Source | Use in scoring |
|---|---|---|
| Company identity, industry, funding and investors | Akta company search and enrichment | Company context and investor links |
| Public event pages, board notices and company announcements | Parallel search and extraction | Source-backed facts with names and dates |
| Work and school history | Full profile provider or cached customer records | Same organization and dated overlap |
| Relationship strength and willingness | Customer records or direct confirmation | Personal access and permission |

Akta and Parallel are discovery sources. They do not confirm permission for an introduction.
A company announcement can support an investor link. It cannot establish a personal relationship.

## Run order

1. Verify the customer workspace.
2. Read the live tool catalog and input schema.
3. Select the exact company domain or profile ID.
4. Test the provider on a small sample.
5. Check identity, source links, coverage and actual cost.
6. Use the authorized scope for the remaining work.
7. Save raw responses and run receipts in private storage.
8. Join accepted facts by stable IDs.
9. Recalculate affected paths. Keep review status unchanged.

Use a Deepline play for more than five rows. Inspect a fitting play before creating another one.
Do not guess a provider field or section name. Provider contracts can change.

Catalog starting points, verified on 23 September 2026:

- `akta_company_search`
- `akta_company_enrichment`
- `parallel_extract`

Discover the current Parallel search operation in the catalog before use.
Akta section availability can depend on the connected account.
A missing section is a coverage gap. It is not evidence that the fact does not exist.

Use `assets/company-research.play.ts` as the input-driven Akta collection template.
It stores provider output in the play dataset. It does not change scores.
Recheck its provider sections and validate the play before each deployment.

## Keep an evidence record

Store the provider, request ID, subject ID, source URL, checked date, event date and supported fact.
Keep the raw response location in the private record.
State whether the source is an issuer, investor, registry, profile or secondary report.
Store conflicting claims separately until reviewed.
Do not merge people by name alone.
Do not merge different company domains without a verified identity link.

## Acceptance checks

- Confirm that the returned domain matches the requested company.
- Reject unresolved or conflicting person identities.
- Detect duplicate funding rounds and duplicate investor records before totals or graph joins.
- Keep investment, board membership and personal acquaintance as separate facts.
- Resolve the investor's entity type. A founder's personal investment does not make the founder's employer an investor. Require a source that names the investing firm before giving its employees company-link points. A cached investor label or a verification flag without a supporting source is insufficient.
- Require a named board role and dated tenure for board overlap.
- Require the same named event and people for a shared appearance.
- Keep source dates distinct from retrieval dates.
- Reject future facts relative to the scoring cutoff.
- Add no points for missing, conflicting or unverified facts.
- Do not count the same fact twice because two providers returned it.
- Do not convert a funding announcement into current ownership.

## Report format

Show company research under the target contact. Include the provider, checked date and source link.
Show only accepted score evidence in the path breakdown.
Keep useful company facts visible even when they add no score.
Report provider failures and partial coverage in simple terms.
Use [clear output rules](readable-output.md).

External source references:

- https://akta.pro/company-data
- https://akta.pro/blog/updates-company-data-api-aug-2026
- https://docs.parallel.ai/introduction
