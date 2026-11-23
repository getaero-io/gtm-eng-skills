# Research: data that improves expert recruitment

Archived design research. Provider prices and availability below are historical observations, not a current quote. No customer records or private receipts are included. See [the public source plan](../RESEARCH.md) for the reusable summary.

Reviewed November 22, 2026. Scope: lawyers and management consultants who create paid scenarios, tasks and evaluations. The decision is which data to collect and which action it should change. This is a source plan and proposed design, not a new live recruiting run.

## Recent evidence and research limits

The requested 30-day window ends November 22, 2026. Verified in-window guidance includes GC AI's October 27 work-sample assessment guide and Upwork's November 2 availability announcement. The NYS registry catalog was updated November 18. Other directly useful screening and onboarding guidance is undated or older, and is labeled accordingly.

The installed Last30Days v3.28.0 engine was run with a host-written query plan, resolved communities, a 30-day window and the explicit November 22 end date. The installed version was retained; upstream tags now include v4.6.0. The runtime was Python 3.14, and existing setup was complete.

The quick run selected Reddit, YouTube and grounding after runtime configuration. Direct Reddit requests encountered HTTP 403; an archive fallback recovered candidates. Six videos were found outside the requested date range, and quick depth did not retrieve transcripts. The run did not return a report after more than eight minutes and was terminated. It emitted no completed evidence report, footer or saved raw artifact. No candidate snippets from that incomplete run support this guide.

Therefore, this is not a verified last-30-days community consensus. The recommendations rely on the linked primary and practitioner sources. Public search was also used to resolve communities and datasets. The engine's configured source list is not reported as executed coverage. No Deepline paid enrichment was run; any direct research-provider charges from the engine are outside the Deepline estimates and were not measured.

## What the evidence supports

Prioritize task-specific evidence, current readiness, clear offers and the experience after submission. Public profiles help discover people. Private outcomes are needed to learn who produces useful work and returns.

A particularly relevant recent tip: evaluate the reasoning behind a sample, using a consistent synthetic packet. GC AI's October 27 guide recommends source verification and human evaluation, distinguishes unobserved behavior from failure, and warns against an unvalidated total-score cutoff. This is vendor guidance for counsel hiring, adapted here to contributor qualification; it is not outcome-validation research. [GC AI](https://gc.ai/blog/ai-fluency-assessment-hiring-in-house-counsel)

1. Separate expertise from readiness. Upwork's November 2 announcement adds a signal for freelancers ready to start. This is current-window product evidence, not an independent test of improved retention. [Upwork](https://upwork.gcs-web.com/node/13381/pdf)
2. Save the person's actual perspective. Umbrex distinguishes buyer, operator, implementer and adviser, alongside recency, availability and rate fit. This undated practitioner guide is closely matched to management-consultant recruitment. [Umbrex](https://umbrex.com/resources/paid-for-your-perspective-how-to-make-money-through-expert-networks/screening-calls-and-compliance-checks/)
3. Reuse relevant qualification evidence. Mercor describes assessments that can apply to multiple opportunities. Keep scope and rubric versions so reuse does not become permanent blanket approval. [Mercor assessments](https://talent.docs.mercor.com/how-to/assessments.md)
4. Record the exact onboarding failure. Mercor separates documents, payment setup, acceptance and submission. Use prerequisite-level records rather than one onboarding-complete flag. [Mercor work trials](https://talent.docs.mercor.com/how-to/work-trial.md)
5. Check the offer and payment experience. Prolific explains why effort and participant population affect compensation; Mercor separates payment approval from receipt. These sources support collecting the data, not importing their rates or promising their timelines. [Prolific](https://researcher-help.prolific.com/en/articles/445230-prolific-s-payment-model) and [Mercor payments](https://talent.docs.mercor.com/how-to/payments.md)

These recommendations are ranked by relevance to the pilot, evidence quality and the action they enable. No causal lift or validated scoring weights have been established for this program.

## Ranked source map

| Rank | Source | Classification | Fields and join | Decision supported | Limitation |
|---|---|---|---|---|---|
| 1 | Your task briefs, samples and human reviews | Private connector/customer CSV | expertId + taskId + artifactId; rubric version and reasons | Match the right person to a specific task | No production outcome feed connected in this example |
| 2 | Expert-confirmed preferences and readiness | Private connector/customer CSV | expertId; hours, start date, rate, preferred task types, confirmation time | Offer work they can accept now | Self-reported; refresh when demand or availability changes |
| 3 | Your assignments, payment and repeat-offer events | Private connector/customer CSV | expertId + assignmentId + paymentId + eventId | Fix blockers and explain repeat participation | Payment status is not proof of why someone left |
| 4 | Public project evidence and firm biographies | Available through generic route | canonical profile URL; project facts, role, source, observed date | Target research and ask about missing evidence | Promotional, incomplete and potentially stale |
| 5 | NYS attorney registration records | Available through generic route | jurisdiction + registration number; status and checked date | Corroborate identity and required credentials | Does not establish practice specialty, willingness or quality |
| 6 | IMC consultant directory | Available through generic route | profile URL, consulting specialty, location | Discover additional candidates | Membership bias; no verified bulk API |
| 7 | Lemlist campaign events and actual replies | Private connector | campaignId + contact ID mapped to expertId | Stop after decline; diagnose offer objections | Opens alone do not establish interest |
| 8 | Expert community discussions | Native | post/comment URL, timestamp, exact phrase | Generate questions and identify friction hypotheses | Anecdotes; do not attach opinions to individual candidates |
| 9 | BLS QCEW and Census CBP | Available through generic route | NAICS + geography + period | Size industry coverage if geographic sourcing expands | Counts of establishments are not counts of available experts |

Search your known pool and prior assessments before acquiring more contacts. This is a proposed operating rule; the current refill Play does not implement the full fit-and-readiness model.

## Exact public artifacts

| Source | Exact artifact | Mirror or catalog | Parser and compatibility | Statistical context |
|---|---|---|---|---|
| NYS Attorney Registrations | Dataset eqw2-r5nb: [CSV export](https://data.ny.gov/api/v3/views/eqw2-r5nb/export.csv?accessType=DOWNLOAD), [JSON export](https://data.ny.gov/api/v3/views/eqw2-r5nb/query.json?accessType=DOWNLOAD), [columns](https://data.ny.gov/api/views/eqw2-r5nb/columns.json) | [data.gov catalog](https://catalog.data.gov/dataset/nys-attorney-registrations), updated Nov 18, 2026 | [R cleaning notebook](https://github.com/irworkshop/accountability_datacleaning/blob/master/state/ny/attorneys/docs/ny_attorneys_diary.md) consumes the older rows.tsv export. It is not a drop-in parser for v3 CSV | QCEW/CBP NAICS 541110, Offices of Lawyers |
| IMC USA | [Public directory HTML](https://www.imcusa.org/directories/all-users/) and [search guide](https://www.imcusa.org/imc-usa-consultant-directory-user-guide/) | No separate mirror verified | No documented bulk endpoint or dedicated parser found in targeted searches | 541611 covers administrative/general management consulting, not every consulting specialty |
| BLS QCEW | [2026_qtrly_by_industry.zip](https://data.bls.gov/cew/data/files/2026/csv/2026_qtrly_by_industry.zip); [2025_annual_by_industry.zip](https://data.bls.gov/cew/data/files/2025/csv/2025_annual_by_industry.zip) | [Official download index](https://www.bls.gov/cew/downloadable-data-files.htm) | [Official code samples](https://www.bls.gov/cew/additional-resources/open-data/sample-code.htm#RSCRIPT) read industry CSV slices, not ZIP files directly. ZIP links verified; contents not inspected | [NAICS hierarchy](https://www.bls.gov/cew/classifications/industry/qcew-naics-hierarchy-crosswalk.htm): 541110 and 541611 |
| Census CBP | [2023 CBP API dataset](https://api.census.gov/data/2023/cbp), [variables](https://api.census.gov/data/2023/cbp/variables.html), [examples](https://api.census.gov/data/2023/cbp/examples.html) | [Official API guide](https://www.census.gov/data/developers/data-sets/cbp-zbp/cbp-api.html) | [tinycensus](https://github.com/christopherkenny/tinycensus/blob/main/README.md) documents tc_get_cbp for the API. Follow current Census key requirements over stale wrapper guidance | Establishments with paid employees; use NAICS and geography, not person joins |

The IMC [competency framework approved October 29, 2026](https://www.imcusa.org/wp-content/uploads/2026/10/IMC_USA_CMC_Summary_Common_Body_of_Knowledge_20261029-Appvd.pdf) explicitly retains the substance of the 2021 framework. Its new publication date is not evidence of a new recruiting practice.

## Language and proprietary data to retain

| Evidence | Preserve | Proposed action |
|---|---|---|
| Expert says the deadline is too short | Exact reply, deadline, availability and offer version | Offer a later slot if one exists |
| Expert says the topic is outside their experience | Exact reply and the specific task requirement | Revise the fit record and search criteria |
| Expert says the first payment is missing | Reply, payment reference, due date and verified status | Reconcile payment with its owner |
| Expert completed a relevant assessment | Assessment ID, permitted reuse scope, rubric version and date | Reuse it where valid; ask only for missing evidence |
| Expert produced accepted work but received no further offer | Accepted artifact, matching demand and offer history | Fix opportunity coverage before interpreting inactivity |

The reply examples are synthetic. Preserve real wording when collected, then store a separate normalized reason. Do not generate project-specific praise without supporting evidence. Store only necessary status and references for payment and identity checks, not bank details or identity documents in the ERM table.

## Live Deepline contracts inspected

The following IDs and prices were inspected on November 22. Inspection did not execute the providers.

| Route | Input and useful output | Classification | Customer-visible cost | Important constraint |
|---|---|---|---|---|
| exa_search | query, date/domain filters; results with URL, title and optional text/date | Native search for generic public sources | auto search: 0.098 credits per request up to 10 results, total rounded up to 0.01 | Search publication dates may be missing; do not infer freshness from crawl date |
| exa_contents | URLs; page text, highlights or summaries in rawV2.results | Native extraction for generic public sources | 0.014 credits per returned text/highlight set/summary per page, summed then rounded up to 0.01 | Text plus summary incurs both charges; check person identity and preserve source |
| findymail_find_from_business_profile | linkedin_url; email, full_name and company_domain | Native | 0.28 credits per result | Optional webhook makes it asynchronous; returned email does not establish task fit or permission to contact |
| scrapecreators_reddit_search | query, timeframe, sort; posts with source and engagement | Native | 0.02 credits per call | Pagination adds calls; thread opinions are not verified professional facts |
| hackernews_search | query, sort, numericFilters; discussion hits | Native | Free | Weak fit for many lawyer/consultant operations questions |
| generic_http_request | GET URL and query; status and response data in rawV2 | Available through generic route | Free in Deepline | Registry/API limits and external terms still apply; no paid API access included |
| query_customer_db | scoped SELECT; rows | Private connector/customer DB | Free; catalog rate limit 100 requests/second | Tool also supports writes; research queries should remain read-only |
| lemlist_add_webhook | campaign_id, target_url, event type; webhook result | Private connector | Free in Deepline | Creates a subscription; not executed here. Receiver needs event deduplication and expert identity mapping |

Managed access was available for the described routes. Separate user-key connections may be required for BYOK; do not assume the same credit basis. The catalog did not state rate limits for most read routes. A production Play must handle provider errors and retries and retain run receipts.

The dedicated planning endpoint could not be called through the documented environment because DEEPLINE_API_BASE_URL and DEEPLINE_API_KEY were absent. CLI authentication and catalog inspection worked. No credentials were copied from another source to bypass that gap.

## Coverage and gaps

| Family | Status for this job |
|---|---|
| Web, news and URL extraction | Live public search and primary-page review completed; native catalog routes described |
| Public registries and dataset leads | Exact NYS, IMC, QCEW and CBP artifacts resolved; generic route |
| People/contact | Native email route described; no new people enriched |
| Company/account | Existing role/firm context and public bios identified; no company-wide paid enrichment needed |
| Community and custom language | Public discussion leads found; Last30Days run incomplete. No recent-community conclusion claimed |
| Video/transcript | Engine video coverage documented in the run note; quick depth did not fetch transcripts |
| Prediction/community ranking | Not a reliable measure of expert task fit; no actionable market signal used |
| Jobs/hiring/funding/technographics | Public role descriptions can clarify requirements; firm funding and technology stacks are low priority here |
| CRM/private sources | Expert and campaign joins specified; no new private recruiting queries or connector writes |
| Warehouse/product/workflow | Use existing synthetic CSV contracts until real event adapters exist |
| X, TikTok, Instagram and other social sources | Availability diagnostics are not proof they ran. Use the run note's actual coverage, not the configured source list |
| Missing integration | Forms/e-sign, project submissions, reviewer events and payment status still need authorized adapters and stable IDs |

## First workflow and cost

Start with one real task brief and five reviewed expert records. Retrieve prior evidence, identify missing requirements, research only those gaps and ask the expert to confirm readiness. Return a recommendation with reasons. Then join assignment, review, payment and repeat-offer events.

For the five-record pilot, a proposed retrieval bundle is one auto web search, text extraction from two pages and at most one successful work-email lookup per expert. Add three shared Reddit searches for friction research. Estimated Deepline cost: 5 × (0.10 + 0.03 + 0.28) + 3 × 0.02 = 2.11 credits. At 100 records with the same shape: 41.06 credits. These are estimates from current contracts, not quotes for the entire engine.

The estimates exclude profile enrichment, LLM scoring, retries, extra pages, human review, compensation and external subscriptions. Coverage has not been probed. This turn ran no paid Deepline enrichment. A full cost-unknown run is not authorized by this source plan; agree its scope and hard cap before execution.

For the first five experts, use descriptive counts and inspect each exception. After enough mature outcomes exist, compare qualification decisions and source costs with accepted work and repeat contributions within similar task families. Keep the business objective: maximize activated and retained experts.
