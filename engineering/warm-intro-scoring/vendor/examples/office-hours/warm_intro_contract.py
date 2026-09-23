"""Shared stable identities for warm-path scoring, drafting, and activation."""

from __future__ import annotations

import hashlib
import json


PATH_ID_VERSION = "warm-path-v1"
ACTIVATION_ID_VERSION = "warm-activation-v1"


def _required_parts(**parts: str) -> tuple[str, ...]:
    normalized: list[str] = []
    for name, value in parts.items():
        candidate = str(value or "").strip()
        if not candidate:
            raise ValueError(f"{name} is required for stable warm-intro identity")
        normalized.append(candidate)
    return tuple(normalized)


def _digest(version: str, parts: tuple[str, ...]) -> str:
    payload = json.dumps(
        [version, *parts],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_path_id(
    campaign_id: str,
    owner_id: str,
    connector_id: str,
    target_id: str,
) -> str:
    """Build one campaign- and owner-namespaced connector-to-target path ID."""
    parts = _required_parts(
        campaign_id=campaign_id,
        owner_id=owner_id,
        connector_id=connector_id,
        target_id=target_id,
    )
    return f"path-{_digest(PATH_ID_VERSION, parts)[:16]}"


def build_activation_idempotency_key(
    campaign_id: str,
    owner_id: str,
    path_id: str,
    channel: str,
    message_version: str,
) -> str:
    """Build the durable identity for one namespaced outbound message version."""
    parts = _required_parts(
        campaign_id=campaign_id,
        owner_id=owner_id,
        path_id=path_id,
        channel=channel,
        message_version=message_version,
    )
    return _digest(ACTIVATION_ID_VERSION, parts)
