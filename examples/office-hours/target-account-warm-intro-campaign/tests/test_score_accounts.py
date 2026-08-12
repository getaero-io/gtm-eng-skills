"""Behavioral tests for transparent target-account ranking."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from schemas import AccountRecord, CampaignConfig  # noqa: E402
from score_accounts import rank_accounts, score_account  # noqa: E402


CONFIG_PATH = PACKAGE_DIR / "config.example.json"


def account(account_id: str, domain: str, **signals: object) -> AccountRecord:
    return AccountRecord(
        account_id=account_id,
        name=account_id.replace("-", " ").title(),
        domain=domain,
        source_metadata_json=json.dumps(signals),
    )


class AccountRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = CampaignConfig.from_mapping(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))

    def test_ranking_retains_exclusions_and_exposes_each_component(self):
        high_growth = account(
            "northstar",
            "northstar.example",
            is_b2b=True,
            engineering_led=True,
            open_roles=["GTM Engineer"],
            growth_recency_days=21,
            customer_similarity=True,
            first_party_engagement=True,
        )
        customer = account(
            "acme-customer",
            "acme-customer.example",
            is_b2b=True,
            engineering_led=True,
            open_roles=["GTM Engineer"],
            growth_recency_days=7,
            customer_similarity=True,
            first_party_engagement=True,
        )
        consumer = account("consumer", "consumer.example", is_b2b=False, open_roles=[])

        scores = rank_accounts((consumer, customer, high_growth), self.config)

        self.assertEqual([score.account_id for score in scores], ["northstar", "acme-customer", "consumer"])
        self.assertEqual(len(scores), 3)
        customer_score = next(score for score in scores if score.account_id == "acme-customer")
        self.assertEqual((customer_score.decision, customer_score.exclusion_reason), ("exclude", "existing_customer"))
        self.assertEqual(next(score for score in scores if score.account_id == "consumer").exclusion_reason, "non_b2b")
        for score in scores:
            with self.subTest(account_id=score.account_id):
                self.assertEqual(
                    score.total_score,
                    sum(
                        (
                            score.icp_fit,
                            score.engineering_led,
                            score.technical_gtm_signal,
                            score.growth_recency,
                            score.customer_similarity,
                            score.first_party_engagement,
                        )
                    ),
                )

    def test_score_components_stay_within_configured_integer_ranges(self):
        score = score_account(
            account(
                "overspecified",
                "overspecified.example",
                is_b2b=999,
                engineering_led=999,
                technical_gtm_signal=999,
                growth_recency=999,
                customer_similarity=999,
                first_party_engagement=999,
            ),
            self.config,
        )

        for field, maximum in self.config.score_weights.items():
            self.assertGreaterEqual(getattr(score, field), 0)
            self.assertLessEqual(getattr(score, field), maximum)

    def test_score_below_review_threshold_is_an_auditable_exclusion(self):
        score = score_account(account("low-fit", "low-fit.example", is_b2b=True), self.config)

        self.assertEqual((score.decision, score.exclusion_reason), ("exclude", "below_review_threshold"))


if __name__ == "__main__":
    unittest.main()
