"""Focused tests for PR D CLI wiring and provenance passthrough."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from folio.cli import _extract_enrich_passthrough, _mark_enrich_stale, cli
from folio.output.frontmatter import generate
from folio.pipeline.provenance_analysis import ProvenanceMatch
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
) -> str:
    fm: dict = {
        "id": note_id,
        "title": title,
        "type": "evidence",
        "status": "active",
        "curation_level": "L0",
        "review_status": "clean",
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
    assert proposal_id.startswith("prov-")

    confirm = runner.invoke(cli, ["--config", str(config_path), "provenance", "confirm", proposal_id])
    assert confirm.exit_code == 0, confirm.output
    fm = _read_fm(source_path)
    assert fm["provenance_links"][0]["link_id"].startswith("plink-")
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
    (library / ".folio.lock").write_text(
        json.dumps({"pid": os.getpid(), "command": "enrich", "timestamp": "2026-03-29T00:00:00Z"}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "provenance"])
    assert result.exit_code != 0
    assert "library lock already held" in result.output
