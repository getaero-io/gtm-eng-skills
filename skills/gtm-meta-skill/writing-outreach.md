# Writing Outreach Skill

Use this skill when the task involves cold emails, personalization, lead scoring, qualification, sequence design, campaign copy, or playground inspection of enrichment results.

## What This Skill Does

- Loads ICP/criteria context from a local file (for example `./icp.md`) using `read_file`.
- Produces strict, structured qualification output:
  - numeric score (`0-10`)
  - fit label (for example `Strong fit: 8/10`)
  - rationale summary
  - question-by-question yes/no/unknown answers with confidence and rationale
- Produces strict, structured 4-step outbound email sequence:
  - subject
  - core value prop
  - message body
  - sequence-level rationale

## Required Inputs

- `prospect_payload`: Person + company context (JSON string/object in row)
- `icp.md` (or equivalent): Local qualification criteria and positioning constraints

## General Setup (Recommended)

Create a small context pack in your working directory before running this flow:

- `icp.md`: Ideal customer profile and disqualifiers
- `qualification_questions.md`: The exact questions you want scored
- `product_context.md`: Value props, proof points, and constraints
- `copy_rules.md`: Tone, banned claims, length limits, CTA style

Minimal folder layout:

```text
./context/
  icp.md
  qualification_questions.md
  product_context.md
  copy_rules.md
```

Example `icp.md` starter:

```markdown
# ICP
## Best-fit companies
- B2B SaaS, 200-5000 employees, multi-product GTM team
- Uses modern data stack and CRM-based workflows

## Best-fit personas
- VP/Head/Director in Marketing, RevOps, Sales Ops, GTM Ops
- Owns pipeline quality, segmentation, scoring, or campaign orchestration

## Core pains
- Slow GTM iteration due to analyst/engineering dependency
- Low trust in black-box scoring
- Weak signal-to-action workflow for reps

## Disqualifiers
- <20 employees
- Pure B2C motion
- No clear sales/marketing operations function
```

## Best Practices

- Keep `icp.md` specific and opinionated. Broad ICPs create generic copy.
- Separate facts vs assumptions in your context docs.
- Put proof points in `product_context.md` so emails can reference them cleanly.
- Define hard copy constraints in `copy_rules.md`:
  tone, max words, banned phrases, allowed CTA types.
- Use `Unknown` for missing evidence in qualification instead of guessing.
- Run the QA prompt template before finalizing sequence copy.
- Version your context docs with the campaign (`context-q1-enterprise.md`, etc.).

## Output Contracts

### Qualification JSON Contract

```json
{
  "data": {
    "score": 8,
    "score_label": "Strong fit: 8/10",
    "fit_band": "STRONG_FIT",
    "rationale": "Short summary of fit and caveats.",
    "qualification": {
      "answers": [
        {
          "question": "string",
          "answer": "Yes",
          "confidence": "HIGH",
          "rationale": "string"
        }
      ],
      "summary": {
        "positives": ["string"],
        "risks": ["string"],
        "next_checks": ["string"]
      }
    }
  }
}
```

### Email Sequence JSON Contract

```json
{
  "data": {
    "emails": [
      {
        "step": 1,
        "subject": "string",
        "coreValueProp": "string",
        "email": "string"
      }
    ],
    "sequence_rationale": "string"
  }
}
```

## Personalization: `run_javascript` vs `call_ai`

When you already have contact + company context in CSV columns, use `run_javascript` for email generation — it's instant, deterministic, and zero LLM cost. Only use `call_ai` when you need per-row web research or complex reasoning.

**Critical: avoid mail-merge output.** If every email has the same structure with only `{{first_name}}` and `{{company_name}}` swapped, it's a template — not personalized outreach. Each email must reference something specific to the company (product, use case, industry, recent news). Use `company_description`, `one_liner`, or other enrichment columns in your JS template or `call_ai` prompt so each email is substantively different.

```bash
# Fast path: template personalization via run_javascript (instant, free)
deepline enrich --input enriched.csv --in-place \
  --with '{"alias":"outbound_email","tool":"run_javascript","payload":{"code":"@${OUTPUT_DIR}/template_email.js"}}'

# Slow path: call_ai when you need per-row research (adds ~60s, LLM cost)
deepline enrich --input enriched.csv --in-place \
  --with '{"alias":"outbound_email","tool":"call_ai","payload":{"prompt":"Research {{company_domain}} and write a personalized email to {{first_name}}...","tools":["WebSearch"]}}'
```

## Recommended Workflow

```bash
deepline tools get read_file
deepline tools get call_ai_claude_code
deepline tools execute read_file --payload '{"path":"./icp.md"}

QUAL_PROMPT=$(jq -Rs '{prompt: ("You are a B2B qualification analyst. Return strict JSON only with this shape: {data:{score:number,score_label:string,fit_band:string,rationale:string,qualification:{answers:[{question:string,answer:\"Yes\"|\"No\"|\"Unknown\",confidence:\"HIGH\"|\"MEDIUM\"|\"LOW\",rationale:string}],summary:{positives:[string],risks:[string],next_checks:[string]}}}}. Use high recall defaults unless explicitly asked for strict matching. Inputs:\nICP file payload: " + . + "\nProspect payload: {{prospect_payload}}"), model:"haiku", agent:"claude", json_mode:true}' ./icp_context.json)

SEQ_PROMPT=$(jq -Rs '{prompt: ("You are a B2B email strategist. Return strict JSON only with this shape: {data:{emails:[{step:number,subject:string,coreValueProp:string,email:string}],sequence_rationale:string}}. Write 4 concise emails tied to qualification rationale and explicit pains. Inputs:\nICP file payload: " + . + "\nQualification payload: {{qualification_output}}\nProspect payload: {{prospect_payload}}"), model:"haiku", agent:"claude", json_mode:true}' ./icp_context.json)

printf "prospect_payload\n{\"person\":{\"firstName\":\"Rachael\",\"lastName\":\"Foster\",\"title\":\"Vice President AMER Field Marketing, Public Sector, Services, & Community\"},\"company\":{\"name\":\"Cloudera\",\"domain\":\"cloudera.com\"}}\n" > ./qualification_email_seed.csv

deepline enrich --input ./qualification_email_seed.csv --output ./qualification_email_seed_enriched.csv \
  --with '{"alias":"qualification_output","tool":"call_ai_claude_code","payload":{"prompt":"${QUAL_PROMPT}"}}' \
  --with '{"alias":"email_sequence_output","tool":"call_ai_claude_code","payload":{"prompt":"${SEQ_PROMPT}"}}' \
```

## Prompt Templates (Copy/Paste)

Use these as `call_ai_claude_code` payload templates inside `--with` columns. **Haiku is the default when model is omitted.**

### 1) Score + Fit Label Template

```json
{
  "prompt": "You are a B2B scoring analyst.\nReturn strict JSON only:\n{\"data\":{\"score\":0,\"score_label\":\"\",\"fit_band\":\"\",\"scoring\":{\"weights\":[{\"factor\":\"\",\"weight\":0,\"evidence\":\"\",\"impact\":\"positive|negative|neutral\"}],\"confidence\":\"HIGH|MEDIUM|LOW\"},\"rationale\":\"\"}}\nRules:\n- score is integer 0-10\n- score_label format: \"Strong fit: X/10\" or \"Possible fit: X/10\" or \"Weak fit: X/10\"\n- fit_band one of: STRONG_FIT, POSSIBLE_FIT, WEAK_FIT\n- use evidence from provided context only; do not invent facts\n- default to higher recall unless strict matching is explicitly requested\nInputs:\nICP context: {{icp_context}}\nProspect payload: {{prospect_payload}}",
  "model": "haiku"
}
```

### 2) Qualification QA + Rationale Template

```json
{
  "prompt": "You are an ICP qualification analyst.\nReturn strict JSON only:\n{\"data\":{\"qualification\":{\"answers\":[{\"question\":\"\",\"answer\":\"Yes|No|Unknown\",\"confidence\":\"HIGH|MEDIUM|LOW\",\"rationale\":\"\"}],\"summary\":{\"positives\":[\"\"],\"risks\":[\"\"],\"next_checks\":[\"\"]}},\"rationale\":\"\"}}\nRules:\n- keep answers short and explicit\n- each rationale must reference concrete evidence from context\n- mark Unknown when evidence is missing\n- avoid strict/exact matching unless explicitly asked\nInputs:\nICP questions: {{qualification_questions}}\nICP context: {{icp_context}}\nProspect payload: {{prospect_payload}}",
  "model": "haiku"
}
```

### 3) 4-Step Email Sequence Design Template

```json
{
  "prompt": "You are a B2B email strategist.\nReturn strict JSON only:\n{\"data\":{\"emails\":[{\"step\":1,\"subject\":\"\",\"coreValueProp\":\"\",\"email\":\"\"}],\"sequence_rationale\":\"\"}}\nRules:\n- exactly 4 emails with step 1..4\n- each email must map to a pain or risk from qualification summary\n- concise style, no fluff, no markdown\n- personalization must reference role/company context from prospect payload\n- avoid claims not supported by inputs\nInputs:\nProduct context: {{product_context}}\nQualification output: {{qualification_output}}\nProspect payload: {{prospect_payload}}",
  "model": "haiku"
}
```

### 4) Subject Line Variant Generator Template

```json
{
  "prompt": "You are a B2B subject line writer.\nReturn strict JSON only:\n{\"data\":{\"subjects\":[{\"variant\":\"\",\"angle\":\"pain|outcome|proof|curiosity\",\"why_it_matches\":\"\"}]}}\nRules:\n- create 8 variants max 7 words each\n- no clickbait, no ALL CAPS, no exclamation marks\n- tie each variant to qualification rationale\nInputs:\nQualification output: {{qualification_output}}\nProspect payload: {{prospect_payload}}",
  "model": "haiku"
}
```

### 5) Email Quality Critique Template (Optional QA Pass)

```json
{
  "prompt": "You are a cold email QA editor.\nReturn strict JSON only:\n{\"data\":{\"issues\":[{\"step\":1,\"severity\":\"HIGH|MEDIUM|LOW\",\"issue\":\"\",\"fix\":\"\"}],\"revised_emails\":[{\"step\":1,\"subject\":\"\",\"coreValueProp\":\"\",\"email\":\"\"}]}}\nRules:\n- flag vague claims, unsupported assertions, and weak personalization\n- keep original structure and tighten only where needed\nInputs:\nQualification output: {{qualification_output}}\nEmail sequence output: {{email_sequence_output}}\nProspect payload: {{prospect_payload}}",
  "model": "haiku"
}
```

## Guardrails

- Keep qualification deterministic and evidence-based from provided context.
- Prefer high recall unless strict matching is explicitly requested.
- Keep outputs strict JSON (no markdown wrappers).
- Keep email copy concise, specific to role/company context, and grounded in qualification rationale.

## Playground Inspection

Use these commands to interact with `deepline csv` directly for inspecting and debugging enrichment results.

### Open an existing CSV in Playground

```bash
deepline csv render --csv leads.csv --open
```

- Use `--open` to launch the UI.

### Inspect rows (`deepline csv show`)

`deepline csv show --csv <path> [--format json|table|csv] [--verbose] [--summary] [--rows START:END]`

- format: json (default, `{rows, _metadata}`), table (ASCII, 40-char cap), csv (RFC 4180)
- --verbose: include step columns + full cell values
- --summary: per-column stats + miss_reasons
- --rows: `start:end` bounds (default `0:19`)

```bash
deepline csv show --csv leads.csv
deepline csv show --csv leads.csv --format table --rows 0:10
deepline csv show --csv leads.csv --summary
```

### Re-run a playground block

```bash
deepline csv --execute_cells --csv leads.csv --rows 0:10 --cols 9:9 --wait
```

- `--cols` is the column index range to re-run (`N:N` for one column).
- Keep `--rows` explicit.
- Use `--wait` when you need completion before the next command.

### CLI-only debug posture

- If you need to inspect or re-execute, use these playground commands directly.
- If you need to add columns or add providers, switch back to `deepline enrich` workflow docs instead of extending this page.
