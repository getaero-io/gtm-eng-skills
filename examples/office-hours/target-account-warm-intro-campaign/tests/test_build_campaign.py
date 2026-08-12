"""Behavioral tests for contact, committee, org, and interaction construction."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from build_campaign import (  # noqa: E402
    build_buying_committee,
    dedupe_contacts,
    person_centric_neighborhood,
    qualify_contact,
    summarize_interactions,
    validate_org_edges,
)
from schemas import CampaignConfig, ContactRecord, InteractionRecord, OrgEdgeRecord  # noqa: E402


def campaign_config(title_catalog=None) -> CampaignConfig:
    return CampaignConfig(
        campaign_id="test-campaign",
        owner_id="owner",
        as_of=date(2026, 8, 12),
        title_catalog=title_catalog or {},
        score_weights={},
        segment_thresholds={},
        exclusions={},
        provider_routes={},
        blocked_operations=(),
        cache_directory=Path(".cache/test"),
        provider_caps={},
        campaign_cap=Decimal("0"),
    )


class ContactDedupeTests(unittest.TestCase):
    def test_linkedin_url_variants_merge_and_preserve_source_ids(self):
        contacts = [
            ContactRecord(
                contact_id="contact-b",
                name="Alex Chen",
                company="Northstar AI",
                title="GTM Engineer",
                linkedin_url="https://www.linkedin.com/in/example-alex/?trk=public",
                source_record_ids=("pdl-22",),
            ),
            ContactRecord(
                contact_id="contact-a",
                name="Alex Chen",
                company="Northstar AI",
                title="GTM Engineer",
                linkedin_url="linkedin.com/in/example-alex/",
                source_record_ids=("crm-11",),
            ),
        ]

        result = dedupe_contacts(contacts)

        self.assertEqual(result.merge_groups, (("contact-a", "contact-b"),))
        self.assertEqual(len(result.canonical_records), 1)
        self.assertEqual(
            result.canonical_records[0].source_record_ids,
            ("crm-11", "pdl-22"),
        )

    def test_verified_work_email_merges_contacts(self):
        contacts = [
            ContactRecord(
                contact_id="contact-one",
                name="Morgan Lee",
                company="Relay Cloud",
                title="Revenue Systems Director",
                work_email="Morgan.Lee@Relay.Example",
            ),
            ContactRecord(
                contact_id="contact-two",
                name="Morgan Lee",
                company="Relay Cloud",
                title="Director, Revenue Systems",
                work_email="morgan.lee@relay.example",
            ),
        ]

        result = dedupe_contacts(contacts)

        self.assertEqual(result.merge_groups, (("contact-one", "contact-two"),))
        self.assertEqual(len(result.canonical_records), 1)

    def test_weak_identity_collision_routes_to_review_without_merging(self):
        contacts = [
            ContactRecord("weak-b", " Sam  Rivera ", "Harbor Systems", "VP RevOps"),
            ContactRecord("weak-a", "sam rivera", " harbor systems ", "vp revops"),
        ]

        result = dedupe_contacts(contacts)

        self.assertEqual(result.merge_groups, ())
        self.assertEqual(result.review_collisions, (("weak-a", "weak-b"),))
        self.assertEqual(
            tuple(contact.contact_id for contact in result.canonical_records),
            ("weak-a", "weak-b"),
        )

    def test_strong_identifiers_form_one_transitive_merge_group(self):
        contacts = [
            ContactRecord(
                "bridge",
                "Kai Morgan",
                "Relay Cloud",
                "GTM Engineer",
                linkedin_url="linkedin.com/in/example-kai",
                work_email="kai@relay.example",
            ),
            ContactRecord(
                "email-only",
                "Kai Morgan",
                "Relay Cloud",
                "GTM Engineer",
                work_email="KAI@RELAY.EXAMPLE",
            ),
            ContactRecord(
                "linkedin-only",
                "Kai Morgan",
                "Relay Cloud",
                "GTM Engineer",
                linkedin_url="https://www.linkedin.com/in/example-kai/",
            ),
        ]

        result = dedupe_contacts(contacts)

        self.assertEqual(
            result.merge_groups,
            (("bridge", "email-only", "linkedin-only"),),
        )
        self.assertEqual(len(result.canonical_records), 1)


class TitleQualificationTests(unittest.TestCase):
    def test_required_gtm_titles_have_explicit_role_families(self):
        expected = {
            "Head of GTM Engineering": "gtm_engineering",
            "Revenue Systems Manager": "revenue_systems",
            "VP RevOps": "revenue_operations",
            "Director, BizOps": "business_operations",
            "Growth Engineering Lead": "growth_engineering",
            "GTM Analytics Manager": "gtm_analytics",
            "Marketing Operations Director": "marketing_operations",
        }

        for number, (title, role_family) in enumerate(expected.items()):
            with self.subTest(title=title):
                result = qualify_contact(
                    ContactRecord(f"contact-{number}", "Test Person", "Northstar AI", title),
                    campaign_config(),
                )
                self.assertTrue(result.qualified)
                self.assertEqual(result.role_family, role_family)

    def test_unrelated_sales_and_recruiting_titles_do_not_qualify(self):
        for number, title in enumerate(("Enterprise Sales Director", "Technical Recruiter")):
            with self.subTest(title=title):
                result = qualify_contact(
                    ContactRecord(f"unrelated-{number}", "Test Person", "Northstar AI", title),
                    campaign_config(),
                )
                self.assertFalse(result.qualified)
                self.assertEqual(result.role_family, "")


class BuyingCommitteeTests(unittest.TestCase):
    def test_members_are_filtered_by_account_and_sorted_by_committee_role(self):
        config = campaign_config(
            {
                "revenue_leadership": {
                    "titles": ["Chief Revenue Officer"],
                    "committee_role": "economic_buyer",
                },
                "data_platform": {
                    "titles": ["Data Platform Architect"],
                    "committee_role": "adjacent_validator",
                },
            }
        )
        contacts = [
            ContactRecord("validator", "Vera", "Northstar AI", "Data Platform Architect", "northstar"),
            ContactRecord("economic", "Eli", "Northstar AI", "Chief Revenue Officer", "northstar"),
            ContactRecord("operational", "Omar", "Northstar AI", "Director of RevOps", "northstar"),
            ContactRecord("technical", "Toni", "Northstar AI", "GTM Engineer", "northstar"),
            ContactRecord("other-account", "Otto", "Relay Cloud", "GTM Engineer", "relay"),
            ContactRecord("unqualified", "Uma", "Northstar AI", "Technical Recruiter", "northstar"),
        ]

        committee = build_buying_committee("northstar", contacts, config)

        self.assertEqual(
            tuple(member.contact_id for member in committee),
            ("technical", "operational", "economic", "validator"),
        )
        self.assertEqual(
            tuple(member.committee_role for member in committee),
            (
                "technical_champion",
                "operational_buyer",
                "economic_buyer",
                "adjacent_validator",
            ),
        )


class OrgSemanticsTests(unittest.TestCase):
    def test_open_role_cannot_be_a_confirmed_reporting_edge_person(self):
        contacts = [
            ContactRecord("person", "Ari", "Northstar AI", "VP Revenue Operations"),
            ContactRecord(
                "open-role",
                "Open GTM Engineer",
                "Northstar AI",
                "GTM Engineer",
                source_metadata_json=json.dumps({"node_type": "open_role"}),
            ),
        ]
        edge = OrgEdgeRecord(
            "edge-open-role",
            "open-role",
            "person",
            "reports_to_confirmed",
            confidence="confirmed",
            source_evidence_ids=("job-evidence",),
        )

        with self.assertRaisesRegex(ValueError, "edge-open-role"):
            validate_org_edges([edge], contacts)

    def test_inferred_edge_type_and_evidence_are_preserved(self):
        contacts = [
            ContactRecord("person", "Ari", "Northstar AI", "VP Revenue Operations"),
            ContactRecord(
                "open-role",
                "Open GTM Engineer",
                "Northstar AI",
                "GTM Engineer",
                source_metadata_json=json.dumps({"node_type": "open_role"}),
            ),
        ]
        inferred = OrgEdgeRecord(
            "edge-inferred",
            "person",
            "open-role",
            "functional_proximity_inferred",
            confidence="medium",
            source_evidence_ids=("job-evidence", "post-evidence"),
        )

        self.assertEqual(validate_org_edges([inferred], contacts), [inferred])

    def test_inferred_confidence_cannot_be_labeled_as_confirmed_reporting(self):
        contacts = [
            ContactRecord("person-a", "Ari", "Northstar AI", "VP Revenue Operations"),
            ContactRecord("person-b", "Bo", "Northstar AI", "GTM Engineer"),
        ]
        edge = OrgEdgeRecord(
            "edge-mislabeled",
            "person-b",
            "person-a",
            "reports_to_confirmed",
            confidence="inferred",
        )

        with self.assertRaisesRegex(ValueError, "edge-mislabeled"):
            validate_org_edges([edge], contacts)

    def test_neighborhood_stops_at_three_levels_and_prevents_cycles(self):
        edges = [
            OrgEdgeRecord("edge-4", "person-3", "person-4", "reports_to_confirmed"),
            OrgEdgeRecord("edge-cycle", "person-2", "person-2", "reports_to_confirmed"),
            OrgEdgeRecord("edge-2", "person-1", "person-2", "reports_to_confirmed"),
            OrgEdgeRecord("edge-1", "target", "person-1", "reports_to_confirmed"),
            OrgEdgeRecord(
                "edge-3",
                "person-2",
                "person-3",
                "functional_proximity_inferred",
                confidence="low",
                source_evidence_ids=("evidence-3",),
            ),
        ]

        neighborhood = person_centric_neighborhood("target", edges)

        self.assertEqual(
            tuple(edge.edge_id for edge in neighborhood),
            ("edge-1", "edge-2", "edge-3"),
        )
        self.assertEqual(neighborhood[-1], edges[-1])


class InteractionAuditTests(unittest.TestCase):
    def test_prior_introduction_email_and_call_include_time_and_evidence(self):
        interactions = [
            InteractionRecord(
                "intro-1",
                "target",
                "crm",
                "introduction",
                datetime(2026, 7, 1, 14, 0, tzinfo=timezone.utc),
                evidence_id="evidence-intro",
            ),
            InteractionRecord(
                "email-1",
                "target",
                "email",
                "email",
                datetime(2026, 7, 2, 14, 0, tzinfo=timezone.utc),
                evidence_id="evidence-email",
            ),
            InteractionRecord(
                "call-1",
                "target",
                "sales_call",
                "call",
                datetime(2026, 7, 3, 14, 0, tzinfo=timezone.utc),
                evidence_id="evidence-call",
            ),
            InteractionRecord(
                "manual-intro",
                "target",
                "manual_confirmation",
                "relationship_confirmation",
                datetime(2026, 7, 4, 14, 0, tzinfo=timezone.utc),
                evidence_id="evidence-manual",
            ),
            InteractionRecord(
                "other-person",
                "other",
                "event",
                "meeting",
                datetime(2026, 7, 5, 14, 0, tzinfo=timezone.utc),
                evidence_id="evidence-other",
            ),
        ]

        summary = summarize_interactions("target", interactions)

        self.assertTrue(summary.has_direct_introduction)
        self.assertEqual(
            tuple(item.interaction_id for item in summary.direct_introductions),
            ("intro-1", "manual-intro"),
        )
        self.assertEqual(tuple(item.interaction_id for item in summary.emails), ("email-1",))
        self.assertEqual(tuple(item.interaction_id for item in summary.calls), ("call-1",))
        self.assertEqual(
            summary.evidence_ids,
            ("evidence-call", "evidence-email", "evidence-intro", "evidence-manual"),
        )
        for item in summary.interactions:
            self.assertIsNotNone(item.occurred_at)
            self.assertTrue(item.evidence_id)

    def test_source_enum_and_immutable_evidence_are_required(self):
        occurred_at = datetime(2026, 7, 1, 14, 0, tzinfo=timezone.utc)
        invalid_source = InteractionRecord(
            "unsupported-source",
            "target",
            "social_dm",
            "message",
            occurred_at,
            evidence_id="evidence-message",
        )
        missing_evidence = InteractionRecord(
            "unverified-manual-intro",
            "target",
            "manual_confirmation",
            "relationship_confirmation",
            occurred_at,
        )

        with self.assertRaisesRegex(ValueError, "unsupported-source"):
            summarize_interactions("target", [invalid_source])
        with self.assertRaisesRegex(ValueError, "unverified-manual-intro"):
            summarize_interactions("target", [missing_evidence])


if __name__ == "__main__":
    unittest.main()
