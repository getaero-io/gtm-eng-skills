# Research and source plan

This example combines structured profile search with task-specific evidence and human review. The [detailed research notes](editorial/RECRUITMENT-RESEARCH.md) preserve the dated source review, route contracts, coverage limits and illustrative costs. They are design research, not live performance claims. Recheck contracts and prices before a paid run.

## Public sources

| Source | Useful evidence | Limits |
|---|---|---|
| [NYS attorney registrations](https://data.ny.gov/Transparency/NYS-Attorney-Registrations/eqw2-r5nb) | Registration number, identity, jurisdiction/status | Not proof of specialty, willingness, availability or task ability |
| [IMC directory](https://www.imcusa.org/member-directory/) | Consultant profile leads | Membership is not a census of consulting practitioners |
| Firm bios, publications and public project descriptions | Work owned, specialty and recency | Resolve identity and avoid confidential client material |
| [Census CBP](https://api.census.gov/data/2023/cbp.html) | Establishments by geography/industry | Market context, not available expert count |
| [BLS QCEW](https://www.bls.gov/cew/) | Employment and industry context | Aggregate counts cannot become a contact list |
| [Mercor assessments](https://talent.docs.mercor.com/how-to/assessments.md) | Reusable skill evidence and role-specific evaluation | Do not import another platform's acceptance rules |
| [GC AI assessment guide](https://gc.ai/blog/ai-fluency-assessment-hiring-in-house-counsel) | Realistic work samples, source checks and human review | Not a validated total-score cutoff for this network |
| [Umbrex screening guide](https://umbrex.com/resources/paid-for-your-perspective-how-to-make-money-through-expert-networks/screening-calls-and-compliance-checks/) | Relevance, recency, perspective, availability and rate fit | Design guidance, not measured conversion lift |

Attorney data artifact: `https://data.ny.gov/api/views/eqw2-r5nb/rows.tsv`. QCEW industry slices for law and consulting use NAICS 541110 and 541611. Keep area/year/ownership keys when joining statistics. Bulk retrieval and parser success must be verified independently before ingestion.

Professional-task benchmarks inform the task/rubric structure. Do not copy benchmark content into production datasets without checking its license. All fixtures here are fictional. Community accounts of unclear tasks, delays and payment friction are hypotheses for instrumentation, not verified prevalence.

## Tools and cost model

The implemented recruiting flow uses `search_contact`, profile/email prebuilt Plays and Lemlist. Proposed research adapters include web search, Exa content extraction, public registry checks and warehouse queries. Customer DB stores workflow evidence; it does not manufacture missing platform data.

Choose structured search for a known employer and role, registries for identity/registration, and web research for relevant experience. Then use an actual sample and domain review for task fit. No provider establishes consent or availability from a profile alone.

Estimate cost from returned profiles, billable search results, extracted pages, email lookups, retries and platform charges. Cap each Play and test a small representative batch. Retain unknown coverage as unknown. Do not treat historical catalog estimates in the research notes as a current quote.

## How this artifact was built

1. Defined expert, opportunity, task, submission, review, usage and relationship records.
2. Reviewed public sources and reusable provider contracts; separated identity evidence from task skill.
3. Created synthetic CSVs where private platform data was unavailable.
4. Built seven scalar lifecycle transitions and a parent with explicit state and durable input/output history.
5. Added bounded sourcing, current-role/email qualification, suppression checks and paused-campaign enrollment.
6. Added replay, concurrency, ambiguous-write and metric tests.
7. Documented the gaps: real events, task-fit review, payments, sending and repeat-work engagement.

Production priority: one funded task, five experts, explicit evidence and human decisions. Compare downstream accepted work and repeat participation before scaling sources or automating new decisions.
