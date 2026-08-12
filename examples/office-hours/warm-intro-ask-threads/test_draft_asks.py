"""Behavior tests for Task 4 scored-path to ask-draft compatibility."""

from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_module():
    spec = importlib.util.spec_from_file_location("draft_asks", HERE / "draft_asks.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScoredCsvCompatibilityTests(unittest.TestCase):
    def test_campaign_warm_paths_load_directly_without_an_adapter(self):
        module = load_module()
        campaign_paths = (
            HERE.parent
            / "target-account-warm-intro-campaign"
            / "expected_output"
            / "warm_paths.csv"
        )

        rows = module.load_scored_csv(str(campaign_paths))

        self.assertEqual(len(rows), 4)
        self.assertTrue(
            all(
                row[field].strip()
                for row in rows
                for field in (
                    "campaign_id",
                    "owner_id",
                    "connector_id",
                    "target_id",
                    "path_id",
                )
            )
        )

    def test_loads_task_4_csv_without_renaming_columns(self):
        module = load_module()
        fieldnames = [
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
        ]
        row = {name: "" for name in fieldnames}
        row.update(
            {
                "campaign_id": "campaign-example",
                "owner_id": "owner-example",
                "connector_id": "connector-casey",
                "target_id": "target-mina",
                "path_id": module.build_path_id(
                    "campaign-example",
                    "owner-example",
                    "connector-casey",
                    "target-mina",
                ),
                "connector_name": "Casey Morgan",
                "connector_linkedin": "https://linkedin.example/in/example-casey-morgan",
                "target_name": "Mina Sol",
                "target_title": "Director of Revenue Systems",
                "target_company": "Relay Cloud",
                "shared_signal": "verified_work_overlap",
                "shared_detail": "Atlas Works, 2021-03-01 to 2023-06-30",
                "work_overlap_score": "30",
                "total_score": "33",
                "segment": "strong_warm_intro",
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "scored.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row)

            loaded = module.load_scored_csv(str(csv_path))

        self.assertEqual(loaded, [row])

    def test_tampered_path_id_is_rejected_before_drafting(self):
        module = load_module()
        fieldnames = sorted(module.REQUIRED_COLUMNS)
        row = {name: "example" for name in fieldnames}
        row.update(
            {
                "campaign_id": "campaign-example",
                "owner_id": "owner-example",
                "connector_id": "connector-casey",
                "target_id": "target-mina",
                "path_id": "path-tampered",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "scored.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row)

            with self.assertRaises(SystemExit) as raised:
                module.load_scored_csv(str(csv_path))

        self.assertIn("does not match", str(raised.exception))

    def test_blank_namespace_value_blocks_drafting_contract(self):
        module = load_module()
        fieldnames = sorted(module.REQUIRED_COLUMNS)
        row = {name: "example" for name in fieldnames}
        row.update(
            {
                "campaign_id": "campaign-example",
                "owner_id": " ",
                "connector_id": "connector-casey",
                "target_id": "target-mina",
                "path_id": "path-example",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "scored.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row)

            with self.assertRaises(SystemExit) as raised:
                module.load_scored_csv(str(csv_path))

        self.assertIn("owner_id", str(raised.exception))

    def test_dated_work_overlap_names_employer_and_overlap_dates(self):
        module = load_module()

        description = module.build_signal_description(
            {
                "connector_name": "Casey Morgan",
                "target_name": "Mina Sol",
                "shared_signal": "verified_work_overlap",
                "shared_detail": "Atlas Works, 2021-03-01 to 2023-06-30",
                "work_overlap_score": "30",
            }
        )

        self.assertIn("Atlas Works", description)
        self.assertIn("2021-03-01", description)
        self.assertIn("2023-06-30", description)

    def test_direct_introduction_names_confirmed_evidence_type(self):
        module = load_module()

        description = module.build_signal_description(
            {
                "connector_name": "Avery Stone",
                "target_name": "Nora Imani",
                "shared_signal": "direct_introduction",
                "shared_detail": "evidence-intro",
                "direct_intro_score": "60",
            }
        )

        self.assertIn("confirmed direct-introduction evidence", description)
        self.assertIn("evidence-intro", description)

    def test_investor_context_is_not_selected_over_a_stronger_supported_reason(self):
        module = load_module()

        description = module.build_signal_description(
            {
                "connector_name": "Avery Stone",
                "target_name": "Nora Imani",
                "shared_signal": "investor_overlap",
                "shared_detail": "Example Seed Fund",
                "direct_intro_score": "60",
                "investor_score": "1",
                "evidence_ids": "evidence-intro;evidence-investor",
            }
        )

        self.assertIn("confirmed direct-introduction evidence", description)
        self.assertNotIn("Seed Fund", description)


class DraftGenerationTests(unittest.TestCase):
    def test_prompt_uses_grounded_context_and_output_is_review_gated(self):
        module = load_module()
        captured_messages = []

        def fake_call(**kwargs):
            captured_messages.append(kwargs["user_message"])
            return {"subject": "Intro to Mina?", "body": "Would you intro me to Mina?"}

        module.call_deepline_agent = fake_call
        row = {
            "campaign_id": "campaign-example",
            "owner_id": "owner-example",
            "connector_id": "connector-casey",
            "target_id": "target-mina",
            "path_id": module.build_path_id(
                "campaign-example",
                "owner-example",
                "connector-casey",
                "target-mina",
            ),
            "connector_name": "Casey Morgan",
            "connector_linkedin": "https://linkedin.example/in/example-casey-morgan",
            "connector_company": "Example Operators",
            "target_name": "Mina Sol",
            "target_title": "Director of Revenue Systems",
            "target_company": "Relay Cloud",
            "shared_signal": "verified_work_overlap",
            "shared_detail": "Atlas Works, 2021-03-01 to 2023-06-30",
            "work_overlap_score": "30",
            "total_score": "33",
            "segment": "strong_warm_intro",
            "why_target_cares": "Relay is standardizing revenue systems.",
            "permissionless_value": "Prototype an exception taxonomy.",
        }

        drafts = module.draft_asks(
            rows=[row],
            api_key="example-key",  # pragma: allowlist secret
            top=None,
            model="example-model",
            verbose=False,
        )

        self.assertIn("Director of Revenue Systems", captured_messages[0])
        self.assertIn("verified dated work overlap", captured_messages[0])
        self.assertIn(row["why_target_cares"], captured_messages[0])
        self.assertIn(row["permissionless_value"], captured_messages[0])
        self.assertEqual(drafts[0]["path_id"], row["path_id"])
        self.assertEqual(drafts[0]["target_title"], row["target_title"])
        self.assertEqual(drafts[0]["target_company"], row["target_company"])
        self.assertEqual(drafts[0]["why_target_cares"], row["why_target_cares"])
        self.assertEqual(drafts[0]["permissionless_value"], row["permissionless_value"])
        self.assertEqual(drafts[0]["approved"], "false")
        self.assertEqual(drafts[0]["message_version"], "1")
        self.assertEqual(drafts[0]["campaign_id"], "campaign-example")
        self.assertEqual(drafts[0]["owner_id"], "owner-example")

    def test_no_strong_path_is_routed_without_calling_drafter(self):
        module = load_module()
        calls = []
        module.call_deepline_agent = lambda **kwargs: calls.append(kwargs)
        row = {
            "campaign_id": "campaign-example",
            "owner_id": "owner-example",
            "connector_id": "connector-parker",
            "target_id": "target-elliot",
            "path_id": module.build_path_id(
                "campaign-example",
                "owner-example",
                "connector-parker",
                "target-elliot",
            ),
            "connector_name": "Parker Quinn",
            "connector_linkedin": "linkedin.com/in/example-parker-quinn",
            "connector_company": "Example Seed Fund",
            "target_name": "Elliot Vale",
            "target_title": "Director of RevOps",
            "target_company": "Northstar AI",
            "shared_signal": "investor_overlap",
            "shared_detail": "Example Seed Fund",
            "total_score": "2",
            "segment": "no_strong_path",
        }

        drafts = module.draft_asks(
            rows=[row],
            api_key="example-key",  # pragma: allowlist secret
            top=None,
            model="example-model",
            verbose=False,
        )

        self.assertEqual(drafts, [])
        self.assertEqual(calls, [])

    def test_review_path_requires_both_explicit_override_flag_and_reviewed_input(self):
        module = load_module()
        calls = []

        def fake_call(**kwargs):
            calls.append(kwargs)
            return {"subject": "Intro?", "body": "Would you make an intro?"}

        module.call_deepline_agent = fake_call
        row = {
            "campaign_id": "campaign-example",
            "owner_id": "owner-example",
            "connector_id": "connector-riley",
            "target_id": "target-tariq",
            "path_id": module.build_path_id(
                "campaign-example",
                "owner-example",
                "connector-riley",
                "target-tariq",
            ),
            "connector_name": "Riley Chen",
            "connector_linkedin": "linkedin.com/in/example-riley-chen",
            "connector_company": "Harbor Guild",
            "target_name": "Tariq Fen",
            "target_title": "Director of BizOps",
            "target_company": "Harbor Systems",
            "shared_signal": "company_proximity",
            "shared_detail": "Nimbus Data; non-overlapping dates",
            "total_score": "2",
            "segment": "review_warm_intro",
            "reviewed_override": "true",
        }

        self.assertEqual(
            module.draft_asks([row], "example-key", None, "example-model", False),
            [],
        )
        self.assertEqual(calls, [])
        row_without_review = {**row, "reviewed_override": "false"}
        self.assertEqual(
            module.draft_asks(
                [row_without_review],
                "example-key",
                None,
                "example-model",
                False,
                allow_reviewed=True,
            ),
            [],
        )
        drafts = module.draft_asks(
            [row],
            "example-key",
            None,
            "example-model",
            False,
            allow_reviewed=True,
        )
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["reviewed_override"], "true")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
