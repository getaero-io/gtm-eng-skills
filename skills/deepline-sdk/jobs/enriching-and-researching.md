# Enriching and researching

Use this when you already have accounts, contacts, companies, or signals and need to add data: email, phone, LinkedIn, reverse enrichment, research, scoring, ICP qualification.

Still need to source the accounts or contacts? Use `jobs/finding-companies-and-contacts.md`. Need copy? Use `jobs/writing-outreach.md` after evidence exists.

## When you are in this doc

You have known entities plus a JTBD: "enrich this CSV", "find phones", "resolve LinkedIns", "score these leads", "research each company", "detect job changes".

For CSV tasks, inspect runtime-visible headers first:

```bash
deepline csv show --csv <input.csv> --summary
```

Use that shape to choose the play and aliases.

## Choose your approach

Route by identifiers and target column. Confirm names with `plays search` + `plays describe`.

| You have | You need | Pattern category | Discovery |
|---|---|---|---|
| `first_name`, `last_name`, `domain` | work email | name + domain → work email waterfall | `deepline plays search email` |
| `first_name`, `last_name`, `company_name` (no domain) or Sales Nav `/sales/lead/` URL | work email | resolve domain first, then name + domain waterfall | discovery, then domain → email |
| Standard `/in/` LinkedIn URL + name | work email | linkedin profile → work email waterfall | `deepline plays search email` |
| `email` | hydrated person + company context | reverse contact enrichment | `deepline plays search contact` |
| `first_name`, `last_name`, `domain` (+ optional `email`/`linkedin_url`) | phone number | identity → phone waterfall | `deepline plays search phone` |
| `first_name`, `last_name`, `company_name` (+ optional `linkedin_url`) | job-change status | job-change detection + verification | `deepline plays search "job change"` |
| `company_name`, `domain`, role intent | candidate contacts at a company | role-based contact waterfall | `deepline plays search contact` |
| `name`, optional company context | LinkedIn profile URL | name → LinkedIn URL waterfall | `deepline plays search linkedin` |
| Existing email | validation status (valid / catch_all / invalid / unknown) | email verifier | `deepline tools search "email verifier"` |
| Account/contact + ICP description | tier / fit classification | structured AI field with `jsonSchema` | (see "Custom AI research") |
| Account/contact + research need not covered by a provider | custom research signal | `deeplineagent` with optional structured output | (see "Custom AI research") |

Use direct tools only as probes. Plays encode hard-won provider sequencing, validation rules, row progress, and retry behavior, so row-level enrichment should run through a prebuilt play or a local scratchpad play. When no prebuilt covers the pattern, when provider order is custom, or when the workflow adds filtering/scoring/validation stages, write a small `*.play.ts` and add one stage at a time.
Once a search or lookup feeds later columns, make it the next play boundary. Keep `definePlay(...)` names short; persisted table identifiers cap at 63 chars.

Pilot with a small CSV:

```bash
head -2 leads.csv > pilot.csv
deepline plays run ./my-play.play.ts --csv pilot.csv --watch
```

Use 2 examples only when they exercise different branches. Passing a range flag does not filter CSVs unless the play implements that input explicitly.

When CSV headers differ, pass aliases instead of editing the play:

```bash
deepline plays run <play-name-from-search> \
  --input '{"csv":"leads.csv","columns":{"first_name":"First Name","last_name":"Last Name","domain":"Company Domain"}}' \
  --watch
```

The play gets canonical fields; output keeps the user's original headers.

## Row Rules

### Sales Navigator URLs do not work in email waterfalls

`linkedin.com/sales/lead/...` URLs are session-scoped and fail email providers. Detect them, resolve company domain, then use name + domain.

```typescript fragment
const isSalesNavUrl = (url: string) => /linkedin\.com\/sales\/lead\//.test(url);
```

### Personal and work email are a hard provider split

Personal email means Gmail/Hotmail/Yahoo/Outlook, not `@company.com`. Work-email providers will return corporate addresses; use `deepline plays search "personal email"`.

### Catch-all is operationally usable, not deliverable

Validator statuses: `valid` sends; `catch_all` is usable but unproven; `invalid` drops; `unknown` is a miss. Flag `catch_all` when the email domain differs from company domain.

### Validation belongs after recovery

Recover email first; validate after. Validating inside each provider attempt burns credits and mixes coverage with deliverability. Add a later verifier boundary so validation does not rerun recovery.

When the user explicitly asks to "validate after," run the email waterfall first, then run a separate verifier stage against the recovered `email` column. Do not count the waterfall's internal pattern checks as the requested after-step validation. Find the current verifier with `deepline tools search "email verifier"` and confirm the payload with `deepline tools describe <tool-id> --json`; for CSV work, add a second `ctx.map` stage in the scratchpad play or use the canonical validation play surface if one is available in `deepline plays search "email validation"`.

Inside a play, tool results serialize with the same shape as `deepline tools execute --json`: Deepline execution metadata is top-level, raw tool response data is `toolResponse.raw`, tool response metadata is `toolResponse.meta`, and Deepline's semantic extractions live in `extractedValues` / `extractedLists`.

```typescript fragment
const verification = await ctx.tools.execute({
  id: 'verify_email',
  tool: '<verifier-tool-id>',
  input: {
    email: row.email,
  },
  description: 'Validate recovered email deliverability.',
});
const email_status =
  verification.extractedValues.email_status?.get()
  ?? verification.toolResponse.raw.status
  ?? null;
```

### Use provider data directly when it is already there

Use provider fields directly when present. Do not ask `deeplineagent` to re-derive industry, confidence, employment history, or validation fields the provider already returned.

### TypeScript for transforms, `deeplineagent` for synthesis

- TypeScript in the play: deterministic transforms, parsing, coalescing, formatting.
- `deeplineagent`: synthesis, research, scoring, structured generation. Use `jsonSchema` when downstream steps read the output.

### Validate the person before trusting a recovered LinkedIn URL

Searched LinkedIn URLs need name validation. Null out profile URLs when last name does not match or first name has no exact/prefix/nickname match. Use `linkedin-url-lookup` for large runs.

### Two-stage maps need distinct keys

Each `ctx.map` in one play needs a unique key after normalization. Reusing a key fails registration.

## Patterns

### Name + domain → work email

Needs `first_name`, `last_name`, canonical `domain`. `company_name` is usually not enough.

Use the prebuilt when it fits:

```bash
deepline plays search email
deepline plays describe <play-name-from-search> --json
deepline plays run <play-name-from-search> --input '{"csv":"leads.csv"}' --watch
deepline runs export <run-id> --out leads_with_emails.csv
```

Map aliases at invocation time:

```bash
deepline plays run <play-name-from-search> \
  --input '{"csv":"leads.csv","columns":{"first_name":"First Name","last_name":"Last Name","domain":"Website"}}' \
  --watch
deepline runs export <run-id> --out leads_with_emails.csv
```

```typescript fragment
const result = await ctx.runPlay('email_waterfall', '<play-name-from-search>', {
  first_name: row.first_name,
  last_name: row.last_name,
  domain: row.domain,
}, {
  description: 'Resolve work email from name and domain.',
});
```

When you only have `company_name` (no domain), or a Sales Navigator `/sales/lead/` URL, resolve the domain first via search, then run the play. The discovery → resolution → email-waterfall sequence is three steps; the middle step extracts the domain from the search response.

If validation was requested, validate after the waterfall has produced an `email` column. Copy the prebuilt with `deepline plays get <play-name-from-search> --source --out ./my-play.play.ts`, then make the smallest local edit that adds a second validation `ctx.map` stage; do not parse JSON source fields or rewrite the waterfall from scratch. Pilot that custom play on exactly one row before the full CSV. The validation result should be a new column such as `email_status`; keep the recovered address even when status is `catch_all` or `unknown` so the user can decide whether to send. Export the final enriched + validated CSV to the exact output path the user requested; intermediate pilot, waterfall, or validation files can live under a working directory, but the deliverable path should not move.
Need custom provider order? Mirror generated prebuilts: `steps()`, `when(...)`, semantic accessors such as `result.extractedValues.email?.get()`, then `.return(...)`.

### LinkedIn `/in/` URL → work email

Use a standard `/in/` URL plus name. Domain is optional but useful. Do not use this path for `/sales/lead/` URLs.

### Email → person and company context

You have an email and want to hydrate person and company fields.

```typescript fragment
const result = await ctx.tools.execute({
  id: 'enrich_contact',
  tool: 'deepline_native_enrich_contact',
  input: {
    email: row.email,
  },
  description: 'Hydrate person and company context from email.',
});
```

Confirm the live tool ID with `deepline tools search "reverse contact"`.

### Identity → phone

Use name + domain; add `email` or `linkedin_url` when available. Prefer the batch prebuilt:

```bash
deepline plays search phone
deepline plays describe <phone-batch-play-from-search> --json
deepline plays run <phone-batch-play-from-search> --input '{"csv":"contacts.csv"}' --watch
deepline runs export <run-id> --out contacts_with_phones.csv
```

Map header aliases instead of copying the play:

```bash
deepline plays run <phone-batch-play-from-search> \
  --input '{"csv":"contacts.csv","columns":{"first_name":"First Name","last_name":"Last Name","email":"Email","linkedin_url":"LinkedIn URL"}}' \
  --watch
deepline runs export <run-id> --out contacts_with_phones.csv
```

After recovery, validate line type/activity with a phone validator (`deepline tools search phone`).

### Contact → job-change status

Use the job-change prebuilt; it appends change columns while preserving source headers.

```bash
deepline plays search "job change"
deepline plays describe <job-change-batch-play-from-search> --json
deepline plays run <job-change-batch-play-from-search> --input '{"csv":"champion_contacts.csv"}' --watch
deepline runs export <run-id> --out job_changes.csv
```

Default CSV headers are `FIRST_NAME`, `LAST_NAME`, `COMPANY_NAME`, `TITLE`, `CONTACT_EMAIL`, `COMPANY_DOMAIN`, and `LINKEDIN_URL`. If the CSV uses different headers, pass a `columns` object inside `--input` for `first_name`, `last_name`, `company_name`, and optional mappings for `title`, `email`, `domain`, or `linkedin_url`.

Pilot job-change detection on two data rows before the full run (`head -3 input.csv > pilot.csv`, which keeps the header plus two contacts). The workflow has multiple provider branches, so a single row can hide missing-column or verification-path issues.

The batch output preserves source columns and appends `job_change`, `job_changed`, `confidence_tier`, `new_company`, and `new_title`. Treat `HIGH` as detector and verification agreement, `MEDIUM` as a single-source change signal, and `LOW` as no reliable change.

### Company + role → candidate contacts

Use company domain plus role/seniority. Prefer exact title tokens (`CEO`, `CTO`, `Head of Security`) for specific intent; broad functions return more noise.

### Custom AI research per row

For synthesis columns, use `deeplineagent` with `jsonSchema` when downstream steps read the output. Confirm live fields:

```bash
deepline tools describe deeplineagent --json
```

```typescript fragment
const research = await ctx.tools.execute({
  id: 'company_research',
  tool: 'deeplineagent',
  input: {
    model: '<model-id-from-describe>',
    prompt: `Research ${row.company_name} (${row.domain}). Return JSON with what_they_build and who_they_sell_to. Use Deepline-managed tools only if needed.`,
    jsonSchema: {
      type: 'object',
      properties: {
        what_they_build: { type: 'string' },
        who_they_sell_to: { type: 'string' },
      },
      required: ['what_they_build', 'who_they_sell_to'],
      additionalProperties: false,
    },
  },
  description: 'Research company positioning for enrichment.',
});
```

### ICP qualification

Tier classification is just `deeplineagent` with a `jsonSchema` that enumerates the tiers.

```typescript fragment
const tiering = await ctx.tools.execute({
  id: 'icp_tiering',
  tool: 'deeplineagent',
  input: {
    model: '<model-id-from-describe>',
    prompt: `Using only the provided context, classify ${row.company_name} into one of: high_fit, medium_fit, low_fit. Context: ${row.company_research}`,
    jsonSchema: {
      type: 'object',
      properties: {
        tier: { type: 'string', enum: ['high_fit', 'medium_fit', 'low_fit'] },
        reason: { type: 'string' },
      },
      required: ['tier', 'reason'],
      additionalProperties: false,
    },
  },
  description: 'Classify company ICP fit from research context.',
});
```

For ICP-engagement classification on a list of people (e.g. reactors on a LinkedIn post), there is usually a prebuilt play — confirm with `deepline plays search "icp"`.

### Research → generation split

Do research as one stage and copy as another so copy variants reuse the same evidence. Route copy to `jobs/writing-outreach.md`.

### Flatten before reuse

`deeplineagent` structured-output columns are wrapped in a result envelope. Downstream interpolation (`{{column}}`) into another `deeplineagent` prompt usually works, but field-level access (`{{column.field}}`) does not because the cell carries an AI result wrapper. If a downstream step needs deterministic field-level reuse, add a `run_javascript` flatten pass that emits a scalar column.

```typescript fragment
const flat = await ctx.tools.execute({
  id: 'flatten_research',
  tool: 'run_javascript',
  input: {
    code: `
    const research = row["company_research"];
    const extracted = research?.output ?? research?.extracted_json ?? research?.result?.object ?? research;
    return extracted?.pain_points ?? null;
  `,
  },
  description: 'Flatten structured research into a reusable scalar field.',
});
```

## Manual waterfall fallback

When no prebuilt play fits and you need explicit provider control, compose with `ctx.waterfall`. Each step takes a tool ID and a payload, and the runtime stops on the first hit. The provider order is your responsibility.

Find the current provider IDs first — names rot:

```bash
deepline tools search "email finder"
```

```typescript fragment
const email = await ctx.waterfall([
  { tool: '<provider-id-from-search>', input: { /* ... */ } },
  { tool: '<provider-id-from-search>', input: { /* ... */ } },
  { tool: '<provider-id-from-search>', input: { /* ... */ } },
]);
```

Confirm the live waterfall API contract by reading `shared/plays-best-practices.md` or by inspecting a prebuilt play's source: `deepline plays describe <play-name> --json`.

When you reach for a manual waterfall, write down why no prebuilt play fit. If the reason is "I needed a different validator threshold," the better move is usually to call the prebuilt play and post-filter, not to rebuild the waterfall.

## Validation patterns

### Email domain ≠ company domain

Compare recovered email domain to company domain. High mismatch rates usually mean upstream contact disambiguation is wrong.

### LinkedIn name validation

Use `linkedin-url-lookup` for high-row-count profile validation.

## Exit

- Outputs a CSV with research and validation columns ready for outreach → `jobs/writing-outreach.md`.
- Discovery yielded weak account/contact coverage because the source set was wrong → back to `jobs/finding-companies-and-contacts.md`.
- A play is failing replay-safety, has a stale set-live mismatch, or hit a lock file → `references/debugging.md`.
