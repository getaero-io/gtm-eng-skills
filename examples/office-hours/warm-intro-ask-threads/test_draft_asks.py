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
    def test_loads_task_4_csv_without_renaming_columns(self):
        module = load_module()
        fieldnames = [
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
                "path_id": "path-example",
                "connector_name": "Casey Morgan",
                "connector_linkedin": "https://linkedin.example/in/casey-morgan",
                "target_name": "Mina Sol",
                "target_title": "Director of Revenue Systems",
                "target_company": "Relay Cloud",
                "shared_signal": "verified_work_overlap",
                "shared_detail": "Atlas Works, 2021-03-01 to 2023-06-30",
                "work_overlap_score": "30",
                "total_score": "33",
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
            "path_id": "path-work",
            "connector_name": "Casey Morgan",
            "connector_linkedin": "https://linkedin.example/in/casey-morgan",
            "connector_company": "Example Operators",
            "target_name": "Mina Sol",
            "target_title": "Director of Revenue Systems",
            "target_company": "Relay Cloud",
            "shared_signal": "verified_work_overlap",
            "shared_detail": "Atlas Works, 2021-03-01 to 2023-06-30",
            "work_overlap_score": "30",
            "total_score": "33",
            "why_target_cares": "Relay is standardizing revenue systems.",
            "permissionless_value": "Prototype an exception taxonomy.",
        }

        drafts = module.draft_asks(
            rows=[row],
            api_key="example-key",
            top=None,
            model="example-model",
            verbose=False,
        )

        self.assertIn("Director of Revenue Systems", captured_messages[0])
        self.assertIn("verified dated work overlap", captured_messages[0])
        self.assertIn(row["why_target_cares"], captured_messages[0])
        self.assertIn(row["permissionless_value"], captured_messages[0])
        self.assertEqual(drafts[0]["path_id"], "path-work")
        self.assertEqual(drafts[0]["target_title"], row["target_title"])
        self.assertEqual(drafts[0]["target_company"], row["target_company"])
        self.assertEqual(drafts[0]["why_target_cares"], row["why_target_cares"])
        self.assertEqual(drafts[0]["permissionless_value"], row["permissionless_value"])
        self.assertEqual(drafts[0]["approved"], "false")
        self.assertEqual(drafts[0]["message_version"], "1")


if __name__ == "__main__":
    unittest.main()
