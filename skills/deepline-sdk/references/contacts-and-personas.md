# Contacts and Personas

Use this when the user asks for contacts, titles, emails, phones, LinkedIn URLs, org charts, or company-to-person workflows. Company fit comes first when account/category/portfolio/vertical matters.

## Known Company to Contact

Use company domains over names. For common names, include domain, product, batch, or another disambiguator. Search for broad function plus seniority, not exact titles.

- Bad: exact `Head of Growth`, `VP RevOps`, `GTM Engineer` filters.
- Good: `Growth` + `VP/Director`, or `Security` + `Director/Head/VP`.
- For <500 employees, narrow title filters often return zero; broaden function and score afterward.
- For <50 employees, classic people DB coverage is weak; use semantic/person web search sooner and validate current company.
- Dropleads `keywords` must be split words (`["GTM","Engineer"]`), not one phrase. Prefer `companyDomains` over fuzzy `companyNames`.

People provider order after play routing:

1. Wiza/Apollo masked sources for sizing; pair Apollo search with match when needed.
2. Dropleads for mid/large company title/seniority/dept/geo/tech/revenue.
3. Apollo when Dropleads misses and filters fit.
4. CrustData person search after autocomplete/contract validation.
5. Lusha or AI Ark for specific filters.
6. Exa people/search for tiny startups, ambiguous titles, or web-indexed roles.
7. ContactOut/Icypeas/RocketReach/PDL only when their contract is best remaining fit.

When coverage is uncertain, prefer routes whose described pricing charges on returned contacts or successful hits. Avoid scaling per-attempt/request/page people searches until a small pilot proves current-company match, title coverage, and cost per usable contact.

After people search, require current company/domain match to the seed account before email enrichment/export. Mark `out_of_seed_domain` instead of exporting off-ICP contacts.

## Contact Pilot Gate

Probe contact routes on 3-5 representative accounts before scaling.

- Compare at least one company-row-to-contact play with at least one direct people-search/provider route when coverage is unknown.
- Contact success requires identity: `contact_name`, non-empty `title`, and `linkedin_url`.
- Email is a bonus, not a substitute for identity.
- If a 1-3 row pilot returns names/LinkedIn but zero titles, inspect/export the pilot and fix projection or route before scale.
- If fewer than ~40% of pilot rows have credible contact identity, change source mix or contact route before scale.
- Stop after the pilot when cost per usable contact is high or misses cluster by company size, geography, or title wording. Change provider order or broaden the persona gate before full fanout.

Keep final column names user-facing: `contact_linkedin_url` -> `linkedin_url`, `work_email` -> `email`, `contact_title`/`matched_role` -> `title` only when it contains real title/persona evidence.

Before final write, run this small projection checklist:

1. Header includes every requested field: `company_name`, `domain`, category, `company_fit_evidence`, `contact_name`, `title`, `linkedin_url`, requested email/phone, `source`, `miss_reason`.
2. Raw play export fields are not dropped during cleanup; preserve evidence/status/source/miss columns.
3. `contact_name`, `title`, and `linkedin_url` have enough non-empty values for the deliverable, or rows have honest `miss_reason`.
4. If title is blank but role/persona is only in `matched_role`, do not pretend it is a title; either fetch/repair title or mark title unavailable.
5. Do not write a polished CSV until those counts are checked.

## Role and Persona Gates

Persona fit is a gate, not decoration. Parse requested function and seniority before people search; export only matching contacts or mark misses.

- Healthcare clinical: clinical operations, clinical informatics, CMIO, nursing informatics, care operations, provider operations, clinical transformation, or adjacent clinical leadership. Generic sales, marketing, engineering, product, finance, or generic IT leaders are misses.
- Security: security engineering, appsec, product security, cloud security, CISO/VP/Director/Head security. Generic IT or compliance may be adjacent, not a match.
- Marketing: marketing/growth/demand gen/product marketing. Pure sales or revenue ops is not enough unless prompt allows.
- Data/AI: data science, ML, analytics, AI platform. Generic engineering leaders need evidence.
- SMB owner personas: owner/CEO/president can be valid only for smaller/local accounts.

Cap contacts per account before email/phone. For account-grain deliverables, keep `contact_1_*` slots. For contact-grain deliverables, create a second contact table with parent account lineage.

## Email, Phone, and LinkedIn

- Small startups: Hunter underperformed in documented small-company runs; LeadMagic-first can be better after identity/domain fit.
- Name+domain email tools need person fields plus domain/company and must declare `extractedValues.email`.
- Domain-search tools are not named-person email finders.
- Validators are not finders; run them after recovery and skip nulls.
- Prefer finder waterfalls that bill on successful hits over validators, request-priced enrichment, or broad AI research passes. Validate only recovered channels.
- Person LinkedIn: quoted name + company + role + `site:linkedin.com/in`; validate current employer and name variants.
- Wrong LinkedIn URLs poison downstream enrichment. Null beats wrong.
- Phone finder requires strong person anchor; validate known phones with verifier tools after recovery.

## Local SMB and Org Charts

For local SMB asks, start with maps/local search, use structured local business search, and pilot one query before scaling cities/categories.

For org charts, choose mode first:

- Company-wide mapping: source roster cheaply, rank roles, infer reporting lines with confidence.
- Person-centric 2-up/2-down: verify anchor current employer, then search adjacent title tiers. Do not pull an entire enterprise roster.

## Convergence

- Filter and supplement instead of restarting when some rows fail.
- If you have about 80% of target with good evidence, ship partials with `miss_reason` rather than buying broad noise.
- If one source caps below target, add disjoint branches: structured pull, adjacent category pull, hiring-aware pull, semantic/web pull. Union, score, dedupe, then slice.
- Use provider-returned firmographics directly. Do not rebuy headcount/funding/HQ with AI.
- Stop source tuning after one shape correction. A second miss means source strategy, not syntax.
- PDL is last resort; use surgically for senior gaps or difficult structured queries.
