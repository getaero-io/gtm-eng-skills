---
name: find-linkedin-profile
description: |
  Find a person's LinkedIn profile URL with Deepline — from their name and company, or from an
  email — and validate it before reporting. Use whenever someone asks: find this person's
  LinkedIn, get the LinkedIn URL for a contact, what's X's LinkedIn profile at company Y,
  check whether this LinkedIn URL is still the right person, or fix a stale LinkedIn link.
  It searches Deepline's people index by name + company, validates every candidate URL against
  known facts (name and current employer must match), flags name collisions instead of
  guessing, and recovers from stale slugs and wrong-person rejects to the canonical
  profile. Do NOT use it to source net-new prospects by persona or title (people-search /
  list-building skills), to find email addresses (find-work-email), or to pull full person
  data for downstream enrichment (enrich skills). It never reports an unvalidated URL and
  never fabricates one.
category: find-contact-data
personas: [sales-development, recruiter]
mechanism: functions
touches: read-only
keywords: []
ported_from: clay-run/clay-skill-creator/skills/clay/find-linkedin-profile
---

# Find a LinkedIn profile

The insight: **a returned URL is a candidate, not an answer — and a rejected candidate is
not a dead end.** Finders hand back plausible URLs for the wrong person without erroring;
slugs go stale and vary; a reject usually means a same-name collision, not a miss. The
ladder: find → validate → recover — a wrong profile is worse than none.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **What they have per row** | a profile URL, an email, or a name plus company | no default — the route depends on it, and each route has a different failure mode |
| **The expected employer** | for personal-email rows, who they think the person works for | ask. A personal email carries no company anchor, so without this the match is unverifiable |
| **Budget** | credits, on the rows that need enrichment | rows that already carry a URL cost nothing; state the count that does |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — what each row already carries and the expected employer you supply.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or returns a profile it could not tie to the employer you named.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json` (health, auth, and balance in one call). If `deepline` is
missing, run `npm install -g deepline && deepline auth register --wait auto`, then re-run
preflight. Tell the user which org you're in (`auth.org_name`) and the balance.

## Step 1 — Triage the input

- **Have a URL** (validate/refresh ask) → Step 3.
- **Have a work email** → Step 3 (`crustdata_v3_person_enrich` accepts `business_emails`).
- **Have a personal email** → `prebuilt/personal-email-to-linkedin` (returns
  `linkedin_url`, `name`, `company`, `title`, `miss_reason`), then Step 3 on its candidate.
  Personal emails carry no company anchor — ask for the expected employer.
- **Name + company** → resolve the company to a domain first, then Step 2. A wrong domain
  silently finds the wrong people.

## Step 2 — Find: search the people index

```
deepline tools execute crustdata_v3_person_search --input '{"filters":{"op":"and","conditions":[
  {"field":"basic_profile.name","type":"=","value":"<full name>"},
  {"field":"experience.employment_details.current.company_website_domain","type":"=","value":"<domain>"}]},
  "limit":5}' --json
```

Records return the profile URL, name, current title, and employer; billing is 0.02 credits
per returned result (empty pages are free), and `total_count` tells you how many matched.
Check the exact field names in the first response. **Gate on match count:**

- **0** → retry spelling variants (`"type":"contains"` on the name); search non-Latin names
  once per script (native, romanized — providers index either). If they may have left,
  swap the domain condition for `experience.employment_details.past.company_name`. Still 0
  → try `prebuilt/person-to-linkedin-harvestapi` (Serper candidates from Google, inputs
  `first_name`, `last_name`, `domain` / `company_name`), then report honestly.
- **1** → a candidate — not yet an identity. Step 3.
- **>1** → collision, the dominant failure mode. NEVER take the top result — ranking is
  not identity. Narrow with `basic_profile.current_title` or `basic_profile.location`
  conditions if given; otherwise show the name/title list and ask (`next_cursor` set =
  still more).

For a CSV, `prebuilt/person-to-linkedin-harvestapi-batch` (`{"csv":"contacts.csv"}`) runs
the find and a HarvestAPI profile check per row; its `linkedin_url` output is still a
candidate for Step 3's three signals, not a verdict.

## Step 3 — Validate: three signals

Enrich the candidate with `crustdata_v3_person_enrich`
(`{"professional_network_profile_urls":["<candidate>"],"fields":["basic_profile","experience"]}`
— it accepts profile URLs or `business_emails` only, NOT name+company; priced per matched
record, field groups change the charge) or `harvestapi_get_profile` (`{"url":"<candidate>"}`,
usage-priced, a live read of the profile). Check `deepline tools describe <id> --json` for
the current price. Score three signals:

1. **Name** — first name must match (hard-fail); tolerate nicknames (Robert/Bob) and
   middle names. A last-name mismatch passes only with employer + location corroboration
   (married names); a bare last initial may hide in the slug (e.g. `/in/priya-r` for a surname starting with R).
2. **Employer** — current company/domain matches the expected employer
   (parent/subsidiary/sister brands count). A missing anchor (personal-email input) is
   neutral, not a failure.
3. **Real profile** — the payload carries an experience history with dates, not a thin
   shell.

All three → **validated**: report the URL from the enrich payload — the canonical slug,
never the raw search hit (sources disagree on slugs for one person). Two → **low
confidence**; name the failed signal. Name fails or fewer → **rejected** → Step 4. A
successful call with no matched record = **not found** — completion is not data
(not-founds return in seconds here — no waterfall; a slow call signals trouble, not a
miss). Name matches,
employer doesn't → **moved**: right person, new company — report URL + current employer +
flag. A stored URL that re-enriches empty = "could not re-verify" — recover; never
overwrite the stored value with nothing.

## Step 4 — Recover

A dead slug or a rejected candidate → re-run Step 2 with a disambiguator (title,
location). The recovered URL MUST differ from the rejected one and MUST pass Step 3
itself. No decisively better candidate → not found / ambiguous — empty beats wrong.

## What good looks like

The deliverable: the canonical enriched URL plus confidence and 1–3 short reasons quoting
the validating facts. Ambiguity is surfaced, never resolved by rank. The common mistake:
trusting one confident-looking hit — a single match can still be a same-named stranger.

## Rules

- MUST validate every candidate — including recovered ones — before reporting.
- MUST stop and disambiguate when more than one profile matches; NEVER pick by rank.
- NEVER construct a slug as a fallback; NEVER ship a URL that passed on one signal.
- MUST state cost and get approval before multi-person runs.

## Output

Per person: `name · company · LinkedIn URL · status (validated / low confidence /
ambiguous — n candidates / moved — now at X / not found) · reasons (1–3 short strings)`.
Batches get a summary line: validated %, low-confidence %, ambiguous %, not found %.

## Worked example

Ask: "Find the LinkedIn for Dana Whitfield at brightloop.example." `crustdata_v3_person_search`
returns one hit, `/in/dana-whitfield-8a41b2` · "VP Operations". `crustdata_v3_person_enrich`
→ canonical `/in/danawhitfield`, org
Brightloop, full history → validated ("VP Operations at Brightloop; name exact").
Counter-example: "Alex Rivera at meridianbank.example" → 6 profiles, different titles →
`ambiguous — 6 candidates` with the title list — never the first one.
