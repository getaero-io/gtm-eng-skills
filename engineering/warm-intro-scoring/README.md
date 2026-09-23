# Warm-intro scoring — engineering handoff

**Start here.** This folder is a self-contained, offline scoring/evaluation package. Keep it outside the generated `skills/` tree. Copy this entire folder into another checkout if needed; Python 3.10+ is the only requirement. No install, credentials, customer database or provider calls are needed for the tests.

```bash
python3 engineering/warm-intro-scoring/check_all.py
```

From inside this folder, the same command is `python3 check_all.py`. It verifies pinned dependencies, runs unit/scoring checks, audits fictional evidence, and generates temporary artifact outputs. Nonzero exit means the handoff is failing.

## Try it

Run from this folder; use fresh output names because scripts refuse overwrite:

```bash
python3 scripts/quality.py assets/example.json --output quality.json
python3 scripts/score.py assets/example.json --output scores.csv
python3 scripts/render.py scores.csv --output paths.html
python3 scripts/evaluate.py assets/evaluation-example.json --output evaluation.json --html evaluation.html
```

Open `paths.html` for the top-three path review or `evaluation.html` for the comparison scorecard. These examples are fictional. The evaluator deliberately reports insufficient evidence.

## What the team is getting

| File | Purpose |
|---|---|
| `SKILL.md` | Agent workflow: warm connections + optional targets, enrichment, scoring, artifact |
| `scripts/quality.py` | Pre-scoring quality audit of the existing reviewed-evidence JSON contract |
| `scripts/score.py`, `render.py` | Deterministic scoring and interactive evidence review |
| `scripts/evaluate.py` | Paired rankings, account-cluster intervals, fixed-window outcome evaluation |
| `assets/customer-db.sql` | PostgreSQL reference migration; inspect tenant and current schema before applying |
| `references/pipeline.md` | Incremental DB → enrichment → features → scoring deployment contract |
| `references/evaluator.md` | Labeling, research-derived challenges, statistical limits |
| `vendor-manifest.json` | Source commit and checksums for the five pinned runtime dependencies |

The defaults use `vendor/`, independent of the repository's examples and refreshable skills directory. The manifest protects against silent drift. When intentionally refreshing the baseline, review the upstream diff, update the pinned files and hashes together, and rerun checks. The original MIT license is included. Vendored ask code is used only to verify CSV compatibility; `check_all.py` never generates or sends asks.

## Checks added

- Profile identity collisions; conflicting identity values across paths; malformed URLs.
- Missing job history, company or title, reported as unknown with coverage counts.
- Missing/invalid evidence references via the scorer's existing validation.
- Stale receipts and duplicate source receipts, reported as warnings.
- Future employment ends, current-job/end-date contradictions and empty candidate sets.
- Private quality reports and nonzero exit on blocking data errors.

Existing tests cover both-edge holds, latest declines, future features, train/test leakage, ranking math, grouped bootstrap, unknown judgments, mature outcome denominators, horizon boundaries, malicious HTML content and no-overwrite output.

`quality.py` exits **0** for structural pass (warnings can remain), **1** for data-quality failures and **2** for malformed JSON/I/O. Freshness defaults to 180 days relative to the scoring cutoff and is configurable with `--max-age-days`; this is an operational threshold, not a validated relationship-decay weight. Quality reports use IDs and counts, not copied profile prose.

## Before connecting production

Implement the provider/DB adapters in `references/pipeline.md`; the SQL and trigger pattern are not deployed. The offline checker does not verify that a profile is full or true, query live tables, or implement queue workers. Deployment acceptance must cover transaction rollback, duplicate event replay, lease expiry, out-of-order profile updates, removals, stale artifact invalidation and no extra paid calls after retry. Use source run receipts to reconcile contacts requested/enriched/partial/failed before accepting a batch. Enforce tenant-scoped keys and access controls in the actual database.

Keep raw profiles, connection exports, credentials and real-person artifacts private. Historical data lacks outcome-complete labels; passing this suite does not establish prediction accuracy or business uplift.

## Forward this to the team

> The warm-intro handoff lives in `engineering/warm-intro-scoring/`, outside the refreshable skills folder. Run `python3 engineering/warm-intro-scoring/check_all.py` with Python 3.10+. It is offline and credential-free. Start with README.md; the fixtures demonstrate scoring, data-quality reports and evaluation artifacts. Production work remaining is the scoped DB/provider/trigger adapter and independently labeled outcomes, not scoring-model deployment based on synthetic results.

## Adjustable preferences and company networks

```bash
python3 scripts/tuning.py assets/tuning-example.json --output tuning.html
python3 scripts/tuning.py assets/tuning-example.json --weights assets/portfolio-focus.weights.json --output portfolio-focus.html
```

Independent controls cover recorded intros, dated work/school overlap, requester relationships, role/industry, shared investor portfolios, public appearances dated board overlap, work city, industry and professional community. Export a config to reuse it. The baseline score and holds remain fixed. See `references/tuning.md` for the input contract and `references/company-network.md` for investor discovery/portfolio expansion. Real customer snapshots and research graphs stay outside Git.

## Target-first report

The report shows one target at a time. Select a contact, compare intro paths, then inspect each score breakdown.
Use the weight panel to change ranking preferences. Weight changes do not confirm relationships or permission.
Company research can show source-backed facts from external providers. It does not automatically add score points.
See [external evidence](references/external-data.md) and [clear output rules](references/readable-output.md).
