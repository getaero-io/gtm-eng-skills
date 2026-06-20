# Waterfall Cost Optimization Framework

**Comment keyword:** `WATERFALL`

This is the framework for designing an enrichment waterfall that is cheap enough to run and accurate enough to trust.

Bad waterfall:

```text
run every provider on every row and call it automation
```

Good waterfall:

```text
route by input quality -> stop on confidence -> review ambiguity -> measure cost per accepted result
```

The useful metric is not cost per API call.

It is cost per usable GTM action.

## The Rule

Do not optimize for the cheapest provider.

Optimize for the cheapest path to a result you trust enough to use.

## Waterfall Design Worksheet

Fill this out before writing the workflow.

| Question | Answer |
| --- | --- |
| What field are we trying to fill? | email, phone, LinkedIn, company domain, title, intent signal |
| What inputs do we have? | name, domain, company, LinkedIn, email, phone, workspace, CRM ID |
| What is the action downstream? | CRM update, sequence, rep task, campaign draft, review queue |
| What is the risk if wrong? | bounce, bad personalization, wrong account, compliance, rep trust |
| What counts as accepted? | verified, corroborated, no conflict, source priority wins |
| What gets reviewed? | ambiguous, conflicted, high-value, high-risk |
| What gets blocked? | suppression, mismatch, missing identity, stale data |
| What is the max cost per accepted result? | define before running |

## Cost Formula

For each provider:

```text
accepted_hit_rate = accepted_results / attempted_rows
cost_per_accepted_result = total_provider_cost / accepted_results
review_adjusted_cost = (provider_cost + human_review_cost) / accepted_results
```

For the full waterfall:

```text
total_cost = sum(provider_attempts * provider_attempt_cost) + review_cost
accepted_results = rows_with_usable_result
waterfall_cost_per_accepted_result = total_cost / accepted_results
```

Human review is not free. If a cheap provider creates a large review queue, it may be expensive.

## Example Waterfall: Work Email

```text
Input: first name, last name, company domain, optional LinkedIn URL

1. Check CRM/database cache
   - stop if verified and fresh
2. Run low-cost email pattern/provider
   - stop if verified
3. Run LinkedIn-aware provider if LinkedIn exists
   - stop if verified
4. Run premium provider only for high-fit accounts
   - stop if verified
5. Validate email
   - accept valid
   - review catch-all or risky
   - block invalid
```

Stop rules:

- stop when email is valid and identity matches
- stop when the row is suppressed
- stop when the account is below fit threshold
- stop when max cost is reached

## Example Waterfall: Mobile Phone

```text
Input: name, company, email or LinkedIn, optional address/location

1. Check CRM/database cache
2. Run high-precision phone provider
3. Run B2B provider only if LinkedIn/email identity is strong
4. Validate name and company match
5. Review before first activation
```

Stop rules:

- block on name mismatch
- review on company mismatch
- never write a phone when identity is weak

## Example Waterfall: Personal Email -> LinkedIn

```text
Input: personal email, name, product workspace, IP/company hint

1. Extract name/handle/domain hints
2. Search candidate profiles
3. Score candidates by name, company, location, role, product context
4. Accept only strong matches
5. Review everything else
```

Stop rules:

- block on name mismatch
- review on one-signal match
- accept only with corroborating evidence

## Segment-Specific Routing

Do not run the same waterfall on every row.

| Segment | Recommended routing |
| --- | --- |
| High-fit target accounts | spend more, require stronger evidence |
| Low-fit accounts | cheap lookup only or skip |
| Existing customers | suppress from acquisition, route to owner |
| Open opportunities | no automated sequence, owner task only |
| Personal email signups | identity review before CRM writeback |
| Event check-ins | fast follow-up, minimal enrichment, high suppressions |
| Closed-lost reactivation | trigger evidence before enrichment spend |

## Backtest The Waterfall

Use historical rows before production.

```text
Take 200 historical records:
- 50 known good contacts
- 50 known bad contacts
- 50 ambiguous records
- 50 high-value accounts

Replay the proposed waterfall in dry-run mode.

For each row, return:
- providers attempted
- provider cost
- accepted result
- blocked/review reason
- expected downstream action
- whether the output matched known truth
- whether the row would have been safe to activate

Compare:
- cheap-first routing
- quality-first routing
- high-fit-only premium routing
- current manual process
```

Ship the version with the best review-adjusted cost per accepted result.

## Eval Checklist

### Email

- Valid email format.
- Deliverability validation passed.
- Name/company identity matches.
- Not unsubscribed.
- No open opportunity suppression.
- Provider/source recorded.

### Phone

- Name validation passed.
- Company or personal identity corroborated.
- Not obviously stale.
- Review required before first outbound use.
- Provider/source recorded.

### LinkedIn / Identity

- Name match.
- Company match or plausible transition.
- Role/title match.
- At least two corroborating signals for personal email.
- Ambiguous matches go to review.

### Company

- Domain resolves.
- CRM duplicate checked.
- Company name/domain conflict reviewed.
- Firmographic source/date recorded.

## Rollout Plan

### Phase 1: Sample

Run 100-200 rows. No writes. Inspect every accepted result.

### Phase 2: Shadow

Run next to the current manual process. Compare accepted result count, quality, cost, and review burden.

### Phase 3: Approval Gate

Create CRM tasks, campaign drafts, or review queue items. No unsupervised sequences.

### Phase 4: Limited Writeback

Write only low-risk, missing fields with provenance.

### Phase 5: Production

Automate only the paths that passed evals. Keep ambiguous and high-risk paths in review.

## Metrics To Track

| Metric | Definition |
| --- | --- |
| Attempted rows | Rows eligible for provider call |
| Provider attempts | Calls made by provider |
| Hit rate | Provider returned a value |
| Accepted-hit rate | Returned value passed checks |
| Review rate | Rows needing human judgment |
| Block rate | Rows suppressed or rejected |
| Cost per accepted result | Total cost divided by accepted rows |
| Review-adjusted cost | Provider cost plus human review cost |
| Downstream conversion | Reply, meeting, opp, expansion, or other workflow-specific outcome |

## Prompt To Optimize Provider Order

```text
Given this waterfall run summary, recommend a cheaper provider order.

Do not optimize for raw hit rate. Optimize for review-adjusted cost per accepted result.

Inputs:
- provider attempts
- provider cost per attempt
- hit rate
- accepted-hit rate
- review rate
- conflict rate
- downstream action value
- segment labels

Return:
- recommended provider order by segment
- providers to skip
- fields that need stronger validation
- rows that should go to review earlier
- estimated cost change
- quality risks introduced by the new order
```

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Running all providers on all rows | route by segment and stop on confidence |
| Measuring hit rate only | measure accepted-hit rate |
| Ignoring review cost | include review-adjusted cost |
| Writing every returned field | write only fields that pass policy |
| Treating CRM as just another provider | CRM owns owner, lifecycle, deal state, suppressions |
| Using one global provider order | route by input quality and field type |
| Skipping backtests | dry-run historical rows first |

## Sources And Basis

Public sources:

- Deepline video page: Waterfall Enrichment Is Workflow Engineering Now, `https://deepline.com/blog/waterfall-enrichment-workflow-engineering`.
- Deepline guide: GTM Data Infrastructure Workflows, `https://deepline.com/blog/gtm-data-infrastructure`.
- Deepline guide: 30 Claude Code GTM Workflows, `https://deepline.com/blog/claude-code-gtm-workflows`.
- Deepline glossary: Waterfall Enrichment, `https://deepline.com/glossary/waterfall-enrichment`.

Internal sources used to build this asset:

- Sung Waterfall Complexity video and blog draft in this repo.
- Anonymized customer-call field notes from March-May 2026 covering multi-provider enrichment, CRM activation, provider selection, data-quality risk, pricing concerns, and workflow implementation.
- Deepline internal GTM operator corpus analysis covering enrichment/contact-data, integration/writeback, cost/credits, workflow automation, and data-quality/freshness pain clusters.

## Send Copy

Here is the waterfall cost optimization framework.

The key idea: stop measuring cost per API call. Measure cost per accepted result, including review time and downstream risk.

Start with one field, one workflow, one backtest. Then optimize provider order by segment instead of running every vendor on every row.
