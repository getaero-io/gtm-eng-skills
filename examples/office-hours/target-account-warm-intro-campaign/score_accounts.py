"""Transparent, deterministic account scoring for the campaign example."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from schemas import AccountRecord, CampaignConfig, normalize_domain


_COMPONENTS = (
    "icp_fit",
    "engineering_led",
    "technical_gtm_signal",
    "growth_recency",
    "customer_similarity",
    "first_party_engagement",
)
_EXCLUSION_KEYS = (
    ("existing_customers", "existing_customer"),
    ("vendors", "vendor"),
    ("partners", "partner"),
    ("do_not_contact", "do_not_contact"),
)


@dataclass(frozen=True)
class AccountScore:
    """The independently reviewable components behind an account decision."""

    account_id: str
    icp_fit: int = 0
    engineering_led: int = 0
    technical_gtm_signal: int = 0
    growth_recency: int = 0
    customer_similarity: int = 0
    first_party_engagement: int = 0
    decision: str = "review"
    exclusion_reason: str = ""

    @property
    def total_score(self) -> int:
        return sum(getattr(self, component) for component in _COMPONENTS)


def _metadata(account: AccountRecord) -> Mapping[str, object]:
    try:
        metadata = json.loads(account.source_metadata_json or "{}")
    except json.JSONDecodeError as error:
        raise ValueError("account source_metadata_json must contain a JSON object") from error
    if not isinstance(metadata, dict):
        raise ValueError("account source_metadata_json must contain a JSON object")
    return metadata


def _component(value: object, maximum: int) -> int:
    """Convert an auditable boolean or bounded integer signal into points."""
    if maximum < 0:
        raise ValueError("score weights must be non-negative integers")
    if isinstance(value, bool):
        return maximum if value else 0
    if isinstance(value, int):
        return min(max(value, 0), maximum)
    return 0


def _configured_weight(config: CampaignConfig, component: str) -> int:
    value = config.score_weights.get(component, 0)
    if not isinstance(value, int):
        raise ValueError(f"score weight for {component} must be an integer")
    return value


def _has_technical_gtm_hiring(metadata: Mapping[str, object], config: CampaignConfig) -> object:
    explicit = metadata.get("technical_gtm_signal", metadata.get("technical_gtm_hiring"))
    if explicit is not None:
        return explicit
    catalog = config.title_catalog.get("technical_gtm", {})
    titles = catalog.get("titles", ()) if isinstance(catalog, Mapping) else ()
    known_titles = {str(title).casefold() for title in titles}
    open_roles = metadata.get("open_roles", ())
    if not isinstance(open_roles, (list, tuple)):
        return False
    return any(str(role).casefold() in known_titles for role in open_roles)


def _growth_signal(metadata: Mapping[str, object]) -> object:
    explicit = metadata.get("growth_recency", metadata.get("recent_growth"))
    if explicit is not None:
        return explicit
    days = metadata.get("growth_recency_days")
    if isinstance(days, int) and not isinstance(days, bool):
        return days <= 90
    return False


def _exclusion_reason(domain: str, metadata: Mapping[str, object], config: CampaignConfig) -> str:
    for config_key, reason in _EXCLUSION_KEYS:
        excluded_domains = {normalize_domain(value) for value in config.exclusions.get(config_key, ())}
        if domain in excluded_domains:
            return reason
    if metadata.get("is_b2b", metadata.get("b2b")) is False:
        return "non_b2b"
    return ""


def score_account(account: AccountRecord, config: CampaignConfig) -> AccountScore:
    """Score one account without discarding excluded accounts or their evidence."""
    metadata = _metadata(account)
    domain = normalize_domain(account.domain)
    exclusion_reason = _exclusion_reason(domain, metadata, config)
    component_values = {
        "icp_fit": metadata.get("icp_fit", metadata.get("is_b2b", metadata.get("b2b", False))),
        "engineering_led": metadata.get("engineering_led", False),
        "technical_gtm_signal": _has_technical_gtm_hiring(metadata, config),
        "growth_recency": _growth_signal(metadata),
        "customer_similarity": metadata.get("customer_similarity", False),
        "first_party_engagement": metadata.get("first_party_engagement", False),
    }
    components = {
        name: _component(value, _configured_weight(config, name))
        for name, value in component_values.items()
    }
    total_score = sum(components.values())
    if exclusion_reason:
        decision = "exclude"
    elif total_score >= config.segment_thresholds.get("include", 0):
        decision = "include"
    elif total_score >= config.segment_thresholds.get("review", 0):
        decision = "review"
    else:
        decision = "exclude"
        exclusion_reason = "below_review_threshold"
    return AccountScore(
        account_id=account.account_id,
        **components,
        decision=decision,
        exclusion_reason=exclusion_reason,
    )


def rank_accounts(accounts: Sequence[AccountRecord], config: CampaignConfig) -> list[AccountScore]:
    """Return every candidate in deterministic decision, score, and domain order."""
    scored = [(score_account(account, config), normalize_domain(account.domain)) for account in accounts]
    decision_order = {"include": 0, "review": 1, "exclude": 2}
    return [
        score
        for score, _domain in sorted(
            scored,
            key=lambda item: (
                decision_order[item[0].decision],
                -item[0].total_score,
                item[1],
            ),
        )
    ]
