---
name: build-event-invite-list
description: |
  Turn one CRM campaign record for a first-party event — a customer dinner, a roadshow, an executive
  roundtable, your own conference — into a ranked invite list, per-bucket invite copy, and sequencer
  enrollment. Starts by asking which relationship the room is for (existing customers, open
  opportunities, net new, or a combination), which accounts are eligible, and which seniority,
  persona and city to target, then fills only that room. Holds owned accounts for rep approval
  instead of auto-sending. Use whenever someone asks: build the invite list for this event, who
  should we invite to the dinner, fill the room for our conference, who do we invite to this
  Salesforce campaign, pull an invite list for the roadshow, find CMOs in San Francisco for our
  dinner, draft invite copy and sequence it in Gong, help me fill 20 seats in New York. Do NOT use it
  for scoring or tiering a book of accounts you already have (account-tier-scoring,
  score-inbound-leads), building a prospect list from an ICP definition with no event attached
  (build-prospect-list), following up with people after an event has happened, or finding people at a
  single named company (find-decision-makers-at-company).
category: build-lists
personas: [marketing, sales-development]
mechanism: functions
touches: writes-records
keywords: [event-follow-up, sequencer]
ported_from: clay-run/clay-skill-creator/skills/davide-grieco/build-event-invite-list
---

# Build an event invite list from a CRM campaign (scope the room first, then fill it)

**The insight: the first question is which relationship the room is for, and it decides everything
downstream — the eligible accounts, the seniority worth inviting, the copy, and the bill.** A
customers-only dinner and a net-new dinner can share a premise, a venue and a date and still overlap
on almost nothing: different accounts qualify, different titles are worth a seat, the copy has
nothing in common, and one of them spends zero on sourcing while the other spends on every seat.

Most invite lists get built the other way round — pull everyone who fits, then discover at copy time
that three incompatible audiences are on one list with one template to serve them. So this skill
asks for the room's scope **before** it reads anything, and everything after that is downstream of
the answer.

Three consequences, and they are the architecture:

- **Three relationship buckets** — expansion (existing customers), acceleration (an open
  opportunity), net new (neither) — resolved in a fixed order, because a person can qualify for two
  and the copy cannot be written until exactly one is chosen. **The scope answer selects which
  buckets are even in play**, and an out-of-scope bucket is never sourced, never priced, never
  written for.
- **Everything free runs first.** Account eligibility, geography, seniority and the per-account cap
  all cut the population before a single credit is spent.
- **Proximity is a filter, not a ranking input.** For a located event, someone who cannot get to the
  venue is not a worse invite — they are not an invite.

**Do not start a step before the steps above it have their answers.** If a declared input is
missing, ask for it — never assume a default and continue.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and if an answer does not exist say which step becomes
unavailable rather than guessing. Where a default IS defensible it is named below, and using it
means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The CRM** | which CRM holds their campaigns, and which objects and fields carry campaign, account, contact, opportunity, owner, account tier and customer status. Ask at install time — do not assume | no default; every step depends on it. Stop and ask |
| **The campaign** | the identifier of the one campaign record for this event | no default — there is no event to invite anyone to |
| **The event brief** | premise, date, city or venue, seat count, and who is hosting or speaking | no default. Step 1 stops rather than inventing an event |
| **Room scope** | which relationships this room is for: existing customers, open opportunities, net new, or a named combination | **no default, and this is the first question.** It decides which buckets are sourced and priced |
| **Account eligibility** | the account-level filter that says which accounts qualify at all — a tier, a segment, a named list, a region, a product fit | no default. Running with every account in the CRM is a legitimate choice but must be said out loud, because it is the single biggest driver of cost |
| **Customer definition** | which field or state means "we already work together" — a closed-won opportunity, a lifecycle stage, an active-subscription flag | no default; without it expansion and net new cannot be separated and the buckets collapse |
| **Seniority and persona** | the seniority rule (an exact level, or a floor like "Director and above"), the function or team, and any title keywords. See Step 2 for the shape both surfaces accept | no default — "senior" and "operator" mean different things per market. Ask |
| **Event city or region** | the venue city, and how far out still counts | for a located event there is no default and no skipping. For a virtual or multi-city event, say so explicitly and the proximity filter is disabled by declaration, not by omission |
| **Geographic field precedence** | whether proximity is read off the contact's own location, the account HQ, or either | either, with the deciding field named per row |
| **Max contacts per account** | how many people per account may be invited | **3 is the recommended default** — enough to reach a buying group, few enough that one account cannot take the room. Using it means saying so |
| **Invite-to-seat ratio** | how many invites they send per seat, from their own past events | the author used **3×** and never measured it. Use it only after saying out loud that it is borrowed and unmeasured |
| **Copy preference** | their own voice: a sample invite that worked, tone rules, length, anything banned. Ask, and ask for a sample rather than adjectives | the four beats in Step 8 are the author's editorial standard, not a tested format. Say that it was used in the absence of theirs |
| **Sender identity** | who the invite comes from — a named host, an exec, the account owner, or per-bucket | no default. The sender decides how the invite reads and is not the skill's to pick |
| **Approval mode** | `review`, `hybrid` or `auto` — see Step 9 | **`hybrid` is the recommended default** and using it means saying so |
| **Suppression list** | who must never be invited — competitors, churned accounts, do-not-contact, anyone already invited to another event this quarter | no default. Run with an empty suppression list only after saying so |
| **The sequencer** | where their sequences live, which sequence is the invite sequence, and whose sequence instance it enrolls under. Ask at install time | Steps 9 and 10 become a CSV handoff instead of enrollment. Say so rather than skipping silently |

**Two of these are vendor-shaped and the skill is honest about it.** The CRM read below was
originally built against Salesforce (SOQL), and the sequencer enrollment against Gong Engage. The
*play* carries to any CRM and any sequencer, but the tool and the field names do not — so Step 0
confirms the tools for the installer's own stack in Deepline rather than assuming these two.

## What this skill touches

- **Reads** — your CRM (accounts, contacts, ownership and campaign membership), the event brief and
  room scope you supply, and Deepline's people search for net-new attendees.
- **Writes** — **new records in your CRM and enrollments in your sequencer.** Both are gated behind an
  explicit approval, and the approval mode you pick decides whether anything enrolls without a human
  looking first.
- **Never** — enrolls anyone before that approval, and never enrolls a sourced person who has no CRM
  record, because the sequencer identifies people by record id.

## Step 0 — Confirm the platform, and say where the work runs

Run `deepline preflight --json` and state the org out loud (missing CLI: `npm install -g deepline &&
deepline auth register --wait auto`), then confirm the tools this run depends on.

```
deepline tools search "<crm> contacts" --json        find the CRM read and write tools
deepline tools describe <tool_id> --json             the real input names, output fields, pricing
```

**Never bind an input from a tool's name or its outputs — read the schema.** A tool that returns a
"not connected" error means the installer's CRM or sequencer is not connected to their Deepline org;
that step becomes a CSV handoff, and the output says so.

**Where the computation happens is what it costs.** Scoping, eligibility, bucketing, ranking,
deduping and the invite copy all happen in the agent reading this skill, at zero credits. Only two
steps call priced tools. If a named tool is absent from the installer's catalogue, **fail loudly and
say which step is unavailable** — never substitute the nearest thing, because a substituted tool
returns a full row and a full row looks like a correct one.

## Step 1 — Say what the run will do, then interview in two tiers

**Never present the declared-inputs table as a form.** Sixteen fields on one screen is not an
intake; it is a bill of materials, and the installer cannot tell which answers matter. Ask instead —
one decisive question at a time, then one block of recommendations to confirm.

### 1a. The preamble, before the first question

Say this up front, in four short lines, so nothing later arrives as a surprise:

- **what it reads** — their campaign, accounts, contacts, opportunities and owners, at no credit cost;
- **what it spends** — only if net-new sourcing is in scope, and only after they approve a number;
- **what it writes** — new records in their CRM and enrollments in their sequencer, both gated
  separately at the end, neither on this pass;
- **where it stops** — before any spend, before any write, and before anything sends.

Then set the shape of the intake itself: **six questions that change the work, then one screen of
recommended settings to accept or amend.** Someone who knows how long a thing takes answers it
better.

### 1b. Tier one — the six that change the work, asked one at a time

For each: one sentence of context, then the question, then a recommendation with its reason. **Wait
for an answer before asking the next.** Two questions in one message means the second gets lost.

**1. Room scope.** *This is the question everything else hangs off, and it is why it is first.*
> Who is this room for — existing customers, accounts with an open opportunity, net new, or a
> combination?

*Recommend:* for a dinner or roundtable, **one or two**, not all three — a room holding all three is
hard to seat and harder to write for. For a conference, all three is normal. **If customers are out
of scope this run spends nothing on sourcing**, so say that when they answer.

**2. Account eligibility.** *This is the largest single driver of what the run costs.*
> Which accounts are eligible at all — a tier, a segment, a named target list, a region?

*Recommend:* **their top one or two tiers, or the named target-account list they already trust.** An
unfiltered CRM read is allowed and produces a list nobody acts on. If the answer is "all of them",
that is a real choice and it gets stated in the output.

**3. Seniority, function and city — asked as one triple.** *Because that is how people describe an
event, and because the answer has to work on two different surfaces.*
> Which seniority, which function or team, and which city?

*Recommend:* for a working-level room, **a floor plus a function** — "Director and above in Sales" —
because an exact title misses everyone doing the job under a different name. For a true executive
room, **an exact level plus title keywords**, because a floor at C-suite returns every officer in the
company. Translate their answer in front of them using Step 2 before moving on.

**4. Seats, and the invite-to-seat ratio.** *The ratio decides how deep the list is cut, so a wrong
one either wastes the room or overfills it.*
> How many seats, and how many invites do you normally send per seat?

*Recommend:* **3× if they have no history to go on** — and say plainly it is a borrowed number that
was never measured, so it lands as a placeholder rather than as their own figure.

**5. Sender and voice.** *Both change how the invite reads more than any word choice in it.*
> Who does this come from, and do you have an invite of your own that worked?

*Recommend:* **the account owner for owned accounts and the named host for everyone else**, so the
name matches the relationship. And **ask for a sample invite rather than tone adjectives** — one real
email they were happy with is worth more than three words describing a voice. If they have one, it
supersedes the standard in Step 8 entirely.

**6. Approval mode.** *This decides whether anything can send without a human seeing it.*
> Should a person approve each invite before it goes, or should the list send on its own?

*Recommend:* **`hybrid`** — owned accounts to the rep's queue, unowned and net-new enrolling
automatically. It protects the failure that actually happens, a marketing invite landing on someone
else's live deal, without stalling the whole list behind eleven inboxes. Name all three modes from
Step 9 so the choice is theirs.

### 1c. Checkpoint — restate before asking for anything else

Before the second tier, say back what the run now looks like given those six answers: which buckets
are in play, roughly how many accounts are eligible, whether Step 6 will spend anything at all, and
what still has to be approved. **A mid-intake mirror is what stops a wrong answer three questions
back from surviving to the end.**

### 1d. Tier two — one screen of recommendations, accepted wholesale or amended line by line

Present as a table, invite them to change any row, and move on when they say it looks right.

| Setting | Recommended | Why this default |
|---|---|---|
| **Max contacts per account** | **3** | enough to reach a buying group, few enough that one enthusiastic account cannot take a third of the room |
| **Radius around the venue** | the venue's **metro area**, not the wider region | people travel across a city for a dinner and not across a state |
| **Which location field decides** | **either** the contact's own location or the account HQ, with the deciding field named per row | contact-level location is better and is often blank; naming the field per row keeps it auditable |
| **Suppression starting set** | competitors, churned accounts, do-not-contact, and anyone already invited to another event this quarter | the last one is the easiest to forget and the most annoying to receive |
| **Title match mode** | **smart** | contains over-matches, exact under-matches; pick another deliberately if they know their titles are unusual |
| **Sourcing breadth** | **full records**, not `preview` | a seat-constrained event needs the location and employment fields that preview mode may omit |
| **Out-of-scope buckets** | **reported with counts, never deleted** | someone always asks how many customers were set aside |
| **Rows that cannot be bucketed** | **reported as unbucketed**, never folded into net new | this is the failure that sends a stranger's email to a customer |
| **Customer definition** | **no default is possible — this row must be answered** | which field means "we already work together". Without it, expansion and net new cannot be separated and the skill says that split is unavailable rather than guessing it |

**An accepted recommendation is a borrowed value, and the output says so.** This is the rule that
keeps the intake honest: a number the installer actively chose and a number they waved through are
different things, and only one of them is theirs. Record which is which and report it at delivery.
**Never let a default pass as the installer's own answer.**

### 1e. Then the event brief

An empty campaign record carries a name, a date and a type. It does not carry the premise, the seat
count, the venue city, or who else is in the room. **Ask. If the answer is not available, stop.** A
list built against a guessed premise is confidently wrong about who would want to be there.

1. **Premise** — why this event exists, in one sentence, in their words. This becomes the *why* beat.
2. **Date, and city or venue** — or an explicit statement that it is virtual or multi-city.
3. **Who is hosting or speaking** — this is the *who* beat, and on a first run it is the only honest
   answer to it. See Step 8.

## Step 2 — Translate the persona onto both surfaces

The Step 1 triple has to be expressible on **both** the CRM read and the people-search tool, and
the translation is where personas quietly go wrong. Do it in front of the installer and confirm it.

**How three real requests actually translate**, and the second one is the trap:

| What they said | Seniority | Function | Title keywords | City |
|---|---|---|---|---|
| CMOs in San Francisco | exact `c-suite` | Marketing and Public Relations | **required** — `CMO, Chief Marketing Officer`, because `c-suite` alone returns every C-level officer | San Francisco |
| RevOps operators in Dallas | leave open, or a low floor | **none fits** | **required and load-bearing** — `Revenue Operations, RevOps, Sales Operations, GTM Operations` | Dallas |
| Director and above in Sales, New York | floor mode, floor `director` | Sales | optional | New York |

**The trap: RevOps is not a job function.** The taxonomy the author read (Clay's people search, one
day in 2026) carries Sales, Marketing and Public Relations, Business Management and Operations,
Finance, Engineering and around two dozen more — and no revenue-operations entry. Crustdata's
`function_category` is a different taxonomy; check it with the free
`crustdata_v3_person_search_autocomplete` before assuming either way. A persona that does not exist in the taxonomy **must** be expressed as
title keywords; picking the nearest-sounding function instead returns confident, wrong people. Check
every requested persona against the live options list before binding it, and where none fits, say so
and use keywords.

Two mechanical facts worth confirming with them:

- **Seniority has two modes.** *Exact* matches only the levels named; *floor* matches a level and
  everything above it. "Director and above" is a floor; "CMO" is exact plus a keyword. Getting this
  backwards is the difference between 12 people and 400. `crustdata_v3_person_search` has no floor
  operator: express a floor as an `in` list of the level and every level above it on
  `experience.employment_details.current.seniority_level` (at most 5 values per `in`).
- **Title matching** — `contains` (over-matches), `=` / `in` (exact, under-matches) on
  `experience.employment_details.current.title`. There is no "smart" mode; use an `or` group of
  `contains` conditions on the keywords.

## Step 3 — Read the CRM, free, filter to eligible accounts, and bucket

Nothing here bills Deepline credits. Read the campaign, then the account, contact, opportunity and
owner records — **with the account eligibility filter and the geographic filter in the query itself**
where the CRM tool allows it, not applied afterwards in the agent. Filtering at the source is what
makes this step free and small.

| CRM | Deepline tool | Filter at the source? |
|---|---|---|
| **HubSpot** | `hubspot_search_objects` (contacts, companies, deals) — free | **yes**: put eligibility, city and seniority into its property filter groups |
| **Attio** | `attio_query_records` | **yes**: structured filter objects |
| **Salesforce** | `salesforce_list_accounts`, `salesforce_list_contacts`, `salesforce_list_opportunities` — free | **no.** These page through records (`limit`, `modified_after`, `next_records_url`) with no `WHERE` clause, and **no Deepline tool reads Salesforce campaign membership or runs SOQL.** Page to the end, filter in the agent, and say the read was unfiltered. For campaign members, ask for a report export |

| | |
|---|---|
| **What to verify** | read the whole response rather than a promised path. Confirm the record count is non-zero and that the fields you asked for came back populated — a query can succeed and return rows with the field you need blank |
| **Cost** | no Deepline credits per `describe`. It consumes the installer's CRM API allowance, which is theirs to spend |

For another CRM, find its read tool with `deepline tools search` and read its schema. The play does
not change; the tool and the input names do.

### The three buckets, resolved in this order — first match wins

| Order | Bucket | Condition | Why it is ordered here |
|---|---|---|---|
| 1 | **Expansion** | the account meets the installer's customer definition | "we already work together" is the strongest thing copy can stand on, so it wins even when an open opportunity also exists |
| 2 | **Acceleration** | not a customer, and has an open opportunity | a live deal is a stronger context than a cold introduction |
| 3 | **Net new** | neither | |
| — | **Unbucketed** | the customer definition or opportunity state could not be read | **a real value, not a failure.** Report these rather than defaulting them into net new, which is what silently sends a stranger's email to a customer |

**Four values, no fifth.** A row that cannot be bucketed is reported as unbucketed and excluded from
copy generation. Never coerce it.

**Then apply the room scope from Step 1.** Out-of-scope buckets are set aside with their counts
reported — they are not deleted quietly, and they are not carried forward into pricing or copy.

Capture per candidate, because later steps need them: account owner, account tier or eligibility
value, contact location, account HQ, title, seniority, last activity date, and the CRM record id —
**the record id is required**, because the sequencer in Step 10 identifies people by CRM id, not by
email.

## Step 4 — Free elimination, before anything paid

Every one of these is free, and each one is reported with a count.

- **Proximity, as a hard filter.** For a located event, drop anyone outside the city or region rule
  and name the field that decided it. Someone who cannot reach the venue is not a lower-ranked
  invite; they are not an invite. Disable this only where the event was declared virtual.
- Apply the suppression list.
- Drop anyone below the seniority floor or outside the persona.
- Drop duplicates across accounts and within them.
- **Apply the per-account cap**, keeping the highest-ranked contacts by the Step 7 order.
- **Check who is already in a sequence.** Gong Engage: `gong_get_prospects_assigned_flows`, input
  `crmProspectsIds` from the CRM read, free. Read `prospectsAssigned` and each flow instance's status;
  someone mid-sequence is a hold, not a send. Other sequencers: `instantly_list_leads` with `search`,
  `smartlead_list_campaign_leads`, `lemlist_export_campaign_leads`.

**Name what this saved.** "Eligibility and proximity removed 302 of 486 candidates before any paid
call" is the sentence that justifies the ordering, and it belongs in the output.

## Step 5 — State the cost, get approval, and wait

Only eligible accounts, in an in-scope bucket, that the CRM could not fill reach Step 6. **If net new
is not in scope, this step costs nothing and Step 6 does not run — say that rather than pricing a
stage that will not happen.**

Present, and do not proceed without a yes:

- how many accounts need net-new sourcing, and how many people per account after the cap;
- the per-call catalogue figures **labelled as catalogue figures**, with the note that declared and
  billed cost differ by plan and that **a miss can bill**;
- that Step 10 writes to the CRM and to the sequencer, which is a mutation, not a read.

**Spend without a stated number is spend without consent.** Read the real charge from
`deepline runs get <run-id> --full --json` (or `deepline billing usage` for direct tool calls)
afterwards and report what was actually billed — never the catalogue figure, and never an org
balance delta, which moves for reasons other than this run.

## Step 6 — Source net-new people, only where scope and the CRM both call for it (paid)

Skip entirely unless net new is in scope. Run only against eligible accounts the CRM could not fill.

**Paid step one — find people at the account.**

| | |
|---|---|
| **What runs** | `crustdata_v3_person_search` |
| **What goes in** | `filters` with `op: "and"`: `experience.employment_details.current.company_website_domain` `=` the account domain; the Step 2 triple bound exactly — `current.seniority_level` (an `in` list for a floor), `function_category` **only where a real one fits**, `current.title` keyword conditions otherwise; `basic_profile.location.city` for the venue city. `limit` set to a little above the per-account cap |
| **What to verify** | `profiles[]` non-empty and `total_count`. Then per person: the current employment's `company_website_domain` echoes the account domain you asked for — **compare with the TLD excluded**, because `com` substring-matches almost anything and washes the check out. A wrong-entity hit is shaped exactly like a right one; this echo is the only detector |
| **Cost** | **0.02 Deepline credits per returned result** per `deepline tools describe`; empty pages are free. Read the billed charge afterwards |

**Two traps, and both change the design.**

- **`in` takes at most 5 values.** Crustdata silently ignores longer arrays, so a seniority floor or a
  title list longer than five is split into separate conditions or searches and merged.
- **`preview: true` is cheaper** but returns only basic fields — not necessarily the location and
  employment detail that the proximity filter and the wrong-entity check need. Use full records for a
  seat-constrained event; use preview only for a large event, and say in the output that those rows
  were neither employment-verified nor proximity-verified.

**Paid step two — find the work email**, for sourced people only. People already in the CRM have one.

| | |
|---|---|
| **What runs** | the prebuilt play `prebuilt/name-and-domain-to-email-waterfall-batch` — chosen because it takes a bare domain, so an account list needs no profile-resolution call first. `prebuilt/person-linkedin-to-email-batch` is the alternative when every sourced row has a profile URL |
| **What goes in** | a CSV with `first_name`, `last_name`, `domain` (optional `company_name`, `linkedin_url`): `deepline plays run prebuilt/name-and-domain-to-email-waterfall-batch --input '{"csv":"sourced.csv"}'` |
| **What to verify** | `email_found_and_valid` true **and** `email` non-empty — an empty value is a miss, and completion status is never data. A miss carries `miss_reason` |
| **Cost** | depends on which provider in the cascade hits; read it from a 3-row pilot with `deepline runs get <run-id> --full --json`. **A miss can bill**: budget for misses and report them as spend |

Where an email cannot be found, the person is `no-contact-path` and drops out. Do not carry them
forward with a guessed address.

## Step 7 — Rank inside each bucket, then cut to the invite target

Ranking is **within** a bucket, never across them — buckets are audiences, not tiers, and a customer
does not outrank a live deal or the reverse. The scope answer already set the mix.

Inside each bucket, order by: seniority against the rule, then account eligibility value where it is
ordered (a tier is), then recency of last activity. **Proximity is not in this list** — it was a
filter in Step 4, and anyone still here already passed it.

Cut each in-scope bucket to its share of `seat count × invite-to-seat ratio`, and **report the ratio
used and whether it was theirs or the borrowed 3×**. Deliver the counts per bucket before the copy,
so the mix can be corrected while it is still cheap.

## Step 8 — Write the copy: one email per in-scope bucket, in their voice

**Ask for their voice before writing.** If they supplied a sample invite or tone rules, follow them
and say so. Only where they have none does the standard below apply — and then say that too.

**It must not read as a marketing email.** Short, punchy, concise, human. Four beats:

1. **Why** — the premise, in one line, from Step 1.
2. **Who** — who else is in the room.
3. **When** — date, city, and what the evening or the day actually is.
4. **Why them** — one sentence on why you thought of *this person*. This is the beat that earns the
   reply and the one that cannot be templated.

**One draft per in-scope bucket, never one merged template**, because the *why them* beat draws on
different evidence in each:

| Bucket | What the relevance line stands on |
|---|---|
| **Expansion** | the existing relationship — what they already run with you, who else at their company you work with |
| **Acceleration** | the live conversation — what they told you they cared about, where the evaluation is |
| **Net new** | their role and the account's own context, since there is no relationship to draw on. This is the hardest of the three and the most likely to read as generic — if there is nothing specific to say, say less rather than padding it |

**A note on the "who" beat that only bites on the first run.** The campaign starts empty, so on the
first pass there are no confirmed attendees. The honest answer to *who* is the host and the speakers
from Step 1 — **never a list of people who have not accepted.** Naming invitees as attendees is a
claim about other people's plans that you do not have.

Show every draft and get it approved before Step 9. Copy is the cheapest thing to fix here and the
most expensive thing to fix after sending.

## Step 9 — Route the list by the approval mode they chose

**Three modes, no fourth.** Ask in Step 1; do not infer one from how the list looks.

| Mode | What happens |
|---|---|
| **`review`** | nothing enrolls until a human approves it. Owned rows go to the account owner, unowned rows to the named reviewer or SDR. The slowest and the safest |
| **`hybrid`** — *recommended* | owned rows go to the account owner's queue; unowned and net-new rows enroll automatically. Protects the failure mode that actually happens without stalling the whole list |
| **`auto`** | the whole approved batch enrolls, no per-row review. Reasonable for a net-new-only room on unowned accounts; **say plainly that no rep sees it first** |

Regardless of mode: **anyone already in a sequence from Step 4 is a hold**, and a held row does not
enroll. **Do not treat silence as approval.** Hand each queue to its named reviewer with the bucket,
the ranking evidence and the drafted email attached.

## Step 10 — Enroll the approved, and deliver

**Net-new people must exist in the CRM before the sequencer can see them.** The enrollment action
identifies a person by CRM record id, so a sourced person with no CRM record cannot be enrolled.
Creating that record is a **write** to the installer's CRM — name it in Step 5's approval and get an
explicit yes for it, separately from the credit spend. Do not create records for held rows.

Create the record with `salesforce_create_contact` (`account_id`, `first_name`, `last_name`,
`email`, `title`) or `hubspot_create_contact`; read back the returned `id`.

**Gong Engage tool:** `gong_assign_prospects` (find the invite flow's id with `gong_list_flows`).

| | |
|---|---|
| **What runs** | one assignment per approved sender, free per `deepline tools describe`; it runs on the installer's own connected Gong account |
| **What goes in** | `flowId`, `crmProspectsIds`, and `flowInstanceOwnerEmail` — **this is what decides whose name the invite comes from**, and it must match the sender identity from the declared inputs. For an approved owned-account row that is usually the account owner; otherwise the named host. `overrides` sets flow variables; its keys resolve against the installer's own flow and are not in the schema. Confirm them in their Gong flow and **never hardcode them** |
| **What to verify** | each id appears in `prospectsAssigned`, not `prospectsNotAssigned`. A call that returns the id under `prospectsNotAssigned` did not enroll anyone |
| **Cost** | no Deepline credits |

Other sequencers: `instantly_add_to_campaign`, `smartlead_push_to_campaign`, `lemlist_add_to_campaign`,
`heyreach_add_to_campaign` — these identify people by email, so the CRM-record step is only needed
for the CRM's own sake. If the event lives on Luma, `luma_post_v1_events_guests_send_invites` sends
the Luma invite itself; it is a send, so it sits behind the same approval.

**Deliver, and show the shape of what is missing:**

- counts per in-scope bucket, and the out-of-scope counts set aside;
- how many were cut to reach the invite target, and which ratio and per-account cap produced it;
- the unbucketed rows, listed, with which field could not be read;
- what eligibility, proximity and suppression each removed;
- rows dropped as `no-contact-path`, and rows not employment- or proximity-verified if
  `preview: true` was used;
- every approval queue, per reviewer, still pending;
- whether the copy followed their sample or the default standard;
- **actual spend** from `deepline runs get --full --json` / `deepline billing usage`, misses included, against the Step 5 estimate.

## What this skill does not claim

- The logic in this skill came from an interview with its author, not from a table or workflow that
  has run. Nothing here has been checked against a system that already executed it, and no step has
  ever been run end to end — so there is no measured cost, latency or fill rate for the play.
- No RSVP or acceptance rate is claimed anywhere. The 3× invite-to-seat ratio is the author's working
  number and was never measured against real event outcomes.
- The recommended cap of 3 contacts per account is the author's judgment about buying groups and room
  balance. No test established that 3 fills rooms better than 2 or 5.
- **Every recommendation in the Step 1 intake is a starting point, not a finding.** The metro-area
  radius, the smart title-match mode, the four-item suppression starting set and the rest are the
  author's working defaults; none was measured against event outcomes. The skill's obligation is to
  label an accepted one as borrowed, not to claim it is right.
- The ordering inside each bucket — seniority, then eligibility value, then recency — is a reasonable
  default the author supplied. Nobody has established that it produces better attendance than another
  order.
- Nothing predicts whether a person will attend. The skill ranks who is worth asking; it does not
  score likelihood to accept, and no such signal is read.
- The rule that a customer with an open opportunity is treated as expansion rather than acceleration
  was the author's call, made for the sake of the copy. Another CRM's data model may make the reverse
  more accurate.
- The net-new sourcing tool bills per returned result, so its cost scales with `limit`, not with
  accounts; the email waterfall's per-row cost is only known after the pilot.
- The job-function taxonomy quoted in Step 2 was read on one day. Personas that fit no function
  today may gain one; **check the live options rather than trusting the list here.**
- The prices quoted here were read with `deepline tools describe` on one day. Declared and
  billed cost differ by plan, prices change, and **if the live catalogue disagrees with a figure in
  this file the catalogue is right and this file is stale.**
- The original vendor-specific arms — a SOQL-based CRM read and a Gong Engage enrollment — were
  confirmed against Clay's catalogue. The Deepline tools named here were confirmed with
  `deepline tools describe` and never executed; Step 0 confirms them for the installer's stack.
- Nothing here measures whether the invite copy performs. The four beats are the author's editorial
  standard, not a tested format, and they are superseded by the installer's own sample whenever one
  exists.

## What good looks like

A good run ends with the room's scope stated at the top, **a visible split between the values the
installer chose and the recommendations they accepted**, and **every row naming the evidence that put
it where it is** — which field made it expansion, which eligibility value qualified the account,
which field decided it was near the venue, which activity date ranked it. The out-of-scope buckets are
reported with counts rather than silently dropped, the unbucketed rows are listed rather than
absorbed, the approval queues are sitting with named reviewers and nothing in them has been sent, and
the reported spend is the charge read back from the response, with misses counted.

A thin run looks different in a way you can see. Buckets that are almost entirely net new usually mean
the customer definition was never supplied and everything fell through to bucket three — check for
unbucketed rows before believing a large net-new count. A large net-new bucket with a small
sourced-people count means the accounts had no reachable contacts near the venue, not that the room
is full. A persona that returned hundreds of people usually means a seniority floor was used where an
exact level was meant, or a function was substituted for a keyword — the RevOps case in Step 2. And a
run where every bucket's copy reads the same has failed at the thing the skill exists to do, even
though it produced three files.

An intake that went wrong is visible too: a run reporting every setting as the installer's own, with
nothing marked borrowed, means the recommendations were passed off as answers.

A failed run says so: it stops at Step 1 with no scope or no event brief rather than inventing one, or
at Step 5 rather than spending unapproved, or it reports that a named tool was absent instead of
quietly calling a different one.

## Rules

- **ALWAYS** say what the run reads, spends, writes and where it stops **before** the first question.
- **ALWAYS** interview in two tiers: the six decisive questions one at a time, then one confirmable
  block of recommendations. **NEVER** present the declared-inputs table as a form.
- **ALWAYS** attach a recommendation and its reason to every question, and **NEVER** let an accepted
  recommendation pass as the installer's own answer — record it as borrowed and report it as such.
- **ALWAYS** ask the room's scope first, and never source or price a bucket that is out of scope.
- **ALWAYS** ask which accounts are eligible before reading anything, and say so out loud if the
  answer is "all of them".
- **ALWAYS** ask seniority, function and city together, and translate them in front of the installer
  before binding them.
- **NEVER** substitute a job function for a persona the taxonomy does not carry — use title keywords
  and say that is what happened.
- **NEVER** rank on proximity. For a located event it is a filter applied before anything paid.
- **NEVER** exceed the per-account cap, and say when the recommended 3 was used instead of theirs.
- **NEVER** send without the approval mode's condition being met, and never read silence as approval.
- **NEVER** default an unbucketed row into net new. Report it.
- **NEVER** name invitees as attendees in the copy. The room is the host and the speakers until
  people accept.
- **NEVER** write the copy in the author's voice when the installer supplied their own.
- **NEVER** spend a credit before the free elimination in Step 4 has run and been reported.
- **NEVER** call a paid tool without stating the estimate and getting a yes, and never report a
  catalogue figure as what was billed.
- **NEVER** substitute a different tool when a named one is absent — say which step is unavailable.
- **NEVER** treat a present-but-empty output field, or a completed run status, as data.
- **NEVER** write to the CRM or enroll anyone without a yes that covers the write specifically.
- **NEVER** invent the scope, the eligibility rule, the event premise, the customer definition, the
  seniority rule, or the sender.
- **ALWAYS** verify the account-domain echo with the TLD excluded before trusting a sourced person.
- **ALWAYS** report misses as spend.

## Worked example

A dinner: 20 seats, New York, October. Premise, in the host's words, "how RevOps teams are handling
AI-assisted territory planning". Hosted by the VP of RevOps.

**Scope, asked first:** open opportunities and net new — no customers in this room. **Eligibility:**
Tier 1 and Tier 2 accounts only. **Persona:** RevOps operators, Director and above, New York — which
translates to floor mode at `director`, **no job function** because the taxonomy has none for revenue
operations, and title keywords `Revenue Operations, RevOps, Sales Operations, GTM Operations`.
**Cap:** 3 per account, the recommended default, said out loud. **Ratio:** not known, so the borrowed
3× is used and flagged — target 60 invites. **Mode:** hybrid.

The CRM read, filtered to Tier 1 and Tier 2 with New York in the query filter, returns 486
candidates across 190 accounts. Free elimination removes 302: 148 non-eligible tiers, 46 outside the
New York rule (38 decided on contact location, 8 on account HQ), 57 below the Director floor, 32
outside the persona, 19 already in a sequence. **184 remain, at zero credits.**

Bucketing: 41 expansion, 88 acceleration, 49 net new, **6 unbucketed** because the subscription-status
field was blank. Scope sets **the 41 expansion rows aside with their count reported** — not deleted,
not priced, not written for. Of the remaining accounts, 34 have no eligible contact and go to paid
sourcing.

Step 5 quotes 34 sourcing searches at 0.02 per returned result plus roughly 60 email lookups at the
pilot's observed per-row cost, flags that the email cost is an estimate, and names the CRM write. Approved. Sourcing runs at `limit: 10`
keeping 3, with the floor as an `in` list, the keywords and `basic_profile.location.city` New York;
three accounts return people whose `company_website_domain` echo fails once the TLD is stripped and are dropped as wrong-entity. 62
people found, 3 kept per account, 48 emails resolved, 11 `no-contact-path`.  Reported spend is read back from the
run against the estimate, misses included.

Ranked and cut to 60 — 33 acceleration, 27 net new. Two drafts, not three: the acceleration note opens
on what the buyer said in the last call, the net-new note on the account's own RevOps hiring. The host
supplied a sample invite, so both follow their voice rather than the default standard, and the output
says so. Both name the VP of RevOps as the host and **no invitee is named as attending.**

Hybrid mode: **38 rows sit on owned accounts and go to eleven reps' queues.** 22 unowned rows enroll
under the host sender, each listed under `prospectsAssigned`. Delivered with the counts, the 41
out-of-scope expansion rows, the 6 unbucketed, the 11 dropped for no contact path, and the real charge.
