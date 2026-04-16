"""Managed analysis document initialization and graph input tracking."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import FolioConfig
from .naming import derive_engagement_short, sanitize_token
from .tracking import registry
from .tracking.registry import RegistryEntry

ANALYSIS_SUBTYPES = (
    "hypothesis",
    "issue_tree",
    "synthesis",
    "framework_application",
    "digest",
)

_BODY_SECTIONS = [
    "Summary",
    "Key Claims",
    "Open Questions",
    "Related",
]


def build_analysis_id(*, client: str, engagement: str, subtype: str, title: str) -> str:
    client_token = sanitize_token(client)
    engagement_token = sanitize_token(derive_engagement_short(engagement) or engagement)
    title_token = sanitize_token(title)[:48].strip("_") or subtype
    date_str = datetime.now().strftime("%Y%m%d")
    return f"{client_token}_{engagement_token}_analysis_{date_str}_{title_token}"


def resolve_analysis_path(
    *,
    library_root: Path,
    client: str,
    engagement: str,
    subtype: str,
    analysis_id: str,
    target: Optional[Path] = None,
) -> Path:
    if target is not None:
        target = Path(target)
        if target.suffix.lower() == ".md":
            return target.resolve()
        return (target / f"{analysis_id}.md").resolve()

    client_token = sanitize_token(client)
    engagement_token = sanitize_token(derive_engagement_short(engagement) or engagement)
    return (
        library_root
        / client_token
        / engagement_token
        / "analysis"
        / subtype
        / f"{analysis_id}.md"
    ).resolve()


def registry_entry_input_identifier(entry: RegistryEntry) -> tuple[str, str]:
    if entry.source_relative_path is not None:
        return (entry.source_hash or "", str(entry.version or 0))
    sourceless_marker = entry.modified or entry.markdown_path or entry.id
    return (f"sourceless:{sourceless_marker}", str(entry.version or 0))


def compute_graph_input_fingerprint(entries: list[RegistryEntry]) -> str:
    payload = [
        [entry.id, *registry_entry_input_identifier(entry)]
        for entry in sorted(entries, key=lambda item: item.id)
    ]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def resolve_input_entries(registry_data: dict, target_ids: list[str]) -> list[RegistryEntry]:
    missing = [target_id for target_id in target_ids if target_id not in registry_data.get("decks", {})]
    if missing:
        raise ValueError(f"Unknown input document(s): {', '.join(sorted(missing))}")
    return [
        registry.entry_from_dict(registry_data["decks"][target_id])
        for target_id in sorted(dict.fromkeys(target_ids))
    ]


def create_analysis_document(
    config: FolioConfig,
    *,
    subtype: str,
    title: str,
    client: str,
    engagement: str,
    draws_from: Optional[list[str]] = None,
    depends_on: Optional[list[str]] = None,
    target: Optional[Path] = None,
) -> tuple[str, Path]:
    if subtype not in ANALYSIS_SUBTYPES:
        raise ValueError(f"Invalid analysis subtype '{subtype}'")

    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    registry_data = registry.load_registry(registry_path)
    if registry_data.get("_corrupt"):
        registry_data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, registry_data)

    draws_from = sorted(dict.fromkeys(draws_from or []))
    depends_on = sorted(dict.fromkeys(depends_on or []))
    input_ids = sorted(dict.fromkeys([*draws_from, *depends_on]))
    input_entries = resolve_input_entries(registry_data, input_ids) if input_ids else []

    analysis_id = build_analysis_id(
        client=client,
        engagement=engagement,
        subtype=subtype,
        title=title,
    )
    output_path = resolve_analysis_path(
        library_root=library_root,
        client=client,
        engagement=engagement,
        subtype=subtype,
        analysis_id=analysis_id,
        target=target,
    )

    try:
        output_path.relative_to(library_root)
    except ValueError as exc:
        raise ValueError(f"Resolved analysis path escapes library root: {output_path}") from exc

    if output_path.exists():
        raise FileExistsError(f"Analysis document already exists: {output_path}")

    today = datetime.now().strftime("%Y-%m-%d")
    frontmatter: dict[str, object] = {
        "id": analysis_id,
        "title": title,
        "type": "analysis",
        "subtype": subtype,
        "status": "active",
        "authority": "analyzed",
        "curation_level": "L1",
        "review_status": "flagged",
        "review_flags": ["synthesis_requires_review"],
        "extraction_confidence": None,
        "client": client,
        "engagement": engagement,
        "tags": [subtype.replace("_", "-"), "analysis"],
        "created": today,
        "modified": today,
    }
    if draws_from:
        frontmatter["draws_from"] = draws_from
    if depends_on:
        frontmatter["depends_on"] = depends_on
    if input_entries:
        frontmatter["_llm_metadata"] = {
            "graph": {
                "input_fingerprint": compute_graph_input_fingerprint(input_entries),
            }
        }

    body = _render_body(title)
    content = _render_frontmatter(frontmatter) + "\n\n" + body + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    md_rel = str(output_path.relative_to(library_root)).replace("\\", "/")
    deck_dir_rel = str(output_path.parent.relative_to(library_root)).replace("\\", "/")
    if deck_dir_rel == ".":
        deck_dir_rel = ""

    entry = RegistryEntry(
        id=analysis_id,
        title=title,
        markdown_path=md_rel,
        deck_dir=deck_dir_rel,
        type="analysis",
        subtype=subtype,
        modified=today,
        client=client,
        engagement=engagement,
        authority="analyzed",
        curation_level="L1",
        staleness_status="current",
        review_status="flagged",
        review_flags=["synthesis_requires_review"],
        extraction_confidence=None,
    )
    registry.upsert_entry(registry_path, entry)
    return analysis_id, output_path


def _render_frontmatter(frontmatter: dict) -> str:
    import yaml

    yaml_str = yaml.dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return f"---\n{yaml_str}---"


def _render_body(title: str) -> str:
    parts = [f"# {title}", ""]
    for section in _BODY_SECTIONS:
        if section == "Related":
            parts.extend([f"## {section}", "", "<!-- manually curated from canonical relationship fields -->", ""])
        else:
            parts.extend([f"## {section}", "", "TBD.", ""])
    return "\n".join(parts).rstrip()
