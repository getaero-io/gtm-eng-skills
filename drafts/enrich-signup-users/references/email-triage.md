# Email triage — classifier semantics, the enum, and the blocklists

## The classifier: build it locally (no Deepline tool does this)

Deepline has no email-components classifier, and it does not need one: the split is
free, deterministic code (a short script, or a `run_javascript` column in a play).
Emit per row: `domain`, `local_part` (before any `+tag`), `is_personal` (domain in a
freemail list: gmail, googlemail, yahoo, outlook, hotmail, live, icloud, me, aol,
proton/protonmail, gmx, yandex, mail.com, zoho, …), `is_education` (`.edu`, `.ac.<cc>`,
`.edu.<cc>`), and `name_hint` parsed from the local-part.

Lessons carried over from Clay's free extract-email-components action (measured
2026-08) — they apply to any classifier you write:

- **"company" is a RESIDUAL class** — it means "not a known freemail/edu".
  Disposable providers and NONEXISTENT domains both land there. Treat it as "company
  candidate", never "real employer".
- **Role local-parts get no flag by default** — `info@`, `support@`, `test@` pass
  through unless you screen them. The generic screen below is your job.
- **A name parsed from the local-part is a hint, never an identity** — handle
  parsing capitalizes bare handles into name-shaped strings ("Kc Builds"). A search
  input later, never a result.

## Your deterministic screens (run on top of the classifier, still free)

1. **Generic-mailbox blocklist** — production builds run ~40 local-part tokens, wider
   than the handful usually quoted: `admin, info, contact, support, sales, hello,
   office, team, billing, hr, press, marketing, careers, jobs, help, service, admissions,
   accounts, finance, legal, security, abuse, postmaster, webmaster, noreply, no-reply,
   donotreply, mail, mailer, newsletter, notifications, alerts, dev, test, demo, root,
   sysadmin, it, ops, orders, enquiries, feedback` (match the local-part before any
   `+tag`, case-insensitive). Hit → enum `generic`.
2. **Disposable-provider list** — mailinator, guerrillamail, yopmail, 10minutemail,
   temp-mail and kin → enum `junk`. These are honeypot-adjacent; never spend on them.
3. **Freemail-typo screen** — a domain within edit-distance 1 of a major freemail
   domain, or a known typosquat (gmial.com, gamil.com, gmali.com, gmail.co, yahooo.com,
   hotmial.com, outlok.com, …), is a mistyped PERSONAL address, not a company: the
   classifier's residual "company" class will happily bless it, and typosquat domains
   are spam-trap territory. Classify `personal` with a `typo-domain` flag (no company
   candidate, no identity anchor, never spend); surface the flag so the user can chase
   the corrected address.
4. **Malformed / no-email** — fails basic RFC shape or the email cell is empty → enum
   `junk` / `no-email`.
5. **Vanity-domain caveat** — when the domain's registrable label ≈ the person's own
   name tokens (jordan@jordanlee…), the "company" is usually the person: treat the
   domain as a personal brand, not an employer anchor — identity may still resolve, but
   don't count the domain as a company signal on its own.
4. **(Optional) dead-domain screen** — a free MX check (any DNS tool; never hardcode a
   DoH URL) on unique domains kills spend on domains that can't receive mail: NXDOMAIN
   or no MX → dead; null MX (`0 .`) → declares no-mail; real MX → proceed.

## The Input Email Type enum

The routing key every downstream step gates on. One distinction to keep straight:
**`junk` is a routing verdict, not an address class.** A work-shaped address at a dead
or nonexistent domain is still a work-TYPE address — one that can't receive mail. Keep
the two facts separate (type: work; liveness: dead → route junk, spend nothing);
"disposable" means a disposable PROVIDER, never "any domain that won't resolve".
Conflating them corrupts both the routing evidence and any downstream segment stats.

Base tier (free, always):

| Value | Meaning | Downstream |
|---|---|---|
| `work` | company-candidate domain, person-shaped local-part | full path: identity → company → fit |
| `personal` | freemail | identity via email tie only; no company anchor; no company-anchored validation |
| `education` | `.edu`-class | the domain is the SCHOOL: identity corroborated via education history, employer comes from the identified person |
| `generic` | role mailbox | disqualify pre-spend ("mailbox, not a person") |
| `junk` | disposable / dead / malformed | disqualify pre-spend |
| `no-email` | empty cell | disqualify pre-spend |

Validated tier (optional, `leadmagic_email_validation` at 0.09 credits/row when the user
wants sendable addresses):
fuse a deliverability verdict into the enum — `valid` / `valid-personal` /
`valid-edu` / `valid-catch-all` / `catch-all` / `invalid` (the production ~8-value
shape; map from the validator's real status field — LeadMagic returns
`email_status` of `valid` / `valid_catch_all` / `catch_all` / `unknown` / `invalid`,
check the first response). Two traps: a validator's `valid` on a freemail address is deliverability, not
identity or policy — never read it as a segment pass; and catch-all is a per-validator
verdict — stay inside one validator's vocabulary. Rows you didn't validate carry
`validity: unverified` — an honest flag; absence of validation never gates a row out
(gate only on positive invalidity evidence).

## Verified failure shapes to gate on

- **Completion is not data** — a successful call wrapping an empty match is the routine
  miss shape, at call level AND row level (a completed play run can hold failed rows).
  Gate every verdict on the presence of an actual value.
- **Misses return in seconds** on single-lookup enrichments — fast+empty is the normal
  not-found path, not an error.
- **Headcount bands are strings** (`basic_info.employee_count_range`, e.g. "1001-5000") —
  prefer `headcount.total` when present, else parse bands or compare
  ordinals; `parseInt` silently yields 1 and `Number()` NaN, both of which flow through
  comparisons as false. Unparseable → `unresolved`, visibly.
