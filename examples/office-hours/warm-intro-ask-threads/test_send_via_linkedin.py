"""Behavior tests for approval-gated, idempotent LinkedIn activation."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent


def load_module():
    spec = importlib.util.spec_from_file_location(
        "send_via_linkedin", HERE / "send_via_linkedin.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_drafts(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "path_id",
        "connector_name",
        "connector_linkedin",
        "target_name",
        "draft_body",
        "approved",
        "message_version",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class ApprovalGateTests(unittest.TestCase):
    def test_unapproved_rows_are_excluded_from_live_sendable_set(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.csv"
            write_drafts(
                path,
                [
                    {
                        "path_id": "path-review",
                        "connector_name": "Casey Morgan",
                        "connector_linkedin": "https://linkedin.example/in/casey-morgan",
                        "target_name": "Mina Sol",
                        "draft_body": "Would you introduce me to Mina?",
                        "approved": "false",
                        "message_version": "1",
                    }
                ],
            )

            rows = module.load_drafts_csv(str(path), require_approved=True)

        self.assertEqual(rows, [])

    def test_approved_row_is_accepted_for_live_send(self):
        module = load_module()
        approved = {
            "path_id": "path-approved",
            "connector_name": "Avery Stone",
            "connector_linkedin": "https://linkedin.example/in/avery-stone",
            "target_name": "Nora Imani",
            "draft_body": "Would you introduce me to Nora?",
            "approved": "TRUE",
            "message_version": "2",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.csv"
            write_drafts(path, [approved])

            rows = module.load_drafts_csv(str(path), require_approved=True)

        self.assertEqual(rows, [approved])

    def test_dry_run_loading_can_preview_unapproved_rows(self):
        module = load_module()
        draft = {
            "path_id": "path-preview",
            "connector_name": "Riley Chen",
            "connector_linkedin": "https://linkedin.example/in/riley-chen",
            "target_name": "Tariq Fen",
            "draft_body": "Would you introduce me to Tariq?",
            "approved": "false",
            "message_version": "1",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.csv"
            write_drafts(path, [draft])

            rows = module.load_drafts_csv(str(path), require_approved=False)

        self.assertEqual(rows, [draft])


class IdempotencyTests(unittest.TestCase):
    def test_repeat_key_is_detected_independently_of_connector_url_format(self):
        module = load_module()
        expected_key = hashlib.sha256(b"path-approved|linkedin|1").hexdigest()
        key = module.build_idempotency_key("path-approved", "linkedin", "1")
        self.assertEqual(key, expected_key)

        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            module.log_send(
                conn=connection,
                connector_linkedin="https://www.linkedin.example/in/avery-stone/",
                connector_name="Avery Stone",
                target_name="Nora Imani",
                message_preview="Would you introduce me to Nora?",
                status="sent",
                idempotency_key=key,
            )

            differently_formatted_url = "linkedin.example/in/avery-stone"
            retry_key = module.build_idempotency_key("path-approved", "linkedin", "1")
            self.assertNotEqual(
                differently_formatted_url,
                "https://www.linkedin.example/in/avery-stone/",
            )
            self.assertTrue(module.already_sent(connection, retry_key))
            connection.close()

    def test_two_connections_cannot_reserve_the_same_key_at_fresh_ttl_boundary(self):
        module = load_module()
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "sends.db"
            first = module.init_log_db(str(db_path))
            second = module.init_log_db(str(db_path))
            key = module.build_idempotency_key("path-atomic", "linkedin", "1")
            details = {
                "idempotency_key": key,
                "connector_linkedin": "https://linkedin.example/in/casey-morgan",
                "connector_name": "Casey Morgan",
                "target_name": "Mina Sol",
                "message_preview": "Would you introduce me to Mina?",
            }

            self.assertTrue(
                module.reserve_send(
                    first, owner_token="owner-first", now=now, **details
                )
            )
            self.assertFalse(
                module.reserve_send(
                    second,
                    owner_token="owner-second",
                    now=now + timedelta(seconds=module.PENDING_TTL_SECONDS),
                    **details,
                )
            )
            rows = first.execute(
                "SELECT status, reservation_owner FROM sends WHERE idempotency_key = ?",
                (key,),
            ).fetchall()
            first.close()
            second.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            (rows[0]["status"], rows[0]["reservation_owner"]),
            ("pending", "owner-first"),
        )

    def test_stale_pending_reservation_can_be_reclaimed(self):
        module = load_module()
        first_time = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        retry_time = first_time + timedelta(seconds=module.PENDING_TTL_SECONDS + 1)
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            key = module.build_idempotency_key("path-stale", "linkedin", "1")
            details = {
                "conn": connection,
                "idempotency_key": key,
                "connector_linkedin": "https://linkedin.example/in/riley-chen",
                "connector_name": "Riley Chen",
                "target_name": "Tariq Fen",
                "message_preview": "Would you introduce me to Tariq?",
            }
            self.assertTrue(
                module.reserve_send(
                    owner_token="owner-crashed", now=first_time, **details
                )
            )

            self.assertTrue(
                module.reserve_send(
                    owner_token="owner-retry", now=retry_time, **details
                )
            )
            row = connection.execute(
                "SELECT status, reservation_owner FROM sends WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            count = connection.execute(
                "SELECT COUNT(*) FROM sends WHERE idempotency_key = ?", (key,)
            ).fetchone()[0]
            connection.close()

        self.assertEqual(
            (row["status"], row["reservation_owner"]), ("pending", "owner-retry")
        )
        self.assertEqual(count, 1)

    def test_pending_reservation_atomically_consumes_last_daily_slot(self):
        module = load_module()
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "sends.db"
            first = module.init_log_db(str(db_path))
            for number in range(module.MAX_DAILY_SENDS - 1):
                module.log_send(
                    first,
                    connector_linkedin=f"https://linkedin.example/in/prior-{number}",
                    connector_name=f"Prior {number}",
                    target_name="Nora Imani",
                    message_preview="Prior send",
                    status="sent",
                    idempotency_key=module.build_idempotency_key(
                        f"path-prior-capacity-{number}", "linkedin", "1"
                    ),
                )
            second = module.init_log_db(str(db_path))

            common = {
                "connector_linkedin": "https://linkedin.example/in/casey-morgan",
                "connector_name": "Casey Morgan",
                "target_name": "Mina Sol",
                "message_preview": "Would you introduce me to Mina?",
                "now": now,
            }
            self.assertTrue(
                module.reserve_send(
                    first,
                    idempotency_key=module.build_idempotency_key(
                        "path-final-slot", "linkedin", "1"
                    ),
                    owner_token="owner-final-slot",
                    **common,
                )
            )
            self.assertFalse(
                module.reserve_send(
                    second,
                    idempotency_key=module.build_idempotency_key(
                        "path-over-capacity", "linkedin", "1"
                    ),
                    owner_token="owner-over-capacity",
                    **common,
                )
            )
            first.close()
            second.close()

    def test_existing_log_is_migrated_with_a_unique_idempotency_index(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "legacy.db"
            legacy = sqlite3.connect(db_path)
            legacy.execute(
                """
                CREATE TABLE sends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sent_at TEXT NOT NULL,
                    connector_linkedin TEXT NOT NULL,
                    connector_name TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    message_preview TEXT NOT NULL,
                    status TEXT NOT NULL,
                    apify_run_id TEXT,
                    error_detail TEXT
                )
                """
            )
            legacy.commit()
            legacy.close()

            migrated = module.init_log_db(str(db_path))
            columns = {
                row["name"] for row in migrated.execute("PRAGMA table_info(sends)")
            }
            indexes = {
                row["name"]: row["unique"]
                for row in migrated.execute("PRAGMA index_list(sends)")
            }
            migrated.close()

        self.assertTrue(
            {
                "idempotency_key",
                "reservation_owner",
                "reservation_updated_at",
            }.issubset(columns)
        )
        self.assertEqual(indexes["sends_idempotency_key_uq"], 1)

    def test_dry_run_log_does_not_block_a_later_live_send(self):
        module = load_module()
        key = module.build_idempotency_key("path-preview", "linkedin", "1")
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            common = {
                "conn": connection,
                "connector_linkedin": "https://linkedin.example/in/riley-chen",
                "connector_name": "Riley Chen",
                "target_name": "Tariq Fen",
                "message_preview": "Would you introduce me to Tariq?",
                "idempotency_key": key,
            }
            module.log_send(status="dry_run", **common)
            self.assertFalse(module.already_sent(connection, key))

            module.log_send(status="sent", **common)
            self.assertTrue(module.already_sent(connection, key))
            connection.close()


class ActivationIntegrationTests(unittest.TestCase):
    def assert_actor_status_is_retryable(self, actor_status):
        module = load_module()
        path_id = f"path-{actor_status.casefold().replace('_', '-')}"
        row = {
            "path_id": path_id,
            "connector_name": "Casey Morgan",
            "connector_linkedin": "https://linkedin.example/in/casey-morgan",
            "target_name": "Mina Sol",
            "draft_body": "Would you introduce me to Mina?",
            "approved": "true",
            "message_version": "1",
        }
        module.send_linkedin_message = lambda **_kwargs: {
            "run_id": f"run-{actor_status.casefold()}",
            "status": actor_status,
        }

        with tempfile.TemporaryDirectory() as directory:
            drafts_path = Path(directory) / "drafts.csv"
            log_path = Path(directory) / "sends.db"
            write_drafts(drafts_path, [row])
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--api-key",
                "example-key",
                "--delay",
                "60",
                "--log-db",
                str(log_path),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                module.main()

            connection = module.init_log_db(str(log_path))
            key = module.build_idempotency_key(path_id, "linkedin", "1")
            self.assertFalse(module.already_sent(connection, key))
            lifecycle = connection.execute(
                "SELECT status, COUNT(*) AS row_count FROM sends WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            self.assertEqual(
                (lifecycle["status"], lifecycle["row_count"]), ("error", 1)
            )
            self.assertTrue(
                module.reserve_send(
                    connection,
                    idempotency_key=key,
                    owner_token="retry-owner",
                    connector_linkedin=row["connector_linkedin"],
                    connector_name=row["connector_name"],
                    target_name=row["target_name"],
                    message_preview=row["draft_body"],
                )
            )
            count_after_retry = connection.execute(
                "SELECT COUNT(*) FROM sends WHERE idempotency_key = ?", (key,)
            ).fetchone()[0]
            connection.close()

        self.assertEqual(count_after_retry, 1)

    def test_live_activation_sends_only_approved_rows_and_skips_repeat_version(self):
        module = load_module()
        sent_urls = []

        def fake_send(connector_linkedin, message_body, api_key):
            sent_urls.append(connector_linkedin)
            return {"run_id": "run-example", "status": "SUCCEEDED"}

        module.send_linkedin_message = fake_send
        rows = [
            {
                "path_id": "path-review",
                "connector_name": "Casey Morgan",
                "connector_linkedin": "https://linkedin.example/in/casey-morgan",
                "target_name": "Mina Sol",
                "draft_body": "Would you introduce me to Mina?",
                "approved": "false",
                "message_version": "1",
            },
            {
                "path_id": "path-approved",
                "connector_name": "Avery Stone",
                "connector_linkedin": "https://www.linkedin.example/in/avery-stone/",
                "target_name": "Nora Imani",
                "draft_body": "Would you introduce me to Nora?",
                "approved": "true",
                "message_version": "1",
            },
        ]

        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            drafts_path = directory_path / "drafts.csv"
            log_path = directory_path / "sends.db"
            write_drafts(drafts_path, rows)
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--api-key",
                "example-key",
                "--delay",
                "60",
                "--log-db",
                str(log_path),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                module.main()

            rows[1]["connector_linkedin"] = "linkedin.example/in/avery-stone"
            write_drafts(drafts_path, rows)
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                module.main()

            verification = module.init_log_db(str(log_path))
            lifecycle_count = verification.execute(
                "SELECT COUNT(*) FROM sends WHERE idempotency_key = ?",
                (module.build_idempotency_key("path-approved", "linkedin", "1"),),
            ).fetchone()[0]
            verification.close()

        self.assertEqual(sent_urls, ["https://www.linkedin.example/in/avery-stone/"])
        self.assertEqual(lifecycle_count, 1)

    def test_failed_actor_status_does_not_mark_message_sent(self):
        self.assert_actor_status_is_retryable("FAILED")

    def test_aborted_actor_status_does_not_mark_message_sent(self):
        self.assert_actor_status_is_retryable("ABORTED")

    def test_timed_out_actor_status_does_not_mark_message_sent(self):
        self.assert_actor_status_is_retryable("TIMED-OUT")

    def test_unknown_actor_status_does_not_mark_message_sent(self):
        self.assert_actor_status_is_retryable("UNKNOWN")

    def test_main_reserves_key_before_calling_external_actor(self):
        module = load_module()
        row = {
            "path_id": "path-before-side-effect",
            "connector_name": "Avery Stone",
            "connector_linkedin": "https://linkedin.example/in/avery-stone",
            "target_name": "Nora Imani",
            "draft_body": "Would you introduce me to Nora?",
            "approved": "true",
            "message_version": "1",
        }
        competing_reservations = []

        with tempfile.TemporaryDirectory() as directory:
            drafts_path = Path(directory) / "drafts.csv"
            log_path = Path(directory) / "sends.db"
            write_drafts(drafts_path, [row])
            key = module.build_idempotency_key(
                "path-before-side-effect", "linkedin", "1"
            )

            def fake_send(**_kwargs):
                competing = module.init_log_db(str(log_path))
                competing_reservations.append(
                    module.reserve_send(
                        competing,
                        idempotency_key=key,
                        owner_token="competing-process",
                        connector_linkedin=row["connector_linkedin"],
                        connector_name=row["connector_name"],
                        target_name=row["target_name"],
                        message_preview=row["draft_body"],
                    )
                )
                competing.close()
                return {"run_id": "run-success", "status": "SUCCEEDED"}

            module.send_linkedin_message = fake_send
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--api-key",
                "example-key",
                "--delay",
                "60",
                "--log-db",
                str(log_path),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                module.main()

        self.assertEqual(competing_reservations, [False])

    def assert_processing_failure_is_retryable_and_batch_continues(self, first_outcome):
        module = load_module()
        actor_calls = []

        def fake_send(**kwargs):
            actor_calls.append(kwargs)
            if len(actor_calls) == 1:
                if isinstance(first_outcome, Exception):
                    raise first_outcome
                return first_outcome
            return {"run_id": "run-second", "status": "SUCCEEDED"}

        module.send_linkedin_message = fake_send
        module.time.sleep = lambda _seconds: None
        rows = [
            {
                "path_id": f"path-os-error-{number}",
                "connector_name": f"Connector {number}",
                "connector_linkedin": f"https://linkedin.example/in/connector-{number}",
                "target_name": "Nora Imani",
                "draft_body": "Would you introduce me to Nora?",
                "approved": "true",
                "message_version": "1",
            }
            for number in range(2)
        ]

        with tempfile.TemporaryDirectory() as directory:
            drafts_path = Path(directory) / "drafts.csv"
            log_path = Path(directory) / "sends.db"
            write_drafts(drafts_path, rows)
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--api-key",
                "example-key",
                "--limit",
                "2",
                "--delay",
                "60",
                "--log-db",
                str(log_path),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                module.main()

            connection = module.init_log_db(str(log_path))
            failed_key = module.build_idempotency_key(
                "path-os-error-0", "linkedin", "1"
            )
            later_key = module.build_idempotency_key("path-os-error-1", "linkedin", "1")
            failed = connection.execute(
                "SELECT status, reservation_owner FROM sends WHERE idempotency_key = ?",
                (failed_key,),
            ).fetchone()
            self.assertEqual(
                (failed["status"], failed["reservation_owner"]), ("error", None)
            )
            self.assertTrue(
                module.reserve_send(
                    connection,
                    idempotency_key=failed_key,
                    owner_token="immediate-retry",
                    connector_linkedin=rows[0]["connector_linkedin"],
                    connector_name=rows[0]["connector_name"],
                    target_name=rows[0]["target_name"],
                    message_preview=rows[0]["draft_body"],
                )
            )
            self.assertTrue(module.already_sent(connection, later_key))
            connection.close()

        self.assertEqual(len(actor_calls), 2)

    def test_file_not_found_actor_failure_is_retryable_and_batch_continues(self):
        self.assert_processing_failure_is_retryable_and_batch_continues(
            FileNotFoundError("deepline executable not found")
        )

    def test_malformed_actor_result_is_retryable_and_batch_continues(self):
        self.assert_processing_failure_is_retryable_and_batch_continues(None)

    def test_process_control_exceptions_are_not_swallowed(self):
        for exception in (KeyboardInterrupt(), SystemExit(7)):
            with self.subTest(exception=type(exception).__name__):
                module = load_module()

                def raise_process_control(**_kwargs):
                    raise exception

                module.send_linkedin_message = raise_process_control
                row = {
                    "path_id": f"path-{type(exception).__name__.casefold()}",
                    "connector_name": "Avery Stone",
                    "connector_linkedin": "https://linkedin.example/in/avery-stone",
                    "target_name": "Nora Imani",
                    "draft_body": "Would you introduce me to Nora?",
                    "approved": "true",
                    "message_version": "1",
                }
                with tempfile.TemporaryDirectory() as directory:
                    drafts_path = Path(directory) / "drafts.csv"
                    log_path = Path(directory) / "sends.db"
                    write_drafts(drafts_path, [row])
                    argv = [
                        "send_via_linkedin.py",
                        "--input",
                        str(drafts_path),
                        "--api-key",
                        "example-key",
                        "--delay",
                        "60",
                        "--log-db",
                        str(log_path),
                    ]
                    with (
                        patch.object(sys, "argv", argv),
                        redirect_stdout(io.StringIO()),
                        redirect_stderr(io.StringIO()),
                        self.assertRaises(type(exception)),
                    ):
                        module.main()

                    connection = module.init_log_db(str(log_path))
                    key = module.build_idempotency_key(row["path_id"], "linkedin", "1")
                    status = connection.execute(
                        "SELECT status FROM sends WHERE idempotency_key = ?", (key,)
                    ).fetchone()["status"]
                    connection.close()

                self.assertEqual(status, "pending")


class RatePolicyTests(unittest.TestCase):
    def test_limit_above_ten_is_rejected(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            drafts_path = Path(directory) / "drafts.csv"
            write_drafts(
                drafts_path,
                [
                    {
                        "path_id": "path-rate",
                        "connector_name": "Avery Stone",
                        "connector_linkedin": "https://linkedin.example/in/avery-stone",
                        "target_name": "Nora Imani",
                        "draft_body": "Would you introduce me to Nora?",
                        "approved": "true",
                        "message_version": "1",
                    }
                ],
            )
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--api-key",
                "example-key",
                "--limit",
                "11",
                "--delay",
                "60",
                "--log-db",
                str(Path(directory) / "sends.db"),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                module.main()

        self.assertEqual(raised.exception.code, 2)

    def test_live_delay_below_sixty_seconds_is_rejected_before_actor_call(self):
        module = load_module()
        actor_calls = []
        module.send_linkedin_message = lambda **kwargs: actor_calls.append(kwargs)
        with tempfile.TemporaryDirectory() as directory:
            drafts_path = Path(directory) / "drafts.csv"
            write_drafts(
                drafts_path,
                [
                    {
                        "path_id": "path-delay",
                        "connector_name": "Casey Morgan",
                        "connector_linkedin": "https://linkedin.example/in/casey-morgan",
                        "target_name": "Mina Sol",
                        "draft_body": "Would you introduce me to Mina?",
                        "approved": "true",
                        "message_version": "1",
                    }
                ],
            )
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--api-key",
                "example-key",
                "--delay",
                "59",
                "--log-db",
                str(Path(directory) / "sends.db"),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                module.main()

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(actor_calls, [])

    def test_dry_run_allows_zero_delay(self):
        module = load_module()
        actor_calls = []
        module.send_linkedin_message = lambda **kwargs: actor_calls.append(kwargs)
        with tempfile.TemporaryDirectory() as directory:
            drafts_path = Path(directory) / "drafts.csv"
            write_drafts(
                drafts_path,
                [
                    {
                        "path_id": "path-preview-rate",
                        "connector_name": "Riley Chen",
                        "connector_linkedin": "https://linkedin.example/in/riley-chen",
                        "target_name": "Tariq Fen",
                        "draft_body": "Would you introduce me to Tariq?",
                        "approved": "false",
                        "message_version": "1",
                    }
                ],
            )
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--dry-run",
                "--delay",
                "0",
                "--log-db",
                str(Path(directory) / "sends.db"),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                module.main()

        self.assertEqual(actor_calls, [])

    def test_rolling_twenty_four_hour_success_ceiling_blocks_eleventh_send(self):
        module = load_module()
        actor_calls = []
        module.send_linkedin_message = lambda **kwargs: actor_calls.append(kwargs) or {
            "run_id": "run-eleven",
            "status": "SUCCEEDED",
        }
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            log_path = directory_path / "sends.db"
            connection = module.init_log_db(str(log_path))
            for number in range(module.MAX_DAILY_SENDS):
                module.log_send(
                    connection,
                    connector_linkedin=f"https://linkedin.example/in/connector-{number}",
                    connector_name=f"Connector {number}",
                    target_name="Nora Imani",
                    message_preview="Prior successful send",
                    status="sent",
                    idempotency_key=module.build_idempotency_key(
                        f"path-prior-{number}", "linkedin", "1"
                    ),
                )
            connection.close()

            drafts_path = directory_path / "drafts.csv"
            write_drafts(
                drafts_path,
                [
                    {
                        "path_id": "path-eleven",
                        "connector_name": "Avery Stone",
                        "connector_linkedin": "https://linkedin.example/in/avery-stone",
                        "target_name": "Nora Imani",
                        "draft_body": "Would you introduce me to Nora?",
                        "approved": "true",
                        "message_version": "1",
                    }
                ],
            )
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--api-key",
                "example-key",
                "--delay",
                "60",
                "--log-db",
                str(log_path),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                module.main()

            verification = module.init_log_db(str(log_path))
            success_count = verification.execute(
                "SELECT COUNT(*) FROM sends WHERE status = 'sent'"
            ).fetchone()[0]
            verification.close()

        self.assertEqual(actor_calls, [])
        self.assertEqual(success_count, module.MAX_DAILY_SENDS)

    def test_rolling_window_excludes_success_older_than_twenty_four_hours(self):
        module = load_module()
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            for path_id in ("path-recent", "path-old"):
                module.log_send(
                    connection,
                    connector_linkedin="https://linkedin.example/in/avery-stone",
                    connector_name="Avery Stone",
                    target_name="Nora Imani",
                    message_preview="Prior successful send",
                    status="sent",
                    idempotency_key=module.build_idempotency_key(
                        path_id, "linkedin", "1"
                    ),
                )
            connection.execute(
                "UPDATE sends SET sent_at = ? WHERE idempotency_key = ?",
                (
                    (now - timedelta(hours=23)).isoformat(),
                    module.build_idempotency_key("path-recent", "linkedin", "1"),
                ),
            )
            connection.execute(
                "UPDATE sends SET sent_at = ? WHERE idempotency_key = ?",
                (
                    (now - timedelta(hours=25)).isoformat(),
                    module.build_idempotency_key("path-old", "linkedin", "1"),
                ),
            )
            connection.commit()

            count = module.successful_sends_in_rolling_window(connection, now=now)
            connection.close()

        self.assertEqual(count, 1)

    def test_failed_actor_attempt_counts_toward_per_run_limit(self):
        module = load_module()
        actor_calls = []
        module.send_linkedin_message = lambda **kwargs: actor_calls.append(kwargs) or {
            "run_id": "run-failed",
            "status": "FAILED",
        }
        module.time.sleep = lambda _seconds: None
        with tempfile.TemporaryDirectory() as directory:
            drafts_path = Path(directory) / "drafts.csv"
            write_drafts(
                drafts_path,
                [
                    {
                        "path_id": f"path-attempt-{number}",
                        "connector_name": f"Connector {number}",
                        "connector_linkedin": f"https://linkedin.example/in/connector-{number}",
                        "target_name": "Nora Imani",
                        "draft_body": "Would you introduce me to Nora?",
                        "approved": "true",
                        "message_version": "1",
                    }
                    for number in range(2)
                ],
            )
            argv = [
                "send_via_linkedin.py",
                "--input",
                str(drafts_path),
                "--api-key",
                "example-key",
                "--limit",
                "1",
                "--delay",
                "60",
                "--log-db",
                str(Path(directory) / "sends.db"),
            ]
            with (
                patch.object(sys, "argv", argv),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                module.main()

        self.assertEqual(len(actor_calls), 1)


if __name__ == "__main__":
    unittest.main()
