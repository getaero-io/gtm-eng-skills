import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from .explainer_artifacts import build_binned_explainer, build_raw_explainer
from .pipeline import canonical_bool


def _interp_calibration(logit: pd.Series, calibrator: Dict[str, Any]) -> pd.Series:
    """Map logits through the saved isotonic calibrator. Input must be logits (not probabilities)."""
    if not calibrator:
        return 1.0 / (1.0 + np.exp(-logit.astype(float)))
    x = np.asarray(calibrator.get("x", []), dtype=float)
    y = np.asarray(calibrator.get("y", []), dtype=float)
    if x.size == 0 or y.size == 0:
        return 1.0 / (1.0 + np.exp(-logit.astype(float)))
    clip_min = float(calibrator.get("clip_min", -10.0))
    clip_max = float(calibrator.get("clip_max", 10.0))
    logits = np.clip(logit.astype(float).values, clip_min, clip_max)
    return pd.Series(np.interp(logits, x, y), index=logit.index)


def build_specs_from_model(model, tier_cuts: Dict[str, int] = None) -> Dict[str, Any]:
    """Construct scoring specs from an in-memory ScorecardModel for artifact-only scoring functions.

    Returns a dict with keys: preprocess (feature kinds), model (intercept, scale, points_map per feature, calibrator arrays, tier_cuts).
    """
    feats = {}
    for fname, fb in model.features_.items():
        feats[fname] = {
            "kind": getattr(fb, "kind", "categorical_low"),
            "points_map": dict(getattr(fb, "points_map", {}) or {}),
        }
    calibrator_spec = None
    if getattr(model, "calibrator_", None) is not None:
        cal = model.calibrator_
        # sklearn isotonic uses attributes X_thresholds_ / y_thresholds_
        x = getattr(cal, "X_thresholds_", None)
        y = getattr(cal, "y_thresholds_", None)
        if x is not None and y is not None:
            calibrator_spec = {
                "x": [float(v) for v in np.asarray(x).tolist()],
                "y": [float(v) for v in np.asarray(y).tolist()],
                "clip_min": float(getattr(model, "_calib_x_min", -10.0)),
                "clip_max": float(getattr(model, "_calib_x_max", 10.0)),
            }
    model_spec = {
        "intercept": float(model.intercept_),
        "scale": int(model.scale_),
        "features": feats,
        **({"calibrator": calibrator_spec} if calibrator_spec is not None else {}),
        **({"tier_cuts": dict(tier_cuts)} if tier_cuts is not None else {}),
    }
    return {"model": model_spec}


def score_from_specs(
    X_binned: pd.DataFrame,
    specs: Dict[str, Any],
    overrides: Optional[Dict[str, Dict[str, int]]] = None,
    X_raw: Optional[pd.DataFrame] = None,
    preprocess_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, pd.Series]:
    """Score pre-binned features using model specs, with optional replacement overrides.

    Precedence: binned feature overrides > raw feature overrides.
    Returns dict with keys: raw_points, logit, p_model, p_calibrated (if calibrator present), breakdown.
    """
    model_spec = specs.get("model", {})
    intercept = float(model_spec.get("intercept", 0.0))
    scale = float(model_spec.get("scale", 1.0))
    feats = (model_spec.get("features", {}) or {})

    # 1) Baseline per-feature points breakdown from points_map
    breakdown_cols: Dict[str, pd.Series] = {}
    for fname, fdef in feats.items():
        if fname not in X_binned.columns:
            breakdown_cols[fname] = pd.Series(0, index=X_binned.index, dtype=int)
            continue
        points_map = fdef.get("points_map", {}) or {}
        s = X_binned[fname].astype("object").astype(str)
        breakdown_cols[fname] = s.map(points_map).fillna(0).astype(int)
    breakdown_df = pd.DataFrame(breakdown_cols, index=X_binned.index).astype(int)

    # 2) Apply overrides (replacement-only)
    if overrides:
        # Build mapping from binned output → raw input to support raw-level overrides
        out_to_in: Dict[str, str] = {}
        if preprocess_spec and isinstance(preprocess_spec.get("features", []), list):
            for spec in preprocess_spec.get("features", []):
                col_in = spec.get("input")
                col_out = spec.get("output", col_in)
                if col_in and col_out:
                    out_to_in[str(col_out)] = str(col_in)

        for fname in breakdown_df.columns:
            series_override: Optional[pd.Series] = None

            # 2a) Binned-level override using the binned feature name
            if fname in overrides:
                ov_map = overrides.get(fname, {}) or {}
                if fname in X_binned.columns:
                    s = X_binned[fname].astype("object").astype(str)
                    series_override = s.map(ov_map)

            # 2b) Raw-level override using the original raw input name (if no binned override applied)
            if (series_override is None or series_override.isna().all()) and X_raw is not None:
                raw_in = out_to_in.get(fname)
                if raw_in and (raw_in in overrides) and (raw_in in X_raw.columns):
                    ov_map_raw = overrides.get(raw_in, {}) or {}
                    s2 = X_raw[raw_in].astype("object").astype(str)
                    series_override = s2.map(ov_map_raw)

            # 2c) Replacement-only where override is not null
            if series_override is not None:
                mask = series_override.notna()
                if mask.any():
                    replacement = series_override.where(mask, other=breakdown_df[fname])
                    breakdown_df[fname] = replacement.fillna(breakdown_df[fname]).astype(int)

    # 3) Sum and compute logits/probabilities
    raw_points = breakdown_df.sum(axis=1).astype(int)
    logit = intercept + (raw_points.astype(float) / scale)
    p_model = 1.0 / (1.0 + np.exp(-logit))

    out: Dict[str, pd.Series] = {
        "raw_points": raw_points,
        "logit": pd.Series(logit, index=X_binned.index),
        "p_model": pd.Series(p_model, index=X_binned.index),
        "breakdown": breakdown_df,
    }
    calibrator = model_spec.get("calibrator")
    if calibrator is not None:
        out["p_calibrated"] = _interp_calibration(out["logit"], calibrator)
    return out


def assign_tiers_from_specs(raw_points: pd.Series, specs: Dict[str, Any]) -> pd.Series:
    model_spec = specs.get("model", {})
    cuts = model_spec.get("tier_cuts") or {}
    cut_A = cuts.get("cut_A")
    cut_B = cuts.get("cut_B")
    if cut_A is None or cut_B is None:
        return pd.Series("A", index=raw_points.index)
    tier = pd.Series("A", index=raw_points.index)
    tier[raw_points.between(int(cut_B), int(cut_A) - 1, inclusive="both")] = "B"
    tier[raw_points < int(cut_B)] = "C"
    return tier


def load_specs(model_dir: str) -> Dict[str, Any]:
    """Load scoring specs: specs.json, then model.json, then the legacy model_meta.json + features.json pair."""
    base = Path(model_dir)
    specs_path = base / "specs.json"
    if specs_path.exists():
        return json.loads(specs_path.read_text())
    model_json = base / "model.json"
    if model_json.exists():
        return {"model": json.loads(model_json.read_text())}
    meta_path, feats_path = base / "model_meta.json", base / "features.json"
    if not (meta_path.exists() and feats_path.exists()):
        raise FileNotFoundError(f"no specs.json, model.json or model_meta.json+features.json in {model_dir}")
    meta = json.loads(meta_path.read_text()); feats = json.loads(feats_path.read_text())
    model_spec = {
        "intercept": float(meta.get("intercept", 0.0)),
        "scale": int(meta.get("scale", 1)),
        "features": {k: {"points_map": v.get("points_map", {}), "kind": v.get("kind", "categorical_low")} for k, v in feats.items()},
        "tier_cuts": meta.get("tier_cuts"),
    }
    if "calibrator" in meta:
        model_spec["calibrator"] = meta["calibrator"]
    return {"model": model_spec}


class ScorecardScorer:
    """Lightweight scorer that uses saved specs only.

    Usage:
      scorer = ScorecardScorer.from_dir(dir)
      out = scorer.score(X_binned)
      proba = scorer.predict_proba(X_binned, calibrated=True)
      tiers = scorer.assign_tiers(out["raw_points"])
    """

    def __init__(self, specs: Dict[str, Any]):
        self.specs = specs

    @classmethod
    def from_dir(cls, artifacts_dir: str) -> "ScorecardScorer":
        return cls(load_specs(artifacts_dir))

    def score(self, X_binned: pd.DataFrame) -> Dict[str, pd.Series]:
        return score_from_specs(X_binned, self.specs)

    def predict_proba(self, X_binned: pd.DataFrame, calibrated: bool = True) -> pd.Series:
        out = score_from_specs(X_binned, self.specs)
        if calibrated and (out.get("p_calibrated") is not None):
            return out["p_calibrated"]
        return out["p_model"]

    def assign_tiers(self, raw_points: pd.Series) -> pd.Series:
        return assign_tiers_from_specs(raw_points, self.specs)

    def explain_points(self, X_binned: pd.DataFrame, top_n: int = 5) -> pd.Series:
        feats = (self.specs.get("model", {}).get("features", {}) or {})
        # Build per-feature points matrix
        cols = {}
        for fname, fdef in feats.items():
            pm = fdef.get("points_map", {}) or {}
            if fname in X_binned.columns:
                s = X_binned[fname].astype("object").astype(str)
                cols[fname] = s.map(pm).fillna(0).astype(int)
            else:
                cols[fname] = pd.Series(0, index=X_binned.index, dtype=int)
        breakdown = pd.DataFrame(cols, index=X_binned.index).astype(int)

        def _row_explain(idx: int) -> str:
            row = breakdown.iloc[idx]
            pos = row[row > 0].sort_values(ascending=False).head(top_n)
            return "\n".join([f"(+{int(v)}) {k}: {str(X_binned.iloc[idx][k]) if k in X_binned.columns else ''}" for k, v in pos.items()])

        return pd.Series([_row_explain(i) for i in range(len(breakdown))], index=X_binned.index)


class ScorecardRunner:
    """End-to-end runner that applies preprocessing then scores using ScorecardScorer.

    Expects two files in artifacts_dir:
      - preprocess.json (typed features with transforms)
      - model.json (typed model spec)
    """

    def __init__(self, preprocess_spec: Dict[str, Any], model_spec: Dict[str, Any]):
        self.preprocess_spec = preprocess_spec
        self.scorer = ScorecardScorer({"model": model_spec})
        # Optional percentile cuts (length 101 for percentiles 0..100) on raw_points only
        self.percentile_cuts = None
        # Artifact directory and overrides loaded when constructed via from_dir
        self.artifacts_dir: Optional[Path] = None
        self.overrides: Optional[Dict[str, Dict[str, int]]] = None
        self.reference: Optional[Dict[str, Any]] = None  # frozen reference.json: sorted training points
        try:
            cuts_rp = (model_spec or {}).get("raw_points_percentile_cuts")
            if isinstance(cuts_rp, list) and len(cuts_rp) >= 2:
                self.percentile_cuts = [float(x) for x in cuts_rp]
        except Exception:
            self.percentile_cuts = None

    @classmethod
    def from_dir(cls, artifacts_dir: str) -> "ScorecardRunner":
        base = Path(artifacts_dir)
        pre_path = base / "preprocess.json"
        if not pre_path.exists():
            raise FileNotFoundError(f"preprocess.json missing in {artifacts_dir}; a bundle needs preprocess.json plus specs.json or model.json")
        preprocess_spec = json.loads(pre_path.read_text())
        model_spec = load_specs(artifacts_dir).get("model", {})
        inst = cls(preprocess_spec, model_spec)
        inst.artifacts_dir = base
        ov_path = base / "overrides.json"
        if ov_path.exists():
            inst.overrides = json.loads(ov_path.read_text())
        ref_path = base / "reference.json"
        if ref_path.exists():
            inst.reference = json.loads(ref_path.read_text())
        cuts_rp_path = base / "raw_points_percentile_cuts.json"
        if cuts_rp_path.exists() and inst.percentile_cuts is None:
            cuts_payload = json.loads(cuts_rp_path.read_text())
            cuts = cuts_payload.get("raw_points_percentile_cuts") if isinstance(cuts_payload, dict) else None
            if isinstance(cuts, list) and len(cuts) >= 2:
                inst.percentile_cuts = [float(x) for x in cuts]
        return inst

    def _apply_preprocessing(self, df: pd.DataFrame) -> pd.DataFrame:
        feats = self.preprocess_spec.get("features", [])
        out = {}
        for spec in feats:
            col_in = spec.get("input")
            col_out = spec.get("output", col_in)
            t = spec.get("transform") or {}
            if not t:
                out[col_out] = df[col_in]
                continue
            if t.get("boolean_text"):
                out[col_out] = canonical_bool(df[col_in])
                continue
            if "edges" in t and ("mapping" not in t):
                from .pipeline import _assign_bins_from_edges
                out[col_out] = _assign_bins_from_edges(df[col_in].astype(float), t.get("edges", []))
                continue
            if "mapping" in t:
                mapping = t.get("mapping", {})
                other = t.get("unknown_label", "Other")
                out[col_out] = df[col_in].astype("object").map(mapping).fillna(other).astype(str)
                continue
            out[col_out] = df[col_in]
        ordered_cols = [spec.get("output", spec.get("input")) for spec in feats]
        return pd.DataFrame(out, index=df.index)[ordered_cols]

    def score(self, raw_df: pd.DataFrame) -> Dict[str, pd.Series]:
        Xb = self._apply_preprocessing(raw_df)
        # Use override-aware scoring so final points/prob reflect overrides
        out = score_from_specs(
            X_binned=Xb,
            specs=self.scorer.specs,
            overrides=self.overrides,
            X_raw=raw_df,
            preprocess_spec=self.preprocess_spec,
        )
        # Frozen-reference percentile (exact-numeric midrank) and A/B/C/D grade
        if self.reference and self.reference.get("scores"):
            ref = np.sort(np.asarray(self.reference["scores"], dtype=float))
            m = self.scorer.specs.get("model", {})
            pts = float(int(round(float(m.get("intercept", 0.0)) * float(m.get("scale", 1))))) + out["raw_points"].astype(float).values  # reference.json stores round(intercept*scale) + points
            if len(np.unique(ref)) < 2:
                out["percentile"] = pd.Series(np.nan, index=raw_df.index); out["grade"] = pd.Series(None, index=raw_df.index, dtype=object)
                out["grade_reason"] = pd.Series("insufficient_reference_variation", index=raw_df.index)
            else:
                less = np.searchsorted(ref, pts, side="left"); le = np.searchsorted(ref, pts, side="right")
                pct = 100.0 * (less + (le - less) / 2.0) / len(ref)
                out["percentile"] = pd.Series(pct, index=raw_df.index)
                out["grade"] = pd.Series(np.select([pct >= 90, pct >= 75, pct >= 50], ["A", "B", "C"], "D"), index=raw_df.index)
                out["grade_reason"] = pd.Series("", index=raw_df.index)
        # Attach percentile rank if cuts are available
        try:
            series_len = len(raw_df)
            if isinstance(self.percentile_cuts, list) and len(self.percentile_cuts) >= 2:
                cuts = np.asarray(self.percentile_cuts, dtype=float)
                base = out.get("raw_points")
                vals = base.astype(float).values if isinstance(base, pd.Series) else np.full(series_len, np.nan)
                idx = np.searchsorted(cuts, vals, side="right") - 1
                idx = np.clip(idx, 0, len(cuts) - 1)
                out["pctl"] = pd.Series(idx, index=(base.index if isinstance(base, pd.Series) else None))
            else:
                n = len(out.get("raw_points")) if isinstance(out.get("raw_points"), pd.Series) else series_len
                out["pctl"] = pd.Series([None] * n, index=(out.get("raw_points").index if isinstance(out.get("raw_points"), pd.Series) else None), dtype=object)
        except Exception:
            out["pctl"] = pd.Series([None] * len(raw_df), index=raw_df.index, dtype=object)
        return out

    def predict_proba(self, raw_df: pd.DataFrame, calibrated: bool = True) -> pd.Series:
        out = self.score(raw_df)  # override-aware path
        if calibrated and out.get("p_calibrated") is not None:
            return out["p_calibrated"]
        return out["p_model"]

    def assign_tiers(self, raw_df: pd.DataFrame) -> pd.Series:
        out = self.score(raw_df)
        return self.scorer.assign_tiers(out["raw_points"])

    def predict_percentile(self, raw_df: pd.DataFrame) -> pd.Series:
        out = self.score(raw_df)
        pctl = out.get("pctl")
        if isinstance(pctl, pd.Series):
            return pctl
        # fallback: nulls
        p = out.get("p_calibrated") if out.get("p_calibrated") is not None else out.get("p_model")
        n = len(p) if isinstance(p, pd.Series) else len(raw_df)
        return pd.Series([None] * n)

    def build_explainers(self, training_df: pd.DataFrame, y_col: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Build binned and raw explainers using this runner's specs and overrides.

        Returns (binned_df, raw_df).
        """
        pre = self.preprocess_spec
        specs = self.scorer.specs
        binned = build_binned_explainer(pre, specs, training_df, y_col, overrides=self.overrides)
        raw = build_raw_explainer(pre, specs, training_df, y_col, overrides=self.overrides)
        return binned, raw
