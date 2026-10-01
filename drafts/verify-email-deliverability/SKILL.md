---
name: verify-email-deliverability
description: |
  Check whether an email address actually accepts mail before you send to it, using a free
  MX pre-check plus a real mailbox-level validator through Deepline. Use whenever someone asks:
  verify this email, is this address deliverable, will this bounce, check if these emails
  are valid, or validate a handful of addresses before a send. It returns a verdict tier —
  valid, catch-all (risky, escalatable), do-not-mail (role/disposable/suppressed), invalid,
  unknown — never a bare yes/no, and it tells you which tiers are safe at volume. Do NOT
  use it to find someone's email in the first place (find-work-email), to bulk-clean and
  refresh a whole list or CRM (clean-email-list), or to identify who owns an address
  (reverse enrichment). It never pattern-guesses addresses and states cost before spending
  any credits.
category: verify-and-clean
personas: [revops, marketing]
mechanism: functions
touches: read-only
keywords: [catch-all-domains]
ported_from: clay-run/clay-skill-creator/skills/clay/verify-email-deliverability
---

# Verify email deliverability

The insight: **"deliverable" is a tier, not a boolean — and every validator hides the
riskiest tier behind its safest-looking field, in opposite directions.** Per the Deepline
tool schemas: BounceBan grades catch-all as `result: risky` with the signal in
`is_accept_all`; IPQS returns a boolean `valid` that can be true on a catch-all host, with
the signal in a separate `catch_all` flag; LeadMagic can return `invalid` on a catch-all or
gateway-protected domain where the mailbox is merely unprovable (signal in
`is_domain_catch_all` / `mx_security_gateway`). Reading one top field either blesses
bounces or discards live mailboxes — the verdict is always the field pair. The reverse trap: a live,
monitored `support@` comes back `do_not_mail` — validators grade for cold-list hygiene,
not readership.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The addresses** | exact strings, one per row | no default, and **never construct or repair an address** — a corrected address is a different address |
| **What they are for** | a one-off reply, or a volume send | ask. It changes which confidence tiers are usable at all, not just the reporting |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the addresses you supply, and the verification providers it runs them through.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or sends to an address to test it.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json` (health, auth, and balance in one call). If `deepline` is
missing, run `npm install -g deepline && deepline auth register --wait auto`, then re-run
preflight. Tell the user which org you're in (`auth.org_name`) and the balance.

## Step 1 — Collect the inputs

1. **The address(es) to verify** — exact strings; never construct or "fix" an address.
2. **What they're for**: one-off reply vs volume send changes which tiers are usable.

## Step 2 — Free MX pre-check (zero credits)

Before paying, resolve MX for each distinct domain (any DNS tool). Three shapes:
**NXDOMAIN / no MX** → guaranteed bounce — report invalid free, skip the paid check.
**Null MX** (single record `0 .`) → the domain *declares* it takes no mail — invalid, even
though a record "exists". **Real MX** → proceed.

## Step 3 — Pick a validator (tier AND vocabulary)

Validators are individual tools. Discover with `deepline tools search "email verify"
--json`; fetch the schema and price with `deepline tools describe <id> --json` — never
guess field names. Vocabulary matters as much as price: you need a validator that separates
catch-all from valid — a binary provider can't produce the tiers. Verified options:

| Tool | Credits/check | Verdict field | Catch-all signal |
|---|---|---|---|
| `zerobounce_validate` | 0.28 | `status` (valid / invalid / catch-all / unknown / spamtrap / abuse / do_not_mail) + `sub_status` | `status: catch-all` |
| `leadmagic_email_validation` | 0.09 | `email_status` (valid / valid_catch_all / catch_all / invalid / unknown) | `is_domain_catch_all` |
| `bounceban_verify_single` | 0.06 | `result` (deliverable / risky / undeliverable / unknown) | `is_accept_all`; also `is_role`, `is_disposable` |
| `ipqs_email_verify` | 0.07 | `valid` (boolean only) | `catch_all`; plus `disposable`, `honeypot` — a trap screen, not a tier source |

Every tool also emits Deepline's normalized `email_status` extraction, but report the raw
provider pair. State per-check cost before running; report the actual charge from the
run's billing (`deepline billing` before/after, or `deepline runs get <id> --full --json`
inside a play).

## Step 4 — Run it

For 1–20 addresses, run the tool directly:
`deepline tools execute zerobounce_validate --input '{"email":"..."}' --json`. Leave
catch-all-collapsing options OFF (e.g. BounceBan `disable_catchall_verify`) — they
collapse the tiers you're here to report. Checks return in seconds, every verdict
(BounceBan may return `status: verifying`; poll `bounceban_get_single_status` with the
id, don't resubmit). For hundreds, recurring
cleans, or addresses you're *finding* rather than checking, hand off to
`clean-email-list` or `find-work-email` and say so.

## Step 5 — Catch-all escalation (optional, 0.06–0.12 credits)

Catch-all isn't a dead end. If the send matters, run a catch-all-aware check on the same
address: `leadmagic_email_validation` → `email_status: valid_catch_all` means engagement
data confirms the mailbox (treat as valid, verified live); plain `catch_all` stays
unconfirmable. `allegrow_validate` (0.12) is the B2B catch-all specialist: `safe` → valid,
`dead_email` → won't bounce but nobody reads it, `some_risk` → hold. Production builds
send to the confirmed case, throttle or skip the rest.

## What good looks like

Map the observed fields to the verdict:

- ZeroBounce `status: valid`, LeadMagic `valid` / `valid_catch_all`, BounceBan
  `deliverable` with `is_accept_all: false`, or Allegrow `safe` → **valid**.
- ZeroBounce `status: catch-all`, LeadMagic `catch_all`, BounceBan `risky` with
  `is_accept_all: true` → **catch-all (risky)** — never report as plain valid; offer
  Step 5.
- ZeroBounce `do_not_mail` (+ `sub_status` such as `role_based`, `disposable`,
  `global_suppression`), `spamtrap`, `abuse`; BounceBan `is_role` / `is_disposable`; IPQS
  `honeypot` / `disposable` → **flagged** — may be genuinely read (support@!) but poison
  for volume; report the sub-reason, the user decides per use.
- ZeroBounce `invalid` (+ `mailbox_not_found`, `does_not_accept_mail`), BounceBan
  `undeliverable` → **invalid**. LeadMagic `invalid` with a populated `mx_record` on a
  gateway-protected domain is "not provable", so confirm with a second provider before
  calling it invalid.
- `unknown`, timeouts, empty payloads → **could not verify** — never round either way,
  and never gate on the tool call succeeding: it succeeds for every verdict; only payload
  fields are data.
- The common mistake: treating the validator as a spam-safety oracle. It answers the
  recipient half only — the top spam causes are sender-side (DNS auth, warming,
  reputation); never promise inbox placement.

## Rules

- MUST run the free MX pre-check before any paid check.
- MUST state per-check and total cost, and get approval before multi-address runs.
- MUST report the raw provider fields alongside the verdict tier.
- NEVER "correct" a typo'd address and verify the corrected version silently.
- NEVER report catch-all, role, or disposable results as plain valid.

## Output

Per address: `email · verdict (valid / catch-all risky / catch-all validated / flagged:
reason / invalid / could not verify) · raw fields · provider`. Multi-address runs add %
per tier plus a one-line recommendation for the stated use.

## Worked example

Ask: "Can I send to jordan.lee@northfield.example and hello@initech-consulting.example?"
MX pre-check: both domains have real MX — proceed. `leadmagic_email_validation` (0.09
credits each, approved): first returns `email_status: valid`, `is_domain_catch_all: false`
→ **valid**. Second returns `catch_all`; the send matters, so `allegrow_validate` on the
same address returns `safe` → **valid (probe-confirmed)**. Summary: 2 sendable, ~0.3
credits.
