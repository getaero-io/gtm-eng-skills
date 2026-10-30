#!/usr/bin/env python3
"""Train an artifact-backed scorecard (lift model by default, propensity model on request).

Input: a feature CSV with one row per account. Required: an id column (default `domain`), a
`status` column (`won|lost|lookalike|unlabeled`) or an explicit 0/1 `--y-col`, and feature columns
(booleans, numerics, categoricals). Optional `split` column: rows marked `validation` or `holdout`
are never used to bin, fit, calibrate or build the reference; they are scored and labeled as such.

Feature columns are an allowlist: pass `--features a,b,c`, or omit it to use every column except
the id/status/split/coverage columns and a built-in denylist of outcome-bearing CRM fields
(deal_labels, lifecyclestage, amount, closedate, ...). A denylisted column that is not excluded is
an error, never a silent drop.

Modes:
  lift        (default) additive WOE points, no fitted weights; works at small n. Probabilities are
              the uncalibrated sigmoid of the logit unless --calibrate is passed.
  propensity  L1 logistic regression on WOE bins, isotonic calibration, learned A/B/C tiers.
              Refused below --min-positives (default 100) unless --force.

The validation metrics in model_lift.csv / bucket reports come from the stratified tuning split that
also serves calibration and tier cuts; they are not an untouched holdout and run_meta says so.

Outputs (out_dir): preprocess.json, specs.json, model.json, training_set.csv, points_table.csv,
scorecard_explainer_{binned,raw}.csv, feature_summary.csv, model_lift.csv, bucket_report_*.csv,
storytelling.csv, tier_lifts.csv (propensity), scores.csv (every input row), reference.json,
model_contract.json + contract_sample.json (replay scorer), run_meta.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from scorecard import (  # noqa: E402
    RunConfig,
    apply_preprocessing_config,
    build_preprocess_config,
    build_top_contributors,
    generate_reports,
    train_scorecard,
)
from scorecard.explainer_artifacts import write_explainers_to_csv  # noqa: E402

STATUS_TO_Y = {"won": 1, "lost": 0}
EXCLUDED_SPLITS = {"validation", "holdout"}
DENYLIST = {"deal_labels", "deal_names", "pipelines", "lifecyclestage", "amount", "closedate", "close_date",
            "hs_is_closed", "hs_is_closed_won", "dealstage", "label", "outcome", "won", "lost", "status",
            "known_at", "scored_at", "name", "deepline_icp_fit", "deepline_icp_fit_reason", "hubspot_description",
            "website", "jobs", "website_status", "jobs_status", "company_createdate", "createdate"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--mode", choices=["lift", "propensity"], default="lift")
    p.add_argument("--id-col", default="domain")
    p.add_argument("--y-col", default=None)
    p.add_argument("--status-col", default="status")
    p.add_argument("--split-col", default="split")
    p.add_argument("--features", default="", help="Comma-separated feature allowlist (default: all non-excluded columns)")
    p.add_argument("--exclude-cols", default="", help="Comma-separated columns to drop in addition to the denylist")
    p.add_argument("--coverage-cols", default="", help="Comma-separated coverage columns; a row with none equal to `success` is unscorable")
    p.add_argument("--dimension", default="account_fit", choices=["account_fit", "lead_fit"],
                   help="Fit dimensions only; engagement models need event windows and first-party observations this CLI does not produce")
    p.add_argument("--test-size", type=float, default=0.30)
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--scale", type=int, default=10)
    p.add_argument("--l1-C", type=float, default=1.0)
    p.add_argument("--n-bins-numeric", type=int, default=5)
    p.add_argument("--max-low-card", type=int, default=25)
    p.add_argument("--min-positives", type=int, default=100)
    p.add_argument("--min-rows", type=int, default=20)
    p.add_argument("--calibrate", action="store_true", help="Lift mode: fit isotonic calibration on the tuning split")
    p.add_argument("--woe-prior", type=float, default=None, help="Pseudo-count per bin (default 0.5; lift mode defaults to 1.0 below 50 fit rows)")
    p.add_argument("--max-features", type=int, default=None, help="Keep only the top-IV features (lift mode defaults to 12 below 50 fit rows)")
    p.add_argument("--max-abs-points", type=int, default=None, help="Clip per-bin points (lift mode defaults to 2*scale below 50 fit rows)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--model-id", default=None)
    return p.parse_args()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def midrank_percentile(reference: np.ndarray, scores: np.ndarray) -> np.ndarray:
    less = np.searchsorted(reference, scores, side="left")
    le = np.searchsorted(reference, scores, side="right")
    return 100.0 * (less + (le - less) / 2.0) / float(len(reference))


def grade_of(pct: np.ndarray) -> list:
    return [None if not np.isfinite(v) else ("A" if v >= 90 else "B" if v >= 75 else "C" if v >= 50 else "D") for v in pct]


def main() -> None:
    args = parse_args()
    src, out = Path(args.input), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "overrides.json").exists():
        sys.exit(f"refused: {out}/overrides.json exists; overrides belong to a scored model version, not a fresh training run")
    df_all = pd.read_csv(src, dtype=str, keep_default_na=False)
    df_all = df_all.replace({"": np.nan})
    if args.id_col not in df_all.columns:
        sys.exit(f"id column {args.id_col!r} not in CSV")

    # ---- labels and splits ----------------------------------------------------
    if args.y_col:
        y_all = pd.to_numeric(df_all[args.y_col], errors="coerce")
        label_source = args.y_col
    else:
        if args.status_col not in df_all.columns:
            sys.exit(f"status column {args.status_col!r} not found; pass --y-col or add a status column")
        y_all = df_all[args.status_col].astype(str).str.strip().str.lower().map(STATUS_TO_Y)
        label_source = f"{args.status_col} (won=1, lost=0; other statuses unlabeled)"
    labeled = y_all.notna()
    split_vals = df_all[args.split_col].astype(str).str.strip().str.lower() if args.split_col in df_all.columns else pd.Series("", index=df_all.index)
    unknown_split = set(split_vals.dropna().unique()) - {"", "nan", "discovery", "train", "validation", "holdout"}
    if unknown_split:
        sys.exit(f"unknown split values {sorted(unknown_split)}; use discovery/train or validation/holdout")
    excluded_split = split_vals.isin(EXCLUDED_SPLITS)
    fit_mask = labeled & ~excluded_split
    coverage_cols = [c for c in (x.strip() for x in args.coverage_cols.split(",")) if c] or [c for c in df_all.columns if c.startswith("coverage__")]
    # ---- eligibility: identity + evidence ------------------------------------------
    ids = df_all[args.id_col].astype(str).str.strip()
    miss_reason = pd.Series("", index=df_all.index, dtype=object)
    miss_reason[ids.isin(["", "nan"])] = "missing_identity"
    if coverage_cols:
        ok = np.zeros(len(df_all), dtype=bool)
        for c in coverage_cols:
            ok |= df_all[c].astype(str).str.strip().str.lower().eq("success").values
        miss_reason[(miss_reason == "") & ~ok] = "no_usable_evidence"
    eligible = miss_reason == ""
    fit_mask = fit_mask & eligible


    n_fit, n_pos = int(fit_mask.sum()), int(y_all[fit_mask].sum())
    n_neg = n_fit - n_pos
    refusal = None
    if args.mode == "propensity" and n_pos < args.min_positives:
        refusal = f"propensity mode needs >= {args.min_positives} positives, found {n_pos}; use --mode lift or --force"
    if args.mode == "lift" and (n_fit < args.min_rows or n_pos < 3 or n_neg < 3):
        refusal = f"lift mode needs >= {args.min_rows} labeled rows and >= 3 of each outcome, found {n_pos} won / {n_neg} lost"
    if refusal and not args.force:
        sys.exit("refused: " + refusal)

    # ---- feature allowlist ------------------------------------------------------
    exclude = {c for c in (x.strip() for x in args.exclude_cols.split(",")) if c}
    structural = {args.id_col, args.status_col, args.split_col, "account_id", "parent_id"} | set(coverage_cols) | exclude
    if args.y_col:
        structural.add(args.y_col)
    if args.features:
        feature_cols = [c for c in (x.strip() for x in args.features.split(",")) if c]
        missing = [c for c in feature_cols if c not in df_all.columns]
        if missing:
            sys.exit(f"--features not in CSV: {missing}")
        clash = [c for c in feature_cols if c in structural]
        if clash:
            sys.exit(f"refused: --features includes id/label/split/coverage columns: {clash}")
    else:
        feature_cols = [c for c in df_all.columns if c not in structural]
    denied = [c for c in feature_cols if c.lower() in DENYLIST]
    if denied:
        sys.exit(f"refused: outcome-bearing or non-feature columns in the feature set: {denied}. Exclude them or name an explicit --features list")
    if not feature_cols:
        sys.exit("no feature columns left")

    X_all_raw = df_all[feature_cols].copy()
    numeric_cols = []
    for c in feature_cols:  # type policy is decided on fit rows only; other rows are coerced to it (unparsable -> missing)
        s = X_all_raw.loc[fit_mask, c]
        num = pd.to_numeric(s, errors="coerce")
        if s.notna().any() and (num.notna() == s.notna()).all() and not set(s.dropna().str.lower().unique()) <= {"0", "1", "true", "false"}:
            numeric_cols.append(c)
            X_all_raw[c] = pd.to_numeric(X_all_raw[c], errors="coerce")
    constant = [c for c in feature_cols if X_all_raw.loc[fit_mask, c].nunique(dropna=False) <= 1]
    if constant:
        X_all_raw = X_all_raw.drop(columns=constant)
        feature_cols = [c for c in feature_cols if c not in constant]
    if not feature_cols:
        sys.exit("every feature is constant on the fit rows")

    # ---- one split, shared by preprocessing and the trainer --------------------------
    X_fit_raw = X_all_raw.loc[fit_mask].reset_index(drop=True)
    y_fit = y_all[fit_mask].astype(int).reset_index(drop=True)
    split_size = args.test_size if min(n_pos, n_neg) >= 4 else 0.5
    pre_cfg = build_preprocess_config(X_fit_raw, y_fit, n_bins_numeric=args.n_bins_numeric, n_bins_cat_high=6,
                                      max_low_card=args.max_low_card, test_size=split_size, random_state=args.random_state)
    X_fit = apply_preprocessing_config(X_fit_raw, pre_cfg)

    small = n_fit < 50
    woe_prior = args.woe_prior if args.woe_prior is not None else (1.0 if (args.mode == "lift" and small) else 0.5)
    max_features = args.max_features if args.max_features is not None else (12 if (args.mode == "lift" and small) else None)
    max_abs_points = args.max_abs_points if args.max_abs_points is not None else (2 * args.scale if (args.mode == "lift" and small) else None)
    run_cfg = RunConfig(
        y_col="__Y__", method="naive_bayes" if args.mode == "lift" else "logistic",
        woe_prior=woe_prior, max_features=max_features, max_abs_points=max_abs_points,
        test_size=split_size, random_state=args.random_state,
        do_calibration=(args.mode == "propensity") or args.calibrate,
        n_bins_numeric=args.n_bins_numeric, n_bins_cat_high=6, max_low_card=args.max_low_card,
        l1_C=args.l1_C, scale=args.scale, top_share=0.10, gate={"enable": False},
        tiers={"enable": args.mode == "propensity", "precA_min": 0.40, "covA_max": 0.12},
    )
    outputs = train_scorecard(X_fit, y_fit, config=run_cfg)
    pipe = outputs["pipeline"]

    # ---- artifacts ------------------------------------------------------------------
    for key, name in (("scorecard", "scorecard.csv"), ("condensed_scorecard", "condensed_scorecard.csv"),
                      ("feature_summary", "feature_summary.csv"), ("model_lift", "model_lift.csv"),
                      ("tier_lifts", "tier_lifts.csv"), ("decile_lift", "decile_lift.csv")):
        v = outputs.get(key)
        if isinstance(v, pd.DataFrame) and not v.empty:
            v.to_csv(out / name, index=False)
    (out / "model_meta.json").write_text(json.dumps(outputs.get("model_meta", {}), indent=2, default=float))
    raw_with_y = pd.concat([y_fit.rename("__Y__"), X_fit_raw], axis=1)
    generate_reports(pipe, out_dir=str(out), features_config=pre_cfg, raw_df=raw_with_y, y_col="__Y__")
    pipe.save_artifacts(str(out))
    (out / "preprocess.json").write_text(json.dumps(pre_cfg, indent=2))
    training = raw_with_y.copy()
    for col in X_fit.columns:
        training[col] = X_fit[col].values
    training.to_csv(out / "training_set.csv", index=False)
    write_explainers_to_csv(str(out / "preprocess.json"), str(out / "specs.json"), str(out / "training_set.csv"), "__Y__", str(out))

    # ---- score every row against the frozen model -------------------------------------
    X_all = apply_preprocessing_config(X_all_raw, pre_cfg)
    scored = pipe.score(X_all)
    points = scored["raw_points"].astype(int)
    prob = scored["model_prob"].astype(float)
    logit = float(pipe.model_.intercept_) + points.astype(float) / float(pipe.model_.scale_)
    drivers = build_top_contributors(scored["breakdown"], X_all_raw, pre_cfg, top_n=5)
    reference_points = np.sort(points[fit_mask.values].to_numpy())
    pct = midrank_percentile(reference_points, points.to_numpy().astype(float))
    if len(np.unique(reference_points)) < 2:
        pct[:] = np.nan
        miss_reason[eligible] = "insufficient_reference_variation"
    pct = np.where(eligible.values, pct, np.nan)
    tiers = pipe.apply_policy_and_tiers(df=X_all, raw_points=points)["tier"] if getattr(pipe, "tier_cuts_", None) else None

    model_id = args.model_id or f"{args.dimension}-{args.mode}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    role = np.where(excluded_split, split_vals.where(excluded_split, ""), np.where(labeled, "train", "unlabeled"))
    scores = pd.DataFrame({
        args.id_col: df_all[args.id_col].values,
        "label": y_all.values, "row_role": role,
        "points": np.where(eligible, points.values, np.nan),
        "logit": np.where(eligible, logit.values, np.nan),
        "probability": np.where(eligible, prob.values, np.nan),
        "percentile": pct, "grade": grade_of(pct),
        "top_contributors": np.where(eligible, drivers.values, ""),
        "model_id": model_id,
        "status": np.where(np.isfinite(pct), "scored", "unscored"),
        "miss_reason": miss_reason.values,
    })
    if tiers is not None:
        scores["tier"] = np.where(eligible, tiers.values, None)
    scores.to_csv(out / "scores.csv", index=False)

    # ---- frozen reference + replay contract (matches scripts/scoring_contract.ts) --------------
    frozen_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scale = int(pipe.model_.scale_); intercept = float(pipe.model_.intercept_)
    reference = {"id": f"{model_id}-ref", "model_id": model_id, "dimension": args.dimension,
                 "scores": [float(int(round(intercept * scale)) + p) for p in reference_points],
                 "population": f"{src.name} fit rows (n={n_fit})", "frozen_at": frozen_at,
                 "note": "scores are round(intercept*scale) + points, the integer-exact quantity scoring_contract.ts computes"}
    (out / "reference.json").write_text(json.dumps(reference, indent=2))
    points_by_feature = {f: {b: int(p) for b, p in fb.points_map.items()} for f, fb in pipe.model_.features_.items()}
    contract = {
        "id": model_id, "dimension": args.dimension, "intercept": int(round(intercept * scale)), "scale": scale,
        "intercept_exact": intercept,
        "weights": {f: 1.0 for f in points_by_feature},
        "max_age_days": {f: 365 for f in points_by_feature},
        "validation": "exploratory",
        "points_by_feature": points_by_feature,
        "preprocess": pre_cfg,
        "observation_rule": "one observation per feature; value = points_by_feature[feature][bin of the row after preprocess]. "
                            "score = intercept + sum(points), with intercept pre-rounded to integer points so the sum is exact in "
                            "floating point; logit ~= score/scale (use intercept_exact for probabilities); "
                            "percentile against reference.json, which stores the same scaled logits. "
                            "Calibrated probability and tiers are not available in the TypeScript scorer.",
    }
    (out / "model_contract.json").write_text(json.dumps(contract, indent=2))
    sample_rows = [int(i) for i in np.flatnonzero(eligible.values)[:3]]
    sample = []
    for i in sample_rows:
        obs = []
        for f in points_by_feature:
            b = str(X_all.iloc[i][f])
            obs.append({"entity_id": str(df_all[args.id_col].iloc[i]), "feature": f, "value": int(points_by_feature[f].get(b, 0)),
                        "dimension": args.dimension, "source_class": "external", "source_id": f"{src.name}#{i}",
                        "known_at": frozen_at, "event_at": frozen_at, "retrieved_at": frozen_at,
                        "status": "observed"})
        sample.append({"entity_id": str(df_all[args.id_col].iloc[i]), "observations": obs,
                       "expected": {"logit": float(int(round(intercept * scale)) + int(points.iloc[i])), "percentile": None if not np.isfinite(pct[i]) else float(pct[i]),
                                    "grade": grade_of(np.array([pct[i]]))[0]}})
    scored_at = (datetime.now(timezone.utc).replace(microsecond=0) + __import__("datetime").timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    (out / "contract_sample.json").write_text(json.dumps({"scored_at": scored_at, "rows": sample}, indent=2))

    vr = pipe.validation_report() or {}
    meta = {
        "model_id": model_id, "mode": args.mode, "method": run_cfg.method, "dimension": args.dimension,
        "input": str(src), "input_sha256": sha256_file(src), "label_source": label_source,
        "rows_total": int(len(df_all)), "rows_labeled": int(labeled.sum()), "rows_fit": n_fit,
        "positives": n_pos, "negatives": n_neg, "rows_excluded_split": int(excluded_split.sum()),
        "rows_unlabeled": int((~labeled).sum()), "rows_unscored": int((scores["status"] == "unscored").sum()),
        "unscored_reasons": scores.loc[scores["status"] == "unscored", "miss_reason"].value_counts().to_dict(),
        "features": feature_cols, "numeric_features": numeric_cols, "dropped_constant": constant, "coverage_cols": coverage_cols,
        "regularization": {"woe_prior": woe_prior, "max_features": max_features, "max_abs_points": max_abs_points,
                           "features_kept": sorted(pipe.model_.features_), "dropped_low_iv": getattr(pipe, "dropped_low_iv_", [])},
        "split": {"test_size": split_size, "random_state": args.random_state,
                  "note": "stratified random tuning split shared by binning, fitting, calibration and tier cuts; "
                          "metrics below are tuning-split results, not an untouched holdout"},
        "validation": {k: (None if (isinstance(v, float) and not np.isfinite(v)) else v) for k, v in vr.items()},
        "calibrated": bool(getattr(pipe.model_, "calibrator_", None) is not None),
        "tier_cuts": getattr(pipe, "tier_cuts_", None),
        "refusal_overridden": refusal if (refusal and args.force) else None,
        "completion_state": "exploratory_end_to_end",
        "frozen_at": frozen_at,
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str))
    print(json.dumps({k: meta[k] for k in ("model_id", "mode", "rows_fit", "positives", "negatives", "rows_unscored", "validation", "calibrated", "refusal_overridden")}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
