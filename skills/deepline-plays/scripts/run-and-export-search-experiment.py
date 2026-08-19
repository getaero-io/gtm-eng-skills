#!/usr/bin/env python3
"""Check, run, and export one search-experiment Play as a single durable step."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("play", type=Path)
    parser.add_argument("--input", default="{}", help="Play input JSON or @file.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dataset", help="Optional returned dataset path.")
    parser.add_argument("--minimum-experiments", type=int, default=1)
    parser.add_argument("--require-live-company-discovery", action="store_true")
    parser.add_argument(
        "--company-to-person",
        action="store_true",
        help="Require two experiments and an accepted-company-to-contact handoff.",
    )
    parser.add_argument("--deepline", default="deepline")
    args = parser.parse_args()
    if args.minimum_experiments < 1:
        parser.error("--minimum-experiments must be positive.")
    if args.company_to_person:
        if args.minimum_experiments not in (1, 2):
            parser.error(
                "--company-to-person owns its two-stage topology; omit --minimum-experiments or set it to 2."
            )
        args.minimum_experiments = 2
        args.require_live_company_discovery = True
    play = args.play.resolve()
    output = args.out.resolve()
    if not play.is_file():
        parser.error(f"Play does not exist: {play}")
    if output.exists():
        parser.error(f"Refusing to overwrite output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    skill_root = Path(__file__).resolve().parent.parent
    check_command = [
        sys.executable,
        str(skill_root / "scripts" / "check-search-experiment.py"),
        str(play),
        "--minimum-experiments",
        str(args.minimum_experiments),
        "--require-declared-getters",
    ]
    if args.require_live_company_discovery:
        check_command.append("--require-live-company-discovery")
    if args.company_to_person:
        check_command.append("--require-company-to-person-handoff")
    run(check_command)
    run([args.deepline, "plays", "check", str(play)])

    with tempfile.TemporaryDirectory(prefix="deepline-search-run-") as directory:
        run_id_file = Path(directory) / "run-id.json"
        run(
            [
                args.deepline,
                "plays",
                "run",
                "--file",
                str(play),
                "--input",
                args.input,
                "--run-id-file",
                str(run_id_file),
            ]
        )
        run_id = json.loads(run_id_file.read_text(encoding="utf-8")).get("runId")
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("Play run completed without a durable run id.")
        export_command = [args.deepline, "runs", "export", run_id]
        if args.dataset:
            export_command.extend(["--dataset", args.dataset])
        export_command.extend(["--out", str(output)])
        run(export_command)

    print(json.dumps({"ok": True, "runId": run_id, "output": str(output)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from error
