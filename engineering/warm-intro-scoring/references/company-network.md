# Company → investors → portfolio expansion

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
