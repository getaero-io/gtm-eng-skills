# Durability: receipts, resume, row isolation

A play run is durable. Every tool call writes a receipt. Every filled cell is stored. A rerun re-pays only what changed. One bad row does not sink the run. The record is queryable after the fact. This page is what those claims cost in credits when measured on prod — not what the marketing says.

All numbers below are real runs against `code.deepline.com` on a 2-3 row CSV, July 2026. Verify them yourself; they will move as provider rates move, but the shape holds.

## Receipts make a rerun nearly free

A receipt is content-addressed on tool plus input. Same tool, same input, same receipt — no second charge. This is the single most important durability fact, so measure it before you trust it.

Measured, `name-and-domain-to-email-waterfall-batch` on 3 rows:

- **First run: 0.31 credits.** 3 leadmagic calls, 3 rows resolved, emails returned.
- **Rerun, identical input: 0.01 credits.** Same 3 emails. The 0.01 is the compute tick — the provider bill was zero.

That is a 31x drop, and the second run charged nothing to the provider. The run log still prints `Executing tool batch leadmagic_email_validation: 3 calls`, but the billing breakdown shows `providers: []` and `providerEvents: 0`. The calls resolved from receipts, not the provider.

Receipts are not scoped to a run. A third run over a **different** CSV that happened to share two rows with the first run also charged 0.01 — the two shared rows reused their receipts across runs. The cache is global to your workspace, keyed on tool and input, not on which run asked.

**What this means for how you work.** Do not hoard runs. Do not fear re-running. Grow a play one stage at a time and rerun constantly — the known-good prefix is already paid. When you sweep many providers on a small sample to pick the best route, the first sweep is real money and every rerun after is free. Measured on the route-fanout play, 2 rows across four routes (leadmagic, zerobounce, fullenrich): **first run 11.33 credits, rerun 0.01.** The expensive validators re-paid nothing the second time. Only the losing route's spend is ever wasted, and only once.

## Read the cost honestly

The reuse is real but the run-level counters lie about it. On the free rerun, `runs get --full` still reported `progress.reused: 0`, `executed: 3`, and every column `cached: 0`. If you trust those fields you would think the work re-ran. It did not.

The truth lives in two places, and only these two:

- **The billing breakdown.** `runs get <id> --full --json` → `billing.providerEvents` and `billing.breakdown.providers`. Zero provider events, empty providers array — nothing was bought.
- **The balance delta.** `billing balance --json` before and after. This never lies.

So when you want to know what a run actually cost, read the billing block or diff the balance. Do not read the `reused` / `cached` counters — on prod they under-report reuse to zero.

One more honesty note for composed plays. `runs get --full` reports the **parent** run's billing. A play that calls `ctx.runPlay` bills its children under child runs; `billingChildCredits` and `billingTotalCreditsRollup` roll them up, but the safe measure is still the balance delta across the whole run.

## Row isolation: one bad row does not sink the run

Give a run a blank or malformed row and the run still completes. The bad row isolates to itself; the good rows finish and their data persists.

Measured: a 3-row CSV with a completely blank middle row (no first name, last name, or domain — all required fields empty). Result:

- Run **status: completed**, not failed. `errors: []`.
- The dispatcher log shows `ready=2` and `Executing tool batch: 2 calls` — only the two valid rows went to the provider. The blank row was never dispatched.
- Export shows all three rows in order. The two valid rows carry their emails; the blank row is present with an empty email. Nothing was lost, nothing was faked.

You do not have to pre-clean a CSV to avoid a failed run. A junk row costs you that row, not the batch. Bad rows show up in the export as blanks with a `miss_reason` when the play sets one, so you can find and fix them without re-running the rows that worked.

## Resume: a rerun continues from completed work

Because receipts and filled cells survive, a rerun is a resume. Edit a play, add a stage, rerun — the completed prefix is already stored and re-pays nothing. A run that half-finished and a run you edited both continue from the last durable checkpoint rather than starting over. This is the same mechanism as the cache; there is no separate resume switch. The evidence is the same evidence: the second run bought nothing it had already bought.

## What `runs get` and `runs export` give you

The durable record is queryable after the run ends. You do not have to keep the terminal output.

`deepline runs get <id> --full --json` returns:

- `status`, `errors`, and per-node progress (which stage ran, how many rows completed / failed).
- `billing` — total credits, provider events, and a per-provider, per-operation breakdown. This is your real cost.
- `dataset_execution_stats` — per-column completed / failed / cached counts for the runtime sheet.
- `resultView` — the datasets the run produced, each with a row count and the exact export command.

`deepline runs export <id> --dataset <name> --out file.csv` writes a dataset to CSV. The dataset names are `result.rows`, `result.ledger`, and so on — if you guess wrong, the error message prints the available names and the exact command to use. The export preserves your source columns and adds the resolved ones (email, source, validated, and any per-route ledger columns).

Everything a run produced is addressable by run id after the fact — rows, ledger, billing, status. The run is a record, not a transcript.

## Friction worth knowing

- **`runs get` progress counters under-report reuse.** Covered above. Read billing, not `reused`/`cached`.
- **Piped JSON carries a resolver preamble.** `bunx deepline@latest ... --json` prints a couple of dependency-resolution lines before the JSON. Strip everything before the first `{` (or `[`) before parsing.
- **The cache is trust, so keep keys stable.** Reuse keys on tool plus input. Rename a column or change an input and you change the key, which re-pays. That is correct — the input changed — but it is why the discipline is one play file edited in place, not `-v2` / `-final` variants that quietly break reuse.
