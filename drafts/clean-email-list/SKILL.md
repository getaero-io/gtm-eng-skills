---
name: clean-email-list
description: |
  Clean a CSV or table of email addresses into keep / risky / remove segments with
  per-row evidence — free deterministic passes first (dedupe, syntax, role and
  disposable screens, domain MX check), then a paid Deepline mailbox validator only on rows
  that survive. Use whenever someone says: clean this email list, scrub my list
  before a send, remove invalid or duplicate emails from this CSV, how many of
  these addresses are still good, or prep this list for cold outreach. Every
  removed row ships with its reason — nothing is silently deleted, and rows that
  can't be verified are flagged, never guessed. Do NOT use it to check one or two
  addresses (verify-email-deliverability), to find or replace missing emails
  (find-work-email), or to merge duplicate CRM contact *records* (dedupe-contacts).
  It states total cost before spending any credits.
category: verify-and-clean
personas: [revops, marketing]
mechanism: functions
touches: read-only
keywords: [catch-all-domains]
ported_from: clay-run/clay-skill-creator/skills/clay/clean-email-list
---

# Clean an email list

The insight: **a list's value is set by its worst segment.** Bounce rate is measured
over the whole send — a few percent of dead rows can gate the other 95% out of inboxes.
So cleaning is triage, not filtering: every input row lands in exactly one of
keep / risky / remove / could-not-verify, with quoted evidence, and rows are never
silently deleted — a row you can't account for is a row you can't defend. The other
half is ordering: every free deterministic pass runs before the first paid call, so the
validator only ever sees rows that could still be sendable.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The list** | a CSV or table, and which column holds the email | no default, and no other column is ever edited |
| **The purpose** | cold volume send, CRM refresh, or re-engagement | ask — it decides the policy: for cold sends role mailboxes are removed and freemail is risky; for the others both are only risky |
| **Budget** | credits for paid validation after the free passes | free passes run regardless; state the cost of what survives them before spending |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the address list you supply, and the validators it runs against it.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, sends to any address, or deletes a row from your list.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json` (health, auth, and balance in one call). If `deepline` is
missing, run `npm install -g deepline && deepline auth register --wait auto`, then re-run
preflight. Tell the user which org you're in (`auth.org_name`) and the balance. Inspect
the list with `deepline csv show --csv <path> --summary` — never read a large CSV into
context.

## Step 1 — Collect the inputs

1. **The list** (CSV/table) and which column holds the email. Never edit other columns.
2. **The purpose** — cold volume send vs CRM refresh vs re-engagement. It decides the
   policy segments: for cold sends, role/generic mailboxes (`info@`, `support@`…) go to
   remove and personal/freemail goes to risky; for other purposes both go to risky.

## Step 2 — Free passes (zero credits, deterministic code — not an LLM)

Run in order, recording per-row reason + evidence at each:

1. **Normalize + dedupe.** Trim, lowercase for comparison (keep the original string).
   Exact-match duplicates: keep the first, mark the rest `remove: duplicate` with a
   pointer to the kept row.
2. **Syntax.** One local-part `@` one domain with a dot, no spaces — a cheap structural
   check, not full RFC. Failures → `remove: syntax-invalid`, quoting the string. Never
   "fix" a typo and keep the fixed version silently.
3. **Role/generic screen.** Local-part blocklist (production lists run ~40 tokens):
   admin, info, contact, support, sales, billing, hr, press, help, hello, office, team,
   marketing, careers, jobs, noreply, no-reply, postmaster, abuse, webmaster… Segment
   per the Step 1 policy — these are policy calls, not deliverability verdicts (a
   `support@` box may be genuinely read).
4. **Disposable domains.** Known disposable providers (mailinator, guerrillamail,
   yopmail…) → `remove: disposable`.
5. **MX per unique domain** (any DNS tool — don't hardcode a DoH URL; some networks
   block them). Three shapes: NXDOMAIN or no MX → dead; **null MX** (single record
   `0 .`) → the domain declares it takes no mail — dead *even though a record exists*;
   real MX → survives. Dead domains → `remove: dead-domain` for every row on them,
   quoting the DNS answer. This kills paid calls on dead rows for free.

## Step 3 — Classify survivors (free, deterministic)

No Deepline tool classifies a domain as personal / company / education for free, so do it
in the same local code (or a `run_javascript` step if the clean runs as a play): a
freemail domain list (gmail.com, googlemail.com, yahoo.*, outlook.com, hotmail.*, live.com,
icloud.com, me.com, aol.com, proton.me, protonmail.com, gmx.*, …) → personal; `.edu` /
`.ac.<cc>` → education; everything else → company. Personal → risky under a cold-send
policy. The paid validators in Step 4 return a cross-check (`free_email` on ZeroBounce,
`is_free` on BounceBan) — record it, but the policy segment comes from this pass.

## Step 4 — Paid validation on what's left (approval gate)

Pick a validator that separates catch-all from valid (`deepline tools search "email
verify" --json`, then `deepline tools describe <id> --json` for fields and price):
`zerobounce_validate` (0.28 credits/check), `leadmagic_email_validation` (0.09),
`bounceban_verify_single` (0.06). **State survivor count × per-check cost and get approval
before running.** Run it as a play over the survivors CSV: one `.withColumn` calling the
validator per row (see `verify-email-deliverability` for single checks), pilot a few rows,
then the full file and `deepline runs export <run-id> --out <validated.csv>`. Checks return
in seconds for every verdict. Map field PAIRS, never one field — vocabularies invert
across validators: ZeroBounce puts catch-all in `status: catch-all`; BounceBan puts it at
`result: risky` + `is_accept_all: true`; LeadMagic at `email_status: catch_all` +
`is_domain_catch_all`. Verdicts: plain valid (ZeroBounce `valid`, BounceBan `deliverable`
with `is_accept_all: false`, LeadMagic `valid`) → **keep**; catch-all → **risky**
(LeadMagic's `valid_catch_all` = keep, probe-confirmed); `do_not_mail` / `spamtrap` /
`abuse` / disposable / role sub-statuses → **remove**, quoting the sub-reason; `invalid` /
`undeliverable` → **remove**; `unknown`, timeouts, empty payloads → **could-not-verify** —
never rounded either way. Fuse validator with classifier: a freemail address can
validate as deliverable (observed on Clay's ZeroBounce action: `valid` / `sub_status:
alternate` + `free_email: true` on a Gmail address) — a mailbox verdict never overrides the
policy segment. A successful tool call is not data: it succeeds for every verdict.

## What good looks like

- **Reconciliation is the first check**: rows in = keep + risky + remove +
  could-not-verify. If the numbers don't add up, a row was dropped silently — the
  cardinal failure of list cleaning.
- Every removed row carries a reason AND quoted evidence (the DNS answer, the validator
  field pair, the duplicate pointer) — an audit trail, not a verdict.
- The common mistake: reading one validator field as a boolean. Catch-all hides inside
  the safest-looking field, in opposite directions per provider.
- Could-not-verify is an honest segment, not a failure — a common shape is `unknown` /
  `mail_server_temporary_error`, which is retryable later; the user decides whether to
  spend more checks.

## Rules

- MUST account for every input row in exactly one segment — never silently drop.
- MUST run all free passes before any paid call, and state cost + get approval first.
- MUST report raw provider fields alongside each verdict.
- NEVER guess a verdict for an unverifiable row; NEVER silently correct a malformed
  address; NEVER report catch-all, role, or disposable rows as plain valid.

## Output

1. **Audit CSV** — every input row: `email · normalized · segment · reason · evidence ·
   duplicate_of · provider`.
2. **keep.csv** — the sendable list (original strings, original columns intact).
3. **Summary**: rows in → unique → per-segment counts + % → credits actually spent
   (from `deepline runs get <run-id> --full --json`) → one-line recommendation for the stated purpose.

## Worked example

Ask: "Clean this 500-row conference list for a cold send." Free passes: 62 duplicates,
8 syntax-invalid, 41 role, 5 disposable, 37 on dead domains (3 of them null-MX) — 347
survive, zero credits. Classify: 29 personal → risky. Validation quote: 347 ×
`leadmagic_email_validation` 0.09 ≈ 31 credits — approved. Result: 214 keep, 71 risky
(29 personal + 42 catch-all), 203 remove, 12 could-not-verify. 500 = 214 + 71 + 203 + 12 ✓.
Recommendation: send to keep; escalate the 42 catch-alls with `allegrow_validate`
(0.12 each, ~5 credits) if the list matters.
