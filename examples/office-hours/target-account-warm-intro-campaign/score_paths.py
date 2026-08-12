"""Evidence-backed connector-to-target warm-path scoring."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from typing import Literal

from schemas import CampaignConfig, ContactRecord, ExperienceRecord, PathScore


_COMPANY_SUFFIXES = {
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


def _normalize_company(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    words = re.sub(r"[^a-z0-9]+", " ", normalized.casefold()).split()
    while words and words[-1] in _COMPANY_SUFFIXES:
        words.pop()
    return " ".join(words)


@dataclass(frozen=True)
class EmploymentOverlap:
    """A verified, date-bounded period at the same employer."""

    company: str
    start_date: date
    end_date: date
    left_experience_id: str
    right_experience_id: str


@dataclass(frozen=True)
class PathEvidence:
    """Auditable facts used to score one connector-to-target path."""

    direct_intro_evidence_ids: tuple[str, ...] = ()
    relationship_confidence: str = "unknown"
    relationship_evidence_ids: tuple[str, ...] = ()
    connector_experiences: tuple[ExperienceRecord, ...] = ()
    target_experiences: tuple[ExperienceRecord, ...] = ()
    shared_schools: tuple[str, ...] = ()
    shared_cities: tuple[str, ...] = ()
    shared_communities: tuple[str, ...] = ()
    shared_appearances: tuple[str, ...] = ()
    role_overlaps: tuple[str, ...] = ()
    industry_overlaps: tuple[str, ...] = ()
    investor_overlaps: tuple[str, ...] = ()
    supporting_evidence_ids: tuple[str, ...] = ()


def employment_overlap(
    left: ExperienceRecord,
    right: ExperienceRecord,
    as_of: date,
) -> EmploymentOverlap | None:
    """Return a confirmed overlap only when employer and dates support it."""
    if not _normalize_company(left.company) or (
        _normalize_company(left.company) != _normalize_company(right.company)
    ):
        return None
    if left.start_date is None or right.start_date is None:
        return None

    left_end = left.end_date or (as_of if left.is_current else None)
    right_end = right.end_date or (as_of if right.is_current else None)
    if left_end is None or right_end is None:
        return None

    overlap_start = max(left.start_date, right.start_date)
    overlap_end = min(left_end, right_end, as_of)
    if overlap_start > overlap_end:
        return None
    return EmploymentOverlap(
        company=left.company.strip(),
        start_date=overlap_start,
        end_date=overlap_end,
        left_experience_id=left.experience_id,
        right_experience_id=right.experience_id,
    )


_RELATIONSHIP_SCORES = {"low": 1, "medium": 2, "high": 3, "confirmed": 3}
_DEFAULT_PATH_WEIGHTS = {
    "direct_intro": 40,
    "work_overlap": 20,
    "school_city_community": 8,
    "role_industry": 4,
    "investor": 3,
    "relationship": 3,
}
_FACTUAL_TIERS = (
    "direct_intro",
    "work_overlap",
    "school_city_community",
    "role_industry",
    "investor",
)


def _path_weights(config: CampaignConfig) -> dict[str, int]:
    weights = {
        name: int(config.score_weights.get(name, default))
        for name, default in _DEFAULT_PATH_WEIGHTS.items()
    }
    negative = tuple(name for name, value in weights.items() if value < 0)
    if negative:
        raise ValueError(
            "invalid path score weights: negative values are not allowed for "
            + ", ".join(negative)
        )
    if weights["investor"] > 3:
        raise ValueError("invalid path score weights: investor must be capped at 3")

    for index, tier in enumerate(_FACTUAL_TIERS[:-1]):
        lower_maximum = sum(weights[name] for name in _FACTUAL_TIERS[index + 1 :])
        if weights[tier] <= lower_maximum:
            raise ValueError(
                "invalid path score weights: "
                f"{tier} ({weights[tier]}) must exceed the combined lower-tier maximum "
                f"({lower_maximum})"
            )
    return weights


def _path_id(
    connector: ContactRecord,
    target: ContactRecord,
    config: CampaignConfig,
) -> str:
    raw = "|".join((config.campaign_id, config.owner_id, connector.contact_id, target.contact_id))
    return f"path-{sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def score_warm_path(
    connector: ContactRecord,
    target: ContactRecord,
    evidence: PathEvidence,
    config: CampaignConfig,
) -> PathScore:
    """Score a single owner-to-connector-to-target path from cited evidence."""
    weights = _path_weights(config)
    direct_intro_score = 0
    reasons: list[str] = []
    if evidence.direct_intro_evidence_ids:
        direct_intro_score = weights["direct_intro"]
        reasons.append("confirmed_direct_introduction")

    relationship_confidence = evidence.relationship_confidence.strip().casefold()
    relationship_score = _RELATIONSHIP_SCORES.get(relationship_confidence, 0)
    if relationship_score:
        configured_maximum = weights["relationship"]
        relationship_score = min(relationship_score, configured_maximum)

    overlap_records: list[tuple[EmploymentOverlap, ExperienceRecord, ExperienceRecord]] = []
    undated_records: list[tuple[ExperienceRecord, ExperienceRecord]] = []
    non_overlapping_records: list[tuple[ExperienceRecord, ExperienceRecord]] = []
    for connector_role in evidence.connector_experiences:
        for target_role in evidence.target_experiences:
            if not _normalize_company(connector_role.company) or (
                _normalize_company(connector_role.company)
                != _normalize_company(target_role.company)
            ):
                continue
            overlap = employment_overlap(connector_role, target_role, config.as_of)
            if overlap is not None:
                overlap_records.append((overlap, connector_role, target_role))
            elif (
                connector_role.start_date is None
                or target_role.start_date is None
                or (connector_role.end_date is None and not connector_role.is_current)
                or (target_role.end_date is None and not target_role.is_current)
            ):
                undated_records.append((connector_role, target_role))
            else:
                non_overlapping_records.append((connector_role, target_role))

    work_overlap_score = weights["work_overlap"] if overlap_records else 0
    for overlap, _, _ in overlap_records:
        reasons.append(
            "dated_work_overlap:"
            f"{overlap.company}:{overlap.start_date.isoformat()}:{overlap.end_date.isoformat()}"
        )
    undated_companies = {connector_role.company.strip() for connector_role, _ in undated_records}
    for company in sorted(undated_companies, key=str.casefold):
        reasons.append(f"company_proximity:{company}:missing_dates")
    non_overlapping_companies = {
        connector_role.company.strip() for connector_role, _ in non_overlapping_records
    }
    for company in sorted(non_overlapping_companies, key=str.casefold):
        reasons.append(f"company_proximity:{company}:non_overlapping_dates")
    if relationship_score:
        reasons.append(f"owner_connector_relationship:{relationship_confidence}")

    contributing_roles = [
        role
        for _, connector_role, target_role in overlap_records
        for role in (connector_role, target_role)
    ]
    contributing_roles.extend(
        role
        for connector_role, target_role in undated_records
        for role in (connector_role, target_role)
    )
    contributing_roles.extend(
        role
        for connector_role, target_role in non_overlapping_records
        for role in (connector_role, target_role)
    )
    experience_evidence_ids = {
        identifier
        for role in contributing_roles
        for identifier in (role.experience_id, role.source_record_id)
        if identifier
    }
    community_signals = (
        *(f"shared_school:{value}" for value in evidence.shared_schools),
        *(f"shared_city:{value}" for value in evidence.shared_cities),
        *(f"shared_community:{value}" for value in evidence.shared_communities),
        *(f"shared_appearance:{value}" for value in evidence.shared_appearances),
    )
    role_industry_signals = (
        *(f"role_proximity:{value}" for value in evidence.role_overlaps),
        *(f"industry_proximity:{value}" for value in evidence.industry_overlaps),
    )
    investor_signals = tuple(
        f"investor_overlap:{value}" for value in evidence.investor_overlaps
    )
    reasons.extend(community_signals)
    reasons.extend(role_industry_signals)
    reasons.extend(investor_signals)

    school_city_community_score = min(
        len(set(community_signals)),
        weights["school_city_community"],
    )
    role_industry_score = min(
        len(set(role_industry_signals)),
        weights["role_industry"],
    )
    investor_score = min(
        len(set(investor_signals)),
        weights["investor"],
        3,
    )

    return PathScore(
        path_id=_path_id(connector, target, config),
        connector_id=connector.contact_id,
        target_id=target.contact_id,
        target_name=target.name,
        target_title=target.title,
        target_company=target.company,
        direct_intro_score=direct_intro_score,
        work_overlap_score=work_overlap_score,
        relationship_score=relationship_score,
        school_city_community_score=school_city_community_score,
        role_industry_score=role_industry_score,
        investor_score=investor_score,
        relationship_confidence=relationship_confidence or "unknown",
        reasons=tuple(reasons),
        evidence_ids=tuple(
            sorted(
                {
                    *evidence.direct_intro_evidence_ids,
                    *evidence.relationship_evidence_ids,
                    *experience_evidence_ids,
                    *evidence.supporting_evidence_ids,
                }
            )
        ),
    )


def segment_path(
    score: PathScore,
    config: CampaignConfig,
) -> Literal["strong_warm_intro", "review_warm_intro", "no_strong_path"]:
    """Gate ranking scores by the factual evidence required for a warm ask."""
    strong_threshold = config.segment_thresholds.get("strong_warm_intro", 1)
    has_relationship = score.relationship_score > 0
    has_strong_factual_signal = score.direct_intro_score > 0 or score.work_overlap_score > 0
    if score.total_score >= strong_threshold and has_relationship and has_strong_factual_signal:
        return "strong_warm_intro"
    has_review_signal = any(reason.startswith("company_proximity:") for reason in score.reasons)
    has_ancillary_signal = (
        score.school_city_community_score > 0 or score.role_industry_score > 0
    )
    review_threshold = config.segment_thresholds.get("review_warm_intro", 1)
    if has_strong_factual_signal or has_review_signal or (
        has_ancillary_signal and score.total_score >= review_threshold
    ):
        return "review_warm_intro"
    return "no_strong_path"
