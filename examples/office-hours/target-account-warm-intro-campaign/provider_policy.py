"""Explicit provider routing, spend guards, and PDL gap-fill exclusions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence

from schemas import ContactRecord, normalize_email, normalize_linkedin_url, normalized_identity


def _decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise TypeError("money values must be Decimal, strings, or integers; never float")
    if isinstance(value, (str, int)):
        return Decimal(str(value))
    raise TypeError("money values must be Decimal, strings, or integers")


@dataclass(frozen=True)
class AuthorizationDecision:
    provider: str
    operation: str
    cache_key: str
    estimated_cost_usd: Decimal
    allowed: bool
    reason: str
    authorization_id: str = ""


@dataclass(frozen=True)
class PdlExclusionSet:
    linkedin_urls: tuple[str, ...]
    emails: tuple[str, ...]
    identities: tuple[str, ...]


class ProviderPolicy:
    """A small in-memory ledger that refuses un-routable paid work by policy."""

    def __init__(
        self,
        *,
        provider_routes: Mapping[str, str],
        blocked_providers: Sequence[str],
        blocked_operations: Sequence[str],
        provider_caps: Mapping[str, Decimal | int | str],
        campaign_cap: Decimal | int | str,
    ) -> None:
        self.provider_routes = {name.casefold(): provider.casefold() for name, provider in provider_routes.items()}
        self.blocked_providers = tuple(sorted({provider.casefold() for provider in blocked_providers}))
        self.blocked_operations = tuple(sorted({operation.casefold() for operation in blocked_operations}))
        self.provider_caps = {provider.casefold(): _decimal(cap) for provider, cap in provider_caps.items()}
        self.campaign_cap = _decimal(campaign_cap)
        self._cache_keys: set[str] = set()
        self._provider_spend: dict[str, Decimal] = {}
        self._campaign_spend = Decimal("0")
        self._reservations: dict[str, AuthorizationDecision] = {}
        self._reserved_provider_spend: dict[str, Decimal] = {}
        self._reserved_campaign_spend = Decimal("0")

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> "ProviderPolicy":
        """Build policy from the JSON configuration without accepting float money."""
        policy_config = config.get("provider_policy", config)
        if not isinstance(policy_config, Mapping):
            raise TypeError("provider_policy must be a mapping")
        return cls(
            provider_routes=dict(policy_config.get("provider_routes", {})),
            blocked_providers=tuple(policy_config.get("blocked_providers", ())),
            blocked_operations=tuple(policy_config.get("blocked_operations", ())),
            provider_caps=dict(policy_config.get("provider_caps", {})),
            campaign_cap=policy_config.get("campaign_cap", "0"),
        )

    @classmethod
    def from_path(cls, path: Path) -> "ProviderPolicy":
        """Load a provider policy from the local campaign JSON configuration."""
        with Path(path).open("r", encoding="utf-8") as source:
            config = json.load(source)
        if not isinstance(config, dict):
            raise ValueError("provider configuration must contain a JSON object")
        return cls.from_config(config)

    @property
    def campaign_spend_usd(self) -> Decimal:
        return self._campaign_spend

    def provider_for(self, operation: str) -> str:
        return self.provider_routes[operation.casefold()]

    def is_blocked(self, provider: str, operation: str) -> bool:
        provider = provider.casefold()
        operation = operation.casefold()
        return provider in self.blocked_providers or (
            operation in self.blocked_operations
            or f"{provider}:{operation}" in self.blocked_operations
            or f"{provider}:*" in self.blocked_operations
        )

    def authorize(
        self,
        provider: str,
        operation: str,
        cache_key: str,
        estimated_cost_usd: Decimal,
        *,
        authorization_id: str | None = None,
        pdl_exclusions: PdlExclusionSet | None = None,
        known_contact_count: int = 0,
    ) -> AuthorizationDecision:
        """Allow a paid call only when it is permitted, uncached, and affordable."""
        normalized_provider = provider.casefold()
        normalized_operation = operation.casefold()
        if isinstance(known_contact_count, bool) or not isinstance(known_contact_count, int):
            raise TypeError("known_contact_count must be an integer")
        if known_contact_count < 0:
            raise ValueError("known_contact_count cannot be negative")
        estimated_cost = _decimal(estimated_cost_usd)
        if estimated_cost < 0:
            raise ValueError("estimated_cost_usd cannot be negative")
        reservation_id = authorization_id or cache_key
        reason = "allowed"
        if normalized_provider in self.blocked_providers:
            reason = "blocked_provider"
        elif self.is_blocked(normalized_provider, normalized_operation):
            reason = "blocked_operation"
        elif self.provider_routes.get(normalized_operation) != normalized_provider:
            reason = "wrong_provider"
        elif (
            normalized_provider == "pdl"
            and normalized_operation == "people_search"
            and known_contact_count > 0
            and (pdl_exclusions is None or not any((pdl_exclusions.linkedin_urls, pdl_exclusions.emails, pdl_exclusions.identities)))
        ):
            reason = "missing_exclusions"
        elif (
            cache_key in self._cache_keys
            or reservation_id in self._reservations
            or any(reservation.cache_key == cache_key for reservation in self._reservations.values())
        ):
            reason = "cache_hit"
        elif (
            self._provider_spend.get(normalized_provider, Decimal("0"))
            + self._reserved_provider_spend.get(normalized_provider, Decimal("0"))
            + estimated_cost
            > self.provider_caps.get(normalized_provider, Decimal("Infinity"))
        ):
            reason = "provider_cap"
        elif self._campaign_spend + self._reserved_campaign_spend + estimated_cost > self.campaign_cap:
            reason = "campaign_cap"
        decision = AuthorizationDecision(
            provider=normalized_provider,
            operation=normalized_operation,
            cache_key=cache_key,
            estimated_cost_usd=estimated_cost,
            allowed=reason == "allowed",
            reason=reason,
            authorization_id=reservation_id,
        )
        if decision.allowed:
            self._reservations[reservation_id] = decision
            self._reserved_provider_spend[normalized_provider] = self._reserved_provider_spend.get(
                normalized_provider, Decimal("0")
            ) + estimated_cost
            self._reserved_campaign_spend += estimated_cost
        return decision

    def record_call(self, decision: AuthorizationDecision, actual_cost_usd: Decimal) -> None:
        """Append an authorized cache miss to the in-memory cost ledger."""
        if not decision.allowed:
            raise ValueError("cannot record a denied provider call")
        reservation = self._reservations.get(decision.authorization_id)
        if reservation is None or reservation != decision:
            raise ValueError("authorization has no active reservation")
        actual_cost = _decimal(actual_cost_usd)
        if actual_cost < 0:
            raise ValueError("actual_cost_usd cannot be negative")
        provider_total = (
            self._provider_spend.get(decision.provider, Decimal("0"))
            + self._reserved_provider_spend.get(decision.provider, Decimal("0"))
            - reservation.estimated_cost_usd
            + actual_cost
        )
        if provider_total > self.provider_caps.get(decision.provider, Decimal("Infinity")):
            raise ValueError("actual cost exceeds provider cap")
        campaign_total = (
            self._campaign_spend
            + self._reserved_campaign_spend
            - reservation.estimated_cost_usd
            + actual_cost
        )
        if campaign_total > self.campaign_cap:
            raise ValueError("actual cost exceeds campaign cap")
        del self._reservations[decision.authorization_id]
        self._reserved_provider_spend[decision.provider] -= reservation.estimated_cost_usd
        self._reserved_campaign_spend -= reservation.estimated_cost_usd
        self._cache_keys.add(decision.cache_key)
        self._provider_spend[decision.provider] = self._provider_spend.get(
            decision.provider, Decimal("0")
        ) + actual_cost
        self._campaign_spend += actual_cost


def build_pdl_exclusions(contacts: Sequence[ContactRecord]) -> PdlExclusionSet:
    """Return the complete stable identifiers that must not be re-searched in PDL."""
    linkedin_urls: set[str] = set()
    emails: set[str] = set()
    identities: set[str] = set()
    for contact in contacts:
        if contact.linkedin_url:
            linkedin_urls.add(normalize_linkedin_url(contact.linkedin_url))
        if contact.work_email:
            emails.add(normalize_email(contact.work_email))
        if contact.name.strip() and contact.company.strip() and contact.title.strip():
            identities.add(normalized_identity(contact.name, contact.company, contact.title))
    return PdlExclusionSet(
        linkedin_urls=tuple(sorted(linkedin_urls)),
        emails=tuple(sorted(emails)),
        identities=tuple(sorted(identities)),
    )
