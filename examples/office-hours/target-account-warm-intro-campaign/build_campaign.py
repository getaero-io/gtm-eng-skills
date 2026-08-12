"""Build auditable contacts, buying committees, and relationship context."""

from __future__ import annotations

import json
import re
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Sequence

from schemas import (
    CampaignConfig,
    ContactRecord,
    InteractionRecord,
    OrgEdgeRecord,
    normalize_email,
    normalize_linkedin_url,
    normalized_identity,
)


_TITLE_SPACE = re.compile(r"[^a-z0-9]+")
_TITLE_FAMILIES = (
    ("gtm_engineering", ("gtm engineer", "gtm engineering")),
    ("revenue_systems", ("revenue system", "revenue systems")),
    ("revenue_operations", ("revenue operations", "revops")),
    ("business_operations", ("business operations", "bizops")),
    ("growth_engineering", ("growth engineer", "growth engineering")),
    ("gtm_analytics", ("gtm analytics",)),
    ("marketing_operations", ("marketing operations", "marketing ops")),
)
_COMMITTEE_ROLES = {
    "gtm_engineering": "technical_champion",
    "revenue_systems": "technical_champion",
    "growth_engineering": "technical_champion",
    "revenue_operations": "operational_buyer",
    "business_operations": "operational_buyer",
    "gtm_analytics": "operational_buyer",
    "marketing_operations": "operational_buyer",
}
_COMMITTEE_ORDER = {
    "technical_champion": 0,
    "operational_buyer": 1,
    "economic_buyer": 2,
    "adjacent_validator": 3,
}
_CONFIGURED_COMMITTEE_ROLES = {
    "technical_champion": "technical_champion",
    "technical_champions": "technical_champion",
    "technical_gtm": "technical_champion",
    "operational_buyer": "operational_buyer",
    "operational_buyers": "operational_buyer",
    "economic_buyer": "economic_buyer",
    "economic_buyers": "economic_buyer",
    "adjacent_validator": "adjacent_validator",
    "adjacent_validators": "adjacent_validator",
}


@dataclass(frozen=True)
class ContactAliasAudit:
    canonical_contact_id: str
    contact_ids: tuple[str, ...]
    linkedin_urls: tuple[str, ...]
    work_emails: tuple[str, ...]
    normalized_identities: tuple[str, ...]


@dataclass(frozen=True)
class DedupeResult:
    canonical_records: tuple[ContactRecord, ...]
    merge_groups: tuple[tuple[str, ...], ...]
    review_collisions: tuple[tuple[str, ...], ...]
    alias_to_canonical: Mapping[str, str]
    alias_audit: tuple[ContactAliasAudit, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "alias_to_canonical",
            MappingProxyType(dict(self.alias_to_canonical)),
        )


@dataclass(frozen=True)
class QualificationResult:
    contact_id: str
    qualified: bool
    role_family: str = ""
    committee_role: str = ""


@dataclass(frozen=True)
class CommitteeMember:
    contact_id: str
    account_id: str
    name: str
    title: str
    role_family: str
    committee_role: str
    source_record_ids: tuple[str, ...] = ()


class InteractionSource(str, Enum):
    CRM = "crm"
    EMAIL = "email"
    EVENT = "event"
    WEBSITE_FORM = "website_form"
    SALES_CALL = "sales_call"
    MANUAL_CONFIRMATION = "manual_confirmation"


@dataclass(frozen=True)
class InteractionAuditEntry:
    interaction_id: str
    source: InteractionSource
    interaction_type: str
    occurred_at: datetime
    evidence_id: str
    direction: str = ""
    participant_ids: tuple[str, ...] = ()
    direct_introduction: bool = False


@dataclass(frozen=True)
class InteractionSummary:
    target_id: str
    interactions: tuple[InteractionAuditEntry, ...]
    direct_introductions: tuple[InteractionAuditEntry, ...]
    emails: tuple[InteractionAuditEntry, ...]
    calls: tuple[InteractionAuditEntry, ...]
    evidence_ids: tuple[str, ...]
    latest_interaction_at: datetime | None

    @property
    def has_direct_introduction(self) -> bool:
        return bool(self.direct_introductions)


_TITLE_IDENTITY_NOISE = {
    "chief",
    "director",
    "head",
    "lead",
    "manager",
    "of",
    "officer",
    "president",
    "senior",
    "sr",
    "the",
    "vice",
    "vp",
}


def _identity_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _title_identity_tokens(value: str) -> frozenset[str]:
    return frozenset(
        token
        for token in _TITLE_SPACE.split(value.casefold())
        if token and token not in _TITLE_IDENTITY_NOISE
    )


def _strong_component_conflicts(members: Sequence[ContactRecord]) -> bool:
    """Return true when a shared identifier bridges contradictory people."""
    names = {_identity_text(member.name) for member in members if member.name.strip()}
    accounts = {
        _identity_text(member.account_id)
        for member in members
        if member.account_id.strip()
    }
    companies = {
        _identity_text(member.company)
        for member in members
        if member.company.strip()
    }
    if len(names) > 1 or len(accounts) > 1 or len(companies) > 1:
        return True
    title_tokens = [
        _title_identity_tokens(member.title)
        for member in members
        if member.title.strip()
    ]
    return any(
        left and right and left.isdisjoint(right)
        for index, left in enumerate(title_tokens)
        for right in title_tokens[index + 1 :]
    )


def dedupe_contacts(contacts: Sequence[ContactRecord]) -> DedupeResult:
    """Merge only coherent strong-ID components and retain every alias."""
    parents = list(range(len(contacts)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    strong_identifiers: dict[tuple[str, str], int] = {}
    normalized_identifiers: dict[int, list[tuple[str, str]]] = {}
    invalid_identity_indices: set[int] = set()
    for index, contact in enumerate(contacts):
        identifiers: list[tuple[str, str]] = []
        if contact.linkedin_url:
            try:
                identifiers.append(("linkedin", normalize_linkedin_url(contact.linkedin_url)))
            except ValueError:
                invalid_identity_indices.add(index)
        if contact.work_email:
            try:
                identifiers.append(("email", normalize_email(contact.work_email)))
            except ValueError:
                invalid_identity_indices.add(index)
        normalized_identifiers[index] = identifiers
        for identifier in identifiers:
            previous_index = strong_identifiers.setdefault(identifier, index)
            union(index, previous_index)

    grouped_indices: dict[int, list[int]] = {}
    for index in range(len(contacts)):
        grouped_indices.setdefault(find(index), []).append(index)

    canonical_records: list[ContactRecord] = []
    merge_groups: list[tuple[str, ...]] = []
    identity_groups: dict[str, set[str]] = {}
    review_collisions: list[tuple[str, ...]] = []
    alias_to_canonical: dict[str, str] = {}
    alias_audit: list[ContactAliasAudit] = []
    for indices in grouped_indices.values():
        indexed_members = sorted(
            ((index, contacts[index]) for index in indices),
            key=lambda item: item[1].contact_id,
        )
        members = tuple(member for _, member in indexed_members)
        if len(members) > 1 and _strong_component_conflicts(members):
            review_collisions.append(tuple(member.contact_id for member in members))
            member_groups = tuple((item,) for item in indexed_members)
        else:
            member_groups = (tuple(indexed_members),)

        for safe_indexed_members in member_groups:
            safe_indices = tuple(index for index, _ in safe_indexed_members)
            safe_members = tuple(member for _, member in safe_indexed_members)
            source_ids = tuple(
                sorted(
                    {
                        source_id
                        for member in safe_members
                        for source_id in member.source_record_ids
                    }
                )
            )
            linkedins = sorted(
                {
                    value
                    for index in safe_indices
                    for kind, value in normalized_identifiers[index]
                    if kind == "linkedin"
                }
            )
            emails = sorted(
                {
                    value
                    for index in safe_indices
                    for kind, value in normalized_identifiers[index]
                    if kind == "email"
                }
            )
            identities: set[str] = set()
            for member in safe_members:
                try:
                    identities.add(
                        normalized_identity(member.name, member.company, member.title)
                    )
                except ValueError:
                    pass
            canonical = safe_members[0]
            canonical_id = canonical.contact_id
            canonical_index = safe_indices[0]
            canonical_linkedins = tuple(
                value
                for kind, value in normalized_identifiers[canonical_index]
                if kind == "linkedin"
            )
            canonical_emails = tuple(
                value
                for kind, value in normalized_identifiers[canonical_index]
                if kind == "email"
            )
            canonical_records.append(
                replace(
                    canonical,
                    linkedin_url=(
                        canonical_linkedins[0]
                        if canonical_linkedins
                        else (linkedins[0] if linkedins else "")
                    ),
                    work_email=(
                        canonical_emails[0]
                        if canonical_emails
                        else (emails[0] if emails else "")
                    ),
                    source_record_ids=source_ids,
                )
            )
            for member in safe_members:
                alias_to_canonical[member.contact_id] = canonical_id
            alias_audit.append(
                ContactAliasAudit(
                    canonical_contact_id=canonical_id,
                    contact_ids=tuple(member.contact_id for member in safe_members),
                    linkedin_urls=tuple(linkedins),
                    work_emails=tuple(emails),
                    normalized_identities=tuple(sorted(identities)),
                )
            )
            if len(safe_members) > 1:
                merge_groups.append(tuple(member.contact_id for member in safe_members))
            if any(index in invalid_identity_indices for index in safe_indices):
                review_collisions.append(
                    tuple(member.contact_id for member in safe_members)
                )
            for member in safe_members:
                try:
                    weak_identity = normalized_identity(
                        member.name, member.company, member.title
                    )
                except ValueError:
                    if not any(normalized_identifiers[index] for index in safe_indices):
                        review_collisions.append((canonical_id,))
                else:
                    identity_groups.setdefault(weak_identity, set()).add(canonical_id)
    canonical_records.sort(key=lambda contact: contact.contact_id)
    review_collisions.extend(
        tuple(sorted(canonical_ids))
        for canonical_ids in identity_groups.values()
        if len(canonical_ids) > 1
    )
    return DedupeResult(
        canonical_records=tuple(canonical_records),
        merge_groups=tuple(sorted(merge_groups)),
        review_collisions=tuple(sorted(set(review_collisions))),
        alias_to_canonical=alias_to_canonical,
        alias_audit=tuple(sorted(alias_audit, key=lambda item: item.canonical_contact_id)),
    )


def _normalized_title(title: str) -> str:
    return " ".join(part for part in _TITLE_SPACE.split(title.casefold()) if part)


def _contains_title_phrase(title: str, phrase: str) -> bool:
    return f" {phrase} " in f" {title} "


def qualify_contact(contact: ContactRecord, config: CampaignConfig) -> QualificationResult:
    """Classify a contact into one explicit technical-GTM role family."""
    normalized_title = _normalized_title(contact.title)
    if any(term in normalized_title.split() for term in ("recruiter", "recruiting")):
        return QualificationResult(contact_id=contact.contact_id, qualified=False)
    for role_family, phrases in _TITLE_FAMILIES:
        if any(_contains_title_phrase(normalized_title, phrase) for phrase in phrases):
            return QualificationResult(
                contact_id=contact.contact_id,
                qualified=True,
                role_family=role_family,
                committee_role=_COMMITTEE_ROLES[role_family],
            )
    for configured_family, raw_entry in config.title_catalog.items():
        if not isinstance(raw_entry, Mapping):
            continue
        raw_titles = raw_entry.get("titles", ())
        titles = (raw_titles,) if isinstance(raw_titles, str) else tuple(raw_titles)
        normalized_configured_titles = tuple(
            title
            for title in (_normalized_title(str(value)) for value in titles)
            if title
        )
        if any(
            _contains_title_phrase(normalized_title, title)
            for title in normalized_configured_titles
        ):
            role_family = str(raw_entry.get("role_family", configured_family))
            configured_role = str(raw_entry.get("committee_role", ""))
            family_key = _normalized_title(str(configured_family)).replace(" ", "_")
            committee_role = configured_role or _COMMITTEE_ROLES.get(
                role_family,
                _CONFIGURED_COMMITTEE_ROLES.get(family_key, "technical_champion"),
            )
            return QualificationResult(
                contact_id=contact.contact_id,
                qualified=True,
                role_family=role_family,
                committee_role=committee_role,
            )
    return QualificationResult(contact_id=contact.contact_id, qualified=False)


def build_buying_committee(
    account_id: str,
    contacts: Sequence[ContactRecord],
    config: CampaignConfig,
) -> list[CommitteeMember]:
    """Return qualified account members in deterministic outreach priority."""
    committee: list[CommitteeMember] = []
    for contact in contacts:
        if contact.account_id != account_id:
            continue
        qualification = qualify_contact(contact, config)
        if not qualification.qualified:
            continue
        committee.append(
            CommitteeMember(
                contact_id=contact.contact_id,
                account_id=contact.account_id,
                name=contact.name,
                title=contact.title,
                role_family=qualification.role_family,
                committee_role=qualification.committee_role,
                source_record_ids=contact.source_record_ids,
            )
        )
    committee.sort(
        key=lambda member: (
            _COMMITTEE_ORDER.get(member.committee_role, len(_COMMITTEE_ORDER)),
            _normalized_title(member.title),
            member.name.casefold(),
            member.contact_id,
        )
    )
    return committee


def _is_open_role(contact: ContactRecord) -> bool:
    try:
        metadata = json.loads(contact.source_metadata_json)
    except json.JSONDecodeError:
        metadata = {}
    if not isinstance(metadata, Mapping):
        metadata = {}
    node_type = metadata.get("node_type", metadata.get("entity_type", ""))
    normalized_node_type = str(node_type).casefold().replace("-", "_").replace(" ", "_")
    normalized_contact_id = contact.contact_id.casefold().replace("-", "_")
    return (
        normalized_node_type in {"open_role", "job_opening"}
        or metadata.get("is_open_role") is True
        or normalized_contact_id == "open_role"
        or normalized_contact_id.startswith("open_role:")
        or normalized_contact_id.startswith("open_role_")
    )


def validate_org_edges(
    edges: Sequence[OrgEdgeRecord], contacts: Sequence[ContactRecord]
) -> list[OrgEdgeRecord]:
    """Reject malformed org semantics without rewriting the source edge."""
    contacts_by_id = {contact.contact_id: contact for contact in contacts}
    validated: list[OrgEdgeRecord] = []
    seen_edge_ids: set[str] = set()
    for edge in edges:
        edge_label = edge.edge_id or "<missing>"
        endpoints = (edge.from_contact_id, edge.to_contact_id)
        if not edge.edge_id or edge.edge_id in seen_edge_ids:
            raise ValueError(f"invalid org edge {edge_label}: edge ID must be unique and non-empty")
        seen_edge_ids.add(edge.edge_id)
        if not all(endpoints) or edge.from_contact_id == edge.to_contact_id:
            raise ValueError(f"invalid org edge {edge_label}: endpoints must be distinct and non-empty")
        missing = [endpoint for endpoint in endpoints if endpoint not in contacts_by_id]
        if missing:
            raise ValueError(
                f"invalid org edge {edge_label}: unknown contact {missing[0]}"
            )
        if edge.edge_type not in {
            "reports_to_confirmed",
            "functional_proximity_inferred",
        }:
            raise ValueError(f"invalid org edge {edge_label}: unsupported edge type")
        has_open_role = any(_is_open_role(contacts_by_id[endpoint]) for endpoint in endpoints)
        if edge.edge_type == "reports_to_confirmed" and has_open_role:
            raise ValueError(f"invalid org edge {edge_label}: open role cannot be confirmed person")
        if edge.edge_type == "reports_to_confirmed" and edge.confidence != "confirmed":
            raise ValueError(
                f"invalid org edge {edge_label}: reports_to_confirmed requires confidence=confirmed"
            )
        validated.append(edge)
    return validated


def person_centric_neighborhood(
    target_id: str,
    edges: Sequence[OrgEdgeRecord],
    max_depth: int = 3,
) -> list[OrgEdgeRecord]:
    """Traverse incident org edges without changing their recorded direction."""
    if not 0 <= max_depth <= 3:
        raise ValueError("max_depth must be between 0 and the global cap of 3")
    adjacency: dict[str, list[OrgEdgeRecord]] = {}
    for edge in edges:
        adjacency.setdefault(edge.from_contact_id, []).append(edge)
        adjacency.setdefault(edge.to_contact_id, []).append(edge)
    for incident in adjacency.values():
        incident.sort(key=lambda edge: edge.edge_id)

    visited_nodes = {target_id}
    visited_edges: set[str] = set()
    queue = deque([(target_id, 0)])
    neighborhood: list[OrgEdgeRecord] = []
    while queue:
        current_id, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in adjacency.get(current_id, ()):
            if edge.edge_id in visited_edges:
                continue
            other_id = (
                edge.to_contact_id
                if edge.from_contact_id == current_id
                else edge.from_contact_id
            )
            if other_id in visited_nodes:
                visited_edges.add(edge.edge_id)
                continue
            visited_edges.add(edge.edge_id)
            visited_nodes.add(other_id)
            neighborhood.append(edge)
            queue.append((other_id, depth + 1))
    return neighborhood


def summarize_interactions(
    target_id: str, interactions: Sequence[InteractionRecord]
) -> InteractionSummary:
    """Normalize aware timestamps to UTC; reject naive first-party audit times."""
    audit_entries: list[InteractionAuditEntry] = []
    for interaction in interactions:
        if (
            interaction.contact_id != target_id
            and target_id not in interaction.participant_ids
        ):
            continue
        try:
            source = InteractionSource(interaction.source.casefold())
        except ValueError as error:
            raise ValueError(
                f"interaction {interaction.interaction_id} has unsupported source {interaction.source!r}"
            ) from error
        if interaction.occurred_at is None:
            raise ValueError(f"interaction {interaction.interaction_id} requires a timestamp")
        if interaction.occurred_at.utcoffset() is None:
            raise ValueError(
                f"interaction {interaction.interaction_id} requires a timezone-aware timestamp"
            )
        if not interaction.evidence_id:
            raise ValueError(f"interaction {interaction.interaction_id} requires an evidence ID")
        occurred_at = interaction.occurred_at.astimezone(timezone.utc)
        interaction_type = interaction.interaction_type.casefold()
        is_direct_introduction = (
            interaction_type == "introduction"
            or source is InteractionSource.MANUAL_CONFIRMATION
        )
        audit_entries.append(
            InteractionAuditEntry(
                interaction_id=interaction.interaction_id,
                source=source,
                interaction_type=interaction.interaction_type,
                occurred_at=occurred_at,
                evidence_id=interaction.evidence_id,
                direction=interaction.direction,
                participant_ids=interaction.participant_ids,
                direct_introduction=is_direct_introduction,
            )
        )
    audit_entries.sort(key=lambda item: (item.occurred_at, item.interaction_id))
    entries = tuple(audit_entries)
    return InteractionSummary(
        target_id=target_id,
        interactions=entries,
        direct_introductions=tuple(item for item in entries if item.direct_introduction),
        emails=tuple(
            item
            for item in entries
            if item.source is InteractionSource.EMAIL
            or item.interaction_type.casefold() == "email"
        ),
        calls=tuple(
            item
            for item in entries
            if item.source is InteractionSource.SALES_CALL
            or item.interaction_type.casefold() in {"call", "sales_call"}
        ),
        evidence_ids=tuple(sorted({item.evidence_id for item in entries})),
        latest_interaction_at=entries[-1].occurred_at if entries else None,
    )
