"""Generate personalized warm intro ask messages for scored connectors.

Takes the CSV output from warm-intro-scoring/lookup.py, uses each row's
shared signal (company overlap or role overlap) to build a grounded prompt,
calls the Deepline API to draft the message, and writes ask_drafts.csv.

Usage:
    python draft_asks.py --input scored_connectors.csv --output ask_drafts.csv
    python draft_asks.py --input scored_connectors.csv --top 20
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ── Prompt ──────────────────────────────────────────────────────────────────

ASK_SYSTEM_PROMPT = """You draft warm intro ask messages. Your output is always a JSON object with two keys: "subject" and "body".

Rules for the body:
- Under 80 words total. Hard limit. Count them.
- Line 1 is the ask. Specific and direct: "Would you be willing to intro me to {target_name} at {target_company}?"
- Line 2 is the reason you're asking this person specifically. Reference the shared signal you're given — shared employer, shared function, shared space. One sentence.
- Line 3 is why this intro matters. One concrete sentence. What you're working on, what you need. No vague synergy language.
- No filler openings. Do not start with "Hope this finds you well", "I wanted to reach out", "I'd love to connect", or any variant.
- Do not say "pick your brain". Do not say "quick chat". Do not say "explore synergies".
- Write like a person, not a salesperson. Confident, not pleading.
- The subject line should be under 8 words. Format: "Intro to {target_name}?" or "Quick intro ask — {target_name}" or similar. Short.

Output format (strict JSON, nothing else):
{"subject": "...", "body": "..."}"""

ASK_USER_TEMPLATE = """Draft a warm intro ask for me to send to my connector.

Connector: {connector_name} (currently at {connector_company})
Target: {target_name} at {target_company}
Shared signal: {signal_description}

Return JSON only."""


# ── CSV helpers ──────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {
    "connector_name",
    "connector_linkedin",
    "target_name",
    "target_company",
    "shared_signal",
    "score",
}

OPTIONAL_COLUMNS = {
    "connector_company",
    "shared_detail",
}


def load_scored_csv(path: str) -> list[dict]:
    """Load and validate the scored connectors CSV.

    Args:
        path: Path to scored connectors CSV.

    Returns:
        List of row dicts.

    Raises:
        SystemExit: If file missing or required columns absent.
    """
    p = Path(path)
    if not p.exists():
        sys.exit(f"Input file not found: {path}")

    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    if not rows:
        sys.exit(f"Input CSV is empty: {path}")

    present = set(rows[0].keys())
    missing = REQUIRED_COLUMNS - present
    if missing:
        sys.exit(
            f"Input CSV is missing required columns: {', '.join(sorted(missing))}\n"
            f"Found columns: {', '.join(sorted(present))}"
        )

    return rows


def build_signal_description(row: dict) -> str:
    """Build a human-readable shared-signal sentence for the prompt.

    Args:
        row: A CSV row dict.

    Returns:
        Short signal description string.
    """
    signal_type = row.get("shared_signal", "").strip()
    detail = row.get("shared_detail", "").strip()
    connector = row.get("connector_name", "your connector").strip()
    target = row.get("target_name", "the target").strip()

    if signal_type == "company_match" and detail:
        return f"{connector} and {target} both worked at {detail}."
    if signal_type == "company_match":
        return f"{connector} worked at the same company as {target}."
    if signal_type == "role_overlap" and detail:
        return f"Both {connector} and {target} work in {detail} — same function, similar space."
    if signal_type == "role_overlap":
        return f"{connector} and {target} share similar roles and functions."
    if detail:
        return detail
    return f"{connector} is a relevant connector to {target}."


# ── Deepline API call ────────────────────────────────────────────────────────

def call_deepline_agent(
    system_prompt: str,
    user_message: str,
    api_key: str,
    model: str = "claude-haiku-4-5",
) -> dict:
    """Call the Deepline agentcompletion endpoint.

    Uses the Deepline API directly via subprocess (matches CLI pattern used
    elsewhere in this repo). Returns parsed JSON dict from the model.

    Args:
        system_prompt: System prompt string.
        user_message: User message string.
        api_key: Deepline API key.
        model: Model ID to use.

    Returns:
        Parsed JSON dict with "subject" and "body" keys.

    Raises:
        RuntimeError: If the API call fails or returns unparseable output.
    """
    payload = {
        "model": model,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
        "max_tokens": 512,
    }

    result = subprocess.run(
        [
            "deepline",
            "api",
            "post",
            "/v1/messages",
            "--body",
            json.dumps(payload),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "DEEPLINE_API_KEY": api_key},
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Deepline API call failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout[:500]}\n"
            f"stderr: {result.stderr[:500]}"
        )

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not parse Deepline API response as JSON: {exc}\n"
            f"Raw output: {result.stdout[:500]}"
        ) from exc

    # Extract text content from the messages response
    content_blocks = response.get("content", [])
    raw_text = ""
    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            raw_text = block.get("text", "").strip()
            break

    if not raw_text:
        raise RuntimeError(
            f"No text content in Deepline API response: {json.dumps(response)[:300]}"
        )

    # Strip markdown code fences if the model wrapped the JSON
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        draft = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model returned non-JSON text: {exc}\nRaw: {raw_text[:400]}"
        ) from exc

    if "subject" not in draft or "body" not in draft:
        raise RuntimeError(
            f"Model JSON missing 'subject' or 'body' keys: {draft}"
        )

    return draft


# ── Main ─────────────────────────────────────────────────────────────────────

def resolve_api_key(explicit_key: Optional[str]) -> str:
    """Resolve Deepline API key from arg, env, or .env file.

    Args:
        explicit_key: Key passed via CLI flag (may be None).

    Returns:
        API key string.

    Raises:
        SystemExit: If no key found.
    """
    if explicit_key:
        return explicit_key

    env_key = os.environ.get("DEEPLINE_API_KEY")
    if env_key:
        return env_key

    # Try .env in current directory
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("DEEPLINE_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val

    sys.exit(
        "No DEEPLINE_API_KEY found. Set it as an environment variable, "
        "add it to a .env file, or pass --api-key."
    )


def draft_asks(
    rows: list[dict],
    api_key: str,
    top: Optional[int],
    model: str,
    verbose: bool,
) -> list[dict]:
    """Generate ask drafts for each connector row.

    Args:
        rows: Scored connector rows from CSV.
        api_key: Deepline API key.
        top: If set, only process the top N rows by score.
        model: Model ID to use for drafting.
        verbose: Print progress.

    Returns:
        List of output row dicts ready for CSV write.
    """
    # Sort by score descending, cap at top N
    sorted_rows = sorted(rows, key=lambda r: float(r.get("score", 0)), reverse=True)
    if top is not None:
        sorted_rows = sorted_rows[:top]

    output_rows: list[dict] = []

    for i, row in enumerate(sorted_rows, 1):
        connector_name = row["connector_name"].strip()
        connector_linkedin = row["connector_linkedin"].strip()
        connector_company = row.get("connector_company", "").strip() or "their company"
        target_name = row["target_name"].strip()
        target_company = row["target_company"].strip()
        score = row.get("score", "")

        signal_description = build_signal_description(row)

        user_message = ASK_USER_TEMPLATE.format(
            connector_name=connector_name,
            connector_company=connector_company,
            target_name=target_name,
            target_company=target_company,
            signal_description=signal_description,
        )

        if verbose:
            print(
                f"[{i}/{len(sorted_rows)}] Drafting ask for {connector_name} → {target_name} "
                f"(score: {score})"
            )

        try:
            draft = call_deepline_agent(
                system_prompt=ASK_SYSTEM_PROMPT,
                user_message=user_message,
                api_key=api_key,
                model=model,
            )
            subject = draft["subject"]
            body = draft["body"]
            status = "ok"
        except RuntimeError as exc:
            print(f"  ERROR for {connector_name}: {exc}", file=sys.stderr)
            subject = ""
            body = ""
            status = f"error: {exc}"

        output_rows.append(
            {
                "connector_name": connector_name,
                "connector_linkedin": connector_linkedin,
                "target_name": target_name,
                "shared_signal": row.get("shared_signal", ""),
                "draft_subject": subject,
                "draft_body": body,
                "score": score,
                "status": status,
            }
        )

    return output_rows


def write_output_csv(rows: list[dict], path: str) -> None:
    """Write output rows to CSV.

    Args:
        rows: Output row dicts.
        path: Destination file path.
    """
    fieldnames = [
        "connector_name",
        "connector_linkedin",
        "target_name",
        "shared_signal",
        "draft_subject",
        "draft_body",
        "score",
        "status",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Draft warm intro ask messages for scored connectors"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to scored connectors CSV (output from warm-intro-scoring/lookup.py)",
    )
    parser.add_argument(
        "--output",
        default="ask_drafts.csv",
        help="Path for output drafts CSV (default: ask_drafts.csv)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Only draft messages for the top N connectors by score",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Deepline API key (default: DEEPLINE_API_KEY env var or .env file)",
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5",
        help="Model to use for drafting (default: claude-haiku-4-5)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress per connector",
    )

    args = parser.parse_args()

    api_key = resolve_api_key(args.api_key)
    rows = load_scored_csv(args.input)

    print(f"Loaded {len(rows)} connectors from {args.input}")
    if args.top:
        print(f"Processing top {args.top} by score")

    output_rows = draft_asks(
        rows=rows,
        api_key=api_key,
        top=args.top,
        model=args.model,
        verbose=args.verbose,
    )

    ok_count = sum(1 for r in output_rows if r["status"] == "ok")
    error_count = len(output_rows) - ok_count

    write_output_csv(output_rows, args.output)

    print(f"\nWrote {len(output_rows)} rows to {args.output}")
    print(f"  Drafted: {ok_count}")
    if error_count:
        print(f"  Errors:  {error_count} (rows have empty draft_body — review before sending)")


if __name__ == "__main__":
    main()
