---
name: contact-to-email
description: "Find and verify email addresses for contacts. Handles name+company, LinkedIn URL, or name+domain starting points."
---

# Contact → Email

This skill is a router. Do not invent your own email workflow here. Read the `gtm-meta-skill` doc `enriching-and-researching.md` and use the native plays documented there.

## Use these entrypoints

- Name + company -> `name_and_company_to_email_waterfall`
- LinkedIn URL -> `person_linkedin_to_email_waterfall`
- First name + last name + domain -> `cost_aware_first_name_and_domain_to_email_waterfall`

## Extractor contract

- Canonical scalar targets for `extract("<target>")`: `email`, `phone`, `linkedin`, `first_name`, `last_name`, `full_name`, `title`
- Use `extract("<target>")` only for those canonical scalar targets.
- Use `extractList({ keys: [...] })` only for list waterfalls. `keys` must be canonical target names the tool knows about.
- If you need explicit paths, shaping, filtering, or logic, write JS instead.

## Required read path

- For `name + company -> email`, read the `name_and_company_to_email_waterfall` section in `gtm-meta-skill/enriching-and-researching.md`.
- For `LinkedIn URL -> email`, read the `person_linkedin_to_email_waterfall` section in `gtm-meta-skill/enriching-and-researching.md`.
- For `name + domain -> email`, read the `cost_aware_first_name_and_domain_to_email_waterfall` section in `gtm-meta-skill/enriching-and-researching.md`.

## Hard rules

Optional columns: `LinkedIn`, `Company Domain` (improves match rate)

---

## Workflow B: LinkedIn URL

When you have LinkedIn profile URLs but no email. Crustdata goes first since it only needs LinkedIn URL:

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with-waterfall "email" \
  --with '{"alias":"crustdata","tool":"crustdata_person_enrichment","payload":{"linkedinProfileUrl":"{{LinkedIn URL}}","fields":["email","current_employers"],"enrichRealtime":true},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"pdl","tool":"peopledatalabs_enrich_contact","payload":{"linkedin_url":"{{LinkedIn URL}}"},"extract_js":"extract(\"email\")"}' \
  --end-waterfall \
  --with '{"alias":"validation","tool":"leadmagic_email_validation","payload":{"email":"{{email}}"}}'
```

Required columns: `LinkedIn URL`

If you also have name + company, add Apollo as the first waterfall step for better match rates:

```bash
  --with '{"alias":"apollo","tool":"apollo_people_match","payload":{"first_name":"{{First Name}}","last_name":"{{Last Name}}","organization_name":"{{Company}}","domain":"{{Company Domain}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"crustdata","tool":"crustdata_person_enrichment","payload":{...},"extract_js":"extract(\"email\")"}' \
```

---

## Workflow C: Pattern matching

When you have name + domain but no LinkedIn. Generates common email patterns (first.last, flast, etc.) and validates each. Most cost-effective for bulk lists:

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with '{"alias":"patterns","tool":"run_javascript","payload":{"code":"@$WORKDIR/email_patterns.js"}}' \
  --with-waterfall "email" \
  --with '{"alias":"v1","tool":"leadmagic_email_validation","payload":{"email":"{{patterns.p1}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"v2","tool":"leadmagic_email_validation","payload":{"email":"{{patterns.p2}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"v3","tool":"leadmagic_email_validation","payload":{"email":"{{patterns.p3}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"v4","tool":"leadmagic_email_validation","payload":{"email":"{{patterns.p4}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"v5","tool":"leadmagic_email_validation","payload":{"email":"{{patterns.p5}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"v6","tool":"leadmagic_email_validation","payload":{"email":"{{patterns.p6}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"apollo","tool":"apollo_people_match","payload":{"first_name":"{{First Name}}","last_name":"{{Last Name}}","organization_name":"{{Company}}","domain":"{{Domain}}"},"extract_js":"extract(\"email\")"}' \
  --end-waterfall \
  --with '{"alias":"final_validation","tool":"leadmagic_email_validation","payload":{"email":"{{email}}"}}'
```

Required columns: `First Name`, `Last Name`, `Domain`

Always use file-backed JS for `run_javascript` columns (`run_javascript:@$WORKDIR/<script>.js`); avoid inline JSON `{"code":"..."}` payloads to prevent quoting failures.

---

## Understanding validation results

After validation, check `validation.data.email_status`:

| Status | Meaning | Action |
|---|---|---|
| `valid` | SMTP-verified deliverable, <1% bounce | ✅ Use for outreach |
| `valid_catch_all` | Catch-all domain + engagement signal confirms address, <5% bounce | ✅ Use for outreach — best result for catch-all domains |
| `catch_all` | Domain accepts all — unverifiable without engagement signal | ✅ Use with caution (same risk as Clay default) |
| `unknown` | Could not verify (server no response) | ❌ Skip or try pattern matching |
| `invalid` | Not deliverable | ❌ Skip or try another workflow |

> **Critical:** `valid_catch_all` is the highest-confidence result for catch-all domains. It is confirmed via engagement signals and has <5% bounce rate. Never treat it as `invalid` or `unknown`. Accept `valid`, `valid_catch_all`, and `catch_all`; reject `unknown` and `invalid`.

---

## Expected coverage

Set realistic expectations before running:

| Workflow | Expected fill rate | Notes |
|----------|-------------------|-------|
| A (name + company) | ~50-65% | Apollo ~50% alone, +15% from Crustdata/PDL |
| B (LinkedIn URL) | ~55-70% | Crustdata strongest with LinkedIn URL input |
| C (pattern matching) | ~40-60% | Depends on domain catch-all policies |

**Validation pass rates:** Of found emails, expect ~85% valid, ~10% catch-all, ~5% invalid. Catch-all is usable for outreach (expect slightly higher bounce).

**Pre-flight rule:** Don't waste credits on rows missing minimum data. Workflow A needs name + company. Workflow B needs LinkedIn URL. Workflow C needs name + domain. Skip rows missing these fields.

## Scale after pilot

```bash
# After reviewing --rows 0:1 output, run remaining rows:
deepline enrich --input leads.csv --in-place --rows 1: \
  # ... same flags as pilot
```

- Use `deepline enrich`, not ad-hoc shell scripts.
- Prefer native plays over hand-written waterfalls.
- Run a one-row pilot first.
- Validate the winning email before treating it as final.
