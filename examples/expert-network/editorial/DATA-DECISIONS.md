## Collect data that changes the next decision

Start with a problem, then choose the field. A field earns its place when it changes who you recruit, what you offer, what you fix or whom you invite back.

Keep three questions separate: Can we reach this person? Can they do this task? Can they start now? An email address, a firm name and a completed signup answer different questions.

The examples below are proposed additions. They do not change the running Plays or start outreach. All example people, rates, dates and outcomes are synthetic.

| Problem | Data to collect | Example and next action | Measure |
|---|---|---|---|
| The queue has 100 people, but none fit the next project | Required specialty, task format, jurisdiction if relevant, due date; each expert's verified skills and availability | You need pricing scenarios. Most candidates have operations experience. Search for pricing experience and keep separate counts by specialty | Eligible, available experts per open task; time to fill |
| A prestigious title hides weak task fit | Project type, personal responsibility, date, source URL, reviewer decision | A consultant led pricing interviews but did not build the financial model. Consider them for interview scenarios; leave modeling fit unknown | Accepted first contributions per qualified expert, by task type |
| A lawyer's profile does not establish the required qualification | Registration number, jurisdiction, registry status, checked date; relevant practice evidence | The task requires experience with New York commercial contracts. Check the registry and review relevant experience separately | Evidence-complete reviews per completed qualification review |
| Several records describe the same person | Stable expert ID, canonical profile URL, confirmed contact address, identity evidence | A referral and a search return the same consultant. Merge the evidence and preserve both source touches | Duplicate enrollments; unique eligible contacts |
| Invitations get replies but few acceptances | Offer version, task scope, estimated effort, rate, payment basis, reply and decline reason | An expert replies that the deadline is too short. Offer a later slot if available; do not rewrite the email opener | Accepted offers per delivered eligible invitation, by offer version |
| Qualified people never start | Required prerequisite, status, blocker, owner, detected time, next review time | Terms are signed but task access is missing. Route an access fix to expert ops | Time from accepted offer to work-ready; blocker age |
| Experts accept work they cannot finish on time | Expert-confirmed hours, earliest start, time zone, due date, confirmation date | The brief needs four hours this week; the expert has two. Reduce scope or offer another task | On-time submissions per accepted assignment |
| Repeated screening drives people away | Assessment ID, task family, rubric version, result, evidence date, permitted reuse | A consultant passed the same pricing assessment last month. Reuse it if the new requirements and validity rule match | Repeat assessments avoided; time to qualify |
| Review scores do not explain failure | Rubric criterion, evidence excerpt, reviewer, rubric version, revision reason | A scenario has sound reasoning but lacks an answer key. Request that specific revision | First-pass acceptance; revision cycles; reviewer agreement |
| A polished sample hides unsupported reasoning | Task-packet version, tool orientation, source checks, corrected claims, evaluator notes | A lawyer produces a fluent answer but cannot support one conclusion. Ask for the source check and record what was not observed | Evidence-supported rubric decisions; later production acceptance |
| An expert disappears after one good task | Accepted artifact ID, review delay, payment due/paid status, dispute, next suitable offer | Work was accepted, but payment is overdue. Resolve payment before sending a generic reactivation message | Payment timeliness; mature-cohort repeat contribution rate |
| A good expert has no second contribution | Matching opportunities offered, response, availability, capacity, reason for pause | No suitable task was offered. Record a demand gap rather than a rejection by the expert | Repeat offers per eligible expert; repeat acceptance per offer |
| You keep funding the wrong source | Source touches, recruiting cost, expert ID, accepted work and later repeat work | A source brings many replies but few accepted artifacts. Inspect task mix and qualification before increasing its budget | Cost per activated expert and per retained contributor |

Registration supports a credential check. It does not prove skill, availability or permission to contribute. Keep confidential client details out of project evidence. Ask for public or anonymized examples.

### Start with these five additions

- Save one task-specific evidence note and its source for every qualification decision.
- Save the exact offer and the expert's stated reason for accepting, declining or waiting.
- Give every onboarding blocker an owner and a review time.
- Save review reasons against a versioned rubric and artifact.
- Join accepted work to payment status, suitable repeat offers and later accepted work.

These priorities are an implementation recommendation for the five-expert pilot. They are not a statistically validated ranking. Firm prestige, email opens and profile completeness should not become substitutes for accepted work.

### Why these are good starting points

GC AI's October 27 guide proposes realistic synthetic work samples with consistent instructions and evidence-based human review. For legal contributors, save the source checks and reasons for corrections. Keep not observed separate from failed. The guide does not validate a total-score hiring cutoff. Adapt the exercise to the actual contribution task. [GC AI assessment guide](https://gc.ai/blog/ai-fluency-assessment-hiring-in-house-counsel)

Umbrex's expert-network guide distinguishes relevant experience, recency, perspective, availability and rate fit. Record what the person actually did: buyer, operator, implementer or adviser. An industry label alone cannot make that distinction. [Umbrex screening guide](https://umbrex.com/resources/paid-for-your-perspective-how-to-make-money-through-expert-networks/screening-calls-and-compliance-checks/)

On November 2, 2026, Upwork introduced an availability signal for experts ready to start work. This is a recent example of treating readiness as separate data. It does not establish a target response time or conversion rate for this program. [Upwork announcement](https://upwork.gcs-web.com/node/13381/pdf)

Mercor's assessment guide describes reusable skill evidence and role-specific scoring. Apply the same principle here: retain the assessment and rubric version, then check whether reuse is valid for the next task. [Mercor assessments](https://talent.docs.mercor.com/how-to/assessments.md)

Mercor's work-trial guide separates prerequisites, acceptance, submission and payment. Its Active status begins at offer acceptance. Our activation measure still requires accepted production work. [Mercor work trials](https://talent.docs.mercor.com/how-to/work-trial.md)

Prolific explains that task duration, effort and the population being recruited affect appropriate compensation. Record estimated and actual effort to identify a poor offer. Its general participant rates are not a rate card for lawyers or consultants. [Prolific payment model, July 17, 2026](https://researcher-help.prolific.com/en/articles/445230-prolific-s-payment-model)

These sources support the design choices. They do not establish that these fields will improve retention in this business. Test that with your own expert outcomes.

### Follow one expert through the data

Expert C is a synthetic consultant with relevant pricing experience and an approved sample. Their record moves from qualified to interested when they accept the documented offer.

They cannot start because task access is missing. The onboarding Play returns waiting, with access as the blocker and expert ops as the owner. It does not send another recruitment email.

After access is restored, they submit a scenario. The reviewer requests an answer key. The record retains the reason and the revised artifact. Activation occurs only when production work is accepted.

Before the next invitation, the relationship Play checks payment, available hours and matching demand. A later accepted contribution can establish retention under the defined observation window.

### Give the coding agent a field contract

For every decision field, store its source, observation time and status: confirmed, self-reported, unknown or disputed. Keep the original evidence separate from the agent's interpretation. Make validity periods explicit.

```json
{
  "expertId": "synthetic-expert-c",
  "taskFamily": "pricing-scenario",
  "fit": {
    "status": "human-approved",
    "rubricVersion": "pricing-v1",
    "evidenceRef": "synthetic-sample-c-01",
    "reviewedAt": "2026-11-20T15:00:00Z"
  },
  "availability": {"hoursThisWeek": 4, "status": "self-reported"},
  "state": "waiting",
  "blocker": {
    "code": "task_access_missing",
    "owner": "expert-ops",
    "reviewAt": "2026-11-23T15:00:00Z"
  },
  "nextAction": "restore_access",
  "synthetic": true
}
```

First implement rules that explain reviewed cases. Keep a reason and evidence reference with every recommendation. Compare recommendations with human decisions before allowing a new rule to take external action.

### Make the queue threshold reflect demand

The recruiting cycle counts unsuppressed research_pending, ready, contacted and onboarding candidates. Below 100, it qualifies a bounded batch and searches for more. It does not count available, task-qualified experts by specialty.

Keep that existing rule visible. Add a separate proposed coverage check: for each funded task family, count distinct qualified experts who are available and have no unresolved prerequisites. Exclude declined, suppressed, already committed and stale records as the operating rules require.

Do not invent a conversion rate from five people. Initially, compare available expert-hours with planned task-hours and review gaps manually. Once outcomes accumulate, use observed conversion and completion rates to set recruiting targets.

For retention analysis, report both repeat contribution and opportunity coverage. An expert cannot accept a second suitable task that you never offered. Compare sources and rubrics within similar task types and mature cohorts; correlation alone does not prove a cause.
