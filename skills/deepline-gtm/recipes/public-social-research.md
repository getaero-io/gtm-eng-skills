---
name: public-social-research
description: 'Find public community language, market signals, launch feedback, and technical discussion across X/Twitter, Bluesky, Hacker News, and other public social sources.'
---

# Public Social Research

Use this recipe when the task is to understand what people are saying publicly: market pull, objections, competitor mentions, launch feedback, custom language, technical pain, recent community signals, or public datasets that can seed total addressable market (TAM) building.

This is a recipe backed by the pre-research planner API, not a prebuilt play. The planner is the core research entry point: it designs the query fanout, ranks public TAM dataset families, and recommends the live Deepline tools to inspect or execute. Use raw provider tools only after the planner returns branches; put repeated query fanout into a scratchpad play when the result needs durable reruns, comparison, scoring, or CSV export.

## Route

1. Call the authenticated pre-research planner first:

```http
POST /api/v2/pre-research/plan
Content-Type: application/json

{
  "query": "<research request>",
  "mode": "auto",
  "limitPerBranch": 4
}
```

Use `mode: "tam_public_dataset"` for TAM/list-building work and `mode: "public_social"` for custom-language/social research. The planner returns `queryBranches`, `candidatePublicDatasets`, `socialSourcePlan`, `recommendedExecutionOrder`, `consolidationRules`, and tool execution commands. It does not execute paid provider calls.

2. Search/describe live tools only for planner-recommended branches before calling them. Tool names below are current hints, not stable contracts.
3. When the user is building a TAM, run public dataset discovery before paid account providers. Find source systems that can produce account lists, not just anecdotes.
4. Use multiple disjoint query branches instead of tiny variants of the same keyword.
5. Keep source, query, timestamp/window, and URL/uri/id in the output. Public evidence without provenance is not usable.
6. Summarize into concise human language only after collecting source rows.

Current tool families:

```bash
deepline tools search --categories company_search --search_terms "public registry,directory,marketplace,license,government"
deepline tools search --categories research --search_terms "public datasets,tam,company lists,job postings,technographics"
deepline tools search "x twitter tweet search social" --json
deepline tools search "reddit comments threads scrapecreators" --json
deepline tools search "youtube search transcript scrapecreators" --json
deepline tools search "tiktok instagram reels social scrapecreators" --json
deepline tools search "hacker news algolia developer discussion" --json
deepline tools search "bluesky public post search" --json
deepline tools search "web search recent pages news" --json
deepline tools describe <tool-id> --json
```

## TAM public dataset mode

Use this mode when the user asks for TAM building, account sourcing, market maps, list building, niche company discovery, ICP coverage, or "where can we find all companies like X?"

The pre-research job is to identify public source systems that can turn into account rows. Prioritize sources with repeatable filters, stable URLs, downloadable/searchable records, and fields that can map to company name, domain, geography, category, size signal, and freshness.

High-value public dataset families:

| Dataset family                        | Good for TAM building                                                                            | Query patterns                                                                                        |
| ------------------------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Government registries                 | Licensed businesses, facilities, permits, filings, public contractors, healthcare/entity records | `site:.gov <industry> license database`, `<state> <category> registry`, `<agency> public records API` |
| Procurement and grants                | Vendors selling into government, funded organizations, contract categories, incumbents           | `<category> awarded contracts`, `<agency> vendor list`, `<market> grants recipients`                  |
| Job postings and hiring pages         | Companies hiring for ICP-relevant roles, tech/process adoption, expansion signals                | `"<role>" "<tool/category>" jobs`, `site:greenhouse.io <keyword>`, `site:lever.co <keyword>`          |
| Directories and marketplaces          | Agencies, partners, app vendors, local services, vertical SaaS categories, certification holders | `<category> directory`, `<platform> partners <category>`, `<certification> members`                   |
| Review and listing sites              | Software categories, service providers, local businesses, restaurants, clinics, franchises       | `<category> reviews`, `<vertical> near me`, `<software category> alternatives`                        |
| App stores and extension marketplaces | Shopify apps, Chrome extensions, Atlassian apps, Slack apps, Salesforce apps, ecommerce plugins  | `<platform> app directory <category>`, `<category> extension marketplace`                             |
| Technical ecosystems                  | GitHub/package users, docs mentions, open-source adopters, integration partners                  | `"<package>" "customers"`, `"<api>" integration`, `site:github.com <category>`                        |
| Ads and content libraries             | Active advertisers, message themes, offer categories, creator/sponsor markets                    | `<brand/category> ad library`, `<category> sponsored youtube`, `<category> paid partnership`          |
| Events, associations, and communities | Exhibitors, members, speakers, sponsors, regional clusters, buyer groups                         | `<industry> association members`, `<event> exhibitors`, `<conference> sponsors`                       |
| Public social/search evidence         | Demand language, niche keywords, competitor sets, category names to expand TAM queries           | Reddit/X/HN/Bluesky/web searches from the rest of this recipe                                         |

For each candidate source, score it before recommending it:

- `coverage`: how many account rows it can plausibly produce
- `filterability`: whether the source exposes geography, category, size, role, technology, or date filters
- `freshness`: whether records are recent or update regularly
- `identity_quality`: whether rows include domain, website, address, license id, profile URL, or another stable join key
- `access_path`: Deepline tool, public API, downloadable file, searchable web page, or browser/actor fallback
- `scale_risk`: whether the source can be sampled safely before scale

Do not stop at "use web search." Name the actual public dataset candidates and explain how each can become account rows.

## When to use each source

| Source                              | Use for                                                                                                 | Watch out for                                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| X/Twitter managed search            | Broad current-market chatter, competitor mentions, founder/operator takes, launch reactions             | Paid/BYOK provider; bound query count and window before fanout                                       |
| Reddit via ScrapeCreators           | Threads, comments, objections, buying-language, implementation pain, and subreddit-specific language    | Use comments when thread body alone is too thin; cap query branches because each request is billable |
| YouTube via ScrapeCreators          | Video reviews, demos, creator commentary, comments-adjacent context, and transcript snippets            | Transcript availability varies; use search first, then transcripts only for promising videos         |
| TikTok/Instagram via ScrapeCreators | Short-form consumer reactions, creator language, captions, and social proof around categories or brands | Higher noise; summarize only after dedupe and source quality checks                                  |
| Hacker News Algolia                 | Developer tools, technical objections, launch threads, buying skepticism                                | HN over-indexes technical/developer audiences                                                        |
| Bluesky AppView search              | Public tech/social conversation when the audience is active on Bluesky                                  | Coverage varies by market; use as a complement, not sole source                                      |
| Web search                          | Baseline public pages, docs, changelogs, launch posts, news, and source verification                    | Use to anchor social findings; do not let generic web snippets replace social evidence               |

## Execution pattern

For a small one-off answer, run direct tool calls after `tools describe`:

```bash
deepline tools execute <x-search-tool> --input '{"query":"\"competitor\" since:2026-05-21","queryType":"Latest"}' --json
deepline tools execute <hackernews-tool> --input '{"query":"competitor alternative","sort":"date","hitsPerPage":20}' --json
deepline tools execute <bluesky-tool> --input '{"q":"competitor alternative","sort":"latest","limit":25}' --json
```

For TAM pre-research, first fan out dataset-discovery queries, then execute only the best-suited tools:

1. Call `/api/v2/pre-research/plan` with `mode: "tam_public_dataset"`.
2. Inspect `candidatePublicDatasets` for the highest-coverage public sources.
3. Follow `recommendedExecutionOrder`.
4. Describe only the tools returned in each selected branch before executing.

For any workflow with multiple accounts, personas, competitors, or repeated reruns, create a V2 scratchpad play. Stable ids make the provider calls replay-safe while you change scoring, dedupe, clustering, and summaries. Fill the three tool ids from `tools describe` output before running:

```ts
import { definePlay } from 'deepline';

type Input = {
  topic: string;
  since?: string;
  xTool: string;
  redditTool: string;
  webSearchTool: string;
  hackerNewsTool: string;
  blueskyTool: string;
};

export default definePlay(
  'public-social-research',
  async (ctx, input: Input) => {
    const query = input.since
      ? `"${input.topic}" since:${input.since}`
      : `"${input.topic}"`;

    const x = await ctx.tools.execute({
      id: `x:${input.topic}:${input.since ?? 'all'}`,
      tool: input.xTool,
      input: { query, queryType: 'Latest' },
      description: 'Search recent X/Twitter posts',
    });

    const reddit = await ctx.tools.execute({
      id: `reddit:${input.topic}:${input.since ?? 'all'}`,
      tool: input.redditTool,
      input: {
        query: input.topic,
        sort: 'relevance',
        timeframe: 'month',
        trim: true,
      },
      description: 'Search Reddit threads for community language',
    });

    const hn = await ctx.tools.execute({
      id: `hn:${input.topic}`,
      tool: input.hackerNewsTool,
      input: { query: input.topic, sort: 'date', hitsPerPage: 20 },
      description: 'Search Hacker News stories and comments',
    });

    const bluesky = await ctx.tools.execute({
      id: `bluesky:${input.topic}:${input.since ?? 'all'}`,
      tool: input.blueskyTool,
      input: { q: input.topic, sort: 'latest', limit: 25 },
      description: 'Search public Bluesky posts',
    });

    const web = await ctx.tools.execute({
      id: `web:${input.topic}:${input.since ?? 'all'}`,
      tool: input.webSearchTool,
      input: { query: input.topic },
      description: 'Search web pages for baseline source verification',
    });

    return { topic: input.topic, x, reddit, hn, bluesky, web };
  },
  { billing: { maxCreditsPerRun: 25 } },
);
```

Before scaling a scratchpad, run `deepline plays check <file.play.ts>`, then a watched pilot with one topic. Increase query branches only after inspecting source quality and dedupe.

## Output shape

Keep final rows flat:

- `source`
- `query`
- `published_at`
- `author_or_site`
- `url_or_uri`
- `text_or_title`
- `engagement_hint`
- `signal_type`
- `why_it_matters`

For TAM dataset discovery, include these additional fields:

- `dataset_family`
- `coverage_estimate`
- `filter_fields`
- `identity_fields`
- `access_path`
- `sample_query_or_url`
- `recommended_next_step`

Summaries should answer: what people are saying, where the evidence came from, how strong the pattern is, and what the GTM implication is.

For TAM work, summaries should also answer: which public datasets are most likely to produce the market list, what filters to start with, what sample to run first, and where paid/private providers should be used only after public-source coverage is understood.
