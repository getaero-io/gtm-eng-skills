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
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from warm_intro_contract import build_path_id  # noqa: E402


def load_module():
    spec = importlib.util.spec_from_file_location(
        "send_via_linkedin", HERE / "send_via_linkedin.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _key(module, path_id: str, channel: str = "linkedin", version: str = "1") -> str:
    return module.build_idempotency_key(
        "campaign-example",
        "owner-example",
        path_id,
        channel,
        version,
    )


def _path_identity(seed: str) -> tuple[str, str, str]:
    connector_id = f"connector-{seed}"
    target_id = f"target-{seed}"
    return (
        connector_id,
        target_id,
        build_path_id("campaign-example", "owner-example", connector_id, target_id),
    )


def write_drafts(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "campaign_id",
        "owner_id",
        "connector_id",
        "target_id",
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
        prepared = []
        for row_number, row in enumerate(rows, 1):
            seed = str(row.get("path_id", row_number)).removeprefix("path-")
            row.setdefault("connector_id", f"connector-{seed}")
            row.setdefault("target_id", f"target-{seed}")
            campaign_id = str(row.get("campaign_id", "campaign-example")).strip()
            owner_id = str(row.get("owner_id", "owner-example")).strip()
            row["path_id"] = build_path_id(
                campaign_id or "campaign-example",
                owner_id or "owner-example",
                row["connector_id"],
                row["target_id"],
            )
            prepared.append(
                {
                    "campaign_id": "campaign-example",
                    "owner_id": "owner-example",
                    **row,
                }
            )
        writer.writerows(prepared)


class ApprovalGateTests(unittest.TestCase):
    def test_blank_namespace_value_blocks_activation_contract(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.csv"
            write_drafts(
                path,
                [
                    {
                        "campaign_id": " ",
                        "path_id": "path-invalid",
                        "connector_name": "Casey Morgan",
                        "connector_linkedin": "linkedin.com/in/example-casey-morgan",
                        "target_name": "Mina Sol",
                        "draft_body": "Would you introduce me to Mina?",
                        "approved": "true",
                        "message_version": "1",
                    }
                ],
            )

            with self.assertRaises(SystemExit) as raised:
                module.load_drafts_csv(str(path), require_approved=True)

        self.assertIn("campaign_id", str(raised.exception))

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
                        "connector_linkedin": "https://linkedin.example/in/example-casey-morgan",
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
            "connector_linkedin": "https://linkedin.example/in/example-avery-stone",
            "target_name": "Nora Imani",
            "draft_body": "Would you introduce me to Nora?",
            "approved": "TRUE",
            "message_version": "2",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.csv"
            write_drafts(path, [approved])

            rows = module.load_drafts_csv(str(path), require_approved=True)

        self.assertEqual(
            rows,
            [{"campaign_id": "campaign-example", "owner_id": "owner-example", **approved}],
        )

    def test_dry_run_loading_can_preview_unapproved_rows(self):
        module = load_module()
        draft = {
            "path_id": "path-preview",
            "connector_name": "Riley Chen",
            "connector_linkedin": "https://linkedin.example/in/example-riley-chen",
            "target_name": "Tariq Fen",
            "draft_body": "Would you introduce me to Tariq?",
            "approved": "false",
            "message_version": "1",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.csv"
            write_drafts(path, [draft])

            rows = module.load_drafts_csv(str(path), require_approved=False)

        self.assertEqual(
            rows,
            [{"campaign_id": "campaign-example", "owner_id": "owner-example", **draft}],
        )

    def test_tampered_path_identity_blocks_activation(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.csv"
            write_drafts(
                path,
                [
                    {
                        "path_id": "path-original",
                        "connector_name": "Avery Stone",
                        "connector_linkedin": "linkedin.example/in/example-avery-stone",
                        "target_name": "Nora Imani",
                        "draft_body": "Would you introduce me to Nora?",
                        "approved": "true",
                        "message_version": "1",
                    }
                ],
            )
            contents = path.read_text(encoding="utf-8")
            path.write_text(
                contents.replace(build_path_id(
                    "campaign-example",
                    "owner-example",
                    "connector-original",
                    "target-original",
                ), "path-tampered"),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit) as raised:
                module.load_drafts_csv(str(path), require_approved=True)

        self.assertIn("does not match", str(raised.exception))


class IdempotencyTests(unittest.TestCase):
    def test_repeat_key_is_detected_independently_of_connector_url_format(self):
        module = load_module()
        expected_key = "".join(
            (
                "307521be633e0a81",
                "00a4c115d08093e7",
                "59550f6e93d536a3",
                "ea83c99515adfe89",
            )
        )
        key = _key(module, "path-approved")
        self.assertEqual(key, expected_key)

        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            module.log_send(
                conn=connection,
                connector_linkedin="https://www.linkedin.example/in/example-avery-stone/",
                connector_name="Avery Stone",
                target_name="Nora Imani",
                message_preview="Would you introduce me to Nora?",
                status="sent",
                idempotency_key=key,
            )

            differently_formatted_url = "linkedin.example/in/example-avery-stone"
            retry_key = _key(module, "path-approved")
            self.assertNotEqual(
                differently_formatted_url,
                "https://www.linkedin.example/in/example-avery-stone/",
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
            connector_id, target_id, path_id = _path_identity("atomic")
            key = _key(module, path_id)
            details = {
                "idempotency_key": key,
                "connector_linkedin": "https://linkedin.example/in/example-casey-morgan",
                "connector_name": "Casey Morgan",
                "target_name": "Mina Sol",
                "message_preview": "Would you introduce me to Mina?",
                "campaign_id": "campaign-example",
                "owner_id": "owner-example",
                "connector_id": connector_id,
                "target_id": target_id,
                "path_id": path_id,
                "message_version": "1",
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
            ("dispatching", "owner-first"),
        )

    def test_stale_post_dispatch_reservation_requires_reconciliation(self):
        module = load_module()
        first_time = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        retry_time = first_time + timedelta(seconds=module.PENDING_TTL_SECONDS + 1)
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            connector_id, target_id, path_id = _path_identity("stale")
            key = _key(module, path_id)
            details = {
                "conn": connection,
                "idempotency_key": key,
                "connector_linkedin": "https://linkedin.example/in/example-riley-chen",
                "connector_name": "Riley Chen",
                "target_name": "Tariq Fen",
                "message_preview": "Would you introduce me to Tariq?",
                "campaign_id": "campaign-example",
                "owner_id": "owner-example",
                "connector_id": connector_id,
                "target_id": target_id,
                "path_id": path_id,
                "message_version": "1",
            }
            self.assertTrue(
                module.reserve_send(
                    owner_token="owner-crashed", now=first_time, **details
                )
            )

            self.assertFalse(
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
            (row["status"], row["reservation_owner"]),
            ("needs_reconciliation", None),
        )
        self.assertEqual(count, 1)

    def test_pending_reservation_atomically_consumes_last_daily_slot(self):
        module = load_module()
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "sends.db"
            first = module.init_log_db(str(db_path))
            for number in range(module.MAX_DAILY_SENDS - 1):
                connector_id, target_id, path_id = _path_identity(
                    f"prior-capacity-{number}"
                )
                key = _key(module, path_id)
                self.assertTrue(module.reserve_send(
                    first,
                    idempotency_key=key,
                    owner_token=f"prior-owner-{number}",
                    connector_linkedin=f"https://linkedin.example/in/example-prior-{number}",
                    connector_name=f"Prior {number}",
                    target_name="Nora Imani",
                    message_preview="Prior send",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=connector_id,
                    target_id=target_id,
                    path_id=path_id,
                    message_version="1",
                    message_body="Prior send",
                ))
                self.assertTrue(module.finish_reserved_send(
                    first,
                    key,
                    f"prior-owner-{number}",
                    "SUCCEEDED",
                    apify_run_id=f"run-prior-{number}",
                ))
            second = module.init_log_db(str(db_path))

            common = {
                "connector_linkedin": "https://linkedin.example/in/example-casey-morgan",
                "connector_name": "Casey Morgan",
                "target_name": "Mina Sol",
                "message_preview": "Would you introduce me to Mina?",
                "now": now,
            }
            final_connector_id, final_target_id, final_path_id = _path_identity(
                "final-slot"
            )
            self.assertTrue(
                module.reserve_send(
                    first,
                    idempotency_key=_key(module, final_path_id),
                    owner_token="owner-final-slot",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=final_connector_id,
                    target_id=final_target_id,
                    path_id=final_path_id,
                    message_version="1",
                    **common,
                )
            )
            over_connector_id, over_target_id, over_path_id = _path_identity(
                "over-capacity"
            )
            self.assertFalse(
                module.reserve_send(
                    second,
                    idempotency_key=_key(module, over_path_id),
                    owner_token="owner-over-capacity",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=over_connector_id,
                    target_id=over_target_id,
                    path_id=over_path_id,
                    message_version="1",
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
                "connector_id",
                "target_id",
                "contract_version",
            }.issubset(columns)
        )
        self.assertEqual(indexes["sends_idempotency_key_uq"], 1)

    def test_legacy_sent_key_blocks_namespaced_reservation_after_upgrade(self):
        module = load_module()
        identity = (
            "campaign-example",
            "owner-example",
            "connector-existing-live-message",
            "target-existing-live-message",
        )
        old_path_id = "path-" + hashlib.sha256("|".join(identity).encode()).hexdigest()[:16]
        new_path_id = build_path_id(*identity)
        self.assertNotEqual(old_path_id, new_path_id)
        old_key = hashlib.sha256(f"{old_path_id}|linkedin|1".encode()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "legacy.db"))
            module.log_send(
                connection,
                connector_linkedin="linkedin.example/in/example-legacy-connector",
                connector_name="Legacy Connector",
                target_name="Legacy Target",
                message_preview="Already delivered under the legacy contract",
                status="sent",
                idempotency_key=old_key,
            )

            with self.assertRaises(RuntimeError) as raised:
                module.reserve_send(
                    connection,
                    idempotency_key=_key(module, new_path_id),
                    owner_token="new-process",
                    connector_linkedin="linkedin.example/in/example-legacy-connector",
                    connector_name="Legacy Connector",
                    target_name="Legacy Target",
                    message_preview="Already delivered under the legacy contract",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=identity[2],
                    target_id=identity[3],
                    path_id=new_path_id,
                    message_version="1",
                )
            connection.close()

        self.assertIn("legacy send history", str(raised.exception))

    def test_partial_migration_cannot_bypass_global_legacy_barrier(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "legacy.db"))
            module.log_send(
                connection,
                connector_linkedin="linkedin.example/in/example-legacy-connector",
                connector_name="Legacy Connector",
                target_name="Legacy Target",
                message_preview="Historical live send",
                status="sent",
                idempotency_key="legacy-key",
            )
            connection.execute(
                """
                UPDATE sends
                SET campaign_id = 'campaign-example', owner_id = 'owner-example',
                    intent_hash = 'nonblank-but-unverified'
                WHERE idempotency_key = 'legacy-key'
                """
            )
            connection.commit()
            connector_id, target_id, path_id = _path_identity("current-example")

            with self.assertRaises(RuntimeError) as raised:
                module.reserve_send(
                    connection,
                    idempotency_key=_key(module, path_id),
                    owner_token="new-process",
                    connector_linkedin="linkedin.example/in/example-current-connector",
                    connector_name="Current Connector",
                    target_name="Current Target",
                    message_preview="New send",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=connector_id,
                    target_id=target_id,
                    path_id=path_id,
                    message_version="1",
                )
            connection.close()

        self.assertIn("legacy send history", str(raised.exception))

    def test_blank_current_contract_marker_blocks_live_activation(self):
        module = load_module()
        connector_id, target_id, path_id = _path_identity("marker-history")
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            key = _key(module, path_id)
            self.assertTrue(
                module.reserve_send(
                    connection,
                    idempotency_key=key,
                    owner_token="historical-owner",
                    connector_linkedin="linkedin.example/in/example-marker-history",
                    connector_name="Marker History",
                    target_name="Marker Target",
                    message_preview="Historical message",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=connector_id,
                    target_id=target_id,
                    path_id=path_id,
                    message_version="1",
                    message_body="Historical message",
                )
            )
            connection.execute(
                "UPDATE sends SET contract_version = '' WHERE idempotency_key = ?",
                (key,),
            )
            connection.commit()
            next_connector, next_target, next_path = _path_identity("after-marker")

            with self.assertRaises(RuntimeError) as raised:
                module.reserve_send(
                    connection,
                    idempotency_key=_key(module, next_path),
                    owner_token="new-owner",
                    connector_linkedin="linkedin.example/in/example-after-marker",
                    connector_name="After Marker",
                    target_name="Next Target",
                    message_preview="Next message",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=next_connector,
                    target_id=next_target,
                    path_id=next_path,
                    message_version="1",
                )
            connection.close()

        self.assertIn("legacy send history", str(raised.exception))

    def test_forged_historical_activation_key_blocks_live_activation(self):
        module = load_module()
        connector_id, target_id, path_id = _path_identity("forged-key-history")
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            key = _key(module, path_id)
            self.assertTrue(
                module.reserve_send(
                    connection,
                    idempotency_key=key,
                    owner_token="historical-owner",
                    connector_linkedin="linkedin.example/in/example-forged-key",
                    connector_name="Forged Key History",
                    target_name="Forged Key Target",
                    message_preview="Historical message",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=connector_id,
                    target_id=target_id,
                    path_id=path_id,
                    message_version="1",
                    message_body="Historical message",
                )
            )
            connection.execute(
                "UPDATE sends SET idempotency_key = 'forged-activation-key' "
                "WHERE idempotency_key = ?",
                (key,),
            )
            connection.commit()
            next_connector, next_target, next_path = _path_identity("after-forgery")

            with self.assertRaises(RuntimeError) as raised:
                module.reserve_send(
                    connection,
                    idempotency_key=_key(module, next_path),
                    owner_token="new-owner",
                    connector_linkedin="linkedin.example/in/example-after-forgery",
                    connector_name="After Forgery",
                    target_name="Next Target",
                    message_preview="Next message",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=next_connector,
                    target_id=next_target,
                    path_id=next_path,
                    message_version="1",
                )
            connection.close()

        self.assertIn("invalid migrated send history", str(raised.exception))

    def test_old_path_and_activation_algorithms_cannot_masquerade_as_migrated(self):
        module = load_module()
        identity = (
            "campaign-example",
            "owner-example",
            "connector-old-algorithm",
            "target-old-algorithm",
        )
        old_path_id = "path-" + hashlib.sha256("|".join(identity).encode()).hexdigest()[:16]
        old_key = hashlib.sha256(f"{old_path_id}|linkedin|1".encode()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "legacy.db"))
            module.log_send(
                connection,
                connector_linkedin="linkedin.example/in/example-old-algorithm",
                connector_name="Old Algorithm",
                target_name="Old Target",
                message_preview="Old message",
                status="sent",
                idempotency_key=old_key,
            )
            connection.execute(
                """
                UPDATE sends
                SET campaign_id = ?, owner_id = ?, connector_id = ?, target_id = ?,
                    path_id = ?, channel = 'linkedin', message_version = '1',
                    contract_version = ?, intent_hash = 'forged-current-intent',
                    message_body = 'Old message'
                WHERE idempotency_key = ?
                """,
                (*identity, old_path_id, module.OUTBOX_CONTRACT_VERSION, old_key),
            )
            connection.commit()
            next_connector, next_target, next_path = _path_identity("after-old")

            with self.assertRaises(RuntimeError) as raised:
                module.reserve_send(
                    connection,
                    idempotency_key=_key(module, next_path),
                    owner_token="new-owner",
                    connector_linkedin="linkedin.example/in/example-after-old",
                    connector_name="After Old",
                    target_name="Next Target",
                    message_preview="Next message",
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=next_connector,
                    target_id=next_target,
                    path_id=next_path,
                    message_version="1",
                )
            connection.close()

        self.assertIn("invalid migrated send history", str(raised.exception))

    def test_dry_run_log_does_not_block_a_later_live_send(self):
        module = load_module()
        key = _key(module, "path-preview")
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            common = {
                "conn": connection,
                "connector_linkedin": "https://linkedin.example/in/example-riley-chen",
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
    def assert_actor_status_requires_reconciliation(self, actor_status):
        module = load_module()
        path_id = f"path-{actor_status.casefold().replace('_', '-')}"
        row = {
            "path_id": path_id,
            "connector_name": "Casey Morgan",
            "connector_linkedin": "https://linkedin.example/in/example-casey-morgan",
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
            path_id = row["path_id"]
            key = _key(module, path_id)
            self.assertFalse(module.already_sent(connection, key))
            lifecycle = connection.execute(
                "SELECT status, COUNT(*) AS row_count FROM sends WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            self.assertEqual(
                (lifecycle["status"], lifecycle["row_count"]),
                ("needs_reconciliation", 1),
            )
            self.assertFalse(
                module.reserve_send(
                    connection,
                    idempotency_key=key,
                    owner_token="retry-owner",
                    connector_linkedin=row["connector_linkedin"],
                    connector_name=row["connector_name"],
                    target_name=row["target_name"],
                    message_preview=row["draft_body"],
                    campaign_id="campaign-example",
                    owner_id="owner-example",
                    connector_id=row["connector_id"],
                    target_id=row["target_id"],
                    path_id=path_id,
                    channel="linkedin",
                    message_version="1",
                    message_body=row["draft_body"],
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
                "connector_linkedin": "https://linkedin.example/in/example-casey-morgan",
                "target_name": "Mina Sol",
                "draft_body": "Would you introduce me to Mina?",
                "approved": "false",
                "message_version": "1",
            },
            {
                "path_id": "path-approved",
                "connector_name": "Avery Stone",
                "connector_linkedin": "https://www.linkedin.example/in/example-avery-stone/",
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

            rows[1]["connector_linkedin"] = "linkedin.example/in/example-avery-stone"
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
                (_key(module, rows[1]["path_id"]),),
            ).fetchone()[0]
            verification.close()

        self.assertEqual(sent_urls, ["https://www.linkedin.example/in/example-avery-stone/"])
        self.assertEqual(lifecycle_count, 1)

    def test_failed_actor_status_does_not_mark_message_sent(self):
        self.assert_actor_status_requires_reconciliation("FAILED")

    def test_aborted_actor_status_does_not_mark_message_sent(self):
        self.assert_actor_status_requires_reconciliation("ABORTED")

    def test_timed_out_actor_status_does_not_mark_message_sent(self):
        self.assert_actor_status_requires_reconciliation("TIMED-OUT")

    def test_unknown_actor_status_does_not_mark_message_sent(self):
        self.assert_actor_status_requires_reconciliation("UNKNOWN")

    def test_main_reserves_key_before_calling_external_actor(self):
        module = load_module()
        row = {
            "path_id": "path-before-side-effect",
            "connector_name": "Avery Stone",
            "connector_linkedin": "https://linkedin.example/in/example-avery-stone",
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
            key = _key(module, row["path_id"])

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
                        campaign_id="campaign-example",
                        owner_id="owner-example",
                        connector_id=row["connector_id"],
                        target_id=row["target_id"],
                        path_id=row["path_id"],
                        channel="linkedin",
                        message_version=row["message_version"],
                        message_body=row["draft_body"],
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

    def assert_processing_failure_is_safely_classified_and_batch_continues(self, first_outcome):
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
                "connector_linkedin": f"https://linkedin.example/in/example-connector-{number}",
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
            failed_key = _key(module, rows[0]["path_id"])
            later_key = _key(module, rows[1]["path_id"])
            failed = connection.execute(
                "SELECT status, reservation_owner FROM sends WHERE idempotency_key = ?",
                (failed_key,),
            ).fetchone()
            pre_dispatch = isinstance(first_outcome, FileNotFoundError)
            self.assertEqual(
                (failed["status"], failed["reservation_owner"]),
                ("ready" if pre_dispatch else "needs_reconciliation", None),
            )
            retry_reserved = module.reserve_send(
                connection,
                idempotency_key=failed_key,
                owner_token="immediate-retry",
                connector_linkedin=rows[0]["connector_linkedin"],
                connector_name=rows[0]["connector_name"],
                target_name=rows[0]["target_name"],
                message_preview=rows[0]["draft_body"],
                campaign_id="campaign-example",
                owner_id="owner-example",
                connector_id=rows[0]["connector_id"],
                target_id=rows[0]["target_id"],
                path_id=rows[0]["path_id"],
                channel="linkedin",
                message_version="1",
                message_body=rows[0]["draft_body"],
            )
            self.assertEqual(retry_reserved, pre_dispatch)
            self.assertTrue(module.already_sent(connection, later_key))
            connection.close()

        self.assertEqual(len(actor_calls), 2)

    def test_file_not_found_actor_failure_is_retryable_and_batch_continues(self):
        self.assert_processing_failure_is_safely_classified_and_batch_continues(
            FileNotFoundError("deepline executable not found")
        )

    def test_malformed_actor_result_requires_reconciliation_and_batch_continues(self):
        self.assert_processing_failure_is_safely_classified_and_batch_continues(None)

    def test_success_status_without_provider_run_id_requires_reconciliation(self):
        self.assert_processing_failure_is_safely_classified_and_batch_continues(
            {"status": "SUCCEEDED"}
        )

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
                    "connector_linkedin": "https://linkedin.example/in/example-avery-stone",
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
                    key = _key(module, row["path_id"])
                    status = connection.execute(
                        "SELECT status FROM sends WHERE idempotency_key = ?", (key,)
                    ).fetchone()["status"]
                    connection.close()

                self.assertEqual(status, "needs_reconciliation")


class DurableOutboxAdversarialTests(unittest.TestCase):
    def _intent(self, module, path_id="path-durable"):
        seed = path_id.removeprefix("path-")
        connector_id, target_id, current_path_id = _path_identity(seed)
        return {
            "idempotency_key": module.build_idempotency_key(
                "campaign-example",
                "owner-example",
                current_path_id,
                "linkedin",
                "1",
            ),
            "campaign_id": "campaign-example",
            "owner_id": "owner-example",
            "connector_id": connector_id,
            "target_id": target_id,
            "path_id": current_path_id,
            "channel": "linkedin",
            "message_version": "1",
            "connector_linkedin": "linkedin.com/in/example-durable-connector",
            "connector_name": "Durable Connector",
            "target_name": "Example Target",
            "message_preview": "Would you make an introduction?",
            "message_body": "Would you make an introduction?",
        }

    def test_proven_pre_dispatch_failure_retries_with_immutable_attempt_audit(self):
        module = load_module()
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            intent = self._intent(module)
            self.assertTrue(
                module.reserve_send(
                    connection,
                    owner_token="attempt-owner-1",
                    now=now,
                    **intent,
                )
            )
            module.record_pre_dispatch_failure(
                connection,
                intent["idempotency_key"],
                "attempt-owner-1",
                "deepline executable not found",
                now=now + timedelta(seconds=1),
            )
            first_attempt = dict(
                connection.execute(
                    "SELECT * FROM send_attempts WHERE idempotency_key = ?",
                    (intent["idempotency_key"],),
                ).fetchone()
            )
            self.assertTrue(
                module.reserve_send(
                    connection,
                    owner_token="attempt-owner-2",
                    now=now + timedelta(seconds=2),
                    **intent,
                )
            )
            attempts = connection.execute(
                "SELECT * FROM send_attempts WHERE idempotency_key = ? ORDER BY attempt_number",
                (intent["idempotency_key"],),
            ).fetchall()
            events = connection.execute(
                "SELECT event_type FROM send_events WHERE idempotency_key = ? ORDER BY event_id",
                (intent["idempotency_key"],),
            ).fetchall()
            self.assertEqual(dict(attempts[0]), first_attempt)
            self.assertEqual([row["attempt_number"] for row in attempts], [1, 2])
            self.assertEqual(
                [row["event_type"] for row in events],
                ["dispatch_started", "pre_dispatch_failure", "dispatch_started"],
            )
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute(
                    "UPDATE send_attempts SET owner_token = 'changed' WHERE attempt_id = ?",
                    (attempts[0]["attempt_id"],),
                )
            first_event_id = connection.execute(
                "SELECT event_id FROM send_events WHERE idempotency_key = ? ORDER BY event_id",
                (intent["idempotency_key"],),
            ).fetchone()["event_id"]
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute(
                    "UPDATE send_events SET detail = 'changed' WHERE event_id = ?",
                    (first_event_id,),
                )
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute(
                    "DELETE FROM send_attempts WHERE attempt_id = ?",
                    (attempts[0]["attempt_id"],),
                )
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute(
                    "DELETE FROM send_events WHERE event_id = ?",
                    (first_event_id,),
                )
            connection.close()

    def test_post_dispatch_unknown_and_stale_recovery_block_automatic_retry(self):
        module = load_module()
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            intent = self._intent(module, "path-unknown")
            self.assertTrue(
                module.reserve_send(
                    connection,
                    owner_token="attempt-owner",
                    now=now,
                    **intent,
                )
            )
            module.finish_reserved_send(
                connection,
                intent["idempotency_key"],
                "attempt-owner",
                "UNKNOWN",
                apify_run_id="run-unknown",
                error_detail="response malformed after dispatch",
                now=now + timedelta(seconds=1),
            )
            self.assertFalse(
                module.reserve_send(
                    connection,
                    owner_token="retry-owner",
                    now=now + timedelta(seconds=module.PENDING_TTL_SECONDS + 2),
                    **intent,
                )
            )
            row = connection.execute(
                "SELECT status, apify_run_id FROM sends WHERE idempotency_key = ?",
                (intent["idempotency_key"],),
            ).fetchone()
            self.assertEqual(
                (row["status"], row["apify_run_id"]),
                ("needs_reconciliation", "run-unknown"),
            )
            provider_event = connection.execute(
                """
                SELECT provider_run_id, provider_status FROM send_events
                WHERE idempotency_key = ? AND event_type = 'provider_result'
                """,
                (intent["idempotency_key"],),
            ).fetchone()
            self.assertEqual(
                (provider_event["provider_run_id"], provider_event["provider_status"]),
                ("run-unknown", "UNKNOWN"),
            )

            stale = self._intent(module, "path-stale-after-dispatch")
            self.assertTrue(
                module.reserve_send(
                    connection,
                    owner_token="crashed-owner",
                    now=now,
                    **stale,
                )
            )
            self.assertFalse(
                module.reserve_send(
                    connection,
                    owner_token="recovery-owner",
                    now=now + timedelta(seconds=module.PENDING_TTL_SECONDS + 1),
                    **stale,
                )
            )
            stale_status = connection.execute(
                "SELECT status FROM sends WHERE idempotency_key = ?",
                (stale["idempotency_key"],),
            ).fetchone()["status"]
            self.assertEqual(stale_status, "needs_reconciliation")
            connection.close()

    def test_success_without_provider_run_id_cannot_bypass_durable_invariant(self):
        module = load_module()
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            connection = module.init_log_db(str(Path(directory) / "sends.db"))
            intent = self._intent(module, "path-success-without-run-id")
            self.assertTrue(
                module.reserve_send(
                    connection,
                    owner_token="attempt-owner",
                    now=now,
                    **intent,
                )
            )

            succeeded = module.finish_reserved_send(
                connection,
                intent["idempotency_key"],
                "attempt-owner",
                "SUCCEEDED",
                apify_run_id=None,
                now=now + timedelta(seconds=1),
            )

            lifecycle = connection.execute(
                "SELECT status, error_detail FROM sends WHERE idempotency_key = ?",
                (intent["idempotency_key"],),
            ).fetchone()
            connection.close()

        self.assertFalse(succeeded)
        self.assertEqual(lifecycle["status"], "needs_reconciliation")
        self.assertIn("run ID", lifecycle["error_detail"])

    def test_response_loss_and_process_control_are_persisted_before_propagation(self):
        for exception in (RuntimeError("response lost"), KeyboardInterrupt(), SystemExit(9)):
            with self.subTest(exception=type(exception).__name__):
                module = load_module()
                row = {
                    "path_id": f"path-{type(exception).__name__.casefold()}",
                    "connector_name": "Avery Stone",
                    "connector_linkedin": "linkedin.com/in/example-avery-stone",
                    "target_name": "Nora Imani",
                    "draft_body": "Would you introduce me to Nora?",
                    "approved": "true",
                    "message_version": "1",
                }

                def fail_after_dispatch(**_kwargs):
                    raise exception

                module.send_linkedin_message = fail_after_dispatch
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
                    context = (
                        self.assertRaises(type(exception))
                        if isinstance(exception, (KeyboardInterrupt, SystemExit))
                        else nullcontext()
                    )
                    with (
                        patch.object(sys, "argv", argv),
                        redirect_stdout(io.StringIO()),
                        redirect_stderr(io.StringIO()),
                        context,
                    ):
                        module.main()
                    connection = module.init_log_db(str(log_path))
                    key = module.build_idempotency_key(
                        "campaign-example",
                        "owner-example",
                        row["path_id"],
                        "linkedin",
                        "1",
                    )
                    lifecycle = connection.execute(
                        "SELECT status FROM sends WHERE idempotency_key = ?",
                        (key,),
                    ).fetchone()
                    events = connection.execute(
                        "SELECT event_type FROM send_events WHERE idempotency_key = ? ORDER BY event_id",
                        (key,),
                    ).fetchall()
                    connection.close()
                self.assertEqual(lifecycle["status"], "needs_reconciliation")
                self.assertEqual(
                    [event["event_type"] for event in events],
                    ["dispatch_started", "post_dispatch_ambiguous"],
                )


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
                        "connector_linkedin": "https://linkedin.example/in/example-avery-stone",
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
                        "connector_linkedin": "https://linkedin.example/in/example-casey-morgan",
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
                        "connector_linkedin": "https://linkedin.example/in/example-riley-chen",
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
                    connector_linkedin=f"https://linkedin.example/in/example-connector-{number}",
                    connector_name=f"Connector {number}",
                    target_name="Nora Imani",
                    message_preview="Prior successful send",
                    status="sent",
                    idempotency_key=_key(module, f"path-prior-{number}"),
                )
            connection.close()

            drafts_path = directory_path / "drafts.csv"
            write_drafts(
                drafts_path,
                [
                    {
                        "path_id": "path-eleven",
                        "connector_name": "Avery Stone",
                        "connector_linkedin": "https://linkedin.example/in/example-avery-stone",
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
                    connector_linkedin="https://linkedin.example/in/example-avery-stone",
                    connector_name="Avery Stone",
                    target_name="Nora Imani",
                    message_preview="Prior successful send",
                    status="sent",
                    idempotency_key=_key(module, path_id),
                )
            connection.execute(
                "UPDATE sends SET sent_at = ? WHERE idempotency_key = ?",
                (
                    (now - timedelta(hours=23)).isoformat(),
                    _key(module, "path-recent"),
                ),
            )
            connection.execute(
                "UPDATE sends SET sent_at = ? WHERE idempotency_key = ?",
                (
                    (now - timedelta(hours=25)).isoformat(),
                    _key(module, "path-old"),
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
                        "connector_linkedin": f"https://linkedin.example/in/example-connector-{number}",
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
