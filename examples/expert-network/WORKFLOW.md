# Complete expert operations workflow

The product's main object is the expert relationship. A CRM stage is one view of it. The richer record contains expertise with evidence, preferences, availability, permissions, task history, rubric feedback, revisions, usage and outstanding commitments. A great recruiter should see what an expert can help create; a project lead should see what recruiting promised them.

| Step | Work and evidence | Tool/source plan | Demo behavior | Owner and proposed timing |
|---|---|---|---|---|
| Define demand | World, scenario gaps, required specialty, deliverable, rubric, budget and capacity | Product backlog, approved project brief | tasks.csv | World designer: before sourcing |
| Build pools | Lawyer practice areas/jurisdictions; consultant function/industry and firsthand experience | NYS registry, firm bios, IMC directory, search_contact | experts.csv source reference | Research ops: per approved brief |
| Resolve identity | Match source identities; retain uncertain matches | Registration number + jurisdiction; verified profile URL; human review | discover child | Research ops: before recruiting |
| Enrich expertise | Evidence of work owned, authored publications, relevant projects, current availability | search_contact, serper_google_search, exa_contents; self-report later | specialty and evidence fields | Research ops: before shortlist |
| Qualify | Domain lead checks expertise and fit with the specific creation task | Evidence packet and human decision | qualify child reads decision | Domain lead: before invitation |
| Reach out | Explain the actual work, expectations, review process and approved compensation | Human-approved channel; CRM/suppression records | Recommendation only, no email draft or send | Recruiter: after approved shortlist |
| Capture response | Interest, questions, preferred channel, opt-out, referrals | Consent form and reply events | recruit child | Recruiter: when a response arrives |
| Onboard | Agreement, conflicts/confidentiality review, orientation, availability and support | Existing onboarding UI, e-sign and platform events | onboard child reads supplied booleans | Expert ops: before work access |
| Assess readiness | Use a representative practice task and explain rubric feedback | Platform task submission and reviewer | Represented by supplied training completion; no automatic score gate | Domain reviewer: before first production task |
| Match opportunity | Specialty, domain, availability, task scope and expert choice | ERM joins task backlog and capacity | match child; requires supplied approval | Project lead: each task |
| Create world/task | Expert supplies context, roles, tools, constraints, branches, evidence, reference result and rubric | Existing authoring tools; scenario/task CSV placeholder | tasks.csv stores a minimal fictional brief | Expert: agreed assignment deadline |
| Review and revise | Reviewer accepts, asks for revision, or requests clarification; preserve versions | Human rubric review; platform artifacts | review child; revision becomes waiting | Reviewer: proposed one business day after submission |
| Observe use | Link accepted tasks to evaluations, usage, abandonment and feedback | world_model_usage_data.csv now; warehouse/API later | learn child joins taskId + worldId | Data ops: after use is recorded |
| Maintain relationship | Discuss new matches, support issues, preferences and changing availability | ERM evidence, support/call history, CRM summary | Recommended next action; no auto-send or global reputation score | Relationship owner: after review or new evidence |
| Settle and retain | Reconcile accepted work with agreed pay; invite further work only when appropriate | Future ledger/payment system and preferences | No payment executed; no inferred rate | Finance/ops: agreed payment terms |
| Pause or exit | Honor declined work and unresolved prerequisites; preserve reason | Human decision, suppression and access policy | waiting or declined terminal episode | Expert ops: on request/event |

Timings are proposed operating defaults, not commitments made to any expert.

## Lawyer example

Alex Example is a fictional commercial-contract specialist. The supplied human reviews approve identity, qualification and onboarding. An approved three-hour fictional negotiation task fits six hours of availability. A reviewer accepts the submission. The engine joins 12 synthetic accepted uses, two abandonment events and qualitative feedback, then recommends discussing the next matching brief. A registration record alone would never establish this creative ability.

## Consultant example

Morgan Example is a fictional pricing-strategy consultant. The same flow reaches a SaaS pricing case, but its review asks for revision. The episode stops with a recommendation for the expert and reviewer to clarify the rubric and revise. Firm prestige does not override the review. Later evidence can start another immutable episode.

## Data that should eventually replace the CSVs

| Fixture | Production owner | Stable keys | Capture |
|---|---|---|---|
| experts.csv | Acquisition + expert ops | expertId, verified source identities | Evidence, specialty, interest, consent, availability, approvals |
| tasks.csv | World creation + reviewers | taskId, worldId, submissionId, reviewerId | Versioned briefs, rubrics, artifact links, review outcomes, revision count |
| world_model_usage_data.csv | Platform analytics | eventId, taskId, worldId | Usage timestamp/window, outcomes, abandonment, evaluator feedback |
| Future compensation ledger | Finance | expertId, assignmentId, paymentId | Agreed rate, payable amount, settlement status |
| Future support/preferences | Expert success | expertId, caseId | Friction, preferences, commitments, resolution |

Production should separate these entities and join them on demand. The demo's immutable JSON snapshot deliberately makes the entire evidence trail easy to reproduce. Login volume is not treated as expertise, and missing usage is not treated as poor quality.
