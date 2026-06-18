---
name: deepline-plays-quickstart
description: 'Run a quick Deepline demo recipe on the V2 CLI using prebuilt plays.'
disable-model-invocation: false
---

# Deepline Plays Quickstart

Run a high-confidence demo recipe to show the user what Deepline can do, using the V2 CLI surface: `tools execute`, `plays run`, and `runs export`. Pick the most relevant recipe below, or default to Recipe 1 if no context is given.

**Always prefer the hardcoded recipes below.** `/deepline-plays` is always available as a fallback but should only be used if: (a) a recipe command fails and all fallbacks are exhausted, or (b) the user's ask doesn't match any recipe here. Never invoke it preemptively.

## Execution flow

Follow this pattern for every recipe:

1. **Tell the user what you're about to do** — explain the goal and which data source(s) you'll use, before running anything.
2. **Run each step**, narrating briefly between commands. Use `--json` so you can parse results, and `--watch` on `plays run` so the run streams to completion.
3. **Export results** with `deepline runs export <run-id> --dataset result.rows --out <file>.csv` after any play run that produces rows.
4. **Tell the user the results** — summarize what came back in a table, where it came from, and what they can do next.

### V2 command notes

- `deepline plays run` always with `--watch --json`; the final JSON includes `runId` and `status`.
- `deepline runs export` may report multiple datasets; pass `--dataset result.rows` for row output.
- `deepline runs get <run-id> --full --json` shows billing (calls, Deepline credits) and the full result, including scalar outputs that the compact view omits.
- Do NOT use `deepline session ...` (v1-only) or `deepline enrich --in-place` (unsupported on V2).

---

## Recipe 1 — Find CTOs in New York with verified work emails

**Goal:** Find 5 CTOs at startups in New York with verified work emails and LinkedIn profiles.
**Data source:** Dropleads people search for the contact list, then Deepline's multi-provider email waterfall for missing work emails.

Substitute the titles/locations from the user's request; keep the row count at 5 unless asked otherwise.

Speed matters more than completeness here: the user should see real contacts quickly. Run the commands below with minimal extra inspection.

### Step 1 — Search people

```bash
deepline tools execute dropleads_search_people --payload '{
  "filters": {
    "jobTitles": ["CTO", "Chief Technology Officer"],
    "personalCountries": { "include": ["United States"] },
    "personalStates": { "include": ["New York"] },
    "personalCities": { "include": ["New York"] }
  },
  "pagination": { "page": 1, "limit": 5 }
}' --output-format csv_file --no-preview --json
```

### Step 2 — Fill emails

Prepare a CSV with `first_name`, `last_name`, and `domain` columns from the people-search result, then run:

```bash
deepline plays run prebuilt/name-and-domain-to-email-waterfall-batch --input '{"csv":"<prepped csv>"}' --watch --json
```

### Step 3 — Export and display

```bash
deepline runs export <run-id> --dataset result.rows --out quickstart-contacts.csv
```

Show a table: `full_name`, `company_name`, `work_email`, `linkedin_url`. The `work_email` column is the final answer.

### Step 4 — Wrap up

Tell the user the flow searched people, then ran a per-row email waterfall. `deepline runs get <run-id> --full --json` shows exactly what the run billed, and they can go deeper — phone numbers, job-change signals, company discovery — with `/deepline-plays`.

### Fallback (if the play fails)

Tell the user, then run `/deepline-plays` with the same goal.

### Last resort

If all commands fail, tell the user, then invoke `/deepline-plays`:

> Find 5 CTOs at startups in New York with their verified work emails and LinkedIn profiles.

---

## Recipe 2 — Build a company target list

**Goal:** Find 5 companies matching a profile (category, size, funding, country) with domains and fit evidence.
**Data source:** the `prebuilt/structured-company-discovery` play.

### Step 1 — Run discovery

```bash
deepline plays run prebuilt/structured-company-discovery --input '{
  "target_count": 5,
  "hq_country": "USA",
  "categories": ["financial technology", "fintech"],
  "employee_count_min": 10,
  "employee_count_max": 200
}' --watch --json
```

Adapt `categories`, employee range, and `funding_rounds` (e.g. `["series_a"]`) to the user's ask. Location granularity is country-level (ISO-3); if the user needs city-level targeting, use Recipe 1's people search instead.

### Step 2 — Export and display

```bash
deepline runs export <run-id> --dataset result.rows --out target-companies.csv
```

Show: company name, domain, headcount, funding round, HQ, fit evidence. Suggest the natural next step — finding the right contact at each company with verified emails (Recipe 1's waterfall, or `/deepline-plays` for the full account-to-contact flow).
