"""Focused unit coverage for provenance repair, locking, and edge cases."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from folio.config import FolioConfig
from folio.lock import LibraryLockError, library_lock
import folio.provenance as provenance_mod
from folio.pipeline.provenance_analysis import ProvenanceMatch
from folio.pipeline.provenance_data import ExtractedEvidenceItem, compute_claim_hash


def _read_fm(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return {}
    end = content.index("\n---", 4)
    return yaml.safe_load(content[4:end]) or {}


def _setup_registry(library_root: Path, entries: dict[str, dict]) -> None:
    payload = {
        "_schema_version": 1,
        "updated_at": "2026-03-29T00:00:00Z",
        "decks": entries,
    }
    (library_root / "registry.json").write_text(json.dumps(payload), encoding="utf-8")


def _registry_entry(note_id: str, markdown_path: str, *, title: str | None = None) -> dict:
    return {
        "id": note_id,
        "title": title or note_id,
        "type": "evidence",
        "markdown_path": markdown_path,
        "deck_dir": str(Path(markdown_path).parent).replace("\\", "/"),
        "source_relative_path": "deck.pptx",
        "source_hash": f"{note_id}-hash",
        "version": 1,
        "converted": "2026-03-29T00:00:00Z",
        "client": "ClientA",
        "engagement": "DD_Q1",
    }


def _make_evidence_note(
    *,
    note_id: str,
    title: str,
    evidence_items: list[tuple[str, str]],
    supersedes: str | None = None,
    provenance_meta: dict | None = None,
    provenance_links: list[dict] | None = None,
    curation_level: str = "L0",
    review_status: str = "clean",
    include_curation_level: bool = True,
    evidence_format: str = "yaml",
) -> str:
    fm: dict = {
        "id": note_id,
        "title": title,
        "type": "evidence",
        "status": "active",
        "review_status": review_status,
        "review_flags": [],
        "client": "ClientA",
        "engagement": "DD_Q1",
        "source": "deck.pptx",
        "source_hash": f"{note_id}-hash",
        "version": 1,
        "created": "2026-03-29T00:00:00Z",
        "modified": "2026-03-29T00:00:00Z",
    }
    if include_curation_level:
        fm["curation_level"] = curation_level
    if supersedes:
        fm["supersedes"] = supersedes
    if provenance_links:
        fm["provenance_links"] = provenance_links
    if provenance_meta:
        fm["_llm_metadata"] = {"provenance": provenance_meta}

    if evidence_format == "markdown":
        evidence_block = "\n".join(
            [
                f'- **{claim_text} (high):** "{quote_text}" *(metric)*'
                for claim_text, quote_text in evidence_items
            ]
        )
    else:
        evidence_block = "\n".join(
            [
                (
                    f"- claim: {claim_text}\n"
                    f'  - quote: "{quote_text}"\n'
                    "  - confidence: high\n"
                    "  - validated: yes"
                )
                for claim_text, quote_text in evidence_items
            ]
        )
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"""\
---
{yaml_str}---

# {title}

**Source:** `deck.pptx`

---

## Slide 1

![Slide 1](slides/slide-001.png)

### Text (Verbatim)

> Raw text.

### Analysis

**Slide Type:** data
**Framework:** none
**Visual Description:** A simple chart.
**Key Data:** {evidence_items[0][0]}
**Main Insight:** {evidence_items[0][0]}

**Evidence:**
{evidence_block}

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2026-03-29 | Initial |
"""


def _write_note(library_root: Path, rel_path: str, content: str) -> Path:
    path = library_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_config(library_root: Path) -> FolioConfig:
    return FolioConfig(library_root=library_root)


def _proposal_dict(
    *,
    proposal_id: str,
    target_doc: str,
    source_item: ExtractedEvidenceItem,
    target_item: ExtractedEvidenceItem,
    basis_fingerprint: str = "sha256:basis",
    confidence: str = "high",
) -> dict:
    return {
        "proposal_id": proposal_id,
        "source_claim": {
            "slide_number": source_item.slide_number,
            "claim_index": source_item.claim_index,
            "claim_text": source_item.claim_text,
            "supporting_quote": source_item.supporting_quote,
            "claim_hash": source_item.claim_hash,
        },
        "target_evidence": {
            "target_doc": target_doc,
            "slide_number": target_item.slide_number,
            "claim_index": target_item.claim_index,
            "claim_text": target_item.claim_text,
            "supporting_quote": target_item.supporting_quote,
            "claim_hash": target_item.claim_hash,
        },
        "confidence": confidence,
        "rationale": "same metric",
        "basis_fingerprint": basis_fingerprint,
        "model": "anthropic/test-model",
        "timestamp_proposed": "2026-03-29T00:00:00Z",
        "lifecycle_state": "queued",
    }


def _link_dict(
    *,
    link_id: str,
    target_doc: str,
    source_item: ExtractedEvidenceItem,
    target_item: ExtractedEvidenceItem,
    source_hash: str | None = None,
    target_hash: str | None = None,
    link_status: str = "confirmed",
    acknowledged_source_hash: str | None = None,
    acknowledged_target_hash: str | None = None,
) -> dict:
    link = {
        "link_id": link_id,
        "source_slide": source_item.slide_number,
        "source_claim_index": source_item.claim_index,
        "source_claim_hash": source_hash or source_item.claim_hash,
        "source_claim_text_snapshot": source_item.claim_text,
        "source_supporting_quote_snapshot": source_item.supporting_quote,
        "target_doc": target_doc,
        "target_slide": target_item.slide_number,
        "target_claim_index": target_item.claim_index,
        "target_claim_hash": target_hash or target_item.claim_hash,
        "target_claim_text_snapshot": target_item.claim_text,
        "target_supporting_quote_snapshot": target_item.supporting_quote,
        "confidence": "high",
        "confirmed_at": "2026-03-29T00:00:00Z",
        "link_status": link_status,
    }
    if acknowledged_source_hash is not None:
        link["acknowledged_at_claim_hash"] = acknowledged_source_hash
    if acknowledged_target_hash is not None:
        link["acknowledged_at_target_hash"] = acknowledged_target_hash
    return link


def test_extract_evidence_items_handles_multiple_slides_and_malformed_blocks():
    content = """\
## Slide 1

**Evidence:**
- claim: Revenue growth is 15% YoY
  - quote: "Revenue grew 15% YoY."
  - confidence: high
  - validated: yes
not a field
- claim: Margin expansion continues
  - confidence: medium

## Slide 2

**Evidence:**
- claim: Cost savings total $10M
  - quote: "Savings reached $10M."
"""

    items = provenance_mod.extract_evidence_items(content)

    assert [(item.slide_number, item.claim_index) for item in items] == [(1, 0), (1, 1), (2, 0)]
    assert items[0].claim_hash == compute_claim_hash("Revenue growth is 15% YoY", "Revenue grew 15% YoY.")
    assert items[1].supporting_quote == ""


def test_extract_evidence_items_parses_production_markdown_format():
    content = """\
## Slide 1

**Evidence:**
- **Revenue growth is 15% YoY (high, pass 2):** "Revenue grew 15% YoY." *(metric)*
- **Margin expanded 300 bps (medium):** "Margins improved by 300 bps." *(body)* [unverified]
"""

    items = provenance_mod.extract_evidence_items(content)

    assert [(item.slide_number, item.claim_index) for item in items] == [(1, 0), (1, 1)]
    assert items[0].claim_text == "Revenue growth is 15% YoY"
    assert items[0].supporting_quote == "Revenue grew 15% YoY."
    assert items[0].original_confidence == "high"
    assert items[0].element_type == "metric"
    assert items[1].original_confidence == "medium"
    assert items[1].element_type == "body"


def test_suppress_rejections_respects_basis_and_clear_rejections():
    source_item = ExtractedEvidenceItem(
        claim_text="Revenue growth is 15% YoY",
        supporting_quote="Revenue grew 15% YoY.",
        original_confidence="high",
        element_type="metric",
        slide_number=1,
        claim_index=0,
        claim_hash=compute_claim_hash("Revenue growth is 15% YoY", "Revenue grew 15% YoY."),
    )
    target_item = ExtractedEvidenceItem(
        claim_text="Revenue grew 15% YoY",
        supporting_quote="Revenue grew 15% YoY.",
        original_confidence="high",
        element_type="metric",
        slide_number=1,
        claim_index=0,
        claim_hash=compute_claim_hash("Revenue grew 15% YoY", "Revenue grew 15% YoY."),
    )
    rejected = provenance_mod.ProvenanceProposal.from_dict(
        {
            **_proposal_dict(
                proposal_id="prov-old",
                target_doc="source_v1",
                source_item=source_item,
                target_item=target_item,
                basis_fingerprint="sha256:same",
            ),
            "lifecycle_state": "rejected",
        }
    )
    same_basis = provenance_mod.ProvenanceProposal.from_dict(
        _proposal_dict(
            proposal_id="prov-same",
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
            basis_fingerprint="sha256:same",
        )
    )
    changed_basis = provenance_mod.ProvenanceProposal.from_dict(
        _proposal_dict(
            proposal_id="prov-new",
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
            basis_fingerprint="sha256:new",
        )
    )
    pair_meta = {"proposals": [rejected.to_dict()]}

    kept = provenance_mod._suppress_rejections([same_basis, changed_basis], pair_meta, clear_rejections=False)
    assert [proposal.proposal_id for proposal in kept] == ["prov-new"]

    cleared = provenance_mod._suppress_rejections([same_basis, changed_basis], pair_meta, clear_rejections=True)
    assert [proposal.proposal_id for proposal in cleared] == ["prov-same", "prov-new"]


def test_surface_link_state_and_dedupe_behaviors():
    source_item = ExtractedEvidenceItem(
        claim_text="Revenue growth is 15% YoY",
        supporting_quote="Revenue grew 15% YoY.",
        original_confidence="high",
        element_type="metric",
        slide_number=1,
        claim_index=0,
        claim_hash=compute_claim_hash("Revenue growth is 15% YoY", "Revenue grew 15% YoY."),
    )
    target_item = ExtractedEvidenceItem(
        claim_text="Revenue grew 15% YoY",
        supporting_quote="Revenue grew 15% YoY.",
        original_confidence="high",
        element_type="metric",
        slide_number=1,
        claim_index=0,
        claim_hash=compute_claim_hash("Revenue grew 15% YoY", "Revenue grew 15% YoY."),
    )
    proposal = provenance_mod.ProvenanceProposal.from_dict(
        _proposal_dict(
            proposal_id="prov-keep",
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
        )
    )

    fresh_link = _link_dict(
        link_id="plink-fresh",
        target_doc="source_v1",
        source_item=source_item,
        target_item=target_item,
    )
    stale_link = _link_dict(
        link_id="plink-stale",
        target_doc="source_v1",
        source_item=source_item,
        target_item=target_item,
        source_hash="sha256:old",
    )
    acknowledged_link = _link_dict(
        link_id="plink-ack",
        target_doc="source_v1",
        source_item=source_item,
        target_item=target_item,
        source_hash="sha256:old",
        target_hash="sha256:old",
        link_status="acknowledged_stale",
        acknowledged_source_hash=source_item.claim_hash,
        acknowledged_target_hash=target_item.claim_hash,
    )
    repair_pending_link = _link_dict(
        link_id="plink-repair",
        target_doc="source_v1",
        source_item=source_item,
        target_item=target_item,
        link_status="re_evaluate_pending",
    )

    assert provenance_mod._surface_link_state(fresh_link, [source_item], [target_item], {}) == ("fresh", False)
    assert provenance_mod._surface_link_state(stale_link, [source_item], [target_item], {}) == ("stale", False)
    assert provenance_mod._surface_link_state(acknowledged_link, [source_item], [target_item], {}) == (
        "acknowledged",
        False,
    )
    assert provenance_mod._surface_link_state(repair_pending_link, [source_item], [target_item], {}) == (
        "re_evaluate_pending",
        False,
    )
    assert provenance_mod._surface_link_state(
        repair_pending_link,
        [source_item],
        [target_item],
        {"repair_error": "llm_error"},
    ) == ("repair_blocked", False)
    assert provenance_mod._surface_link_state(fresh_link, [source_item], [], {}) == ("stale", True)

    assert provenance_mod._dedupe_against_confirmed([proposal], [fresh_link], [source_item], [target_item], {}) == []
    assert provenance_mod._dedupe_against_confirmed([proposal], [stale_link], [source_item], [target_item], {}) == [
        proposal
    ]
    assert provenance_mod._dedupe_against_confirmed(
        [proposal],
        [acknowledged_link],
        [source_item],
        [target_item],
        {},
    ) == []
    assert provenance_mod._dedupe_against_confirmed(
        [proposal],
        [repair_pending_link],
        [source_item],
        [target_item],
        {},
    ) == [proposal]


def test_build_shards_claim_overflow_is_deterministic():
    source_items = [
        ExtractedEvidenceItem(
            claim_text=f"Claim {index}",
            supporting_quote="growth " * 1000,
            original_confidence="high",
            element_type="metric",
            slide_number=1,
            claim_index=index,
            claim_hash=compute_claim_hash(f"Claim {index}", "growth " * 1000),
        )
        for index in range(4)
    ]
    target_items = [
        ExtractedEvidenceItem(
            claim_text="Target claim",
            supporting_quote="support " * 100,
            original_confidence="high",
            element_type="metric",
            slide_number=1,
            claim_index=0,
            claim_hash=compute_claim_hash("Target claim", "support " * 100),
        )
    ]

    first, _ = provenance_mod._build_shards(source_items, target_items, 2600)
    second, _ = provenance_mod._build_shards(source_items, target_items, 2600)

    assert len(first) > 1
    assert [
        ([item.claim_index for item in claim_chunk], [item.claim_index for item in target_chunk])
        for claim_chunk, target_chunk in first
    ] == [
        ([item.claim_index for item in claim_chunk], [item.claim_index for item in target_chunk])
        for claim_chunk, target_chunk in second
    ]


def test_build_shards_can_exceed_pair_ceiling():
    source_items = [
        ExtractedEvidenceItem(
            claim_text=f"Claim {index}",
            supporting_quote="growth " * 1500,
            original_confidence="high",
            element_type="metric",
            slide_number=1,
            claim_index=index,
            claim_hash=compute_claim_hash(f"Claim {index}", "growth " * 1500),
        )
        for index in range(9)
    ]
    target_items = [
        ExtractedEvidenceItem(
            claim_text="Target claim",
            supporting_quote="support " * 50,
            original_confidence="high",
            element_type="metric",
            slide_number=1,
            claim_index=0,
            claim_hash=compute_claim_hash("Target claim", "support " * 50),
        )
    ]

    shards, _ = provenance_mod._build_shards(source_items, target_items, 2600)
    assert len(shards) > provenance_mod.PAIR_SHARD_CEILING


def test_confirm_range_reversed_endpoints_confirms_inclusive_range(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_note = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            evidence_items=[
                ("Claim 1", "Quote 1"),
                ("Claim 2", "Quote 2"),
            ],
            provenance_meta={
                "pairs": {
                    "source_v1": {
                        "proposals": [],
                    }
                }
            },
        ),
    )
    _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[
                ("Target 1", "Quote A"),
                ("Target 2", "Quote B"),
            ],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    source_items = provenance_mod.extract_evidence_items(source_note.read_text(encoding="utf-8"))
    target_items = provenance_mod.extract_evidence_items((library / "ClientA/source_v1.md").read_text(encoding="utf-8"))
    fm = _read_fm(source_note)
    pair_meta = fm["_llm_metadata"]["provenance"]["pairs"]["source_v1"]
    pair_meta["proposals"] = [
        _proposal_dict(
            proposal_id="prov-000000000001",
            target_doc="source_v1",
            source_item=source_items[0],
            target_item=target_items[0],
        ),
        _proposal_dict(
            proposal_id="prov-000000000002",
            target_doc="source_v1",
            source_item=source_items[1],
            target_item=target_items[1],
        ),
    ]
    source_note.write_text(provenance_mod._replace_frontmatter(source_note.read_text(encoding="utf-8"), fm), encoding="utf-8")

    count = provenance_mod.confirm_range(config, "prov-000000000002..prov-000000000001")

    assert count == 2
    fm = _read_fm(source_note)
    assert len(fm["provenance_links"]) == 2
    assert fm["_llm_metadata"]["provenance"]["pairs"]["source_v1"]["proposals"] == []


def test_confirm_range_missing_endpoint_errors(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_note = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            evidence_items=[("Claim 1", "Quote 1")],
            provenance_meta={
                "pairs": {
                    "source_v1": {
                        "proposals": [
                            {
                                "proposal_id": "prov-000000000001",
                                "source_claim": {
                                    "slide_number": 1,
                                    "claim_index": 0,
                                    "claim_text": "Claim 1",
                                    "supporting_quote": "Quote 1",
                                    "claim_hash": compute_claim_hash("Claim 1", "Quote 1"),
                                },
                                "target_evidence": {
                                    "target_doc": "source_v1",
                                    "slide_number": 1,
                                    "claim_index": 0,
                                    "claim_text": "Target 1",
                                    "supporting_quote": "Quote A",
                                    "claim_hash": compute_claim_hash("Target 1", "Quote A"),
                                },
                                "confidence": "high",
                                "rationale": "same metric",
                                "basis_fingerprint": "sha256:basis",
                                "model": "anthropic/test-model",
                                "timestamp_proposed": "2026-03-29T00:00:00Z",
                                "lifecycle_state": "queued",
                            }
                        ],
                    }
                }
            },
        ),
    )
    _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    with pytest.raises(ValueError, match="Range endpoints not found"):
        provenance_mod.confirm_range(config, "prov-000000000001..prov-missing")


def test_stale_refresh_hashes_and_acknowledge_remove(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            evidence_items=[("Claim 1", "Quote 1")],
        ),
    )
    target_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    source_item = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))[0]
    target_item = provenance_mod.extract_evidence_items(target_path.read_text(encoding="utf-8"))[0]
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        _link_dict(
            link_id="plink-000000000001",
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
            source_hash="sha256:old-source",
            target_hash="sha256:old-target",
        )
    ]
    source_path.write_text(provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm), encoding="utf-8")

    provenance_mod.stale_refresh_hashes(config, "plink-000000000001")
    fm = _read_fm(source_path)
    link = fm["provenance_links"][0]
    refreshed_link_id = link["link_id"]
    assert link["source_claim_hash"] == source_item.claim_hash
    assert link["target_claim_hash"] == target_item.claim_hash
    assert link["link_status"] == "confirmed"

    source_path.write_text(
        source_path.read_text(encoding="utf-8").replace(
            "- claim: Claim 1",
            "- claim: Claim 1 updated",
            1,
        ),
        encoding="utf-8",
    )
    provenance_mod.stale_acknowledge(config, refreshed_link_id)
    fm = _read_fm(source_path)
    link = fm["provenance_links"][0]
    assert link["link_status"] == "acknowledged_stale"
    assert "acknowledged_at_claim_hash" in link

    provenance_mod.stale_remove(config, refreshed_link_id)
    fm = _read_fm(source_path)
    assert fm["provenance_links"] == []


def test_stale_doc_actions_acknowledge_then_remove_all(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            evidence_items=[("Claim 1", "Quote 1"), ("Claim 2", "Quote 2")],
        ),
    )
    target_one_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A"), ("Target 2", "Quote B")],
        ),
    )
    target_two_path = _write_note(
        library,
        "ClientA/source_v0.md",
        _make_evidence_note(
            note_id="source_v0",
            title="Source V0",
            evidence_items=[("Legacy 1", "Quote Z")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
            "source_v0": _registry_entry("source_v0", "ClientA/source_v0.md"),
        },
    )

    source_items = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))
    target_one_items = provenance_mod.extract_evidence_items(target_one_path.read_text(encoding="utf-8"))
    target_two_items = provenance_mod.extract_evidence_items(target_two_path.read_text(encoding="utf-8"))
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        _link_dict(
            link_id="plink-000000000010",
            target_doc="source_v1",
            source_item=source_items[0],
            target_item=target_one_items[0],
            source_hash="sha256:old-source-1",
            target_hash="sha256:old-target-1",
        ),
        _link_dict(
            link_id="plink-000000000011",
            target_doc="source_v0",
            source_item=source_items[1],
            target_item=target_two_items[0],
            source_hash="sha256:old-source-2",
            target_hash="sha256:old-target-2",
        ),
    ]
    source_path.write_text(provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm), encoding="utf-8")

    count = provenance_mod.stale_acknowledge_doc(config, "source_v2")
    assert count == 2
    fm = _read_fm(source_path)
    assert [link["link_status"] for link in fm["provenance_links"]] == [
        "acknowledged_stale",
        "acknowledged_stale",
    ]

    count = provenance_mod.stale_remove_doc(config, "source_v2")
    assert count == 2
    fm = _read_fm(source_path)
    assert fm["provenance_links"] == []


def test_protection_gate_skips_evaluation_but_surfaces_stale_links(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            curation_level="L1",
            review_status="reviewed",
            evidence_items=[("Claim 1", "Quote 1")],
        ),
    )
    target_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    source_item = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))[0]
    target_item = provenance_mod.extract_evidence_items(target_path.read_text(encoding="utf-8"))[0]
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        _link_dict(
            link_id="plink-000000000100",
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
            source_hash="sha256:stale-source",
            target_hash="sha256:stale-target",
        )
    ]
    source_path.write_text(provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm), encoding="utf-8")

    with patch("folio.provenance.evaluate_provenance_matches", side_effect=AssertionError("LLM should not run")):
        result = provenance_mod.provenance_batch(config)

    rows = provenance_mod.provenance_status_summary(config)

    assert result.protected == 1
    assert rows[0]["stale"] == 1
    assert rows[0]["blocked"] == 0


def test_missing_curation_level_is_treated_as_l0_and_analyzed(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            include_curation_level=False,
            evidence_items=[("Claim 1", "Quote 1")],
        ),
    )
    _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    with patch(
        "folio.provenance.evaluate_provenance_matches",
        return_value=[ProvenanceMatch(claim_ref="C1", target_ref="T1", confidence="high", rationale="same metric")],
    ):
        result = provenance_mod.provenance_batch(config)

    fm = _read_fm(source_path)
    assert result.protected == 0
    assert result.proposed == 1
    assert fm["_llm_metadata"]["provenance"]["pairs"]["source_v1"]["status"] == "proposed"


def test_confirm_proposal_clears_ack_fields_on_reconfirm(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            evidence_items=[("Claim 1", "Quote 1")],
        ),
    )
    target_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    source_item = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))[0]
    target_item = provenance_mod.extract_evidence_items(target_path.read_text(encoding="utf-8"))[0]
    link_id = provenance_mod._link_id("source_v2", 1, 0, "source_v1", 1, 0)
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        _link_dict(
            link_id=link_id,
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
            link_status="acknowledged_stale",
            acknowledged_source_hash=source_item.claim_hash,
            acknowledged_target_hash=target_item.claim_hash,
        )
    ]
    fm["_llm_metadata"] = {
        "provenance": {
            "pairs": {
                "source_v1": {
                    "proposals": [
                        _proposal_dict(
                            proposal_id="prov-000000000123",
                            target_doc="source_v1",
                            source_item=source_item,
                            target_item=target_item,
                        )
                    ]
                }
            }
        }
    }
    source_path.write_text(
        provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm),
        encoding="utf-8",
    )

    provenance_mod.confirm_proposal(config, "prov-000000000123")

    link = _read_fm(source_path)["provenance_links"][0]
    assert link["link_status"] == "confirmed"
    assert "acknowledged_at_claim_hash" not in link
    assert "acknowledged_at_target_hash" not in link


def test_repair_link_without_pair_marker_self_heals_to_new_proposal(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            evidence_items=[("Claim 1", "Quote 1")],
        ),
    )
    target_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    source_item = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))[0]
    target_item = provenance_mod.extract_evidence_items(target_path.read_text(encoding="utf-8"))[0]
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        _link_dict(
            link_id="plink-000000000555",
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
            link_status="re_evaluate_pending",
        )
    ]
    source_path.write_text(
        provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm),
        encoding="utf-8",
    )

    with patch(
        "folio.provenance.evaluate_provenance_matches",
        return_value=[ProvenanceMatch(claim_ref="C1", target_ref="T1", confidence="high", rationale="same metric")],
    ):
        result = provenance_mod.provenance_batch(config)

    pair = _read_fm(source_path)["_llm_metadata"]["provenance"]["pairs"]["source_v1"]
    assert result.proposed == 1
    assert pair["proposals"][0]["replaces_link_id"] == "plink-000000000555"


def test_stale_pair_marker_without_pending_link_self_clears(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            provenance_meta={
                "pairs": {
                    "source_v1": {
                        "pair_fingerprint": "sha256:will-be-reset",
                        "re_evaluate_requested": True,
                        "repair_error": "llm_error",
                        "repair_error_detail": "old",
                        "proposals": [],
                    }
                }
            },
            evidence_items=[("Claim 1", "Quote 1")],
        ),
    )
    _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )
    source_items = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))
    target_items = provenance_mod.extract_evidence_items((library / "ClientA/source_v1.md").read_text(encoding="utf-8"))
    fm = _read_fm(source_path)
    fm["_llm_metadata"]["provenance"]["pairs"]["source_v1"]["pair_fingerprint"] = provenance_mod._pair_fingerprint(
        source_items,
        target_items,
        "default",
    )
    source_path.write_text(
        provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm),
        encoding="utf-8",
    )

    with patch("folio.provenance.evaluate_provenance_matches", side_effect=AssertionError("LLM should not run")):
        result = provenance_mod.provenance_batch(config)

    pair = _read_fm(source_path)["_llm_metadata"]["provenance"]["pairs"]["source_v1"]
    assert result.unchanged == 1
    assert pair["re_evaluate_requested"] is False
    assert pair["repair_error"] is None
    assert pair["repair_error_detail"] is None


def test_refresh_hashes_clears_pair_repair_metadata_but_keeps_link(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            provenance_meta={
                "pairs": {
                    "source_v1": {
                        "re_evaluate_requested": True,
                        "repair_error": "llm_error",
                        "repair_error_detail": "timeout",
                        "repair_attempts": 2,
                        "proposals": [],
                    }
                }
            },
            evidence_items=[("Claim 1", "Quote 1 updated")],
        ),
    )
    target_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    source_item = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))[0]
    target_item = provenance_mod.extract_evidence_items(target_path.read_text(encoding="utf-8"))[0]
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        _link_dict(
            link_id="plink-000000000777",
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
            source_hash="sha256:old-source",
            target_hash="sha256:old-target",
            link_status="re_evaluate_pending",
        )
    ]
    source_path.write_text(
        provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm),
        encoding="utf-8",
    )

    provenance_mod.stale_refresh_hashes(config, "plink-000000000777")

    fm = _read_fm(source_path)
    pair = fm["_llm_metadata"]["provenance"]["pairs"]["source_v1"]
    assert fm["provenance_links"][0]["link_status"] == "confirmed"
    assert pair["re_evaluate_requested"] is False
    assert pair["repair_error"] is None
    assert pair["repair_error_detail"] is None
    assert "repair_attempts" not in pair


def test_serialize_proposals_matches_repairs_by_full_coordinates():
    source_item = ExtractedEvidenceItem(
        claim_text="Claim 1",
        supporting_quote="Quote 1",
        original_confidence="high",
        element_type="metric",
        slide_number=1,
        claim_index=0,
        claim_hash=compute_claim_hash("Claim 1", "Quote 1"),
    )
    target_one = ExtractedEvidenceItem(
        claim_text="Target 1",
        supporting_quote="Quote A",
        original_confidence="high",
        element_type="metric",
        slide_number=1,
        claim_index=0,
        claim_hash=compute_claim_hash("Target 1", "Quote A"),
    )
    target_two = ExtractedEvidenceItem(
        claim_text="Target 2",
        supporting_quote="Quote B",
        original_confidence="high",
        element_type="metric",
        slide_number=1,
        claim_index=1,
        claim_hash=compute_claim_hash("Target 2", "Quote B"),
    )

    proposals = provenance_mod._serialize_proposals(
        source_id="source_v2",
        target_id="source_v1",
        matches=[ProvenanceMatch(claim_ref="C1", target_ref="T2", confidence="high", rationale="same metric")],
        claims_lookup={"C1": source_item},
        target_lookup={"T1": target_one, "T2": target_two},
        profile_name="default",
        provider_name="anthropic",
        model="test-model",
        repair_links=[
            _link_dict(
                link_id="plink-000000000901",
                target_doc="source_v1",
                source_item=source_item,
                target_item=target_one,
                link_status="re_evaluate_pending",
            ),
            _link_dict(
                link_id="plink-000000000902",
                target_doc="source_v1",
                source_item=source_item,
                target_item=target_two,
                link_status="re_evaluate_pending",
            ),
        ],
    )

    assert proposals[0].replaces_link_id == "plink-000000000902"


def test_repair_retry_limit_blocks_further_reruns(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config = _make_config(library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            supersedes="source_v1",
            provenance_meta={
                "pairs": {
                    "source_v1": {
                        "repair_attempts": provenance_mod.REPAIR_RETRY_LIMIT,
                        "proposals": [],
                    }
                }
            },
            evidence_items=[("Claim 1", "Quote 1")],
        ),
    )
    target_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            evidence_items=[("Target 1", "Quote A")],
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md"),
        },
    )

    source_item = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))[0]
    target_item = provenance_mod.extract_evidence_items(target_path.read_text(encoding="utf-8"))[0]
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        _link_dict(
            link_id="plink-000000000999",
            target_doc="source_v1",
            source_item=source_item,
            target_item=target_item,
            link_status="re_evaluate_pending",
        )
    ]
    source_path.write_text(
        provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm),
        encoding="utf-8",
    )

    with patch("folio.provenance.evaluate_provenance_matches", side_effect=AssertionError("LLM should not run")):
        result = provenance_mod.provenance_batch(config)

    pair = _read_fm(source_path)["_llm_metadata"]["provenance"]["pairs"]["source_v1"]
    assert result.blocked == 1
    assert pair["repair_error"] == "repair_retry_limit_exceeded"


def test_library_lock_recent_live_lock_blocks_and_old_timestamp_is_stale(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    lock_path = library / ".folio.lock"
    recent = datetime.now(timezone.utc).isoformat()
    lock_path.write_text(
        json.dumps({"pid": os.getpid(), "command": "enrich", "timestamp": recent}),
        encoding="utf-8",
    )

    with pytest.raises(LibraryLockError, match="library lock already held"):
        with library_lock(library, "provenance"):
            pass

    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    lock_path.write_text(
        json.dumps({"pid": os.getpid(), "command": "enrich", "timestamp": old}),
        encoding="utf-8",
    )

    with library_lock(library, "provenance"):
        assert lock_path.exists()
    assert not lock_path.exists()
