"""Synthetic fixtures only: historical private content must never enter tests."""

import copy
import unittest

from audit_history import audit


class HistoricalAuditTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"targets": [{"top": [{
            "draft": {
                "approved": False,
                "forwardable_note": "A synthetic forwardable introduction for review.",
                "connector_ask": (
                    "You may know this person. Do you know them well enough "
                    "to introduce us? No pressure."
                ),
            },
            "components": [{"evidence": [{
                "source": "synthetic", "observed_at": "2026-01-01",
                "detail": "Synthetic overlap",
            }]}],
        }]}]}

    def test_valid_draft(self):
        result = audit(self.payload)
        self.assertTrue(result["passed"])
        self.assertEqual(result["counts"]["drafts"], 1)

    def test_approval_must_be_literal_false(self):
        for approved in (True, None, 0, "false"):
            with self.subTest(approved=approved):
                value = copy.deepcopy(self.payload)
                value["targets"][0]["top"][0]["draft"]["approved"] = approved
                self.assertEqual(audit(value)["findings"], {"approval_not_false": 1})

    def test_component_requires_evidence(self):
        self.payload["targets"][0]["top"][0]["components"][0]["evidence"] = []
        self.assertEqual(audit(self.payload)["findings"], {"component_missing_evidence": 1})

    def test_evidence_requires_provenance_fields(self):
        self.payload["targets"][0]["top"][0]["components"][0]["evidence"] = [{}]
        self.assertEqual(audit(self.payload)["findings"], {
            "evidence_missing_detail": 1, "evidence_missing_observed_at": 1,
            "evidence_missing_source": 1,
        })

    def test_missing_drafts(self):
        self.assertEqual(audit({"targets": []})["findings"], {"missing_drafts": 1})

    def test_forwardable_note_required(self):
        for note in (None, "", "   ", 42):
            with self.subTest(note=note):
                value = copy.deepcopy(self.payload)
                value["targets"][0]["top"][0]["draft"]["forwardable_note"] = note
                self.assertEqual(audit(value)["findings"], {"missing_forwardable_note": 1})

    def test_unsafe_language(self):
        self.payload["targets"][0]["top"][0]["draft"]["connector_ask"] = "Make this introduction."
        self.assertEqual(audit(self.payload)["findings"], {
            "missing_no_pressure": 1, "missing_relationship_question": 1,
            "missing_uncertainty": 1,
        })


if __name__ == "__main__":
    unittest.main()
