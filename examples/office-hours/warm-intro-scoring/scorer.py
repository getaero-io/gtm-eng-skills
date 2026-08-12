"""Similarity scoring engine for warm intro matches."""
import hashlib
import re
import unicodedata
from datetime import date
from typing import Optional

from .models import Contact, Experience, Education, PublicAppearance, WarmIntroMatch
from .db import WarmIntroDB


class WarmIntroScorer:
    """Score potential warm intro connections based on shared attributes."""

    # Scoring weights
    WEIGHT_SAME_COMPANY = 50.0
    WEIGHT_SAME_SCHOOL = 20.0
    WEIGHT_SAME_INDUSTRY = 10.0
    WEIGHT_ROLE_OVERLAP = 15.0
    WEIGHT_RECENCY = 5.0
    WEIGHT_SHARED_APPEARANCE = 40.0  # Strong signal - same podcast/event
    WEIGHT_DIRECT_INTRO = 160.0
    WEIGHT_VERIFIED_WORK_OVERLAP = 80.0
    WEIGHT_SCHOOL_CITY_COMMUNITY = 40.0
    WEIGHT_ROLE_INDUSTRY = 20.0
    MAX_INVESTOR_SCORE = 3.0

    # Common company suffixes to strip during normalization
    COMPANY_SUFFIXES = [
        "inc",
        "inc.",
        "incorporated",
        "llc",
        "l.l.c.",
        "ltd",
        "ltd.",
        "limited",
        "corp",
        "corp.",
        "corporation",
        "co",
        "co.",
        "company",
        "plc",
        "gmbh",
        "ag",
        "sa",
        "srl",
        "bv",
        "nv",
        "pty",
        "pte",
        # Domain suffixes (for companies like "Prove.com")
        "com",
        "io",
        "ai",
        "co",
        "net",
        "org",
    ]

    # School name variations to normalize
    SCHOOL_SUFFIXES = [
        "university",
        "univ",
        "univ.",
        "college",
        "institute",
        "inst",
        "inst.",
        "school",
        "academy",
    ]

    # Platform stopwords to remove during normalization
    PLATFORM_STOPWORDS = [
        "the",
        "podcast",
        "show",
        "talks",
        "radio",
        "fm",
        "am",
    ]

    EMPLOYER_LEGAL_SUFFIXES = {
        "ag",
        "bv",
        "co",
        "company",
        "corp",
        "corporation",
        "gmbh",
        "inc",
        "incorporated",
        "limited",
        "llc",
        "ltd",
        "nv",
        "plc",
        "pte",
        "pty",
        "sa",
        "srl",
    }
    DOTTED_LEGAL_SUFFIXES = {
        ("i", "n", "c"),
        ("l", "l", "c"),
        ("l", "t", "d"),
    }

    def __init__(self, db: Optional[WarmIntroDB] = None):
        """Initialize scorer with optional database connection."""
        self.db = db

    def normalize_company(self, name: str) -> str:
        """Normalize company name for comparison.

        - Lowercase
        - Strip whitespace
        - Remove punctuation (except for internal use)
        - Remove common suffixes (Inc, LLC, Ltd, Corp, etc.)
        """
        if not name:
            return ""

        # Unicode normalization (NFKD decomposes accents, then we keep only ASCII)
        normalized = unicodedata.normalize("NFKD", name)
        normalized = normalized.encode("ascii", "ignore").decode("ascii")

        # Lowercase and strip
        normalized = normalized.lower().strip()

        # Replace punctuation with spaces (so "Prove.com" -> "prove com")
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Split into words (collapses multiple spaces)
        words = normalized.split()

        # Remove trailing suffix words
        while words and words[-1] in self.COMPANY_SUFFIXES:
            words.pop()

        return " ".join(words).strip()

    def normalize_employer_identity(self, name: str) -> str:
        """Canonicalize legal-name noise without dropping meaningful identity tokens."""
        if not name:
            return ""
        normalized = unicodedata.normalize("NFKD", name)
        normalized = normalized.encode("ascii", "ignore").decode("ascii")
        words = re.sub(r"[^\w\s]", " ", normalized.casefold()).split()
        while words:
            if words[-1] in self.EMPLOYER_LEGAL_SUFFIXES:
                words.pop()
                continue
            dotted_suffix = next(
                (
                    suffix
                    for suffix in self.DOTTED_LEGAL_SUFFIXES
                    if len(words) >= len(suffix) and tuple(words[-len(suffix) :]) == suffix
                ),
                None,
            )
            if dotted_suffix is None:
                break
            del words[-len(dotted_suffix) :]
        return " ".join(words)

    def normalize_school(self, name: str) -> str:
        """Normalize school name for comparison.

        - Lowercase
        - Handle university/college/institute variations
        """
        if not name:
            return ""

        # Unicode normalization
        normalized = unicodedata.normalize("NFKD", name)
        normalized = normalized.encode("ascii", "ignore").decode("ascii")

        # Lowercase and strip
        normalized = normalized.lower().strip()

        # Remove punctuation (but keep alphanumeric and spaces)
        normalized = re.sub(r"[^\w\s]", "", normalized)

        return normalized.strip()

    def company_matches(self, company1: str, company2: str) -> bool:
        """Check if two company names match after normalization.

        Supports exact match and word-boundary-aware substring matching.
        """
        if not company1 or not company2:
            return False

        norm1 = self.normalize_company(company1)
        norm2 = self.normalize_company(company2)

        if not norm1 or not norm2:
            return False

        # Exact match
        if norm1 == norm2:
            return True

        # Word-boundary aware substring match
        # "Anthropic" matches "Anthropic AI" but "Apple" doesn't match "Pineapple"
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        # Check if one is a subset of the other (all words match)
        if words1.issubset(words2) or words2.issubset(words1):
            return True

        return False

    def school_matches(self, school1: str, school2: str) -> bool:
        """Check if two school names match after normalization.

        Supports exact match and word-boundary-aware substring matching.
        """
        if not school1 or not school2:
            return False

        norm1 = self.normalize_school(school1)
        norm2 = self.normalize_school(school2)

        if not norm1 or not norm2:
            return False

        # Exact match
        if norm1 == norm2:
            return True

        # Word-boundary aware substring match
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        # Check if one is a subset of the other (all words match)
        if words1.issubset(words2) or words2.issubset(words1):
            return True

        return False

    def normalize_platform(self, name: str) -> str:
        """Normalize platform name for comparison.

        - Lowercase
        - Strip whitespace
        - Remove punctuation
        - Remove common words (the, podcast, show, etc.)
        """
        if not name:
            return ""

        # Unicode normalization
        normalized = unicodedata.normalize("NFKD", name)
        normalized = normalized.encode("ascii", "ignore").decode("ascii")

        # Lowercase and strip
        normalized = normalized.lower().strip()

        # Remove punctuation
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Remove stopwords
        words = [w for w in normalized.split() if w not in self.PLATFORM_STOPWORDS]

        return " ".join(words).strip()

    def platform_matches(self, platform1: str, platform2: str) -> bool:
        """Check if two platform names match after normalization.

        Supports exact match and word-boundary-aware substring matching.
        """
        if not platform1 or not platform2:
            return False

        norm1 = self.normalize_platform(platform1)
        norm2 = self.normalize_platform(platform2)

        if not norm1 or not norm2:
            return False

        # Exact match
        if norm1 == norm2:
            return True

        # Word-boundary aware substring match
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        # Check if one is a subset of the other (all words match)
        if words1.issubset(words2) or words2.issubset(words1):
            return True

        return False

    def get_recency_boost(self, connected_on: Optional[date]) -> float:
        """Calculate recency boost based on connection date.

        Returns a value between 0.5 and 1.0:
        - 1.0 for connections within the last 30 days
        - Linear decay down to 0.5 for connections older than 3 years
        """
        if connected_on is None:
            return 0.5  # Minimum boost for unknown connection date

        today = date.today()
        days_ago = (today - connected_on).days

        # Recent connections (within 30 days) get max boost
        if days_ago <= 30:
            return 1.0

        # Connections older than 3 years get minimum boost
        max_age_days = 365 * 3
        if days_ago >= max_age_days:
            return 0.5

        # Linear interpolation between 1.0 and 0.5
        # At 30 days: 1.0, at 3 years: 0.5
        age_range = max_age_days - 30
        age_normalized = (days_ago - 30) / age_range
        return 1.0 - (age_normalized * 0.5)

    def score_target_connector(
        self,
        connector: Contact,
        connector_experiences: list[Experience],
        target: Contact,
        target_experiences: list[Experience],
        relationship_confidence: str = "unknown",
        direct_intro_evidence_ids: tuple[str, ...] = (),
        relationship_evidence_ids: tuple[str, ...] = (),
        shared_schools: tuple[str, ...] = (),
        shared_cities: tuple[str, ...] = (),
        shared_communities: tuple[str, ...] = (),
        shared_appearances: tuple[str, ...] = (),
        role_industry_matches: tuple[str, ...] = (),
        investor_overlaps: tuple[str, ...] = (),
        evidence_ids: tuple[str, ...] = (),
        as_of: Optional[date] = None,
    ) -> WarmIntroMatch:
        """Score explicit connector-to-target evidence without changing legacy lookup scoring."""
        scoring_date = as_of or date.today()
        confidence = relationship_confidence.strip().casefold() or "unknown"
        relationship_score = {
            "low": 5.0,
            "medium": 10.0,
            "high": 15.0,
            "confirmed": 15.0,
        }.get(confidence, 0.0)
        direct_intro_score = self.WEIGHT_DIRECT_INTRO if direct_intro_evidence_ids else 0.0

        overlaps: list[tuple[Experience, Experience, date, date]] = []
        company_proximities: set[str] = set()
        for connector_role in connector_experiences:
            for target_role in target_experiences:
                if not self.company_matches(connector_role.company_name, target_role.company_name):
                    continue
                company_proximities.add(connector_role.company_name)
                if self.normalize_employer_identity(
                    connector_role.company_name
                ) != self.normalize_employer_identity(target_role.company_name):
                    continue
                if connector_role.start_date is None or target_role.start_date is None:
                    continue
                connector_end = connector_role.end_date or (
                    scoring_date if connector_role.is_current else None
                )
                target_end = target_role.end_date or (
                    scoring_date if target_role.is_current else None
                )
                if connector_end is None or target_end is None:
                    continue
                overlap_start = max(connector_role.start_date, target_role.start_date)
                overlap_end = min(connector_end, target_end, scoring_date)
                if overlap_start <= overlap_end:
                    overlaps.append(
                        (connector_role, target_role, overlap_start, overlap_end)
                    )

        work_overlap_score = self.WEIGHT_VERIFIED_WORK_OVERLAP if overlaps else 0.0
        community_values = tuple(
            dict.fromkeys(
                (*shared_schools, *shared_cities, *shared_communities, *shared_appearances)
            )
        )
        school_city_community_score = (
            self.WEIGHT_SCHOOL_CITY_COMMUNITY if community_values else 0.0
        )
        role_industry_score = self.WEIGHT_ROLE_INDUSTRY if role_industry_matches else 0.0
        investor_score = float(
            min(len(set(investor_overlaps)), self.MAX_INVESTOR_SCORE)
        )

        reasons: list[str] = []
        if direct_intro_score:
            reasons.append("confirmed_direct_introduction")
        for connector_role, target_role, overlap_start, overlap_end in overlaps:
            reasons.append(
                "verified_work_overlap:"
                f"{connector_role.company_name}:{overlap_start.isoformat()}:{overlap_end.isoformat()}"
            )
        if relationship_score:
            reasons.append(f"owner_connector_relationship:{confidence}")
        reasons.extend(f"school_city_community:{value}" for value in community_values)
        reasons.extend(f"role_industry:{value}" for value in role_industry_matches)
        reasons.extend(f"investor_overlap:{value}" for value in investor_overlaps)

        if direct_intro_score:
            shared_signal = "direct_introduction"
            shared_detail = "; ".join(sorted(set(direct_intro_evidence_ids)))
        elif overlaps:
            first_overlap = sorted(
                overlaps,
                key=lambda item: (
                    item[2],
                    item[3],
                    self.normalize_company(item[0].company_name),
                ),
            )[0]
            shared_signal = "verified_work_overlap"
            shared_detail = (
                f"{first_overlap[0].company_name}, {first_overlap[2].isoformat()} "
                f"to {first_overlap[3].isoformat()}"
            )
        elif company_proximities:
            shared_signal = "company_proximity"
            shared_detail = (
                f"{sorted(company_proximities, key=str.casefold)[0]}; "
                "employment dates unavailable or non-overlapping"
            )
        elif community_values:
            shared_signal = "school_city_community"
            shared_detail = "; ".join(community_values)
        elif role_industry_matches:
            shared_signal = "role_industry"
            shared_detail = "; ".join(role_industry_matches)
        elif investor_overlaps:
            shared_signal = "investor_overlap"
            shared_detail = "; ".join(investor_overlaps)
        else:
            shared_signal = ""
            shared_detail = ""

        has_strong_signal = bool(direct_intro_score or work_overlap_score)
        if has_strong_signal and relationship_score:
            segment = "strong_warm_intro"
        elif shared_signal and shared_signal != "investor_overlap":
            segment = "review_warm_intro"
        else:
            segment = "no_strong_path"

        overlap_evidence_ids = {
            identifier
            for connector_role, target_role, _, _ in overlaps
            for identifier in (connector_role.id, target_role.id)
        }
        all_evidence_ids = tuple(
            sorted(
                {
                    *evidence_ids,
                    *direct_intro_evidence_ids,
                    *relationship_evidence_ids,
                    *overlap_evidence_ids,
                }
            )
        )
        component_total = sum(
            (
                direct_intro_score,
                work_overlap_score,
                relationship_score,
                school_city_community_score,
                role_industry_score,
                investor_score,
            )
        )
        path_key = "|".join((connector.id, target.id, target.current_company or ""))
        return WarmIntroMatch(
            contact=connector,
            score=component_total,
            reasons=reasons,
            shared_companies=sorted(company_proximities, key=str.casefold),
            shared_schools=list(shared_schools),
            shared_appearances=list(shared_appearances),
            shared_affiliations=[*shared_communities, *investor_overlaps],
            path_id="path-" + hashlib.sha256(path_key.encode("utf-8")).hexdigest()[:16],
            target_name=target.full_name,
            target_title=target.current_position or "",
            target_company=target.current_company or "",
            shared_signal=shared_signal,
            shared_detail=shared_detail,
            relationship_confidence=confidence,
            direct_intro_score=direct_intro_score,
            work_overlap_score=work_overlap_score,
            relationship_score=relationship_score,
            school_city_community_score=school_city_community_score,
            role_industry_score=role_industry_score,
            investor_score=investor_score,
            segment=segment,
            evidence_ids=all_evidence_ids,
        )

    def score_target_contact(self, *args, **kwargs) -> WarmIntroMatch:
        """Backward-friendly alias for the explicit target-person scorer."""
        return self.score_target_connector(*args, **kwargs)

    def score_contact(
        self,
        contact: Contact,
        experiences: list[Experience],
        educations: list[Education],
        target_company: Optional[str],
        target_school: Optional[str],
        target_role: Optional[str],
        appearances: Optional[list[PublicAppearance]] = None,
        target_platforms: Optional[list[str]] = None,
    ) -> WarmIntroMatch:
        """Score a contact based on overlap with target criteria.

        Returns a WarmIntroMatch with score and explanation.
        """
        score = 0.0
        reasons = []
        shared_companies = []
        shared_companies_normalized = set()  # Track normalized names to prevent double-counting
        shared_schools = []
        shared_schools_normalized = set()
        shared_appearances = []
        shared_appearances_normalized = set()
        role_similarity = 0.0
        shared_signal = ""
        shared_detail = ""

        # Check company overlap
        if target_company:
            # Check current company
            if contact.current_company and self.company_matches(
                contact.current_company, target_company
            ):
                score += self.WEIGHT_SAME_COMPANY
                shared_companies.append(contact.current_company)
                shared_companies_normalized.add(self.normalize_company(contact.current_company))
                reasons.append(f"Currently works at {contact.current_company}")
                shared_signal = "company_proximity"
                shared_detail = f"Company-name match: {contact.current_company}; dates not compared"

            # Check past experiences
            for exp in experiences:
                if self.company_matches(exp.company_name, target_company):
                    # Don't double-count if it's the same company (normalized)
                    normalized = self.normalize_company(exp.company_name)
                    if normalized not in shared_companies_normalized:
                        score += self.WEIGHT_SAME_COMPANY
                        shared_companies.append(exp.company_name)
                        shared_companies_normalized.add(normalized)
                        if exp.is_current:
                            reasons.append(f"Currently works at {exp.company_name}")
                        else:
                            reasons.append(f"Previously worked at {exp.company_name}")
                        if not shared_signal:
                            shared_signal = "company_proximity"
                            shared_detail = (
                                f"Company-name match: {exp.company_name}; target-person dates not compared"
                            )

        # Check school overlap
        if target_school:
            for edu in educations:
                if self.school_matches(edu.school_name, target_school):
                    normalized = self.normalize_school(edu.school_name)
                    if normalized not in shared_schools_normalized:
                        score += self.WEIGHT_SAME_SCHOOL
                        shared_schools.append(edu.school_name)
                        shared_schools_normalized.add(normalized)
                        degree_info = f" ({edu.degree})" if edu.degree else ""
                        reasons.append(f"Attended {edu.school_name}{degree_info}")

        # Check role overlap (simple keyword matching for now)
        if target_role and contact.current_position:
            target_role_lower = target_role.lower()
            position_lower = contact.current_position.lower()

            # Simple keyword overlap scoring
            target_words = set(target_role_lower.split())
            position_words = set(position_lower.split())
            overlap = target_words & position_words

            if overlap:
                role_similarity = len(overlap) / max(
                    len(target_words), len(position_words)
                )
                role_score = role_similarity * self.WEIGHT_ROLE_OVERLAP
                score += role_score
                reasons.append(f"Role overlap: {contact.current_position}")

        # Check shared appearances (same podcast/event)
        if appearances and target_platforms:
            for appearance in appearances:
                for target_platform in target_platforms:
                    if self.platform_matches(appearance.platform, target_platform):
                        normalized = self.normalize_platform(appearance.platform)
                        if normalized not in shared_appearances_normalized:
                            score += self.WEIGHT_SHARED_APPEARANCE
                            shared_appearances.append(appearance.platform)
                            shared_appearances_normalized.add(normalized)
                            reasons.append(f"Both appeared on {appearance.platform}")
                        break  # Don't match same appearance to multiple targets

        # Apply recency boost
        recency_boost = self.get_recency_boost(contact.connected_on)
        recency_score = recency_boost * self.WEIGHT_RECENCY
        score += recency_score

        return WarmIntroMatch(
            contact=contact,
            score=score,
            reasons=reasons,
            shared_companies=shared_companies,
            shared_schools=shared_schools,
            shared_appearances=shared_appearances,
            role_similarity=role_similarity,
            recency_boost=recency_boost,
            target_company=target_company or "",
            shared_signal=shared_signal,
            shared_detail=shared_detail,
        )

    def find_matches(
        self,
        target_company: Optional[str] = None,
        target_school: Optional[str] = None,
        target_role: Optional[str] = None,
        target_platforms: Optional[list[str]] = None,
        min_score: float = 0.0,
        limit: int = 20,
    ) -> list[WarmIntroMatch]:
        """Find warm intro matches from the database.

        Queries enriched contacts, scores them against criteria,
        and returns top matches sorted by score.
        """
        if self.db is None or self.db.conn is None:
            raise ValueError("Database connection required for find_matches")

        matches = []

        # Get all enriched contacts
        contact_rows = self.db.conn.execute("""
            SELECT * FROM contacts WHERE enriched_at IS NOT NULL
        """).fetchall()

        if not contact_rows:
            return []

        contact_ids = [row["id"] for row in contact_rows]

        # Batch fetch all experiences for these contacts (single query)
        placeholders = ",".join("?" * len(contact_ids))
        exp_rows = self.db.conn.execute(
            f"SELECT * FROM experiences WHERE contact_id IN ({placeholders})",
            contact_ids,
        ).fetchall()

        # Group experiences by contact_id
        experiences_by_contact: dict[str, list[Experience]] = {cid: [] for cid in contact_ids}
        for exp_row in exp_rows:
            exp = Experience(
                id=exp_row["id"],
                contact_id=exp_row["contact_id"],
                company_name=exp_row["company_name"],
                company_linkedin_url=exp_row["company_linkedin_url"],
                title=exp_row["title"] or "",
                description=exp_row["description"],
                location=exp_row["location"],
                start_date=(
                    date.fromisoformat(exp_row["start_date"])
                    if exp_row["start_date"]
                    else None
                ),
                end_date=(
                    date.fromisoformat(exp_row["end_date"])
                    if exp_row["end_date"]
                    else None
                ),
                is_current=bool(exp_row["is_current"]),
            )
            experiences_by_contact[exp_row["contact_id"]].append(exp)

        # Batch fetch all educations for these contacts (single query)
        edu_rows = self.db.conn.execute(
            f"SELECT * FROM educations WHERE contact_id IN ({placeholders})",
            contact_ids,
        ).fetchall()

        # Group educations by contact_id
        educations_by_contact: dict[str, list[Education]] = {cid: [] for cid in contact_ids}
        for edu_row in edu_rows:
            edu = Education(
                id=edu_row["id"],
                contact_id=edu_row["contact_id"],
                school_name=edu_row["school_name"],
                school_linkedin_url=edu_row["school_linkedin_url"],
                degree=edu_row["degree"],
                field_of_study=edu_row["field_of_study"],
                start_year=edu_row["start_year"],
                end_year=edu_row["end_year"],
            )
            educations_by_contact[edu_row["contact_id"]].append(edu)

        # Batch fetch all appearances for these contacts (if target_platforms provided)
        appearances_by_contact: dict[str, list[PublicAppearance]] = {cid: [] for cid in contact_ids}
        if target_platforms:
            app_rows = self.db.conn.execute(
                f"SELECT * FROM appearances WHERE contact_id IN ({placeholders})",
                contact_ids,
            ).fetchall()

            for app_row in app_rows:
                app_date = None
                if app_row["date"]:
                    app_date = date.fromisoformat(app_row["date"])

                app = PublicAppearance(
                    id=app_row["id"],
                    contact_id=app_row["contact_id"],
                    appearance_type=app_row["appearance_type"],
                    title=app_row["title"],
                    platform=app_row["platform"],
                    url=app_row["url"],
                    date=app_date,
                    description=app_row["description"],
                )
                appearances_by_contact[app_row["contact_id"]].append(app)

        # Score each contact
        for row in contact_rows:
            contact = self.db._row_to_contact(row)
            experiences = experiences_by_contact.get(contact.id, [])
            educations = educations_by_contact.get(contact.id, [])
            appearances = appearances_by_contact.get(contact.id, [])

            match = self.score_contact(
                contact=contact,
                experiences=experiences,
                educations=educations,
                target_company=target_company,
                target_school=target_school,
                target_role=target_role,
                appearances=appearances,
                target_platforms=target_platforms,
            )

            if match.score >= min_score:
                matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)

        return matches[:limit]
