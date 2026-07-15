# Fanout And Consolidation

Use this reference when comparing `/deepline-pre-research` to `last30days` or when designing the actual Deepline workflow.

## Baseline To Preserve

`last30days` gets its usefulness from a two-phase retrieval loop:

1. Broad fanout across public sources in parallel.
2. Supplemental fanout from discovered handles, subreddits, entities, and source-specific leads.
3. Normalization into comparable result fields.
4. Relevance, recency, engagement, and source-quality scoring.
5. Same-source dedupe plus cross-source linking.
6. Source stats, errors, missing-source nudges, and synthesis.

Deepline should preserve that shape. Pre-research itself should prioritize public-source discovery and a `last30days`-style "What I learned" synthesis for the GTM problem. Private and workflow data are identified as join targets and handed to `deepline-gtm`, `deepline-analytics`, or a play after the public map is clear.

## Deepline Fanout Contract

### Stage 0: Parse

Extract objective, entity scope, time window, public sources, private sources, dataset leads, custom-language outputs, and final artifact. Turn unclear scope into explicit assumptions before any provider calls.

### Stage 1: Broad Parallel Fanout

Search in parallel across public sources first:

- social/community: Reddit threads, Reddit comments, X/Twitter, YouTube, TikTok, Instagram, HN, Polymarket, Bluesky, Truth Social
- web/source discovery: web, news, docs, blogs, GitHub, directories, app stores, reviews
- public and niche datasets: public records, registries, licenses, inspections, permits, government datasets, open CSVs/APIs, professional directories, association/member lists, accreditation databases
- GTM public signals: company/account, people/contact, jobs, hiring, technographics, funding, review volume, ads and public activity
- Deepline provider catalog is not part of Stage 1. Search and describe Deepline tools only after the public-source synthesis identifies which source families, private joins, probes, costs, and gaps matter.

Do not treat private datasets as the broad fanout unless the user specifically asks for proprietary-data analysis. For GTM work, identify private/proprietary datasets as Stage 7 join targets after public-source discovery.

### Stage 2: Supplemental Fanout

For every useful result, extract follow-up keys and run targeted searches:

- subreddits, handles, channels, creators, domains, URLs, GitHub repos
- company domains, LinkedIn URLs, account ids, CRM object ids, deal/opportunity ids
- workflow/play/run ids, dataset ids, sheet ids, warehouse dimensions
- public-record registry names, license ids, permit ids, agency names
- healthcare registry examples such as NPI registry/provider taxonomy; these are generic-route public sources when no native catalog tool exists
- persona terms, pain phrases, objections, competitor names, category language

Supplemental searches should be attributable to the lead that produced them so evidence clusters remain explainable.

### Stage 3: Normalize

Every result should fit a common evidence shape:

| Field | Meaning |
| --- | --- |
| `source_family` | social, web, company, person, jobs, technographic, funding, CRM, warehouse, workflow, support, sheet, custom-language |
| `route_status` | native, generic route, private connector, gap |
| `tool_or_provider` | Deepline tool id, provider, connector, or proposed gap |
| `source_id_or_url` | stable id, URL, CRM id, workflow id, or dataset id |
| `title_or_label` | human-readable result label |
| `text_or_excerpt` | quoted evidence or normalized text |
| `author_or_owner` | author, channel, CRM owner, source system, or blank |
| `timestamp` | created/published/observed date when available |
| `engagement_or_outcome` | public engagement or private outcome metric |
| `join_key` | domain, email, LinkedIn URL, account id, contact id, dataset key |
| `cost_basis` | Deepline credit basis or unknown until describe/probe |
| `confidence` | extraction/match confidence |
| `provenance` | query, supplemental lead, run id, file id, or connector object path |

### Stage 4: Score

Preserve `last30days`-style relevance, recency, engagement, and source-quality scoring. Add Deepline-specific score inputs:

- materializability: can this become a repeatable dataset/API/provider call?
- private-outcome value: does it connect to conversion, retention, revenue, support load, or usage?
- activation value: can the result drive a CRM field, enrichment column, campaign step, or play branch?
- join confidence: are stable join keys present?
- cost/coverage value: does the source justify its Deepline credit cost?
- custom-language fit: is the phrase tied to the right persona, segment, stage, and context?

### Stage 5: Dedupe And Cluster

Use at least the `last30days` dedupe discipline:

- canonical URL/source id match
- normalized text similarity
- token or n-gram similarity
- per-source dedupe before cross-source linking

Then add Deepline-specific consolidation:

- company identity joins by domain, CRM account id, LinkedIn company URL, or verified provider id
- person identity joins by email, LinkedIn profile URL, CRM contact id, and company/title
- dataset canonicalization by agency/API/repo URL and stable dataset id
- private/public evidence clusters that keep CRM/workflow ids separate from public citations
- custom-language clusters grouped by phrase, persona, pain, objection, and reuse field

### Stage 6: Coverage Nudge

Before synthesis, emit a coverage table for each required source family:

- `searched and useful`
- `searched and weak`
- `searched and errored`
- `not searched because missing credentials`
- `not available in catalog`
- `not relevant to this job`

Only synthesize after the user can see what is strong, weak, missing, and cost-unknown.

### Stage 7: Segment Synthesis And Handoff

Return a concise GTM research report before the implementation plan:

1. "Research Report" with key findings and a "What I learned" section, following `last30days --agent` style.
2. "Best public sources" - public registries, communities, reviews, directories, datasets, and source leads with route status and join keys.
3. "What to join later" - proprietary CRM, warehouse, workflow, support, customer CSV, product, or outcome datasets that would prove the public signals matter.
4. "Deepline route" - only now map sources to Deepline tools, costs, probes, and gaps.

For example, in healthcare provider analysis, "NPI registry has no native Deepline tool" is not the conclusion. The conclusion is: "NPI taxonomy is a high-recall seed but over-includes non-ICP storefronts; pull it via generic web/API route, then validate against Maps/website identity and join proprietary win/loss or CRM outcomes."

## Better-Than-last30days Criteria

Claim Deepline is better only when the workflow:

- covers the same public/community sources or explicitly marks gaps
- identifies private datasets and customer-owned evidence to join after public discovery
- quotes Deepline-facing cost before scaled execution
- produces joinable rows, not just prose
- preserves citations, raw paths, run ids, and connector object ids
- outputs a workflow/play shape that can be rerun
- separates exact market language from rewritten copy
