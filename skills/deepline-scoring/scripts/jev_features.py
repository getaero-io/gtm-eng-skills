#!/usr/bin/env python3
"""Extract typed website features per account with Jev (`ai_evaluate`, model `typesafe-ai/jev`).

Reads an accounts CSV with a `website` cell (the shape collect_sources.py writes) and a frozen
questions JSON (`{id: {type, instructions, criteria?}}`). Writes a copy of the CSV plus one
`jev__<id>` column per question and `coverage__jev`, so the columns pass straight through
`build_feature_matrix.py --carry` into `train_scorecard.py`:

  boolean -> probability (0..1)   choice -> chosen label   score -> expected level index

Accounts without usable website text get empty values and `coverage__jev` = the website state
(missing|empty|error): no text is unknown, not a "no". Receipts under `<out>.receipts/` are keyed
by domain and the questions hash, so reruns do not re-buy and an edited question set never reuses
old answers. `<out>.manifest.json` records the hash; pass `--questions-sha256` when scoring to
prove the set matches the one used in discovery.

    python3 jev_features.py --input accounts_sources.csv --questions questions.json \
      --state-cols company,industry --output accounts_jev.csv --limit 2
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import analyze_signals_v2 as az  # noqa: E402  (shared website adapter)
from collect_sources import deepline, now  # noqa: E402

MODEL = "typesafe-ai/jev"
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def questions_sha256(questions: dict, model: str = MODEL) -> str:
    return hashlib.sha256(json.dumps({"model": model, "questions": questions}, sort_keys=True).encode()).hexdigest()


def build_state(row: dict, state_cols: list[str], max_chars: int) -> tuple[dict | None, str]:
    """Return (state, website coverage). State is None when there is no text to judge."""
    docs, coverage = az.source(row.get("website"), "website")
    text = "\n\n".join(f"# {d['url']}\n{d['text']}" if d["url"] else d["text"] for d in docs).strip()
    if not text:
        return None, coverage
    state = {"domain": row.get("domain", ""), "website_text": text[:max_chars]}
    state.update({c: row.get(c, "") for c in state_cols})
    return state, coverage


def flatten(questions: dict, extracted: dict) -> dict:
    """One feature value per question; a missing answer fails loudly instead of becoming a zero."""
    out = {}
    for qid, spec in questions.items():
        ans = extracted.get(qid)
        if not isinstance(ans, dict):
            raise ValueError(f"no answer for question {qid!r}")
        kind = spec["type"]
        out[f"jev__{qid}"] = ans["probability"] if kind == "boolean" else ans["choice"] if kind == "choice" else ans["score"]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True)
    p.add_argument("--questions", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--state-cols", default="", help="Comma-separated input columns added to the state (name, firmographics)")
    p.add_argument("--max-chars", type=int, default=14_000, help="Website text sent per account")
    p.add_argument("--questions-sha256", help="Fail unless the questions file hashes to this (frozen set)")
    p.add_argument("--limit", type=int, default=None, help="Only evaluate the first N accounts without receipts (pilot/budget guard)")
    p.add_argument("--workers", type=int, default=8)
    args = p.parse_args()

    questions = json.loads(Path(args.questions).read_text())
    digest = questions_sha256(questions)
    if args.questions_sha256 and args.questions_sha256 != digest:
        sys.exit(f"questions hash {digest} != expected {args.questions_sha256}; the question set changed since it was frozen")
    state_cols = [c for c in (x.strip() for x in args.state_cols.split(",")) if c]
    rows = list(csv.DictReader(open(args.input, encoding="utf-8-sig", newline="")))
    receipts = Path(args.output + ".receipts"); receipts.mkdir(parents=True, exist_ok=True)
    cols = [f"jev__{q}" for q in questions]

    def receipt_path(domain: str) -> Path:
        return receipts / f"{domain}__{digest[:12]}.json"

    def evaluate(domain: str, state: dict) -> dict:
        res = deepline("ai_evaluate", {"model": MODEL, "questions": questions, "state": state}, timeout=120)
        raw = (res.get("toolResponse") or {}).get("rawV2") or {}
        rec = {"domain": domain, "questions_sha256": digest, "evaluated_at": now(), "billing": res.get("billing"),
               "usage": raw.get("usage"), "extracted_json": raw.get("extracted_json") or {}}
        flatten(questions, rec["extracted_json"])  # validate before persisting
        receipt_path(domain).write_text(json.dumps(rec))
        return rec

    todo, plan = {}, []
    for row in rows:
        domain = (row.get("domain") or "").strip().lower().removeprefix("www.")
        state, coverage = build_state(row, state_cols, args.max_chars) if domain else (None, "missing_domain")
        plan.append((row, domain, state, coverage))
        if state is None or domain in todo or receipt_path(domain).exists():
            continue
        if args.limit is not None and len(todo) >= args.limit:
            continue
        todo[domain] = state

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:  # ponytail: no client-side pacing; 30 req/s limit >> 8 workers at ~2.5s/call
        futures = {pool.submit(evaluate, d, s): d for d, s in todo.items()}
        for fut in as_completed(futures):
            done += 1
            try:
                fut.result(); print(f"[{done}/{len(todo)}] {futures[fut]} ok", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[{done}/{len(todo)}] {futures[fut]} error: {str(exc)[:200]}", flush=True)

    counts: dict[str, int] = {}
    for row, domain, state, coverage in plan:
        row.update({c: "" for c in cols})
        path = receipt_path(domain) if domain else None
        if state is None:
            row["coverage__jev"] = coverage
        elif path and path.exists():
            row.update(flatten(questions, json.loads(path.read_text())["extracted_json"]))
            row["coverage__jev"] = "success"
        else:
            row["coverage__jev"] = "not_evaluated" if domain not in todo else "error"
        counts[row["coverage__jev"]] = counts.get(row["coverage__jev"], 0) + 1

    fields = list(rows[0].keys()) if rows else []
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    Path(args.output + ".manifest.json").write_text(json.dumps(
        {"model": MODEL, "questions_sha256": digest, "questions": questions, "max_chars": args.max_chars,
         "state_cols": state_cols, "written_at": now(), "coverage": counts}, indent=2))
    print(json.dumps({"output": args.output, "questions_sha256": digest, "newly_evaluated": len(todo), "coverage": counts}))


if __name__ == "__main__":
    main()
