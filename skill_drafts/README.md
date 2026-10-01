# Skill drafts: Clay skills ported to Deepline

> **Status: DRAFTS.** Like [`../drafts/`](../drafts/), these are not installed by `deepline skills` and
> are not production playbooks until reviewed and promoted into `skills/`.

These 66 skills are ports of the community and Clay-authored skills in
[clay-run/clay-skill-creator](https://github.com/clay-run/clay-skill-creator) (MIT, see
[`LICENSE-clay-skill-creator`](LICENSE-clay-skill-creator)). Each `SKILL.md` names its upstream path
in a `ported_from` frontmatter field.

## What changed in a port

- Clay mechanics were replaced with Deepline ones: `clay whoami` became `deepline preflight`, catalog
  actions and functions became `deepline tools execute`, tables, workflows and Audiences became plays,
  Customer DB tables or CSVs, and Claygent became `deeplineagent`.
- The skill's insight, rules, output contract and worked examples were kept.
- Every tool, play and monitor ID was confirmed against the live catalogue with `deepline tools describe`
  or `plays describe`. To re-check a skill, run
  `python3 deepline-skill-author/scripts/lint_skill.py <skill> --online`.
- Costs, counts and hit rates that the original authors measured on Clay are kept but labelled as
  Clay-measured. They are not Deepline prices.
- Where Deepline has no equivalent, the skill says so instead of approximating silently.
- Clay marketplace frontmatter and provenance instructions were removed. `clay-skill-author` became
  `deepline-skill-author` and `clay-org-chart-builder` became `org-chart-builder`.

## Verification state

- Offline tests pass in every skill that ships them (10 suites).
- **None has been run end to end against live Deepline.** No paid tool or play was executed during the
  port. Some output field names are marked "confirm on first response" because `describe` does not
  list them. Pilot a skill on a few rows before trusting it.

## Index

| Skill | What it does |
| --- | --- |
| [`10k-value-prop-match`](10k-value-prop-match/) | Match a seller's own value proposition against what a public target account actually says it's prioritizing in its 10-K — instead of matching on fixed… |
| [`account-health-audit`](account-health-audit/) | Audit what your account records CLAIM against independently re-derived evidence, and deliver a reviewable field-by-field delta — never a silent overwrite. |
| [`account-intelligence-analyst`](account-intelligence-analyst/) | Answer a specific question about a list of accounts with graded, sourced evidence — not a dossier. |
| [`account-tier-scoring`](account-tier-scoring/) | Tier a book of accounts with Deepline — turn a raw account list plus your ICP definition into tuned, auditable tiers (1–4 or A–F) with every score… |
| [`account-tiering-workflow`](account-tiering-workflow/) | Stand up an always-on account-tiering workflow as a Deepline play — a triggered pipeline (cron over a CRM segment, or an inbound webhook) that fires per… |
| [`alert-reps-on-account-signals`](alert-reps-on-account-signals/) | Turn a rep's target-account list into Slack alerts with Deepline — load the accounts into a Customer DB table, watch every account with three Deepline… |
| [`alpha-campaign`](alpha-campaign/) | Run a Deepline workflow that sources up to 100 people from an editable audience brief, qualifies them with Alpha Radar, finds and verifies work emails, and… |
| [`alpha-copy`](alpha-copy/) | Run Alpha Copy with Deepline: turn verified company changes into relevant, evidence-backed outreach using an editable offer, ICP, CTA, greeting and signature. |
| [`alpha-radar`](alpha-radar/) | Source a professional audience from a plain-English brief and learn which candidate types the user values through explicit likes and dislikes. |
| [`build-event-invite-list`](build-event-invite-list/) | Turn one CRM campaign record for a first-party event — a customer dinner, a roadshow, an executive roundtable, your own conference — into a ranked invite… |
| [`build-prospect-list`](build-prospect-list/) | Build a validated prospect list with Deepline from a target definition: an ICP (vertical + geography + size band) plus buyer personas → a deduped,… |
| [`buyer-classification`](buyer-classification/) | Classify each contact in a list as buyer / influencer / not-a-buyer FOR YOUR PRODUCT — is_buyer, a buyer-persona label, confidence, and a one-line rationale… |
| [`campaign-angle-finder`](campaign-angle-finder/) | Build the three-bullet "I had a few ideas for you" email, where the sender names what each bullet slot is about up front and the model only fills that slot… |
| [`check-employment-with-jev`](check-employment-with-jev/) | Build an always-on Deepline play, "Person Active At Company (Jev)", that answers whether a person still works at a given company, and in what capacity:… |
| [`clean-and-refresh-contact-data`](clean-and-refresh-contact-data/) | Clean and refresh an existing contact list or CRM export with Deepline — verify each person is still who the record says (right employer, right title,… |
| [`clean-company-names-for-copy`](clean-company-names-for-copy/) | Turn the raw company-name string on a lead row into the short human form a person would say out loud, so it can be dropped into email copy, using Deepline… |
| [`clean-email-list`](clean-email-list/) | Clean a CSV or table of email addresses into keep / risky / remove segments with per-row evidence — free deterministic passes first (dedupe, syntax, role… |
| [`clean-first-names-for-greetings`](clean-first-names-for-greetings/) | Turn the raw first-name field on a lead row into the name a person would actually be greeted by, so an email can open with it, using a Deepline play. |
| [`company-research-brief`](company-research-brief/) | Produce a structured, evidence-linked research brief on one company from its domain using Deepline — what it does, who it sells to, value prop and products,… |
| [`competitive-intelligence-radar`](competitive-intelligence-radar/) | Run a standing radar on a named competitor set with Deepline — sweep each competitor's public exhaust (announcements, pricing and positioning changes,… |
| [`contact-unlimited-enrichment-cascade`](contact-unlimited-enrichment-cascade/) | Build a reusable contact enrichment cascade on Deepline — a config-driven runner that takes a person and returns them with whatever contact details were… |
| [`dedupe-contacts`](dedupe-contacts/) | Find duplicate contacts in a CSV, a Deepline play dataset, or a CRM export and produce a merge plan — which records are the same person, which record… |
| [`deepline-skill-author`](deepline-skill-author/) | Create a Deepline GTM skill: turn a Deepline play you already built, a run you just did in this session, or just an idea, into a portable SKILL.md for the… |
| [`detect-tech-stack`](detect-tech-stack/) | Detect the technologies a company runs on its website — CMS, ecommerce platform, analytics, chat, marketing and ad tools — from a domain, using Deepline's… |
| [`enrich-account-list`](enrich-account-list/) | Enrich a list of accounts with validated firmographics using Deepline — industry, headcount, revenue, HQ, founded — one clean row per company, from a CSV or… |
| [`enrich-signup-users`](enrich-signup-users/) | Turn raw product signups — often just an email, frequently a personal one — into routed, evidence-backed leads using Deepline: classify every email into a… |
| [`event-follow-up-router`](event-follow-up-router/) | Turn an event or webinar registrant export into a synced campaign plus a routed follow-up plan — reconcile every registrant against your CRM for free, write… |
| [`find-decision-makers-at-company`](find-decision-makers-at-company/) | Find the actual decision-makers at a specific company with Deepline — the named people, with title, LinkedIn, seniority, and current-employment evidence —… |
| [`find-linkedin-profile`](find-linkedin-profile/) | Find a person's LinkedIn profile URL with Deepline — from their name and company, or from an email — and validate it before reporting. |
| [`find-recent-company-developments`](find-recent-company-developments/) | Summarize what changed at a company inside a lookback window you choose — new leadership who started in that window, merger, acquisition and divestiture… |
| [`find-work-email`](find-work-email/) | Find and verify a person's work email address using Deepline — from their name and company, or their LinkedIn URL. |
| [`find-work-phone`](find-work-phone/) | Find a person's work phone number — ideally a validated mobile — using Deepline, from their LinkedIn URL or name and company. |
| [`funding-signal-line`](funding-signal-line/) | Produce a copy-ready sentence about a company's funding round, and the list filters that select companies which have ever raised or raised recently. |
| [`generate-personalized-gift`](generate-personalized-gift/) | Pick one specific, buyable gift and write the note that goes with it, for each person on a list of LinkedIn profiles — by writing (once) and running a… |
| [`get-top-conference-attendees`](get-top-conference-attendees/) | Takes in (or finds) attendees you should connect with at your next conference, ranks and researches them, and adds them — along with their full research… |
| [`headcount-growth`](headcount-growth/) | Measure a company's headcount growth with Deepline — employee count plus percent change across 1/3/6/12/24-month windows, bucketed (shrinking / flat /… |
| [`hiring-radar`](hiring-radar/) | Turn open job postings into a hiring signal you can rank on — pick the arm whose filters can express the roles you care about, count them inside a stated… |
| [`icp-matrix-builder`](icp-matrix-builder/) | Turn an ICP described in your own words into an executable matrix — every dimension translated into the exact field and allowed value the platform will… |
| [`icp-outbound-campaign`](icp-outbound-campaign/) | Build an outbound campaign from your ideal customer profile: interview you for the ICP (who the buyer is, which companies, where, how many), turn it into a… |
| [`inbound-triggers-monitor`](inbound-triggers-monitor/) | Find the people already engaging with you on social and turn each interaction into a dated, deduplicated inbound trigger — pull your team's recent posts,… |
| [`job-posting-language-signal`](job-posting-language-signal/) | Produce a copy-ready clause about a role a company is currently hiring for, selected by language the sender cares about — "cold call", "outbound… |
| [`kill-or-keep`](kill-or-keep/) | Judge every live outbound campaign against thresholds set before anyone looks at the numbers, and return one verdict per campaign: fix deliverability first,… |
| [`linkedin-url-to-contact-card-to-save-in-your-contacts`](linkedin-url-to-contact-card-to-save-in-your-contacts/) | Use when the user pastes a LinkedIn profile URL (or asks for work email, mobile, and a contact/VCF card from LinkedIn) and you should enrich that person… |
| [`list-clearance`](list-clearance/) | Check a lead list before it goes anywhere near a sequencer, and return one verdict for the whole list: go, fix, or no-go. |
| [`monitor-buying-signals`](monitor-buying-signals/) | Watch a fixed list of target accounts for buying signals with Deepline — funding rounds, M&A, executive hires, expansion and other news events — and turn… |
| [`org-chart-builder`](org-chart-builder/) | Build an interactive org chart of a target account's current C-Suite and VP leaders from Deepline people search (CrustData), with reporting lines inferred… |
| [`prepare-job-application`](prepare-job-application/) | For each company and role on a job seeker's list, find the open posting and the recruiter attached to it, rewrite the resume in that posting's own… |
| [`pricing-page-signal`](pricing-page-signal/) | Decide whether a company publishes public self-serve pricing, and extract its plan tiers, price points and the axis its tiers differ on. |
| [`prospect-one-account`](prospect-one-account/) | Turn one company domain into a ready-to-review outbound package: what your CRM already knows about the account (recent activity, past opportunities, an… |
| [`renewal-risk-radar`](renewal-risk-radar/) | Watch the accounts whose renewal is coming up and surface the ones that got riskier this week, each with its evidence, as a ranked digest waiting for you on… |
| [`resolve-company-domain`](resolve-company-domain/) | Resolve a company name to its single canonical operating-company domain with Deepline — validated, evidence-backed, or an honest "ambiguous", "not found",… |
| [`score-accounts-with-jev`](score-accounts-with-jev/) | Build an account lead-scoring play in Deepline that uses Jev, TypeSafe's decision model, for the judgment calls and plain code for everything numeric. |
| [`score-contacts-with-jev`](score-contacts-with-jev/) | Build a contact lead-scoring play in Deepline that uses Jev, TypeSafe's decision model, to judge each person (their likely role in the purchase, their… |
| [`score-inbound-leads`](score-inbound-leads/) | Turn enriched inbound leads (person + company + ICP fields) into a composite score, an A/B/C/D tier, and a per-lead evidence trail — deterministic weights… |
| [`scrape-any-website`](scrape-any-website/) | Extract structured data from any web page or site using Deepline — pull the fields you name off a URL, a list of URLs, or a directory, and return clean rows. |
| [`signal-sourcer`](signal-sourcer/) | Source net-new accounts from live buying signals with Deepline — no starting list: define the events that matter (funding, breach/incident, expansion,… |
| [`source-candidates`](source-candidates/) | Turn a hiring conversation into a scored candidate list with Deepline — start from two or three profiles of people they would hire, or from the experience… |
| [`source-local-businesses`](source-local-businesses/) | Build a deduped, validated list of local businesses with Deepline — gyms, restaurants, clinics, retailers, agencies, any physical-location category — from a… |
| [`specificity-rewrite`](specificity-rewrite/) | Write the one sentence that makes a generic offer feel written for this company rather than for five thousand people. |
| [`swap-test`](swap-test/) | Measure how much of a "personalised" cold email is template, then rewrite the template sentences from sourced facts. |
| [`tam-audience-loader`](tam-audience-loader/) | Load a list of companies and a list of people into the Deepline customer database — a target account list, a TAM you built in a model conversation, a… |
| [`tam-builder`](tam-builder/) | Enumerate a total addressable market from an ICP definition with Deepline and report how much of it you can prove you have — a population figure with a… |
| [`track-champion-job-changes`](track-champion-job-changes/) | Build a recurring Deepline watcher over your champions — past buyers, power users, and key contacts at existing customers — that tells you the moment one… |
| [`value-first-cold-email`](value-first-cold-email/) | Write value-first B2B cold email for a prospect list, with every first line built on a why-now signal that was checked, not guessed. |
| [`verify-email-deliverability`](verify-email-deliverability/) | Check whether an email address actually accepts mail before you send to it, using a free MX pre-check plus a real mailbox-level validator through Deepline. |
| [`webinar-followup-router`](webinar-followup-router/) | Route webinar and event registrants into follow-up branches on three exact field reads — attended versus no-show, the account's qualification tier, and… |
