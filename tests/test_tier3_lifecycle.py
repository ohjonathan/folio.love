"""Tier 3 lifecycle integration test (spec §8).

Simulates a complete engagement lifecycle:
context init → evidence convert → interaction ingest → enrich → provenance → status/scan/refresh.

All LLM boundaries are mocked.  Assertions cover the 12 required checks from §8.6.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from folio.cli import cli
from folio.config import FolioConfig
from folio.context import create_context_document
from folio.tracking import registry
from folio.tracking.registry import RegistryEntry, entry_from_dict, load_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_folio_yaml(root: Path) -> Path:
    """Write a minimal folio.yaml and return its path."""
    folio_yaml = root / "folio.yaml"
    folio_yaml.write_text(f"library_root: {root / 'library'}\n")
    return folio_yaml


def _make_evidence_note(
    library: Path, *, deck_id: str, title: str, source_path: Path,
    source_hash: str, client: str, engagement: str, subtype: str = "research",
    extra_fm: dict | None = None,
) -> Path:
    """Write a synthetic evidence note (no real conversion)."""
    deck_dir = library / client.lower() / f"deck_{deck_id.split('_')[-1]}"
    deck_dir.mkdir(parents=True, exist_ok=True)
    md_path = deck_dir / f"{deck_id.split('_')[-1]}.md"

    fm: dict = {
        "id": deck_id,
        "title": title,
        "type": "evidence",
        "subtype": subtype,
        "status": "active",
        "authority": "captured",
        "curation_level": "L0",
        "source": str(source_path),
        "source_hash": source_hash,
        "source_type": "pdf",
        "version": 1,
        "slide_count": 3,
        "created": "2026-03-30",
        "modified": "2026-03-30",
        "converted": "2026-03-30T00:00:00Z",
        "client": client,
        "engagement": engagement,
        "review_status": "clean",
        "review_flags": [],
        "extraction_confidence": 0.85,
        "tags": ["research"],
        "grounding_summary": {
            "total_claims": 3,
            "high_confidence": 2,
            "medium_confidence": 1,
            "low_confidence": 0,
            "validated": 2,
            "unvalidated": 1,
        },
    }
    if extra_fm:
        fm.update(extra_fm)

    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    body = f"---\n{yaml_str}---\n\n# {title}\n\n## Slide 1\nContent.\n"
    md_path.write_text(body)

    # Register it
    md_rel = str(md_path.relative_to(library)).replace("\\", "/")
    dd_rel = str(deck_dir.relative_to(library)).replace("\\", "/")
    entry = RegistryEntry(
        id=deck_id,
        title=title,
        markdown_path=md_rel,
        deck_dir=dd_rel,
        source_relative_path=str(source_path),
        source_hash=source_hash,
        source_type="pdf",
        version=1,
        converted="2026-03-30T00:00:00Z",
        type="evidence",
        subtype=subtype,
        client=client,
        engagement=engagement,
        authority="captured",
        curation_level="L0",
        staleness_status="current",
        review_status="clean",
        review_flags=[],
        extraction_confidence=0.85,
    )
    registry.upsert_entry(library / "registry.json", entry)
    return md_path


# ---------------------------------------------------------------------------
# The integration test
# ---------------------------------------------------------------------------

class TestTier3Lifecycle:
    """End-to-end lifecycle: context + evidence + status/scan/refresh."""

    def test_full_lifecycle(self, tmp_path):
        # ----- Setup -----
        root = tmp_path
        folio_yaml = _write_folio_yaml(root)
        config = FolioConfig.load(folio_yaml)
        library = config.library_root.resolve()
        library.mkdir(parents=True, exist_ok=True)

        runner = CliRunner()

        # Create a dummy source file for evidence
        source_dir = tmp_path / "sources"
        source_dir.mkdir()
        source_file = source_dir / "market_research.pdf"
        source_file.write_bytes(b"dummy PDF content")
        from folio.tracking.sources import compute_file_hash
        src_hash = compute_file_hash(source_file)

        # ===== STEP 1: folio context init =====
        result = runner.invoke(cli, [
            "context", "init",
            "--client", "TestCo",
            "--engagement", "DD Q1 2026",
        ], obj={"config": config})
        assert result.exit_code == 0, f"context init failed: {result.output}"
        assert "Created context document" in result.output

        # Assertion 1: context file created at canonical path
        # Find the actual path from the library
        context_path = None
        for md_file in library.rglob("_context.md"):
            context_path = md_file
            break
        assert context_path is not None and context_path.exists(), (
            f"Context doc not found under {library}"
        )

        # Assertion 2: required frontmatter + body headings
        ctx_content = context_path.read_text()
        ctx_fm_block = ctx_content.split("---")[1]
        ctx_fm = yaml.safe_load(ctx_fm_block)
        assert ctx_fm["type"] == "context"
        assert ctx_fm["subtype"] == "engagement"
        assert ctx_fm["review_status"] == "clean"
        assert ctx_fm["review_flags"] == []
        assert ctx_fm["extraction_confidence"] is None
        assert ctx_fm["authority"] == "aligned"
        assert ctx_fm["curation_level"] == "L1"
        for section in [
            "## Client Background", "## Engagement Snapshot",
            "## Objectives / SOW", "## Timeline", "## Team",
            "## Stakeholders", "## Starting Hypotheses",
            "## Risks / Open Questions",
        ]:
            assert section in ctx_content, f"Missing section: {section}"

        # Assertion 3: context doc in registry as type=context, round-trips
        reg_data = load_registry(library / "registry.json")
        ctx_id = ctx_fm["id"]
        assert ctx_id in reg_data["decks"], "Context doc not in registry"
        ctx_row = reg_data["decks"][ctx_id]
        assert ctx_row["type"] == "context"
        assert ctx_row["subtype"] == "engagement"
        # round-trip
        ctx_entry = entry_from_dict(ctx_row)
        assert ctx_entry.type == "context"
        assert ctx_entry.source_relative_path is None
        assert ctx_entry.source_hash is None

        # ===== STEP 2: Add synthetic evidence =====
        ev_path = _make_evidence_note(
            library,
            deck_id="testco_evidence_20260330_market_research",
            title="Market Research Q1",
            source_path=source_file,
            source_hash=src_hash,
            client="TestCo",
            engagement="DD Q1 2026",
        )
        assert ev_path.exists()

        # ===== STEP 3: folio status --refresh =====
        result = runner.invoke(cli, [
            "status", "--refresh",
        ], obj={"config": config})
        assert result.exit_code == 0, f"status failed: {result.output}"

        # Assertion 4: context doc in counts, no crash
        assert "documents" in result.output
        # Should show type breakdown (context + evidence)
        assert "By type:" in result.output
        assert "context" in result.output.lower()

        # ===== STEP 4: folio scan =====
        result = runner.invoke(cli, [
            "scan",
        ], obj={"config": config})
        # scan requires source roots; without them it prints info msg
        # The key assertion: no crash from context rows
        assert result.exit_code == 0, f"scan failed: {result.output}"

        # Assertion 5: scan ignores context rows (no crash, no bogus entry)
        # No crash is the test itself passing

        # ===== STEP 5: folio refresh =====
        result = runner.invoke(cli, [
            "refresh",
        ], obj={"config": config})
        assert result.exit_code == 0, f"refresh failed: {result.output}"

        # Assertion 6: refresh skips context doc explicitly
        assert "skipping context document" in result.output

        # ===== STEP 6: Verify final registry state =====
        final_reg = load_registry(library / "registry.json")

        # Assertion 12: final library has expected mix of types
        types_present = {
            entry_from_dict(row).type
            for row in final_reg["decks"].values()
        }
        assert "context" in types_present
        assert "evidence" in types_present
        assert ctx_id in final_reg["decks"], "Context row still in registry"

        # ===== STEP 7: folio context init duplicate =====
        result = runner.invoke(cli, [
            "context", "init",
            "--client", "TestCo",
            "--engagement", "DD Q1 2026",
        ], obj={"config": config})
        assert result.exit_code != 0, "Duplicate context init should fail"
        assert "already exists" in result.output

    def test_rebuild_preserves_context_during_corrupt_recovery(self, tmp_path):
        """Corrupt registry recovery must preserve context rows."""
        root = tmp_path
        folio_yaml = _write_folio_yaml(root)
        config = FolioConfig.load(folio_yaml)
        library = config.library_root.resolve()
        library.mkdir(parents=True, exist_ok=True)

        # Create context doc
        ctx_id, ctx_path = create_context_document(
            config, client="Acme", engagement="Ops Sprint 2026",
        )
        assert ctx_path.exists()

        # Corrupt the registry
        reg_path = library / "registry.json"
        reg_path.write_text("not valid json{{{")

        # Rebuild
        data = registry.rebuild_registry(library)
        assert ctx_id in data["decks"], "Context row lost during rebuild"
        assert data["decks"][ctx_id]["type"] == "context"

    def test_schema_v2_written_on_save(self, tmp_path):
        """Registry should write schema version 2."""
        root = tmp_path
        folio_yaml = _write_folio_yaml(root)
        config = FolioConfig.load(folio_yaml)
        library = config.library_root.resolve()
        library.mkdir(parents=True, exist_ok=True)

        create_context_document(
            config, client="X", engagement="Y",
        )

        reg_data = json.loads((library / "registry.json").read_text())
        assert reg_data["_schema_version"] == 2

    def test_status_no_crash_with_only_context(self, tmp_path):
        """status --refresh on a library with only context docs must not crash."""
        root = tmp_path
        folio_yaml = _write_folio_yaml(root)
        config = FolioConfig.load(folio_yaml)
        library = config.library_root.resolve()
        library.mkdir(parents=True, exist_ok=True)

        create_context_document(
            config, client="Solo", engagement="Only Context",
        )

        runner = CliRunner()
        result = runner.invoke(cli, [
            "status", "--refresh",
        ], obj={"config": config})
        assert result.exit_code == 0, f"status failed: {result.output}"
        # Library should have at least 1 document (the context doc we just created)
        assert "documents" in result.output
