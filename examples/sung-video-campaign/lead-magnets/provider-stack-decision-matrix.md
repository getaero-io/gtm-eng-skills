# GTM Provider Stack Decision Matrix

**Comment keyword:** `PROVIDERS`

This is the provider decision matrix for GTM engineers who are tired of picking data vendors by vibes.

Provider sprawl does not mean "we use too many vendors."

It means nobody knows which provider is trusted for which field, which one runs first, what counts as enough evidence, what should be sent to review, and what is safe to write back to CRM.

## The Rule

Every provider needs a job.

If a provider does not have an explicit job, it becomes another tab, another CSV, and another argument about which row is "more right."

## Provider Jobs

| Job | Examples of inputs | What good looks like | Default action |
| --- | --- | --- | --- |
| Company resolution | domain, company name, website | canonical company, domain, LinkedIn, industry, size | write if missing |
| Contact identity | name, company, LinkedIn, email | same person, current role, title, profile URL | write if high confidence |
| Work email | name + domain, LinkedIn, company | verified or likely-valid email | validate before activation |
| Mobile phone | name, LinkedIn, email, address hint | high-confidence direct dial/mobile | review before first use |
| Firmographics | domain, company | employee count, industry, HQ, revenue band | write if source priority wins |
| Technographics | domain, job posts, website, docs | stack evidence with source | add as evidence, not truth |
| Intent/timing | hiring, funding, layoffs, ads, pricing, product usage | reason to act now | route to workflow |
| CRM context | account/contact/deal state | owner, lifecycle, opp, customer, suppression | source of truth for action |
| Campaign destination | HubSpot, Salesforce, Marketo, Smartlead, Instantly | correct owner/list/sequence/task | write only after guardrails |

## Source Priority

You need field-level priority rules. A single global provider ranking will fail.

Example:

| Field | Priority order | Notes |
| --- | --- | --- |
| CRM owner | CRM only | Never let enrichment overwrite owner |
| Lifecycle stage | CRM only | Used for suppressions |
| Company domain | CRM -> website -> company resolver | Review conflicts |
| Company size | CRM -> firmographic provider -> LinkedIn estimate | Keep source/date |
| Contact title | CRM recent manual edit -> LinkedIn -> people provider | Prefer recent human edits |
| Work email | verified provider -> pattern + validation -> review | Validate before campaign |
| Mobile | consumer/phone provider -> B2B provider -> review | Higher risk; require evidence |
| Product usage | warehouse/product DB | Enrichment vendors do not define usage |
| Why-now signal | first-party -> public source -> inferred | Preserve evidence URL/table |

## Routing By Input

### Domain Only

Use when you have a company list.

```text
domain
-> company resolver
-> firmographics
-> technographics / timing signals
-> CRM match
-> contact search only if account passes fit
```

Do not search contacts for every domain before you know the account is worth it.

### Company Name Only

Use when the list came from events, spreadsheets, forms, or partner data.

```text
company_name
-> domain resolution
-> duplicate/domain confidence check
-> company enrichment
-> review if multiple plausible domains
```

Company-name-only matching should be conservative. Bad domain resolution poisons every downstream step.

### LinkedIn URL Present

Use when you have the strongest contact identity clue.

```text
linkedin_url
-> profile enrichment
-> current company/title validation
-> email waterfall
-> CRM match
-> safe writeback
```

If LinkedIn is present, providers that perform best with profile URLs should run before generic name/domain search.

### Personal Email

Use when product signups arrive from Gmail, iCloud, Outlook, university, or other personal domains.

```text
personal_email + name + product/workspace context
-> identity candidate search
-> LinkedIn/company resolution
-> corroboration
-> review unless high confidence
```

Never treat a personal email match as automatically CRM-safe.

### Work Email

Use when the domain itself is useful evidence.

```text
work_email
-> domain extraction
-> company match
-> contact lookup
-> CRM duplicate check
-> enrichment only for missing fields
```

Do not spend money enriching fields you already trust.

## Confidence Levels

| Level | Meaning | Action |
| --- | --- | --- |
| Accepted | Strong identity + source priority + no conflict | Write or activate |
| Corroborated | Two or more independent signals agree | Write low-risk fields, review high-risk |
| Plausible | One good signal, no contradiction | Review |
| Conflicted | Two trusted sources disagree | Review and preserve both |
| Blocked | Suppression, missing identity, low trust, or policy risk | Do not activate |

## Writeback Policy

Do not write data just because a provider returned it.

| CRM field type | Default policy |
| --- | --- |
| Owner | never overwrite |
| Lifecycle stage | never overwrite from enrichment |
| Email | write if verified and field is empty; otherwise review |
| Phone | write if confidence high and field empty; otherwise review |
| Title | write if empty or enrichment source is newer and trusted |
| Company size | write with source/date |
| Intent signal | append as evidence, do not overwrite |
| Sequence/list membership | approval-gated until evals pass |

## Provider Scorecard

Use this before adding a provider.

| Criterion | Question | Score 1-5 |
| --- | --- | ---: |
| Coverage | Does it return results for our ICP? |  |
| Precision | Are returned fields usable without cleanup? |  |
| Input fit | Does it need LinkedIn, email, domain, phone, or name? |  |
| Freshness | Is the result current enough for activation? |  |
| Evidence | Does it return source/provenance? |  |
| Cost | What is cost per attempt and accepted result? |  |
| Latency | Can it run in the workflow SLA? |  |
| Failure mode | Does it fail cleanly or return garbage? |  |
| Writeback risk | Could wrong output damage CRM or outreach? |  |
| Review burden | How many rows need human review? |  |

## Decision Matrix

| Use case | Start with | Fallback | Review trigger |
| --- | --- | --- | --- |
| Build TAM from domains | company resolver + firmographics | web research + job posts | multiple domains or low fit |
| Find contacts at known accounts | LinkedIn/Sales Nav-style source | people provider | stale title or missing company |
| Find work emails | cheapest accurate email source | email waterfall | unverified or catch-all |
| Find mobile phones | high-precision phone source | B2B provider only when identity strong | any name/company mismatch |
| Resolve personal emails | identity graph + LinkedIn search | manual review | weak or single-signal match |
| Add timing signals | first-party CRM/product data | public trigger sources | no source URL/table |
| Push to campaign | CRM + suppression check | owner review | customer, open opp, unsubscribed |

## Evals

Run provider evals by use case, not globally.

Minimum eval set:

- 50 known good records.
- 50 known bad records.
- 25 ambiguous records.
- 25 historical records that caused issues.

Track:

| Metric | Why it matters |
| --- | --- |
| Attempt rate | Did the provider run when expected? |
| Hit rate | Did it return anything? |
| Accepted-hit rate | Did it return something usable? |
| Conflict rate | Did it disagree with trusted data? |
| Review rate | Did it create human work? |
| Cost per attempt | What did it cost to call? |
| Cost per accepted result | What did useful output cost? |
| Bad-write risk | Could this damage CRM or campaigns? |

## The Practical Rollout

1. Pick one workflow.
2. List every field the workflow needs.
3. Assign one source of truth per field.
4. Add fallback providers only for missing fields.
5. Decide review triggers before the first run.
6. Run 100 historical rows in dry-run mode.
7. Compare accepted results to known good CRM/product/account state.
8. Turn on writeback only for low-risk fields.
9. Keep high-risk actions approval-gated.

## Sources And Basis

Public sources:

- Deepline video page: Provider Sprawl Is Eating GTM Workflows, `https://deepline.com/blog/provider-sprawl-gtm-workflows`.
- Deepline guide: GTM Data Infrastructure Workflows, `https://deepline.com/blog/gtm-data-infrastructure`.
- Deepline guide: GTM Operator Corpus Analysis summary incorporated from internal research, including Clay Slack and Deepline prompt-corpus patterns.

Internal sources used to build this asset:

- Anonymized customer-call field notes from March-May 2026 covering provider choice, CRM activation, implementation risk, pricing/data-quality objections, and multi-vendor consolidation.
- Sung Provider Sprawl video and blog draft in this repo.
- Deepline campaign sample workflows for signup, product usage, personal email identity, and event follow-up.

## Send Copy

Here is the provider stack decision matrix.

The useful version is not "which vendor is best?" It is "which vendor is trusted for which field, on which input, with what evidence, and what happens if it disagrees with CRM?"

Start by assigning provider jobs, field-level source priority, review triggers, and writeback rules. Everything else gets easier after that.
