#!/usr/bin/env python3
"""Check, run, export, and price one search-experiment Play as a single step.

The output gate: its `{ok: true, ...}` is the only completion receipt. Exports
two datasets — the results CSV the user asked for, and the route scorecard that
says which route earned it at what price — then prints a COST RECEIPT built from
the run's billing breakdown. Pass that block through verbatim.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# `runs export` retries internally, but a large dataset can stay unmaterialized
# past that window and report RUN_EXPORT_NOT_READY for a run that is fine. A
# failed export after a successful run is the worst possible outcome: the rows
# are already paid for.
NOT_READY_MARKERS = ("was not ready to export", "RUN_EXPORT_NOT_READY")
EXPORT_RETRY_DELAYS_SECONDS = (5, 10, 20, 30, 60)
# Above this many exported rows, a run with no fixture beside the Play is very
# likely a debug loop over the full cohort. Measured on a 43-row job: ten
# full-cohort runs consumed 35 of 45 minutes and every defect they found
# reproduced in five rows or fewer. The scaffold offers `--input-csv` for this,
# and a behaviour eval found it is reached for about a third of the time, so the
# reminder fires here instead — at the moment the cost is visible.
FIXTURE_REMINDER_ROW_THRESHOLD = 20


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def export_dataset(
    deepline: str,
    run_id: str,
    dataset: str | None,
    output: Path,
    required: bool,
) -> bool:
    """Export one dataset, waiting out a not-yet-materialized backing table."""
    command = [deepline, "runs", "export", run_id]
    if dataset:
        command.extend(["--dataset", dataset])
    command.extend(["--out", str(output)])
    last: subprocess.CompletedProcess[str] | None = None
    for attempt, delay in enumerate((0, *EXPORT_RETRY_DELAYS_SECONDS)):
        if delay:
            time.sleep(delay)
        last = subprocess.run(command, capture_output=True, text=True)
        if last.returncode == 0:
            sys.stdout.write(last.stdout)
            return True
        combined = f"{last.stdout}\n{last.stderr}"
        if not any(marker in combined for marker in NOT_READY_MARKERS):
            break
        sys.stderr.write(
            f"Dataset {dataset or 'default'} not materialized yet "
            f"(attempt {attempt + 1}); waiting.\n"
        )
    assert last is not None
    if required:
        sys.stderr.write(last.stdout)
        sys.stderr.write(last.stderr)
        raise subprocess.CalledProcessError(last.returncode, command)
    sys.stderr.write(
        f"Optional dataset '{dataset}' did not export; the cost receipt will "
        f"fall back to per-operation totals only.\n{last.stderr}"
    )
    return False


def fixture_reminder_for(play: Path, exported: Path) -> str | None:
    """Warn when a full-cohort run happened with no fixture beside the Play.

    Fires after the export because that is where the row count is known, and
    because the next thing the author does is edit route code and run again.
    """
    if (play.parent / "fixture.csv").is_file():
        return None
    try:
        with exported.open(encoding="utf-8") as handle:
            rows = max(0, sum(1 for _ in handle) - 1)
    except OSError:
        return None
    if rows <= FIXTURE_REMINDER_ROW_THRESHOLD:
        return None
    return (
        f"FIXTURE REMINDER — this run exported {rows} rows and there is no "
        f"fixture.csv beside {play.name}.\n"
        "  Full-cohort runs score; they do not debug. Before the next edit, cut a\n"
        "  stratified fixture and point `rows` at it:\n"
        f"    python3 <skill-root>/scripts/scaffold-search-experiment.py <new-dir> "
        f"--name <slug> --input-csv <rows.csv>\n"
        "  or copy 5 rows spanning sparse, collision-prone, and complete cases into\n"
        f"    {play.parent / 'fixture.csv'}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("play", type=Path)
    parser.add_argument("--input", default="{}", help="Play input JSON or @file.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--dataset",
        help="Returned results dataset path. Defaults to the scaffold's.",
    )
    parser.add_argument(
        "--scorecard-dataset",
        help="Returned route-scorecard dataset path. Defaults to the scaffold's.",
    )
    parser.add_argument(
        "--no-scorecard",
        action="store_true",
        help="Skip the scorecard export and its per-route cost join.",
    )
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
    # The scaffolded Plays always return more than one dataset, so an export
    # with no --dataset is ambiguous and fails on the skill's own output.
    results_dataset = args.dataset or "result.results"
    scorecard_dataset = args.scorecard_dataset or (
        "result.contactScorecard" if args.company_to_person else "result.scorecard"
    )
    play = args.play.resolve()
    output = args.out.resolve()
    scorecard_output = output.with_name(f"{output.stem}.route-scorecard.csv")
    if not play.is_file():
        parser.error(f"Play does not exist: {play}")
    for path in (output, scorecard_output):
        if path.exists():
            parser.error(f"Refusing to overwrite output: {path}")
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
        export_dataset(args.deepline, run_id, results_dataset, output, required=True)
        scorecard_exported = not args.no_scorecard and export_dataset(
            args.deepline,
            run_id,
            scorecard_dataset,
            scorecard_output,
            required=False,
        )

    receipt_command = [
        sys.executable,
        str(skill_root / "scripts" / "cost-receipt.py"),
        run_id,
        "--deepline",
        args.deepline,
    ]
    if scorecard_exported:
        receipt_command.extend(["--scorecard", str(scorecard_output)])
    receipt = subprocess.run(receipt_command, capture_output=True, text=True)
    if receipt.returncode == 0:
        print(receipt.stdout.rstrip())
    else:
        # A missing receipt is reported, never silently dropped: a run whose
        # cost cannot be read is a run whose cost must not be guessed.
        print(
            f"COST RECEIPT — run {run_id}\n"
            f"  unavailable: {receipt.stderr.strip()}\n"
            "  Report cost as unknown. Do not substitute a wallet delta or a "
            "catalog estimate for observed spend."
        )

    fixture_reminder = fixture_reminder_for(play, output)
    if fixture_reminder:
        print(fixture_reminder)

    print(
        json.dumps(
            {
                "ok": True,
                "runId": run_id,
                "output": str(output),
                "scorecard": str(scorecard_output) if scorecard_exported else None,
                "fixtureReminder": bool(fixture_reminder),
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from error
