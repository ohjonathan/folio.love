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
    status: str  # "pending_human_confirmation" or "rejected"

    def to_dict(self) -> dict:
        """Serialize to dict matching spec section 9.3."""
        return {
            "relation": self.relation,
            "target_id": self.target_id,
            "basis_fingerprint": self.basis_fingerprint,
            "confidence": self.confidence,
            "signals": list(self.signals),
            "rationale": self.rationale,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RelationshipProposal:
        """Deserialize from dict."""
        return cls(
            relation=d["relation"],
            target_id=d["target_id"],
            basis_fingerprint=d.get("basis_fingerprint", ""),
            confidence=d.get("confidence", "medium"),
            signals=list(d.get("signals", [])),
            rationale=d.get("rationale", ""),
            status=d.get("status", "pending_human_confirmation"),
        )


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
) -> str:
    """Compute relationship context fingerprint.

    Note-scoped: derived only from the note's own canonical relationship
    targets and stored proposal targets.
    """
    combined = json.dumps(
        {
            "canonical": sorted(canonical_targets),
            "proposals": sorted(proposal_targets),
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
