"""Interaction ingestion orchestration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from .config import FolioConfig
from .converter import _read_existing_frontmatter
from .llm.runtime import EndpointNotAllowedError
from .naming import (
    build_interaction_artifact_name,
    build_interaction_id,
    derive_engagement_short,
    humanize_token,
    sanitize_token,
)
from .output.frontmatter import generate_interaction
from .output.interaction_markdown import assemble_interaction
from .pipeline.interaction_analysis import (
    InteractionAnalysisResult,
    analyze_interaction_text,
    normalize_source_text,
)
from .tracking import registry, sources, versions
from .tracking.registry import RegistryEntry

_SUPPORTED_EXTENSIONS = {".md", ".txt"}
_TARGET_REINGEST_ERROR = "Use --target <existing-note.md> to disambiguate."
_TITLE_H1_RE = re.compile(r"(?m)^#\s+(.+?)\s*$")


@dataclass
class IngestResult:
    """Result payload for a completed ingest run."""

    interaction_id: str
    output_path: Path
    version: int
    review_status: str
    llm_status: str

    @property
    def degraded(self) -> bool:
        return self.llm_status != "executed"


@dataclass
class _ResolvedIdentity:
    markdown_path: Optional[Path]
    existing_frontmatter: Optional[dict]
    target_dir_override: Optional[Path]
    matched_entry: Optional[RegistryEntry]


class IngestError(RuntimeError):
    """Base ingest failure."""


class IngestAmbiguityError(IngestError):
    """Raised when re-ingest identity is ambiguous."""


class IngestSubtypeMismatchError(IngestError):
    """Raised when an existing interaction matches but subtype differs."""


def ingest_source(
    config: FolioConfig,
    *,
    source_path: Path,
    subtype: str,
    event_date: date,
    client: Optional[str] = None,
    engagement: Optional[str] = None,
    participants: Optional[list[str]] = None,
    duration_minutes: Optional[int] = None,
    source_recording: Optional[Path] = None,
    title: Optional[str] = None,
    target: Optional[Path] = None,
    llm_profile: Optional[str] = None,
    note: Optional[str] = None,
) -> IngestResult:
    """Convert a transcript or notes file into an interaction note."""

    source_path = Path(source_path).resolve()
    if event_date > date.today():
        raise IngestError(f"Event date cannot be in the future: {event_date.isoformat()}")
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    if source_path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        raise IngestError(
            f"Unsupported source extension '{source_path.suffix}'. v0.5.0 supports .txt and .md only."
        )
    if duration_minutes is not None and duration_minutes <= 0:
        raise IngestError("--duration-minutes must be a positive integer")
    if source_recording is not None:
        source_recording = Path(source_recording).resolve()
        if not source_recording.exists():
            raise FileNotFoundError(f"Source recording not found: {source_recording}")

    explicit_target_md, target_dir_override = _resolve_target(target)
    library_root = config.library_root.resolve()
    registry_data = _load_registry_data(library_root)

    raw_source_text = source_path.read_text()
    normalized_source_body = normalize_source_text(
        raw_source_text,
        strip_markdown_frontmatter=source_path.suffix.lower() == ".md",
    )
    source_hash = sources.compute_file_hash(source_path)

    identity = _resolve_existing_identity(
        library_root=library_root,
        registry_data=registry_data,
        source_path=source_path,
        source_hash=source_hash,
        subtype=subtype,
        explicit_target_md=explicit_target_md,
        target_dir_override=target_dir_override,
    )

    resolved_title = _resolve_title(
        explicit_title=title,
        normalized_source_body=normalized_source_body,
        source_stem=source_path.stem,
    )

    interaction_id, output_dir, markdown_path = _resolve_output_identity(
        library_root=library_root,
        registry_data=registry_data,
        source_path=source_path,
        source_hash=source_hash,
        subtype=subtype,
        event_date=event_date,
        client=client,
        engagement=engagement,
        title=resolved_title,
        identity=identity,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    source_info = sources.compute_source_info(source_path, markdown_path)
    source_recording_relative = None
    if source_recording is not None:
        source_recording_relative = sources.compute_source_info(
            source_recording,
            markdown_path,
        ).relative_path

    profile = config.llm.resolve_profile(llm_profile, task="ingest")
    fallback_profiles = config.llm.get_fallbacks(override=llm_profile, task="ingest")
    fallback_specs = [
        (fb.provider, fb.model, fb.api_key_env, fb.base_url_env)
        for fb in fallback_profiles
    ]

    try:
        analysis_result = analyze_interaction_text(
            normalized_source_body,
            subtype,
            provider_name=profile.provider,
            model=profile.model,
            api_key_env=profile.api_key_env,
            base_url_env=profile.base_url_env,
            fallback_profiles=fallback_specs,
            all_provider_settings=config.providers,
        )
    except EndpointNotAllowedError as exc:
        analysis_result = _degraded_analysis_result(
            f"LLM analysis did not run: {exc}",
        )

    version_info = versions.compute_version(
        deck_dir=output_dir,
        source_hash=source_info.file_hash,
        source_path=source_info.relative_path,
        slide_count=1,
        new_texts={1: normalized_source_body},
        note=note,
    )

    llm_metadata = {
        "ingest": {
            "requested_profile": llm_profile or profile.name,
            "profile": profile.name,
            "provider": profile.provider,
            "model": profile.model,
            "extraction_method": "source_text",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fallback_used": False,
            "status": analysis_result.llm_status,
            "pass_strategy": analysis_result.pass_strategy,
        }
    }

    frontmatter = generate_interaction(
        interaction_id=interaction_id,
        title=resolved_title,
        subtype=subtype,
        event_date=event_date.isoformat(),
        version_info=version_info,
        source_transcript=source_info.relative_path,
        source_hash=source_info.file_hash,
        analysis_result=analysis_result,
        client=client,
        engagement=engagement,
        participants=participants,
        duration_minutes=duration_minutes,
        source_recording=source_recording_relative,
        existing_frontmatter=identity.existing_frontmatter,
        llm_metadata=llm_metadata,
    )

    markdown = assemble_interaction(
        title=resolved_title,
        frontmatter=frontmatter,
        source_display_path=source_info.relative_path,
        version_info=version_info,
        analysis_result=analysis_result,
        raw_transcript=normalized_source_body,
    )
    _atomic_write_text(markdown_path, markdown)

    if _is_within(markdown_path, library_root):
        registry_path = library_root / "registry.json"
        registry.upsert_entry(
            registry_path,
            RegistryEntry(
                id=interaction_id,
                title=resolved_title,
                markdown_path=_relative_to_root(markdown_path, library_root),
                deck_dir=_relative_to_root(output_dir, library_root),
                source_relative_path=source_info.relative_path,
                source_hash=source_info.file_hash,
                source_type=None,
                type="interaction",
                version=version_info.version,
                converted=version_info.timestamp,
                modified=version_info.timestamp,
                client=client,
                engagement=engagement,
                authority=identity.existing_frontmatter.get("authority") if identity.existing_frontmatter else "captured",
                curation_level=identity.existing_frontmatter.get("curation_level") if identity.existing_frontmatter else "L0",
                staleness_status="current",
                review_status=analysis_result.review_status,
                review_flags=list(analysis_result.review_flags),
                extraction_confidence=analysis_result.extraction_confidence,
                grounding_summary=analysis_result.grounding_summary,
            ),
        )

    return IngestResult(
        interaction_id=interaction_id,
        output_path=markdown_path,
        version=version_info.version,
        review_status=analysis_result.review_status,
        llm_status=analysis_result.llm_status,
    )


def _resolve_target(target: Optional[Path]) -> tuple[Optional[Path], Optional[Path]]:
    if target is None:
        return None, None

    target = Path(target)
    if target.exists():
        target = target.resolve()
        if target.is_file():
            if target.suffix.lower() != ".md":
                raise IngestError(f"Target file must be a markdown note: {target}")
            return target, None
        return None, target

    if target.suffix.lower() == ".md":
        raise IngestError(f"Target markdown note does not exist: {target}")

    return None, target.resolve()


def _load_registry_data(library_root: Path) -> dict:
    registry_path = library_root / "registry.json"
    if registry_path.exists():
        data = registry.load_registry(registry_path)
        if data.get("_corrupt"):
            data = registry.rebuild_registry(library_root)
            registry.save_registry(registry_path, data)
        return data
    if library_root.exists():
        data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, data)
        return data
    return {"_schema_version": 1, "decks": {}}


def _resolve_existing_identity(
    *,
    library_root: Path,
    registry_data: dict,
    source_path: Path,
    source_hash: str,
    subtype: str,
    explicit_target_md: Optional[Path],
    target_dir_override: Optional[Path],
) -> _ResolvedIdentity:
    if explicit_target_md is not None:
        existing_fm = _read_existing_frontmatter(explicit_target_md)
        if not existing_fm or existing_fm.get("type") != "interaction":
            raise IngestError(f"Target note is not an interaction note: {explicit_target_md}")
        return _ResolvedIdentity(
            markdown_path=explicit_target_md,
            existing_frontmatter=existing_fm,
            target_dir_override=None,
            matched_entry=None,
        )

    entries = [
        registry.entry_from_dict(item)
        for item in registry_data.get("decks", {}).values()
        if item.get("type") == "interaction"
    ]

    path_matches = [
        entry for entry in entries
        if _entry_source_matches_path(library_root, entry, source_path)
    ]
    if len(path_matches) > 1:
        raise IngestAmbiguityError(
            f"Multiple interactions reference {source_path}. {_TARGET_REINGEST_ERROR}"
        )
    if len(path_matches) == 1:
        return _resolved_match(path_matches[0], library_root, subtype, target_dir_override)

    hash_matches = [entry for entry in entries if entry.source_hash == source_hash]
    if len(hash_matches) > 1:
        raise IngestAmbiguityError(
            f"Multiple interactions match source hash {source_hash}. {_TARGET_REINGEST_ERROR}"
        )
    if len(hash_matches) == 1:
        return _resolved_match(hash_matches[0], library_root, subtype, target_dir_override)

    return _ResolvedIdentity(
        markdown_path=None,
        existing_frontmatter=None,
        target_dir_override=target_dir_override,
        matched_entry=None,
    )


def _resolved_match(
    entry: RegistryEntry,
    library_root: Path,
    subtype: str,
    target_dir_override: Optional[Path],
) -> _ResolvedIdentity:
    markdown_path = (library_root / entry.markdown_path).resolve()
    existing_fm = _read_existing_frontmatter(markdown_path)
    existing_subtype = existing_fm.get("subtype") if existing_fm else None
    if existing_subtype and existing_subtype != subtype:
        raise IngestSubtypeMismatchError(
            f"Existing interaction {entry.id} has subtype '{existing_subtype}', not '{subtype}'."
        )
    return _ResolvedIdentity(
        markdown_path=markdown_path,
        existing_frontmatter=existing_fm,
        target_dir_override=target_dir_override,
        matched_entry=entry,
    )


def _resolve_output_identity(
    *,
    library_root: Path,
    registry_data: dict,
    source_path: Path,
    source_hash: str,
    subtype: str,
    event_date: date,
    client: Optional[str],
    engagement: Optional[str],
    title: str,
    identity: _ResolvedIdentity,
) -> tuple[str, Path, Path]:
    artifact_name = build_interaction_artifact_name(
        event_date=event_date,
        source_stem=source_path.stem,
        source_hash=source_hash,
    )

    if identity.markdown_path is not None:
        existing_fm = identity.existing_frontmatter or {}
        interaction_id = existing_fm.get("id") or build_interaction_id(
            subtype=subtype,
            event_date=event_date,
            descriptor=title,
            client=client,
            engagement=engagement,
        )
        markdown_path = identity.markdown_path
        return interaction_id, markdown_path.parent, markdown_path

    if identity.target_dir_override is not None:
        output_dir = identity.target_dir_override
    else:
        output_dir = _default_output_dir(
            library_root=library_root,
            artifact_name=artifact_name,
            client=client,
            engagement=engagement,
        )

    markdown_path = output_dir / f"{artifact_name}.md"
    if identity.target_dir_override is None and output_dir.exists() and any(output_dir.iterdir()):
        raise IngestError(
            f"Output directory already exists for a different interaction: {output_dir}"
        )
    if markdown_path.exists():
        raise IngestError(
            f"Target markdown already exists. Use --target <existing-note.md> to re-ingest it: {markdown_path}"
        )

    interaction_id = _resolve_unique_interaction_id(
        registry_data=registry_data,
        subtype=subtype,
        event_date=event_date,
        title=title,
        client=client,
        engagement=engagement,
        source_hash=source_hash,
    )
    return interaction_id, output_dir, markdown_path


def _resolve_unique_interaction_id(
    *,
    registry_data: dict,
    subtype: str,
    event_date: date,
    title: str,
    client: Optional[str],
    engagement: Optional[str],
    source_hash: str,
) -> str:
    descriptor = sanitize_token(title)
    candidate = build_interaction_id(
        subtype=subtype,
        event_date=event_date,
        descriptor=descriptor,
        client=client,
        engagement=engagement,
    )
    if candidate not in registry_data.get("decks", {}):
        return candidate
    return build_interaction_id(
        subtype=subtype,
        event_date=event_date,
        descriptor=descriptor,
        client=client,
        engagement=engagement,
        hash_suffix=source_hash[:8],
    )


def _default_output_dir(
    *,
    library_root: Path,
    artifact_name: str,
    client: Optional[str],
    engagement: Optional[str],
) -> Path:
    engagement_short = derive_engagement_short(engagement) if engagement else ""
    if client and engagement:
        return (
            library_root
            / sanitize_token(client)
            / sanitize_token(engagement_short or engagement)
            / "interactions"
            / artifact_name
        )
    if client:
        return library_root / sanitize_token(client) / "interactions" / artifact_name
    return library_root / "interactions" / artifact_name


def _entry_source_matches_path(library_root: Path, entry: RegistryEntry, source_path: Path) -> bool:
    try:
        return registry.resolve_entry_source(library_root, entry) == source_path.resolve()
    except Exception:
        return False


def _resolve_title(
    *,
    explicit_title: Optional[str],
    normalized_source_body: str,
    source_stem: str,
) -> str:
    if explicit_title and explicit_title.strip():
        return explicit_title.strip()

    match = _TITLE_H1_RE.search(normalized_source_body)
    if match:
        return match.group(1).strip()

    return humanize_token(source_stem) or source_stem


def _degraded_analysis_result(message: str) -> InteractionAnalysisResult:
    return InteractionAnalysisResult(
        warnings=[message],
        review_status="flagged",
        review_flags=["analysis_unavailable"],
        extraction_confidence=None,
        grounding_summary={
            "total_claims": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "validated": 0,
            "unvalidated": 0,
        },
        pass_strategy="single_pass",
        llm_status="pending",
    )


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content)
    tmp_path.replace(path)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _relative_to_root(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
