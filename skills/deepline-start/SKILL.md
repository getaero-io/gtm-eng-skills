---
name: deepline-start
description: 'Interview a user to discover a concrete GTM problem or manual task, recommend the right installed Deepline skill, prebuilt Play, recipe, or tool, confirm the plan and org, then start the chosen workflow. Use only when the user explicitly invokes deepline-start.'
disable-model-invocation: true
---

# Discover a Deepline GTM workflow

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

Use a one-question-at-a-time interview to turn an unclear GTM need into a
specific, executable Deepline plan. This skill adapts the `grilling` interview
pattern; it does not require that skill to be installed.

## Route first

Start this interview only when the user explicitly invokes `deepline-start`.
Do not invoke it automatically for unclear GTM requests or from another skill.

When the user invokes this skill, keep the discovery and confirmation flow.
If the outcome, inputs, and scope are already clear, skip redundant questions
and propose the plan for confirmation. For a specific execution request that
did not invoke this skill or ask for discovery, use its owning skill directly.
`deepline-gtm` is the generalist for GTM implementation. A specialist leads
when its narrower job is the user's actual goal; it may route back to
`deepline-gtm` for execution.

| Emerging need                                                                  | Likely owner                 | What to verify before recommending                                    |
| ------------------------------------------------------------------------------ | ---------------------------- | --------------------------------------------------------------------- |
| Find accounts or people, enrich a list, write outreach, or automate row work   | `deepline-gtm`               | Input identifiers, target criteria, useful output, and batch size     |
| Build a TAM, source a portfolio, map an account, or find qualified roles       | `deepline-gtm` recipe        | Which established recipe matches the target and available identifiers |
| Watch for new hiring, funding, or other provider events                        | `deepline-gtm` monitor route | Event definition, cadence, downstream action, and access              |
| Discover public/private sources, current market language, or provider coverage | `deepline-research`          | Research question, evidence needed, recency, and source access        |
| Learn ICP signals, audit won/lost evidence, or score accounts/leads            | `deepline-scoring`           | Decision, population, labels or approved rules, and evaluation goal   |
| Answer a funnel, pipeline, or RevOps metric question                           | `deepline-analytics`         | Metric, period, grain, and governed data source                       |
| Build or upload an ads audience                                                | `deepline-ads-audiences`     | Platform, audience, suppression, data rights, and destination         |
| Turn a defined state machine into a durable Play                               | `deepline-engine`            | States, transitions, inputs, and outputs                              |
| Review and improve existing Play results with a human                          | `deepline-plays-review`      | Play/run, review surface, and acceptance criteria                     |

These are starting points, not a complete inventory. Inspect the skills
available in the current agent environment before naming an owner, and read
the candidate's `SKILL.md` once the job is clear. Read its guidance without
invoking its workflow during the interview: an early handoff can replace the
one-question interview with the specialist's intake or execution. Do not claim an uninstalled
skill is available. If the specialist is unavailable, route through the
installed `deepline-gtm` guidance where it covers the task; otherwise state
the gap and give the user a usable plan.

## Interview

Ask one concise question per turn, wait for the answer, and give your
recommended answer or a short set of choices with a recommendation. Follow the
branch the answer opens; do not send a questionnaire. Look up facts available
from supplied files, the current environment, or read-only catalog calls
instead of asking the user to recall them. Decisions about priorities,
acceptable output, data use, spend, and external actions belong to the user.
When you cannot recommend the business answer yet, recommend how to decide
between the choices rather than guessing the user's preference.
Include that recommendation even when asking about files or systems: recommend
an input format or inspection approach without inventing the missing fact.

Start with the result they want or the recurring work that consumes time. If
they cannot name a problem, offer concrete starting points: building target
lists, filling missing contact data, researching accounts or buyer language,
ranking accounts, personalizing outreach, preparing ad audiences, and
measuring pipeline. Ask which is most costly or blocked today.

For example: “Which recurring task costs your team the most time right now:
finding target accounts, filling missing contact data, researching accounts,
ranking leads, or preparing outreach? I recommend starting with the one you
can show me a recent example of.” Wait for that answer before drilling down.

As the branch becomes clearer, resolve only uncertainties that change the
workflow:

- What happens now, with one recent example and the manual steps?
- Who or what is processed, and what identifiers or private sources already exist?
- What decision or deliverable would make the work useful, and how will the user judge success?
- How many items and how often, and where should the result go?
- Which constraints matter: geography, freshness, quality, budget, data rights,
  or permission for outreach, CRM writes, recurring work, and paid calls?

Do not demand every answer before proposing a plan. Mark a nonessential
unknown as an assumption or first validation step. Revisit a branch when an
answer contradicts the current hypothesis. Briefly summarize what you heard
as the problem sharpens, and ask the next highest-impact question.

## Select the workflow

Once the job is specific enough, inspect the candidate skill instructions and
choose one primary owner and any necessary sequence of supporting skills. For
most GTM implementation plans, the primary owner is `deepline-gtm`. Use
`deepline-research` during planning when uncertainty about public/private
sources or market language would materially change that GTM plan; carry its
read-only findings into the proposal and defer paid probes until approved. If
discovering or evaluating a score is the goal,
let `deepline-scoring` lead and use `deepline-gtm` for any collection it needs.
Do not run a broad research pass when the input and route are already known.

For a prospective Deepline operation, use read-only live catalog search to
look for a matching prebuilt Play or tool and describe promising contracts;
names in skills are hints, not proof that a capability is available now. Run
`deepline --maintenance off preflight --json` by itself before other Deepline
commands in this session. Use `--maintenance off` for every pre-confirmation
CLI check, including catalog search and org status, so automatic updates or
skill synchronization do not install anything before approval.
Search with the known input and desired result, then inspect a
candidate's input, output, and Deepline-facing price. If the CLI or workspace
is unavailable, recommend the workflow category and label the exact route and
price unverified. Never invent a prebuilt, provider result, coverage, or cost.

Prefer a matching prebuilt Play for repeatable or batch work, a direct tool for
an isolated lookup, and a custom Play when transformation, branching, joins,
or fallbacks are needed. A specialist recipe is appropriate when its job and
inputs match. Use the smallest coherent sequence that reaches the outcome.
Name the owning skill even when the work needs no provider calls. For example,
drafting outreach from already-enriched rows still uses `deepline-gtm` and its
outreach guidance; a small scope does not remove that handoff.

## Confirm and hand off

Present a compact plan with:

1. The user's problem and the measurable result.
2. Inputs and constraints, including any assumptions.
3. The primary skill, any supporting skills, and the proposed Play, recipe, or
   tool category; name a specific live candidate only when verified.
4. The first validation step, intended output/destination, and any approval
   still needed for paid or external actions.
5. The verified active Deepline org where the workflow will run.

Before presenting that plan, read the primary skill's `SKILL.md` and check
the proposed sequence against it. A description or routing-table entry alone
cannot establish the specialist's source order, prerequisites, or quality gates.

Resolve the effective org in the same working directory and command environment
that execution will use. Reuse the current preflight's `auth.org_id` and
`auth.org_name`; if unavailable or the command context has changed, run
`deepline --maintenance off org status --json` and inspect `organization` and `current_org_id`.
Show the verified org name with the plan, adding its ID only if needed to
distinguish duplicate names. Do not infer the org from the user's company,
an input file, remembered credentials, or a global default that folder auth
may override. If the CLI, authentication, or org cannot be verified, continue
planning but hold execution until the target is resolved.

Ask **one explicit confirmation question covering both plan and org**, such as
“Proceed with this plan in Deepline org **<verified org name>**?” and wait.
Approval of a plan without its org does not authorize the handoff: include the
verified org in the combined confirmation even when the plan was already agreed.
**Check the conversation for the user's explicit acceptance of the displayed
org before proceeding.** “The plan is confirmed” or “start now” without an
accepted org name is not org approval. A CLI result identifies the active org;
it does not supply user consent. If org acceptance is absent, ask the combined
confirmation and stop; never tell the implementing skill that both were approved.
If the user chooses another org, use the documented `deepline org set` path
for that choice, then verify the effective org. Preserve an explicit approval
of both the plan and that chosen org instead of asking the same question again.
Do not
execute paid or state-changing provider calls, create or publish Plays, write
to destinations, install skills, or start recurring work before confirmation.
Read-only public research and catalog inspection are allowed to make the
proposal concrete. If the user changes the plan, revise it and confirm the
revised version.

After confirmation, complete these steps in order. This skill owns discovery;
the selected skill owns implementation.

1. **Run `deepline --maintenance off org status --json` before loading the selected skill.**
   Compare the effective org ID with the confirmed one; cached preflight is
   not a substitute for this check. A mismatch blocks the handoff and execution
   until resolved with the user. This read-only identity check also applies
   when the workflow otherwise only creates local files.
2. Prepare the agreed brief: outcome, population, identifiers/sources, success
   criteria, constraints, approved scope, destination, selected candidate, and
   unresolved assumptions, plus the confirmed org name and ID. State that the
   user confirmed both the plan and org.
3. **Call the skill loader for the primary skill before any implementation
   tool call.** If a `Skill` tool is available, call it with the selected skill
   name and the agreed brief as arguments. Reading its file during planning
   does not replace this call. If no skill loader exists, read its entrypoint
   and explicitly start following it with the brief.
4. Under the selected skill, take the first authorized implementation step in
   this conversation. Do not ask the user to paste the brief, restart discovery,
   or repeat a confirmation they already gave.

Preserve exact totals, per-item counts, filenames,
and action limits; quote the user's approved requirement when paraphrasing
could change it. Have the implementing skill check its result against these
success criteria before claiming completion. The user should not have to restate the brief or paste
a generated prompt. Follow that skill's own pilot, spend, data-rights, and
external-action gates; confirmation of a plan does not imply blanket approval
for paid calls, outreach, CRM writes, or recurring automation. If an approval
was already explicit and bounded, preserve it instead of asking again.
