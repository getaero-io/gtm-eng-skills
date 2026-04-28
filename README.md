# GTM Engineering Skills for Claude Code

> AI agent skills that turn Claude Code into a GTM engineering workstation — lead enrichment, signal discovery, TAM building, and outbound automation. Powered by [Deepline](https://code.deepline.com).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skills-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![Deepline](https://img.shields.io/badge/Deepline-CLI-orange)](https://code.deepline.com)

## Quick Start

### From Claude Code / Codex

Paste this prompt:

```
Install the Deepline CLI and skills using https://code.deepline.com/agent-install.txt
```

### From the command line

```bash
curl -fsSL "https://code.deepline.com/api/v2/cli/install" | bash
```

Then tell Claude what you need:

```
> "Build a TAM of VP Sales at 50-500 person SaaS companies in the US"
> "Find LinkedIn URLs for the contacts in my CSV with identity validation"
> "Find companies in a16z's portfolio and get the Head of Growth at each"
```

Claude automatically picks the right skill and runs it.

---

## What This Repo Does

These skills give Claude Code the ability to run real GTM workflows — not toy demos, but the same enrichment pipelines that GTM engineers build manually with Apollo, Hunter, PDL, and dozens of other providers.

Each skill is a markdown file (`SKILL.md`) that encodes:
- **Which providers to call and in what order** (waterfall sequences)
- **How to validate results** (email verification, identity matching)
- **Cost optimization patterns** (cheapest provider first, approval gates before expensive runs)
- **Output formats** (enriched CSVs, CRM updates, campaign imports)

Skills use the [Deepline CLI](https://code.deepline.com) under the hood — one command that orchestrates 40+ data providers (Apollo, Crustdata, PDL, Hunter, LeadMagic, Dropleads, Apify, and more) with cost-aware routing and waterfall fallbacks.

---

## Skills

| Skill | Description | Use Case |
|---|---|---|
| [`deepline-gtm`](skills/deepline-gtm/SKILL.md) | Meta-skill that routes GTM prospecting, enrichment, qualification, and outbound workflows across 40+ providers | Any CSV-heavy or provider-driven GTM task |
| [`deepline-quickstart`](skills/deepline-quickstart/SKILL.md) | Run a quick Deepline demo recipe to show how Deepline works | First-time setup, walkthroughs |
| [`build-tam`](skills/build-tam/SKILL.md) | Build a Total Addressable Market list by sourcing accounts and contacts from providers like Apollo, Crustdata, and PDL | Account sourcing from ICP filters |
| [`portfolio-prospecting`](skills/portfolio-prospecting/SKILL.md) | Find companies backed by a specific investor or accelerator, then find contacts and build personalized outbound | VC portfolio prospecting, accelerator outbound |
| [`linkedin-url-lookup`](skills/linkedin-url-lookup/SKILL.md) | Resolve LinkedIn profile URLs from name + company with strict identity validation to avoid false positives | LinkedIn enrichment with false-positive prevention |
| [`niche-signal-discovery`](skills/niche-signal-discovery/SKILL.md) | Discover niche first-party signals that differentiate Closed Won vs Closed Lost accounts for ICP analysis | ICP analysis, account scoring, signal-based prospecting |
| [`clay-to-deepline`](skills/clay-to-deepline/SKILL.md) | Convert a Clay table configuration into local Deepline scripts (extraction, action mapping, script generation, parity validation) | Migrating from Clay to code-based enrichment |
| [`workflow-hello-world`](skills/workflow-hello-world/SKILL.md) | Create a cloud Deepline workflow that runs on a recurring cron schedule or via webhook | Workflow scaffolding and trigger validation |
| [`deepline-feedback`](skills/deepline-feedback/SKILL.md) | Send feedback or bug reports to the Deepline team, including session transcript and environment info | Bug reports, feature requests |

> `gtm-meta-skill` is also published as a deprecated stub that redirects to `deepline-gtm`. Use `deepline-gtm` directly.

---

## How It Works

```
You: "Find emails for the contacts in accounts.csv"
       │
       ▼
Claude Code picks the `deepline-gtm` skill and routes to the
right recipe + provider playbook for the task.
       │
       ▼
Skill runs the appropriate `deepline` CLI commands with the
provider waterfall, validation rules, and cost gates encoded
in the skill's instructions.
       │
       ▼
You get: enriched CSV with verified results + provider metadata
```

Every enrichment opens in the Deepline Playground — a spreadsheet UI where you can inspect results, re-run failed cells, and iterate before committing to a full run.

---

## Installation

### Option 1: Skills CLI (recommended)

```bash
npx skills add getaero-io/gtm-eng-skills --all
```

Install specific skills only:

```bash
npx skills add getaero-io/gtm-eng-skills --skill deepline-gtm build-tam linkedin-url-lookup
```

Install globally (available across all projects):

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

## Prerequisites

You need a [Deepline](https://code.deepline.com) account. The Deepline CLI powers all enrichment commands in these skills.

```bash
npm install -g @deepline/cli
deepline auth login
```

Free tier includes 100 credits (~300 enrichments). [Sign up here](https://code.deepline.com).

---

## Usage Examples

### Build a TAM

> "Build a TAM of VP Sales and CROs at 50-500 person SaaS companies in the US"

Claude runs `build-tam`, sourcing accounts from Apollo, Crustdata, and PDL, deduplicating, and outputting a list with contact details.

### LinkedIn URL Lookup with Identity Validation

> "Find LinkedIn URLs for the contacts in my CSV and verify they're the right people"

Claude runs `linkedin-url-lookup`, resolving profile URLs from name + company with strict name validation to avoid false positives.

### Signal-Based Prospecting

> "What signals differentiate our closed-won deals from closed-lost?"

Claude runs `niche-signal-discovery`, analyzing website content, job listings, tech stack, and maturity markers across your won/lost lists to build a scoring model.

### Portfolio Prospecting

> "Find all companies in a16z's latest fund and get me the Head of Growth at each"

Claude runs `portfolio-prospecting`, sourcing portfolio companies, finding decision-makers, and drafting personalized outreach.

### Clay Migration

> "I have this Clay table export — convert it to a Deepline enrichment script"

Claude runs `clay-to-deepline`, analyzing the schema, mapping Clay columns to Deepline providers, and generating a runnable script.

### Cloud Workflow Setup

> "Create a Deepline workflow that runs every Monday and enriches my new HubSpot contacts"

Claude runs `workflow-hello-world` to scaffold the cron-triggered workflow and validate it end to end.

### General GTM Tasks

> "Enrich the leads in this CSV, score them against my ICP, and queue the top 50 in Lemlist"

Claude invokes `deepline-gtm` (the meta-skill), which loads the relevant recipes and provider playbooks for the multi-step workflow.

---

## Why Deepline

These skills use the [Deepline CLI](https://code.deepline.com) instead of calling provider APIs directly. Here's why:

| Without Deepline | With Deepline |
|---|---|
| Manage 40+ API keys and auth methods | One CLI, one credential |
| Build your own waterfall logic | Built-in waterfall with cost-aware routing |
| Pay per-provider subscriptions | Pay per enrichment, provider-agnostic |
| Handle rate limits, retries, normalization | Handled automatically |
| No visibility into provider performance | Tracks hit rates per provider for your ICP |

**Integrated providers:** Apollo, Crustdata, PDL, Hunter, LeadMagic, Dropleads, Apify, Exa, Firecrawl, HubSpot, Attio, Instantly, Lemlist, HeyReach, Smartlead, ZeroBounce, Prospeo, Icypeas, and more.

---

## Compatibility

These skills work with any AI coding agent that supports the `SKILL.md` format:

- **Claude Code** (primary)
- **Cursor**
- **Codex CLI**
- **Gemini CLI**
- **Antigravity**

---

## Documentation

- **Full CLI reference:** [code.deepline.com/docs](https://code.deepline.com/docs)
- **AI-readable docs:** [llms.txt](https://docs.code.deepline.com/docs/llms.txt)
- **Waterfall patterns:** [code.deepline.com/docs/waterfalls](https://code.deepline.com/docs/waterfalls)
- **GTM plays & recipes:** [code.deepline.com/docs/plays](https://code.deepline.com/docs/plays)

---

## Contributing

PRs welcome. Each skill lives in `skills/<name>/SKILL.md`. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT
