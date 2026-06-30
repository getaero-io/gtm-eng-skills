---
name: deepline-quickstart
description: 'Run a quick Deepline demo recipe to show the user how Deepline works.'
disable-model-invocation: false
---

# Deepline Quickstart

Run a high-confidence demo recipe to show the user what Deepline can do. Pick the most relevant recipe below, or default to Recipe 1 if no context is given.

**Always prefer the hardcoded recipes below.** `/deepline-gtm` is always available as a fallback but should only be used if: (a) a recipe command fails and all fallbacks are exhausted, or (b) the user's ask doesn't match any recipe here. Never invoke it preemptively.

## Execution flow

Follow this pattern for every recipe:

1. **Tell the user what you're about to do** — explain the goal and which data source(s) you'll use, before running anything.
2. **Run the recipe directly.** For this default quickstart, do not spend time on separate session/progress commands; they do not improve the demo.
3. **Tell the user the results** — summarize what came back, where it came from, and the exact CSV path they can inspect next.

### CLI surface

This quickstart needs to be fast. Do not run `deepline --version`, `deepline auth status`, or separate CLI discovery commands on the fast path. Use the SDK CLI `deepline enrich` shape with `--name quickstart-ny-cto-email` and the hyphenated `person-linkedin-to-email` prebuilt id. If a retry needs command-shape confirmation, use `deepline --help` or `deepline enrich --help`.

## Recipe 1 — Find CTOs at NY startups

**Goal:** Find 5 CTOs at startups in New York with verified emails and LinkedIn profiles.
**Data sources:** Dropleads (people search) + waterfall email enrichment via `person-linkedin-to-email`.

**Steps:**

1. Search Dropleads for CTOs in New York
2. Waterfall enrich emails
3. Display results

### Fast path

For the default quickstart, run this whole block as one Bash call. Do not split it into separate tool calls. Do not inspect the JSON, run `csv show`, print the CSV with Python, or run extra validation after the enrich command; those checks make the quickstart miss the one-minute budget.

```bash
set -e
mkdir -p deepline/data

deepline tools execute dropleads_search_people --json --payload '{
  "filters": {
    "jobTitles": ["CTO"],
    "personalStates": {"include": ["New York"]},
    "employeeRanges": ["1-10", "11-50", "51-200"]
  },
  "pagination": {"page": 1, "limit": 5}
}' > deepline/data/quickstart_search.json

python3 - <<'PY'
import csv, json
d = json.load(open("deepline/data/quickstart_search.json"))
leads = (
    d.get("result", {}).get("data", {}).get("leads")
    or d.get("toolResponse", {}).get("raw", {}).get("leads")
    or d.get("leads")
    or d.get("output_preview", {}).get("preview")
    or []
)
if not leads:
    raise SystemExit("No Dropleads leads returned")

with open("deepline/data/quickstart_ny_ctos.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["first_name", "last_name", "company", "title", "linkedin_url"])
    w.writeheader()
    for r in leads[:5]:
        url = (r.get("linkedinUrl") or r.get("linkedin_url") or "").strip()
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        w.writerow({
            "first_name": r.get("firstName") or r.get("first_name") or "",
            "last_name": r.get("lastName") or r.get("last_name") or "",
            "company": r.get("companyName") or r.get("company") or "",
            "title": r.get("title") or "",
            "linkedin_url": url,
        })
PY

deepline enrich --input deepline/data/quickstart_ny_ctos.csv --output deepline/data/quickstart_enriched.csv --name quickstart-ny-cto-email --all \
  --with '{"alias":"email","tool":"person-linkedin-to-email","payload":{"linkedin_url":"{{linkedin_url}}"}}'
```

### Step 1 — Search

Only use the detailed steps below if the fast path fails.

```bash
deepline tools execute dropleads_search_people --payload '{
  "filters": {
    "jobTitles": ["CTO"],
    "personalStates": {"include": ["New York"]},
    "employeeRanges": ["1-10", "11-50", "51-200"]
  },
  "pagination": {"page": 1, "limit": 5}
}'
```

Note the output CSV path from the result.

### Step 2 — Waterfall enrich emails

First, make sure the CSV has plain string columns named `first_name`, `last_name`, and `linkedin_url`. If the Dropleads result uses `fullName` and `linkedinUrl`, normalize those columns locally instead of running a separate Deepline enrichment pass; this quickstart should spend paid work only on the email waterfall. Use full `https://www.linkedin.com/in/...` URLs.

Then run the waterfall:

```bash
deepline enrich --input <normalized_csv> --output <enriched_csv> --name quickstart-ny-cto-email --all \
  --with '{"alias":"email","tool":"person-linkedin-to-email","payload":{"linkedin_url":"{{linkedin_url}}"}}'
```

Report the output CSV path after this step.

### Step 3 — Display results

After the fast path finishes, do not run another command just to display rows. Tell the user the enriched CSV path and that emails were filled via the dedicated LinkedIn-to-email waterfall. Mention they can go deeper — phone, firmographics, job change signals — with `/deepline-gtm`.

### Fallback (if Step 1 errors)

Tell the user, then try Dropleads:

```bash
deepline tools execute dropleads_search_people --payload '{
  "filters": {
    "jobTitles": ["CTO", "Chief Technology Officer"],
    "personalCountries": {"include": ["United States"]},
    "personalStates": {"include": ["New York"]},
    "personalCities": {"include": ["New York"]}
  },
  "pagination": {
    "page": 1,
    "limit": 5
  }
}'
```

### Last resort

If all commands fail, tell the user, then invoke `/deepline-gtm`:

> Find 5 CTOs at startups in New York with their emails and LinkedIn profiles.
