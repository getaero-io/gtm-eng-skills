# The play, step by step, and the traps it avoids

Built by `scripts/build_workflow.py`: it renders `person-active-at-company-jev.play.ts` into this
skill's state folder, runs `deepline plays check` on it (free), and on approval
`deepline plays publish`. Re-running publishes a new revision under the same name; there is
nothing to adopt or clean up.

## "person-active-at-company-jev" (CSV, rows, webhook)

```
input: {"csv": "people.csv"} | {"rows": [...]} | one record (a webhook POST body is the input verbatim)
  → now (ctx.step)                 the run's clock, checkpointed once; every date in the verdict code
                                   counts from it
  → records (dataset)              one row per person
  → found (tool column)            crustdata_v3_person_enrich {professional_network_profile_urls: [url],
                                   fields: ["basic_profile", "experience"]}, ONLY when intake() says the
                                   person has a LinkedIn profile URL and no usable profile (or one older
                                   than max_profile_age_days) and skip_enrichment is not true. A failed
                                   purchase returns {_enrich_error}, which reads as no work history
  → jev (tool column)              prepare() picks the profile (bought, else supplied), finds the
                                   candidate roles and builds the one ai_evaluate request. Nothing to
                                   ask: no call, no cost. A thrown tool error is caught and handed on
                                   as {status, category, message}
  → verdict (code column)          verdict(): every output key, always present
  → one column per output key      active_at_company, relationship, … checked_at, so
                                   `deepline runs export <run> --dataset result.records` is a flat CSV
```

Calling it:

- **A file:** `deepline plays run --name person-active-at-company-jev --input '{"csv":"people.csv"}'`,
  then `deepline runs export <run-id> --dataset result.records --out verdicts.csv`. Column names
  must be the inputs' own names (rename them in the CSV first; `check_local.py --show-map` shows
  which column is which).
- **Anything that can POST:** the webhook URL from the publish output (`triggerBindings[].endpointUrl`),
  body = one record. The response is `202 {event_id, run_id}`; read the verdict with
  `deepline runs get <run_id> --json` or export it. Send a stable `x-deepline-dedupe-key` per
  person if a sender may retry.

## Traps

- **`plays check` rejects `Date.now()` outside a `ctx.step`**: a replayed run would see a different
  clock. The verdict code reads `NOW_MS`, set once from `ctx.step('now', …)`; the local preview sets
  it from the machine's clock.
- **A local variable named `ctx` inside the play is read as the play context** by the checker
  (`ctx.map(...)` is flagged as the removed API). The verdict code calls its own `cur_ctx`.
- **The verdict code is plain JavaScript under `// @ts-nocheck`**, so the identical text runs under
  `node` for the preview and the offline tests. The play's own wiring is still typechecked
  against the SDK by `plays check`.
- **A tool's output is read at `toolResponse.rawV2`** (`.data` when `view` is `data`); the
  verdict code also accepts the envelope one level down, because neither shape was observed
  live for this skill.
- **A failed Jev call is caught, never retried by the play**, and comes back `failed` with the
  reason (rate limit, billing, upstream). Re-run those rows.
- **The dataset table name is "<play name>_records"** and must stay under 63 characters, so the
  play name is short and fixed.
- **A named play run uses the live (published) revision.** `plays run --file` runs a local draft
  without publishing; the smoke test runs `--name` so it proves what callers get.
