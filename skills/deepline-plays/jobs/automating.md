# Automating stage graphs

Use this for webhook, cron, monitor, review-gated, and activation Plays. The
trigger starts a stage graph; it does not change the truth contract of each
search, enrichment, signal, or scoring stage. This page is complete for that job.

## What replay actually costs

A receipt is content-addressed on tool plus input, and the cache is workspace-
global, not run-scoped. Measured on a 3-row email waterfall: first run 0.31
credits, identical rerun 0.01 (the compute tick; `providerEvents: 0`). A third
run over a different CSV sharing two rows also charged 0.01. So a rerun is a
resume — edit a stage, rerun, and the completed prefix re-pays nothing. There is
no separate resume switch.

Two consequences for automation. Keep reuse keys stable: rename an input and you
change the key and re-pay, which is why one play file edited in place beats
`-v2` / `-final` variants. And one bad row does not sink the run — a blank row in
a 3-row CSV completed with `status: completed`, `errors: []`, only the two valid
rows dispatched, and the blank row exported with an empty value and no
fabrication.

## Freeze the execution contract

Write:

- **trigger:** webhook payload, schedule, or provider event;
- **identity:** the stable event or row key used for replay;
- **stage graph:** inputs, outputs, and seams for every stage;
- **decision boundary:** which evidence permits each branch;
- **review boundary:** automatic, human-approved, or dry-run only;
- **side effects:** systems touched and idempotency keys;
- **receipt:** durable proof that an action was planned or applied.

Reuse existing Plays for proven stages. Run the search experiment only on an
uncertain edge, then embed the learned waterfall in the larger graph.

## Choose the trigger

| Trigger | Use when                                           | Key requirement                         |
| ------- | -------------------------------------------------- | --------------------------------------- |
| Webhook | One inbound event should start work immediately    | Validate payload and stable event ID    |
| Cron    | A bounded population needs periodic recomputation  | Time window, overlap, and stale policy  |
| Monitor | A provider event stream supplies candidate signals | Capability-registry event identity      |
| Manual  | A person intentionally launches a batch            | Explicit input artifact and run receipt |

Trigger fields are `definePlay` authoring contracts, not comments or returned
metadata. Bind the trigger in the third argument, then run `plays check`:

```typescript
export default definePlay(
  'inbound',
  async (ctx, input: Input) => {
    // durable stages
  },
  { webhook: {} },
);

export default definePlay(
  'daily-sync',
  async (ctx) => {
    // durable stages
  },
  { cron: { schedule: '0 9 * * *' } },
);
```

Add webhook HMAC options when the sender supports signing. A draft may remain
unpublished; the binding still belongs in the authored Play.

## Separate planning from execution

A **dry-run** returns the exact intended operation without calling the external
system. Include destination, normalized payload, idempotency key, prerequisite
evidence, and the reason the operation would or would not run.

An **execution** stage performs the side effect through a described connector
and retains its receipt. Use the same payload builder for dry-run and execute so
reviewed intent cannot drift from applied intent.

```text
evidence → decision → planned operation → review gate → idempotent execution
```

Unknown evidence routes to `needs_review`, not the positive branch. A model may
classify bound facts; it cannot fill missing firmographics or signals.

## Webhook and cron discipline

- Keep webhook handlers small: validate, normalize, then enter durable stages.
- Give every stage a stable key derived from semantic identity, not wall time.
- Define cron lookback windows with deliberate overlap and evidence freshness;
  deduplicate on source event identity.
- Put campaign, CRM, audience, and messaging calls after the explicit review or
  execution boundary.
- Preserve rejected, skipped, and unresolved branches in the output ledger.

## Complete when

The Play checks; every branch has a mechanical predicate; dry-run paths make no
external writes; execution paths are idempotent; and the result exposes trigger
input, stage decisions, planned/applied operations, and receipts.
