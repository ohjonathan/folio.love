"""Shared naming helpers for Folio IDs and path-safe tokens."""

from __future__ import annotations

import re
from datetime import date


_INTERACTION_TYPE_SHORT = {
    "client_meeting": "meeting",
    "expert_interview": "interview",
    "internal_sync": "sync",
    "partner_check_in": "checkin",
    "workshop": "workshop",
}


def sanitize_token(value: str) -> str:
    """Return a path-safe, ID-safe token."""
    token = re.sub(r"[^\w\-.]", "_", value or "")
    token = re.sub(r"_+", "_", token)
    return token.strip("_").lower()


def humanize_token(value: str) -> str:
    """Return a human-readable title from a sanitized token."""
    return (value or "").replace("_", " ").replace("-", " ").title()


def derive_engagement_short(value: str) -> str:
    """Derive a deterministic short engagement token.

    Examples:
    - ``DD Q1 2026`` -> ``ddq126``
    - ``Ops Sprint 2026`` -> ``opssprint2026``
    """
    tokens = re.findall(r"[a-z0-9]+", (value or "").lower())
    if not tokens:
        return ""

    if (
        len(tokens) >= 3
        and tokens[0].isalpha()
        and re.fullmatch(r"q[1-4]", tokens[1])
        and re.fullmatch(r"\d{4}", tokens[2])
    ):
        return f"{tokens[0]}{tokens[1]}{tokens[2][-2:]}"

    if len(tokens) >= 2 and tokens[0].isalpha() and re.fullmatch(r"\d{4}", tokens[1]):
        return f"{tokens[0]}{tokens[1][-2:]}"

    compact = "".join(tokens)
    return compact or sanitize_token(value)


def build_interaction_id(
    *,
    subtype: str,
    event_date: str | date,
    descriptor: str,
    client: str | None = None,
    engagement: str | None = None,
    hash_suffix: str | None = None,
) -> str:
    """Build an interaction note ID following the Tier 3 convention."""
    type_short = _INTERACTION_TYPE_SHORT[subtype]
    if isinstance(event_date, date):
        date_str = event_date.strftime("%Y%m%d")
    else:
        date_str = str(event_date).replace("-", "")

    parts: list[str] = []
    if client:
        parts.append(sanitize_token(client))
    if engagement:
        engagement_short = derive_engagement_short(engagement)
        if engagement_short:
            parts.append(engagement_short)
    parts.extend([type_short, date_str, sanitize_token(descriptor)])
    if hash_suffix:
        parts.append(sanitize_token(hash_suffix))
    return "_".join(part for part in parts if part)


def build_interaction_artifact_name(
    *,
    event_date: str | date,
    source_stem: str,
    source_hash: str,
) -> str:
    """Build the default interaction artifact folder/name."""
    if isinstance(event_date, date):
        date_str = event_date.isoformat()
    else:
        date_str = str(event_date)
    return f"{date_str}_{sanitize_token(source_stem)}_{source_hash[:8]}"
