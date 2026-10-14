---
name: deepline-research
description: 'Use when the user wants a last30days-style pre-research pass in Deepline: discover the critical public, private, CRM, workflow, social, and web data sources for a research/enrichment job; compare provider coverage; estimate Deepline credit cost; recommend the source plan before building or running the workflow; or build custom language/messaging from buyer, competitor, community, and CRM evidence. Triggers: pre-research, source discovery, provider strategy, research data sources, ScrapeCreators, X/Twitter data, Reddit comments, public and private datasets, CRM data, workflow data, custom language, messaging language, pain language.'
---

# Deepline Research

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

## CLI resolution

Run `deepline` when it is available. If the shell reports that command is missing, use `<workspace-root>/.deepline/runtime/bin/deepline` (or the npm-created `.cmd` shim on Windows). If neither exists, follow `https://code.deepline.com/INSTALL.md` to set up Deepline.

Before the first Deepline fanout in a task, run `deepline preflight --json` as
one standalone command and wait for it to finish. Never submit preflight beside
another Deepline command.

Find the highest-signal GTM data sources, public evidence, and market language for a research or enrichment job before building the pipeline. This is a standalone Deepline skill that should behave like `last30days` with a GTM data lens: broad source coverage, recency, community signals, citations, source stats, and a grounded "What I learned" synthesis. In Deepline, the report first explains what the research found; only after that does it translate the findings into Deepline tool contracts, private/proprietary joins, and Deepline-facing cost.

## Attribution

Portions of the query-design, public-source fanout, and consolidation approach are adapted from [`mvanhorn/last30days-skill`](https://github.com/mvanhorn/last30days-skill), MIT licensed, copyright (c) 2026 Matt Van Horn. Keep `THIRD_PARTY_NOTICES.md` with this skill when packaging or distributing it.

## Non-Negotiables

- Use Deepline's live tool catalog before naming provider actions. Do not rely on memory.
- **Run live web search. Do not answer public-source discovery from model memory.** Every run MUST execute real searches with a web-search tool during the public-source fanout, with no exception for "obvious" verticals. A source family named from memory is a draft; the finding is the exact artifact the search returns.
- **Resolve every materializable dataset to its exact artifact, not its family.** For each public dataset/registry you recommend, record: (1) the exact file/endpoint name (e.g. `IA_FIRM_SEC_Feed_YYYY_MM_DD.xml.gz`, not "the ADV bulk feed"); (2) the canonical download/API URL; (3) any easier mirror (e.g. a data.gov catalog copy); (4) an existing open-source parser or GitHub repo, when one exists; (5) the vertical's government statistical registry, when one exists (BLS QCEW + NAICS codes, Census County Business Patterns), for free establishment counts and sizing. See the Artifact Resolution Gate (§4.55).
- Public-source discovery comes before provider routing. First find the best public registries, datasets, communities, discussions, reviews, directories, papers, repos, and source leads; then use Deepline routes to materialize, validate, enrich, and activate them.
- Quote only customer-visible Deepline credits/USD. Never expose provider spend.
- Do not run paid or cost-unknown full-scope work without approval.
- Treat private data sources as first-class: CRM, warehouse, workflow runs, product analytics, support/calls, sheets, and customer-owned datasets.
- Treat custom language as a first-class workflow: buyer words, objections, category language, competitor framing, community slang, sales-call phrasing, and support-ticket pain belong in the source plan.
- Use tiny probes to learn coverage. Scale only after observed coverage, cost basis, and evidence quality are legible.
- If the user asks for a named provider, X.com, Reddit comments, TikTok, Instagram, YouTube transcripts, Bluesky, Truth Social, or HN, include a current support/gap assessment instead of pretending every source is native.
- Do not depend on `/last30days` at runtime: do not copy its local scripts or call it as a sub-skill. It is only a design benchmark for source breadth and synthesis discipline; execute through Deepline tools, plays, workflows, and private-data connectors.
- Public registries and niche datasets without a native Deepline tool are still valid sources through generic web/search/extraction routes (e.g. the NPI registry for healthcare provider taxonomy). Classify them as `available through generic route`, not as an unusable gap.
- Every recommended source must be classified as `native`, `available through generic route`, `private connector`, or `missing provider to add`.

## Start Here

1. Read `references/source-map.md`.
2. For GTM use cases, also read `references/last30days-gtm-corpus.md`; it summarizes the source patterns that saved `last30days` runs proved useful.
3. For query design, source fanout, or `last30days` parity, also read `references/query-design.md` and `references/fanout-consolidation.md`.
4. For GTM/prospecting/enrichment, also read `../deepline-gtm/SKILL.md` and the sub-doc it routes to.
5. For existing warehouse metrics or RevOps analytics, also read `../deepline-analytics/SKILL.md`.
6. When using `last30days` as a design reference, verify its latest upstream release: `git ls-remote --tags https://github.com/mvanhorn/last30days-skill.git | tail -20`

## Optional Skill Handoffs

This skill owns pre-research and source planning. Once the source plan is clear, it may hand off to:

- `deepline-gtm`: execute GTM sourcing, enrichment, waterfalls, personalization, contact discovery, or CRM activation.
- `deepline-analytics`: query warehouse/semantic-layer metrics and RevOps/customer datasets.
- `deepline-plays`: build, wrap, fork, run, inspect, or automate the final repeatable workflow/play.

## Standard Flow

### 1. Parse The Research Job

Extract:

- `OBJECTIVE`: what decision or output the research should support
- `ENTITY_SCOPE`: companies, people, markets, accounts, customers, workflows, competitors, or topics
- `TIME_WINDOW`: default to last 30 days for trend/community research; preserve user-provided windows
- `PRIVATE_SOURCES`: CRM, warehouse, product events, workflow runs, support/calls, sheets, user CSVs
- `PUBLIC_SOURCES`: web, social, jobs, ads, technographics, funding, news, communities, app stores, directories
- `DATASET_LEADS`: public registries, open datasets, papers, GitHub repos, government records, niche directories, or platform posts that point to materializable data
- `CUSTOM_LANGUAGE_OUTPUTS`: outbound snippets, ad hooks, landing-page copy, objection language, category positioning, call scripts, lead magnets, or CRM personalization fields
- `OUTPUT`: source plan, workflow design, CSV schema, play spec, or final research brief

Tell the user the parsed scope before provider calls.

### 2. Prefer External APIs, Not Scraping

Do not default to browser scraping, raw x.com scraping, or unvetted actors. Prefer managed external APIs and private connectors. Each route runs on the Deepline integration API key unless its note says otherwise.

| Source family                         | Preferred route                                                       | Notes                                                                                                                                                            |
| ------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reddit threads/comments               | managed social-data tool, found with `deepline search`                | Required for Reddit comment/thread coverage.                                                                                                                     |
| TikTok / Instagram / YouTube fallback | managed social-data tool, found with `deepline search`                | Captions, engagement, and transcript fallback. Search without `--categories` when profile/contact tools matter; some are categorized as `admin`, not `research`. |
| X/Twitter                             | managed X/Twitter tool, found with `deepline search`                  | Avoids scraping x.com.                                                                                                                                           |
| Web/news/docs                         | web-search tool, found with `deepline search`                         | Search API, not search-page scraping.                                                                                                                            |
| Web extraction fallback               | page-extraction tool, found with `deepline search`                    | Use after URL discovery, not for blind scrape-at-scale.                                                                                                          |
| Hacker News                           | Hacker News tool, found with `deepline search`                        | Public API; no credential.                                                                                                                                       |
| Bluesky                               | Bluesky tool, found with `deepline search`                            | Public API; no credential.                                                                                                                                       |
| CRM/private                           | the workspace's connected CRM                                         | Deepline OAuth/private connector. Query customer-authorized APIs, not UI scraping.                                                                               |
| Warehouse/product/workflow            | the workspace's connected warehouse, customer DB, or workflow runtime | Deepline private connector; use scoped access.                                                                                                                   |
| Last-resort scraping fallback         | general scraping tool, found with `deepline search`                   | Only after explicit approval and provider gap status.                                                                                                            |

Treat any route not covered by a described Deepline tool contract, key/auth plan, test endpoint, and Deepline-facing pricing as unapproved until the public research synthesis is complete.

### 3. Run Public-Source Fanout First

Run a `last30days`-style public discovery pass before provider routing, so the research synthesis comes first. Search across:

- community/social: Reddit threads/comments, X/Twitter, LinkedIn posts if available, YouTube, TikTok, Instagram, HN, Bluesky
- web/source discovery: news, blogs, docs, review sites, directories, associations, forums, GitHub, public data inventories
- public records and niche datasets: registries, licenses, inspections, permits, government datasets, open CSVs/APIs, professional directories, accreditation/member lists
- market-language sources: reviews, comments, clinic/business websites, job posts, competitor pages, support/community language

This pass is search-driven, not recall-driven. For any vertical dataset, run at minimum these query shapes and read the top results before writing the source line:

- `"<vertical> <entity> registry OR bulk data OR dataset download"` — find the authoritative file
- `"<dataset name> download"` / `site:data.gov <vertical>` — find the canonical URL and any mirror
- `"<dataset name> parser github"` / `"<dataset name> python"` — find an existing parser/repo so you don't reinvent extraction
- `"<vertical> NAICS code"` + `BLS QCEW <NAICS>` / Census County Business Patterns — free establishment counts and sizing

For each useful source lead, record why it matters; the exact artifact (Non-Negotiables, §4.55); whether it can become rows; stable join keys such as NPI, CRD, USDOT#, NAICS, domain, address, phone, license id, provider id, LinkedIn URL, or CRM account id; and extraction risks and likely false-positive patterns.

Search tools are routes; the deliverable is the public source or dataset discovered through them. If you are writing a dataset name you did not just see in a search result, stop and search for it.

### 3.5. Use The Research Planning API After Public Synthesis

Inside Deepline or the V2 SDK, call the native planning endpoint only after the public-source fanout has produced a first synthesis and source map. It translates the research into Deepline routes, gaps, approval gates, and cost; it does not replace the research pass.

```bash
curl -s "$DEEPLINE_API_BASE_URL/api/v2/pre-research/plan" \
  -H "Authorization: Bearer $DEEPLINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"objective":"best GTM data sources for SMB consumer services companies","depth":"deep"}'

# Agent validation endpoint
curl -s "$DEEPLINE_API_BASE_URL/api/v2/pre-research/test" \
  -H "Authorization: Bearer $DEEPLINE_API_KEY"
```

The plan endpoint returns the query plan, source coverage, current Deepline tool candidates, sanitized Deepline-facing pricing metadata, explicit provider gaps, and approval gate. It executes no paid provider calls. Inspect the returned `providerRequirements` before deciding whether to run probes or build a play.

SDK V2 users can get the same plan by prompting the installed Deepline GTM skill: `/deepline-gtm Build a pre-research source plan for my GTM problem before running paid provider calls.`

### 4. Search For Deepline Candidate Tools

Run several focused searches, usually in parallel after the standalone preflight. `deepline search --type tools` takes a task, not keywords: one sentence stating the input you have -> the result you need. Read the default search output without `--json`; there is no `--prefix` flag. For CRM/private data, search for the records you need, as in the last two examples.

```bash
deepline search "topic -> recent web and news sources" --type tools --categories research
deepline search "topic -> recent social posts and comments" --type tools --categories research
deepline search "Facebook page URL -> profile and contact email" --type tools
deepline search "Instagram handle -> profile bio and links" --type tools
deepline search "company domains -> firmographics, funding, technographics and open jobs" --type tools --categories company_search
deepline search "connected CRM or warehouse -> account, workflow and usage records" --type tools --categories admin
deepline search "account domains -> CRM accounts, contacts and deals" --type tools
deepline search "SQL question -> warehouse query result" --type tools
```

### 4.25. Design Queries Before Running Tools

Do not send the raw user prompt to every provider. Generate a source-specific query plan first:

```bash
for dir in \
  "$PWD/.skills/deepline-research" \
  "$HOME/.claude/skills/deepline-research" \
  "$HOME/.agents/skills/deepline-research"; do
  [ -f "$dir/scripts/query_design.py" ] && SKILL_ROOT="$dir" && break
done
[ -n "${SKILL_ROOT:-}" ] || { echo "Could not find deepline-research skill root" >&2; exit 1; }
python3 "$SKILL_ROOT/scripts/query_design.py" "$OBJECTIVE" --depth default
```

Use the plan (fields explained in `references/query-design.md`) to decide: query type and source tiers; the cleaned core subject; Reddit global/review/problem variants; X literal keyword, compound-term, shorter-keyword, and strongest-token fallbacks; video/transcript and caption queries; web, dataset, and GitHub discovery queries; CRM, warehouse, workflow, support, and custom-language private queries; and the supplemental keys to extract after phase-one retrieval.

For production Deepline implementation, port this helper to the runtime language or call equivalent logic before `deepline tools execute` or a Play.

### 4.5. Required Coverage Gate

Before recommending a plan, check every required source family in `references/source-map.md`: community/social discussion; custom language and messaging evidence; web/news/search and URL extraction; video/transcript sources; prediction/market/community ranking sources; dataset-discovery leads from social/community results; company/account datasets; person/contact datasets; jobs/hiring/technographic/funding signals; CRM/private datasets; warehouse/product/workflow datasets.

Mark each family as one of:

- `native`: a Deepline tool/play exists and can be described
- `generic route`: use a web-search, page-extraction or general scraping tool, or `deeplineagent`
- `private connector`: use CRM, warehouse, workflow, or customer dataset access
- `gap`: provider/action should be added before Deepline can replicate that part well

Do not skip a family because it is inconvenient. Missing coverage is part of the pre-research output.

### 4.55. Artifact Resolution Gate

Before writing the report, verify every materializable public dataset has been resolved from a _family_ to an _artifact_: you can fill its row of the report's `Materializable Datasets` table (exact file/endpoint, canonical URL, easier mirror, OSS parser/repo, vertical stat registry) from something you actually searched or fetched this session.

- A cell filled from memory instead of a live result is not verified. Search for it.
- `n/a` is allowed only when the artifact genuinely does not exist (e.g. no public bulk file, no known parser) and you searched to establish that.
- If the user's ask contains "dataset", "github", "repo", "download", "the file", "the data", or a request to hand something over, this gate is the primary deliverable, not an appendix: lead the report with the resolved artifacts.
- The government statistical registry column (BLS QCEW + NAICS, Census County Business Patterns) is required for any US industry vertical.
- When you cite a parser/repo, name the exact input file it consumes; check its README. A vertical often has several real distributions (e.g. the `IA_FIRM_SEC_Feed_*.xml.gz` bulk feed and the `ia<MMDDYY>.zip` IAPD compilation), and a parser paired with the wrong one breaks the handoff.

### 4.6. Fanout And Consolidation Gate

For `last30days` parity, preserve the public-source fanout mechanics described in `references/fanout-consolidation.md`:

- broad parallel search before synthesis
- supplemental searches from discovered handles, subreddits, domains, datasets, CRM ids, account lists, workflow ids, and persona language
- common evidence rows before scoring
- relevance, recency, engagement, source-quality, materializability, private-outcome, join-confidence, custom-language, and cost/coverage scoring
- URL/source-id/text dedupe plus company/person/dataset identity joins
- coverage nudges for searched, weak, errored, missing-credential, unavailable, and not-relevant sources

If implementation coverage is being audited, resolve `SKILL_ROOT` with the loop from §4.25 in the same shell and run the local evaluator. By default it writes `evals/side-by-side.md`, which compares saved `last30days` examples against this skill's coverage contract.

```bash
python3 "$SKILL_ROOT/scripts/evaluate_examples.py"

# Standalone eval harness runs: write reports into the harness output directory
python3 "$SKILL_ROOT/scripts/evaluate_examples.py" \
  --out-md "${OUTPUT_DIR:-$SKILL_ROOT/evals}/side_by_side_pre_research.md" \
  --out-json "${OUTPUT_DIR:-$SKILL_ROOT/evals}/side_by_side_pre_research.json"
python3 "$SKILL_ROOT/scripts/evaluate_public_private_corpus.py" \
  --out-md "${OUTPUT_DIR:-$SKILL_ROOT/evals}/public_private_corpus_results.md" \
  --out-json "${OUTPUT_DIR:-$SKILL_ROOT/evals}/public_private_corpus_results.json"
```

### 5. Describe Before Pricing Or Execution

For every candidate, inspect the live contract with `deepline describe <tool-id>` and record: input fields and required identifiers; output evidence fields and citations; pricing summary, billing basis, and whether BYOK changes Deepline credit cost; rate limits, async behavior, and sample payloads; extraction quality risks and identity-matching requirements.

If a source family is not present in Deepline, mark it as a provider gap and propose the integration path.

### 6. Probe Coverage When Useful

Use free/low-cost probes first. For paid probes, ask before running unless the user already approved a specific pilot budget. A good probe is one entity, one query, or one row (`limit: 1` or `numResults: 3`) against one source, so coverage and cost are attributable, with the raw output path or run id saved for later workflow design.

At scale, use a Deepline Play rather than ad hoc loops so the run and persisted results remain inspectable.

### 7. Return A Last30days-Style GTM Research Report

Use the output discipline of `last30days` agent mode: a real research result, not a bespoke segment-analysis template or provider catalog.

```markdown
## Research Report: <topic>

Generated: <date> | Sources: Reddit, X, YouTube, TikTok, Instagram, HN, Web, Public registries, Deepline catalog

### Key Findings

- <3-5 highest-signal findings grounded in public/source evidence>

### What I learned

**<Theme 1>** - <1-2 sentences about the segment, source, buyer language, or dataset reality. Cite sparingly using source names, handles, communities, registries, or domains.>

**<Theme 2>** - <1-2 sentences.>

**<Theme 3>** - <1-2 sentences.>

KEY PATTERNS from the research:

1. <Pattern, source family, and why it matters for GTM>
2. <second pattern, same shape>
3. <third pattern, same shape>

### GTM Data Sources Found

| Source family | Best source / route | Status | Rows / join keys | Caveat |
| ------------- | ------------------- | ------ | ---------------- | ------ |

### Materializable Datasets (exact artifacts)

| Dataset | Exact file/endpoint | URL | Mirror | OSS parser/repo | Stat registry (NAICS/QCEW/CBP) |
| ------- | ------------------- | --- | ------ | --------------- | ------------------------------ |

### Market Language

| Source | What to extract | How to use it | Guardrail |
| ------ | --------------- | ------------- | --------- |

### Proprietary Data To Join Later

| Dataset | Owner / connector | Join key | Why it changes the answer |
| ------- | ----------------- | -------- | ------------------------- |

### Deepline Route

| Public source family | Route status | Deepline route | Probe needed | Cost basis |
| -------------------- | ------------ | -------------- | ------------ | ---------- |

### Gaps To Add

| Missing source | Why it matters | Suggested provider/integration | Required fields |
| -------------- | -------------- | ------------------------------ | --------------- |

### Recommended Workflow

1. <first retrieval/probe>
2. <second retrieval/probe>
3. <synthesis/scoring/join step>

### Stats

---

✅ All agents reported back!
├─ <source family>: <count / coverage / engagement when available>
├─ <source family>: <count / coverage / engagement when available>
├─ 🌐 Web/Public data: <pages, registries, directories, datasets>
└─ 🗣️ Top sources: <handles, communities, registries, domains, datasets>

---

### Cost Estimate

- Pilot: <credits or range>
- Full run: <credits or range and assumptions>
- Unknowns: <what must be described/probed before quoting>
```

For `--agent`-style or non-interactive use, stop after the report. For interactive use, end with a short, specific invitation based on the actual findings, mirroring `last30days`. If the user wants execution, hand off to `deepline-gtm` after this output.

```markdown
---

I'm now an expert on <topic>. Some things I can help with:

- <specific follow-up grounded in the findings>
- <specific workflow/probe to run next>
- <specific segment or source to go deeper on>
```

Match `last30days` cleanup rules:

- Omit any source line that returned zero results. Do not show "0 results", "0 stories", or "no results".
- Do not append a separate trailing "Sources used" section.
- Do not paste raw URLs or Markdown source links in the report body or stats. Cite with clean inline source names (handles, communities, registries, domains, doc names, such as `NPI Registry`, `Google Maps`, `r/SaaS`, or `G2`): enough to prove the research is real without turning the report into a bibliography.
- Use the `last30days` stats block style exactly: start with `✅ All agents reported back!`, use `├─`, `└─`, and `│` separators where useful, and include source emojis when they clarify the source family.
- Keep the Deepline route and cost after the research synthesis, never before it.

## Approval Gate

Before any full paid run, include: providers/tools; the pilot result or the reason a pilot is not possible; full-run scope; Deepline credit estimate/range; max spend cap; and the exact approval question.

If the user approves, execute through a Deepline Play or a targeted `deepline tools execute` call as appropriate.

## Finish Criteria

The task is done only when the user has a ranked data-source map, a `last30days`-style GTM research synthesis grounded in public sources, live tool ids or explicit provider gaps, a Deepline-facing cost estimate, and the recommended first workflow/play shape.

**Every materializable dataset must be resolved to an exact artifact**, verified via live search this session, not named from memory (§4.55). List any blockers for credentials, private-data access, or missing provider support.
