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

        self.assertIn("idempotency_key", columns)
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
                "0",
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

        self.assertEqual(sent_urls, ["https://www.linkedin.example/in/avery-stone/"])


if __name__ == "__main__":
    unittest.main()
