# Identity recovery — the search arm, .edu corroboration, and tool mechanics

Tool contracts verified with `deepline tools describe` / `plays describe` 2026-09-30.
Yield observations marked "measured on Clay" come from the Clay version of this skill
(2026-08) — re-measure on a pilot before trusting them here.

## The reverse-lookup arm (try first, expect misses)

- **Work email** → `crustdata_v3_person_enrich`
  `{"business_emails": ["<email>"], "fields": ["basic_profile", "experience",
  "education"]}`. Priced per matched record, varying by field group — read
  `describe` and request only the groups you use.
- **Personal email** → `prebuilt/personal-email-to-linkedin`
  (`deepline plays run prebuilt/personal-email-to-linkedin --input
  '{"personal_email":"<email>"}'`; `-batch` variant takes `{"csv": "signups.csv"}`).
  This is an email tie, so it is allowed on personal rows; a bare-name search is not.

Realities to plan for:
- **Low yield on email** (measured on Clay's Enrich Person: real corporate addresses
  routinely returned complete + `{}` in seconds). The miss is the normal path — that's
  why the recovery arm exists.
- **Two-level gating**: check call/run status AND per-row value presence — a completed
  play run can hold failed or empty rows.
- **Multiple current roles**: when it DOES resolve, `experience.employment_details.current[]`
  can hold more than one entry (board seats, portfolio execs). Pick the primary role
  deliberately; treat multiple current entries as multi-role, never as a job change.
- Record actual spend after the batch (`deepline billing usage`, or `deepline runs get
  <run-id> --full --json` for a play) next to the declared estimate.

## The search-recovery arm (work + education rows only)

`crustdata_v3_person_search` (0.02 credits per returned row; empty pages free):

```json
{"filters": {"op": "and", "conditions": [
  {"field": "basic_profile.name", "type": "(.)", "value": "Maya Torres"},
  {"field": "experience.employment_details.current.company_website_domain", "type": "=", "value": "brightloop.example"}
]}, "limit": 5}
```

- Name: CSV name first, else the handle-parsed name hint (if the only name is a
  non-name handle, skip recovery — searching "Kc Builds" is a guess factory).
- Education rows: anchor on `education.schools.school` (the school name) instead of
  the employer — see below.

Reading results:
- Each profile carries the LinkedIn URL at
  `social_handles.professional_network_identifier.profile_url`, name, current title, and
  per-role `start_date` under `experience.employment_details.current[]`.
- **Gate on match count**: exactly 1 → candidate identity with evidence attached;
  0 → could-not-identify; 2+ → narrow with a title condition or flag for review —
  never pick one silently.
- **Ship the canonical URL**: the same person carries different LinkedIn slugs across
  sources; enrich the search hit before shipping its URL, or mark it raw.
- Your domain filter is the anchor, not evidence — employment reads come from the
  person's own `current[]` entries (measured on Clay: the record's `domain` field
  echoed the search anchor).
- Employment cross-check: compare domains, never name strings; a mismatch may be a job
  change OR a concurrent role (multi-role) — resolve through person enrichment and emit
  `multi-role` / `departed` / `employment unconfirmed` explicitly.

## .edu corroboration (the education branch)

The `.edu` domain is the **school**. Rules:
1. Never use it as a current-employer filter for an employer claim, and never blank the
   signal entirely — search with the available name, then corroborate the candidate by
   the school appearing in their **education history** (`education.schools[].school`),
   not employment.
2. The identified person's *current employer* (from their profile) becomes the company
   candidate — it will usually differ from the `.edu` domain, and that is correct.
3. A candidate whose education doesn't include the school stays unconfirmed — the tie
   was the whole anchor.

## Company resolution mechanics

- `crustdata_v3_company_identify` (FREE; `{"names": ["<employer>"]}` → candidate
  companies with domains): use when a row has an employer name but no domain.
  Sanity-check the output — name lookups can resolve the wrong entity; on low
  confidence emit `unresolved`, never a proxy.
- `crustdata_v3_company_enrich` (0.8 credits/result; `{"domains": [...], "fields":
  ["basic_info", "headcount", "locations", "taxonomy"]}` — omit `fields` and you get
  only `basic_info`): once per unique domain (Step 5 dedupe), joined back to rows.
  `basic_info.employee_count_range` is a band string — use `headcount.total` when
  present, else parse bands/ordinals; unparseable → `unresolved` visibly.
- Multi-signup detection is the same computation as the dedupe: count rows per unique
  domain before enrichment; count > 1 → flag the account as a PLG signal and carry the
  count into routing rank.
- At batch scale, run these as a Deepline play over the signups CSV (`deepline plays
  run signups.play.ts --input '{"csv":"signups.csv"}'`, then `deepline runs export
  <run-id> --out digest.csv`) rather than row-by-row `tools execute` calls.
