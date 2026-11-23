# Run and adapt the example

Run commands from `examples/expert-network`. Local tests need Node.js, npm and Python 3. Live use also needs the authenticated [Deepline CLI](https://code.deepline.com/agent-install.txt), Customer DB access, named prebuilt Plays and connected provider tools. The runtime supplies the `deepline` SDK during Play execution.

## Local checks

```sh
npm ci
npm test
python3 build-fixtures.py
python3 csv-input.py --expert syn-expert-1 --episode demo-2026-11-19 --out /tmp/erm-input.json
```

The generator recreates CSVs, JSON fixtures, schema and child type copies. Three cases complete, wait for revision, and decline. Keep synthetic markers and source references. Tests use no real contacts.

## Publish the synthetic lifecycle

Inspect `deepline auth status --json`, then set `ERM_WORKSPACE_ID` to your intended workspace ID. The operation script refuses a different or unset workspace. Schema and publish commands change that workspace; pilot commands run the published Plays.

```sh
export ERM_WORKSPACE_ID='YOUR_WORKSPACE_ID'
python3 operate.py check-children
python3 operate.py schema
python3 operate.py publish-children
python3 operate.py publish-parent
python3 operate.py pilot
```

The pilot executes three snapshots and one identical replay, with a 1-credit root cap each. Receipts go under ignored `evidence/`. No paid provider calls occur. Use a separate example workspace or review existing `storage.erm_*` tables first: table and Play names are fixed.

`operate.py pilot` captures `evidence/counts-before-replay.json` before its replay. After all four runs succeed, run `python3 verify-live.py` to reconcile results, published versions/caps and unchanged durable row counts. Local tests also verify replay without live credentials. Do not run concurrent workflows while comparing those live table counts.

## Publish recruiting

Review the employer allowlist and title filters in `refill/policy.ts`. Set your dedicated paused campaign in `refill/enrollment-policy.ts`. The placeholder is not a usable destination. Ensure connected tools can read complete suppressions and campaign membership.

```sh
deepline plays describe prebuilt/person-linkedin-to-company
deepline plays describe prebuilt/person-to-email
python3 refill/deploy.py
python3 refill/deploy-enrollment.py
```

Scripts require the same `ERM_WORKSPACE_ID`, apply schemas, publish dependencies before parents and verify live caps. Enrollment publication refuses the unconfigured campaign placeholder. They do not install triggers. Use the current CLI help/contract if a command changes. No deployment was performed when publishing this example.

Begin with bounded provider calls; these incur usage and may add a contact to the paused campaign:

```sh
deepline run erm-refill-experts-v1 --input '{"batchLimit":1}'
deepline run erm-qualify-enroll-v1 --input '{"limit":1}'
# After inspecting results:
deepline run erm-recruitment-cycle-v1 --input '{"qualificationLimit":5,"refillLimit":100}'
```

At 100 the cycle skips both operations. Use the standalone qualification batch for a full backlog. Qualification processes existing rows before refill; newly found people wait for another call.

Recurring operation needs trigger permissions, queue progression from real events and a verified paused-campaign test. Sending is a separate integration; see the [outreach contract](refill/outreach-contract.md).

## Diagrams

Source and renders are included. Optional rebuilding needs D2 with ELK and Playwright Chromium:

```sh
d2 --layout elk diagrams/expert-flow.d2 diagrams/expert-flow-d2.svg
d2 --layout elk diagrams/expert-flow.d2 diagrams/expert-flow-d2.png
npx playwright install chromium
node diagrams/build-options.mjs
```

The generator uses the included HTML, not a private skill installation. Excalidraw has an editable scene and geometric preview. External HTML export libraries need network access.
