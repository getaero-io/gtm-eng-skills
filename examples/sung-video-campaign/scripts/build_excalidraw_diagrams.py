#!/usr/bin/env python3
"""Generate public-safe Excalidraw workflow diagrams for the Sung campaign."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PALETTE = {
    "source": "#e7f5ff",
    "decision": "#fff4e6",
    "action": "#ebfbee",
    "guardrail": "#fff5f5",
    "storage": "#f8f9fa",
}


def base_element(element_id: str, element_type: str, x: int, y: int, w: int, h: int) -> dict:
    return {
        "id": element_id,
        "type": element_type,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": "#1f2937",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": abs(hash(element_id)) % 1000000,
        "version": 1,
        "versionNonce": abs(hash(element_id + "n")) % 1000000,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
    }


def node(element_id: str, label: str, x: int, y: int, kind: str = "source", w: int = 180, h: int = 74) -> list[dict]:
    rect = base_element(element_id, "rectangle", x, y, w, h)
    rect["backgroundColor"] = PALETTE[kind]
    text = base_element(f"{element_id}_text", "text", x + 16, y + 18, w - 32, h - 24)
    text.update(
        {
            "text": label,
            "fontSize": 18,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "baseline": 24,
            "containerId": element_id,
            "originalText": label,
            "lineHeight": 1.2,
            "backgroundColor": "transparent",
            "strokeWidth": 1,
        }
    )
    rect["boundElements"] = [{"type": "text", "id": text["id"]}]
    return [rect, text]


def diamond(element_id: str, label: str, x: int, y: int, w: int = 170, h: int = 90) -> list[dict]:
    item = base_element(element_id, "diamond", x, y, w, h)
    item["backgroundColor"] = PALETTE["decision"]
    text = base_element(f"{element_id}_text", "text", x + 22, y + 24, w - 44, h - 34)
    text.update(
        {
            "text": label,
            "fontSize": 17,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "baseline": 22,
            "containerId": element_id,
            "originalText": label,
            "lineHeight": 1.2,
            "backgroundColor": "transparent",
            "strokeWidth": 1,
        }
    )
    item["boundElements"] = [{"type": "text", "id": text["id"]}]
    return [item, text]


def arrow(element_id: str, x1: int, y1: int, x2: int, y2: int, label: str | None = None) -> list[dict]:
    arr = base_element(element_id, "arrow", x1, y1, x2 - x1, y2 - y1)
    arr.update(
        {
            "points": [[0, 0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "roundness": {"type": 2},
        }
    )
    if not label:
        return [arr]
    text = base_element(f"{element_id}_label", "text", (x1 + x2) // 2 - 60, (y1 + y2) // 2 - 26, 120, 28)
    text.update(
        {
            "text": label,
            "fontSize": 14,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "baseline": 18,
            "originalText": label,
            "lineHeight": 1.2,
            "backgroundColor": "#ffffff",
            "strokeWidth": 1,
        }
    )
    return [arr, text]


def scene(elements: list[dict]) -> dict:
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def flow(prefix: str, labels: list[tuple[str, str]], decisions: set[int] | None = None) -> list[dict]:
    decisions = decisions or set()
    elements: list[dict] = []
    x = 40
    y = 120
    for i, (label, kind) in enumerate(labels):
        if i in decisions:
            elements.extend(diamond(f"{prefix}_{i}", label, x, y - 8))
        else:
            elements.extend(node(f"{prefix}_{i}", label, x, y, kind))
        if i < len(labels) - 1:
            elements.extend(arrow(f"{prefix}_a{i}", x + 180, y + 37, x + 250, y + 37))
        x += 250
    return elements


DIAGRAMS = {
    "diagrams/core/warehouse-gtm-operating-loop.excalidraw": flow(
        "core1",
        [
            ("Raw warehouse\nsignals", "source"),
            ("Identity graph", "storage"),
            ("Semantic\ndefinitions", "decision"),
            ("Backtest vs\nrevenue events", "decision"),
            ("Draft smallest\nuseful action", "action"),
            ("Writeback +\nrun summary", "storage"),
            ("Feedback loop", "action"),
        ],
    ),
    "diagrams/core/product-usage-crm-campaign.excalidraw": flow(
        "core2",
        [
            ("Product usage\nmilestone", "source"),
            ("Account + CRM\ncontext", "storage"),
            ("Fit and owner\ncheck", "decision"),
            ("Suppress risky\nrecords", "guardrail"),
            ("Draft campaign\nor rep task", "action"),
            ("Approval sample", "decision"),
            ("Launch / log\nchanges", "storage"),
        ],
        {2, 5},
    ),
    "diagrams/core/backtest-guardrail-activation.excalidraw": flow(
        "core3",
        [
            ("Historical\noutcomes", "source"),
            ("Candidate\nsignals", "source"),
            ("Backtest lift\nand leakage", "decision"),
            ("Add product\ncontext", "storage"),
            ("Guardrail\nchecks", "guardrail"),
            ("Activation\nqueue", "action"),
            ("Measure result", "storage"),
        ],
        {2},
    ),
    "diagrams/identity/personal-email-linkedin-resolution.excalidraw": flow(
        "id1",
        [
            ("Personal email\nsignup", "source"),
            ("Usage says\nhigh intent", "source"),
            ("Search profile\ncandidates", "decision"),
            ("Validate name +\n2 signals", "guardrail"),
            ("Stage for\nreview", "action"),
            ("Verified\nLinkedIn", "storage"),
            ("Route account\nor suppress", "action"),
        ],
        {2, 3},
    ),
    "diagrams/identity/contact-enrichment-waterfall.excalidraw": flow(
        "id2",
        [
            ("CRM contact\ntrigger", "source"),
            ("Provider A", "source"),
            ("Provider B\nfallback", "source"),
            ("Profile scrape\nvalidation", "guardrail"),
            ("Confidence\nthreshold", "decision"),
            ("CRM writeback", "action"),
            ("Run summary", "storage"),
        ],
        {4},
    ),
    "diagrams/identity/champion-job-change-recovery.excalidraw": flow(
        "id3",
        [
            ("Former power\nuser", "source"),
            ("Job change\nsignal", "source"),
            ("New company\nmatch", "decision"),
            ("Customer / opp\nsuppression", "guardrail"),
            ("Warm note\ndraft", "action"),
            ("Owner review", "decision"),
            ("CRM update", "storage"),
        ],
        {2, 5},
    ),
    "diagrams/workflows/product-usage-to-campaign-draft.excalidraw": flow(
        "wf1",
        [
            ("API trigger:\nworkspace id", "source"),
            ("Load usage\nsnapshot", "storage"),
            ("Join CRM\ncontext", "storage"),
            ("Score + reason", "decision"),
            ("Apply\nsuppressions", "guardrail"),
            ("Create draft\ncampaign", "action"),
            ("Post run\nsummary", "storage"),
        ],
        {3},
    ),
    "diagrams/workflows/personal-email-identity-resolution.excalidraw": flow(
        "wf2",
        [
            ("Webhook:\nnew signup", "source"),
            ("Detect personal\nemail", "decision"),
            ("Search LinkedIn\ncandidates", "source"),
            ("Validate\nidentity", "guardrail"),
            ("Attach likely\naccount", "action"),
            ("Stage uncertain\nmatches", "guardrail"),
            ("Log decision", "storage"),
        ],
        {1, 3},
    ),
    "diagrams/workflows/event-attendee-follow-up.excalidraw": flow(
        "wf3",
        [
            ("Event attendee\nor check-in", "source"),
            ("Normalize\nidentity", "storage"),
            ("Enrich account\nand role", "source"),
            ("Segment by\nattendance", "decision"),
            ("Suppress\ncustomers/opps", "guardrail"),
            ("Draft follow-up", "action"),
            ("Sync list +\nsummary", "storage"),
        ],
        {3},
    ),
}


def main() -> None:
    for relative_path, elements in DIAGRAMS.items():
        path = ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(scene(elements), indent=2) + "\n")
        print(path)


if __name__ == "__main__":
    main()
