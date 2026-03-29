"""Data model and deterministic helpers for retroactive provenance linking."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


PROVENANCE_SPEC_VERSION = 1
PROVENANCE_REVIEW_FLAG = "provenance_link_stale"


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_digest(payload: object) -> str:
    return _sha256_hex(json.dumps(payload, sort_keys=True, ensure_ascii=False))


@dataclass(frozen=True)
class ExtractedEvidenceItem:
    """A claim-like evidence item extracted from a note's **Evidence:** blocks."""

    claim_text: str
    supporting_quote: str
    original_confidence: str
    element_type: str
    slide_number: int
    claim_index: int
    claim_hash: str = ""

    def to_prompt_dict(self) -> dict:
        return {
            "slide_number": self.slide_number,
            "claim_index": self.claim_index,
            "claim_text": self.claim_text,
            "supporting_quote": self.supporting_quote,
            "original_confidence": self.original_confidence,
            "element_type": self.element_type,
        }


@dataclass(frozen=True)
class ProvenanceProposal:
    """A machine-generated provenance proposal for one source claim."""

    proposal_id: str
    source_claim: ExtractedEvidenceItem
    target_doc: str
    target_evidence: ExtractedEvidenceItem
    confidence: str
    rationale: str
    basis_fingerprint: str
    model: str
    timestamp_proposed: str
    status: str = "pending_human_confirmation"
    replaces_link_id: str | None = None

    def to_dict(self) -> dict:
        result = {
            "proposal_id": self.proposal_id,
            "source_claim": {
                "slide_number": self.source_claim.slide_number,
                "claim_index": self.source_claim.claim_index,
                "claim_text": self.source_claim.claim_text,
                "supporting_quote": self.source_claim.supporting_quote,
                "claim_hash": self.source_claim.claim_hash,
            },
            "target_doc": self.target_doc,
            "target_evidence": {
                "slide_number": self.target_evidence.slide_number,
                "claim_index": self.target_evidence.claim_index,
                "claim_text": self.target_evidence.claim_text,
                "supporting_quote": self.target_evidence.supporting_quote,
                "claim_hash": self.target_evidence.claim_hash,
            },
            "confidence": self.confidence,
            "rationale": self.rationale,
            "basis_fingerprint": self.basis_fingerprint,
            "model": self.model,
            "timestamp_proposed": self.timestamp_proposed,
            "status": self.status,
        }
        if self.replaces_link_id:
            result["replaces_link_id"] = self.replaces_link_id
        return result


def compute_claim_hash(claim_text: str, supporting_quote: str) -> str:
    normalized_claim = " ".join((claim_text or "").split())
    normalized_quote = " ".join((supporting_quote or "").split())
    return f"sha256:{_sha256_hex(f'{normalized_claim}|{normalized_quote}')}"


def compute_pair_fingerprint(
    source_claims: list[ExtractedEvidenceItem],
    target_evidence: list[ExtractedEvidenceItem],
    profile_name: str,
    spec_version: int = PROVENANCE_SPEC_VERSION,
) -> str:
    payload = {
        "source_claims": [
            (
                item.slide_number,
                item.claim_index,
                item.claim_hash,
            )
            for item in sorted(source_claims, key=lambda item: (item.slide_number, item.claim_index))
        ],
        "target_evidence": [
            (
                item.slide_number,
                item.claim_index,
                item.claim_hash,
            )
            for item in sorted(target_evidence, key=lambda item: (item.slide_number, item.claim_index))
        ],
        "profile": profile_name,
        "provenance_spec_version": spec_version,
    }
    return f"sha256:{_stable_digest(payload)}"


def compute_basis_fingerprint(
    claim_hash: str,
    target_claim_hash: str,
    profile_name: str,
) -> str:
    return f"sha256:{_stable_digest([claim_hash, target_claim_hash, profile_name])}"


def make_proposal_id(
    source_doc: str,
    source_slide: int,
    source_claim_index: int,
    target_doc: str,
    target_slide: int,
    target_claim_index: int,
) -> str:
    digest = _stable_digest(
        [
            source_doc,
            source_slide,
            source_claim_index,
            target_doc,
            target_slide,
            target_claim_index,
        ]
    )[:8]
    return f"prov-{digest}"


def make_link_id(
    source_doc: str,
    source_slide: int,
    source_claim_index: int,
    target_doc: str,
    target_slide: int,
    target_claim_index: int,
) -> str:
    digest = _stable_digest(
        [
            source_doc,
            source_slide,
            source_claim_index,
            target_doc,
            target_slide,
            target_claim_index,
        ]
    )[:8]
    return f"plink-{digest}"
