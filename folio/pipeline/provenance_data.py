"""Shared data model and deterministic helpers for retroactive provenance linking."""

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

    def to_prompt_dict(self, ref: str | None = None) -> dict:
        payload = {
            "slide_number": self.slide_number,
            "claim_index": self.claim_index,
            "claim_text": self.claim_text,
            "supporting_quote": self.supporting_quote,
            "original_confidence": self.original_confidence,
            "element_type": self.element_type,
        }
        if ref is not None:
            payload["ref"] = ref
        return payload


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
