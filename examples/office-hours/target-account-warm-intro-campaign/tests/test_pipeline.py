"""End-to-end behavior for the anonymized deterministic fixture campaign."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from pipeline import run_pipeline  # noqa: E402


INPUT_DIR = PACKAGE_DIR / "sample_data"
CONFIG_PATH = PACKAGE_DIR / "config.example.json"
EXPECTED_DIR = PACKAGE_DIR / "expected_output"
REVIEW_ARTIFACTS = (
    "ranked_accounts.csv",
    "contact_dedupe_audit.csv",
    "pdl_gapfill_requests.json",
    "buying_committee.csv",
    "org_edges_review.csv",
    "interaction_audit.csv",
    "warm_paths.csv",
    "direct_outreach.csv",
    "campaign_ledger.json",
)
STAGE_ORDER = (
    "rank_accounts",
    "dedupe_contacts",
    "prepare_pdl_gapfill",
    "build_buying_committees",
    "review_org_edges",
    "audit_interactions",
    "score_warm_paths",
    "prepare_direct_outreach",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


class FixturePipelineTests(unittest.TestCase):
    def test_fixture_is_complete_anonymized_and_byte_deterministic(self):
        with TemporaryDirectory() as first_dir, TemporaryDirectory() as second_dir:
            first = Path(first_dir)
            second = Path(second_dir)

            ledger = run_pipeline(INPUT_DIR, first, CONFIG_PATH, date(2026, 8, 1))
            run_pipeline(INPUT_DIR, second, CONFIG_PATH, date(2026, 8, 1))

            self.assertEqual(tuple(path.name for path in sorted(first.iterdir())), tuple(sorted(REVIEW_ARTIFACTS)))
            for artifact in REVIEW_ARTIFACTS:
                with self.subTest(artifact=artifact):
                    self.assertEqual((first / artifact).read_bytes(), (second / artifact).read_bytes())
            for expected in sorted(EXPECTED_DIR.glob("*.csv")):
                with self.subTest(expected_output=expected.name):
                    self.assertEqual(expected.read_bytes(), (first / expected.name).read_bytes())
            self.assertEqual(
                {path.name for path in EXPECTED_DIR.glob("*.csv")},
                {artifact for artifact in REVIEW_ARTIFACTS if artifact.endswith(".csv")},
            )

            accounts = read_csv(first / "ranked_accounts.csv")
            with (INPUT_DIR / "accounts.csv").open(encoding="utf-8") as source:
                fixture_account_count = sum(1 for _ in source) - 1
            self.assertEqual(len(accounts), fixture_account_count)
            self.assertTrue(all(row["decision"] in {"include", "review", "exclude"} for row in accounts))
            self.assertEqual(
                next(row for row in accounts if row["domain"] == "acme-customer.example")["exclusion_reason"],
                "existing_customer",
            )

            dedupe_audit = read_csv(first / "contact_dedupe_audit.csv")
            self.assertEqual({row["match_types"] for row in dedupe_audit}, {"linkedin_url", "work_email"})
            pdl_requests = json.loads((first / "pdl_gapfill_requests.json").read_text(encoding="utf-8"))
            self.assertTrue(pdl_requests["requests"])
            self.assertTrue(all(request["exclusions"]["identities"] for request in pdl_requests["requests"]))
            self.assertNotIn("acme-customer.example", {request["account_id"] for request in pdl_requests["requests"]})

            paths = read_csv(first / "warm_paths.csv")
            self.assertEqual({row["segment"] for row in paths}, {"strong_warm_intro", "review_warm_intro", "no_strong_path"})
            reasons = "\n".join(row["reasons"] for row in paths)
            self.assertIn("confirmed_direct_introduction", reasons)
            self.assertIn("dated_work_overlap:", reasons)
            self.assertIn("non_overlapping_dates", reasons)
            investor_only = [row for row in paths if row["investor_only"] == "true"]
            self.assertTrue(investor_only)
            self.assertTrue(all(row["segment"] != "strong_warm_intro" for row in investor_only))

            org_review = read_csv(first / "org_edges_review.csv")
            inferred = next(row for row in org_review if row["edge_type"] == "functional_proximity_inferred")
            self.assertEqual((inferred["review_required"], inferred["to_kind"]), ("true", "open_role"))
            evidence_types = {row["source_type"] for row in read_csv(INPUT_DIR / "evidence.csv")}
            self.assertTrue({"job", "post", "talk", "interaction"}.issubset(evidence_types))

            for contact in read_csv(INPUT_DIR / "contacts.csv"):
                if contact["work_email"]:
                    self.assertTrue(contact["work_email"].casefold().endswith(".example"))
                if contact["linkedin_url"]:
                    self.assertRegex(
                        contact["linkedin_url"],
                        r"^(?:https?://(?:www\.)?)?linkedin\.com/in/example-[^/?]+(?:/)?(?:\?.*)?$",
                    )
            for filename, column in (("accounts.csv", "website_url"), ("evidence.csv", "source_url")):
                for row in read_csv(INPUT_DIR / filename):
                    if row[column]:
                        self.assertTrue((urlsplit(row[column]).hostname or "").endswith(".example"))

            combined = b"\n".join((first / artifact).read_bytes() for artifact in REVIEW_ARTIFACTS)
            domains = re.findall(rb"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+)", combined)
            self.assertTrue(domains)
            self.assertTrue(all(domain.lower().endswith(b".example") for domain in domains))

            ledger_json = json.loads((first / "campaign_ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger.total_authorized_provider_calls, 0)
            self.assertEqual(ledger.total_estimated_spend_usd, "0.00")
            self.assertEqual(tuple(stage["stage"] for stage in ledger_json["stages"]), STAGE_ORDER)
            self.assertTrue(all(stage["authorized_provider_calls"] == 0 for stage in ledger_json["stages"]))
            self.assertTrue(all(stage["estimated_spend_usd"] == "0.00" for stage in ledger_json["stages"]))
            for artifact, expected_hash in ledger_json["artifact_hashes"].items():
                with self.subTest(hash_artifact=artifact):
                    self.assertEqual(hashlib.sha256((first / artifact).read_bytes()).hexdigest(), expected_hash)


if __name__ == "__main__":
    unittest.main()
