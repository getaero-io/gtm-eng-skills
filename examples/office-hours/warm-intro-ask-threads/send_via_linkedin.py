"""Send warm intro ask messages via LinkedIn using Apify.

Takes the draft CSV from draft_asks.py and sends each message to the
connector's LinkedIn profile via the Apify linkedin-message-sender actor.

# WARNING: LinkedIn automation carries ToS risk.
# - Use a warmed account (6+ months old, regular organic activity).
# - Run at human pace. Suggested max: 10 messages per day.
# - Space sends at least 60 seconds apart.
# - Do not run this from a datacenter IP — use residential or your own IP.
# - Monitor your account for "Unusual activity" warnings; stop immediately if flagged.

Usage:
    python send_via_linkedin.py --input ask_drafts.csv --dry-run
    python send_via_linkedin.py --input ask_drafts.csv --limit 5
    python send_via_linkedin.py --input ask_drafts.csv --limit 10 --skip-sent
"""
import argparse
import csv
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Constants ────────────────────────────────────────────────────────────────

# Apify actor for LinkedIn messaging.
# curious_coder/linkedin-message-sender is the canonical actor for DM sends.
# If it becomes unavailable, check Apify store for "linkedin message sender".
APIFY_ACTOR_ID = "curious_coder/linkedin-message-sender"

# Seconds to wait between sends. LinkedIn rate-limits DMs aggressively.
# 90 seconds = ~40 sends/hour max. Stay well below that.
SEND_DELAY_SECONDS = 90

# Default per-run send cap. Operator can raise via --limit, but 10/day is the
# suggested ceiling before ToS risk becomes meaningful.
DEFAULT_LIMIT = 5

LOG_DB_PATH = "send_log.db"


# ── Send log (SQLite) ────────────────────────────────────────────────────────

def init_log_db(db_path: str) -> sqlite3.Connection:
    """Initialize the send log database.

    Creates the sends table if it does not exist.

    Args:
        db_path: Path to the SQLite file.

    Returns:
        Open sqlite3 connection.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sends (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at     TEXT NOT NULL,
            connector_linkedin TEXT NOT NULL,
            connector_name     TEXT NOT NULL,
            target_name        TEXT NOT NULL,
            message_preview    TEXT NOT NULL,
            status             TEXT NOT NULL,
            apify_run_id       TEXT,
            error_detail       TEXT
        )
    """)
    conn.commit()
    return conn


def log_send(
    conn: sqlite3.Connection,
    connector_linkedin: str,
    connector_name: str,
    target_name: str,
    message_preview: str,
    status: str,
    apify_run_id: Optional[str] = None,
    error_detail: Optional[str] = None,
) -> None:
    """Insert a send record into the log.

    Args:
        conn: Open sqlite3 connection.
        connector_linkedin: LinkedIn URL of the person messaged.
        connector_name: Display name.
        target_name: The intro target referenced in the message.
        message_preview: First 120 chars of the message body.
        status: "sent", "dry_run", or "error".
        apify_run_id: Apify run ID if available.
        error_detail: Error string if status is "error".
    """
    conn.execute(
        """
        INSERT INTO sends
            (sent_at, connector_linkedin, connector_name, target_name,
             message_preview, status, apify_run_id, error_detail)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            connector_linkedin,
            connector_name,
            target_name,
            message_preview[:120],
            status,
            apify_run_id,
            error_detail,
        ),
    )
    conn.commit()


def already_sent(conn: sqlite3.Connection, connector_linkedin: str) -> bool:
    """Check if a message was already sent to this LinkedIn URL.

    Args:
        conn: Open sqlite3 connection.
        connector_linkedin: LinkedIn URL to check.

    Returns:
        True if a successful send is already logged.
    """
    row = conn.execute(
        "SELECT id FROM sends WHERE connector_linkedin = ? AND status = 'sent' LIMIT 1",
        (connector_linkedin,),
    ).fetchone()
    return row is not None


# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_drafts_csv(path: str) -> list[dict]:
    """Load the ask drafts CSV from draft_asks.py.

    Args:
        path: Path to ask_drafts.csv.

    Returns:
        List of row dicts.

    Raises:
        SystemExit: If file missing, empty, or missing required columns.
    """
    p = Path(path)
    if not p.exists():
        sys.exit(f"Input file not found: {path}")

    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    if not rows:
        sys.exit(f"Input CSV is empty: {path}")

    required = {"connector_linkedin", "connector_name", "target_name", "draft_body"}
    present = set(rows[0].keys())
    missing = required - present
    if missing:
        sys.exit(
            f"Input CSV missing required columns: {', '.join(sorted(missing))}\n"
            f"Run draft_asks.py first to generate ask_drafts.csv."
        )

    # Skip rows with empty draft_body (errored during drafting)
    sendable = [r for r in rows if r.get("draft_body", "").strip()]
    skipped = len(rows) - len(sendable)
    if skipped:
        print(f"Skipping {skipped} rows with empty draft_body (draft errors).")

    return sendable


# ── API key ───────────────────────────────────────────────────────────────────

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


# ── Apify send ────────────────────────────────────────────────────────────────

def send_linkedin_message(
    connector_linkedin: str,
    message_body: str,
    api_key: str,
) -> dict:
    """Send a LinkedIn message via the Deepline apify_run_actor_sync tool.

    Calls `deepline tool run apify_run_actor_sync` via subprocess with the
    curious_coder/linkedin-message-sender actor input.

    Actor input schema (curious_coder/linkedin-message-sender):
        profileUrl: LinkedIn profile URL of the recipient
        message: Message text to send

    Args:
        connector_linkedin: LinkedIn profile URL of the recipient.
        message_body: Message text.
        api_key: Deepline API key.

    Returns:
        Dict with keys: "run_id", "status", "dataset_id".

    Raises:
        RuntimeError: If the Deepline CLI call fails or returns unexpected output.
    """
    actor_input = {
        "profileUrl": connector_linkedin,
        "message": message_body,
    }

    tool_payload = {
        "tool": "apify_run_actor_sync",
        "input": {
            "actorId": APIFY_ACTOR_ID,
            "input": actor_input,
        },
    }

    result = subprocess.run(
        [
            "deepline",
            "tool",
            "run",
            "--body",
            json.dumps(tool_payload),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "DEEPLINE_API_KEY": api_key},
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"deepline tool run failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout[:500]}\n"
            f"stderr: {result.stderr[:500]}"
        )

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not parse deepline tool run output as JSON: {exc}\n"
            f"Raw: {result.stdout[:500]}"
        ) from exc

    run_id = response.get("runId") or response.get("id") or response.get("data", {}).get("id")
    dataset_id = (
        response.get("defaultDatasetId")
        or response.get("data", {}).get("defaultDatasetId")
    )
    status = (
        response.get("status")
        or response.get("data", {}).get("status")
        or "UNKNOWN"
    )

    return {
        "run_id": run_id,
        "status": status,
        "dataset_id": dataset_id,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send warm intro ask messages via LinkedIn (Apify)"
    )
    parser.add_argument(
        "--input",
        default="ask_drafts.csv",
        help="Path to ask_drafts.csv from draft_asks.py (default: ask_drafts.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without calling Apify",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum sends per run (default: {DEFAULT_LIMIT}). Suggested max: 10/day.",
    )
    parser.add_argument(
        "--skip-sent",
        action="store_true",
        help="Skip connectors already in send_log.db with status='sent'",
    )
    parser.add_argument(
        "--log-db",
        default=LOG_DB_PATH,
        help=f"Path to send log SQLite file (default: {LOG_DB_PATH})",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Deepline API key (default: DEEPLINE_API_KEY env var or .env file)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=SEND_DELAY_SECONDS,
        help=f"Seconds between sends (default: {SEND_DELAY_SECONDS})",
    )

    args = parser.parse_args()

    if args.limit > 10:
        print(
            f"WARNING: --limit {args.limit} exceeds the recommended 10/day ceiling. "
            "LinkedIn ToS risk rises sharply above this threshold."
        )

    api_key = resolve_api_key(args.api_key) if not args.dry_run else "dry-run"
    rows = load_drafts_csv(args.input)
    log_conn = init_log_db(args.log_db)

    print(f"Loaded {len(rows)} sendable drafts from {args.input}")
    print(f"Limit: {args.limit} per run | Delay: {args.delay}s | Dry run: {args.dry_run}")
    print()

    sent_count = 0
    skipped_count = 0

    for row in rows:
        if sent_count >= args.limit:
            print(f"Reached send limit ({args.limit}). Stopping.")
            break

        connector_linkedin = row["connector_linkedin"].strip()
        connector_name = row["connector_name"].strip()
        target_name = row["target_name"].strip()
        message_body = row["draft_body"].strip()
        preview = message_body[:80].replace("\n", " ")

        if args.skip_sent and already_sent(log_conn, connector_linkedin):
            print(f"  SKIP (already sent): {connector_name}")
            skipped_count += 1
            continue

        print(f"[{sent_count + 1}/{args.limit}] → {connector_name} ({connector_linkedin})")
        print(f"   Target: {target_name}")
        print(f"   Message: {preview}...")

        if args.dry_run:
            print("   [DRY RUN — not sent]")
            log_send(
                conn=log_conn,
                connector_linkedin=connector_linkedin,
                connector_name=connector_name,
                target_name=target_name,
                message_preview=preview,
                status="dry_run",
            )
            sent_count += 1
            print()
            continue

        try:
            result = send_linkedin_message(
                connector_linkedin=connector_linkedin,
                message_body=message_body,
                api_key=api_key,
            )
            run_id = result.get("run_id")
            apify_status = result.get("status", "UNKNOWN")
            print(f"   Sent. Apify run: {run_id} | status: {apify_status}")

            log_send(
                conn=log_conn,
                connector_linkedin=connector_linkedin,
                connector_name=connector_name,
                target_name=target_name,
                message_preview=preview,
                status="sent",
                apify_run_id=run_id,
            )
            sent_count += 1

        except RuntimeError as exc:
            print(f"   ERROR: {exc}", file=sys.stderr)
            log_send(
                conn=log_conn,
                connector_linkedin=connector_linkedin,
                connector_name=connector_name,
                target_name=target_name,
                message_preview=preview,
                status="error",
                error_detail=str(exc)[:500],
            )

        print()

        # Delay between sends (skip after last send)
        if sent_count < args.limit and sent_count < len(rows):
            print(f"   Waiting {args.delay}s before next send...")
            time.sleep(args.delay)

    log_conn.close()

    print(f"Done. Sent: {sent_count} | Skipped: {skipped_count}")
    print(f"Send log: {args.log_db}")

    if not args.dry_run and sent_count > 0:
        print(
            "\nReminder: Do not run this script again today if you're near the 10/day ceiling. "
            "Check send_log.db for your daily count."
        )


if __name__ == "__main__":
    main()
