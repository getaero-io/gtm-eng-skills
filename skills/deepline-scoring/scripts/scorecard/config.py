from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union, Literal

from pydantic import BaseModel, Field, model_validator
from typing import Dict


class GateRunConfig(BaseModel):
    enable: bool = Field(default=False)
    min_intrusion: float = Field(default=2.0)
    min_prec_gain: float = Field(default=0.0)


class TiersRunConfig(BaseModel):
    enable: bool = Field(default=True)
    precA_min: float = Field(default=0.40)
    covA_max: float = Field(default=0.12)


class PolicyRule(BaseModel):
    id: str
    target: str  # column name (raw or engineered bin)
    source: Literal["raw", "bin"] = Field(default="raw")
    op: Literal["lte", "gte", "eq", "in", "between", "regex"] = Field(default="eq")
    value: Optional[Union[float, str]] = Field(default=None)
    values: Optional[List[Union[float, str]]] = Field(default=None)
    override_points: int = Field(default=0)
    enabled: bool = Field(default=True)
    priority: int = Field(default=100)

    @model_validator(mode="after")
    def _validate_values(self) -> "PolicyRule":
        if self.op == "between":
            if not self.values or len(self.values) != 2:
                raise ValueError("'between' op requires values: [low, high]")
        if self.op == "in":
            if not self.values or len(self.values) == 0:
                raise ValueError("'in' op requires non-empty values list")
        if self.op in ("lte","gte","eq","regex") and self.value is None:
            raise ValueError(f"'{self.op}' op requires 'value'")
        return self


class PolicyConfig(BaseModel):
    rules: List[PolicyRule] = Field(default_factory=list)
    combine: Literal["sum", "max"] = Field(default="sum")


class CatBinningConfig(BaseModel):
    mode: Literal["te", "lift", "raw"] = Field(default="te")
    columns: List[str] = Field(default_factory=list)
    bucket_col_suffix: str = Field(default="_BIN")
    drop_raw_cat: bool = Field(default=True)
    lift_edges: Union[Literal["auto"], List[float]] = Field(default=[1.5, 3.0])
    min_n: int = Field(default=50, ge=0)
    min_pos: int = Field(default=3, ge=0)
    zero_conv_min_n: int = Field(default=25, ge=0)

    @model_validator(mode="after")
    def validate_lift_edges(self) -> "CatBinningConfig":
        if isinstance(self.lift_edges, list):
            if len(self.lift_edges) != 2 or not (self.lift_edges[0] < self.lift_edges[1]):
                raise ValueError("lift_edges must be 'auto' or two ascending floats, e.g. [1.5, 3.0]")
        return self


class PreprocessConfig(BaseModel):
    enable: bool = Field(default=False)
    cat_binning: Optional[CatBinningConfig] = Field(default=None)
    # numeric binning: create engineered categorical bins from numeric columns
    numeric_bins: Dict[str, "NumericBinSpec"] = Field(default_factory=dict)


class RunConfig(BaseModel):
    y_col: str
    # "logistic" = propensity model (L1 logistic on WOE bins); "naive_bayes" = lift model (additive WOE points)
    method: Literal["logistic", "naive_bayes"] = Field(default="naive_bayes")
    woe_prior: float = Field(default=0.5, gt=0.0)
    max_features: Optional[int] = Field(default=None, ge=1)
    max_abs_points: Optional[int] = Field(default=None, ge=1)
    test_size: float = Field(default=0.25, ge=0.0, le=0.9)
    random_state: int = Field(default=42)
    do_calibration: bool = Field(default=True)
    n_bins_numeric: int = Field(default=5, ge=2)
    n_bins_cat_high: int = Field(default=6, ge=2)
    max_low_card: int = Field(default=25, ge=1)
    l1_C: float = Field(default=1.0, gt=0.0)
    scale: int = Field(default=10, ge=1)
    top_share: float = Field(default=0.10, gt=0.0, le=1.0)
    gate: GateRunConfig = Field(default_factory=GateRunConfig)
    tiers: TiersRunConfig = Field(default_factory=TiersRunConfig)
    policy: Optional[PolicyConfig] = Field(default=None)
    # Optional: columns to pass through (identifiers) that should not be treated as model features
    id_columns: Optional[List[str]] = Field(default=None)


class JobConfig(BaseModel):
    csv: Path
    out_dir: Path = Field(default=Path("tmp_reports/scorecard_out"))
    include_cols: Optional[List[str]] = Field(default=None)
    exclude_cols: Optional[List[str]] = Field(default=None)
    run: RunConfig
    preprocess: PreprocessConfig = Field(default_factory=PreprocessConfig)

    @model_validator(mode="after")
    def validate_columns(self) -> "JobConfig":
        if self.include_cols and self.exclude_cols:
            overlap = set(self.include_cols).intersection(set(self.exclude_cols))
            if overlap:
                raise ValueError(f"include_cols and exclude_cols overlap: {sorted(overlap)}")
        return self
class NumericBinSpec(BaseModel):
    edges: List[Union[float, str]]
    unknown_bin: str = Field(default="Unknown")
    bin_name: Optional[str] = Field(default=None)
    drop_raw: bool = Field(default=True)

    @model_validator(mode="after")
    def _validate_edges(self) -> "NumericBinSpec":
        if not self.edges or len(self.edges) < 2:
            raise ValueError("numeric_bins.edges must provide at least two boundaries")
        return self
