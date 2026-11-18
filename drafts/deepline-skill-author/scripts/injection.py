#!/usr/bin/env python3
"""Injection detection — the reference implementation.

    "Does this package instruct the reader to do something its author should not be asking?"

The patterns are NOT in this file. They live in `fixtures/injection_patterns.json`, loaded at
import, for a reason that was learned the expensive way: the first delivery of this pattern set was
a Markdown specification with the regexes inline, and the recipient could not use it — extracting
regexes from a rendered document mangles them, and a hand-transcribed regex drifts from the one
that was measured. **Prose is a lossy channel for code.** So the data is the contract and this file
is one consumer of it.

`lint_skill.py` is its caller: it runs `scan_package` over every text file in a skill and turns each
finding into a lint finding with the same severity.

TWO THINGS THAT MAKE THIS DIFFERENT FROM EVERY OTHER CHECK HERE

1. IT IS HEURISTIC AND IT BLOCKS. Every other check in the lint obeys "nothing heuristic ever
   blocks", with credential detection as the single exception. This is the second, and it earns it
   in a different currency: a published skill runs on other people's machines and the instruction it
   carries executes there. A missed injection harvests credentials from every installer; a false
   positive costs one round of review. The override (`resolution: waived`, with the redacted
   evidence shown) is what makes blocking defensible rather than absolute.

2. IT READS AN ADVERSARIAL ARTEFACT. The input is content designed to make a reader follow it. This
   module treats it as bytes and matches patterns; it never interprets, never summarises, and must
   never hand the content to a model as anything but data.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATTERNS_PATH = os.path.join(_HERE, "fixtures", "injection_patterns.json")

_FLAGS = {"IGNORECASE": re.IGNORECASE, "DOTALL": re.DOTALL, "MULTILINE": re.MULTILINE}


def _flags(names) -> int:
    out = 0
    for n in names or ():
        out |= _FLAGS[n]
    return out


@dataclass
class Finding:
    pattern_id: str
    severity: str  # block | report
    label: str
    path: str  # the entry it came from — a finding without this is unactionable
    line: int
    evidence: str
    creator_message: str

    def as_dict(self) -> dict:
        return asdict(self)


class Patterns:
    """The loaded pattern set. Fail loudly if it is absent: a scanner that silently finds nothing
    because its rules did not load is the worst possible outcome for a blocking check."""

    def __init__(self, path: str = _PATTERNS_PATH):
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        self.version = spec["version"]
        self.raw = spec
        base = _flags(spec.get("flags"))
        self.lexical, self.structural, self.density = [], [], []
        for p in spec["patterns"]:
            if p.get("regex"):
                self.lexical.append((p, re.compile(p["regex"], base)))
            elif p.get("structural"):
                st = p["structural"]
                self.structural.append((
                    p,
                    [re.compile(r, base | _flags(st.get("region_flags"))) for r in st["regions"]],
                    re.compile(st["directive_regex"], base),
                ))
            elif p.get("density"):
                d = p["density"]
                self.density.append((p, re.compile(d["term_regex"], base)))
            else:
                raise ValueError(f"pattern {p['id']} declares no matcher")
        if not (self.lexical and self.structural and self.density):
            raise ValueError("pattern file is missing a whole matcher class — refusing to scan")

    def digest(self) -> str:
        """So a caller can state WHICH pattern set produced a verdict: a silent edit to the rules is a
        silent contract change."""
        import hashlib
        with open(_PATTERNS_PATH, "rb") as fh:
            return "sha256:" + hashlib.sha256(fh.read()).hexdigest()[:32]


_DESC = re.compile(r"^description:\s*\|?\s*\n((?:[ \t]+.*\n|\n)*)|^description:[ \t]*(.*)$", re.M)


def _description(text: str) -> str:
    m = _DESC.search(text)
    return (m.group(1) or m.group(2) or "") if m else ""


def _line_of(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1


def scan_entry(text: str, path: str, pat: Patterns) -> list[Finding]:
    """Scan ONE text entry. Callers must invoke this for every recognised entry in the package —
    a clean SKILL.md with the payload in a reference file measures 0 findings scanned alone against
    12 scanned fully, so entry coverage is not a refinement, it is the whole attack."""
    out: list[Finding] = []

    def add(p, line, evidence):
        out.append(Finding(p["id"], p["severity"], p["label"], path, line,
                           evidence[:120].replace("\n", " ").strip(), p["creator_message"]))

    for p, rx in pat.lexical:
        for m in rx.finditer(text):
            add(p, _line_of(text, m.start()), m.group(0))

    for p, regions, directive in pat.structural:
        for rx in regions:
            for m in rx.finditer(text):
                inner = m.group(1) if m.groups() else m.group(0)
                if directive.search(inner):
                    add(p, _line_of(text, m.start()), inner)

    for p, term_rx in pat.density:
        field = p["density"].get("field")
        subject = _description(text) if field == "description" else text
        if not subject:
            continue
        distinct = {t.lower() for t in term_rx.findall(subject)}
        if len(distinct) >= p["density"]["distinct_terms_threshold"]:
            add(p, 1, f"{len(distinct)} distinct promotional terms in the {field}")

    return out


def scan_package(entries: dict[str, str], pat: Patterns | None = None) -> dict:
    """`entries` maps entry path -> text. Returns the full result, including the pattern digest so
    a verdict can be attributed to a specific rule set."""
    pat = pat or Patterns()
    findings = [f for path, text in sorted(entries.items()) for f in scan_entry(text, path, pat)]
    blocking = [f for f in findings if f.severity == "block"]
    return {
        "pattern_version": pat.version,
        "pattern_digest": pat.digest(),
        "entries_scanned": len(entries),
        "findings": [f.as_dict() for f in findings],
        "blocking_count": len(blocking),
        # `blocked` and `findings` are separate on purpose: a report-only result is not a pass with
        # notes, it is a pass. Only `block` severity stops anything.
        "verdict": "blocked" if blocking else "ok",
    }


if __name__ == "__main__":
    import sys
    pat = Patterns()
    ents = {}
    for arg in sys.argv[1:]:
        if os.path.isdir(arg):
            for dp, _, fns in os.walk(arg):
                for fn in fns:
                    fp = os.path.join(dp, fn)
                    ents[os.path.relpath(fp, arg)] = open(fp, encoding="utf-8",
                                                          errors="replace").read()
        else:
            ents[os.path.basename(arg)] = open(arg, encoding="utf-8", errors="replace").read()
    print(json.dumps(scan_package(ents, pat), indent=1))
