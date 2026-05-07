# Warm intro scoring

Office-hours example from May 7, 2026.

Score your LinkedIn connections as intro paths to a target person. Uses job history (not just current company) to surface connectors who overlapped with the target at a past employer — catching the people that current-company-only lookups miss.

**What we built this for:** finding the best intro paths from Jai Toor's 6,484 LinkedIn connections to three targets at Stripe and Modal. Full write-up in `warm_intro_blog_post.md`.

## How it works

1. Export LinkedIn connections CSV (Settings → Data privacy → Get a copy of your data → Connections).
2. Ingest into a local SQLite DB via `ingest.py` — gets you name, current company, connection date for all contacts.
3. Enrich job histories for connections at target companies via Edges `linkedin-extract-people-experiences`. 0.6 credits per profile (~$0.01). Takes ~2 min for 100 profiles.
4. Run `scorer.py` against each target — scores company match (50 pts), seniority (5–20), connection recency (7–30), and role overlap (0–15).
5. Review top results. Pick connectors. Draft the ask.

## Scoring model

| Signal | Points | Why |
|---|---|---|
| Company match (current or past) | 50 | Shared employer = most likely real relationship |
| Seniority | 5–20 | VP/founder = more social capital for the ask |
| Connection recency | 7–30 | Connected 90 days ago vs 3 years ago = very different |
| Role overlap | 0–15 | GTM connector → GTM intro is more natural |

Company names are normalized — "Stripe, Inc." and "Stripe" score identically. Double credit if a connector appears at the target company twice in their history (e.g. via acquisition).

Validation on first name only, not current company. The lookup sometimes returns a correct profile where the current company differs because the person has since moved. Rejecting on company mismatch would drop valid results.

## What job history enrichment changes

Running on current-company data only, the top result for a MongoDB target was Sathishkumar Gopalaswamy — scored 91. After enrichment: he left MongoDB for Harness in January 2025. The DB said MongoDB. The real answer was Harness.

Current-company data from a LinkedIn export is a snapshot. The snapshot is already wrong. Enrichment with live job history is necessary before acting on results.

## Files

- `scorer.py` — scoring engine. Takes Contact + Experience objects, returns WarmIntroMatch with score and reasons.
- `enrich.py` — Edges API enrichment. Pulls job histories for a list of LinkedIn URLs, writes experience records to SQLite.
- `ingest.py` — ingests LinkedIn Connections.csv into SQLite.
- `models.py` — dataclasses: Contact, Experience, Education, PublicAppearance, WarmIntroMatch.
- `db.py` — SQLite wrapper with insert/query helpers.
- `lookup.py` — CLI interface: `python -m scripts.warm_intro.lookup --company Stripe --limit 10`.

## Usage

```bash
# 1. Ingest your LinkedIn connections
python -m scripts.warm_intro.ingest ~/Downloads/Connections.csv

# 2. Enrich job histories for connections at target companies
export EDGES_API_KEY=your_key
python -m scripts.warm_intro.enrich_targeted --companies Stripe,MongoDB,Google --limit 100

# 3. Find intro paths
python -m scripts.warm_intro.lookup --company Stripe
python -m scripts.warm_intro.lookup --company Stripe --role "Senior Director Engineering"
```

## Cost

- Enrichment: 0.6 Edges credits per profile (~$0.01 at Silver plan pricing)
- 100 profiles: ~60 credits (~$1.16)
- 6,484 profiles (full network): ~3,890 credits (~$75)

## What the scorer doesn't know

It surfaces factual overlap. It doesn't know if two people actually talked. A score of 90 is a reason to look at the person — not a reason to send the ask without thinking about the relationship.

Multi-hop paths (A → B → target) and shared public appearances (same podcast, conference panel) are not implemented yet. Both would improve ranking quality meaningfully.
