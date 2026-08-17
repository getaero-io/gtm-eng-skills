---
name: deepline-engine
description: 'Build a Deepline Play as a durable state machine over Customer DB tables. Invoke this skill explicitly when the user asks to build an engine.'
disable-model-invocation: true
---

# Deepline Engine

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

Build an engine from the state machine the user defines.

An engine is an orchestrator Deepline Play that accepts an input, determines its state, calls the transition Play for that state, and produces a new state. The durable data plane lives in Customer DB: every state has an input table and an output table. The output of one transition can become the input to the next state.

The user owns the states, transition rules, transformations, and terminal behavior. This skill owns the reusable structure for turning those decisions into a replay-safe Play. Do not import an outbound workflow, GTM recipes, provider choices, or domain-specific policy unless the user asks for them.

## Core model

For each state, define:

| Part            | Meaning                                                                             |
| --------------- | ----------------------------------------------------------------------------------- |
| Input table     | Rows waiting to be handled in this state                                            |
| State decision  | The user-defined rule that establishes the row's current state                      |
| Transition Play | The child Play that performs the transformation for this state                      |
| Output table    | The input, result, transition status, and next state                                |
| Next input      | The row admitted to the next state's input table, unless the transition is terminal |

Keep the state decision explicit. Inferring state from incidental fields creates transitions the user did not define and makes replay behavior hard to explain.

## Workflow

1. **Capture the state machine.** Ask for the states, initial state, terminal states, allowed transitions, state-decision rules, and transformation for each state. Preserve unresolved choices instead of inventing them.
2. **Define row identity.** Choose the stable business key and a transition idempotency key. A retry must address the same row and transition instead of creating a second result.
3. **Define the tables.** Give every state an input table and an output table in Customer DB. Let the user choose names and domain columns. Record the structural fields needed to connect an input, its result, and the next state.
4. **Choose a durable source directory.** Generate the engine under a maintained project directory selected with the user or inferred from repository conventions. Keep the orchestrator, new child Plays, shared types, README, and Mermaid diagram together as project source. Do not use an ignored `tmp/` scaffold; temporary paths hide work from version control and make the engine disposable.
5. **Resolve every transition Play before authoring one.** Search callable Plays visible to the user's workspace with `deepline plays search "<transition outcome>" --all --json`. Inspect owned and prebuilt candidates with `deepline plays describe <name> --json`. Reuse an exact contract match; names are only hints, so verify input, output, and inline-composition compatibility. If no candidate fits, author one new Play for that transition instead of embedding its transformation in the orchestrator.
6. **Author the orchestrator Play.** Use `definePlay(name, handler, options)`. Determine the state, select the matching transition Play, and call it through `ctx.runPlay(...)` with a stable key. The orchestrator owns state routing and Customer DB persistence; transition Plays own transformations.
7. **Persist the transition.** Materialize the accepted input, the child Play result, `from_state`, `to_state`, status, error or miss information, timestamps, workflow version, transition Play identity/version, and idempotency key. If the transition continues, write the next state's input idempotently.
8. **Choose the advancement model with the user.** Either process one transition per invocation or continue through multiple states in one run. Do not choose silently; it changes retry, trigger, and observability behavior.
9. **Validate every edge.** Check every new transition Play and the orchestrator. Test each allowed transition, each terminal state, an invalid or unknown state, a child Play failure, an invalid state returned by a child, and replay of a completed transition.
10. **Run safely.** Test only with synthetic rows until the user separately approves an engine run and any resulting side effects.

Read [references/state-machine-contract.md](references/state-machine-contract.md) when designing the transition table, Customer DB table roles, Play shape, and tests.

## Invariants

- Keep the engine as an orchestrator Play and every transformation as a transition Play. A switch statement full of embedded business transformations hides reusable work and is not the engine architecture.
- Keep generated engine artifacts in a durable, maintained project directory. The orchestrator, child Plays, types, README, and Mermaid diagram are source, not an ignored `tmp/` scaffold.
- Search the user's callable Plays and Deepline prebuilts before creating a transition Play. Reimplementing an existing contract creates duplicate behavior that will drift.
- Accept a reused Play only when its described input/output contract and composition shape fit the transition. A child that owns `ctx.dataset()`, `ctx.csv()`, event waits, or another lifecycle boundary cannot be composed with `ctx.runPlay`; create or adapt a scalar transition Play instead.
- Let the user's state machine drive the implementation. Do not ship a canned business workflow under generic names.
- Give each state distinct input and output table roles. Combining them is acceptable only when the user chooses it and the transition history remains unambiguous.
- Persist engine state with idempotent, schema-qualified Customer DB mutations. `ctx.dataset(...)` creates a run-scoped Runtime Sheet and cannot replace the durable state input and output tables.
- Persist the original input alongside or by stable reference from the output. A result without its input cannot be audited or replayed safely.
- Persist a typed failed or invalid output before rethrowing a child failure, unknown state, or forbidden child result. Failure outcomes use the same transition idempotency key and never create a next-state handoff.
- Make state transitions idempotent. A retry may repair an incomplete handoff, but it must not duplicate a completed output or next-state input.
- Treat unknown states and forbidden transitions as loud failures. Falling through to a default process silently corrupts the machine.
- Keep customer workflow rows and state-transition data in Customer DB. Product control-plane state used by Deepline UI/API/CLI, credentials, billing, and platform run state remain in their Deepline-owned stores, including Convex where applicable.
- Use stable Play names, dataset names, row keys, step ids, and tool ids. Renaming durable identities can make completed work look new.
- Do not publish without the user's approval. Publishing does not authorize running the engine, installing triggers, mutating a real Customer DB, or calling providers.

## Publication approval

Treat the user's explicit instruction to **publish** as approval for one complete dependency-ordered workflow:

1. Check every new child transition Play.
2. Publish the children required for `ctx.runPlay` name and contract resolution.
3. Check the orchestrator against those published child contracts.
4. Publish the orchestrator.
5. Verify every published version with the publication result plus `deepline plays describe <name> --json` and `deepline plays versions --name <name> --json`, then report the checked and live versions.

Do not request another approval between publishing the children and publishing the orchestrator. If any check, publication, or version verification fails, stop the workflow, preserve the successful results, and report the exact failure rather than advancing with an unresolved dependency.

This approval ends at publication. Obtain separate approval before running the engine, calling providers, installing triggers, or mutating Customer DB.

## Deliverable

Return:

- the user-confirmed state and transition table
- a Mermaid `stateDiagram-v2` diagram showing the complete state machine, including initial, terminal, and unresolved transitions
- the input/output table contract for every state
- the transition-Play reuse inventory, including owned and prebuilt candidates considered
- the maintained project source directory and source tree
- the implemented orchestrator `.play.ts` file and any newly required transition `.play.ts` files
- shared type source, a project README, and the Mermaid diagram as a maintained project file
- the state-decision and `ctx.runPlay` dispatch logic
- the idempotency and replay strategy
- the checks run and their actual results
- unresolved decisions or actions still requiring approval

After returning the deliverables, ask whether the user would like to see an end-to-end example that follows one item through the whole lifecycle: initial-state input, state determination, each transition Play, output persistence, next-state handoffs, terminal completion, and a representative failure or retry when relevant.
