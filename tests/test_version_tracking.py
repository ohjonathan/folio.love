"""Comprehensive version tracking tests (G4, G5).

Covers: detect_changes(), compute_version(), load/save edge cases,
5-version lifecycle integration, cross-spec tests, and truncation.
"""

import json
import pytest
from pathlib import Path

from folio.tracking.versions import (
    ChangeSet,
    VersionInfo,
    _normalize_text,
    _to_str,
    _atomic_write_json,
    _TEXTS_CACHE_VERSION,
    detect_changes,
    compute_version,
    load_texts_cache,
    load_version_history,
    save_texts_cache,
    save_version_history,
)
from folio.output.markdown import _format_version_history


# ---------------------------------------------------------------------------
# detect_changes() unit tests (10)
# ---------------------------------------------------------------------------


class TestDetectChanges:
    def test_detect_no_changes(self):
        old = {1: "hello", 2: "world"}
        new = {1: "hello", 2: "world"}
        cs = detect_changes(old, new)
        assert not cs.has_changes
        assert cs.unchanged == [1, 2]
        assert cs.added == []
        assert cs.removed == []
        assert cs.modified == []

    def test_detect_added_slides(self):
        old = {1: "hello"}
        new = {1: "hello", 2: "new slide"}
        cs = detect_changes(old, new)
        assert cs.added == [2]
        assert cs.unchanged == [1]
        assert cs.has_changes

    def test_detect_removed_slides(self):
        old = {1: "hello", 2: "world"}
        new = {1: "hello"}
        cs = detect_changes(old, new)
        assert cs.removed == [2]
        assert cs.unchanged == [1]
        assert cs.has_changes

    def test_detect_modified_slides(self):
        old = {1: "hello", 2: "world"}
        new = {1: "hello", 2: "changed"}
        cs = detect_changes(old, new)
        assert cs.modified == [2]
        assert cs.unchanged == [1]
        assert cs.has_changes

    def test_detect_mixed_changes(self):
        old = {1: "keep", 2: "modify me", 3: "remove me"}
        new = {1: "keep", 2: "modified!", 4: "brand new"}
        cs = detect_changes(old, new)
        assert cs.unchanged == [1]
        assert cs.modified == [2]
        assert cs.removed == [3]
        assert cs.added == [4]

    def test_whitespace_only_not_detected(self):
        old = {1: "hello world"}
        new = {1: "hello   world"}
        cs = detect_changes(old, new)
        assert not cs.has_changes
        assert cs.unchanged == [1]

    def test_whitespace_newlines_not_detected(self):
        old = {1: "line one\nline two"}
        new = {1: "  line one   line two  "}
        cs = detect_changes(old, new)
        assert not cs.has_changes
        assert cs.unchanged == [1]

    def test_empty_to_nonempty_detected(self):
        old = {1: ""}
        new = {1: "now has content"}
        cs = detect_changes(old, new)
        assert cs.modified == [1]

    def test_empty_old_all_added(self):
        cs = detect_changes({}, {1: "a", 2: "b"})
        assert cs.added == [1, 2]
        assert cs.removed == []

    def test_empty_new_all_removed(self):
        cs = detect_changes({1: "a", 2: "b"}, {})
        assert cs.removed == [1, 2]
        assert cs.added == []

    def test_slidetext_objects_accepted(self):
        """SlideText objects work via _to_str() conversion."""
        from folio.pipeline.text import SlideText

        old = {1: SlideText(slide_num=1, full_text="hello")}
        new = {1: SlideText(slide_num=1, full_text="changed")}
        cs = detect_changes(old, new)
        assert cs.modified == [1]

    def test_slidetext_unchanged(self):
        from folio.pipeline.text import SlideText

        old = {1: SlideText(slide_num=1, full_text="same")}
        new = {1: "same"}
        cs = detect_changes(old, new)
        assert not cs.has_changes
        assert cs.unchanged == [1]


# ---------------------------------------------------------------------------
# compute_version() unit tests (6)
# ---------------------------------------------------------------------------


class TestComputeVersion:
    def test_first_version_is_1(self, tmp_path):
        texts = {1: "slide one", 2: "slide two"}
        vi = compute_version(tmp_path, "hash1", "src.pptx", 2, texts)
        assert vi.version == 1
        assert vi.changes.added == [1, 2]
        assert vi.changes.removed == []
        assert vi.changes.modified == []

    def test_second_version_increments(self, tmp_path):
        t1 = {1: "a", 2: "b"}
        t2 = {1: "a", 2: "changed"}
        compute_version(tmp_path, "h1", "src.pptx", 2, t1)
        vi = compute_version(tmp_path, "h2", "src.pptx", 2, t2)
        assert vi.version == 2
        assert vi.changes.modified == [2]
        assert vi.changes.unchanged == [1]

    def test_version_persists_history(self, tmp_path):
        compute_version(tmp_path, "h1", "src.pptx", 1, {1: "a"})
        history = load_version_history(tmp_path / "version_history.json")
        assert len(history) == 1
        assert history[0]["version"] == 1

    def test_version_persists_texts_cache(self, tmp_path):
        compute_version(tmp_path, "h1", "src.pptx", 2, {1: "alpha", 2: "beta"})
        cache = load_texts_cache(tmp_path / ".texts_cache.json")
        assert cache == {1: "alpha", 2: "beta"}

    def test_version_with_note(self, tmp_path):
        vi = compute_version(tmp_path, "h1", "src.pptx", 1, {1: "a"}, note="Initial import")
        assert vi.note == "Initial import"
        history = load_version_history(tmp_path / "version_history.json")
        assert history[0]["note"] == "Initial import"

    def test_no_change_reconversion(self, tmp_path):
        texts = {1: "same", 2: "content"}
        compute_version(tmp_path, "h1", "src.pptx", 2, texts)
        vi = compute_version(tmp_path, "h2", "src.pptx", 2, texts)
        assert vi.version == 2
        assert not vi.changes.has_changes
        assert vi.changes.unchanged == [1, 2]


# ---------------------------------------------------------------------------
# Load/save edge cases (6)
# ---------------------------------------------------------------------------


class TestLoadSaveEdgeCases:
    def test_load_texts_cache_missing_file(self, tmp_path):
        result = load_texts_cache(tmp_path / "nonexistent.json")
        assert result == {}

    def test_load_texts_cache_corrupt_json(self, tmp_path):
        path = tmp_path / ".texts_cache.json"
        path.write_text("{not valid json!!")
        result = load_texts_cache(path)
        assert result == {}

    def test_load_texts_cache_version_mismatch(self, tmp_path):
        path = tmp_path / ".texts_cache.json"
        data = {"_cache_version": 999, "1": "text"}
        path.write_text(json.dumps(data))
        result = load_texts_cache(path)
        assert result == {}

    def test_load_version_history_missing_file(self, tmp_path):
        result = load_version_history(tmp_path / "nonexistent.json")
        assert result == []

    def test_load_version_history_corrupt_json(self, tmp_path):
        path = tmp_path / "version_history.json"
        path.write_text("<<<corrupt>>>")
        result = load_version_history(path)
        assert result == []

    def test_atomic_write_json_creates_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "data.json"
        _atomic_write_json(deep_path, {"key": "value"})
        assert deep_path.exists()
        assert json.loads(deep_path.read_text()) == {"key": "value"}


# ---------------------------------------------------------------------------
# 5-version lifecycle integration test (1)
# ---------------------------------------------------------------------------


class TestFiveVersionLifecycle:
    def test_five_version_lifecycle(self, tmp_path):
        """Exercises 5 versions with progressive changes."""
        # v1: Initial 3 slides (all added)
        v1_texts = {1: "Introduction to Q4 Results", 2: "Revenue grew 15% YoY", 3: "Regional breakdown by market"}
        vi1 = compute_version(tmp_path, "h1", "deck.pptx", 3, v1_texts)
        assert vi1.version == 1
        assert vi1.changes.added == [1, 2, 3]
        assert vi1.changes.removed == []
        assert vi1.changes.modified == []
        assert vi1.changes.unchanged == []

        # v2: Modify slide 2 (content change)
        v2_texts = {1: "Introduction to Q4 Results", 2: "Revenue grew 18% YoY (revised)", 3: "Regional breakdown by market"}
        vi2 = compute_version(tmp_path, "h2", "deck.pptx", 3, v2_texts)
        assert vi2.version == 2
        assert vi2.changes.added == []
        assert vi2.changes.removed == []
        assert vi2.changes.modified == [2]
        assert vi2.changes.unchanged == [1, 3]

        # v3: Add slide 4
        v3_texts = {1: "Introduction to Q4 Results", 2: "Revenue grew 18% YoY (revised)", 3: "Regional breakdown by market", 4: "Outlook for next quarter"}
        vi3 = compute_version(tmp_path, "h3", "deck.pptx", 4, v3_texts)
        assert vi3.version == 3
        assert vi3.changes.added == [4]
        assert vi3.changes.removed == []
        assert vi3.changes.modified == []
        assert vi3.changes.unchanged == [1, 2, 3]

        # v4: Remove slide 3
        v4_texts = {1: "Introduction to Q4 Results", 2: "Revenue grew 18% YoY (revised)", 4: "Outlook for next quarter"}
        vi4 = compute_version(tmp_path, "h4", "deck.pptx", 3, v4_texts)
        assert vi4.version == 4
        assert vi4.changes.added == []
        assert vi4.changes.removed == [3]
        assert vi4.changes.modified == []
        assert vi4.changes.unchanged == [1, 2, 4]

        # v5: No changes (identical to v4)
        v5_texts = {1: "Introduction to Q4 Results", 2: "Revenue grew 18% YoY (revised)", 4: "Outlook for next quarter"}
        vi5 = compute_version(tmp_path, "h5", "deck.pptx", 3, v5_texts)
        assert vi5.version == 5
        assert vi5.changes.added == []
        assert vi5.changes.removed == []
        assert vi5.changes.modified == []
        assert vi5.changes.unchanged == [1, 2, 4]
        assert not vi5.changes.has_changes

        # Verify accumulated history
        history = load_version_history(tmp_path / "version_history.json")
        assert len(history) == 5
        assert [h["version"] for h in history] == [1, 2, 3, 4, 5]

        # Verify texts cache reflects latest state
        cache = load_texts_cache(tmp_path / ".texts_cache.json")
        assert set(cache.keys()) == {1, 2, 4}


# ---------------------------------------------------------------------------
# Cross-spec tests (2)
# ---------------------------------------------------------------------------


class TestCrossSpec:
    def test_extraction_version_bump_all_modified(self, tmp_path):
        """Simulate extraction version bump: all slides get different text.

        After an extraction upgrade, the first conversion sees different text
        for every slide. The texts cache self-corrects (honest diff), and
        version history shows all-modified. This is expected behavior.
        """
        original = {1: "old extraction A", 2: "old extraction B", 3: "old extraction C"}
        compute_version(tmp_path, "h1", "deck.pptx", 3, original)

        # New extraction produces different text for every slide
        upgraded = {1: "new extraction A+", 2: "new extraction B+", 3: "new extraction C+"}
        vi = compute_version(tmp_path, "h1", "deck.pptx", 3, upgraded)
        assert vi.version == 2
        assert vi.changes.modified == [1, 2, 3]
        assert vi.changes.unchanged == []

    def test_metadata_only_resave_no_version_change(self, tmp_path):
        """PPTX touched (source_hash differs) but slide content identical.

        detect_changes() reports no changes, compute_version() increments
        (audit trail), and staleness via check_staleness() reports "stale"
        (hash differs). All three are correct.
        """
        from folio.tracking.sources import check_staleness

        texts = {1: "unchanged", 2: "also unchanged"}

        # v1 with hash "aaa"
        compute_version(tmp_path, "aaa", "deck.pptx", 2, texts)

        # v2 with different hash "bbb" but same texts
        vi = compute_version(tmp_path, "bbb", "deck.pptx", 2, texts)
        assert vi.version == 2
        assert not vi.changes.has_changes
        assert vi.changes.unchanged == [1, 2]

        # Create a fake source file and markdown to test staleness
        src = tmp_path / "deck.pptx"
        src.write_bytes(b"different content")
        md_path = tmp_path / "output.md"
        md_path.touch()

        # Stored hash "aaa" won't match the actual file hash
        result = check_staleness(md_path, "deck.pptx", "aaa")
        assert result["status"] == "stale"


# ---------------------------------------------------------------------------
# Version history table truncation tests (4)
# ---------------------------------------------------------------------------


def _make_history(n: int) -> list[dict]:
    """Build a version history list with n entries."""
    history = []
    for i in range(1, n + 1):
        history.append({
            "version": i,
            "timestamp": f"2026-01-{i:02d}T00:00:00+00:00",
            "source_hash": f"hash{i}",
            "source_path": "deck.pptx",
            "note": None,
            "slide_count": 3,
            "changes": {
                "added": [1, 2, 3] if i == 1 else [],
                "removed": [],
                "modified": [2] if i > 1 else [],
                "unchanged": [1, 3] if i > 1 else [],
            },
        })
    return history


class TestVersionHistoryTruncation:
    def test_version_history_table_under_limit(self):
        history = _make_history(5)
        output = _format_version_history(history, max_display=10)
        assert "Showing last" not in output
        # All 5 versions present
        for i in range(1, 6):
            assert f"v{i}" in output

    def test_version_history_table_at_limit(self):
        history = _make_history(10)
        output = _format_version_history(history, max_display=10)
        assert "Showing last" not in output
        for i in range(1, 11):
            assert f"v{i}" in output

    def test_version_history_table_over_limit(self):
        history = _make_history(15)
        output = _format_version_history(history, max_display=10)
        assert "*Showing last 10 of 15 versions.*" in output
        # Only versions 6-15 shown (last 10)
        for i in range(6, 16):
            assert f"v{i}" in output
        # Versions 1-5 NOT shown
        for i in range(1, 6):
            assert f"| v{i} |" not in output

    def test_version_history_table_default_limit(self):
        history = _make_history(15)
        # Call without max_display arg — default is 10
        output = _format_version_history(history)
        assert "*Showing last 10 of 15 versions.*" in output
        # Only last 10 shown
        for i in range(6, 16):
            assert f"v{i}" in output
