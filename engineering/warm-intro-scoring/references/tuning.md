# Evidence-preserving weight tuning

Generate a private, standalone artifact (no network requests, credentials, or publication):

```sh
python3 scripts/tuning.py normalized-features.json --output private-tuning.html
python3 scripts/tuning.py normalized-features.json --weights intro-weights.json --output private-tuning-custom.html
```

The destination must not exist; new files use mode 0600. Opening the HTML loads all supplied paths locally. Share the artifact only as intentionally as its underlying evidence. Export weights downloads a plain JSON object containing only the selected weights, suitable for `--weights`.

## Input contract

Input is an object with a required full `YYYY-MM-DD` `as_of` evidence cutoff and a nonempty `paths` list. Connector and target IDs must differ, and connector/target pairs cannot repeat even under different path IDs. Every path must contain unique `id`, `target_id`, `target_name`, `connector_id`, `connector_name`, finite nonnegative `baseline_score`, immutable `review_status` from `needs_confirmation`, `blocked_declined`, or `ready_for_human_review`, and optionally `features`.

```json
{
  "as_of": "2026-09-23",
  "paths": [{
    "id": "owner:connector:target",
    "target_id": "target",
    "target_name": "Target name",
    "connector_id": "connector",
    "connector_name": "Connector name",
    "baseline_score": 80,
    "review_status": "needs_confirmation",
    "features": {
      "work_overlap": {
        "value": 1,
        "evidence_ids": ["receipt-123"],
        "explanation": "Employment overlapped at the same company.",
        "timing_status": "verified_overlap",
        "overlap_start": "2020-06-01",
        "overlap_end": "2021-05-31"
      }
    }
  }]
}
```

Supported keys and default weights:

| Key | Weight |
|---|---:|
| direct_intro | 160 |
| work_overlap | 80 |
| school_overlap | 20 |
| relationship | 15 |
| role_industry | 20 |
| investor_portfolio | 3 |
| appearance | 20 |
| board_overlap | 30 |

Every supplied feature requires numeric `value` in [0,1], a nonempty `explanation`, and a list of `evidence_ids`. Positive values require at least one nonempty evidence ID. `timing_status` is one of `verified_overlap`, `non_overlap`, `unknown`, or `not_applicable`; omission defaults to unknown. Missing dimensions become zero with a visible unknown explanation. Explicit zero can distinguish established non-overlap from missing research through its explanation and timing status.

Positive work, school, and board overlap additionally require `verified_overlap` and full `YYYY-MM-DD` intersection dates `overlap_start` and `overlap_end`, start <= end <= as_of. Do not invent days to upgrade year-only or month-only records. Non-overlapping employment or college attendance contributes zero to the overlap dimension. A shared exact public event can use appearance without a broader tenure interval. The caller must establish that it is the same event and cite that evidence.

`normalize(data)` returns validated independent path dictionaries; `rank(data, config=None)` adds `tuned_score` and `ready_for_human_review` and sorts descending by tuned score. `render(data, config=None)` returns HTML. `weights(config=None)` merges optional overrides with defaults; unknown keys, booleans, negative and nonfinite numbers are rejected. Resulting score overflow is also rejected. Review readiness is true only for the exact status `ready_for_human_review`; the other supported statuses remain held; unrecognized statuses are rejected.

## Interpretation and limitations

Tuned score is the sum of feature value × weight; baseline score is preserved separately and is not added to the tuned score. The default heuristic may differ from the existing baseline model because dimensions are split differently. Defaults are not empirically calibrated. There is no probability or causal claim. Investor weight can exceed all other weights to prioritize portfolio connections without changing any review status, willingness, or evidence.

The UI defaults to top three per target including held paths, with an all-paths view, immediate re-ranking, numeric inputs plus sliders, reset to model defaults, and configuration export. A held path can rank first but is visibly held and gains no send or approval control.

This module validates structure, numerical ranges, citations being present, the evidence cutoff, distinct path pairs, allowed review statuses, and supplied overlap intervals. It does not resolve evidence IDs, verify source truth, infer features from prose, confirm that two appearances refer to the same event, or evaluate overlap from raw biographies. Upstream extraction and review must do that work. Feature explanations and names are inserted as text, and JSON payload HTML delimiters are escaped. A content security policy blocks network requests; the artifact includes no remote assets. Browser configuration downloads follow the browser's filesystem permissions, which this code cannot enforce.

## Date precision and conservative overlap

Use `scripts/temporal.py` after resolving the same employer, school or board identity. It accepts YYYY, YYYY-MM or YYYY-MM-DD without inventing precision. A positive interval is the guaranteed intersection: latest possible start through earliest possible end. Preserve the original dates and explain that the returned days are conservative bounds, not exact employment/attendance dates. If only the possible intervals overlap, return unknown. A missing end never implies current. For a current role, guaranteed tenure stops at the profile's observation date; later tenure remains possible but unverified.

The baseline retained by an artifact can use an older historical snapshot. The tuning artifact must show its own evidence cutoff, and source explanations must identify cached profile dates rather than claiming a fresh profile pull. Public investment observations retrieved later can add context at the newer cutoff, but cannot extend older work/school history.

## Default priority rationale

| Dimension | Maximum default points | Reason |
|---|---:|---|
| Recorded introduction | 160 | Direct observed access is stronger than similarity. |
| Verified work overlap | 80 | Shared employer identity and dated overlap, still not proof of familiarity. |
| School overlap | 20 | Same school and overlapping attendance, not prestige or broad alumni membership. |
| Requester relationship | 15 | Reviewed relationship evidence, not connection-list membership alone. |
| Role/industry | 20 | Professional relevance rather than relationship proof. |
| Investor/portfolio | 3 | Weak company-network context by default. Portfolio-focus preset increases this to 120. |
| Shared public appearance | 20 | Identifiable shared event/episode; general attendance alone is insufficient. |
| Board overlap | 30 | A named board role overlapping the other person's tenure at that company; investor affiliation alone does not qualify. |

These are interpretable initial preferences, not fitted coefficients. Rankings are sorted both within targets and across target groups, so increasing portfolio priority can raise a portfolio target as well as its candidate routes. No tuning setting changes the fixed review status.

## Contact review view

The artifact lists target contacts in a side panel. Select one contact to see its top three possible introduction paths. Each card shows the requester, connector and target. It shows point contributions and the evidence for each positive feature. Open the evidence section to inspect all eight features and their sources. The score has no fixed maximum. It is not a percentage.

Use **Adjust weights** to open the controls. **Download weights** saves only the chosen weights. A change in weight does not change review status. An investor company link can change target priority. It does not prove that a connector knows the target.

Optional context fields do not affect the score:

- Each path can include nonempty `target_company`, `target_title`, `connector_company`, `connector_title` and `requester_name` strings.
- The root can include `requester_name` and `profiles_checked_at` strings. State the source observation date. Do not call a cached role current.
- The root `evidence` list contains records with nonempty `id`, `source`, `detail` and `observed_at` strings. IDs must be unique. Feature source IDs resolve to these records. Use a source URL or a database locator for `source`. Keep `detail` short and factual.
- The root `target_research` object maps each target ID to a list of records. Each record needs nonempty `label`, `detail`, `source_url`, `observed_at` and `provider` strings. These facts appear under **Company research**. They add no score points.

Only HTTP and HTTPS source links are clickable. Other locators appear as text. Names, descriptions and source details appear as text, never as executable HTML. The artifact does not make background requests. A user can open a source link in a new tab.

If an evidence registry is supplied, each positive feature must reference records in that registry. A missing record stops rendering. Inputs without a registry can still show source IDs, but the renderer cannot resolve those IDs. Evidence and company-research observation dates must be full `YYYY-MM-DD` dates at or before the artifact cutoff.

## Fallback features (v2)

Three optional features restore background matches: `city_overlap`, `industry_match`, and `community_match`.
Each has a default maximum of 10 points. Missing inputs stay unknown and add zero points.
These are preference weights, not measured success probabilities. Existing v1 scores can change only when new evidence is supplied.

`city_overlap` requires the same specific city or metro and verified overlap dates.
For job-location evidence, say “work city.” Do not call it a home address or proof that people met.
Exclude remote-only work and broad state or country labels.

`industry_match` requires evidence for both companies or professional histories.
Do not infer industry from a job title. Do not count the same industry fact in `role_industry` as well.
The live v2 report uses `role_industry` for job function only; the old key stays compatible with saved inputs.

`community_match` requires an explicit shared professional group.
Membership alone is weak evidence. Do not infer sensitive affiliations or a personal relationship.
If the same shared activity already supplies appearance points, do not count it again as community evidence.

The three defaults total 30 points. They remain below verified work overlap at 80 points.
Users can change weights. No weight setting changes the review status.

Employment checks must exclude roles that are only board, advisory, or angel-investor appointments.
Do not treat a board location as an employee work location. Use the separate board feature after its evidence passes review.
