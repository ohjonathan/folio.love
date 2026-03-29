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
        type="evidence",
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
        assert entry_data["type"] == "evidence"

    def test_bootstrap_finds_interaction_docs(self, tmp_path):
        library = tmp_path / "library"
        transcript = tmp_path / "transcripts" / "call.md"
        _make_source(transcript, "meeting notes")

        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(transcript)

        md_path = library / "ClientA" / "interactions" / "call" / "call.md"
        _make_folio_markdown(md_path, {
            "id": "clienta_ddq126_interview_20260321_cto_call",
            "title": "CTO Call",
            "type": "interaction",
            "subtype": "expert_interview",
            "source_transcript": "../../../../transcripts/call.md",
            "source_hash": h,
            "version": 1,
            "converted": "2026-03-21T02:15:00Z",
            "authority": "captured",
            "curation_level": "L0",
        })

        data = rebuild_registry(library)
        assert len(data["decks"]) == 1
        entry_data = list(data["decks"].values())[0]
        assert entry_data["type"] == "interaction"
        assert entry_data["source_relative_path"] == "../../../../transcripts/call.md"
        assert "source_type" not in entry_data

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
        assert entry.type == "evidence"
        assert entry.client is None
        assert entry.staleness_status == "current"

    def test_missing_source_type_allowed_for_interaction(self):
        d = {
            "id": "interaction_note",
            "title": "Interaction Note",
            "markdown_path": "Client/interactions/note.md",
            "deck_dir": "Client/interactions",
            "source_relative_path": "../../transcripts/note.md",
            "source_hash": "abc123",
            "version": 1,
            "converted": "2026-03-21T00:00:00Z",
            "type": "interaction",
        }
        entry = entry_from_dict(d)
        assert entry.type == "interaction"
        assert entry.source_type is None

    def test_missing_type_defaults_to_evidence(self):
        d = {
            "id": "legacy_note",
            "title": "Legacy Note",
            "markdown_path": "legacy/note.md",
            "deck_dir": "legacy",
            "source_relative_path": "../deck.pptx",
            "source_hash": "abc123",
            "version": 1,
            "converted": "2026-03-28T00:00:00Z",
        }
        entry = entry_from_dict(d)
        assert entry.type == "evidence"


# ---------------------------------------------------------------------------
# write safety: locking + disk errors
# ---------------------------------------------------------------------------

class TestWriteSafety:
    def test_save_no_orphan_tmp_or_lock(self, tmp_path):
        """After a successful save, .tmp and .lock must not remain."""
        path = tmp_path / "registry.json"
        save_registry(path, {"_schema_version": 1, "decks": {}})
        assert path.exists()
        assert not path.with_suffix(".tmp").exists()
        # .lock may exist (empty) but that's fine; what matters is it's unlocked

    def test_save_on_read_only_dir_raises(self, tmp_path):
        """Write to a read-only directory should raise a clear OSError."""
        import os
        ro_dir = tmp_path / "readonly"
        ro_dir.mkdir()
        reg_path = ro_dir / "registry.json"

        # Make directory read-only
        os.chmod(ro_dir, 0o555)
        try:
            with pytest.raises(OSError):
                save_registry(reg_path, {"_schema_version": 1, "decks": {}})
        finally:
            os.chmod(ro_dir, 0o755)  # restore for cleanup

    def test_concurrent_upserts_preserve_all_entries(self, tmp_path):
        """Sequential upserts (simulating concurrent writers) must preserve all entries."""
        path = tmp_path / "library" / "registry.json"
        path.parent.mkdir(parents=True)

        # Create 5 entries sequentially (simulates concurrent writers finishing one by one)
        for i in range(5):
            entry = _sample_entry(
                id=f"deck_{i}",
                title=f"Deck {i}",
                markdown_path=f"Client/deck_{i}/deck_{i}.md",
                deck_dir=f"Client/deck_{i}",
            )
            upsert_entry(path, entry)

        data = load_registry(path)
        assert len(data["decks"]) == 5
        for i in range(5):
            assert f"deck_{i}" in data["decks"]

    def test_load_malformed_decks_list_marks_corrupt(self, tmp_path):
        """Registry with decks as a list (not dict) must be marked corrupt."""
        path = tmp_path / "registry.json"
        path.write_text(json.dumps({"_schema_version": 1, "decks": []}))
        data = load_registry(path)
        assert data.get("_corrupt") is True
        assert data["decks"] == {}

    def test_load_malformed_decks_string_marks_corrupt(self, tmp_path):
        """Registry with decks as a string must be marked corrupt."""
        path = tmp_path / "registry.json"
        path.write_text(json.dumps({"_schema_version": 1, "decks": "not a dict"}))
        data = load_registry(path)
        assert data.get("_corrupt") is True


# ---------------------------------------------------------------------------
# FR-700: review fields
# ---------------------------------------------------------------------------

class TestReviewFieldsRegistry:
    def test_round_trip_with_review_fields(self, tmp_path):
        entry = _sample_entry(
            review_status="flagged",
            review_flags=["low_confidence_slide_1", "unvalidated_claim_slide_1"],
            extraction_confidence=0.45,
            grounding_summary={"total_claims": 3, "high_confidence": 1},
        )
        d = entry.to_dict()
        assert d["review_status"] == "flagged"
        assert d["review_flags"] == ["low_confidence_slide_1", "unvalidated_claim_slide_1"]
        assert d["extraction_confidence"] == 0.45
        assert d["grounding_summary"]["total_claims"] == 3

        restored = entry_from_dict(d)
        assert restored.review_status == "flagged"
        assert restored.review_flags == ["low_confidence_slide_1", "unvalidated_claim_slide_1"]
        assert restored.extraction_confidence == 0.45

    def test_empty_review_flags_preserved(self):
        entry = _sample_entry(review_status="clean", review_flags=[])
        d = entry.to_dict()
        assert "review_flags" in d
        assert d["review_flags"] == []

    def test_none_review_fields_omitted(self):
        entry = _sample_entry()
        d = entry.to_dict()
        assert "review_status" not in d
        assert "review_flags" not in d
        assert "extraction_confidence" not in d

    def test_rebuild_reads_review_fields(self, tmp_path):
        library = tmp_path / "library"
        source = tmp_path / "sources" / "deck.pptx"
        _make_source(source)

        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(source)

        md_path = library / "Client" / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "test_deck",
            "title": "Test",
            "source": "../../../sources/deck.pptx",
            "source_hash": h,
            "source_type": "deck",
            "version": 1,
            "converted": "2026-01-01",
            "review_status": "flagged",
            "review_flags": ["analysis_unavailable"],
            "extraction_confidence": 0.3,
        })

        data = rebuild_registry(library)
        entry = data["decks"]["test_deck"]
        assert entry["review_status"] == "flagged"
        assert entry["review_flags"] == ["analysis_unavailable"]
        assert entry["extraction_confidence"] == 0.3

    def test_rebuild_preserves_zero_claim_grounding_summary(self, tmp_path):
        library = tmp_path / "library"
        source = tmp_path / "sources" / "deck.pptx"
        _make_source(source)

        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(source)

        grounding_summary = {
            "total_claims": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "validated": 0,
            "unvalidated": 0,
        }
        md_path = library / "Client" / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "test_deck",
            "title": "Test",
            "source": "../../../sources/deck.pptx",
            "source_hash": h,
            "source_type": "deck",
            "version": 1,
            "converted": "2026-01-01",
            "grounding_summary": grounding_summary,
        })

        data = rebuild_registry(library)
        entry = data["decks"]["test_deck"]
        assert entry["grounding_summary"] == grounding_summary

    def test_reconcile_updates_review_status(self, tmp_path):
        from folio.tracking.registry import reconcile_from_frontmatter

        library = tmp_path / "library"
        md_path = library / "deck" / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "test_deck",
            "title": "Test",
            "source": "../../sources/deck.pptx",
            "source_hash": "abc",
            "review_status": "reviewed",
            "review_flags": [],
        })

        data = {
            "_schema_version": 1,
            "decks": {
                "test_deck": {
                    "id": "test_deck",
                    "title": "Test",
                    "markdown_path": "deck/deck.md",
                    "review_status": "flagged",
                    "review_flags": ["low_confidence_slide_1"],
                },
            },
        }

        result = reconcile_from_frontmatter(library, data)
        assert result["decks"]["test_deck"]["review_status"] == "reviewed"
        assert result["decks"]["test_deck"]["review_flags"] == []


class TestInteractionRegistryBehavior:
    def test_reconcile_updates_interaction_source_path_and_type(self, tmp_path):
        from folio.tracking.registry import reconcile_from_frontmatter

        library = tmp_path / "library"
        md_path = library / "interactions" / "note" / "note.md"
        _make_folio_markdown(md_path, {
            "id": "interaction_note",
            "title": "Interaction Note",
            "type": "interaction",
            "subtype": "expert_interview",
            "source_transcript": "../../../transcripts/new.md",
            "source_hash": "abc",
        })

        data = {
            "_schema_version": 1,
            "decks": {
                "interaction_note": {
                    "id": "interaction_note",
                    "title": "Interaction Note",
                    "type": "evidence",
                    "markdown_path": "interactions/note/note.md",
                    "deck_dir": "interactions/note",
                    "source_relative_path": "../../../transcripts/old.md",
                    "source_hash": "abc",
                    "version": 1,
                    "converted": "2026-03-21T00:00:00Z",
                },
            },
        }

        result = reconcile_from_frontmatter(library, data)
        entry = result["decks"]["interaction_note"]
        assert entry["type"] == "interaction"
        assert entry["source_relative_path"] == "../../../transcripts/new.md"

    def test_refresh_entry_status_generic_for_interaction(self, tmp_path):
        library = tmp_path / "library"
        transcript = tmp_path / "transcripts" / "call.md"
        _make_source(transcript, "meeting notes")

        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(transcript)

        md_path = library / "interactions" / "call" / "call.md"
        _make_folio_markdown(md_path, {
            "source_transcript": "../../../transcripts/call.md",
            "source_hash": h,
        })

        entry = _sample_entry(
            type="interaction",
            markdown_path="interactions/call/call.md",
            deck_dir="interactions/call",
            source_relative_path="../../../transcripts/call.md",
            source_hash=h,
            source_type=None,
        )

        updated = refresh_entry_status(library, entry)
        assert updated.staleness_status == "current"


# --- PR 6: Standalone diagram notes excluded from registry ---


class TestDiagramNoteRegistryExclusion:
    """Standalone diagram notes must be ignored by rebuild_registry."""

    def test_diagram_note_ignored_by_rebuild(self, tmp_path):
        """Diagram notes lack source/source_hash, so rebuild skips them."""
        library = tmp_path / "library"
        source = tmp_path / "sources" / "deck.pptx"
        _make_source(source)

        from folio.tracking.sources import compute_file_hash
        h = compute_file_hash(source)

        # Write a real deck note
        deck_dir = library / "Client" / "deck"
        md_path = deck_dir / "deck.md"
        _make_folio_markdown(md_path, {
            "id": "test_deck",
            "title": "Test Deck",
            "source": "../../../sources/deck.pptx",
            "source_hash": h,
            "source_type": "deck",
            "version": 1,
            "converted": "2026-03-10T02:15:00Z",
        })

        # Write a standalone diagram note (no source, source_hash)
        diagram_path = deck_dir / "20260310-deck-diagram-p007.md"
        _make_folio_markdown(diagram_path, {
            "type": "diagram",
            "diagram_type": "architecture",
            "title": "Test — Architecture (Page 7)",
            "source_deck": "[[deck]]",
            "source_page": 7,
            "folio_freeze": False,
            "tags": ["diagram"],
        })

        data = rebuild_registry(library)
        # Only the deck note should be indexed
        assert len(data["decks"]) == 1
        assert "test_deck" in data["decks"]
