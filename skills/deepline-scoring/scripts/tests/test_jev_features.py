"""Known-answer check for jev_features.py against a stub `deepline` CLI (no paid calls, synthetic rows).

Run:  python3 scripts/tests/test_jev_features.py   (or via pytest)
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]

STUB = """#!/usr/bin/env python3
import json, sys
payload = json.loads(sys.argv[sys.argv.index("--input") + 1])
assert payload["model"] == "typesafe-ai/jev" and "website_text" in payload["state"]
open(sys.argv[0] + ".calls", "a").write(payload["state"]["domain"] + "\\n")
print(json.dumps({"billing": {"credits_charged": 0.001}, "toolResponse": {"rawV2": {"extracted_json": {
  "sells_b2b": {"type": "boolean", "probability": 0.96},
  "billing": {"type": "choice", "choice": "subscription", "probabilities": {"subscription": 0.9, "usage": 0.1}},
  "complexity": {"type": "score", "score": 1.7, "probabilities": {"0": 0.1, "1": 0.1, "2": 0.8}}}}}}))
"""

QUESTIONS = {
    "sells_b2b": {"type": "boolean", "instructions": "Sells mainly to businesses?"},
    "billing": {"type": "choice", "instructions": "How it charges", "criteria": {"subscription": "plan", "usage": "metered"}},
    "complexity": {"type": "score", "instructions": "Operating complexity", "criteria": ["low", "medium", "high"]},
}


def run(tmp: Path, *extra: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": f"{tmp}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run([sys.executable, str(SCRIPTS / "jev_features.py"), "--input", str(tmp / "in.csv"),
                           "--questions", str(tmp / "q.json"), "--output", str(tmp / "out.csv"), *extra],
                          capture_output=True, text=True, env=env)


def test_jev_features_end_to_end(tmp_path: Path | None = None) -> None:
    tmp = tmp_path or Path(tempfile.mkdtemp())
    stub = tmp / "deepline"; stub.write_text(STUB); stub.chmod(0o755)
    (tmp / "q.json").write_text(json.dumps(QUESTIONS))
    site = json.dumps({"pages": [{"url": "https://a.example", "markdown": "Payroll for employers. $8 per seat."}]})
    with open(tmp / "in.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["domain", "status", "website"]); w.writeheader()
        w.writerows([{"domain": "a.example", "status": "won", "website": site},
                     {"domain": "a.example", "status": "won", "website": site},   # duplicate shares one call
                     {"domain": "b.example", "status": "lost", "website": ""}])    # no text -> unknown, no call

    res = run(tmp)
    assert res.returncode == 0, res.stderr
    rows = list(csv.DictReader(open(tmp / "out.csv")))
    assert rows[0]["jev__sells_b2b"] == "0.96" and rows[0]["jev__billing"] == "subscription" and rows[0]["jev__complexity"] == "1.7"
    assert rows[0]["coverage__jev"] == rows[1]["coverage__jev"] == "success"
    assert rows[2]["coverage__jev"] == "missing" and rows[2]["jev__sells_b2b"] == ""
    assert (tmp / "deepline.calls").read_text().split() == ["a.example"]

    digest = json.loads((tmp / "out.csv.manifest.json").read_text())["questions_sha256"]
    assert run(tmp, "--questions-sha256", digest).returncode == 0
    assert (tmp / "deepline.calls").read_text().split() == ["a.example"], "rerun must reuse the receipt"
    assert run(tmp, "--questions-sha256", "0" * 64).returncode != 0, "a changed question set must fail"


if __name__ == "__main__":
    test_jev_features_end_to_end()
    print("ok")
