from __future__ import annotations

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class FeaturePointsSpec(BaseModel):
    points_map: Dict[str, int] = Field(default_factory=dict)


class CalibratorSpec(BaseModel):
    x: List[float]
    y: List[float]
    clip_min: float
    clip_max: float


class TierCuts(BaseModel):
    cut_A: int
    cut_B: int


class ModelSpec(BaseModel):
    intercept: float
    scale: int
    features: Dict[str, FeaturePointsSpec] = Field(default_factory=dict)
    calibrator: Optional[CalibratorSpec] = None
    tier_cuts: Optional[TierCuts] = None
    feature_kinds: Optional[Dict[str, Literal["boolean","categorical_low","numeric"]]] = None


class ScorecardSpecs(BaseModel):
    schema_version: str = Field(default="1.0")
    model: ModelSpec


# --- Preprocess typed specs (lightweight, no validators) ---

class TransformSpec(BaseModel):
    edges: Optional[List[float]] = None
    include_lowest: Optional[bool] = None
    closed: Optional[Literal["right","left"]] = "right"
    mapping: Optional[Dict[str, str]] = None
    unknown_label: Optional[str] = None


class FeatureSpec(BaseModel):
    input: str
    output: str
    transform: Optional[TransformSpec] = None


class PreprocessSpec(BaseModel):
    schema_version: str = Field(default="1.0")
    features: List[FeatureSpec]
