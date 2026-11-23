---
name: route-inbound-demo-requests
description: |
  Route inbound demo requests to the right queue — enterprise sales, mid-market, or self-serve —
  using company size and the requester's role, with an explicit needs_human_review outcome for
  requests that fit no rule. Use whenever someone asks: route our demo requests, who should follow up
  on this inbound, split inbound by segment, or set up demo request triage. Do NOT use it to enrich
  the signup first (enrich-signup-users), to score lead quality (score-inbound-leads), or to write
  the follow-up email (personalized outbound skills).
---

# Route inbound demo requests

> **This skill came from an interview, not from a play.** The source play carried no comparisons, so
> the yield check routed to the interview rather than converting. Its thresholds are the creator's
> stated intent — nothing compared them against a system that already ran, and the section below
> saying what it does not claim is where that is written down.
> This example exists to show what that outcome looks like: a complete, usable skill with an honest
> label, instead of a skill fabricated from column names.
> It also shows what a good `## Representative output` does. Two of its four rows are *held*, not
> routed; every row names the rule that fired and the value the decision used; the counts are whole
> numbers because nothing here measures tenths; and the coverage line says what was skipped and why.
> A table of four successes teaches the reader that this skill always succeeds.

The insight: **the request that fits no rule is the one worth a human.** Most routing skills force
every row into a queue, which means the ambiguous ones land wherever the last `else` points.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The requests** | `email` required; `company_name` and `job_title` if they have them | no default — with only an email, rule 1 catches most of the volume and that is the correct outcome, not a failure |
| **Queue names** | what their three destinations are actually called | ask — `enterprise` / `mid_market` / `self_serve` are this author's words, and a skill that hardcodes them routes into queues that do not exist |
| **Size thresholds** | the headcount cut between enterprise and mid-market | the author used **1,000 and 50** and those numbers came from an interview, not from a system that ran. Ask; if the installer has no view, use them **and say they are borrowed** |
| **Seniority definition** | which titles count as senior enough to escalate | the author used director-and-above. Ask, because the same title means different things across companies |
| **Human-review triggers** | what makes a request ambiguous *for them* — competitor domains, student roles, partner enquiries | ask — this is the rule the skill exists for, and it is the one most specific to a business |

**Why a thin skill still has five inputs.** The yield check routed this to an interview because the
play held no comparisons — but a routing decision is *all* context, so almost everything in it belongs
to the installer. Thresholds an author states in conversation are the easiest thing to hardcode by
accident and the fastest way to make a skill work for exactly one company.

## Step 1 — Take the request

Fields: `email`, `company_name` (optional), `job_title` (optional).

## Step 2 — Route, in precedence order. First match wins.

1. `needs_human_review` — free-email domain with no company name, or a role reading as a student, a
   job seeker, or a competitor. **Checked first**, deliberately.
2. `enterprise` — company size **1,000 or more**, or a director-level-and-above title.
3. `mid_market` — company size **50 or more**.
4. `self_serve` — everything else.

## Representative output

### Routed request log

214 requests came in. 209 were routed automatically and 5 were held for a person to look at.

| Who asked | Company | Their role | Size we used | Why it went there | Queue |
|---|---|---|---|---|---|
| dana@northwind.example | Northwind Logistics | VP Operations | 1,400 people | 1,000 or more, so enterprise. Her title would also have qualified | `enterprise` |
| sam@contoso.example | Contoso Tooling | Office Manager | 120 people | over 50 but under 1,000, and the title is not senior enough to escalate | `mid_market` |
| pat@gmail.example | — | — | not supplied | a personal email address with no company name — there is nothing here to route on | `needs_human_review` |
| lee@fabrikam.example | Fabrikam | Student, MSc Marketing | 900 people | held *before* size was considered, so a student at a 900-person company does not land in mid-market | `needs_human_review` |

The queue names are the installer's own — `enterprise`, `mid_market`, `self_serve` and
`needs_human_review` are this author's words and get replaced with whatever their queues are called.

### Coverage line

5 requests held: 2 personal email with no company, 3 on the role. The size column was filled in on
176 of 214 requests; the remaining 38 were routed on job title, or fell through to `self_serve`.

## What this skill does not claim

- Logic came from the creator interview, which has no ground truth in a play — it is the creator's stated intent, not a mechanism verified against a system that already ran.
- No deterministic claims existed to compare, so no threshold was traced to source code. Never run against real inbound.

## What good looks like

- `needs_human_review` has a real, non-zero rate. If it is always empty, rule 1 is not firing and
  ambiguous requests are being routed by accident.
- Every routed request carries the field values the decision used.
- The common failure: routing on company name alone. "Acme Consulting" says nothing about size.

## Rules

- MUST evaluate `needs_human_review` before any segment rule.
- MUST emit the values the routing decision used.
- NEVER route a free-email request to enterprise on title alone.
