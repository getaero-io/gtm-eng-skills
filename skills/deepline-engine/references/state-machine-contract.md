# State machine contract

Use this contract to turn a user-defined workflow into a composable set of Plays: one durable orchestrator plus one child Play for each transformation. The names below describe roles, not required table or field names.

## Transition matrix

Write the matrix before the Play:

| Current state | How state is determined                                        | Input table | Transition Play        | Allowed next states | Output table | Terminal?  |
| ------------- | -------------------------------------------------------------- | ----------- | ---------------------- | ------------------- | ------------ | ---------- |
| `<state>`     | `<explicit field, durable lookup, or user-defined classifier>` | `<table>`   | `<owned/prebuilt/new>` | `<states>`          | `<table>`    | `<yes/no>` |

Do not fill missing cells with guessed business logic. Unknown transitions stay unresolved until the user defines them.

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

The orchestrator composes the selected Play with `ctx.runPlay`. That boundary accepts scalar child Plays only. A child that uses `ctx.dataset()`, `ctx.csv()`, a Runtime Sheet, an event wait, or an explicit timeout owns a separate lifecycle and cannot be used as an inline transition. When no compatible Play exists, author a scalar transition Play and include it in the engine's dependency-ordered check and publication workflow after the user approves publishing.

## Maintained source tree

Generate the engine in a durable project directory that follows the repository's source conventions. Keep these artifacts together:

- orchestrator Play
- newly authored child transition Plays
- shared state and transition types
- README describing the contract, local validation, and approval boundaries
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

The same state and table contracts apply to both.

## Test matrix

Before a real run, prove:

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

Use synthetic rows for these tests. Provider calls, publication, triggers, and real Customer DB mutation require the user's approval.

## Publication order

One explicit user instruction to publish approves the complete publication workflow for the engine. Check all new child Plays, publish the children needed for `ctx.runPlay` resolution, check the orchestrator against the live child contracts, publish the orchestrator, then verify every published version. Do not pause for a second approval between dependency publication and orchestrator publication.

Verify each publication by reconciling the publish result with both `deepline plays describe <name> --json` and `deepline plays versions --name <name> --json`. Report the checked version, published version, live revision, and any mismatch. Stop on a failed check, publish, or verification instead of publishing a dependent Play against an uncertain contract.

Publication approval does not include running the engine, calling providers, installing triggers, or mutating Customer DB. Those actions require separate approval.
