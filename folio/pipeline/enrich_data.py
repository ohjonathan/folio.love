"""Enrich data model: constants, enums, dataclasses, and fingerprint functions.

Defines the data structures and deterministic fingerprint functions used by
``folio enrich`` for idempotency, conflict detection, and relationship
proposal lifecycle management.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENRICH_SPEC_VERSION = 2

RELATIONSHIP_FIELDS = (
    "depends_on",
    "draws_from",
    "impacts",
    "relates_to",
    "supersedes",
    "instantiates",
)

_SINGULAR_RELATIONSHIP_FIELDS = frozenset({"supersedes"})


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EnrichOutcome(str, Enum):
    """Per-note enrichment outcome."""

    updated = "updated"
    unchanged = "unchanged"
    protected = "protected"
    conflicted = "conflicted"
    failed = "failed"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

PROPOSAL_LIFECYCLE_STATES: frozenset[str] = frozenset({
    "queued",
    "accepted",
    "rejected",
    "suppressed",
    "stale",
    "superseded",
})

_STATUS_TO_LIFECYCLE: dict[str, str] = {
    "pending_human_confirmation": "queued",
    "rejected": "rejected",
}


@dataclass
class RelationshipProposal:
    """A machine-generated relationship proposal.

    Stored under ``_llm_metadata.enrich.axes.relationships.proposals``.
    """

    relation: str
    target_id: str
    basis_fingerprint: str
    confidence: str  # "high" or "medium"
    signals: list[str]
    rationale: str
    lifecycle_state: str = "queued"
    proposal_id: str = ""
    producer: str = "enrich"

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "relation": self.relation,
            "target_id": self.target_id,
            "producer": self.producer,
            "basis_fingerprint": self.basis_fingerprint,
            "confidence": self.confidence,
            "signals": list(self.signals),
            "rationale": self.rationale,
            "lifecycle_state": self.lifecycle_state,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RelationshipProposal:
        """Deserialize from dict with backward-compat for legacy ``status`` key."""
        relation = d["relation"]
        target_id = d["target_id"]
        basis_fingerprint = d.get("basis_fingerprint", "")
        producer = d.get("producer", "enrich")
        lifecycle_state = d.get("lifecycle_state")
        if lifecycle_state is None:
            old_status = d.get("status", "pending_human_confirmation")
            lifecycle_state = _STATUS_TO_LIFECYCLE.get(old_status, old_status)
        proposal = cls(
            relation=relation,
            target_id=target_id,
            basis_fingerprint=basis_fingerprint,
            confidence=d.get("confidence", "medium"),
            signals=list(d.get("signals", [])),
            rationale=d.get("rationale", ""),
            lifecycle_state=lifecycle_state,
            proposal_id=d.get("proposal_id", ""),
            producer=producer,
        )
        if not proposal.proposal_id:
            proposal.proposal_id = compute_relationship_proposal_id(
                source_id=str(d.get("source_id", "")),
                relation=relation,
                target_id=target_id,
                basis_fingerprint=basis_fingerprint,
            )
        return proposal


@dataclass
class EnrichAxisResult:
    """Per-axis enrichment result."""

    status: str  # "updated", "no_change", "skipped", "error", "proposed",
                 # "skipped_protected", "conflict"

    # Tag axis
    added: Optional[list[str]] = None

    # Entity axis
    mentions: Optional[list[dict]] = None
    resolved: Optional[list[str]] = None
    unresolved_created: Optional[list[str]] = None

    # Relationship axis
    proposals: Optional[list[dict]] = None

    def to_dict(self) -> dict:
        """Serialize, omitting None fields."""
        d: dict = {"status": self.status}
        if self.added is not None:
            d["added"] = self.added
        if self.mentions is not None:
            d["mentions"] = self.mentions
        if self.resolved is not None:
            d["resolved"] = self.resolved
        if self.unresolved_created is not None:
            d["unresolved_created"] = self.unresolved_created
        if self.proposals is not None:
            d["proposals"] = self.proposals
        return d


@dataclass
class EnrichResult:
    """Per-note enrichment result."""

    outcome: EnrichOutcome
    tags_axis: Optional[EnrichAxisResult] = None
    entities_axis: Optional[EnrichAxisResult] = None
    relationships_axis: Optional[EnrichAxisResult] = None
    body_axis: Optional[EnrichAxisResult] = None
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    # Summary counts for CLI output
    tags_added: int = 0
    entities_added: int = 0
    proposals_count: int = 0


# ---------------------------------------------------------------------------
# Fingerprint functions
# ---------------------------------------------------------------------------

def _sha256_hex(data: str) -> str:
    """Compute sha256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_relationship_proposal_id(
    *,
    source_id: str,
    relation: str,
    target_id: str,
    basis_fingerprint: str,
) -> str:
    """Compute a deterministic proposal ID for document-level relationships."""
    payload = json.dumps(
        [source_id, relation, target_id, basis_fingerprint],
        sort_keys=True,
    )
    return f"rprop-{_sha256_hex(payload)[:16]}"


def is_singular_relationship(relation: str) -> bool:
    """Return True when a canonical relationship field accepts one target only."""
    return relation in _SINGULAR_RELATIONSHIP_FIELDS


def compute_input_fingerprint(
    stripped_content: str,
    entity_fp: str,
    relationship_fp: str,
    profile_name: str,
    spec_version: int,
) -> str:
    """Compute the input fingerprint for skip detection.

    Changes to any component force a fresh enrich run.
    """
    combined = json.dumps(
        [stripped_content, entity_fp, relationship_fp, profile_name, spec_version],
        sort_keys=True,
    )
    return f"sha256:{_sha256_hex(combined)}"


def compute_entity_resolution_fingerprint(
    mentions: list[tuple[str, str]],
) -> str:
    """Compute entity resolution fingerprint from mention/resolution pairs.

    Args:
        mentions: List of (mention_text, resolution_outcome) pairs.
            Resolution outcomes are strings like:
            - ``confirmed:<type>/<key>``
            - ``unconfirmed:<type>/<key>``
            - ``proposed_match:<type>/<key>``
            - ``unresolved``

    The list is sorted deterministically before hashing.
    """
    sorted_pairs = sorted(mentions, key=lambda x: (x[0].lower(), x[1]))
    data = json.dumps(sorted_pairs, sort_keys=True)
    return f"sha256:{_sha256_hex(data)}"


def compute_relationship_context_fingerprint(
    canonical_targets: list[str],
    proposal_targets: list[str],
    target_identifiers: dict[str, tuple[str, str]] | None = None,
) -> str:
    """Compute relationship context fingerprint.

    Note-scoped: derived only from the note's own canonical relationship
    targets, stored proposal targets, and their current source/version
    identifiers (spec §D9).

    ``target_identifiers`` maps target_id to (source_hash, version).
    """
    ident_data = {}
    if target_identifiers:
        for tid in sorted(target_identifiers):
            sh, ver = target_identifiers[tid]
            ident_data[tid] = [sh, ver]

    combined = json.dumps(
        {
            "canonical": sorted(canonical_targets),
            "proposals": sorted(proposal_targets),
            "target_identifiers": ident_data,
        },
        sort_keys=True,
    )
    return f"sha256:{_sha256_hex(combined)}"


def compute_managed_body_fingerprint(
    managed_contents: dict[str, str],
) -> str:
    """Compute managed body fingerprint from section heading -> content map.

    Args:
        managed_contents: Dict of section_heading -> content, sorted by key.
    """
    sorted_items = sorted(managed_contents.items())
    data = json.dumps(sorted_items, sort_keys=True)
    return f"sha256:{_sha256_hex(data)}"
