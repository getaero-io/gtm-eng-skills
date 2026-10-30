# --- scorecard_report.py ---
from pathlib import Path
import json
import pandas as pd
import numpy as np
try:
    from tabulate import tabulate as _TAB
except ImportError:
    _TAB = None

from .pipeline import ScorecardPipeline
from .config import RunConfig

def build_top_contributors(breakdown_df: pd.DataFrame, raw_df: pd.DataFrame, features_config: object, top_n: int = 5) -> pd.Series:
    out_to_in = {}
    if features_config is not None:
        if isinstance(features_config, dict) or isinstance(features_config, list):
            feats_list = features_config.get("features", features_config) if isinstance(features_config, dict) else features_config
            for spec in (list(feats_list) if feats_list is not None else []):
                col_in = spec.get("input")
                col_out = spec.get("output", col_in)
                if col_in and col_out:
                    out_to_in[str(col_out)] = str(col_in)
        else:
            raise ValueError("features_config must be a dict or list if provided")

    def _display_val(idx, feat_name: str):
        base_in = out_to_in.get(str(feat_name), str(feat_name))
        if base_in in raw_df.columns:
            return raw_df.loc[idx, base_in]
        if feat_name in raw_df.columns:
            return raw_df.loc[idx, feat_name]
        return None

    def _row_explain(idx):
        pts = breakdown_df.loc[idx]
        pos = pts[pts > 0].sort_values(ascending=False)
        if pos.empty:
            return ""
        items = []
        for fname, val in pos.iloc[:top_n].items():
            v_raw = _display_val(idx, fname)
            disp_name = out_to_in.get(str(fname), str(fname))
            # Display integers without trailing .0 for stability
            if v_raw is None:
                v_str = ""
            else:
                try:
                    import numpy as _np
                    if isinstance(v_raw, (int, _np.integer)):
                        v_str = str(int(v_raw))
                    elif isinstance(v_raw, (float, _np.floating)) and float(v_raw).is_integer():
                        v_str = str(int(v_raw))
                    else:
                        v_str = str(v_raw)
                except Exception:
                    v_str = str(v_raw)
            items.append(f"(+{int(val)}) {disp_name}: {v_str}")
        return "\n".join(items)

    s = pd.Series(index=breakdown_df.index, dtype=object)
    for idx in breakdown_df.index:
        s.loc[idx] = _row_explain(idx)
    return s

def _feature_summary_from_pipe(pipe) -> pd.DataFrame:
    assert pipe.model_ is not None and pipe._validation_split_ is not None, "Fit first."
    model = pipe.model_
    X_tr, X_va, y_tr, y_va = pipe._validation_split_
    points_va, breakdown_va = model.score_points(X_va)
    rows = []
    abs_total = breakdown_va.abs().sum(axis=1).replace(0, np.nan)
    denom = abs_total.sum()
    for fname, fb in model.features_.items():
        beta = float(model.coefs_.get(fname, 0.0))
        iv = float(fb.iv) if fb.iv is not None else np.nan
        beta_iv = abs(beta) * (iv if iv == iv else 0.0)
        mean_abs = float(breakdown_va[fname].abs().mean())
        share_abs = float(breakdown_va[fname].abs().sum() / denom) if denom and denom > 0 else 0.0
        rows.append({"feature": fname, "kind": fb.kind, "beta": beta, "IV": iv, "|beta|*IV": beta_iv,
                     "mean_abs_points_on_valid": mean_abs, "share_abs_points": share_abs})
    return pd.DataFrame(rows).sort_values(["|beta|*IV", "mean_abs_points_on_valid", "share_abs_points"], ascending=False).reset_index(drop=True)

def eval_performance_split(model, X_in: pd.DataFrame, y_in: pd.Series, top_share: float) -> dict:
    from math import ceil as _ceil
    from sklearn.metrics import roc_auc_score as _auc_fn, average_precision_score as _ap_fn
    raw_pts, _ = model.score_points(X_in)
    k = max(1, int(_ceil(len(raw_pts) * top_share))) if len(raw_pts) else 0
    order = raw_pts.sort_values(ascending=False)
    top_idx = order.index[:k]
    base = float(y_in.mean()) if len(y_in) else float('nan')
    prec_top = float(y_in.loc[top_idx].mean()) if len(top_idx) else float('nan')
    lift = float(prec_top / base) if base and base > 0 else float('nan')
    auc = float(_auc_fn(y_in, model.predict_proba(X_in))) if len(pd.unique(y_in)) > 1 else float('nan')
    ap = float(_ap_fn(y_in, model.predict_proba(X_in))) if len(y_in) > 0 else float('nan')
    return {
        "rows": int(len(y_in)),
        "positives": int(y_in.sum()),
        "baseline_rate": base,
        "top_share": float(top_share),
        "precision_top_share": prec_top,
        "lift_top_share": lift,
        "auc": auc,
        "average_precision": ap,
    }

def _build_value_points_table(pipe, features_config, raw_df: pd.DataFrame = None, y_col: str = None) -> pd.DataFrame:
    """Produce per-category points for all features that use categorical mapping.

    Returns a DataFrame with columns: feature, kind, input_value, mapped_bin, points, count, label_rate, lift (optional)
    """
    rows = []
    if features_config is None:
        return pd.DataFrame(rows)
    feats = features_config.get("features", features_config) if isinstance(features_config, dict) else features_config
    feats = list(feats or [])
    model = pipe.model_
    # Compute base rate for lift if labels are available
    base_rate = None
    if raw_df is not None and (y_col is not None) and (y_col in raw_df.columns):
        try:
            base_rate = float(raw_df[y_col].astype(int).mean())
        except Exception:
            base_rate = None

    for spec in feats:
        col_in = spec.get("input")
        col_out = spec.get("output", col_in)
        t = spec.get("transform") or {}
        mapping = t.get("mapping") if isinstance(t, dict) else None
        if not mapping:
            continue
        unknown_label = t.get("unknown_label", "Other")
        fb = model.features_.get(col_out)
        if fb is None:
            continue
        points_map = getattr(fb, "points_map", {}) or {}
        feature_kind = getattr(fb, "kind", "")
        # Iterate over declared categories in mapping
        for cat, bin_label in mapping.items():
            mapped_bin = str(bin_label) if bin_label is not None else str(unknown_label)
            pts = int(points_map.get(mapped_bin, 0))
            count = None
            rate = None
            if raw_df is not None and (col_in in raw_df.columns):
                mask = raw_df[col_in].astype("object") == cat
                count = int(mask.sum())
                if (y_col is not None) and (y_col in raw_df.columns) and count > 0:
                    rate = float(raw_df.loc[mask, y_col].astype(int).mean())
            rows.append({
                "feature": col_in,
                "kind": feature_kind,
                "input_value": cat,
                "mapped_bin": mapped_bin,
                "points": pts,
                **({"count": count} if count is not None else {}),
                **({"label_rate": rate} if rate is not None else {}),
                **({"lift": (float(rate) / float(base_rate)) if (rate is not None and base_rate and base_rate > 0) else None} if rate is not None else {}),
            })
    return pd.DataFrame(rows)


def generate_reports(pipe, out_dir: str = "/mnt/data/reports", features_config: object = None, raw_df: pd.DataFrame = None, y_col: str = None):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    assert pipe.model_ is not None, "Fit the pipeline first."
    points = pipe.export_points_tables(); p_points = f"{out_dir}/points_table.csv"; points.to_csv(p_points, index=False)
    report_model = pipe.validation_bucket_report(top_share=0.10, use_policy=False)
    p_report_model = f"{out_dir}/bucket_report_model.csv"; report_model.to_csv(p_report_model, index=False)
    report_policy = pipe.validation_bucket_report(top_share=0.10, use_policy=True)
    p_report_policy = f"{out_dir}/bucket_report_policy.csv"; report_policy.to_csv(p_report_policy, index=False)
    feat_summary = _feature_summary_from_pipe(pipe); p_feat = f"{out_dir}/feature_summary.csv"; feat_summary.to_csv(p_feat, index=False)
    meta = {"gate": pipe.gate_, "tier_cuts": pipe.tier_cuts_, "validation_model": pipe.validation_report()}
    p_meta = f"{out_dir}/gate_and_tier_meta.json"; Path(p_meta).write_text(json.dumps(meta, indent=2))
    points_ext = points.copy()
    points_ext["predicate"] = points_ext.apply(lambda r: f"{r['feature']}=={r['bin']}", axis=1)
    storytelling = points_ext.merge(report_model, on="predicate", how="left")
    cols_order = [
        "feature", "kind", "bin", "predicate", "points",
        "prob_lift", "bucket_rate", "baseline_rate",
        "WOE", "beta", "model_odds_multiplier",
        "n", "share", "top_share_presence", "intrusion_ratio",
        "top_share_precision_segment", "top_share_precision_overall", "precision_gap",
        "is_reference", "iv",
    ]
    storytelling = storytelling.reindex(columns=[c for c in cols_order if c in storytelling.columns])
    p_story = f"{out_dir}/storytelling.csv"; storytelling.to_csv(p_story, index=False)
    p_model_lift = None
    if pipe._validation_split_ is not None:
        X_tr, X_va, y_tr, y_va = pipe._validation_split_
        raw_points, _ = pipe.model_.score_points(X_va)
        k = max(1, int(len(raw_points) * 0.10))
        order = raw_points.sort_values(ascending=False)
        top_idx = order.index[:k]
        prec_top = float(y_va.loc[top_idx].mean()) if len(top_idx) else float('nan')
        base_rate = float(y_va.mean()) if len(y_va) else float('nan')
        model_lift = float(prec_top / base_rate) if base_rate and base_rate > 0 else float('nan')
        vr = pipe.validation_report()
        model_rows = [{
            "top_share": 0.10,
            "precision_top_share": prec_top,
            "baseline_rate": base_rate,
            "lift_top_share": model_lift,
            "auc": float(vr.get("auc", float('nan'))),
            "average_precision": float(vr.get("average_precision", float('nan'))),
            "n_valid": int(vr.get("n_valid", 0)),
        }]
        model_df = pd.DataFrame(model_rows)
        p_model_lift = f"{out_dir}/model_lift.csv"; model_df.to_csv(p_model_lift, index=False)
    p_tier = None
    if pipe.tier_cuts_ is not None and pipe._validation_split_ is not None:
        X_tr, X_va, y_tr, y_va = pipe._validation_split_
        applied = pipe.score_and_assign_tiers(X_va)
        tiers = applied["tier"]
        base_rate = float(y_va.mean()) if len(y_va) else np.nan
        rows = []
        for t in ["A", "B", "C"]:
            mask = tiers == t
            if mask.any():
                rate = float(y_va.loc[mask].mean())
                lift = float(rate / base_rate) if base_rate and base_rate > 0 else np.nan
                rows.append({"tier": t, "rate": rate, "baseline_rate": base_rate, "lift": lift, "count": int(mask.sum())})
        tier_df = pd.DataFrame(rows)
        p_tier = f"{out_dir}/tier_lifts.csv"; tier_df.to_csv(p_tier, index=False)
    # Optional: emit value-level points for mapped categoricals
    p_value_points = None
    try:
        vp = _build_value_points_table(pipe, features_config, raw_df=raw_df, y_col=y_col)
        if isinstance(vp, pd.DataFrame) and not vp.empty:
            p_value_points = f"{out_dir}/value_points.csv"; vp.to_csv(p_value_points, index=False)
    except Exception:
        p_value_points = None

    # Print a concise value-level preview at the very end to ensure it appears in logs
    try:
        if isinstance(vp, pd.DataFrame) and not vp.empty:
            feat_to_show = "INDUSTRY" if "INDUSTRY" in vp["feature"].unique().tolist() else vp["feature"].iloc[0]
            sub = vp.loc[vp["feature"] == feat_to_show].copy()
            sub = sub.sort_values(["points", "count" if "count" in sub.columns else "points"], ascending=[False, False]).head(20)
            cols = [c for c in ["feature","kind","input_value","mapped_bin","points","count","lift"] if c in sub.columns]
            print("\n=== Value-level Points (preview) ===")
            if _TAB is not None:
                print(_TAB(sub[cols], headers='keys', tablefmt='github', floatfmt='.6f', showindex=False))
            else:
                print(sub[cols].to_string(index=False))
    except Exception:
        pass

    return {
        "points_table_csv": p_points,
        "bucket_report_model_csv": p_report_model,
        "bucket_report_policy_csv": p_report_policy,
        "feature_summary_csv": p_feat,
        "storytelling_csv": p_story,
        **({"model_lift_csv": p_model_lift} if p_model_lift else {}),
        **({"tier_lifts_csv": p_tier} if p_tier else {}),
        "gate_and_tier_meta_json": p_meta,
        **({"value_points_csv": p_value_points} if p_value_points else {}),
    }

def train_scorecard(
    X_or_df: pd.DataFrame,
    y: pd.Series = None,
    config: RunConfig = None,
    raw_df: pd.DataFrame = None,
    features_config: object = None,
) -> dict:
    """
    Fit the scorecard end-to-end and return in-memory artifacts.

    Config keys (examples):
      - y_col (required)
      - test_size, random_state, do_calibration
      - n_bins_numeric, n_bins_cat_high, max_low_card
      - l1_C, scale
      - top_share
      - gate: {enable: bool, top_share: float, min_intrusion: float, min_prec_gain: float}
      - tiers: {enable: bool, top_share_hint: float, precA_min: float, covA_max: float}
    """
    assert config is not None, "config is required"
    y_col = config.y_col
    if y is not None:
        df = X_or_df.copy()
        df[y_col] = pd.Series(y).astype(int).values
    else:
        df = X_or_df
    assert y_col in df.columns, f"Missing target column {y_col}"

    # Dataset summary (pre-split)
    y_all = df[y_col].astype(int)
    n_rows = int(len(y_all))
    n_pos = int(y_all.sum())
    base_rate = float(y_all.mean()) if n_rows else float('nan')
    print("\n=== Dataset Summary ===")
    print(f"rows={n_rows}, positives={n_pos}, base_rate={base_rate:.6f}")

    pipe = ScorecardPipeline(
        y_col=y_col,
        test_size=config.test_size,
        random_state=config.random_state,
        do_calibration=config.do_calibration,
        n_bins_numeric=config.n_bins_numeric,
        n_bins_cat_high=config.n_bins_cat_high,
        max_low_card=config.max_low_card,
        l1_C=config.l1_C,
        scale=config.scale,
        method=getattr(config, "method", "logistic"),
        woe_prior=getattr(config, "woe_prior", 0.5),
        max_features=getattr(config, "max_features", None),
        max_abs_points=getattr(config, "max_abs_points", None),
    )

    df_fit = df.copy()
    raw_helper_cols = [c for c in df_fit.columns if c != y_col and (str(c).endswith("_RAW"))]
    if raw_helper_cols:
        df_fit = df_fit.drop(columns=raw_helper_cols)
    # Drop known passthrough/non-feature columns from modeling frame
    passthrough_cols = []
    if "account_id" in df_fit.columns:
        passthrough_cols.append("account_id")
    if passthrough_cols:
        df_fit = df_fit.drop(columns=passthrough_cols)

    model = pipe.fit(df_fit)

    points = pipe.export_points_tables().copy()
    points["predicate"] = points.apply(lambda r: f"{r['feature']}=={r['bin']}", axis=1)
    top_share = float(config.top_share)
    report_model = pipe.validation_bucket_report(top_share=top_share, use_policy=False)
    scorecard = points.merge(report_model, on="predicate", how="left")
    feature_summary = _feature_summary_from_pipe(pipe)

    X_tr, X_va, y_tr, y_va = pipe._validation_split_
    raw_points, _ = model.score_points(X_va)
    k = max(1, int(len(raw_points) * top_share))
    order = raw_points.sort_values(ascending=False)
    top_idx = order.index[:k]
    prec_top = float(y_va.loc[top_idx].mean()) if len(top_idx) else float("nan")
    base_rate = float(y_va.mean()) if len(y_va) else float("nan")
    lift_top = float(prec_top / base_rate) if base_rate and base_rate > 0 else float("nan")
    vr = pipe.validation_report()
    model_lift_rows = [{
        "variant": "model",
        "top_share": top_share,
        "precision_top_share": prec_top,
        "baseline_rate": base_rate,
        "lift_top_share": lift_top,
        "auc": float(vr.get("auc", float('nan'))),
        "average_precision": float(vr.get("average_precision", float('nan'))),
        "n_valid": int(vr.get("n_valid", 0)),
    }]

    decision_points_policy = None
    policy_cfg = config.policy
    if policy_cfg and getattr(policy_cfg, "rules", None):
            decision_points_policy = raw_points.copy()
            overrides = pd.Series(0, index=decision_points_policy.index, dtype=int)
            import re
            def _match(rule, row):
                v = row.get(rule.target, None)
                if rule.source == "bin":
                    v = str(v) if v is not None else None
                    if rule.op == "lte":
                        return (float(v) <= float(rule.value)) if v is not None else False
                    if rule.op == "gte":
                        return (float(v) >= float(rule.value)) if v is not None else False
                    if rule.op == "eq":
                        return v == rule.value
                    if rule.op == "in":
                        return v in (rule.values or [])
                    if rule.op == "between":
                        lo, hi = rule.values[0], rule.values[1]
                        return (float(v) >= float(lo)) and (float(v) <= float(hi)) if v is not None else False
                    if rule.op == "regex":
                        return bool(re.search(str(rule.value), str(v or "")))
                return False
            for rule in sorted([r for r in policy_cfg.rules if r.enabled], key=lambda r: int(r.priority)):
                mask = X_va.apply(lambda r: _match(rule, r), axis=1)
                if policy_cfg.combine == "sum":
                    overrides.loc[mask] = overrides.loc[mask] + int(rule.override_points)
                else:
                    overrides.loc[mask] = np.maximum(overrides.loc[mask].astype(int), int(rule.override_points))
            decision_points_policy = decision_points_policy + overrides
            order_p = decision_points_policy.sort_values(ascending=False)
            top_idx_p = order_p.index[:k]
            prec_top_p = float(y_va.loc[top_idx_p].mean()) if len(top_idx_p) else float("nan")
            lift_top_p = float(prec_top_p / base_rate) if base_rate and base_rate > 0 else float("nan")
            model_lift_rows.append({
                "variant": "policy",
                "top_share": top_share,
                "precision_top_share": prec_top_p,
                "baseline_rate": base_rate,
                "lift_top_share": lift_top_p,
                "auc": float(vr.get("auc", float('nan'))),
                "average_precision": float(vr.get("average_precision", float('nan'))),
                "n_valid": int(vr.get("n_valid", 0)),
            })

    model_lift = pd.DataFrame(model_lift_rows)

    tier_cuts = None
    tier_lifts = None
    policy_tier_lifts = None
    tiers_cfg = config.tiers
    if tiers_cfg.enable:
        pipe.learn_tier_cutoffs(
            top_share_hint=top_share,
            precA_min=tiers_cfg.precA_min,
            covA_max=tiers_cfg.covA_max,
        )
        tier_cuts = dict(pipe.tier_cuts_) if pipe.tier_cuts_ is not None else None
        applied = pipe.score_and_assign_tiers(X_va)
        tiers = applied["tier"]
        rows = []
        for t in ["A", "B", "C"]:
            mask = tiers == t
            if mask.any():
                rate = float(y_va.loc[mask].mean())
                lift = float(rate / base_rate) if base_rate and base_rate > 0 else float('nan')
                rows.append({"variant": "policy" if pipe.gate_ else "model", "tier": t, "rate": rate, "baseline_rate": base_rate, "lift": lift, "count": int(mask.sum())})
        tier_lifts = pd.DataFrame(rows) if rows else None
        if decision_points_policy is not None and pipe.tier_cuts_ is not None:
            A_cut = pipe.tier_cuts_.get("cut_A"); B_cut = pipe.tier_cuts_.get("cut_B")
            def _tier_from_pts(v: float):
                x = float(v)
                if A_cut is not None and x >= A_cut:
                    return "A"
                if B_cut is not None and x >= B_cut:
                    return "B"
                return "C"
            tiers_p = decision_points_policy.apply(_tier_from_pts)
            rows_p = []
            for t in ["A","B","C"]:
                mk = (tiers_p == t)
                if mk.any():
                    rate = float(y_va.loc[mk].mean())
                    lift = float(rate / base_rate) if base_rate and base_rate > 0 else float('nan')
                    rows_p.append({"tier": t, "rate": rate, "baseline_rate": base_rate, "lift": lift, "count": int(mk.sum())})
            policy_tier_lifts = pd.DataFrame(rows_p) if rows_p else None

    # Scoring outputs
    scores_va = pipe.score(X_va)
    validation_scoring = pd.DataFrame({
        "raw_points": scores_va["raw_points"].astype(int).values,
        "model_prob": scores_va["model_prob"].astype(float).values,
    }, index=X_va.index)

    X_all = df.drop(columns=[y_col]).copy()
    scores_all = pipe.score(X_all)
    all_scoring = pd.DataFrame({
        "raw_points": scores_all["raw_points"].astype(int).values,
        "model_prob": scores_all["model_prob"].astype(float).values,
    }, index=X_all.index)

    # Explainer omitted in training persistence; scoring/inference should call build_top_contributors

    # Overall calibration on full dataset

    # Print condensed scorecard on every run
    print("\n=== Scorecard (Condensed: feature, bin, points, lift_total, n_total, support_valid, lift_valid, share_total) ===")
    y_all_full = df[y_col].astype(int).copy()
    # Now that y_all_full is defined, print calibration
    n_all = int(len(y_all_full))
    actual_rate_all = float(y_all_full.mean()) if n_all else float('nan')
    avg_pred_all = float(scores_all["model_prob"].mean()) if n_all else float('nan')
    ratio_pa = float(avg_pred_all / actual_rate_all) if (actual_rate_all and actual_rate_all > 0) else float('nan')
    print("\n=== Overall Calibration (full dataset) ===")
    print(f"n={n_all}, actual_rate={actual_rate_all:.6f}, avg_pred={avg_pred_all:.6f}, pred/actual={ratio_pa:.3f}")
    base_rate_total = float(y_all_full.mean()) if len(y_all_full) else float('nan')
    rows_bins = []
    for fname, fb in pipe.model_.features_.items():
        if str(fname).lower() == "account_id":
            continue
        if fname not in X_all.columns:
            continue
        bins_all = X_all[fname].astype("object").astype(str)
        grp = pd.DataFrame({"bin": bins_all, "y": y_all_full}).groupby("bin").agg(n_total=("y","size"), rate_total=("y","mean")).reset_index()
        grp["feature"] = fname
        grp["kind"] = getattr(fb, "kind", "")
        grp["points"] = grp["bin"].map((getattr(fb, "points_map", {}) or {})).fillna(0).astype(int)
        grp["share_total"] = grp["n_total"] / float(len(y_all_full) or 1)
        grp["lift_total"] = grp.apply(lambda r: float(r["rate_total"]/base_rate_total) if base_rate_total and base_rate_total>0 else float('nan'), axis=1)
        rows_bins.append(grp)
    bins_total_df = pd.concat(rows_bins, ignore_index=True) if rows_bins else pd.DataFrame()
    sc_small_cols = [c for c in ["feature","kind","bin","points","prob_lift","n"] if c in scorecard.columns]
    sc_small_val = scorecard.reindex(columns=sc_small_cols).copy()
    sc_small_val = sc_small_val.rename(columns={"prob_lift":"lift_valid","n":"support_valid"})
    condensed = pd.merge(
        bins_total_df,
        sc_small_val,
        on=["feature","kind","bin","points"], how="left"
    )
    condensed = condensed[["feature","kind","bin","points","lift_total","n_total","support_valid","lift_valid","share_total"]]
    condensed = condensed.sort_values(["feature","points"], ascending=[True, False])
    try:
        from tabulate import tabulate
        print(tabulate(condensed, headers='keys', tablefmt='github', floatfmt='.6f', showindex=False))
    except ImportError:
        print(condensed.to_string(index=False))

    # Print value-level points for mapped categoricals (brief preview)
    if features_config is not None:
        vp_df = _build_value_points_table(pipe, features_config, raw_df=raw_df, y_col=y_col)
        if isinstance(vp_df, pd.DataFrame) and not vp_df.empty:
            print("\n=== Value-level Points (preview, top by feature) ===")
            # Limit rows per feature to keep output readable
            for feat in vp_df["feature"].unique():
                sub = vp_df.loc[vp_df["feature"] == feat].copy()
                sub = sub.sort_values(["points", "count" if "count" in sub.columns else "points"], ascending=[False, False]).head(10)
                cols = [c for c in ["feature","kind","input_value","mapped_bin","points","count","lift"] if c in sub.columns]
                if _TAB is not None:
                    print(_TAB(sub[cols], headers='keys', tablefmt='github', floatfmt='.6f', showindex=False))
                else:
                    print(sub[cols].to_string(index=False))

    # Build per-row results for full dataset (points, probability, tier when available)
    tiers_series = None
    if pipe.tier_cuts_ is not None:
        policy = pipe.apply_policy_and_tiers(df=X_all, raw_points=scores_all["raw_points"])
        tiers_series = policy["tier"].astype(str)
    all_results_cols = {
        "points": scores_all["raw_points"].astype(int).values,
        "probability": scores_all["model_prob"].astype(float).values,
    }
    if tiers_series is not None:
        all_results_cols["tier"] = tiers_series.values
    # Pass through id column if present
    if "account_id" in df.columns:
        all_results_cols["account_id"] = df["account_id"].values
    # Do not persist explainer from training path
    all_results = pd.DataFrame(all_results_cols, index=X_all.index)

    model_meta = {
        "intercept": model.intercept_,
        "scale": model.scale_,
        "coefs": model.coefs_,
        "has_calibrator": model.calibrator_ is not None,
        "validation": pipe.validation_report(),
        "feature_kinds": getattr(pipe, "_kinds_", {}),
    }

    # Print per-row scoring results (sample)
    cols = [c for c in ["account_id","points","probability","tier"] if c in all_results.columns]
    if cols:
        print("\n=== Scoring results (account_id, points, probability, tier) ===")
        if _TAB is not None:
            print(_TAB(all_results[cols].head(25), headers='keys', tablefmt='github', floatfmt='.6f', showindex=False))
        else:
            print(all_results[cols].head(25).to_string(index=False))

    # Print performance metrics: model lift and tier lifts, plus by-split summary
    X_tr, X_va, y_tr, y_va = pipe._validation_split_
    X_all_perf = df.drop(columns=[y_col]).copy(); y_all_perf = df[y_col].astype(int).copy()
    split_rows = [
        {"split": "train", **eval_performance_split(model, X_tr, y_tr, top_share)},
        {"split": "valid", **eval_performance_split(model, X_va, y_va, top_share)},
        {"split": "all", **eval_performance_split(model, X_all_perf, y_all_perf, top_share)},
    ]
    print("\n=== Performance (by split) ===")
    df_splits = pd.DataFrame(split_rows)
    if _TAB is not None:
        print(_TAB(df_splits, headers='keys', tablefmt='github', floatfmt='.6f', showindex=False))
    else:
        print(df_splits.to_string(index=False))
    if isinstance(model_lift, pd.DataFrame) and not model_lift.empty:
        print("\n=== Performance (Model Lift) ===")
        cols_ml = [c for c in ["top_share","precision_top_share","baseline_rate","lift_top_share","auc","average_precision","n_valid"] if c in model_lift.columns]
        if _TAB is not None:
            print(_TAB(model_lift[cols_ml], headers='keys', tablefmt='github', floatfmt='.6f', showindex=False))
        else:
            print(model_lift[cols_ml].to_string(index=False))
    if isinstance(tier_lifts, pd.DataFrame) and not tier_lifts.empty:
        print("\n=== Performance (Tier Lifts) ===")
        cols_tl = [c for c in ["tier","rate","baseline_rate","lift","count"] if c in tier_lifts.columns]
        if _TAB is not None:
            print(_TAB(tier_lifts[cols_tl], headers='keys', tablefmt='github', floatfmt='.6f', showindex=False))
        else:
            print(tier_lifts[cols_tl].to_string(index=False))

    # Decile lift by actual outcomes on the full dataset
    decile_lift_df = None
    try:
        probs_all = scores_all["model_prob"] if isinstance(scores_all, dict) else None
    except Exception:
        probs_all = None
    if probs_all is not None and len(probs_all) > 0:
        n_all = len(probs_all)
        ranks = probs_all.rank(method="first", ascending=False)
        deciles = np.ceil(ranks / float(max(1, n_all)) * 10).astype(int).clip(1, 10)
        base_rate_all = float(y_all_full.mean()) if len(y_all_full) else float('nan')
        df_dec = pd.DataFrame({"decile": deciles.astype(int), "prob": probs_all.astype(float).values, "y": y_all_full.astype(int).values})
        agg = df_dec.groupby("decile").agg(n=("y","size"), actual_rate=("y","mean"), avg_prob=("prob","mean")).reset_index().sort_values("decile")
        agg["actual_lift"] = agg.apply(lambda r: (float(r["actual_rate"]) / float(base_rate_all)) if base_rate_all and base_rate_all > 0 else float('nan'), axis=1)
        decile_lift_df = agg
        print("\n=== Decile Lift (actuals over full dataset) ===")
        cols_dl = [c for c in ["decile","n","actual_rate","avg_prob","actual_lift"] if c in decile_lift_df.columns]
        if _TAB is not None:
            print(_TAB(decile_lift_df[cols_dl], headers='keys', tablefmt='github', floatfmt='.6f', showindex=False))
        else:
            print(decile_lift_df[cols_dl].to_string(index=False))

    return {
        "scorecard": scorecard.sort_values(["feature", "points"], ascending=[True, False]).reset_index(drop=True),
        "condensed_scorecard": condensed.sort_values(["feature","points"], ascending=[True, False]).reset_index(drop=True),
        "feature_summary": feature_summary.reset_index(drop=True),
        "model_lift": model_lift.reset_index(drop=True),
        **({"tier_lifts": tier_lifts.reset_index(drop=True)} if tier_lifts is not None else {}),
        **({"policy_tier_lifts": policy_tier_lifts.reset_index(drop=True)} if policy_tier_lifts is not None else {}),
        **({"decile_lift": decile_lift_df.reset_index(drop=True)} if decile_lift_df is not None else {}),
        **({"tier_cuts": tier_cuts} if tier_cuts is not None else {}),
        **({"validation_scoring": validation_scoring} if validation_scoring is not None else {}),
        **({"all_scoring": all_scoring} if all_scoring is not None else {}),
        **({"all_results": all_results} if all_results is not None else {}),
        "pipeline": pipe,
        "model_meta": model_meta,
    }
