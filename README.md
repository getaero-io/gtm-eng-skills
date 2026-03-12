# GTM Eng Skills for Claude Code

> AI agent skills for GTM teams — prospecting, enrichment, signal discovery, and lead generation powered by [Deepline](https://code.deepline.com).

---

## What are GTM Eng Skills?

GTM Eng Skills are markdown-based instructions that give Claude Code specialized knowledge for sales and marketing workflows. Once installed, Claude automatically applies the right skill when you describe a GTM task.

These skills wrap the [Deepline CLI](https://code.deepline.com) — a unified platform that orchestrates 50+ data providers (Apollo, Crustdata, PDL, Hunter, Dropleads, Apify, etc.) through a single interface for AI-powered lead enrichment, signal discovery, and outbound list building.

---

## What is Deepline?

[Deepline](https://code.deepline.com) is a GTM data orchestration platform that provides:

**Unified API Access** — One CLI, one credential, 50+ providers. No juggling multiple API keys or learning different schemas. Deepline handles provider authentication, rate limits, retries, and normalization.

**Credit-Based Pricing** — Pay one flat rate per enrichment (e.g., 0.3 credits for email finding), regardless of which provider returns the result. No surprise bills from individual provider subscriptions.

**Waterfall Orchestration** — Try multiple providers in sequence until you get a result. Example: `Dropleads → Hunter → LeadMagic` for email finding. First valid result wins, you only pay for what works.

**AI-Powered Enrichment** — Use `call_ai` columns to run research tasks per row (funding stage, tech stack, buying signals) with web search access and structured JSON output.

**Interactive Playground** — Every enrichment opens a spreadsheet-like UI where you can inspect results, re-run failed cells, and iterate on your data pipeline visually.

**Provider-Agnostic Patterns** — Skills in this repo encode battle-tested waterfall orders, validation rules, and cost optimization patterns. You get the benefit of hundreds of real enrichment runs without trial-and-error.

### Why These Skills Require Deepline

1. **Provider Abstraction** — Skills use Deepline's unified `deepline tools execute` commands instead of calling 50+ different APIs directly. This keeps skills maintainable and portable.

2. **Cost Efficiency** — Waterfall patterns in these skills (e.g., `contact-to-email`, `linkedin-url-lookup`) automatically fail over to cheaper providers, minimizing cost while maximizing coverage.

3. **Iterative Workflows** — The `deepline enrich` command powers all CSV enrichment. It supports multi-step pipelines, preserves lineage metadata, and auto-opens the Playground for review—critical for real GTM workflows that require iteration.

4. **Credit Safety** — Skills include approval gates before expensive operations (e.g., run pilot on `--rows 0:1`, show preview, wait for user approval before full run).

Without Deepline, you'd need to:
- Manually integrate 50+ provider APIs with different auth methods
- Handle rate limiting, retries, and error handling for each
- Build your own waterfall logic and provider fallback chains
- Pay full price for each provider subscription instead of pay-per-use
- Rebuild the enrichment orchestration and playground UI from scratch

**Get started**: Sign up at [code.deepline.com](https://code.deepline.com) — free tier includes 100 credits (~300 enrichments).

---

## Skills included

| Skill | What it does |
|---|---|
| [`job-change-detector`](skills/job-change-detector/SKILL.md) | Detect HubSpot contacts who changed jobs (last 6 months), find new work emails, update CRM, add to campaigns |
| [`niche-signal-discovery`](skills/niche-signal-discovery/SKILL.md) | Find custom buying signals: funding, hiring, stack changes, org moves |
| [`waterfall-enrichment`](skills/waterfall-enrichment/SKILL.md) | Enrich any CSV field using multiple providers in sequence (email, phone, LinkedIn) |
| [`contact-to-email`](skills/contact-to-email/SKILL.md) | Find and verify email addresses from name+company, LinkedIn URL, or name+domain |
| [`get-leads-at-company`](skills/get-leads-at-company/SKILL.md) | Find GTM contacts at a company, pick best ICP fit, research posts, draft outreach |
| [`build-tam`](skills/build-tam/SKILL.md) | Build your Total Addressable Market from ICP filters using Apollo, PDL, and Crustdata |
| [`linkedin-url-lookup`](skills/linkedin-url-lookup/SKILL.md) | Resolve LinkedIn profile URLs from name+company with nickname handling and Apify verification |
| [`clay-to-deepline`](skills/clay-to-deepline/SKILL.md) | Migrate Clay table configurations to local Deepline enrichment scripts — schema analysis, dependency graph, and script generation |

---

## Prerequisites

You need a Deepline account to use these skills. The Deepline CLI powers all enrichment commands.

1. Sign up at [code.deepline.com](https://code.deepline.com)
2. Install the CLI:

```bash
npm install -g @deepline/cli
deepline auth login
```

---

## Installation

### Option 1: Skills CLI (recommended)

```bash
npx skills add getaero-io/gtm-eng-skills --all
```

This installs all skills and symlinks them into your agent directories.

To install specific skills only:

```bash
npx skills add getaero-io/gtm-eng-skills --skill niche-signal-discovery waterfall-enrichment
```

To install globally (available across all projects):

```bash
npx skills add getaero-io/gtm-eng-skills --all --global
```

### Option 2: Git clone

```bash
git clone https://github.com/getaero-io/gtm-eng-skills.git ~/.claude/skills/gtm-eng-skills
```

### Option 3: Git submodule (for teams)

```bash
cd your-project
git submodule add https://github.com/getaero-io/gtm-eng-skills.git .claude/skills/gtm-eng-skills
```

---

## Usage examples

Once installed, describe your task and Claude applies the right skill automatically:

**Job change detection:**
> "Find GTM contacts in HubSpot who changed jobs in the last 6 months and add them to a Lemlist campaign"

**Signal discovery:**
> "Find buying signals for the companies in my accounts.csv"
[Example Output](https://www.notion.so/aero-ai/Niche-Signals-Sample-Report-310da8d1d8eb81e399b1fc06ec47f72c)

**Email enrichment:**
> "My leads.csv has First Name, Last Name, and Company — find their email addresses"

**Lead generation:**
> "Get me the top GTM contact at each company in this list and draft personalized outreach"

**TAM building:**
> "Build a TAM of VP Sales and CROs at 50-500 person SaaS companies in the US"

**LinkedIn URL lookup:**
> "Find LinkedIn URLs for the contacts in my CSV and verify they're the right people"

**Waterfall enrichment:**
> "Enrich my CSV with phone numbers using the waterfall pattern"

**Clay migration:**
> "I have this Clay table export — convert it to a Deepline enrichment script"

---

## Documentation

Full CLI reference and platform docs: [code.deepline.com/docs](https://code.deepline.com/docs)

---

## Contributing

PRs welcome. Each skill lives in `skills/<name>/SKILL.md`. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT
