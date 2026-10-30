# --- schema-agnostic scorecard_pipeline.py ---
from typing import Dict, List, Optional, Tuple, Any
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score


# --- example usage ---
# from scorecard_pipeline import ScorecardPipeline
# from scorecard_report import generate_reports
# pipe = ScorecardPipeline(y_col="converted")
# pipe.fit(df)
# pipe.discover_gate(top_share=0.10)
# pipe.learn_tier_cutoffs(precA_min=0.40)
# paths = generate_reports(pipe, out_dir="/mnt/data/reports")
# out = pipe.apply_gates_and_tiers(df_new)
# print(paths)


BOOL_TRUE = {"true", "1", "1.0", "yes", "t", "y"}
BOOL_FALSE = {"false", "0", "0.0", "no", "f", "n"}


def is_boolean_like(series: pd.Series) -> bool:
    vals = {str(v).strip().lower() for v in series.dropna().unique()}
    return bool(vals) and vals <= (BOOL_TRUE | BOOL_FALSE)


def canonical_bool(series: pd.Series) -> pd.Series:
    """Map any truthy/falsy spelling to the strings "True"/"False"; missing stays "nan" (its own bin).

    Used identically at training, batch scoring and replay so a missing flag is never read as False.
    """
    def one(v):
        try:
            if v is None or pd.isna(v):
                return "nan"
        except (TypeError, ValueError):
            pass
        t = str(v).strip().lower()
        if t in BOOL_TRUE: return "True"
        if t in BOOL_FALSE: return "False"
        if t in ("", "nan", "none", "null"): return "nan"
        raise ValueError(f"non-boolean value in boolean feature: {v!r}")
    return series.map(one).astype(str)

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))

def _woe_iv_from_counts(good: np.ndarray, bad: np.ndarray, min_count: float = 0.5):
    good = good.astype(float) + min_count
    bad = bad.astype(float) + min_count
    dist_good = good / good.sum()
    dist_bad = bad / bad.sum()
    woe = np.log(np.clip(dist_good / dist_bad, 1e-12, None))
    iv = np.sum((dist_good - dist_bad) * woe)
    return woe, float(iv)

def _compute_categorical_woe(s: pd.Series, y: pd.Series, min_count: float = 0.5):
    df = pd.DataFrame({"val": s.astype("object"), "y": y.astype(int)})
    agg = df.groupby("val")["y"].agg(["sum", "count"])
    good = agg["sum"].to_numpy()
    bad = (agg["count"] - agg["sum"]).to_numpy()
    woe, iv = _woe_iv_from_counts(good, bad, min_count=min_count)
    woe_map = {k: float(v) for k, v in zip(agg.index.tolist(), woe)}
    counts = {k: (int(g), int(b)) for k, g, b in zip(agg.index.tolist(), good, bad)}
    return woe_map, iv, counts

def _target_encode_oof(s: pd.Series, y: pd.Series, n_splits: int = 5, m: float = 100.0, random_state: int = 42):
    y = y.astype(int).values
    s = s.astype("object")
    prior = y.mean()
    enc = pd.Series(index=s.index, dtype=float)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    for train_idx, val_idx in skf.split(np.zeros(len(y)), y):
        s_tr, y_tr = s.iloc[train_idx], y[train_idx]
        s_va = s.iloc[val_idx]
        df_tr = pd.DataFrame({"v": s_tr, "y": y_tr})
        grp = df_tr.groupby("v")["y"].agg(["sum", "count"])
        rate = (grp["sum"] + m * prior) / (grp["count"] + m)
        enc.iloc[val_idx] = s_va.map(rate).fillna(prior).values
    df_full = pd.DataFrame({"v": s, "y": y})
    grp_full = df_full.groupby("v")["y"].agg(["sum", "count"])
    rate_full = (grp_full["sum"] + m * prior) / (grp_full["count"] + m)
    global_map = {k: float(v) for k, v in rate_full.items()}
    return enc.astype(float), global_map, float(prior)

def _quantile_bins(x: pd.Series, n_bins: int = 6):
    try:
        cats, edges = pd.qcut(x, q=min(n_bins, max(2, x.nunique())), retbins=True, duplicates="drop")
    except ValueError:
        cats, edges = pd.qcut(x, q=2, retbins=True, duplicates="drop")
    return pd.Series(cats).astype(str), list(edges.astype(float))

def edges_to_float(edges):
    """Edges are stored as numbers or the strings "-inf"/"inf" (JSON cannot carry infinities)."""
    return [float(e) if not isinstance(e, str) else float(e) for e in edges]


def open_outer_edges(edges):
    e = [float(v) for v in edges]
    if len(e) >= 2:
        e[0], e[-1] = float("-inf"), float("inf")  # values beyond the training range join the outer bins, not the missing bin
    return e


def _assign_bins_from_edges(x: pd.Series, edges):
    e = edges_to_float(edges)
    out = pd.cut(x, bins=e, include_lowest=True, duplicates="drop").astype(str)
    return out.where(x.notna(), "nan")

def _infer_feature_types(df: pd.DataFrame, y_col: str, feature_types: Optional[Dict[str, str]] = None, max_low_card: int = 25):
    """Infer feature kinds for training assuming preprocessing already produced bins.

    - Allow only boolean and categorical_low kinds for non-preprocessed numeric/high-card features.
    - If a non-boolean numeric column is present, raise a ValueError instructing to preprocess first.
    - If the caller supplies feature_types, honor it.
    """
    kinds = {}
    for col in df.columns:
        if col == y_col:
            continue
        if feature_types and col in feature_types:
            kinds[col] = feature_types[col]
            continue
        s = df[col]
        # Booleans or {0,1}
        if pd.api.types.is_bool_dtype(s) or set(pd.unique(s.dropna())) <= {0, 1, True, False}:
            kinds[col] = "boolean"
            continue
        # Disallow raw numeric inputs (must be pre-binned)
        if pd.api.types.is_numeric_dtype(s):
            raise ValueError(
                f"Column '{col}' appears numeric with >2 unique values; please run preprocess() to bin numeric features before training."
            )
        # Treat all other inputs as categorical_low (string-like bin labels)
        kinds[col] = "categorical_low"
    return kinds

from dataclasses import dataclass, field
@dataclass
class FeatureBins:
    name: str
    kind: str
    bin_edges: Optional[list] = None
    oof_prior: Optional[float] = None
    te_map: Optional[dict] = None
    woe_map: dict = field(default_factory=dict)
    points_map: dict = field(default_factory=dict)
    ref_bin: Optional[str] = None
    iv: Optional[float] = None

@dataclass
class ScorecardModel:
    intercept_: float
    scale_: int
    coefs_: dict
    features_: dict
    calibrator_: Optional[IsotonicRegression] = None
    _calib_x_min: float = field(default=-10.0, init=False, repr=False)
    _calib_x_max: float = field(default=+10.0, init=False, repr=False)

    def score_points(self, X: pd.DataFrame):
        breakdown = {}
        for fname, fb in self.features_.items():
            if fb.kind == "numeric":
                bins = _assign_bins_from_edges(X[fname].astype(float), fb.bin_edges)
                pts = bins.map(fb.points_map).fillna(0).astype(int)
            elif fb.kind == "boolean":
                bins = X[fname].astype(bool).astype(str)
                pts = bins.map(fb.points_map).fillna(0).astype(int)
            elif fb.kind == "categorical_low":
                bins = X[fname].astype("object").astype(str)
                pts = bins.map(fb.points_map).fillna(0).astype(int)
            elif fb.kind == "categorical_high":
                enc = X[fname].astype("object").map(fb.te_map).fillna(fb.oof_prior)
                bins = _assign_bins_from_edges(enc, fb.bin_edges)
                pts = bins.map(fb.points_map).fillna(0).astype(int)
            else:
                raise ValueError(f"Unknown feature kind: {fb.kind}")
            breakdown[fname] = pts
        breakdown_df = pd.DataFrame(breakdown, index=X.index).astype(int)
        total_points = breakdown_df.sum(axis=1)
        return total_points, breakdown_df

    def predict_proba(self, X: pd.DataFrame):
        total_points, _ = self.score_points(X)
        raw_logit = self.intercept_ + (total_points.astype(float) / self.scale_)
        if self.calibrator_ is not None:
            x = np.clip(raw_logit, self._calib_x_min, self._calib_x_max)
            return pd.Series(self.calibrator_.predict(x), index=total_points.index)
        return pd.Series(1.0 / (1.0 + np.exp(-raw_logit)), index=total_points.index)

class ScorecardTrainer:
    def __init__(self, y_col: str, feature_types: Optional[Dict[str,str]] = None, max_low_card: int = 25,
                 n_bins_numeric: int = 5, n_bins_cat_high: int = 6, scale: int = 10, l1_C: float = 1.0,
                 test_size: float = 0.25, random_state: int = 42, do_calibration: bool = True,
                 method: str = "logistic", woe_prior: float = 0.5, max_features: int | None = None,
                 max_abs_points: int | None = None):
        if method not in ("logistic", "naive_bayes"):
            raise ValueError("method must be 'propensity' (logistic) or 'lift' (naive_bayes)")
        self.method = method
        self.woe_prior = float(woe_prior)          # Jeffreys-style pseudo-count added to every bin (0.5 default; larger shrinks rare bins)
        self.max_features = max_features           # keep only the top-IV features on the training fold (lift mode guard at small n)
        self.max_abs_points = max_abs_points       # clip per-bin points so no single feature dominates
        self.y_col = y_col; self.feature_types = feature_types or {}; self.max_low_card = max_low_card
        self.n_bins_numeric = n_bins_numeric; self.n_bins_cat_high = n_bins_cat_high; self.scale = scale
        self.l1_C = l1_C; self.test_size = test_size; self.random_state = random_state; self.do_calibration = do_calibration
        self.model_ = None; self._validation_split_ = None; self.gate_ = None; self.tier_cuts_ = None; self._kinds_ = {}

    def fit(self, df: pd.DataFrame):
        assert self.y_col in df
        y = df[self.y_col].astype(int); X = df.drop(columns=[self.y_col]).copy()
        # Build a working feature frame that ignores helper columns
        # 1) Drop any *_RAW helper columns entirely
        raw_helper_cols = [c for c in X.columns if str(c).endswith("_RAW")]
        if raw_helper_cols:
            X = X.drop(columns=raw_helper_cols)
        # 2) Use columns as-is (explicitness): do not rename *_bin or *_BIN columns.
        kinds = _infer_feature_types(X, self.y_col, self.feature_types, max_low_card=self.max_low_card); self._kinds_ = kinds
        X_train, X_valid, y_train, y_valid = train_test_split(X, y, test_size=self.test_size, stratify=y, random_state=self.random_state)
        self._validation_split_ = (X_train.copy(), X_valid.copy(), y_train.copy(), y_valid.copy())
        artifacts = {}
        for fname, kind in kinds.items():
            s_tr = X_train[fname]
            if kind == "boolean":
                bins = s_tr.astype(bool).astype(str)
            else:
                # Treat all non-boolean features as pre-binned categorical labels
                bins = s_tr.astype("object").astype(str)
            wmap, iv, _ = _compute_categorical_woe(bins, y_train, min_count=self.woe_prior)
            artifacts[fname] = FeatureBins(name=fname, kind=kind, woe_map=wmap, iv=iv)
        if self.max_features is not None and len(artifacts) > self.max_features:
            keep = sorted(artifacts, key=lambda f: -(artifacts[f].iv or 0.0))[: self.max_features]
            self.dropped_low_iv_ = sorted(set(artifacts) - set(keep))
            artifacts = {f: artifacts[f] for f in keep}
        else:
            self.dropped_low_iv_ = []

        def build_woe_matrix(X_in: pd.DataFrame):
            cols = {}
            for fname, fb in artifacts.items():
                if fb.kind == "boolean":
                    bins = X_in[fname].astype(bool).astype(str)
                else:
                    bins = X_in[fname].astype("object").astype(str)
                cols[fname] = bins.map(fb.woe_map).fillna(0.0).astype(float)
            return pd.DataFrame(cols, index=X_in.index)

        Xtr_woe = build_woe_matrix(X_train); Xva_woe = build_woe_matrix(X_valid)
        if self.method == "naive_bayes":
            # Lift model: additive WOE points, no fitted weights. Each feature contributes
            # scale * (WOE_bin - WOE_ref); the intercept is the training base log-odds.
            coefs = {c: 1.0 for c in Xtr_woe.columns.tolist()}
            p = float(y_train.mean()); p = min(max(p, 1e-6), 1 - 1e-6)
            intercept = float(np.log(p / (1 - p)))
        else:
            try:  # sklearn >= 1.8 spells L1 as l1_ratio=1.0; older versions need penalty="l1"
                clf = LogisticRegression(l1_ratio=1.0, C=self.l1_C, solver="liblinear", fit_intercept=True, max_iter=200, random_state=self.random_state)
                clf.fit(Xtr_woe.values, y_train.values)
            except (TypeError, ValueError):
                clf = LogisticRegression(penalty="l1", C=self.l1_C, solver="liblinear", fit_intercept=True, max_iter=200, random_state=self.random_state)
                clf.fit(Xtr_woe.values, y_train.values)
            coefs = dict(zip(Xtr_woe.columns.tolist(), clf.coef_.ravel().tolist())); intercept = float(clf.intercept_[0])

        intercept_shift = 0.0
        for fname, fb in artifacts.items():
            if fb.kind == "boolean":
                bins = X_train[fname].astype(bool).astype(str)
            else:
                bins = X_train[fname].astype("object").astype(str)
            ref_bin = bins.value_counts().idxmax(); fb.ref_bin = str(ref_bin)
            beta = coefs.get(fname, 0.0); w_ref = fb.woe_map.get(str(ref_bin), 0.0); intercept_shift += beta * w_ref
            fb.points_map = {str(b): int(np.round(self.scale * beta * (w - w_ref))) for b, w in fb.woe_map.items()}
            if self.max_abs_points is not None:
                fb.points_map = {b: int(max(-self.max_abs_points, min(self.max_abs_points, p))) for b, p in fb.points_map.items()}

        intercept_adj = intercept + intercept_shift
        calibrator = None; calib_x_min, calib_x_max = -10, +10
        if self.do_calibration and len(X_valid) > 0 and int(y_valid.sum()) >= 5 and int((1 - y_valid).sum()) >= 5:
            tmp = ScorecardModel(intercept_=intercept_adj, scale_=self.scale, coefs_=coefs, features_=artifacts, calibrator_=None)
            raw_points, _ = tmp.score_points(X_valid)
            raw_logit = intercept_adj + raw_points.astype(float) / self.scale
            calibrator = IsotonicRegression(out_of_bounds="clip"); calibrator.fit(raw_logit.values, y_valid.values)
            calib_x_min = float(np.min(raw_logit.values)); calib_x_max = float(np.max(raw_logit.values))

        model = ScorecardModel(intercept_=intercept_adj, scale_=self.scale, coefs_=coefs, features_=artifacts, calibrator_=calibrator)
        model._calib_x_min = calib_x_min; model._calib_x_max = calib_x_max; self.model_ = model

        va_prob = model.predict_proba(X_valid)
        if len(pd.unique(y_valid)) > 1:
            auc = roc_auc_score(y_valid, va_prob)
            ap = average_precision_score(y_valid, va_prob)
        else:
            auc, ap = float("nan"), float("nan")
        self._validation_report_ = {"auc": auc, "average_precision": ap, "n_valid": int(len(X_valid))}
        return model

    def validation_report(self): return getattr(self, "_validation_report_", {})

    def export_points_tables(self) -> pd.DataFrame:
        assert self.model_ is not None
        rows = []
        for fname, fb in self.model_.features_.items():
            for b, pts in sorted(fb.points_map.items(), key=lambda kv: kv[1], reverse=True):
                rows.append({"feature": fname, "kind": fb.kind, "bin": b, "points": int(pts), "is_reference": b == fb.ref_bin, "iv": fb.iv})
        return pd.DataFrame(rows)

    def _build_predicates(self, X: pd.DataFrame) -> Dict[str, pd.Series]:
        preds = {}
        for fname, fb in self.model_.features_.items():
            if fb.kind == "numeric":
                bins = _assign_bins_from_edges(X[fname].astype(float), fb.bin_edges)
                for label in bins.astype(str).unique(): preds[f"{fname}=={label}"] = (bins.astype(str) == label)
            elif fb.kind == "boolean":
                preds[f"{fname}==True"] = X[fname].astype(bool)
            elif fb.kind == "categorical_low":
                bins = X[fname].astype("object").astype(str)
                for label in bins.unique(): preds[f"{fname}=={label}"] = (bins == label)
            else:
                enc = X[fname].astype("object").map(fb.te_map).fillna(fb.oof_prior)
                bins = _assign_bins_from_edges(enc, fb.bin_edges)
                for label in bins.astype(str).unique(): preds[f"{fname}=={label}"] = (bins.astype(str) == label)
        return preds

    def _policy_points_from_gate(self, raw_points: pd.Series, gate_mask: pd.Series, big_penalty: int = 10_000) -> pd.Series:
        return raw_points - big_penalty * gate_mask.astype(int)

    def discover_gate(self, top_share: float = 0.10, min_intrusion: float = 2.0, min_prec_gain: float = 0.0):
        assert self.model_ is not None and self._validation_split_ is not None
        X_tr, X_va, y_tr, y_va = self._validation_split_
        raw_points, _ = self.model_.score_points(X_va)
        preds = self._build_predicates(X_va)

        def eval_mask(mask: pd.Series):
            policy_points = self._policy_points_from_gate(raw_points, mask)
            k = max(1, int(len(policy_points) * top_share))
            top_idx = policy_points.sort_values(ascending=False).index[:k]
            prec_top = y_va.loc[top_idx].mean(); lift_top = prec_top / y_va.mean()
            order = policy_points.sort_values(ascending=False).index; y_ordered = y_va.loc[order].values
            if (y_ordered == 1).any():
                cum_tp = (y_ordered == 1).cumsum(); ranks = np.arange(1, len(y_ordered)+1)
                ap_like = (cum_tp[y_ordered==1] / ranks[y_ordered==1]).mean()
            else: ap_like = 0.0
            return {"prec_top": float(prec_top), "lift_top": float(lift_top), "ap_like": float(ap_like)}

        base = eval_mask(pd.Series(False, index=raw_points.index))
        best = None
        for name, mask in preds.items():
            if mask.mean() <= 0.0 or mask.mean() >= 0.9: continue
            k = max(1, int(len(raw_points) * top_share))
            top_idx0 = raw_points.sort_values(ascending=False).index[:k]
            intrusion = (mask.loc[top_idx0].mean()) / (mask.mean() or 1.0)
            mask_top = mask.loc[top_idx0]
            prec_gap = (y_va.loc[top_idx0][mask_top].mean() if mask_top.any() else base["prec_top"]) - base["prec_top"]
            if intrusion < min_intrusion and prec_gap >= -0.05: continue
            metrics = eval_mask(mask)
            gain_prec = metrics["prec_top"] - base["prec_top"]; gain_ap = metrics["ap_like"] - base["ap_like"]
            if (gain_ap > 0) or (gain_prec > min_prec_gain):
                key = (metrics["ap_like"], metrics["prec_top"], -mask.mean())
                if (best is None) or (key > best[0]): best = (key, {"name": name, "support": float(mask.mean()), "intrusion": float(intrusion),
                                                                   "gain_prec": float(gain_prec), "gain_ap": float(gain_ap)})
        self.gate_ = None if best is None else best[1]
        return self.gate_

    def validation_bucket_report(self, top_share: float = 0.10, use_policy: bool = False) -> pd.DataFrame:
        assert self.model_ is not None and self._validation_split_ is not None
        X_tr, X_va, y_tr, y_va = self._validation_split_
        raw_points, _ = self.model_.score_points(X_va)
        score_for_rank = raw_points.copy()
        if use_policy and self.gate_ is not None:
            mask_gate = self._predicate_to_mask(X_va, self.gate_["name"])
            score_for_rank = self._policy_points_from_gate(raw_points, mask_gate)
        k = max(1, int(len(score_for_rank) * top_share))
        order = score_for_rank.sort_values(ascending=False); top_idx = order.index[:k]
        prec_top = y_va.loc[top_idx].mean(); base_rate = y_va.mean()
        rows = []; preds = self._build_predicates(X_va); coefs = self.model_.coefs_; woe_maps = {fname: fb.woe_map for fname, fb in self.model_.features_.items()}
        for name, mask in preds.items():
            if mask.mean() <= 0 or mask.sum() < 10: continue
            n = int(mask.sum()); bucket_rate = y_va.loc[mask].mean(); prob_lift = (bucket_rate / base_rate) if base_rate > 0 else np.nan
            w, beta = 0.0, 0.0
            if "==" in name:
                feat, label = name.split("==", 1); w = woe_maps.get(feat, {}).get(label, 0.0); beta = coefs.get(feat, 0.0)
            model_odds_multiplier = float(np.exp(beta * w)); odds_lift_univar = float(np.exp(w))
            in_top = mask.loc[top_idx].mean(); intrusion = (in_top / mask.mean()) if mask.mean() > 0 else np.nan  # presence in top share vs prevalence
            # Safe precision among top-share restricted by predicate
            mask_top = mask.loc[top_idx]
            prec_in_top = y_va.loc[top_idx][mask_top].mean() if mask_top.any() else np.nan
            prec_gap = (prec_in_top - prec_top) if pd.notnull(prec_in_top) else np.nan
            rows.append({"predicate": name, "n": n, "share": float(mask.mean()), "bucket_rate": float(bucket_rate), "baseline_rate": float(base_rate),
                         "prob_lift": float(prob_lift), "WOE": float(w), "beta": float(beta), "odds_lift_univar": odds_lift_univar, "model_odds_multiplier": model_odds_multiplier,
                         "top_share_presence": float(in_top), "intrusion_ratio": float(intrusion), "top_share_precision_segment": float(prec_in_top) if pd.notnull(prec_in_top) else np.nan,
                         "top_share_precision_overall": float(prec_top), "precision_gap": float(prec_gap) if pd.notnull(prec_gap) else np.nan})
        cols = ["predicate", "n", "share", "bucket_rate", "baseline_rate", "prob_lift", "WOE", "beta", "odds_lift_univar",
                "model_odds_multiplier", "top_share_presence", "intrusion_ratio", "top_share_precision_segment",
                "top_share_precision_overall", "precision_gap"]
        if not rows:
            return pd.DataFrame(columns=cols)
        return pd.DataFrame(rows).sort_values(["intrusion_ratio", "precision_gap"], ascending=[False, True]).reset_index(drop=True)

    def learn_tier_cutoffs(self, top_share_hint: float = 0.10, precA_min: float = 0.40, covA_max: float = 0.12, grid: range = range(-30, 61)):
        assert self.model_ is not None and self._validation_split_ is not None
        X_tr, X_va, y_tr, y_va = self._validation_split_
        raw_points, _ = self.model_.score_points(X_va)
        points = raw_points.copy()
        if self.gate_ is not None:
            mask = self._predicate_to_mask(X_va, self.gate_["name"]); points = self._policy_points_from_gate(points, mask)
        best = None
        for cut_B in grid:
            for cut_A in grid:
                if cut_A <= cut_B: continue
                A = points >= cut_A; B = (points >= cut_B) & (~A)
                covA = A.mean(); precA = y_va.loc[A].mean() if A.any() else 0.0; precB = y_va.loc[B].mean() if B.any() else 0.0
                ok = (precA >= precA_min) and (covA <= covA_max); key = (precA, precB, -abs(covA - top_share_hint))
                if ok and ((best is None) or (key > best[0])): best = (key, {"cut_B": int(cut_B), "cut_A": int(cut_A)})
        if best is None:
            qB = int(np.percentile(points, 100*(1 - 2*top_share_hint))); qA = int(np.percentile(points, 100*(1 - top_share_hint)))
            self.tier_cuts_ = {"cut_B": qB, "cut_A": qA}
        else: self.tier_cuts_ = best[1]
        return self.tier_cuts_

    def _predicate_to_mask(self, X: pd.DataFrame, pred_name: str) -> pd.Series:
        preds = self._build_predicates(X);
        return preds.get(pred_name, pd.Series(False, index=X.index))

    def score_and_assign_tiers(self, df: pd.DataFrame):
        assert self.model_ is not None
        if self.tier_cuts_ is None: raise ValueError("Learn tier cutoffs first by calling learn_tier_cutoffs().")
        scored = self.score(df)
        policy = self.apply_policy_and_tiers(df=df, raw_points=scored["raw_points"])
        # Build a single DataFrame with key scoring outputs
        result_df = pd.DataFrame({
            "raw_points": scored["raw_points"].astype(int),
            "model_prob": scored["model_prob"].astype(float),
            "policy_points": policy["policy_points"].astype(int),
            "tier": policy["tier"].astype(str),
        }, index=df.index)
        return {
            # New consolidated DataFrame for convenience
            "scored": result_df,
            # Backwards-compatible individual outputs
            "model_prob": scored["model_prob"],
            "raw_points": scored["raw_points"],
            "policy_points": policy["policy_points"],
            "tier": policy["tier"],
            # Detailed breakdown
            "breakdown": scored["breakdown"],
            # Gate and tier metadata
            "gate_mask": policy["gate_mask"],
            "gate_name": policy["gate_name"],
            "tier_cuts": dict(self.tier_cuts_),
            "gate_info": dict(self.gate_) if self.gate_ is not None else None,
        }


    def score(self, df: pd.DataFrame) -> dict:
        """Compute per-row probabilities, raw points and points breakdown.

        Delegates to a single scoring path built from model specs to ensure parity with artifact-based scoring.
        Returns a dict with keys: model_prob (Series), raw_points (Series), breakdown (DataFrame).
        """
        assert self.model_ is not None
        from .scorer import build_specs_from_model, score_from_specs
        specs = build_specs_from_model(self.model_, tier_cuts=self.tier_cuts_)
        # Score using specs
        scored = score_from_specs(df, specs)
        model_prob = scored.get("p_calibrated", None)
        if model_prob is None:
            model_prob = scored.get("p_model")
        # For breakdown, still use model to produce per-feature points exactly as before
        raw_points, breakdown = self.model_.score_points(df)
        # Ensure raw_points parity with spec scorer
        try:
            if not raw_points.equals(scored["raw_points"].astype(int)):
                # If mismatch, favor spec scorer but keep both paths visible for debugging
                raw_points = scored["raw_points"].astype(int)
        except Exception:
            pass
        return {"model_prob": model_prob, "raw_points": raw_points, "breakdown": breakdown}

    def apply_policy_and_tiers(self, df: pd.DataFrame, raw_points: pd.Series) -> dict:
        """Apply gate penalty (if any) and assign tiers using learned cutoffs.

        Requires self.tier_cuts_ to be set (via learn_tier_cutoffs) and optionally self.gate_.
        Returns a dict with keys: policy_points (Series), tier (Series), gate_mask (Series), gate_name (str or None).
        """
        assert self.model_ is not None
        if self.tier_cuts_ is None:
            raise ValueError("Learn tier cutoffs first by calling learn_tier_cutoffs().")
        policy_points = raw_points.copy()
        gate_mask = pd.Series(False, index=df.index)
        gate_name = None
        if self.gate_ is not None:
            gate_mask = self._predicate_to_mask(df, self.gate_["name"])
            policy_points = self._policy_points_from_gate(raw_points, gate_mask)
            gate_name = self.gate_["name"]
        cut_B = self.tier_cuts_["cut_B"]; cut_A = self.tier_cuts_["cut_A"]
        tier = pd.Series("A", index=df.index)
        tier[policy_points.between(cut_B, cut_A - 1, inclusive="both")] = "B"
        tier[policy_points < cut_B] = "C"
        return {"policy_points": policy_points, "tier": tier, "gate_mask": gate_mask, "gate_name": gate_name}

    def save_artifacts(self, base_path: str = "/mnt/data/scorecard_artifacts"):
        import os; os.makedirs(base_path, exist_ok=True)
        points_df = self.export_points_tables(); points_csv = f"{base_path}/points_table.csv"; points_df.to_csv(points_csv, index=False)
        # Persist optional calibrator arrays if present
        calibrator_payload = None
        if getattr(self.model_, "calibrator_", None) is not None:
            cal = self.model_.calibrator_
            x = getattr(cal, "X_thresholds_", None)
            y = getattr(cal, "y_thresholds_", None)
            if x is not None and y is not None:
                calibrator_payload = {
                    "x": [float(v) for v in np.asarray(x).tolist()],
                    "y": [float(v) for v in np.asarray(y).tolist()],
                    "clip_min": float(getattr(self.model_, "_calib_x_min", -10.0)),
                    "clip_max": float(getattr(self.model_, "_calib_x_max", 10.0)),
                }
        # Write typed model.json and preprocess.json only
        model_json = f"{base_path}/model.json"
        payload = {"intercept": self.model_.intercept_, "scale": self.model_.scale_,
                   "features": {fname: {"points_map": fb.points_map} for fname, fb in self.model_.features_.items()},
                   "tier_cuts": self.tier_cuts_, "feature_kinds": self._kinds_}
        if calibrator_payload is not None:
            payload["calibrator"] = calibrator_payload
        with open(model_json, "w") as f: json.dump(payload, f, indent=2)
        # Also write unified specs.json for typed scorer usage
        try:
            from .specs import ScorecardSpecs, ModelSpec, FeaturePointsSpec
            feat_specs = {fname: FeaturePointsSpec(points_map=fb.points_map) for fname, fb in self.model_.features_.items()}
            m = ModelSpec(intercept=self.model_.intercept_, scale=self.model_.scale_, features=feat_specs,
                          calibrator=calibrator_payload, tier_cuts=self.tier_cuts_, feature_kinds=self._kinds_)
            specs = ScorecardSpecs(model=m)
            specs_path = f"{base_path}/specs.json"
            import json as _json
            with open(specs_path, "w") as f:
                f.write(specs.model_dump_json(indent=2))
        except Exception:
            specs_path = None
        return {"points_csv": points_csv, "model_json": model_json, **({"specs_json": specs_path} if specs_path else {})}

# Temporary alias for back-compat
ScorecardPipeline = ScorecardTrainer



def build_preprocess_config(X: pd.DataFrame, y: pd.Series, n_bins_numeric: int = 5, n_bins_cat_high: int = 6,
                            max_low_card: int = 25, test_size: float = 0.25, random_state: int = 42,
                            overrides: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Learn a compact features config from data, without applying it.

    Returns a dict: {"schema_version": "1.0", "features": [ {input, output, transform} ... ]}
    """
    X = X.copy(); y = y.astype(int).copy()
    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )
    transforms: Dict[str, Dict[str, Any]] = {}
    passthrough_id_cols = {c for c in X.columns if str(c).lower().endswith("_id")}
    for col in X.columns:
        s_all = X[col]
        if col in passthrough_id_cols:
            transforms[col] = {"kind": "passthrough"}
            continue
        if pd.api.types.is_bool_dtype(s_all) or is_boolean_like(s_all):
            transforms[col] = {"kind": "boolean_text"}
            continue
        if pd.api.types.is_numeric_dtype(s_all):
            s_tr = X_train[col].astype(float)
            _, edges = _quantile_bins(s_tr.dropna(), n_bins=n_bins_numeric)
            edges = ["-inf"] + [float(v) for v in open_outer_edges(edges)[1:-1]] + ["inf"]
            transforms[col] = {"kind": "numeric_binned", "edges": edges}
            continue
        nunique = s_all.dropna().astype("object").nunique()
        if nunique <= max_low_card:
            transforms[col] = {"kind": "categorical_low"}
        else:
            # Learn TE on training fold, then COMPILE to a category->bin mapping for runtime simplicity
            s_tr = X_train[col].astype("object")
            enc_tr, te_map, prior = _target_encode_oof(s_tr, y_train, n_splits=5, m=100.0, random_state=random_state)
            _, edges = _quantile_bins(enc_tr, n_bins=n_bins_cat_high)
            edges = open_outer_edges(edges)  # full-training encodings can exceed the OOF range; never map them to NaN
            # Build category -> bin label mapping using learned te_map and edges
            def _bucket(val: float):
                try:
                    return pd.cut(pd.Series([float(val)]), bins=edges, include_lowest=True, duplicates="drop").astype(str).iloc[0]
                except Exception:
                    return str(pd.Interval(left=float('-inf'), right=float('inf')))
            category_to_bin = {cat: _bucket(v) for cat, v in te_map.items()}
            unknown_bin = _bucket(prior)
            transforms[col] = {"kind": "categorical_mapping", "mapping": category_to_bin, "unknown_label": unknown_bin, "bin_col": f"{col}_bin"}

    overrides = overrides or {}
    for col, ovr in overrides.items():
        if col not in X.columns: continue
        base = transforms.get(col, {})
        if isinstance(ovr, dict):
            merged = base.copy(); merged.update({k: v for k, v in ovr.items() if v is not None})
            if ("mapping" in merged) and (merged.get("kind") != "passthrough"):
                merged["kind"] = "categorical_mapping"
            transforms[col] = merged

    # Build features list in input order
    features: List[Dict[str, Any]] = []
    for col, info in transforms.items():
        kind = info.get("kind")
        if kind == "boolean_text":
            features.append({"input": col, "output": col, "transform": {"boolean_text": True}})
        elif kind in ("boolean", "categorical_low", "passthrough"):
            features.append({"input": col, "output": col, "transform": None})
        elif kind == "numeric_binned":
            features.append({"input": col, "output": f"{col}_bin", "transform": {"edges": info.get("edges", []), "include_lowest": True, "closed": "right"}})
        elif kind == "categorical_high_binned":
            # Backward compatibility: if any legacy transforms exist
            features.append({"input": col, "output": f"{col}_bin", "transform": {"te_map": info.get("te_map", {}), "prior": info.get("prior", 0.5), "edges": info.get("edges", [])}})
        elif kind == "categorical_mapping":
            features.append({"input": col, "output": info.get("bin_col", f"{col}_bin"), "transform": {"mapping": info.get("mapping", {}), "unknown_label": info.get("unknown_label", "Other")}})
        elif kind == "categorical_mapping":
            features.append({"input": col, "output": info.get("bin_col", f"{col}_bin"), "transform": {"mapping": info.get("mapping", {}), "unknown_label": info.get("unknown_label", "Other")}})
        else:
            features.append({"input": col, "output": col, "transform": None})
    return {"schema_version": "1.0", "features": features}
def preprocess(df: pd.DataFrame, y_col: str, n_bins_numeric: int = 5, n_bins_cat_high: int = 6,
              max_low_card: int = 25, test_size: float = 0.25, random_state: int = 42,
              return_config: bool = False, overrides: Optional[Dict[str, Dict[str, Any]]] = None):
    """Learn bin edges/encodings on the training fold and apply to the full dataset.

    - Numeric columns (excluding boolean-like) are quantile-binned on the training split.
    - High-cardinality categoricals are target-encoded (OOF on training) then quantile-binned; labels applied to full data.
    - Low-cardinality categoricals and booleans are left as-is.
    - Original columns are NOT modified. New columns are emitted with suffix `_bin`.

    Returns (X, y) in sklearn style.
    If return_config is True, also returns a compact features config list describing input→output transforms.
    """
    assert y_col in df.columns, f"Missing target column {y_col}"
    y = df[y_col].astype(int)
    X = df.drop(columns=[y_col]).copy()
    # Build config from the provided dataset (learn using a train split)
    features_config = build_preprocess_config(
        X,
        y,
        n_bins_numeric=n_bins_numeric,
        n_bins_cat_high=n_bins_cat_high,
        max_low_card=max_low_card,
        test_size=test_size,
        random_state=random_state,
        overrides=overrides,
    )

    # Apply transforms to full dataset; DO NOT modify original columns. Write bins to <col>_bin
    # Apply config to the full dataset
    X_out = apply_preprocessing_config(X, features_config)

    # Select only training columns:
    # - keep raw for boolean and categorical_low
    # - keep <col>_bin for numeric_binned and categorical_high_binned
    feature_cols = [spec.get("output", spec.get("input")) for spec in features_config.get("features", [])]
    X_feats = X_out[feature_cols].copy()
    # Return X (training-only columns) and y separately; optionally include config
    if return_config:
        return X_feats, y, features_config
    return X_feats, y


def apply_preprocessing_config(df: pd.DataFrame, features_config: Any, overrides: Optional[Dict[str, Dict[str, Any]]] = None) -> pd.DataFrame:
    """Apply a compact features config (as emitted by preprocess with return_config=True) to raw df.

    - features_config can be either a dict with key "features" or a bare list of feature specs.
    - Each feature spec has: {"input": str, "output": str, "transform": None|dict}
      - If transform has "edges": numeric binning via saved edges
      - If transform has "mapping": categorical mapping; unseen → unknown_label (default "Other")
      - If transform has "te_map" and "edges": apply TE then bin by edges
      - If transform is None: passthrough (no change)
    - overrides can replace per-column transform dicts (by input column name)
    """
    # Normalize feature list
    feats: List[Dict[str, Any]] = features_config.get("features", features_config) if isinstance(features_config, dict) else features_config
    feats = list(feats or [])
    overrides = overrides or {}
    out = {}
    for spec in feats:
        col_in = spec.get("input")
        col_out = spec.get("output", col_in)
        base_t = spec.get("transform")
        ovr_t = overrides.get(col_in)
        t = base_t.copy() if isinstance(base_t, dict) else ({} if base_t is None else {})
        if isinstance(ovr_t, dict):
            t.update({k: v for k, v in ovr_t.items() if v is not None})

        if not t:
            # Passthrough
            out[col_out] = df[col_in]
            continue

        if t.get("boolean_text"):
            out[col_out] = canonical_bool(df[col_in])
            continue
        # Numeric edges
        if "edges" in t and ("te_map" not in t) and ("mapping" not in t):
            edges = t.get("edges", [])
            out[col_out] = _assign_bins_from_edges(df[col_in].astype(float), edges).astype(str)
            continue

        # Note: TE-at-runtime removed. TE is compiled to categorical_mapping in build_preprocess_config.

        # Categorical mapping
        if "mapping" in t:
            mapping = t.get("mapping", {})
            other_label = t.get("unknown_label", "Other")
            out[col_out] = df[col_in].astype("object").map(mapping).fillna(other_label).astype(str)
            continue

        # Fallback passthrough
        out[col_out] = df[col_in]

    # Assemble output DataFrame in declared order
    ordered_cols = [spec.get("output", spec.get("input")) for spec in feats]
    return pd.DataFrame(out, index=df.index)[ordered_cols]
