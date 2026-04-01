# GTM Engineering Skills for Claude Code

> 10 AI agent skills that turn Claude Code into a GTM engineering workstation — lead enrichment, waterfall email finding, signal discovery, TAM building, and outbound automation. Powered by [Deepline](https://code.deepline.com).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skills-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![Deepline](https://img.shields.io/badge/Deepline-CLI-orange)](https://code.deepline.com)

## Quick Start

### From Claude Code / Codex

Paste this prompt:

```Install the Deepline CLI and skills using https://code.deepline.com/agent-install.txt```

### From the command line

```bash
curl -fsSL "https://code.deepline.com/api/v2/cli/install" | bash
```

Then tell Claude what you need:

```
> "Find work emails for the 200 contacts in my leads.csv using waterfall enrichment"
> "Build a TAM of VP Sales at 50-500 person SaaS companies in the US"
> "Detect job changes in my HubSpot contacts and add movers to a Lemlist campaign"
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

Skills use the [Deepline CLI](https://code.deepline.com) under the hood — one command that orchestrates 28+ data providers (Apollo, Crustdata, PDL, Hunter, LeadMagic, Dropleads, Apify, and more) with cost-aware routing and waterfall fallbacks.

---

## Skills

| Skill | Description | Use Case |
|---|---|---|
| [`waterfall-enrichment`](skills/waterfall-enrichment/SKILL.md) | Run multiple providers in sequence, stop at first valid result | Email, phone, or LinkedIn enrichment at scale |
| [`contact-to-email`](skills/contact-to-email/SKILL.md) | Find and verify work emails from name+company, LinkedIn URL, or domain | Building verified contact lists for outbound |
| [`build-tam`](skills/build-tam/SKILL.md) | Build Total Addressable Market lists from ICP filters | Account sourcing with Apollo, PDL, Crustdata |
| [`get-leads-at-company`](skills/get-leads-at-company/SKILL.md) | Find GTM contacts at a company, pick best ICP fit, draft outreach | Account-based prospecting |
| [`niche-signal-discovery`](skills/niche-signal-discovery/SKILL.md) | Discover buying signals that differentiate won vs lost deals | ICP analysis, account scoring, signal-based prospecting |
| [`job-change-detector`](skills/job-change-detector/SKILL.md) | Detect HubSpot contacts who changed jobs, find new emails, update CRM | Job change campaigns, warm re-engagement |
| [`linkedin-url-lookup`](skills/linkedin-url-lookup/SKILL.md) | Resolve LinkedIn URLs from name+company with identity validation | LinkedIn enrichment with false-positive prevention |
| [`portfolio-prospecting`](skills/portfolio-prospecting/SKILL.md) | Find companies backed by a specific investor or accelerator | VC portfolio prospecting, accelerator outbound |
| [`clay-to-deepline`](skills/clay-to-deepline/SKILL.md) | Convert Clay table configs to local Deepline enrichment scripts | Migrating from Clay to code-based enrichment |
| [`deepline-feedback`](skills/deepline-feedback/SKILL.md) | Send feedback or bugs to the Deepline team with session context | Bug reports, feature requests |

---

## How It Works

```
You: "Find emails for the contacts in accounts.csv"
       │
       ▼
Claude Code reads your CSV, picks `waterfall-enrichment` skill
       │
       ▼
Skill runs: deepline enrich accounts.csv --add-column work_email \
            --provider dropleads hunter leadmagic --waterfall
       │
       ▼
Deepline tries Dropleads first → falls back to Hunter → then LeadMagic
       │
       ▼
You get: accounts_enriched.csv with verified emails + provider metadata
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
npx skills add getaero-io/gtm-eng-skills --skill waterfall-enrichment contact-to-email build-tam
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

### Waterfall Email Enrichment

> "My leads.csv has First Name, Last Name, and Company — find their email addresses"

Claude runs `waterfall-enrichment`, trying Dropleads → Hunter → LeadMagic in sequence. First valid, verified email wins. You pay once.

### Build a TAM

> "Build a TAM of VP Sales and CROs at 50-500 person SaaS companies in the US"

Claude runs `build-tam`, sourcing accounts from Apollo and PDL, deduplicating, and outputting a scored list with contact details.

### Job Change Detection

> "Find contacts in HubSpot who changed jobs in the last 6 months and add them to a Lemlist campaign"

Claude runs `job-change-detector`, cross-referencing CRM contacts against current employment data, finding new work emails, and importing movers into your sequencer.

### Signal-Based Prospecting

> "What signals differentiate our closed-won deals from closed-lost?"

Claude runs `niche-signal-discovery`, analyzing website content, job listings, tech stack, and maturity markers across your won/lost lists to build a scoring model.

### Portfolio Prospecting

> "Find all companies in a16z's latest fund and get me the Head of Growth at each"

Claude runs `portfolio-prospecting`, sourcing portfolio companies, finding decision-makers, and drafting personalized outreach.

### Clay Migration

> "I have this Clay table export — convert it to a Deepline enrichment script"

Claude runs `clay-to-deepline`, analyzing the schema, mapping Clay columns to Deepline providers, and generating a runnable script.

---

## Why Deepline

These skills use the [Deepline CLI](https://code.deepline.com) instead of calling provider APIs directly. Here's why:

| Without Deepline | With Deepline |
|---|---|
| Manage 28+ API keys and auth methods | One CLI, one credential |
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
