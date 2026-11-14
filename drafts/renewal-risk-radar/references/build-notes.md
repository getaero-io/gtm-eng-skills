# Build notes — CRM intake, the weekly play, and per-signal routing

Mechanics only. The decisions live in `SKILL.md`; this file is what to type and what has bitten
builds before. Everything here is a starting point to **re-verify** against the installed CLI version
(`deepline tools describe <id> --json`), never a substitute for the live pull.

## Asking which CRM without demanding a recital

A skill authenticated to a CRM can usually **read** that CRM's shape, so do not ask the installer to
type field names from memory. The flow:

1. **Name the shape** — the four fields in `SKILL.md` Step 1 (account id+name, renewal date, owner,
   champion contact), each with what it is for.
2. **Read their system.** Ask which CRM they run (a trigger phrase, not a dependency — this skill is
   CRM-agnostic), then read the account object's schema through the connected account. All of these
   are free reads:

   | CRM | Schema read | Record read |
   |---|---|---|
   | HubSpot | `hubspot_fetch_properties` (`name`: object type) | `hubspot_search_objects` (`object_type`, `filter_groups`, `properties`) |
   | Salesforce | `salesforce_fetch_fields` (`name`: object) | `salesforce_list_accounts`, `salesforce_list_contacts`, `salesforce_get_record` |
   | Attio | `attio_list_attributes` | `attio_query_company_records` (`filter`) |

3. **Show the mapping you found** — which of their fields you matched to each row, and which you could
   not.
4. **Ask only about the unmatched rows**, and gate the judgment calls (windows, rules, model) that no
   schema can answer.

Where the CRM is not connected in Deepline, ask for an export CSV, inspect it with
`deepline csv show --csv <path> --summary`, and map from that — still far better than a vague "tell
me your fields". Never let the input degrade into a loosely-worded request; that just moves the guess
somewhere nobody can see it.

The champion is the field most often *not* a field: it may be a contact **role** on the account, a
tag, or a named person. Read how they record it; if nothing records it, the champion-change signal is
`unmeasured` for those accounts and the digest says so.

## The weekly play — shape and the traps

Read `recipes/deepline-plays.md` in the `deepline-gtm` skill before authoring, then:

```
deepline plays check renewal-risk-radar.play.ts
deepline plays run --file renewal-risk-radar.play.ts --input '{...}' --debug   # 10-row pilot
deepline runs get <run-id> --full --json                                      # per-step outcome + billing
```

Shape, left to right:

```
cron binding (weekly, static input: CRM object, renewal field, window days, rules)
  → CRM read + scope the book to the renewal window (drop out-of-window/renewed)            [free]
  → per account, three signal columns (.withColumn each)                                   [paid]
  → combine signals + rank in play code (all judgment lives HERE, never deeplineagent)      [free]
  → return the dataset (Customer DB table + CSV export) (+ optional slack_post_message)    [no CRM write]
```

Design around these, do not discover them:

- **Every signal column emits a value.** An account with no champion still gets an explicit
  `unmeasured` cell, so the combine step never has to guess whether a blank means "no risk" or "not
  run".
- **Carry account fields forward explicitly.** Keep account id, renewal date and owner as columns on
  the row rather than reading them back out of a tool's response; tool responses do not echo inputs
  reliably.
- **A cron trigger receives `{}` unless its binding declares `input`.** Put every scheduled argument
  in the binding's static JSON `input`; it is pinned to the published revision.
- **Read declared getters first** (`extractedValues.*.get()` / `extractedLists.*.get()`); fall back to
  the raw tool response only for fields no getter exposes.
- **Watch a broken schedule.** After publishing, add a notification for `play.cron.failed`
  (`deepline notifications add ... --for play.cron.failed`) so a silent failed Monday is seen.

Idempotency: on the stateless (recent-window) model a re-run recomputes and overwrites the week's rows
— safe. On the stateful (compare-to-last-week) model you must persist last run's per-account snapshot
(the play's Customer DB table, keyed on account id) and read it back; handle a skipped run (a two-week
gap must not read as "no change") and a duplicated run (do not double-count). Diff on the
**provider's signal date**, not the run date.

## Per-signal routing — resolve names and costs live

For each signal, confirm the tool ID with `describe`, read the input schema, and record: what runs,
what goes in, what to verify, what it costs. Read `pricing.unit` before the rate; budget for billed
misses (a call can succeed with an empty payload and still bill). Prices below are Deepline list
prices at the time of writing.

| Signal | Tool (starting point) | Input (declared) | Verify in response | Cost note |
|---|---|---|---|---|
| Champion changed employer | `job_change` (or batch via `prebuilt/job-change-check`); standing alternative `deepline_native.contact_job_changes` monitor | champion LinkedIn URL / email / name + account domain | status "moved"; new employer ≠ account; carry the provider's change date (`job_change.date` on the prebuilt); if no champion → `unmeasured` | 1.96 credits/result; the monitor is 3.5 credits per contact per month, recurring |
| Headcount fell | `crustdata_v3_company_enrich` with `fields: ["headcount"]`; `akta_headcount_trends` (`company`) for a history series | account domain | both current and trailing figures present (null horizon ≠ 0); numeric compare; prefer an exact count over a band string; check the growth field names in the first response | 0.8 credits/result; akta is calculated from usage |
| Company went quiet | `predictleads_company_news_events` (`found_at_from`), `predictleads_company_job_openings` (`first_seen_at_from`), `harvestapi_get_company_posts` (`postedLimit: "month"`), `contextdev_post_news_search` (`filterBy.date`) | account domain (LinkedIn company URL for posts) | "no activity found" ≠ "arm returned nothing"; date the last activity | 0.56 / 0.56 credits per call, 0.03 per page, free; waterfall the boolean + evidence only, never the count you rank on |

Route by the input the installer holds (a domain vs a contact), not by what a lookup returns — that
keeps the build deterministic. Fail loudly when a named tool is absent (`describe` errors); never
silently substitute the nearest arm — a substituted liveness probe fills every row and asserts dead
companies are alive.
