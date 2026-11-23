# Optional Exa Time Machine

The base combined workflow uses fresh deeplineagent research. To compare historical and current
observations automatically, use your own Exa key. Deepline's managed `exa_contents` tool has no
`snapshotAsOf` input, so the runner calls Exa through Deepline `generic_http_request`.

1. Export the key in the shell that runs the script: `export EXA_API_KEY=...`. Do not paste the
   key into chat, a contact row, a shared brief, or a prompt.
2. Run with `--exa`:

```bash
python3 scripts/run.py --state PRIVATE_RUN_DIR --brief PRIVATE_BRIEF.json \
  --audience-brief "Your people audience" --max-people 5 --exa --start
```

The runner reads `EXA_API_KEY` only at call time and sends it as the `x-api-key` header; it is
not written to the graph or any run record. Exa requests run only after the person's email
passes verification.

In brief_json set comparison_mode to before_after, comparison_as_of to a past YYYY-MM-DD,
comparison_focus to the kind of shift that matters, and optionally comparison_page_path
(default `/`, for example `/pricing`). The employer domain comes from the actual person.

Two `generic_http_request` calls POST to https://api.exa.ai/contents. Each requests exactly one
same-company URL: the historical call uses snapshotAsOf; the current call uses maxAgeHours=0.
The normalizer requires successful responses, matching URLs, request IDs, substantive
text and a freshly crawled current response. In strict `before_after` mode it fails on unknown response envelopes or
unavailable history. In `auto` mode it preserves available valid observations, records
why a side is unavailable, and allows deeplineagent to find an independently verified dated
event. Missing history never supports a comparison. Copy independently checks that the observations support a real shift.

snapshotAsOf is a retrieval cutoff, not a capture date or the date the business changed.
Published dates do not establish historical captures. Changed messaging does not prove a
new operational need. No history means no before-and-after claim. Strict comparison holds; auto may use a verified dated event.

The API key must have applicable Snapshot access. Coverage, trial caps and entitlement vary.
Run one real company and inspect both outputs in the person's run record before scaling.
Fixture tests do not prove an authenticated call. Exa bills your key separately from Deepline
credits (`generic_http_request` itself is free); no fixed price is promised.

Official reference: https://exa.ai/docs/reference/get-contents.
