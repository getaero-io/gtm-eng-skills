"""Known-answer checks for the ported scorecard package and the training CLI.

Synthetic data only (no customer rows). Run:  .venv/bin/python -m pytest scripts/tests -q
or plainly:  .venv/bin/python scripts/tests/test_scorecard.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from scorecard import ScorecardRunner, ScorecardTrainer, build_preprocess_config, apply_preprocessing_config  # noqa: E402


def synthetic(n: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    strong = rng.random(n) < 0.35
    weak = rng.random(n) < 0.5
    noise = rng.random(n) < 0.5
    size = rng.lognormal(5, 1.2, n).round()
    industry = rng.choice(["fintech", "health", "retail", "saas", "other"], n)
    logit = -2.2 + 2.0 * strong + 0.6 * weak + 0.4 * (industry == "fintech") + 0.0003 * size
    y = rng.random(n) < 1 / (1 + np.exp(-logit))
    return pd.DataFrame({"domain": [f"acct{i}.example" for i in range(n)],
                         "status": np.where(y, "won", "lost"),
                         "strong_signal": strong, "weak_signal": weak, "noise_signal": noise,
                         "employees": size, "industry": industry})


def test_lift_mode_points_follow_prevalence_ratio():
    df = synthetic()
    X = df.drop(columns=["domain", "status"])
    y = (df["status"] == "won").astype(int)
    cfg = build_preprocess_config(X, y, test_size=0.3, random_state=1)
    Xb = apply_preprocessing_config(X, cfg)
    frame = Xb.copy(); frame["__Y__"] = y.values
    t = ScorecardTrainer(y_col="__Y__", method="naive_bayes", test_size=0.3, random_state=1, do_calibration=False)
    model = t.fit(frame)
    assert all(abs(v - 1.0) < 1e-9 for v in model.coefs_.values()), "lift mode must not fit weights"
    pts = model.features_["strong_signal"].points_map
    assert pts["True"] > pts["False"] and pts["True"] >= 8, pts
    assert abs(model.features_["noise_signal"].points_map["True"]) <= 3
    total, breakdown = model.score_points(Xb)
    assert (breakdown.sum(axis=1) == total).all()


def test_propensity_mode_fits_and_tiers():
    df = synthetic(n=800)
    X = df.drop(columns=["domain", "status"]); y = (df["status"] == "won").astype(int)
    cfg = build_preprocess_config(X, y, test_size=0.3, random_state=2)
    Xb = apply_preprocessing_config(X, cfg); frame = Xb.copy(); frame["__Y__"] = y.values
    t = ScorecardTrainer(y_col="__Y__", method="logistic", test_size=0.3, random_state=2)
    model = t.fit(frame)
    assert model.coefs_["strong_signal"] > 0.3
    assert t.validation_report()["auc"] > 0.65
    cuts = t.learn_tier_cutoffs()
    assert cuts["cut_A"] > cuts["cut_B"]


def test_cli_lift_end_to_end_and_artifact_replay(tmp_path: Path):
    df = synthetic(n=300)
    # unlabeled rows must be scored but never fitted on
    df.loc[df.index[:30], "status"] = "unlabeled"
    src = tmp_path / "features.csv"; df.to_csv(src, index=False)
    out = tmp_path / "run"
    cmd = [sys.executable, str(SCRIPTS / "train_scorecard.py"), "--input", str(src), "--out-dir", str(out),
           "--mode", "lift", "--random-state", "3"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr[-2000:]
    for name in ("preprocess.json", "specs.json", "model.json", "scores.csv", "reference.json",
                 "model_contract.json", "points_table.csv", "scorecard_explainer_binned.csv", "run_meta.json"):
        assert (out / name).exists(), name
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["rows_fit"] == 270 and meta["rows_unlabeled"] == 30 and meta["mode"] == "lift"
    scores = pd.read_csv(out / "scores.csv")
    assert len(scores) == 300 and set(scores["grade"].dropna()) <= {"A", "B", "C", "D"}
    assert (scores.loc[scores.row_role == "unlabeled", "status"] == "scored").all()
    # Replay: the saved artifacts reproduce the CLI's points exactly
    runner = ScorecardRunner.from_dir(str(out))
    replay = runner.score(df.drop(columns=["domain", "status"]))
    assert (replay["raw_points"].astype(int).values == scores["points"].values).all()
    # Runner grades against the frozen reference with the same midrank percentiles as the CLI
    assert np.allclose(replay["percentile"].values, scores["percentile"].values, equal_nan=True)
    assert (replay["grade"].astype(str).values == scores["grade"].astype(str).values).all()
    # Contract: one weight per feature (1/scale); observation value = the row's bin points; score = logit
    contract = json.loads((out / "model_contract.json").read_text())
    pre = json.loads((out / "preprocess.json").read_text())
    binned = apply_preprocessing_config(df.drop(columns=["domain", "status"]), pre)
    row = binned.iloc[0]
    scaled = contract["intercept"] + sum(contract["weights"][f] * contract["points_by_feature"][f].get(str(row[f]), 0) for f in contract["weights"])
    assert abs((scaled - contract["intercept"] + contract["intercept_exact"] * contract["scale"]) / contract["scale"] - float(scores["logit"].iloc[0])) < 1e-9
    # And the real TypeScript scorer agrees (tsx available on this machine)
    import shutil
    if shutil.which("tsx"):
        ts = subprocess.run(["tsx", str(SCRIPTS / "tests" / "contract_check.ts"), str(out)], capture_output=True, text=True)
        assert ts.returncode == 0, ts.stdout + ts.stderr


def test_missing_boolean_is_its_own_bin_not_false(tmp_path: Path):
    df = synthetic(n=200)
    df["strong_signal"] = df["strong_signal"].astype(object)
    df.loc[df.index[:40], "strong_signal"] = np.nan  # failed collection, not observed absence
    src = tmp_path / "f.csv"; df.to_csv(src, index=False)
    out = tmp_path / "o"
    res = subprocess.run([sys.executable, str(SCRIPTS / "train_scorecard.py"), "--input", str(src), "--out-dir", str(out), "--mode", "lift"], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr[-1500:]
    specs = json.loads((out / "specs.json").read_text())
    bins = set(specs["model"]["features"]["strong_signal"]["points_map"])
    assert "nan" in bins and "True" in bins and "False" in bins, bins
    runner = ScorecardRunner.from_dir(str(out))
    a = runner.score(pd.DataFrame({**df.iloc[[0]].drop(columns=["domain", "status"]).to_dict("list"), "strong_signal": [np.nan]}))
    b = runner.score(pd.DataFrame({**df.iloc[[0]].drop(columns=["domain", "status"]).to_dict("list"), "strong_signal": [False]}))
    assert int(a["raw_points"].iloc[0]) != int(b["raw_points"].iloc[0]) or specs["model"]["features"]["strong_signal"]["points_map"]["nan"] == specs["model"]["features"]["strong_signal"]["points_map"]["False"]


def test_tiny_set_and_eligibility(tmp_path: Path):
    df = synthetic(n=24)
    df["status"] = ["won"] * 5 + ["lost"] * 15 + ["unlabeled"] * 4
    df["coverage__website"] = ["success"] * 20 + ["error", "error", "success", "success"]
    df["deal_labels"] = "won|lost"
    src = tmp_path / "f.csv"; df.to_csv(src, index=False); out = tmp_path / "o"
    base = [sys.executable, str(SCRIPTS / "train_scorecard.py"), "--input", str(src), "--out-dir", str(out), "--mode", "lift",
            "--coverage-cols", "coverage__website"]
    res = subprocess.run(base, capture_output=True, text=True)
    assert res.returncode != 0 and "deal_labels" in (res.stdout + res.stderr), "denylisted column must be refused"
    res = subprocess.run(base + ["--exclude-cols", "deal_labels"], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr[-1500:]
    scores = pd.read_csv(out / "scores.csv")
    bad = scores[scores["coverage__website"] == "error"] if "coverage__website" in scores else scores.iloc[20:22]
    assert (bad["status"] == "unscored").all() and (bad["miss_reason"] == "no_usable_evidence").all()
    assert scores["points"].isna().sum() == 2


def test_validation_split_rows_never_fit(tmp_path: Path):
    df = synthetic(n=200)
    df["split"] = ["validation"] * 50 + ["discovery"] * 150
    src = tmp_path / "f.csv"; df.to_csv(src, index=False); out = tmp_path / "o"
    res = subprocess.run([sys.executable, str(SCRIPTS / "train_scorecard.py"), "--input", str(src), "--out-dir", str(out), "--mode", "lift"], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr[-1500:]
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["rows_fit"] == 150 and meta["rows_excluded_split"] == 50
    assert len(json.loads((out / "reference.json").read_text())["scores"]) == 150
    scores = pd.read_csv(out / "scores.csv")
    assert (scores["row_role"].iloc[:50] == "validation").all() and scores["status"].iloc[:50].eq("scored").all()


def test_cli_refuses_propensity_on_small_data(tmp_path: Path):
    df = synthetic(n=60); src = tmp_path / "f.csv"; df.to_csv(src, index=False)
    res = subprocess.run([sys.executable, str(SCRIPTS / "train_scorecard.py"), "--input", str(src),
                          "--out-dir", str(tmp_path / "o"), "--mode", "propensity"], capture_output=True, text=True)
    assert res.returncode != 0 and "refused" in (res.stdout + res.stderr)


if __name__ == "__main__":
    import tempfile
    test_lift_mode_points_follow_prevalence_ratio()
    test_propensity_mode_fits_and_tiers()
    with tempfile.TemporaryDirectory() as d:
        test_cli_lift_end_to_end_and_artifact_replay(Path(d))
    for fn in (test_missing_boolean_is_its_own_bin_not_false, test_tiny_set_and_eligibility, test_validation_split_rows_never_fit, test_cli_refuses_propensity_on_small_data):
        with tempfile.TemporaryDirectory() as d:
            fn(Path(d))
    print("all scorecard tests passed")
