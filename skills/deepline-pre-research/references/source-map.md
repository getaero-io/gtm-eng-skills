# Source Map

Use this reference to choose source families for `/deepline-pre-research`. Tool ids drift; always confirm with `deepline tools search` and `deepline tools describe`.

## Required Dataset Inventory

To replicate `last30days`-style functionality inside Deepline, every pre-research plan must account for these dataset families. Some are already first-class Deepline providers, some can be reached through generic routes, and some are explicit integration gaps to add.

| Dataset family | Required evidence fields | Deepline route today | Parity status |
| --- | --- | --- | --- |
| Reddit threads | post URL, subreddit, title/body, author when available, score/upvotes, comments count, created date | public-source discovery first; translate to catalog route after synthesis | generic route or gap |
| Reddit comments | comment text, comment URL/permalink, author when available, upvotes, parent post, created date | ScrapeCreators-style provider or vetted `apify` actor | gap unless catalog finds native support |
| X/Twitter posts | post URL/id, handle, text, timestamp, likes, reposts, replies, quote count, optional entity handle search | public-source discovery first; translate to catalog route after synthesis | generic route or gap |
| YouTube search/transcripts | video URL/id, channel, title, publish date, views/likes, transcript excerpts | public-source discovery first; translate to catalog route after synthesis | generic route or gap |
| TikTok | video URL/id, creator, caption/transcript, hashtags, timestamp, views/likes/comments | ScrapeCreators-style provider or `apify` actor | gap or generic route |
| Instagram Reels/posts | URL/id, creator, caption/transcript, timestamp, views/likes/comments | ScrapeCreators-style provider or `apify` actor | gap or generic route |
| Hacker News | story/comment URL, title/text, author, points, comments, created date | Algolia HN native provider recommended; web/search fallback | gap or generic route |
| Polymarket | market URL/id, question, outcomes, odds, movement, volume/liquidity, close date | Gamma API native provider recommended; web/search fallback | gap or generic route |
| Bluesky | post URL/id, handle, text, timestamp, likes/reposts/replies | native BYOK/app-password route recommended | gap unless catalog finds support |
| Truth Social | post URL/id, handle, text, timestamp, likes/reposts/replies | native/BYOK or vetted extraction route recommended | gap unless catalog finds support |
| Web/news/blogs/docs | URL, title, snippet/full text, publish date, source domain, citations | `serper`, `exa`, `parallel`, `firecrawl`, `deeplineagent` | native/generic route |
| Public registries and niche public datasets | registry/API URL, dataset title, row identifiers, entity names, addresses, status/taxonomy/license fields, update date, source agency | generic web/API discovery through `serper`, `exa`, `parallel`, `firecrawl`, `generic_http`, `deeplineagent`; native tool only when catalog finds one | generic route unless catalog finds native support |
| Company/account datasets | domain, name, LinkedIn URL, firmographics, funding, industry, geo, employee count, source URL | `crustdata`, `apollo`, `dropleads`, `openmart`, `aviato`, `peopledatalabs`, `forager` | native |
| People/contact datasets | full name, title, company, LinkedIn URL, email/phone when approved, confidence, source | `apollo`, `dropleads`, `hunter`, `leadmagic`, `bettercontact`, `icypeas`, `rocketreach`, `contactout`, `wiza`, `peopledatalabs` | native |
| Jobs/hiring signals | job title, company, location, posted date, description, URL | `crustdata`, `predictleads`, `bloomberry`, `serper`, `firecrawl` | native |
| Technographics/install base | domain/company, vendor/tool, category, detected date, confidence/source | `builtwith`, `theirstack`, `bloomberry` | native |
| Funding/company events/news | company, event type, date, amount/round when available, source URL | `crustdata`, `aviato`, `predictleads`, `serper`, `exa` | native/generic route |
| CRM data | account/contact/deal ids, owner, stage, lifecycle timestamps, activity fields, custom fields | `salesforce`, `hubspot`, `attio` | private connector |
| Warehouse/semantic metrics | metric name, dimensions, filters, result rows, rendered SQL/audit trail | `snowflake_get_semantic_layer`, `snowflake_run_semantic_query` | private connector |
| Product/workflow usage | org/user/account ids, event/run ids, timestamps, status, outputs, credits/run metadata | `plays`, workflow/session/usage tools, warehouse/customer DB | private connector |
| Support/call/docs data | transcript/note URL/id, speaker/contact, timestamp, summary/snippet, related account | CRM, Attio, Slack/docs connectors, call transcript tools where configured | private connector |
| Sheets/CSVs/customer-owned lists | row ids, domains/emails, source file/sheet id, provenance columns | user CSV, Google Sheets, Deepline Playground | private/customer source |
| Custom language corpus | exact quote/snippet, speaker/source, audience/persona, context, timestamp, engagement or CRM outcome when available | Reddit/X/LinkedIn/YouTube/TikTok/Instagram, sales calls, support tickets, CRM notes, win/loss notes, Gong/Fireflies-like transcripts, docs/sheets | native/generic/private mix |

Minimum useful parity for a last-30-days community research run is: web/news, Reddit threads, Reddit comments, X posts, YouTube transcripts, TikTok or Instagram when relevant, HN, Polymarket when relevant, and at least one private/customer context source when the job is GTM/customer-facing.

For custom language runs, minimum useful parity is: at least one community/social source, at least one long-form context source (YouTube transcript, podcast, blog, call transcript, support thread, or Reddit comments), and one business-context source such as CRM stage/outcome, persona, segment, deal notes, or target account list.

## What To Preserve From last30days

The useful pattern is not the local script itself. Preserve:

- broad source taxonomy: Reddit, X/Twitter, YouTube, TikTok, Instagram, HN, Polymarket, Bluesky, Truth Social, and web
- recency-first retrieval for trends and news
- community evidence with engagement stats
- source coverage stats and explicit missing-source nudges
- comparison mode that researches each side separately plus direct comparison
- synthesis weighted by source quality, engagement, and cross-platform agreement
- two-phase fanout: broad parallel source search, then supplemental searches from discovered handles, subreddits, domains, datasets, and entities
- common evidence rows before scoring, dedupe, clustering, and synthesis

Deepline adaptation:

- route through Deepline tools, plays, workflows, CRM connectors, and warehouse connectors
- quote Deepline credits only
- save outputs in CSVs/runs/playgrounds where agents and users can inspect them
- convert the source plan into a repeatable workflow when the user wants automation
- add private/source-of-truth joins, provider-cost checks, approval gates, and workflow activation paths that `last30days` does not own

## Public Source Families

| Need | Start With | Notes |
| --- | --- | --- |
| General web/news/source discovery | `serper`, `exa`, `parallel`, `deeplineagent`, `firecrawl` | Use search to discover URLs; use extraction for known pages or JS-rendered sources. |
| Public registries / niche datasets | `serper`, `exa`, `parallel`, `firecrawl`, `generic_http`, `deeplineagent` | Treat public registries as materializable sources even without native Deepline tools. Example: NPI registry/provider taxonomy data can be found and pulled through generic web/API search/extraction, then joined by NPI, organization name, address, phone, and taxonomy. |
| Reddit threads/comments | Discover public/community evidence first; search Deepline catalog after synthesis to pick the execution route | If full Reddit comments are core, recommend a native ScrapeCreators-style provider or a vetted Apify actor. |
| X/Twitter posts | Discover public/social evidence first; search catalog after synthesis for X/Twitter/social execution | Browser cookies are not an acceptable backend Deepline integration pattern. Prefer official/BYOK or managed provider integration. |
| YouTube search/transcripts | Discover video/transcript evidence first; search catalog after synthesis for transcript execution | Preserve channel, URL, views, publish date, and transcript excerpts. |
| TikTok/Instagram | Discover short-form/social evidence first; search catalog after synthesis for execution route | Use captions/transcripts plus engagement. For local-business contact workflows, also consider Instagram profile bio links/contact fields as candidate contact-data signals. Search ScrapeCreators unfiltered because profile tools may be categorized as `admin`, not `research`. Avoid unauthenticated brittle scraping at scale. |
| Facebook pages/profiles | Discover public page/profile contact details when local businesses, restaurants, storefronts, or social-first companies may publish email/phone/website there | Candidate route through ScrapeCreators profile tools or generic web extraction. Search ScrapeCreators unfiltered because Facebook profile tools may be categorized as `admin`, not `research`. Preserve profile URL and identity evidence. |
| Hacker News | Search/web fallback may be enough; native Algolia HN would be cheap to add | Capture points, comments, author, URL, and story age. |
| Polymarket | Search/web fallback may be enough; native Gamma API would be cheap to add | Capture odds, movement, market close date, and volume/liquidity when available. |
| Bluesky/Truth Social | Treat as explicit gap unless catalog search finds a current route | Prefer API-backed access over brittle page scraping. |
| Jobs/hiring signals | `crustdata`, `predictleads`, `bloomberry`, `theirstack`, `serper`, `firecrawl` | Jobs are high-intent and often better than marketing pages. |
| Tech stack/install base | `builtwith`, `theirstack`, `bloomberry`, `wappalyzer-like catalog hits` | Confirm whether the tool supports domain lookup, vendor lookup, or customer list search. |
| Funding/company events | `crustdata`, `aviato`, `apollo`, `predictleads`, `serper`, `exa` | Verify event date, source URL, and company domain. |
| Ads/audience signals | `dataforseo`, `google-ads-audiences`, `linkedin-ads-audiences`, `meta-audiences` | Use only when the research question needs market demand or ad targeting. |

## Private And Customer-Owned Sources

Private data often beats public data. Do not build a public-only plan when the user has relevant internal data.

| Dataset | Deepline Route | Good Join Keys | Guardrails |
| --- | --- | --- | --- |
| Salesforce | `salesforce` tools after catalog search/describe | account id, domain, contact email, opportunity id | Do not scan broad objects blindly. Inspect schema/list fields first. |
| HubSpot | `hubspot` tools after catalog search/describe | company id, domain, contact email, deal id | Preserve CRM object ids and lifecycle timestamps. |
| Attio | `attio` tools after catalog search/describe | record id, domain, email, list id | Respect workspace object model; describe objects before querying. |
| Warehouse / semantic layer | `snowflake_get_semantic_layer`, `snowflake_run_semantic_query` | account id, domain, email, user id, date | Use semantic metrics before raw SQL. Read `deepline-analytics`. |
| Customer DB | `customer-db` / `query_customer_db` when available | workspace/org/account ids, domain | Query narrowly; avoid large scans. |
| Workflow/run data | `plays`, workflow/run/session tools if present | play id, run id, org id, output dataset id | Billing belongs in metadata, not row output. |
| Product analytics | analytics/browser or warehouse-backed tools if exposed | user id, org id, account id, event date | Aggregate when possible; do not leak PII unnecessarily. |
| Support/calls/meetings | CRM, Attio, call transcript, Slack, docs connectors where configured | contact email, company domain, meeting id | Quote only relevant snippets and cite source location. |
| Sheets/CSVs | user-provided CSV, Google Sheets connector, Deepline Playground | stable ids, domain, email | Never enrich source files in place; write derived outputs. |

## Custom Language Workflow

Use this when the user needs language that sounds like the market, not generic AI copy.

Source hierarchy:

1. **Buyer/customer words**: sales calls, support tickets, Gong/Fireflies-like transcripts, CRM notes, win/loss notes, onboarding calls, email replies.
2. **Community words**: Reddit comments, X/LinkedIn posts, YouTube transcripts/comments, TikTok/Instagram captions, niche forums, Slack/community exports when provided.
3. **Competitor/category words**: competitor homepages, reviews, docs, pricing pages, G2/Capterra-like reviews when reachable, customer case studies.
4. **Internal desired framing**: product docs, positioning docs, ICP notes, campaign briefs, prior high-performing outbound.

Extract fields:

- exact phrase or quote
- source and timestamp
- persona/segment/account when known
- emotion or pain type
- objection or desired outcome
- product/category term
- proof point or evidence source
- suggested reuse: subject line, opener, ad hook, landing-page section, sales-call talk track, CRM personalization field

Guardrails:

- Keep exact quotes separate from rewritten copy.
- Do not treat high-engagement social language as a factual claim.
- Preserve audience context; do not reuse SMB language for enterprise personas without checking fit.
- For outbound at scale, output structured columns that can be used by `deepline enrich`, not just prose.

## CRM Method

1. Identify the business question before touching CRM data.
2. List candidate CRM objects and fields; inspect schema/describe endpoints first.
3. Choose stable join keys: CRM object ids first, normalized domains/emails second.
4. Pull the smallest useful slice. Prefer recent, scoped records over whole-object exports.
5. Preserve provenance columns: object id, source system, field name, timestamp, and source URL when available.
6. Separate facts from inferences. CRM activity fields often reflect sales effort, not buyer fit.
7. Join private and public sources only after each side has passed a quality gate.

## Provider Gaps Worth Considering

These are likely additions if Deepline wants true `last30days` parity:

- `scrapecreators`: Reddit full comments, TikTok, Instagram, YouTube backup. Useful because one API covers several high-signal community sources.
- Native X/Twitter search: official/BYOK or managed provider route. Do not build around local browser cookies for cloud workflows.
- Native Hacker News Algolia: cheap, no-auth, structured comments/stories.
- Native Polymarket Gamma: cheap/no-auth market discovery with odds and movement.
- Native Bluesky: app-password/BYOK flow for public posts.
- Native community transcript tools for YouTube/TikTok/Instagram if Apify actors are too variable.

For each proposed provider, require:

- test endpoint or tool action for agent validation
- pricing in Deepline credits
- sample payload and sample output fixture
- evidence fields: URL, author/channel, timestamp, engagement, text excerpt
- failure modes and rate-limit behavior

## Cost Method

Use current tool metadata, not provider websites, for Deepline-facing estimates:

```bash
deepline tools describe <tool-id> --json
deepline billing balance
```

Estimate separately:

- discovery cost: queries/searches
- extraction cost: pages/posts/comments/transcripts
- enrichment cost: per row or per successful result
- synthesis cost: `deeplineagent` or model-backed steps
- rerun/freshness cost: what changes when run daily/weekly

If pricing is missing, say "unknown until describe/probe" and do not scale.

## Output Quality Bar

A good pre-research answer is opinionated and operational:

- A good O&P report should surface the actual research learning: official taxonomy over-includes wig shops and generic DME suppliers, Google reviews are a patient-volume proxy but not an absolute estimate, and the useful public source is the registry plus storefront validation, not generic company databases.
- "Use Serper to find source URLs, Firecrawl to extract them, Crustdata for hiring signals, Salesforce for customer context, and Apify/ScrapeCreators gap for Reddit comments."
- "Pilot should cost about X Deepline credits under these assumptions; full run is unknown until we know result count."
- "This source is weak because it lacks comments/transcripts/author timestamps."
- "After the public research pass, this private dataset should be joined because it tells us which accounts actually converted."

A bad answer is a generic list of providers without contracts, costs, join keys, or probe plan.
