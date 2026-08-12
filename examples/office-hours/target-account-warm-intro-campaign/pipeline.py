"""Deterministic local orchestration for the fictional warm-intro campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date, timezone
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence

from build_campaign import (
    CommitteeMember,
    build_buying_committee,
    dedupe_contacts,
    summarize_interactions,
    validate_org_edges,
)
from provider_policy import ProviderPolicy, build_pdl_exclusions
from schemas import (
    AccountRecord,
    CampaignConfig,
    ConnectorEdge,
    ContactRecord,
    EvidenceRecord,
    ExperienceRecord,
    InteractionRecord,
    OrgEdgeRecord,
    PathScore,
    load_csv_records,
    normalize_email,
    normalize_linkedin_url,
    write_csv_records,
)
from score_accounts import AccountScore, rank_accounts
from score_paths import PathEvidence, score_warm_path, segment_path


@dataclass(frozen=True)
class CampaignStageLedger:
    """One immutable, externally auditable pipeline-stage result."""

    stage: str
    input_count: int
    output_count: int
    exclusions: dict[str, int]
    review_count: int
    cache_hits: int
    authorized_provider_calls: int
    estimated_spend_usd: str
    artifact_hashes: dict[str, str]


@dataclass(frozen=True)
class CampaignLedger:
    """Deterministic summary returned by :func:`run_pipeline`."""

    campaign_id: str
    as_of: str
    fixture_mode: bool
    stages: tuple[CampaignStageLedger, ...]
    artifact_hashes: dict[str, str]
    total_cache_hits: int
    total_authorized_provider_calls: int
    total_estimated_spend_usd: str
    evidence_freshness: dict[str, int]
    path_segment_counts: dict[str, int]
    approved_message_count: int
    activated_message_count: int
    hash_scope: str = "normalized_review_artifacts_except_campaign_ledger.json"


_ACCOUNT_FIELDS = (
    "rank",
    "account_id",
    "name",
    "domain",
    "icp_fit",
    "engineering_led",
    "technical_gtm_signal",
    "growth_recency",
    "customer_similarity",
    "first_party_engagement",
    "total_score",
    "decision",
    "exclusion_reason",
)
_DEDUPE_FIELDS = (
    "audit_id",
    "action",
    "canonical_contact_id",
    "related_contact_ids",
    "match_types",
    "reason",
    "linkedin_aliases",
    "work_email_aliases",
    "identity_aliases",
)
_COMMITTEE_FIELDS = (
    "account_id",
    "account_name",
    "contact_id",
    "name",
    "title",
    "role_family",
    "committee_role",
    "linkedin_url",
    "work_email",
    "source_record_ids",
    "evidence_ids",
)
_ORG_FIELDS = (
    "edge_id",
    "from_contact_id",
    "from_name",
    "from_kind",
    "to_contact_id",
    "to_name",
    "to_kind",
    "edge_type",
    "confidence",
    "review_required",
    "source_evidence_ids",
)
_INTERACTION_FIELDS = (
    "interaction_id",
    "target_id",
    "source",
    "interaction_type",
    "occurred_at",
    "direction",
    "participant_ids",
    "evidence_id",
    "direct_introduction",
)
_PATH_FIELDS = (
    "campaign_id",
    "owner_id",
    "path_id",
    "connector_id",
    "connector_name",
    "connector_linkedin",
    "connector_company",
    "target_id",
    "target_name",
    "target_title",
    "target_company",
    "direct_intro_score",
    "work_overlap_score",
    "relationship_score",
    "school_city_community_score",
    "role_industry_score",
    "investor_score",
    "total_score",
    "relationship_confidence",
    "segment",
    "reviewed_override",
    "investor_only",
    "shared_signal",
    "shared_detail",
    "reasons",
    "evidence_ids",
    "validation_errors",
)
_DIRECT_FIELDS = (
    "target_id",
    "target_name",
    "target_title",
    "target_company",
    "account_id",
    "account_name",
    "linkedin_url",
    "work_email",
    "path_segment",
    "why_target_cares",
    "permissionless_value",
    "evidence_ids",
    "approved",
)
_SEGMENT_ORDER = {
    "strong_warm_intro": 0,
    "review_warm_intro": 1,
    "no_strong_path": 2,
}
_COMMITTEE_ORDER = {
    "technical_champion": 0,
    "operational_buyer": 1,
    "economic_buyer": 2,
    "adjacent_validator": 3,
}


def _load_json_object(path: Path) -> dict[str, object]:
    with Path(path).open("r", encoding="utf-8") as source:
        value = json.load(source, parse_float=Decimal)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _metadata(record: object) -> dict[str, object]:
    raw = getattr(record, "source_metadata_json", "{}") or "{}"
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        record_id = getattr(record, "source_record_id", "<unknown>")
        raise ValueError(f"record {record_id} has invalid source_metadata_json") from error
    if not isinstance(value, dict):
        raise ValueError("source_metadata_json must contain a JSON object")
    return value


def _metadata_strings(metadata: Mapping[str, object], key: str) -> tuple[str, ...]:
    raw = metadata.get(key, ())
    if isinstance(raw, str):
        return (raw,) if raw else ()
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(str(value) for value in raw if str(value))


def _is_open_role(contact: ContactRecord) -> bool:
    metadata = _metadata(contact)
    node_type = str(metadata.get("node_type", metadata.get("entity_type", "")))
    normalized = node_type.casefold().replace("-", "_").replace(" ", "_")
    return normalized in {"open_role", "job_opening"} or metadata.get("is_open_role") is True


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _stage(
    stage: str,
    *,
    input_count: int,
    output_count: int,
    exclusions: Mapping[str, int] | None,
    review_count: int,
    output_dir: Path,
    artifacts: Sequence[str],
) -> CampaignStageLedger:
    return CampaignStageLedger(
        stage=stage,
        input_count=input_count,
        output_count=output_count,
        exclusions=dict(sorted((exclusions or {}).items())),
        review_count=review_count,
        cache_hits=0,
        authorized_provider_calls=0,
        estimated_spend_usd="0.00",
        artifact_hashes={name: _sha256(output_dir / name) for name in sorted(artifacts)},
    )


def _dedupe_match_types(group: Sequence[str], contacts: Mapping[str, ContactRecord]) -> str:
    linkedins: list[str] = []
    emails: list[str] = []
    for contact_id in group:
        contact = contacts[contact_id]
        if contact.linkedin_url:
            linkedins.append(normalize_linkedin_url(contact.linkedin_url))
        if contact.work_email:
            emails.append(normalize_email(contact.work_email))
    kinds: list[str] = []
    if len(linkedins) != len(set(linkedins)):
        kinds.append("linkedin_url")
    if len(emails) != len(set(emails)):
        kinds.append("work_email")
    return "|".join(kinds)


def _unique_index(records: Sequence[object], field: str, label: str) -> dict[str, object]:
    index: dict[str, object] = {}
    for record in records:
        value = str(getattr(record, field, "") or "").strip()
        if not value:
            raise ValueError(f"{label} ID must be non-empty")
        if value in index:
            raise ValueError(f"duplicate {label} ID: {value}")
        index[value] = record
    return index


def _remap_contact_id(
    value: str,
    aliases: Mapping[str, str],
    *,
    label: str,
    allow: Sequence[str] = (),
) -> str:
    candidate = str(value or "").strip()
    if candidate in allow:
        return candidate
    try:
        return aliases[candidate]
    except KeyError as error:
        raise ValueError(f"{label} references unknown contact {candidate!r}") from error


def _remap_dependent_records(
    *,
    experiences: Sequence[ExperienceRecord],
    interactions: Sequence[InteractionRecord],
    org_edges: Sequence[OrgEdgeRecord],
    evidence: Sequence[EvidenceRecord],
    connector_edges: Sequence[ConnectorEdge],
    aliases: Mapping[str, str],
    owner_id: str,
) -> tuple[
    tuple[ExperienceRecord, ...],
    tuple[InteractionRecord, ...],
    tuple[OrgEdgeRecord, ...],
    tuple[EvidenceRecord, ...],
    tuple[ConnectorEdge, ...],
]:
    remapped_experiences = tuple(
        replace(
            item,
            contact_id=_remap_contact_id(
                item.contact_id, aliases, label=f"experience {item.experience_id}"
            ),
        )
        for item in experiences
    )
    remapped_interactions = tuple(
        replace(
            item,
            contact_id=_remap_contact_id(
                item.contact_id, aliases, label=f"interaction {item.interaction_id}"
            ),
            participant_ids=tuple(
                _remap_contact_id(
                    participant,
                    aliases,
                    label=f"interaction {item.interaction_id} participant",
                    allow=(owner_id,),
                )
                for participant in item.participant_ids
            ),
        )
        for item in interactions
    )
    remapped_org_edges = tuple(
        replace(
            item,
            from_contact_id=_remap_contact_id(
                item.from_contact_id, aliases, label=f"org edge {item.edge_id}"
            ),
            to_contact_id=_remap_contact_id(
                item.to_contact_id, aliases, label=f"org edge {item.edge_id}"
            ),
        )
        for item in org_edges
    )
    remapped_evidence = tuple(
        replace(
            item,
            subject_contact_id=(
                _remap_contact_id(
                    item.subject_contact_id,
                    aliases,
                    label=f"evidence {item.evidence_id}",
                )
                if item.subject_contact_id
                else ""
            ),
        )
        for item in evidence
    )
    remapped_connector_edges: list[ConnectorEdge] = []
    for item in connector_edges:
        metadata = _metadata(item)
        raw_target_id = str(metadata.get("target_id", "")).strip()
        if not raw_target_id:
            raise ValueError(f"connector edge {item.edge_id} requires target_id metadata")
        metadata["target_id"] = _remap_contact_id(
            raw_target_id,
            aliases,
            label=f"connector edge {item.edge_id} target",
        )
        remapped_connector_edges.append(
            replace(
                item,
                connector_id=_remap_contact_id(
                    item.connector_id,
                    aliases,
                    label=f"connector edge {item.edge_id}",
                ),
                source_metadata_json=json.dumps(
                    metadata, sort_keys=True, separators=(",", ":")
                ),
            )
        )
    return (
        remapped_experiences,
        remapped_interactions,
        remapped_org_edges,
        remapped_evidence,
        tuple(remapped_connector_edges),
    )


def _path_signal(score: PathScore) -> tuple[str, str]:
    if score.direct_intro_score:
        return "direct_introduction", ";".join(score.evidence_ids)
    if score.work_overlap_score:
        reason = next(
            reason for reason in score.reasons if reason.startswith("dated_work_overlap:")
        )
        _, company, start, end = reason.split(":", 3)
        return "verified_work_overlap", f"{company}, {start} to {end}"
    for prefix, signal in (
        ("company_proximity:", "company_proximity"),
        ("shared_school:", "school_city_community"),
        ("shared_city:", "school_city_community"),
        ("shared_community:", "school_city_community"),
        ("shared_appearance:", "school_city_community"),
        ("role_proximity:", "role_industry"),
        ("industry_proximity:", "role_industry"),
        ("investor_overlap:", "investor_overlap"),
    ):
        matching = [reason for reason in score.reasons if reason.startswith(prefix)]
        if matching:
            return signal, "; ".join(reason.removeprefix(prefix) for reason in matching)
    return "", ""


def _evidence_freshness(
    evidence: Sequence[EvidenceRecord], as_of: date
) -> dict[str, int]:
    buckets = {
        "0_30_days": 0,
        "31_90_days": 0,
        "91_365_days": 0,
        "over_365_days": 0,
        "future": 0,
        "unknown": 0,
    }
    for item in evidence:
        if item.observed_at is None:
            buckets["unknown"] += 1
            continue
        observed = item.observed_at
        if observed.utcoffset() is None:
            raise ValueError(f"evidence {item.evidence_id} requires a timezone-aware timestamp")
        age_days = (as_of - observed.astimezone(timezone.utc).date()).days
        if age_days < 0:
            buckets["future"] += 1
        elif age_days <= 30:
            buckets["0_30_days"] += 1
        elif age_days <= 90:
            buckets["31_90_days"] += 1
        elif age_days <= 365:
            buckets["91_365_days"] += 1
        else:
            buckets["over_365_days"] += 1
    return buckets


def _score_to_row(
    score: AccountScore,
    account: AccountRecord,
    rank: int,
) -> dict[str, object]:
    return {
        "rank": rank,
        "account_id": account.account_id,
        "name": account.name,
        "domain": account.domain,
        "icp_fit": score.icp_fit,
        "engineering_led": score.engineering_led,
        "technical_gtm_signal": score.technical_gtm_signal,
        "growth_recency": score.growth_recency,
        "customer_similarity": score.customer_similarity,
        "first_party_engagement": score.first_party_engagement,
        "total_score": score.total_score,
        "decision": score.decision,
        "exclusion_reason": score.exclusion_reason,
    }


def _committee_rows(
    members: Sequence[CommitteeMember],
    accounts: Mapping[str, AccountRecord],
    contacts: Mapping[str, ContactRecord],
    evidence: Sequence[EvidenceRecord],
) -> list[dict[str, object]]:
    evidence_by_contact: dict[str, list[str]] = {}
    for item in evidence:
        if item.subject_contact_id:
            evidence_by_contact.setdefault(item.subject_contact_id, []).append(item.evidence_id)
    rows: list[dict[str, object]] = []
    for member in members:
        contact = contacts[member.contact_id]
        rows.append(
            {
                "account_id": member.account_id,
                "account_name": accounts[member.account_id].name,
                "contact_id": member.contact_id,
                "name": member.name,
                "title": member.title,
                "role_family": member.role_family,
                "committee_role": member.committee_role,
                "linkedin_url": normalize_linkedin_url(contact.linkedin_url) if contact.linkedin_url else "",
                "work_email": normalize_email(contact.work_email) if contact.work_email else "",
                "source_record_ids": tuple(sorted(contact.source_record_ids)),
                "evidence_ids": tuple(sorted(evidence_by_contact.get(member.contact_id, ()))),
            }
        )
    return rows


def _validated_path_evidence(
    edge: ConnectorEdge,
    connector: ContactRecord,
    target: ContactRecord,
    experiences_by_contact: Mapping[str, tuple[ExperienceRecord, ...]],
    evidence_by_id: Mapping[str, EvidenceRecord],
    interactions_by_evidence_id: Mapping[str, tuple[InteractionRecord, ...]],
    config: CampaignConfig,
) -> PathEvidence:
    metadata = _metadata(edge)
    errors: list[str] = []
    if edge.owner_id != config.owner_id:
        errors.append(f"wrong_owner:{edge.owner_id or '<missing>'}")
        return PathEvidence(
            connector_experiences=experiences_by_contact.get(connector.contact_id, ()),
            target_experiences=experiences_by_contact.get(target.contact_id, ()),
            validation_errors=tuple(errors),
        )

    valid_direct_ids: list[str] = []
    for evidence_id in _metadata_strings(metadata, "direct_intro_evidence_ids"):
        item = evidence_by_id.get(evidence_id)
        if item is None:
            errors.append(f"forged_direct_intro_evidence:{evidence_id}")
            continue
        matching_interactions = interactions_by_evidence_id.get(evidence_id, ())
        expected_participants = {config.owner_id, connector.contact_id, target.contact_id}
        participant_match = any(
            (
                interaction.interaction_type.casefold() == "introduction"
                or interaction.source.casefold() == "manual_confirmation"
            )
            and expected_participants.issubset(set(interaction.participant_ids))
            for interaction in matching_interactions
        )
        if (
            item.source_type.casefold() != "interaction"
            or item.confidence.casefold() != "confirmed"
            or item.subject_contact_id != target.contact_id
        ):
            errors.append(f"mismatched_direct_intro_evidence:{evidence_id}")
        elif not participant_match:
            errors.append(f"wrong_participant:{evidence_id}")
        else:
            valid_direct_ids.append(evidence_id)

    valid_relationship_ids: list[str] = []
    for evidence_id in edge.evidence_ids:
        item = evidence_by_id.get(evidence_id)
        if item is None:
            errors.append(f"missing_relationship_evidence:{evidence_id}")
            continue
        if evidence_id in valid_direct_ids:
            valid_relationship_ids.append(evidence_id)
            continue
        if item.source_type.casefold() != "interaction":
            errors.append(f"unsupported_relationship_evidence_type:{evidence_id}")
            continue
        if item.subject_contact_id != connector.contact_id:
            errors.append(f"wrong_relationship_subject:{evidence_id}")
            continue
        interactions = interactions_by_evidence_id.get(evidence_id, ())
        if not any(
            {config.owner_id, connector.contact_id}.issubset(
                set(interaction.participant_ids)
            )
            for interaction in interactions
        ):
            errors.append(f"unverified_relationship_interaction:{evidence_id}")
            continue
        valid_relationship_ids.append(evidence_id)

    supporting_ids = _metadata_strings(metadata, "supporting_evidence_ids")
    valid_supporting_ids: list[str] = []
    for evidence_id in supporting_ids:
        item = evidence_by_id.get(evidence_id)
        if item is None:
            errors.append(f"missing_supporting_evidence:{evidence_id}")
            continue
        subject_supported = (
            item.subject_contact_id in {connector.contact_id, target.contact_id}
            or item.subject_account_id == target.account_id
        )
        if not subject_supported:
            errors.append(f"wrong_supporting_subject:{evidence_id}")
            continue
        valid_supporting_ids.append(evidence_id)

    valid_supporting_records = tuple(
        evidence_by_id[evidence_id] for evidence_id in valid_supporting_ids
    )

    def supported_category(
        metadata_key: str,
        allowed_source_types: frozenset[str],
    ) -> tuple[str, ...]:
        values = _metadata_strings(metadata, metadata_key)
        if not values:
            return ()
        if any(
            item.source_type.casefold() in allowed_source_types
            for item in valid_supporting_records
        ):
            return values
        errors.append(f"unsupported_{metadata_key}_evidence")
        return ()

    return PathEvidence(
        direct_intro_evidence_ids=tuple(valid_direct_ids),
        relationship_confidence=(
            edge.relationship_confidence if valid_relationship_ids else "unknown"
        ),
        relationship_evidence_ids=tuple(valid_relationship_ids),
        connector_experiences=experiences_by_contact.get(connector.contact_id, ()),
        target_experiences=experiences_by_contact.get(target.contact_id, ()),
        shared_schools=supported_category(
            "shared_schools", frozenset({"public_profile"})
        ),
        shared_cities=supported_category(
            "shared_cities", frozenset({"public_profile"})
        ),
        shared_communities=supported_category(
            "shared_communities", frozenset({"post", "public_profile", "talk"})
        ),
        shared_appearances=supported_category(
            "shared_appearances", frozenset({"talk"})
        ),
        role_overlaps=supported_category(
            "role_overlaps", frozenset({"post", "public_profile", "talk"})
        ),
        industry_overlaps=supported_category(
            "industry_overlaps", frozenset({"post", "public_profile", "talk"})
        ),
        investor_overlaps=supported_category(
            "investor_overlaps", frozenset({"public_profile"})
        ),
        supporting_evidence_ids=tuple(valid_supporting_ids),
        validation_errors=tuple(sorted(set(errors))),
    )


def _entry_angle(
    account_id: str,
    evidence: Sequence[EvidenceRecord],
) -> tuple[str, str, tuple[str, ...]]:
    for item in sorted(evidence, key=lambda value: value.evidence_id):
        if item.subject_account_id != account_id:
            continue
        metadata = _metadata(item)
        why = str(metadata.get("why_target_cares", ""))
        value = str(metadata.get("permissionless_value", ""))
        if why and value:
            return why, value, (item.evidence_id,)
    return (
        "Review the cited account evidence before choosing a direct entry angle.",
        "Prepare a small evidence-backed workflow sketch for human review.",
        (),
    )


def run_pipeline(
    input_dir: Path,
    output_dir: Path,
    config_path: Path,
    as_of: date,
) -> CampaignLedger:
    """Run the fixture-only campaign and write byte-stable review artifacts."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_values = _load_json_object(Path(config_path))
    config = replace(CampaignConfig.from_mapping(config_values), as_of=as_of)
    policy = ProviderPolicy.from_path(Path(config_path))

    accounts = load_csv_records(input_dir / "accounts.csv", AccountRecord)
    contacts = load_csv_records(input_dir / "contacts.csv", ContactRecord)
    experiences = load_csv_records(input_dir / "experiences.csv", ExperienceRecord)
    interactions = load_csv_records(input_dir / "interactions.csv", InteractionRecord)
    org_edges = load_csv_records(input_dir / "org_edges.csv", OrgEdgeRecord)
    evidence = load_csv_records(input_dir / "evidence.csv", EvidenceRecord)
    connector_edges = load_csv_records(input_dir / "connector_edges.csv", ConnectorEdge)

    _unique_index(accounts, "account_id", "account")
    _unique_index(contacts, "contact_id", "contact")
    _unique_index(experiences, "experience_id", "experience")
    _unique_index(interactions, "interaction_id", "interaction")
    _unique_index(org_edges, "edge_id", "org edge")
    _unique_index(evidence, "evidence_id", "evidence")
    _unique_index(connector_edges, "edge_id", "connector edge")

    stages: list[CampaignStageLedger] = []
    accounts_by_id = {account.account_id: account for account in accounts}

    account_scores = rank_accounts(accounts, config)
    ranked_rows = [
        _score_to_row(score, accounts_by_id[score.account_id], rank)
        for rank, score in enumerate(account_scores, 1)
    ]
    write_csv_records(output_dir / "ranked_accounts.csv", ranked_rows, _ACCOUNT_FIELDS)
    account_exclusions = Counter(
        score.exclusion_reason
        for score in account_scores
        if score.decision == "exclude" and score.exclusion_reason
    )
    stages.append(
        _stage(
            "rank_accounts",
            input_count=len(accounts),
            output_count=len(ranked_rows),
            exclusions=account_exclusions,
            review_count=sum(score.decision == "review" for score in account_scores),
            output_dir=output_dir,
            artifacts=("ranked_accounts.csv",),
        )
    )

    dedupe = dedupe_contacts(contacts)
    raw_contacts_by_id = {contact.contact_id: contact for contact in contacts}
    alias_audit_by_canonical = {
        audit.canonical_contact_id: audit for audit in dedupe.alias_audit
    }
    dedupe_rows: list[dict[str, object]] = []
    for index, group in enumerate(dedupe.merge_groups, 1):
        audit = alias_audit_by_canonical[group[0]]
        dedupe_rows.append(
            {
                "audit_id": f"merge-{index:03d}",
                "action": "merge",
                "canonical_contact_id": group[0],
                "related_contact_ids": tuple(group),
                "match_types": _dedupe_match_types(group, raw_contacts_by_id),
                "reason": "shared_strong_identifier",
                "linkedin_aliases": audit.linkedin_urls,
                "work_email_aliases": audit.work_emails,
                "identity_aliases": audit.normalized_identities,
            }
        )
    for index, group in enumerate(dedupe.review_collisions, 1):
        match_types = _dedupe_match_types(group, raw_contacts_by_id)
        dedupe_rows.append(
            {
                "audit_id": f"review-{index:03d}",
                "action": "review",
                "canonical_contact_id": group[0],
                "related_contact_ids": tuple(group),
                "match_types": match_types or "normalized_identity",
                "reason": (
                    "conflicting_strong_identity"
                    if match_types
                    else "weak_identity_collision"
                ),
                "linkedin_aliases": tuple(
                    sorted(
                        {
                            normalize_linkedin_url(raw_contacts_by_id[contact_id].linkedin_url)
                            for contact_id in group
                            if raw_contacts_by_id[contact_id].linkedin_url
                        }
                    )
                ),
                "work_email_aliases": tuple(
                    sorted(
                        {
                            normalize_email(raw_contacts_by_id[contact_id].work_email)
                            for contact_id in group
                            if raw_contacts_by_id[contact_id].work_email
                        }
                    )
                ),
                "identity_aliases": tuple(
                    sorted(
                        {
                            "|".join(
                                (
                                    raw_contacts_by_id[contact_id].name.casefold().strip(),
                                    raw_contacts_by_id[contact_id].company.casefold().strip(),
                                    raw_contacts_by_id[contact_id].title.casefold().strip(),
                                )
                            )
                            for contact_id in group
                        }
                    )
                ),
            }
        )
    write_csv_records(output_dir / "contact_dedupe_audit.csv", dedupe_rows, _DEDUPE_FIELDS)
    canonical_contacts = tuple(dedupe.canonical_records)
    canonical_by_id = {contact.contact_id: contact for contact in canonical_contacts}
    (
        experiences,
        interactions,
        org_edges,
        evidence,
        connector_edges,
    ) = _remap_dependent_records(
        experiences=experiences,
        interactions=interactions,
        org_edges=org_edges,
        evidence=evidence,
        connector_edges=connector_edges,
        aliases=dedupe.alias_to_canonical,
        owner_id=config.owner_id,
    )
    evidence_by_id = {item.evidence_id: item for item in evidence}
    interactions_by_evidence_id: dict[str, tuple[InteractionRecord, ...]] = {}
    for evidence_id in sorted({item.evidence_id for item in interactions}):
        interactions_by_evidence_id[evidence_id] = tuple(
            sorted(
                (item for item in interactions if item.evidence_id == evidence_id),
                key=lambda item: item.interaction_id,
            )
        )
    for interaction in interactions:
        cited = evidence_by_id.get(interaction.evidence_id)
        if cited is None:
            raise ValueError(
                f"interaction {interaction.interaction_id} cites unknown evidence "
                f"{interaction.evidence_id}"
            )
        if cited.source_type.casefold() != "interaction":
            raise ValueError(
                f"interaction {interaction.interaction_id} evidence must have source_type=interaction"
            )
        if cited.subject_contact_id != interaction.contact_id:
            raise ValueError(
                f"interaction {interaction.interaction_id} evidence subject does not match contact"
            )
    for org_edge in org_edges:
        missing = sorted(set(org_edge.source_evidence_ids) - set(evidence_by_id))
        if missing:
            raise ValueError(
                f"org edge {org_edge.edge_id} cites unknown evidence {missing[0]}"
            )
    stages.append(
        _stage(
            "dedupe_contacts",
            input_count=len(contacts),
            output_count=len(canonical_contacts),
            exclusions={"merged_duplicates": len(contacts) - len(canonical_contacts)},
            review_count=len(dedupe.review_collisions),
            output_dir=output_dir,
            artifacts=("contact_dedupe_audit.csv",),
        )
    )

    actionable_account_ids = {
        score.account_id for score in account_scores if score.decision in {"include", "review"}
    }
    pdl_requests: list[dict[str, object]] = []
    exclusion_counts = Counter()
    for account in sorted(
        (account for account in accounts if account.account_id in actionable_account_ids),
        key=lambda item: item.domain,
    ):
        canonical_known_contacts = tuple(
            contact
            for contact in canonical_contacts
            if contact.account_id == account.account_id and not _is_open_role(contact)
        )
        canonical_known_ids = {contact.contact_id for contact in canonical_known_contacts}
        known_contacts = tuple(
            contact
            for contact in contacts
            if dedupe.alias_to_canonical[contact.contact_id] in canonical_known_ids
            and not _is_open_role(contact)
        )
        exclusions = build_pdl_exclusions(known_contacts)
        if not exclusions.identities:
            raise ValueError(f"PDL gap-fill for {account.domain} requires known-contact exclusions")
        exclusion_counts.update(
            {
                "known_linkedin_urls": len(exclusions.linkedin_urls),
                "known_emails": len(exclusions.emails),
                "known_identities": len(exclusions.identities),
            }
        )
        pdl_requests.append(
            {
                "account_id": account.account_id,
                "account_name": account.name,
                "domain": account.domain,
                "exclusions": {
                    "emails": list(exclusions.emails),
                    "identities": list(exclusions.identities),
                    "linkedin_urls": list(exclusions.linkedin_urls),
                },
                "known_contact_count": len(known_contacts),
                "operation": "people_search",
                "provider": policy.provider_for("people_search"),
                "status": "fixture_preview_not_executed",
            }
        )
    pdl_payload = {
        "as_of": as_of.isoformat(),
        "fixture_mode": True,
        "requests": pdl_requests,
    }
    _write_json(output_dir / "pdl_gapfill_requests.json", pdl_payload)
    stages.append(
        _stage(
            "prepare_pdl_gapfill",
            input_count=sum(request["known_contact_count"] for request in pdl_requests),
            output_count=len(pdl_requests),
            exclusions=exclusion_counts,
            review_count=0,
            output_dir=output_dir,
            artifacts=("pdl_gapfill_requests.json",),
        )
    )

    committee: list[CommitteeMember] = []
    actionable_people = tuple(
        contact
        for contact in canonical_contacts
        if contact.account_id in actionable_account_ids and not _is_open_role(contact)
    )
    for account_id in sorted(actionable_account_ids):
        committee.extend(build_buying_committee(account_id, actionable_people, config))
    committee_rows = _committee_rows(committee, accounts_by_id, canonical_by_id, evidence)
    committee_rows.sort(
        key=lambda row: (
            str(row["account_id"]),
            _COMMITTEE_ORDER.get(str(row["committee_role"]), len(_COMMITTEE_ORDER)),
            str(row["contact_id"]),
        )
    )
    write_csv_records(output_dir / "buying_committee.csv", committee_rows, _COMMITTEE_FIELDS)
    committee_ids = {member.contact_id for member in committee}
    stages.append(
        _stage(
            "build_buying_committees",
            input_count=len(canonical_contacts),
            output_count=len(committee_rows),
            exclusions={
                "open_roles": sum(_is_open_role(contact) for contact in canonical_contacts),
                "out_of_scope_contacts": sum(
                    not contact.account_id or contact.account_id not in actionable_account_ids
                    for contact in canonical_contacts
                ),
                "unqualified_contacts": sum(
                    contact.contact_id not in committee_ids for contact in actionable_people
                ),
            },
            review_count=0,
            output_dir=output_dir,
            artifacts=("buying_committee.csv",),
        )
    )

    validated_edges = validate_org_edges(org_edges, canonical_contacts)
    org_rows: list[dict[str, object]] = []
    for edge in sorted(validated_edges, key=lambda item: item.edge_id):
        left = canonical_by_id[edge.from_contact_id]
        right = canonical_by_id[edge.to_contact_id]
        org_rows.append(
            {
                "edge_id": edge.edge_id,
                "from_contact_id": edge.from_contact_id,
                "from_name": left.name,
                "from_kind": "open_role" if _is_open_role(left) else "person",
                "to_contact_id": edge.to_contact_id,
                "to_name": right.name,
                "to_kind": "open_role" if _is_open_role(right) else "person",
                "edge_type": edge.edge_type,
                "confidence": edge.confidence,
                "review_required": edge.edge_type == "functional_proximity_inferred",
                "source_evidence_ids": tuple(sorted(edge.source_evidence_ids)),
            }
        )
    write_csv_records(output_dir / "org_edges_review.csv", org_rows, _ORG_FIELDS)
    stages.append(
        _stage(
            "review_org_edges",
            input_count=len(org_edges),
            output_count=len(org_rows),
            exclusions={},
            review_count=sum(row["review_required"] is True for row in org_rows),
            output_dir=output_dir,
            artifacts=("org_edges_review.csv",),
        )
    )

    interaction_rows: list[dict[str, object]] = []
    for interaction in interactions:
        summary = summarize_interactions(interaction.contact_id, (interaction,))
        entry = summary.interactions[0]
        interaction_rows.append(
            {
                "interaction_id": entry.interaction_id,
                "target_id": interaction.contact_id,
                "source": entry.source.value,
                "interaction_type": entry.interaction_type,
                "occurred_at": entry.occurred_at,
                "direction": entry.direction,
                "participant_ids": tuple(sorted(entry.participant_ids)),
                "evidence_id": entry.evidence_id,
                "direct_introduction": entry.direct_introduction,
            }
        )
    interaction_rows.sort(key=lambda row: (str(row["occurred_at"]), str(row["interaction_id"])))
    write_csv_records(output_dir / "interaction_audit.csv", interaction_rows, _INTERACTION_FIELDS)
    stages.append(
        _stage(
            "audit_interactions",
            input_count=len(interactions),
            output_count=len(interaction_rows),
            exclusions={},
            review_count=0,
            output_dir=output_dir,
            artifacts=("interaction_audit.csv",),
        )
    )

    experiences_by_contact: dict[str, tuple[ExperienceRecord, ...]] = {}
    for contact_id in sorted({experience.contact_id for experience in experiences}):
        experiences_by_contact[contact_id] = tuple(
            sorted(
                (experience for experience in experiences if experience.contact_id == contact_id),
                key=lambda item: item.experience_id,
            )
        )
    scored_paths: list[tuple[PathScore, str, bool, ContactRecord]] = []
    for edge in connector_edges:
        metadata = _metadata(edge)
        target_id = str(metadata.get("target_id", ""))
        if not target_id:
            raise ValueError(f"connector edge {edge.edge_id} requires target_id metadata")
        try:
            connector = canonical_by_id[edge.connector_id]
            target = canonical_by_id[target_id]
        except KeyError as error:
            raise ValueError(f"connector edge {edge.edge_id} references an unknown contact") from error
        path_evidence = _validated_path_evidence(
            edge,
            connector,
            target,
            experiences_by_contact,
            evidence_by_id,
            interactions_by_evidence_id,
            config,
        )
        score = score_warm_path(connector, target, path_evidence, config)
        segment = segment_path(score, config)
        investor_only = edge.relationship_type.casefold() == "investor" and bool(
            path_evidence.investor_overlaps
        )
        scored_paths.append((score, segment, investor_only, connector))
    scored_paths.sort(
        key=lambda item: (
            _SEGMENT_ORDER[item[1]],
            -item[0].total_score,
            item[0].path_id,
        )
    )
    path_rows: list[dict[str, object]] = []
    for score, segment, investor_only, connector in scored_paths:
        shared_signal, shared_detail = _path_signal(score)
        path_rows.append(
            {
                "campaign_id": config.campaign_id,
                "owner_id": config.owner_id,
                "path_id": score.path_id,
                "connector_id": score.connector_id,
                "connector_name": connector.name,
                "connector_linkedin": normalize_linkedin_url(connector.linkedin_url)
                if connector.linkedin_url
                else "",
                "connector_company": connector.company,
                "target_id": score.target_id,
                "target_name": score.target_name,
                "target_title": score.target_title,
                "target_company": score.target_company,
                "direct_intro_score": score.direct_intro_score,
                "work_overlap_score": score.work_overlap_score,
                "relationship_score": score.relationship_score,
                "school_city_community_score": score.school_city_community_score,
                "role_industry_score": score.role_industry_score,
                "investor_score": score.investor_score,
                "total_score": score.total_score,
                "relationship_confidence": score.relationship_confidence,
                "segment": segment,
                "reviewed_override": False,
                "investor_only": investor_only,
                "shared_signal": shared_signal,
                "shared_detail": shared_detail,
                "reasons": score.reasons,
                "evidence_ids": score.evidence_ids,
                "validation_errors": score.validation_errors,
            }
        )
    write_csv_records(output_dir / "warm_paths.csv", path_rows, _PATH_FIELDS)
    stages.append(
        _stage(
            "score_warm_paths",
            input_count=len(connector_edges),
            output_count=len(path_rows),
            exclusions={
                "investor_only_not_strong": sum(
                    investor_only and segment != "strong_warm_intro"
                    for _, segment, investor_only, _ in scored_paths
                )
            },
            review_count=sum(segment == "review_warm_intro" for _, segment, _, _ in scored_paths),
            output_dir=output_dir,
            artifacts=("warm_paths.csv",),
        )
    )

    best_path_by_target: dict[str, tuple[PathScore, str]] = {}
    for score, segment, _investor_only, _connector in scored_paths:
        current = best_path_by_target.get(score.target_id)
        if current is None or (_SEGMENT_ORDER[segment], -score.total_score, score.path_id) < (
            _SEGMENT_ORDER[current[1]],
            -current[0].total_score,
            current[0].path_id,
        ):
            best_path_by_target[score.target_id] = (score, segment)
    direct_rows: list[dict[str, object]] = []
    direct_exclusions = Counter()
    for member in committee:
        best = best_path_by_target.get(member.contact_id)
        if best is not None and best[1] == "strong_warm_intro":
            direct_exclusions[best[1]] += 1
            continue
        contact = canonical_by_id[member.contact_id]
        account = accounts_by_id[member.account_id]
        why, value, evidence_ids = _entry_angle(member.account_id, evidence)
        path_segment = best[1] if best is not None else "no_strong_path"
        path_evidence_ids = best[0].evidence_ids if best is not None else ()
        direct_rows.append(
            {
                "target_id": member.contact_id,
                "target_name": member.name,
                "target_title": member.title,
                "target_company": contact.company,
                "account_id": member.account_id,
                "account_name": account.name,
                "linkedin_url": normalize_linkedin_url(contact.linkedin_url)
                if contact.linkedin_url
                else "",
                "work_email": normalize_email(contact.work_email) if contact.work_email else "",
                "path_segment": path_segment,
                "why_target_cares": why,
                "permissionless_value": value,
                "evidence_ids": tuple(sorted({*evidence_ids, *path_evidence_ids})),
                "approved": False,
            }
        )
    direct_rows.sort(key=lambda row: (str(row["account_id"]), str(row["target_id"])))
    write_csv_records(output_dir / "direct_outreach.csv", direct_rows, _DIRECT_FIELDS)
    stages.append(
        _stage(
            "prepare_direct_outreach",
            input_count=len(committee),
            output_count=len(direct_rows),
            exclusions=direct_exclusions,
            review_count=len(direct_rows),
            output_dir=output_dir,
            artifacts=("direct_outreach.csv",),
        )
    )

    artifact_hashes = {
        name: digest
        for stage in stages
        for name, digest in stage.artifact_hashes.items()
    }
    ledger = CampaignLedger(
        campaign_id=config.campaign_id,
        as_of=as_of.isoformat(),
        fixture_mode=True,
        stages=tuple(stages),
        artifact_hashes=dict(sorted(artifact_hashes.items())),
        total_cache_hits=sum(stage.cache_hits for stage in stages),
        total_authorized_provider_calls=sum(stage.authorized_provider_calls for stage in stages),
        total_estimated_spend_usd="0.00",
        evidence_freshness=_evidence_freshness(evidence, as_of),
        path_segment_counts={
            segment: sum(item[1] == segment for item in scored_paths)
            for segment in (
                "no_strong_path",
                "review_warm_intro",
                "strong_warm_intro",
            )
        },
        approved_message_count=0,
        activated_message_count=0,
    )
    _write_json(output_dir / "campaign_ledger.json", asdict(ledger))
    return ledger


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", dest="config_path", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    ledger = run_pipeline(args.input_dir, args.output_dir, args.config_path, args.as_of)
    print(
        f"Wrote {len(ledger.artifact_hashes) + 1} deterministic fixture artifacts "
        f"with {ledger.total_authorized_provider_calls} provider calls and "
        f"${ledger.total_estimated_spend_usd} estimated spend."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
