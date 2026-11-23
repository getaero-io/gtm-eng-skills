# Verification

Run `npm ci && npm test`. Tests use fixtures and mocks, not live providers.

- Lifecycle: allowed branches, missing prerequisites, negative decisions, usage joins, replay, changed-input rejection, invalid edges and interrupted handoffs.
- Queue: capacity at 99/100/101, profile normalization, country/employer mismatch and excluded titles.
- Qualification: identity, role, employer, email validation and incomplete responses.
- Enrollment: paused campaign, suppression pagination/bounds, existing contacts, membership readback, replay and ambiguous writes.
- Metrics: synthetic exclusion, maturity, duplicate events/artifacts, withdrawn acceptance, time boundaries and zero denominators.

For a live deployment, save workspace, published revisions, caps, schema results, fixture outputs, replay row counts, source counts, qualification evidence and membership readback. Keep those receipts and contact records out of public Git.

This package contains no customer deployment receipts. Passing tests do not prove your connections, schedule permissions or campaign. `npm test` does not deploy, call providers or send messages.
