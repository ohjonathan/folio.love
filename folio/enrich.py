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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from .config import FolioConfig, LLMProfile
from .llm.types import FallbackProfileSpec, ProviderRuntimeSettings
from .pipeline.enrich_data import (
    ENRICH_SPEC_VERSION,
    RELATIONSHIP_FIELDS,
    EnrichOutcome,
    EnrichAxisResult,
    EnrichResult,
    RelationshipProposal,
    compute_input_fingerprint,
    compute_entity_resolution_fingerprint,
    compute_relationship_context_fingerprint,
    compute_managed_body_fingerprint,
)
from .pipeline.enrich_analysis import (
    analyze_note_for_enrichment,
    evaluate_relationships,
)
from .pipeline.entity_resolution import resolve_entities
from .pipeline.section_parser import MarkdownDocument
from .tracking import registry as registry_mod
from .tracking.entities import sanitize_wikilink_name

logger = logging.getLogger(__name__)


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
    """Strip enrich-managed sections from content for fingerprinting.

    This gives a stable fingerprint of the note's non-enrich content.
    """
    managed = doc.get_managed_sections(doc_type)
    result = content
    # Remove managed sections from the content (process in reverse order
    # by start position to avoid offset drift)
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
) -> list[EnrichPlanEntry]:
    """Build the deterministic enrichment plan.

    Bootstrap/load registry, filter by scope and type, compute fingerprints,
    and determine disposition for each eligible note.
    """
    library_root = config.library_root.resolve()

    # Bootstrap or load registry
    registry_path = library_root / "registry.json"
    if registry_path.exists():
        data = registry_mod.load_registry(registry_path)
        if data.get("_corrupt"):
            data = registry_mod.rebuild_registry(library_root)
            registry_mod.save_registry(registry_path, data)
    else:
        data = registry_mod.rebuild_registry(library_root)
        registry_mod.save_registry(registry_path, data)

    # Resolve profile name for fingerprinting
    try:
        profile = config.llm.resolve_profile(llm_profile, task="enrich")
        profile_name = profile.name
    except ValueError:
        profile_name = "default"

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
            fm = {}

        doc_type = entry.type or "evidence"
        doc = MarkdownDocument(content)

        # Determine disposition
        disposition, reason = _determine_disposition(
            fm=fm,
            doc=doc,
            doc_type=doc_type,
            profile_name=profile_name,
            force=force,
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
) -> tuple[str, str]:
    """Determine the enrichment disposition for a note.

    Returns (disposition, reason) tuple.
    """
    enrich_meta = _get_enrich_meta(fm)
    managed_sections = doc.get_managed_sections(doc_type)

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
            # Compute current input fingerprint
            stripped = _strip_managed_content(doc.content, doc, doc_type)
            entity_fp = enrich_meta.get("entity_resolution_fingerprint", "")
            relationship_fp = enrich_meta.get("relationship_context_fingerprint", "")
            current_input_fp = compute_input_fingerprint(
                stripped, entity_fp, relationship_fp,
                profile_name, ENRICH_SPEC_VERSION,
            )
            if current_input_fp == stored_input_fp:
                return "skip", "fingerprint match"

    return "analyze", "eligible"


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
            )
            warnings.extend(resolution_result.warnings)

            # Build mention records with spec-defined status prefixes
            # (confirmed/unconfirmed/proposed_match/unresolved)
            for category, names in resolution_result.entities.items():
                for name in names:
                    entity_mention_records.append({
                        "text": name,
                        "type": category,
                        "resolution": f"confirmed:{category}/{name}",
                    })
                    resolved_names.append(name)

            for created in resolution_result.created_entities:
                unresolved_created.append(created.canonical_name)
                if created.proposed_match:
                    resolution = f"proposed_match:{created.entity_type}/{created.key}"
                else:
                    resolution = f"unconfirmed:{created.entity_type}/{created.key}"
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

            for raw_p in raw_proposals:
                # Compute basis fingerprint
                target_id = raw_p.get("target_id", "")
                basis_fp = _compute_proposal_basis_fingerprint(
                    content, _get_enrich_meta(fm), target_id, config,
                )
                proposal = RelationshipProposal(
                    relation=raw_p.get("relation", ""),
                    target_id=target_id,
                    basis_fingerprint=basis_fp,
                    confidence=raw_p.get("confidence", "medium"),
                    signals=raw_p.get("signals", []),
                    rationale=raw_p.get("rationale", ""),
                    status="pending_human_confirmation",
                )
                proposals.append(proposal)

            # Enforce singular supersedes
            proposals = _enforce_singular_supersedes(proposals)

            # Step 10: suppress rejected proposals with unchanged basis
            proposals = _suppress_rejected_proposals(
                new_proposals=proposals,
                existing_meta=_get_enrich_meta(fm),
                force=force,
            )

            # Remove proposals already promoted to canonical fields (spec 9.2.7)
            proposals = _remove_promoted_proposals(proposals, fm)

            if proposals:
                relationships_axis = EnrichAxisResult(
                    status="proposed",
                    proposals=[p.to_dict() for p in proposals],
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

    # Compute fingerprints
    entity_fp = _compute_current_entity_fp(entity_mention_records)
    canonical_targets = _get_canonical_targets(fm)
    proposal_targets = [p.target_id for p in proposals]
    relationship_fp = compute_relationship_context_fingerprint(
        canonical_targets, proposal_targets,
    )

    stripped_content = _strip_managed_content(content, doc, doc_type)
    input_fp = compute_input_fingerprint(
        stripped_content, entity_fp, relationship_fp,
        profile.name, ENRICH_SPEC_VERSION,
    )

    enrich_block = {
        "requested_profile": llm_profile or profile.name,
        "profile": profile.name,
        "provider": profile.provider,
        "model": profile.model,
        "fallback_used": fallback_used,
        "status": "executed",
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

    # Atomic write
    _atomic_write_text(plan_entry.md_path, new_content)

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
) -> list[RelationshipProposal]:
    """Suppress proposals that were previously rejected with unchanged basis.

    --force still respects unchanged rejection basis (spec section 7.3).
    """
    # Build rejected map: (relation, target_id) -> basis_fingerprint
    rejected: dict[tuple[str, str], str] = {}
    axes = existing_meta.get("axes", {})
    rel_meta = axes.get("relationships", {})
    old_proposals = rel_meta.get("proposals", [])
    if isinstance(old_proposals, list):
        for p in old_proposals:
            if isinstance(p, dict) and p.get("status") == "rejected":
                key = (p.get("relation", ""), p.get("target_id", ""))
                rejected[key] = p.get("basis_fingerprint", "")

    result = []
    for proposal in new_proposals:
        key = (proposal.relation, proposal.target_id)
        if key in rejected:
            old_basis = rejected[key]
            if old_basis and old_basis == proposal.basis_fingerprint:
                # Basis unchanged — suppress even with --force
                continue
        result.append(proposal)
    return result


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
    enrich_meta: dict,
    target_id: str,
    config: FolioConfig,
) -> str:
    """Compute basis_fingerprint for a relationship proposal."""
    entity_fp = enrich_meta.get("entity_resolution_fingerprint", "")
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
            for name, wikilink in wikilink_map.items():
                if name in line and wikilink not in line:
                    # Simple first-occurrence replacement
                    line = line.replace(name, wikilink, 1)

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

    if not resolved_links:
        # Remove stale ## Related if it exists
        if existing_related:
            return doc.remove_section("## Related")
        return content

    related_content = _render_related_section(resolved_links)

    if existing_related:
        # Replace existing ## Related
        return doc.replace_section_body(existing_related, related_content)
    else:
        # Insert ## Related at the appropriate position
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
    full_section = f"## Related\n{related_body}\n"

    if doc_type == "evidence":
        # Before ## Version History
        version_history = doc.get_section("## Version History")
        if version_history:
            return doc.insert_before_section("## Version History", full_section)
        # At end
        return content.rstrip() + "\n\n" + full_section

    elif doc_type == "interaction":
        # After ## Impact on Hypotheses, before raw transcript
        impact = doc.get_section("## Impact on Hypotheses")
        if impact:
            # Insert after impact section ends
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
    # with trailing whitespace), outside any YAML block scalar.
    lines = content.split("\n")
    in_block_scalar = False
    block_indent: int | None = None

    for i, line in enumerate(lines):
        if i == 0:
            continue  # skip opening ---

        stripped = line.rstrip()

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

        # Detect block scalar start: line ending with | or > (with optional
        # chomping/indentation indicators)
        if not in_block_scalar and re.match(r"^[^#]*:\s+[|>]", line):
            in_block_scalar = True
            # Block indent determined by first non-empty continuation line
            block_indent = None
            # Look ahead to determine indent
            for j in range(i + 1, len(lines)):
                ahead = lines[j]
                if ahead.strip():
                    block_indent = len(ahead) - len(ahead.lstrip())
                    break

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
    plan = plan_enrichment(config, scope=scope, force=force, llm_profile=llm_profile)

    if not plan:
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
