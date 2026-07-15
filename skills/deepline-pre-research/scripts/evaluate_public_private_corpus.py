#!/usr/bin/env python3
"""Run the shipped public/private last30days planner parity corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from query_design import build_query_plan, plan_to_dict


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "evals" / "last30days-public-private-corpus.json"
OUT_MD = ROOT / "evals" / "public-private-corpus-results.md"
OUT_JSON = ROOT / "evals" / "public-private-corpus-results.json"

DEEPLINE_PRIVATE_SOURCES = {"crm", "warehouse", "workflow", "support"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the Deepline pre-research query planner on the 20-case last30days corpus")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help="Corpus JSON path")
    parser.add_argument("--out-md", type=Path, default=OUT_MD, help="Markdown report path")
    parser.add_argument("--out-json", type=Path, default=OUT_JSON, help="JSON report path")
    return parser.parse_args()


def load_corpus(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def planned_sources(plan: dict[str, Any]) -> set[str]:
    sources: set[str] = set()
    for values in plan["enabled_sources"].values():
        sources.update(values)
    for variant in plan["variants"]:
        sources.add(variant["source"])
    return sources


def evaluate_case(case: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    topic = case["topic"].replace(" --agent", "").strip()
    explicit_sources = set(defaults.get("requiredBaseSources", [])) | set(case.get("mustIncludeSources", []))
    plan = build_query_plan(
        topic,
        depth=defaults.get("depth", "deep"),
        from_date=defaults.get("fromDate"),
        to_date=defaults.get("toDate"),
        explicit_sources=explicit_sources,
    )
    plan_data = plan_to_dict(plan)
    actual_sources = planned_sources(plan_data)
    expected_sources = set(case.get("mustIncludeSources", [])) | set(defaults.get("requiredBaseSources", []))
    expected_keys = set(case.get("mustIncludeExtractionKeys", [])) | set(defaults.get("requiredBaseExtractionKeys", []))
    actual_keys = set(plan_data["extraction_keys"])
    expected_routes = set(case.get("expectedQueryTypes", []))
    missing_sources = sorted(expected_sources - actual_sources)
    missing_keys = sorted(expected_keys - actual_keys)
    deepline_private_additions = sorted(actual_sources & DEEPLINE_PRIVATE_SOURCES)
    same_or_better = plan_data["query_type"] in expected_routes and not missing_sources and not missing_keys
    return {
        "id": case["id"],
        "topic": case["topic"],
        "kind": case["kind"],
        "expected_route": sorted(expected_routes),
        "actual_route": plan_data["query_type"],
        "last30days_sources": case.get("last30daysSources", []),
        "expected_sources": sorted(expected_sources),
        "actual_sources": sorted(actual_sources),
        "missing_sources": missing_sources,
        "expected_extraction_keys": sorted(expected_keys),
        "actual_extraction_keys": sorted(actual_keys),
        "missing_extraction_keys": missing_keys,
        "deepline_private_additions": deepline_private_additions,
        "same_or_better": same_or_better,
    }


def build_markdown(results: list[dict[str, Any]], corpus_path: Path) -> str:
    passed = sum(1 for result in results if result["same_or_better"])
    lines = [
        "# Deepline Pre-Research Public/Private Corpus Eval",
        "",
        f"Corpus: `{corpus_path}`",
        f"Result: {passed}/{len(results)} cases same_or_better",
        "",
        "| Case | Expected route | Actual route | Missing sources | Missing extraction keys | Deepline private additions | Result |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            "| {id} | {expected} | {actual} | {missing_sources} | {missing_keys} | {private} | {status} |".format(
                id=result["id"],
                expected=", ".join(result["expected_route"]),
                actual=result["actual_route"],
                missing_sources=", ".join(result["missing_sources"]) or "none",
                missing_keys=", ".join(result["missing_extraction_keys"]) or "none",
                private=", ".join(result["deepline_private_additions"]) or "none",
                status="same_or_better" if result["same_or_better"] else "gap",
            )
        )
    lines += [
        "",
        "## Notes",
        "",
        "- This standalone eval runs the skill-shipped query planner and corpus only; it does not call paid providers.",
        "- Public-source parity is checked from the accepted last30days corpus expectations.",
        "- Deepline private additions are expected on private/workflow prompts and are reported separately from public coverage.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    corpus = load_corpus(args.corpus)
    results = [evaluate_case(case, corpus["defaults"]) for case in corpus["cases"]]
    output = {
        "corpus": str(args.corpus),
        "total_cases": len(results),
        "same_or_better_cases": sum(1 for result in results if result["same_or_better"]),
        "all_same_or_better": all(result["same_or_better"] for result in results),
        "cases": results,
    }
    markdown = build_markdown(results, args.corpus)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown, encoding="utf-8")
    args.out_json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_md}")
    print(f"Wrote {args.out_json}")
    if not output["all_same_or_better"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
