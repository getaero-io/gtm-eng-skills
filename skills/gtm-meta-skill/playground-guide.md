---
name: deepline-playground
description: "Playground-only CLI reference for running and inspecting CSV enrichment blocks."
---

# Deepline CSV Playground Guide (Commands Only)

Use this document for operations that interact with `deepline csv` directly.

## 1) Open an existing CSV in Playground

```bash
deepline csv render --csv leads.csv --open
```

- Use `--open` to launch the UI.

## 2) Inspect rows (`deepline csv show`)

`deepline csv show --csv <path> [--format json|table|csv] [--verbose] [--summary] [--rows START:END]`

- format: json (default, `{rows, _metadata}`), table (ASCII, 40-char cap), csv (RFC 4180)
- --verbose: include step columns + full cell values
- --summary: per-column stats + miss_reasons
- --rows: `start:end` bounds (default `0:19`)

```bash
deepline csv show --csv leads.csv
deepline csv show --csv leads.csv --format table --rows 0:10
deepline csv show --csv leads.csv --summary
```

## 3) Re-run a playground block

```bash
deepline csv --execute_cells --csv leads.csv --rows 0:10 --cols 9:9 --wait
```

- `--cols` is the column index range to re-run (`N:N` for one column).
- Keep `--rows` explicit.
- Use `--wait` when you need completion before the next command.

## 4) CLI-only debug posture

- If you need to inspect or re-execute, use these playground commands directly.
- If you need to add columns or add providers, switch back to `deepline enrich` workflow docs instead of extending this page.
