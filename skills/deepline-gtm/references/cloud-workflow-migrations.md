# Cloud Workflow Migrations

When migrating a cloud workflow from Clay (or another platform) that has production data, establishing parity against ground truth is the critical verification step. The source system artifact (Clay JSON export, etc.) is the spec — prompts are used verbatim, scoring logic is replicated exactly. The workflow spec just cites the source artifact and notes any intentional adaptations.

---

## Source-Specific Extraction

Extraction is source-specific. Each source platform has its own extraction procedure documented in the appropriate skill recipe:

- **Clay** → `recipes/clay-to-deepline.md` §1 Extraction (covers MCP and script-based extraction, API endpoints, config structure)

For other source systems (n8n, Zapier, etc.), extraction procedures will be documented in their respective recipes as they are built.

---

## Ground Truth

Extract representative rows from the source data covering each branch/routing outcome. Store as `tmp/ground_truth_<workflow_name>.json`:

```json
[
  {
    "label": "Kurt Lohse — CPG qualified, score 10",
    "input": { "first_name": "Kurt", "email": "kurt@boredandthirsty.com", "..." : "..." },
    "expected": {
      "cpg_company": true,
      "total_score": 10,
      "status": "create_deal",
      "category": "POSITIVE_INTEREST"
    }
  }
]
```

At minimum: 2 rows for initial parity, 10+ for batch validation. Cover each routing outcome and boundary condition.

## Prompts

Use the **exact prompt text** from the source system — not a summary or rewrite. Small prompt differences cause systematic classification drift. Replace platform-specific syntax (e.g., `Clay.formatForAIPrompt()`) with `{{placeholder}}` equivalents, but do not rephrase, compress, or "improve" the prompt content. If you intentionally adapt a prompt, document why.

## Parity Thresholds

| Field type | Threshold | Rationale |
|------------|-----------|-----------|
| Deterministic formula (scoring, junk filter) | **100% exact match** | Same inputs + same logic = same output |
| LLM classification (category, sentiment) | **≥90% exact match** on unambiguous cases | LLM nondeterminism on genuinely ambiguous inputs is expected |
| LLM generation (drafts, summaries) | **Tone and intent match** (manual review) | Exact text match is meaningless for generative outputs |
| Routing outcome | **100% for deterministic paths**, ≥90% for LLM-dependent | Score of 11 must route to create_deal. Ambiguous classification → acceptable variance. |
| Side effects (Slack, CRM) | **Payload shape match** via dry_run inspection | Verify what *would* be sent is correct |

---

## Parity Testing Process

### Phase 1: Smoke test (2 rows)
```bash
deepline workflows call --workflow-name <name> --payload '<row>' --mode smoke_test --json
```
- Validates: structure, step sequencing, `run_if_js` branching, formula logic
- Uses fixture adapters — deterministic but not realistic
- Compare: **deterministic fields only** (junk filter, scoring formulas, routing thresholds)
- Fix structural failures before proceeding

### Phase 2: Dry run (2 rows)
```bash
deepline workflows call --workflow-name <name> --payload '<row>' --mode dry_run --json
```
- Validates: real enrichment, real LLM classification, real prompt behavior
- Skips side effects (CRM writes, Slack, campaigns)
- Compare **all fields** against ground truth
- For LLM fields, run 3x on the same input to distinguish prompt bugs from nondeterminism

### Phase 3: Batch parity (10+ rows)
```bash
for row in <rows>; do
  deepline workflows call --workflow-name <name> --payload "$row" --mode dry_run --json
done
```
Report as a scorecard:
```
Category:  9/10 (90%)  — 1 miss on ambiguous input
Score:     10/10 (100%) — deterministic formulas correct
Routing:   9/10 (90%)  — follows from category
```
If category parity < 90%, investigate prompt differences. If deterministic parity < 100%, fix the formula.

### Phase 4: Live test (1-2 rows)
```bash
deepline workflows call --workflow-name <name> --payload '<row>' --json
```
- Validates side effects fire (CRM records created, Slack sent)
- Requires real credentials
- Manual verification in target systems

---

## Diagnosing LLM Parity Mismatches

When classification differs from ground truth:

**1. Check prompt parity.** Diff against source system's exact prompt. Common causes of systematic drift:
- Missing examples or category definitions
- Missing priority/tiebreaker rules (e.g., "warm + question → POSITIVE_INTEREST, not INFORMATION_REQUEST")
- Summarized vs verbatim descriptions

**2. Check model parity.** Map source models to closest available:

| Source model | Deepline equivalent | Notes |
|---|---|---|
| `gpt-5-mini` | `openai/gpt-5-mini` | Exact match |
| `gpt-5.1` | `openai/gpt-5.2-chat` | No 5.1 full available; 5.1-instant is a different variant |
| `gpt-5.4-mini` | `openai/gpt-5.4-mini` | Exact match |
| `claude-sonnet-4-6` | `anthropic/claude-sonnet-4.6` | Exact match |
| `clay-argon` (Claygent) | `anthropic/claude-sonnet-4.6` | Claygent has web access — use `deeplineagent` if web research is needed |
| `clay-neon` (Claygent) | `deeplineagent` | Web search model |
| `clay-helium` (Claygent) | `openai/gpt-5.4-mini` | Lightweight model |

**3. Check for true ambiguity.** Run 3x on the same input:
- Consistently wrong → prompt issue
- Varies across runs → genuinely ambiguous input, source system got lucky

**4. Document, don't overfit.** If 9/10 match and the 1 miss is genuinely ambiguous, document it and move on. Special-case prompt tweaks for one edge case break other cases.
