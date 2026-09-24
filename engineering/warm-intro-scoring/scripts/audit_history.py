#!/usr/bin/env python3
"""Audit a private historical companion artifact without emitting its contents.

Accepts the companion HTML's embedded ``const DATA`` JSON or its JSON payload.
This is a structural and language-marker check, not a factual-verification or
send-approval system. Exit 0 means these limited checks passed; 1 means findings;
2 means the artifact could not be read or parsed.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re


UNCERTAINTY = re.compile(
    r"\b(?:may|might|perhaps|possibly|seems?|appears?)\b|"
    r"\bit looks like\b|\b(?:if|whether) you (?:know|have|feel)\b|"
    r"\b(?:do you know|would you feel comfortable)\b",
    re.I,
)
QUESTION = re.compile(
    r"\b(?:know|introduc\w*|intro|connect\w*|comfortable|willing)\b", re.I
)
NO_PRESSURE = re.compile(
    r"\bno pressure\b|\bno worries\b|\bfeel free to (?:decline|pass)\b|"
    r"\b(?:totally|completely|perfectly) (?:fine|okay|ok) if\b|"
    r"\b(?:only|if) (?:you(?:'re| are) )?comfortable\b",
    re.I,
)


def load_payload(path):
    text = Path(path).read_text(encoding="utf-8")
    if text.lstrip().startswith("{"):
        payload = json.loads(text)
    else:
        marker = re.search(r"\bconst\s+DATA\s*=\s*", text)
        if marker is None:
            raise ValueError("unsupported artifact")
        payload, _ = json.JSONDecoder().raw_decode(text[marker.end():])
    if not isinstance(payload, dict) or not isinstance(payload.get("targets"), list):
        raise ValueError("unsupported payload")
    return payload


def audit(payload):
    findings = Counter()
    counts = Counter(targets=0, paths=0, drafts=0, components=0, evidence_entries=0)
    targets = payload.get("targets") if isinstance(payload, dict) else None
    if not isinstance(targets, list):
        targets = []
        findings["invalid_targets"] += 1
    for target in targets:
        counts["targets"] += 1
        paths = target.get("top") if isinstance(target, dict) else None
        if not isinstance(paths, list):
            findings["invalid_paths"] += 1
            continue
        for path in paths:
            counts["paths"] += 1
            if not isinstance(path, dict):
                findings["invalid_path"] += 1
                continue
            draft = path.get("draft")
            # Withheld drafts are valid; require at least one actual draft overall.
            if draft is None:
                continue
            counts["drafts"] += 1
            if not isinstance(draft, dict):
                findings["invalid_draft"] += 1
                continue
            if draft.get("approved") is not False:
                findings["approval_not_false"] += 1
            ask = draft.get("connector_ask")
            if not isinstance(ask, str):
                ask = ""
            if not ask.strip():
                findings["missing_ask"] += 1
            forwardable = draft.get("forwardable_note")
            if not isinstance(forwardable, str) or not forwardable.strip():
                findings["missing_forwardable_note"] += 1
            if not UNCERTAINTY.search(ask):
                findings["missing_uncertainty"] += 1
            questions = re.findall(r"[^.!?]*\?", ask)
            if not any(QUESTION.search(question) for question in questions):
                findings["missing_relationship_question"] += 1
            if not NO_PRESSURE.search(ask):
                findings["missing_no_pressure"] += 1
            components = path.get("components")
            if not isinstance(components, list) or not components:
                findings["missing_components"] += 1
                continue
            for component in components:
                counts["components"] += 1
                evidence = component.get("evidence") if isinstance(component, dict) else None
                if not isinstance(evidence, list) or not evidence:
                    findings["component_missing_evidence"] += 1
                    continue
                for entry in evidence:
                    counts["evidence_entries"] += 1
                    for field in ("source", "observed_at", "detail"):
                        value = entry.get(field) if isinstance(entry, dict) else None
                        if not isinstance(value, str) or not value.strip():
                            findings["evidence_missing_" + field] += 1
    if not counts["drafts"]:
        findings["missing_drafts"] += 1
    return {"passed": not findings, "counts": dict(counts), "findings": dict(sorted(findings.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="Private companion HTML or extracted JSON")
    args = parser.parse_args()
    try:
        result = audit(load_payload(args.artifact))
    except (OSError, UnicodeError, ValueError, RecursionError):
        # Never echo exception messages: they may contain private input or paths.
        print(json.dumps({"passed": False, "counts": {}, "findings": {"unreadable_or_invalid_artifact": 1}}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
