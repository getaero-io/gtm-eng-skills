---
name: webinar-followup-router
description: |
  Route webinar and event registrants into follow-up branches on three exact field reads — attended
  versus no-show, the account's qualification tier, and whether the account is net-new, an open
  opportunity or an existing customer — then draft per-branch copy and attach the right sender and CC
  to each row. The from-line and the copy are decided by different axes: routing collapses onto
  account status and tier, while attendance only changes what the email says. Use whenever someone
  asks: follow up on my webinar, segment my event registrants, who should email each attendee, draft
  post-event outreach, split attendees and no-shows, route my livestream leads to the right rep, or
  write follow-up copy per segment. Bucketing is deterministic field reads, never an LLM guess, and a
  row missing an axis is held rather than defaulted. Do NOT use it for scoring a list you already
  have into tiers (score-inbound-leads), routing raw product signups (enrich-signup-users), deciding
  who at an account is a buyer (buyer-classification), cleaning an address list before send
  (clean-email-list), or writing cold outbound with no event to reference.
category: route-and-automate
personas: [marketing, sales-development]
mechanism: logic-only
touches: writes-own-output
keywords: [webinar, event-follow-up]
ported_from: clay-run/clay-skill-creator/skills/davide-grieco/webinar-followup-router
---

# Webinar follow-up router (route on one axis, write on another)

The insight: **who the email comes from and what the email says are decided by different axes, and
treating them as one decision is what breaks event follow-up.**

The segmentation is a matrix of three facts about each registrant — attendance, the account's
qualification tier, and whether the account is net-new, an open opportunity or an existing customer.
Crossed, that is roughly two × four × three = **24 cells**. But the from-line takes far fewer values
than that, because **attendance does not change who sends.** A no-show at an existing customer and
an attendee at the same customer both come from the same person. So the same 24 cells collapse two
different ways:

| Decision | Axes it depends on | Distinct values |
|---|---|---|
| **Who sends, and who is copied** | account status, then tier | **3 arms** |
| **What the email says** | attendance × arm | **6 variants** |

Three consequences, and each one is a real failure mode rather than a tidiness argument.

**Cross the axes as one matrix and you get 24 variants nobody writes.** Twenty-four is past the
point where a human writes distinct copy, so the matrix quietly becomes one generic email with a
merge field — which is the outcome the segmentation existed to prevent. The collapse is what makes
the play executable at all.

**Route on attendance and the from-line goes wrong on exactly the accounts that matter.** Attendance
is the most visible field in a registrant export — it arrives labelled, populated, and needs no CRM
join — so it is the field a follow-up naturally branches on. Branch there and an existing customer
gets a follow-up from a shared team mailbox while their account owner learns about it from the
customer. Attendance is a copy axis. It is not a routing axis.

**All three axes are exact field reads, so nothing here needs an LLM to decide.** Attendance is a
campaign-member status. Tier is a field on the account. Account status is a CRM state. An LLM asked
to "work out the right segment" produces rows nobody can audit and a bill per row, for a decision
that is three lookups and a precedence order. The model writes prose. It does not assign the bucket.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The registrant list** | one row per person from the event — campaign members, registrants, an export or a table — carrying an email and an account or company identifier. For a Luma event, `luma_get_v1_events_guests_list` returns guests with per-ticket `checked_in_at` for attendance | no default; there is nothing to route |
| **Event context** | session title, date, recording or replay link, and the two or three substantive things actually covered | no default; without it the copy is generic and the deliverable is worthless |
| **Attendance field** | which field distinguishes attended from registered-no-show, and which values mean each | no default; it is the copy axis, and without it every email opens with a false claim about what the person did |
| **Qualification field, and the disqualifying values** | the field holding the account's tier or qualification band, and exactly which values are disqualified | ask which CRM or table holds it and which field. If they have no qualification band at all, treat every account as qualified, collapse to two arms, and SAY so in the output |
| **Account-status source** | how net-new, open-opportunity and existing-customer are told apart — which object and field, and which values map to which state | no default; without it the owned-account arm cannot be separated from the rep arm, and that is the arm where a wrong sender costs most |
| **Sender per arm** | for each arm: either a named mailbox, or a per-account lookup — the account owner, the assigned development rep — plus the field holding that person | **no default, ever.** A substituted from-line is not a recoverable error |
| **CC per arm, and why** | who is copied on each arm, and the reason — visibility for a manager, weight from an exec, the owner because someone is sending on their behalf | ask per arm. An arm whose CC was never stated ships with **no CC** rather than a guessed one, and the output says which arms those were |
| **Precedence between account status and tier** | which wins when an existing customer sits in a disqualified tier | this skill checks account status first (see Step 3), because a customer is a customer regardless of tier — but that is a reading, not a decision anyone made. Ask |
| **The messaging source of truth** | where the event's own positioning already lives, if anywhere — a campaign record's description, the invite or landing page, a brief, a run of show — and how to read it | there may genuinely be none, and then the copy is built from the event context above. Ask before writing anything: an installer who has a source and was not asked gets copy that contradicts how the event was sold |
| **Segments that get no email** | which segments, if any, are handled some other way — a task, a nurture, nothing at all | assume every segment gets an email, and say so. Never invent a non-email action |
| **Where the copy lands** | drafts for review, a CSV, or a sequencer or CRM object — and what identifies the destination | **drafts for review**, stated in the output. This skill never sends |

These are collected in Steps 1, 2 and 3, in that order. **Do not start a step before the steps above
it have their answers. If a declared input is missing, ask for it — never assume a default and continue.**

## What this skill touches

- **Reads** — the registrant list, the attendance and qualification fields you name, and your
  account-status source.
- **Writes** — only its own output: the drafts, to wherever you said drafts land. It never changes a
  record that already exists.
- **Never** — sends mail, enrolls anyone in a sequence, or writes to a CRM record. This play produces
  drafts for a human to review.

## Step 0 — Confirm the platform, and say where the work runs

Run `deepline preflight --json`. If the CLI is missing, install it (`npm install -g deepline &&
deepline auth register --wait auto`) and re-run. Say which org out loud before touching anything.

Then state where each part of the work happens, because that is what it costs:

| Part | Where it runs | What it costs |
|---|---|---|
| Reading the three axes off fields | a formula, or the agent | **nothing** |
| Assigning the arm and resolving sender and CC | the agent | **nothing** |
| Writing the copy | one prose generation per row — the agent itself for a small list, or a `deeplineagent` column in a play (priced from returned usage) | the only per-row charge in the play |
| Any enrichment | **not part of this play** | see below |

**This play buys no data.** Every field it reads is already in the registrant export or the record
beside it. If a row is missing an axis it is **held** (Step 4), not enriched — a person whose tier is
unknown is a person nobody has qualified, and paying to guess at it produces a routing decision with
no owner. If the installer wants missing accounts resolved or enriched first, that is a separate job
run before this one, and its cost belongs to that job.

## Steps 1–3 — The definition, in three passes, in this order

**The interview is three passes and the order is load-bearing.** Segmentation, then behaviour per
segment, then copy per segment. Run them out of order and the work is wasted rather than merely
untidy:

- **Copy before behaviour** produces polished emails for segments that turn out to be handled some
  other way, or that get no email at all.
- **Behaviour before segmentation** asks who sends to a group nobody has defined yet, and the answer
  changes the moment the group does.
- **Segmentation without the exact field names** produces a design that cannot be executed, and the
  gap only surfaces at the point of reading the data — after the copy has been agreed.

Do not compress the three into one pass. Finish each and read it back before starting the next.

### Step 1 — Segmentation logic, and the exact fields it reads

Three questions, and none of them is answered by an assumption:

1. **How do they want to segment?** Which facts about a person or their account define the groups.
   The author's own split is attendance × qualification band × account status, and that is an example,
   not a default — an installer may segment on fewer axes, or on different ones entirely.
2. **Where does each of those facts live?** Which system, and which object — the registration export,
   the campaign member record, the account, the opportunity.
3. **Which exact field, by name, and which values mean what?** Not "the tier field" but the field's
   actual name and its value list, with the values that count as disqualified named explicitly.

Read the segmentation back as a list of named groups with the field test for each one, and get an
explicit yes before moving on. **A group whose test cannot be written from named fields is not a
group yet** — say which fact is unavailable and let the installer either name a different field or
drop the axis. Never bridge the gap with a model's judgement about the person.

### Step 2 — Expected behaviour for each segment

For every group from Step 1, in turn:

- **Who sends** — a named mailbox, or a per-record lookup, and the field holding that person.
- **Who is copied, and why** — the reason decides whether the CC follows the group or the person.
- **What the email asks for** — a meeting, a reply, a piece of content, nothing.
- **Whether it gets an email at all** — a segment may be handled by a task, a nurture, or left alone.
  Ask; do not assume every group is an email.

**Stop here if a sender is missing.** No substitute exists, and a wrong from-line cannot be walked
back. This is the one place the play refuses to continue rather than degrading.

Read the behaviour back per group and get a yes before discussing a single line of copy.

### Step 3 — Copy per segment, from their source of truth first

**Ask where the event's messaging already lives before writing any.** A campaign record's
description, the invite or landing page, a brief, the run of show — somewhere in most organisations
there is a canonical statement of what the session was about and how it was sold. Where one exists,
the copy is built from it, and the skill says which source it drew on. Where one does not, say so and
build from the event context the installer described.

Then, per group: the angle, the specific thing from the session it references, and the one ask
already settled in Step 2. Agree these before generating anything, because copy is the only part of
this play that costs money per row.

If the source of truth and the installer's description of the event disagree, surface the conflict
rather than picking one. That disagreement is usually the most useful thing the interview finds.

## Step 4 — Read the axes off fields, and let `unknown` be an answer

One value per axis per person, read from the field named in Step 1, never inferred from a name, a
title or a domain. Enumerate every axis fully, including its abstention value — a play whose axes
have no `unknown` will fabricate rather than admit a gap.

The author's own three axes, as a worked shape:

| Axis | Values | Source |
|---|---|---|
| **Attendance** | `attended` · `no_show` · `unknown` | the campaign-member or registration status field |
| **Qualification** | `qualified` · `disqualified` · `unknown` | the account's tier or qualification field, against the installer's stated disqualifying values |
| **Account status** | `customer` · `open_opportunity` · `net_new` · `unknown` | the object and field the installer named |

`unknown` is not a bucket to be cleaned up later. It is the honest value when the field is empty, the
person did not match an account, or the field holds a value the installer's mapping does not cover —
and the third case is the one worth catching, because it means the mapping is incomplete rather than
the data being thin.

## Step 5 — Collapse to routing arms; first match wins, in this order

Arms come from Step 2, and one of them is always the hold arm. On the author's own split that is four
arms, no fifth, evaluated in order:

1. **`hold`** — any axis is `unknown`, or the row has no account match. No copy is written and no
   sender is assigned. Held rows are reported, never quietly dropped and never defaulted into an arm.
2. **`owned_account`** — account status is `customer` or `open_opportunity`. The named sender for this
   arm sends; the account owner is copied. Tier is not consulted.
3. **`net_new_qualified`** — account status is `net_new` and qualification is `qualified`. The
   account's assigned development rep sends.
4. **`net_new_disqualified`** — account status is `net_new` and qualification is `disqualified`. The
   shared team mailbox for this arm sends.

**Account status is checked before tier, and that ordering is a choice worth seeing.** A customer or
an open opportunity sitting in a disqualified tier still routes to the owned-account arm, on the
reading that a live commercial relationship outranks a scoring band. The reverse order is defensible
— it would send that person from a shared mailbox — so this is a declared input, not a fact. Ask, and
say which order ran.

**Resolve the sender and the CC per row before writing any copy.** An arm whose sender is a
per-record lookup can fail on an individual row — no owner on the account, no rep assigned — and a
row whose sender cannot be resolved moves to `hold`. It does not fall back to another arm's sender: a
fallback from-line is a silent misroute, which is the failure this whole play is arranged against.

## Step 6 — State the cost, and wait

Everything up to here was free. Prose generation is the only per-row charge, and it applies to the
routed rows only — held rows cost nothing. Report the count of rows that will bill, the per-row basis
and the total, and get an explicit approval before generating.

Generate one sample row per variant first — on the author's split that is six rows, covering every
combination — and let the installer approve the pattern before the rest runs.

## Step 7 — Generate the copy: attendance sets the opening, the arm sets the ask

On the author's split, six variants, each the intersection of two things already decided:

| | `attended` | `no_show` |
|---|---|---|
| **`owned_account`** | reference what was covered and connect it to work already in flight | lead with the replay, then the same connection |
| **`net_new_qualified`** | reference what was covered, then a specific first conversation | lead with the replay, then the same ask, lower-commitment |
| **`net_new_disqualified`** | thank, give the replay and the next session; no meeting ask | replay and the next session; no meeting ask |

Hard constraints on every variant, because the failure mode here is fluent invention:

- **Never claim attendance a `no_show` does not have**, and never claim a `no_show` said, asked or
  reacted to anything. Half a registrant list did not turn up, and copy that thanks them for their
  time is the single most visible way this play fails.
- **Never attribute a question, a poll answer or a comment to a person unless that row carries it.**
  If the export has per-person engagement, use it and say which field it came from. If it does not,
  reference the session, not the person's behaviour in it.
- **No invented numbers, outcomes or customer names**, and no positioning the source of truth from
  Step 3 does not support. Nothing goes in the copy that is not in the row, the messaging source, or
  the event context the installer supplied.
- **One ask per email**, and it is the ask agreed for that group in Step 2 — not a stronger one.
- Every row's copy names something specific from the session. If the material is too thin to do that
  in as many distinguishable ways as there are groups, say so and write fewer variants rather than
  padding.

## Step 8 — Deliver one row per person, with the reason attached

Per row: the person, their account, every axis value, the arm, the resolved sender, the resolved CC,
the subject and the body. **The axis values travel with the row permanently** — a bucket without them
cannot be audited, corrected or re-run, and "why did this person get this email" is the question that
gets asked first.

Then the coverage report, which is the part that makes the run reviewable:

- rows per arm, and rows `hold`, with the reason each was held broken out — missing tier, no account
  match, unresolvable sender, unmapped field value;
- which arms shipped with no CC because none was stated;
- which precedence order ran;
- which messaging source the copy drew on, or that there was none;
- whether every declared axis was actually available in the data.

State it at the top of the delivery, not in a footnote: **these are drafts, nothing has been sent,
and the held rows are not zeroes.**

## Step 9 — Hand off; never send

Write to wherever the installer said drafts land. **This play does not send mail, does not enrol
anyone in a sequence, and does not write to a record unless the installer named that destination in
Step 2.** A human reviews the from-line and the body before anything leaves. The whole point of
resolving a sender per row is that a person is accountable for the email — that stops being true the
moment the play sends it for them.

## What this skill does not claim

- The logic here came from an interview with one practitioner, not from a workflow whose results were
  measured. Nothing in it has been checked against a system that already ran.
- No claim that this segmentation outperforms a single follow-up email to everyone. No reply rate,
  meeting rate or open rate is asserted anywhere, and none was measured.
- The precedence between account status and tier was never decided by anyone. An existing customer in
  a disqualified tier routes as a customer here because that reading loses less, not because it was
  chosen.
- The CC was stated for one arm only — the account owner, on the owned-account arm. The other arms
  carry no CC rather than a guessed one.
- The arm count is three because three senders were described. Whether a fourth distinction is worth
  a fourth arm is unknown.
- Never run end to end, so there is no measured cost or latency per registrant.
- Nothing here validates that a person's account match is correct. A wrong match sends customer copy
  to a stranger, and this play cannot detect it.
- No claim that a qualification tier means the same thing in anyone else's CRM, or that a band named
  the same way is scored the same way.
- The three-pass interview order is one practitioner's stated sequence. That running it out of order
  wastes work is reasoning, not something measured against runs that did it both ways.
- The figures in the worked example are illustrative, chosen to show the shape of a run and the
  arithmetic of the collapse. They are not measurements from a real registrant list.

## What good looks like

- Every routed row carries all three axis values, so any bucket can be argued with by reading it.
- Held rows exist, are counted, and name why they were held. A run with zero held rows on a real
  registrant list is a sign the axes were defaulted, not a sign the data was clean.
- No email claims attendance, a question or a comment that its row does not carry.
- Every from-line was stated by the installer or resolved from a named field. No row got a fallback
  sender.
- The precedence order, the messaging source the copy drew on, and whether every declared axis was
  actually available are all visible in the delivery.
- The three definition passes each ended in an explicit yes, and no copy was written for a segment
  whose behaviour had not been settled.
- The commonest failure: branching on attendance because it is the field that arrives populated, so
  a customer receives a shared-mailbox email and their account owner hears about it from them.
  Second-commonest: handing the segmentation to a model — the rows look plausible, cost money, and
  cannot be audited or re-run to the same answer.

## Rules

- MUST complete the definition in three passes in order — segmentation, then behaviour per segment,
  then copy — and read each back for a yes before starting the next; NEVER discuss copy for a segment
  whose behaviour is unsettled.
- MUST collect the exact field name and value list for every axis; NEVER accept a described segment
  whose test cannot be written from named fields.
- MUST ask where the event's messaging already lives and draw from it where it exists; NEVER invent
  positioning for the event when a source of truth was named.
- MUST ask whether a segment gets an email at all; NEVER assume every segment is an email.
- MUST read every axis from named fields and carry them into the output; NEVER infer an axis from
  a job title, an email domain or a company name.
- MUST run every free step — reading axes, assigning arms, resolving senders — before anything
  bills, and MUST state the per-row cost and get approval before generating copy.
- MUST assign the arm deterministically in the stated order; NEVER ask a model to choose the segment.
- MUST resolve the sender and CC per row before writing copy, and MUST move a row to `hold` when the
  sender cannot be resolved; NEVER fall back to another arm's sender.
- MUST ask for the sender of every arm and stop if one is missing; NEVER substitute a plausible
  from-line.
- MUST route on account status before tier, or on the order the installer stated, and MUST say which
  ran.
- MUST report held rows with their reasons; NEVER default an `unknown` axis into a bucket.
- NEVER claim attendance, a question, a poll answer or a comment that the row does not carry.
- NEVER put a number, outcome or customer name in the copy that is not in the row, the messaging
  source, or the event context the installer supplied.
- NEVER send, enrol or write to a CRM record; this play produces drafts for a human to review.

## Worked example

412 registrants from a 45-minute session, exported with a campaign-member status, joined to accounts
carrying a four-band tier and a CRM state.

Axes read, free: 168 `attended`, 244 `no_show`. 31 rows have no account match and 9 more have an
empty tier — **40 rows to `hold`** before anything is written, and the hold report separates the two
causes because they get fixed by different people.

The remaining 372 collapse: 88 `owned_account` (54 customers, 34 open opportunities), 201
`net_new_qualified`, 83 `net_new_disqualified`. Six of the 88 have no account owner on the record, so
their sender cannot be resolved and they move to `hold` too — 46 held in total, not 40, and that
difference is the sender-resolution rule doing its job rather than a fallback quietly firing.

Note what the collapse did: 24 cells became **3 arms and 6 copy variants**, and the two customers in
the disqualified tier routed to `owned_account` — flagged in the delivery, because the precedence
that put them there was a reading and not a decision.

The session's own campaign description was the messaging source, so the copy drew on how the event
was actually sold rather than on a fresh angle. 366 rows bill for one generation each — one sample
per variant approved first, then the rest.

Delivered: 366 drafts, each with its three axis values, its arm, a resolved from-line and a CC on the
88 owned-account rows only; 46 held rows with causes; and a header stating that the tier axis was
four-band, that account status was checked before tier, that two arms carry no CC because none was
stated, and that nothing has been sent.
