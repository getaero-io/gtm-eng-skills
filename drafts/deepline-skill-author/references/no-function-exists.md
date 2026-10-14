# Jobs the catalogue has no tool for, and tools a skill must not use

**Read this during the interview, not after drafting.** If someone says "and then merge them" and
nothing merges, that has to surface in the conversation. Finding out afterwards means a draft already
names something imaginary, and the repair is a rewrite instead of a sentence.

> **Observed 2026-09-30 with `deepline tools search` / `grep` / `describe` on CLI 0.3.218.** Absences
> are re-checkable in seconds and worth re-checking: a new provider changes an answer here before it
> changes anything else in this kit. Search by intent *and* grep by literal, and page through; one
> search that returns nothing is not proof of absence.

## Absent, or narrower than the name suggests

- **No HubSpot or Salesforce merge tool.** `deepline tools search "merge duplicate contacts crm"`
  returns Affinity's merge endpoints (`affinity_v2_person_merges_post`) and nothing for the two
  commonest CRMs. **Deepline can find duplicates; the merge executes in the CRM.** A skill promising a
  merge on those CRMs is unshippable as written: the deliverable is a dry-run merge plan for a human.
- **No identified-website-visitor tool** turned up for *"identify company from website visitor ip"*;
  the nearest results are generic Apify actor runners. Matching a name is not matching a capability.
- **No scoring or classification tool.** Scoring is built per skill: deterministic arithmetic in the
  agent or in play code, judgment through `deeplineagent` with a `jsonSchema`. That is not a gap for a
  skill, because **the agent reading the skill is the model**: Deepline supplies the facts, the agent
  supplies the judgment.

## Present, and the reason a skill rule exists

- **Delete tools exist.** `hubspot_delete_contact`, `attio_delete_record`,
  `emailbison_bulk_delete_leads_by_id` and about 260 more `*_delete*` tools are in the catalogue, priced
  **Free** on the installer's own credentials (`billingSource: own_provider_credentials`). So "never
  destroy data" is not enforced by an absence here; it is enforced only by the skill. **A drafted skill
  never calls a delete, archive or clearing update**, whatever the creator asks for. It emits the
  reviewed list and the installer runs it in the system that holds their audit log and undo.
- **Batch email verification exists** (`bounceban_verify_bulk`, 0.06 credits per result), alongside
  single-address verifiers. Read the input schema rather than the name: a plural name does not prove a
  batch input, and a batch tool can be asynchronous.
- **`deeplineagent` is a general AI call** (`prompt`, `system`, `jsonSchema`, `maxToolCalls`) that can
  search the web. It prices *after* execution from usage, so any step built on it needs a cap
  (`maxToolCalls`, a row limit) and a balance read afterwards. Use it for prose and for classification
  into a declared schema; never for arithmetic, comparison or routing, which belong in code.
- **`generic_http_request` reaches any HTTP endpoint.** That makes it the nearest route for a job no
  provider covers, and also the easiest way to move installer data somewhere they did not name. A
  skill that uses it names the host as a declared input and says in `## What this skill touches` what
  is sent there.

## When a requested dimension has no tool

**Say so and leave its weight in the denominator.** Dropping it quietly inflates coverage: the skill
then reports high confidence over the subset it could see, which is the same number it would report if
the missing dimension did not matter. State the maximum achievable coverage up front (one proxy of ten
unobservable caps it at 0.80) and offer the nearest route: `generic_http_request`, `deeplineagent` web
research, or a search provider, each priced.

**Also worth catching in the interview:** a job that *looks* like it has a tool because a tool matches
on name. Match on the input and output schema from `deepline tools describe`, never on the name.
