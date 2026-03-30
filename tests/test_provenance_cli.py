"""Focused tests for PR D CLI wiring and provenance passthrough."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

import folio.provenance as provenance_mod
from folio.cli import _extract_enrich_passthrough, _mark_enrich_stale, cli
from folio.output.frontmatter import generate
from folio.pipeline.provenance_analysis import ProvenanceMatch
from folio.pipeline.provenance_data import ExtractedEvidenceItem, compute_claim_hash
from folio.tracking.versions import ChangeSet, VersionInfo


def _make_config(path: Path, library_root: Path) -> None:
    path.write_text(yaml.dump({"library_root": str(library_root)}, default_flow_style=False))


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
    claim_text: str,
    quote_text: str,
    supersedes: str | None = None,
    provenance_meta: dict | None = None,
    provenance_links: list[dict] | None = None,
    curation_level: str = "L0",
    review_status: str = "clean",
) -> str:
    fm: dict = {
        "id": note_id,
        "title": title,
        "type": "evidence",
        "status": "active",
        "curation_level": curation_level,
        "review_status": review_status,
        "client": "ClientA",
        "engagement": "DD_Q1",
        "source": "deck.pptx",
        "source_hash": f"{note_id}-hash",
        "version": 1,
        "created": "2026-03-29T00:00:00Z",
        "modified": "2026-03-29T00:00:00Z",
    }
    if supersedes:
        fm["supersedes"] = supersedes
    if provenance_links:
        fm["provenance_links"] = provenance_links
    if provenance_meta:
        fm["_llm_metadata"] = {"provenance": provenance_meta}

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
**Key Data:** {claim_text}
**Main Insight:** {claim_text}

**Evidence:**
- claim: {claim_text}
  - quote: "{quote_text}"
  - confidence: high
  - validated: yes

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


def test_provenance_uses_shared_evidence_model_and_normalized_claim_hashes():
    assert provenance_mod.ExtractedEvidenceItem is ExtractedEvidenceItem
    assert compute_claim_hash("Revenue  growth", "Revenue   grew  15%") == compute_claim_hash(
        "Revenue growth",
        "Revenue grew 15%",
    )


def test_build_shards_preserves_original_claim_hash_when_truncating_quotes():
    long_quote = "growth " * 5000
    source_item = ExtractedEvidenceItem(
        slide_number=1,
        claim_index=0,
        claim_text="Revenue growth is 15% YoY",
        supporting_quote=long_quote,
        original_confidence="high",
        element_type="metric",
        claim_hash=compute_claim_hash("Revenue growth is 15% YoY", long_quote),
    )
    target_item = ExtractedEvidenceItem(
        slide_number=1,
        claim_index=0,
        claim_text="Revenue grew 15% YoY",
        supporting_quote=long_quote,
        original_confidence="high",
        element_type="metric",
        claim_hash=compute_claim_hash("Revenue grew 15% YoY", long_quote),
    )

    shards, warnings = provenance_mod._build_shards([source_item], [target_item], 2500)

    assert warnings
    shard_source, shard_target = shards[0]
    assert shard_source[0].supporting_quote != long_quote
    assert shard_target[0].supporting_quote != long_quote
    assert shard_source[0].claim_hash == source_item.claim_hash
    assert shard_target[0].claim_hash == target_item.claim_hash


def test_passthrough_helpers_preserve_provenance_and_mark_pairs_stale():
    fm = {
        "supersedes": "older_note",
        "provenance_links": [{"link_id": "plink-1234", "target_doc": "older_note"}],
        "_llm_metadata": {
            "enrich": {
                "status": "executed",
                "input_fingerprint": "sha256:abc",
                "axes": {"relationships": {"proposals": [{"target_id": "older_note"}]}},
            },
            "provenance": {
                "pairs": {
                    "older_note": {
                        "pair_fingerprint": "sha256:pair",
                        "repair_error": "llm_error",
                        "repair_error_detail": "timeout",
                        "re_evaluate_requested": True,
                        "proposals": [
                            {"proposal_id": "prov-a", "status": "pending_human_confirmation"},
                            {"proposal_id": "prov-b", "status": "rejected"},
                        ],
                    }
                }
            },
        },
    }

    preserved = _extract_enrich_passthrough(fm)
    assert preserved is not None
    _mark_enrich_stale(preserved)

    assert preserved["provenance_links"][0]["link_id"] == "plink-1234"
    enrich = preserved["_llm_metadata"]["enrich"]
    assert enrich["status"] == "stale"
    assert "input_fingerprint" not in enrich

    pair = preserved["_llm_metadata"]["provenance"]["pairs"]["older_note"]
    assert "pair_fingerprint" not in pair
    assert "repair_error" not in pair
    assert "repair_error_detail" not in pair
    assert "re_evaluate_requested" not in pair
    statuses = [proposal["status"] for proposal in pair["proposals"]]
    assert statuses == ["stale_pending", "rejected"]


def test_frontmatter_generate_preserves_provenance_passthrough(tmp_path):
    preserved = {
        "supersedes": "older_note",
        "provenance_links": [{"link_id": "plink-1234", "target_doc": "older_note"}],
        "_llm_metadata": {
            "provenance": {
                "requested_profile": "default",
                "profile": "default",
                "provider": "anthropic",
                "model": "test-model",
                "pairs": {"older_note": {"status": "proposed", "proposals": []}},
            }
        },
    }
    version_info = VersionInfo(
        version=2,
        timestamp="2026-03-29T00:00:00Z",
        source_hash="new-hash",
        source_path="deck.pptx",
        note=None,
        slide_count=1,
        changes=ChangeSet(),
    )
    generated = generate(
        title="Evidence",
        deck_id="evidence_v2",
        source_relative_path="deck.pptx",
        source_hash="new-hash",
        source_type="pptx",
        version_info=version_info,
        analyses={},
        preserved_enrich_fields=preserved,
    )
    parsed = yaml.safe_load(generated.strip().strip("---"))
    assert parsed["supersedes"] == "older_note"
    assert parsed["provenance_links"][0]["link_id"] == "plink-1234"
    assert parsed["_llm_metadata"]["provenance"]["pairs"]["older_note"]["status"] == "proposed"


@patch(
    "folio.provenance.evaluate_provenance_matches",
    return_value=[ProvenanceMatch(claim_ref="C1", target_ref="T1", confidence="high", rationale="same metric")],
)
def test_provenance_cli_run_confirm_and_re_evaluate(mock_match, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
            supersedes="source_v1",
        ),
    )
    target_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md", title="Source V2"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md", title="Source V1"),
        },
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "provenance", "source_v2"])
    assert result.exit_code == 0, result.output
    assert "Provenance complete:" in result.output

    fm = _read_fm(source_path)
    pair = fm["_llm_metadata"]["provenance"]["pairs"]["source_v1"]
    proposals = pair["proposals"]
    assert len(proposals) == 1
    proposal_id = proposals[0]["proposal_id"]
    assert re.fullmatch(r"prov-[0-9a-f]{12}", proposal_id)

    confirm = runner.invoke(cli, ["--config", str(config_path), "provenance", "confirm", proposal_id])
    assert confirm.exit_code == 0, confirm.output
    fm = _read_fm(source_path)
    assert re.fullmatch(r"plink-[0-9a-f]{12}", fm["provenance_links"][0]["link_id"])
    link_id = fm["provenance_links"][0]["link_id"]

    source_path.write_text(
        source_path.read_text(encoding="utf-8").replace(
            "claim: Revenue growth is 15% YoY",
            "claim: Revenue growth is 18% YoY",
            1,
        ),
        encoding="utf-8",
    )
    stale = runner.invoke(cli, ["--config", str(config_path), "provenance", "stale", "re-evaluate", link_id])
    assert stale.exit_code == 0, stale.output
    fm = _read_fm(source_path)
    assert fm["provenance_links"][0]["link_status"] == "re_evaluate_pending"


def test_provenance_cli_respects_existing_lock(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
            supersedes="source_v1",
        ),
    )
    _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md", title="Source V2"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md", title="Source V1"),
        },
    )
    (library / ".folio.lock").write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "command": "enrich",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    with patch(
        "folio.provenance.evaluate_provenance_matches",
        return_value=[ProvenanceMatch(claim_ref="C1", target_ref="T1", confidence="high", rationale="same metric")],
    ):
        result = runner.invoke(cli, ["--config", str(config_path), "provenance", "source_v2"])
    assert result.exit_code != 0
    assert "library lock already held" in result.output


def test_provenance_cli_evaluates_without_holding_lock(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
            supersedes="source_v1",
        ),
    )
    _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md", title="Source V2"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md", title="Source V1"),
        },
    )

    def fake_match(*args, **kwargs):
        assert not (library / ".folio.lock").exists()
        return [ProvenanceMatch(claim_ref="C1", target_ref="T1", confidence="high", rationale="same metric")]

    runner = CliRunner()
    with patch("folio.provenance.evaluate_provenance_matches", side_effect=fake_match):
        result = runner.invoke(cli, ["--config", str(config_path), "provenance", "source_v2"])

    assert result.exit_code == 0, result.output
    fm = _read_fm(source_path)
    assert fm["_llm_metadata"]["provenance"]["pairs"]["source_v1"]["status"] == "proposed"


def test_provenance_cli_skips_when_source_changes_during_evaluation(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
            supersedes="source_v1",
        ),
    )
    _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md", title="Source V2"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md", title="Source V1"),
        },
    )

    def fake_match(*args, **kwargs):
        source_path.write_text(
            source_path.read_text(encoding="utf-8").replace(
                "claim: Revenue growth is 15% YoY",
                "claim: Revenue growth is 18% YoY",
                1,
            ),
            encoding="utf-8",
        )
        return [ProvenanceMatch(claim_ref="C1", target_ref="T1", confidence="high", rationale="same metric")]

    runner = CliRunner()
    with patch("folio.provenance.evaluate_provenance_matches", side_effect=fake_match):
        result = runner.invoke(cli, ["--config", str(config_path), "provenance", "source_v2"])

    assert result.exit_code == 0, result.output
    assert "changed during evaluation; rerun" in result.output

    fm = _read_fm(source_path)
    pair = fm.get("_llm_metadata", {}).get("provenance", {}).get("pairs", {}).get("source_v1", {})
    assert pair.get("proposals", []) == []
    assert "provenance_links" not in fm


def test_provenance_cli_review_and_status_match_spec_output(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
            supersedes="source_v1",
            provenance_meta={
                "pairs": {
                    "source_v1": {
                        "proposals": [
                            {
                                "proposal_id": "prov-000000000321",
                                "source_claim": {
                                    "slide_number": 1,
                                    "claim_index": 0,
                                    "claim_text": "Revenue growth is 15% YoY",
                                    "supporting_quote": "Revenue grew 15% YoY.",
                                    "claim_hash": compute_claim_hash("Revenue growth is 15% YoY", "Revenue grew 15% YoY."),
                                },
                                "target_evidence": {
                                    "target_doc": "source_v1",
                                    "slide_number": 1,
                                    "claim_index": 0,
                                    "claim_text": "Revenue growth is 15% YoY",
                                    "supporting_quote": "Revenue grew 15% YoY.",
                                    "claim_hash": compute_claim_hash("Revenue growth is 15% YoY", "Revenue grew 15% YoY."),
                                },
                                "confidence": "high",
                                "rationale": "Same metric",
                                "basis_fingerprint": "sha256:basis",
                                "model": "anthropic/test-model",
                                "timestamp_proposed": "2026-03-29T00:00:00Z",
                                "status": "pending_human_confirmation",
                                "replaces_link_id": "plink-000000000654",
                            }
                        ]
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
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
        ),
    )
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        {
            "link_id": "plink-000000000654",
            "source_slide": 1,
            "source_claim_index": 0,
            "source_claim_hash": "sha256:stale-source",
            "source_claim_text_snapshot": "Revenue growth is 15% YoY",
            "source_supporting_quote_snapshot": "Revenue grew 15% YoY.",
            "target_doc": "source_v1",
            "target_slide": 1,
            "target_claim_index": 0,
            "target_claim_hash": "sha256:stale-target",
            "target_claim_text_snapshot": "Revenue growth is 15% YoY",
            "target_supporting_quote_snapshot": "Revenue grew 15% YoY.",
            "confidence": "high",
            "confirmed_at": "2026-03-29T00:00:00Z",
            "link_status": "confirmed",
        }
    ]
    source_path.write_text(provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm), encoding="utf-8")
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md", title="Source V2"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md", title="Source V1"),
        },
    )

    runner = CliRunner()
    review = runner.invoke(cli, ["--config", str(config_path), "provenance", "review", "source_v2"])
    assert review.exit_code == 0, review.output
    assert "Rationale: Same metric" in review.output
    assert "Replaces: plink-000000000654" in review.output

    status = runner.invoke(cli, ["--config", str(config_path), "provenance", "status", "source_v2"])
    assert status.exit_code == 0, status.output
    assert "| Source Document |" in status.output
    assert "| source_v2 |" in status.output
    assert "Coverage:" in status.output


def test_provenance_cli_refresh_hashes_shows_snapshot_comparison(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_path = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            claim_text="Revenue growth is 18% YoY",
            quote_text="Revenue grew 18% YoY.",
            supersedes="source_v1",
        ),
    )
    target_path = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md", title="Source V2"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md", title="Source V1"),
        },
    )

    source_item = provenance_mod.extract_evidence_items(source_path.read_text(encoding="utf-8"))[0]
    target_item = provenance_mod.extract_evidence_items(target_path.read_text(encoding="utf-8"))[0]
    fm = _read_fm(source_path)
    fm["provenance_links"] = [
        {
            "link_id": "plink-000000000777",
            "source_slide": 1,
            "source_claim_index": 0,
            "source_claim_hash": "sha256:old-source",
            "source_claim_text_snapshot": "Revenue growth is 15% YoY",
            "source_supporting_quote_snapshot": "Revenue grew 15% YoY.",
            "target_doc": "source_v1",
            "target_slide": 1,
            "target_claim_index": 0,
            "target_claim_hash": "sha256:old-target",
            "target_claim_text_snapshot": target_item.claim_text,
            "target_supporting_quote_snapshot": target_item.supporting_quote,
            "confidence": "high",
            "confirmed_at": "2026-03-29T00:00:00Z",
            "link_status": "confirmed",
        }
    ]
    source_path.write_text(provenance_mod._replace_frontmatter(source_path.read_text(encoding="utf-8"), fm), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(config_path), "provenance", "stale", "refresh-hashes", "plink-000000000777"],
    )
    assert result.exit_code == 0, result.output
    assert "Persisted Claim:" in result.output
    assert "Current Claim:" in result.output
    assert "✓ Refreshed plink-000000000777" in result.output

    refreshed = _read_fm(source_path)["provenance_links"][0]
    assert refreshed["source_claim_hash"] == source_item.claim_hash


def test_provenance_cli_dry_run_respects_limit_and_shows_repair_preview(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_v2 = _write_note(
        library,
        "ClientA/source_v2.md",
        _make_evidence_note(
            note_id="source_v2",
            title="Source V2",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
            supersedes="source_v1",
            curation_level="L1",
        ),
    )
    target_v1 = _write_note(
        library,
        "ClientA/source_v1.md",
        _make_evidence_note(
            note_id="source_v1",
            title="Source V1",
            claim_text="Revenue growth is 15% YoY",
            quote_text="Revenue grew 15% YoY.",
        ),
    )
    _write_note(
        library,
        "ClientA/source_v3.md",
        _make_evidence_note(
            note_id="source_v3",
            title="Source V3",
            claim_text="Margin expanded 300 bps",
            quote_text="Margins improved by 300 bps.",
            supersedes="source_v0",
        ),
    )
    _write_note(
        library,
        "ClientA/source_v0.md",
        _make_evidence_note(
            note_id="source_v0",
            title="Source V0",
            claim_text="Margin expanded 300 bps",
            quote_text="Margins improved by 300 bps.",
        ),
    )
    _setup_registry(
        library,
        {
            "source_v2": _registry_entry("source_v2", "ClientA/source_v2.md", title="Source V2"),
            "source_v1": _registry_entry("source_v1", "ClientA/source_v1.md", title="Source V1"),
            "source_v3": _registry_entry("source_v3", "ClientA/source_v3.md", title="Source V3"),
            "source_v0": _registry_entry("source_v0", "ClientA/source_v0.md", title="Source V0"),
        },
    )

    source_item = provenance_mod.extract_evidence_items(source_v2.read_text(encoding="utf-8"))[0]
    target_item = provenance_mod.extract_evidence_items(target_v1.read_text(encoding="utf-8"))[0]
    fm = _read_fm(source_v2)
    fm["provenance_links"] = [
        {
            "link_id": "plink-000000000888",
            "source_slide": 1,
            "source_claim_index": 0,
            "source_claim_hash": source_item.claim_hash,
            "source_claim_text_snapshot": source_item.claim_text,
            "source_supporting_quote_snapshot": source_item.supporting_quote,
            "target_doc": "source_v1",
            "target_slide": 1,
            "target_claim_index": 0,
            "target_claim_hash": target_item.claim_hash,
            "target_claim_text_snapshot": target_item.claim_text,
            "target_supporting_quote_snapshot": target_item.supporting_quote,
            "confidence": "high",
            "confirmed_at": "2026-03-29T00:00:00Z",
            "link_status": "re_evaluate_pending",
        }
    ]
    source_v2.write_text(provenance_mod._replace_frontmatter(source_v2.read_text(encoding="utf-8"), fm), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(config_path), "provenance", "ClientA", "--dry-run", "--limit", "1"],
    )
    assert result.exit_code == 0, result.output
    assert result.output.count("planned call(s)") == 1
    assert "queued_repair=1" in result.output
    assert "would trigger LLM on protected note [curation_level=L1]" in result.output
