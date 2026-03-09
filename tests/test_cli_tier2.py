"""Tests for Tier 2 CLI commands: status, scan, refresh, promote."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from click.testing import CliRunner
from folio.cli import cli
from folio.tracking.registry import (
    RegistryEntry,
    load_registry,
    save_registry,
    upsert_entry,
)


def _make_folio_markdown(path: Path, frontmatter: dict) -> None:
    """Write a markdown file with YAML frontmatter."""
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{yaml_str}---\n\n# Content\n")


def _make_source(path: Path, content: str = "binary data") -> None:
    """Create a source file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _make_config(path: Path, config: dict) -> None:
    """Write folio.yaml."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(config, default_flow_style=False))


def _sample_registry_entry(**overrides) -> dict:
    defaults = {
        "id": "test_evidence_20260310_deck",
        "title": "Test Deck",
        "markdown_path": "TestClient/test_deck/test_deck.md",
        "deck_dir": "TestClient/test_deck",
        "source_relative_path": "../../../sources/deck.pptx",
        "source_hash": "abc123def456",
        "source_type": "deck",
        "version": 1,
        "converted": "2026-03-10T02:15:00Z",
        "modified": "2026-03-10T02:15:00Z",
        "client": "TestClient",
        "authority": "captured",
        "curation_level": "L0",
        "staleness_status": "current",
        "type": "evidence",
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

class TestStatusCommand:
    def test_status_bootstraps_registry(self, tmp_path):
        """Status should create registry.json when it doesn't exist."""
        library = tmp_path / "library"
        source = tmp_path / "sources" / "deck.pptx"
        _make_source(source)

        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(source)

        md_path = library / "Client" / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "client_evidence_deck",
            "title": "Deck",
            "source": "../../../sources/deck.pptx",
            "source_hash": h,
            "source_type": "deck",
            "version": 1,
        })

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "status"])
        assert result.exit_code == 0
        assert "Bootstrapping registry" in result.output
        assert "Library: 1 decks" in result.output
        assert (library / "registry.json").exists()

    def test_status_reads_existing_registry(self, tmp_path):
        """Status should use existing registry without bootstrap."""
        library = tmp_path / "library"
        library.mkdir(parents=True)

        source = tmp_path / "sources" / "deck.pptx"
        _make_source(source)
        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(source)

        md_path = library / "Client" / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "source": "../../../sources/deck.pptx",
            "source_hash": h,
        })

        # Pre-create registry
        entry = _sample_registry_entry(
            markdown_path="Client/deck/deck.md",
            deck_dir="Client/deck",
            source_relative_path="../../../sources/deck.pptx",
            source_hash=h,
        )
        reg_data = {"_schema_version": 1, "decks": {entry["id"]: entry}}
        save_registry(library / "registry.json", reg_data)

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "status"])
        assert result.exit_code == 0
        assert "Bootstrapping" not in result.output
        assert "Library: 1 decks" in result.output


# ---------------------------------------------------------------------------
# scan command
# ---------------------------------------------------------------------------

class TestScanCommand:
    def test_scan_no_sources_config(self, tmp_path):
        """Scan should print helpful message when no sources configured."""
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(tmp_path / "library")})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "scan"])
        assert result.exit_code == 0
        assert "No source roots configured" in result.output

    def test_scan_finds_new_sources(self, tmp_path):
        """Scan should detect unconverted source files."""
        library = tmp_path / "library"
        library.mkdir(parents=True)
        sources_dir = tmp_path / "client_materials"
        _make_source(sources_dir / "ClientA" / "deck.pptx")

        # Empty registry
        save_registry(library / "registry.json", {"_schema_version": 1, "decks": {}})

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {
            "library_root": str(library),
            "sources": [{"name": "materials", "path": str(sources_dir), "target_prefix": ""}],
        })

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "scan"])
        assert result.exit_code == 0
        assert "New: 1" in result.output


# ---------------------------------------------------------------------------
# promote command
# ---------------------------------------------------------------------------

class TestPromoteCommand:
    def test_promote_l0_to_l1_success(self, tmp_path):
        """Promote should succeed when L0→L1 requirements are met."""
        library = tmp_path / "library"
        deck_dir = library / "Client" / "deck"
        md_path = deck_dir / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "client_evidence_deck",
            "title": "Deck",
            "type": "evidence",
            "curation_level": "L0",
            "client": "ClientA",
            "engagement": "Q1 2026",
            "tags": ["market-sizing"],
            "source": "../../../sources/deck.pptx",
            "source_hash": "abc123",
        })

        entry = _sample_registry_entry(
            id="client_evidence_deck",
            markdown_path="Client/deck/deck.md",
            deck_dir="Client/deck",
            curation_level="L0",
            client="ClientA",
        )
        reg_data = {"_schema_version": 1, "decks": {"client_evidence_deck": entry}}
        save_registry(library / "registry.json", reg_data)

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "promote", "client_evidence_deck", "L1"])
        assert result.exit_code == 0
        assert "Promoted" in result.output
        assert "L0 → L1" in result.output

        # Verify frontmatter updated
        content = md_path.read_text()
        assert "curation_level: L1" in content

        # Verify registry updated
        data = load_registry(library / "registry.json")
        assert data["decks"]["client_evidence_deck"]["curation_level"] == "L1"

        # Verify promotion event in version_history
        history_path = deck_dir / "version_history.json"
        assert history_path.exists()
        history = json.loads(history_path.read_text())
        assert "events" in history
        assert len(history["events"]) == 1
        assert history["events"][0]["kind"] == "promotion"

    def test_promote_l0_to_l1_missing_client(self, tmp_path):
        """Promote should block L0→L1 when client is missing."""
        library = tmp_path / "library"
        md_path = library / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "no_client_deck",
            "title": "Deck",
            "type": "evidence",
            "curation_level": "L0",
            "tags": ["tag"],
            "source": "../../sources/deck.pptx",
            "source_hash": "abc",
        })

        entry = _sample_registry_entry(
            id="no_client_deck",
            markdown_path="deck/deck.md",
            deck_dir="deck",
            curation_level="L0",
            client=None,
        )
        reg_data = {"_schema_version": 1, "decks": {"no_client_deck": entry}}
        save_registry(library / "registry.json", reg_data)

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "promote", "no_client_deck", "L1"])
        assert result.exit_code != 0
        assert "client" in result.output.lower()

    def test_promote_l1_to_l2_warns_no_relationships(self, tmp_path):
        """Promote L1→L2 should warn when no relationship fields present."""
        library = tmp_path / "library"
        deck_dir = library / "Client" / "deck"
        md_path = deck_dir / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "relationship_deck",
            "title": "Deck",
            "type": "evidence",
            "curation_level": "L1",
            "client": "ClientA",
            "engagement": "Q1",
            "tags": ["tag"],
            "source": "../../../sources/deck.pptx",
            "source_hash": "abc",
        })

        entry = _sample_registry_entry(
            id="relationship_deck",
            markdown_path="Client/deck/deck.md",
            deck_dir="Client/deck",
            curation_level="L1",
        )
        reg_data = {"_schema_version": 1, "decks": {"relationship_deck": entry}}
        save_registry(library / "registry.json", reg_data)

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "promote", "relationship_deck", "L2"])
        assert result.exit_code == 0
        assert "⚠" in result.output
        assert "relationship" in result.output.lower()

    def test_promote_downward_rejected(self, tmp_path):
        """Promote should reject downward transitions."""
        library = tmp_path / "library"
        md_path = library / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "high_deck",
            "curation_level": "L2",
            "source": "x.pptx",
            "source_hash": "abc",
        })

        entry = _sample_registry_entry(
            id="high_deck",
            markdown_path="deck/deck.md",
            deck_dir="deck",
            curation_level="L2",
        )
        reg_data = {"_schema_version": 1, "decks": {"high_deck": entry}}
        save_registry(library / "registry.json", reg_data)

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "promote", "high_deck", "L1"])
        assert result.exit_code != 0
        assert "upward" in result.output.lower()


# ---------------------------------------------------------------------------
# version events
# ---------------------------------------------------------------------------

class TestVersionEventsPreservation:
    """Promotion events must survive subsequent conversions."""

    def test_events_preserved_by_save_version_history(self, tmp_path):
        from folio.tracking.versions import (
            append_promotion_event,
            load_version_history,
            save_version_history,
        )

        history_path = tmp_path / "version_history.json"

        # Create an event
        append_promotion_event(history_path, {
            "kind": "promotion",
            "from_level": "L0",
            "to_level": "L1",
        })

        # Simulate a conversion save
        versions = [{"version": 1, "timestamp": "2026-01-01"}]
        save_version_history(history_path, versions)

        # Verify events survived
        data = json.loads(history_path.read_text())
        assert "events" in data
        assert len(data["events"]) == 1
        assert data["events"][0]["kind"] == "promotion"
        assert len(data["versions"]) == 1

    def test_promotion_does_not_create_fake_version(self, tmp_path):
        from folio.tracking.versions import append_promotion_event

        history_path = tmp_path / "version_history.json"
        # Pre-existing history
        history_path.write_text(json.dumps({"versions": [
            {"version": 1, "timestamp": "2026-01-01"},
        ]}))

        append_promotion_event(history_path, {
            "kind": "promotion",
            "from_level": "L0",
            "to_level": "L1",
        })

        data = json.loads(history_path.read_text())
        assert len(data["versions"]) == 1  # No new version created
        assert len(data["events"]) == 1


# ---------------------------------------------------------------------------
# B1: Promote preserves frontmatter formatting (no YAML round-trip)
# ---------------------------------------------------------------------------

class TestPromotePreservesFormatting:
    def test_promote_preserves_timestamps(self, tmp_path):
        """Promote must not reformat timestamps or strip comments."""
        library = tmp_path / "library"
        deck_dir = library / "Client" / "deck"
        md_path = deck_dir / "deck.md"

        # Write frontmatter with precise ISO timestamps that PyYAML would mangle
        raw_frontmatter = (
            "---\n"
            "id: ts_deck\n"
            "title: Timestamp Deck\n"
            "type: evidence\n"
            "curation_level: L0\n"
            "client: ClientA\n"
            "engagement: Q1 2026\n"
            "tags:\n"
            "- market-sizing\n"
            "source: ../../../sources/deck.pptx\n"
            "source_hash: abc123\n"
            "created: 2026-03-10T14:30:00Z\n"
            "modified: 2026-03-10T15:00:00Z\n"
            "converted: 2026-03-10T15:00:00Z\n"
            "# Human comment here\n"
            "---\n"
            "\n# Content body\n"
        )
        deck_dir.mkdir(parents=True, exist_ok=True)
        md_path.write_text(raw_frontmatter)

        entry = _sample_registry_entry(
            id="ts_deck",
            markdown_path="Client/deck/deck.md",
            deck_dir="Client/deck",
            curation_level="L0",
            client="ClientA",
        )
        reg_data = {"_schema_version": 1, "decks": {"ts_deck": entry}}
        save_registry(library / "registry.json", reg_data)

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "promote", "ts_deck", "L1"])
        assert result.exit_code == 0

        content = md_path.read_text()

        # Verify curation_level was updated
        assert "curation_level: L1" in content

        # Verify timestamps preserved exactly (PyYAML would convert to datetime objects)
        assert "2026-03-10T14:30:00Z" in content
        assert "2026-03-10T15:00:00Z" in content

        # Verify comment preserved
        assert "# Human comment here" in content

        # Verify body preserved
        assert "# Content body" in content

    def test_promote_only_changes_curation_level_line(self, tmp_path):
        """All non-curation_level lines should be byte-identical before/after."""
        library = tmp_path / "library"
        deck_dir = library / "Client" / "deck"
        md_path = deck_dir / "deck.md"

        raw_frontmatter = (
            "---\n"
            "id: byte_deck\n"
            "title: Byte Check Deck\n"
            "type: evidence\n"
            "curation_level: L0\n"
            "client: ClientA\n"
            "engagement: Q1 2026\n"
            "tags:\n"
            "- analysis\n"
            "source: ../../../sources/deck.pptx\n"
            "source_hash: def456\n"
            "---\n"
            "\n# Body content\n"
        )
        deck_dir.mkdir(parents=True, exist_ok=True)
        md_path.write_text(raw_frontmatter)

        entry = _sample_registry_entry(
            id="byte_deck",
            markdown_path="Client/deck/deck.md",
            deck_dir="Client/deck",
            curation_level="L0",
            client="ClientA",
        )
        reg_data = {"_schema_version": 1, "decks": {"byte_deck": entry}}
        save_registry(library / "registry.json", reg_data)

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        before_lines = raw_frontmatter.split("\n")
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "promote", "byte_deck", "L1"])
        assert result.exit_code == 0

        after_lines = md_path.read_text().split("\n")

        # Compare line by line; only the curation_level line should differ
        assert len(before_lines) == len(after_lines)
        for before, after in zip(before_lines, after_lines):
            if before.startswith("curation_level:"):
                assert after == "curation_level: L1"
            else:
                assert before == after


# ---------------------------------------------------------------------------
# B2: Reconversion preserves curation_level
# ---------------------------------------------------------------------------

class TestReconversionPreservesCuration:
    def test_frontmatter_generate_preserves_curation_level(self):
        """frontmatter.generate() should preserve curation_level from existing."""
        from folio.output.frontmatter import generate
        from folio.tracking.versions import VersionInfo, ChangeSet

        version_info = VersionInfo(
            version=2,
            timestamp="2026-03-10T15:00:00Z",
            source_hash="abc123",
            source_path="deck.pptx",
            note=None,
            slide_count=1,
            changes=ChangeSet(),
        )

        fm_str = generate(
            title="Test Deck",
            deck_id="test_deck",
            source_relative_path="deck.pptx",
            source_hash="abc123",
            source_type="deck",
            version_info=version_info,
            analyses={},
            existing_frontmatter={
                "id": "test_deck",
                "created": "2026-03-10T14:00:00Z",
                "authority": "analyzed",
                "curation_level": "L1",
            },
        )

        assert "curation_level: L1" in fm_str
        assert "authority: analyzed" in fm_str

    def test_frontmatter_generate_defaults_without_existing(self):
        """Without existing frontmatter, defaults to L0/captured."""
        from folio.output.frontmatter import generate
        from folio.tracking.versions import VersionInfo, ChangeSet

        version_info = VersionInfo(
            version=1,
            timestamp="2026-03-10T15:00:00Z",
            source_hash="abc123",
            source_path="deck.pptx",
            note=None,
            slide_count=1,
            changes=ChangeSet(),
        )

        fm_str = generate(
            title="Test Deck",
            deck_id="test_deck",
            source_relative_path="deck.pptx",
            source_hash="abc123",
            source_type="deck",
            version_info=version_info,
            analyses={},
        )

        assert "curation_level: L0" in fm_str
        assert "authority: captured" in fm_str


# ---------------------------------------------------------------------------
# S3: append_promotion_event backs up corrupt file
# ---------------------------------------------------------------------------

class TestAppendPromotionEventCorruptFile:
    def test_corrupt_json_backed_up(self, tmp_path):
        """Corrupt version_history.json should be backed up, not silently reset."""
        from folio.tracking.versions import append_promotion_event

        history_path = tmp_path / "version_history.json"
        history_path.write_text("not valid json{{{")

        append_promotion_event(history_path, {
            "kind": "promotion",
            "from_level": "L0",
            "to_level": "L1",
        })

        # Backup should exist
        backup = history_path.with_suffix(".json.bak")
        assert backup.exists()
        assert "not valid json" in backup.read_text()

        # New file should have the event
        data = json.loads(history_path.read_text())
        assert len(data["events"]) == 1

    def test_non_dict_backed_up(self, tmp_path):
        from folio.tracking.versions import append_promotion_event

        history_path = tmp_path / "version_history.json"
        history_path.write_text(json.dumps([1, 2, 3]))

        append_promotion_event(history_path, {
            "kind": "promotion",
            "from_level": "L0",
            "to_level": "L1",
        })

        backup = history_path.with_suffix(".json.bak")
        assert backup.exists()


# ---------------------------------------------------------------------------
# S7: status --refresh flag
# ---------------------------------------------------------------------------

class TestStatusRefreshFlag:
    def test_status_without_refresh_uses_cached_staleness(self, tmp_path):
        """Without --refresh, status should use cached staleness_status."""
        library = tmp_path / "library"
        library.mkdir(parents=True)

        entry = _sample_registry_entry(staleness_status="stale")
        reg_data = {"_schema_version": 1, "decks": {entry["id"]: entry}}
        save_registry(library / "registry.json", reg_data)

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "status"])
        assert result.exit_code == 0
        assert "Stale: 1" in result.output
