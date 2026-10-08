---
name: deepline-gtm
description: "GTM prospecting, enrichment, outreach, and Deepline Play work/audits. Providers: adyntel,affinity,ai_ark,akta,allegrow,amplemarket,apify,attention,attio,aviato,bettercontact,bigquery,bluesky,bounceban,brave,browserbase,builtwith,cbinsights,clay,clickhouse,cloudflare,contactout,contextdev,crustdata-v3,customer_db,databricks,dataforseo,datagma,deepline_ip_to_company,deepline_native,deeplineagent,discolike,dropleads,edges,emailbison,emailguard,enformion,enigma,exa,findymail,firecrawl,fireflies,firmable,forager,fullenrich,fundable,generic_http,getleads,gong,google_ads_audiences,google_workspace,govfiles,grain,hackernews,harvestapi,heyreach,hubspot,hunter,icypeas,instantly,intercom,ipqs,kaspr,kernel,leadmagic,lemlist,limadata,linkedin_ads_audiences,luma,lusha,meta_audiences,millionverifier,nooks,openmart,opensosdata,openwebninja,outreach,parallel,peopledatalabs,pitchbook,podscan,postgres,predictleads,prospeo,quickenrich,rapidapi,redshift,rocketreach,salesforce,salesforge,salesloft,scrapecreators,searchbug,…."
---

# GTM Meta Skill

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

## 1. Find the right guidance and capabilities

Identify the business outcome, target population, constraints, time horizon,
requested destination and spend/authority boundaries. Resolve implementation
details yourself: providers, queries, identifier recovery and workflow shape.
Ask one concise question with a recommendation only when a missing requirement
materially changes the result or external action. Otherwise state a reasonable
assumption and proceed. User-specified values override workflow defaults.

### Domain guides

Read the relevant guide before new provider work; do not load unrelated guides
just to inspect an existing run.

| Job | Read and apply |
| --- | --- |
| Find companies/people, build lead lists, portfolio/VC sourcing, ICP discovery, contact finding or coverage at scale | [Finding companies and contacts](finding-companies-and-contacts.md): filters, provider mix, parallel search, role matching and list-builder delegation. |
| Research people/companies; enrich CSVs; find emails, phones or LinkedIn; coalesce, transform, score or add custom signals | [Enriching and researching](enriching-and-researching.md): Play routing, waterfalls, provider evidence and multi-pass research. |
| Write cold emails, qualification, personalization, sequences or inspect in Playground | [Writing outreach](writing-outreach.md) and its `prompts.json` templates. Also read enrichment guidance when research informs the writing. Keep outreach context active throughout sequence work. |
| Continuous provider event feeds / Monitors | Run `deepline monitors status --json`. Read [Monitors](recipes/deepline-monitors.md) only after exit 0 with `has_access: true`. Exit 1 with `has_access: false` is rollout denial; exit 3 is auth/permission, exit 5 configuration/reachability. Other failures are not denial. |
| Public/social source discovery, community language, pre-research source planning or provider coverage/cost comparisons | Use the standalone `deepline-research` skill. |

### Inspect logs or events from existing runs

Start with `deepline runs logs --help` for all known kinds and filter examples.
A run ID alone reads text logs; omit it or add a search flag to search events.
Use `--out` for all retained text, `--kind` for run/step outcomes, and
`--payloads` for available details or saved results. Follow `next.logs` to page.
These reads execute no providers. Read [Run logs and events](references/run-events.md)
for more recipes and SDK fields.

### Discover Plays and tools

For new work, look for a suitable prebuilt Play before assembling a custom
workflow. Search for the information needed and relevant controls, not only a
provider name; describe the selected capability to confirm inputs, outputs and
pricing. Names in guides are starting hints, not substitutes for the live
contract.

```bash
deepline search "<information needed and controls>" --type tools,prebuilts --task "<input you have -> result you need>"
deepline plays describe <play-name> --json
deepline tools describe <tool-id> --json
```

Read search's default readable output. Choose from its current filters,
cost and availability rather than a fixed provider ranking. If ranked tool search misses the capability, use
`deepline tools grep <substring> --json` or
`deepline tools list <returned-category> --json`. Read the relevant
provider playbook below for payload conventions, pricing and caveats. Different
vendors can expose the same underlying source; they are not automatically
independent corroboration.

Use a supplied Play or already-selected capability directly when suitable;
don't rediscover or replace it unnecessarily. For an existing run, skip
discovery and inspect its results.

### Specialized recipes

| Recipe | Use when |
| --- | --- |
| [Account org chart](recipes/account-orgchart.md) | Account maps, buying committees, stakeholders and multi-threading around a person/company. |
| [Build TAM](recipes/build-tam.md) | Total addressable market or large company lists from ICP criteria. |
| [Clay conversion](recipes/clay-to-deepline.md) | Translate a Clay table's actions and data dependencies into a custom Play. |
| [Monitors](recipes/deepline-monitors.md) | Access-gated event capture and downstream automation; apply the access and consent rules. |
| [Play authoring](recipes/deepline-plays.md) | Create/audit local or saved Plays, durable datasets, fallbacks, joins and orchestration. |
| [Find qualified titles](recipes/find-qualified-titles.md) | Nuanced roles at known companies: qualify actual company titles before revealing contacts. |
| [LinkedIn URL lookup](recipes/linkedin-url-lookup.md) | Resolve a person's URL from name/company with strict identity validation. |
| [Portfolio prospecting](recipes/portfolio-prospecting.md) | Investor-backed companies, then contacts and personalized outbound. |
| [Small-business prospecting](recipes/small-business-prospecting.md) | Local/storefront/service-area businesses using Maps-style search. |

### Domain decisions to preserve

- **Companies before people:** when company criteria drive the task, establish
  the company set first, then find people there.
- **Names are enough to start:** recover canonical company domains from official
  evidence; don't ask the user to supply recoverable identifiers. Carry that
  evidence forward and surface genuine identity ambiguity.
- **Nuanced roles:** use the real `company_titles` roster, qualify exact titles,
  then `search_contact` with `title_lists`. Use Exa for public
  profile gaps and DropLeads for supplemental database rows or broad sizing.
- **LinkedIn:** prefer native HarvestAPI for profiles, employees, posts and
  engagers; use Apify when the native provider lacks the required surface.
- **Provider routing:** direct structured search first for discovery; AI research
  for synthesis/ambiguity. Use deterministic transforms for non-AI work,
  `ai_inference` for classification and `deeplineagent` for context/research.
  Confirm current tools rather than guessing fields.
- **Quality:** consult [contact accuracy](references/contact-accuracy.md) before
  activation. Verification starts with `leadmagic_email_validation`, then
  corroboration; high-value outreach needs more than a single provider claim.
  For job-change recovery prefer quality-first Crustdata/PDL before LeadMagic
  fallbacks; phone recovery follows the enrichment guide.
- **Population:** preserve every supplied contact/account, including misses.
  For a fungible “find N” discovery job, source extra candidates within budget
  (roughly 1.4×N as an initial heuristic), then select the best qualified N.
  Don't apply that drop-incomplete-rows tactic to a fixed input cohort.

### Provider Playbooks

Provider-specific playbooks are bundled as separate reference files. Open the relevant playbook when provider-specific behavior, pricing, caveats, or payload conventions matter.

[fullenrich](provider-playbooks/fullenrich.md), [firmable](provider-playbooks/firmable.md), [bloomberry](provider-playbooks/bloomberry.md), [serper](provider-playbooks/serper.md), [akta](provider-playbooks/akta.md), [zoho-crm](provider-playbooks/zoho-crm.md), [meta-audiences](provider-playbooks/meta-audiences.md), [adyntel](provider-playbooks/adyntel.md), [apify](provider-playbooks/apify.md), [lusha](provider-playbooks/lusha.md), [quickenrich](provider-playbooks/quickenrich.md), [contextdev](provider-playbooks/contextdev.md), [linkedin-ads-audiences](provider-playbooks/linkedin-ads-audiences.md), [contactout](provider-playbooks/contactout.md), [kernel](provider-playbooks/kernel.md), [intercom](provider-playbooks/intercom.md), [datagma](provider-playbooks/datagma.md), [firecrawl](provider-playbooks/firecrawl.md), [scrapecreators](provider-playbooks/scrapecreators.md), [file-transport](provider-playbooks/file-transport.md), [ai-ark](provider-playbooks/ai-ark.md), [allegrow](provider-playbooks/allegrow.md), [hubspot](provider-playbooks/hubspot.md), [kaspr](provider-playbooks/kaspr.md), [hunter](provider-playbooks/hunter.md), [sentrion](provider-playbooks/sentrion.md), [instantly](provider-playbooks/instantly.md), [fundable](provider-playbooks/fundable.md), [lemlist](provider-playbooks/lemlist.md), [gong](provider-playbooks/gong.md), [ipqs](provider-playbooks/ipqs.md), [crustdata-v2](provider-playbooks/crustdata-v2.md), [smartleads](provider-playbooks/smartleads.md), [sec-edgar](provider-playbooks/sec-edgar.md), [buyercaddy](provider-playbooks/buyercaddy.md), [wiza](provider-playbooks/wiza.md), [searchbug](provider-playbooks/searchbug.md), [sumble](provider-playbooks/sumble.md), [pitchbook](provider-playbooks/pitchbook.md), [fireflies](provider-playbooks/fireflies.md), [amplemarket](provider-playbooks/amplemarket.md), [nooks](provider-playbooks/nooks.md), [exa](provider-playbooks/exa.md), [builtwith](provider-playbooks/builtwith.md), [google-ads-audiences](provider-playbooks/google-ads-audiences.md), [outreach](provider-playbooks/outreach.md), [waterfall](provider-playbooks/waterfall.md), [bettercontact](provider-playbooks/bettercontact.md), [deepline-ip-to-company](provider-playbooks/deepline-ip-to-company.md), [dropleads](provider-playbooks/dropleads.md), [crustdata](provider-playbooks/crustdata.md), [trestle](provider-playbooks/trestle.md), [slack](provider-playbooks/slack.md), [versium](provider-playbooks/versium.md), [tamradar](provider-playbooks/tamradar.md), [theswarm](provider-playbooks/theswarm.md), [deeplineagent](provider-playbooks/deeplineagent.md), [emailbison](provider-playbooks/emailbison.md), [discolike](provider-playbooks/discolike.md), [salesforce](provider-playbooks/salesforce.md), [browserbase](provider-playbooks/browserbase.md), [openwebninja](provider-playbooks/openwebninja.md), [integration-operation](provider-playbooks/integration-operation.md), [govfiles](provider-playbooks/govfiles.md), [attio](provider-playbooks/attio.md), [cbinsights](provider-playbooks/cbinsights.md), [google-sheets](provider-playbooks/google-sheets.md), [millionverifier](provider-playbooks/millionverifier.md), [postgres](provider-playbooks/postgres.md), [cloudflare](provider-playbooks/cloudflare.md), [edges](provider-playbooks/edges.md), [generic-http](provider-playbooks/generic-http.md), [findymail](provider-playbooks/findymail.md), [bounceban](provider-playbooks/bounceban.md), [enformion](provider-playbooks/enformion.md), [luma](provider-playbooks/luma.md), [predictleads](provider-playbooks/predictleads.md), [limadata](provider-playbooks/limadata.md), [pipedrive](provider-playbooks/pipedrive.md), [harvestapi](provider-playbooks/harvestapi.md), [crustdata-v3](provider-playbooks/crustdata-v3.md), [rb2b](provider-playbooks/rb2b.md), [grain](provider-playbooks/grain.md), [aviato](provider-playbooks/aviato.md), [peopledatalabs](provider-playbooks/peopledatalabs.md), [salesloft](provider-playbooks/salesloft.md), [deepline-native](provider-playbooks/deepline-native.md), [prospeo](provider-playbooks/prospeo.md), [affinity](provider-playbooks/affinity.md), [redshift](provider-playbooks/redshift.md), [brave](provider-playbooks/brave.md), [forager](provider-playbooks/forager.md), [openmart](provider-playbooks/openmart.md), [snowflake](provider-playbooks/snowflake.md), [clay](provider-playbooks/clay.md), [leadmagic](provider-playbooks/leadmagic.md), [test](provider-playbooks/test.md), [salesforge](provider-playbooks/salesforge.md), [hackernews](provider-playbooks/hackernews.md), [upcell](provider-playbooks/upcell.md), [bluesky](provider-playbooks/bluesky.md), [zerobounce](provider-playbooks/zerobounce.md), [emailguard](provider-playbooks/emailguard.md), [icypeas](provider-playbooks/icypeas.md), [attention](provider-playbooks/attention.md), [rapidapi](provider-playbooks/rapidapi.md), [zoominfo](provider-playbooks/zoominfo.md), [dataforseo](provider-playbooks/dataforseo.md), [heyreach](provider-playbooks/heyreach.md), [vector](provider-playbooks/vector.md), [snitcher](provider-playbooks/snitcher.md), [test-unhinted](provider-playbooks/test-unhinted.md), [clickhouse](provider-playbooks/clickhouse.md), [parallel](provider-playbooks/parallel.md), [theirstack](provider-playbooks/theirstack.md), [twitterapi](provider-playbooks/twitterapi.md), [bigquery](provider-playbooks/bigquery.md), [podscan](provider-playbooks/podscan.md), [google-workspace](provider-playbooks/google-workspace.md), [getleads](provider-playbooks/getleads.md), [opensosdata](provider-playbooks/opensosdata.md), [databricks](provider-playbooks/databricks.md), [socrata](provider-playbooks/socrata.md), [wizleads](provider-playbooks/wizleads.md), [enigma](provider-playbooks/enigma.md)

## 2. Build, run and retrieve

- **Build:** reuse a suitable prebuilt or author a Play for workflows and batches;
  direct tools are for spot checks. Follow [Play authoring](recipes/deepline-plays.md)
  and the [SDK reference](references/plays-sdk-reference.md). Preserve supplied
  Plays unless a material mismatch needs a decision.
- **Check:** inspect input headers and mappings; run `deepline plays check <file>`
  before executing local source.
- **Pilot:** test costly or unproven work on a small authorized sample; inspect
  actual results and spend before scaling. Don't duplicate a small supplied run
  or reprocess pilot rows unnecessarily.
- **Run:** `plays run` waits by default; `--no-wait` returns the run ID immediately.
  Follow an existing run with `runs tail <run-id>`; inspect it with
  `runs get <run-id>`. Reconnect after a timeout rather than launching again.
- **Inspect/transform:** overview first, then follow the suggested commands.
  Play datasets persist in database tables. Prefer read-only SQL for filtering,
  joining, flattening and aggregating stored data before downloading. Inspect
  actual column types and sample values first; don't assume a JSON structure.
  After a type error, inspect the data rather than guessing another query.
  Adapt the suggested SQL, preserving its table and run filter.

  Get the run ID, physical tables and suggested SQL in one call:

  ```bash
  deepline runs get <run-id> --json run.id,datasets.storage,actions
  ```

  Use the returned schema/table for `<returned-table>` (for example,
  `"storage"."contact_email_waterfall_email_rows"`). Copy the run-membership
  predicate from the suggested SQL into `<returned-run-filter>` (for example,
  `_run_id = '<run-id>'`); storage alone doesn't supply it. Check additional
  status filters and sample limits before computing whole-run totals.
  Use the dataset's actual columns and JSON structure:

  ```sql
  -- Aggregate before downloading.
  SELECT domain, COUNT(*) AS contacts, COUNT(email) AS emails_found
  FROM <returned-table>
  WHERE <returned-run-filter>
  GROUP BY domain;
  ```

  These are read-only projections, not changes to stored rows.

- **Export:** use the suggested export command for complete rows: CSV for
  delivery, `--format json` for nested evidence. The response is a file
  receipt—read the file. Use `csv show <file> --summary` for local CSV summaries.
- **CLI hygiene:** use `-h`; run `deepline preflight --json` as a standalone command
  and wait before parallel Deepline work. After preflight, prefix each concurrent
  command with `DEEPLINE_SKIP_SELF_UPDATE=1`. Prefer field selection or summaries
  when inspecting structured results. Preserve complete evidence responses,
  separate stderr from JSON, and check exit status (`pipefail` for pipelines).
- **Evidence:** previews aren't complete results; completed runs can contain
  failed rows; nulls don't explain misses. Inspect affected rows, then use
  `runs logs <run-id> --kind receipt.completed --payloads --json` for saved
  tool results. Select an exact result by its returned `eventId` with `--where`.
  Logs reads don't execute tools. Investigate unresolved requested conditions
  and stop once supported; repeating a provider isn't independent corroboration.
- **Save:** keep deliverables in a durable project directory, not system temp;
  preserve source files, input identities and evidence.
- **Experiments:** route comparisons, scaffolds and cost receipts apply when
  designing or comparing workflows—not every execution.
- **Authority:** planning or inspection authorizes no paid execution. Returned
  actions are capabilities, not approval to retry, publish or write externally.
  A credit shortage blocks paid work, not accessible retained results.

## 3. Scope, spend and approval

For calibration, scope or prioritization decisions, show the actual records,
comparison or supporting evidence and one recommendation:

```markdown
<the table, comparison, draft, or evidence>

Recommendation: <one concrete next state and why>.
Want me to use that, or adjust it?
```

Use that final question only when a calibration decision is needed. For a paid
scope decision use the approval format below instead, not both questions.
When no decision is needed, proceed without manufacturing one.

A user-stated bounded row-processing scope (“these 5 contacts”, “everyone in this
CSV”) authorizes completing that scope within stated constraints. Do not ask
again merely because a pilot finished. For small supplied Plays, the requested
run itself is the check; no mandatory extra pilot.

For larger or uncertain new work, use a small representative subset within the
approved scope/budget to validate identity, coverage, shape and cost before
scaling. Account for processed inputs rather than repeating them solely to
satisfy a full-run ritual. Stop when wrong matches, low usable coverage or cost
changes require a decision; don't enter an unbounded fix-and-rerun loop.
For open-ended requests, agree bounded scope/spend before a paid pilot.
Planning or inspection alone authorizes no paid execution.

Estimate with the Play contract, `deepline plays list --show-cost` where
available and observed Deepline spend; label extrapolations. Prefer
success-priced routes when appropriate, but verify the provider's actual price
basis before assuming a one-result search pays for only one result. Monthly
caps and estimates are not hard per-run controls. Do not advertise a runtime
Play spending cap unless the current contract actually supports it.

When a paid scope decision is needed, show the following format and ask only
its approval question. Use actual pilot evidence if one was authorized; label
“not run” rather than spending or inventing a preview to fill the template.

```markdown
Assumptions

- <intent and constraints>

CSV Preview (ASCII)
<real pilot rows, or "Not run — approval required before paid work.">

Credits + Scope + Cap

- Provider: <route>
- Estimated credits: <range and basis>
- Full-run scope: <rows/items>
- Spend cap: <user budget; distinguish monitored from enforced>
- Pilot summary: <observed findings, or not run>

Approval Question
Approve full run?
```

When approving only a pilot, replace “Full-run scope” / “Approve full run?” with
“Pilot scope” / “Approve pilot?” so the question matches the authorized action.

**Monitors are different:** require explicit approval for every paid deploy,
reactivate or historical widening, even when scope was stated. Inspect scope,
reuse candidates, downstream actions/unknown consumers and live Deepline price
before asking. Check Slack for an existing delivery channel; otherwise offer
Slack or the configured CRM. Don't call a historical rung empty before its
provider completion window. Follow the monitor recipe; bounded row permission
does not authorize recurring work, outreach or CRM writes.

For credit issues use `deepline billing balance`, `deepline billing usage` or
`deepline billing limit` as appropriate. For an exact charge, use
`deepline billing usage --request-id <job_id> --json`; only `posted` is final,
while holds and pending results are provisional. If credits are unavailable,
stop paid work. When recovery information is returned, quote its
`top_up_command` and `checkout_command` exactly, including `--json` and
`--no-open`, and wait for approval before running them. Use live prices, not a
hardcoded USD-to-credit conversion.

## 4. Deliver results

Show useful records and a plain-language summary: delivered population,
coverage, missing/rejected values, actual failures and any evidence limits.
Don't claim “nothing failed” when commands failed and recovered.
An agent-written explanation is analysis, not a raw provider response.
Link a person's name to a returned, verified LinkedIn profile. Keep raw IDs
and plumbing internal unless they affect cost, scope or confidence.

For row-processing work, export the complete requested population to the
intended final file, link it and the returned Play page, and verify identity,
row count and requested columns. Preserve evidence and lineage fields
(including authored `_dl_meta` and runtime `_metadata`) when transforming.
A partial pilot is not completion of a larger request; label partial coverage
explicitly.

When transforming CSVs, use a CSV writer rather than hand-joining fields: commas,
quotes and embedded newlines otherwise shift data into the wrong columns.
Before delivery, round-trip the saved file through a strict CSV reader and check
every record has exactly the header's field count. Python `DictReader` alone
accepts extra or missing fields; reject its `None` keys/values explicitly.
Correct malformed records from source evidence, without dropping or padding them.

On multi-phase work, checkpoint the best-so-far deliverable at the intended path
and update it as phases finish, so interruption doesn't erase useful results.
Honor the requested destination and filename; don't invent a CSV or Play link
for monitor-only, advisory or research work that produced neither.

## 5. Feedback and session sharing

### Proactive issue reporting

Unless the user restricts external reporting, send `deepline feedback send`
once per issue cluster when repeated failures, wrong output, a blocking bug,
substantial workaround or avoidable latency/steps impair the task. Then
continue. Include goal, tool/provider/model, exact error, attempted reproduction
and whether work stopped. For latency include run ID, input size, timing and
actual versus expected path; don't report legitimately long provider work.

Use `--error-outcome terminal` or `--error-outcome continued` for errors; omit
it for non-errors. Issue reporting does not authorize paid reproduction or
session upload.

### End-of-session consent

After the substantive result is resolved, ask once in a separate message—not
beside a table, recommendation, approval request or unresolved decision:

`Would you like me to send this session activity to the Deepline team so they can improve the experience? (Yes/No)`

Only after Yes, run
`deepline sessions send --current-session --rating <good|poor|neutral>`.
After No, do not send or ask again for that run/session. Rate by outcome, not
tone. Respect a user prohibition on external sharing.

After a successful upload, output `Session sent to Deepline. Rating: <rating>`
using the chosen `good`, `poor`, or `neutral` rating.

Don't ask after the terminal no-change outcome
`Change: none — I’m leaving it as is.`; keep that as the final line.
