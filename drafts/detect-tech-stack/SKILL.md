---
name: detect-tech-stack
description: |
  Detect the technologies a company runs on its website — CMS, ecommerce platform,
  analytics, chat, marketing and ad tools — from a domain, using Deepline's BuiltWith
  domain lookup (`builtwith_domain_lookup`). Use whenever someone asks: what tech stack
  does this company use, do they run Shopify or HubSpot or Marketo, detect technologies
  on this domain, get technographics for these accounts, or find displacement targets
  from their current tools. It returns detected technologies grouped for GTM use, graded
  by how well the evidence supports *current* usage, plus an explicit list of what this
  method cannot see. Do NOT use it to prove a company does NOT use a tool (website
  detection cannot show absence), to detect back-office SaaS — finance, HR, ERP, most
  CRMs (invisible to website scanning; that needs deeper research), or to find people at
  the company (people search). It never pads sparse results and states cost before
  spending credits.
category: research
personas: [sales-development, marketing]
mechanism: functions
touches: read-only
keywords: [tech-stack]
ported_from: clay-run/clay-skill-creator/skills/clay/detect-tech-stack
---

# Detect a company's tech stack

The insight: **technographics answer "what can the website prove?", never "what does the
company use?" — and an unfiltered answer is a lifetime archive, not a snapshot.** The
BuiltWith lookup reads the site's source code, so it sees what runs in a visitor's
browser and is blind to everything server-side or back-office (finance, HR, ERP always;
CRM unless a form embeds it). Asked for history, it returns *every technology ever
detected* — a current Shopify Plus store still lists Magento and WordPress from years
past. Both verdicts are traps: **detected** may be history, and **not detected is never
evidence of non-use**.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Domains** | one hostname per row | given only a company name, resolve the domain first and sanity-check it — a wrong domain returns a confidently wrong stack with no error |
| **The GTM question** | map the visible stack, confirm one named tool, look below the SaaS layer, or detect a back-office competitor | ask **before** spending. This surface fully answers the first, answers the second only when the tool is website-visible, and only contributes partial evidence to the last two |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the domains you supply, and the technology sources it queries per domain.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or claims a technology it did not observe.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, run
`npm install -g deepline && deepline auth register --wait auto`, then re-run preflight. Tell
the user which org you are in and the balance it reports.

## Step 1 — Collect the inputs

1. **Domain(s)** — `builtwith_domain_lookup` takes `domain` (one hostname) or `domains`
   (up to 16). Given only a company name, resolve the domain first with the free
   `crustdata_v3_company_identify` (`names: [...]`) and sanity-check it: name-only matches
   are candidates, and a wrong domain returns a confidently wrong stack with no error.
2. **The GTM question** — which scenario, because it sets the confidence bar:
   (a) map the visible stack; (b) confirm one named tool; (c) infrastructure below the
   SaaS layer; (d) back-office competitor detection. This lookup fully answers (a),
   answers (b) only when the named tool is website-visible, and only contributes partial
   evidence to (c) and (d) — say which case applies *before* spending, not after.

## Step 2 — Run the lookup

```bash
deepline tools describe builtwith_domain_lookup --json   # live inputs + pricing
deepline tools execute builtwith_domain_lookup \
  --input '{"domain":"acme.example","live_only":true,"no_pii":true}'
```

`live_only` defaults to `true` (currently live technologies only); set it `false` only when
the user wants history, and then treat every entry as possibly archival. `first_detected_range`
/ `last_detected_range` narrow by detection date. `no_meta: true` drops BuiltWith metadata
(company name, socials, ranks) when you only want technologies.

Pricing on this tool is "calculated after execution from returned usage" — there is no
fixed per-call rate in `describe`. Run one domain first, read the charge with
`deepline billing`, quote that as the per-domain estimate, and state that a miss can
still bill. Get approval before multi-domain runs. For hundreds of domains or a recurring
refresh, move to a play (`deepline plays run`, one `.withColumn` calling
`builtwith_domain_lookup`) and say so.

Corroboration arms, when one detection carries the decision:
- `predictleads_company_technology_detections` (0.56 credits/call, `company_id_or_domain`,
  `first_seen_at_*` / `last_seen_at_*` filters) — dated detections, good for "is this
  still current".
- `bloomberry_get_company_tech_stack` (0.43 credits/call, `domain`) — vendor list grouped
  by category; can include vendors that are not website-visible.
- For scenario (d), `theirstack_technographics` (1.66 credits/result, `company_domain`)
  infers technologies from job-posting mentions — a different evidence class (the company
  hires for the tool), not a website detection. Label it as such.

## Step 3 — Read the raw output for what it is

The output field names are the provider's; check them in the first response before
parsing. Know the defects before reporting anything:
- **Not-found is an empty technology list** with the call still succeeding — gate on
  content, never on status.
- **History leaks in** whenever `live_only` is off or a date range is wide: the same
  domain can list two ecommerce platforms or three web servers. Read the
  first/last-detected dates the response carries.
- **Pseudo-entries**: BuiltWith metadata can ride along (copyright year, traffic ranks,
  stock-exchange listings, hreflang tags, "403 Error"). Filter these out, or pass
  `no_meta: true`; they are not technologies.

Then grade each real finding:
- **Detected, corroborated** — multiple same-family entries (Shopify + Shopify Hosted +
  Shop Pay...), a recent last-detected date, or a structural role you can confirm on the
  live site. Safe to cite.
- **Detected, uncorroborated** — a single mention, or an old last-detected date (the
  archive problem). Usable for whitespace/ICP inference, never quoted as current usage in
  outreach without a live-site check. Contradictory sets (Magento *and* Shopify; three
  different web servers) are the archive showing itself — pick what the live evidence
  supports.
- **Not detected (visible category)** — weak evidence of absence, still not proof.
- **Not assessable (invisible category)** — the scan proves nothing either way; name
  these explicitly when they're what the user asked about.

## What good looks like

- Displacement outreach cites only corroborated detections — a stale archive entry
  quoted as current is the mistake that burns the email.
- A sparse result on a real but minimal site is a finding ("little detectable
  technology"), not a failure to fix by re-running or padding.
- The common mistake: reporting "no CRM detected" as "no CRM". The honest line is "no
  CRM visible on the website — most CRM usage isn't."

## Rules

- MUST state per-domain cost before running, including that misses still bill.
- MUST filter metadata pseudo-entries and use detection dates to separate live from archive.
- NEVER report "not detected" as "does not use".
- NEVER present an uncorroborated (possibly historical) detection as current usage.
- NEVER pad a sparse result with plausible-sounding technologies.

## Output

Per domain: technologies grouped by GTM-relevant category (commerce, marketing/ads,
analytics, support, infrastructure), each as `technology · evidence (corroborated /
uncorroborated) · last detected`, then a **not-assessable line** naming the invisible
layers relevant to the user's question, then a one-line readout tied to their stated
scenario.

## Worked example

Ask: "Does northfield-outfitters.example run Shopify? We sell a Shopify competitor."
Scenario (b), website-visible — this surface can answer. Run one
`builtwith_domain_lookup` (charge read back from `deepline billing`, approved): the list
includes Shopify, Shopify Hosted, Shop Pay, Shopify Custom Theme → corroborated current
storefront — displacement-qualified. A history pull (`live_only: false`) also contains
"Magento" with a last-detected date years back: archive noise, contradicted by the
corroborated Shopify family — not reported as in use. Counter-case: "Do they use
Workday?" → not assessable from the website — HR systems don't appear in site source;
recommend job-postings evidence (`theirstack_technographics`) labeled as hiring-derived,
instead of spending here.
