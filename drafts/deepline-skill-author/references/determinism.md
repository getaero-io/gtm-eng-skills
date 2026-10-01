# Writing a deterministic skill

**The test, and it fits in one sentence: could two competent installers follow this step and end up
calling different things?** If yes, the step describes what *you* did rather than instructing anyone.

"Enrich the author to get an email" fails that test. Every reader resolves it differently: a different
tool, different inputs, a different bill.

It does **not** mean reproducible output. A company hires, a domain moves, a page is rewritten: same
input, different answer, and that is correct. It means **the same instruction produces the same calls.**
Determinism lives in the mechanism, never in the data.

## First decide the shape, because the rest of this file assumes one of them

**Call the tools.** The agent runs the loop: `deepline tools execute <tool_id> --input '{…}'`, compares,
judges, writes the result. This is the default for 1 to about 20 rows, and it is what most skills are.

**Ship a play.** A `.play.ts` the skill carries under `scripts/` and runs with `deepline plays run`.
Two forcing conditions and no others: **something has to run when no agent is present** (a cron or
webhook trigger on the play, or a `deepline monitors` deployment), or **the volume exceeds what one
conversation can hold** (a CSV of hundreds of rows, a `.withColumn` per step). The cost is real: a play
is code the installer has to trust, `deepline plays check` it before running, and debug from
`deepline runs logs`. Where the cadence forces a play, write one. Where it does not, tool calls are not a
consolation prize; they are the shape the installer can read line by line.

**A prebuilt play is a third option for one step**, not a shape: `deepline plays search <intent>
--json`, then `deepline plays describe prebuilt/<name> --json`. An email waterfall someone already
maintains (`prebuilt/person-linkedin-to-email`) beats one you hand-roll, and the skill names it the
same way it names a tool.

One absence that reads like a gap and is not: there is no scoring tool. The agent reading the skill
**is** the model: Deepline supplies the facts, the agent supplies the judgment. `deeplineagent` exists
for prose and schema-bound classification inside a play; never for extraction, comparison or routing.

## The four things any step that spends money must name

| | Why it cannot be left implicit |
|---|---|
| **What runs**: the tool ID or play ID | "enrich" is a category. Several tools do it, at different prices, returning different fields |
| **What goes in**: which fields, from which declared input, matched to `inputSchema` | otherwise field mapping is a guess, and that is where silent misses come from |
| **What to verify in the response**, at its exact path | a call can succeed and return nothing useful. See below |
| **What it costs**: `pricing.displayText` and `pricing.unit`, and who confirms before it runs | spend without a stated number is spend without consent |

One row per paid step, in the skill. A reader can then price the run before starting it.

## Name what you expect, confirm it at runtime, fail loudly if it is gone

1. **Name the tool you expect**: its ID, its price, and the field you will read out of the response.
2. **Confirm it against the live catalogue before relying on it**, with the commands below.
3. **Fail loudly when the named tool is absent** (`deepline tools describe` exits non-zero with
   `UNKNOWN_TOOL`). Never silently substitute the nearest thing.

Rule 3 is the one people skip, and the cost of skipping it is that **dead and acquired companies enrich
perfectly well on last-known data**. A run that substitutes an enrichment call for an unavailable
liveness check goes green, fills every row, and asserts that defunct companies are alive. A filled row
is not a live company.

The procedure, which outlives any particular name, all free:

```
deepline tools search "<intent>" --json        candidates, ranked by intent
deepline tools grep "<literal>" --json         literal match over ids, descriptions, input fields
deepline tools describe <tool_id> --json       inputSchema, outputSchema, targetGetters, pricing, billingSource
deepline plays search "<intent>" --json        prebuilt plays for a whole step
deepline plays describe <play_id> --json       a play's contract and cost estimate
```

**Confirm subcommand names with `--help` on the installed version.** A skill that hardcodes a
subcommand ages the same way one that hardcodes a provider does. Per-provider gotchas are in the
`deepline-gtm` skill's `provider-playbooks/<provider>.md`; read the one for each provider you name.

### Ways a reasonable reading of the catalogue is wrong

These were measured on Clay's action catalogue (2026-08) and each has a Deepline form worth checking.

- **A search is ranked, not exhaustive.** `tools search` returns the best matches for the words you
  used; `tools grep` finds literals it ranked low. Use both, and never conclude a tool does not exist
  from one call.
- **Present does not mean callable for this installer.** `describe` carries `callable`, `connected`,
  `credentialStatus` and `disabled`. A tool on the installer's own CRM credentials is only callable once
  they have connected it; say so as a declared input.
- **A plural name does not mean batch.** Read `inputSchema`, not the name.
- **The description can be wrong where the schema is right.** A tool described as working from a name
  and company may require a profile URL, and fail per row without one. `describe` says it of itself:
  *"tools describe shows declared schema and Deepline getters; it is not an observed provider
  response."* A schema's description is a claim, not a contract.
- **Undeclared inputs pass silently.** A run that *starts* proves nothing about whether your inputs
  were understood. Trust the declared schema and the per-row result.
- **The declared output is a floor, never a ceiling.** Read the whole first response, and use an
  undeclared field if you say it is undeclared.

### Cost: read the pricing block, and notice when it cannot give you a total

`deepline tools describe <id> --json` carries `pricing` (`displayText`, `unit`, `creditsPerUnit`) and
`billingSource`. Three shapes, all real in the catalogue today:

| `pricing` says | Example | What the skill writes |
|---|---|---|
| a price per `call` or per `result` | `hunter_email_verifier`: *0.15 Deepline credits per result* | the number, and the unit |
| `Free`, `billingSource: own_provider_credentials` | `hubspot_update_company`: *"Free through Deepline with your own provider credentials"* | **zero Deepline credits, and it still bills or writes on their own account**; the gate names the write |
| *"Calculated after execution"* | `deeplineagent` (from usage), `crustdata_v3_person_search` (0.02 per returned result) | a per-unit price, a cap, and a `deepline billing balance` read afterwards |

- **A per-result price on a step whose result count is its output has no total before it runs.** The
  rows are the output, so there is nothing yet to multiply. Measured on a Clay action, 2026-08-28: told
  6 credits, spent 33, because identical calls returned 4 rows and 25. `crustdata_v3_person_search`
  states the same thing of itself: *"Search cost is based on returned rows, not the matched
  total_count. Use a strict limit."* Carry a cap.
- **Read the parameter descriptions before pricing anything.** A per-unit basis sometimes lives in a
  parameter (a page size, a location count, `maxToolCalls`) rather than in the price field. On Clay's
  catalogue a build priced from the cost field alone understated by up to 100×, with 4 of 20 priced arms
  billing per unit. Pass a limit where one exists.
- **Read the balance before and after, and report what was charged, not the estimate**, with one
  caveat: balance movement is not a per-call measurement when anything else spends in the same org at
  the same time (on Clay, nine calls reported 11.8 credits while the balance moved 15.4 because a
  parallel session was spending). Per-call cost from the run's own receipts (`deepline runs get <id>
  --full --json` for a play) beats a balance delta.
- **A miss can bill.** Budget for misses and report them as spend. A miss that is free is the
  exception; check the provider playbook.

## The waterfall is the deterministic shape for enrichment

When several providers can answer the same question, the pattern that is both cheap and reproducible is
an **ordered set of calls where each one's run condition tests the specific output path of the one
before it**.

```
call A                          always runs, cheapest of the set
call B    runs only if   A's <named output path> is empty
call C    runs only if   A's and B's named paths are both empty
coalesce  first non-empty of A → B → C
```

Three details carry the whole pattern:

1. **The gate names a field, not a status.** `A ran` is not the condition; `A returned nothing at this
   path` is. Gating on completion buys every later call for nothing.
2. **Order by cost, ascending, and the spread is worth ordering for.** On Clay's catalogue in 2026-08,
   five observables were each priced 1 to 10× apart across providers: a four-proxy question was 900
   versus 9,000 credits across 300 accounts, for identical output. Read the real prices with `describe`
   at authoring time and say what order you chose and why.
3. **Cheapest is not cheapest when the cheap arm cannot answer the question.** An arm that needs a
   profile URL costs its price *plus a resolution call* from a domain-anchored list. An arm that cannot
   filter on the dimension you need returns a confident zero. Route by what the source can filter.

**Before hand-rolling one, check for a prebuilt waterfall** (`deepline plays search email --json`).

**A waterfall is right for a fact and wrong for a metric.** Where the arms do not share a scale, a
column filled by whichever arm resolved first cannot be ranked, thresholded, or diffed over time.
Waterfall the boolean and the evidence, never the count.

## Reading a result: five things that are not what they look like

`describe` gives the paths to read (`targetGetters`, and `failureMode` for when a value means "no"),
but the paths are declared, not observed. **Record the path you actually saw in the first response,
verbatim, in the skill.** "Completed and returned nothing" and "you read the wrong key" look identical
from outside.

1. **Completion is not data.** A call that returns without error can carry `{}`, `null`, an empty list,
   or a field present but empty-string valued. Gate on non-empty content at a named path.
2. **A null is not a zero.** One arm returned nine time horizons with the most recent null; read as 0%,
   that null becomes a negative verdict assembled from a data gap.
3. **Compare band strings as bands, but make the rule per field.** `"1,001-5,000 employees"` through a
   naive `parseInt` yields **1**. Use an exact count where the payload carries one and name the field;
   never invent a number from a band.
4. **`0` and `false` are observed values, not absences.** Never test presence by truthiness. In one
   scoring build a truthiness test promoted a failing row to a perfect top tier.
5. **Count the right unit.** 10 rows that are 4 distinct titles across 6 locations, with a `jobCount: 33`
   beside them: "33 openings", "10 postings" and "4 roles" are all true and answer different questions.

And one that decides whether any of the above matters: **a wrong-entity hit is shaped exactly like a
right one.** Where a response echoes the entity it matched, that echo is the only detector; compare it,
and exclude the TLD, because `com` substring-matches "company".

## Four more traps that cost real debugging

- **The wrong organization returns not-found, not "wrong org".** Say the organization at Step 0.
- **Concurrency has a ceiling that is not yours.** Providers rate-limit, and a fan-out that works on
  ten rows fails on a real list. A play has `--max-concurrent-external-calls`; state the cap you used.
- **Silent truncation exists.** One string output ended mid-name at exactly 8,192 characters with no
  flag (measured on Clay). Treat a suspiciously round-length result as incomplete.
- **A field's name is not evidence of its content.** A production build carried a field named for
  revenue that held an employee count. Read the payload, never the label.

## Provenance, and how this file goes wrong

The structural rules here apply to every skill. Figures attributed to Clay were measured there and are
not Deepline prices; Deepline prices come from `describe` on the day you write the skill. **If a rule
here contradicts the live catalogue, the catalogue wins and this file is wrong.** Say so in the skill.

## Before you ship a step, ask it out loud

> Could two competent installers read this and call different things?

If yes, the step is not finished. The fix is never longer prose. It is naming the four things above.
