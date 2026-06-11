---
name: contact-accuracy
description: 'Use when enriching, scraping LinkedIn, finding or validating B2B emails, checking whether contacts still work at the target company, discovering role-holders at known accounts, or preparing any contact list that will be sent. Triggers on stale titles, same-name matches, job-changers, catch-all emails, malformed final CSV cells, duplicate contacts, or "is this list accurate enough to send?" Skip for pure copywriting with no contact validation.'
---

# Contact Accuracy & Freshness

Use this for any B2B contact list that will be activated, whatever role the user targets: finance, engineering, sales, clinical, ops, founders, or another function. The role changes only the ICP keep-list in §5. Every other gate is role-agnostic.

A row is sendable only when it is the **right person**, in their **current role**, reachable at a **deliverable email at their current employer**. Most bad enrichment rows look complete. The quiet failures are stale titles, same-name strangers, and emails on companies the person already left.

The throughline: **a field is only good when you can name its source and the check it passed. Flag everything else.**

## 1. Current role: take the latest active WORK role, not the top-level title

LinkedIn scrapers expose a top-level `jobTitle`/`companyName` and a full `experiences[]` array. Reconstruct the current role from `experiences[]`. The top-level title is often a past, secondary, board, or advisory entry because the scraper follows whatever LinkedIn surfaced first.

The current role is the experience entry that is **active** and has the **latest start date**:

- "Active" = `jobStillWorking === true`, OR no `jobEndedOn`/`endDate`.
- Among active entries, pick the one with the **most recent `jobStartedOn`/start date**.
- Use `scripts/select-current-role.py` for this; it encodes the rules below and is eval-tested. Don't re-derive the logic inline each time.

### Exclude board, advisory, charity, and retired roles when a real job also exists

A person can hold a board seat, advisory role, charity trusteeship, or "Self-Employed" entry alongside their actual operating job. Those are not the current employer for outbound. If the only active entry is board-only, retired, trustee, or similar, flag and HOLD instead of emailing them at the non-operating organization.

Deprioritize: `board member`, `member board of directors`, `of the board`, generic `advisor`/`advisory`, `trustee`, `volunteer`, `mentor`, `charity`/`foundation`/`non-profit`, `self-employed`, `retired`, `emeritus`, `ambassador`, and obvious non-profit companies (`foundation`, `trees for`, `rotary`, `united way`, `.org`). Exception: if the user explicitly targets advisor roles, such as Security Advisor, Clinical Advisor, Financial Advisor, or Technical Advisor, treat that title as work when it is at a real operating company.

### Company-name-in-title artifact

Scrapers sometimes put the company name in the experience `title` field. If `norm(title) == norm(company)`, recover the real title from the top-level `jobTitle` when it is a work role, or from the leading role phrase in `headline`. `select-current-role.py` handles this fallback chain.

## 2. Identity gate: confirm it's the right person, not a same-name stranger

Relaxed searches and name+domain provider lookups routinely return a **different human with the same name**. Two checks decide whether a scraped or searched identity is safe:

1. **Name match.** The returned `firstName`/`lastName` must match the row's name. Allow nicknames via `scripts/validate-linkedin-names.py`, first/last swaps, and maiden-to-married variants when the LinkedIn numeric ID suffix is identical. A non-match means wrong person: reject it.
2. **Company-in-work-history.** The row's target company (or its email domain) must appear **somewhere** in the person's `experiences[]`, current OR past. If the target company appears nowhere in their history, you matched a stranger. The strongest confirmation is domain-anchored provider search (Apollo/Crustdata by `companyDomain`), which can't return a person at a different company. For name-based or scrape results, verify the company appears before trusting the row.

When you cannot confirm both, output HOLD/REVIEW with the reason. A guessed identity is not a found contact.

## 3. Freshness: catch job-changers; their email is on a dead domain

People move. On older lists, a job-changer's listed email is often on their old company domain, so outreach is both wrong-context and bounce-prone. After you have the current role (§1):

- Compare current employer vs the row's listed company. If they differ -> `still_at_company = NO`, and the listed email is suspect.
- For NO rows, either (a) re-find a fresh email at the **current** employer's domain, or (b) flag for removal from the campaign. Surface both the old and new company so the user decides.
- This is the highest-value check on an *active* campaign list: those are the rows actively getting wrong messaging.

## 4. Email validation: never trust a single provider's status

Provider "verified"/"valid" flags are the provider grading its own homework. Independently validate every email with a dedicated validator. ZeroBounce and LeadMagic are current starting hints; confirm live tools with `deepline tools search "email validation" --json` and `describe`.

- **valid:** deliverable, ship.
- **catch-all:** the domain accepts everything; ship only when a second independent finder returned the exact same address.
- **invalid / do_not_mail:** drop.
- **unknown / no-status:** retry once, then hold unless a second validator says valid.

Validate after recovery/coalescing, once per final address, not during every waterfall leg.

## 5. ICP filter: keep the real targets, hold the drift

Title-anchored lists drift, whatever the target role. A list sourced as "X" accumulates people who left that function (a "Heads of Sales" list collects ex-sellers now in ops or consulting; a "DevOps leads" list collects people who moved to management or left the company) or were never in it (a same-name decoy from §2). After resolving the *current* title (§1), bucket each row against **the user's stated ICP**, not against a fixed taxonomy:

- **Keep, on-ICP:** the current title matches the target function. Define the match by the user's role family, not by exact string: a "VP Finance **and** Operations" stays on a finance list because finance is present; a "Senior Staff Engineer" stays on an engineering-leaders list. When in doubt about seniority cutoffs, keep and flag rather than drop.
- **Keep, decision-maker even if off-title (SMB):** Founder / Co-Founder / CEO / President / Owner / Principal / Managing Partner. At a small company the owner is often the buyer for *any* function, so they belong on most SMB lists regardless of the nominal target role. Confirm this fits the campaign; some want only titled function-holders.
- **Hold, off-ICP or adjacent:** a current title in a *different* function than the target (the ops person on a finance list, the recruiter on an engineering list), plus clear non-targets (a job that has nothing to do with the campaign, board-only, retired, student). Send to REVIEW with the reason; don't drop silently.

The point is role-agnostic: resolve the current title, then keep the rows whose current function matches what the user actually asked for. **Worked example (finance list):** keep CFO / Chief Financial Officer / Chief Accounting Officer / Controller / Comptroller / VP·SVP·EVP Finance / Director of Finance / Treasurer / Finance Manager / Accountant; hold a current COO or Director of Operations with no finance in the title. Swap that keep-list for the user's actual target (sales leaders, engineering managers, marketing heads, clinicians, whatever) and the same machinery applies. Always *show* which bucket each row fell in so the user can correct the line.

## 6. Lineage: every field names its source

A reviewer (and you, later) must be able to see **where each value came from**. Per the export contract, carry `source`, `status`, and `miss_reason`, and for accuracy-critical lists, go further: tag the source *per field*, not just per row. Useful columns: `title_source`, `email_source`, `identity_confirmation` (how you confirmed the person works there: `apollo_org` / `crustdata_domain` / `linkedin_experience` / `email_domain_match` / `NONE`), `email_validation` (`zerobounce:valid` / `leadmagic:valid` / `catch-all:2-provider`), and `still_at_company`. When you coalesce multiple sources, record which source won each field. This is what lets the user trust 460 rows without re-checking each one, and lets you debug the wrong ones.

## 7. Golden record: one authoritative value per field, all signals kept

When you've pulled the same field from several sources (a LinkedIn scrape, Apollo, Crustdata, PDL, the original list), the deliverable should not make the user guess which to believe. Produce a **golden record**: for each field, one chosen value plus an explicit **source-of-truth** and **confidence**, with every upstream signal preserved in its own column. The golden columns are the answer; the upstream columns are the evidence. Where the golden disagrees with an upstream value, that's intentional, and visible.

Build it deterministically:

- **Precedence, not averaging.** Define an explicit order and take the first source that has a value, e.g. for a *current title*: fresh LinkedIn scrape (active-work-role logic) -> PDL (only when the scrape failed) -> original list (unverified, last resort). Record which one won in `<field>_source_of_truth`.
- **Confidence tier per row**, derived from the winning source + the gates it passed: `HIGH` (fresh first-party source, all gates passed), `MEDIUM` (fallback source, or catch-all email, or current-role not flagged still-working), `LOW` (only an unverified/original value survived), `HOLD` (failed a gate: board/charity-only, identity mismatch, audit-flagged). The user reads this column to decide what to send vs. review.
- **Keep upstream signals as columns, not overwritten.** Name them by source: `src_*` (original list), `li_scrape_*`, `pdl_*`, `disc_*` (domain-anchored discovery), `gap_*` (recovery waterfall), `audit_*`, `history_*`. This is what makes a wrong golden value debuggable and lets a human override with full context.
- **Surface disagreement.** A `sources_disagree` flag (golden title/company conflicts with another source that also had data) points the reviewer straight at the rows most worth a look. Don't hide conflicts behind the golden value.

A golden record done this way means the user can trust the `GOLD_*` columns for a bulk action and still audit any single row down to the provider call that produced each cell. Pair it with a short **data dictionary** (one line per column: what it is, its source, valid values) so the file is self-describing.

## 8. Company-first discovery: when you have the accounts, anchor on them, not the names

§2 said domain-anchored search is the strongest identity confirmation. When your input is a list of **known accounts** (companies + domains) and the goal is "the person in role X at each" (the CFO, the VP Eng, the Head of Sales, the office manager, whatever the campaign targets), invert the whole pipeline: don't start from a name you're trying to verify, start from the company and *discover* the current role-holder. Because you never matched on a name, the **same-name-decoy class from §2 can't occur** here: a domain-anchored search can't hand you a stranger who happens to share a name with someone on your list. It can still hand you the wrong *person at the right company* (a former employee whose profile still lists the domain), so §8's verification is about role-freshness, not name-matching.

This matters most when the list is stale or title-anchored. In stale-account audits, name-first refresh often keeps the *original* person even after they left; company-first discovery finds the **current** role-holder who replaced them. The same applies to any role: a VP Eng who left is replaced by the new VP Eng, and company-first finds the successor while name-first keeps emailing the person who walked. The company-first row is the one you actually want to email.

The pattern, in durable terms:

- **Input contract:** company name + domain (+ optional tier).
- **Discovery:** domain-anchored people search filtered to the **target role**, across multiple providers in a waterfall: Apollo by organization-domain, Crustdata by company-domain, a search/finder provider as fallback. Pass the role as a title filter (the user's target function, not hardcoded to finance). Each provider is blind to the others; take the first that returns a current role-holder at that domain. Find the live tool/play names with `deepline plays search "company contacts" --json` and `deepline tools search "people search domain" --json`; confirm input shape with `describe` before running, because provider field names rot.
- **Verify the discovered person, but don't name-gate them.** The §2 name-match check does not apply: you *want* a different name than the one on your stale list, so requiring the names to match would reject the successor you came to find. What you owe instead is (a) §1's current-role logic on the returned person, to confirm the company is their *current* employer and not a role they already left, and (b) that the company genuinely appears as their current/recent employer (the domain anchor gives you this for free). Confirm those two, and the discovered name is the answer.
- **Coalesce with any name-first data you also have.** When you run both pipelines (company-first discovery + a name-first refresh of the original contact), record per field which pipeline won, and flag where they disagree: that disagreement is exactly the "the original person left, here's the successor" signal worth surfacing.

Company-first is the safer default for account lists; fall back to name-first only when you have no reliable domain or the account isn't the unit of work (e.g. a list of individuals with no shared employer).

## 9. Validate every cell, not just every row, before you ship

Row gates (§1–§5) catch wrong people and stale roles. They do not catch malformed cells: an email that will not parse, a LinkedIn URL that 404s, a bad date, or a title field that still contains the company name. Run a deterministic audit over the final file before delivery:

- **Email** parses as RFC-valid and the domain has a dot. Validity is not deliverability, but malformed strings should never reach the file.
- **LinkedIn URL** is a well-formed `linkedin.com/in/...` (or a clearly-marked abbreviated slug), not a search URL or a bare name.
- **Dates** match the formats your golden record promises (`YYYY`, `YYYY-MM`, `Mon YYYY`).
- **Title ≠ company.** If `norm(title) == norm(company)`, the company name leaked into the title (§1) and the repair didn't take; fix it or flag it.
- **Email-domain vs company.** When the email domain isn't an obvious match to the current company (and isn't a known acronym/parent domain), flag it for eyeball: usually a legitimate alternate corporate domain, occasionally a job-changer §3 missed.
- **Confidence consistency.** No row should be `HIGH` confidence with an empty title, or claim a source-of-truth it has no column for.

Emit row-addressable flags so each issue is reviewable without re-scanning the file. Most flags mean "eyeball this," not "wrong"; the point is that nothing malformed ships silently.

```bash
python3 scripts/contact-accuracy-audit.py final.csv > final_audited.csv
```

The audit adds `email_risk`, `profile_age_days`, `email_verification_age_days`, `flags`, `flag_reason`, and `ACTION`. It checks:

- profile and email verification freshness, using 30 days as the default freshness SLA
- catch-all risk, with `catch-all` allowed to ship only when at least two independent finders returned the same address
- job-changer detection and old-domain email detection
- company email-domain aliases via `allowed_email_domains`
- malformed final cells: email shape, LinkedIn `/in/` URL, and `title != company`
- duplicate-person conflicts using LinkedIn URL, then email, then name + company domain + title

Eval it with `python3 scripts/contact-accuracy-audit.py --fixtures scripts/fixtures_contact_accuracy_audit.json`.

## 10. The deliverable: one ACTION column, holds sorted to the top

A reviewer staring at 400 validated rows needs to know *what to do with each one* faster than they can read a confidence tier and infer it. The format that worked: a single **`ACTION`** column with a small, exhaustive vocabulary, plus a **`flag_reason`** column that says why in one line. Sort so the rows needing a human come first.

| ACTION | Means | Maps from |
| --- | --- | --- |
| `SEND` | Right person, current role confirmed, email is deliverable | HIGH confidence; or MED whose only soft signal is a 2-provider-corroborated catch-all email (§4); `still_at_company` not NO |
| `REMOVE / RE-TARGET` | Not safe to email *for this campaign*: either a job-changer (listed email on a dead domain) or a board/charity-only contact (no operating role to target) | §3 `still_at_company=NO`, or §1 board/charity-only HOLD |
| `VERIFY` | Couldn't confirm the current role (e.g. unscrapeable profile); eyeball before sending | LOW confidence / unverified source |
| `REVIEW` | Real person, but a soft signal needs a human: current role not flagged still-working, or sources disagree on title | MED confidence, `sources_disagree=YES` |

`ACTION` is derived from the golden record's confidence + flags (§7); it's a *decision projection* of columns the file already has, not new judgment. The one place it isn't a pure tier read is the catch-all carve-out: a MED row whose only softness is a corroborated catch-all email is deliverable enough to `SEND` (§4), so don't bucket every MED into `REVIEW`. Keep `flag_reason` specific ("Job-changed: left X, now at Y") so the reviewer trusts the call without re-deriving it. The `REMOVE / RE-TARGET` rows are the highest-value output on an active campaign: the job-changers in that bucket are getting wrong messaging at a company they've left right now.

## 11. Confidence is honest, and some sources don't earn trust

Two failure modes that look like success:

**Don't promise deliverability you can't guarantee.** Email validity is point-in-time: a mailbox valid at validation can bounce a week later, and a catch-all domain never confirms the specific mailbox at all (§4). A list that's been gated through §1–§10 is *as accurate as the current data allows*, which is the honest claim. Stating it that way, rather than "zero mistakes" or "100% deliverable", sets the right expectation and is what the user actually relies on. Overclaiming erodes trust the first time a verified row bounces.

**A provider that returns *a* person isn't a provider that returns the *right* person.** Name+domain lookups (PDL and similar) for contacts with no LinkedIn will confidently return a same-name human who isn't your target: the §2 decoy problem, just from a structured provider instead of a search. These are not safe to ship as confident rows; they need the same name+company-in-history gate, and when the gate can't confirm, they belong in HOLD/`VERIFY`, not in `SEND`. "The provider returned something" is not confirmation; "the returned person's history contains the target company" is.

## Putting it together (recommended order)

For a contact list you will send:

1. **Source company-first when you can** (§8). For known accounts, anchor on company + domain and discover the current role-holder. Verify by current role, not by name match, because a successor may be the correct answer. See also `recipes/account-orgchart.md`.
2. **Resolve the current role** with `select-current-role.py` (§1): latest active work role, board/charity excluded, company-name-in-title fixed.
3. **Identity gate the names you *brought in*** (§2): name match + company-in-history. This is for verifying a name you already have (a scrape or a name-first refresh) and applies to structured-provider results too (PDL by name+domain), not just searches (§11). It does *not* apply to company-first discoveries from step 1.
4. **Freshness** (§3): flag job-changers; re-find at the current domain or hold.
5. **Find + validate email** (§4): waterfall to find, ZeroBounce/LeadMagic to confirm, catch-all needs corroboration.
6. **ICP filter** (§5): keep rows whose current title matches the user's target role (+ SMB owners); hold off-ICP/adjacent-function rows.
7. **Emit lineage** (§6): per-field source, validation, identity confirmation, still_at_company.
8. **Build the golden record** (§7): one chosen value per field with source-of-truth + confidence, upstream signals kept as columns, plus a data dictionary so the file is self-describing.
9. **Validate every cell** (§9): run `contact-accuracy-audit.py` over the final file for email/URL/date shape, `title != company`, domain alignment, freshness, catch-all risk, aliases, and duplicate-person conflicts.
10. **Project to an ACTION column** (§10): `SEND` / `REMOVE / RE-TARGET` / `VERIFY` / `REVIEW` with a one-line `flag_reason`, holds sorted to the top. Anything that fails a gate lands in a non-`SEND` bucket with its reason, never silently shipped.
11. **State confidence honestly** (§11): "as accurate as the current data allows," not "zero mistakes." Email validity is point-in-time.

Eval the role selector with `python3 scripts/select-current-role.py --fixtures scripts/fixtures_current_role.json`.
Eval the final-row audit with `python3 scripts/contact-accuracy-audit.py --fixtures scripts/fixtures_contact_accuracy_audit.json`.
