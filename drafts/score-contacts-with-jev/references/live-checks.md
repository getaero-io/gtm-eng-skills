# Live checks: what was run, and what was not

## The Deepline port (2026-09-30)

| # | What | Result |
|---|---|---|
| 1 | `scripts/test_offline.py` | Every check passes: the scoring code under `node`, the arithmetic, failures by error category, abstentions, disqualifiers, reasons, rubric checks, mapping, the rendered play |
| 2 | `deepline plays check` on the play rendered from `rubric.example.json` | Valid: 1 trigger (webhook), 1 tool (`ai_evaluate`), 1 dataset, 15 columns, 1 output |
| 3 | `build_scorer.py --plan` against a real workspace | Rendered, checked, nothing published |

**Not run live for the port:** an `ai_evaluate` call (the answer shape is from the evaluation API's
types and Deepline's tool documentation, not an observed response), `plays publish`, a play run,
the webhook, and `smoke_test.py`. The first preview is therefore also the first live test of the
answer parsing: if a preview record comes back `failed` with "Jev returned no answers", run one
`deepline tools execute ai_evaluate --input @body.json --json` and compare its
`toolResponse.raw.result.answers` with `references/jev-api.md`. Deepline's per-call charge for
`ai_evaluate` was not observed; read it in `deepline billing` after the preview.

## Earlier, on Clay (a test workspace, 2026-09-29)

The skill was first built as a Clay workflow calling Jev (`jev-1.13.0`) directly with a TypeSafe
key. These results were measured there; they carry over only as evidence about Jev and the rubric
logic, not about the Deepline route:

- A six-company preview of the example rubric parsed real Jev answers on every path: a distributor
  98 A; a competitor `disqualified` by a rule with no Jev call; a logistics firm `disqualified` by
  Jev at ≥ 80%; a blank record `insufficient_data`; unsure answers listed for review; about $0.0001
  in total at TypeSafe's price.
- A six-person contact preview: a VP of Operations at an A-tier account 96 A; a recruiter
  `disqualified`; no title `not_scored`; a time-in-role date rule scored.
- One account and one contact through the hosted workflow matched the local preview exactly
  (98 A and 96 A), and a real webhook POST scored 48 B with `source_ref` echoed.
