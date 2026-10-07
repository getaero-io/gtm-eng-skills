---
name: deepline-quickstart
description: 'Run a quick Deepline demo with a maintained Play.'
disable-model-invocation: false
---

# Deepline Quickstart

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

Use the current Plays workflow for quick demos. Do not use the retired CSV
enrichment command or its flags.

## Single record

1. Ask which field the user wants to enrich and what identifiers they have.
2. Search for a maintained Play and inspect its input and output contract:

   ```bash
   deepline plays search email --json
   deepline plays describe prebuilt/<play-from-search> --json
   ```

3. Confirm the user wants to spend credits, then pilot one real record:

   ```bash
   deepline plays run prebuilt/<play-from-search> \
     --input '{"linkedin_url":"https://www.linkedin.com/in/example/"}'
   ```

4. Report the run result and the exact next step. Do not claim an output file
   exists unless one was written.

## CSV

Inspect the file and choose a batch Play whose input schema matches its
columns. Run a representative pilot before the full file:

```bash
deepline plays search email --json
deepline plays describe prebuilt/<batch-play-from-search> --json
deepline plays check prebuilt/<batch-play-from-search> --json
WORKDIR="deepline/data/quickstart-pilot" && mkdir -p "$WORKDIR"
head -n 4 leads.csv > "$WORKDIR/leads-pilot.csv"
deepline plays run prebuilt/<batch-play-from-search> --csv "$WORKDIR/leads-pilot.csv"
deepline runs export <run-id> --out "$WORKDIR/leads-pilot-enriched.csv"
```

Wait for a terminal run result before exporting. Review row alignment and
results before asking whether to process the rest of the file. Never substitute
a scalar Play for a batch Play unless its contract explicitly accepts rows.
