---
name: icp-outbound-campaign
description: |
  Build an outbound campaign from your ideal customer profile: interview you for the ICP (who
  the buyer is, which companies, where, how many), turn it into a Deepline company-then-people search you confirm
  in plain words, widen in declared tiers only if the strict ICP cannot reach your target, strip
  titles that match but never buy, keep a set number of leads per company, find verified work
  emails, optionally enrich any extra data point you want to personalize on (recent posts,
  company news, a funding round, anything a Deepline tool can find) using the best enrichment for
  it, save the kept leads to a CSV as their own segment, and draft a two-email (optionally three)
  campaign in your sequencer (Instantly, Smartlead or Lemlist) around your offer. Use whenever someone asks: find leads in my ICP, build an outbound
  campaign, get me 200 VPs of Sales with emails, find CISOs to email, build a prospect list and a
  sequence, personalize outbound on recent funding or posts, or turn my ICP into a lead list. Do
  NOT use it to score or tier a list you already have, to enrich an existing CRM export, to find
  companies rather than people, to send or launch a campaign, or to write replies to people who
  answered.
category: build-lists
personas: [sales-development, revops]
mechanism: functions
touches: writes-records
keywords: [cold-email, sequencer]
ported_from: clay-run/clay-skill-creator/skills/tanvi-reddy/icp-outbound-campaign
---

# ICP outbound campaign (ask for the ICP, tier the search, then fill in order)

The insight: **the strict ICP on the source run found 141 people for a target of 200, so this
skill widens in declared tiers and fills them in order rather than loosening the definition.** The
source run, made on Clay's people search before this port, targeted CISOs and heads of security at
fast-growing software companies in the US and Canada on 2026-09-28:

| Tier | Definition | People found |
|---|---|---:|
| 1 | persona titles, core industry, 51–5,000 employees, 20%+ 12-month headcount growth | **141** |
| 2 | same titles and growth, adjacent industries | 52 more (193) |
| 3 | same titles, industries and growth, 11–50 and 5,001–10,000 employees | 99 more (292) |

The strict definition alone could not reach 200 — and it lost more on the way: 12 titles that
matched the search but do not buy (vendor "Field" titles, deputies, program managers), 2 whose
company resolved to a junk domain, 24 with no verified email, and 24 who were a second leader at a
company already on the list. The run kept 200 of 230 eligible, filled tier 1 first (116), then
tier 2 (38), then tier 3 (46). How big any other ICP's pool is was not measured; that is why the
skill counts tier 1 before promising a number.

Four more things follow, and the first three bit the run that produced this skill.

**The ICP is the installer's, and saved context may hold the wrong one.** The source run's
saved business context described a different company than the seller. An ICP read from context and
used silently would have targeted someone else's buyers. So this skill asks for the ICP every time,
and shows any saved ICP only as a starting point to confirm.

**Title similarity matching over-reaches in a predictable direction.** A title search expands into
related titles, and some of them never own a budget — on the source run, asking for "CISO" also
returned Field CISOs at vendors, deputies, fractional CISOs and advisors. Every persona has its own
version, so the skill shows the titles that came back and asks which to drop before anything paid
runs.

**A sequence follow-up is not a reply.** The sequence stops for a lead the moment they reply, so the
second step only ever reaches people who did not answer. Anything meant for people who said yes is
a message a human sends from the thread, not a sequence step.

**A personalization data point is only worth paying for if it reaches the email.** The source run
personalized on nothing beyond the fact the search filtered on, so it needed no extra enrichment. An
extra data point — a recent post, a funding round, a news story — costs a lookup per lead, returns
nothing for some of them, and can be wrong about the company. So the skill asks whether the
installer wants one, picks the enrichment by testing it on real rows, and writes copy that still
reads naturally for the leads where it came back empty.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and if an answer does not exist say which step becomes
unavailable rather than guessing. Where a default IS defensible it is named below, and using it
means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Buyer persona** | the job titles that count as the buyer, and the seniority levels | no default — Step 3 has nothing to search for |
| **Company profile** | industries, employee size range, and any company signal that defines fit (headcount growth, hiring for a role, technology used, headquarters location) | no default — ask. A search with titles and no company profile is too broad to send to |
| **Geography** | where the people must be based | no default — ask |
| **Target count** | how many leads they want in the finished segment | the author recommends 250–300 for a first test campaign; recommend it, let the installer decide, and never pick a number for them |
| **Exclusions** | companies or lists never to contact (customers, competitors, an existing list or CRM export) | everyone already in the sequencer's workspace is excluded regardless; ask for anything beyond that |
| **Title exclusions** | titles that match the search but never buy | built from the search results in Step 4 and confirmed by the installer; never assumed |
| **Widening order** | which ICP criterion to relax first if tier 1 falls short | asked in Step 3 only if tier 1 falls short; never widen silently |
| **Leads per company** | how many people one company may contribute | the source run used 1, a run-time default rather than a stated rule; say it is borrowed |
| **Personalization data points** | any extra fact per lead or per company they want the emails to use, and how recent it must be | none is a complete answer — the campaign personalizes only on name, company and the ICP fact the search filtered on |
| **Sequencer variables for data points** | the custom variable each extra data point travels as | propose a snake_case name per data point; confirm it at Step 5 |
| **Seller and offer** | who is sending, what is offered, and what the recipient has to give to accept it (a call, a form, access) | no default — Step 9 cannot write copy |
| **Product facts and proof** | one or two sentences on what the product does, and any customer result the installer is cleared to cite | copy runs with no proof line. Never invent a customer or a number |
| **Lead-source tag** | the value written to the lead-source field so this batch forms its own segment | no default — without it Step 8 cannot build a segment that holds only this run |
| **Lead-source field** | the CSV column and sequencer custom variable that hold the tag | `lead_source`; say so if used |
| **Follow-up delay** | days between the first email and the follow-up | the author recommends 3–4 days; if they have no view use 3 and say it is the author's |
| **Third email** | whether to add a third email, and its delay | two emails is the default. The author's experience is that anything after email 2 has a very low chance of a response; if they want a third, it goes 7 or more days after email 2, and say so |

**If an answer sheet is present beside this skill, load it and ask only for what it does not
cover.** A partial sheet is normal; a value it is missing gets asked for on its own rather than
restarting the interview. Say which values came from the sheet before using them. If there is no
sheet, say nothing about sheets.

## What this skill touches

- **Reads** — Deepline company and people search (`crustdata_v3_company_search`, `crustdata_v3_person_search`), the leads already in the installer's sequencer and any earlier run's Customer DB table, existing campaigns, the Deepline tool and play catalogue, and the declared prices of the enrichments it chooses.
- **Writes** — a CSV of the kept leads (name, title, company, location, work email, profile URL, lead-source tag, and any approved personalization fields), the Customer DB tables the batch plays persist automatically, one new campaign in the installer's sequencer created with two sequence steps (three if the installer asks), and the kept leads added to that campaign.
- **Never** — activates, sends, pauses or deletes a campaign; sends a test email; deletes or clears any record or field; overwrites a populated field with a blank; adds anyone already in the sequencer's workspace or on the exclusion list.
- **Halts** — Step 1 other, Step 3 sample-review, Step 5 sample-review, Step 6 spend-approval, Step 6 write-approval.

## Step 0 — Check the platform works, and say what this run touches

Run `deepline preflight --json`. It must return a connected org and a balance; name the org out loud.
If the CLI is missing, the install is `npm install -g deepline && deepline auth register --wait auto`;
if auth fails, say which component is wrong and the one command that fixes it, and stop. Then ask
which sequencer they send from and confirm Deepline can read it: `deepline tools execute
instantly_list_campaigns --input '{}'` (or `smartlead_list_campaigns`, `lemlist_list_campaigns`). A
not-connected error means the campaign step ends at a CSV they import themselves; say so now.

Then say, before anything else: *"I'll ask you about your ICP first, then search for people who
match, find their work emails, add any extra details you want to personalize on, save the kept leads
to a CSV, and create a draft campaign in your sequencer with those leads in it. Nothing is sent or
launched — you do that in the sequencer."*

Do not start a step before the steps above it have their answers. If a declared input is missing,
ask for it — never assume a default and continue.

## Step 1 — Interview for the ICP (do not guess)

**The ICP is the installer's judgment about their own market. Ask for it; never infer it from the
org, the seller's website, or an earlier campaign.** One question per message, in this order,
each with a one-line example so the installer knows the level of detail wanted:

1. **Who is the buyer?** *"Which job titles, and how senior — e.g. VP or Head of Sales, Director and
   above."*
2. **Which companies?** *"Industry, employee size range, and anything that makes a company a fit now
   — growing headcount, hiring for a role, using a technology, headquartered somewhere."*
3. **Where are the people based?** *"Countries or regions."*
4. **How many leads do you want?** *"For a first test campaign, 250–300 leads is a good size — big
   enough to read a reply rate, small enough to fix the copy before scaling."*
5. **Who must never be contacted?** *"Customers, competitors, an existing list."*

If an earlier run left an ICP note beside this skill (Step 10 offers one), **show it and ask whether
it applies to this campaign** — it may describe an old ICP. Use it only on a yes, and only as the
starting point for the questions above.

If an answer is vague ("fast-growing", "mid-market", "tech"), ask once for the number or list behind
it. If they have no view, offer the closest searchable default, name it, and record it as borrowed —
for example, more than 20% headcount growth over 12 months for vague growth wording (the source run's
default).

Then **play the ICP back in one short paragraph** — the titles, seniority, company profile, geography,
exclusions and target — and ask *"is that your ICP?"*. Stop until they say yes. This is the Step 1
halt.

## Step 2 — Look at what already exists (free)

1. List campaigns in their sequencer (Step 0) and name any that look like an earlier run for the same
   ICP or seller, including empty drafts.
2. `deepline db query --sql 'select ...' --json` against any Customer DB table an earlier run of this
   skill persisted (the run output names it). Name it if found.
3. If either exists, ask once whether to build fresh (excluding everyone already contacted) or to
   top up the earlier list. Recommend fresh, excluding everyone.

## Step 3 — Turn the ICP into a search, confirm it, count tier 1

**Companies first, then people.** Headcount growth, industry and size are company facts; person
search cannot filter on growth. Read both tools' filter vocabularies live — never restate them from
memory:

```
deepline tools describe crustdata_v3_company_search --json
deepline tools describe crustdata_v3_person_search --json
```

and read the `crustdata-v3` provider playbook in the `deepline-gtm` skill. Use the free autocomplete
tools (`crustdata_v3_company_search_autocomplete`, `crustdata_v3_person_search_autocomplete`) for every
industry, seniority, title and location value — a value the index does not hold returns zero rows
without an error.

The shape, with every value from the confirmed ICP:

1. `crustdata_v3_company_search` — `filters` on industry, headcount range, HQ country and the company
   signal (headcount growth over 12 months). `limit: 1` returns `total_count`, which sizes tier 1 for
   the price of one result.
2. `crustdata_v3_person_search` — `filters` with `op: "and"`: current title (persona titles), current
   seniority, `experience.employment_details.current.company_website_domain` `in` the tier's company
   domains, and location country. **`in` takes at most 5 values** — Crustdata silently ignores longer
   arrays — so batch the domains five at a time and merge. Adding
   `experience.employment_details.current.business_email_verified = true` keeps only people a work
   email can be found for.

Both searches bill 0.02 Deepline credits per returned result (empty pages free); keep `limit` strict
and page with `cursor` / `next_cursor`.

**If an ICP criterion has no search field, say so plainly** — name it, say what the search will use
instead (the closest field, or nothing), and offer to check it per lead as a data point in Step 5.
Never drop it silently.

**Before running anything paid, read the search back in plain words** — *"people titled VP or Head of
Sales, Director and above, at software companies with 201–1,000 employees that grew headcount more
than 20% in the last year, based in the UK, not already in your sequencer"* — and ask them to
confirm. Keep each tier's rows in its own file — **never merge with a shell glob that can pick up
unrelated JSON files**; that happened on the source run and polluted the merge.

**Show the first page as a sample** — the 10 most common titles and a handful of companies — and ask
whether these look like their buyers. This is the Step 3 halt, and it is where a wrong industry or an
over-broad title shows up before much is spent.

**Widen only if tier 1 cannot reach the target.** Aim for roughly 1.4× the target in candidates,
because the source run lost about 30% between search and final list. If tier 1 falls short, say how
many it found and ask which criterion to relax first — an adjacent industry, a wider size band, a
looser signal, a neighbouring geography. Each widening is its own tier and its own search; label
every row with its tier. Dedupe across tiers on the profile URL.

Profiles carry `basic_profile.name`, the profile URL at
`social_handles.professional_network_identifier.profile_url`, location, and current employment with
title, company name and `company_website_domain`. If a row lacks the profile URL, the email step
still runs on name and domain.

## Step 4 — Free cleanup before anything paid

1. **Build the title exclusions with the installer.** List the distinct titles across all tiers,
   grouped, and propose the ones that look like non-buyers — vendor-facing "Field" titles, deputies,
   interim or fractional roles, advisors, consultants, interns, analysts, board seats, assistants,
   and roles from a different function that share a keyword. Ask them to confirm or edit the list.
2. Drop rows whose current title is empty or matches the confirmed exclusions (case-insensitive,
   whole-phrase).
3. Drop rows on the exclusion list, and anyone already in the sequencer (`instantly_list_leads` with
   `search` on the email or name, or the earlier run's Customer DB table). `instantly_add_to_campaign`
   also takes `skip_if_in_workspace: true` as a last guard at Step 9.
4. Rank what remains: tier ascending, then seniority — the most senior title first.
5. List unique company domains. Domains come back on the person rows, so there is no separate
   domain lookup unless a row lacks one.

Say the counts: found, removed by title, removed as already contacted, remaining, unique companies.

## Step 5 — Ask for personalization data points, and choose the enrichment for each

**Ask one question, with examples, and accept "none" as a complete answer:**

> *"Beyond their name, company and the ICP fact we searched on, is there anything else you'd like the
> emails to reference? Deepline can find things like a person's recent LinkedIn posts, a company's
> recent news, or its latest funding round — or something else specific to your pitch. Name as many
> as you like, or say none."*

If they say none, skip to Step 6. For each data point they name, do the following. Do not name a
provider or tool to the installer until `deepline tools describe` has confirmed it exists.

1. **Pin the definition before looking for a source.** Ask only what the data point leaves open and
   the copy needs: is it about the **person** or the **company**, and **how recent** must it be
   (e.g. posts from the last 30 days, a round announced in the last 12 months)? A time-bound fact with
   no window is not usable — an undated or out-of-window result counts as not found.
2. **Find the candidates, plays first.** `deepline plays search "<data point>" --json` for a prebuilt
   that fits, then `deepline tools search "<data point>" --json` with two or three synonyms. Read each
   candidate's real input schema and pricing with `deepline tools describe <id> --json`. Never carry a
   tool name or price in from memory. For a company's news or funding, `predictleads_company_news_events`
   and `predictleads_company_financing_events` are where to start; for posts, search "linkedin posts".
3. **Compare the candidates on four things, then pick one:**
   - **Inputs** — can every kept row supply them? A candidate needing a profile URL when half the rows
     lack one covers only half.
   - **Cost** — `pricing` from `describe`. A tool priced "calculated after execution" or per result
     returned cannot be totalled before it runs, so give its per-unit price and set a cap on items per
     lead.
   - **Output** — does it return the field the copy needs, with a date where the definition needs one?
   - **Scope** — a person-level fact runs once per lead; a company-level fact runs once per **unique
     company**, which is cheaper and must be joined back to each lead.
   Prefer the candidate that covers the most rows with the needed field at the lowest cost. If none
   can find the data point, say so plainly and drop it — never approximate it with an AI guess.
4. **Test the chosen enrichment on the first 10 ranked leads** (`deepline tools execute` per row) and
   show, per lead: the value found, its date, and whether it is about the right person or company.
   **Check the entity**: news and posts can name a similarly named company or a different person — a
   result that is not clearly about this lead's company counts as not found. If fewer than half return
   a usable value, or the entity check fails often, say so and offer the next candidate or dropping
   the data point.
5. **Choose the column it lands in** — and, if the sequencer is the destination, the custom variable
   name it will carry there. For a long raw result (a post body, an article), keep a short extract —
   one or two sentences plus the date and source link — so the field stays readable and the copy step
   is grounded.

Then play back each data point in one line: *what it is, which tool, per-lead or per-company, test hit
rate, cost, and the column it lands in.* This is the Step 5 halt; wait for a yes before the gate.

## Step 6 — Small batch, then ONE gate: the batch, the cost, the writes, the ask

Read declared prices by id:

```
deepline plays describe prebuilt/name-and-domain-to-email-waterfall-batch --json
deepline tools describe <enrichment tool id> --json   # pricing
```

The work-email step is the prebuilt waterfall `prebuilt/name-and-domain-to-email-waterfall-batch`
(first name, last name, domain; mailbox-verified), or `prebuilt/person-linkedin-to-email-batch` when
every row has a profile URL. Its cost depends on which provider in the cascade hits, so it is read
from the pilot, not declared up front.

Run the email play on **10 rows** first (`deepline plays run prebuilt/name-and-domain-to-email-waterfall-batch
--input '{"csv":"pilot.csv"}'`), then read `deepline runs get <run-id> --full --json` for the billed
cost and show the 10 results: company, domain, email found or not. The Step 5 tests already cover any
personalization enrichment.

Then one message, and stop:

- the batch result, including any domain that is obviously wrong (hosting previews such as
  `vercel.app`, `netlify`, `github.io`, `herokuapp`, `wixsite`, `notion.site`, or a social-network domain);
- the full cost, computed and itemized: search results already pulled × 0.02 + remaining people × the
  pilot's observed email cost per row + each personalization enrichment × its row count (per lead or
  per unique company). State it as an estimate from 10 rows; for a per-item-priced enrichment, give
  the per-item price and the cap instead of a total;
- **the writes, in the word:** *"this writes a CSV of N leads with the columns …, creates a campaign
  named … in <sequencer> with N steps, and adds the N leads to it. Those are mutations in your
  sequencer, not reads. The campaign is not activated."*;
- the ask.

This single gate is both the spend approval and the write approval.

## Step 7 — Find work emails and personalization data

1. **Work email.** Run the email play on every remaining row; `deepline runs export <run-id> --out
   emails.csv`. Keep rows where `email_found_and_valid` is true. A miss carries a `miss_reason` —
   skip the person, never guess a pattern. Drop junk domains listed in Step 6 — the person is skipped,
   not guessed.
2. **Personalization data.** Run each approved enrichment only on leads that have a verified email —
   per lead or per unique company, as chosen in Step 5 — as one `.withColumn` per data point in a small
   play, or `deepline tools execute` when it is 20 rows or fewer. Apply the same window and entity
   checks as the test. A lead with no usable value keeps an empty field; that is not a reason to drop
   them.
3. Report found and not found for each.

## Step 8 — Select and save

1. From people with an email, walk the ranked list and keep up to the declared leads-per-company,
   deduping on email, until the target count.
2. Write a CSV with `full_name, first_name, last_name, title, company, domain, location, work_email,
   linkedin_url, lead_source, tier`, plus one column per approved data point. This CSV is the segment:
   it holds only this run, tagged with the lead-source value.
3. Verify the CSV row count equals the kept count. If it does not, say how many landed and stop.

## Step 9 — Draft the campaign, never launch it

1. Ask the copy inputs now: seller, offer and what accepting it requires, product facts, proof, and
   whether they want a third email.
2. **Two habits carry most of the weight, and every email follows both** (the author's practice):
   - **Keep the offer specific to the person receiving it.** Tie it to their role, their company, and
     the fact the search or a data point established — never an offer that would read the same to
     anyone.
   - **Be straightforward about who you are and what you want.** Name the sender and company early,
     say plainly what is being offered and what you are asking for, and do not disguise a sales email
     as something else.
3. Write the steps:
   - **Initial email**, new thread. The reason to write is the ICP criterion the search actually
     filtered on (their growth, their hiring, their stack) — never a claim the data does not support.
     Then the offer, what it gives them, what it asks of them, and a yes/no ask. Keep "free" out of the
     subject.
   - **First follow-up**, reply in thread 3–4 days later (the declared delay). It reaches only
     non-responders: more on what the offer delivers, where the product fits, the proof line if
     cleared, a one-word reply ask.
   - **Second follow-up — only if the installer asked for one**, 7 or more days after the first
     follow-up. Tell them once that response odds this late are very low. Keep it short, give one
     new reason to reply, and make it easy to say no.
   Add spintax to several sentences in the sequencer's own syntax, and avoid spam-trigger phrases such
   as "no cost".
4. **Use each data point through one short per-lead opener**, placed where it replaces the generic
   reason to write — usually the opening line of the initial email. Generate it with a `deeplineagent`
   column (`maxToolCalls: 0`, a `jsonSchema` with one `opener` string) whose prompt is: *write one
   sentence referencing this recent item: {{data point}}; if it is empty, write a one-sentence opener
   from the ICP fact instead, without implying research.* The opener may only restate what the field
   says; it must not infer opinions, results or intent the field does not contain. Every lead gets an
   opener, so no lead is dropped for a missing data point. It travels to the sequencer as a custom
   variable and the copy references it as a merge tag (e.g. `{{opener}}` in Instantly).
5. Review every email as the recipient — a busy member of the ICP triaging the inbox — and fix only
   material objections. Check both habits first: would this offer read the same to anyone, and is it
   clear within two sentences who is writing and what they want? Read the rendered email for one lead
   that has each data point and one that does not. If a preview lead's company does not look like the
   ICP, say so. **No Deepline tool spam-scores copy**; check it with the sequencer's own checker or
   by hand against the trigger-phrase list.
6. Create the campaign: `instantly_create_campaign` with `name` `"<seller> — <offer> — <ICP label>
   (<date>)"`, a `campaign_schedule`, `stop_on_reply: true`, and `sequences[0].steps` holding the emails
   with their `delay` in days. Reuse a timezone from an existing campaign (`instantly_get_campaign`)
   rather than guessing one. No `email_list` (sending accounts) is set. For Smartlead or Lemlist,
   `smartlead_create_campaign` / `lemlist_create_campaign` create the campaign by name only; the steps
   are pasted in the sequencer UI.
7. Add the leads: `instantly_add_to_campaign` with the `campaign_id`, `leads` from the CSV (email,
   first name, last name, company name, and custom variables for `opener` and each data point), and
   `skip_if_in_workspace: true`. Push in batches and re-read the campaign's lead count with
   `instantly_list_leads` afterwards; it must equal the CSV row count. Smartlead:
   `smartlead_push_to_campaign`; Lemlist: `lemlist_add_to_campaign`.

No sender accounts are set, nothing is activated, and no test email is sent.

## Step 10 — Deliver

Report the confirmed ICP in one line, the segment name and count, each data point with its hit rate,
the campaign name, the final copy with readable placeholders, the coverage line, any ICP criterion
the search could not express, and three things the installer does next: add sender accounts and
launch in the sequencer; confirm any proof line is cleared to cite; and reply by hand to anyone who
says yes, because the sequence stops at their reply.

At delivery, offer: *"Want me to save your ICP and settings to a file alongside this? It isn't part of
the skill — it's a note of what you told me: your titles, company profile, geography, exclusions,
data points and offer. Next time you won't re-answer these, and a teammate who has it can run this
without knowing your setup. It stays with you, is never submitted or published, and holds no
passwords or keys."*

## Representative output

### Confirmed ICP

People titled VP or Head of Sales, Director and above, at software companies with 201–1,000
employees that grew headcount more than 20% in the last year, based in the UK and Ireland, excluding
current customers and everyone already in the sequencer. Target: 150 leads, one per company.

### Personalization data points

| Data point | About | Window | Enrichment chosen | Test hit rate | Final hit rate | Field |
|---|---|---|---|---|---|---|
| Latest funding round | company | last 12 months | `predictleads_company_financing_events`, once per company | 4 of 10 | 61 of 150 | Latest funding |
| Recent LinkedIn post | person | last 30 days | a LinkedIn profile-posts tool, capped at 3 posts per lead | 3 of 10 — below half | dropped by the installer | — |

### Lead segment summary

| Group | Leads | Share | Definition |
|---|---:|---:|---|
| Tier 1 — confirmed ICP | 98 | 65% | the ICP exactly as confirmed |
| Tier 2 — size band widened | 52 | 35% | same, 1,001–5,000 employees, widened on the installer's say-so |
| Not kept — no verified email | 19 | — | skipped, never guessed |

Titles kept: 61 VP of Sales · 47 Head of Sales · 42 Director of Sales.

### Initial email, as one lead would receive it

Subject: Pipeline review for Northwind

> Hi Dana,
>
> Congrats on Northwind's Series B in March — a round like that usually means the sales team grows
> faster than the pipeline data behind it.
>
> I'm with Contoso. I'd like to offer a pipeline review for Northwind, on us: a 30-minute call where
> we look at your last two quarters of opportunities and show where deals stalled and why.
>
> There's nothing to buy, and you keep the findings either way.
>
> Want me to set one up?
>
> Sam

### Coverage line

212 found across two tiers · 9 removed by title · 169 with a verified email · 150 kept after one
per company, filled tier 1 first · funding found for 61 of 150 · 0 already in the sequencer · draft
campaign, not launched.

## What this skill does not claim

- The widening pattern was measured on one ICP (security leaders); how often a strict ICP falls short of its target for other personas was not measured.
- The 1.4× over-sourcing ratio comes from one run's losses and will differ by persona and market.
- The personalization step was never run end to end; no hit rate, cost or accuracy for any data point was measured, and the figures in the representative output are invented.
- Choosing an enrichment on a 10-row test is a small sample; the full-run hit rate can differ.
- News and post results can be about a different company or person with a similar name; the entity check reduces this and does not eliminate it.
- No reply rate, meeting rate or deliverability outcome was ever measured — the source campaign had not launched when this skill was written.
- The Deepline build of this skill has not been run end to end; the counts above were measured on Clay's people search and work-email function, and Deepline's search index and email waterfall will return different numbers.
- The email cost at the gate is extrapolated from a 10-row pilot; the waterfall's cost per row depends on which provider hits.
- Some ICP criteria have no search field; the skill names them and approximates or skips them rather than claiming to have filtered on them.
- The proposed title exclusions are a starting list from one run; the installer confirms them every time.
- Company-name-to-domain lookup can return a wrong company for a common name; only obvious junk is filtered.
- One lead per company and the source run's tier definitions were run-time defaults, not argued for.
- The 250–300 test size, the 3–4 day and 7-day spacing, the low response odds after email 2, and the two copy habits are the creator's practice; this skill did not measure them.
- The broader reading — that for senior personas the list, not the copy, is generally the constraint — was not confirmed by the creator; one run found it true once.
- The logic comes from the creator's stated intent and one live run, not from a table or workflow that already encoded it.

## What good looks like

A good run starts with an ICP the installer confirmed in their own words and a search they approved
in plain words, and ends with a segment whose count equals the CSV exactly, a coverage line that
accounts for every person found — removed by title, no email, over the per-company limit, or kept —
and a draft campaign whose preview reads naturally for a real lead who looks like the ICP. Tier 1
fills first, and any widening was asked for and appears as its own row. Every personalization data
point shows the enrichment chosen, why, its test and final hit rates, and a preview for a lead
without it that still reads well. A thin run says so: *"your ICP found 60; you asked for 200; I
stopped before widening"*, or *"posts came back for 3 of 10, so I dropped them."* A bad run looks
finished and hides one of these — an ICP the agent inferred, a criterion silently dropped from the
search, a segment count that does not match, a tier widened without asking, a non-buyer title in the
list, a guessed email, an opener about the wrong company, a data point with no fallback that drops
leads from enrollment, or a follow-up written as if the person had replied.

## Rules

- **NEVER** infer the ICP. Ask for it, play it back, and wait for a yes.
- **NEVER** use saved business context as the ICP without showing it and getting a yes.
- **NEVER** drop an ICP criterion silently; name any the search cannot express.
- **NEVER** pick a personalization enrichment from memory. Read what the Deepline catalogue has, compare on inputs, cost, output and scope, and test on 10 leads.
- **NEVER** let AI generate a data point the enrichment did not return; a missing value uses the fallback.
- **NEVER** activate, send, pause or delete a campaign, or send a test email. The installer launches in the sequencer.
- **NEVER** guess an email address or a domain. No verified result means the person is skipped.
- **NEVER** widen past tier 1 without asking, and never mix tiers without labelling them.
- **NEVER** add anyone already in the sequencer's workspace; Step 4 removes them and `skip_if_in_workspace` guards the push.
- **NEVER** cite a customer result the installer has not confirmed they can use.
- **NEVER** send an offer that would read the same to anyone, or hide who is writing and what they want.
- **NEVER** schedule the first follow-up outside 3–4 days, or a third email sooner than 7 days after the second, without the installer choosing that.
- **NEVER** clear or blank a populated field; the upsert removes null values.
- **MUST** run the free title cleanup and per-company pass before any paid step.
- **MUST** hold one gate before the paid and write steps, carrying the batch, every cost and every write.
- **MUST** verify the segment count against the CSV before creating the campaign.

## Worked example

The source run, on Clay before this port. A GTM ops lead at a compliance-automation vendor asked for 200 leads in their ICP: CISOs and heads of
security at rapidly growing software companies, then a two-email campaign offering a free security
assessment. The saved business context described a different company, so it was
not used. Asked where the leads should be based, they chose the US and Canada; "rapidly growing"
had no number behind it, so the reference's default of more than 20% 12-month headcount growth was
applied and recorded as borrowed. Two earlier lists and two empty drafts from the same vendor already existed; they chose a fresh
build excluding everyone already contacted. Tier 1
returned 141, so tiers 2 and 3 were added (292 total). Title cleanup removed 12 — Field CISOs,
deputies, program managers — leaving 280 across 252 companies. No extra personalization data point
was used on this run; the copy personalized on first name, company and the growth the search
filtered on. The domain lookup returned 250 usable domains (two junk hosting domains dropped); the
email lookup found 254 of 278. One per company left 230, and the first 200 in tier order were saved
as a segment of exactly 200. A draft campaign was created on that segment with a three-day
follow-up. Clay's spam check scored the first draft 56
("fair": no spintax, "no cost" flagged); after adding spintax and changing "no cost" to "on us" it
scored 100 (Deepline has no spam checker; Step 9 says what to use instead). The preview lead worked at a security vendor, which was flagged. Nothing was launched.
