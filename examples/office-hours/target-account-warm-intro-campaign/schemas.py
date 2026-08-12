"""Immutable records and deterministic file contracts for the campaign example."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import MISSING, dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType, UnionType
from typing import Iterable, Mapping, Sequence, TypeVar, Union, get_args, get_origin, get_type_hints
from urllib.parse import urlsplit


T = TypeVar("T")

_DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_IDENTITY_SPACE = re.compile(r"\s+")


def _clean_text(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    return value.strip()


def normalize_domain(value: str) -> str:
    """Return a hostname suitable for the stable account identifier."""
    candidate = _clean_text(value).lower()
    if not candidate or any(character.isspace() for character in candidate):
        raise ValueError("value is not a domain")

    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}", scheme="https")
    hostname = parsed.hostname
    if not hostname or parsed.username or parsed.password or "@" in candidate:
        raise ValueError("value is not a domain")
    hostname = hostname.rstrip(".")
    if hostname.startswith("www."):
        hostname = hostname[4:]
    labels = hostname.split(".")
    if len(labels) < 2 or any(not _DOMAIN_LABEL.fullmatch(label) for label in labels):
        raise ValueError("value is not a domain")
    return hostname


def normalize_linkedin_url(value: str) -> str:
    """Normalize a LinkedIn person URL without query strings or a scheme."""
    candidate = _clean_text(value)
    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}", scheme="https")
    hostname = (parsed.hostname or "").lower()
    if hostname == "www.linkedin.com":
        hostname = "linkedin.com"
    path_parts = [part for part in parsed.path.split("/") if part]
    if hostname != "linkedin.com" or len(path_parts) != 2 or path_parts[0].lower() != "in":
        raise ValueError("value is not a LinkedIn profile URL")
    slug = path_parts[1].strip().lower()
    if not slug or any(character.isspace() for character in slug):
        raise ValueError("value is not a LinkedIn profile URL")
    return f"linkedin.com/in/{slug}"


def normalize_email(value: str) -> str:
    """Normalize and validate a work-email identifier."""
    candidate = _clean_text(value).lower()
    if candidate.count("@") != 1 or any(character.isspace() for character in candidate):
        raise ValueError("value is not an email address")
    local, domain = candidate.rsplit("@", 1)
    if not local:
        raise ValueError("value is not an email address")
    return f"{local}@{normalize_domain(domain)}"


def _normalize_identity_part(value: str) -> str:
    return _IDENTITY_SPACE.sub(" ", _clean_text(value).casefold())


def normalized_identity(name: str, company: str, title: str) -> str:
    """Return the deterministic weak identity used only when strong IDs are absent."""
    parts = tuple(_normalize_identity_part(value) for value in (name, company, title))
    if not all(parts):
        raise ValueError(
            "identity review required: name, company, and title are required for a weak identity"
        )
    return "|".join(parts)


@dataclass(frozen=True)
class AccountRecord:
    account_id: str
    name: str
    domain: str
    website_url: str = ""
    industry: str = ""
    employee_count: int | None = None
    source_record_id: str = ""
    source_ref: str = ""
    source_metadata_json: str = "{}"


@dataclass(frozen=True)
class ContactRecord:
    contact_id: str
    name: str
    company: str
    title: str
    account_id: str = ""
    linkedin_url: str = ""
    work_email: str = ""
    source_record_ids: tuple[str, ...] = ()
    source_ref: str = ""
    source_metadata_json: str = "{}"


def canonical_contact_key(contact: ContactRecord) -> tuple[str, str]:
    """Return one stable primary key using the campaign's required precedence."""
    if contact.linkedin_url:
        return "linkedin", normalize_linkedin_url(contact.linkedin_url)
    if contact.work_email:
        return "email", normalize_email(contact.work_email)
    return "identity", normalized_identity(contact.name, contact.company, contact.title)


@dataclass(frozen=True)
class ExperienceRecord:
    experience_id: str
    contact_id: str
    company: str
    title: str
    account_id: str = ""
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    source_record_id: str = ""
    source_ref: str = ""
    source_metadata_json: str = "{}"


@dataclass(frozen=True)
class InteractionRecord:
    interaction_id: str
    contact_id: str
    source: str
    interaction_type: str
    occurred_at: datetime | None = None
    direction: str = ""
    participant_ids: tuple[str, ...] = ()
    evidence_id: str = ""
    source_record_id: str = ""
    source_ref: str = ""
    source_metadata_json: str = "{}"


@dataclass(frozen=True)
class OrgEdgeRecord:
    edge_id: str
    from_contact_id: str
    to_contact_id: str
    edge_type: str
    confidence: str = "unknown"
    source_evidence_ids: tuple[str, ...] = ()
    source_record_id: str = ""
    source_ref: str = ""
    source_metadata_json: str = "{}"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source_type: str
    observed_at: datetime | None = None
    source_url: str = ""
    immutable_source_id: str = ""
    subject_contact_id: str = ""
    subject_account_id: str = ""
    confidence: str = "unknown"
    cache_key: str = ""
    source_ref: str = ""
    source_metadata_json: str = "{}"


@dataclass(frozen=True)
class ConnectorEdge:
    edge_id: str
    owner_id: str
    connector_id: str
    relationship_type: str
    relationship_confidence: str = "unknown"
    evidence_ids: tuple[str, ...] = ()
    source_record_id: str = ""
    source_ref: str = ""
    source_metadata_json: str = "{}"


@dataclass(frozen=True)
class PathScore:
    path_id: str
    connector_id: str
    target_id: str
    target_name: str
    target_title: str
    target_company: str
    direct_intro_score: int = 0
    work_overlap_score: int = 0
    relationship_score: int = 0
    school_city_community_score: int = 0
    role_industry_score: int = 0
    investor_score: int = 0
    relationship_confidence: str = "unknown"
    reasons: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    @property
    def total_score(self) -> int:
        return sum(
            (
                self.direct_intro_score,
                self.work_overlap_score,
                self.relationship_score,
                self.school_city_community_score,
                self.role_industry_score,
                self.investor_score,
            )
        )


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise TypeError("money values must be Decimal, strings, or integers; never float")
    if isinstance(value, (str, int)):
        return Decimal(str(value))
    raise TypeError("money values must be Decimal, strings, or integers")


def _freeze(value: object) -> object:
    """Recursively copy mutable config data into immutable deterministic values."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class CampaignConfig:
    campaign_id: str
    owner_id: str
    as_of: date
    title_catalog: Mapping[str, object]
    score_weights: Mapping[str, int]
    segment_thresholds: Mapping[str, int]
    exclusions: Mapping[str, tuple[str, ...]]
    provider_routes: Mapping[str, str]
    blocked_operations: tuple[str, ...]
    cache_directory: Path
    provider_caps: Mapping[str, Decimal]
    campaign_cap: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "title_catalog", _freeze(self.title_catalog))
        object.__setattr__(self, "score_weights", MappingProxyType(dict(self.score_weights)))
        object.__setattr__(self, "segment_thresholds", MappingProxyType(dict(self.segment_thresholds)))
        object.__setattr__(
            self,
            "exclusions",
            MappingProxyType({key: tuple(value) for key, value in self.exclusions.items()}),
        )
        object.__setattr__(self, "provider_routes", MappingProxyType(dict(self.provider_routes)))
        object.__setattr__(self, "blocked_operations", tuple(self.blocked_operations))
        object.__setattr__(self, "cache_directory", Path(self.cache_directory))
        object.__setattr__(
            self,
            "provider_caps",
            MappingProxyType({key: _decimal(value) for key, value in self.provider_caps.items()}),
        )
        object.__setattr__(self, "campaign_cap", _decimal(self.campaign_cap))

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "CampaignConfig":
        """Build config from parsed JSON while preserving exact decimal money values."""
        as_of_value = values["as_of"]
        if isinstance(as_of_value, date):
            as_of = as_of_value
        elif isinstance(as_of_value, str):
            as_of = date.fromisoformat(as_of_value)
        else:
            raise TypeError("as_of must be an ISO date")
        return cls(
            campaign_id=str(values["campaign_id"]),
            owner_id=str(values["owner_id"]),
            as_of=as_of,
            title_catalog=dict(values.get("title_catalog", {})),
            score_weights={key: int(value) for key, value in dict(values.get("score_weights", {})).items()},
            segment_thresholds={key: int(value) for key, value in dict(values.get("segment_thresholds", {})).items()},
            exclusions={key: tuple(value) for key, value in dict(values.get("exclusions", {})).items()},
            provider_routes={key: str(value) for key, value in dict(values.get("provider_routes", {})).items()},
            blocked_operations=tuple(values.get("blocked_operations", ())),
            cache_directory=Path(str(values.get("cache_directory", ".cache"))),
            provider_caps=dict(values.get("provider_caps", {})),
            campaign_cap=_decimal(values["campaign_cap"]),
        )


def _required_columns(record_type: type[object]) -> set[str]:
    return {
        record_field.name
        for record_field in fields(record_type)
        if record_field.init
        and record_field.default is MISSING
        and record_field.default_factory is MISSING  # type: ignore[comparison-overlap]
    }


def _parse_csv_value(value: str, annotation: object) -> object:
    if annotation is str:
        return value
    if annotation is int:
        return int(value)
    if annotation is bool:
        lowered = value.strip().casefold()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
        raise ValueError(f"invalid boolean value: {value!r}")
    if annotation is Decimal:
        return _decimal(value)
    if annotation is Path:
        return Path(value)
    if annotation is datetime:
        return datetime.fromisoformat(value)
    if annotation is date:
        return date.fromisoformat(value)

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, UnionType) and type(None) in args:
        if value == "":
            return None
        non_none = next(argument for argument in args if argument is not type(None))
        return _parse_csv_value(value, non_none)
    if origin is tuple:
        if not value:
            return ()
        decoded = json.loads(value) if value.lstrip().startswith("[") else value.split("|")
        if not isinstance(decoded, list):
            raise ValueError("tuple fields must contain a JSON array or pipe-delimited values")
        return tuple(decoded)
    return value


def _encode_csv_value(value: object) -> str:
    """Encode every supported record value so ``_parse_csv_value`` can restore it."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return json.dumps(list(value), ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int)):
        return str(value)
    raise TypeError(f"unsupported CSV field value type: {type(value).__name__}")


def load_csv_records(path: Path, record_type: type[T]) -> list[T]:
    """Load dataclass records without losing provider columns unknown to this version."""
    try:
        record_fields = fields(record_type)
    except TypeError as error:
        raise TypeError("record_type must be a dataclass type") from error
    field_names = {record_field.name for record_field in record_fields}
    if "source_metadata_json" not in field_names:
        raise ValueError("record_type must define source_metadata_json")
    annotations = get_type_hints(record_type)

    with Path(path).open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")
        present_columns = set(reader.fieldnames)
        missing = sorted(_required_columns(record_type) - present_columns)
        if missing:
            raise ValueError(f"missing required columns: {', '.join(missing)}")

        records: list[T] = []
        for row in reader:
            existing_metadata = row.get("source_metadata_json", "") or "{}"
            try:
                metadata = json.loads(existing_metadata)
            except json.JSONDecodeError as error:
                raise ValueError("source_metadata_json must contain a JSON object") from error
            if not isinstance(metadata, dict):
                raise ValueError("source_metadata_json must contain a JSON object")
            metadata.update(
                {key: value for key, value in row.items() if key not in field_names and value is not None}
            )
            values: dict[str, object] = {}
            for record_field in record_fields:
                if record_field.name == "source_metadata_json":
                    values[record_field.name] = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
                elif record_field.name in row and row[record_field.name] is not None:
                    values[record_field.name] = _parse_csv_value(
                        row[record_field.name] or "", annotations.get(record_field.name, str)
                    )
            records.append(record_type(**values))
    return records


def write_csv_records(
    path: Path,
    rows: Iterable[Mapping[str, object]],
    fieldnames: Sequence[str],
) -> None:
    """Write deterministic UTF-8 CSV output with the caller's declared column order."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=list(fieldnames),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _encode_csv_value(value) for key, value in row.items()})
