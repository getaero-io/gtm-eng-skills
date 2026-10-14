# The runner, and the traps that shape it

Every rule here exists because breaking it cost a real debugging session. None of them is
obvious from the outside, and several fail *silently* — which is why they are written down
rather than left to be rediscovered.

## One record

```
intake ──> for each leg in order:  need_<key>? ──yes──> call provider ──┐
                                               └─no────────────────────┴──> resolve
       ──> emit ──> (callback POST, if the record carries callback_url)
```

| Step | Does |
|---|---|
| `intake` | normalises the interface (domain stripped to host, name split), stamps provenance `supplied` / `unknown`, computes every `need_<key>` |
| call | one `deepline tools execute`, `deepline plays run`, or `generic_http_request` — only when `need_<key>` is true |
| `resolve` | merge supplied-vs-found, label provenance, recompute every `need_<key>`, return the record |
| `emit` | build the output contract by exclusion, verification and domain-match reporting |

The handlers are Python generated from templates in `cascade.py` and compiled at start-up, so
`test_codegen.py` can parse and run exactly the code the runner executes.

## The carry contract

**Every `resolve` returns the COMPLETE record**, not just its own field. That is why adding a
provider is an append rather than a rewrite: a leg reads the record and nothing else.

It also means **`need` is recomputed after every leg.** This is the mechanism that makes several
legs on one field into a waterfall with no extra machinery: a later leg's `need` is false the
moment an earlier leg filled the field. The same recompute rebuilds every http leg's request
body, so a body can reference a field an earlier leg resolved.

## `requires` — skip, do not fire empty

A leg runs only when the caller wants it, the field is still missing, AND every field in
`requires` is populated. Required provider inputs reject an empty value, and a call that fails
spends nothing useful and looks like a miss. So a leg whose input never arrived **skips** and
reports `blocked_missing_input`. `--dry-run` refuses a config where a field mapped to a required
Deepline input is missing from `requires`.

## Enablers fire on demand

A leg whose field another leg `requires` is eligible whenever that consumer is still wanted and
still empty — flag or no flag. Without that clause every leg keyed off the pivot reports
`blocked_missing_input` and the cascade quietly does nothing.

## Scan, don't pin, the response

`resolve` walks an ordered list of candidate paths and takes the first non-empty,
non-sentinel value. **This is deliberate and it is not defensive programming.** A wrong
pinned response path resolves to null, which reads as "not found" — a genuine miss and a
mis-wired path look identical, so the bug survives review and shows up as a bad hit rate
months later. A scan either finds the value or genuinely did not get one.

The same reasoning covers sentinels: a provider returning the literal string `n/a` has not
found anything, and treating it as a value poisons the record and every count built on it.

Where the value sits differs per provider type: a `deepline_tool` answer is the provider's raw
payload; a `deepline_play` answer is the play's output object, located by the `required` keys of
its `outputSchema`; an `http` answer is `generic_http_request`'s envelope with the provider body
under `data`.

## Attribution must not be overwritten

When several legs fill one field, every later leg sees the value already present. Labelling
it `supplied` at that point erases which provider actually found it — and with it any
ability to judge provider hit rates, which is the entire reason for running a waterfall.
So a leg only sets `supplied` when the existing provenance is empty or `unknown`.

This was a live bug, not a hypothetical.

## A failed call is not a miss

A provider call that errors (a `401`, a timeout, a bad input) resolves the field as `not_found`
so the record still completes — and the error is kept in `leg_errors` beside it. Without that, a
wrong key reads as a provider with no data, and the fix (the key) is never looked for.
`--report` counts rows with a leg error; read them before trusting a `not_found`.

## Credentials

**The config never holds a key.** An http leg names an environment variable (`key_env`) and a
header (`key_header`, `key_prefix`); the runner reads the variable at call time, puts it in that
one header, and nowhere else. `validate` refuses a credential-shaped config field or header name,
and the retired credential keys fail loudly. Payloads go to the CLI through a temp file
(`--input @file`), so neither a record nor a key lands in a process listing.

`generic_http_request` requires `https` for auth-like headers and redacts reflected values from
its result.

## Output by exclusion

The record in transit carries machinery: per-leg request bodies, `need_*` gates. None of that is
the deliverable, and a callback that POSTs it ships the runner's internals to somebody else's
endpoint. So `emit` builds the contract by exclusion — no `_`-prefixed key, no `need_*`, no
`<field>_source` for a field with no leg — and that is what `record_json` and the CSV carry.

## Verifying before you spend

`scripts/test_codegen.py` generates every handler, parses it, runs it against a fake context,
then runs whole records through `run_record` against a fake Deepline — no credentials, no
network, no cost. Run it after changing a config or the runner. A syntax error or a leftover
substitution marker otherwise produces a runner that starts fine and dies on every row.

`cascade.py --dry-run` then validates every Deepline leg against the live schema (free).
