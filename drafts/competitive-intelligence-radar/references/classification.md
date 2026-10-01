# Classification — event taxonomy, implication mapping, FACT/READ discipline

## The two registers

Every digest item carries both, visually separated, in this order:

- **FACT** — what happened: event class, dated (with derivation basis: in-text /
  URL-path / dateline / corroborated), source URL, a ≤140-char quote from the
  source. No adjectives, no speculation, nothing the link can't back.
- **READ** — what it opens for YOU, prefixed `READ:`. Reads may be wrong; that's
  allowed. A read presented as a fact is not allowed. A read never cites another
  read as evidence.

An item with a FACT and no confident READ ships anyway (logged tier). An item with
a READ and no FACT does not exist.

## Event taxonomy → implication mapping

| Class | Detection cues | Default READ (adapt to the user's motion) | Audience |
|---|---|---|---|
| **Launch** | product/feature announcement, GA/beta vocabulary | Positioning counter: update battlecard; expect it in deals within a quarter | sellers, marketing |
| **Pricing / packaging** | pricing page change, tier vocabulary, "now free/included" | Displacement window at THEIR renewal cohort; switching-cost math is the lead | sellers |
| **Positioning shift** | new category language, homepage/tagline change (page-diff arm) | Their ICP is moving — check overlap with yours before reacting | marketing, founders |
| **Exec change** | C-level/VP arrival or departure vocabulary | Arrival = roadmap tell (function signals direction, 2–3 quarters out); departure = instability read, short shelf life | founders, sellers |
| **Funding / M&A** | round/acquisition vocabulary | Raise = sales-pressure forecast (quota expansion follows); acquired = integration distraction window | founders, sellers |
| **Customer win / loss** | case study, logo announcement, churn coverage | Win in your segment = head-to-head prep; visible loss = reference-call opening | sellers |
| **Hiring pattern** | aggregate posting/arrival concentration (hiring arm) | Function concentration = investment tell; goes in READ only with the aggregate numbers as FACT | founders |
| **other** | anything real but unmapped | none — digest tail, never promoted, never padded with a manufactured read | — |

Rules of the mapping:
- One event, one class — the DOMINANT one (an acquisition that changes pricing is
  funding-M&A with the pricing note inside the READ).
- The default READs are conventions — restate them in the user's terms during
  Step 1, and drop classes the user declared out of scope from act-on-now (they
  still log).
- **Shelf life**: exec-change and win/loss reads decay in weeks — stamp reads
  with the sweep date; re-verify before anyone uses a read older than a month.

## Routing tiers

- **act-on-now** — in-scope class + strong implication + fresh: FACT + READ at the
  top of the competitor's section.
- **logged** — real event, weak or out-of-scope implication: FACT line only.
- **quiet** — no in-window events for that competitor: one line, window shown.
  Quiet is a result; padding a quiet competitor with archive material is the
  cardinal sin.
- **dropped-with-note** — out-of-window by content date, wrong entity
  (name-boundary), or single-source-unverifiable in degraded mode when the user
  requires corroboration. The note names the rule that fired.

## Digest skeleton

```
## <Competitor> — <domain> · sweep <date> · window <from → to>
ACT ON NOW
- FACT [launch, 2026-08-05, in-text date] "<quote>" (source)
  READ: <implication in the user's terms>
LOGGED
- FACT [...]
(or) QUIET — no in-window events (window shown)
```

Set-level footer: sweeps run · events by class · dropped-with-note count ·
credits spent (measured where the surface reports it) · next window start.
