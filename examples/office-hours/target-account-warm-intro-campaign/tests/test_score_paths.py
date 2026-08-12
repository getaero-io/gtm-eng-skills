"""Behavioral tests for evidence-backed warm-intro path scoring."""

from __future__ import annotations

import importlib.util
import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from schemas import CampaignConfig, ContactRecord, ExperienceRecord  # noqa: E402
from score_paths import (  # noqa: E402
    PathEvidence,
    employment_overlap,
    score_warm_path,
    segment_path,
)


def campaign_config(score_weights=None) -> CampaignConfig:
    return CampaignConfig(
        campaign_id="test-campaign",
        owner_id="owner",
        as_of=date(2026, 8, 12),
        title_catalog={},
        score_weights=score_weights or {},
        segment_thresholds={},
        exclusions={},
        provider_routes={},
        blocked_operations=(),
        cache_directory=Path(".cache/test"),
        provider_caps={},
        campaign_cap=Decimal("0"),
    )


CONNECTOR = ContactRecord(
    "connector", "Casey Morgan", "Relay Cloud", "VP Revenue Operations"
)
TARGET = ContactRecord(
    "target", "Taylor Kim", "Northstar AI", "Head of GTM Engineering"
)


def load_legacy_lookup():
    """Load the hyphenated legacy example as an isolated package by file path."""
    legacy_dir = PACKAGE_DIR.parent / "warm-intro-scoring"
    package_name = "_task4_legacy_warm_intro"
    package = types.ModuleType(package_name)
    package.__path__ = [str(legacy_dir)]
    sys.modules[package_name] = package

    for module_name in ("models", "db", "scorer"):
        spec = importlib.util.spec_from_file_location(
            f"{package_name}.{module_name}", legacy_dir / f"{module_name}.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.lookup", legacy_dir / "lookup.py"
    )
    assert spec is not None and spec.loader is not None
    lookup = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = lookup
    spec.loader.exec_module(lookup)
    return (
        lookup,
        sys.modules[f"{package_name}.models"],
        sys.modules[f"{package_name}.scorer"],
    )


class EmploymentOverlapTests(unittest.TestCase):
    def test_bounded_employment_ranges_overlap_inclusively(self):
        connector_role = ExperienceRecord(
            "connector-role",
            "connector",
            "Northstar AI",
            "Revenue Systems Lead",
            start_date=date(2021, 1, 1),
            end_date=date(2023, 6, 30),
        )
        target_role = ExperienceRecord(
            "target-role",
            "target",
            "Northstar AI, Inc.",
            "GTM Engineer",
            start_date=date(2022, 4, 1),
            end_date=date(2024, 1, 31),
        )

        overlap = employment_overlap(connector_role, target_role, date(2026, 8, 12))

        self.assertIsNotNone(overlap)
        assert overlap is not None
        self.assertEqual(overlap.start_date, date(2022, 4, 1))
        self.assertEqual(overlap.end_date, date(2023, 6, 30))
        self.assertEqual(overlap.company, "Northstar AI")

    def test_same_employer_with_non_overlapping_tenures_is_not_verified(self):
        former = ExperienceRecord(
            "former",
            "connector",
            "Relay Cloud",
            "VP Revenue Operations",
            start_date=date(2017, 1, 1),
            end_date=date(2019, 12, 31),
        )
        later = ExperienceRecord(
            "later",
            "target",
            "Relay Cloud",
            "Revenue Systems Manager",
            start_date=date(2020, 1, 1),
            end_date=date(2022, 1, 1),
        )

        self.assertIsNone(employment_overlap(former, later, date(2026, 8, 12)))

    def test_current_role_uses_as_of_as_the_open_end_date(self):
        current = ExperienceRecord(
            "current",
            "connector",
            "Harbor Systems",
            "GTM Engineer",
            start_date=date(2024, 1, 1),
            is_current=True,
        )
        bounded = ExperienceRecord(
            "bounded",
            "target",
            "Harbor Systems",
            "Director, RevOps",
            start_date=date(2025, 3, 1),
            end_date=date(2027, 1, 1),
        )

        overlap = employment_overlap(current, bounded, date(2026, 8, 12))

        self.assertIsNotNone(overlap)
        assert overlap is not None
        self.assertEqual(overlap.end_date, date(2026, 8, 12))

    def test_missing_dates_never_create_verified_overlap(self):
        missing_start = ExperienceRecord(
            "missing-start", "connector", "Harbor Systems", "GTM Engineer", is_current=True
        )
        complete = ExperienceRecord(
            "complete",
            "target",
            "Harbor Systems",
            "Director, RevOps",
            start_date=date(2025, 1, 1),
            is_current=True,
        )

        self.assertIsNone(employment_overlap(missing_start, complete, date(2026, 8, 12)))


class WarmPathScoreTests(unittest.TestCase):
    def test_default_path_weights_preserve_hierarchy_over_all_lower_tiers(self):
        score = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                direct_intro_evidence_ids=("intro-1",),
                connector_experiences=(
                    ExperienceRecord(
                        "connector-role",
                        CONNECTOR.contact_id,
                        "Northstar AI",
                        "Revenue Systems Lead",
                        start_date=date(2021, 1, 1),
                        end_date=date(2024, 1, 1),
                    ),
                ),
                target_experiences=(
                    ExperienceRecord(
                        "target-role",
                        TARGET.contact_id,
                        "Northstar AI",
                        "Head of GTM Engineering",
                        start_date=date(2022, 1, 1),
                        is_current=True,
                    ),
                ),
                shared_schools=tuple(f"School {number}" for number in range(8)),
                role_overlaps=tuple(f"Role {number}" for number in range(4)),
                investor_overlaps=tuple(f"Fund {number}" for number in range(4)),
                relationship_confidence="high",
            ),
            campaign_config(),
        )

        self.assertGreater(
            score.direct_intro_score,
            score.work_overlap_score
            + score.school_city_community_score
            + score.role_industry_score
            + score.investor_score,
        )
        self.assertGreater(
            score.work_overlap_score,
            score.school_city_community_score
            + score.role_industry_score
            + score.investor_score,
        )
        self.assertGreater(
            score.school_city_community_score,
            score.role_industry_score + score.investor_score,
        )
        self.assertGreater(score.role_industry_score, score.investor_score)

    def test_hostile_path_weights_cannot_invert_combined_tier_hierarchy(self):
        invalid_weights = (
            {
                "direct_intro": 30,
                "work_overlap": 20,
                "school_city_community": 8,
                "role_industry": 4,
                "investor": 3,
            },
            {
                "direct_intro": 50,
                "work_overlap": 20,
                "school_city_community": 15,
                "role_industry": 4,
                "investor": 3,
            },
        )

        for weights in invalid_weights:
            with self.subTest(weights=weights):
                with self.assertRaisesRegex(ValueError, "combined lower-tier maximum"):
                    score_warm_path(
                        CONNECTOR,
                        TARGET,
                        PathEvidence(direct_intro_evidence_ids=("intro-1",)),
                        campaign_config(weights),
                    )

    def test_confirmed_direct_intro_carries_target_metadata_and_evidence(self):
        score = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                direct_intro_evidence_ids=("intro-1",),
                relationship_confidence="high",
                relationship_evidence_ids=("relationship-1",),
            ),
            campaign_config(),
        )

        self.assertEqual(score.target_name, "Taylor Kim")
        self.assertEqual(score.target_title, "Head of GTM Engineering")
        self.assertEqual(score.evidence_ids, ("intro-1", "relationship-1"))
        self.assertTrue(score.reasons)
        self.assertGreater(score.direct_intro_score, 0)
        self.assertEqual(segment_path(score, campaign_config()), "strong_warm_intro")

    def test_dated_work_overlap_is_strong_but_ranks_below_direct_intro(self):
        direct_intro = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                direct_intro_evidence_ids=("intro-1",),
                relationship_confidence="high",
                relationship_evidence_ids=("relationship-1",),
            ),
            campaign_config(),
        )
        connector_role = ExperienceRecord(
            "connector-role",
            CONNECTOR.contact_id,
            "Northstar AI",
            "Revenue Systems Lead",
            start_date=date(2021, 1, 1),
            end_date=date(2024, 1, 1),
            source_record_id="experience-source-1",
        )
        target_role = ExperienceRecord(
            "target-role",
            TARGET.contact_id,
            "Northstar AI",
            "Head of GTM Engineering",
            start_date=date(2022, 1, 1),
            is_current=True,
            source_record_id="experience-source-2",
        )

        dated_work_overlap = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                connector_experiences=(connector_role,),
                target_experiences=(
                    target_role,
                    ExperienceRecord(
                        "unrelated-role",
                        TARGET.contact_id,
                        "Elsewhere Labs",
                        "Engineer",
                        start_date=date(2020, 1, 1),
                        end_date=date(2020, 12, 31),
                    ),
                ),
                relationship_confidence="high",
                relationship_evidence_ids=("relationship-1",),
            ),
            campaign_config(),
        )

        self.assertGreater(direct_intro.total_score, dated_work_overlap.total_score)
        self.assertGreater(dated_work_overlap.work_overlap_score, 0)
        self.assertIn("connector-role", dated_work_overlap.evidence_ids)
        self.assertIn("target-role", dated_work_overlap.evidence_ids)
        self.assertNotIn("unrelated-role", dated_work_overlap.evidence_ids)
        self.assertEqual(
            segment_path(dated_work_overlap, campaign_config()),
            "strong_warm_intro",
        )

    def test_same_employer_with_missing_dates_routes_to_review_without_work_points(self):
        score = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                connector_experiences=(
                    ExperienceRecord(
                        "connector-undated",
                        CONNECTOR.contact_id,
                        "Northstar AI",
                        "Revenue Systems Lead",
                        is_current=True,
                    ),
                ),
                target_experiences=(
                    ExperienceRecord(
                        "target-dated",
                        TARGET.contact_id,
                        "Northstar AI",
                        "Head of GTM Engineering",
                        start_date=date(2025, 1, 1),
                        is_current=True,
                    ),
                ),
                relationship_confidence="medium",
            ),
            campaign_config(),
        )

        self.assertEqual(score.work_overlap_score, 0)
        self.assertIn("company_proximity:Northstar AI:missing_dates", score.reasons)
        self.assertEqual(segment_path(score, campaign_config()), "review_warm_intro")

    def test_same_employer_non_overlapping_dates_route_to_review_without_work_points(self):
        score = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                connector_experiences=(
                    ExperienceRecord(
                        "connector-former",
                        CONNECTOR.contact_id,
                        "Northstar AI",
                        "Revenue Systems Lead",
                        start_date=date(2018, 1, 1),
                        end_date=date(2020, 12, 31),
                    ),
                ),
                target_experiences=(
                    ExperienceRecord(
                        "target-later",
                        TARGET.contact_id,
                        "Northstar AI",
                        "Head of GTM Engineering",
                        start_date=date(2021, 1, 1),
                        end_date=date(2024, 1, 1),
                    ),
                ),
                relationship_confidence="medium",
            ),
            campaign_config(),
        )

        self.assertEqual(score.work_overlap_score, 0)
        self.assertIn("company_proximity:Northstar AI:non_overlapping_dates", score.reasons)
        self.assertEqual(segment_path(score, campaign_config()), "review_warm_intro")

    def test_ancillary_signals_rank_below_dated_work_and_investor_is_capped(self):
        dated_work_overlap = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                connector_experiences=(
                    ExperienceRecord(
                        "connector-role",
                        CONNECTOR.contact_id,
                        "Northstar AI",
                        "Revenue Systems Lead",
                        start_date=date(2021, 1, 1),
                        end_date=date(2024, 1, 1),
                    ),
                ),
                target_experiences=(
                    ExperienceRecord(
                        "target-role",
                        TARGET.contact_id,
                        "Northstar AI",
                        "Head of GTM Engineering",
                        start_date=date(2022, 1, 1),
                        is_current=True,
                    ),
                ),
                relationship_confidence="high",
            ),
            campaign_config(),
        )
        school_city_social = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                shared_schools=("State University",),
                shared_cities=("New York",),
                shared_communities=("Revenue Builders",),
                shared_appearances=("GTM Systems Live",),
                role_overlaps=("revenue systems",),
                relationship_confidence="high",
                supporting_evidence_ids=("school-1", "city-1", "community-1"),
            ),
            campaign_config(),
        )
        investor_only = score_warm_path(
            CONNECTOR,
            TARGET,
            PathEvidence(
                investor_overlaps=("Seed Fund", "Growth Fund", "Operator Fund", "Fourth Fund"),
                supporting_evidence_ids=("investor-1",),
            ),
            campaign_config(),
        )

        self.assertGreater(dated_work_overlap.total_score, school_city_social.total_score)
        self.assertLessEqual(investor_only.investor_score, 3)
        self.assertEqual(segment_path(investor_only, campaign_config()), "no_strong_path")
        self.assertEqual(investor_only.evidence_ids, ("investor-1",))


class LegacyCsvExportTests(unittest.TestCase):
    def test_csv_has_stable_contract_and_deterministic_score_name_sort(self):
        lookup_module, models, _ = load_legacy_lookup()
        alice = models.Contact(
            "alice", "Alice", "Zephyr", "linkedin.com/in/alice", current_company="Relay Cloud"
        )
        zoe = models.Contact(
            "zoe", "zoe", "Alpha", "linkedin.com/in/zoe", current_company="Harbor Systems"
        )
        matches = [
            models.WarmIntroMatch(
                contact=zoe,
                score=10,
                path_id="path-zoe",
                shared_signal="verified_work_overlap",
                shared_detail="Northstar AI, 2022-01-01 to 2023-01-01",
                work_overlap_score=8,
                relationship_score=2,
                segment="strong_warm_intro",
                evidence_ids=("work-z",),
            ),
            models.WarmIntroMatch(
                contact=alice,
                score=10,
                path_id="path-alice",
                shared_signal="company_proximity",
                shared_detail="Northstar AI; employment dates unavailable",
                work_overlap_score=8,
                relationship_score=2,
                segment="review_warm_intro",
                evidence_ids=("company-a",),
            ),
        ]
        output = io.StringIO(newline="")
        instance = object.__new__(lookup_module.WarmIntroLookup)

        instance.export_csv(
            matches,
            output,
            target_name="Taylor Kim",
            target_title="Head of GTM Engineering",
            target_company="Northstar AI",
        )

        rows = output.getvalue().splitlines()
        self.assertEqual(
            rows[0],
            "path_id,connector_name,connector_linkedin,connector_company,target_name,"
            "target_title,target_company,shared_signal,shared_detail,relationship_confidence,"
            "direct_intro_score,work_overlap_score,relationship_score,"
            "school_city_community_score,role_industry_score,investor_score,total_score,"
            "segment,evidence_ids",
        )
        self.assertTrue(rows[1].startswith("path-alice,Alice Zephyr,"))
        self.assertTrue(rows[2].startswith("path-zoe,zoe Alpha,"))
        self.assertTrue(output.getvalue().endswith("\n"))
        self.assertNotIn("\r\n", output.getvalue())


class LegacyCliTests(unittest.TestCase):
    def test_csv_supplements_human_output_and_quiet_suppresses_it(self):
        lookup_module, models, _ = load_legacy_lookup()
        real_lookup_class = lookup_module.WarmIntroLookup
        match = models.WarmIntroMatch(
            contact=models.Contact(
                "connector",
                "Casey",
                "Morgan",
                "linkedin.com/in/casey",
                current_company="Relay Cloud",
            ),
            score=10,
            path_id="path-connector",
            shared_signal="company_proximity",
            shared_detail="Northstar AI; dates require review",
            segment="review_warm_intro",
            evidence_ids=("company-1",),
        )

        class FakeDB:
            def __init__(self, path):
                self.path = path

            def init(self):
                return None

            def get_contact_count(self):
                return 1

            def get_enriched_count(self):
                return 1

            def close(self):
                return None

        class FakeLookup:
            CSV_FIELDNAMES = real_lookup_class.CSV_FIELDNAMES

            def __init__(self, db):
                self.db = db

            def search(self, **kwargs):
                return [match]

            def export_csv(self, *args, **kwargs):
                return real_lookup_class.export_csv(self, *args, **kwargs)

            def print_results(self, *args, **kwargs):
                return real_lookup_class.print_results(self, *args, **kwargs)

        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            normal_csv = output_dir / "normal.csv"
            quiet_csv = output_dir / "quiet.csv"
            base_args = [
                "lookup.py",
                "--company",
                "Northstar AI",
                "--target-name",
                "Taylor Kim",
                "--target-title",
                "Head of GTM Engineering",
            ]

            with (
                patch.object(lookup_module, "WarmIntroDB", FakeDB),
                patch.object(lookup_module, "WarmIntroLookup", FakeLookup),
            ):
                human_output = io.StringIO()
                with patch.object(sys, "argv", [*base_args, "--csv", str(normal_csv)]):
                    with redirect_stdout(human_output):
                        self.assertEqual(lookup_module.main(), 0)

                quiet_output = io.StringIO()
                with patch.object(
                    sys,
                    "argv",
                    [*base_args, "--csv", str(quiet_csv), "--quiet"],
                ):
                    with redirect_stdout(quiet_output):
                        self.assertEqual(lookup_module.main(), 0)

            self.assertIn("Database: 1 contacts (1 enriched)", human_output.getvalue())
            self.assertIn("Found 1 match(es)", human_output.getvalue())
            self.assertIn("Casey Morgan", human_output.getvalue())
            self.assertEqual(quiet_output.getvalue(), "")
            self.assertEqual(normal_csv.read_bytes(), quiet_csv.read_bytes())
            self.assertIn(b"path-connector,Casey Morgan", normal_csv.read_bytes())


class LegacyScorerCompatibilityTests(unittest.TestCase):
    def test_target_scorer_direct_intro_outranks_all_combined_lower_tiers(self):
        _, models, scorer_module = load_legacy_lookup()
        connector = models.Contact(
            "connector", "Casey", "Morgan", "linkedin.com/in/casey"
        )
        target = models.Contact(
            "target",
            "Taylor",
            "Kim",
            "linkedin.com/in/taylor",
            current_company="Northstar AI",
        )
        scorer = scorer_module.WarmIntroScorer()
        direct = scorer.score_target_connector(
            connector,
            [],
            target,
            [],
            relationship_confidence="high",
            direct_intro_evidence_ids=("intro-1",),
        )
        combined_lower_tiers = scorer.score_target_connector(
            connector,
            [
                models.Experience(
                    "connector-role",
                    connector.id,
                    "Northstar AI",
                    start_date=date(2021, 1, 1),
                    end_date=date(2024, 1, 1),
                )
            ],
            target,
            [
                models.Experience(
                    "target-role",
                    target.id,
                    "Northstar AI, Inc.",
                    start_date=date(2022, 1, 1),
                    is_current=True,
                )
            ],
            relationship_confidence="high",
            shared_schools=tuple(f"School {number}" for number in range(5)),
            shared_cities=tuple(f"City {number}" for number in range(5)),
            role_industry_matches=tuple(f"Role {number}" for number in range(5)),
            investor_overlaps=tuple(f"Fund {number}" for number in range(5)),
            as_of=date(2026, 8, 12),
        )

        self.assertGreater(direct.total_score, combined_lower_tiers.total_score)

    def test_original_company_lookup_labels_name_match_as_proximity(self):
        _, models, scorer_module = load_legacy_lookup()
        connector = models.Contact(
            "connector",
            "Casey",
            "Morgan",
            "linkedin.com/in/casey",
            current_company="Northstar AI",
            current_position="VP Revenue Operations",
        )

        match = scorer_module.WarmIntroScorer().score_contact(
            connector,
            experiences=[],
            educations=[],
            target_company="Northstar AI",
            target_school=None,
            target_role=None,
        )

        self.assertEqual(match.shared_signal, "company_proximity")
        self.assertEqual(match.work_overlap_score, 0)
        self.assertNotIn("verified_work_overlap", match.reasons)

    def test_target_connector_entry_point_verifies_dated_overlap(self):
        _, models, scorer_module = load_legacy_lookup()
        connector = models.Contact(
            "connector",
            "Casey",
            "Morgan",
            "linkedin.com/in/casey",
            current_company="Relay Cloud",
            current_position="VP Revenue Operations",
        )
        target = models.Contact(
            "target",
            "Taylor",
            "Kim",
            "linkedin.com/in/taylor",
            current_company="Northstar AI",
            current_position="Head of GTM Engineering",
        )

        match = scorer_module.WarmIntroScorer().score_target_connector(
            connector=connector,
            connector_experiences=[
                models.Experience(
                    "connector-role",
                    connector.id,
                    "Northstar AI",
                    start_date=date(2021, 1, 1),
                    end_date=date(2024, 1, 1),
                )
            ],
            target=target,
            target_experiences=[
                models.Experience(
                    "target-role",
                    target.id,
                    "Northstar AI, Inc.",
                    start_date=date(2022, 1, 1),
                    is_current=True,
                )
            ],
            relationship_confidence="high",
            relationship_evidence_ids=("relationship-1",),
            as_of=date(2026, 8, 12),
        )

        self.assertEqual(match.target_name, "Taylor Kim")
        self.assertEqual(match.target_title, "Head of GTM Engineering")
        self.assertEqual(match.shared_signal, "verified_work_overlap")
        self.assertIn("2022-01-01", match.shared_detail)
        self.assertGreater(match.work_overlap_score, 0)
        self.assertEqual(match.segment, "strong_warm_intro")
        self.assertEqual(
            match.evidence_ids,
            ("connector-role", "relationship-1", "target-role"),
        )

    def test_fuzzy_employer_match_is_proximity_not_verified_overlap(self):
        _, models, scorer_module = load_legacy_lookup()
        connector = models.Contact(
            "connector",
            "Casey",
            "Morgan",
            "linkedin.com/in/casey",
            current_company="Relay Cloud",
        )
        target = models.Contact(
            "target",
            "Taylor",
            "Kim",
            "linkedin.com/in/taylor",
            current_company="Acme Security",
        )

        match = scorer_module.WarmIntroScorer().score_target_connector(
            connector=connector,
            connector_experiences=[
                models.Experience(
                    "connector-acme",
                    connector.id,
                    "Acme",
                    start_date=date(2021, 1, 1),
                    end_date=date(2024, 1, 1),
                )
            ],
            target=target,
            target_experiences=[
                models.Experience(
                    "target-acme-security",
                    target.id,
                    "Acme Security",
                    start_date=date(2022, 1, 1),
                    end_date=date(2023, 1, 1),
                )
            ],
            relationship_confidence="high",
            as_of=date(2026, 8, 12),
        )

        self.assertEqual(match.work_overlap_score, 0)
        self.assertEqual(match.shared_signal, "company_proximity")
        self.assertEqual(match.segment, "review_warm_intro")
        self.assertFalse(any("verified_work_overlap" in reason for reason in match.reasons))


if __name__ == "__main__":
    unittest.main()
