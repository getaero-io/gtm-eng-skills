# Find Companies, Contacts, And TAM

Use this when the user asks for accounts, companies, contacts, personas, TAM, portfolio/investor/accelerator lists, hiring-qualified accounts, source universe, signals, or provider strategy. This page is GTM sourcing alpha; return to `SKILL.md` for exact play/tool contracts and bootstrap basics.

The expensive failure is enriching contacts at the wrong accounts. Source and fit companies first when ICP, category, portfolio, geography, funding, hiring, or account quality matters.

## Source Universe

| Source shape | Preferred route | Why |
| --- | --- | --- |
| Official portfolio, accelerator, conference, partner directory, registry, filing | Extract source URL directly, then enrich | Official source beats provider reconstruction |
| Crisp ICP: funding, headcount, HQ, stage, category | Structured company discovery play/provider | Stable filters and useful firmographics |
| Fuzzy niche category, pain language, market concept | Semantic/web account seed, then evidence scoring | Taxonomies may be empty or broad |
| Known company/domain list | Company-to-contact route | Avoid broad people-search drift |
| Known people/contact rows | People email/phone/LinkedIn route | This is enrichment, not discovery |
| Hiring-qualified accounts | Company seed first, then hiring evidence | Hiring is a qualification layer |
| Local SMB/maps-style ask | Local/maps source, website/domain validation | Generic B2B providers under-cover SMBs |

Known-source rule: if you have the URL, fetch/extract it. Search only to find the URL. Keep `source_url`.

## Core Commands

```bash
deepline plays search "company list ICP TAM funding headcount hiring" --json
deepline plays search "company people email" --json
deepline tools search "company search funding headcount hq" --categories company_search --json
deepline tools search "people search title seniority linkedin domain" --categories people_search --json
deepline tools describe <tool-id> --json
```

After selecting likely play/tool candidates, return to `SKILL.md` for `plays describe`/`tools describe` contract gates and bootstrap/wrap/fork decisions.

## TAM

TAM means count basis plus representative sample, not just a CSV.

- TAM sizing only: count or `limit:1` first; return estimate, filter definitions, assumptions, confidence, and provider caveats.
- TAM list build: structured company discovery first; bootstrap `company-list` when filters, evidence, or export columns need edits.
- TAM plus contacts: confirm company source first, then contact/persona route; cap people/account.
- TAM plus automation: prove batch route first, then add cron/webhook/API wrapper.

Counts are gates for source choice, page count, and fanout. They are not enough when the user asked for rows.

## Scout Before Scale

For hard account-list asks:

1. Probe 2-3 plausible company sources with 3-10 row limits.
2. Normalize to `company_name`, `domain`, category, `company_fit_evidence`, `source`, and `miss_reason`.
3. Compare company quality, domain quality, category evidence, geographic fit, duplicate rate, cost, and billing shape.
4. Reject broad taxonomy noise before contact fanout.
5. Bootstrap/scale the winning route.

If rows are org units, directories, missing root domains, sentinel headcount values, weak evidence, or URL shorteners, the source is not validated.

## Structured Company Search

Preserve provider-returned firmographics directly: `company_name`, `domain`, `headcount`, `funding_round`, `hq_country`, category, growth, `company_fit_evidence`, `source`, `status`, and `miss_reason`.

Scar tissue:

- Validate enum-like filters before scale, especially categories, industries, funding rounds, and geography.
- Some providers use ISO-3 country codes (`USA`, `GBR`, `DEU`, `FRA`, `NLD`) while people geography may use full names.
- For niche verticals, prefer specific categories over broad industries.
- Growth metrics can be a free hiring proxy before paid job listings.
- Taxonomy is not evidence. Add `<vertical>_category` or `category` plus evidence text/URL.

## Hiring-Qualified Accounts

Hiring is a qualification layer:

1. Source companies from a known list or company search.
2. Qualify with job listings, careers pages, scoped web search, or growth proxy.
3. Filter/score hiring evidence before people lookup.
4. Preserve `hiring_evidence`, `hiring_source_url`, and `hiring_status`.

## Contacts And Personas

Use company domains over names. For common names, include domain/product/batch. Search broad function plus seniority, then score.

- Bad: exact title filters only.
- Good: function + seniority, e.g. `Growth` + `VP/Director`, `Security` + `Director/Head/VP`.
- For small companies, classic people DB coverage is weaker; use semantic/person web search sooner and validate current company.
- Require current company/domain match before email/phone enrichment. Mark `out_of_seed_domain` instead of exporting off-account contacts.

Contact pilot gate:

- Probe 3-5 representative accounts before scaling.
- Contact identity requires `contact_name`, non-empty `title`, and `linkedin_url`.
- Email is a bonus, not a substitute for identity.
- If fewer than about 40% of pilot rows have credible contact identity, change source mix or persona route before scale.
- Cap contacts per account before email/phone.

Final contact columns should be user-facing: `company_name`, `domain`, category, `company_fit_evidence`, `contact_name`, `title`, `linkedin_url`, requested email/phone, `source`, `status`, `miss_reason`.

## Provider Playbooks

- People search only after domains are seeded when account fit matters.
- Domain search is for domain/company discovery, not named-person email.
- Email finders require described person identity plus company/domain/LinkedIn context and declared `extractedValues.email`.
- Validators are not finders. Validate recovered channels after recovery and skip nulls.
- Phone finder requires a strong person anchor.
- Person LinkedIn search should validate name variants and current employer. Null beats wrong.
- Prefer result-priced or successful-hit billing when coverage is uncertain.

## Signals

For "find signals that separate won vs lost", "ICP signal discovery", or "net-new accounts like these wins":

1. Start with won/lost domains.
2. Dedupe and apex normalize.
3. Enrich website/jobs/evidence.
4. Score differential signals.
5. Preserve citations.
6. Produce top net-new prospects.

Quality gates: good website coverage, cited evidence for top signals, spot-checked job rows, and explicit lift/confidence. Contacts/emails require approval or a separate fanout route.

## Handoff

- Return to `SKILL.md` for exact play/tool contracts, bootstrap/wrap/fork, and generated SDK/API reference loading.
- Use `run-export-inspect-repair.md` before scale and after every run to inspect rows, billing, cache/reuse, failures, and exports.
