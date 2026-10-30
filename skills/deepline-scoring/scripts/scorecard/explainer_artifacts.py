from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Tuple
import json
import pandas as pd
import numpy as np


def assign_bins_numeric(s: pd.Series, edges: list) -> pd.Series:
    from .pipeline import _assign_bins_from_edges
    return _assign_bins_from_edges(s.astype(float), edges)


def _feature_specs_list(preprocess: Dict[str, Any]) -> list[dict]:
    if isinstance(preprocess, dict):
        feats = preprocess.get("features", [])
    else:
        feats = preprocess
    return list(feats or [])


def apply_feature_transform(df: pd.DataFrame, feature_spec: Dict[str, Any]) -> tuple[str, pd.Series]:
    col_in = feature_spec.get("input")
    col_out = feature_spec.get("output", col_in)
    t = feature_spec.get("transform") or {}
    # If the input column is missing but the output column already exists (pre-binned frame), use it directly
    if (col_in not in df.columns) and (col_out in df.columns):
        return col_out, df[col_out]
    if not t:
        return col_out, df[col_in]
    if t.get("boolean_text"):
        from .pipeline import canonical_bool
        return col_out, canonical_bool(df[col_in])
    if "edges" in t and ("mapping" not in t):
        return col_out, assign_bins_numeric(df[col_in], t["edges"])
    if "mapping" in t:
        mapping = t.get("mapping", {})
        other = t.get("unknown_label", "Other")
        return col_out, df[col_in].astype("object").map(mapping).fillna(other).astype(str)
    return col_out, df[col_in]


def points_map_for(specs: dict, out_col: str) -> Dict[str, int]:
    model = specs.get("model", {})
    feats = model.get("features", {}) or {}
    fdef = feats.get(out_col, {}) or {}
    return {str(k): int(v) for k, v in (fdef.get("points_map", {}) or {}).items()}


def build_binned_explainer(
    preprocess: Dict[str, Any],
    specs: Dict[str, Any],
    training_df: pd.DataFrame,
    y_col: str,
        model_version: str | None = None,
        overrides: Dict[str, Dict[str, int]] | None = None,
) -> pd.DataFrame:
    baseline_rate = float(training_df[y_col].astype(int).mean())
    rows = []
    for spec in _feature_specs_list(preprocess):
        col_in = spec.get("input")
        out_col, binned = apply_feature_transform(training_df, spec)
        if (col_in not in training_df.columns) and (out_col not in training_df.columns):
            continue
        pmap = points_map_for(specs, out_col)
        grp = pd.DataFrame({"bin_label": binned.astype("object").astype(str), "y": training_df[y_col].astype(int)})
        agg = grp.groupby("bin_label").agg(n=("y","size"), rate=("y","mean")).reset_index()
        agg["feature"] = str(out_col)
        agg["baseline_rate"] = baseline_rate
        agg["historical_lift"] = agg.apply(lambda r: float(r["rate"]/baseline_rate) if baseline_rate > 0 else np.nan, axis=1)
        agg["points"] = agg["bin_label"].map(pmap).fillna(0).astype(int)
        # Annotate overrides at binned level if provided
        if overrides and out_col in overrides:
            ovmap = overrides.get(out_col, {}) or {}
            agg["override_points"] = agg["bin_label"].map(lambda v: ovmap.get(str(v))).astype("Int64")
        else:
            agg["override_points"] = pd.Series([pd.NA] * len(agg), index=agg.index, dtype="Int64")
        rows.append(agg)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=[
        "feature","bin_label","n","rate","baseline_rate","historical_lift","points","override_points"
    ])
    out["ref_bin"] = (out["points"] == 0)
    if model_version is not None:
        out.insert(0, "model_version", str(model_version))
    return out.sort_values(["feature","points","n"], ascending=[True, False, False]).reset_index(drop=True)


def build_raw_explainer(
    preprocess: Dict[str, Any],
    specs: Dict[str, Any],
    training_df: pd.DataFrame,
    y_col: str,
        model_version: str | None = None,
        overrides: Dict[str, Dict[str, int]] | None = None,
) -> pd.DataFrame:
    """
    Unified "raw" explainer:
      - For mapped categoricals: include raw_value and bin_label rows.
      - For numeric/edge-binned features: include bin-level rows with raw_value set to None.
    """
    baseline_rate = float(training_df[y_col].astype(int).mean())
    rows: list[pd.DataFrame] = []
    for spec in _feature_specs_list(preprocess):
        col_in = spec.get("input")
        out_col = spec.get("output", col_in)
        t = spec.get("transform") or {}
        mapping = t.get("mapping") if isinstance(t, dict) else None
        pmap = points_map_for(specs, out_col)

        if mapping:
            # Raw categorical values mapped to bins
            if col_in not in training_df.columns:
                continue
            other = t.get("unknown_label", "Other")
            bin_s = training_df[col_in].astype("object").map(mapping).fillna(other).astype(str)
            raw_vals = training_df[col_in].astype("object")
            tmp = pd.DataFrame({"raw_value": raw_vals, "bin_label": bin_s, "y": training_df[y_col].astype(int)})
            agg = tmp.groupby(["raw_value","bin_label"]).agg(n=("y","size"), rate=("y","mean")).reset_index()
            agg["feature"] = str(col_in)
            agg["baseline_rate"] = baseline_rate
            agg["historical_lift"] = agg.apply(lambda r: float(r["rate"]/baseline_rate) if baseline_rate > 0 else np.nan, axis=1)
            agg["points"] = agg["bin_label"].map(pmap).fillna(0).astype(int)
            # Add override annotation for raw level
            if overrides and ((spec.get("transform", {}) or {}).get("mapping") or True):
                ovmap = (overrides.get(col_in, {}) or {})
                ov_series = agg["raw_value"].map(lambda v: ovmap.get(str(v)))
                agg["override_points"] = ov_series.astype("Int64")
            else:
                agg["override_points"] = pd.Series([pd.NA] * len(agg), index=agg.index, dtype="Int64")
            rows.append(agg[["feature","raw_value","bin_label","n","rate","baseline_rate","historical_lift","points","override_points"]])
        else:
            # Numeric features: emit bin-level rows (raw_value is None)
            out_col2, binned_series = apply_feature_transform(training_df, spec)
            if out_col2 is None:
                continue
            grp = pd.DataFrame({"bin_label": binned_series.astype("object").astype(str), "y": training_df[y_col].astype(int)})
            agg = grp.groupby("bin_label").agg(n=("y","size"), rate=("y","mean")).reset_index()
            agg["feature"] = str(out_col)
            agg["raw_value"] = None
            agg["baseline_rate"] = baseline_rate
            agg["historical_lift"] = agg.apply(lambda r: float(r["rate"]/baseline_rate) if baseline_rate > 0 else np.nan, axis=1)
            agg["points"] = agg["bin_label"].map(pmap).fillna(0).astype(int)
            rows.append(agg[["feature","raw_value","bin_label","n","rate","baseline_rate","historical_lift","points"]])

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=[
        "feature","raw_value","bin_label","n","rate","baseline_rate","historical_lift","points","override_points"
    ])
    if model_version is not None:
        out.insert(0, "model_version", str(model_version))
    return out.sort_values(["feature","points","n"], ascending=[True, False, False]).reset_index(drop=True)


def write_explainers_to_csv(
    preprocess_path: str,
    specs_path: str,
    training_csv_path: str,
    y_col: str,
    out_dir: str,
    model_version: str | None = None,
) -> Dict[str, str]:
    pre = json.loads(Path(preprocess_path).read_text())
    specs = json.loads(Path(specs_path).read_text())
    df = pd.read_csv(training_csv_path, dtype=str, keep_default_na=False).replace({"": np.nan})  # keep "NA"/"None" categories literal
    # Load overrides.json if present alongside specs
    overrides_path = Path(specs_path).parent / "overrides.json"
    overrides: Dict[str, Dict[str, int]] | None = None
    if overrides_path.exists():
        try:
            overrides = json.loads(overrides_path.read_text())
        except Exception:
            overrides = None
    binned = build_binned_explainer(pre, specs, df, y_col, model_version=model_version, overrides=overrides)
    raw = build_raw_explainer(pre, specs, df, y_col, model_version=model_version, overrides=overrides)
    base = Path(out_dir); base.mkdir(parents=True, exist_ok=True)
    p1 = base / "scorecard_explainer_binned.csv"
    p2 = base / "scorecard_explainer_raw.csv"
    binned.to_csv(p1, index=False)
    raw.to_csv(p2, index=False)
    return {"binned_csv": str(p1), "raw_csv": str(p2)}
