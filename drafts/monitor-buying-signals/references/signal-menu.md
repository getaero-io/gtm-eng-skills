# The signal menu — classification rules, hook quality, validation

Signals are picked by intent specificity × capturability × cost ×
**outbound hook quality**. This skill's sweep
covers the news-shaped subset; the wider menu rows are listed so the user's ask can be
routed honestly (some belong to sibling skills or different infrastructure).

## News-shaped signals (this skill's territory)

| Signal | Fires on | Hook quality | Opener angle |
|---|---|---|---|
| Funding round | raise / round / series / seed / IPO vocabulary + amount | GOOD | "Congrats on the round" |
| M&A | acquires / acquired / merger / acquisition | GOOD-EXCELLENT | post-acquisition change angle |
| Executive hire | names / appoints / joins as + C-level or VP title | EXCELLENT | "Congrats on the new role" |
| Expansion | opens / expands / new office / new market | GOOD | growth angle |
| Layoffs / restructuring | layoffs / cuts / restructuring | BORDERLINE — handle with care | usually watch, not act-now |
| Security breach / outage | breach / incident / outage | SENSITIVE | act-now only if you sell the fix; never gloat |
| Product / partnership launch | launches / partners with / integration | MEDIUM | complement framing |

## Deterministic classification rules (code first, judgment second)

1. Match on **title + snippet + date**, lowercase, word-boundary keyword sets per row
   above. First matching menu row wins; order the checks by specificity (M&A before
   generic "announcement").
2. **Amount/title corroboration**: funding needs a money token ($, million, Series X);
   exec hire needs a seniority token (Chief, C-level acronym, VP, President, Head of).
   Vocabulary without corroboration → `other`, never a fired signal.
3. **Date discipline**: event date must fall inside the sweep window; outside → drop
   with a note. No date on the event → `other` (undated news is archive material).
4. **Entity discipline**: the event must be about YOUR account — corroborate on the
   domain or exact company name from the account list; a similarly-named company in
   the headline is the classic false positive. Two trap shapes verified live on a
   real payload: `former <account>` (an alumnus's news, not the account's — drop to
   `other`), and `<account> supplier|partner|customer|rival <other-company>` (your
   account as a MODIFIER of the story's real subject — ambiguous). When ambiguous →
   `watch` with a verify-first note, never act-now.
4b. **Relative dates are real dates in disguise**: the web-search arms
   (`serper_google_search`, the Google News SERP) can return
   event dates as relative strings ("2 days ago", "3 weeks ago") — parse them to
   absolute dates at sweep time before the window check; an unparseable date string
   → `other` (rule 3 applies).
5. Anything unmatched → `other` → digest tail. An LLM pass may reclassify ONLY
   ambiguous events, and must quote the evidence line it ruled on.

## Non-nullable output fields per fired signal

`signal_present` boolean (never null — downstream gates must be deterministic) ·
`signal_evidence` ≤140 chars taken from the actual event text ·
`signal_source` URL · `signal_date` inside the window.
Cross-corroboration strengthens routing (funding + hiring growth = stronger act-now);
one uncorroborated weak signal never outranks a corroborated one.

## The wider menu (routed elsewhere — say so instead of faking coverage)

| Signal | Why not here | Where it lives |
|---|---|---|
| Person job changes (champions, buyers) | person-grain; contact radar monitor (`contact_job_changes`) or `prebuilt/job-change-check` | track-champion-job-changes |
| Hiring patterns (open roles by function) | its own column territory; role-scoped job-post feeds | hiring-radar / `company_job_openings` radar monitor |
| Tech-stack adoption/churn | provider install/last-seen dates, not news | detect-tech-stack (snapshot) + provider tenure fields |
| Web intent (visited your pricing page) | needs the customer's own visitor IPs; NEVER referenced in copy | `company_reveal` (IP → company) on their logs, prioritization only |
| Product usage (PLG) | customer's own telemetry | their warehouse → Deepline (warehouse/`postgres` tools or the Customer DB) |

## Re-qualification rule (before anyone acts on a fired signal)

An event proves a state change, not deal fit. Before outreach spend on an act-now row:
(1) the premise still holds (hire still in seat, deal closed as reported);
(2) the account is still in-ICP; (3) the entity matches on DOMAIN, not name strings.
The digest carries the re-qualify note on every act-now row.
