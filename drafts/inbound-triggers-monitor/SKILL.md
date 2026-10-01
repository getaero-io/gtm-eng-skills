---
name: inbound-triggers-monitor
description: |
  Find the people already engaging with you on social and turn each interaction into a
  dated, deduplicated inbound trigger — pull your team's recent posts, pull who reacted,
  commented and reshared, drop your own employees and company pages, resolve each engager
  to a person and account, and rank by how hard they leaned in. Use whenever someone asks:
  who engaged with our posts, who commented on our founder's content, turn LinkedIn
  engagement into pipeline, find warm leads from people reacting to us, or which accounts
  are showing up in our comments. Do NOT use it to watch accounts for third-party news
  events (monitor-buying-signals), to source net-new accounts from events (signal-sourcer),
  to score and route inbound once you have it (score-inbound-leads), or to track a champion
  changing jobs (track-champion-job-changes). Built on Deepline's LinkedIn post tools; the
  engager lists are paged samples, so it reports who it CAN see and never claims a complete
  engager list.
ported_from: clay-run/clay-skill-creator/skills/clay/inbound-triggers-monitor
category: signals
personas: [sales-development, marketing]
mechanism: functions
touches: read-only
keywords: []
---

# Inbound-triggers monitor (engagement → warm rows)

The insight: **this is a ranking problem wearing a detection problem's clothes.** Every
other monitor asks "did the event happen?" — the event either fired or it didn't. Here the
platform hands you a **truncated, self-contaminated top-N sample** of the people who
engaged, and three things follow that the naive build gets wrong:

1. **What you see is a page budget, not the engagement.** The engager tools return one
   page per call; a post with 400 reactions needs many pages, and every page you don't
   fetch is people you don't see. Providers also return what they can reach, not what
   exists (see `references/interaction-mechanics.md`). So a viral post is *less*
   observable than a quiet one for the same budget, and absence of a person from the feed
   is never evidence they didn't engage.
2. **Your loudest engagers are your own people.** Employees, the company page itself, and
   partner accounts sit at the top of every reaction list. An inbound monitor without a
   suppression gate reports your own marketing team as buying intent — and it does it
   confidently, because those rows are real interactions.
3. **The same human appears many times.** One person who reacts to four posts and comments
   on two is six rows and one lead. Deduplicating by event (what a news monitor does) is
   wrong here; the key is the **person**, and the interactions are their intensity.

So the output is never "here are the people who engaged." It is **"here is who we can see,
after suppression, ranked by how hard they leaned in — and here is where the sample was
cut off."**

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Whose posts** | person profile URLs (and/or company page URLs) whose content draws their buyers | no default. Person profiles and company pages use different stage-1 tools; both exist |
| **Window and depth** | how far back, and how many pages of posts per profile | **one month and one page per profile is defensible.** The tool's date filter takes buckets (`24h`/`week`/`month`, up to `6months` as a post-filter), so the exact window is still enforced when reading timestamps |
| **Which interaction types** | reactions, comments, shares | **reactions + comments is defensible** and must be stated. Comments are the strongest signal; reshares need a separate, pricier tool keyed on the post URN |
| **The suppression set** | their own domains and company pages, their employees, plus partners, agencies and investors | ask — this is non-negotiable. Without it the play degrades into people who engage structurally rather than out of interest |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the posts you point it at and the interaction types you choose.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, pushes anywhere, or contacts anyone who interacted.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing: `npm install -g deepline &&
deepline auth register --wait auto`. Tell the user which org they're in and the balance.

Confirm the arm exists before promising it — never assume the catalog:

```
deepline tools describe harvestapi_get_profile_posts --json
deepline tools describe harvestapi_get_post_reactions --json
deepline tools describe harvestapi_get_post_comments --json
```

The tools this play runs, their inputs and prices, are in
`references/interaction-mechanics.md`. Two traps worth naming here:

- Profile-keyed tools such as `harvestapi_get_profile_comments`
  answer "what did this profile do"; `harvestapi_get_post_reactions` /
  `harvestapi_get_post_comments` answer "who engaged with this post". This play is
  post-keyed tools downstream of one posts-by-author call. They are easy to swap and the
  swap silently inverts the question.
- `scrapecreators_reddit_post_comments` and other non-LinkedIn "post comments" tools
  come up in the same search. Name-matching the catalog is how you end up calling them.

## Step 1 — Collect the monitored surface (interview; do not guess)

1. **Whose posts.** Person profile URLs whose content draws your buyers — founder, execs,
   the people who post — via `harvestapi_get_profile_posts` (`profile`, e.g.
   `linkedin.com/in/…`). Company pages go through `harvestapi_get_company_posts`
   (`company`, e.g. `linkedin.com/company/…`).
2. **Window and depth.** How far back, and how many pages of posts per profile. The
   tools take `postedLimit` (`24h` / `week` / `month`) or `scrapePostedLimit` (up to
   `6months`) — buckets, so the exact window is enforced by you when you read each
   post's date, not by the call.
3. **Which interaction types.** Reactions, comments, shares. Comments are the strongest.
   Default: reactions + comments; shares on request (separate tool, keyed on post URN).
4. **The suppression set** — non-negotiable, and the play degrades into noise without it:
   - your own company domain(s) and company page URL(s),
   - your employees (a roster, or the domain that resolves from step 7),
   - partners, agencies, investors, and anyone else who engages structurally rather than
     out of interest.
5. **The book.** Existing customers and open pipeline. These are **not dropped** — an
   engaging customer is an expansion signal — but they must be labelled, because routing a
   customer to an SDR as a new lead is the embarrassing failure here.

## Step 2 — State cost, get approval

Read prices from `deepline tools describe <id> --json` → `pricing`. On 2026-09-30 the
harvestapi post tools were **0.03 Deepline credits per page**; reshares via
`aviato_get_post_reshares` were 0.28 credits per call. The arithmetic, stated before
spending:

```
stage 1:  0.03 × (monitored profiles) × (pages of posts per profile)
stage 2:  0.03 × (posts in window) × (types: reactions, comments) × (pages per post)
        + 0.28 × (posts in window) × (pages per post)            if shares are on
```

Worked: 3 profiles, 1 page each, 10 posts in the window, reactions + comments at up to 3
pages each → `0.03×3 + 0.03×10×2×3 = 1.89 credits` worst case. Identity resolution in
step 7 is priced separately and only for rows that survive the gate — which is the whole
reason the gate runs first.

Give the number, get a yes, then spend. If the user wants a cheaper first pass: comments
only, first page, which is also the highest-intent subset.

## Step 3 — Enumerate the posts (stage 1)

Per monitored profile, `harvestapi_get_profile_posts` with `profile` and a `postedLimit`
covering the window (company pages: `harvestapi_get_company_posts` with `company`). Page
with `page` + `paginationToken` until the window is covered or the page budget is spent.
Keep for each post: the canonical post URL, its posted date, and whose profile it came
from.

Then apply the window yourself, on the post's date. Drop anything older. Report how many
posts each profile contributed — a profile that posted twice this month contributes two
posts, and the digest should not look thin without saying why.

## Step 4 — Pull the interactions (stage 2)

Per post, per chosen type:

| Tool | Input | Paging |
|---|---|---|
| `harvestapi_get_post_reactions` | `post` (post URL) | `page` |
| `harvestapi_get_post_comments` | `post` (post URL), `sortBy` (`date` for a window) | `page`, `paginationToken` (relevance sort) |
| `aviato_get_post_reshares` | `postUrn` | `page`, `perPage`, `paginationToken` |

**Set the page budget explicitly per type and record it.** Read the first page to learn
the page size and whether the response reports a total; stopping at page 1 on a
well-engaged post is a recall loss that looks identical to a quiet post in the output.

Record per post: how many interactions came back per type, how many pages you fetched,
and whether more pages existed (a full last page, a returned pagination token, or a
reported total above what you hold). A post with more pages unfetched is definitely
truncated, and step 9 has to say so.

But **a short return does not mean complete** — observed on Clay's equivalent reactions
action (2026-08): a request for 50 reactions on a well-engaged post returned **48**. The
provider returns what it can reach, not what exists, so a short return is *unexplained*,
not reassuring. Report the requested budget and the returned count side by side and let
the reader see the gap; do not convert either into a completeness claim.

Each returned interaction should carry the engager's name, profile URL, a
person-vs-organization discriminator, their headline, the interaction type and, for
comments, the text. `describe` does not publish these tools' output fields — read the
first response and map each concept to its real field name before writing the gate;
treat any field that is not reliably present as a bonus, never as required.

**A reaction carries no content.** Only a comment's text is the person's own words. If
the payload has a synthesized label on a reaction (e.g. `"Like by <name>"`), it restates
fields you already have; quoting it as evidence of what someone said is fabrication with a
real field name attached.

## Step 5 — Canonicalize, then key

**Canonicalize the interactor URL before it is used for anything**: strip the query string,
strip the trailing slash, lowercase. The same person arrives with tracking parameters on
one post and bare on another, and un-canonicalized URLs make one human look like three.

Then build the interaction key:

```
interaction_key = clean_profile_url | interaction_type | canonical_post_url
```

That composite is what makes re-running the play idempotent: the same interaction on the
same post is the same key, so a weekly run adds new interactions instead of duplicating
old ones. Key on the **person**, not the interaction, when you aggregate in step 8 —
`interaction_key` is for deduplication, not for grain.

## Step 6 — The suppression gate (runs BEFORE any paid enrichment)

Four rules, evaluated **in this order, stopping at the first match**. A row can satisfy two
rules at once — a partner's company page is both rule 1 and rule 3 — so first match wins and
every dropped row is attributed to **exactly one** rule. Without that, the per-rule counts
are not reproducible, and counts nobody can reproduce are counts nobody can act on. Every
dropped row is counted and reported by rule: a silent gate is indistinguishable from a gate
that isn't running.

1. **Not a person.** Drop where the author-type field indicates a company/organization
   page. Where it is missing or unrecognized, fall back to the URL shape: a `/in/` path is
   a person, a `/company/` path is not. Two independent tests because the type field is a
   provider field and provider fields go missing.
2. **Not us.** Drop your own company page URLs and anyone on the employee roster from
   step 1.5. If no roster was supplied, this rule cannot run — say so in the output rather
   than pretending the gate was complete, and re-apply it after step 7 resolves employers.
3. **Not structural.** Drop partners, agencies, and investors named in step 1.
4. **Label, do not drop, the book.** Customers and open pipeline stay, tagged
   `existing_relationship`, and never enter the new-lead route.

A row that survives all four is a **candidate**. Nothing has been enriched yet.

## Step 7 — Resolve identity (candidates only)

For each surviving candidate, resolve the profile to a person and their current employer
(`harvestapi_get_profile` with `url`, usage-priced — read the charge from the run), then
the employer to a canonical domain (`crustdata_v3_company_identify`, free; see
resolve-company-domain). Two consequences to handle honestly:

- **A resolution miss is not a drop.** Keep the row with `account: unresolved` and the
  profile URL intact. A named human who engaged twice is actionable even without a domain,
  and dropping them hides the strongest signals behind an enrichment failure.
- **Re-run suppression rule 2 now.** This is where "not us" actually becomes checkable
  without a roster: an engager whose resolved employer domain equals the user's own domain
  is an employee, whatever their profile said.

## Step 8 — Aggregate to the person, then rank

Group interactions by `clean_profile_url`. Score each person by summing the weight of
their **distinct** `(post, interaction_type)` pairs — the same person reacting to the same
post twice counts once:

| Interaction | Weight |
|---|---|
| Comment | 3 |
| Share | 2 |
| Reaction | 1 |

`intensity = Σ weights over distinct (post, interaction_type) pairs`

| Intensity | Tier |
|---|---|
| ≥ 5 | `hot` |
| 3 – 4 | `warm` |
| 1 – 2 | `watch` |

The bands are exhaustive and non-overlapping over the integers the weights can produce, and
the minimum possible score for a surviving row is 1, so every candidate lands in exactly
one tier. A single comment (3) is `warm`; a comment plus any two other interactions (≥5) is
`hot`; one reaction is `watch`. Roll the same interactions up to the account grain by
summing person intensities within a resolved domain, and report both grains — a single `hot`
person and four `watch` people from the same account are different situations.

## Step 9 — Deliver, with the sample disclosed

Per person: name · clean profile URL · resolved title and account (or `unresolved`) ·
intensity and tier · the distinct interactions with dates · the comment text where there
is one · `existing_relationship` where it applies. Per account: summed intensity, the
people, the tier mix.

Then the part that makes the digest honest, and it is not optional:

- **Coverage.** How many posts were pulled, and **which posts had pages left unfetched** —
  by name, with the type that truncated. `"4 of 11 posts had more reaction pages than the
  2-page budget; the engager list for those posts is incomplete."`
- **Suppression counts, by rule.** How many rows each rule dropped, and explicitly whether
  rule 2 ran with a roster or only after resolution.
- **A quiet window is reported quiet.** No posts in the window, or no surviving candidates,
  is `0` with the reason. Never pad a digest by widening the window without saying you
  widened it, and never re-report last week's people as this week's triggers.

Hand the surviving rows to `score-inbound-leads` for scoring and routing. For a standing
version on a company page, offer the Deepline monitor in
`references/interaction-mechanics.md` §Standing version instead of a weekly re-pull. This play detects
and ranks; it does not score against an ICP, write outreach, or push to a CRM.

## What good looks like

- The user recognizes the names, and **isn't shown their own colleagues**.
- Every reported person traces to a specific post and a specific dated interaction.
- The digest states where the platform cut the sample off, so nobody reads a truncated list
  as a complete one.
- A re-run next week adds new interactions rather than re-reporting the same ones.
- The common failure: a long list of reactions from employees and company pages, ranked by
  nothing, presented as intent. The second-worst: the first page of reactions per post
  reported as the engagement, because nobody set or disclosed the page budget.

## Rules

- MUST set the page budget per type explicitly and record whether pages were left
  unfetched; never report a truncated list without saying it was truncated.
- MUST canonicalize the interactor URL (strip query, strip trailing slash, lowercase)
  before keying or deduplicating; NEVER key on the raw URL.
- MUST run the suppression gate before any paid enrichment; NEVER enrich first and filter
  after — it inverts the cost and buries the drops.
- MUST test person-vs-company on the author-type field AND on URL shape; NEVER treat a
  missing provider field as "person".
- MUST label existing customers rather than dropping them; NEVER route one as a new lead.
- MUST keep an unresolved candidate with the profile URL intact; NEVER let an enrichment
  miss delete a real signal.
- MUST report suppression counts by rule and the per-post coverage; NEVER present a filtered
  digest as the raw feed.
- MUST state the credit arithmetic before spending; NEVER run stage 2 across a post list
  without approval.
- NEVER claim a complete engager list, and NEVER infer that someone did not engage from
  their absence in a truncated sample.

## Worked example

Three monitored profiles: a founder and two AEs. The window is 14 days;
`postedLimit: "month"` returns 6, 3 and 2 posts respectively, of which 8 fall inside the
window. Reactions + comments at up to 2 pages each → `0.03×3 + 0.03×8×2×2 = 1.05 credits`
worst case, approved.

Reactions still had pages left on two of the eight posts — both flagged truncated. 214 raw
interactions collapse to 96 distinct `(person, post, type)` triples after canonicalization,
which is the first sign the URLs needed cleaning: 31 of those collapses were the same
people arriving with tracking parameters.

The gate drops 22 company pages (rule 1), 19 employees (rule 2, from the roster), and 4
agency accounts (rule 3) — 45 rows, reported by rule. Two customers are labelled, not
dropped. 49 candidates go to resolution; 41 resolve, 8 stay `unresolved` with their profile
URLs.

Ranking puts one person at intensity 8 — a comment on the founder's post (3), reactions to
three others (1+1+1), and a reshare (2) — and the digest shows that sum term by term rather
than asserting the total, because a tier nobody can recompute is a tier nobody trusts. One
account contributes
three `watch` people and no comments: interesting, but not the same as the single `hot`
commenter, and the account grain says so. The delivered digest leads with the two truncated
posts, because the person who matters most may be in the 350 reactions nobody can see.
