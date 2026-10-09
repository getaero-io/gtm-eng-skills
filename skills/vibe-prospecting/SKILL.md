---
name: vibe-prospecting
description: |
  Build B2B prospect and account lists, enrich companies and contacts, and
  research buying signals with the Vibe Prospecting remote MCP (Explorium).
  Use when the user asks to find prospects, build a lead list, enrich
  firmographics or contacts, or run Explorium-backed outbound research
  without the Deepline CLI path.

  Triggers:
  - "build a prospect list with Vibe Prospecting / Explorium"
  - "enrich this CSV via Explorium MCP"
  - "find VP Sales at Series B SaaS companies"

  Requires: Vibe Prospecting remote MCP — https://vibeprospecting.ai
  (OAuth browser sign-in; complementary to Deepline skills in this repo)
---

# Vibe Prospecting (Explorium MCP)

Turn a natural-language ICP brief into a previewable prospect or account list, then enrich and export once the audience looks right.

This skill is **complementary to Deepline** skills in this repository. Prefer Deepline when the user already has the Deepline CLI connected. Prefer this skill when the user wants the Explorium / Vibe Prospecting MCP path (hosted connector, no CLI install).

## Setup

1. Add the Vibe Prospecting remote MCP: `https://vibeprospecting.explorium.ai/mcp` (product: [vibeprospecting.ai](https://vibeprospecting.ai)).
2. Complete browser OAuth when prompted. Do **not** paste API keys into chat.
3. Confirm MCP tools are available in the session before fetching rows.

## Non-negotiables

1. **Sample first.** Always show a small preview (~5–10 rows) and restate audience filters before any full export.
2. **No invented data.** If the connector is missing or a field is empty, say so; never fabricate emails, phones, or firmographics.
3. **Email before phone.** Default contact enrichment to email-oriented fields. Add phone only when the user explicitly needs dialer-ready numbers.
4. **No secrets in the skill body.** Authentication is OAuth via the connector.
5. **Honest gaps.** Call out missing titles, domains, or match counts instead of silently widening filters.

## Workflow

### 1. Intake

Collect or infer:

- List type: people (prospects) vs companies (accounts)
- Titles and seniority (combine both when filtering people)
- Industry, employee band, geography
- Optional tech stack, funding or hiring events, and requested row count (default 25)

### 2. Preview (pilot)

Resolve fuzzy industry or title phrases to the connector's canonical values when discovery tools exist. Fetch a small sample. Show the translated filters and the sample table. Adjust before continuing.

### 3. Export

After approval, materialize the requested count. Restate the locked audience definition so the user can reuse it.

### 4. Enrich (optional)

- **People:** email and profile fields by default; phone only on request.
- **Companies:** firmographics, tech stack, funding, and growth signals as requested.
- Attach a short note on fill rate.

### 5. Handoff

Deliver a table artifact the user can copy into a CRM, sequencer, or sheet. Suggest Deepline skills in this repo when the user needs multi-provider waterfall CLI workflows next.

## Troubleshooting

- **Connector not connected.** Tell the user to add the Vibe Prospecting remote MCP, restart the agent session, and retry. Do not proceed with synthetic leads.
- **Audience too broad or empty.** Tighten title plus seniority, or widen employee band or geography one axis at a time; re-preview after each change.
- **Low email fill.** Report the fill rate; offer a second enrichment pass only for prioritized rows.

## Example outcomes

- "Twenty-five VP-level sales leaders at Series B SaaS firms in the United States, fifty to two hundred employees — preview then CSV."
- "Enrich this account CSV with industry, size, and primary tech stack."
- "Shortlist five decision-makers at each of these ten domains for outbound."
