# Draft skills (not Deepline CLI-managed)

> **Status: DRAFTS.** These skills, templates, and workflow sketches are experimental.
> They are **not** installed or overwritten by `deepline skills` / the Deepline CLI skill sync.
> Do not treat them as production playbooks until reviewed and promoted into `skills/` or `workflows/`.

## Why this folder exists

The Deepline CLI (`deepline skills`) reinstalls the **released** skill set under agent skill directories
and mirrors the published packs that live in this repo's `skills/` tree. Anything you put only in
`skills/` may be treated as part of that release surface.

This `drafts/` tree is intentionally separate so GTM operators can iterate on event, Luma, and HubSpot
patterns without colliding with CLI reinstalls.

## What's here

| Draft | Purpose |
| --- | --- |
| [`luma-event-campaign`](luma-event-campaign/) | End-to-end Luma campaign: guest list → enrich → invite/social → sequence staging |
| [`hubspot-follow-email`](hubspot-follow-email/) | HubSpot marketing / follow-up email drafting with brand + anti-slop rules |
| [`event-ops-score-and-door`](event-ops-score-and-door/) | Score RSVPs, approve against capacity, ship day-of door pack |
| [`event-host-prep-dossiers`](event-host-prep-dossiers/) | Rank hosts' must-meet guests → one-pager dossier pack |
| [`luma-inbound-webhook-enrich`](luma-inbound-webhook-enrich/) | Standing Luma registration webhook → enrich → CRM/customer DB |
| [`workflows/`](workflows/) | Placeholder apply-payload sketches (IDs/secrets as env placeholders only) |

## Anonymization

Drafts use fictional placeholders only:

- Event: `City GTM Meetup — Sample Night`
- Companies: `Acme Labs`, `Northwind Analytics`, `Contoso RevOps`
- People: role labels (`Founder, Acme Labs`) — never real customer rows
- No live org IDs, API keys, credit balances, campaign IDs, or private CRM fields

## How to try a draft

1. Copy one draft folder into your local agent skills dir **manually** (do not run `deepline skills` expecting these to appear).
2. Or open the `SKILL.md` and follow it as a checklist with your own tools/CLI.
3. Before any paid enrich or send: pilot ≤10 rows; keep campaigns **paused** until a human approves.

## Promotion path

When a draft is stable:

1. Strip remaining TODOs
2. Add evals / sample CSVs under `examples/` if useful
3. Open a PR that moves it into `skills/` or `workflows/` and updates the root README table
4. Only then consider it part of the CLI-managed surface
