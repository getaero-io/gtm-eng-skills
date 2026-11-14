# The ledger, the shards, and picking up where it died

A TAM load is long, interruptible, and duplicating ten thousand companies is not something anyone
gets to take back. So the design constraint is not throughput — it is that **the only state that
matters is on disk, and "what is left" is recomputed from it rather than remembered.**

## One line per row, written the moment its batch returns

The ledger is JSONL, append-only, never rewritten in place. Rows are written in batches — one
`INSERT … ON CONFLICT … RETURNING id, match_key` per batch, through `deepline db query` — and a line
per row goes down as soon as that statement returns, before the next batch starts. A batch is one
statement, so it is atomic: either its rows came back from `RETURNING` or none of them landed.

```
{"row_key":"northwind","status":"completed","entity_id":42,
 "match_key":"domain","match_value":"northwind.example","associated":null,
 "dropped_fields":["employee_count"],"reason":"","at":"2026-05-04T11:02:19Z"}
```

| Field | |
|---|---|
| `row_key` | the row's key in the file. The ledger is indexed on this |
| `status` | one of the five below |
| `entity_id` | the table's `id` that `RETURNING` handed back for this row's match key. **On companies this is the read-back** — the contacts load folds it into the `company_id` foreign key |
| `match_key` / `match_value` | which key this row was matched on, and with what. The table's `match_key` column holds `<match_key>:<match_value>` |
| `associated` | contacts only — `true`, `false`, or `null` on a company line |
| `dropped_fields` | values left out because their column could not parse them |
| `reason` | why, on a `rejected_*` or a `failed`; empty otherwise |

## Five verdicts, three of them settled

| Status | Settled | Meaning |
|---|---|---|
| `completed` | yes | the row's match key came back from `RETURNING` with an id |
| `rejected_no_match_key` | yes | the row carries none of the match keys. **Never sent** — screened in the driver |
| `rejected_duplicate_row_key` | no, deliberately | a second row with a row key already seen in this file. Written and counted, but never allowed to supersede what the real row did |
| `skipped_no_company` | yes | a contact whose company never loaded, under the flag that holds rather than loads such contacts |
| `failed` | **no** | the statement errored, or this row's key did not come back. Stays in the work set |

Two rules follow, and the second is the expensive one:

- **Only settled verdicts remove a row from the work set.** A re-run rewrites everything else, and
  because the write is an upsert on `match_key`, rewriting a row that did land costs nothing.
- **Do not "fix" a transient failure before retrying it.** A statement that timed out or hit a
  connection blip fails its whole batch at once and clears on its own. Read the `reason` before
  deciding it is not transient: a type error names the column and the value, and that one does need
  fixing at Step 3.

**A row that did not come back is `failed`, not `completed`.** `deepline db query` bounds the rows it
returns; if a batch is larger than what came back, the missing rows simply retry next pass. Settling
requires positive evidence.

## Recomputing what is left

```python
settled = {}
for line in open(ledger):
    try:
        r = json.loads(line)
    except ValueError:
        continue                     # a torn last line is normal after a kill
    if r.get("status") in SETTLED:
        settled[r["row_key"]] = r    # later lines supersede earlier ones
todo = [row for row in rows if row["row_key"] not in settled]
```

Three properties this relies on and one it tolerates:

- **Last line wins.** A row can legitimately settle twice — a forced re-run, a corrected export —
  and the later line is the current truth.
- **A torn final line is survivable.** A process killed mid-write leaves partial JSON; skipping an
  unparseable line costs one row, which the next pass rewrites.
- **The work set is derived, never stored.** There is no "remaining" file to fall out of sync.
- **A re-run over an untouched file writes nothing**, because every row is already settled. That is
  the test that the row key is stable — if a re-run creates records, the row key is not doing its
  job and the load should stop until that is understood.

## Batches and shards

**200 rows per INSERT, half a second between batches** (`--batch`, `--pace`). Neither number is
measured; they keep each statement and its `RETURNING` small. The loader also splits a batch where a
match key would repeat, because Postgres refuses an upsert that touches the same row twice in one
statement and that refusal fails the whole batch.

Concurrency, if a load needs it, is **process-based, over disjoint inputs**: `--shard i --of n` takes
a strided slice — `todo[i::n]` — so each shard owns rows no other shard touches, appends to a shared
ledger never collide on content, and no lock is needed. Start with one; a single process writing
batches is usually fast enough, and a rising failure rate is the signal to come down.

Detach so that a long load outlives the session that started it:

```
nohup python3 scripts/load_drive.py --entity companies … > logs/companies.log 2>&1 < /dev/null & disown
```

## The resume breadcrumb

The driver writes `RESUME.md` beside the ledger on start and rewrites it on exit. It holds four
things and no narrative:

1. **Where the state is** — the ledger paths, the mapping file, the build state.
2. **What is settled and what is left**, as counts by status, recomputed from the ledger at the
   moment it was written.
3. **The exact next command**, copy-pasteable, with every path filled in.
4. **What must not be repeated** — that the tables and columns exist, and that settled rows are
   never rewritten.

The bar it has to clear: someone opening a cold session, reading one file, and continuing without
asking anything. A breadcrumb that says "resume the load" and not which command has not cleared it.

## Two things a re-run must not do

- **It must not change the prefix.** `build-state.json` names the two tables. If it is gone, a build
  with the same `--prefix` is safe — every statement is `IF NOT EXISTS` — and rewrites it. A
  different prefix is a different pair of tables, and a contacts load against one with a company
  ledger from the other links to ids that are not there (the foreign key refuses it, loudly).
- **It must not widen the mapping without saying so.** A re-run with more columns than the first is
  a new set of columns and a different load. That is allowed; it is not allowed to be quiet.
