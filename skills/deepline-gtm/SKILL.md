---
name: deepline-gtm
description: "GTM prospecting, enrichment, outreach, and Deepline Play work/audits. Providers: adyntel,affinity,ai_ark,akta,allegrow,amplemarket,apify,attention,attio,aviato,bettercontact,bigquery,bluesky,bounceban,brave,browserbase,builtwith,cbinsights,clay,clickhouse,cloudflare,contactout,contextdev,crunchbase,crustdata-v3,customer_db,databricks,dataforseo,datagma,dealroom,deepline_ip_to_company,deepline_native,deeplineagent,discolike,dropleads,edges,emailbison,emailguard,enformion,enigma,exa,findymail,firecrawl,fireflies,firmable,forager,fullenrich,fundable,generic_http,getleads,gong,google_ads_audiences,google_workspace,govfiles,grain,hackernews,harvestapi,heyreach,hubspot,hunter,icypeas,instantly,intercom,ipqs,kaspr,kernel,leadmagic,lemlist,limadata,linkedin_ads_audiences,luma,lusha,meta_audiences,millionverifier,nooks,notion,openmart,opensosdata,openwebninja,outreach,parallel,peopledatalabs,pitchbook,podscan,polymarket,postgres,predictleads,prospeo,quickenrich,rapidapi,redshift,rocketreach,salesforce,salesforge,…."
---

# Deepline GTM

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

Deepline is a GTM data platform reached through the `deepline` CLI. It has four
kinds of things: provider tools for one-off lookups and searches, plays for
durable multi-step workflows over rows, runs as the record of each play
execution, and a customer database where play results persist. If `deepline`
is missing, follow `https://code.deepline.com/INSTALL.md`.

Every command documents itself. `deepline --help` opens with the CLI version
and whether this shell is connected, then lists the surface and the
conventions every command shares; `deepline <command> --help` explains one
command's purpose, exact input forms, output fields, and cost; `--help
--verbose` adds field-level references and edge cases. That help is the
reference for everything below. Make sure to run `--help` before running a
command, you'll often find its behavior has some differences from your
expectations!

## Command surface

| Command group                                                                                                                                                   | What it covers                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `preflight`, `health`, `auth` (`register`, `wait`), `org` (`list`, `status`, `set`, `create`)                                                         | Server health, authentication, and the active workspace                                                                                        |
| `search` | One ranked search across prebuilt plays, provider tools, plays your workspace created, and monitor types |
| `tools` (`grep`, `list`, `describe`, `execute`)                                                                                                       | The provider catalog: read a tool's contract and price, run it once                                                                    |
| `plays` (`grep`, `list`, `describe`, `get`, `check`, `run`, `save`, `publish`, `set-live`, `versions`, `deploy`, `triggers`, `share`)    | Durable workflows: prebuilt waterfalls for email, phone, people, and company data, and authored `.play.ts` files                               |
| `runs` (`get`, `status`, `list`, `watch`, `logs`, `export`, `children`, `rerun`, `stop`, `stop-all`)                                                                          | Each play execution: status, row counts, logs and saved tool results, CSV or JSON export, cancellation                                                                        |
| `csv` (`show`, `render`)                                                                                                                                        | Local CSV inspection                                                                                                                           |
| `db` (`query`, `repair`)                                                                                                                                        | SQL over the customer database where play results persist                                                                                     |
| `billing` (`balance`, `usage`, `limit`, `status`, `plans`, `invoices`, `top-up`, `auto-recharge`, `subscription`)                                               | Deepline credit balance, spend, and plan                                                                                                       |
| `monitors`, `notifications`, `settings`, `secrets`, `git`, `providers`                                                                                          | Provider event feeds, alert routing, CLI settings, stored credentials, repository links, and the provider changelog                            |
| `sessions` (`send`, `render`), `feedback` (`send`)                                                                                                              | Share an agent session transcript or send feedback to Deepline                                                                                 |
| `skills`, `update`, `setup`, `doctor`                                                                                                                | The CLI and skills installation itself                                                                                                         |

## 1. Understand the job and find what to use

Identify the business outcome, the target population, constraints, the
requested destination, and the spend and authority limits. Resolve
implementation details yourself: which tools, queries, identifier recovery and
workflow shape. Ask one concise question, with a recommendation, only when a
missing requirement materially changes the result or an external action;
otherwise state a reasonable assumption and proceed. Values the user states
override defaults.

- Search once, with the task as one sentence, written as the input you have
  -> the result you need, not as keywords:
  `deepline search "50 seed-stage company domains -> each company's lead
  investors"`. One search ranks prebuilt plays,
  provider tools, plays your workspace created, and monitor types together,
  and each result names its kind. When a prebuilt play fits the job, use it
  or adapt it before authoring one from scratch; otherwise use the tool.
- Names in guides are starting hints. Confirm inputs, outputs and price on
  the live contract: `deepline describe <name>`.
- A tool is one operation and a play is GTM work as code: tools combined
  with your own logic over batches, with rate limits, retries, saved
  progress and recovery handled by Deepline. For a workflow or a batch, use
  a supplied play, reuse or adapt a prebuilt, or author one. Direct tool
  calls are for single spot checks; do not process a batch by looping tool
  calls in a script or in repeated agent calls.
- Read tool results through the exact getters `deepline describe`
  lists. Other fields live under `toolResponse.rawV2` with the provider's
  nesting kept: `.data` and `.data.data` are different. Check the fields you
  need on a pilot row before a bulk run. An extraction mismatch is not a
  provider miss, an invalid email, or a business hold.
- A supplied play or an already chosen tool is used directly; do not
  rediscover or replace it. For an existing run, skip discovery and inspect
  its results (section 2).
- Monitors are gated. Run `deepline monitors status --json` and read
  [Monitors](recipes/deepline-monitors.md) only after exit 0 with
  `has_access: true`. Exit 1 with `has_access: false` is a rollout denial;
  exit 3 is auth or permission; exit 5 is configuration or reachability.

## 2. Build, run and retrieve

- **CSV input:** a CSV goes through the batch form of a prebuilt play, never
  one single-record run per row:
  `deepline plays run prebuilt/<play>-batch --input '{"csv":"leads.csv"}'`,
  then `deepline runs export <run-id> --out <path>`. Inspect the file first
  with `deepline csv show <path> --summary` and route by the
  identifiers it holds. Work emails: `prebuilt/person-to-email-batch` takes
  the whole file in one run. Each row tries its LinkedIn profile first and
  falls through to name and company domain, so a row needs a LinkedIn URL,
  or a first name, last name, and company domain. Do not split the file or
  run a second pass. Phones: a known person →
  `prebuilt/person-to-phone-batch`. Waterfalls stop at the first verified
  hit and name the winning provider in `email_source` / `phone_source`.
- **Build:** to write a play, run `deepline plays --help`: it lists the
  commands to start from working code and, with `--verbose`, the authoring
  rules. Keep a supplied play as it is unless a material mismatch needs a
  decision.
- **Check:** inspect input headers and column mappings, and run
  `deepline plays check <file>` before running local source.
- **Pilot:** test costly or unproven work on a small authorized slice, read
  the actual results and the actual cost with
  `deepline billing usage --run-id <run-id>`, then run the full file under
  the same play. Do not rerun pilot rows without a reason. A stated-scope
  input of about 25 rows or fewer is its own pilot: run it once.
- **Run:** `deepline plays run` waits by default; `--no-wait` returns the
  run id at once. Follow a run with `deepline runs watch <run-id>` and read
  it with `deepline runs get <run-id>`. After a timeout, reconnect to the
  run; do not launch it again.
- **Inspect and transform:** read the overview first, then the commands it
  suggests. Play datasets persist in database tables, so filter, join,
  flatten and aggregate with read-only SQL before downloading.
  `deepline runs get <run-id> --json run.id,datasets.storage,actions`
  returns the run id, the tables and suggested SQL in one call. Use the
  returned table, and copy the run-membership predicate from the suggested
  SQL: storage alone does not supply it. Look at the actual column types
  and sample values first, and after a type error inspect the data instead
  of guessing another query.

  ```sql
  -- Aggregate before downloading.
  SELECT domain, COUNT(*) AS contacts, COUNT(email) AS emails_found
  FROM <returned-table>
  WHERE <returned-run-filter>
  GROUP BY domain;
  ```

- **Export:** the suggested export command gives complete rows: CSV for
  delivery, `--format json` for nested evidence. The response is a file
  receipt; read the file.
- **CLI hygiene:** run `deepline preflight --json` as a standalone command
  and wait for it before parallel Deepline work. Keep stderr apart from JSON you parse, and
  check exit status (`pipefail` in pipelines).
- **Evidence:** a preview is not the full result, a completed run can hold
  failed rows, and a null does not explain a miss. Inspect the affected
  rows, then read what the tool returned:
  `deepline runs receipt <run-id> --key '<receipt-key>'` for a key the row
  retains, otherwise
  `deepline runs logs <run-id> --kind receipt.completed --payloads --json`
  and one result by its `eventId` with `--where`. These reads run no tools.
  Stop investigating once the requested condition is supported; repeating a
  provider is not independent corroboration.
- **Save:** keep deliverables in a durable project directory, not system
  temp, with the source files, input identities and evidence.
- **Authority:** planning or inspection authorizes no paid execution.
  Commands a result suggests are capabilities, not approval to retry,
  publish or write externally. A credit shortage blocks paid work, not
  reading retained results.

## 3. Scope, spend and approval

- **The balance is a ceiling, not a budget to use up.** Before each paid
  call, estimate its cost: the price from `deepline tools describe <tool>
  --pricing-only` or `deepline plays list --show-cost`, times the results or
  rows you will request, and label extrapolations. Take the cheapest route
  that can answer and test it with the smallest limit. If one tool call
  would cost more than about 5 credits, lower its limit or find a cheaper
  route first. A success-priced route still needs its price basis checked:
  a one-result search can bill for more than one result. Monthly caps and
  estimates are not per-run controls.
- **A stated scope is the approval.** "These 5 contacts" or "everyone in
  this CSV" authorizes finishing that scope within the stated constraints.
  Do not ask again because a pilot finished. For a small supplied play, the
  requested run is the check.
- **Larger or uncertain new work** starts with a small representative
  subset inside the approved scope and budget, to validate identity,
  coverage, shape and cost. Stop when wrong matches, low usable coverage or
  a cost change needs a decision; do not enter a fix-and-rerun loop. For an
  open-ended request, agree a bounded scope and spend before a paid pilot.
- **A calibration or prioritization decision** shows the actual records or
  evidence and one recommendation. Ask only when a decision is needed.

  ```markdown
  <the table, comparison, draft, or evidence>

  Recommendation: <one concrete next state and why>.
  Want me to use that, or adjust it?
  ```

- **A paid scope decision** uses this format and asks only its approval
  question. Use real pilot rows when a pilot was authorized, and write "not
  run" rather than spending or inventing a preview. For a pilot, say "Pilot
  scope" and "Approve pilot?".

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

- **Monitors need explicit approval every time** they deploy, reactivate or
  widen history at a cost, even when the scope was stated. Permission to
  process rows does not cover recurring work, outreach or CRM writes.
  Follow the monitor recipe.
- **Credit problems:** read `deepline billing balance`,
  `deepline billing usage` or `deepline billing limit`. An exact charge is
  `deepline billing usage --request-id <job_id> --json`; only `posted` is
  final. When the balance runs out or a run fails on balance, stop
  spending, deliver the rows you have, and name the rows left unresolved
  and why. Never top up, buy credits, or change billing unless the user
  asks: when a result returns a `top_up_command` or `checkout_command`,
  quote it exactly, including `--json` and `--no-open`, and wait for
  approval. Use live prices, not a fixed dollar-to-credit conversion.

## 4. Deliver results

- Show useful records and a plain summary: the delivered population,
  coverage, missing or rejected values, actual failures, and any limits of
  the evidence. Do not say nothing failed when commands failed and
  recovered. Your own explanation is analysis, not a provider response.
- Link a person's name to a returned, verified LinkedIn profile. Keep raw
  ids and plumbing out of the answer unless they affect cost, scope or
  confidence.
- For row work, export the complete requested population to the intended
  file, link it and the play page the run returned, and verify identity,
  row count and the requested columns. Keep evidence and lineage fields
  (`_dl_meta`, `_metadata`) when transforming. A partial pilot is not the
  larger request; label partial coverage.
- When you transform a CSV yourself, write it with a CSV writer, never by
  joining fields by hand: commas, quotes, and embedded newlines otherwise
  shift data into the wrong columns. Before delivering, read the file back
  with a strict CSV reader and check every record has the header's field
  count. Correct a malformed record from source evidence; do not drop or
  pad it.
- On multi-phase work, write the best result so far to the intended path
  and update it as phases finish, so an interruption does not erase it.
  Honor the requested destination and filename, and do not invent a CSV or
  play link for work that produced neither.

## 5. Feedback and session sharing

- **Report product problems unasked,** unless the user restricts external
  reporting: `deepline feedback send` once per issue when repeated
  failures, wrong output, a blocking bug, a substantial workaround, or
  avoidable latency or steps get in the way. Then continue.
  `deepline feedback send --help` lists the evidence to include and the
  flags. A report does not authorize paid reproduction or a session upload.
- **Ask about the session once, at the end,** in its own message and not
  beside a table, recommendation, approval request or open decision:

  `Would you like me to send this session activity to the Deepline team so they can improve the experience? (Yes/No)`

  Only after Yes, run
  `deepline sessions send --current-session --rating <good|poor|neutral>`,
  rated by outcome and not tone, then output
  `Session sent to Deepline. Rating: <rating>`. After No, do not send or
  ask again in that session. Do not ask after the final line
  `Change: none — I’m leaving it as is.`

## Guides

Task guides for work the command help does not cover.

### Specialized recipes

Recipes live in `recipes/`:

| Recipe | Use when... |
| --- | --- |
| `account-orgchart.md` | Building an interactive HTML org chart for one account: decision makers, reporting lines, the buying committee, and warm intro paths. |
| `build-tam.md` | Building a TAM or large account list from ICP filters, then finding contacts at those companies. |
| `find-qualified-titles.md` | Finding who holds a nuanced role at named companies, starting from each company's real title roster. |
| `linkedin-url-lookup.md` | Resolving LinkedIn profile URLs from a name, with or without a company, and validating each match. |
| `portfolio-prospecting.md` | Finding companies backed by an investor or accelerator, their contacts, and personalized outbound. |
| `small-business-prospecting.md` | Finding local small businesses, such as dentists, plumbers, med spas, agencies, and storefronts. |
| `clay-to-deepline.md` | Converting a Clay table into Deepline plays with parity checks against Clay's output. |
| `deepline-monitors.md` | Setting up provider event feeds (job posts, email replies, funding, intent) that trigger plays; an access-gated beta. |

If none match, use the command surface above and each command's `--help`.

References:

- `references/clay-extraction.md`, `references/clay-api-surface.md`, and
  `references/clay-action-mappings.md`: extracting a Clay table and the
  Deepline tool for each Clay action.
- `references/monitor-sdk.md`: defining monitors in code.
- `references/run-events.md`: the event kinds and filters `deepline runs logs`
  can search.
- `writing-outreach.md`: cold email copy, personalization, sequence design,
  and lead qualification.

## Related skills

- `deepline-research` for discovering data sources and market language.
- `deepline-scoring` for account and lead scoring.
- `deepline-ads-audiences` for paid ads audience lists.
- `deepline-analytics` for warehouse and semantic-layer questions.
- `deepline-plays-review` for human review loops over play output.
