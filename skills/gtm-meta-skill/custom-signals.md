# Custom Signals (`call_ai`) and prompts.json

Use this doc when building enrichment prompts for custom signals, messaging, qualification, or outreach content. Read when the task involves `call_ai*`, `call_ai_claude_code`, or `call_ai_codex`.

## Messaging and enrichment quality

- `call_ai*` (`call_ai`, `call_ai_claude_code`, `call_ai_codex`) — highest-quality custom signals. Messaging. Anything custom. Use to build your OWN signals. These can call parallel, exa, themselves directly.
- `exa_*`/`parallel_*` direct calls are faster and cheaper but usually lower depth than full AI-column orchestration.

## Signal buckets

Use these signal buckets when building enrichment prompts:

- Funding recency: last round type/date/amount, investor names, use-of-proceeds clues.
- Hiring acceleration: new roles in sales, revenue ops, solutions, partnerships, AI.
- Job-posting drift: compare job post stack/signals vs company website stack.
- Org change: new leaders, promotions, team expansion, leadership churn.
- Product or packaging shifts: new SKUs, pricing model changes, enterprise plans.
- Stack changes: newly adopted data/CRM/support/analytics/AI tools.
- Geographic expansion: new regions, markets, offices.
- Compliance/security signals: SOC2, ISO, HIPAA, FedRAMP, procurement readiness.
- Channel/partner motion: alliances, marketplace entries, reseller changes.
- Running ads: use `leadmagic_b2b_ads_search` and `adyntel_facebook_ad_search` together for Meta B2B ad presence, then synthesize into a signal with `call_ai` or `run_javascript`.

## Prompt pattern guidance

- Start from templates in `prompts.json` (has 50+ template/prompts)
- Include all schema keys you need (score/summary/notes) in `json_mode` or system instructions.
- Include source URLs per claim in outputs.
- Keep missing values explicit (`null`), avoid inventing fields.
- Start with lightweight model/short prompt; increase detail only when shape is stable.

## Template index (for `call_ai`)

Pick the closest match, adapt, don't write from scratch. Skipping this produces weaker prompts and wastes credits on bad schema outputs:

- `10-K Analysis of Top Annual Initiatives` → strategic/company signals, annual priorities, exec-level research
- `5 interesting facts about a candidate` → person research, personalization data points
- `Accelerator participation` → startup signals, funding stage, accelerator/investor context
- `AI Outbound - Followup with Event Attendees` → outreach content, personalized messaging, event-triggered hooks

The full `call_ai` prompt catalog (including all custom-signal templates) is stored in `prompts.json`.

## Structured output quality guardrails

- **Show sources** — Include source URLs per claim and indicate which API or tool provided each piece of data so the user can assess reliability.
- Use `null` explicitly for missing fields.
- Keep confidence where practical for non-trivial claims.
- Prefer entity-stable matching (name + domain + LinkedIn).
- For `call_ai*`, `json_mode` expects JSON Schema object/stringified schema.
- **Haiku is the default for call_ai when model is omitted.** Only use sonnet or opus when haiku explicitly fails.
- Do not invent values.
