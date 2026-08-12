"""Behavioral tests for the campaign's shared data contracts."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from schemas import (  # noqa: E402
    AccountRecord,
    CampaignConfig,
    ContactRecord,
    PathScore,
    canonical_contact_key,
    load_csv_records,
    normalize_domain,
    write_csv_records,
)


@dataclass(frozen=True)
class SupportedValueRecord:
    record_id: str
    count: int
    enabled: bool
    amount: Decimal
    location: Path
    day: date
    observed_at: datetime
    optional_count: int | None
    source_ids: tuple[str, ...]
    source_metadata_json: str = "{}"


class IdentityResolutionTests(unittest.TestCase):
    def test_contact_key_prefers_linkedin_then_email_then_fallback(self):
        linkedin = ContactRecord(
            contact_id="a",
            name="Alex Chen",
            company="Northstar AI",
            title="GTM Engineer",
            linkedin_url="https://www.linkedin.com/in/example-alex-chen/",
        )
        email = ContactRecord(
            contact_id="b",
            name="Alex Chen",
            company="Northstar AI",
            title="GTM Engineer",
            work_email="ALEX@NORTHSTAR.EXAMPLE",
        )
        fallback = ContactRecord(
            contact_id="c",
            name="Alex Chen",
            company="Northstar AI",
            title="GTM Engineer",
        )

        self.assertEqual(
            canonical_contact_key(linkedin),
            ("linkedin", "linkedin.com/in/example-alex-chen"),
        )
        self.assertEqual(
            canonical_contact_key(email),
            ("email", "alex@northstar.example"),
        )
        self.assertEqual(canonical_contact_key(fallback)[0], "identity")

    def test_domain_normalization_rejects_non_domain_noise(self):
        self.assertEqual(
            normalize_domain("https://www.northstar.example/careers"),
            "northstar.example",
        )
        with self.assertRaises(ValueError):
            normalize_domain("Northstar AI")

    def test_contact_key_requires_complete_fallback_identity(self):
        partial = ContactRecord(
            contact_id="partial",
            name="Alex Chen",
            company="Northstar AI",
            title="",
        )
        blank = ContactRecord(contact_id="blank", name="", company="", title="")

        for contact in (partial, blank):
            with self.subTest(contact_id=contact.contact_id):
                with self.assertRaisesRegex(ValueError, "review required"):
                    canonical_contact_key(contact)


class CsvContractTests(unittest.TestCase):
    def test_csv_round_trip_is_utf8_with_stable_columns_and_newlines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "accounts.csv"
            fieldnames = ("account_id", "name", "domain")
            write_csv_records(
                path,
                [{"account_id": "northstar", "name": "Northstar AI", "domain": "northstar.example"}],
                fieldnames,
            )

            self.assertEqual(
                path.read_bytes(),
                b"account_id,name,domain\nnorthstar,Northstar AI,northstar.example\n",
            )
            self.assertEqual(load_csv_records(path, AccountRecord)[0].domain, "northstar.example")

    def test_csv_load_retains_unknown_source_columns_as_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "accounts.csv"
            path.write_text(
                "account_id,name,domain,provider_note\nnorthstar,Northstar AI,northstar.example,priority account\n",
                encoding="utf-8",
                newline="",
            )

            account = load_csv_records(path, AccountRecord)[0]
            self.assertEqual(
                json.loads(account.source_metadata_json),
                {"provider_note": "priority account"},
            )

    def test_csv_load_rejects_missing_required_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "accounts.csv"
            with path.open("w", encoding="utf-8", newline="") as output:
                csv.DictWriter(output, fieldnames=("account_id", "name")).writeheader()

            with self.assertRaisesRegex(ValueError, "missing required columns: domain"):
                load_csv_records(path, AccountRecord)

    def test_csv_round_trips_every_supported_value_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "supported.csv"
            record = SupportedValueRecord(
                record_id="record-1",
                count=3,
                enabled=True,
                amount=Decimal("0.40"),
                location=Path("cache/record-1"),
                day=date(2026, 8, 1),
                observed_at=datetime(2026, 8, 1, 10, 30, 0),
                optional_count=None,
                source_ids=("source-1", "source-2"),
            )
            write_csv_records(path, [record.__dict__], tuple(record.__dict__))

            self.assertIn(b'"[""source-1"",""source-2""]"', path.read_bytes())
            self.assertEqual(load_csv_records(path, SupportedValueRecord), [record])

    def test_csv_round_trips_tuple_ids_on_campaign_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "interactions.csv"
            row = {
                "interaction_id": "interaction-1",
                "contact_id": "target-1",
                "source": "crm",
                "interaction_type": "introduction",
                "participant_ids": ("owner-1", "connector-1"),
                "evidence_id": "evidence-1",
            }
            write_csv_records(path, [row], tuple(row))

            from schemas import InteractionRecord  # noqa: PLC0415

            interaction = load_csv_records(path, InteractionRecord)[0]
            self.assertEqual(interaction.participant_ids, ("owner-1", "connector-1"))


class ImmutableRecordTests(unittest.TestCase):
    def test_path_score_derives_total_from_its_components(self):
        score = PathScore(
            path_id="path-1",
            connector_id="connector-1",
            target_id="target-1",
            target_name="Alex Chen",
            target_title="GTM Engineer",
            target_company="Northstar AI",
            direct_intro_score=8,
            work_overlap_score=5,
            investor_score=2,
        )

        self.assertEqual(score.total_score, 15)
        with self.assertRaises(TypeError):
            PathScore(
                path_id="path-2",
                connector_id="connector-1",
                target_id="target-1",
                target_name="Alex Chen",
                target_title="GTM Engineer",
                target_company="Northstar AI",
                total_score=99,
            )

    def test_campaign_config_converts_money_to_decimal_and_freezes_cap_maps(self):
        config = CampaignConfig(
            campaign_id="campaign-1",
            owner_id="owner-1",
            as_of=date(2026, 8, 1),
            title_catalog={},
            score_weights={},
            segment_thresholds={},
            exclusions={},
            provider_routes={},
            blocked_operations=(),
            cache_directory=Path(".cache"),
            provider_caps={"pdl": "0.40"},
            campaign_cap="10.00",
        )

        self.assertEqual(config.provider_caps["pdl"], Decimal("0.40"))
        self.assertEqual(config.campaign_cap, Decimal("10.00"))
        with self.assertRaises(TypeError):
            config.provider_caps["pdl"] = Decimal("1.00")

    def test_campaign_config_deep_freezes_and_copies_title_catalog(self):
        title_catalog = {
            "gtm_engineering": {
                "titles": ["GTM Engineer"],
                "criteria": {"seniority": ["director"]},
            }
        }
        config = CampaignConfig(
            campaign_id="campaign-1",
            owner_id="owner-1",
            as_of=date(2026, 8, 1),
            title_catalog=title_catalog,
            score_weights={},
            segment_thresholds={},
            exclusions={},
            provider_routes={},
            blocked_operations=(),
            cache_directory=Path(".cache"),
            provider_caps={},
            campaign_cap="10.00",
        )
        title_catalog["gtm_engineering"]["titles"].append("Revenue Systems")
        title_catalog["gtm_engineering"]["criteria"]["seniority"].append("vp")

        self.assertEqual(config.title_catalog["gtm_engineering"]["titles"], ("GTM Engineer",))
        self.assertEqual(
            config.title_catalog["gtm_engineering"]["criteria"]["seniority"],
            ("director",),
        )
        with self.assertRaises(TypeError):
            config.title_catalog["gtm_engineering"]["criteria"]["new"] = "value"


if __name__ == "__main__":
    unittest.main()
