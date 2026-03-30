"""Unit tests for folio.context — context document creation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from folio.context import (
    build_context_id,
    create_context_document,
    resolve_context_path,
)
from folio.tracking import registry
from folio.tracking.registry import RegistryEntry, entry_from_dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_config(library_root: Path):
    """Return a FolioConfig-like object with just library_root."""
    from folio.config import FolioConfig

    folio_yaml = library_root / "folio.yaml"
    folio_yaml.write_text(f"library_root: {library_root}\n")
    return FolioConfig.load(folio_yaml)


# ---------------------------------------------------------------------------
# build_context_id
# ---------------------------------------------------------------------------

class TestBuildContextId:
    def test_basic_pattern(self):
        with patch("folio.context.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 30, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            cid = build_context_id(client="US Bank", engagement="Tech Resilience DD")
        assert "us_bank" in cid
        assert "context" in cid
        assert "20260330" in cid
        assert cid.endswith("_engagement")

    def test_special_chars_sanitized(self):
        with patch("folio.context.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            cid = build_context_id(client="Acme Corp!", engagement="Q1 2026 Sprint")
        # Should not contain special chars
        assert "!" not in cid
        assert cid.startswith("acme_corp")

    def test_engagement_short_derivation(self):
        """Engagement short should use derive_engagement_short logic."""
        with patch("folio.context.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 1, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            cid = build_context_id(client="TestCo", engagement="DD Q1 2026")
        # derive_engagement_short("DD Q1 2026") -> "ddq126"
        assert "ddq126" in cid


# ---------------------------------------------------------------------------
# resolve_context_path
# ---------------------------------------------------------------------------

class TestResolveContextPath:
    def test_default_path(self, tmp_path):
        result = resolve_context_path(
            library_root=tmp_path,
            client="US Bank",
            engagement="Tech Resilience DD",
        )
        assert result.name == "_context.md"
        assert "us_bank" in str(result)
        assert result.is_relative_to(tmp_path)

    def test_target_directory(self, tmp_path):
        target = tmp_path / "custom" / "dir"
        result = resolve_context_path(
            library_root=tmp_path,
            client="X",
            engagement="Y",
            target=target,
        )
        assert result == (target / "_context.md").resolve()

    def test_target_md_file(self, tmp_path):
        target = tmp_path / "custom" / "my_context.md"
        result = resolve_context_path(
            library_root=tmp_path,
            client="X",
            engagement="Y",
            target=target,
        )
        assert result == target.resolve()
        assert result.name == "my_context.md"


# ---------------------------------------------------------------------------
# create_context_document
# ---------------------------------------------------------------------------

class TestCreateContextDocument:
    def test_creates_file_and_registers(self, tmp_path):
        config = _minimal_config(tmp_path)
        context_id, output_path = create_context_document(
            config, client="Acme", engagement="Ops Sprint 2026",
        )

        assert output_path.exists()
        assert output_path.name == "_context.md"

        # Parse frontmatter
        content = output_path.read_text()
        assert "---" in content
        fm_block = content.split("---")[1]
        fm = yaml.safe_load(fm_block)

        assert fm["type"] == "context"
        assert fm["subtype"] == "engagement"
        assert fm["client"] == "Acme"
        assert fm["engagement"] == "Ops Sprint 2026"
        assert fm["authority"] == "aligned"
        assert fm["curation_level"] == "L1"
        assert fm["review_status"] == "clean"
        assert fm["review_flags"] == []
        assert fm["extraction_confidence"] is None

        # Verify body sections
        for section in [
            "## Client Background",
            "## Engagement Snapshot",
            "## Objectives / SOW",
            "## Timeline",
            "## Team",
            "## Stakeholders",
            "## Starting Hypotheses",
            "## Risks / Open Questions",
        ]:
            assert section in content, f"Missing section: {section}"

        # Check registry entry
        reg_path = tmp_path / "registry.json"
        assert reg_path.exists()
        reg_data = json.loads(reg_path.read_text())
        assert context_id in reg_data["decks"]

        row = reg_data["decks"][context_id]
        assert row["type"] == "context"
        assert row["subtype"] == "engagement"
        assert "source_relative_path" not in row  # omitted when None
        assert "source_hash" not in row
        assert "version" not in row

    def test_duplicate_raises_file_exists(self, tmp_path):
        config = _minimal_config(tmp_path)
        create_context_document(config, client="X", engagement="Y")
        with pytest.raises(FileExistsError):
            create_context_document(config, client="X", engagement="Y")

    def test_registry_round_trip(self, tmp_path):
        """Context row survives entry_from_dict round-trip."""
        config = _minimal_config(tmp_path)
        context_id, _ = create_context_document(
            config, client="Test", engagement="Demo Q1 2026",
        )

        reg_data = json.loads((tmp_path / "registry.json").read_text())
        row = reg_data["decks"][context_id]
        entry = entry_from_dict(row)

        assert entry.type == "context"
        assert entry.subtype == "engagement"
        assert entry.source_relative_path is None
        assert entry.source_hash is None
        assert entry.version is None
        assert entry.client == "Test"


# ---------------------------------------------------------------------------
# Registry integration: source-less rows
# ---------------------------------------------------------------------------

class TestRegistrySourcelessRows:
    def test_refresh_file_present(self, tmp_path):
        """Source-less row with existing file should be 'current'."""
        md_path = tmp_path / "test" / "_context.md"
        md_path.parent.mkdir(parents=True)
        md_path.write_text("# test")

        entry = RegistryEntry(
            id="test_ctx",
            title="Test",
            markdown_path="test/_context.md",
            deck_dir="test",
            type="context",
        )
        result = registry.refresh_entry_status(tmp_path, entry)
        assert result.staleness_status == "current"

    def test_refresh_file_missing(self, tmp_path):
        """Source-less row with missing file should be 'missing'."""
        entry = RegistryEntry(
            id="test_ctx",
            title="Test",
            markdown_path="test/_context.md",
            deck_dir="test",
            type="context",
        )
        result = registry.refresh_entry_status(tmp_path, entry)
        assert result.staleness_status == "missing"

    def test_resolve_entry_source_raises(self, tmp_path):
        """Source-less entry should raise ValueError from resolve_entry_source."""
        entry = RegistryEntry(
            id="test_ctx",
            title="Test",
            markdown_path="test/_context.md",
            deck_dir="test",
            type="context",
        )
        with pytest.raises(ValueError, match="source-less"):
            registry.resolve_entry_source(tmp_path, entry)

    def test_rebuild_discovers_context_docs(self, tmp_path):
        """rebuild_registry should discover context docs alongside evidence."""
        # Create a context doc
        ctx_dir = tmp_path / "acme" / "ddq126"
        ctx_dir.mkdir(parents=True)
        (ctx_dir / "_context.md").write_text(
            "---\n"
            "id: acme_ddq126_context_20260330_engagement\n"
            "title: Acme DD Q1 - Context\n"
            "type: context\n"
            "subtype: engagement\n"
            "client: Acme\n"
            "engagement: DD Q1 2026\n"
            "---\n"
            "# Content\n"
        )

        # Create a source-backed evidence doc
        ev_dir = tmp_path / "acme" / "ddq126" / "deck1"
        ev_dir.mkdir(parents=True)
        source_file = ev_dir / "source.pdf"
        source_file.write_bytes(b"dummy pdf")
        from folio.tracking.sources import compute_file_hash

        src_hash = compute_file_hash(source_file)
        (ev_dir / "deck1.md").write_text(
            "---\n"
            "id: acme_evidence_20260330_deck1\n"
            "title: Deck 1\n"
            "type: evidence\n"
            f"source: {source_file.name}\n"
            f"source_hash: {src_hash}\n"
            "---\n"
            "# Content\n"
        )

        data = registry.rebuild_registry(tmp_path)
        assert "acme_ddq126_context_20260330_engagement" in data["decks"]
        assert "acme_evidence_20260330_deck1" in data["decks"]

        # Context row should have no source fields
        ctx_row = data["decks"]["acme_ddq126_context_20260330_engagement"]
        assert ctx_row["type"] == "context"
        assert "source_relative_path" not in ctx_row
        assert "source_hash" not in ctx_row

    def test_entry_from_dict_schema_v1_evidence(self):
        """Schema v1 evidence rows still load correctly."""
        v1_row = {
            "id": "test_evidence",
            "title": "Test",
            "markdown_path": "test/deck.md",
            "deck_dir": "test",
            "source_relative_path": "../source.pdf",
            "source_hash": "abc123",
            "version": 2,
            "converted": "2026-03-30T00:00:00Z",
            "type": "evidence",
        }
        entry = entry_from_dict(v1_row)
        assert entry.source_relative_path == "../source.pdf"
        assert entry.source_hash == "abc123"
        assert entry.version == 2
        assert entry.subtype is None  # v1 rows don't have subtype


# ---------------------------------------------------------------------------
# Validation tooling
# ---------------------------------------------------------------------------

class TestContextValidation:
    def test_valid_context_passes(self, tmp_path):
        """A properly formed context doc should pass validation."""
        from tests.validation.validate_frontmatter import validate_deck

        ctx_path = tmp_path / "_context.md"
        ctx_path.write_text(
            '---\n'
            'id: test_context\n'
            'title: "Test Context"\n'
            'type: context\n'
            'subtype: engagement\n'
            'status: active\n'
            'authority: aligned\n'
            'curation_level: L1\n'
            'review_status: clean\n'
            'review_flags: []\n'
            'extraction_confidence: null\n'
            'client: TestCo\n'
            'engagement: Demo\n'
            'industry: []\n'
            'tags:\n'
            '  - engagement-context\n'
            'created: 2026-03-30\n'
            'modified: 2026-03-30\n'
            '---\n'
            '\n'
            '# Test Context\n'
            '\n'
            '## Client Background\n'
            '\n'
            'TBD.\n'
            '\n'
            '## Engagement Snapshot\n'
            '\n'
            'TBD.\n'
            '\n'
            '## Objectives / SOW\n'
            '\n'
            'TBD.\n'
            '\n'
            '## Timeline\n'
            '\n'
            'TBD.\n'
            '\n'
            '## Team\n'
            '\n'
            'TBD.\n'
            '\n'
            '## Stakeholders\n'
            '\n'
            'TBD.\n'
            '\n'
            '## Starting Hypotheses\n'
            '\n'
            'TBD.\n'
            '\n'
            '## Risks / Open Questions\n'
            '\n'
            'TBD.\n'
        )
        result = validate_deck(ctx_path)
        assert result["errors"] == [], f"Unexpected errors: {result['errors']}"

    def test_context_with_source_field_fails(self, tmp_path):
        """Context doc with source field should fail validation."""
        from tests.validation.validate_frontmatter import validate_deck

        ctx_path = tmp_path / "_context.md"
        ctx_path.write_text(
            '---\n'
            'id: test_context\n'
            'title: "Test Context"\n'
            'type: context\n'
            'subtype: engagement\n'
            'status: active\n'
            'authority: aligned\n'
            'curation_level: L1\n'
            'review_status: clean\n'
            'review_flags: []\n'
            'extraction_confidence: null\n'
            'client: TestCo\n'
            'engagement: Demo\n'
            'tags: []\n'
            'created: 2026-03-30\n'
            'modified: 2026-03-30\n'
            'source: "../bad_source.pdf"\n'
            'source_hash: "abc123"\n'
            '---\n'
            '\n'
            '# Test\n'
            '## Client Background\n'
            '## Engagement Snapshot\n'
            '## Objectives / SOW\n'
            '## Timeline\n'
            '## Team\n'
            '## Stakeholders\n'
            '## Starting Hypotheses\n'
            '## Risks / Open Questions\n'
        )
        result = validate_deck(ctx_path)
        error_msgs = [e[1] for e in result["errors"]]
        assert any("source" in m for m in error_msgs)
