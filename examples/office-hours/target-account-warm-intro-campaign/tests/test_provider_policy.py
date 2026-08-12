"""Behavioral tests for explicit provider routing and spend controls."""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from provider_policy import ProviderPolicy, build_pdl_exclusions  # noqa: E402
from schemas import ContactRecord  # noqa: E402


CONFIG = PACKAGE_DIR / "config.example.json"


class ProviderPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ProviderPolicy.from_path(CONFIG)

    def test_provider_routes_are_explicit(self):
        self.assertEqual(self.policy.provider_for("company_jobs"), "sentrion")
        self.assertEqual(self.policy.provider_for("linkedin_person_posts"), "apify")
        self.assertEqual(self.policy.provider_for("x_posts"), "twitterapi")
        self.assertIn("bloomberry", self.policy.blocked_providers)
        self.assertTrue(self.policy.is_blocked("crustdata", "linkedin_person_posts"))

    def test_paid_call_requires_budget_and_cache_miss(self):
        decision = self.policy.authorize("pdl", "people_search", "account:northstar", Decimal("0.40"))
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "allowed")
        self.policy.record_call(decision, actual_cost_usd=Decimal("0.40"))
        cached = self.policy.authorize("pdl", "people_search", "account:northstar", Decimal("0.40"))
        self.assertFalse(cached.allowed)
        self.assertEqual(cached.reason, "cache_hit")

    def test_authorization_reports_provider_and_campaign_caps(self):
        provider_cap = self.policy.authorize("pdl", "people_search", "account:costly", Decimal("1.01"))
        campaign_cap = self.policy.authorize("public_web", "search", "account:costly", Decimal("5.01"))

        self.assertEqual(provider_cap.reason, "provider_cap")
        self.assertEqual(campaign_cap.reason, "campaign_cap")
        self.assertEqual(
            self.policy.authorize("bloomberry", "company_jobs", "account:block", Decimal("0")).reason,
            "blocked_provider",
        )
        self.assertEqual(
            self.policy.authorize("crustdata", "linkedin_person_posts", "account:block", Decimal("0")).reason,
            "blocked_operation",
        )

    def test_pdl_exclusions_normalize_and_sort_known_identifiers(self):
        exclusions = build_pdl_exclusions(
            (
                ContactRecord(
                    contact_id="alex",
                    name=" Alex  Chen ",
                    company="Northstar AI",
                    title="GTM Engineer",
                    linkedin_url="https://www.linkedin.com/in/Alex-Chen/?trk=public",
                    work_email="ALEX@NORTHSTAR.EXAMPLE",
                ),
                ContactRecord(
                    contact_id="blair",
                    name="Blair Kim",
                    company="Northstar AI",
                    title="RevOps",
                    linkedin_url="linkedin.com/in/blair-kim",
                ),
            )
        )

        self.assertEqual(exclusions.linkedin_urls, ("linkedin.com/in/alex-chen", "linkedin.com/in/blair-kim"))
        self.assertEqual(exclusions.emails, ("alex@northstar.example",))
        self.assertEqual(
            exclusions.identities,
            ("alex chen|northstar ai|gtm engineer", "blair kim|northstar ai|revops"),
        )


if __name__ == "__main__":
    unittest.main()
