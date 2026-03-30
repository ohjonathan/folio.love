"""Context document creation and management."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import FolioConfig
from .naming import derive_engagement_short, sanitize_token
from .tracking import registry
from .tracking.registry import RegistryEntry

logger = logging.getLogger(__name__)

_CONTEXT_FILENAME = "_context.md"

# Required body sections per spec §D7
_BODY_SECTIONS = [
    "Client Background",
    "Engagement Snapshot",
    "Objectives / SOW",
    "Timeline",
    "Team",
    "Stakeholders",
    "Starting Hypotheses",
    "Risks / Open Questions",
]


def build_context_id(*, client: str, engagement: str) -> str:
    """Build a deterministic context document ID.

    Pattern: <client-token>_<engagement-short>_context_<YYYYMMDD>_engagement
    """
    client_token = sanitize_token(client)
    eng_short = derive_engagement_short(engagement)
    engagement_token = sanitize_token(eng_short or engagement)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{client_token}_{engagement_token}_context_{date_str}_engagement"


def resolve_context_path(
    *,
    library_root: Path,
    client: str,
    engagement: str,
    target: Optional[Path] = None,
) -> Path:
    """Resolve the output path for a context document.

    Default: <library_root>/<client-token>/<engagement-short>/_context.md

    If --target is given:
    - ends in .md → write to that exact path
    - otherwise → treat as directory, write _context.md inside it
    """
    if target is not None:
        target = Path(target)
        if target.suffix.lower() == ".md":
            return target.resolve()
        return (target / _CONTEXT_FILENAME).resolve()

    client_token = sanitize_token(client)
    eng_short = derive_engagement_short(engagement)
    engagement_token = sanitize_token(eng_short or engagement)
    return (
        library_root / client_token / engagement_token / _CONTEXT_FILENAME
    ).resolve()


def create_context_document(
    config: FolioConfig,
    *,
    client: str,
    engagement: str,
    target: Optional[Path] = None,
) -> tuple[str, Path]:
    """Create an engagement context document and register it.

    Returns (context_id, output_path).
    Raises ValueError if path escapes library root.
    Raises FileExistsError if the context doc already exists.
    """
    library_root = config.library_root.resolve()
    output_path = resolve_context_path(
        library_root=library_root,
        client=client,
        engagement=engagement,
        target=target,
    )

    # Safety: reject paths that escape library root (default routing only)
    if target is None:
        try:
            output_path.relative_to(library_root)
        except ValueError:
            raise ValueError(
                f"Resolved context path escapes library root: {output_path}"
            )

    if output_path.exists():
        raise FileExistsError(f"Context document already exists: {output_path}")

    context_id = build_context_id(client=client, engagement=engagement)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"{client} {engagement} - Engagement Context"

    content = _render_template(
        context_id=context_id,
        title=title,
        client=client,
        engagement=engagement,
        today=today,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    # Register in registry.json
    md_rel = str(output_path.relative_to(library_root)).replace("\\", "/")
    deck_dir_rel = str(
        output_path.parent.relative_to(library_root)
    ).replace("\\", "/")
    if deck_dir_rel == ".":
        deck_dir_rel = ""

    entry = RegistryEntry(
        id=context_id,
        title=title,
        markdown_path=md_rel,
        deck_dir=deck_dir_rel,
        type="context",
        subtype="engagement",
        modified=today,
        client=client,
        engagement=engagement,
        authority="aligned",
        curation_level="L1",
        staleness_status="current",
        review_status="clean",
        review_flags=[],
        extraction_confidence=None,
    )

    registry_path = library_root / "registry.json"
    registry.upsert_entry(registry_path, entry)

    return context_id, output_path


def _render_template(
    *,
    context_id: str,
    title: str,
    client: str,
    engagement: str,
    today: str,
) -> str:
    """Render the full context document template."""
    return f"""---
id: {context_id}
title: "{title}"
type: context
subtype: engagement
status: active
authority: aligned
curation_level: L1
review_status: clean
review_flags: []
extraction_confidence: null
client: {client}
engagement: {engagement}
industry: []
service_line: ""
tags:
  - engagement-context
created: {today}
modified: {today}
---

# {title}

## Client Background

TBD.

## Engagement Snapshot

- Engagement name: {engagement}
- Engagement type: TBD
- Current phase: TBD

## Objectives / SOW

- TBD

## Timeline

- Kickoff: TBD
- Key milestones: TBD
- Decision date: TBD

## Team

- Engagement lead: [[TBD]]
- Team members:
  - [[TBD]]

## Stakeholders

- Client sponsor: [[TBD]]
- Key stakeholders:
  - [[TBD]]

## Starting Hypotheses

- TBD

## Risks / Open Questions

- TBD
"""
