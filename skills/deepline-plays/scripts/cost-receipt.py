#!/usr/bin/env python3
"""Join a run's billing breakdown onto its route scorecard and print one block.

The scorecard can only carry credits an attempt received a receipt for, and no
tool call does, so its cost column is empty while `runs get --full --json` has
the per-operation numbers. On one 43-row run that hid `hunter_domain_search` at
3.95 credits/call producing zero emails for ten rounds.

Pass the block through verbatim. Recomputing it in prose is how "1.51 credits
per email" gets reported for a route whose marginal cost is 0.21.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class CostReceiptError(RuntimeError):
    """A receipt could not be built from the inputs given."""


def load_run_json(run_id: str, deepline: str) -> dict[str, Any]:
    completed = subprocess.run(
        [deepline, "runs", "get", run_id, "--full", "--json"],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise CostReceiptError(
            f"`{deepline} runs get {run_id} --full --json` failed: "
            f"{completed.stderr.strip() or completed.returncode}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise CostReceiptError(
            f"`runs get --full --json` did not return JSON: {error}"
        ) from error


def find_billing(payload: Any) -> dict[str, Any]:
    """Locate the run billing object without guessing one envelope shape."""
    if isinstance(payload, dict):
        billing = payload.get("billing")
        if isinstance(billing, dict) and "totalCredits" in billing:
            return billing
        for key in ("data", "run", "status", "result"):
            nested = payload.get(key)
            if isinstance(nested, (dict, list)):
                try:
                    return find_billing(nested)
                except CostReceiptError:
                    continue
    raise CostReceiptError(
        "No run billing object was present. `runs get --full --json` returns it "
        "only for a settled run; retry once the run has finished settling."
    )


def operation_rows(billing: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten billing.breakdown.providers[].operations[] into sortable rows."""
    breakdown = billing.get("breakdown")
    if not isinstance(breakdown, dict):
        return []
    rows: list[dict[str, Any]] = []
    for provider in breakdown.get("providers") or []:
        if not isinstance(provider, dict):
            continue
        for operation in provider.get("operations") or []:
            if not isinstance(operation, dict):
                continue
            calls = int(operation.get("totalCalls") or 0)
            credits = float(operation.get("totalCredits") or 0.0)
            rows.append(
                {
                    "provider": str(provider.get("provider") or "unknown"),
                    "operation": str(operation.get("operation") or "unknown"),
                    "calls": calls,
                    "credits": credits,
                    "credits_per_call": credits / calls if calls else None,
                }
            )
    runtime = breakdown.get("runtime")
    if isinstance(runtime, dict) and int(runtime.get("totalCalls") or 0):
        calls = int(runtime.get("totalCalls") or 0)
        credits = float(runtime.get("totalCredits") or 0.0)
        rows.append(
            {
                "provider": "compute",
                "operation": "runtime",
                "calls": calls,
                "credits": credits,
                "credits_per_call": credits / calls if calls else None,
            }
        )
    rows.sort(key=lambda row: (-row["credits"], row["operation"]))
    return rows


def read_scorecard(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise CostReceiptError(f"Route scorecard {path} has no rows.")
    if "program_id" not in rows[0]:
        raise CostReceiptError(
            f"{path} is not a route scorecard export (no program_id column). "
            "Export the scorecard dataset, not the results dataset."
        )
    return rows


def to_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def join_routes(
    scorecard: list[dict[str, str]],
    operations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attribute observed operation credits to the routes that declared them."""
    by_operation = {row["operation"]: row for row in operations}
    # '' means the program declared no `tools`, so its spend is unknown.
    # 'none' means the author asserted it calls no Deepline tool: zero is a fact.
    declared: dict[str, list[str] | None] = {}
    for row in scorecard:
        raw = (row.get("tool_ids") or "").strip()
        if not raw:
            declared[row["program_id"]] = None
        elif raw == "none":
            declared[row["program_id"]] = []
        else:
            declared[row["program_id"]] = [
                tool.strip() for tool in raw.split("|") if tool.strip()
            ]
    # A tool declared by several routes splits its credits by attempted calls,
    # so a shared search tool cannot be billed twice to look expensive.
    claimants: dict[str, list[str]] = {}
    for program_id, tool_ids in declared.items():
        for tool_id in tool_ids or []:
            claimants.setdefault(tool_id, []).append(program_id)
    attempted_by_program = {
        row["program_id"]: to_int(row.get("total_calls")) for row in scorecard
    }
    joined: list[dict[str, Any]] = []
    for row in scorecard:
        program_id = row["program_id"]
        credits = 0.0
        billed_calls = 0.0
        unattributed = declared[program_id] is None and to_int(
            row.get("total_calls")
        ) > 0
        for tool_id in declared[program_id] or []:
            operation = by_operation.get(tool_id)
            if operation is None:
                continue
            sharers = claimants.get(tool_id, [program_id])
            if len(sharers) == 1:
                share = 1.0
            else:
                total_attempted = sum(
                    attempted_by_program.get(other, 0) for other in sharers
                )
                share = (
                    attempted_by_program.get(program_id, 0) / total_attempted
                    if total_attempted
                    else 1.0 / len(sharers)
                )
            credits += operation["credits"] * share
            billed_calls += operation["calls"] * share
        complete = to_int(row.get("complete_results"))
        joined.append(
            {
                "program_id": program_id,
                "reachability": row.get("reachability") or "unknown",
                "attempts": to_int(row.get("attempts")),
                "attempted_calls": to_int(row.get("total_calls")),
                "billed_calls": round(billed_calls, 2),
                "observed_credits": None if unattributed else round(credits, 4),
                "complete_results": complete,
                "credits_per_complete_result": (
                    None
                    if unattributed or not complete
                    else round(credits / complete, 4)
                ),
                "unattributed": unattributed,
                "billable": bool(declared[program_id]),
            }
        )
    joined.sort(
        key=lambda row: (
            0 if row["observed_credits"] is None else 1,
            -(row["observed_credits"] or 0),
            row["program_id"],
        )
    )
    return joined


def format_block(
    run_id: str,
    billing: dict[str, Any],
    operations: list[dict[str, Any]],
    routes: list[dict[str, Any]] | None,
) -> str:
    total_credits = float(billing.get("totalCredits") or 0.0)
    billed_calls = int(billing.get("totalCalls") or 0)
    rollup = billing.get("rollup")
    lines = [f"COST RECEIPT — run {run_id}"]
    if isinstance(rollup, dict) and float(rollup.get("childCredits") or 0) > 0:
        lines.append(
            f"  observed: {round(float(rollup.get('totalCreditsRollup') or 0), 4)} credits "
            f"({round(float(rollup.get('ownCredits') or 0), 4)} this run + "
            f"{round(float(rollup.get('childCredits') or 0), 4)} across "
            f"{int(rollup.get('descendantRunCount') or 0)} child run(s))"
        )
        if not rollup.get("rollupComplete", True):
            lines.append(
                "  WARNING: child billing did not fully resolve; the total above is a floor."
            )
    else:
        lines.append(
            f"  observed: {round(total_credits, 4)} credits over {billed_calls} billed call(s)"
        )

    lines.append("")
    lines.append("  per operation (billed calls only)")
    if not operations:
        lines.append("    none — this run billed nothing")
    else:
        lines.append(
            f"    {'operation':<38}{'calls':>7}{'credits':>12}{'per call':>12}"
        )
        for row in operations:
            per_call = (
                f"{row['credits_per_call']:.4f}"
                if row["credits_per_call"] is not None
                else "n/a"
            )
            lines.append(
                f"    {row['operation'][:37]:<38}{row['calls']:>7}"
                f"{row['credits']:>12.4f}{per_call:>12}"
            )

    if routes is not None:
        lines.append("")
        lines.append("  per route (billing operations joined on declared tool ids)")
        lines.append(
            f"    {'program_id':<28}{'reach':>13}{'calls':>7}{'credits':>10}"
            f"{'complete':>10}{'cr/complete':>13}"
        )
        for row in routes:
            per_complete = (
                f"{row['credits_per_complete_result']:.4f}"
                if row["credits_per_complete_result"] is not None
                else "—"
            )
            credits = (
                "unknown"
                if row["observed_credits"] is None
                else f"{row['observed_credits']:.4f}"
            )
            lines.append(
                f"    {row['program_id'][:27]:<28}{row['reachability']:>13}"
                f"{row['attempted_calls']:>7}{credits:>10}"
                f"{row['complete_results']:>10}{per_complete:>13}"
            )
        # Only tool-backed routes can produce a billing fact, so a ctx.fetch or
        # local-code route must not inflate the cached-call delta.
        attempted_calls = sum(
            row["attempted_calls"] for row in routes if row["billable"]
        )
        if attempted_calls > billed_calls:
            lines.append("")
            lines.append(
                f"    {attempted_calls} tool call(s) attempted, {billed_calls} billed — "
                f"{attempted_calls - billed_calls} served from durable receipts and "
                "cost nothing. A rerun of the same inputs will be cheaper than a "
                "first run; quote the marginal rate below, not this run's total."
            )
        cut = [
            row
            for row in routes
            if (row["observed_credits"] or 0) > 0 and row["complete_results"] == 0
        ]
        if cut:
            lines.append("")
            for row in cut:
                lines.append(
                    f"    CUT CANDIDATE: {row['program_id']} spent "
                    f"{row['observed_credits']:.4f} credits over "
                    f"{row['attempted_calls']} call(s) and completed 0 row(s)."
                )
        never = [row for row in routes if row["reachability"] == "never_reached"]
        if never:
            lines.append("")
            lines.append(
                "    NEVER REACHED: "
                + ", ".join(row["program_id"] for row in never)
                + " — never invoked, so their zero results are not a coverage ceiling."
            )
        unattributed = [row for row in routes if row["unattributed"]]
        if unattributed:
            lines.append("")
            lines.append(
                "    UNATTRIBUTED: "
                + ", ".join(row["program_id"] for row in unattributed)
                + " — made calls but declared no `tools`, so their credits stay in "
                "the per-operation table only. Add `tools: [...]` to the program."
            )
        earners = [
            row for row in routes if row["credits_per_complete_result"] is not None
        ]
        lines.append("")
        lines.append("  marginal cost")
        paid = [
            row for row in earners if row["credits_per_complete_result"] > 0
        ]
        if paid:
            best = min(paid, key=lambda row: row["credits_per_complete_result"])
            lines.append(
                f"    cheapest paid completing route: {best['program_id']} at "
                f"{best['credits_per_complete_result']:.4f} credits per complete row"
            )
        elif earners:
            lines.append(
                "    every completing route was free; the paid stages completed nothing"
            )
        free = [
            row
            for row in routes
            if row["observed_credits"] == 0
            and not row["unattributed"]
            and row["attempted_calls"] > 0
        ]
        if free:
            lines.append(
                "    free stages: " + ", ".join(row["program_id"] for row in free)
            )
        lines.append(
            "    Report this marginal rate, not total credits ÷ successes. The "
            "average is inflated by every route you would now cut."
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument(
        "--scorecard",
        type=Path,
        help="Exported route-scorecard CSV, for the per-route join.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON as well.")
    parser.add_argument("--deepline", default="deepline")
    parser.add_argument(
        "--run-json",
        type=Path,
        help="Read a saved `runs get --full --json` payload instead of calling the CLI.",
    )
    args = parser.parse_args()

    payload = (
        json.loads(args.run_json.read_text(encoding="utf-8"))
        if args.run_json
        else load_run_json(args.run_id, args.deepline)
    )
    billing = find_billing(payload)
    operations = operation_rows(billing)
    routes = (
        join_routes(read_scorecard(args.scorecard), operations)
        if args.scorecard
        else None
    )
    block = format_block(args.run_id, billing, operations, routes)
    print(block)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "runId": args.run_id,
                    "totalCredits": billing.get("totalCredits"),
                    "totalBilledCalls": billing.get("totalCalls"),
                    "operations": operations,
                    "routes": routes,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CostReceiptError as error:
        sys.stderr.write(f"{error}\n")
        raise SystemExit(1) from error
