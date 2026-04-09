# What NOT to use for scoring — confirmation-biased CRM fields

Some CRM fields look like predictive signals but are actually downstream artifacts of AE engagement. They get populated **after** an AE decides an opportunity is worth working — so their correlation with win-rate is measuring "did the AE work this deal" rather than any causal property of the account. **Treat them as warning flags about pipeline hygiene, never as inputs to an ICP scoring model.**

## The fields to exclude

| Field | Why it's confounded |
|---|---|
| Catalyst note count (or any per-opp activity count) | AEs log notes on deals they're actively working. Won deals have more notes because someone was working them; the note count doesn't cause the win. On one real run, this field showed "109x lift" as the most extreme signal in the dataset — headline material — until we noticed the direction of causality. |
| `number_of_champions_c` / `number_of_decision_makers_c` / economic-buyer count | AE-counted fields. They get filled in during deal qualification, meaning they're present when someone bothered to qualify the deal. An unworked opp shows 0 across the board regardless of the account's actual buying committee. |
| `OpportunityContactRole` derivatives — total roles, champion count, technical-evaluator count | Same failure mode: OCRs are created as a byproduct of AE effort, not as evidence about the account itself. |
| MEDDPICC picklists (champion score, decision criteria score, decision process score, identify-implicate pain score) | In practice these fields are sparsely populated or uncalibrated. On one real run, both won and lost opps averaged <1 across all four scores — the signal is noise and the correlation is zero. Even when populated, they're AE judgments formed during qualification, not independent properties of the account. |
| Any field of the form "did the AE do X on this opp" | Rule of thumb: if the field is populated by the AE during deal execution, it's downstream of engagement. |

## How to think about it

The question an ICP scoring model should answer is "should we work this account?" — which means every input has to be observable **without** already working the account. Website content, job listings, tech stack, firmographics, and third-party news or funding signals all pass that test. CRM fields populated by AE activity don't.

## Safer alternative read for loss-reason data

Loss reasons themselves (`loss_decline_reason_c` = 'Poor Fit', 'Unresponsive', 'Return on Investment', etc.) ARE useful, but as a **diagnosis of the top-of-funnel ICP** rather than as scoring inputs. If 65% of your lost pipeline is "Poor Fit" + "Unresponsive", the lever is tighter ICP gating before opps get created — which is what this whole skill produces.
