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


_OFFICE_HOURS_DIR = Path(__file__).resolve().parent.parent
if str(_OFFICE_HOURS_DIR) not in sys.path:
    sys.path.insert(0, str(_OFFICE_HOURS_DIR))

from warm_intro_contract import build_path_id  # noqa: E402


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
- Use only the facts supplied in the prompt. Do not invent personal history.
- If target context or permissionless value is marked not supplied, omit it rather than inventing it.
- A proximity signal does not prove that the connector and target know each other. Never claim that it does.
- The subject line should be under 8 words. Format: "Intro to {target_name}?" or "Quick intro ask — {target_name}" or similar. Short.

Output format (strict JSON, nothing else):
{"subject": "...", "body": "..."}"""

ASK_USER_TEMPLATE = """Draft a warm intro ask for me to send to my connector.

Connector: {connector_name} (currently at {connector_company})
Target: {target_name}, {target_title} at {target_company}
Verified path reason: {signal_description}
Why the target may care: {why_target_cares}
Permissionless value to offer: {permissionless_value}

Return JSON only."""


# ── CSV helpers ──────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {
    "campaign_id",
    "owner_id",
    "connector_id",
    "target_id",
    "path_id",
    "connector_name",
    "connector_linkedin",
    "connector_company",
    "target_name",
    "target_title",
    "target_company",
    "shared_signal",
    "shared_detail",
    "relationship_confidence",
    "direct_intro_score",
    "work_overlap_score",
    "relationship_score",
    "school_city_community_score",
    "role_industry_score",
    "investor_score",
    "total_score",
    "segment",
    "evidence_ids",
}

OPTIONAL_COLUMNS = {
    "why_target_cares",
    "permissionless_value",
    "reviewed_override",
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

    identity_columns = ("campaign_id", "owner_id", "connector_id", "target_id", "path_id")
    for row_number, row in enumerate(rows, 2):
        blank = [name for name in identity_columns if not row.get(name, "").strip()]
        if blank:
            sys.exit(
                f"Input CSV row {row_number} has blank identity fields: "
                f"{', '.join(blank)}"
            )
        expected_path_id = build_path_id(
            row["campaign_id"],
            row["owner_id"],
            row["connector_id"],
            row["target_id"],
        )
        if row["path_id"].strip() != expected_path_id:
            sys.exit(
                f"Input CSV row {row_number} path_id does not match its "
                "campaign/owner/connector/target identity"
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

    def has_score(field: str) -> bool:
        try:
            return float(row.get(field, 0) or 0) > 0
        except (TypeError, ValueError):
            return False

    score_priority = (
        ("direct_introduction", "direct_intro_score"),
        ("dated_work_overlap", "work_overlap_score"),
        ("school_city_community", "school_city_community_score"),
        ("role_industry", "role_industry_score"),
        ("investor_overlap", "investor_score"),
    )
    selected_signal = next(
        (candidate for candidate, field in score_priority if has_score(field)),
        "dated_work_overlap" if signal_type == "verified_work_overlap" else signal_type,
    )
    detail_matches_selection = signal_type == selected_signal or (
        signal_type == "verified_work_overlap" and selected_signal == "dated_work_overlap"
    )

    if selected_signal == "direct_introduction":
        evidence_detail = (
            detail
            if detail_matches_selection
            else str(row.get("evidence_ids", "") or "").strip()
        )
        evidence = f" ({evidence_detail})" if evidence_detail else ""
        return (
            f"A confirmed direct-introduction evidence record{evidence} supports asking "
            f"{connector} for an introduction to {target}."
        )
    if selected_signal == "dated_work_overlap" and detail_matches_selection and detail:
        return f"{connector} and {target} have a verified dated work overlap: {detail}."
    if selected_signal == "dated_work_overlap":
        return f"{connector} and {target} have a verified dated work overlap."
    if selected_signal == "school_city_community" and detail_matches_selection and detail:
        return (
            f"{connector} and {target} share school, city, community, or appearance "
            f"proximity ({detail}); this does not establish that they know each other."
        )
    if selected_signal == "school_city_community":
        return (
            f"{connector} and {target} have school, city, community, or appearance "
            "proximity; this does not establish that they know each other."
        )
    if selected_signal == "role_industry" and detail_matches_selection and detail:
        return (
            f"{connector} and {target} have role or industry proximity ({detail}); "
            "this does not establish that they know each other."
        )
    if selected_signal == "role_industry":
        return (
            f"{connector} and {target} have role or industry proximity; this does not "
            "establish that they know each other."
        )
    if selected_signal == "investor_overlap" and detail_matches_selection and detail:
        return (
            f"{connector} and {target} share investor context ({detail}); this does not "
            "establish that they know each other."
        )
    if selected_signal == "investor_overlap":
        return (
            f"{connector} and {target} share investor context; this does not establish "
            "that they know each other."
        )
    if selected_signal == "company_proximity" and detail:
        return (
            f"{connector} and {target} have employer proximity ({detail}); this does not "
            "confirm overlapping dates or that they know each other."
        )
    if selected_signal == "company_proximity":
        return (
            f"{connector} and {target} have employer proximity; this does not confirm "
            "overlapping dates or that they know each other."
        )
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
    allow_reviewed: bool = False,
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
    draftable_rows: list[dict] = []
    for row in rows:
        blank_identity = [
            name
            for name in ("campaign_id", "owner_id", "connector_id", "target_id", "path_id")
            if not str(row.get(name, "") or "").strip()
        ]
        if blank_identity:
            raise ValueError(
                "scored path has blank identity fields: " + ", ".join(blank_identity)
            )
        expected_path_id = build_path_id(
            row["campaign_id"],
            row["owner_id"],
            row["connector_id"],
            row["target_id"],
        )
        if row["path_id"].strip() != expected_path_id:
            raise ValueError(
                "scored path_id does not match campaign/owner/connector/target identity"
            )
        segment = str(row.get("segment", "") or "").strip()
        if segment == "strong_warm_intro":
            draftable_rows.append(row)
        elif (
            segment == "review_warm_intro"
            and allow_reviewed
            and str(row.get("reviewed_override", "") or "").strip().casefold()
            == "true"
        ):
            draftable_rows.append(row)
        elif segment == "no_strong_path":
            if verbose:
                print(
                    f"Routing {row.get('path_id', '<missing>')} to direct outreach; "
                    "no warm ask will be drafted."
                )
        elif verbose:
            print(
                f"Holding {row.get('path_id', '<missing>')} for explicit evidence review."
            )

    # Sort eligible rows by score descending, then cap the drafted set.
    sorted_rows = sorted(
        draftable_rows,
        key=lambda r: float(r.get("total_score", 0) or 0),
        reverse=True,
    )
    if top is not None:
        sorted_rows = sorted_rows[:top]

    output_rows: list[dict] = []

    for i, row in enumerate(sorted_rows, 1):
        connector_name = row["connector_name"].strip()
        connector_linkedin = row["connector_linkedin"].strip()
        connector_company = row.get("connector_company", "").strip() or "their company"
        target_name = row["target_name"].strip()
        target_title = row["target_title"].strip()
        target_company = row["target_company"].strip()
        total_score = row.get("total_score", "")
        why_target_cares = row.get("why_target_cares", "").strip()
        permissionless_value = row.get("permissionless_value", "").strip()

        signal_description = build_signal_description(row)

        user_message = ASK_USER_TEMPLATE.format(
            connector_name=connector_name,
            connector_company=connector_company,
            target_name=target_name,
            target_title=target_title,
            target_company=target_company,
            signal_description=signal_description,
            why_target_cares=why_target_cares or "Not supplied; do not invent one.",
            permissionless_value=permissionless_value or "Not supplied; do not invent one.",
        )

        if verbose:
            print(
                f"[{i}/{len(sorted_rows)}] Drafting ask for {connector_name} → {target_name} "
                f"(score: {total_score})"
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
                "campaign_id": row["campaign_id"].strip(),
                "owner_id": row["owner_id"].strip(),
                "connector_id": row["connector_id"].strip(),
                "target_id": row["target_id"].strip(),
                "path_id": row["path_id"].strip(),
                "connector_name": connector_name,
                "connector_linkedin": connector_linkedin,
                "target_name": target_name,
                "target_title": target_title,
                "target_company": target_company,
                "shared_signal": row.get("shared_signal", ""),
                "shared_detail": row.get("shared_detail", ""),
                "why_target_cares": why_target_cares,
                "permissionless_value": permissionless_value,
                "draft_subject": subject,
                "draft_body": body,
                "total_score": total_score,
                "segment": row["segment"].strip(),
                "reviewed_override": row.get("reviewed_override", "false").strip()
                or "false",
                "approved": "false",
                "message_version": "1",
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
        "campaign_id",
        "owner_id",
        "connector_id",
        "target_id",
        "path_id",
        "connector_name",
        "connector_linkedin",
        "target_name",
        "target_title",
        "target_company",
        "shared_signal",
        "shared_detail",
        "why_target_cares",
        "permissionless_value",
        "draft_subject",
        "draft_body",
        "total_score",
        "segment",
        "reviewed_override",
        "approved",
        "message_version",
        "status",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
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
    parser.add_argument(
        "--allow-reviewed",
        action="store_true",
        help=(
            "Draft review_warm_intro rows only when their reviewed_override column "
            "is also true"
        ),
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
        allow_reviewed=args.allow_reviewed,
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
