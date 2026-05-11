# We built a warm intro scorer on 6,484 LinkedIn connections. Here's what actually worked.

A warm intro converts at 40-60%. Cold email converts at 2-4%. So finding the right person to make an introduction is worth real effort.

The problem is that "finding the right person" usually means: open LinkedIn, stare at a contact's profile, try to remember how you know them, decide it's too awkward to ask, close LinkedIn.

We built something more systematic.

---

## The setup

Starting point: Jai's LinkedIn export. 6,484 connections, mostly from the last 5 years of B2B GTM work.

Three targets:

- **Target A** — VP of Sales at Modal (GPU compute infra)
- **Target B** — Head of Engineering, Identity Product at Stripe
- **Target C** — Senior Director of Engineering at Stripe (Manpreet's manager, 17 direct reports)

The goal wasn't just to find someone at the same company. It was to find the person most likely to make a warm, well-placed introduction — and score them on how good that path actually is.

---

## The scoring model

Four signals. Each one is justified, not just arbitrary.

```
Total score = company match + seniority + connection recency + role overlap
```

**Company match (50 pts)** is the biggest weight because shared employers are the strongest proxy for actual relationship. If you both worked at [Company E], there's a reasonable chance you know each other or at least have a natural conversation opener. The scorer normalizes company names so "Stripe, Inc." and "Stripe" don't count differently. It also gives double credit for multiple overlaps in the history — someone who shows up at Stripe twice (once as an employee, once via acquisition) has a deeper relationship with the company than someone who spent six months there.

**Seniority (5-20 pts)** matters because a VP or founder asking for an intro has more social capital than an IC asking the same favor. Not a moral judgment — just how it works. VP/founder gets 20, Director/Head of gets 17, Manager/Lead gets 12, Senior/Principal gets 9, IC gets 5.

**Connection recency (7-30 pts)** is the most underrated signal. A connection from last month is completely different from one from 2019. You're more likely to get a response, and the introduction comes with more credibility when the relationship is fresh. Connected in the last 90 days: 30 points. 90 days to a year: 22. One to two years: 14. Two-plus years: 7.

**Role overlap (0-15 pts)** catches natural fit — a GTM connector asking a GTM intro is a more comfortable ask than a cross-functional one. It's keyword matching on job titles, not semantic similarity, so it's rough. But it adds signal at the margin.

---

## What the data looked like before enrichment

We ingested all 6,484 connections from the LinkedIn export CSV — just names, current companies, and connection dates. No job history yet.

Running the scorer gave us current-company signals only. Results for Target A:

| Connector | Score | Via |
|---|---|---|
| Connector 1 | 91 | [Company E] (current) |
| Connector 3 Vieth | 81 | [Company E] (current) |
| Mikiko Bazeley | 72 | [Company E] (current) |

Both Connector 1 and Connector 3 were flagged as "currently at [Company E]." Neither was. Connector 1 left for [Company D] in January 2025. Connector 3 left for [Company C] in 2024. LinkedIn's exported data is a snapshot, and the snapshot was already wrong.

Current-company data alone is unreliable for anything you actually plan to act on.

---

## Enriching with Edges

We used Edges' `linkedin-extract-people-experiences` action to pull full job histories for the 94 connections at target companies. Edges runs on managed LinkedIn identities — no cookies, no account risk, fresh session per call.

Cost: 0.6 credits per profile. 94 profiles. ~56 credits total. About $1.09.

Rate limit on the Silver plan is 600 requests per minute. 94 profiles at one every 120ms took under 2 minutes.

The enrichment wrote 780 experience records across 473 unique companies. Each record has company name, title, start date, end date, and whether it's current.

Re-running the scorer with full history changed several results. The biggest change was for Target C at Stripe:

| Connector | Score (before enrichment) | Score (after) | Why it changed |
|---|---|---|---|
| George Xing | 83 | 122 | Double Stripe hit — current employee + Supaglue acquisition history |
| Connector 2 | — | 135 | Not in Stripe results before; enrichment revealed double Google history, Ron worked at Google pre-Stripe |
| Spencer Aller | — | 134 | Also surfaced via Google history |

Connector 2 went from invisible to the highest-scoring connector for Target C That wouldn't have happened without job history.

---

## Final scores

```
Target: Target A (VP Sales, Modal)
  #1 Connector 1 — 90  [warm, connected Jan 2025]
       Now at [Company D]. Worked at [Company E] when Target A was there.
       Seniority: Sr Director = 20 pts. Still has the [Company E] network.
  #2 Connector 3 Vieth — 81  [warm, connected Aug 2025]
       Now at [Company C]. Left [Company E] 2024.
       Freshest connection but cross-functional (Eng → Sales).
  #3 Mikiko Bazeley — 72  [cold, connected May 2024]
       Still at [Company E]. Staff Dev Advocate.

Note: Target A is already a direct connection (Dec 2023, 869 days ago).
Cold but reachable directly — no intro needed.
```

```
Target: Target B (Head of Eng, Identity Product, Stripe)
  #1 George Xing — 125  [cold, connected Sep 2022]
       Currently at Stripe. Founded Supaglue, which Stripe acquired.
       Double company match = 106 pts on company alone.
       Cold connection but has deep internal Stripe credibility.
  #2 Carla Colindres — 77  [warm, connected Dec 2024]
       Currently at Stripe, Product role.
       Lower score than George but a much fresher relationship.

Target: Target C (Sr Director of Engineering, Stripe)
  #1 Connector 2 — 135  [warm, connected Dec 2024]
       Head of Operations, Health AI Research at Google.
       Double Google hit in her history. Ron was at Google before Stripe.
  #2 Spencer Aller — 134  [cold, connected 2015]
       Strategic Client Director at Google. Triple hit (Wildfire/Google history).
       High score, but a 10-year-old connection.
  #3 George Xing — 122  [cold]
       Double Stripe hit. Same connector as Manpreet — one ask, two intros.
```

George Xing is the most efficient path. One ask to one person covers both Stripe targets.

---

## What the data got wrong (and what we adjusted)

**Name validation is fuzzy.** The `linkedin-find-profile-url` call takes a full name and company, does some matching, and returns a LinkedIn URL. It returned the wrong person 20% of the time in our run. We validated every URL against the actual profile via Apify's LinkedIn scraper — first name match only, not current company, because the profile might show a previous role.

Validating on current company would have rejected correct profiles where the person had since changed jobs. That's a real edge case, not a hypothetical one.

**Recency score is a rough proxy for relationship strength.** Two people who met at a conference, traded cards, and connected on LinkedIn are not the same as two people who worked together for three years. The scorer doesn't know the difference. It just knows when the connection was made. You still have to look at the actual person and decide whether the relationship supports an intro ask.

**Current-company data goes stale fast.** LinkedIn exports a snapshot. The snapshot is wrong by the time you run it. Enrichment with live job history is necessary to avoid confidently recommending someone who left the company six months ago.

---

## The actual workflow

```
1. Export LinkedIn connections CSV
2. Ingest into SQLite via warm_intro ingest script (6,484 contacts, ~2 min)
3. Filter to connections at target companies (94 contacts)
4. Enrich job histories via Edges (94 × 0.6 credits = $1.09, ~2 min)
5. Run scorer against each target (instant, in-memory)
6. Review top results, pick connectors, draft the ask
```

Total time from export to ranked results: under 30 minutes. Most of that is waiting for Edges to return profiles.

Total cost: $1.09 for enrichment. The rest is free.

---

## What the scorer doesn't know

It tells you who has the most factual overlap. It doesn't tell you whether to ask them.

Connector 1 scoring 90 for a Target A intro means he ran partner sales at [Company E] when Target A was an AE there — real overlap on paper. Whether they actually knew each other, whether Connector 1 would pick up the phone, whether he knows Target A personally or just by reputation: none of that shows up in the data.

A score of 90 is a strong reason to look at the person. It's not a strong reason to send the ask. That decision still requires a human who knows the relationship.

---

## What this cost to build and run

The scoring model is in `scripts/warm_intro/scorer.py`. About 380 lines of Python with no external dependencies beyond SQLite. The enrichment script is another 150 lines wrapping Edges API calls.

Total compute cost for this specific run:
- Edges enrichment (94 profiles): ~$1.09
- Nothing else

The model itself took a few hours to design and test. The tests in `tests/warm_intro/` validate against 16 real historical warm intro successes from 2024 — people who actually connected via shared companies and made introductions that led somewhere.

---

## What's missing

**Interaction history.** The scorer knows when you connected. It doesn't know if you've spoken since. Someone you connected with six months ago and have emailed twice is not the same as someone you connected with six months ago and have never spoken to. Recency is a rough proxy. Actual interaction history would be much better — but that data isn't in the LinkedIn export.

**Multi-hop paths.** The scorer only looks at direct connections. The best intro path is sometimes two hops: you know someone who knows the target well. Building that requires a graph, not a list. Not there yet.

**Appearance matching.** The model has `WEIGHT_SHARED_APPEARANCE = 40` — if someone in your network co-presented with your target at a conference or was on the same podcast, that's a stronger signal than almost any company overlap. We don't have that data for most people, so it rarely fires. But if you had it, it would change a lot of rankings.

---

What would you use this for? Trying to understand whether people are running warm intro workflows systematically or mostly by memory.

---

---

*All code and artifacts in this example:*

| File | What it is |
|---|---|
| [`scorer.py`](scorer.py) | Scoring engine — takes Contact + Experience objects, returns ranked WarmIntroMatch list |
| [`enrich.py`](enrich.py) | Edges API enrichment — pulls full job histories for a list of LinkedIn URLs |
| [`ingest.py`](ingest.py) | Ingests LinkedIn Connections.csv into SQLite |
| [`models.py`](models.py) | Dataclasses: Contact, Experience, Education, WarmIntroMatch |
| [`db.py`](db.py) | SQLite wrapper with insert/query helpers |
| [`lookup.py`](lookup.py) | CLI: `python -m lookup --company Stripe` |
| [`slide.html`](slide.html) | Visual summary of the scoring results |
