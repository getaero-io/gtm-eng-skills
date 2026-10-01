# Finding mechanics — search arms, buyer mapping, employment fields

Tool contracts verified with `deepline tools describe` 2026-09-30; re-check pricing and
fields with `describe` before a run. Behavioral observations marked "measured on Clay"
come from the Clay version of this skill (2026-08) and are kept as cautions, not as
Deepline facts.

## The default search arm — `crustdata_v3_person_search` (0.02 credits/returned row)

```bash
deepline tools execute crustdata_v3_person_search --input '{
  "filters": {"op": "and", "conditions": [
    {"field": "experience.employment_details.current.company_website_domain", "type": "=", "value": "brightloop.example"},
    {"field": "experience.employment_details.current.title", "type": "(.)", "value": "CFO"}
  ]},
  "limit": 25
}' --json
```

- Title vocabulary: one `(.)` (fuzzy) condition per term, grouped under `"op": "or"`
  inside the `and`; or an `in` list. **`in` / `not_in` arrays hold at most 5 items** —
  CrustData can silently ignore longer arrays, so split larger vocabularies across
  searches and merge. Widen VOCABULARY before seniority: "CFO" misses "Head of
  Finance", "Finance Director", localized titles.
- Optional `experience.employment_details.current.seniority_level` /
  `function_category` filters narrow further; get exact values from the free
  `crustdata_v3_person_search_autocomplete` (`{"field": "...", "query": ""}`) — never
  guess enum strings.
- Filters are RECALL, not guarantees — post-validate every returned record against
  the role/company ask; never trust the filter to have enforced it.
- `total_count` comes back (optional in the schema — read it defensively) and
  `next_cursor` is null at the end; a shortfall claim is honest only after paging to
  `next_cursor: null`.
- Records carry the LinkedIn URL at
  `profiles[].social_handles.professional_network_identifier.profile_url`, name, current
  title, and per-role `start_date` under
  `profiles[].experience.employment_details.current[]`.
- Empty pages are free.

## The roster arm — `company_titles` → `search_contact` (nuanced roles)

When the function's vocabulary is unusual ("Revenue Architect", "GTM Systems"), stop
guessing and read the company's own title strings (the find-qualified-titles pattern):

1. `company_titles` `{"domain": "<domain>"}` — FREE, the verbatim title roster.
2. Pick the titles that ARE the target role (you, or a `deeplineagent` call with a
   `jsonSchema` of `{matched_titles: string[]}` told to return exact strings from the
   list).
3. `search_contact` `{"domain": "<domain>", "title_lists": [{"name": "buyer",
   "titles": [...]}], "page_size": 50}` — 0.56 credits per returned row; LinkedIn URL +
   title only (no email/phone). Matching is not exact (live runs return titles that
   merely contain a listed title) — re-check each `title` before keeping the row.

## Why not the obvious function (the measured reality)

Measured on Clay's managed **Find People at Company** (2026-08): it returned the
company's top ~10 profiles ranked by SENIORITY and ignored every name/role filter it
accepted (name-filter keys accepted-and-ignored; `total: 10000` on a big company; a
famous-CEO ground-truth passed only because the CEO ranks first). The lesson carries
to any seniority-ranked lister: for any persona below "most senior person," it returns
the wrong people. On Deepline, `prebuilt/company-to-contact` does take `roles` and
`seniority` — but it returns "the best role-matched contact", so treat its output as
candidates that still pass Steps 3–4, never as the committee. Use a seniority-ranked
pull only when the ask genuinely IS "who's most senior here."

## Buyer mapping (what-you-sell → department × seniority floor)

Canonical enums (use verbatim — they drive deterministic gates):

Seniority (7): `C-Level, Founders, Owners` · `Executives and Senior Leadership` ·
`Non-Executive Management` · `Individual Contributors and Non-Management` ·
`External partners and contractors` · `Non-corporate role` · `Other`.

Title-token override rules, applied in order (0 and 2b are live-eval folds):
0. **"Chief of Staff" → Non-Executive Management** — applied BEFORE the Chief token:
   a Chief of Staff (to the CFO/CEO/anyone) is a staff role, not a function owner;
   the bare Chief-token rule misclassifies it as C-level (caught live: a "CFO"
   keyword search returned "Chief of Staff to the CFO" as its top hit).
1. Chief / Founder / Owner → C-Level, Founders, Owners
2. Director / VP / Vice President → Executives and Senior Leadership
2b. **Controller / Treasurer → Executives and Senior Leadership** — finance
   leadership titles with no VP/Director token; without this rule they fall to
   "Other" and get dropped.
3. Senior / Lead / Group → Non-Executive Management
4. Product / project / program / relationship / renewal MANAGERS → Individual
   Contributors (the classic misread — "manager" in these titles is not management)

**Keyword containment ≠ role identity**: fuzzy title filters match SUBSTRINGS —
"CFO" surfaces "Chief of Staff to the CFO". Every hit must pass role-identity
post-validation (is this title THE role, or a title that mentions it?) before
classification. The provider's own `seniority_level` / `normalized_title` fields are a
hint, not a substitute for these overrides. And index coverage has holes at the very
top: a major public company's sitting CFO can be absent under the exact title while
their SVPs are present — the honest output is "senior-most identifiable: SVP Finance",
never a promotion of the nearest hit.

Department (12): Engineering & Data & R&D · Design · Marketing & PR · Product ·
Finance & Accounting · IT & Security · People & HR & Recruiting · Operations ·
Legal · Sales · Customer Service · Other.

Common sell-into mappings: spend/finance tooling → Finance & Accounting, Director+;
security → IT & Security, Director+; devtools → Engineering, Director+ (plus
staff-level champions); HR tech → People & HR, Director+; martech → Marketing & PR,
Director+. At small companies (< ~200 headcount) the economic buyer floor rises to
C-level and the CEO is often genuinely the buyer.

Buying-committee framing: `Economic Buyer` (final budget authority — usually the
function's C/VP peak, or CEO at small cos) · `Champion` (senior operator who'd run
the tool) · `Influencer` (adjacent stakeholder). Emit the role per kept person; the
opener differs per role.

## Employment verification fields

- Filtering on `...current.company_website_domain` means the search asked for current
  employment — but still read the person's own
  `experience.employment_details.current[]` entries (company, `company_website_domain`,
  title, `start_date`) and quote them; never quote your search anchor back as evidence.
- Multiple entries in `current[]` are real (board seats, advisors, portfolio execs) —
  pick the one at the target company as the role; length>1 = `multi-role` flag, never
  "departed".
- Mismatch resolution ladder: `crustdata_v3_person_enrich`
  (`{"professional_network_profile_urls": ["<url>"], "fields": ["basic_profile",
  "experience"]}`, priced per matched record — read `describe`) → emit `multi-role` /
  `departed` / `employment unconfirmed`. A departed hit at the target company is a
  lead for track-champion territory, not a decision-maker row.
- Slug variance: the same person carries different LinkedIn slugs across sources —
  ship the canonical URL from enrichment, or mark the raw search URL as raw.

## Cost posture

Role-scoped search: 0.02 credits per returned row on `crustdata_v3_person_search`;
empty pages free. Roster arm: `company_titles` free, `search_contact` 0.56 credits per
returned row. Optional per-person enrichment (canonical URL / employment resolution):
`crustdata_v3_person_enrich`, priced per matched record by field group — state before
spending. A seniority-ranked lister is the baseline, not a rung.
