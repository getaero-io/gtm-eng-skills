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
    template_identity = "  'search-experiment-template',"
    if template.count(template_identity) != 1:
        raise ValueError("Search experiment template has no unique Play identity marker.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        template.replace(template_identity, f"  '{slug}',"), encoding="utf-8"
    )


def scaffold(output_directory: Path, name: str) -> dict[str, object]:
    skill_root = Path(__file__).resolve().parent.parent
    slug = play_name(name)
    targets = [
        (
            skill_root / "plays" / "search-experiment.template.ts",
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
    existing = [destination for _, destination in targets if destination.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite " + ", ".join(str(path) for path in existing)
        )
    copy_play(targets[0][0], targets[0][1], slug)
    for source, destination in targets[1:]:
        copy_new(source, destination)
    return {
        "play": str(targets[0][1]),
        "helpers": [str(destination) for _, destination in targets[1:]],
        "next": [
            "Replace the scope rows and frozen claim contract.",
            "Use pre-research to write 5–10 source-mechanism cards, then implement the strongest 3–5 as ordinary strategy blocks.",
            "Describe each selected tool, then change only its literal call input and declared getter; do not guess raw response paths.",
            "Keep candidates separate from final accepted claims; acceptance failures remain experiment gaps and trigger dormant strategies.",
            f"deepline plays check {targets[0][1]}",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--name", default="search-experiment")
    args = parser.parse_args()
    try:
        result = scaffold(args.output_directory.resolve(), args.name)
    except (FileExistsError, ValueError) as error:
        json.dump({"ok": False, "error": str(error)}, sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 1
    json.dump({"ok": True, **result}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
