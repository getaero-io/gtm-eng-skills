# Clay Action → Deepline Tool Mappings

## Provider / Model Translation

| Clay model | Deepline model | Notes |
|---|---|---|
| gpt-4.1, claude (clay-argon) | `model: "sonnet", agent: "claude"` | Complex reasoning, json_mode |
| gpt-4o-mini, gpt-5-mini, haiku | `model: "haiku", agent: "auto"` | Fast classify/generate |
| gpt-5-nano | `model: "haiku", agent: "auto"` | Cheapest tier |

## Action Key Mappings

### `use-ai` (no web browsing)
```json
"call_ai": {
  "prompt": "<translated prompt>",
  "model": "sonnet",
  "agent": "claude",
  "json_mode": <schema if Clay had output schema>
}
```
- If Clay prompt had `useCase: "claygent"` AND `allowBrowsing: true` → use exa_search pass first (see Claygent below)
- If Clay prompt only used formula fields (no web) → call_ai only, no exa needed

### `use-ai` (Claygent / web browsing mode)
Two-pass pattern — the exa_search must be a prior column:

**Pass N**: `exa_research=exa_search:{"query": "{{fields.company_name}} {{fields.company_domain}} <topic>", "num_results": 5, "contents": {"text": true, "highlights": true}}`

**Pass N+1**: `col_name=call_ai:{"prompt": "...\n\nWeb research:\n{{exa_research}}\n...", "model": "sonnet", "agent": "claude", "json_mode": <schema>}`

### `chat-gpt-schema-mapper`
Simple field classification — use haiku:
```json
"call_ai": {
  "prompt": "<classification prompt>",
  "model": "haiku",
  "agent": "auto"
}
```
Return only the value (no json_mode needed for single-field output).

### `run_javascript`
Direct translation. Rules:
- Wrap async code: `return (async () => { ... })()`
- No top-level `await`
- Use `row.column_name` for input (not `row.columns.xxx`)
- String concatenation instead of template literals for external vars

### `octave-qualify-person` (proprietary Octave)
Replace with `call_ai` sonnet using win/loss ICP scoring:

```json
{
  "prompt": "<ICP definition + scoring rubric + prospect signals>",
  "system": "You are a B2B GTM analyst scoring prospects against a specific ICP.",
  "model": "sonnet",
  "agent": "claude",
  "json_mode": {
    "type": "object",
    "properties": {
      "score": {"type": "number"},
      "tier": {"type": "string", "enum": ["A", "B", "C"]},
      "qualified": {"type": "boolean"},
      "rationale": {"type": "string"},
      "disqualifiers": {"type": "array", "items": {"type": "string"}}
    }
  }
}
```

ICP scoring framework (4-dimension, sum to 10):
1. **Persona fit** (0-4): Does title/function match target persona?
2. **Seniority** (0-2): Dir-VP range with tooling ownership?
3. **Hiring signals** (0-2): Actively hiring for target function?
4. **Strategic fit** (0-2): Initiatives match product value prop?

Tier: A = 8-10, B = 5-7, C = 0-4. Qualified if score >= 6.

### `score-your-data` (Clay native scorer)
If configured in Clay: map each scoring item to a `call_ai` haiku boolean check, sum scores.
If unconfigured (all null slots): treat as `octave-qualify-person` — build ICP from product context.

### `exa_search` (Clay native)
Direct equivalent: `exa_search` deepline tool. Same parameters.

## Field Reference Translation

Clay uses `{{f_0sy80p3xxx}}` refs in prompts. Steps to translate:

1. Get field list from `GET /v3/tables/{TABLE_ID}` (fields[].id + fields[].name)
2. Build map: `f_0sy80p3xxx` → `snake_case(field.name)`
3. After Pass 1 flatten: most fields are under `{{fields.xxx}}`
4. Special case: `call_ai` json_mode output → always `{{col_name.extracted_json}}`

## Column Naming Convention

```
clay_record          raw bulk-fetch-records output (run_javascript)
fields               flattened clay_record (run_javascript flatten pass)
exa_research         web research results (exa_search)
job_function         persona classification (call_ai haiku)
strategic_initiatives company initiatives (call_ai sonnet, json_mode)
tension_mapping      PQS pain analysis (call_ai sonnet, json_mode)
key_gtm_friction     outreach question (call_ai haiku)
pvp_messages         value promises (call_ai sonnet, json_mode)
tech_resources_readiness hiring signal sentence (call_ai haiku)
qualify_person       ICP score (call_ai sonnet, json_mode)
```
