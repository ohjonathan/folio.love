"""Core enrichment pipeline for folio enrich.

Implements the enrich planning and execution pipeline per the folio enrich
spec. Processes registry-managed evidence and interaction notes to add
tags, entity wikilinks, and relationship proposals.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shlex
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Optional

import yaml

from .config import FolioConfig, LLMProfile
from .lock import library_lock
from .llm.types import FallbackProfileSpec, ProviderRuntimeSettings
from .pipeline.enrich_data import (
    ENRICH_SPEC_VERSION,
    RELATIONSHIP_FIELDS,
    EnrichOutcome,
    EnrichAxisResult,
    EnrichResult,
    RelationshipProposal,
    _STATUS_TO_LIFECYCLE,
    compute_relationship_proposal_id,
    compute_input_fingerprint,
    compute_entity_resolution_fingerprint,
    compute_relationship_context_fingerprint,
    compute_managed_body_fingerprint,
)
from .pipeline.enrich_analysis import (
    analyze_note_for_enrichment,
    evaluate_relationships,
)
from .pipeline.entity_resolution import resolve_entities, commit_deferred_entities
from .pipeline.section_parser import MarkdownDocument
from .tracking import registry as registry_mod
from .tracking.entities import sanitize_wikilink_name

logger = logging.getLogger(__name__)

# Per tier4_discovery_proposal_layer_spec.md section 9.1
QUEUE_CAP: int = 20

# Ownership marker for generated ## Related sections (B6)
_RELATED_MARKER = "<!-- enrich:generated -->"

# Plural category keys from resolution_result.entities → singular registry types
_PLURAL_TO_SINGULAR = {
    "people": "person",
    "departments": "department",
    "systems": "system",
    "processes": "process",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches_scope(path: str, scope: str) -> bool:
    """Scope matching — duplicated from cli.py to avoid import cycle."""
    norm_scope = scope.rstrip("/") + "/"
    return path == scope or path.startswith(norm_scope)


def _read_frontmatter(path: Path) -> dict | None:
    """Read frontmatter from a markdown file."""
    from .output.diagram_notes import _parse_frontmatter_from_content
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
        return _parse_frontmatter_from_content(content)
    except Exception:
        return None


def _atomic_write_text(path: Path, content: str) -> None:
    """Atomic file write via tmp-then-replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def _sha256_content(content: str) -> str:
    """Return sha256 hex digest of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _strip_managed_content(content: str, doc: MarkdownDocument, doc_type: str) -> str:
    """Strip frontmatter and enrich-managed sections from content for fingerprinting.

    Removes frontmatter so that metadata updates (tags, timestamps) don't
    change the fingerprint (B2 fix). Also removes managed sections so that
    enrich output doesn't self-invalidate.
    """
    # Strip frontmatter first (B2 fix)
    result = content
    if result.startswith("---"):
        # Find end of frontmatter
        fm_end = result.find("\n---", 3)
        if fm_end != -1:
            # Skip past the closing --- and its newline
            body_start = fm_end + 4
            if body_start < len(result) and result[body_start] == '\n':
                body_start += 1
            result = result[body_start:]

    # Remove managed sections from the body (process in reverse order
    # by start position to avoid offset drift)
    body_doc = MarkdownDocument(result)
    managed = body_doc.get_managed_sections(doc_type)
    sections_by_pos = sorted(managed.values(), key=lambda s: s.start, reverse=True)
    for section in sections_by_pos:
        result = result[:section.start] + result[section.end:]
    return result


def _get_canonical_targets(fm: dict) -> list[str]:
    """Extract all canonical relationship target IDs from frontmatter."""
    targets = []
    for field_name in RELATIONSHIP_FIELDS:
        val = fm.get(field_name)
        if isinstance(val, str) and val:
            targets.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item:
                    targets.append(item)
    return targets


def _get_proposal_targets(enrich_meta: dict) -> list[str]:
    """Extract proposal target IDs from _llm_metadata.enrich."""
    targets = []
    axes = enrich_meta.get("axes", {})
    relationships = axes.get("relationships", {})
    proposals = relationships.get("proposals", [])
    if isinstance(proposals, list):
        for p in proposals:
            if isinstance(p, dict):
                tid = p.get("target_id")
                if isinstance(tid, str) and tid:
                    targets.append(tid)
    return targets


def _get_target_identifiers(
    target_ids: set[str],
    config: FolioConfig,
) -> dict[str, tuple[str, str]]:
    """Look up source_hash and version for target IDs from the registry."""
    if not target_ids:
        return {}
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    if not registry_path.exists():
        return {}
    try:
        reg_data = registry_mod.load_registry(registry_path)
    except Exception:
        return {}
    result: dict[str, tuple[str, str]] = {}
    for tid in target_ids:
        entry = reg_data.get("decks", {}).get(tid, {})
        result[tid] = (
            entry.get("source_hash", ""),
            str(entry.get("version", "")),
        )
    return result


def _get_enrich_meta(fm: dict) -> dict:
    """Get _llm_metadata.enrich block, defaulting to empty dict."""
    llm_meta = fm.get("_llm_metadata", {})
    if not isinstance(llm_meta, dict):
        return {}
    return llm_meta.get("enrich", {}) or {}


def _collect_managed_contents(doc: MarkdownDocument, doc_type: str) -> dict[str, str]:
    """Collect managed section contents as heading -> body text."""
    managed = doc.get_managed_sections(doc_type)
    contents = {}
    for key, section in managed.items():
        body = doc.content[section.body_start:section.end]
        contents[key] = body
    return contents


# ---------------------------------------------------------------------------
# Plan entry and batch result
# ---------------------------------------------------------------------------

@dataclass
class EnrichPlanEntry:
    """A single note to be considered for enrichment."""

    entry: registry_mod.RegistryEntry
    md_path: Path
    doc_type: str
    disposition: str  # "analyze", "skip", "protect", "conflict"
    reason: str
    existing_fm: dict
    doc: MarkdownDocument


@dataclass
class EnrichBatchResult:
    """Summary of a batch enrichment run."""

    updated: int = 0
    unchanged: int = 0
    protected: int = 0
    conflicted: int = 0
    failed: int = 0
    outcomes: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Planning phase
# ---------------------------------------------------------------------------

def plan_enrichment(
    config: FolioConfig,
    scope: str | None = None,
    force: bool = False,
    llm_profile: str | None = None,
    dry_run: bool = False,
) -> list[EnrichPlanEntry]:
    """Build the deterministic enrichment plan.

    Bootstrap/load registry, filter by scope and type, compute fingerprints,
    and determine disposition for each eligible note.

    When ``dry_run`` is True, the registry is built in memory but never
    written to disk (B1 fix: dry-run writes nothing).
    """
    library_root = config.library_root.resolve()

    # Bootstrap or load registry (read-only in dry-run)
    registry_path = library_root / "registry.json"
    if registry_path.exists():
        data = registry_mod.load_registry(registry_path)
        if data.get("_corrupt"):
            data = registry_mod.rebuild_registry(library_root)
            if not dry_run:
                registry_mod.save_registry(registry_path, data)
    else:
        data = registry_mod.rebuild_registry(library_root)
        if not dry_run:
            registry_mod.save_registry(registry_path, data)

    # Resolve profile name for fingerprinting
    try:
        profile = config.llm.resolve_profile(llm_profile, task="enrich")
        profile_name = profile.name
    except ValueError:
        profile_name = "default"

    missing_type_count = sum(
        1
        for entry_data in data.get("decks", {}).values()
        if isinstance(entry_data, dict) and "type" not in entry_data
    )
    if missing_type_count:
        logger.warning(
            "Detected %d registry entr%s missing 'type'; defaulting to "
            "'evidence' for compatibility. If this library was built by an older "
            "folio-love version, run 'folio status --refresh' to persist current "
            "registry fields.",
            missing_type_count,
            "y" if missing_type_count == 1 else "ies",
        )

    plan: list[EnrichPlanEntry] = []

    for deck_id, entry_data in data.get("decks", {}).items():
        entry = registry_mod.entry_from_dict(entry_data)

        # Filter: evidence and interaction only
        if entry.type not in ("evidence", "interaction"):
            continue

        # Scope filter
        if scope:
            if not (_matches_scope(entry.markdown_path, scope) or
                    _matches_scope(entry.deck_dir, scope)):
                continue

        md_path = library_root / entry.markdown_path
        if not md_path.exists():
            continue

        # Read frontmatter and content
        try:
            content = md_path.read_text(encoding="utf-8")
        except Exception:
            continue

        fm = _read_frontmatter(md_path)
        if fm is None:
            # Frontmatter parse failure on existing file — treat as protected
            # to avoid body mutation on a note whose curation_level/review_status
            # are unknown (S3 fix).
            logger.warning("Frontmatter unreadable for %s; treating as protected", md_path.name)
            fm = {"_frontmatter_unreadable": True}

        doc_type = entry.type or "evidence"
        doc = MarkdownDocument(content)

        # Determine disposition
        disposition, reason = _determine_disposition(
            fm=fm,
            doc=doc,
            doc_type=doc_type,
            profile_name=profile_name,
            force=force,
            entities_path=library_root / "entities.json",
            config=config,
        )

        plan.append(EnrichPlanEntry(
            entry=entry,
            md_path=md_path,
            doc_type=doc_type,
            disposition=disposition,
            reason=reason,
            existing_fm=fm,
            doc=doc,
        ))

    return plan


def _determine_disposition(
    *,
    fm: dict,
    doc: MarkdownDocument,
    doc_type: str,
    profile_name: str,
    force: bool,
    entities_path: Path | None = None,
    config: FolioConfig | None = None,
) -> tuple[str, str]:
    """Determine the enrichment disposition for a note.

    Returns (disposition, reason) tuple.
    """
    enrich_meta = _get_enrich_meta(fm)
    managed_sections = doc.get_managed_sections(doc_type)

    # S3: unreadable frontmatter → protect
    if fm.get("_frontmatter_unreadable"):
        return "protect", "frontmatter unreadable"

    # Protection checks (still get metadata-only updates)
    curation = fm.get("curation_level", "L0")
    review_status = fm.get("review_status", "clean")

    if curation and curation != "L0":
        return "protect", f"curation_level={curation}"

    if review_status in ("reviewed", "overridden"):
        return "protect", f"review_status={review_status}"

    if not managed_sections and enrich_meta:
        # Can't identify managed sections on a note that was previously enriched
        return "protect", "managed sections not identifiable"

    # Conflict check: managed body fingerprint mismatch
    stored_body_fp = enrich_meta.get("managed_body_fingerprint")
    if stored_body_fp and managed_sections:
        current_contents = _collect_managed_contents(doc, doc_type)
        current_body_fp = compute_managed_body_fingerprint(current_contents)
        if current_body_fp != stored_body_fp:
            return "conflict", "managed body fingerprint mismatch"

    # Stale status always requires analysis
    if enrich_meta.get("status") == "stale":
        return "analyze", "stale"

    # Skip if fingerprint matches (unless force)
    if not force:
        stored_input_fp = enrich_meta.get("input_fingerprint")
        if stored_input_fp:
            stripped = _strip_managed_content(doc.content, doc, doc_type)

            # Recompute entity_resolution_fingerprint from live entities.json
            # so that human confirmations trigger re-enrichment (V4 fix 1).
            entity_fp = _recompute_live_entity_fp(enrich_meta, entities_path)
            # Recompute relationship_context_fingerprint from live canonical
            # targets so human-confirmed relationship edits trigger
            # re-enrichment and ## Related regeneration (B2 fix).
            relationship_fp = _recompute_live_relationship_fp(
                fm, enrich_meta, config.library_root.resolve(),
            )

            current_input_fp = compute_input_fingerprint(
                stripped, entity_fp, relationship_fp,
                profile_name, ENRICH_SPEC_VERSION,
            )
            if current_input_fp == stored_input_fp:
                return "skip", "fingerprint match"

    return "analyze", "eligible"


def _recompute_live_entity_fp(
    enrich_meta: dict,
    entities_path: Path | None,
) -> str:
    """Recompute entity_resolution_fingerprint from live entities.json.

    Reads the stored mention records from enrich metadata, then looks up
    each mention's current resolution status in the live entity registry.
    This ensures human confirmations change the fingerprint.
    """
    axes = enrich_meta.get("axes", {})
    mentions = axes.get("entities", {}).get("mentions", [])
    if not mentions or not entities_path or not entities_path.exists():
        return enrich_meta.get("entity_resolution_fingerprint", "")

    from .tracking.entities import EntityRegistry, lookup_person_matches

    registry = EntityRegistry(entities_path)
    try:
        registry.load()
    except Exception:
        return enrich_meta.get("entity_resolution_fingerprint", "")

    pairs: list[tuple[str, str]] = []
    for m in mentions:
        text = m.get("text", "")
        etype = m.get("type", "")
        # Look up current status in live registry
        if etype == "person":
            results = lookup_person_matches(registry, text)
        else:
            results = registry.lookup(text, entity_type=etype)
        if len(results) == 1:
            _et, _key, entry = results[0]
            # Use canonical_name (not key) to match what enrich_note stores
            cname = entry.canonical_name
            if entry.needs_confirmation:
                if entry.proposed_match:
                    resolution = f"proposed_match:{_et}/{cname}"
                else:
                    resolution = f"unconfirmed:{_et}/{cname}"
            else:
                resolution = f"confirmed:{_et}/{cname}"
        else:
            # Ambiguous or missing live matches must not preserve a stale
            # fingerprint for the first result.
            resolution = "unresolved"
        pairs.append((text, resolution))

    return compute_entity_resolution_fingerprint(pairs)


def _recompute_live_relationship_fp(
    fm: dict,
    enrich_meta: dict,
    library_root: Path,
) -> str:
    """Recompute relationship_context_fingerprint from live canonical state.

    Reads canonical relationship targets directly from current frontmatter
    and proposal targets from stored metadata so that human-confirmed
    relationship edits (e.g., adding ``supersedes: target_id``) trigger
    re-enrichment and ``## Related`` regeneration (B2 fix).

    Also includes target source/version identifiers per spec §D9.
    """
    canonical_targets = _get_canonical_targets(fm)
    # Get stored proposal targets
    proposals = (
        enrich_meta
        .get("axes", {})
        .get("relationships", {})
        .get("proposals", [])
    )
    proposal_targets = [p.get("target_id", "") for p in proposals if p.get("target_id")]

    # Look up target source/version identifiers from registry
    target_identifiers: dict[str, tuple[str, str]] = {}
    all_targets = set(canonical_targets) | set(proposal_targets)
    if all_targets:
        registry_path = library_root / "registry.json"
        if registry_path.exists():
            try:
                reg_data = registry_mod.load_registry(registry_path)
                for tid in all_targets:
                    entry = reg_data.get("decks", {}).get(tid, {})
                    target_identifiers[tid] = (
                        entry.get("source_hash", ""),
                        str(entry.get("version", "")),
                    )
            except Exception:
                pass

    return compute_relationship_context_fingerprint(
        canonical_targets, proposal_targets, target_identifiers,
    )


# ---------------------------------------------------------------------------
# Per-note enrichment
# ---------------------------------------------------------------------------

def enrich_note(
    config: FolioConfig,
    plan_entry: EnrichPlanEntry,
    llm_profile: str | None = None,
    force: bool = False,
) -> EnrichResult:
    """Enrich a single note per spec section 10 steps 6-17."""
    library_root = config.library_root.resolve()
    fm = dict(plan_entry.existing_fm)
    doc = plan_entry.doc
    doc_type = plan_entry.doc_type
    content = doc.content

    # Step 6: resolve LLM profile
    profile = config.llm.resolve_profile(llm_profile, task="enrich")
    fallbacks = config.llm.get_fallbacks(llm_profile, task="enrich")
    fallback_specs: list[FallbackProfileSpec] = [
        (fb.provider, fb.model, fb.api_key_env, fb.base_url_env)
        for fb in fallbacks
    ]

    provider_settings = config.get_all_provider_settings() if hasattr(config, 'get_all_provider_settings') else {}

    # Step 7: primary enrich analysis
    existing_tags = fm.get("tags", [])
    if not isinstance(existing_tags, list):
        existing_tags = []

    # Build peer context for relationship cues
    peer_context = _build_peer_context(config, plan_entry)

    analysis_output = analyze_note_for_enrichment(
        note_content=content,
        doc_type=doc_type,
        existing_tags=existing_tags,
        existing_frontmatter=fm,
        provider_name=profile.provider,
        model=profile.model,
        api_key_env=profile.api_key_env,
        base_url_env=profile.base_url_env,
        fallback_profiles=fallback_specs,
        all_provider_settings=provider_settings,
        peer_context=peer_context,
    )

    warnings: list[str] = []

    # Step 8: entity resolution
    entities_path = library_root / "entities.json"
    entity_mentions = analysis_output.entity_mention_candidates

    entities_axis = EnrichAxisResult(status="skipped")
    resolution_result = None
    entity_mention_records: list[dict] = []
    resolved_names: list[str] = []
    unresolved_created: list[str] = []

    if entity_mentions:
        try:
            resolution_result = resolve_entities(
                entities_path=entities_path,
                extracted_entities=entity_mentions,
                source_text=content,
                provider_name=profile.provider,
                model=profile.model,
                api_key_env=profile.api_key_env,
                base_url_env=profile.base_url_env,
                fallback_profiles=fallback_specs,
                all_provider_settings=provider_settings,
                defer_persistence=True,
            )
            warnings.extend(resolution_result.warnings)

            # Build mention records with spec-defined status prefixes
            # (confirmed/unconfirmed/proposed_match/unresolved).
            # created_entities overlap with resolution_result.entities
            # (both contain auto-created names), so build a skip set to
            # avoid duplicates and wrong confirmed: labels (B2 fix).
            created_names = {c.canonical_name for c in resolution_result.created_entities}

            for category, names in resolution_result.entities.items():
                singular_type = _PLURAL_TO_SINGULAR.get(category, category)
                for name in names:
                    if name in created_names:
                        continue  # handled below with correct prefix
                    # B4 fix: ambiguous matches are unresolved, not confirmed
                    if (singular_type, name) in resolution_result.ambiguous_names:
                        entity_mention_records.append({
                            "text": name,
                            "type": singular_type,
                            "resolution": "unresolved",
                        })
                    else:
                        entity_mention_records.append({
                            "text": name,
                            "type": singular_type,
                            "resolution": f"confirmed:{singular_type}/{name}",
                        })
                        resolved_names.append(name)

            for created in resolution_result.created_entities:
                unresolved_created.append(created.canonical_name)
                if created.proposed_match:
                    resolution = f"proposed_match:{created.entity_type}/{created.canonical_name}"
                else:
                    resolution = f"unconfirmed:{created.entity_type}/{created.canonical_name}"
                entity_mention_records.append({
                    "text": created.canonical_name,
                    "type": created.entity_type,
                    "resolution": resolution,
                })

            entities_axis = EnrichAxisResult(
                status="updated" if resolution_result.entities else "no_change",
                mentions=entity_mention_records if entity_mention_records else None,
                resolved=resolved_names if resolved_names else None,
                unresolved_created=unresolved_created if unresolved_created else None,
            )
        except Exception as exc:
            logger.warning("Entity resolution failed: %s", exc)
            warnings.append(f"Entity resolution failed: {exc}")
            entities_axis = EnrichAxisResult(status="error")

    # Compute entity fingerprint early so relationship evaluation can use it
    # for basis_fingerprint (B3 fix: use fresh value, not stale metadata)
    entity_fp = _compute_current_entity_fp(entity_mention_records)

    # Step 9: relationship evaluation (optional)
    relationships_axis = EnrichAxisResult(status="skipped")
    proposals: list[RelationshipProposal] = []

    client = fm.get("client")
    engagement = fm.get("engagement")
    has_relationship_scope = bool(client and engagement)
    relationship_cues = analysis_output.relationship_cues

    allowed_relations = _get_allowed_relations(doc_type)

    if has_relationship_scope and relationship_cues and allowed_relations:
        try:
            note_descriptor = _build_note_descriptor(plan_entry)
            peer_descriptors = _build_peer_descriptors(config, plan_entry)
            raw_proposals = evaluate_relationships(
                note_descriptor=note_descriptor,
                peer_descriptors=peer_descriptors,
                allowed_relations=allowed_relations,
                provider_name=profile.provider,
                model=profile.model,
                api_key_env=profile.api_key_env,
                base_url_env=profile.base_url_env,
                fallback_profiles=fallback_specs,
                all_provider_settings=provider_settings,
            )

            # S1 fix: normalize content for basis_fingerprint (strip
            # frontmatter and prior enrich output per spec §9.3)
            normalized_content = _strip_managed_content(content, doc, doc_type)

            for raw_p in raw_proposals:
                # B5 defense-in-depth: reject disallowed relation types
                raw_relation = raw_p.get("relation", "")
                if raw_relation not in allowed_relations:
                    continue
                # Compute basis fingerprint
                target_id = raw_p.get("target_id", "")
                basis_fp = _compute_proposal_basis_fingerprint(
                    normalized_content, entity_fp, target_id, config,
                )
                # Validate confidence (spec allows only high/medium)
                raw_confidence = raw_p.get("confidence", "medium")
                if raw_confidence not in ("high", "medium"):
                    raw_confidence = "medium"

                # Validate signals (spec §13.2 defines allowed sets)
                _ALLOWED_SIGNALS = {
                    "supersedes": {"same_source_stem", "title_lineage_match",
                                   "version_order", "newer_converted_timestamp"},
                    "impacts": {"explicit_document_reference",
                                "explicit_hypothesis_change",
                                "shared_named_asset"},
                }
                allowed = _ALLOWED_SIGNALS.get(raw_relation, set())
                raw_signals = raw_p.get("signals", [])
                validated_signals = [s for s in raw_signals if s in allowed] if allowed else raw_signals

                proposal = RelationshipProposal(
                    proposal_id=compute_relationship_proposal_id(
                        source_id=plan_entry.entry.id,
                        relation=raw_relation,
                        target_id=target_id,
                        basis_fingerprint=basis_fp,
                    ),
                    relation=raw_relation,
                    target_id=target_id,
                    producer="enrich",
                    basis_fingerprint=basis_fp,
                    confidence=raw_confidence,
                    signals=validated_signals,
                    rationale=raw_p.get("rationale", ""),
                    lifecycle_state="queued",
                )
                proposals.append(proposal)

            # Enforce singular supersedes
            proposals = _enforce_singular_supersedes(proposals)

            existing_meta = _get_enrich_meta(fm)

            # Step 10a: mark rejected-basis matches as suppressed
            proposals, rejection_suppressed = _suppress_rejected_proposals(
                new_proposals=proposals,
                existing_meta=existing_meta,
                force=force,
            )

            # Step 10b: remove proposals already promoted to canonical fields
            proposals = _remove_promoted_proposals(proposals, fm)

            # Step 10c: enforce queue cap (v0.6.3)
            existing_queued = _count_library_queued_proposals(
                config, "enrich", exclude_doc_id=plan_entry.entry.id,
            )
            proposals, cap_suppressed = _enforce_queue_cap(
                proposals, existing_queued,
            )

            # Step 10d: preserve rejected entries from previous runs
            preserved_rejected = _preserve_rejected_proposals(existing_meta)

            all_proposal_dicts = (
                preserved_rejected + [p.to_dict() for p in proposals]
            )

            # Suppression diagnostics
            suppression_counts: dict[str, int] = {}
            if rejection_suppressed:
                suppression_counts["rejection_memory"] = rejection_suppressed
            if cap_suppressed:
                suppression_counts["queue_cap"] = cap_suppressed

            if suppression_counts:
                parts = [f"{k}: {v}" for k, v in suppression_counts.items()]
                warnings.append(
                    f"{sum(suppression_counts.values())} proposal(s) suppressed "
                    f"({', '.join(parts)})"
                )

            if all_proposal_dicts:
                relationships_axis = EnrichAxisResult(
                    status="proposed",
                    proposals=all_proposal_dicts,
                    suppression_counts=suppression_counts or None,
                )
            else:
                relationships_axis = EnrichAxisResult(status="no_change")

        except Exception as exc:
            logger.warning("Relationship evaluation failed: %s", exc)
            warnings.append(f"Relationship evaluation failed: {exc}")
            relationships_axis = EnrichAxisResult(status="error")

    # Step 11: additive tag merge
    new_tags = analysis_output.tag_candidates
    tags_axis, merged_tags = _merge_tags(existing_tags, new_tags)

    # Build _llm_metadata.enrich block (spec section 9.2)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fallback_used = False  # simplified for v1

    # Compute remaining fingerprints (entity_fp already computed above)
    canonical_targets = _get_canonical_targets(fm)
    proposal_targets = [p.target_id for p in proposals]
    # Include target source/version identifiers per spec §D9
    target_identifiers = _get_target_identifiers(
        set(canonical_targets) | set(proposal_targets), config,
    )
    relationship_fp = compute_relationship_context_fingerprint(
        canonical_targets, proposal_targets, target_identifiers,
    )

    stripped_content = _strip_managed_content(content, doc, doc_type)
    input_fp = compute_input_fingerprint(
        stripped_content, entity_fp, relationship_fp,
        profile.name, ENRICH_SPEC_VERSION,
    )

    # Determine enrich status: if all axes are empty/error/skipped,
    # the LLM likely failed — mark as pending, not executed (V5 fix 3).
    all_axes_empty = (
        tags_axis.status in ("skipped", "no_change", "error")
        and entities_axis.status in ("skipped", "no_change", "error")
        and relationships_axis.status in ("skipped", "no_change", "error")
    )
    any_axis_error = (
        tags_axis.status == "error"
        or entities_axis.status == "error"
        or relationships_axis.status == "error"
    )
    if any_axis_error and all_axes_empty:
        enrich_status = "pending"
    elif all_axes_empty and not analysis_output.tag_candidates and not analysis_output.entity_mention_candidates:
        enrich_status = "pending"
    else:
        enrich_status = "executed"

    enrich_block = {
        "requested_profile": llm_profile or profile.name,
        "profile": profile.name,
        "provider": profile.provider,
        "model": profile.model,
        "fallback_used": fallback_used,
        "status": enrich_status,
        "timestamp": now_str,
        "spec_version": ENRICH_SPEC_VERSION,
        "input_fingerprint": input_fp,
        "entity_resolution_fingerprint": entity_fp,
        "relationship_context_fingerprint": relationship_fp,
        "axes": {
            "tags": tags_axis.to_dict(),
            "entities": entities_axis.to_dict(),
            "relationships": relationships_axis.to_dict(),
        },
    }

    # Step 12: body mutation safety
    disposition = plan_entry.disposition
    body_safe = disposition == "analyze"
    body_axis_status = "updated" if body_safe else (
        "skipped_protected" if disposition == "protect" else "conflict"
    )

    managed_sections = doc.get_managed_sections(doc_type)
    if not managed_sections and disposition == "analyze":
        body_safe = False
        body_axis_status = "skipped_protected"
        warnings.append("Managed sections not identifiable; body protected")

    # Step 13: rewrite managed sections if safe
    new_content = content
    if body_safe and managed_sections:
        new_content = _rewrite_managed_sections(
            content=content,
            doc=doc,
            doc_type=doc_type,
            resolution_result=resolution_result,
            entity_mentions=entity_mentions,
        )

    # Generate/update/remove ## Related from canonical frontmatter
    # Only mutate body (including ## Related) when body is safe (B1 fix)
    if body_safe:
        new_content = _update_related_section(
            content=new_content,
            doc_type=doc_type,
            fm=fm,
            config=config,
        )

    # Compute managed body fingerprint after changes
    new_doc = MarkdownDocument(new_content)
    new_managed_contents = _collect_managed_contents(new_doc, doc_type)
    if new_managed_contents:
        managed_body_fp = compute_managed_body_fingerprint(new_managed_contents)
        enrich_block["managed_body_fingerprint"] = managed_body_fp

    body_axis = EnrichAxisResult(status=body_axis_status)
    enrich_block["axes"]["body"] = body_axis.to_dict()

    # Step 15: update frontmatter and write
    # Update tags in frontmatter
    if merged_tags:
        fm["tags"] = merged_tags

    # Update _llm_metadata.enrich
    if "_llm_metadata" not in fm:
        fm["_llm_metadata"] = {}
    fm["_llm_metadata"]["enrich"] = enrich_block

    # Store relationship proposals in metadata
    # (canonical fields remain human-owned, D7)

    # Rewrite frontmatter in the note content
    new_content = _replace_frontmatter(new_content, fm)

    # Step 15: Atomic write
    _atomic_write_text(plan_entry.md_path, new_content)

    # Step 16: Persist deferred entity creations AFTER successful note write
    # (B3 fix: entities.json must not be updated if note write fails)
    if resolution_result is not None:
        persist_warnings = commit_deferred_entities(entities_path, resolution_result)
        warnings.extend(persist_warnings)

    # Determine outcome
    if body_safe and (tags_axis.status == "updated" or
                      entities_axis.status == "updated" or
                      relationships_axis.status == "proposed"):
        outcome = EnrichOutcome.updated
    elif disposition == "protect":
        outcome = EnrichOutcome.protected
    elif disposition == "conflict":
        outcome = EnrichOutcome.conflicted
    elif (tags_axis.status in ("updated",) or
          relationships_axis.status == "proposed"):
        outcome = EnrichOutcome.updated
    else:
        outcome = EnrichOutcome.unchanged

    return EnrichResult(
        outcome=outcome,
        tags_axis=tags_axis,
        entities_axis=entities_axis,
        relationships_axis=relationships_axis,
        body_axis=body_axis,
        warnings=warnings,
        tags_added=len(tags_axis.added) if tags_axis.added else 0,
        entities_added=len(resolved_names),
        proposals_count=len(proposals),
    )


# ---------------------------------------------------------------------------
# Tag merge
# ---------------------------------------------------------------------------

def _merge_tags(
    existing: list[str],
    candidates: list[str],
) -> tuple[EnrichAxisResult, list[str]]:
    """Additive tag merge: case-normalize, deduplicate, preserve existing."""
    existing_lower = {t.lower() for t in existing}
    new_tags = []
    for tag in candidates:
        normalized = tag.strip().lower()
        if normalized and normalized not in existing_lower:
            new_tags.append(normalized)
            existing_lower.add(normalized)

    merged = sorted(set(existing) | set(new_tags), key=str.lower)

    if new_tags:
        return EnrichAxisResult(status="updated", added=sorted(new_tags)), merged
    return EnrichAxisResult(status="no_change"), existing


# ---------------------------------------------------------------------------
# Relationship helpers
# ---------------------------------------------------------------------------

def _get_allowed_relations(doc_type: str) -> list[str]:
    """Get allowed relationship types for a document type."""
    if doc_type == "evidence":
        return ["supersedes"]
    elif doc_type == "interaction":
        return ["impacts"]
    return []


def _enforce_singular_supersedes(
    proposals: list[RelationshipProposal],
) -> list[RelationshipProposal]:
    """Enforce singular cardinality for supersedes.

    When multiple supersedes proposals exist, keep only the highest
    confidence one (``high`` > ``medium``).
    """
    _CONFIDENCE_RANK = {"high": 0, "medium": 1}
    # Sort supersedes proposals by confidence descending so the best one
    # comes first and survives the dedup pass.
    proposals = sorted(
        proposals,
        key=lambda p: _CONFIDENCE_RANK.get(p.confidence, 2)
        if p.relation == "supersedes" else -1,
    )
    seen_supersedes = False
    filtered = []
    for p in proposals:
        if p.relation == "supersedes":
            if seen_supersedes:
                continue  # Skip lower-confidence duplicate
            seen_supersedes = True
        filtered.append(p)
    return filtered


def _suppress_rejected_proposals(
    new_proposals: list[RelationshipProposal],
    existing_meta: dict,
    force: bool,
) -> tuple[list[RelationshipProposal], int]:
    """Mark proposals matching a rejected basis as suppressed.

    Returns (all_proposals_with_state_set, suppression_count).
    --force still respects rejection memory (§10.1 zero-defect invariant).
    """
    # Build rejected map: (relation, target_id) -> basis_fingerprint
    rejected: dict[tuple[str, str], str] = {}
    axes = existing_meta.get("axes", {})
    rel_meta = axes.get("relationships", {})
    old_proposals = rel_meta.get("proposals", [])
    if isinstance(old_proposals, list):
        for p in old_proposals:
            if isinstance(p, dict):
                if _get_lifecycle_state(p) != "rejected":
                    continue
                key = (p.get("relation", ""), p.get("target_id", ""))
                rejected[key] = p.get("basis_fingerprint", "")

    result = []
    suppressed_count = 0
    for proposal in new_proposals:
        key = (proposal.relation, proposal.target_id)
        if key in rejected:
            old_basis = rejected[key]
            if old_basis and old_basis == proposal.basis_fingerprint:
                proposal.lifecycle_state = "suppressed"
                suppressed_count += 1
        result.append(proposal)
    return result, suppressed_count


def _preserve_rejected_proposals(existing_meta: dict) -> list[dict]:
    """Return raw dicts for rejected proposals from existing frontmatter.

    These are appended to the output proposals list so operator rejections
    survive re-enrichment (§10.1 zero-defect invariant).
    """
    axes = existing_meta.get("axes", {})
    rel_meta = axes.get("relationships", {})
    old_proposals = rel_meta.get("proposals", [])
    preserved = []
    if isinstance(old_proposals, list):
        for p in old_proposals:
            if not isinstance(p, dict):
                continue
            state = p.get("lifecycle_state")
            if state is None:
                old_status = p.get("status")
                state = _STATUS_TO_LIFECYCLE.get(old_status, old_status)
            if state == "rejected":
                preserved.append(p)
    return preserved


def _get_lifecycle_state(raw: dict) -> str:
    """Get effective lifecycle state from a raw proposal dict."""
    state = raw.get("lifecycle_state")
    if state is None:
        old_status = raw.get("status", "pending_human_confirmation")
        state = _STATUS_TO_LIFECYCLE.get(old_status, old_status)
    return state


def _count_library_queued_proposals(
    config,
    producer: str,
    exclude_doc_id: str,
) -> int:
    """Count queued proposals across the library for a producer.

    L2 failure policy: per-document errors are caught and skipped.
    Registry read failure returns 0 (fail-open).
    """
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    if not registry_path.exists():
        return 0
    try:
        reg_data = registry_mod.load_registry(registry_path)
    except Exception:
        logger.warning("Queue cap: cannot read registry; cap not enforced")
        return 0

    count = 0
    for deck_id, entry_data in reg_data.get("decks", {}).items():
        if deck_id == exclude_doc_id:
            continue
        md_rel = entry_data.get("markdown_path", "")
        if not md_rel:
            continue
        md_path = library_root / md_rel
        try:
            if not md_path.exists():
                continue
            fm = _read_frontmatter(md_path)
            if not fm:
                continue
            producer_meta = fm.get("_llm_metadata", {}).get(producer)
            if not isinstance(producer_meta, dict):
                continue
            proposals = (
                producer_meta.get("axes", {})
                .get("relationships", {})
                .get("proposals", [])
            )
            if not isinstance(proposals, list):
                continue
            for raw in proposals:
                if isinstance(raw, dict) and _get_lifecycle_state(raw) == "queued":
                    count += 1
        except Exception:
            logger.warning("Queue cap: skipping unreadable %s", deck_id)
            continue
    return count


def _enforce_queue_cap(
    proposals: list[RelationshipProposal],
    existing_queued_count: int,
    cap: int = QUEUE_CAP,
) -> tuple[list[RelationshipProposal], int]:
    """Enforce per-producer queue cap. Only queued proposals are eligible.

    Returns (all_proposals, cap_suppression_count).
    Tie-breaking: high confidence first, then emission order (stable sort).
    """
    queued = [p for p in proposals if p.lifecycle_state == "queued"]
    non_queued = [p for p in proposals if p.lifecycle_state != "queued"]

    remaining_capacity = cap - existing_queued_count
    if remaining_capacity >= len(queued):
        return proposals, 0

    # Stable sort: high confidence first
    queued_sorted = sorted(
        queued,
        key=lambda p: 0 if p.confidence == "high" else 1,
    )

    suppressed_count = 0
    if remaining_capacity <= 0:
        for p in queued_sorted:
            p.lifecycle_state = "suppressed"
            suppressed_count += 1
    else:
        for p in queued_sorted[remaining_capacity:]:
            p.lifecycle_state = "suppressed"
            suppressed_count += 1

    return non_queued + queued_sorted, suppressed_count


def _remove_promoted_proposals(
    proposals: list[RelationshipProposal],
    fm: dict,
) -> list[RelationshipProposal]:
    """Remove proposals whose (relation, target_id) already exists in canonical fields.

    Spec rule 9.2.7: if a human copies a target into the canonical frontmatter
    field, the next enrich run removes that proposal from the active list.
    """
    result = []
    for proposal in proposals:
        canonical_val = fm.get(proposal.relation)
        if isinstance(canonical_val, str) and canonical_val == proposal.target_id:
            continue  # Already promoted to canonical
        if isinstance(canonical_val, list) and proposal.target_id in canonical_val:
            continue  # Already promoted to canonical
        result.append(proposal)
    return result


def _compute_proposal_basis_fingerprint(
    note_content: str,
    entity_fp: str,
    target_id: str,
    config: FolioConfig,
) -> str:
    """Compute basis_fingerprint for a relationship proposal.

    Uses the freshly computed entity_fp, not the stored value from prior
    run metadata (B3 fix).
    """
    # Get target note's source info from registry
    target_hash = ""
    target_version = ""
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    if registry_path.exists():
        reg_data = registry_mod.load_registry(registry_path)
        target_entry = reg_data.get("decks", {}).get(target_id, {})
        target_hash = target_entry.get("source_hash", "")
        target_version = str(target_entry.get("version", ""))

    combined = json.dumps(
        [_sha256_content(note_content), entity_fp, target_hash, target_version],
        sort_keys=True,
    )
    return f"sha256:{hashlib.sha256(combined.encode()).hexdigest()}"


# ---------------------------------------------------------------------------
# Entity fingerprint
# ---------------------------------------------------------------------------

def _compute_current_entity_fp(mention_records: list[dict]) -> str:
    """Compute entity resolution fingerprint from mention records."""
    pairs = [(m.get("text", ""), m.get("resolution", "")) for m in mention_records]
    return compute_entity_resolution_fingerprint(pairs)


# ---------------------------------------------------------------------------
# Peer context helpers
# ---------------------------------------------------------------------------

def _build_peer_context(config: FolioConfig, plan_entry: EnrichPlanEntry) -> str:
    """Build bounded peer context for enrich analysis."""
    client = plan_entry.existing_fm.get("client")
    engagement = plan_entry.existing_fm.get("engagement")
    if not client or not engagement:
        return ""

    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    if not registry_path.exists():
        return ""

    reg_data = registry_mod.load_registry(registry_path)
    peers = []
    for deck_id, entry_data in reg_data.get("decks", {}).items():
        if deck_id == plan_entry.entry.id:
            continue
        if entry_data.get("client") != client:
            continue
        if entry_data.get("engagement") != engagement:
            continue
        doc_type = entry_data.get("type", "evidence")
        if doc_type not in ("evidence", "interaction"):
            continue

        desc = (
            f"ID: {deck_id}\n"
            f"Title: {entry_data.get('title', '')}\n"
            f"Type: {doc_type}\n"
            f"Source hash: {entry_data.get('source_hash', '')}\n"
            f"Version: {entry_data.get('version', 1)}\n"
        )
        # Add tags from frontmatter if available
        md_path = library_root / entry_data.get("markdown_path", "")
        if md_path.exists():
            peer_fm = _read_frontmatter(md_path)
            if peer_fm:
                peer_tags = peer_fm.get("tags", [])
                if peer_tags:
                    desc += f"Tags: {', '.join(peer_tags[:10])}\n"
                # Add canonical relationship fields
                for rf in RELATIONSHIP_FIELDS:
                    val = peer_fm.get(rf)
                    if val:
                        desc += f"{rf}: {val}\n"
                # Add grounding_summary (spec D3 allowed peer context)
                gs = peer_fm.get("grounding_summary")
                if gs:
                    desc += f"Grounding: {gs}\n"
        peers.append(desc)

    return "\n---\n".join(peers[:20])  # Bounded peer context


def _build_note_descriptor(plan_entry: EnrichPlanEntry) -> str:
    """Build a note descriptor for relationship evaluation."""
    fm = plan_entry.existing_fm
    return (
        f"ID: {plan_entry.entry.id}\n"
        f"Title: {fm.get('title', '')}\n"
        f"Type: {plan_entry.doc_type}\n"
        f"Client: {fm.get('client', '')}\n"
        f"Engagement: {fm.get('engagement', '')}\n"
        f"Source: {fm.get('source', fm.get('source_transcript', ''))}\n"
        f"Source hash: {fm.get('source_hash', '')}\n"
        f"Version: {fm.get('version', 1)}\n"
        f"Tags: {', '.join(fm.get('tags', []))}\n"
    )


def _build_peer_descriptors(
    config: FolioConfig,
    plan_entry: EnrichPlanEntry,
) -> list[str]:
    """Build bounded peer descriptors for relationship evaluation."""
    client = plan_entry.existing_fm.get("client")
    engagement = plan_entry.existing_fm.get("engagement")
    if not client or not engagement:
        return []

    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    if not registry_path.exists():
        return []

    reg_data = registry_mod.load_registry(registry_path)
    descriptors = []
    for deck_id, entry_data in reg_data.get("decks", {}).items():
        if deck_id == plan_entry.entry.id:
            continue
        if entry_data.get("client") != client:
            continue
        if entry_data.get("engagement") != engagement:
            continue

        desc = (
            f"ID: {deck_id}\n"
            f"Title: {entry_data.get('title', '')}\n"
            f"Type: {entry_data.get('type', 'evidence')}\n"
            f"Source hash: {entry_data.get('source_hash', '')}\n"
            f"Version: {entry_data.get('version', 1)}\n"
        )
        gs = entry_data.get("grounding_summary")
        if gs:
            desc += f"Grounding: {gs}\n"
        descriptors.append(desc)

    return descriptors[:20]


# ---------------------------------------------------------------------------
# Body rewriting
# ---------------------------------------------------------------------------

def _rewrite_managed_sections(
    *,
    content: str,
    doc: MarkdownDocument,
    doc_type: str,
    resolution_result,
    entity_mentions: dict[str, list[str]],
) -> str:
    """Rewrite managed sections with enriched content."""
    if doc_type == "evidence":
        return _rewrite_evidence_sections(content, doc, resolution_result, entity_mentions)
    elif doc_type == "interaction":
        return _rewrite_interaction_sections(content, doc, resolution_result, entity_mentions)
    return content


def _rewrite_evidence_sections(
    content: str,
    doc: MarkdownDocument,
    resolution_result,
    entity_mentions: dict[str, list[str]],
) -> str:
    """Insert entity wikilinks into evidence ### Analysis prose fields."""
    if not resolution_result:
        return content

    # Build name -> wikilink map
    wikilink_map = _build_wikilink_map(resolution_result)
    if not wikilink_map:
        return content

    managed = doc.get_managed_sections("evidence")
    # Process sections in reverse order to avoid offset issues
    sections_by_pos = sorted(
        [(k, s) for k, s in managed.items() if k != "## Related"],
        key=lambda x: x[1].start,
        reverse=True,
    )

    result = content
    for key, section in sections_by_pos:
        body = result[section.body_start:section.end]
        new_body = _insert_wikilinks_in_analysis(body, wikilink_map)
        if new_body != body:
            result = result[:section.body_start] + new_body + result[section.end:]

    return result


def _rewrite_interaction_sections(
    content: str,
    doc: MarkdownDocument,
    resolution_result,
    entity_mentions: dict[str, list[str]],
) -> str:
    """Regenerate ## Entities Mentioned subsections for interaction notes."""
    if not resolution_result:
        return content

    entities_section = doc.get_section("## Entities Mentioned")
    if not entities_section:
        return content

    # Regenerate entity lists using same format as _append_entities
    new_body = _build_entities_mentioned_body(resolution_result.entities)
    return doc.replace_section_body(entities_section, new_body)


def _build_entities_mentioned_body(entities: dict[str, list[str]]) -> str:
    """Build ## Entities Mentioned body in the standard format."""
    lines = []
    for category, label in [
        ("people", "People"),
        ("departments", "Departments"),
        ("systems", "Systems"),
        ("processes", "Processes"),
    ]:
        lines.append(f"\n### {label}\n")
        values = entities.get(category, [])
        if not values:
            lines.append("- None")
        else:
            for item in values:
                sanitized = sanitize_wikilink_name(item)
                lines.append(f"- [[{sanitized}]]")
        lines.append("")

    return "\n".join(lines) + "\n"


def _build_wikilink_map(resolution_result) -> dict[str, str]:
    """Build name -> [[wikilink]] map from resolution results."""
    wikilink_map: dict[str, str] = {}
    if not resolution_result:
        return wikilink_map

    for category, names in resolution_result.entities.items():
        for name in names:
            sanitized = sanitize_wikilink_name(name)
            wikilink_map[name] = f"[[{sanitized}]]"

    return wikilink_map


def _insert_wikilinks_in_analysis(body: str, wikilink_map: dict[str, str]) -> str:
    """Insert wikilinks into Analysis prose fields.

    Only targets **Visual Description:**, **Key Data:**, and
    **Main Insight:** fields. Does NOT touch **Evidence:** blocks.
    """
    # Split into lines and process only safe prose fields
    lines = body.split("\n")
    result_lines = []
    in_evidence_block = False

    for line in lines:
        # Detect evidence block start/end
        if line.strip().startswith("**Evidence:**"):
            in_evidence_block = True
            result_lines.append(line)
            continue
        if in_evidence_block:
            # Evidence block continues until a non-indented line or new bold field
            if line.strip() and not line.startswith(" ") and not line.startswith("-"):
                in_evidence_block = False
            else:
                result_lines.append(line)
                continue

        # Only insert wikilinks in allowed prose fields
        is_prose_field = any(
            line.strip().startswith(prefix)
            for prefix in ("**Visual Description:**", "**Key Data:**", "**Main Insight:**")
        )
        if is_prose_field:
            # Sort by name length descending so longer names replace first,
            # preventing "Art" from matching inside "Artifacts" (V4 fix 2).
            replaced_names: set[str] = set()
            for name, wikilink in sorted(
                wikilink_map.items(), key=lambda x: len(x[0]), reverse=True,
            ):
                # Skip if a longer name containing this one was already replaced
                if any(name in rn for rn in replaced_names):
                    continue
                if name in line and wikilink not in line:
                    # Word-boundary replacement to avoid substring corruption
                    new_line = re.sub(
                        r'\b' + re.escape(name) + r'\b',
                        wikilink,
                        line,
                        count=1,
                    )
                    if new_line != line:
                        line = new_line
                        replaced_names.add(name)

        result_lines.append(line)

    return "\n".join(result_lines)


# ---------------------------------------------------------------------------
# ## Related section
# ---------------------------------------------------------------------------

def _update_related_section(
    *,
    content: str,
    doc_type: str,
    fm: dict,
    config: FolioConfig,
) -> str:
    """Generate, update, or remove ## Related from canonical frontmatter."""
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"

    # Collect canonical relationship targets
    targets_by_relation: dict[str, list[str]] = {}
    for field_name in RELATIONSHIP_FIELDS:
        val = fm.get(field_name)
        if isinstance(val, str) and val:
            targets_by_relation.setdefault(field_name, []).append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item:
                    targets_by_relation.setdefault(field_name, []).append(item)

    # Resolve targets through registry
    reg_data = {}
    if registry_path.exists():
        reg_data = registry_mod.load_registry(registry_path)

    resolved_links: dict[str, list[str]] = {}
    for relation, target_ids in targets_by_relation.items():
        for tid in target_ids:
            entry_data = reg_data.get("decks", {}).get(tid)
            if entry_data:
                md_path = entry_data.get("markdown_path", "")
                title = entry_data.get("title", tid)
                # Remove .md extension for wikilink
                link_path = md_path.removesuffix(".md") if md_path.endswith(".md") else md_path
                link = f"[[{link_path}|{title}]]"
                resolved_links.setdefault(relation, []).append(link)
            else:
                logger.warning(
                    "Canonical %s target '%s' not found in registry; "
                    "skipping from ## Related but preserving in frontmatter",
                    relation, tid,
                )

    # Build ## Related content
    doc = MarkdownDocument(content)
    existing_related = doc.get_section("## Related")

    # B6 fix: only remove/replace ## Related if it has the enrich ownership
    # marker, to avoid destroying human-authored ## Related sections.
    has_ownership = (
        existing_related is not None
        and _RELATED_MARKER in content[existing_related.start:existing_related.end]
    )

    if not resolved_links:
        # Remove stale generated ## Related if it exists and is ours
        if existing_related and has_ownership:
            end_pos = existing_related.end
            if doc_type == "interaction":
                # The callout is not a heading, so it gets grouped into ## Related.
                # Stop removal at the callout to preserve the raw transcript.
                match = re.search(r'^> \[!quote\]', content[existing_related.start:existing_related.end], re.MULTILINE)
                if match:
                    end_pos = existing_related.start + match.start()
            return content[:existing_related.start] + content[end_pos:]
        return content

    related_content = _render_related_section(resolved_links)

    if existing_related and has_ownership:
        # Replace our existing generated ## Related (include marker in body)
        marked_content = f"{_RELATED_MARKER}\n{related_content}"
        
        end_pos = existing_related.end
        if doc_type == "interaction":
            match = re.search(r'^> \[!quote\]', content[existing_related.start:existing_related.end], re.MULTILINE)
            if match:
                end_pos = existing_related.start + match.start()
                return content[:existing_related.body_start] + marked_content + content[end_pos:]

        return doc.replace_section_body(existing_related, marked_content)
    elif existing_related and not has_ownership:
        # Human-authored ## Related — don't touch it, warn
        logger.warning(
            "Skipping ## Related update: section exists but was not "
            "generated by enrich (no ownership marker)"
        )
        return content
    else:
        # Insert new ## Related at the appropriate position
        return _insert_related_section(content, doc_type, related_content, doc)


def _render_related_section(resolved_links: dict[str, list[str]]) -> str:
    """Render ## Related section body content."""
    lines = ["\n"]
    for relation, links in sorted(resolved_links.items()):
        # Capitalize and format relation name
        heading = relation.replace("_", " ").title()
        lines.append(f"### {heading}")
        for link in links:
            lines.append(f"- {link}")
        lines.append("")

    return "\n".join(lines)


def _insert_related_section(
    content: str,
    doc_type: str,
    related_body: str,
    doc: MarkdownDocument,
) -> str:
    """Insert ## Related at the correct position."""
    full_section = f"## Related\n{_RELATED_MARKER}\n{related_body}\n"

    if doc_type == "evidence":
        # Before ## Version History
        version_history = doc.get_section("## Version History")
        if version_history:
            return doc.insert_before_section("## Version History", full_section)
        # At end
        return content.rstrip() + "\n\n" + full_section

    elif doc_type == "interaction":
        # After ## Impact on Hypotheses, before raw transcript callout.
        # The raw transcript callout starts with "> [!quote]" and may be
        # the last content in the note. We must insert BEFORE it, not after
        # impact.end which may include or follow the callout (B4 fix).
        callout_match = re.search(r'^> \[!quote\]', content, re.MULTILINE)
        if callout_match:
            # Insert before the callout
            insert_pos = callout_match.start()
            return (
                content[:insert_pos].rstrip()
                + "\n\n" + full_section + "\n"
                + content[insert_pos:]
            )
        # No callout — insert after ## Impact on Hypotheses
        impact = doc.get_section("## Impact on Hypotheses")
        if impact:
            return (
                content[:impact.end]
                + "\n" + full_section
                + content[impact.end:]
            )
        # At end
        return content.rstrip() + "\n\n" + full_section

    return content.rstrip() + "\n\n" + full_section


# ---------------------------------------------------------------------------
# Frontmatter replacement
# ---------------------------------------------------------------------------

def _replace_frontmatter(content: str, fm: dict) -> str:
    """Replace the YAML frontmatter in content with updated dict.

    Uses line-by-line scanning to find the closing ``---`` delimiter,
    which safely handles multi-line YAML values that may contain ``---``.
    """
    yaml_str = yaml.dump(
        fm,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    new_fm = f"---\n{yaml_str}---"

    if not (content.startswith("---\n") or content.startswith("---\r\n")):
        return new_fm + "\n\n" + content

    # Find closing --- by scanning lines, skipping the opening delimiter.
    # The closing delimiter must be a line that is exactly '---' (possibly
    # with trailing whitespace), outside any YAML block scalar or multi-line
    # quoted string.
    lines = content.split("\n")
    in_block_scalar = False
    block_indent: int | None = None
    in_quoted: str | None = None  # tracks open quote char (' or ")

    for i, line in enumerate(lines):
        if i == 0:
            continue  # skip opening ---

        stripped = line.rstrip()

        # Track multi-line quoted strings (V4 fix 5).
        # A quoted value that spans multiple lines keeps the quote open.
        if in_quoted:
            # Count unescaped quote chars to detect close
            if in_quoted in stripped:
                # Simple heuristic: if the quote char appears, the string ends
                in_quoted = None
            # While inside a quoted string, skip all other checks
            continue

        # Track YAML block scalars (| or > indicators)
        if in_block_scalar:
            # Block scalar ends when we see a line at or below block_indent
            if stripped and not line[:1].isspace():
                in_block_scalar = False
                block_indent = None
            elif stripped:
                current_indent = len(line) - len(line.lstrip())
                if block_indent is not None and current_indent < block_indent:
                    in_block_scalar = False
                    block_indent = None

        if not in_block_scalar and stripped == "---":
            # Found closing delimiter
            rest_start = sum(len(l) + 1 for l in lines[:i + 1])
            return new_fm + content[rest_start - 1:]

        # Detect block scalar start: value is a block scalar indicator
        # (| or >) optionally followed by chomping (+/-) and/or indent digit.
        # Must be the sole value content to avoid false positives on strings
        # containing > (e.g. "note: x > y").
        if not in_block_scalar and re.match(r"^[^#]*:\s+[|>][+-]?\d*\s*(#.*)?$", line):
            in_block_scalar = True
            # Block indent determined by first non-empty continuation line
            block_indent = None
            # Look ahead to determine indent
            for j in range(i + 1, len(lines)):
                ahead = lines[j]
                if ahead.strip():
                    block_indent = len(ahead) - len(ahead.lstrip())

        # Detect multi-line quoted string opening.
        # Pattern: key: "value without closing quote  OR  key: 'value without closing quote
        if not in_block_scalar:
            m = re.match(r'^[^#]*:\s+(["\'])', line)
            if m:
                quote_char = m.group(1)
                # Count occurrences of the quote char after the opening one
                after_open = line[m.end():]
                # If the quote isn't closed on this line, we're in a multi-line string
                if after_open.count(quote_char) % 2 == 0:
                    # Even count (0, 2, ...) means no unmatched close
                    in_quoted = quote_char

    # Fallback: no closing delimiter found, prepend
    return new_fm + "\n\n" + content


# ---------------------------------------------------------------------------
# Batch enrichment
# ---------------------------------------------------------------------------

def enrich_batch(
    config: FolioConfig,
    scope: str | None = None,
    dry_run: bool = False,
    llm_profile: str | None = None,
    force: bool = False,
    echo=None,
) -> EnrichBatchResult:
    """Run batch enrichment over the library.

    Args:
        config: Folio configuration.
        scope: Optional scope filter.
        dry_run: If True, no LLM calls and no writes.
        llm_profile: Override LLM profile.
        force: Bypass fingerprint skip.
        echo: Output function (default: print).
    """
    if echo is None:
        echo = print

    # Plan phase
    plan = plan_enrichment(config, scope=scope, force=force, llm_profile=llm_profile, dry_run=dry_run)

    if not plan:
        logger.warning(
            "No eligible documents found. If this library was built by an older "
            "folio-love version, try 'folio status --refresh' to sync registry fields."
        )
        echo("No eligible documents found.")
        return EnrichBatchResult()

    # Count dispositions
    analyze_count = sum(1 for e in plan if e.disposition == "analyze")
    skip_count = sum(1 for e in plan if e.disposition == "skip")
    protect_count = sum(1 for e in plan if e.disposition == "protect")
    conflict_count = sum(1 for e in plan if e.disposition == "conflict")

    # Estimate relationship calls: notes with client+engagement that are analyze
    relationship_eligible = sum(
        1 for e in plan
        if e.disposition == "analyze"
        and e.existing_fm.get("client")
        and e.existing_fm.get("engagement")
    )

    echo(f"Scope: {len(plan)} eligible document(s)")
    echo(f"Estimated calls: primary={analyze_count} relationship<={relationship_eligible}")

    if dry_run:
        echo("")
        for entry in plan:
            symbol = {
                "analyze": "→",
                "skip": "↷",
                "protect": "!",
                "conflict": "!",
            }.get(entry.disposition, "?")
            echo(f"{symbol} {entry.entry.id}  {entry.disposition}: {entry.reason}")

        echo("")
        echo(
            f"Dry run: {analyze_count} would_analyze, {skip_count} would_skip, "
            f"{protect_count} would_protect, {conflict_count} would_conflict"
        )
        return EnrichBatchResult(
            unchanged=skip_count,
            protected=protect_count,
            conflicted=conflict_count,
        )

    # Execution phase
    echo("")
    echo(f"Enriching {len(plan)} document(s)...")
    result = EnrichBatchResult()

    with library_lock(config.library_root.resolve(), "enrich"):
        for plan_entry in plan:
            if plan_entry.disposition == "skip":
                echo(f"↷ {plan_entry.entry.id}  unchanged")
                result.unchanged += 1
                result.outcomes.append((plan_entry.entry.id, EnrichOutcome.unchanged))
                continue

            try:
                enrich_result = enrich_note(
                    config, plan_entry,
                    llm_profile=llm_profile,
                    force=force,
                )

                if enrich_result.outcome == EnrichOutcome.updated:
                    detail_parts = []
                    if enrich_result.tags_added:
                        detail_parts.append(f"tags:+{enrich_result.tags_added}")
                    if enrich_result.entities_added:
                        detail_parts.append(f"entities:+{enrich_result.entities_added}")
                    if enrich_result.proposals_count:
                        detail_parts.append(f"proposals:{enrich_result.proposals_count}")
                    detail = "  " + " ".join(detail_parts) if detail_parts else ""
                    echo(f"✓ {plan_entry.entry.id}{detail}")
                    result.updated += 1
                elif enrich_result.outcome == EnrichOutcome.unchanged:
                    echo(f"↷ {plan_entry.entry.id}  unchanged")
                    result.unchanged += 1
                elif enrich_result.outcome == EnrichOutcome.protected:
                    echo(f"! {plan_entry.entry.id}  protected; metadata only")
                    result.protected += 1
                elif enrich_result.outcome == EnrichOutcome.conflicted:
                    echo(f"! {plan_entry.entry.id}  conflict; metadata only")
                    result.conflicted += 1

                result.outcomes.append((plan_entry.entry.id, enrich_result.outcome))

                for warning in enrich_result.warnings:
                    logger.warning("%s: %s", plan_entry.entry.id, warning)

            except Exception as exc:
                echo(f"✗ {plan_entry.entry.id}  {exc}")
                result.failed += 1
                result.outcomes.append((plan_entry.entry.id, EnrichOutcome.failed))

    echo("")
    echo(
        f"Enrich complete: {result.updated} updated, {result.unchanged} unchanged, "
        f"{result.protected} protected, {result.conflicted} conflicted, "
        f"{result.failed} failed"
    )

    return result


# ---------------------------------------------------------------------------
# v1.0.0 diagnose surface (folio enrich diagnose)
# Tier-4 Roadmap row #4 sub-item A. Read-only enrichability hygiene check.
# Surfaces (disposition, reason) tuples from _determine_disposition as
# stable finding codes. See docs/specs/v1.0.0_folio_enrich_diagnose_spec.md
# and docs/specs/folio_enrich_spec.md §7.7 for the contract.
# ---------------------------------------------------------------------------

DIAGNOSE_SCHEMA_VERSION = "1.0"
DIAGNOSE_COMMAND_NAME = "enrich diagnose"

_SEVERITY_RANK = {"error": 3, "warning": 2, "info": 1}


class ScopeResolutionError(Exception):
    """Raised when --scope does not resolve to any registered deck.

    CB-3 closure: parent §7.7 says invalid scope is fatal exit non-zero.
    Diagnose treats a non-None scope that matches zero decks as fatal
    (typo guard).
    """


@dataclass(frozen=True)
class DiagnoseFinding:
    """A single enrichability blocker for a registry-managed note.

    Field order mirrors parent spec §7.7 fixed schema (5 keys), then
    trails the additive trust_status key per operator-confirmed product
    shape (annotation-only trust posture; see spec §6 firewall).
    """
    code: str
    severity: str
    subject_id: str
    detail: str
    recommended_action: str
    trust_status: str


@dataclass(frozen=True)
class DiagnoseSummary:
    """Aggregate counters for the run, surfaced in the §7 envelope.

    by_code is wrapped in MappingProxyType for value-level immutability
    (frozen-dataclass guarantee extends to dict values; PEER-MIN-003).
    """
    total: int
    by_code: Mapping[str, int]
    flagged_total: int


@dataclass(frozen=True)
class DiagnoseResult:
    """Top-level result of a diagnose run; mirrors §7 envelope shape.

    DCB-1 closure (D.4 fix): unfiltered_total carries the pre-truncation
    finding count so the text renderer can emit "showing N of M" per
    spec §4.3 (was emitting "showing N of more" in v1.3 because the
    renderer had no source of truth for M).
    """
    schema_version: str
    command: str
    scope: Optional[str]
    limit: Optional[int]
    findings: tuple[DiagnoseFinding, ...]
    summary: DiagnoseSummary
    truncated: bool
    unfiltered_total: int


def _finding_sort_key(f: DiagnoseFinding) -> tuple[int, str, str]:
    """Three-level sort key (CSF-1):
    severity desc (worst first), then code asc (group within tier),
    then subject_id asc (tie-break alphabetic).
    """
    return (-_SEVERITY_RANK[f.severity], f.code, f.subject_id)


def _check_registry_or_raise(config: FolioConfig) -> None:
    """DCB-2 closure (D.4 fix): unconditional registry health check.

    Runs BEFORE scope resolution and unconditionally for library-wide
    scope=None. Honors parent §7.7 fatal-on-unreadable-registry without
    being bypassed on library-wide invocation.

    DSF-003 closure: also fails fast when library_root does not exist
    or is not a directory (was producing "Registry bootstrapped: 0
    entries / No findings" — false-clean on a misconfigured root).

    Raises ScopeResolutionError on:
      - library_root nonexistent or not a directory (DSF-003)
      - registry.json present but flagged _corrupt (DCB-2)
    Does NOT raise when registry.json is simply missing (empty library
    is a valid healthy state).
    """
    library_root = config.library_root.resolve()
    if not library_root.exists() or not library_root.is_dir():
        raise ScopeResolutionError(
            f"Library root {library_root} does not exist or is not a "
            f"directory. Investigate the config before re-running diagnose."
        )
    registry_path = library_root / "registry.json"
    if not registry_path.exists():
        return
    data = registry_mod.load_registry(registry_path)
    if data.get("_corrupt"):
        raise ScopeResolutionError(
            f"Registry at {registry_path} is corrupt and cannot be parsed safely. "
            f"Investigate manually before re-running diagnose."
        )


def _resolve_scope_or_raise(config: FolioConfig, scope: str) -> None:
    """CB-3 scope-resolution preflight (post _check_registry_or_raise).

    Verify scope matches at least one registered deck. Raises
    ScopeResolutionError if scope is non-empty and no deck's deck_dir or
    markdown_path satisfies the scope-prefix predicate. Library-wide
    scope (None) bypasses this check entirely (DCB-2 closure: the
    library-wide health check is now done by _check_registry_or_raise).
    """
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    if not registry_path.exists():
        return
    data = registry_mod.load_registry(registry_path)
    if data.get("_corrupt"):
        raise ScopeResolutionError(
            f"Registry at {registry_path} is corrupt and cannot be parsed safely. "
            f"Investigate manually before re-running diagnose."
        )
    for entry_data in data.get("decks", {}).values():
        if not isinstance(entry_data, dict):
            continue
        entry = registry_mod.entry_from_dict(entry_data)
        if entry.type not in ("evidence", "interaction"):
            continue
        if (_matches_scope(entry.markdown_path, scope) or
                _matches_scope(entry.deck_dir, scope)):
            return
    raise ScopeResolutionError(
        f"Scope '{scope}' did not match any registered evidence or interaction "
        f"deck. Run 'folio status' to list registered scopes."
    )


def _entry_to_finding(entry: EnrichPlanEntry) -> Optional[DiagnoseFinding]:
    """Map an EnrichPlanEntry to a DiagnoseFinding, or None if healthy.

    Defensive defaults (ADV-SF-003): future protect / conflict / non-
    eligible analyze reasons surface as managed_sections_unidentified
    rather than silently disappearing. Future disposition values not in
    {protect, conflict, analyze, skip} return None and emit a warning.
    """
    disposition = entry.disposition
    reason = entry.reason
    subject_id = entry.entry.id

    if disposition == "protect":
        if reason == "frontmatter unreadable":
            code = "frontmatter_unreadable"
            severity = "error"
            action = (
                "Frontmatter cannot be parsed; restore the YAML block "
                "manually before re-running enrich."
            )
        elif reason == "managed sections not identifiable":
            code = "managed_sections_unidentified"
            severity = "warning"
            action = (
                "Verify the note's `## Slide N` / `### Analysis` / "
                "`## Related` / `## Entities Mentioned` headings are intact "
                "and not nested inside fenced code blocks."
            )
        elif reason.startswith("curation_level="):
            code = "protected_by_curation_level"
            severity = "warning"
            action = (
                "Body protection is intentional. To allow enrich to modify "
                "this note, edit the note's `curation_level` frontmatter "
                "field to a lower tier (L1 or L0) — no command demotion path "
                "exists today. Otherwise accept that enrich will not modify "
                "this note."
            )
        elif reason.startswith("review_status="):
            code = "protected_by_review_status"
            severity = "warning"
            action = (
                "Body protection is intentional. To allow enrich to modify "
                "this note, edit the note's `review_status` frontmatter "
                "field back to `clean` (no `folio unflag` command exists "
                "today). Otherwise accept that enrich will not modify this "
                "note."
            )
        else:
            code = "managed_sections_unidentified"
            severity = "warning"
            action = f"Unrecognized protect reason: {reason}. Investigate manually."
    elif disposition == "conflict":
        if reason == "managed body fingerprint mismatch":
            code = "managed_body_conflict"
            severity = "error"
            # DSF-002 closure (D.4): shlex.quote subject_id to prevent
            # shell-injection if a malicious deck_id contains backticks
            # or other shell metacharacters that an operator might
            # copy-paste into a shell.
            quoted = shlex.quote(subject_id)
            action = (
                f"Managed body content has been edited by hand. Reconcile "
                f"manually, then re-run with `folio enrich --force {quoted}` "
                f"to overwrite."
            )
        else:
            code = "managed_sections_unidentified"
            severity = "warning"
            action = f"Unrecognized conflict reason: {reason}. Investigate manually."
    elif disposition == "analyze" and reason == "stale":
        code = "enrich_status_stale"
        severity = "info"
        # DSF-002 closure (D.4): shlex.quote subject_id (see managed_body_conflict above).
        quoted = shlex.quote(subject_id)
        action = (
            f"Enrich state is stale (source was re-ingested or refreshed). "
            f"Re-run `folio enrich {quoted}` to refresh."
        )
    elif disposition == "analyze" and reason != "eligible":
        code = "managed_sections_unidentified"
        severity = "warning"
        action = f"Unrecognized analyze reason: {reason}. Investigate manually."
    elif disposition in ("analyze", "skip"):
        return None
    else:
        import warnings
        warnings.warn(
            f"Unrecognized disposition '{disposition}' for entry {subject_id}; "
            f"omitting from diagnose findings. Future enrich changes may need "
            f"diagnose updates.",
            RuntimeWarning,
        )
        return None

    review_status = entry.existing_fm.get("review_status", "clean")
    trust_status = "flagged" if review_status == "flagged" else "ok"

    return DiagnoseFinding(
        code=code,
        severity=severity,
        subject_id=subject_id,
        detail=reason,
        recommended_action=action,
        trust_status=trust_status,
    )


def diagnose_notes(
    config: FolioConfig,
    *,
    scope: Optional[str] = None,
    limit: Optional[int] = None,
) -> DiagnoseResult:
    """Run the read-only enrichability hygiene check.

    Identifies registry-managed evidence and interaction notes whose
    managed sections cannot be safely updated by `folio enrich`. Surfaces
    the (disposition, reason) tuples computed by _determine_disposition
    as stable finding codes per parent enrich spec §7.7.

    Args:
        config: FolioConfig
        scope: Optional scope prefix (deck_dir / markdown_path). None =
            library-wide.
        limit: Optional cap on rendered findings (post-sort). Must be >= 1
            or None.

    Returns:
        DiagnoseResult with the §7 envelope shape.

    Raises:
        ScopeResolutionError: scope is non-None and matches no registered
            evidence/interaction deck (CB-3 closure).
        ValueError: limit is not None and limit < 1 (ADV-SF-004 closure).
    """
    # DCB-2 / DSF-003 closure (D.4): unconditional registry + library_root
    # health check, runs BEFORE scope resolution and for library-wide too.
    _check_registry_or_raise(config)

    if scope is not None:
        _resolve_scope_or_raise(config, scope)

    if limit is not None and limit < 1:
        raise ValueError(f"limit must be >= 1 or None; got {limit!r}")

    plan = plan_enrichment(
        config, scope=scope, force=False, dry_run=True,
    )

    raw_findings: list[DiagnoseFinding] = []
    for entry in plan:
        finding = _entry_to_finding(entry)
        if finding is not None:
            raw_findings.append(finding)

    raw_findings.sort(key=_finding_sort_key)

    unfiltered_count = len(raw_findings)
    if limit is not None:
        rendered = tuple(raw_findings[:limit])
    else:
        rendered = tuple(raw_findings)

    by_code_dict = dict(sorted(Counter(f.code for f in rendered).items()))
    summary = DiagnoseSummary(
        total=len(rendered),
        by_code=MappingProxyType(by_code_dict),
        flagged_total=sum(1 for f in rendered if f.trust_status == "flagged"),
    )

    return DiagnoseResult(
        schema_version=DIAGNOSE_SCHEMA_VERSION,
        command=DIAGNOSE_COMMAND_NAME,
        scope=scope,
        limit=limit,
        findings=rendered,
        summary=summary,
        truncated=len(rendered) < unfiltered_count,
        unfiltered_total=unfiltered_count,  # DCB-1 closure (D.4)
    )
