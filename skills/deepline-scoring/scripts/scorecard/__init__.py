"""Scorecard package: ported from dbt-aero lib/scorecard (Prove propensity run, 2025-09) with a lift mode added."""
from .pipeline import ScorecardTrainer, ScorecardPipeline, build_preprocess_config, apply_preprocessing_config
from .scorer import ScorecardScorer, ScorecardRunner, load_specs, score_from_specs, build_specs_from_model
from .specs import ScorecardSpecs, ModelSpec, PreprocessSpec
from .report import generate_reports, train_scorecard, build_top_contributors
from .config import RunConfig, JobConfig
