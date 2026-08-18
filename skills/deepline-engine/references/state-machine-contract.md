# State machine contract

Use this contract to turn a user-defined workflow into a composable set of Plays: one durable orchestrator plus one child Play for each transformation. The names below describe roles, not required table or field names.

## Transition matrix

Write the matrix before the Play:

| Current state | How state is determined                                        | Input table | Transition Play        | Allowed next states | Output table | Terminal?  |
| ------------- | -------------------------------------------------------------- | ----------- | ---------------------- | ------------------- | ------------ | ---------- |
| `<state>`     | `<explicit field, durable lookup, or user-defined classifier>` | `<table>`   | `<owned/prebuilt/new>` | `<states>`          | `<table>`    | `<yes/no>` |

Infer routine structural details from the request and project conventions, and record those assumptions. Do not invent missing business policy. Ask only when competing interpretations would materially change a state decision, allowed transition, transformation, or terminal outcome.

## Table roles

Each state's input table needs enough information to identify and process one item:

- stable business row key
- current state or the inputs required by the state-decision rule
- payload or a stable reference to it
- received timestamp
- transition idempotency key
- source or prior-transition reference when relevant

Each state's output table needs enough information to audit the transition:

- stable business row key
- reference to the accepted input
- `from_state` and `to_state`
- transformation result
- `completed`, `failed`, `invalid`, or another user-defined status
- typed error or miss reason
- processed timestamp
- Play/workflow version
- transition Play reference and version
- transition idempotency key

When a transition is nonterminal, its output supplies the next state's input. Use the same stable business key and a deterministic handoff key so replay repairs a missing handoff without creating another one.

## Resolve transition Plays

Treat each state transformation as a callable Play, not a helper function hidden inside the engine. Before writing one:

```bash
deepline plays search "<transition outcome>" --all --json
deepline plays describe <owned-or-prebuilt-candidate> --json
```

`--all` includes Plays created in the user's workspace as well as prebuilts. Search by the transformation's outcome and input contract, not a guessed name. Prefer an exact owned or prebuilt contract over new code. Record why each candidate fits or fails; a similar title is not enough.

The orchestrator composes the selected Play with `ctx.runPlay`. That boundary accepts scalar child Plays only. A child that uses `ctx.dataset()`, `ctx.csv()`, a Runtime Sheet, an event wait, or an explicit timeout owns a separate lifecycle and cannot be used as an inline transition. When no compatible Play exists, author a scalar transition Play and include it in the engine's automatic dependency-ordered check and publication workflow.

## Maintained source tree

Generate the engine in a durable project directory that follows the repository's source conventions. Keep these artifacts together:

- orchestrator Play
- newly authored child transition Plays
- shared state and transition types
- README describing the contract, local validation, and automatic publication and synthetic-test boundaries
- Mermaid `stateDiagram-v2` source for the complete machine

Do not put these artifacts in an ignored `tmp/` directory. Before handoff, confirm the chosen directory is durable and visible to the project's source-control workflow.

## Orchestrator shape

Keep the state machine visible in code:

```ts
import { definePlay } from 'deepline';

type EngineInput = {
  itemKey: string;
  payload: Record<string, unknown>;
  state?: string;
};

type TransitionResult = {
  nextState: string;
  output: Record<string, unknown>;
};

export default definePlay(
  'user-chosen-engine-name',
  async (ctx, input: EngineInput) => {
    const state = await determineState(ctx, input); // implement the user's rule
    let transition: TransitionResult;

    try {
      switch (state) {
        case 'user-defined-state-a':
          transition = await ctx.runPlay<TransitionResult>(
            'transition-from-state-a',
            'user-owned-or-prebuilt-transition-play-a',
            { itemKey: input.itemKey, payload: input.payload },
            { description: 'Apply the user-defined transition from state A.' },
          );
          break;
        case 'user-defined-state-b':
          transition = await ctx.runPlay<TransitionResult>(
            'transition-from-state-b',
            'user-owned-or-prebuilt-transition-play-b',
            { itemKey: input.itemKey, payload: input.payload },
            { description: 'Apply the user-defined transition from state B.' },
          );
          break;
        default:
          throw new UnknownEngineStateError(state);
      }
    } catch (error) {
      await persistTransitionFailure(ctx, input, state, {
        status: isUnknownStateError(error) ? 'invalid' : 'failed',
        error: toTypedTransitionError(error),
      });
      throw error;
    }

    try {
      assertAllowedTransition(state, transition.nextState);
    } catch (error) {
      await persistInvalidTransition(ctx, input, state, transition, {
        error: toTypedTransitionError(error),
      });
      throw error;
    }

    await persistTransitionAndHandoff(ctx, input, state, transition);
    return transition;
  },
  {
    description: 'Advance one item through the user-defined state machine.',
  },
);
```

Replace every placeholder with the user's contract. Do not copy the example state names into a real engine.

The example shows dispatch and outcome ordering; its named error and persistence helpers are placeholders for the user's table contract. Implement those helpers with `ctx.customerDb.query(...)`: use schema-qualified Customer DB `INSERT ... ON CONFLICT` mutations keyed by the transition idempotency key for state outputs and deterministic handoff keys for next-state inputs. Persist a typed `failed` output when the child Play rejects and a typed `invalid` output when the state or proposed next state is forbidden, without writing a next-state handoff. After a valid child result, write the completed output first, then the next-state input; replay must repair a missing handoff without duplicating either row. Do not use `ctx.dataset(...)` for engine state tables: it materializes a run-scoped Runtime Sheet, not durable Customer DB state. A dataset may expose an optional per-run view, but it is not the engine's persistence layer. Keep Customer DB reads bounded and provider calls or other transformation work inside the transition Play; call the child through `ctx.runPlay(...)` so retries reuse durable work.

## Advancement choice

Choose one model explicitly:

- **One transition per invocation:** easiest to observe and repair. Choose an explicit supported caller, such as an API/CLI submission, webhook, schedule, or another user-approved dispatch path, to start the next run from the next-state input. Writing an arbitrary Customer DB table does not itself trigger a Play; SQL listeners bind only to supported monitor tool streams.
- **Multiple transitions per invocation:** lower handoff latency, but one run owns more control flow. Persist every state boundary before continuing so a resume does not repeat completed work.

Infer the model from the workflow. When no external event must occur between states, default to multiple transitions through terminal completion. Record the choice and its retry and observability implications. The same state and table contracts apply to both.

## Test matrix

Before publication, prove with static checks and provider-free fixtures:

- every declared state dispatches to the intended transition Play
- every transition reuses a described compatible owned/prebuilt Play or has a checked new transition Play
- every allowed transition writes the correct output and next-state input
- terminal transitions do not enqueue another state
- unknown states and forbidden transitions fail loudly
- transition Play failures retain the input and a typed failure result
- a child result proposing a forbidden next state fails before handoff
- replaying the same transition idempotency key does not duplicate output or handoff rows
- two different business keys remain independent
- the Play passes `deepline plays check <file.play.ts>`

Do not execute a provider during this pre-publication matrix. Defer provider-backed edge tests to the bounded pilot after the caps and workspace gate below are verified. Use synthetic rows for all tests. An explicit request to build an engine authorizes publication. The bounded paid pilot below additionally requires an explicit internal/test workspace or explicit user approval for the paid pilot and scope. It does not authorize real customer rows, trigger installation, a larger run, or unrelated Customer DB mutations.

## Automatic publication and paid pilot

Inspect live Deepline balance and pricing before publishing paid code. Choose the pilot records and calculate the per-run cap. Put a static `billing.maxCreditsPerRun` no greater than the orchestrator cap on every newly authored provider-backed child before its first check or publication, then check and publish the capped children needed for `ctx.runPlay` resolution. A published child is independently callable, so relying only on the parent's inline cap leaves its root-run path unbounded. Never publish an uncapped revision of a newly authored paid child.

Place the static `billing.maxCreditsPerRun` in the orchestrator source before checking or publishing it. A preliminary uncapped live revision creates an avoidable window for unbounded runs, especially if bindings are added later.

Check the capped orchestrator against the live child contracts and publish it once. Verify each publication with `deepline plays get <name> --json`: inspect `play.liveRevision.version` and the static `billing.maxCreditsPerRun` in `play.liveRevision.sourceCode`, not a working revision. Reconcile that version with the publication result and `deepline plays versions --name <name> --json`. `plays describe` and revision summaries omit the billing limit, so they cannot verify a cap by themselves. Report the checked version, published version, live revision, every provider-backed Play's live cap, and any mismatch. Stop on a failed check, publish, or verification instead of publishing a dependent Play against an uncertain contract.

Calculate and disclose the aggregate pilot maximum as `(number of pilot top-level runs + one replay attempt) × billing.maxCreditsPerRun`. A per-run cap resets for each top-level run, so presenting it as the whole pilot bound understates exposure. Do not hardcode a credit-to-currency conversion. If credits are zero or unavailable, stop; quote any CLI-provided recovery commands exactly, but do not run them without approval.

Run without another approval in an explicit internal/test workspace. A customer workspace additionally requires explicit approval for the provider, record count, per-run cap, and aggregate maximum plus a verified supported path for restoring the exact consumed test credits. If either is missing, use an internal/test workspace. Do not turn this into a second design review or ask again between pilot records covered by the same bound.

Submit one representative synthetic record through the published engine and its real paid transitions. Add at most two more synthetic records only when distinct branches need coverage, and keep all records within one bounded pilot. Stop when outputs are wrong, coverage is poor, a required field is missing, or observed cost per usable result is too high. Replaying a completed transition with the same idempotency key must not create another provider charge, output, or handoff. When the engine has no paid transition, run the same live pilot and report zero spend; adding an unrelated provider would test a different workflow.

Show the pilot inputs, final outputs, observed Deepline spend, published `billing.maxCreditsPerRun`, aggregate bound, and replay result in the deliverable. If a customer workspace was used, restore every Deepline credit consumed by the test and verify the resulting balance; include the restoration receipt. Retain exact per-step traces, including provider calls and charges, and offer them on request instead of including them by default. Real customer data, installed triggers, a larger run, or other external side effects require separate approval. Before a larger paid run, show the pilot results, observed spend, proposed scope, and proposed Deepline-credit cap, then ask for explicit approval. Scaling requires a newly checked and published revision with that approved cap; do not silently remove or raise the pilot cap.
