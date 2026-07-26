# Enriching rows

Row-shaped input, target columns to fill: emails, phones, LinkedIn, hydration, signals, AI research, qualification. Seed lists come from `finding.md`; copy built on these columns lives in `writing.md`.

## Enriching rows

You have row-shaped input (CSV, JSON array, or discovery output) and a target column. Inspect the CSV with the CLI before choosing a play, so the play choice and any `--columns.*` mapping are based on the actual shape the runtime sees:

```bash
deepline csv show --csv <input.csv> --summary
```

Route by the identifiers each row has:

| You have                                                            | You need                     | Pattern category                                   | Discover with                                   |
| ------------------------------------------------------------------- | ---------------------------- | -------------------------------------------------- | ----------------------------------------------- |
| `first_name`, `last_name`, `domain`                                 | work email                   | name + domain → work email waterfall               | `deepline plays search email --json`            |
| name + `company_name` (no domain), or `/sales/lead/` URL            | work email                   | resolve domain first, then name + domain waterfall | discovery, then domain → email                  |
| `/in/` LinkedIn URL + name                                          | work email                   | linkedin profile → work email waterfall            | `deepline plays search email --json`            |
| `email`                                                             | hydrated person + company    | reverse contact enrichment                         | `deepline plays search contact --json`          |
| name + `domain` (+ optional email/linkedin)                         | phone number                 | identity → phone waterfall                          | `deepline plays search phone --json`            |
| name + `company_name` (+ optional linkedin)                         | job-change status            | job-change detection + verification                | `deepline plays search "job change" --json`     |
| existing `email`                                                    | validation status + verdict  | email verifier                                     | `deepline tools search "email verifier" --json` |
| name, optional company                                              | LinkedIn profile URL         | name → LinkedIn URL waterfall                       | `deepline plays search linkedin --json`         |
| row + ICP description                                               | tier / fit classification    | structured AI column with `jsonSchema`             | (see AI research)                               |

Plays encode provider sequencing, validation, row progress, and retry behavior — row-level enrichment should run through a prebuilt or scratchpad play, not loose `tools execute` calls. Keep custom `definePlay(...)` names short (`email-wf`, `phone-wf`, `company-fit`): the persisted sheet table is `normalized play name + ctx.dataset key`, and Postgres caps that combined identifier at 63 characters.

When source headers do not match a play's canonical names, pass column aliases at invocation instead of editing the play — the play gets canonical fields in code while persisted output keeps the user's original headers next to derived columns:

```bash
deepline plays run <play-name> \
  --input '{"csv":"leads.csv","columns":{"first_name":"First Name","last_name":"Last Name","domain":"Website"}}' \
  --watch
deepline runs export <run-id> --out leads_with_emails.csv
```

The batch phone play defaults to headers `FIRST_NAME`, `LAST_NAME`, `COMPANY_DOMAIN`, `CONTACT_EMAIL`, `LINKEDIN_URL`; the job-change play adds `COMPANY_NAME`, `TITLE`. Job-change output appends `job_change`, `job_changed`, `confidence_tier`, `new_company`, `new_title` — treat `HIGH` as detector-and-verification agreement, `MEDIUM` as a single-source signal, `LOW` as no reliable change. Pilot job-change on two data rows (`head -3 input.csv > pilot.csv`) because its multiple provider branches can hide a missing-column or verification-path issue on a single row.

**Run shapes.** For a CSV, run the batch prebuilt directly. For one row, use the scalar prebuilt. For a custom CSV play, compose the scalar prebuilt inside a row `ctx.dataset` with `ctx.runPlay(...)` when no batch prebuilt fits — the prebuilt carries the current provider order, fallbacks, normalization, and no-result handling. Use a stable step key inside the dataset; row identity comes from `ctx.dataset`, so do not generate per-row keys. The child play returns an object (`{ email, email_source, ... }`) — **extract the scalar** so the column exports cleanly:

```typescript
const enriched = await ctx
  .dataset('linkedin_email_waterfall', rows)
  .withColumn('email', async (row, rowCtx) => {
    const result = await rowCtx.runPlay<{ email: string | null }>(
      'linkedin_email',
      'prebuilt/person-linkedin-to-email',
      { linkedin_url: row.linkedin_url, first_name: row.first_name, last_name: row.last_name, domain: row.domain },
      { description: 'Resolve work email from LinkedIn profile.' },
    );
    return result.email ?? null;
  })
  .run({ key: 'linkedin_url', description: 'Resolve work emails per row.' });
```

Drop to `ctx.tools.execute(...)` only when you need one explicit provider call the prebuilt does not expose. For manual provider fallback, pick the order by measuring marginal coverage per cost on a golden set (`../shared/correctness.md`), not by vendor reputation; give each attempt a stable `id` and stop on first useful result. Prefer `steps(...).step(...).return(...)` so every attempt becomes its own visible, cached column.

**Probe the discovery provider's real output before hand-authoring.** The reruns in a custom composition come from provider output shape, not logic. Run the discovery tool once (`deepline tools execute <ref> --input '{...}' --json`), inspect the real payload, then **derive the row key from a guaranteed-present field** (a domain, a stable id) and **assume identifiers can be null** — a LinkedIn URL, a phone, a secondary email are all optionally absent. Keying a `ctx.dataset` on an identifier that some rows lack is what cost a CTO pilot its rerun loop: blank-LinkedIn rows broke the row key, forcing an edit→preflight→run cycle a five-second probe would have prevented.

### Durable enrichment gotchas

- **Sales Navigator URLs do not work in email waterfalls.** `linkedin.com/sales/lead/...` URLs are rejected by every provider that accepts a LinkedIn URL — they are scoped to a Sales Navigator session and have no public-profile equivalent. Feeding them into a waterfall returns zero matches everywhere, even though the same person's `/in/` URL would resolve. Detect the form (`/linkedin\.com\/sales\/lead\//`), resolve the company domain first, then use name + domain.
- **Personal vs work email is a hard provider split.** "Personal emails" means Gmail/Hotmail/Yahoo/Outlook — the address that follows the person across jobs. Work-email providers (Hunter, LeadMagic) return `@company.com` regardless, because that is the only class they index. Routing a personal-email request to a work-email provider lands the campaign in someone's corporate inbox and burns deliverability. Find the personal-email play with `deepline plays search "personal email" --json`.
- **Email status is a normalized contract; catch-all means verify, not send.** Statuses: `valid`, `valid_catch_all`, `catch_all`, `unknown`, `invalid`, `do_not_mail`, `spamtrap`, `abuse`, `disposable`. Verdicts: `valid` → send; `valid_catch_all` → send with caution; `catch_all` → `verify_next` (domain accepts mail at any address, so the inbox is unproven — verify with a second independent finder, do not count it as a confirmed pattern hit inside a waterfall); `unknown` → hold; the rest → drop. A `catch_all` whose domain does not match the person's company domain is a strong wrong-person signal (often a previous employer) — flag rather than send.
- **Validation belongs after recovery.** Recovering an address and confirming deliverability read better as separate stages: validating inside a waterfall step inflates cost (one validator call per attempt, including misses) and conflates recovery coverage with deliverability. Use the two-stage `ctx.dataset` pattern; a single combined stage is right only when the validator steers which provider to try next. Each `ctx.dataset` needs a distinct key after normalization (`email_waterfall`, then `email_validation`) — reusing a key fails the runtime's idempotency check at registration.
- **Use provider data directly when it is already there.** Company/contact responses often include firmographics, employment history, validation status, and confidence in the same payload. Re-running a `deeplineagent` column to get an industry the discovery provider already returned wastes credits and adds synthesis error. AI is for synthesis the providers cannot do, not for re-deriving fields they handed back.
- **Validate the person before trusting a recovered LinkedIn URL.** Searched-recovered URLs (from name + company) carry a substantial false-positive rate without a name gate: null out URLs where last name does not match exactly or as a substring, or first name does not match exactly / by 3+ char prefix / by a known nickname. Full treatment in the sibling `linkedin-url-lookup` skill.
- **Email domain ≠ company domain.** After recovery, compare each row's email domain against the company domain it should belong to. Mismatches are often previous-employer or wrong-person matches; more than ~20% mismatch means the contact-finding step needs re-running with better company disambiguation.

Inside a play, tool results serialize like `deepline tools execute --json`: execution metadata is top-level, raw provider data is `toolResponse.raw`, tool metadata is `toolResponse.meta`, semantic extractions are `extractedValues` / `extractedLists`.

## Start cheap, measure coverage, escalate — proactively

The cheapest capable route (a single prebuilt) is tier 1 — start there. But coverage is a property of the data, not the provider: one provider leaves rows empty that another fills. Do not return the first cheap answer and stop; measure coverage and decide out loud.

1. **Run the cheapest capable route on the pilot** (a single prebuilt/waterfall — not `route-fanout`).
2. **Report two numbers, honestly:**
   - **Coverage** = fill rate, read straight from the run package: `dataset_execution_stats[<column>].non_empty` (formatted `"N/M (X%)"`, e.g. `"34/50 (68%)"`) and `rowCounts.{persisted, succeeded, failed}` via `deepline runs get <id> --full --json`. The runtime computed it; don't recompute it. Multi-dataset runs surface `dataset_execution_stats_list`. Per-column execution buckets (`completed:executed`, `completed:reused`, `skipped:missed`, `failed`) explain a low fill: `skipped:missed` is honest empties, not a bug.
   - **Cost as marginal per unit** (~X credits/email), NOT the run total. A small pilot's total is inflated by fixed compute and validators (e.g. zerobounce) that amortize over scale — "11 credits for 2 emails" is a fixed-cost artifact, not the per-email price. Quote "~Y credits/email at scale," and name any expensive validator the user could drop.
3. **Decide by coverage — this is the point:**
   - **High (≥ ~85%):** ship. Mention the uplift option once ("I can try to lift the last few % with more providers — say the word").
   - **Moderate (~60–85%):** proactively **offer** the uplift — "coverage is 68%; fanning out more providers typically adds 20–30% for ~Y more credits/row. Want me to?"
   - **Low (< ~60%):** don't make the user ask — **escalate automatically** to a wider fan-out, report the lifted coverage, and get approval before scaling the extra spend. A single cheap provider clearly wasn't enough.

**`route-fanout` is the escalation engine** — it fans out many providers in parallel and fuses them (`plays/route-fanout.play.ts`). It is overkill for a trivial case where one provider suffices (it pays for breadth you don't need), and it is exactly right when coverage demands breadth. So: cheap prebuilt first, `route-fanout` when the coverage number says the single route isn't enough. The rung mechanics below are how that escalation actually runs.

## When the primary route misses

A miss on one route is not a dead row — but a second route is a purchase, not a reflex. A property's coverage ceiling is the union of independent routes, and each escalation rung must earn its marginal cost (score rungs the way `../shared/correctness.md` scores waterfall legs). On a bounded miss set, run candidate rungs **in parallel inside one play** — each rung its own column with stable ids — so the ranking lands in one run; go rung-by-rung sequentially only when spend discipline demands later rungs touch only earlier misses. Field-measured:

- **Mint a different identifier, then re-route.** The strongest escalation is resolving the person's LinkedIn URL and re-entering through the LinkedIn-based email pattern — it also catches stale employer data the original row carried. But bolt on a **hard identity gate**: the resolved profile's employer or geography must corroborate the row, not just the name. Name-only matching on common names confidently returns strangers' emails — a wrong-identity email is worse than a miss, and the reliable tell is an email domain that disagrees with the person's known employer.
- **Check the registry when the vertical has one** (healthcare NPI/NPPES, clinical trials, government contractors). Registries rarely hold emails but confirm identity and employer for free and often yield a verified phone — evidence that upgrades or vetoes every other route's output.
- **Escalate to a multi-source aggregator before concluding a ceiling.** Async aggregator tools (BetterContact-class — `deepline tools search aggregator email --json`) cascade many upstream sources per contact and recover emails single-provider waterfalls miss; field-measured on hospital-employed physicians, an aggregator more than doubled work-email coverage after the waterfall, people-search, registry, and pattern rungs had topped out. Prefer aggregators whose contract exposes a pollable job id and per-row deliverability status; one that only resolves within a sync-wait ceiling and returns profiles without contacts wastes the run. Aggregator fills still pass the validation gate.
- **Feed aggregators only validated identifiers.** An identifier you minted but did not identity-gate (a resolved LinkedIn URL that merely name-matched) poisons aggregator matching — it returns the wrong person with confidence. Gate minted identifiers before any downstream rung.
- **Check credentials before planning a rung.** Some providers are bring-your-own-credentials (`tools describe` shows the billing source); without a linked account every call fails closed with a credentials error. Confirm the connection or drop the rung — do not count it in projected coverage.
- **Cut losing rungs fast.** If a rung's first ~5 attempts return nothing usable, stop it — people-search databases and pattern-guessing often hold nothing for a niche population, and burning the full set proves nothing the first five didn't.
- **Recognize a structural ceiling — after the aggregator rung.** Some populations keep work emails behind directories few sources index, and their mail domains block SMTP validation, so correct pattern guesses can't be promoted to fills. Once waterfall, re-route, registry, and aggregator rungs are all measured, the right output is the validated fills, honest nulls with miss reasons, and a channel pivot the evidence already paid for (verified practice phone, mobile). Report the measured ceiling instead of buying the same misses again.

After a phone is recovered, validate line type and activity with a phone validator (`deepline tools search phone --json`). A number that connects to the wrong person costs more than a missing number.

## Custom AI research and qualification

Deterministic logic — normalization, coalescing, templating, parsing, formatting — is plain TypeScript in the play body or a `withColumn` resolver. There is no `run_javascript` tool inside plays; the runtime rejects it. `deeplineagent` is for synthesis: research, classification, scoring, structured generation. Reach for the deterministic option first. Use `jsonSchema` for any structured output a downstream step reads, and confirm the live model menu with `deepline tools describe deeplineagent --json`.

```typescript
const research = await ctx.tools.execute({
  id: 'company_research',
  tool: 'deeplineagent',
  input: {
    model: '<model-id-from-describe>',
    prompt: `Research ${row.company_name} (${row.domain}). Return JSON with what_they_build and who_they_sell_to.`,
    jsonSchema: {
      type: 'object',
      properties: { what_they_build: { type: 'string' }, who_they_sell_to: { type: 'string' } },
      required: ['what_they_build', 'who_they_sell_to'],
      additionalProperties: false,
    },
  },
  description: 'Research company positioning for enrichment.',
});
```

Scoring and qualification are native, two paths, both `deeplineagent` under the hood. There is no `deepline_native` scoring action, and `route-fanout` fusion is a route-*selection* mechanism, not a score; don't use it to score.

- **Person vs ICP → tier:** run the prebuilt `prebuilt/engagers-to-icp-qualification`. Its output is `{ icp_tier: 'tier1' | 'tier2' | 'tier3', icp_reason }`: a structured tier plus a one-sentence reason, exactly the ICP-engagement classification a list of reactors needs.
- **Anything else** (account/company fit, a custom lead score, a ranking): call `deeplineagent` with a constrained `jsonSchema` (the block above), or `enrich --with '{"tool":"deeplineagent","payload":{"prompt":...,"jsonSchema":...}}'`. Use an enum for a tier plus a `reason` field, grounded only on the provided context.

**Flatten structured output before deterministic reuse.** `deeplineagent` structured columns are wrapped in a result envelope. Interpolating `{{column}}` into another prompt usually works; field-level `{{column.field}}` does not. When a downstream step needs a field, add a plain-TypeScript flatten column that emits a scalar — the structured payload is at `toolResponse.raw.extracted_json`.

## Exit

- Research columns exist and copy is next → `writing.md`.
- Ranking an uncertain route or QA before shipping → `../shared/correctness.md`.
- A run failed, stalled, or output looks wrong → `../references/debugging.md`.
