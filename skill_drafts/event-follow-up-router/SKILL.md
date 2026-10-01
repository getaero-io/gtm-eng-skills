---
name: event-follow-up-router
description: |
  Turn an event or webinar registrant export into a synced campaign plus a routed follow-up
  plan — reconcile every registrant against your CRM for free, write a campaign status for ALL
  of them including the ones nobody will contact, create records for the registrants your CRM
  has never seen, then qualify and route the rest. Use whenever someone asks: process my
  webinar registrants, sync my event list to Salesforce or HubSpot, set campaign member status
  after a webinar, add event leads to a campaign, follow up with event attendees and no-shows,
  who should we email after the livestream, route event leads to the right rep, segment
  attendees for outreach, or load event follow-up into Gong Engage, Outreach or Salesloft. The
  free path runs before the paid one and every CRM write is reviewable. Do NOT use it to score an inbound lead list into tiers (score-inbound-leads), to
  route raw product signups from an email address (enrich-signup-users), to decide whether a
  contact is a buyer for your product (buyer-classification), to screen an email list for
  deliverability (clean-email-list), or to build the invite list in the first place
  (build-prospect-list).
category: route-and-automate
personas: [marketing, revops]
mechanism: functions
touches: writes-records
keywords: [event-follow-up, sequencer]
ported_from: clay-run/clay-skill-creator/skills/davide-grieco/event-follow-up-router
---

# Event follow-up router (sync everyone, then decide who to contact)

The insight: **syncing the list and deciding who to contact are two separate jobs over the same
rows, and running them as one pass is what silently corrupts event reporting.** Every registrant
needs a campaign status whether or not a single email is ever sent to them — attendance is a fact
about the event, contactability is a decision about outreach — so the sync runs first and covers
the whole list, and nothing the qualification ladder decides afterwards changes campaign
membership.

The evidence for keeping them apart is the size of what qualification removes. On the author's run
of this play, one episode's campaign had **624 eligible members and 295 that were contactable**:
329 rows were held back by fields already populated before the event happened — explicit opt-out,
marketing opt-out, a disqualified-persona flag, already sitting in another sequence, account-level
suppression, no email, no contact record. All 329 of those people still attended, and still belong
in the campaign's numbers. A run that writes status only for the people it intends to email
under-reports its own attendance by half.

Separating them is also what makes the sync affordable, and this is the part that decides the bill.
**Registrants your CRM already knows can be synced for zero enrichment spend; only the ones it has
never seen need to be created, and creating them is the only paid step in the play.** So the two
halves get two different mechanisms — a free lookup-and-write for the known, a priced
enrich-and-create path for the unknown — and the skill states the split before it spends
anything. Collapsing them into one paid call per row is the most expensive way to run this and the
easiest mistake to make: on one Clay workspace's catalogue (read 2026-08-24, before this port), two
routines whose names both amount to "enrich and add to CRM" declared **8.9 and 197.1 Clay credits per
row**, and the cheaper one was still four times the price of composing the same result from a domain
lookup plus the CRM's own free record actions. Nothing in any of those names tells you that, and the
same trap exists among Deepline tools and plays.

One mechanical finding shapes the routing half: **the account owner field is not a sender.** On the
author's run, roughly **43% of these accounts were owned by a CRM integration user**, so "email from
the account owner" resolves to a mailbox no human reads. A sender is a resolution chain with
service accounts explicitly skipped, not a single field lookup.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing. Where a default IS defensible it is named below, and using it
means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The registrant export** | CSV from the event platform; minimum an email column plus an attendance-outcome column. For a Luma event, `luma_get_v1_events_guests_list` (free, paged by `pagination_cursor`) returns guests with `approval_status` and per-ticket `checked_in_at`, which gives registered / attended / no-show | no default — there is nothing to sync or route |
| **The CRM and its connected account** | which CRM they run, which object holds campaign membership, how a campaign is identified, and which connected account this session may write through | ask; without a write-capable account the sync degrades to an upload-ready file and the output says so |
| **The campaign** | the campaign identifier and name for this event | ask — never infer a campaign from an event name in the export |
| **Campaign status values** | their campaign-member status picklist, verbatim, and which value each attendance outcome maps to | ask; a status this skill invents fails the write or corrupts reporting |
| **A create-and-add play** *(optional)* | the name of a saved Deepline play of theirs that takes a person's contact details, ensures the account and contact exist, adds them to the campaign, and returns a per-row outcome | most orgs will not have one — fall back to Step 3's composed path, which uses only Deepline's CRM tools and enrichment and works anywhere the CRM is connected |
| **Credit ceiling for creation** | the maximum spend for creating unmatched registrants this run | state rows × declared cost and get an explicit yes; there is no defensible default for spending someone's credits |
| **Qualification fields** | every field meaning "do not contact this person": explicit opt-outs, disqualified-persona flags, account-level suppression, already-in-a-sequence flags | ask for the full list up front; a field discovered after a send is a send that should not have happened |
| **Outreach scope** | which attendance outcomes get follow-up at all | ask per run — the author excluded replay-viewers from outreach, which is a judgment about their events, not a rule |
| **The bucket ladder** | their segments, in first-match-wins order, and the field or condition deciding each | ask; the four buckets in the worked example are the author's and are borrowed at best |
| **Persona / seniority field** | the field marking a decision-maker versus an influencer, and its values | ask; never infer seniority from job-title text when the CRM carries a graded field |
| **Persona grading** | either the CRM field that already holds a graded persona, or the name of their own scoring play | no prebuilt Deepline play grades this — it is the installer's definition of seniority, so without one ungraded rows are `unrouted` rather than guessed |
| **Routing play** *(optional)* | the name of a saved play encoding their own rules of engagement, if they have one | no prebuilt Deepline play does this — fall back to the bucket ladder and sender chain below, and never approximate someone's routing rules |
| **Sender resolution chain** | the ordered fallback for who a follow-up comes from, plus every service or integration mailbox to skip | ask for the skip list explicitly — it is the input teams forget and the one that breaks sends |
| **The sequencer** | where sequences live, what identifies the right sequence for a bucket, and whether the sender must be a licensed user there | ask; a sender who is not a user in the sending tool cannot be enrolled |
| **Sequence naming** | how sequence names encode the event and the bucket | ask, then resolve by token match rather than by constructing a name — see Step 9 |
| **Copy themes per bucket** | what each bucket should hear, in their words | ask; this skill drafts and stops for redline, it does not approve its own copy |
| **Send ceiling** | a maximum number of live enrollments per run | dry run is the only safe default: run it, and say the run was a dry run |

**Do not start a step before the steps above it have their answers.** If a declared input is
missing, ask for it — never assume a default and continue.

## What this skill touches

- **Reads** — the registrant export you supply, and your CRM through your own connected account, to
  reconcile each registrant against an existing contact, lead, or nothing at all.
- **Writes** — **campaign membership and campaign status in your CRM, and enrollments in your
  sequencer.** Rows with no CRM record are the only part that creates anything, and creation is
  bounded by the credit ceiling you set.
- **Never** — proceeds to enrollment on copy you have not redlined, and never exceeds the send
  ceiling. A dry run is the default, and a dry run says so.

## Step 0 — Confirm the platform, and say where each stage runs

Run `deepline preflight --json`. If the CLI is missing, install it (`npm install -g deepline &&
deepline auth register --wait auto`) and re-run this skill. Say which org you are in, out loud.

Then say where each stage runs, because that is what it costs:

- **Reconciliation, qualification, bucketing and sender resolution run IN THIS AGENT** on fields
  the CRM already holds. Zero credits, no per-row charge. This covers every registrant the CRM
  already knows, which is usually most of the list.
- **CRM lookups and writes run through the installer's own CRM connected to Deepline.** Read with
  `deepline tools describe`, the HubSpot and Salesforce record tools (`hubspot_search_objects`,
  `hubspot_batch_read_objects`, `hubspot_batch_upsert_objects`, `hubspot_add_records_to_list`,
  `salesforce_list_contacts`, `salesforce_list_leads`, `salesforce_create_contact`,
  `salesforce_update_contact`, `salesforce_create_account`) all price as **Free**, so they bill
  against the CRM's API quota rather than credits. Re-read this rather than trusting the sentence;
  the point that survives is *check whether your CRM tools cost credits before assuming either way*.
- **Salesforce campaign membership has no Deepline tool.** There is no CampaignMember read or write
  and no SOQL tool. For Salesforce, the sync half delivers an upload-ready CampaignMember file (record
  id, campaign id, status) for the Data Import Wizard, and the output says so. HubSpot has no
  campaign-member status either; the nearest is a static list per status
  (`hubspot_add_records_to_list`) or a contact property written with `hubspot_batch_upsert_objects` —
  confirm which the installer reports on.
- **Paid enrichment enters in exactly one place** — Step 3, creating the registrants the CRM has
  never seen — plus optionally Step 5 for ungraded personas. If every registrant already exists in
  the CRM and carries a graded persona, this skill spends nothing at all.

State that split before doing anything.

## Step 1 — Collect the definition (interview; do not guess)

Work down the declared inputs above, in that order. Three of them decide whether the run is safe:

1. **The status map.** Get their picklist verbatim, then map each attendance outcome in the export
   to one value. Every outcome needs a mapping, including the ones nobody will contact.
2. **Write authority and the connected account.** Ask explicitly which CRM account this session may
   write through, or whether the deliverable is an upload-ready file they load themselves. Both are
   valid; guessing is not.
3. **The full qualification list.** Ask for every field, not the obvious two. Prompt for: explicit
   email opt-out, a separate marketing-only opt-out, a disqualified-persona or junk-lead flag,
   account-level suppression, and an already-in-an-active-sequence flag. Then ask what else their
   team checks by hand before a send — that question surfaces the gate nobody wrote down.

If they cannot supply the status map or the qualification list, **stop**. The first decides what
gets written to their CRM; the second decides who gets contacted. Inventing either is how a skill
mails someone who asked not to be mailed.

## Step 2 — Reconcile the export against the CRM (free)

Match every row in the export to a CRM contact or lead, and to a campaign membership record, using
the installer's CRM read tool: `hubspot_batch_read_objects` with `id_property` email, or
`hubspot_search_objects`; for Salesforce, page `salesforce_list_contacts` and `salesforce_list_leads`
to the end and match in the agent. Deterministic passes only, in this order, recording which pass
matched each row:

1. exact email match;
2. normalized email match — lowercase, strip dots and plus-tags where the mail domain allows it;
3. corporate-domain match plus full-name match, for people whose work address the CRM holds under a
   different spelling.

Never match on company name alone, and never on first name plus company. Both produce confident
wrong joins, and a wrong join sends the right email to the wrong person.

**This step is what makes the run affordable, so do it before pricing anything.** Emit four counts
and show them: **matched to a contact**, **matched to a lead only**, **already a member of this
campaign**, **no CRM record**. Only the last group reaches a paid call. Flag personal-domain
registrations (free mail providers) separately — a personal address cannot be attributed to an
account, and that limitation should be visible rather than resolved by a guess.

## Step 3 — Sync the full list: free for the known, priced for the unknown

**This step covers every registrant, unconditionally.** Nothing about qualification has been decided
yet and it does not belong here — a person who opted out of email still attended.

**Arm A — rows the CRM already knows (free).** Write or update the campaign membership with the
mapped status, through the CRM write named in Step 0 (or the upload-ready file where no tool can
write membership). No enrichment, no credits.

**Arm B — rows with no CRM record (the only paid part of the sync).** These need an account and a
contact to exist before they can hold a campaign status. **Two ways to get there, and which one you
have decides the price**, so check before promising either:

**B1 — a single create-and-add play, if the installer has one.** One call per row: it enriches,
ensures the account and contact exist, adds the campaign membership, and returns a per-row outcome.
Fewest moving parts, and the outcome field is the thing that makes it trustworthy — a play
returning only success or failure cannot tell you whether it created a duplicate. **Assume the
installer does NOT have one.** A play like this is something a team builds for itself; check with
`deepline plays list` and `deepline plays grep "campaign"` (org-owned plays), and read the
contract with `deepline plays describe <name> --json` before trusting what its name says.

**B2 — compose it from portable pieces, which is the path that works anywhere.** Two layers, and only
the first costs credits:

1. **Fill what the CSV is missing** with Deepline enrichment. Resolve a company domain from a
   company name with `crustdata_v3_company_identify` (free; name-only results are unverified
   candidates, so confirm against the registrant's email domain before writing); find a work email
   from a name plus domain where the export has none with the prebuilt play
   `prebuilt/name-and-domain-to-email-waterfall-batch`. Read each one's price before running it.
2. **Write the records through the installer's CRM tools**: look up the account, create the account
   and the contact if absent (`salesforce_create_account`, `salesforce_create_contact`, or
   `hubspot_batch_upsert_objects`), then create the campaign membership (Step 0 says where that is a
   file instead of a write). These tools price as Free — the spend is the CRM's API quota, not
   credits.

**B2 is usually cheaper than B1, because it does less.** Measured on Clay before this port (one
workspace, 2026-08-24): a workspace-custom create-and-add routine declared **8.9 Clay credits per
row** — but it also enriched a phone number and a social profile, which a campaign sync does not
need. Composed from managed pieces, a row needing only a domain resolved declared **0.8**, and one
needing a work email as well about **1.9**. In Deepline the domain step is free and only the email
waterfall bills. Pick B1 for fewer failure modes, B2 for the lower price; state which and why.

**Two traps in the same neighbourhood**, both from that Clay catalogue and both general. A routine
named for enriching a contact *and adding it to the CRM* declared **197.1 Clay credits per row with
variable pricing** and did not touch campaign membership — twenty-two times the price of the routine
that actually did the job, with nothing in either name to distinguish them. And the deep
person-enrichment routine required a social profile URL as input, which an event export will not
have. **Read the declared price and the input schema of the specific tool or play you resolved. Never
price a step, or assume its inputs, from its name.**

Discover all of it against the live catalogue, because tools and prices change:

```
deepline tools search "<crm> create contact" --json
deepline tools describe <tool_id> --json          # inputSchema and pricing
deepline plays describe <play_name> --json        # a play's input contract
```

**Then state the four things, in the output, before calling anything:**

| | For this step |
|---|---|
| **What runs** | every tool and play you resolved, by id, with the name each reported |
| **What goes in** | which export columns feed which input, plus the campaign id and the mapped status |
| **What to verify** | the per-row outcome and the returned record ids — never that the run started. A run can complete and return no record id |
| **What it costs** | unmatched-row count × the declared per-row cost, against the installer's ceiling |

**Direct `deepline tools execute` is for 1–20 rows.** A larger remainder runs as one play over the
CSV (`deepline plays run ... --input '{"csv":"unmatched.csv"}'`), piloted on 3 rows first. Say which
it will be rather than promising one call.

**If neither path is available** — no create-and-add play and no CRM connected to Deepline — report
the unmatched rows as a separate list, say the sync was partial and why, and let the installer decide.
A partial sync that says so is a good outcome; a silent one is not.

**Both arms go through a reviewable file first.** One row per registrant, carrying the CRM record id
where one exists, the campaign, the mapped status, the match pass from Step 2, and which arm the row
is taking. Hand it over, get explicit approval, then write — and report **per-row** failures rather
than a summary. A write reporting success while dropping rows is worse than one that fails.

## Step 4 — Qualify for outreach (free), and report the cut

Now, and only now, decide who can be contacted. Apply every qualification field the installer named
to every synced row, before any copy exists and before anything else is priced. One pass, and
record which gate held back each row — a report where rows vanish without a named reason is not
reviewable.

Report the cut as a number: *N in, M contactable, and the count per gate*. Show it even when it is
small. Then apply the outreach scope from Step 1 — the outcomes the installer excluded from
follow-up drop out here, counted as excluded-by-scope rather than as unqualified, because those are
two different reasons and a reader needs to tell them apart.

**Nothing in this step changes campaign membership.** Step 3 already happened and stands.

## Step 5 — Fill only the fields the ladder needs

Rows that survived Step 4 but lack the field the bucket ladder reads — typically a persona or
seniority grade — cannot be bucketed. Two honest options and no third:

- **Fill it**, if the installer has their own scoring play. Discover and price it the same way as
  Step 3. On the Clay workspace checked before this port, a workspace-custom persona-and-ICP grade
  from a job title declared **3 Clay credits per row** — cheap enough that the question is how many
  rows need it, not whether to run it. **But expect not to find one.** Persona grading is a
  definition of seniority, not a data lookup, so there is no prebuilt to fall back on.
- **Leave them `unrouted`**, and report the count. A row with no graded persona is not a row with an
  average persona.

Never infer the grade from job-title text yourself when the installer has a graded field or a
play for it — a title string is not a persona, and hand-grading it produces a number nobody can
audit against their own definitions.

## Step 6 — Bucket the contactable rows, first match wins

Buckets come from the installer, resolved **in a stated order, first match wins**, so no row can
land in two. Enumerate the values and include one for abstention: a row the ladder cannot place is
`unrouted`, never quietly assigned to the largest bucket.

Rank the conditions so the most specific wins first. The author's ladder ran: an open opportunity on
the account owned by a named seller; then decision-maker persona; then influencer or other persona;
then everyone remaining into an automated tier. That order encodes one judgment worth stating to the
installer rather than inheriting silently — **an active deal outranked persona**, because follow-up
into a live opportunity is a different message from follow-up into cold interest.

If the installer has a routing play encoding their own rules of engagement, use it instead of this
ladder and say so. Approximating someone's routing rules by hand produces assignments their revops
team will not recognise.

Show the bucket distribution before writing any copy. A ladder putting 90% of the list in one bucket
is not segmenting, and the installer should see that while it is still cheap to change.

## Step 7 — Resolve a sender per row, and never trust the owner field

Walk the installer's chain in order, skipping every mailbox on their skip list, and record which
link resolved each row. The author's chain was: account owner, then the assigned development rep on
the contact record, then a named marketing fallback.

Two checks that are not optional:

- **The skip list applies at every link**, not only the first. A service account further down the
  chain is the same failure.
- **The resolved sender must exist as a user in the sequencer.** This is where a near-miss bites: an
  address that is a valid CRM user is not necessarily a licensed user in the sending tool, and the
  enrollment then fails per-record at send time rather than at validation. Verify membership in the
  sending tool, not in the CRM.

Any row whose chain resolves to nobody is `unrouted`. Report the count.

## Step 8 — Draft first-touch copy per bucket, then stop

One draft per bucket, on the themes the installer supplied, and **first touch only**. Later steps in
a sequence are the sequence's job; generating them here produces copy nobody reviews.

Then stop and get a redline. Do not proceed to enrollment on unreviewed copy, and do not treat
silence as approval.

## Step 9 — Resolve the sequence, dry run, then live

**Resolve the target sequence by matching tokens, not by constructing a name.** Sequence names drift
between events even inside one team — the author observed one bucket named four different ways
across sampled events, and only about five of eleven events had a sequence for every bucket. So:
score candidate sequences on event token, then bucket signature, then attendance-status token, and
require a threshold before accepting a match. Report every bucket with **no** matching sequence as a
gap rather than enrolling it into the nearest name.

List candidate sequences with the sequencer's own tool: `gong_list_flows`, `outreach_list_sequence_states`
for existing states, `instantly_list_campaigns`, `smartlead_list_campaigns`, `lemlist_list_campaigns`.

Then dry run, always, and report what a live run would do: per-bucket enrollment counts, per sender,
with the resolved sequence named. Only on an explicit yes, and never above the installer's send
ceiling, enroll live: `gong_assign_prospects` (`flowId`, `crmProspectsIds`,
`flowInstanceOwnerEmail` = the resolved sender; verify each id lands in `prospectsAssigned`),
`outreach_create_sequence_state`, or `instantly_add_to_campaign` / `smartlead_push_to_campaign` /
`lemlist_add_to_campaign`. **Salesloft has no Deepline tool that creates a cadence membership** —
for a Salesloft installer, the live step is a per-bucket upload file.  Say plainly in the output whether the run was a dry run or live.

## What this skill does not claim

- The logic here came from an interview with its author and their prior build of this play, not from
  a system that ran end to end under measurement. Nothing in it has been compared against a source
  of truth, and there is no ground truth for it anywhere.
- The 624-to-295 figure and the 43% integration-owner figure are from one event, in one company's
  CRM, on one plan. They are the evidence for separating the sync from the outreach decision, not a
  benchmark, and no claim is made that any other list qualifies at that rate.
- **Every credit figure quoted — 8.9, 197.1, 3 — was read from one Clay workspace's catalogue on
  2026-08-24, before this port, and is nobody's Deepline price.** They are quoted to show that
  similarly-named steps differ by more than an order of magnitude, which is why the skill makes you
  read the declared price. Read yours with `deepline tools describe`; it wins over this file.
- No conversion, reply or meeting rate is claimed for any bucket, any sender, or any copy theme. The
  play has never been measured against a control.
- The four-bucket ladder and the three-link sender chain in the worked example are the author's,
  taken from one company's CRM schema. They illustrate a shape; they are not a recommended
  configuration.
- Whether replay-viewers should get follow-up was the author's judgment for their events and is not
  established as correct for anyone else's.
- The skill does not verify that any play it discovers actually deduplicates correctly. It
  requires a play that *reports* created-versus-already-a-member, and checks that report; it
  cannot tell you whether the play's own matching is sound.
- The Deepline tools named here were confirmed with `deepline tools describe` and never executed in
  writing this port. Nothing here establishes that the composed path in Step 3 works for every CRM
  connection — check it, do not assume it.
- The token-scoring approach to sequence resolution is a workaround for naming drift, not a fix. It
  was tuned by hand against one team's naming history and its threshold has no derivation.
- This skill does not verify email deliverability. A qualification ladder answers "should we contact
  this person"; it says nothing about whether the mailbox accepts mail.
- No end-to-end runtime or latency figure is given. The play has been run in pieces, never timed as
  a whole.

## What good looks like

A good run reads as two clean halves, and every number in it has a named reason.

- **The sync half covers the whole export.** Row count out equals row count in, every registrant
  carries a mapped status, and the file was reviewed before the write. A sync that only covers the
  people the run intends to email has failed even if every email lands.
- **The paid arm is small and was priced before it ran.** Most rows went down the free arm because
  the CRM already knew them; the unmatched remainder was counted, multiplied by a declared cost, and
  approved. A run where every row went through a paid path is a working run that cost twenty
  times what it needed to.
- **The qualification half reports N in, M contactable, and a count per gate**, with rows excluded by
  outreach scope counted separately from rows held back by a qualification field. A row that
  disappeared without an attributed reason is a defect.
- Every contactable row carries a bucket, a resolved sender, and the chain link that resolved it.
  Rows the ladder or the chain could not place are `unrouted` with a count — never absorbed into the
  largest bucket or the marketing fallback.
- Buckets with no matching sequence are reported as gaps. Zero is a good sign; three named honestly
  is also a good outcome, because the fix is to create three sequences.
- The output states whether the run was a dry run or live, and names the send ceiling.

A thin run looks different and should be called thin: most rows unmatched (the export's email column
is not the CRM's), or 90% of the list in one bucket (the ladder is not discriminating), or every
sender resolving to the marketing fallback (the skip list ate the chain). None of those is a reason
to send anyway.

## Rules

- **NEVER** let qualification change campaign membership. The sync in Step 3 covers everyone and
  stands regardless of what Step 4 decides.
- **NEVER** send a row down the paid arm before the free reconcile in Step 2 has run.
- **NEVER** price a tool or play from its name. Read its declared cost and input schema, and state both.
- **NEVER** create records for unmatched registrants without an approved credit ceiling.
- **NEVER** improvise a create-and-add path when the CRM tools Step 0 named are not connected —
  report the partial sync instead.
- **NEVER** write to the CRM or enroll anyone before the reviewable file has been approved.
- **NEVER** run a live send without a dry run first, and never above the installer's ceiling.
- **NEVER** invent a campaign status value, a qualification field, or a bucket the installer did not
  name.
- **NEVER** treat silence as approval, for copy or for a write.
- **NEVER** match a registrant to a CRM record on company name alone, or on first name plus company.
- **NEVER** infer seniority from job-title text when the CRM carries a graded persona field or the
  installer has a scoring play.
- **NEVER** construct a sequence name and assume it exists. Resolve by match, and report misses.
- **ALWAYS** run every free qualification gate before pricing or calling anything paid.
- **ALWAYS** verify the per-row outcome a create-and-add play or CRM write returns, not that the run started.
- **ALWAYS** report the qualification cut per gate, and count scope exclusions separately.
- **ALWAYS** resolve buckets and senders in a stated order, first match wins, with an explicit
  `unrouted` value for anything unplaceable.
- **ALWAYS** verify the resolved sender is a user in the sending tool, not just in the CRM.

## Worked example

An episode of a recurring webinar. The export carries 700 rows with an email column and an outcome
column of registered / attended / no-show / watched-recording. The installer's status map covers all
four; the campaign id is supplied.

Step 2 reconciles for free: 622 matched to a contact, 34 to a lead only, 44 with no CRM record — of
which 19 registered from a free mail provider. **Only those 44 can reach a paid call.**

Step 3 splits. Arm A writes campaign membership for 656 rows through the installer's connected CRM
at no credit cost; two rows fail a validation rule and are reported individually. Arm B finds
no create-and-add play, so it composes: 31 of the 44 rows need a company domain resolved, 9 need a
work email as well, and 4 have neither a company nor a corporate address and cannot be placed. (This
run was priced on Clay before the port, at a declared 0.8 credits per domain and 1.1 more per email,
~35 credits against a 500-credit ceiling; on Deepline the domain step is free and the 9 emails bill
at the waterfall's observed rate.) Stated, approved, then run. The CRM writes that follow cost no credits: 40
accounts looked up, 12 created, 40 contacts created, 40 campaign memberships created. One contact
fails a required-field rule and is reported individually. The 700-row status file was approved before
any of it.

Step 4 qualifies for outreach. The installer excludes watched-recording from follow-up for these
events, so 76 rows drop out by scope. Of the 624 remaining, seven gates hold back 329 — 84 opted
out, 61 marketing opt-out, 77 disqualified persona, 52 already in an active sequence, 31
account-suppressed, 14 no email, 10 no contact record. **295 contactable.** All 700 still carry a
campaign status.

Step 5 finds 13 contactable rows with no graded persona. This installer has no scoring play and
there is no prebuilt one to borrow, so all 13 are marked `unrouted` and reported rather than guessed. Step 6 buckets the remaining
282 first-match-wins: 36 in open-opportunity accounts, 71 decision-makers, 96 influencers, 79
automated tier. Step 7 resolves senders and reports that 127 rows' account owner was the integration
mailbox and fell through to the next link; 4 resolve to nobody.

Step 8 drafts four first-touch emails; the installer redlines two. Step 9 finds sequences for three
of the four buckets, reports the fourth as a gap, dry-runs 205 enrollments across 31 senders, and
enrolls live only after an explicit yes. Total spend: ~35 Clay credits on a 700-row export, all of it on 40 registrants the CRM had never seen.
