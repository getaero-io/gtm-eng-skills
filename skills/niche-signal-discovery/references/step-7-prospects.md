# Optional prospect and contact handoff

Only source prospects when the user's scope includes it. There is no mandatory top-ten quota. Deliver the requested size or explain the verified shortfall without padding.

Each candidate needs identity, scope, source-backed signals, uncertainty, freshness and CRM category: unknown, net-new verified, existing account, re-engage, active opportunity or current customer. No unvalidated composite score.

The local find_contacts_v2.py helper exports a shortlist WITHOUT buying data and preserves all input columns. --top is optional; omit it for all rows. It does not discover new companies.

The legacy paid contact chain is intentionally retired: deprecated CLI commands, eight-character company matching, guessed LinkedIn-slug names, generic role-token matches and domain-only “validated” emails were unsafe. --contacts now fails before any network call or output write, with directions to the current GTM plays.

For actual contact work, follow deepline-gtm: search/describe the live persona play, verify current employer and requested full role, run the authorized scope, inspect results, and use the described email waterfall plus validation. Do not assume a play is free or hardcode its provider cascade. A provider error is not permission to query a different private workspace.

Keep work identity, deliverability status, raw output, source provenance and unknowns separate. Generic search snippets are candidates, not verified current-employment evidence. Names must come from an actual identity source, not a profile URL slug. No emails/messages are sent by this skill.
