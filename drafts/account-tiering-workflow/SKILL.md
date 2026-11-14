---
name: account-tiering-workflow
description: |
  Stand up an always-on account-tiering workflow as a Deepline play — a triggered pipeline (cron over a
  CRM segment, or an inbound webhook) that fires per account as it enters the segment, enriches it, scores its fit for your product, tiers it, and writes
  the result back onto the record with no one in the loop. Use whenever someone asks: build me an
  account-tiering workflow, score accounts for fit as they enter a segment, tier my book automatically
  and write it back to the CRM, run fit scoring on a schedule, or set up an unattended account-scoring
  pipeline. It scores prospects and existing customers on DIFFERENT rubrics (net-new fit vs upgrade
  potential), and it separates fit from timing: a strong-fit account with no live signal is Tier 2, not
  Tier 1. It reads the account record and public enrichment, and it WRITES six scoring fields back onto
  the account in the CRM (HubSpot, Salesforce or Attio via Deepline's CRM tools). Do NOT use it to tier a static list you paste in once with nobody triggering it (that is
  a function-calling scorer, not a workflow), to route inbound leads or people, to audit whether a CRM's
  existing fields are accurate, or to monitor a single company for one signal. It never contacts anyone
  and never deletes a field.
category: score-and-qualify
personas: [revops, gtm-engineer]
mechanism: workflow
touches: writes-records
keywords: [lead-scoring, tech-stack, plg]
ported_from: clay-run/clay-skill-creator/skills/sung-jo/account-tiering-workflow
---

# Account tiering workflow

The insight: **fit and timing are two axes, not one, and a single score cannot serve both a prospect
and a customer.** A book ranked by fit alone points reps at accounts with no reason to be called this
week; a book ranked by activity alone points them at noise. So the tier is a fit score *gated on a live
signal* — Tier 1 is strong fit **and** a reason to act now, and a strong-fit account with nothing
happening is Tier 2 "nurture," not a missed Tier 1. And because a prospect and an existing customer are
different questions — *would they buy* versus *would they upgrade* — the plan the account is on picks
which rubric it is scored against, deterministically, before any judgment runs.

Two more things follow from "unattended." Because a signal starts each run and no one is present, the
tier CUT lives in a **code** step, not the scoring model — the model produces the dimension scores and
the rationale, arithmetic and thresholds are deterministic and auditable. And because it writes to the
record, the whole thing is gated: nothing is built or run against real accounts without an explicit yes,
with the cost and the write named in the same breath.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it at build
time, never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing. Where a default is defensible it is named, and using it means saying
so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The trigger segment** | the CRM list/segment whose accounts should be scored as they enter it (a HubSpot list id, a Salesforce account filter, an Attio list) — or the system that will POST new accounts to a webhook | no default — there is nothing to trigger the workflow |
| **Your product & ICP** | one paragraph on what you sell and to whom, and what signals fit: the tooling, hiring, firmographics and usage that mean a good account for *you* | ask — this is the whole scoring rubric; without it the score is generic and wrong |
| **Account-record fields** | which fields on the record hold: domain, company LinkedIn URL, company name, current plan/tier, acquisition type (prospect/customer/churned), a usage metric, open pipeline, open-opp count, engagement status & summary, last-signal date, employee count | each unmapped field drops out of scoring and is listed as unobserved; domain is required (it is the write key) |
| **In-scope rule** | which accounts should run at all — the default is *prospects, plus existing customers on the plan you want to expand from*; everything else ends the run before any credit is spent | ask — an empty rule scores your whole segment and spends on accounts you would never work |
| **Expansion-from plan** | the plan name that means "existing customer worth an upgrade motion" (the source workflow used `Pro`) | if absent, every in-scope account is scored on the New-Business rubric only |
| **Usage-pressure thresholds** | the usage-metric cut-offs that mean an account has outgrown its plan (source defaults: ≥5 moderate, ≥10 high, ≥20 severe) | default to the source values and say so; only meaningful on the Expansion track |
| **Tier cut-offs** | the score cuts for the tiers (source defaults: ≥75 Tier 1/2 line, ≥60 Tier 2/3 line) | default to the source values and say so — they are editable, and a distribution with most accounts in Tier 1 means re-tune, not celebrate |
| **Tech-stack arm** | which tech-stack tool to use: `builtwith_domain_lookup` (usage-priced), `bloomberry_get_company_tech_stack` (0.43 credits/call) or `theirstack_technographics` (1.66 credits/result) | default to `bloomberry_get_company_tech_stack` and say so; if they decline any, the tech dimension is unobserved |
| **CRM + write-target fields** | which CRM (HubSpot / Salesforce / Attio, connected in Deepline) and the six account properties to write: fit score, tier, priority, rationale, why-now, track — created in the CRM if they do not exist | if the installer does not want a write, this is not this skill (see the boundary) | if the installer does not want a write, this is not this skill (see the boundary) |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.** A
partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist. At delivery, offer to
save the answers back (identifiers and settings only — never a token or a password), private and never
published, phrased so it explains itself: *"want me to save your answers to a file, so the next person
on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the account record from the trigger segment (the fields you map), plus three per-account public enrichments: tech stack, open GTM roles, and company profile + headcount growth (one call).
- **Writes** — six scoring fields onto each in-scope CRM account record: fit score, account tier, priority flag, fit rationale, why-now, and tiering track. The installer creates those properties in the CRM if they are absent; it does not touch any other field, and null values are dropped from the write payload so a blank result never overwrites existing data.
- **Never** — contacts anyone, deletes or blanks a field, moves account data to a third party, or scores an account it never enriched.
- **Halts** — Step 3 write-approval, Step 5 spend-approval, Step 5 write-approval.

## Representative output

### Scored & tiered account record

Six fields written per in-scope account — one deliverable, six fields. This is their shape (placeholder
accounts, invented values); `fabrikam.example` is the insight on one row: a 77 clears the fit bar and
still lands Tier 2, because Tier 1 requires a live signal.

| Account | Track | Fit score | Tier | Priority | Why now | Rationale |
|---|---|---|---|---|---|---|
| northwind.example | New Business | 82 | Tier 1 | Yes | 3 RevOps roles posted in the last 60 days | Full outbound stack (CRM + sequencer + data provider), RevOps + GTM-engineering hiring, 22% headcount growth; engagement thin, scored conservatively there. |
| contoso.example | Expansion | 88 | Tier 1 | Yes | severe usage pressure on the current plan (24 workspaces) | On the expansion plan with 24 workspaces — structurally past it; large, still-hiring GTM org; open opportunity already in flight. |
| fabrikam.example | New Business | 77 | Tier 2 | No | No timing signal | Strong stack and healthy growth, but no GTM roles posted, no recent funding, and last signal is stale — good fit, nothing making it live this week. |

The ranking key the workflow computes (fit + a Tier-1 bonus + a Priority bonus) is what makes a
downstream digest sortable; it is computed but not written to the record.

## Step 0 — State the posture, then confirm the platform

Say it before anything runs: **this reads the account record and public enrichment, and it WRITES six
scoring fields back onto each in-scope CRM account.** It contacts no one, deletes nothing, and moves
nothing outside the CRM. Where it runs decides what it costs — the enrichment bills in Deepline credits
per account, and the numbers are read from `deepline tools describe` at build time, never quoted from
anywhere else.

Then confirm Deepline is working: run `deepline preflight --json`. If the CLI is missing,
`npm install -g deepline && deepline auth register --wait auto`, then re-run preflight. Name the org
and the balance out loud. Confirm the CRM is connected by describing its write tool
(`deepline tools describe hubspot_batch_upsert_objects --json`, `salesforce_update_account`, or
`attio_assert_company_record`) — **if the CRM is not connected, that is the installer's to fix**; name
it and stop. Do not work around it with a CSV and call it a workflow.

## Step 1 — Collect the definition (interview at build; do not guess)

Ask for the declared inputs above, in this order, and stop as soon as the picture is complete:

1. **The trigger segment and the account fields.** Which CRM list or segment feeds the workflow (or
   which system will POST accounts to its webhook), and which property on the record holds each input
   the scoring needs (domain, company LinkedIn URL, plan, acquisition type, usage metric, pipeline,
   engagement, employee count, last-signal date). Domain is required — it is the key the write upserts
   on. Every field they cannot map drops out of the score and is reported as unobserved, never scored
   as zero.
2. **Your product and ICP, in their words.** What they sell, to whom, and what makes an account good for
   *them* — the tooling a fit account runs, the roles it hires, the firmographics and the usage that
   signal budget and urgency. This becomes the scoring prompt. *(As a shape, not a default: the source
   workflow sold a GTM data-and-automation platform, so its fit signals were an outbound stack —
   CRM + sequencer + data provider — plus RevOps / GTM-engineering hiring and headcount growth. Use
   their signals, not these.)*
3. **The in-scope rule and the two tracks.** Who runs at all (default: prospects + customers on the
   expansion-from plan), which plan name means "expansion candidate," and confirm the two-rubric design:
   prospects scored on net-new fit, expansion candidates scored on upgrade potential. If they only sell
   net-new, drop the Expansion track and say so.
4. **The thresholds.** Tier cuts (default ≥75 / ≥60) and usage-pressure cut-offs (default 5 / 10 / 20).
   These are the installer's and editable — carry the source defaults, say they are defaults, and note
   that a distribution with most accounts in Tier 1 means the weights or cuts need re-tuning.

## Step 2 — Confirm tool contracts on the installed CLI

**Never hardcode the build from memory.** Read every contract off the live catalog before writing a
step:

```
deepline tools describe <tool_id> --json        # input fields + pricing
deepline plays bootstrap --help                 # starter shapes for triggered plays
```

Resolve every step by its full Deepline tool ID — "enrich company" or "tech stack" names several
vendors at different prices. The tools this play uses, as a starting point to confirm, not to trust
blind:

| Step | Tool ID | Input → what to read | Price (describe, 2026-09-30) |
|---|---|---|---|
| Tech stack | `bloomberry_get_company_tech_stack` (or `builtwith_domain_lookup`) | `domain` → technology list | 0.43 / call (BuiltWith: usage) |
| GTM hiring | `crustdata_v3_job_search` | company domain + title + posted-date filters, `limit` 10 → postings | 0.02 / returned posting |
| Company profile + headcount growth | `crustdata_v3_company_enrich` | `domains: [domain]`, `fields: ["basic_info","headcount","funding"]` → industry, founded, headcount, growth, last funding | 0.8 / company |
| Score | `deeplineagent` | prompt + `jsonSchema` → dimension scores, rationale, why-now | usage |
| Write | `hubspot_batch_upsert_objects` / `salesforce_update_account` / `attio_assert_company_record` | domain (or record id) → the six properties | free (your CRM quota) |

The source workflow ran headcount growth and company profile as two separate paid calls (Clay's
`cpj-get-company-employee-growth` and `cpj-enrich-company`); one `crustdata_v3_company_enrich` with both
field groups covers both. Field paths inside each response are read off the pilot in Step 4, not
assumed.

## Step 3 — Build the play  *(write-approval: publishing a live, CRM-writing play)*

Say what is about to be created — one play with a trigger, an in-scope gate, three enrichment steps,
a scoring step, a tier step and a CRM write — and get a yes before saving anything. Then author
`account-tiering.play.ts` per `deepline-gtm`'s `recipes/deepline-plays.md`, in dependency order.
Every step reads from the account row, never "through" an enrichment step.

1. **Trigger** — one of:
   - **Cron over a CRM segment** (the default): `cron: { schedule, timezone, input: { list_id, ... } }`
     with every argument in the static `input` object. The handler pulls the segment
     (`hubspot_list_memberships` + `hubspot_batch_read_objects`, `salesforce_list_accounts`, or
     `attio_query_company_records`) and runs the dataset with `.run({ key: 'domain', mode: 'net_new' })`
     so each account is scored once, as it first appears — the "enters the segment" semantics.
   - **Webhook**: `webhook: { auth: { type: 'standard-webhooks', ... } }`, the CRM's own workflow POSTs
     the account record when it enters the segment.

2. **In-Scope Gate** — a filter before any paid step. The default rule, OR-combined:
   acquisition type = prospect, **or** plan = the expansion-from plan, **or** the record's type = prospect.
   Unmatched accounts are dropped from the dataset here, before any enrichment credit is spent. State
   this fallthrough explicitly; it is the credit-protection move.

3. **Resolve Track** — deterministic code. Picks the rubric and grades usage pressure:

   ```ts
   function resolveTrack(acct: Record<string, unknown>, cfg: {
     expansion_plan?: string; pressure_moderate?: number; pressure_high?: number; pressure_severe?: number;
   }) {
     const s = (v: unknown) => (v == null ? '' : String(v).trim());
     const product_tier = s(acct.product_tier);            // the account's current plan
     const usageNum = Number(acct.usage_metric);
     const usage = Number.isFinite(usageNum) ? Math.trunc(usageNum) : 0;

     // DECLARED INPUTS — from the play input; the defaults are fallbacks, not literals.
     const expansion_plan = s(cfg.expansion_plan);
     const moderate = cfg.pressure_moderate ?? 5, high = cfg.pressure_high ?? 10, severe = cfg.pressure_severe ?? 20;

     const isExpansion = !!expansion_plan && product_tier.toLowerCase() === expansion_plan.toLowerCase();
     const track = isExpansion ? 'Expansion' : 'New Business';
     const rubric = isExpansion ? `upgrade potential from your ${expansion_plan} plan` : 'net-new fit for your product';

     let usage_pressure = 'none';
     if (isExpansion) {
       if (usage >= severe) usage_pressure = 'severe';
       else if (usage >= high) usage_pressure = 'high';
       else if (usage >= moderate) usage_pressure = 'moderate';
     }
     return {
       track, rubric, product_tier: product_tier || 'none',
       acquisition_type: s(acct.acquisition_type) || s(acct.csv_type) || 'unknown',
       usage, usage_pressure,
     };
   }
   ```

4–6. **Three enrichment columns** (`.withColumn` each, `rowCtx.tools.execute({ id, tool, input,
   description })`). Each is fed from the account row (domain), not from the step before it. **All three
   always run — this is not a waterfall**, so ordering them buys no saving; the per-account cost is
   simply the sum of the three. For every paid step name the four things — what runs (the tool ID from
   Step 2), what goes in (which mapped field), what to verify, and what it costs (`describe` pricing):
   - **Tech stack** — verify the technology list is non-empty. Empty is the common case (in the source
     workflow, measured on Clay's BuiltWith action, populated on ~1% of accounts), so treat empty as
     *no detectable stack, scored conservatively*, never as an error.
   - **GTM hiring** — `crustdata_v3_job_search` with a `limit` (source used 10), filtered to GTM titles
     and the last 60 days. **Cost trap: it bills PER RETURNED POSTING** (`pricing.unit: result`), so a
     call costs up to `limit` × 0.02. Keep the cap, and price it at the cap.
   - **Company profile + headcount growth** — verify industry / founded / type / revenue / description
     and the growth fields; **a null horizon is not 0%** — read it as unobserved, not as shrinkage.

7. **Score Account Fit** — a `deeplineagent` column with a `jsonSchema`. It applies exactly one rubric,
   chosen by `track`, and returns dimension scores plus prose — never the tier. Output schema
   (product-neutral keys, none named after this workflow): `fit_score` (0–100), the four dimension scores
   `motion_or_usage` / `hiring` / `growth` / `engagement`, `fit_rationale`, `why_now`,
   `recommended_play`, and `has_timing_signal` (Yes/No). The tier code recomputes the total from the four
   dimensions, so the model's own total is informational. The prompt, generalised — fill the ICP from
   Step 1:

   > You are scoring one account for **{your company}**'s sales team. {your company} is {one-paragraph
   > product description}. The best-fit accounts are {ICP in their words}.
   >
   > Score this account on the rubric its **Track** selected.
   >
   > **New Business** — net-new fit, out of 100: motion & stack (0–35), GTM hiring (0–25), growth &
   > funding (0–20), engagement & intent (0–20).
   > **Expansion** — upgrade potential, out of 100: usage pressure against the current plan (0–35, the
   > dominant signal — severe/high usage means the account has structurally outgrown its plan), GTM team
   > scale & hiring (0–25), growth & funding (0–20), engagement & champion strength (0–20).
   >
   > Rules: use only the evidence provided; where a signal is missing, score that dimension
   > conservatively and say so in the rationale; **the four dimension scores must sum to the total**; set
   > `has_timing_signal` to Yes only if at least one holds — a GTM role posted in the last 60 days, a
   > funding event in the last 6 months, engagement status highly/moderately engaged, or usage pressure
   > high/severe — otherwise No; `fit_rationale` is 2–3 sentences naming the specific evidence used;
   > `why_now` is one sentence on the timing hook or exactly "No timing signal."

8. **Tier & Priority** — deterministic code. This is where fit becomes a tier, and it is deterministic on
   purpose. **Recompute the total from the four dimension scores here** rather than trusting the model's
   addition — the model judges, the code adds:

   ```ts
   function tierAndPriority(r: Record<string, unknown>, cfg: { tier1_cut?: number; tier2_cut?: number }) {
     const n = (v: unknown) => { const x = Number(v); return Number.isFinite(x) ? x : 0; };
     const s = (v: unknown) => (v == null ? '' : String(v).trim());

     // deterministic total: sum the dimensions the model scored, don't trust its arithmetic
     const score = Math.round((n(r.motion_or_usage) + n(r.hiring) + n(r.growth) + n(r.engagement)) * 10) / 10;
     const timing = s(r.has_timing_signal).toLowerCase() === 'yes';
     const track = s(r.track) || 'New Business';
     const pressure = s(r.usage_pressure).toLowerCase();
     const pipeline = n(r.open_pipeline);

     // DECLARED INPUTS — tier cut-offs from the play input; the defaults are fallbacks, not literals.
     const tier1 = cfg.tier1_cut ?? 75, tier2 = cfg.tier2_cut ?? 60;
     let tier: string, tier_reason: string;
     if (score >= tier1 && timing) [tier, tier_reason] = ['Tier 1', 'Strong fit with a live timing signal'];
     else if (score >= tier1) [tier, tier_reason] = ['Tier 2', 'Strong fit but no timing signal — nurture until one appears'];
     else if (score >= tier2) [tier, tier_reason] = ['Tier 2', 'Moderate fit'];
     else [tier, tier_reason] = ['Tier 3', 'Weak fit on the evidence available'];

     const reasons: string[] = [];
     if (s(r.engagement_status).toLowerCase().startsWith('highly')) reasons.push('highly engaged in the last 90 days');
     if (pipeline > 0) reasons.push(`open pipeline of ${pipeline.toLocaleString('en-US')}`);
     if (pressure === 'high' || pressure === 'severe') reasons.push(`${pressure} usage pressure on the current plan`);
     const isPriority = tier === 'Tier 1' && reasons.length > 0;

     // Internal output keys — the WRITE step maps these to the installer's OWN property names.
     return {
       account_tier: tier, tier_reason,
       priority_account: isPriority ? 'Yes' : 'No',
       priority_reason: reasons.length ? reasons.join('; ') : 'none',
       fit_score: score, track,
       sort_key: score + (isPriority ? 1000 : 0) + (tier === 'Tier 1' ? 500 : 0),
     };
   }
   ```

9. **Write Scores to the CRM** — the CRM write tool, keyed on domain (HubSpot:
   `hubspot_batch_upsert_objects` with `object_type: companies`, `id_property: domain`; Salesforce:
   `salesforce_update_account` by record id read in step 1; Attio: `attio_assert_company_record` with
   `matching_attribute: domains`). **Drop null and empty values from the payload** so a blank result
   never overwrites existing data. **Map the internal outputs to the installer's OWN property names,
   never to properties named after this workflow:** `fit_score`, `account_tier`, `priority_account`,
   and `track` come from the tier step; `fit_rationale` and `why_now` come from the scoring step — each
   is written into the property the installer named in Declared inputs. Confirm those properties exist
   (`hubspot_fetch_properties` on HubSpot) and have the installer create them if not; do not invent
   property names of your own.

## Step 4 — Check and dry-run a small sample

`deepline plays check ./account-tiering.play.ts` (mandatory), then run it against a **small sample of
in-scope accounts** with the CRM write switched off (an `apply: false` input that skips step 9):
`deepline plays run --file ./account-tiering.play.ts --input '{...,"apply":false}' --debug`. Read the
payloads with `deepline runs get <run-id> --full --json` before the write goes wide: confirm each
enrichment returns the fields you read (completion status is never data — gate on non-empty values),
confirm the track resolves correctly for a known prospect and a known customer, and confirm the tier cut
behaves at the boundary (a ≥75 with no timing lands Tier 2, not Tier 1). Fix mappings here, where it is
cheap.

## Step 5 — First live batch, then go live  *(spend-approval + write-approval, one gate)*

Everything free has run. Now, in **one** message and then stop: the sample result, the **actual cost per
account** read from `deepline runs get <run-id> --full --json` billing (three enrichments + one scoring
call, with the per-result hiring step priced at the cap), the count of in-scope accounts currently in
the segment so the total is a real number and not a guess, exactly what will be written and where, and
the ask. On yes, run the first live batch with `apply: true` (the sample's accounts, written for real),
report actual spend against the estimate, then `deepline plays publish ./account-tiering.play.ts` so the
cron or webhook trigger goes live, and set `billing.maxCreditsPerRun` in the play options as a ceiling.
Add a failure notification rule for `play.cron.failed` (`deepline notifications configuration get`,
add the rule, then `deepline notifications configuration apply <file>`) so a broken trigger is not silent. **Re-read the balance after the batch (`deepline billing balance`) and report the
real figure** — an estimate never reconciled is how an overrun goes unnoticed. From then on it bills per
account entering the segment; say that plainly, because a standing trigger is a standing cost.

## What this skill does not claim

- It does not measure whether an account is a good fit — it scores the *evidence available*, and the
  most fit-predictive signal (the tech stack) is empty on most accounts, so a low score often means thin
  data, not a bad account. The rationale says which dimensions were unobserved; read it before acting.
- The tier cut-offs, usage-pressure thresholds and dimension weights are the source workflow's values
  carried as editable defaults; none of them is validated against an outcome, and nothing re-checks a
  cut-off the installer re-tunes.
- Per-account credit and token cost are not quoted as fixed here — they are read from `describe` at
  build time and reconciled after the first batch. The one structural cost fact carried is that the
  hiring step bills per returned posting.
- This port has not been run end to end on Deepline; the source workflow ran on Clay.
- `has_timing_signal` is produced by the scoring model from the evidence it was given; if an enrichment
  silently returned empty, a real timing signal can be missed and the account under-tiered.

## What good looks like

- A rep can answer "why is this account Tier 1?" from the record alone — score, the four dimension
  scores in the rationale, the tier reason, and the why-now — with no black box.
- Re-tuning a cut-off is a one-line change to the play input, not a rebuild.
- A ≥75 account with nothing happening reads as Tier 2 with "nurture until a signal appears," not as a
  missed Tier 1 — and the installer can see it was fit, not the pipeline, that held it back.
- The common mistake this avoids: letting the scoring model also do the tiering and the arithmetic, so
  the cut drifts run to run and the total does not equal its parts.

## Rules

- MUST keep the tier cut and the total in deterministic code; the model produces dimension scores and
  prose, never the tier and never the sum.
- MUST filter on the in-scope rule before any paid step so out-of-scope accounts cost nothing.
- MUST resolve every step by its full Deepline tool ID against `deepline tools describe`, and price the
  hiring step at its per-result cap.
- MUST gate the build behind write-approval and the first live run behind one spend-and-write approval
  that names the cost and the write together; reconcile actual spend afterwards.
- MUST score prospects and expansion candidates on their own rubric, chosen deterministically by plan
  before any judgment runs.
- NEVER contact anyone, delete or blank a field, or move account data anywhere but the CRM.
- NEVER score a dimension whose input was unobserved as zero — leave it out and say so in the rationale.

## Worked example

A team selling a GTM data platform points the play at their "Target Accounts" HubSpot list and maps
domain, company LinkedIn URL, plan, acquisition type, and a workspace-count usage property. In-scope
rule: prospects, plus customers on the "Pro" plan. The build is one play on a weekday cron; the dry run
on eight accounts shows the tech-stack lookup empty on seven of them (expected) and the tracks resolving
correctly. The go-live gate reports per-account cost (0.43 tech + ≤0.2 hiring at cap + 0.8 profile +
the measured scoring call) and 412 in-scope accounts in the list; the team approves. First batch: a prospect running a full outbound stack with three RevOps roles posted lands
**New Business · 82 · Tier 1 · Priority** (live hiring signal); a Pro customer on 24 workspaces lands
**Expansion · 88 · Tier 1 · Priority** (severe usage pressure); a strong-fit prospect with a stale last-
signal lands **New Business · 77 · Tier 2** — fit without timing. The play is published; new accounts
entering the list are scored automatically from then on.
