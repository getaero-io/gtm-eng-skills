# GTM Eng Skills for Claude Code

> AI agent skills for GTM teams — prospecting, enrichment, signal discovery, and lead generation powered by [Deepline](https://code.deepline.com).

---

## What are GTM Eng Skills?

GTM Eng Skills are markdown-based instructions that give Claude Code specialized knowledge for sales and marketing workflows. Once installed, Claude automatically applies the right skill when you describe a GTM task.

These skills wrap the [Deepline CLI](https://code.deepline.com) — a platform for AI-powered lead enrichment, signal discovery, and outbound list building.

---

## Skills included

| Skill | What it does |
|---|---|
| [`niche-signal-discovery`](skills/niche-signal-discovery/SKILL.md) | Find custom buying signals: funding, hiring, stack changes, org moves |
| [`waterfall-enrichment`](skills/waterfall-enrichment/SKILL.md) | Enrich any CSV field using multiple providers in sequence (email, phone, LinkedIn) |
| [`contact-to-email`](skills/contact-to-email/SKILL.md) | Find and verify email addresses from name+company, LinkedIn URL, or name+domain |
| [`get-leads-at-company`](skills/get-leads-at-company/SKILL.md) | Find GTM contacts at a company, pick best ICP fit, research posts, draft outreach |
| [`build-tam`](skills/build-tam/SKILL.md) | Build your Total Addressable Market from ICP filters using Apollo, PDL, and Crustdata |
| [`linkedin-url-lookup`](skills/linkedin-url-lookup/SKILL.md) | Resolve LinkedIn profile URLs from name+company with nickname handling and Apify verification |

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

This installs all 6 skills and symlinks them into your agent directories.

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

**Signal discovery:**
> "Find buying signals for the companies in my accounts.csv"

**Email enrichment:**
> "My leads.csv has First Name, Last Name, and Company — find their email addresses"

**Lead generation:**
> "Get me the top GTM contact at each company in this list and draft personalized outreach"

**TAM building:**
> "Build a TAM of VP Sales and CROs at 50-500 person SaaS companies in the US"

**Waterfall enrichment:**
> "Enrich my CSV with phone numbers using the waterfall pattern"

---

## Documentation

Full CLI reference and platform docs: [code.deepline.com/docs](https://code.deepline.com/docs)

---

## Contributing

PRs welcome. Each skill lives in `skills/<name>/SKILL.md`. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT
