# A warm-intro score should tell you what to verify

Finding an introduction path is usually treated as a memory exercise: search a
network, recognize a few names, and guess which relationship is strongest. We
wanted a review process that exposed the evidence behind the guess.

The result is a small warm-intro scorer. It does not predict whether a person will
reply. It ranks factual reasons to inspect a connector and makes weak evidence look
weak.

All people, companies, source records, counts, and output excerpts in this article
are fictionalized. They illustrate the method, not a measured conversion claim.

## The setup

The input was a LinkedIn connection export containing several thousand contacts.
The public example reduces that workflow to three fictional accounts:

- Northstar AI, where Nora Imani leads GTM engineering;
- Relay Cloud, where Mina Sol leads revenue systems;
- Harbor Systems, where Tariq Fen leads business operations.

The first pass knew each connector's name, profile URL, current company, title,
and connection date. A bounded enrichment pass added employment histories for a
reviewed subset. The target-person path scorer then combined that history with
explicit owner-relationship and source evidence.

The goal was not “find someone at the target company.” It was “show the strongest
cited path to this person, explain why it ranks there, and make the remaining
uncertainty impossible to miss.”

## Discovery and verification are different jobs

The first useful distinction was between company discovery and dated work overlap.

A connection export can say that a connector currently works at Atlas Works. An
enriched profile can say that the connector previously worked there. Either fact
is useful for discovery. Neither tells us whether the connector and target worked
there at the same time.

The scorer therefore has two interfaces:

1. Criteria discovery compares a connector with a company, school, role, or public
   appearance. A company-name match is labeled `company_proximity` because target
   dates were not compared.
2. Target-person scoring compares both employment histories. It awards work points
   only when normalized employer identity matches and the date intervals intersect.

Suppose Casey Morgan worked at Atlas Works from January 2020 through June 2023,
while Mina Sol worked there from March 2021 through January 2024. Their cited
overlap is March 2021 through June 2023. That supports a work-overlap reason.

Now suppose Riley Chen left Nimbus Data in 2018 and Tariq Fen joined in 2019. The
company is the same, but the intervals do not overlap. That result remains useful
for review, but it earns zero work-overlap points. The campaign audit artifact
records the explicit reason
`company_proximity:Nimbus Data:non_overlapping_dates`.

Missing dates get the same cautious treatment. “Both worked there” is not silently
promoted to “worked together.”

## The evidence hierarchy

The target-person score is additive and visible:

```text
total = direct introduction
      + dated work overlap
      + owner-to-connector relationship
      + school/city/community/appearance
      + role/industry
      + investor context
```

The implementation uses a superincreasing factual hierarchy: a higher factual tier
must remain above every lower tier combined, even after accounting for the maximum
relationship-confidence difference. Repeating evidence in a tier adds citations,
not points. Investor context is capped at three.

That constraint matters. Without it, five weak facts can accidentally outrank one
confirmed introduction. A total score may look precise while representing the
wrong ordering of evidence.

Relationship confidence is separate from the connector-to-target fact. A strong
owner relationship tells us the ask may be comfortable. It does not tell us that
the connector knows the target. Conversely, a dated target overlap does not tell us
that the campaign owner has enough relationship capital to ask.

The strongest segment therefore requires both sides:

- a scored owner-to-connector relationship; and
- confirmed-introduction evidence or dated connector-to-target work overlap.

Community, role, and company proximity route to review. Investor-only context does
not become a warm path.

## What enrichment changed

Current-company data was useful for narrowing the search, but it was not reliable
enough for final wording. The example enricher does not replace
`Contact.current_company`; it updates headline, location, and `enriched_at`, then
replaces stored experience and education rows. Legacy discovery can therefore
continue to read the original snapshot company after enrichment.

The added experience evidence may show a later or current role, multiple roles
under legal-name variants, or a shared employer years apart. Before acting, review
the most recent dated/current experience and reconcile it with the snapshot. Do not
describe the enriched experience as a corrected current-company field.

Employment histories changed the workflow in three ways:

- stale current-company snapshots could be challenged by dated experience evidence,
  but still required manual reconciliation;
- people who had relevant prior experience became discoverable; and
- same-company proximity split into dated overlap, missing dates, and explicitly
  non-overlapping dates.

The important gain was not a larger score. It was a better review state. Reviewers
could see which claim was supported, which source IDs contributed, and which
sentence would overstate the evidence.

## Stable output matters downstream

The CLI exports deterministic CSV rows with campaign, owner, connector, and target
IDs; a shared versioned path ID; target title; the six explicit score components;
segment; evidence IDs; and an evidence-safe `shared_signal`/`shared_detail` pair.

That file is the direct input to the ask-drafting example. The drafter prefers
confirmed introduction over dated work overlap, then weaker contextual tiers. It
also tells the model that proximity does not prove familiarity. Each draft starts
unapproved.

Activation uses a separate identity:

```text
SHA256(JSON(["warm-activation-v1", campaign_id, owner_id,
             path_id, channel, message_version]))
```

The durable local outbox prevents a successful or ambiguous message version from
being sent automatically again. The provider does not expose an atomic
idempotency token, so uncertain post-dispatch outcomes require reconciliation. A
material edit requires a new version and another approval. The scorer is
deliberately unable to cross that boundary on its own.

## What the model still cannot know

The data can show that Casey and Mina had overlapping employment dates. It cannot
show whether they worked on the same team, trust one another, or would welcome an
introduction request.

A connection date is also an imperfect relationship proxy. Two people may have
connected after years of collaboration, or after one short event conversation.
Public appearances and community membership have similar ambiguity.

The review therefore asks questions the score cannot answer:

- Is this the correct connector identity?
- Is the target's role current?
- Does the source actually support the reason text?
- Does the connector know the target well enough to make the requested
  introduction?
- Is the owner's relationship with the connector current and appropriate for the
  ask?
- Is outreach permitted by consent, suppression, privacy, and channel policy?

If those questions are unanswered, the right output is review—not a more
aggressive message.

## A reproducible workflow

The method can be summarized without private data or performance promises:

1. Ingest a connection export into a local store.
2. Resolve identities before combining sources.
3. Narrow enrichment to a reviewed, budgeted subset.
4. Preserve dated employment records and immutable evidence IDs.
5. Use criteria scoring for discovery and target-person scoring for evidence.
6. Export component scores, target title, segment, reasons, and citations.
7. Review the relationship and factual claim before drafting.
8. Generate unapproved drafts from the scorer CSV.
9. Approve selected copy explicitly, dry-run it, and activate with a durable
   idempotency log and channel limits.

The useful artifact is not a leaderboard of people. It is an audit trail from a
candidate account to a target, from a target to a connector, and from a connector
to the exact fact a reviewer must verify.

## Code and examples

| Path | Purpose |
|---|---|
| [`scorer.py`](scorer.py) | Criteria discovery and evidence-backed target-person scoring. |
| [`lookup.py`](lookup.py) | Human-readable results and deterministic `--csv` export. |
| [`models.py`](models.py) | Contact, experience, evidence-adjacent, and score records. |
| [`ingest.py`](ingest.py) | Connection-export ingestion. |
| [`enrich.py`](enrich.py) | Bounded live profile enrichment; review provider policy before use. |
| [`../target-account-warm-intro-campaign/`](../target-account-warm-intro-campaign/) | End-to-end fictional campaign orchestration and audit contracts. |
| [`../warm-intro-ask-threads/`](../warm-intro-ask-threads/) | Drafting, approval, rate policy, and idempotent activation. |
