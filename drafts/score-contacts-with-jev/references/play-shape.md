# The play, step by step, and the traps it avoids

Built by `scripts/build_scorer.py` from the saved rubric, the column mapping the preview confirmed,
and the scoring code in `scripts/jev_lib.py` (`CORE`). The rendered file sits in the state folder
under `plays/`; `deepline plays check` must call it valid before anything is published.

## "jev-lead-score-<accounts|contacts>-<rubric>"

```
input: {"csv": "file.csv"} | {"rows": [ {...}, … ]} | one record (a webhook POST body, verbatim)
  → clock          ctx.step('now'): one checkpointed timestamp for date rules and scored_at
  → records        dataset, one row per record
      → jev        pick (the rubric's own keys first, then the mapped column) → intake: every rule
                   worked out, which questions have the data they read, the one request.
                   Nothing to ask (required input missing, a rule disqualified it, no question had
                   its data) → null, no call, no cost. Otherwise one ai_evaluate call; a tool error
                   is caught and kept as {status, category, message}
      → verdict    score: every output key, always present
      → lead_score, lead_tier, … one column per output key, so an export is a flat CSV
  → returns {records}
```

How it is called:

- **A file:** `deepline plays run <play> --input '{"csv":"accounts.csv"}'`, then
  `deepline runs export <run-id> --dataset result.records --out scored.csv`. The CLI stages the
  local file. Columns are read by the rubric's input names first, then by the mapping baked in at
  build time, so the same CSV layout the preview used works as it is.
- **Rows from another script:** `{"rows": [...]}` with the same keys.
- **One record from another system:** POST the record as the body to the webhook URL
  (`triggerBindings[].endpointUrl` from `deepline plays publish --json`). The response is `202`
  with a `run_id`; the score is in that run (`deepline runs get <run-id> --json`, or export).

## Traps, each of which fails silently or fails the check

- **One source for the scoring code.** The play embeds `CORE` verbatim; the preview and
  `test_offline.py` run the same text under `node`. Never hand-edit the rendered play: change the
  rubric, preview, rebuild.
- **No wall clock in play code.** `Date.now()` is not replay-safe in a durable play and fails
  `plays check`. The play reads the time once in `ctx.step('now', …)` and the code uses that
  (`NOW_MS`); dates are counted by calendar arithmetic, never parsed with `Date`.
- **`// @ts-nocheck` on the generated file.** The scoring code is plain JavaScript shared with
  node; the play's own SDK calls are still bundled and checked by `plays check`.
- **Read the tool output from `toolResponse.rawV2`** (`.rawV2.data` when `view === 'data'`).
  `toolResponse.raw` is the legacy projection and `plays check` warns on it. `score()` also
  unwraps one `data` level, so either shape scores the same.
- **A failed Jev call is data, not a score.** The `jev` column catches the tool error for that
  record only; `score()` turns it into `failed` with the reason. A batch never stops on one
  record, and a failure is never a zero.
- **A webhook runs the PUBLISHED revision.** `deepline plays run --file` runs a local file without
  publishing it; the build publishes, and the smoke test runs the play by name (the live revision).
- **Publish what was checked.** The build passes `--expected-artifact <hash from plays check>` to
  `plays publish`, so bytes changed after the check are refused.
- **A changed rubric is a new revision of the same play name.** Results carry `rubric` as
  `name vN`, so scores from two versions are never silently compared.
