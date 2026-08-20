#!/usr/bin/env python3
"""Copy the one-file Deepline search-experiment authoring surface.

`--input-csv` also writes a small stratified `fixture.csv`. Iterate route code
against it, not the full cohort: on a 43-row job, ten full-cohort runs consumed
35 of 45 minutes and every bug they found reproduced in five rows or fewer.
"""

from __future__ import annotations

import argparse
import csv
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


def _filled_cell_count(row: dict[str, str]) -> int:
    return sum(1 for value in row.values() if (value or "").strip())


def _collision_column(rows: list[dict[str, str]], columns: list[str]) -> str | None:
    """The text column most likely to make two different entities look alike.

    A column every row shares (`state`) proves nothing, and a unique-per-row
    column (`npi`) can never collide. The useful one is in between: many
    values, some repeated.
    """
    best: tuple[int, int, str] | None = None
    for column in columns:
        values = [
            (row.get(column) or "").strip().lower()
            for row in rows
            if (row.get(column) or "").strip()
        ]
        if len(values) < 2:
            continue
        if all(value.replace(".", "").replace("-", "").isdigit() for value in values):
            continue
        counts: dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        distinct = len(counts)
        if distinct < 2 or distinct == len(values):
            continue
        # Many small duplicate groups (surnames) beat one huge group (state).
        groups = sum(1 for count in counts.values() if count > 1)
        candidate = (groups, distinct, column)
        if best is None or candidate > best:
            best = candidate
    return best[2] if best else None


def stratify(rows: list[dict[str, str]], size: int) -> list[tuple[str, int]]:
    """Pick row indexes spanning the strata that actually break route code.

    Sparse rows, collision-prone rows, and the ordinary middle fail for
    different reasons. Sampling the head of the file finds only the third.
    Returns (stratum, index) pairs so the choice is inspectable, not magic.
    """
    if not rows:
        return []
    columns = list(rows[0].keys())
    size = max(1, min(size, len(rows)))
    picked: list[tuple[str, int]] = []
    used: set[int] = set()

    def take(stratum: str, index: int | None) -> None:
        if index is None or index in used or len(picked) >= size:
            return
        used.add(index)
        picked.append((stratum, index))

    filled = sorted(range(len(rows)), key=lambda index: _filled_cell_count(rows[index]))
    take("sparse", filled[0])
    take("complete", filled[-1])

    collision_column = _collision_column(rows, columns)
    if collision_column:
        tokens: dict[str, list[int]] = {}
        for index, row in enumerate(rows):
            value = (row.get(collision_column) or "").strip().lower()
            if value:
                tokens.setdefault(value, []).append(index)
        collisions = [indexes for indexes in tokens.values() if len(indexes) > 1]
        for indexes in sorted(collisions, key=len, reverse=True):
            take("collision-prone", indexes[0])
            break

    remaining = size - len(picked)
    if remaining > 0:
        step = max(1, len(rows) // (remaining + 1))
        for position in range(1, remaining + 1):
            take("spread", min(position * step, len(rows) - 1))
    for index in range(len(rows)):
        take("spread", index)
    return picked[:size]


def write_fixture(
    input_csv: Path, destination: Path, size: int
) -> dict[str, object]:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    with input_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = [row for row in reader]
        fieldnames = reader.fieldnames or []
    if not rows:
        raise ValueError(f"{input_csv} has no data rows to stratify.")
    picked = stratify(rows, size)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        # csv defaults to CRLF; the fixture must read like the input it samples.
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for _, index in picked:
            writer.writerow(rows[index])
    return {
        "path": str(destination),
        "rows": len(picked),
        "source_rows": len(rows),
        "strata": [
            {"stratum": stratum, "source_row": index + 2}
            for stratum, index in picked
        ],
    }


def scaffold(
    output_directory: Path,
    name: str,
    topology: str,
    input_csv: Path | None = None,
    fixture_size: int = 5,
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
    fixture: dict[str, object] | None = None
    if input_csv is not None:
        fixture = write_fixture(
            input_csv, output_directory / "fixture.csv", fixture_size
        )
    run_command = (
        f"python3 {skill_root / 'scripts' / 'run-and-export-search-experiment.py'} "
        f"{targets[0][1]} --input '{{}}' --out ./search-results.csv"
    )
    if topology == "company-to-person":
        run_command += " --company-to-person"
    # This list is the authoring contract. It is printed at the moment the seams
    # are about to be edited, which is why the mechanics live here rather than in
    # SKILL.md, and why the scaffold test pins its contents.
    next_steps = [
        f"Start with {strategy_map}: write the source terrain and 6–12 candidate cards before editing route code. A card names its corpus, join key, first probe, acceptance proof, and the distinct rescue path that makes it worth keeping when another route misses. Cards differ by corpus, join key, query shape, evidence source, or workflow stage — not by vendor.",
        "Run the catalog preflight before binding a Deepline-tool route. If `deepline tools list` fails, record the exact error in strategy-map.md and stop with this scaffold unbound; do not replace CATALOG_REQUIRED with throwing stubs or write final rows.",
        "Edit four seams only: (1) rows and the required-claim contract; (2) the incumbent's mechanism, declared getter, evidence binding, and canonical entity key; (3) one heterogeneous challenger against the same stage contract; (4) the final row mapping. That mapping is the CSV contract — use the user's field names exactly, since renamed headers break downstream imports and hide coverage checks. Omit targetRows unless the user set a stopping count.",
        "Run `deepline tools list`, list the relevant capability categories, and describe the 6–12 executable routes worth binding. Copy one returned named getter into every tool-backed program body.",
        "Declare each program's catalog tool ids in `tools: [...]`. That is what turns the route scorecard's cost column from a catalog upper bound into observed credits after the run. `tools: []` asserts a route calls no Deepline tool; leaving it unset means its spend is unknown, not free.",
        "Add a `coherenceChecks` entry for every pair of required claims that must describe the same entity. Each claim validates alone, so a row can pass every `accept` while mixing two entities — one run reported 43/43 verified this way and was mostly wrong. `check({ verified })` returns null to accept or a short reason to reject.",
        "Use three materially different programs in the first wave and bind three or more dormant recovery programs. List every retained id in boundProgramIds; never replace this Play with a shell loop or manual CSV. Competing routes never share one Promise.all or dataset column — the helper needs separate outcomes to rank.",
        "The helper calls the first wave in parallel, then opens dormant routes only for unresolved gaps. Candidates and acceptance failures stay visible as gaps.",
        "`boundClaim` (via bindResearchEvidenceToSource) requires the literal returned value to occur in the source receipt. A finder plus a verifier is a candidate seam plus an acceptance seam; a validator rejection reopens only that row and claim.",
        "Pilot on one schema-probe row, then 3–5 stratified rows: easy, normal, sparse or niche, and collision-prone. Count only terminal outputs that pass the task's gates — ten candidates for the wrong company are zero covered rows.",
        "The generated Play persists a route scorecard beside final rows. Treat pilot plus holdout as the first eval; for repeated work, freeze normal, sparse, and likely-miss cases in strategy-map.md before comparing the same source concept again.",
        "For paid or variable-cost routes, set maximumDeeplineCredits and maximumDeeplineCreditsPerAttempt before running; unknown cost is never zero. The ceiling is admission control — it stops the next wave and is not a record of spend.",
    ]
    if topology == "company-to-person":
        next_steps.append(
            "This file already has the only valid handoff: companyExperiment.finalResults becomes contactRows. Bind company routes first, then contact routes. Do not make a separate contact-lookup Play or hand-pick a company cohort."
        )
    else:
        next_steps.append(
            "For company → contact work, invoke this scaffold with --topology company-to-person. Its accepted company finalResults are the only contact input."
        )
    if fixture is not None:
        next_steps.insert(
            0,
            f"Iterate against {fixture['path']} ({fixture['rows']} stratified rows of "
            f"{fixture['source_rows']}), not the full cohort. Point rows at the fixture "
            "until the route code is correct, then switch to the full input for one "
            "scored run. Debugging on the full cohort is the single largest time sink "
            "in this workflow.",
        )
    else:
        next_steps.insert(
            0,
            "Rerun this scaffold with --input-csv <file> to get a stratified fixture.csv, "
            "or cut one by hand before your second run. Iterating route code on the full "
            "cohort is the single largest time sink in this workflow.",
        )
    next_steps.extend(
        [
            run_command,
            "Run that command before writing final rows. Its {ok: true, runId, output} response is the only completion receipt: it gates the structural check, Play check, completed run, and run-derived CSV. Inspect its run ID and report comparison, exploitation, recovery, and Deepline cost receipts.",
            "That command also prints a COST RECEIPT block built from the run's billing breakdown. Pass it through verbatim; do not recompute credits in prose and never report total credits divided by successes.",
        ]
    )
    result: dict[str, object] = {
        "play": str(targets[0][1]),
        "strategy_map": str(strategy_map),
        "helpers": [str(destination) for _, destination in targets[1:]],
        "next": next_steps,
    }
    if fixture is not None:
        result["fixture"] = fixture
    return result


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
    parser.add_argument(
        "--input-csv",
        type=Path,
        help="Supplied rows. Writes a stratified fixture.csv to iterate against.",
    )
    parser.add_argument(
        "--fixture",
        type=int,
        default=5,
        help="Fixture row count (default 5). Requires --input-csv.",
    )
    args = parser.parse_args()
    if args.fixture < 1:
        parser.error("--fixture must be positive.")
    if args.input_csv is not None and not args.input_csv.is_file():
        parser.error(f"--input-csv does not exist: {args.input_csv}")
    try:
        result = scaffold(
            args.output_directory.resolve(),
            args.name,
            args.topology,
            args.input_csv.resolve() if args.input_csv else None,
            args.fixture,
        )
    except (FileExistsError, ValueError) as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 1
    json.dump({"ok": True, **result}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
