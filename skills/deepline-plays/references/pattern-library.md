# Pattern library

## Winner-take-all topology forced redundant provider work

**Observed failure:** a company-research Play made every candidate topology
prove every requested field. The official-page route was good for ICP, the
registry route was good for officers, and the jobs route was good for hiring,
but each was scored as a failed whole-row strategy. The agent then paid every
source for every row and still could not exploit the complementary evidence.

**Guard:** compare and select **actions**, not whole providers. An action card
states a claim set, source family, correlation group, terminal/lead evidence
mode, cost ceiling, and falsifiable hypothesis. After each result, bind and
evaluate the affected claim, record the outcome, and re-plan the next action.
The final row still needs every required claim; no individual action does.

## Repeated provider retries masqueraded as exploration

**Observed failure:** after a people database missed a local-business operator,
the agent changed title terms and called the same corpus repeatedly. Each retry
looked like a new strategy in prose but generated nearly identical evidence and
consumed the pilot budget.

**Guard:** group cards by underlying source correlation, not vendor name. The
portfolio controller excludes an already attempted exact action for a row and
exponentially discounts additional actions from the same correlation group. A
real registry, official page, public current-role validator, or private join is
an independent action. Change the source family or the causal evidence
mechanism before spending again.

## Global provider statistics contaminated a local phenotype

**Observed failure:** an agent used good enterprise-SaaS people-search results
as evidence that the same provider would find operator titles at small regional
fuel distributors. The model over-exploited a source whose coverage mechanism
did not transfer to the present entity class.

**Guard:** store strategy memory only as aggregate verified-claim,
materialized-lead-artifact, and attempted-claim counts keyed by a non-secret
task phenotype. Pool only an exact
phenotype or an explicit `*` prior. The current run's receipts dominate the
weak Beta prior; raw customer rows, domains, prompts, evidence, identities, and
provider costs never enter shared memory.

## Fresh-agent opening loop

**Observed failure:** a fresh agent read the entrypoint, three long guides,
and several unrelated examples before it authored a Play or retrieved a row.
It then exhausted its useful time in catalog exploration.

**Guard:** the entrypoint creates a local scaffold first and allows one catalog
search plus two tool descriptions before the first `plays check`. The agent
only opens a deeper reference in response to a concrete branch or compiler/run
failure.

## Public route that never really ran

**Observed failure:** a route was labelled public but its adapter was inferred
from a remembered tool result. It errored, contributed no evaluable rows, and
the structured route was selected as if public coverage were zero.

**Guard:** an adapter card names the literal ID, confirmed result path, source
URL/text fields, and price. An error excludes the route from selection; repair
or replace it on a pilot row before promotion.

## Narrow first-pass people lookup

**Observed failure:** a people provider was limited to one result and public
search was constrained to LinkedIn. Both choices hid candidates that would
have passed a company/title gate.

**Guard:** materialize 3–5 structured candidates, then gate them. Search the
company and role family broadly first; use a distinct source for current-role
verification.

## Related-person verification merge

**Observed failure:** a SERP result for one RevOps leader mentioned another
leader in its related-people snippet. A surname-only verifier treated that as
evidence for the candidate and emitted the wrong verification URL.

**Guard:** require the candidate's full normalized name in verification text.
If the result title carries an accepted role but names someone else, reject it.

## Generic company-claim cold start

**Observed failure:** a fresh agent opening generic company research read a
large fixture and sprayed catalog searches before it made its first retrieval.
It then built the same public-search → official-page → gap-only follow-up
topology from scratch.

**Guard:** start from the shared research-experiment compiler and write the
claim contracts beside the task-local provider adapters. Make one broad official
pass, evaluate the actual gaps, and then run one claim-family supplemental pass
only for unresolved claims. Do not add an AI research loop or a third provider
until a measured gap needs one.

## From-scratch company list seeded from memory

**Observed failure:** a fresh agent received “find three companies from
scratch,” typed three plausible companies and domains into `pilotRows`, then
proved only that some selected pages existed. One domain was wrong and another
company was outside the requested geography, so the apparently fair route
comparison never had a valid denominator.

**Guard:** put candidate discovery inside the custom Play as a shared durable
stage. Retain the discovery artifact, canonical-domain check, core ICP and
geography gate, selected/excluded reason, and every rejected near match. Pass
only the resulting selected rows to all downstream topologies. Claim policies
remain claim-specific: first-party pages for offer/geography, leadership or
current-role sources for people, and active dated listings for hiring.

## Comparison that intentionally skips a required field

**Observed failure:** an agent made one route search official pages and a
second route search official pages differently, then wrote that the second
route “intentionally preserves” a required operator as unresolved. Neither
route performed company-scoped people retrieval, so the pilot could never
produce a shippable row.

**Guard:** every candidate topology must attempt every required claim. For a
current operator, compare an official leadership-page route against a true
company→person→current-role route. Search snippets discover candidates but do
not verify a role. An optional hiring signal may remain unresolved after its
own bounded evidence test; a required operator cannot be intentionally skipped.

## Core-ICP-only candidate promoted as a final row

**Observed failure:** a pilot correctly found three in-market fuel companies,
then ran its expensive verification routes and discovered that one had no
verified named operator. The final answer reported it anyway as a 2/3 complete
set even though the user requested an operator for every row.

**Guard:** make operator coverage a second selection gate when it is a required
field. Discover more than N, use one cheap company→person→current-role screen,
and retain `operator_unresolved` candidates as audit rows. Only the first N
with both ICP and operator proof reach hiring verification. An explicitly
optional hiring signal can remain unresolved; a required operator cannot.

## Promotion floor quietly accepts an incomplete cohort

**Observed failure:** a three-company request set the compiler floor to one
complete row. The decision artifact could therefore promote a route with only
two verified operators, and the final prose table made the shortfall look like
an acceptable abstention.

**Guard:** for N requested rows, set `minimumCompleteRows: N` and require 1.0
verified coverage over the required claim families. Make only fields the user
explicitly permits to remain unresolved non-required. An underfilled cohort is
a measured failure that triggers replacement from the durable candidate pool,
not a winner.

## Repair laundered an ineligible title through a finalizer

**Observed failure:** the experiment correctly rejected public `President`
directory entries for a request limited to owner, operations, customer-service,
or CX roles. A follow-up finalizer hard-coded those names and URLs, fetched the
pages, then presented the people as verified operators. The retrieval was
durable, but the finalizer had silently changed the semantic acceptance rule.

**Guard:** an accepted role must be explicit in the same source-bound context.
`President` alone does not mean owner or operations. Keep the original
`defineResearchExperiment` contract on every repair and require its compiled
evaluation before producing a customer row. A separate finalizer may project
already-promoted rows, never re-adjudicate rejected fields or hard-code an
inferred person/title.

## Broad people search consumed the pilot budget

**Observed failure:** after an official route missed two operators, the Play
ran a people provider for every three-row candidate with `limit: 10`. The
provider charged per returned result, producing a several-credit branch before
any individual person had been independently validated. One valid person did
not justify the blind cohort spend.

**Guard:** people retrieval is gap-only. Run cheap official staff/leadership
screening first; send only unresolved rows to the provider; request 1–3
candidates; and calculate `unresolved_rows × limit × live_per_result_credits`
before execution. Persist the expected ceiling and actual yield. If the ceiling
is over budget, narrow or abandon that route rather than treating ten raw
people as better research.

## Compiler imported but never executed

**Observed failure:** a Play imported the research compiler, declared strong
claims and a strict promotion floor, but its candidate callbacks returned empty
claims and the runtime only wrote raw provider columns. The eventual answer was
therefore based on agent interpretation rather than the compiler's decision.

**Guard:** a topology callback performs row-scoped retrieval and returns a real
`CandidateOutcome`; the Play materializes `experiment.evaluate(...)` results;
and customer rows derive only from a promoted compiled evaluation. An unused
compiler import or `{ claims: {} }` candidate is a design failure, not partial
coverage.

## Compound claim counted as two sources

**Observed failure:** an agent required two evidence items for one ICP claim,
then supplied one official sentence that stated both fuel offer and service
area. The compiler correctly rejected the claim because `minimumEvidence: 2`
is an item count, not a fact count.

**Guard:** use one evidence item with an explicit semantic acceptance check for
a compound statement, or split the facts into distinct claims. An authoritative
source can satisfy independence policy but never bypasses an absolute minimum
evidence-item count.

## Post-run browser repair

**Observed failure:** an agent ran a durable in-Play discovery stage, then used
browser search to find operator names and official pages, reporting a polished
three-row answer without a row-producing Play run. The facts could not be
replayed, scored, or attributed to the selected topology.

**Guard:** a discovery Play is only a selection artifact. Freeze its selected
rows into a complete experiment Play, fetch every final evidence source through
literal Play tool calls, and project the answer strictly from the completed
datasets. Do not cite a browser result in a customer row. If the full Play has
not established a required fact, leave it unresolved.

## Renamed duplicate topology

**Observed failure:** two candidates had different names but both called the
same first-party helper with the same literal tool IDs. They collided at runtime
when run concurrently, and even after sequential repair they did not compare
two mechanisms or attempt a people-search route.

**Guard:** give every candidate a named route-specific adapter accepting
`rowCtx`, use unique literal tool/checkpoint IDs, and inspect the callback code
before `plays check`. A required operator comparison needs a company-scoped
people retrieval plus a separate current-role verification route, not a second
label for official-page search.

## Direct-database debug escape

**Observed failure:** after a Play completed, an agent issued a direct database
query to inspect runtime rows. That bypassed the durable run boundary and could
have depended on mutable customer state.

**Guard:** use only run get/logs/export for Play diagnosis. An absent field in
those artifacts is an observability issue to record, not authorization to query
the database directly.

## Delivery check poisoning a valid run

**Observed failure:** a run had complete, grounded artifacts but its final
reporting step used a locale-default CSV parser on UTF-8 data and `git status`
in an eval workdir that was not a repository. The task then appeared to fail.

**Guard:** validate exported CSV/JSON with Python and explicit UTF-8. Treat
the eval workdir as a plain directory, not a checkout. Keep validation separate
from retrieval so an artifact-check problem is loud and repairable.

## Historical-event and customer-list selection

**Observed failure:** broad public research found relevant official pages but
gave the user a later deal for a requested historical event, and a customer
directory instead of selected customer case studies. Both outputs looked
plausible while answering a weaker question than the one asked.

**Guard:** a dated event needs the primary document to state the requested time
and event. A request for _N_ examples needs _N_ individual first-party pages;
directories and search results are discovery artifacts only. Collapse candidate
lists to the evidence-supported answer, and turn a bounded negative search into
an explicit abstention.

## Firecrawl JSON input literal widening

**Observed failure:** an agent adapted a working research kernel and its first
`plays check` rejected the Firecrawl `formats` object because TypeScript widened
`type: 'json'` to `string`. The retrieval code was otherwise valid.

**Guard:** keep the deep Firecrawl input constructor as a narrowly scoped
`function scrapeInput(...): any`. That isolates provider-schema drift without
loosening the typed input rows, dataset records, or output contract.

## Duplicate active run

**Observed failure:** an agent read `running` from a real Play and submitted
the same source and input again before the first run reached a terminal state.
The second run was unnecessary provider work and blurred which artifact was
authoritative.

**Guard:** one checked source/input gets one `plays run`. While it is active,
inspect that exact run or keep `--watch` open. A new run requires a material
source or input change and an explicit note of why the old run could not answer
the task.

## Dated but non-event account evidence

**Observed failure:** a broader account-signal search selected a dated customer
review. It named the account and contained a date, so a loose identity/date
gate admitted it as a risk signal even though it was not company-level news.

**Guard:** discover first-party newsroom pages first. Before fetching a broader
candidate, require both the target-company name and event language in its
search artifact. The page extractor must return a permitted event category plus
a separate target-company identity excerpt. Reject reviews, individual
complaints, directories, job listings, and generic profile pages even when
they are dated.

## Post-run factual repair

**Observed failure:** a fresh agent found real evidence in a completed Play's
export but the event description field held the wrong extraction value. It
rewrote the local answer CSV after the run, producing a prettier score without
a replayable Play output.

**Guard:** an answer CSV is a projection of durable datasets, not a place to
repair factual rows. Keep local work to column renames, evidence joins, and
static metadata. Fix the extractor/selection source, re-check, and re-run the
changed Play; record that reason with the new run ID.

## Low-value official page outranking product evidence

**Observed failure:** an official-domain search returned contact and legal
pages above a product page. The extractor produced technically attributable
but useless buyer and market-language claims.

**Guard:** score first-party candidates before fetching. Prefer product,
platform, solutions, customer, or use-case pages; strongly reject contact,
legal, privacy, terms, login, careers, and docs. When no page clears that
gate, fetch the official home page rather than accepting a low-value result.

## Homepage treated as the stable-data source

**Observed failure:** a strict public-company probe used a valid first-party
homepage for offering, buyer, and market language. The offer passed, but the
homepage did not contain an admissible buyer or market claim, so both otherwise
different topologies tied at low coverage. This was a source-plan flaw, not a
reason to relax raw evidence or semantic gates.

**Guard:** evaluate the first pass with `getResearchClaimGaps(...)`. For the
remaining IDs only, have the agent discover one first-party claim-family page
(product/platform, solution/use case, or industry/category as appropriate),
apply the returned final URL policy, then use
`fillResearchClaimGaps(...)`. A verified homepage claim is preserved; a
nonempty social-proof or paraphrased extractor field is still a gap.

## Generated table name overflow

**Observed failure:** a provider-free verification Play passed TypeScript but
failed `plays check` because the normalized Play name plus dataset name was 65
characters, above the 63-character storage-table limit.

**Guard:** give fixture and long research Plays short semantic names before the
first check. The dataset can retain its descriptive name when the combined
normalized identifier stays under the limit; otherwise shorten the Play name,
not the evidence contract.

## Stale candidate replay after a semantic edit

**Observed failure:** an agent tightened a candidate's evidence binder, then
ran the same five-row pilot. The Play completed quickly but `rowCtx.step(...)`
reused completed candidate work because the checkpoint IDs were unchanged.
The score still reflected the old binder, not the revised source.

**Guard:** write a visible semantic policy revision in the Play. On every
source query, extractor schema, evidence gate, claim-acceptance, or source
policy change, give each changed candidate a new literal checkpoint ID that
includes that revision. Put the revision in scorecard and decision artifacts.
This reruns the adapter code while allowing identical underlying provider calls
to reuse their cache safely. Keep the normalized checkpoint ID below 63
characters because it becomes a durable runtime key.
