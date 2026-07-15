# Query Design

`/deepline-pre-research` should not send the user's raw prompt to every source. The query-design layer is the core behavior to preserve from `last30days`.

Attribution: the query-cleaning, query-type, source-tiering, and supplemental extraction patterns are adapted from `mvanhorn/last30days-skill` under the MIT License. See `../THIRD_PARTY_NOTICES.md`.

Use `scripts/query_design.py` to generate the query plan:

```bash
python3 .skills/deepline-pre-research/scripts/query_design.py "best GTM data sources for SMB consumer services companies" --depth deep
```

In Deepline runtime, use the native API route only after the public-source fanout has produced a first synthesis and source map. The API translates findings into Deepline routes and costs; it must not replace the research pass:

```bash
curl -s "$DEEPLINE_API_BASE_URL/api/v2/pre-research/plan" \
  -H "Authorization: Bearer $DEEPLINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"objective":"best GTM data sources for SMB consumer services companies","depth":"deep"}'
```

The script emits JSON with:

- `query_type`: product, concept, opinion, how_to, comparison, breaking_news, prediction, gtm_dataset, private_workflow, or custom_language
- `core_subject`: a cleaned version of the prompt with question/meta/noise words removed
- `enabled_sources`: tiered source defaults for the detected query type
- `variants`: source-specific broad and fallback queries
- `supplemental_templates`: phase-two templates for discovered handles, subreddits, domains, accounts, CRM ids, datasets, and language phrases
- `extraction_keys`: what to pull from phase-one results before supplemental fanout
- `scoring_notes`: how to rank results before synthesis

## What Was Ported

Preserve these behaviors:

- Strip common prompt wrappers and research/noise words before platform searches.
- Keep different core subjects by platform. X should be aggressive because keyword search is literal; YouTube/TikTok/Instagram should keep content-type terms like tutorial, review, and tips.
- Detect query type before choosing source defaults.
- Expand Reddit into core, original, review/opinion, and problem/issue variants depending on depth and query type.
- Expand X into the core query with a recency filter, quoted compound-term OR queries, shorter keyword fallback, and strongest-token fallback.
- Run video/social caption searches separately from web searches.
- Treat private/workflow/custom-language queries as first-class query types, not post-processing.
- Extract phase-one handles, hashtags, subreddits, domains, datasets, CRM ids, workflow ids, personas, pain phrases, objections, competitors, and category terms for supplemental fanout.

## Deepline Additions

The Deepline query planner extends `last30days` in four ways:

- `gtm_dataset` query type for provider strategy, public records, account data, contact data, intent data, and enrichment waterfalls.
- `private_workflow` query type for CRM, warehouse, product usage, workflow runs, and RevOps evidence.
- `custom_language` query type for buyer language, objections, competitor/category phrasing, and campaign hooks.
- Provider-catalog and cost-awareness hooks so synthesized research findings can become Deepline source plans with approval gates after the public pass.

## Implementation Contract

Any Deepline runtime implementation should follow this order:

1. Build query plan with `query_design.py` logic or equivalent TypeScript port.
2. Execute public broad variants across the selected source families.
3. Extract supplemental keys from phase-one evidence.
4. Execute targeted supplemental variants.
5. Normalize every result to the evidence schema in `fanout-consolidation.md`.
6. Score, dedupe, cluster, and emit coverage nudges.
7. Synthesize the `last30days`-style GTM research report.
8. Search/describe Deepline tools for the useful source families, private joins, costs, probes, and provider gaps.

Do not collapse this into one generic web search. The source-specific query variants are the quality lever.
