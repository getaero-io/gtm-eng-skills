# CRM Cleanup With Outcome Checks

Office-hours example from May 7, 2026.

Use explicit good examples and outcome checks to clean account and contact data without hiding failures behind fuzzy fallbacks.

## Flow

1. Define the cleanup outcome in stable interface terms: valid domain, normalized company, reachable contact, owner, lifecycle stage, and reason.
2. Give the agent 3-5 good rows and 3-5 bad rows before asking it to transform a whole export.
3. Validate each row with deterministic checks before writing back to CRM.
4. Route ambiguous rows to review instead of guessing.
5. Emit a change report with counts by reason.

## Files

- `cleanup.ts` - TypeScript helpers for row validation and review routing.
