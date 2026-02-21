---
name: niche-signal-discovery
description: |
  Discover niche, first-party signals for target accounts using AI-powered research.
  Use when you need custom buying signals to prioritize outreach: funding, hiring
  acceleration, tech stack changes, org changes, or any other niche trigger.

  Triggers:
  - "find signals for this company"
  - "what's interesting about this prospect"
  - "research buying signals for my account list"
  - "find custom data points about these companies"

  Requires: Deepline CLI — https://code.deepline.com
---

# Niche Signal Discovery

Use this skill to find unique, non-obvious buying signals that differentiate hot prospects from cold ones. These signals go beyond standard firmographic data — they reveal companies in motion.

## What counts as a niche signal

| Signal bucket | What to look for |
|---|---|
| Funding recency | Last round type/date/amount, investor names, use-of-proceeds signals |
| Hiring acceleration | New roles in sales, revenue ops, solutions, partnerships, AI |
| Job-posting drift | Compare job post stack vs company website stack |
| Org change | New leaders, promotions, team expansion, leadership churn |
| Product/pricing shifts | New SKUs, pricing model changes, enterprise plans launched |
| Stack changes | Newly adopted CRM, data, support, analytics, or AI tools |
| Geographic expansion | New regions, offices, markets opened |
| Compliance readiness | SOC2, ISO, HIPAA, FedRAMP, procurement signals |
| Channel/partner motion | Alliances, marketplace entries, reseller partnerships |

## Quickstart: signal discovery for a single company

```bash
deepline tools execute call_ai_claude_code \
  --payload '{
    "model": "sonnet",
    "json_mode": {
      "type": "object",
      "properties": {
        "signals": {"type": "array", "items": {"type": "string"}},
        "top_signal": {"type": "string"},
        "why_now": {"type": "string"},
        "source_urls": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["signals", "top_signal", "why_now", "source_urls"]
    },
    "system": "You are a GTM researcher. Find niche buying signals for outbound prioritization. Always cite URLs.",
    "prompt": "Company: Acme Corp (acmecorp.com)\n\nFind 3-5 niche buying signals from the last 90 days. Focus on: hiring acceleration, tech stack changes, leadership changes, funding, or product launches. Return strict JSON."
  }' --json
```

## Batch signal enrichment for a CSV list

Run on one row first, then scale:

```bash
deepline enrich --input accounts.csv --in-place --rows 0:1 \
  --with 'signals=call_ai_claude_code:{"model":"sonnet","json_mode":{"type":"object","properties":{"top_signal":{"type":"string"},"why_now":{"type":"string"},"signal_type":{"type":"string","enum":["hiring","funding","stack_change","leadership","product","compliance","expansion","other"]},"confidence":{"type":"number"}},"required":["top_signal","why_now","signal_type","confidence"]},"system":"GTM researcher finding niche buying signals for prioritization.","prompt":"Company: {{Company}} ({{Domain}})\n\nWhat is the single strongest buying signal from the past 90 days? Return strict JSON."}'
```

Scale after pilot looks good:

```bash
deepline enrich --input accounts.csv --in-place --rows 1: \
  --with 'signals=call_ai_claude_code:{"model":"sonnet","json_mode":{"type":"object","properties":{"top_signal":{"type":"string"},"why_now":{"type":"string"},"signal_type":{"type":"string","enum":["hiring","funding","stack_change","leadership","product","compliance","expansion","other"]},"confidence":{"type":"number"}},"required":["top_signal","why_now","signal_type","confidence"]},"system":"GTM researcher finding niche buying signals for prioritization.","prompt":"Company: {{Company}} ({{Domain}})\n\nWhat is the single strongest buying signal from the past 90 days? Return strict JSON."}'
```

## Research-first pattern (higher quality, more expensive)

Use Exa to gather research, then pass to AI for signal extraction:

```bash
deepline enrich --input accounts.csv --in-place --rows 0:1 \
  --with 'research=exa_research:{"query":"{{Company}} recent news hiring funding 2025","numResults":5,"useAutoprompt":true}' \
  --with 'signals=call_ai_claude_code:{"model":"sonnet","json_mode":{"type":"object","properties":{"top_signal":{"type":"string"},"why_now":{"type":"string"},"evidence":{"type":"string"}},"required":["top_signal","why_now","evidence"]},"prompt":"Based on this research about {{Company}}:\n{{research.data}}\n\nExtract the single strongest GTM buying signal. Return strict JSON."}'
```

## Output contract

All signal enrichment should produce at minimum:

- `top_signal` — one-sentence description of the signal
- `why_now` — why this makes the company worth reaching out to now
- `signal_type` — category bucket
- `source_urls` — where the signal was found

## Tips

- Always run `--rows 0:1` pilot before full batch
- Use `model: "haiku"` for speed, `model: "sonnet"` for quality
- Include source URLs in your prompts to get cited evidence back
- Cross-reference Exa research with LinkedIn signals for highest confidence
- Use `confidence` score to auto-filter low-confidence rows before outreach

## Get started

Sign up and get your API key at [code.deepline.com](https://code.deepline.com).

```bash
npm install -g @deepline/cli
deepline auth login
```
