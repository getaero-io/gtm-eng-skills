#!/usr/bin/env python3
"""Reject direct multi-route fanout that bypasses a search experiment."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def code_only(source: str) -> str:
    """Preserve offsets while hiding strings and comments from simple lexical checks."""
    output = list(source)
    index = 0
    while index < len(source):
        if source.startswith("//", index):
            end = source.find("\n", index)
            end = len(source) if end == -1 else end
        elif source.startswith("/*", index):
            end = source.find("*/", index + 2)
            end = len(source) if end == -1 else end + 2
        elif source[index] in "'\"`":
            quote = source[index]
            end = index + 1
            while end < len(source):
                if source[end] == "\\":
                    end += 2
                    continue
                end += 1
                if source[end - 1] == quote:
                    break
        else:
            index += 1
            continue
        for offset in range(index, min(end, len(source))):
            if output[offset] != "\n":
                output[offset] = " "
        index = end
    return "".join(output)


def matching_brace(code: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def matching_square_bracket(code: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(code)):
        if code[index] == "[":
            depth += 1
        elif code[index] == "]":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def matching_parenthesis(code: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(code)):
        if code[index] == "(":
            depth += 1
        elif code[index] == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def static_program_arrays(code: str) -> list[tuple[str, int, int]]:
    """Find ordinary typed `const companyPrograms: SearchProgram[] = [...]` declarations."""
    arrays: list[tuple[str, int, int]] = []
    declaration = re.compile(
        r"\b(?:const|let)\s+(?P<name>\w*[Pp]rograms\w*)\s*"
        r"(?::[^;=]+)?=\s*\["
    )
    for match in declaration.finditer(code):
        opening = match.end() - 1
        closing = matching_square_bracket(code, opening)
        if closing is not None:
            arrays.append((match.group("name"), opening, closing))
    return arrays


def experiment_argument_ranges(code: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for match in re.finditer(r"\brunSearchExperiment\s*\(", code):
        opening = code.find("(", match.start(), match.end())
        closing = matching_parenthesis(code, opening)
        if closing is not None:
            ranges.append((opening, closing))
    return ranges


def experiment_program_array_ranges(code: str) -> list[tuple[int, int]]:
    arguments = experiment_argument_ranges(code)
    ranges: list[tuple[int, int]] = []
    for name, start, end in static_program_arrays(code):
        if any(
            re.search(rf"\b{re.escape(name)}\b", code[left:right])
            for left, right in arguments
        ):
            ranges.append((start, end))
    return ranges


def has_hardcoded_company_cohort(code: str) -> bool:
    """Detect the common open-world shortcut: inline company+domain rows."""
    declaration = re.compile(r"\b(?:const|let)\s+\w*(?:rows|scope)\w*\s*(?::[^;=]+)?=\s*\[", re.I)
    for match in declaration.finditer(code):
        opening = match.end() - 1
        closing = matching_square_bracket(code, opening)
        if closing is None:
            continue
        values = code[opening:closing]
        if re.search(r"\b(?:company|company_name)\s*:\s*[^,}\n]+", values) and re.search(
            r"\bdomain\s*:\s*[^,}\n]+", values
        ):
            return True
    return False


def has_company_to_person_handoff(code: str) -> bool:
    """Require the contact stage to consume accepted company experiment output."""
    handoff = re.search(
        r"\b(?:const|let)\s+(?P<rows>\w*(?:contact|people)\w*)\s*[^=]*="
        r"[^;]*\b(?P<experiment>\w*(?:company|discovery)\w*)\s*\.\s*finalResults\b",
        code,
        re.I | re.S,
    )
    if handoff is None:
        return False
    rows_name = handoff.group("rows")
    experiment_name = handoff.group("experiment")
    if not re.search(
        rf"\b{re.escape(rows_name)}\b[^;]*\.\s*(?:filter|map|flatMap)\s*\(",
        code[handoff.start() : handoff.start() + 1200],
        re.S,
    ):
        return False
    return bool(
        re.search(
            rf"\brunSearchExperiment\s*\([\s\S]{{0,4000}}?\brows\s*:\s*{re.escape(rows_name)}\b",
            code[handoff.end() :],
        )
    ) and experiment_name.lower().startswith(("company", "discovery"))


def program_run_ranges(code: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    program_arrays = experiment_program_array_ranges(code)
    run_start = re.compile(r"\b(?:async\s+)?run\s*\(|\brun\s*:\s*(?:async\s*)?\(")
    for match in run_start.finditer(code):
        if not inside(match.start(), program_arrays):
            continue
        parameters = code.find("(", match.start(), match.end())
        after_parameters = matching_parenthesis(code, parameters)
        if after_parameters is None:
            continue
        opening = after_parameters
        while opening < len(code) and code[opening].isspace():
            opening += 1
        if code.startswith("=>", opening):
            opening += 2
            while opening < len(code) and code[opening].isspace():
                opening += 1
        if opening >= len(code) or code[opening] != "{":
            continue
        closing = matching_brace(code, opening)
        if closing is not None:
            ranges.append((opening, closing))
    return ranges


def programs_missing_declared_getters(code: str) -> list[int]:
    """Return tool-backed strategies that fail to consume each call's own getter."""
    assigned_call = re.compile(
        r"\b(?:const|let)\s+(?P<response>[A-Za-z_$][\w$]*)\s*=\s*"
        r"await\s+\w+\s*\.\s*tools\s*\.\s*execute\s*\("
    )
    getter_binding = re.compile(
        r"\b(?:const|let)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*"
        r"(?P<response>[A-Za-z_$][\w$]*)\s*\.\s*extracted(?:Values|Lists)\s*\.\s*"
        r"[A-Za-z_$][\w$]*\s*;"
    )

    def body_has_getter_for_each_call(program: str) -> bool:
        calls = list(assigned_call.finditer(program))
        total_tool_calls = len(
            re.findall(r"\b\w+\s*\.\s*tools\s*\.\s*execute\s*\(", program)
        )
        # A response that was not assigned cannot safely be associated with a
        # declared getter. Reject it rather than accepting a getter from a
        # different provider response.
        if len(calls) != total_tool_calls:
            return False
        for call in calls:
            response = call.group("response")
            direct_getter = rf"\b{re.escape(response)}\s*\.\s*extracted(?:Values|Lists)\s*\.\s*[A-Za-z_$][\w$]*\s*\?*\.\s*get\s*\("
            if any(
                not re.search(r"\bvoid\s*$", program[: match.start()])
                for match in re.finditer(direct_getter, program)
            ):
                continue
            bindings = [
                match.group("name")
                for match in getter_binding.finditer(program)
                if match.group("response") == response
            ]
            if not any(
                any(
                    not re.search(r"\bvoid\s*$", program[: match.start()])
                    for match in re.finditer(
                        rf"\b{re.escape(name)}\s*\?*\.\s*get\s*\(",
                        program,
                    )
                )
                for name in bindings
            ):
                return False
        return True

    return [
        start
        for start, end in program_run_ranges(code)
        if re.search(r"\b\w+\s*\.\s*tools\s*\.\s*execute\s*\(", code[start:end])
        and not body_has_getter_for_each_call(code[start:end])
    ]


def programs_using_raw_parser(code: str) -> list[int]:
    """Reject a raw-response alias that is subsequently used as a typed record.

    Raw responses may remain source receipts for bound evidence. Turning one into
    an alias and reading fields from it is exactly the unstable shape guessing
    that declared getters avoid.
    """
    alias = re.compile(
        r"\b(?:const|let)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*"
        r"[A-Za-z_$][\w$]*\s*\.\s*toolResponse\s*\.\s*raw"
        r"(?:\s+as\s+[^;\n]+)?\s*;"
    )
    raw_parsers: list[int] = []
    for start, end in program_run_ranges(code):
        program = code[start:end]
        if not re.search(r"\b\w+\s*\.\s*tools\s*\.\s*execute\s*\(", program):
            continue
        if any(
            re.search(
                rf"\b{re.escape(match.group('name'))}\s*(?:\?\.|\[)",
                program[match.end() :],
            )
            for match in alias.finditer(program)
        ):
            raw_parsers.append(start)
    return raw_parsers


def inside(position: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in ranges)


def inspect(
    source: str,
    minimum_experiments: int,
    require_live_company_discovery: bool,
    require_declared_getters: bool,
    require_company_to_person_handoff: bool,
) -> dict[str, object]:
    code = code_only(source)
    experiment_count = len(re.findall(r"\brunSearchExperiment\s*\(", code))
    ranges = program_run_ranges(code)
    retrieval = re.compile(
        r"\b\w+\s*\.\s*(?:tools\s*\.\s*execute|fetch|runPlay)\s*\("
    )
    direct_calls = [
        match.start()
        for match in retrieval.finditer(code)
        if not inside(match.start(), ranges)
    ]
    missing_getter_programs = (
        programs_missing_declared_getters(code) if require_declared_getters else []
    )
    raw_parser_programs = (
        programs_using_raw_parser(code) if require_declared_getters else []
    )
    errors: list[str] = []
    if "replace-with" in source or "CATALOG_REQUIRED" in source:
        errors.append(
            "Scaffold placeholder remains. Replace the scope, bind every retained strategy, and remove CATALOG_REQUIRED before checking."
        )
    if re.search(r"\bboundProgramIds\s*:[^=]*=\s*\[\s*\]", code):
        errors.append(
            "No bound program ids. List each retained strategy only after its body has a literal executable mechanism."
        )
    if experiment_count < minimum_experiments:
        errors.append(
            f"Expected at least {minimum_experiments} runSearchExperiment call(s), found {experiment_count}."
        )
    if direct_calls:
        errors.append(
            "Found retrieval outside SearchProgram.run. Move the route into a program body; do not direct-fanout with Promise.all or a dataset column."
        )
    if missing_getter_programs:
        errors.append(
            "A tool-backed SearchProgram did not read a named declared getter for every tool call. "
            "Copy extractedValues.<name>.get() or extractedLists.<name>.get() "
            "from tools describe; do not guess toolResponse.raw paths."
        )
    if raw_parser_programs:
        errors.append(
            "A tool-backed SearchProgram parsed fields from toolResponse.raw. Read the named declared getter into the result value; raw may only remain evidence context for boundClaim."
        )
    if require_live_company_discovery and has_hardcoded_company_cohort(code):
        errors.append(
            "Open-world company discovery cannot start from inline company+domain rows. Use source/query partitions; accepted discovered companies become the next-stage rows."
        )
    if require_company_to_person_handoff and not has_company_to_person_handoff(code):
        errors.append(
            "Company → person work needs contact rows derived from accepted companyExperiment.finalResults and passed to the second runSearchExperiment; do not use a hand-picked cohort or a separate lookup Play."
        )
    return {
        "ok": not errors,
        "experiments": experiment_count,
        "direct_retrieval_calls": len(direct_calls),
        "programs_missing_declared_getters": len(missing_getter_programs),
        "programs_using_raw_parser": len(raw_parser_programs),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("play", type=Path)
    parser.add_argument("--minimum-experiments", type=int, default=1)
    parser.add_argument(
        "--require-live-company-discovery",
        action="store_true",
        help="Reject inline company/domain cohorts for an open-world company task.",
    )
    parser.add_argument(
        "--require-company-to-person-handoff",
        action="store_true",
        help="Require a second experiment over contact rows derived from accepted company results.",
    )
    parser.add_argument(
        "--require-declared-getters",
        action="store_true",
        help="Require every tool-backed strategy to use a named declared getter.",
    )
    args = parser.parse_args()
    if args.minimum_experiments < 1:
        parser.error("--minimum-experiments must be positive.")
    result = inspect(
        args.play.read_text(encoding="utf-8"),
        args.minimum_experiments,
        args.require_live_company_discovery,
        args.require_declared_getters,
        args.require_company_to_person_handoff,
    )
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
