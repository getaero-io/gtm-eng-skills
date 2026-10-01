---
name: source-candidates
description: |
  Turn a hiring conversation into a scored candidate list with Deepline — start from two or three
  profiles of people they would hire, or from the experience they are looking for, then split
  every criterion into what the people search can filter, what only a scorecard can judge, and
  what is not observable at all, and run one query per population who could do the job. Use
  whenever someone asks: find me candidates for this role, source people for this job, build a
  candidate list from this JD or brief, find me more people like these profiles, who could fill
  this position, find senior engineers in Berlin with eight years experience, build a talent pool
  or sourcing pipeline, or source passive candidates. Outreach lands as drafts with one-click
  links that compose in the recruiter's own mailbox; it sends nothing. Do NOT use
  it to translate a sales ICP into filters (icp-matrix-builder), to build a list of buyers to sell
  to (build-prospect-list), to read job postings as a buying signal (hiring-radar), to find
  decision-makers at one named company (find-decision-makers-at-company), to track when your own
  contacts change jobs (track-champion-job-changes), or to write the job description itself.
category: build-lists
type: play
tags: [jd, brief, exemplar-profiles, people-search, scorecard, outreach-drafts, persona:recruiter, persona:hiring-manager, persona:talent-partner, persona:founder]
keyword: source-candidates
ported_from: clay-run/clay-skill-creator/skills/davide-grieco/source-candidates-2
---

# Source candidates (every criterion goes in one of three places)

The insight: **the criteria that separate a good candidate from a plausible one are exactly the
ones the search cannot hold — and it does not tell you when it drops them.** This was first
established against Clay's people-search query reference (2026-08), and the same shape holds on
the people search this skill runs in Deepline, `crustdata_v3_person_search`:

- A people search takes filters, not judgments. Scoring and ranking language — *score*, *weight*,
  *rank*, *prioritise*, *top performers*, *proven track record* — has no field to land in. Those
  are the words every hiring brief is written in.
- When some requested criteria cannot be expressed, **a valid query is still produced from the
  rest.** Correct behaviour, and it means no error is raised.
- The search drops some of what you *did* express, too. Its own schema
  (`deepline tools describe crustdata_v3_person_search --json`) documents that **`in` and `not_in`
  lists longer than five items can be silently ignored** — split them into separate conditions —
  and that a piped value under the all-words operator `(.)` is **AND, not OR**: `"paid|media|sem"`
  asks for profiles carrying all three words.
- Some things are not filterable at all: prior founder exit history, whether someone wants a job,
  compensation, and actual performance.

So a brief goes in, a plausible query comes out, a plausible list comes back, and the half of the
brief that was actually discriminating has evaporated. Nothing in the output looks wrong.

**And the obvious repair makes it worse.** Faced with *"strong quantitative background"*, the
instinct is a keyword condition on the about section for `analytics` or `SQL`. Two things then
happen at once. It selects for people who narrate their own skills, which is not the same
population as people who have them. And text matching is not substring matching you control: on
Clay's surface `contains` was documented as whole-word (`contains "engineer"` matched "Software
Engineer" and **not** "engineering"); on `crustdata_v3_person_search`, `(.)` is documented as an
all-words match and `[.]` as an exact phrase, and whether `engineer` reaches `engineering` is not
stated — **check it on the sample before trusting it.** Either way the proxy can quietly exclude on
spelling. A soft criterion belongs on a scorecard or in a separately-queried population. Never in
a keyword.

**A second thing follows, and it is why this skill is a conversation rather than a form.** A
find-people-like-this-profile engine does not solve it. **The problem was never that the feature
is missing. The problem is that a lookalike engine chooses the similarity axes and does not tell
you which.**

Measured on Clay's `find-people-lookalikes` action on 2026-08-28, seeded with one exemplar — a
growth manager at a physical-security company — it returned 26 people, and it had anchored on
exactly two things: **the literal job-title token**, and **the seed's employer industry**. So the
results were IT-ops and security vendors across nine countries, including an HR "People Growth
Manager" caught by token match on *Growth Manager*. Both axes it chose were ones the hiring manager
had explicitly ruled out — *"that's me recognising logos, not a requirement"*. It reproduced the
over-specification error, silently, at speed.

**Deepline has no person-lookalike tool** (searched 2026-09-30: `deepline tools search "similar
people lookalike profiles"` returns company lookalikes only). The nearest route is a company
lookalike — `discolike_discover`, seeded with the exemplar's employer domain — which returns
employers similar to theirs; the people at those employers are then a population you query and
judge. It has the same vice one level up: it chooses what "similar company" means.

That is the whole case for the conversation. Three profiles a hiring manager likes share dozens of
attributes and **they care about four of them. Which four is judgment that exists only in their
head** — and neither a decomposition nor a lookalike engine recovers it. Use lookalikes as **a
population you seed and then judge** (Step 4), never as a substitute for asking. And note the
approximation you must still disclose either way: "companies like the exemplar's" arrives as an
industry anchor or a list of lookalike employers, not as the thing the hiring manager meant.

## Declared inputs

**Nothing here ships with a value.** Every row is the installer's. Ask for it, never substitute a
plausible default, and where an answer does not exist say which step becomes unavailable rather
than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The role** | the title, and one line on what the person will own | **stop.** Nothing downstream is derivable |
| **The seed** | either two or three profiles of people they would hire, or the specific experience they are looking for, in their words | **stop.** This is the intake; a JD alone is context, not a definition — see Step 1 |
| **Which shared attributes matter** | of everything the seed profiles have in common, the ones that are the point | the skill cannot guess and must not average them. It proposes and asks |
| **Location** | cities, states, countries, or a region — and whether remote counts, and remote from where | no default. "Anywhere" is a real answer that roughly triples yield; never quietly use the company's HQ |
| **Seniority and experience** | a seniority band and a years-of-experience floor or range | no seniority filter at all: an unmentioned level is omitted, never guessed |
| **Scorecard criteria and weights** | the criteria a filter cannot hold, each weighted | no default. Weights nobody stated are this skill's opinion wearing numbers |
| **Band cut-offs** | the score at which a candidate is worth contacting | **70 / 40 out of 100 is a stated default** — strong from 70, possible 40–69, weak below. Nothing validates it against hire outcomes; see the gaps |
| **Per-employer cap** | how many candidates may come from one company | **2 is a stated default.** Without a cap one large employer floods the list. The search has no native per-company cap, so the agent applies it after paging (Step 7) |
| **Do-not-source list** | companies not to approach — current employer, customers, partners, anyone under agreement | no exclusions applied, and the output must say so. This is the omission a recruiter notices from the wrong side |
| **Suppression list** | optional list of people already in the pipeline, by profile URL, or name plus employer | no dedupe against an existing pipeline |
| **Target list size** | how many candidates they want to review | **50 is the stated default** — enough to show the yield split across populations, small enough that a hiring manager actually reads it. Raise it freely; nothing validates 50 beyond it being a readable list |
| **Contact address** | personal email, work email, or profile link only | **profile link only.** Never default to a work address — see Step 9 |
| **Sender and pitch facts** | who the mail is from and their relation to the role, plus level, comp band if shareable, hiring manager, team size, remote policy, funding or traction, and the one thing that makes this different | the copy step is skipped rather than filled with invention |
| **Availability heuristic** | on or off, and the tenure threshold if on | **off.** It is a guess, not a signal — see Step 4 |
| **The Deepline balance** | nothing to supply beyond being signed in — but read it, because it sets the shape of the run, not whether it happens | **scope the run down; never refuse it.** `crustdata_v3_person_search` is priced per returned result (0.02 credits per result per `deepline tools describe`, 2026-09-30; empty pages are free). On a thin balance, run **two populations at 25 rows each** and say the populations are not exhausted — which is true, and is the honest thing to report |

## Step 0 — Verify the platform, pull the field list live, and say where the work runs

```
deepline preflight --json
```

Not connected, or no CLI: `npm install -g deepline && deepline auth register --wait auto`, then
re-run. **Say which Deepline organization, out loud** — preflight prints it.

Pull the query surface fresh every run. **Never write a query from a remembered field list:**

```
deepline tools describe crustdata_v3_person_search --json
deepline tools describe crustdata_v3_person_search_autocomplete --json
```

**Confirm from the schema you just pulled** that it still carries `years_of_experience`, the
`education.schools.*` family, and per-experience seniority
(`experience.employment_details.current.seniority_level` and `.past.seniority_level`). Those three
are the most common criteria in any brief; a search without a years-of-experience field forces you
to approximate it with a count of roles, which measures job-hopping. If any has gone, say so and
stop rather than approximating. **Use the autocomplete tool for exact values** — seniority levels,
titles, industries, locations — before filtering on them. It is free (`pricing.creditsPerUnit: 0`)
and it is what stops a zero-result query that was only a spelling.

**Search the catalog before concluding anything is unavailable, and never plan from memory.** This
is the mistake that looks like a platform limitation and is not one:

```
deepline tools search "linkedin profile enrich" --json
deepline tools search "personal email finder" --json
deepline plays search "work email from linkedin" --json
```

Search two to four synonyms; a single query can miss the tool that exists. Identify every tool by
its **tool ID**, confirmed with `deepline tools describe <id> --json` — which is also where its
input schema and price live — and every prebuilt by its play name, confirmed with
`deepline plays describe <name> --json`.

**Three separate meters run in this skill and they are not interchangeable.** Cost is a design
property here, not a footnote:

| The work | Where it runs | What it consumes |
|---|---|---|
| The conversation, decomposing exemplars, writing queries, designing the scorecard | the agent | nothing |
| Looking up exact filter values (`crustdata_v3_person_search_autocomplete`) | a Deepline tool | **free** |
| Sizing a population (`crustdata_v3_person_search` with `limit: 1`) | a Deepline tool | **one result's price** — the response carries `total_count` for the whole match |
| Paging results (`crustdata_v3_person_search`) | a Deepline tool | **credits per returned result** — 0.02 per result at describe time. Each row already carries a profile URL, headline and per-role descriptions |
| Reading the about section or a fuller profile (`crustdata_v3_person_enrich`, up to 25 profile URLs per call) | a Deepline tool, or a play over a CSV | **credits per matched record**, varying with the field groups requested — priced after execution, so price it on a 2–3 row pilot in Step 6 |
| Seeding an employer-lookalike population (`discolike_discover`) | a Deepline tool | **credits, priced from returned usage** — pilot it |
| Finding a work email (`prebuilt/person-linkedin-to-email-batch`) | a Deepline play | **credits per row** — priced on the pilot in Step 6 |
| Finding a personal email (`leadmagic_personal_email_finder`) | a Deepline tool | **0.68 credits per result** at describe time |
| Scoring against the scorecard, and ranking across the set | the agent, over the text the search returned | **free** |
| Writing the copy — **per population, not per row** | the agent | **free** |
| Building the compose links | the agent | **free** |

Scoring 300 candidates in the agent costs nothing. Scoring them as a `deeplineagent` column in a
play bills 300 rows for the same arithmetic, and is right only when the play is a working surface a
team returns to. Choose deliberately, and say which you chose.

## Step 1 — Have the conversation. It is the intake, not a formality

**A JD is context, never the definition.** It was written to attract applicants and it is full of
the unfilterable — *ownership*, *bar-raiser*, *thrives in ambiguity*. Read it if there is one, and
still do this step.

Ask for the role and where, then take **one of two entry points. Let them pick; both are real:**

**Seed A — exemplars.** *"Give me two or three profiles of people you'd hire for this."* Then go
to Step 2. This is the faster route and usually the more accurate one, because a hiring manager can
recognise the right person long before they can specify them.

**Seed B — described experience.** *"Tell me the specific experience you're looking for."* Then
follow up on what they actually said, not from a checklist. The useful follow-ups are the ones that
distinguish populations: have they done this exact job before or the adjacent one, at what scale,
building the team or running an existing one, and what would rule someone out.

Then **write the whole definition back to them and let them correct it** — the populations, the
three-way split from Step 3, and the scorecard. Do not keep interviewing first. A hiring manager
corrects a wrong population in four words and answers an abstract question in a paragraph that has
to be reinterpreted anyway.

**Never invent a criterion the conversation did not contain.** A role that was never described as
needing a degree does not get a degree filter because it sounds like it should. Anything the skill
proposes rather than heard is **labelled as proposed, on screen, before it reaches a query.**

## Step 2 — Decompose the exemplars, then ask which parts are the point

Only on Seed A. For each profile, get the attributes — either pasted by the installer, free, or by
running `crustdata_v3_person_enrich` on the two or three profile URLs (one call takes up to 25),
priced live in Step 6. Request only the field groups you will read — `basic_profile`,
`experience`, `education` — because the requested groups drive the price. Read off:

current title · seniority · years of experience · current employer, its industry and size ·
previous employers and the shape of the path · education · **and the words they use about their own
work**, which is the raw material for the scorecard, not for a filter.

Then **lay out what the profiles share, and ask which of it is the point.** This is the question the
skill exists to ask, because the exemplar is over-specified: three people the hiring manager likes
may all have been at Series B companies, all have MBAs, and all be in London — and only one of
those three is a requirement. Averaging them produces a query nobody asked for. Guessing produces
one that looks right.

Where they differ, **that is usually two populations, not noise.** An ex-consultant and a lifelong
operator are not one blurred profile with error bars.

**If you seed an employer lookalike, read what it returns as evidence about the exemplar rather than
as candidates.** `discolike_discover` with the exemplar's employer domain returns the companies it
thinks are similar, and what it anchored on — industry, size, business model — tells you which
attributes of that employer are loudest, which is the question you are asking the hiring manager
anyway. **Show them that**: *"the machine thinks the point is that they work in security — is it?"*
A hiring manager corrects that in four words. Keep the employer list as a seeded population per
Step 4 if it is any good, and drop it without ceremony if not.

**The exemplar's employer becomes an anchor, and you must say so.** Either an industry anchor —
`experience.employment_details.current.company_industries` or
`.company_professional_network_industry`, with values taken from autocomplete — or a list of
lookalike employer domains on `experience.employment_details.current.company_website_domain`. Both
are approximations of "companies like theirs"; tell the user which one was applied. **Only** filter
to exact employer domains when the installer explicitly wants people *at those exact companies* — a
farm list, not a similarity anchor.

## Step 3 — Split every criterion three ways, in front of the person who set them

**Show the table. A criterion that appears nowhere has been dropped, and dropping it silently is
the failure this skill exists to prevent.**

**Filterable — goes in the query.** Confirm each against the schema from Step 0:

- years of experience, as a number — `years_of_experience`
- job title, current or past — `experience.employment_details.current.title` / `.past.title`, or
  the normalized `basic_profile.normalized_title.matched_title` — and title exclusions, which must
  never be dropped
- seniority — `experience.employment_details.current.seniority_level`; take the value set from
  autocomplete, never from memory
- function or discipline — `experience.employment_details.current.function_category`,
  `basic_profile.normalized_title.department` and `.sub_department`
- employment type — `experience.employment_details.employment_type`
- named employers: **current** employer under `experience.employment_details.current.*`;
  **former** under `.past.*`; **any tenure** under the unqualified `experience.employment_details.*`
- employer industry and size — `company_industries`, `company_headcount_range`,
  `company_headcount_latest` under the same three families
- role start and end dates, so "has held this title two years" and "started over 30 months ago"
  are both expressible — `start_date`, `end_date`
- location of the person — `basic_profile.location.city` / `.state` / `.country`, or
  `geo_distance` for a radius — and separately the location of the role,
  `experience.employment_details.location`
- education: `education.schools.school`, `.degree`, `.field_of_study`
- languages on the profile — `basic_profile.languages`
- keywords in headline, about, and experience descriptions — `basic_profile.headline`,
  `basic_profile.summary`, `experience.employment_details.current.description` — **matched by the
  all-words or exact-phrase operators, and this is the trap**

**Scorecard — a real criterion, not filterable, judged after the search.** Everything soft lands
here: depth versus breadth, has-done-this-exact-job versus adjacent, quantitative rigour, ownership
versus execution, scrappiness, whether the scale resembles yours, whether they built the team or
inherited it. Each gets a **weight** and **the profile field its evidence is read from** — headline,
about, or experience descriptions.

**Not observable, or only partly — named out loud, then handled.** This is a go-to-market
database, not a candidate database:

- **whether they want a job.** The only signal is `professional_network.open_to_cards`, which
  carries values such as `CAREER_INTEREST` for people who opted in on their profile. It is a real
  signal where present and **silent where absent** — most people never set it, so its absence is
  not a no. Never filter the main population on it; if the installer wants it, run it as a second
  pass like the availability heuristic and report both yields
- **compensation**, current or expected
- **work authorisation**, visa status, notice period
- **detailed skills.** `skills.professional_network_skills` is filterable, but it is the
  self-reported skills list — self-narration again — so a tools-and-technologies checklist is
  scorecard material at best, never a gate
- **actual performance** — references, attainment, promotion velocity, whether any of it went well
- **prior founder exit history**, not filterable, and specifically **not** to be approximated by
  excluding people who are currently founders

**NEVER move a scorecard criterion into the query as a keyword.** The two reasons are at the top of
this file: it selects for self-narration, and text matching excludes on spelling. If a soft
criterion must shape the search, the honest form is **a separate population** whose people
genuinely sit somewhere else — not a keyword bolted on.

**One carve-out, and it is narrow: keywords for category, never for quality.** Some titles do not
encode which *discipline* a person practises, and that is a hard category. Measured on Clay's
people search on 2026-08-28: at early-stage B2B companies, a similar-title expansion of ("Growth
Manager", "Growth Lead") reached into **sales** roles — founding BDRs, enterprise AEs, a VP of
Sales, and in the worst case a Director of ASIC Digital Design caught on the token *Growth*.
**14 of 25 rows were the wrong ladder.** Adding paid-marketing terms to the **current role's
description** — "paid search", "paid media", "google ads", "performance marketing", "demand
generation", "SEM", "paid social" — returned 7 rows of which **7 were the right ladder.**

On `crustdata_v3_person_search` there is a better first move: **discipline is a field.**
`experience.employment_details.current.function_category` and
`basic_profile.normalized_title.department` / `.sub_department` express *marketing, not sales*
directly, with no keyword. Try them first and check the sample. Use a description keyword only when
the category field does not separate the ladders — and then as an **`or` group of `[.]` phrase
conditions**, one per phrase, because a piped `(.)` value means *all of these words*, not *any*.

Three conditions on using it, and they are the whole difference between this and the failure above:

- **Category, not quality.** *Is this marketing or sales* is a fact about the role. *Strong
  quantitative background* is a judgment about a person. The first is a legitimate keyword; the
  second is scorecard material and always was.
- **The current role's description, not the about section.** Measured the same day on Clay: the
  same keyword list against the about section returned 8 rows of which 2 were the weakest
  already-scored candidates. The about section is where people narrate themselves, so a keyword
  there reintroduces exactly the self-narration bias — the description of what a role *was* is
  closer to a fact.
- **Run it as its own population, never as a patch to an existing one.** Precision cost recall
  hard: 25 rows became 7, exhausted. Report both yields and let the installer see the trade rather
  than silently shrinking their list.

## Step 4 — One query per population

A **population** is a group defined by where its people sit right now: title, seniority, and the
kind of employer. It comes out of Step 1 or Step 2 — **however many the conversation actually
produced.** One is a legitimate answer. Do not manufacture a third for symmetry.

**Run each one as its own query, and keep the label on every row it returns.** The yield per
population is the part a hiring manager can act on: *"forty here, six there, none at all from
consulting"* answers whether to widen the location, drop a level, or stop waiting for people who
are not there. A single merged query cannot report it — an `and` across populations asks for the
intersection, an `or` returns rows that no longer say which group they came from.

**A seeded population is a legitimate fourth kind, and it plays by different rules.** People at the
employers `discolike_discover` returned are anchored on an engine's idea of a similar company, not
on the brief — so they are **not comparable** to the queried populations and must never be folded
into one yield line. Report them as their own labelled population, name the exemplar that seeded
them, say what the engine appears to have anchored on, and filter them against the brief **after**
the fact rather than pretending a query held. Their virtue is sometimes surfacing a population the
decomposition missed; their vice is that the axes are not yours.

**Hold location, seniority and the experience floor constant across populations.** Those come from
the brief. What varies is title, employer type, and history — otherwise the yields are not
comparable and the split says nothing.

**The syntax that decides whether the query means what you think.** All of this is from the tool's
schema, and each line is a mistake worth not making:

- **Titles: take exact values from autocomplete, and list them.** There is no synonym expansion;
  `in` on `experience.employment_details.current.title` matches the strings you give it, so
  "Head of Growth" and "VP Growth" are two values, and more than five values is two conditions in an
  `or` group — a sixth value can be silently ignored. `basic_profile.normalized_title.matched_title`
  is the normalized alternative and is often the better net.
- **Current, past and any-tenure are different field families.** `experience.employment_details.
  current.*` for people **currently** there, `.past.*` for former, the unqualified
  `experience.employment_details.*` for any tenure. A generic role search and anything phrased
  *currently* means `current`; *former*, *past*, *alumni* mean `past`; *has experience at* and
  *ever worked* mean the unqualified family. Swapping these silently changes who you get.
- **Conditions that must hold for the same role go in an `all_of` group.** Plain `and` combines at
  the document level, so `current.title` and `current.company_industries` in a plain `and` can be
  satisfied by two different current roles of a person who holds two. An `and` group nested inside
  `op: "all_of"` is matched within a single role.
- **Do not guess a seniority level.** If the conversation did not name one, omit the filter — the
  title condition already carries the role. And keep the ladders apart: individual-contributor
  searches must not carry leadership values.
- **Exclusions go in every population's query, identically**, and are never dropped: a `not_in` on
  `experience.employment_details.current.company_website_domain` for the do-not-source list (five
  values per condition, so a longer list is several conditions), `(!)` on the title for the wrong
  ladder, and `post_processing.exclude_profiles` for the suppression list's profile URLs. A title
  list does **not** exclude unrelated titles by itself.
- **Cap per employer in the agent.** The search has no per-company limit. Page past the target —
  about 1.4× — then keep at most two rows per
  `experience.employment_details.current[].crustdata_company_id`. Without it, one large employer
  can be most of a list — a real failure in candidate sourcing, where thirty people from the same
  org is one conversation, not thirty options.

A shape that follows the schema pulled on 2026-09-30. It has not been executed, which says nothing
about whether it is the right query for anyone's role — confirm field names and values on the
sample:

```json
{
  "filters": {"op": "and", "conditions": [
    {"field": "years_of_experience", "type": "=>", "value": 8},
    {"field": "basic_profile.location.city", "type": "in", "value": ["London"]},
    {"op": "all_of", "conditions": [{"op": "and", "conditions": [
      {"field": "experience.employment_details.current.seniority_level", "type": "in", "value": ["<from autocomplete>"]},
      {"field": "experience.employment_details.current.title", "type": "in", "value": ["Head of Growth", "VP Growth"]},
      {"field": "experience.employment_details.current.company_industries", "type": "in", "value": ["<from autocomplete>"]}
    ]}]},
    {"field": "experience.employment_details.current.company_website_domain", "type": "not_in", "value": ["competitor.com"]}
  ]},
  "limit": 25
}
```

**The availability heuristic is off by default and is a guess when on.** With only an opt-in
open-to-work flag, the nearest thing for everyone else is tenure — a current role that started more
than roughly 30 months ago (`experience.employment_details.current.start_date`). Turning it on
trades a large part of the list for a hunch about restlessness. If the installer wants it, run it
as **a second pass over the same population** so both yields are visible and the cost of the hunch
is on screen. **Label it a guess in the output, every time.**

**If asked to filter on a protected characteristic or a proxy for one: say what it is, offer the
clean equivalent, then build what they asked for.** The two that come up are education dates used
to infer age — in the United States an ADEA age-discrimination exposure, and age is protected under
UK and EU equality law — and school or name used to infer ethnicity or nationality. The clean
equivalents are years of experience and seniority, which measure what a brief actually means.
**Say it once, name the exposure, then do as they asked.** This skill warns; it does not refuse,
and it does not repeat the warning.

## Step 5 — The sample gate: 25 rows per population, before anything else

The only step that catches a query which is syntactically valid and semantically wrong.

```
deepline tools execute crustdata_v3_person_search --input '{"filters": {...}, "limit": 1}' --json    # sizes it: total_count
deepline tools execute crustdata_v3_person_search --input '{"filters": {...}, "limit": 25}' --json   # the sample
```

**There is a cheap count.** `limit: 1` returns `total_count` for the whole match at the price of
one result. The schema notes `total_count_relation` (exact or a lower bound) and that it is
currently returned as `null` — so treat a large total as an estimate. Size every population before
sampling; a population of four does not need a 25-row sample to discover it.

**Pagination is by cursor.** Pass the response's `next_cursor` as `cursor` for the next page; a
`null` cursor means no more results. Keep each population's cursor with its label — it is how Step
7 continues without re-buying the sample.

**Read the field names off this sample. Do not assume the output shape.** Per the tool's output
schema the default response carries the name, headline, current title, location, the profile URL
(`social_handles.professional_network_identifier.profile_url`), and per-role `title`,
`description`, `start_date`, `seniority_level` and employer fields for current and past roles —
which is most of what the scorecard reads. It does **not** list the about section
(`basic_profile.summary`) or `years_of_experience` in the default output, though both are
filterable. Ask for them with the `fields` parameter; an unsupported path returns a `400` whose
`metadata.available_fields` lists what can be selected. What is still missing goes to Step 6.

Report per population before proceeding: **the total, rows returned, whether more exist, and three
named profiles a human can eyeball.** Then one decision each — proceed, rewrite, or drop:

- 25 with more available: the population is real. Proceed.
- Under ten with none more: thin here. Say the number and offer the three levers — widen location,
  drop a level, relax the experience floor — as a choice, not a silent fix.
- Zero: **a real answer, and one of the most useful this skill produces.** Never pad it, never
  loosen the query to avoid reporting it, never fold the population into another one. But first
  rule out a spelling: a filter value not taken from autocomplete is the commonest false zero.
- Obviously the wrong ladder or industry: the query is wrong, not the market. Rewrite and re-sample.

**On a credit or billing error do not retry blindly** — backoff never helps. Read the message. If
the balance is exhausted, **stop paging and say so**, quoting the `recovery` top-up command the
error carries exactly — a half-built list reported as complete is worse than a stated shortfall. A
`400` is a malformed query or an unsupported field; read `metadata.available_fields` and fix it. A
rate limit may be retried once.

## Step 6 — State the cost, then wait

Nothing past here is free. Put the whole bill on screen and get an explicit yes.

- **Search results**: target size per population, at the per-result price from `describe`, plus the
  25 already spent on each sample.
- **Per-row enrichment — the about section, and optionally the address.** The search already gave
  a profile URL, a headline and per-role descriptions. Enrichment is for what it did not give.

  **The profile.** `crustdata_v3_person_enrich` takes `professional_network_profile_urls` (up to 25
  per call) and a `fields` list of groups — `basic_profile` carries the headline and about section,
  `experience` the full role history with descriptions, `education` the schools. It is priced per
  matched record and the requested groups change the price, so **request only what the scorecard
  reads, and price it on a 2–3 row pilot**: run it, then read the exact charge with
  `deepline billing usage --json`. Confirm the tool ID and its schema live, because tools and
  prices drift:

  ```
  deepline tools describe crustdata_v3_person_enrich --json
  ```

  It matches on the profile URL the search returned, so wrong-person resolution is not the risk it
  is with a name lookup — **stale data is.** Check the returned current employer against the row
  you sent before scoring — that is Step 8's `identity_conflict`, and it is free.

  **The address**, only if asked for:

  - **Work address** — `prebuilt/person-linkedin-to-email-batch`, a waterfall play that takes a CSV
    of profile URLs and returns `email`, `email_source`, `email_validated` and `miss_reason` per
    row. Run it on a pilot slice first and read the real spend with `deepline runs get <run-id>
    --full --json`. A miss carries a `miss_reason`; never read an empty `email` as a failed run.
  - **Personal address** — `leadmagic_personal_email_finder`, one profile URL per call, 0.68
    credits per result at describe time. Expect a lower hit rate than work addresses.

  Name four things before spending: **what runs** (the tool ID or play name), **what goes in**
  (which fields, from which population's results), **what to verify in the response** (a call can
  succeed and return nothing — check for the field you need, not for success), and **what it costs
  per row.** Multiply by rows, out loud.

- **How it runs at scale.** `deepline tools execute` is right for proving a tool on two or three
  rows, and wrong for a hundred. At scale, write the candidates to a CSV and run a play: the work
  email prebuilt takes the CSV directly
  (`deepline plays run prebuilt/person-linkedin-to-email-batch --input '{"csv":"candidates.csv"}'`),
  and a profile enrichment is a short custom play with one `.withColumn` wrapping
  `crustdata_v3_person_enrich` (see the deepline-gtm skill's plays recipe; `deepline plays check`
  before running). Export with `deepline runs export <run-id> --out <final.csv>`.

  **Build nothing else.** A play run persists its dataset in the Deepline customer DB, and that is
  the only thing this skill leaves behind. The deliverable itself is the CSV and the report.

- **Scoring and copy: keep them in the agent, and say so.** Both are free there and both are worse
  as a per-row play column for this job. Scoring per row bills for judgment the agent does at no
  marginal cost once the text is in hand, and a per-row scorer reads each candidate **in
  isolation**, which cannot rank a set. A deterministic formula cannot help at all here: every
  scorecard criterion reads prose, and the parts a formula could compute are already query filters.
  **Copy is per population, so a per-row generator is a category error** — three populations need
  three drafts, and generating a hundred produces each one blind to the others. Score in a play
  (`deeplineagent` column) only when the list must be a living surface a team works in, with rows
  still arriving after this run ends; say which you chose and why.

Then wait. **Spending someone's money without having asked is a defect, not a style.**

## Step 7 — Page the full set, then score it

Page each population separately, continuing from its own `next_cursor`, while more results exist:

```
deepline tools execute crustdata_v3_person_search --input '{"filters": {...}, "limit": <n>, "cursor": "<next_cursor>"}' --json
```

Stop at about 1.4× that population's target (the per-employer cap removes some), or when the cursor
comes back `null`, or on the billing rules in Step 5 — whichever comes first. **Keep the population
label on every row**; it is the axis the whole deliverable is built on and cannot be reconstructed
later. Then apply the per-employer cap and trim to the target.

Then score against the Step 3 scorecard and nothing else:

- **Every score quotes the profile text it was read from**, one line, naming the phrase. A number
  with no evidence is not reviewable and cannot be defended to a hiring manager.
- **Score only what the scorecard names.** A criterion nobody weighted does not quietly influence
  the number here.

## Step 8 — Verdicts: evidence status first, then the band

Two verdicts. The second is emitted only when the first is `scored` — a band on an empty profile is
the error this split prevents.

**Part A — evidence status, in precedence order. First match wins.**

1. `identity_conflict` — the returned record contradicts the query that found it: current employer
   or title is not what was filtered for. Profile data goes stale. Check it free, from the row you
   already have, before scoring.
2. `suppressed` — on the do-not-source or existing-pipeline list. Reported, never scored, never
   contacted.
3. `unscoreable` — **the profile carries no text the scorecard can read**: no about section, no
   experience descriptions, a headline that repeats the job title. **Not a zero and not a weak
   candidate.** It skews senior, because the people least likely to narrate their work are often
   the ones who have done the most of it. Excluded from the ranking, reported as its own group,
   worth a human skim on title and employer alone.
4. `scored` — the scorecard had evidence to read.

**Part B — the band, only when Part A is `scored`.** Weights sum to 100.

1. `strong` — 70 and above. Worth contacting.
2. `possible` — 40 to 69. Worth a skim first.
3. `weak` — below 40. Reported; not contacted, and never padded into the list to hit a number.

**The 70 and 40 cut-offs are a stated default, not a measured one.** No hire-outcome data anywhere
in this skill validates them. They exist so it is runnable rather than aspirational, and they are
the installer's to move — say what they are, say they are unvalidated, change them without argument.

## Step 9 — Outreach copy, per population, drafts only

**Copy is per population — not per candidate, and not one template for the role.** That is the
point of splitting them: they are moved by different things. The operator wants scope and budget;
the person who builds wants to own a surface; the consultant wants to stop advising and start
owning. One email to all three lands with none of them.

**Derive the pitch from the brief first, show what you extracted, then ask only for the gaps.** A
JD usually carries the mission, scope, team and remote policy. It almost never carries the three
that matter most, so ask for exactly those: **the comp band if it is shareable, the hiring manager,
and who the mail is from and their relation to the role.** A recruiting email with no level, no
money and no named human is a form letter.

Each draft carries: why **this population** specifically, what the person will own, the concrete
facts (level, band, manager, team size, remote policy, traction), one low-friction ask, and the
sender's real name. **No invention** — a fact that was not supplied does not get a sentence. A
fabricated detail about a role surfaces in the first conversation.

### The one-click compose link

A link per candidate that opens a **pre-filled compose window in the recruiter's own mailbox**. Two
columns, because a plain `mailto:` routes to a desktop client and a browser Gmail user needs a web
compose URL:

```
mailto:<address>?subject=<url-encoded subject>&body=<url-encoded body>
https://mail.google.com/mail/?view=cm&fs=1&to=<address>&su=<url-encoded subject>&body=<url-encoded body>
```

**Cap the link body near 900 characters of raw text.** Encoded compose URLs stop working past
roughly 2,000 characters, and newlines cost three each as `%0A`. Measured 2026-08-28 on eight real
rows: **bodies of 652–733 raw characters encoded to `mailto:` URLs of 1,094–1,203 and Gmail URLs of
1,128–1,237** — an inflation of roughly 1.65×, not 3×, because prose is mostly unreserved
characters. So a 900-character body lands near 1,500 encoded and clears the ceiling comfortably.
The cap is therefore about **what a first recruiting email should be**, more than about the URL
limit. **Compute the encoded length and assert it rather than trusting the ratio**, and if a body
exceeds the cap, **keep the full copy in its own column and say the link version is trimmed** —
never ship a link that truncates mid-sentence.

Two ways to build the encoding, at two prices:

- **In the agent, free.** The delivery is a CSV handed over once: encode both fields in the agent
  (`encodeURIComponent`, or Python's `urllib.parse.quote`) and write finished URLs into the columns.
  Nothing bills.
- **As a play column, per row.** The play is the working surface, bodies are generated per row,
  and links must exist for rows arriving later. Use a `run_javascript` column — Deepline's
  deterministic transform step — with `encodeURIComponent` on the subject and the body. Confirm it
  with `deepline tools describe run_javascript --json`. Encode the subject first, then build the
  link from the scheme, the address and both encoded parts.

**Which address, and why the default is neither.** The search **does not return email
addresses** — only `contact.has_business_email` / `has_personal_email` booleans saying whether one
exists — so every compose link depends on a per-row lookup priced in Step 6. Ask which address,
and say this when you ask: **a recruiting email sent to a work address is delivered onto the
current employer's mail system**, where it may be scanned, archived, or read by someone other than
the candidate. Personal-address finders exist, cost per row, and hit less often.

1. **Profile link only — the default.** The profile URL comes back on the search row itself, so
   this costs nothing beyond the search; no address is found and no compose link is built. The
   recruiter opens the profile and messages there, which for passive senior candidates is often
   the better channel anyway.
2. **Work address** — `prebuilt/person-linkedin-to-email-batch` over the profile URLs. Say what it
   costs the candidate, as above, then build it if they still want it.
3. **Personal address** — `leadmagic_personal_email_finder`. Filter first to rows where the search
   reported `contact.has_personal_email: true`, and expect a lower hit rate.

Where no address is found the row keeps its profile URL and **no compose link** — never a `mailto:`
built on a guessed address.

**This skill sends nothing and enrols nobody.** There is no send step; copy lands as drafts. That is
a design choice, not a gap: candidate outreach pushed through a cold sales sequencer burns the
sender's domain reputation and reads, to the candidate, exactly like what it is. A link that
composes in the recruiter's own mailbox sends from a real human, returns replies to a real inbox,
and stops at a human's click.

## Step 10 — Deliver, with the shape of what is missing

Per population, in this order:

1. **The yield line** — total matched, rows returned, target, whether the population is exhausted.
   **Including the populations that returned nothing.**
2. **The bands** — strong, possible, weak, plus `unscoreable`, `suppressed` and `identity_conflict`
   as their own rows. These do not fold into weak.
3. **The candidates**, ranked within band: name, current title and employer, location, years of
   experience, profile URL, score, the evidence line, and the compose link or the reason there is
   none.
4. **The outreach draft** for that population.

Then once, across the run:

- **Every criterion and where it went** — query, scorecard, or not observable. The part a hiring
  manager should read first and will not think to ask for.
- **Every approximation applied**, named: an industry anchor or lookalike-employer list standing in
  for "companies like theirs", a tenure heuristic standing in for availability.
- **What was spent**, in Deepline credits, against what was approved — read from
  `deepline billing usage`, not estimated.
- **What was left behind** — any play run, with its id and the customer-DB table its dataset
  persisted to. Nothing else should appear on this line.
- **What this list is not**: people who match a shape, not people who want the job. Beyond the
  opt-in open-to-work flag, no availability, compensation or work-authorisation signal exists in
  this data.

## What this skill does not claim

- The logic came from an interview with its author, not from a workflow that has run end to end.
  No measured yield, cost, response rate or hire rate exists for any of it.
- What was verified live is narrow and worth separating from the rest. Against Clay's people search
  on 2026-08-27: that its advanced query mode carried years-of-experience, education and
  per-experience seniority fields, and that a `count from ...` mode was refused. Against Deepline
  on 2026-09-30, by `describe` only: that `crustdata_v3_person_search` carries `years_of_experience`,
  education and per-role seniority filters; the operator set; the five-item `in`/`not_in` limit;
  `total_count` and cursor pagination; and the per-result price. **No Deepline search in this file
  has been executed, and nothing about result quality was measured.**
- The claim that keyword-proxying a soft criterion loses most of the qualified population is
  reasoned from two behaviours — that a search has no field for judgment, and that text matching
  excludes on spelling. **The size of that loss has not been measured**, and it will differ by role
  and seniority.
- The author's framing of populations — that a merged query fails in both directions — is the
  author's reading, not the creator's claim. **The creator's instruction was that the definition
  should come out of a conversation with the hiring manager, from exemplar profiles or described
  experience, rather than from the skill decomposing a brief on a theory of its own.** The
  one-query-per-population mechanic is theirs; the strength of the merged-query failure is not
  established.
- The 70 and 40 band cut-offs are defaults chosen so the skill runs. No hire-outcome data validates
  them, and nothing here can say whether they match an installer's bar.
- The per-employer cap of 2 is a stated default with no measurement behind it.
- The tenure-based availability heuristic has never been checked against whether those people
  moved, and the open-to-work flag's coverage is unmeasured.
- Scoring reads a public profile, so it measures what someone wrote about their work, not the work.
  That bias runs against senior and less self-promotional candidates in a direction this skill can
  flag but cannot correct.
- **The wrong-ladder measurement is one role, in two cities, on Clay's search.** That 14 of 25
  rows from a growth-title query were sales people, and that a current-role description keyword took
  7 of 7 to the right ladder, was observed on one brief on 2026-08-28. **It is a real observation
  and not a general precision figure**, and it was not repeated on `crustdata_v3_person_search`,
  whose function and department fields may separate the ladders without a keyword at all.
- **The lookalike finding is one call, on one seed, on Clay's person-lookalike action.** Deepline
  has no person-lookalike tool; the company-lookalike route through `discolike_discover` has not
  been measured for this use at all.
- Whether `(.)` matches partial words (`engineer` against `engineering`) is not stated in the
  schema and has not been tested here.
- The recommendation to score and write copy in the agent rather than in a play is reasoned from
  architecture — relative ranking needs the whole set in one place, and copy is per population —
  **not from a measured comparison.**
- Prices quoted here are from `deepline tools describe` on 2026-09-30. Several tools price after
  execution, so this file cannot tell an installer in advance what a run will cost; the pilot can.
- The compliance warning in Step 4 names two common exposures in two jurisdictions. It is not legal
  advice, not a complete list, and does not survey the installer's jurisdiction.

## What good looks like

- **The definition came out of a conversation** — two or three exemplar profiles taken apart with
  the hiring manager saying which shared attributes were the point, or their own description of the
  experience followed back. Not a JD parsed on the skill's authority.
- **Every criterion appears in exactly one of three places, and the split is on screen before any
  query runs.** The not-observable ones are named in the final delivery, not quietly absent from it.
- Each population has its own query, yield, bands and copy — **including the one that returned
  zero**, reported as a finding rather than dropped from the summary.
- Every approximation is disclosed where it was applied, not just in a preamble: "companies like
  theirs" became named industries or a lookalike-employer list, and the output says so.
- Every scored candidate quotes the profile phrase behind the score, so a hiring manager can
  disagree with one score instead of distrusting all of them.
- Thin profiles sit in `unscoreable` as their own reviewable group. A bottom band full of senior
  people with empty About sections is a list that scored profile-writing.
- No employer is more than the cap of the list.
- Every compose link opens with real facts in it — a level, a named manager, a real sender — or the
  row carries a profile URL and no link.
- **The commonest failure: taking "strong quantitative background" out of the brief, adding a
  keyword condition on the about section for `SQL` and `analytics`, and shipping a valid query, a
  plausible list, and the silent removal of most of the qualified population.** Nothing in the
  output looks wrong.
- **The second: one merged query.** Two hundred rows, no way to tell which population they came
  from, and a hiring manager who cannot tell whether the market is thin or the query was.
- **The third: averaging the exemplars.** Three profiles share an MBA, a city and a Series B
  employer; all three go into the query; the list comes back small and nobody knows which filter
  did it.

## Rules

- MUST start from a conversation — exemplar profiles or described experience — and MUST write the
  definition back for correction before running anything. NEVER treat a JD as the definition.
- MUST treat a lookalike population as seeded, not queried: MUST label it, name its seed, say what
  the engine appears to have anchored on, and filter it against the brief afterwards; NEVER fold
  its rows into a queried population's yield line, and NEVER use it as a substitute for asking
  which attributes are the point.
- MUST ask which of the exemplars' shared attributes are the point; NEVER average exemplars into a
  single query, and never guess which attribute mattered.
- MUST confirm the years-of-experience, education and per-experience seniority fields exist in the
  schema pulled **this run**, and MUST take filter values from autocomplete; NEVER write a query
  from a remembered field list.
- MUST show the three-way split of every criterion before running anything, and MUST report the
  not-observable ones in the delivery; NEVER let a criterion disappear without being named.
- NEVER convert a scorecard criterion into a keyword filter. Where a soft criterion must shape the
  search it becomes a separate population, or it stays on the scorecard.
- MUST run one query per population and keep the label on every row; NEVER merge populations with
  `or`, and never `and` traits from different populations.
- MUST hold location, seniority and the experience floor constant across populations.
- MUST list title values explicitly and split any `in` or `not_in` list longer than five; MUST use
  the `current` family for current employers, `past` for former ones and the unqualified family for
  any tenure; MUST group same-role conditions under `all_of`; MUST omit seniority when no level was
  named; MUST keep every exclusion.
- MUST apply a per-employer cap; NEVER deliver a list where one company is most of it.
- MUST disclose every approximation where it was applied — an industry anchor or lookalike-employer
  list standing in for company similarity, tenure standing in for availability.
- MUST size each population and sample 25 rows before the full run; MUST report a zero yield as a
  finding; NEVER pad a thin population, and never loosen a query to avoid reporting one.
- MUST state the full cost — per-result search price and per-row enrichment, discovered live from
  `describe` and a pilot — and wait for an explicit yes before the first paid call beyond the
  sample; NEVER quote a credit price from memory or from this file.
- MUST name the tool or play, its inputs, what to verify in its response, and its per-row cost
  before any enrichment. "Enrich for emails" is an intention, not an instruction.
- MUST mark a profile with no readable text `unscoreable` and exclude it from the ranking; NEVER
  score it low, and never let it fall into the weak band.
- MUST quote the profile evidence behind every score.
- MUST warn once, name the specific exposure, and offer years-of-experience or seniority as the
  clean equivalent when asked to filter on a protected characteristic or a proxy — and MUST then
  build what was asked for. NEVER refuse, and never repeat the warning.
- MUST default the contact address to profile-link-only, and MUST say that a recruiting email to a
  work address is delivered onto the current employer's mail system before that option is chosen.
- MUST cap the compose-link body near 900 characters and keep the untruncated copy in its own
  column; NEVER ship a link that truncates mid-sentence, and never build one on an address the
  lookup did not return.
- MUST search the tool and play catalog with several synonyms before concluding anything is
  unavailable, and MUST confirm every tool ID with `deepline tools describe`; NEVER infer a
  platform limitation from one search.
- MUST check the Deepline balance before paging and MUST stop and say so when it cannot finish the
  run; NEVER report a partial list as a list.
- MUST verify the enriched record's current employer against the row that was sent before scoring
  it; profile data goes stale.
- MUST build nothing beyond the play runs the enrichment needs, and MUST report their ids in the
  delivery.
- MUST keep scoring and copy in the agent unless the installer wants a living surface a team works
  in, and MUST say which was chosen; NEVER generate copy per row when copy is per population.
- NEVER send anything, enrol anyone in a sequencer, or write to a CRM. Copy lands as drafts and a
  human clicks.
- NEVER state a pitch fact the installer did not supply.
- NEVER invent a criterion the conversation did not contain; anything proposed is labelled as
  proposed.

## Worked example

Asked: *"We're hiring a Head of Growth in London. Here are three people I'd hire."* Three profile
URLs, plus a JD. **The yields below are the shape of a run, not measurements — this skill has not
been run end to end, which is the first thing its does-not-claim section says. The query follows
the schema pulled on 2026-09-30 and has not been executed.**

**Decomposing the three exemplars** — one `crustdata_v3_person_enrich` call on the three URLs —
produced eleven shared attributes. Read back, the hiring manager kept four and killed the rest:

| Shared by all three | Their call |
|---|---|
| 8–12 years, Head or Director level | **keep** — the floor |
| currently at B2B SaaS, roughly 50–500 people | **keep**, as an industry and size anchor |
| owned paid acquisition *and* lifecycle | **keep** |
| in London | **keep** |
| MBA | *"coincidence — two of them, and it's not why I like them"* |
| all worked at a company I've heard of | *"that's me recognising logos, not a requirement"* |
| all posted on LinkedIn in the last month | not a criterion |
| two came through consulting | **not a shared attribute — a second population** |

That last row is the conversation earning its place. Averaging the three would have produced one
query with an MBA filter in it and no consultant population at all.

**The split, shown before anything ran.** Of twelve criteria from the JD and the conversation, five
were filterable, four went to the scorecard — *"owned a number, not a channel"* at weight 25,
*"strong quantitative background"* at 20, *"built a team rather than inherited one"* at 20, *scale
resembling ~$10M ARR* at 20, *scrappiness* at 15 — and three were named not-observable: **whether
they want to leave, their comp expectations, and their right to work in the UK.** Those three are
what a recruiter assumes was handled. (The opt-in open-to-work flag was offered as a second pass and
declined.)

**Two populations, two queries, same floor and location in each.** The first:

```json
{
  "filters": {"op": "and", "conditions": [
    {"field": "years_of_experience", "type": "=>", "value": 8},
    {"field": "basic_profile.location.city", "type": "in", "value": ["London"]},
    {"op": "all_of", "conditions": [{"op": "and", "conditions": [
      {"field": "experience.employment_details.current.seniority_level", "type": "in", "value": ["<Head and Director values from autocomplete>"]},
      {"field": "experience.employment_details.current.title", "type": "in", "value": ["Head of Growth", "VP Growth"]},
      {"field": "experience.employment_details.current.company_industries", "type": "in", "value": ["<Software Development value from autocomplete>"]},
      {"field": "experience.employment_details.current.company_headcount_range", "type": "in", "value": ["<51-200 and 201-500 values from autocomplete>"]}
    ]}]},
    {"field": "experience.employment_details.current.company_website_domain", "type": "not_in", "value": ["competitor.com"]}
  ]},
  "limit": 25
}
```

Disclosed with it: *"companies like the ones your three exemplars are at"* became a named industry
and a headcount band, because the search has no similar-company filter for people.

| Population | Total (`limit: 1`) | Sampled (25 max) | Read |
|---|---|---|---|
| In-house growth leaders at B2B SaaS | 140 | 25, more available | the population is here |
| Ex-consultants two to four years in-house | 61 | 25, more available | real, and a different pitch |

**Bands on the 140 — and note what had to happen first.** The search rows carry headlines and
per-role descriptions, but no about section, so the installer was asked whether to buy it. Here
they did: 140 rows through a one-column play wrapping `crustdata_v3_person_enrich` with
`fields: ["basic_profile"]`, priced on a three-row pilot first. 31 strong, 58 possible, 34 weak,
**14 `unscoreable`**, 3 `suppressed`. Had the installer declined the enrichment — a legitimate
choice — the scoring would have read the headlines and role descriptions alone and said so.

The fourteen `unscoreable` are not weak — they are profiles with no About section and one-line role
entries, several at companies the hiring manager had named unprompted. They went back as their own
group for a skim on title and employer.

**Contact channel:** the search returns the profile URL, so profile-link-only on the first pass
cost nothing beyond the search. After reading the strong band the installer asked for addresses on
those 31 rows only — priced on a pilot, approved explicitly, and the work-email play returned an
address for 22 of 31. Those 22 rows carry two compose links each. The other nine carry a profile URL
and no link.

**Copy:** two drafts — **two, not 140.** The in-house draft leads with budget and scope; the
consultant draft leads with owning the number instead of advising on it. Both under 900 characters
of raw body, both naming the hiring manager, the level and the band, both from the founder rather
than a careers alias. The per-candidate part is only the merge and the encoding, which is free.
Nothing was sent.

## Listing
- **one-liner:** Turn a hiring conversation into a scored candidate list, one query per population who could actually do the job.
- **problem:** The criteria separating a good candidate from a plausible one are the ones a people search cannot hold — and it never says when it drops them. A brief goes in, a valid query comes out, the list looks plausible, and the discriminating half has evaporated. The usual repair, turning "strong quantitative background" into a keyword, makes it worse: it selects for people who narrate their skills and excludes on spelling.
- **delivers:** A definition built in conversation — two or three profiles you'd hire, with you saying which shared attributes are the point — then every criterion split three ways: filterable, scorecard, or not observable. One query per population, so an empty one is reported rather than hidden. Scores that quote their evidence, thin profiles marked unscoreable instead of weak, and outreach drafts that compose in your own mailbox.
- **example prompt:** We're hiring a Head of Growth in London — here are three profiles of people I'd hire, find me more.
- **also asked as:** Source people for this job | Build me a candidate list from this brief | Who could fill this role, and is the market even there?
