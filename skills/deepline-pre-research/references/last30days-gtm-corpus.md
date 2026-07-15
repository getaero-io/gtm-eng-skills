# Last30Days GTM Corpus

This summarizes the relevant saved `last30days` runs under `~/Documents/Last30Days` as of this review. Use it as source-selection memory for `/deepline-pre-research`; do not depend on `last30days` at runtime.

## Corpus Shape

Filename classification found:

| Family | Approx. relevant runs | What it means for Deepline |
| --- | ---: | --- |
| Provider strategy / enrichment / waterfall | 144 | Provider comparison, cost, coverage, waterfall design, and data-quality runs are the most common GTM use case. |
| Contact enrichment / identity / LinkedIn / email / phone | 137 | Name/company to LinkedIn/email/phone, same-name disambiguation, small-company misses, and verification are core. |
| GTM content/community/social/custom language | 119 | LinkedIn/X/YouTube/community sources are useful for messaging, hooks, voice, event/community discovery, custom language, objection phrasing, and market language. |
| CRM/workflow/private data | 83 | Salesforce, HubSpot, Snowflake, Marketo, workflow runs, PLG/product usage, and call/email/Slack transcripts must be first-class. |
| Signals/scoring/intent | 72 | Buying triggers, propensity, launch/cross-sell, audience matching, and account prioritization need mixed private + public evidence. |
| Public records / niche datasets | 51 | SMB, restaurant, grocery, nursing-home, construction, legal-entity, permit/license, event-attendee, and owner lookup runs are high-signal. |

The broad lesson: GTM value came less from "what are people saying?" and more from "what public or private dataset did the discussion point us toward?"

## Relevant Run Families

### 1. Provider Strategy And Waterfalls

Representative runs:

- `best-gtm-data-sources-smb-consumer-services-companies-raw-v3.md`
- `b2b-data-enrichment-pricing-quality-benchmark-provider-comparison-apollo-zoominfo-clay-cognism-lusha-peopledatalabs-international-coverage-accuracy-raw.md`
- `clay-ads-primer-metadata-io-best-providers-best-practices-b2b-audience-personal-email-phone-enrichment-meta-google-linkedin-raw.md`
- `clay-waterfall-enrichment-credits-raw-v3.md`
- `gtm-tool-pricing-stack-migration-claude-code-cli-pain-language-raw-v3.md`

Reusable source pattern:

- Start with community evidence from Reddit/X for pain, coverage complaints, and current vendor sentiment.
- Use web/docs only to verify vendor claims and pricing.
- Translate into Deepline provider routing: direct provider, waterfall, or gap.
- Always distinguish "lead source" from "contact enrichment" from "verification"; many bad workflows blur these.

Implication for `/deepline-pre-research`: provider strategy output must include coverage basis, cost basis, expected miss patterns, and fallback order.

### 2. Contact Enrichment And Identity Resolution

Representative runs:

- `linkedin-profile-url-lookup-from-name-api-scraping-resolution-raw-v3.md`
- `linkedin-url-lookup-pipelines-from-name-and-company-providers-validation-false-positives-gtm-engineering-raw-v3.md`
- `finding-people-not-on-linkedin-collections-specialists-admin-roles-lower-level-prospecting-raw-v3.md`
- `finding-contacts-at-small-companies-under-50-employees-when-data-providers-return-zero-results-gtm-engineer-sales-ops-raw-v3.md`
- `email-pattern-guessing-false-positive-wrong-person-verification-identity-confirmation-b2b-cold-outreach-raw-v3.md`
- `best-b2b-mobile-phone-number-data-providers-accuracy-compari-raw.md`

Reusable source pattern:

- LinkedIn search/scrape is often the identity anchor, but not sufficient.
- Small companies and non-US targets frequently miss in large B2B databases; search/web/registry fallback matters.
- Same-name and stale-role failures are common enough to be a first-class gate.
- Email guessing without identity validation creates wrong-person risk.

Implication: pre-research must require identity evidence fields, not just returned contact fields: current company, current title, work-history corroboration, source URL, and validation status.

### 3. Public Records And Niche Datasets

Representative runs:

- `restaurant-owner-phone-number-data-sources-public-records-sos-liquor-license-health-permit-business-license-api-2025-2026-raw-v3.md`
- `public-data-sources-independent-grocery-store-owners-nyc-raw-v3.md`
- `cms-nursing-home-public-data-deficiencies-staffing-star-rati-raw.md`
- `building-permit-and-construction-project-data-providers-raw-v3.md`
- `cannabis-public-data-sources-license-registry-regulatory-filings-raw-v3.md`
- `legal-entity-data-gtm-corporate-hierarchy-parent-subsidiary-api-raw-v3.md`
- `event-attendee-list-conference-prospecting-raw-v3.md`

Reusable source pattern:

- The strongest GTM datasets are often vertical public records: permits, licenses, inspections, deficiencies, business registries, county records, public ownership, and event attendance.
- Social/community results are useful because they reveal that a dataset exists, not because the posts are final evidence.
- Government/open-data datasets need fetch/download/normalize/join steps before enrichment.

Implication: `/deepline-pre-research` should promote "dataset lead discovery" as a source family and ask whether a public registry can be materialized before defaulting to generic company databases.

### 4. Signals, Scoring, And Propensity

Representative runs:

- `buying-signals-sales-prospecting-hard-to-find-rare-unique-intent-data-raw-hard-signals.md`
- `ai-propensity-to-buy-and-external-signals-for-b2b-saas-expansion-raw-pcc.md`
- `default-account-scoring-gtm-workflows-lead-routing-ai-raw.md`
- `how-companies-target-accounts-for-new-product-launches-with-ai-tools-or-historical-scoring-models-raw-launch.md`
- `backtesting-prompts-for-gtm-lead-scoring-and-qualification-apply-scoring-framework-to-last-100-leads-validate-model-against-historical-data-raw-v3.md`

Reusable source pattern:

- Public buying signals are useful when they can be tied to a dated event: hiring, funding, launches, job posts, regulatory changes, intent-like behavior, ads/audience membership, or product usage.
- Private data decides whether the signal is predictive: won/lost accounts, conversion, pipeline, usage, and expansion history.
- Backtesting needs historical CRM/warehouse data, not just a prompt.

Implication: source plans for scoring must include both public signal retrieval and private outcome labels, with join keys and a validation split/backtest plan.

### 5. CRM, Workflow, Warehouse, And Product Usage

Representative runs:

- `ai-agent-workflow-salesforce-separate-database-scoring-inbou-raw.md`
- `data-warehouse-gtm-engineering-plg-product-usage-workflows-raw.md`
- `b2b-sales-signal-workflows-snowflake-listagg-limits-cost-attribution-per-step-llm-cost-caps-crustdata-enrichment-middleware-traps-brief-format-raw-session-retro.md`
- `marketo-cross-sell-campaign-orchestration-using-propensity-scores-and-account-expansion-signals-raw.md`
- `hubspot-button-webhook-enrich-record-external-api-raw-v3.md`
- `ai-automatically-update-todo-prioritization-list-email-slack-call-transcripts-task-ownership-raw-v3.md`

Reusable source pattern:

- CRM should not be only an output destination. It is a private evidence source: lifecycle, owner, stage, activity, field history, source attribution.
- Warehouse/product usage/workflow runs are often the real truth layer for PLG and expansion.
- Call transcripts, Slack/email, and workflow outputs are useful when converted into dated, attributable signals.

Implication: `/deepline-pre-research` should ask for CRM/warehouse/workflow access before finalizing any GTM source plan.

### 6. Custom Language, Messaging, And Community Language

Representative runs:

- `cold-email-outreach-hooks-personalization-what-s-working-2026-raw-v3.md`
- `linkedin-post-hooks-viral-2026-raw-v3.md`
- `founder-led-gtm-linkedin-content-claude-code-ai-gtm-engineering-raw-v3.md`
- `b2b-gtm-lead-magnets-that-convert-2026-lead-magnet-ideas-for-revops-and-growth-engineers-ai-gtm-data-tooling-lead-magnets-coreyhaines-lead-magnet-raw-v3.md`
- `youtube-seo-event-video-clips-thumbnails-b2b-saas-ranking-2026-raw.md`
- `gtm-tool-pricing-stack-migration-claude-code-cli-pain-language-raw-v3.md`
- `warm-outbound-visitor-message-template-vs-ai-personalization-raw-v3.md`
- `post-call-follow-up-email-b2b-saas-what-to-include-raw-v3.md`

Reusable source pattern:

- X/LinkedIn/Reddit/YouTube are strongest for language, objections, proof points, hooks, and examples.
- Sales calls, reply emails, CRM notes, support threads, and win/loss notes are the strongest private-language sources because they preserve the buyer's exact words and outcome context.
- These sources are weaker for durable facts unless corroborated by docs, product pages, official sources, or datasets.
- Engagement counts help rank messaging patterns, but should not become factual proof.

Implication: split "market language" from "verified dataset/source" in the output, and produce structured language assets when requested: pain phrases, objection language, category terms, hooks, subject lines, opener snippets, CTA language, and account/persona-specific personalization fields.

Custom language workflow:

1. Gather exact phrases from public community and private customer sources.
2. Cluster them by persona, pain, objection, desired outcome, and maturity stage.
3. Preserve representative verbatim snippets with source context.
4. Rewrite into target channel formats only after the evidence table exists.
5. Return both evidence columns and generated copy columns so the workflow can be rerun.

## Mining-Safety Example

A Codex session captured the strongest GTM lesson:

- `/last30days` found an open government mining-safety dataset via a Reddit post.
- It found a predictive mine-safety research paper via X.
- It found a government-agency post pointing to roughly 3M violation records.
- The agent built a risk model, scored 6,537 mines, found safety decision makers, validated emails/LinkedIn URLs, and wrote Lemlist campaigns.

This should become the canonical `/deepline-pre-research` mental model:

1. Use social/community/web to discover the dataset and modeling literature.
2. Materialize the dataset.
3. Build the scoring or filtering layer.
4. Enrich account/contact records.
5. Activate into outbound/workflow tools.

The social post is not the deliverable. The operational dataset and workflow are the deliverable.

## Source Families To Prioritize In Deepline

High-priority because repeated GTM logs used them:

- Reddit comments/threads: pain language, niche datasets, practitioner failures.
- X/Twitter: current practitioner tactics, dataset/paper pointers, named operators.
- YouTube/TikTok/Instagram transcripts and captions: phrasing, examples, demos, creator framing, objections, and hooks.
- Web/news/docs/GitHub: official docs, repos, public data inventories, pricing pages, API docs.
- ScrapeCreators-style social data: Reddit comments plus TikTok/Instagram captions are useful enough to justify native support or a strong generic provider route.
- Apify actors: pragmatic route for LinkedIn, social scraping, and odd public web datasets when native providers are missing.
- Public records/government/open-data: vertical-specific GTM alpha.
- CRM/warehouse/product/workflow data: private truth layer for scoring and activation.
- Contact/enrichment/verification stack: Apollo, Dropleads, Hunter, LeadMagic, BetterContact, Icypeas, RocketReach, ContactOut, Wiza, PDL, ZeroBounce-style validation, and LinkedIn scraping.
- Campaign activation: Lemlist, Smartlead, Instantly, HeyReach, Marketo, HubSpot/Salesforce actions where relevant.

## Add To Every GTM Pre-Research Plan

Before choosing providers, answer:

1. What public/community source can reveal hidden datasets or unusual signals?
2. What private dataset proves the signal matters?
3. What registry/API/source can be materialized into rows?
4. What contact/enrichment path reaches the right buyer after scoring?
5. What activation surface receives the result?
6. What cost/coverage probe validates the plan before scale?
7. What exact buyer/community/customer language should be preserved for messaging or personalization?
