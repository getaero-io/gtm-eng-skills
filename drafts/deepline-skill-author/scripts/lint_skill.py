#!/usr/bin/env python3
"""Lint one Deepline skill package before it goes into getaero-io/gtm-eng-skills.

    "Will this skill run for an installer who has the Deepline CLI and nothing of yours?"

DETERMINISTIC EVIDENCE BLOCKS; HEURISTIC EVIDENCE REPORTS. A hard block on a regex over English is
the one failure a skill author cannot debug, so only shape-level facts block: a missing file, a
leftover Clay command, an absolute path on your disk, a credential, a closed-vocabulary word outside
its list, an injection pattern marked `block`. Everything else is reported once and left to a person.

Offline by default. `--online` additionally resolves every Deepline tool and play ID the package
names, with the free `deepline tools describe` / `deepline plays describe`, and blocks on any ID the
catalogue does not know. That is the check that catches an invented tool ID, and it is the one most
worth running before a PR.

Usage:
  lint_skill.py <skill_dir> [--online] [--json]

Exit: 0 clean (reports allowed) · 4 blocking findings · 2 bad invocation · 1 the tool itself broke.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import injection  # noqa: E402

TEXT_EXT = {".md", ".py", ".ts", ".js", ".mjs", ".json", ".yaml", ".yml", ".sh", ".txt", ".csv"}
ROOT_FILES_OK = {"SKILL.md", "package.json", "skill-metadata.json"}
SUPPORT_DIRS = {"references", "scripts", "templates", "examples"}
HALTS = {"sample-review", "spend-approval", "send-approval", "write-approval", "other"}

NAME_RX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FENCE_RX = re.compile(r"```.*?```", re.S)
# A relative reference: `references/x.md`, (scripts/y.py), ../references/z.md. Code spans and links.
REF_RX = re.compile(r"(?<![\w/.-])((?:\.\./|\./)?(?:references|scripts|templates|examples)/[\w./-]+\.\w+)")
# Clay mechanics that do not exist for a Deepline installer.
CLAY_CMD_RX = re.compile(
    r"(?m)(?:^|[`$;|&]\s*)clay\s+(?:whoami|login|tables|workflows|routines|search|credits|mcp|setup)\b"
    r"|mcp__[\w-]*clay\w*|\bclay-run/|marketplace\.clay\.com|api\.clay\.com|\bclaygent\b",
    re.I)
CLAY_WORD_RX = re.compile(r"\bclay\b", re.I)
CLAY_OK_LINE_RX = re.compile(r"ported_from|migrat|measured on|from clay|clay-to-deepline", re.I)
ABS_PATH_RX = re.compile(r"(?<![\w.])(?:/Users/[\w.-]+|/home/[\w.-]+|[A-Z]:\\\\Users\\\\)")
CRED_RX = re.compile(
    r"\b(?:sk-(?:ant-)?[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35})\b"
    r"|(?i:(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{24,})")
ANSWER_SHEET_RX = re.compile(r"answer[-_]?sheet|answers\.ya?ml$", re.I)
TOOL_ID_RXS = [
    re.compile(r"deepline\s+tools\s+(?:execute|describe|get)\s+([a-z][a-z0-9_]+)"),
    re.compile(r"\btool(?:Id)?\s*:\s*['\"]([a-z][a-z0-9_]+)['\"]"),
]
PLAY_ID_RXS = [
    re.compile(r"deepline\s+plays\s+(?:run|describe|check)\s+(prebuilt/[\w-]+)"),
    re.compile(r"['\"](prebuilt/[\w-]+)['\"]"),
]
PILOT_RX = re.compile(r"--rows\s+0:1|\bpilot\b|\b10-row\b|small batch|dry run", re.I)
HALTS_RX = re.compile(r"\*\*Halts\*\*\s*[—:-]\s*(.+)")


def _frontmatter(text: str) -> dict | None:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    out, key = {}, None
    for line in m.group(1).splitlines():
        km = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if km and not line.startswith((" ", "\t")):
            key = km.group(1)
            out[key] = km.group(2).strip().strip("|>-").strip().strip("'\"")
        elif key:
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _headings(text: str) -> set[str]:
    return {h.strip().lower() for h in re.findall(r"(?m)^##\s+(.+?)\s*$", text)}


def lint(skill_dir: str, online: bool = False, describe=None) -> dict:
    skill_dir = os.path.abspath(skill_dir)
    findings: list[dict] = []

    def add(sev, check, path, line, msg):
        findings.append({"severity": sev, "check": check, "path": path, "line": line, "message": msg})

    entries: dict[str, str] = {}
    for dp, dns, fns in os.walk(skill_dir):
        dns[:] = [d for d in dns if not d.startswith(".") and d not in {"node_modules", "__pycache__"}]
        for fn in fns:
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, skill_dir)
            if os.path.islink(fp):
                add("block", "symlink", rel, 0, "symlinks do not survive a copy into a skills dir")
                continue
            if ANSWER_SHEET_RX.search(fn):
                add("block", "answer_sheet_in_package", rel, 0,
                    "an answer sheet holds the author's own values; keep it beside the package, never in it")
            top = rel.split(os.sep)[0]
            if os.sep not in rel and rel not in ROOT_FILES_OK and not fn.startswith("."):
                add("report", "loose_root_file", rel, 0, "supporting files belong under references/ or scripts/")
            elif os.sep in rel and top not in SUPPORT_DIRS:
                add("report", "unexpected_dir", rel, 0, f"'{top}/' is not a conventional skill directory")
            if os.path.splitext(fn)[1] in TEXT_EXT:
                with open(fp, encoding="utf-8", errors="replace") as fh:
                    entries[rel] = fh.read()

    skill = entries.get("SKILL.md")
    if skill is None:
        add("block", "missing_skill_md", "SKILL.md", 0, "exactly one SKILL.md at the package root")
        return _result(findings, set(), set())

    # Frontmatter: the repo reads name + description, and nothing else is required.
    fm = _frontmatter(skill)
    if fm is None:
        add("block", "frontmatter", "SKILL.md", 1, "no YAML frontmatter block")
        fm = {}
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not NAME_RX.match(name):
        add("block", "frontmatter_name", "SKILL.md", 1, f"name '{name}' must be lowercase-hyphenated")
    elif name != os.path.basename(skill_dir):
        add("block", "name_dir_mismatch", "SKILL.md", 1,
            f"name '{name}' does not match directory '{os.path.basename(skill_dir)}'")
    if not desc:
        add("block", "frontmatter_description", "SKILL.md", 1, "description is the trigger; it cannot be empty")
    elif CLAY_WORD_RX.search(desc) and not CLAY_OK_LINE_RX.search(desc):
        add("report", "clay_in_description", "SKILL.md", 1, "description names Clay; installers route on Deepline")

    # Body contract.
    heads = _headings(skill)
    if "declared inputs" not in heads:
        add("block", "declared_inputs", "SKILL.md", 0, "`## Declared inputs` is the one required body section")
    for h in ("what this skill touches", "representative output", "what this skill does not claim",
              "what good looks like"):
        if h not in heads:
            add("report", "section_missing", "SKILL.md", 0, f"no `## {h[0].upper() + h[1:]}` section")
    if "what this skill touches" in heads:
        sect = skill.lower().split("## what this skill touches", 1)[1].split("\n## ", 1)[0]
        for axis in ("reads", "writes", "never"):
            if f"**{axis}**" not in sect:
                add("report", "touches_axis", "SKILL.md", 0, f"`## What this skill touches` has no **{axis.title()}** line")
    for m in HALTS_RX.finditer(skill):
        for word in re.findall(r"Step\s+\w+\s+`?([\w-]+)`?", m.group(1)):
            if word not in HALTS:
                add("block", "halts_vocabulary", "SKILL.md", _line(skill, m.start()),
                    f"'{word}' is not one of {sorted(HALTS)}; repeat the step number instead of compounding")
    if not PILOT_RX.search(skill):
        add("report", "no_pilot", "SKILL.md", 0, "no pilot / small-batch step before a full run")
    if "deepline" in skill.lower() and "code.deepline.com" not in skill:
        add("report", "no_setup_link", "SKILL.md", 0, "link https://code.deepline.com for CLI setup")

    # Content, every text entry.
    tool_ids: set[str] = set()
    play_ids: set[str] = set()
    for rel, text in sorted(entries.items()):
        is_md = rel.endswith(".md")
        for m in (REF_RX.finditer(text) if is_md else ()):
            ref = m.group(1).rstrip(".,)")
            if "<" in ref or "*" in ref:
                continue
            base = skill_dir if not ref.startswith(("./", "../")) else os.path.dirname(os.path.join(skill_dir, rel))
            target = os.path.normpath(os.path.join(base, ref))
            alt = os.path.normpath(os.path.join(os.path.dirname(os.path.join(skill_dir, rel)), ref))
            if not target.startswith(skill_dir):
                add("block", "reference_outside_package", rel, _line(text, m.start()), f"{ref} points outside the package")
            elif not (os.path.exists(target) or os.path.exists(alt)):
                add("block", "missing_file", rel, _line(text, m.start()), f"{ref} does not exist in the package")
        for m in ABS_PATH_RX.finditer(text):
            add("block", "absolute_path", rel, _line(text, m.start()), "a path on the author's disk resolves nowhere else")
        for m in CRED_RX.finditer(text):
            add("block", "credential", rel, _line(text, m.start()), "credential-shaped string (value not shown)")
        if is_md:
            for m in CLAY_CMD_RX.finditer(text):
                ln = text.splitlines()[_line(text, m.start()) - 1]
                if not CLAY_OK_LINE_RX.search(ln):
                    add("block", "clay_mechanics", rel, _line(text, m.start()),
                        f"Clay-only mechanic `{m.group(0).strip()}`; use the Deepline equivalent")
            for i, ln in enumerate(text.splitlines(), 1):
                if CLAY_WORD_RX.search(ln) and not CLAY_CMD_RX.search(ln) and not CLAY_OK_LINE_RX.search(ln):
                    add("report", "clay_mention", rel, i, "mentions Clay; keep only migration notes and attributed measurements")
        for rx in TOOL_ID_RXS:
            tool_ids.update(rx.findall(text))
        for rx in PLAY_ID_RXS:
            play_ids.update(rx.findall(text))

    # Prompt-injection scan over every text entry — a clean SKILL.md with the payload in a reference is the attack.
    inj = injection.scan_package({k: v for k, v in entries.items()
                                  if os.path.basename(k) != "injection_patterns.json"})  # the rules, not a payload
    for f in inj["findings"]:
        add(f["severity"], "injection/" + f["pattern_id"], f["path"], f["line"], f["creator_message"])

    if online:
        describe = describe or _describe
        for tid in sorted(tool_ids):
            if not describe("tools", tid):
                add("block", "unknown_tool_id", "*", 0, f"`deepline tools describe {tid}` does not resolve")
        for pid in sorted(play_ids):
            if not describe("plays", pid):
                add("block", "unknown_play_id", "*", 0, f"`deepline plays describe {pid}` does not resolve")
    return _result(findings, tool_ids, play_ids, online)


def _describe(kind: str, ident: str) -> bool:
    r = subprocess.run(["deepline", kind, "describe", ident, "--json"], capture_output=True, text=True,
                       timeout=60, env={**os.environ, "DEEPLINE_SKIP_SELF_UPDATE": "1"})
    return r.returncode == 0


def _result(findings, tool_ids, play_ids, online=False) -> dict:
    blocking = [f for f in findings if f["severity"] == "block"]
    return {
        "verdict": "blocked" if blocking else "ok",
        "blocking_count": len(blocking),
        "findings": findings,
        "tool_ids": sorted(tool_ids),
        "play_ids": sorted(play_ids),
        "ids_resolved_online": online,
    }


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(json.dumps({"error": {"code": "validation_error", "message": "usage: lint_skill.py <skill_dir> [--online] [--json]"}}),
              file=sys.stderr)
        return 2
    try:
        res = lint(args[0], online="--online" in argv)
    except Exception as exc:  # the tool broke, not the package
        print(json.dumps({"error": {"code": "internal_error", "message": f"{type(exc).__name__}: {exc}"}}), file=sys.stderr)
        return 1
    if "--json" in argv:
        print(json.dumps(res, indent=1))
    else:
        for f in sorted(res["findings"], key=lambda f: f["severity"] != "block"):
            loc = f"{f['path']}:{f['line']}" if f["line"] else f["path"]
            print(f"{f['severity'].upper():6} {f['check']:28} {loc}  {f['message']}")
        ids = "resolved online" if res["ids_resolved_online"] else "NOT RESOLVED (run with --online)"
        print(f"\n{res['verdict']} · {res['blocking_count']} blocking · "
              f"{len(res['tool_ids'])} tool ids, {len(res['play_ids'])} play ids {ids}")
    return 4 if res["verdict"] == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
