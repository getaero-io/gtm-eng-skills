# Run the example

Run commands from `examples/expert-network`. Local checks need Node.js, npm and Python 3. Deployment also needs the authenticated [Deepline CLI](https://code.deepline.com/agent-install.txt), Customer DB and the providers listed in [PLAYS.md](PLAYS.md).

## Local tests and inputs

```sh
npm ci
npm test
python3 csv-input.py --expert syn-expert-1 --episode demo-2026-11-19 --out /tmp/erm-input.json
```

Tests cover lifecycle branches and replay, queue thresholds, qualification, suppression, uncertain writes and metrics. They call no real providers.

`fixtures/` contains fictional experts, assignments, tasks and usage plus three compiled inputs: complete, waiting and declined. `types.ts` defines the contract. `build-fixtures.py` regenerates fixtures, lifecycle schema and the local type copies needed to bundle child Plays.

## Deploy the synthetic lifecycle

Check `deepline auth status --json` and set the intended workspace. Use an example workspace or inspect existing `storage.erm_*` tables first; names are fixed.

```sh
export ERM_WORKSPACE_ID='YOUR_WORKSPACE_ID'
python3 operate.py check-children
python3 operate.py schema
python3 operate.py publish-children
python3 operate.py publish-parent
python3 operate.py pilot
python3 verify-live.py
```

The pilot runs three inputs and one replay, each with a 1-credit root cap and no paid enrichment. Receipts stay in ignored `evidence/`. Verification compares versions, results and row counts; avoid concurrent runs during that comparison.

The database stores an immutable snapshot per episode and input/output per state. Replaying an episode reuses completed results and repairs interrupted handoffs. New evidence needs a new episode ID. Changed behavior needs versioned Play identities. See [the state diagram](state-machine.mmd), [types](types.ts) and [schema](schema.sql).

## Deploy recruiting

1. Review firms and title filters in `refill/policy.ts`.
2. Set `CAMPAIGN` in `refill/enrollment-policy.ts` to your own dedicated **paused** campaign.
3. Connect the tools and inspect the two prebuilt contracts.

```sh
deepline plays describe prebuilt/person-linkedin-to-company
deepline plays describe prebuilt/person-to-email
python3 refill/deploy.py
python3 refill/deploy-enrollment.py
```

The scripts check `ERM_WORKSPACE_ID`, apply schemas, publish dependencies first and verify caps. Enrollment publication refuses the campaign placeholder.

Start small. These calls use paid providers and can add a contact to the paused campaign:

```sh
deepline run erm-refill-experts-v1 --input '{"batchLimit":1}'
deepline run erm-qualify-enroll-v1 --input '{"limit":1}'
# After reviewing results:
deepline run erm-recruitment-cycle-v1 --input '{"qualificationLimit":5,"refillLimit":100}'
```

The cycle qualifies existing candidates, then refills. Newly sourced people wait for a later call. At 100 it skips both operations; use the standalone qualification batch to process a full backlog.

## Queue and recovery rules

The queue counts unsuppressed research_pending, ready, contacted and onboarding profiles. Profile URLs are unique. A 15-minute lease and capacity checks control refill; qualification has a separate lease.

Recruiting qualification verifies current role/employer and a valid employer-domain email. It does not establish task competence, credentials, availability or consent.

Enrollment requires a paused/draft campaign, complete suppression checks and no existing contact requiring review. Its outbox is unique by campaign/profile and campaign/email. Submitted means acknowledged; confirmed means membership read back. Neither means a message was sent.

For uncertain writes, set `ERM_CAMPAIGN_ID` to the same campaign and run `python3 refill/reconcile-enrollment.py`. It checks membership without resubmitting. `retry-enrollment.py` is limited to two failed records with no outbox claim; inspect them before use. Never blindly retry an ambiguous submission.

No schedule or sending sequence is installed. Before enabling them, supply the real offer, sender, compensation and reply owner; connect delivery, reply and opt-out events to queue updates. Keep real contacts and run receipts out of public Git.
