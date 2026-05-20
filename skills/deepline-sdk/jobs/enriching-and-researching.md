# Enriching and researching

Row-level work: take rows that already have some identifiers and fill in additional columns. Covers email recovery, phone lookup, LinkedIn URL resolution, reverse-email hydration, persona lookup, custom AI research, classification, scoring, and ICP qualification.

This doc does **not** cover building a list from scratch. If you do not yet have rows or known entities, read `jobs/finding-companies-and-contacts.md` first. It does not cover writing outreach copy either — that lives in `jobs/writing-outreach.md` and assumes the research columns it needs already exist.

## When you are in this doc

You have an input that is row-shaped — a CSV, a JSON array of objects, or output from a previous discovery step — and a target column or columns to produce. The user phrasing is something like:

- "enrich this CSV with work emails"
- "find phone numbers for these contacts"
- "resolve the LinkedIn URL for each row"
- "score these leads as Tier 1 / 2 / 3 against this ICP"
- "research what each company does and who they sell to"
- "detect who in this list changed jobs recently"

If the prompt is closer to "find me 25 companies that match X" or "find contacts at these accounts", you are in `jobs/finding-companies-and-contacts.md`.

Before choosing a play for a CSV task, inspect the CSV with the CLI, not only by reading the file:

```bash
deepline csv show --csv <input.csv> --summary
```

Use the summary to confirm row count, exact headers, and whether columns already match the target play's CSV contract. Do this before `plays search`/`plays describe` so the play choice and any `--columns.*` mapping are based on the actual input shape visible to the runtime.

## Choose your approach

Route by what identifiers each row has and what column you need. The play names below are starting hints — confirm with `deepline plays search` + `deepline plays describe` before invoking, because canonical play names get renamed when the underlying provider mix evolves.

| You have | You need | Pattern category | Discovery |
|---|---|---|---|
| `first_name`, `last_name`, `domain` | work email | name + domain → work email waterfall | `deepline plays search email --json` |
| `first_name`, `last_name`, `company_name` (no domain) or Sales Nav `/sales/lead/` URL | work email | resolve domain first, then name + domain waterfall | discovery, then domain → email |
| Standard `/in/` LinkedIn URL + name | work email | linkedin profile → work email waterfall | `deepline plays search email --json` |
| `email` | hydrated person + company context | reverse contact enrichment | `deepline plays search contact --json` |
| `first_name`, `last_name`, `domain` (+ optional `email`/`linkedin_url`) | phone number | identity → phone waterfall | `deepline plays search phone --json` |
| `first_name`, `last_name`, `company_name` (+ optional `linkedin_url`) | job-change status | job-change detection + verification | `deepline plays search "job change" --json` |
| `company_name`, `domain`, role intent | candidate contacts at a company | role-based contact waterfall | `deepline plays search contact --json` |
| `name`, optional company context | LinkedIn profile URL | name → LinkedIn URL waterfall | `deepline plays search linkedin --json` |
| Existing email | validation status (valid / catch_all / invalid / unknown) | email verifier | `deepline tools search "email verifier" --json` |
| Row + ICP description | tier / fit classification | structured AI column with `jsonSchema` | (see "Custom AI research") |
| Row + research need not covered by a provider | custom research column | `deeplineagent` with optional structured output | (see "Custom AI research") |

Use direct tools rather than a play only when no play covers the pattern, when the workflow needs a custom provider order, or when testing a niche provider path. Plays encode hard-won provider sequencing and validation rules — start with them.

For custom play files, keep `definePlay(...)` names short. The persisted sheet table is named from the normalized play name plus the `ctx.map` key, and Postgres caps that combined identifier at 63 characters. Use names like `email-wf-eval`, `phone-wf`, or `company-fit`, not long task descriptions.

For CSV pilots, create a separate one-row pilot CSV and run the same play against that smaller file:

```bash
head -2 leads.csv > pilot.csv
deepline plays run ./my-play.play.ts --input '{"file":"pilot.csv"}' --watch
```

Use 2 rows only when the second row exercises a different branch you need to verify and there is enough time budget. Passing `--input '{"rows":"0:1"}'` does not filter a CSV unless the play code explicitly reads `input.rows` and slices the dataset.

When source CSV headers do not match a play's canonical input names, pass column aliases instead of editing the play. Inspect the current contract with `deepline plays describe <play> --json`, then map the user's headers at invocation time:

```bash
deepline plays run <play-name-from-search> \
  --input '{"csv":"leads.csv","columns":{"first_name":"First Name","last_name":"Last Name","domain":"Company Domain"}}' \
  --watch
```

The play gets canonical fields in code, while persisted output keeps the user's original CSV headers next to the derived columns. That preserves lineage and avoids creating duplicate raw fields.

## Durable rules

These rules survive provider renames and are worth carrying in your head every time you do row-level work. The cross-cutting rules in `SKILL.md` (pilot, never-fabricate, evidence preservation, replay-safety) apply here too — they are not restated.

### Sales Navigator URLs do not work in email waterfalls

LinkedIn URLs in the form `linkedin.com/sales/lead/...` are rejected by every provider that accepts a LinkedIn URL — they are scoped to a Sales Navigator session and have no public-profile equivalent. Feeding them into an email waterfall returns zero matches across every provider, even though the same person's `/in/` URL would resolve. Detect the form, resolve the company domain first, then use a name + domain pattern.

```typescript
const isSalesNavUrl = (url: string) => /linkedin\.com\/sales\/lead\//.test(url);
```

### Personal and work email are a hard provider split

When the user asks for "personal emails" they mean Gmail, Hotmail, Yahoo, Outlook — the address that follows the person across jobs. Work-email providers (Apollo, Hunter, LeadMagic) return `@company.com` addresses regardless, because that is the only data class they index. Routing a personal-email request to a work-email provider returns work emails marked as personal, lands the campaign in someone's corporate inbox, and burns deliverability before the user catches it. Personal-email work uses a different provider class entirely. Find the canonical play with `deepline plays search "personal email" --json`.

### Catch-all is operationally usable, not deliverable

Email validators return one of `valid`, `catch_all`, `invalid`, `unknown`:

- `valid` — deliverable, send.
- `catch_all` — the domain accepts mail at any address, so the validator cannot prove the inbox exists. Operationally usable for outreach but riskier; do not count it as a confirmed pattern hit inside a waterfall.
- `invalid` — drop.
- `unknown` — unresolved; treat like a miss.

A `catch_all` email whose domain does not match the person's company domain is a strong signal of a wrong-person match (often a previous employer); flag rather than send.

### Validation belongs after recovery

The two responsibilities — recovering an address and confirming it is deliverable — read better as separate stages. Validating inside a waterfall step inflates cost (one validator call per provider attempt, including the misses) and conflates the recovery question (which provider returns the most coverage) with the validation question (which subset of recovered addresses is deliverable). The two-stage `ctx.map` pattern in `SKILL.md` is the default; a single combined stage is occasionally right when the validator's response steers which provider to try next, but the cost of finding out is high enough that it should be a deliberate choice.

When the user explicitly asks to "validate after," run the email waterfall first, then run a separate verifier stage against the recovered `email` column. Do not count the waterfall's internal pattern checks as the requested after-step validation. Find the current verifier with `deepline tools search "email verifier" --json` and confirm the payload with `deepline tools describe <tool-id> --json`; for CSV work, add a second `ctx.map` stage or use the canonical validation play/tool surface if one is available in `deepline plays search "email validation" --json`.

Inside a play, tool results use the same shape as `deepline tools execute --json`: Deepline execution metadata is top-level, provider output is `result.data`, provider metadata is `result.meta`, and Deepline's semantic extractions live in `extracted`.

```typescript
const verification = await ctx.tools.execute('verify_email', '<verifier-tool-id>', {
  email: row.email,
}, {
  description: 'Validate recovered email deliverability.',
});
const email_status =
  verification.result.data.status
  ?? verification.extracted.email_status?.value
  ?? null;
```

### Use provider data directly when it is already there

Provider responses for company and contact lookups often include firmographics, employment history, role context, validation status, and confidence scores in the same payload. Use those fields directly. Re-running a `deeplineagent` research column to get a company's industry when the discovery provider already returned it wastes credits and introduces synthesis error where deterministic data was available. AI is for the synthesis the providers cannot do, not for re-deriving fields they handed back.

### `run_javascript` for transforms, `deeplineagent` for synthesis

The two AI-adjacent escape hatches are not interchangeable:

- **`run_javascript`** is for deterministic logic: normalization, coalescing, templating, conditional dispatch, parsing, formatting. Inside, `row` is the current row. Confirm the live tool with `deepline tools describe run_javascript --json`.
- **`deeplineagent`** is for synthesis: research, classification, scoring, structured generation, multi-step reasoning. Use `jsonSchema` for any structured output a downstream step will read. Confirm the live model menu with `deepline tools describe deeplineagent --json`.

Reach for the deterministic option first. Using AI for a transform that JS can do is slow, costly, and non-reproducible across runs.

### Validate the person before trusting a recovered LinkedIn URL

Searched-recovered LinkedIn URLs (from name + company queries) carry a ~26% false-positive rate without a name-validation gate, measured on a 253-person dataset. Null out URLs where the profile name does not match: last name should match exactly or as a substring; first name should match exactly, by 3+ char prefix, or by a known nickname. The sibling skill `linkedin-url-lookup` has the full treatment when row counts get large.

### Two-stage maps need distinct keys

Each `ctx.map` in one play needs a unique key after normalization. The `SKILL.md` example uses `LINKEDIN_URL` for the enrich stage and `LINKEDIN_URL_EMAIL_STATUS` for the validate stage. Reusing the same key fails the runtime's idempotency check at registration time — the play will not run.

## Patterns

### Name + domain → work email

You have first name, last name, and the company's canonical domain (not a LinkedIn URL). Required payload: `first_name`, `last_name`, `domain` — `company_name` is generally not part of the contract.

For a CSV that already has first name, last name, and domain columns, run the prebuilt directly and export rows:

```bash
deepline plays search email --json
deepline plays describe <play-name-from-search> --json
deepline plays run <play-name-from-search> --input '{"csv":"leads.csv"}' --watch --out leads_with_emails.csv
```

If the CSV headers are variants such as `First Name`, `Last Name`, and `Website`, keep the prebuilt and provide aliases:

```bash
deepline plays run <play-name-from-search> \
  --input '{"csv":"leads.csv","columns":{"first_name":"First Name","last_name":"Last Name","domain":"Website"}}' \
  --watch \
  --out leads_with_emails.csv
```

```typescript
const result = await ctx.runPlay('email_waterfall', '<play-name-from-search>', {
  first_name: row.first_name,
  last_name: row.last_name,
  domain: row.domain,
}, {
  description: 'Resolve work email from name and domain.',
});
```

When you only have `company_name` (no domain), or a Sales Navigator `/sales/lead/` URL, resolve the domain first via search, then run the play. The discovery → resolution → email-waterfall sequence is three steps; the middle step extracts the domain from the search response.

If validation was requested, validate after the waterfall has produced an `email` column. For a one-off job, run the prebuilt to an intermediate CSV, then validate that CSV in a second run. If the user explicitly asks for a customized play, copy the prebuilt with `deepline plays get <play-name-from-search> --source --out ./my-play.play.ts`, then make the smallest local edit that adds a second validation `ctx.map` stage; do not parse JSON source fields or rewrite the waterfall from scratch. Pilot that custom play on exactly one row before the full CSV. The validation result should be a new column such as `email_status`; keep the recovered address even when status is `catch_all` or `unknown` so the user can decide whether to send. Export the final enriched + validated CSV to the exact output path the user requested; intermediate pilot, waterfall, or validation files can live under a working directory, but the deliverable path should not move.

### LinkedIn `/in/` URL → work email

You have a standard LinkedIn profile URL plus name; domain is optional but unlocks extra deterministic finder steps.

For a one-row direct lookup, run the prebuilt play. For a custom CSV play, prefer an inline provider waterfall with `ctx.tools.execute(...)`/`ctx.waterfall(...)` rather than wrapping this prebuilt via `ctx.runPlay(...)`; nested prebuilt calls in Cloudflare-backed CSV plays require trusted child manifests and can fail preflight.

```typescript
const result = await ctx.runPlay('linkedin_email_waterfall', 'prebuilt/person-linkedin-to-email', {
  linkedin_url: row.linkedin_url,
  first_name: row.first_name,
  last_name: row.last_name,
  domain: row.domain,
}, {
  description: 'Resolve work email from LinkedIn profile.',
});
```

Do not use this play for `/sales/lead/` URLs — see rule #2.

### Email → person and company context

You have an email and want to hydrate person and company fields.

```typescript
const result = await ctx.tools.execute('enrich_contact', 'deepline_native_enrich_contact', {
  email: row.email,
}, {
  description: 'Hydrate person and company context from email.',
});
```

Confirm the live tool ID with `deepline tools search "reverse contact" --json`.

### Identity → phone

You have name + domain and want a phone number; `email` and `linkedin_url` are optional hints that unlock additional provider paths inside the play.

For a CSV, use the batch prebuilt directly:

```bash
deepline plays search phone --json
deepline plays describe <phone-batch-play-from-search> --json
deepline plays run <phone-batch-play-from-search> --input '{"csv":"contacts.csv"}' --watch --out contacts_with_phones.csv
```

Default CSV headers are `FIRST_NAME`, `LAST_NAME`, `COMPANY_DOMAIN`, `CONTACT_EMAIL`, and `LINKEDIN_URL`. If the user's CSV uses different headers, map them at invocation time instead of copying the play:

```bash
deepline plays run <phone-batch-play-from-search> \
  --input '{"csv":"contacts.csv","columns":{"first_name":"First Name","last_name":"Last Name","email":"Email","linkedin_url":"LinkedIn URL"}}' \
  --watch \
  --out contacts_with_phones.csv
```

For a one-row direct lookup, use the scalar prebuilt:

```typescript
const result = await ctx.runPlay('phone_waterfall', 'prebuilt/person-to-phone', {
  first_name: row.first_name,
  last_name: row.last_name,
  domain: row.domain,
  email: row.email ?? undefined,
  linkedin_url: row.linkedin_url ?? undefined,
}, {
  description: 'Resolve phone from contact identity.',
});
```

After the phone is recovered, validate line type and activity with a phone validator (find one with `deepline tools search phone --json`).

### Contact → job-change status

You have contacts with their current company and want to detect whether they changed jobs. Use the job-change prebuilt before writing a custom play; it combines a job-change detector with profile verification and appends outcome columns while preserving the original CSV headers.

```bash
deepline plays search "job change" --json
deepline plays describe <job-change-batch-play-from-search> --json
deepline plays run <job-change-batch-play-from-search> --input '{"csv":"champion_contacts.csv"}' --watch --out job_changes.csv
```

Default CSV headers are `FIRST_NAME`, `LAST_NAME`, `COMPANY_NAME`, `TITLE`, `CONTACT_EMAIL`, `COMPANY_DOMAIN`, and `LINKEDIN_URL`. If the CSV uses different headers, pass a `columns` object inside `--input` for `first_name`, `last_name`, `company_name`, and optional mappings for `title`, `email`, `domain`, or `linkedin_url`.

Pilot job-change detection on two data rows before the full run (`head -3 input.csv > pilot.csv`, which keeps the header plus two contacts). The workflow has multiple provider branches, so a single row can hide missing-column or verification-path issues.

The batch output preserves source columns and appends `job_change`, `job_changed`, `confidence_tier`, `new_company`, and `new_title`. Treat `HIGH` as detector and verification agreement, `MEDIUM` as a single-source change signal, and `LOW` as no reliable change.

### Company + role → candidate contacts

You have a company domain and want contacts at a target role or seniority.

```typescript
const result = await ctx.runPlay('company_contacts_waterfall', 'prebuilt/company-to-contact-by-role-waterfall', {
  company_name: row.company_name,
  domain: row.domain,
  roles: row.roles,           // exact title tokens or broad function
  seniority: row.seniority,   // portable values: C-Level, VP, Head, Director
}, {
  description: 'Find contacts at a target role or seniority.',
});
```

Prefer exact title tokens (`CEO`, `CTO`, `Head of Security`, `VP Marketing`) when the user intent is specific. Use broad functional roles (`marketing`, `engineering`, `security`) only when the intent is genuinely broad — they return more candidates but noisier ones. Use `seniority` as a level hint with portable values; do not pass provider-specific enums like `c_level` unless you are bypassing the play and calling a provider directly.

### Custom AI research per row

When the column is synthesis (pain points, tier classification, summary, custom signal), use `deeplineagent`. Add `jsonSchema` for any output a downstream step will interpolate.

Confirm the live tool contract first — the model menu and accepted fields evolve:

```bash
deepline tools describe deeplineagent --json
```

```typescript
const research = await ctx.tools.execute('company_research', 'deeplineagent', {
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
}, {
  description: 'Research company positioning for enrichment.',
});
```

### ICP qualification as a structured AI column

Tier classification is just `deeplineagent` with a `jsonSchema` that enumerates the tiers.

```typescript
const tiering = await ctx.tools.execute('icp_tiering', 'deeplineagent', {
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
}, {
  description: 'Classify company ICP fit from research context.',
});
```

For ICP-engagement classification on a list of people (e.g. reactors on a LinkedIn post), there is usually a prebuilt play — confirm with `deepline plays search "icp" --json`.

### Research → generation split

When the eventual deliverable is outreach copy, do research as one row stage and copy as a second. The research column gets reused across multiple copy variants without re-running synthesis. Route the copy stage to `jobs/writing-outreach.md`.

### Flatten before reuse

`deeplineagent` structured-output columns are wrapped in a result envelope. Downstream interpolation (`{{column}}`) into another `deeplineagent` prompt usually works, but field-level access (`{{column.field}}`) does not because the cell carries an AI result wrapper. If a downstream step needs deterministic field-level reuse, add a `run_javascript` flatten pass that emits a scalar column.

```typescript
const flat = await ctx.tools.execute('flatten_research', 'run_javascript', {
  code: `
    const research = row["company_research"];
    const extracted = research?.output ?? research?.extracted_json ?? research?.result?.object ?? research;
    return extracted?.pain_points ?? null;
  `,
}, {
  description: 'Flatten structured research into a reusable scalar field.',
});
```

## Manual waterfall fallback

When no prebuilt play fits and you need explicit provider control, compose with `ctx.waterfall`. Each step takes a tool ID and a payload, and the runtime stops on the first hit. The provider order is your responsibility.

Find the current provider IDs first — names rot:

```bash
deepline tools search "email finder" --json
```

```typescript
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

After recovery, compare each row's email domain against the company domain it should belong to. Mismatches are often previous-employer or wrong-person matches. If more than ~20% of rows mismatch, the contact-finding step upstream likely needs re-running with better company disambiguation.

### LinkedIn name validation

The durable rule is in the rules section above. The full treatment for high-row-count work lives in the `linkedin-url-lookup` sibling skill.

## Exit

- Outputs a CSV with research and validation columns ready for outreach → `jobs/writing-outreach.md`.
- Discovery yielded zero or sparse rows because the company set itself was wrong → back to `jobs/finding-companies-and-contacts.md`.
- A custom play is failing replay-safety, has a stale set-live mismatch, or hit a lock file → `references/debugging.md`.
