---
name: deepline-quickstart
description: 'Run a quick Deepline demo with a maintained Play.'
disable-model-invocation: false
---

# Deepline Quickstart

## Quick Start

```bash
npm install -g deepline
deepline -h
```

Run quick demos with a maintained Play.

## Single record

1. Ask which field the user wants to enrich and what identifiers they have.
2. Search for a maintained Play and inspect its input and output contract:

   ```bash
   deepline search "<input you have -> result you need>" --type prebuilts
   deepline describe prebuilt/<play-from-search>
   ```

3. Show the `--dry-run` price, confirm the user wants to spend credits, then
   run the same command without `--dry-run` to pilot one real record:

   ```bash
   deepline run prebuilt/<play-from-search> \
     --input '{"linkedin_url":"https://www.linkedin.com/in/example/"}' --dry-run
   ```

4. Report the result, its cost, and the exact next step from the receipt. Do
   not claim an output file exists unless the receipt names one.

## CSV

Inspect the file and choose a batch Play whose input schema matches its
columns. Run a representative pilot before the full file, showing the
`--dry-run` price and confirming the spend before the paid run:

```bash
deepline search "<input you have -> result you need>" --type prebuilts
deepline describe prebuilt/<batch-play-from-search>
deepline plays check prebuilt/<batch-play-from-search>
WORKDIR="deepline/data/quickstart-pilot" && mkdir -p "$WORKDIR"
head -n 4 leads.csv > "$WORKDIR/leads-pilot.csv"
deepline run prebuilt/<batch-play-from-search> \
  --input '{"csv":"'"$WORKDIR/leads-pilot.csv"'"}' --dry-run
deepline run prebuilt/<batch-play-from-search> \
  --input '{"csv":"'"$WORKDIR/leads-pilot.csv"'"}' \
  --csv-out "$WORKDIR/leads-pilot-enriched-$(date -u +%Y%m%dT%H%M%SZ).csv"
```

Review row alignment and results before asking whether to process the rest of
the file. Never substitute a scalar Play for a batch Play unless its contract
explicitly accepts rows.
