# Company employees, investors and portfolio companies

## Employees as candidate connectors

When the requester supplies a source company, retrieve its current employees and full profiles, then score every employee against every target. Include these employees as candidate connectors alongside the requester's connection export. The source company defaults to the requester's employer when supplied. For example, a WorkOS requester can use WorkOS employees as possible routes to external target accounts. Do not apply this rule to the target company unless the requester asks for that population.

1. Resolve the employer's canonical domain and company ID. Search the supported company-employee provider with that ID. Inspect its current schema; do not guess tool names or parameters.
2. Retrieve all accessible current employees. Follow every page or cursor. Do not filter by title or cap the result at ten. Retain the search receipt, source total, retrieved count, observation date and completion state. If a provider or approved budget limits retrieval, report partial coverage and the remaining work. Never call a partial roster “all employees.”
3. Verify current employment from sourced profiles. Keep former staff, ambiguous identities and unverified employment separate from the accepted roster. Deduplicate against personal connections by canonical profile URL or stable ID; retain both membership sources. Do not duplicate a person to increase their score.
4. Obtain a full profile for every unique current employee through the [batch collection workflow](batch-collection.md). Use `collect.play.ts` cached mode to normalize retained batch receipts; do not run its legacy live mode for each employee. Include all available work history, role dates, education and supported investor or board roles. A roster row or headline is not a full profile. Reuse a complete cached profile within the chosen freshness window; otherwise pull it. Retry failed or partial profiles within the approved scope. Keep unresolved employees in coverage with a reason; never silently drop them. Then merge accepted employee snapshots into `FeatureInput.connectors`. Use `Snapshot.source` for profile provenance and keep the roster membership receipt separately. Reuse cached full histories. Score every accepted employee against every supplied target, including zero-score results, exclude self-pairs and reconcile all rows. Use the existing batch limits and report renderer; do not truncate the candidate universe to fit a report.
5. Report roster total, unique current employees, full/partial/failed profiles, scored employees, self-pairs and resulting path count. Reconcile these counts before claiming completion. The top-three view is a display limit, not a collection, enrichment or scoring limit.
6. Label this group **Company network**. Use **Verified LinkedIn connection** only when an owner-scoped connection export or direct relationship source supports it. A coworker is a candidate route, not an automatically verified first-degree LinkedIn edge. Keep requester relationship points at zero and willingness unknown until supported. Never clear a decline or review hold through roster membership.

This adds one-hop coworker candidates; it does not collect each employee's private connections or infer permission to contact anyone. Use the ordinary work, investor, board and other evidence factors to rank their routes. Employee membership itself adds no points.

## Investors and portfolio companies

When the user supplies their employer (for example WorkOS or Deepline), resolve its canonical domain first. Read issuer funding announcements and the customer's existing sourced investment tables. Record every named investor with the source, observation date and investment date precision. Keep individual angels, firm funds and board seats separate.

For each resolved investor, retrieve every accessible official portfolio page, exhaust pagination and retain per-investor coverage: complete retrieved listing, selected investments, identity unresolved, unavailable, or not expanded. Compare source totals with exported totals. Do not promise an exhaustive cap table or holdings list from selected public disclosures. Unnamed investors remain a gap. Use the existing Deepline research workflow for live provider retrieval; never execute guessed tool schemas.

Save normalized `companies`, `investors`, `edges` and `coverage` arrays/objects privately. Each edge has `company_id`, `investor_id`, `source_url`, `observed_at`; retain investment year/date only when explicitly disclosed. Every company/investor ID must resolve. IDs and domains must be canonical; company-name similarity alone does not establish an investment edge.

```bash
python3 scripts/portfolio.py company-investor-graph.json \
  --company domain:example.com --output company-portfolio.json
```

This offline traversal finds the seed's disclosed investors and all matching portfolio edges in the input graph, excludes the seed and deduplicates repeated receipts. It reports partial coverage by default. It does not retrieve a graph by itself.

Join portfolio companies to current employers using verified domains/canonical IDs, keeping source IDs on both investment edges and the employee/employer claim. A historical investment is not current ownership, a board seat or familiarity with an employee. Board membership needs a named individual, board organization and dated tenure; do not turn a fund investment or an advisor title into a board role. Shared appearances require the same identifiable event/episode and date; generic co-registration does not prove interaction.

Tuning uses `investor_portfolio` as contextual priority. Both personal relationship edges and willingness remain separately reviewed. Raising this weight can change ordering but cannot release a held introduction. Avoid double-counting one source under investor and board features without independent evidence for the latter.
