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
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
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

# Default per-run send cap. The CLI enforces a hard 10-send rolling-day ceiling.
DEFAULT_LIMIT = 5
MAX_DAILY_SENDS = 10
MIN_LIVE_DELAY_SECONDS = 60

LOG_DB_PATH = "send_log.db"
CHANNEL = "linkedin"
TERMINAL_SUCCESS_STATUSES = {"SUCCEEDED"}
PENDING_TTL_SECONDS = 60 * 60


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
            error_detail       TEXT,
            idempotency_key    TEXT,
            reservation_owner  TEXT,
            reservation_updated_at TEXT
        )
    """)
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(sends)").fetchall()
    }
    if "idempotency_key" not in columns:
        conn.execute("ALTER TABLE sends ADD COLUMN idempotency_key TEXT")
    if "reservation_owner" not in columns:
        conn.execute("ALTER TABLE sends ADD COLUMN reservation_owner TEXT")
    if "reservation_updated_at" not in columns:
        conn.execute("ALTER TABLE sends ADD COLUMN reservation_updated_at TEXT")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS sends_idempotency_key_uq
        ON sends(idempotency_key)
        WHERE idempotency_key IS NOT NULL
        """
    )
    conn.commit()
    return conn


def build_idempotency_key(path_id: str, channel: str, message_version: str) -> str:
    """Build the stable activation identity for one message version."""
    raw = "|".join((path_id.strip(), channel.strip(), message_version.strip()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def reserve_send(
    conn: sqlite3.Connection,
    idempotency_key: str,
    owner_token: str,
    connector_linkedin: str,
    connector_name: str,
    target_name: str,
    message_preview: str,
    now: Optional[datetime] = None,
) -> bool:
    """Atomically reserve one message version before any external side effect."""
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    reserved_at = current_time.isoformat()
    stale_before = current_time - timedelta(seconds=PENDING_TTL_SECONDS)
    window_cutoff = current_time - timedelta(hours=24)
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            "SELECT status, reservation_updated_at FROM sends WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            can_retry = existing["status"] == "error"
            if existing["status"] == "pending":
                updated_at = existing["reservation_updated_at"]
                can_retry = updated_at is None or datetime.fromisoformat(
                    updated_at
                ) < stale_before
            if not can_retry:
                conn.rollback()
                return False
        capacity_in_use = conn.execute(
            """
            SELECT COUNT(*) AS reservation_count
            FROM sends
            WHERE (status = 'sent' AND julianday(sent_at) >= julianday(?))
               OR (status = 'pending' AND julianday(reservation_updated_at) >= julianday(?))
            """,
            (window_cutoff.isoformat(), stale_before.isoformat()),
        ).fetchone()["reservation_count"]
        if capacity_in_use >= MAX_DAILY_SENDS:
            conn.rollback()
            return False
        if existing is not None:
            conn.execute(
                """
                UPDATE sends
                SET sent_at = ?, connector_linkedin = ?, connector_name = ?,
                    target_name = ?, message_preview = ?, status = 'pending',
                    apify_run_id = NULL, error_detail = NULL,
                    reservation_owner = ?, reservation_updated_at = ?
                WHERE idempotency_key = ?
                """,
                (
                    reserved_at,
                    connector_linkedin,
                    connector_name,
                    target_name,
                    message_preview[:120],
                    owner_token,
                    reserved_at,
                    idempotency_key,
                ),
            )
            conn.commit()
            return True
        conn.execute(
            """
            INSERT INTO sends
                (sent_at, connector_linkedin, connector_name, target_name,
                 message_preview, status, idempotency_key, reservation_owner,
                 reservation_updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (
                reserved_at,
                connector_linkedin,
                connector_name,
                target_name,
                message_preview[:120],
                idempotency_key,
                owner_token,
                reserved_at,
            ),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise


def finish_reserved_send(
    conn: sqlite3.Connection,
    idempotency_key: str,
    owner_token: str,
    actor_status: str,
    apify_run_id: Optional[str] = None,
    error_detail: Optional[str] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Finish an owned reservation as sent or retryable error."""
    completed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    succeeded = is_terminal_success(actor_status)
    status = "sent" if succeeded else "error"
    detail = None if succeeded else (error_detail or f"Apify actor status: {actor_status}")
    cursor = conn.execute(
        """
        UPDATE sends
        SET sent_at = ?, status = ?, apify_run_id = ?, error_detail = ?,
            reservation_owner = NULL, reservation_updated_at = ?
        WHERE idempotency_key = ? AND status = 'pending' AND reservation_owner = ?
        """,
        (
            completed_at,
            status,
            apify_run_id,
            detail,
            completed_at,
            idempotency_key,
            owner_token,
        ),
    )
    if cursor.rowcount != 1:
        conn.rollback()
        raise RuntimeError("send reservation is no longer owned by this process")
    conn.commit()
    return succeeded


def log_send(
    conn: sqlite3.Connection,
    connector_linkedin: str,
    connector_name: str,
    target_name: str,
    message_preview: str,
    status: str,
    apify_run_id: Optional[str] = None,
    error_detail: Optional[str] = None,
    idempotency_key: Optional[str] = None,
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
        idempotency_key: Stable path/channel/version key. It is persisted only for
            successful live sends so previews and errors remain retryable.
    """
    conn.execute(
        """
        INSERT INTO sends
            (sent_at, connector_linkedin, connector_name, target_name,
            message_preview, status, apify_run_id, error_detail, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            idempotency_key if status == "sent" else None,
        ),
    )
    conn.commit()


def already_sent(conn: sqlite3.Connection, idempotency_key: str) -> bool:
    """Check if this path/channel/message version was already sent.

    Args:
        conn: Open sqlite3 connection.
        idempotency_key: Stable activation key to check.

    Returns:
        True if a successful send is already logged.
    """
    row = conn.execute(
        "SELECT id FROM sends WHERE idempotency_key = ? AND status = 'sent' LIMIT 1",
        (idempotency_key,),
    ).fetchone()
    return row is not None


def successful_sends_in_rolling_window(
    conn: sqlite3.Connection,
    now: Optional[datetime] = None,
) -> int:
    """Count successful live sends in the preceding 24 hours."""
    cutoff = (now or datetime.now(timezone.utc)).astimezone(timezone.utc) - timedelta(
        hours=24
    )
    row = conn.execute(
        """
        SELECT COUNT(*) AS send_count
        FROM sends
        WHERE status = 'sent' AND julianday(sent_at) >= julianday(?)
        """,
        (cutoff.isoformat(),),
    ).fetchone()
    return int(row["send_count"])


def is_terminal_success(actor_status: str) -> bool:
    """Return true only for an explicit terminal actor success."""
    return str(actor_status or "").strip().upper() in TERMINAL_SUCCESS_STATUSES


# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_drafts_csv(path: str, require_approved: bool = True) -> list[dict]:
    """Load the ask drafts CSV from draft_asks.py.

    Args:
        path: Path to ask_drafts.csv.
        require_approved: When true, include only rows explicitly marked approved.

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

    required = {
        "path_id",
        "connector_linkedin",
        "connector_name",
        "target_name",
        "draft_body",
        "approved",
        "message_version",
    }
    present = set(rows[0].keys())
    missing = required - present
    if missing:
        sys.exit(
            f"Input CSV missing required columns: {', '.join(sorted(missing))}\n"
            f"Run draft_asks.py first to generate ask_drafts.csv."
        )

    # Empty or unapproved drafts are never in the live-sendable set.
    sendable = [
        row
        for row in rows
        if row.get("draft_body", "").strip()
        and (
            not require_approved
            or row.get("approved", "").strip().casefold() == "true"
        )
    ]
    skipped = len(rows) - len(sendable)
    if skipped:
        reason = "empty or unapproved drafts" if require_approved else "empty drafts"
        print(f"Skipping {skipped} {reason}.")

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
        help=(
            f"Maximum sends per run (default: {DEFAULT_LIMIT}; "
            f"hard rolling-day ceiling: {MAX_DAILY_SENDS})"
        ),
    )
    parser.add_argument(
        "--skip-sent",
        action="store_true",
        help="Deprecated compatibility flag; duplicate message versions are always skipped",
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

    if not 1 <= args.limit <= MAX_DAILY_SENDS:
        parser.error(f"--limit must be between 1 and {MAX_DAILY_SENDS}")
    if not args.dry_run and args.delay < MIN_LIVE_DELAY_SECONDS:
        parser.error(
            f"--delay must be at least {MIN_LIVE_DELAY_SECONDS} seconds for live sends"
        )

    api_key = resolve_api_key(args.api_key) if not args.dry_run else "dry-run"
    rows = load_drafts_csv(args.input, require_approved=not args.dry_run)
    log_conn = init_log_db(args.log_db)
    recent_successes = (
        0 if args.dry_run else successful_sends_in_rolling_window(log_conn)
    )
    remaining_capacity = max(0, MAX_DAILY_SENDS - recent_successes)
    run_limit = args.limit if args.dry_run else min(args.limit, remaining_capacity)

    print(f"Loaded {len(rows)} sendable drafts from {args.input}")
    print(f"Limit: {run_limit} per run | Delay: {args.delay}s | Dry run: {args.dry_run}")
    if not args.dry_run:
        print(
            f"Rolling 24h successes: {recent_successes}/{MAX_DAILY_SENDS} "
            f"| Remaining capacity: {remaining_capacity}"
        )
    print()

    sent_count = 0
    attempted_count = 0
    skipped_count = 0

    for row_index, row in enumerate(rows):
        if attempted_count >= run_limit:
            print(f"Reached send limit ({run_limit}). Stopping.")
            break

        connector_linkedin = row["connector_linkedin"].strip()
        connector_name = row["connector_name"].strip()
        target_name = row["target_name"].strip()
        message_body = row["draft_body"].strip()
        idempotency_key = build_idempotency_key(
            row["path_id"], CHANNEL, row["message_version"]
        )
        preview = message_body[:80].replace("\n", " ")

        if args.dry_run and already_sent(log_conn, idempotency_key):
            print(f"  SKIP (message version already sent): {connector_name}")
            skipped_count += 1
            continue

        print(f"[{attempted_count + 1}/{run_limit}] → {connector_name} ({connector_linkedin})")
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
                idempotency_key=idempotency_key,
            )
            attempted_count += 1
            sent_count += 1
            print()
            continue

        owner_token = uuid.uuid4().hex
        if not reserve_send(
            conn=log_conn,
            idempotency_key=idempotency_key,
            owner_token=owner_token,
            connector_linkedin=connector_linkedin,
            connector_name=connector_name,
            target_name=target_name,
            message_preview=preview,
        ):
            print(f"   SKIP (sent or reserved by another process): {connector_name}")
            skipped_count += 1
            print()
            continue

        attempted_count += 1

        try:
            result = send_linkedin_message(
                connector_linkedin=connector_linkedin,
                message_body=message_body,
                api_key=api_key,
            )
            run_id = result.get("run_id")
            apify_status = result.get("status", "UNKNOWN")
            if not is_terminal_success(apify_status):
                print(
                    f"   ERROR: Apify run {run_id} ended with status {apify_status}",
                    file=sys.stderr,
                )
                finish_reserved_send(
                    conn=log_conn,
                    idempotency_key=idempotency_key,
                    owner_token=owner_token,
                    actor_status=apify_status,
                    apify_run_id=run_id,
                    error_detail=f"Apify actor status: {apify_status}",
                )
            else:
                finish_reserved_send(
                    conn=log_conn,
                    idempotency_key=idempotency_key,
                    owner_token=owner_token,
                    actor_status=apify_status,
                    apify_run_id=run_id,
                )
                print(f"   Sent. Apify run: {run_id} | status: {apify_status}")
                sent_count += 1

        except RuntimeError as exc:
            print(f"   ERROR: {exc}", file=sys.stderr)
            row = log_conn.execute(
                "SELECT status, reservation_owner FROM sends WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is not None and row["status"] == "pending" and row["reservation_owner"] == owner_token:
                finish_reserved_send(
                    conn=log_conn,
                    idempotency_key=idempotency_key,
                    owner_token=owner_token,
                    actor_status="ERROR",
                    error_detail=str(exc)[:500],
                )

        print()

        # Delay between sends (skip after last send)
        if attempted_count < run_limit and row_index + 1 < len(rows):
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
