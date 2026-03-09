"""Tests for folio/tracking/registry.py."""

import json
from pathlib import Path

import pytest
import yaml

from folio.tracking.registry import (
    RegistryEntry,
    entry_from_dict,
    load_registry,
    rebuild_registry,
    refresh_entry_status,
    remove_entry,
    resolve_entry_source,
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


def _sample_entry(**overrides) -> RegistryEntry:
    defaults = dict(
        id="test_evidence_20260310_deck",
        title="Test Deck",
        markdown_path="TestClient/test_deck/test_deck.md",
        deck_dir="TestClient/test_deck",
        source_relative_path="../../../sources/deck.pptx",
        source_hash="abc123def456",
        source_type="deck",
        version=1,
        converted="2026-03-10T02:15:00Z",
        modified="2026-03-10T02:15:00Z",
        client="TestClient",
        authority="captured",
        curation_level="L0",
        staleness_status="current",
    )
    defaults.update(overrides)
    return RegistryEntry(**defaults)


# ---------------------------------------------------------------------------
# load / save tests
# ---------------------------------------------------------------------------

class TestRegistryLoadSave:
    def test_load_missing_file_returns_empty(self, tmp_path):
        data = load_registry(tmp_path / "registry.json")
        assert data["_schema_version"] == 1
        assert data["decks"] == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "registry.json"
        entry = _sample_entry()
        data = {"_schema_version": 1, "decks": {entry.id: entry.to_dict()}}
        save_registry(path, data)

        loaded = load_registry(path)
        assert entry.id in loaded["decks"]
        assert loaded["decks"][entry.id]["title"] == "Test Deck"
        assert "updated_at" in loaded

    def test_load_corrupt_json_returns_empty(self, tmp_path):
        path = tmp_path / "registry.json"
        path.write_text("not json{{{")
        data = load_registry(path)
        assert data["decks"] == {}

    def test_load_non_dict_returns_empty(self, tmp_path):
        path = tmp_path / "registry.json"
        path.write_text(json.dumps([1, 2, 3]))
        data = load_registry(path)
        assert data["decks"] == {}

    def test_save_is_atomic(self, tmp_path):
        """Temp file should not remain after save."""
        path = tmp_path / "registry.json"
        save_registry(path, {"_schema_version": 1, "decks": {}})
        assert path.exists()
        assert not path.with_suffix(".tmp").exists()


# ---------------------------------------------------------------------------
# upsert / remove tests
# ---------------------------------------------------------------------------

class TestRegistryUpsertRemove:
    def test_upsert_new_entry(self, tmp_path):
        path = tmp_path / "registry.json"
        entry = _sample_entry()
        upsert_entry(path, entry)

        data = load_registry(path)
        assert entry.id in data["decks"]

    def test_upsert_updates_existing(self, tmp_path):
        path = tmp_path / "registry.json"
        entry = _sample_entry()
        upsert_entry(path, entry)

        entry.version = 2
        entry.title = "Updated Title"
        upsert_entry(path, entry)

        data = load_registry(path)
        assert data["decks"][entry.id]["version"] == 2
        assert data["decks"][entry.id]["title"] == "Updated Title"

    def test_remove_entry(self, tmp_path):
        path = tmp_path / "registry.json"
        entry = _sample_entry()
        upsert_entry(path, entry)
        remove_entry(path, entry.id)

        data = load_registry(path)
        assert entry.id not in data["decks"]

    def test_remove_nonexistent_is_noop(self, tmp_path):
        path = tmp_path / "registry.json"
        entry = _sample_entry()
        upsert_entry(path, entry)
        remove_entry(path, "nonexistent_id")

        data = load_registry(path)
        assert entry.id in data["decks"]


# ---------------------------------------------------------------------------
# bootstrap from markdown
# ---------------------------------------------------------------------------

class TestRegistryBootstrap:
    def test_bootstrap_finds_folio_docs(self, tmp_path):
        library = tmp_path / "library"
        source = tmp_path / "sources" / "deck.pptx"
        _make_source(source)

        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(source)

        md_path = library / "ClientA" / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "clienta_evidence_20260310_deck",
            "title": "Test Deck",
            "source": "../../../sources/deck.pptx",
            "source_hash": h,
            "source_type": "deck",
            "version": 1,
            "converted": "2026-03-10T02:15:00Z",
            "client": "ClientA",
            "authority": "captured",
            "curation_level": "L0",
        })

        data = rebuild_registry(library)
        assert len(data["decks"]) == 1
        entry_data = list(data["decks"].values())[0]
        assert entry_data["id"] == "clienta_evidence_20260310_deck"
        assert entry_data["staleness_status"] == "current"

    def test_bootstrap_ignores_non_folio_md(self, tmp_path):
        library = tmp_path / "library"
        md_path = library / "README.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("# Just a readme\n")

        data = rebuild_registry(library)
        assert len(data["decks"]) == 0

    def test_bootstrap_ignores_md_without_frontmatter(self, tmp_path):
        library = tmp_path / "library"
        md_path = library / "notes.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("No frontmatter here.\n")

        data = rebuild_registry(library)
        assert len(data["decks"]) == 0


# ---------------------------------------------------------------------------
# staleness refresh
# ---------------------------------------------------------------------------

class TestStalenessRefresh:
    def test_refresh_current(self, tmp_path):
        library = tmp_path / "library"
        source = tmp_path / "sources" / "deck.pptx"
        _make_source(source)

        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(source)

        md_path = library / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "source": "../../sources/deck.pptx",
            "source_hash": h,
        })

        entry = _sample_entry(
            markdown_path="deck/deck.md",
            deck_dir="deck",
            source_relative_path="../../sources/deck.pptx",
            source_hash=h,
            staleness_status="unknown",
        )

        updated = refresh_entry_status(library, entry)
        assert updated.staleness_status == "current"

    def test_refresh_stale(self, tmp_path):
        library = tmp_path / "library"
        source = tmp_path / "sources" / "deck.pptx"
        _make_source(source, "original content")

        md_path = library / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "source": "../../sources/deck.pptx",
            "source_hash": "old_hash_value",
        })

        entry = _sample_entry(
            markdown_path="deck/deck.md",
            deck_dir="deck",
            source_relative_path="../../sources/deck.pptx",
            source_hash="old_hash_value",
        )

        updated = refresh_entry_status(library, entry)
        assert updated.staleness_status == "stale"

    def test_refresh_missing(self, tmp_path):
        library = tmp_path / "library"
        md_path = library / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "source": "../../sources/gone.pptx",
            "source_hash": "abc123",
        })

        entry = _sample_entry(
            markdown_path="deck/deck.md",
            deck_dir="deck",
            source_relative_path="../../sources/gone.pptx",
            source_hash="abc123",
        )

        updated = refresh_entry_status(library, entry)
        assert updated.staleness_status == "missing"


# ---------------------------------------------------------------------------
# entry_from_dict resilience
# ---------------------------------------------------------------------------

class TestEntryFromDict:
    def test_unknown_fields_ignored(self):
        d = _sample_entry().to_dict()
        d["future_field"] = "some value"
        d["another_unknown"] = 42
        entry = entry_from_dict(d)
        assert entry.id == "test_evidence_20260310_deck"

    def test_missing_optional_fields(self):
        d = {
            "id": "minimal",
            "title": "Minimal",
            "markdown_path": "a.md",
            "deck_dir": "a",
            "source_relative_path": "../x.pptx",
            "source_hash": "abc",
            "source_type": "deck",
            "version": 1,
            "converted": "2026-01-01",
        }
        entry = entry_from_dict(d)
        assert entry.id == "minimal"
        assert entry.client is None
        assert entry.staleness_status == "current"
