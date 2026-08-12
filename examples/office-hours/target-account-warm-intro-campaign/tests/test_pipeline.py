"""End-to-end behavior for the anonymized deterministic fixture campaign."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
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
            self.assertEqual(
                [
                    {
                        key: stage[key]
                        for key in (
                            "stage",
                            "input_count",
                            "output_count",
                            "exclusions",
                            "review_count",
                            "cache_hits",
                            "authorized_provider_calls",
                            "estimated_spend_usd",
                        )
                    }
                    for stage in ledger_json["stages"]
                ],
                [
                    {"stage": "rank_accounts", "input_count": 5, "output_count": 5, "exclusions": {"existing_customer": 1, "non_b2b": 1}, "review_count": 0, "cache_hits": 0, "authorized_provider_calls": 0, "estimated_spend_usd": "0.00"},
                    {"stage": "dedupe_contacts", "input_count": 11, "output_count": 9, "exclusions": {"merged_duplicates": 2}, "review_count": 0, "cache_hits": 0, "authorized_provider_calls": 0, "estimated_spend_usd": "0.00"},
                    {"stage": "prepare_pdl_gapfill", "input_count": 6, "output_count": 3, "exclusions": {"known_emails": 4, "known_identities": 6, "known_linkedin_urls": 4}, "review_count": 0, "cache_hits": 0, "authorized_provider_calls": 0, "estimated_spend_usd": "0.00"},
                    {"stage": "build_buying_committees", "input_count": 9, "output_count": 4, "exclusions": {"open_roles": 1, "out_of_scope_contacts": 4, "unqualified_contacts": 0}, "review_count": 0, "cache_hits": 0, "authorized_provider_calls": 0, "estimated_spend_usd": "0.00"},
                    {"stage": "review_org_edges", "input_count": 2, "output_count": 2, "exclusions": {}, "review_count": 1, "cache_hits": 0, "authorized_provider_calls": 0, "estimated_spend_usd": "0.00"},
                    {"stage": "audit_interactions", "input_count": 5, "output_count": 5, "exclusions": {}, "review_count": 0, "cache_hits": 0, "authorized_provider_calls": 0, "estimated_spend_usd": "0.00"},
                    {"stage": "score_warm_paths", "input_count": 4, "output_count": 4, "exclusions": {"investor_only_not_strong": 1}, "review_count": 1, "cache_hits": 0, "authorized_provider_calls": 0, "estimated_spend_usd": "0.00"},
                    {"stage": "prepare_direct_outreach", "input_count": 4, "output_count": 2, "exclusions": {"strong_warm_intro": 2}, "review_count": 2, "cache_hits": 0, "authorized_provider_calls": 0, "estimated_spend_usd": "0.00"},
                ],
            )
            self.assertEqual(
                ledger_json["evidence_freshness"],
                {
                    "0_30_days": 5,
                    "31_90_days": 3,
                    "91_365_days": 2,
                    "future": 0,
                    "over_365_days": 0,
                    "unknown": 0,
                },
            )
            self.assertEqual(
                ledger_json["path_segment_counts"],
                {
                    "no_strong_path": 1,
                    "review_warm_intro": 1,
                    "strong_warm_intro": 2,
                },
            )
            self.assertEqual(ledger_json["approved_message_count"], 0)
            self.assertEqual(ledger_json["activated_message_count"], 0)
            for artifact, expected_hash in ledger_json["artifact_hashes"].items():
                with self.subTest(hash_artifact=artifact):
                    self.assertEqual(hashlib.sha256((first / artifact).read_bytes()).hexdigest(), expected_hash)

    def test_forged_or_mismatched_direct_intro_claims_downgrade_with_errors(self):
        mutations = {
            "forged": (
                "connector_edges.csv",
                "evidence-intro",
                "evidence-forged",
                "forged",
            ),
            "wrong_owner": (
                "connector_edges.csv",
                "campaign-owner",
                "other-owner",
                "wrong_owner",
            ),
            "owner_whitespace": (
                "connector_edges.csv",
                "campaign-owner,connector-direct",
                " campaign-owner ,connector-direct",
                "wrong_owner",
            ),
            "wrong_participant": (
                "interactions.csv",
                "campaign-owner|connector-direct|contact-northstar-gtm",
                "campaign-owner|contact-northstar-gtm",
                "wrong_participant",
            ),
        }
        for label, (filename, before, after, expected_error) in mutations.items():
            with self.subTest(label=label), TemporaryDirectory() as directory:
                root = Path(directory)
                mutated_inputs = root / "inputs"
                shutil.copytree(INPUT_DIR, mutated_inputs)
                path = mutated_inputs / filename
                path.write_text(
                    path.read_text(encoding="utf-8").replace(before, after),
                    encoding="utf-8",
                    newline="\n",
                )
                output = root / "output"

                run_pipeline(mutated_inputs, output, CONFIG_PATH, date(2026, 8, 1))

                direct = next(
                    row
                    for row in read_csv(output / "warm_paths.csv")
                    if row["connector_id"] == "connector-direct"
                )
                self.assertEqual(direct["direct_intro_score"], "0")
                self.assertEqual(direct["segment"], "review_warm_intro")
                self.assertIn(expected_error, direct["validation_errors"])

    def test_invalid_relationship_or_supporting_claim_cannot_leave_path_strong(self):
        mutations = {
            "relationship_type": (
                "evidence-owner-work",
                "evidence-talk-relay",
                "unsupported_relationship_evidence_type",
            ),
            "supporting_subject": (
                "evidence-talk-relay",
                "evidence-job-harbor",
                "wrong_supporting_subject",
            ),
        }
        for label, (before, after, expected_error) in mutations.items():
            with self.subTest(label=label), TemporaryDirectory() as directory:
                root = Path(directory)
                mutated_inputs = root / "inputs"
                shutil.copytree(INPUT_DIR, mutated_inputs)
                path = mutated_inputs / "connector_edges.csv"
                path.write_text(
                    path.read_text(encoding="utf-8").replace(before, after, 1),
                    encoding="utf-8",
                    newline="\n",
                )

                run_pipeline(
                    mutated_inputs,
                    root / "output",
                    CONFIG_PATH,
                    date(2026, 8, 1),
                )

                work = next(
                    row
                    for row in read_csv(root / "output" / "warm_paths.csv")
                    if row["connector_id"] == "connector-work"
                )
                self.assertEqual(work["work_overlap_score"], "30")
                self.assertEqual(work["segment"], "review_warm_intro")
                self.assertIn(expected_error, work["validation_errors"])

    def test_duplicate_primary_ids_fail_closed_before_maps_or_dedupe(self):
        cases = (
            ("accounts.csv", "account", "account_id"),
            ("contacts.csv", "contact", "contact_id"),
            ("connector_edges.csv", "connector edge", "edge_id"),
        )
        for filename, label, id_field in cases:
            with self.subTest(filename=filename), TemporaryDirectory() as directory:
                root = Path(directory)
                mutated_inputs = root / "inputs"
                shutil.copytree(INPUT_DIR, mutated_inputs)
                path = mutated_inputs / filename
                rows = read_csv(path)
                duplicate = dict(rows[0])
                duplicate[next(field for field in duplicate if field != id_field)] += " conflict"
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows([*rows, duplicate])

                with self.assertRaisesRegex(ValueError, f"duplicate {label} ID"):
                    run_pipeline(
                        mutated_inputs,
                        root / "output",
                        CONFIG_PATH,
                        date(2026, 8, 1),
                    )

    def test_source_privacy_gate_allows_only_example_linkedin_slugs_or_metavariables(self):
        roots = (
            PACKAGE_DIR,
            PACKAGE_DIR.parent / "warm-intro-scoring",
            PACKAGE_DIR.parent / "warm-intro-ask-threads",
            PACKAGE_DIR.parents[2] / "docs" / "superpowers",
        )
        linkedin_path = re.compile(
            r"(?:linkedin\.com|linkedin\.example)/in/([^\s\"'<>),]+)",
            re.IGNORECASE,
        )
        violations = []
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {
                    ".csv",
                    ".html",
                    ".json",
                    ".md",
                    ".py",
                }:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                for match in linkedin_path.finditer(text):
                    slug = match.group(1).rstrip("./")
                    if not (slug.casefold().startswith("example-") or slug.startswith("{")):
                        violations.append(f"{path}:{slug}")
        self.assertEqual(violations, [])

    def test_safe_alias_merge_remaps_foreign_keys_and_pdl_excludes_all_aliases(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            mutated_inputs = root / "inputs"
            shutil.copytree(INPUT_DIR, mutated_inputs)
            contacts_path = mutated_inputs / "contacts.csv"
            contacts = read_csv(contacts_path)
            alias = next(row for row in contacts if row["contact_id"] == "duplicate-relay-email")
            alias["linkedin_url"] = "linkedin.com/in/example-mina-sol-alias"
            with contacts_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(contacts[0]))
                writer.writeheader()
                writer.writerows(contacts)
            experiences_path = mutated_inputs / "experiences.csv"
            experiences_path.write_text(
                experiences_path.read_text(encoding="utf-8").replace(
                    "contact-relay-revops,Atlas Works",
                    "duplicate-relay-email,Atlas Works",
                ),
                encoding="utf-8",
                newline="\n",
            )
            for filename in (
                "experiences.csv",
                "interactions.csv",
                "org_edges.csv",
                "evidence.csv",
                "connector_edges.csv",
            ):
                dependent_path = mutated_inputs / filename
                dependent_path.write_text(
                    dependent_path.read_text(encoding="utf-8").replace(
                        "contact-northstar-gtm",
                        "duplicate-northstar-profile",
                    ),
                    encoding="utf-8",
                    newline="\n",
                )
            output = root / "output"

            run_pipeline(mutated_inputs, output, CONFIG_PATH, date(2026, 8, 1))

            work_path = next(
                row
                for row in read_csv(output / "warm_paths.csv")
                if row["connector_id"] == "connector-work"
            )
            self.assertEqual(work_path["work_overlap_score"], "30")
            direct_path = next(
                row
                for row in read_csv(output / "warm_paths.csv")
                if row["connector_id"] == "connector-direct"
            )
            self.assertEqual(
                (direct_path["target_id"], direct_path["direct_intro_score"]),
                ("contact-northstar-gtm", "60"),
            )
            direct_interaction = next(
                row
                for row in read_csv(output / "interaction_audit.csv")
                if row["interaction_id"] == "interaction-intro-northstar"
            )
            self.assertEqual(direct_interaction["target_id"], "contact-northstar-gtm")
            northstar_edge = next(
                row
                for row in read_csv(output / "org_edges_review.csv")
                if row["edge_id"] == "edge-northstar-report"
            )
            self.assertEqual(northstar_edge["from_contact_id"], "contact-northstar-gtm")
            requests = json.loads(
                (output / "pdl_gapfill_requests.json").read_text(encoding="utf-8")
            )["requests"]
            relay = next(row for row in requests if row["account_id"] == "relay-cloud.example")
            self.assertEqual(
                relay["exclusions"]["linkedin_urls"],
                [
                    "linkedin.com/in/example-mina-sol",
                    "linkedin.com/in/example-mina-sol-alias",
                ],
            )


if __name__ == "__main__":
    unittest.main()
