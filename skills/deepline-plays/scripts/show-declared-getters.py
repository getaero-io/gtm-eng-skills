#!/usr/bin/env python3
"""Print the compact getter contract from `deepline tools describe --json`."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def record(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def entries(value: object) -> list[dict[str, str]]:
    if isinstance(value, dict):
        source = [
            {"name": name, **record(item)} for name, item in value.items()
        ]
    elif isinstance(value, list):
        source = value
    else:
        return []
    result: list[dict[str, str]] = []
    for item in source:
        item_record = record(item)
        name = item_record.get("name")
        expression = item_record.get("expression")
        if isinstance(name, str) and isinstance(expression, str):
            result.append({"name": name, "expression": expression})
    return result


def getter_contract(describe: dict[str, Any]) -> dict[str, Any]:
    # `getters` is the concise current CLI contract. usageGuidance keeps this
    # helper compatible with stored/older describe output.
    getters = record(describe.get("getters"))
    if not getters:
        guidance = record(describe.get("usageGuidance"))
        execution = record(
            guidance.get("toolExecutionResult")
            or guidance.get("tool_execution_result")
        )
        getters = {
            "extractedLists": execution.get("extractedLists")
            or execution.get("extracted_lists"),
            "extractedValues": execution.get("extractedValues")
            or execution.get("extracted_values"),
        }
    return {
        "toolId": describe.get("toolId"),
        "lists": entries(getters.get("extractedLists")),
        "values": entries(getters.get("extractedValues")),
        "starterScript": record(describe.get("starterScript")).get("sourceCode"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "describe_json",
        type=argparse.FileType("r", encoding="utf-8"),
        nargs="?",
        help="Optional saved output from `deepline tools describe --json`; stdin by default.",
    )
    args = parser.parse_args()
    try:
        describe = json.load(args.describe_json or sys.stdin)
    except json.JSONDecodeError as error:
        print(json.dumps({"ok": False, "error": f"Invalid describe JSON: {error}"}))
        return 2
    if not isinstance(describe, dict):
        print(json.dumps({"ok": False, "error": "Describe output must be a JSON object."}))
        return 2
    contract = getter_contract(describe)
    if not contract["lists"] and not contract["values"]:
        print(
            json.dumps(
                {
                    "ok": False,
                    "toolId": contract["toolId"],
                    "error": "This tool declares no Deepline getters. Choose a route with a getter, or bind an explicit artifact seam before using raw output.",
                },
                indent=2,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                **contract,
                "playExpressions": {
                    "lists": [
                        {
                            **entry,
                            "expression": entry["expression"].replace(
                                "toolExecutionResult", "response", 1
                            ),
                        }
                        for entry in contract["lists"]
                    ],
                    "values": [
                        {
                            **entry,
                            "expression": entry["expression"].replace(
                                "toolExecutionResult", "response", 1
                            ),
                        }
                        for entry in contract["values"]
                    ],
                },
                "authoringRule": "Copy a listed playExpression into the same named response that made the call. For a list, await its .get() handle and project provider fields through list.keys; do not cast toolResponse.raw.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
