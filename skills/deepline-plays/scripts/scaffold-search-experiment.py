#!/usr/bin/env python3
"""Copy the one-file Deepline search-experiment authoring surface."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def play_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        raise ValueError("Play name must contain a letter or digit.")
    return normalized


def copy_new(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_play(source: Path, destination: Path, slug: str) -> None:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    template = source.read_text(encoding="utf-8")
    template_identity = "'search-experiment-template'"
    if template.count(template_identity) != 1:
        raise ValueError("Search experiment template has no unique Play identity marker.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        template.replace(template_identity, f"'{slug}'"), encoding="utf-8"
    )


def copy_strategy_map(source: Path, destination: Path, slug: str) -> None:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    template = source.read_text(encoding="utf-8")
    marker = "# Strategy map: <task>"
    if template.count(marker) != 1:
        raise ValueError("Strategy map template has no unique task marker.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        template.replace(marker, f"# Strategy map: {slug}"), encoding="utf-8"
    )


def scaffold(
    output_directory: Path, name: str, topology: str
) -> dict[str, object]:
    skill_root = Path(__file__).resolve().parent.parent
    slug = play_name(name)
    template_name = (
        "company-to-person-experiment.template.ts"
        if topology == "company-to-person"
        else "search-experiment.template.ts"
    )
    targets = [
        (
            skill_root / "plays" / template_name,
            output_directory / f"{slug}.play.ts",
        ),
        (
            skill_root / "plays" / "shared" / "research-experiment.ts",
            output_directory / "shared" / "research-experiment.ts",
        ),
        (
            skill_root / "plays" / "shared" / "grounded-extraction.ts",
            output_directory / "shared" / "grounded-extraction.ts",
        ),
        (
            skill_root / "plays" / "shared" / "search-experiment.ts",
            output_directory / "shared" / "search-experiment.ts",
        ),
        (
            skill_root / "plays" / "shared" / "search-strategy.ts",
            output_directory / "shared" / "search-strategy.ts",
        ),
    ]
    strategy_map = output_directory / "strategy-map.md"
    existing = [destination for _, destination in targets if destination.exists()]
    if strategy_map.exists():
        existing.append(strategy_map)
    if existing:
        raise FileExistsError(
            "Refusing to overwrite " + ", ".join(str(path) for path in existing)
        )
    copy_play(targets[0][0], targets[0][1], slug)
    for source, destination in targets[1:]:
        copy_new(source, destination)
    copy_strategy_map(skill_root / "templates" / "strategy-map.md", strategy_map, slug)
    run_command = (
        f"python3 {skill_root / 'scripts' / 'run-and-export-search-experiment.py'} "
        f"{targets[0][1]} --input '{{}}' --out ./search-results.csv"
    )
    if topology == "company-to-person":
        run_command += " --company-to-person"
    next_steps = [
        f"Start with {strategy_map}: read {skill_root / 'references' / 'strategy-pre-research.md'}, then write the source terrain and 6–12 candidate cards before editing route code. Each card needs a corpus, join, first probe, and distinct rescue path.",
        "Run the catalog preflight before binding a Deepline-tool route. If `deepline tools list` fails, record the exact error in strategy-map.md and stop with this scaffold unbound; do not replace CATALOG_REQUIRED with throwing stubs or write final rows.",
        "Replace rows and the required-claim contract. Omit targetRows unless the user explicitly set a stopping count.",
        "Run `deepline tools list`, list the relevant capability categories, and describe the 6–12 executable routes worth binding. Copy one returned named getter into every tool-backed program body.",
        "Use three materially different programs in the first wave and bind three or more dormant recovery programs. List every retained id in boundProgramIds; never replace this Play with a shell loop or manual CSV.",
        "The helper calls the first wave in parallel, then opens dormant routes only for unresolved gaps. Candidates and acceptance failures stay visible as gaps.",
        "The generated Play persists a route scorecard beside final rows. Treat pilot plus holdout as the first eval; for repeated work, freeze normal, sparse, and likely-miss cases in strategy-map.md before comparing the same source concept again.",
        "For paid or variable-cost routes, set maximumDeeplineCredits and maximumDeeplineCreditsPerAttempt before running; unknown cost is never zero.",
    ]
    if topology == "company-to-person":
        next_steps.append(
            "This file already has the only valid handoff: companyExperiment.finalResults becomes contactRows. Bind company routes first, then contact routes. Do not make a separate contact-lookup Play or hand-pick a company cohort."
        )
    else:
        next_steps.append(
            "For company → contact work, invoke this scaffold with --topology company-to-person. Its accepted company finalResults are the only contact input."
        )
    next_steps.extend(
        [
            run_command,
            "Run that command before writing final rows. Its {ok: true, runId, output} response is the only completion receipt: it gates the structural check, Play check, completed run, and run-derived CSV. Inspect its run ID and report comparison, exploitation, recovery, and Deepline cost receipts.",
        ]
    )
    return {
        "play": str(targets[0][1]),
        "strategy_map": str(strategy_map),
        "helpers": [str(destination) for _, destination in targets[1:]],
        "next": next_steps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--name", default="search-experiment")
    parser.add_argument(
        "--topology",
        choices=("single-stage", "company-to-person"),
        default="single-stage",
        help="Use company-to-person for open-world company discovery followed by contact discovery.",
    )
    args = parser.parse_args()
    try:
        result = scaffold(args.output_directory.resolve(), args.name, args.topology)
    except (FileExistsError, ValueError) as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 1
    json.dump({"ok": True, **result}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
