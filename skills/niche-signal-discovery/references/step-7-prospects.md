# Step 7 — Top 10 net-new prospects (required deliverable)

A signal report without a companion prospect list is incomplete. The signals tell you what to look for; Step 7 produces the actual "here are 10 real companies the user should pursue" list. **This is a hard requirement of the pipeline.**

## What's required vs. what's optional

| Output | Status | Why |
|---|---|---|
| **10 net-new companies** with descriptions, signal scores, matched signals, cited evidence | **REQUIRED** — every run | A signal report without target companies forces the user to do their own prospecting pass, which is the expensive thing they wanted to skip. |
| **Contacts + corporate emails** at those companies | **OPTIONAL** — credit-aware | Contact discovery uses additional Deepline credits for the email waterfall. Always offer it; only run it if the user approves the credit spend. Default to `--no-contacts` if the user hasn't said. |

When contacts are skipped, the prospect cards still need to ship — they just include "(contacts not enriched — re-run with `--contacts` to add)" in place of the contact bullets.

## What every prospect card must contain

1. **Company identity** — name, apex domain, 1-sentence description (location, what they do)
2. **Category label** from Step 1.0.5: Net-new / Account-only / Re-engage; excluded items dropped entirely
3. **Signal score** + the 4–6 matched signals from Step 4/5, shown as inline code
4. **3–5 cited evidence quotes** from the company's own website or job listings (same format as Step 5) proving the signals actually hit
5. **(if `--contacts` is on)** 1–3 named contacts with full name (linked to LinkedIn), title, and corporate email validated against the company's apex domain. "(email not found)" annotation when the waterfall returned nothing — be honest about gaps rather than shipping false positives.

## Use the shipped orchestrator

`scripts/find_contacts.py` runs the full chain via Deepline. Don't rebuild it inline.

```bash
# Companies only (no credit spend on contacts):
python3 scripts/find_contacts.py \
    --input prospects_actionable.csv \
    --output top10.csv \
    --top 10 \
    --no-contacts

# Companies + contacts + emails (asks for credit approval).
# IMPORTANT: --roles must be the buyer-persona job titles from THIS run's
# Step 0/0.5 ecosystem discovery. Don't reuse another vertical's roles.
python3 scripts/find_contacts.py \
    --input prospects_actionable.csv \
    --output top10.csv \
    --roles "<persona job titles from Step 0.5>" \
    --top 10 \
    --contacts

# Vertical examples (substitute the persona that came out of YOUR Step 0.5):
#   creative ops:   "Creative Director,Brand Manager,Content Operations Lead,Marketing Operations"
#   AR automation:  "AR Manager,Accounts Receivable Specialist,Controller,Finance Director"
#   sales engagement: "SDR Manager,Sales Operations,VP Sales,Head of Sales Development"
#   developer tools: "Staff Engineer,Platform Engineer,DevOps Lead,Engineering Manager"
#   metal AM (the run that motivated this skill): "Design Engineer,Mechanical Design Engineer,Additive Manufacturing Engineer,DfAM Engineer"
```

## The 3-phase contact chain (when `--contacts` is on)

**Phase 1 — `company_to_contact_by_role_waterfall` (FREE tier).** Dropleads → deepline_native → Apollo → Icypeas → Prospeo → Crustdata. Works on >200-employee US/EU companies. Returns LinkedIn URLs + titles, often no emails. Run first because it's free.

**Phase 2 — `exa_search_people` fallback for the gaps.** For any company Phase 1 returned ZERO contacts for, fall back to `exa_search_people` with `includeDomains=['linkedin.com']` and a query like `"Design Engineer OR Mechanical Engineer OR DfAM Engineer at {{company_name}}"`. Exa neural search finds LinkedIn profiles by semantic match against the company name — far better coverage for small / non-US / niche industrial targets than the B2B provider waterfall.

**This fallback is not optional.** On the run that motivated adding it, Phase 1 returned 0 contacts on all 10 top-scoring prospects (all <200-employee industrial companies). Phase 2 found 15 real contacts at 6 of those same 10 in the same run. If you skip Phase 2 because Phase 1 "worked" (ran without error and returned 0 rows), you ship an empty list with no explanation.

**Two Exa guardrails matter:**
- **Title parse**: Exa results follow `Name | Role at Company`. Regex the name out of the leading capitalized tokens; treat the rest as the title. Fall back to de-slugging the LinkedIn URL when the title doesn't parse cleanly.
- **Company-match filter**: Require the company name (or its first ~8 characters) to appear somewhere in the result title or text. Exa neural will sometimes return profiles at COMPETING companies — e.g., searching for "plasma process engineer at Plasma Processes" returned a real plasma process engineer working at Hypertherm. Discard any result where the company name doesn't match.

**Phase 3 — `person_linkedin_only_to_email_waterfall` for email resolution.** For every named contact with a LinkedIn URL, run this waterfall (dropleads + deepline_native + crustdata + PDL). Returns one primary email per contact.

**Domain-match validation is mandatory.** Always check that the returned email's apex domain matches the company's apex domain before publishing. Providers return stale addresses often enough that this is the difference between a usable list and an embarrassing one. On one real run:
- A contact at X-Bow Systems came back with `@orbitalatk.com` (his previous employer, acquired into Northrop Grumman years earlier)
- Another came back with `@governors-america.com` (a completely unrelated company)
- A third came back with a personal `@googlemail.com`

Use `extract_apex()` from `scripts/dedupe_utils.py` on both the email domain and the company domain; if they don't match, mark `email_source=apex_mismatch` and publish "(email not found)" instead. Keep the raw value in `raw_email` for auditing.

## Output card skeleton

Render each prospect as a card (heading + description + signals + evidence + contacts), not a wide table. Cards make it possible to include the required 3–5 evidence quotes per prospect without blowing up layout.

```markdown
### [company name] — score [N] [category badge]

*1-sentence description of the company.*

Domain: `apex.com`

Matched signals: `signal1`, `signal2`, `signal3`, `signal4`

**Cited evidence:**
- [📄 website] [page title]: "...exact quote around keyword..."
  https://apex.com/source-page
- [💼 job] [job title]: "...exact quote from listing..."
  https://linkedin.com/jobs/view/...

**Contacts:** (only if --contacts was on)
- **Full Name** — Role  ·  ✉ `email@apex.com`
  https://linkedin.com/in/profile
- **Other Name** — Role  ·  (email not found)
  https://linkedin.com/in/profile
```

## How many is "10"

10 is a ceiling, not a floor. If the actionable pool (post-dedupe, scored) has fewer than 10 companies that pass the minimum score threshold, ship whatever you have and explain the shortfall — don't pad with low-confidence entries. If the pool has more than 10, prefer top-scoring first, then break ties on category preference (net-new > account-only > re-engage) to surface the cleanest outbound targets.
