# Evaluation and reviewed-evidence contracts

`validation.play.ts` accepts a CSV with `case_id`, `operation`, `payload_json`, and `today`. Optional columns are `expected_json`, `expected_error`, and `max_age_days` (default 180). Supported operations are `evaluate`, `quality`, `legacy`, `temporal`, and `portfolio`.

- `evaluate`: the existing `scripts/evaluate.py` input object. Its `as_of` and each query's `scored_at` are explicit observation cutoffs.
- `quality`: the existing `scripts/quality.py` reviewed-evidence input. `today` is the explicit clock used by the embedded scorer.
- `legacy`: the existing `scripts/score.py` reviewed-evidence input. `today` is the explicit clock. Output preserves the existing model version, fields, path IDs, and review gates.
- `temporal`: `{left, right, as_of}`. Date precision and conservative overlap are preserved.
- `portfolio`: `{graph, company_id}`. `today` is the explicit source-observation cutoff.

The output records each result and a parity status. `pass` requires matching expected output or the requested validation rejection. `not_checked` means no expected output was supplied. A mismatch or missing expected rejection produces `fail`. A runtime `TypeError` or other unexpected exception does not count as a successful expected rejection. Check these statuses after export: a completed Play is not proof of parity.

Numeric comparisons use an absolute tolerance of `1e-12`. The account bootstrap uses CPython's integer-seeded MT19937 and rejection-sampled `randrange`; it does not substitute JavaScript's random generator. No report permits automatic promotion or claims causal uplift.

## Explicit input limits

The JavaScript transport accepts integer seeds from 0 through `2^53−1`. Python accepts seeds through `2^63−1`. Larger seeds fail instead of being rounded. This is a documented input-range difference.

Evaluator timestamps use extended ISO dates and times with seconds and a timezone: `YYYY-MM-DDTHH:MM:SS[.fraction]Z` or a signed `HH:MM` offset. A space separator and decimal comma are accepted. Exact microseconds are retained; further fraction digits are truncated like Python `datetime`. Other valid Python `fromisoformat` spellings, including basic dates and omitted seconds, are not accepted here. Inputs must use the documented format before comparison.

Raw JSON is parsed with duplicate-key and nonfinite-number rejection. An already parsed object cannot retain evidence of duplicate source keys.

## Report rendering

`reports.ts` exposes `renderLegacy(rows, template)` using `assets/review.html` and `renderEvaluation(report)` using the existing evaluator stylesheet and report content. Tests compare the embedded report, visible evaluation tables, warning list, and script escaping. Whitespace and numeric JSON serialization need not be byte-identical to Python HTML.

The old vendor SQL lookup methods and unreviewed contact-search ranking are not part of `scripts/score.py` and are not exposed by this Play.

## Reproduce

```sh
python3 plays/parity-evaluation.py /private/path/validation-cases.csv
python3 plays/parity-reports.py
deepline plays check plays/validation.play.ts
deepline plays run plays/validation.play.ts --input '{"csv":"/private/path/validation-cases.csv"}' --debug
```

The CSV contains fictional fixtures. Export the run and inspect every `result.parity`; keep run receipts outside the repository. Live provider calls and source-truth checks are separate from this deterministic parity test.
