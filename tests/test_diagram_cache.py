"""Tests for diagram cache layer (PR 4).

Covers load/save per stage, image-hash keying, version invalidation,
per-entry hash invalidation, per-miss durability, and no cross-pollution
with consulting-slide caches.
"""

import json
import pytest
from pathlib import Path

from folio.pipeline.diagram_cache import (
    DIAGRAM_CACHE_VERSION,
    DIAGRAM_SCHEMA_VERSION,
    DIAGRAM_PIPELINE_VERSION,
    DIAGRAM_IMAGE_STRATEGY_VERSION,
    _PASS_A_FILENAME,
    _POST_B_FILENAME,
    _FINAL_FILENAME,
    _prompt_version,
    _stable_hash,
    text_inventory_hash,
    page_profile_hash,
    pass_a_graph_hash,
    post_b_graph_hash,
    load_stage_cache,
    load_stale_entry,
    save_stage_cache,
    check_entry,
    store_entry,
)


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------


class TestHashHelpers:
    def test_prompt_version_deterministic(self):
        v1 = _prompt_version("Extract diagram structure")
        v2 = _prompt_version("Extract diagram structure")
        assert v1 == v2
        assert len(v1) == 12

    def test_prompt_version_changes_on_edit(self):
        v1 = _prompt_version("Extract diagram structure v1")
        v2 = _prompt_version("Extract diagram structure v2")
        assert v1 != v2

    def test_stable_hash_deterministic(self):
        h1 = _stable_hash("a", "b", "c")
        h2 = _stable_hash("a", "b", "c")
        assert h1 == h2
        assert len(h1) == 16

    def test_text_inventory_hash(self):
        h1 = text_inventory_hash("TEXT: hello")
        h2 = text_inventory_hash("TEXT: hello")
        assert h1 == h2

    def test_page_profile_hash(self):
        h = page_profile_hash(
            "diagram", "medium", 300, (0.0, 0.0, 612.0, 792.0),
            0, 150, 50, 1000, True,
        )
        assert len(h) == 16

    def test_pass_a_graph_hash_deterministic(self):
        graph = {"nodes": [{"id": "a"}], "edges": [], "groups": []}
        h1 = pass_a_graph_hash("architecture", graph)
        h2 = pass_a_graph_hash("architecture", graph)
        assert h1 == h2

    def test_post_b_graph_hash(self):
        graph = {"nodes": [{"id": "a"}], "edges": []}
        h1 = post_b_graph_hash("flow", graph, False)
        h2 = post_b_graph_hash("flow", graph, True)
        assert h1 != h2


# ---------------------------------------------------------------------------
# Load / save lifecycle
# ---------------------------------------------------------------------------


class TestLoadSave:
    def test_save_and_load_pass_a(self, tmp_path):
        cache = {"img123": {"data": "test"}}
        save_stage_cache(tmp_path, "pass_a", cache, "anthropic", "model-1", "prompt-v1")
        loaded = load_stage_cache(tmp_path, "pass_a", "anthropic", "model-1", "prompt-v1")
        assert loaded.get("img123") == {"data": "test"}

    def test_save_and_load_post_b(self, tmp_path):
        cache = {"abc": {"value": 42}}
        save_stage_cache(tmp_path, "post_b", cache, "openai", "gpt-4", "prompt")
        loaded = load_stage_cache(tmp_path, "post_b", "openai", "gpt-4", "prompt")
        assert loaded.get("abc") == {"value": 42}

    def test_save_and_load_final(self, tmp_path):
        cache = {"xyz": {"result": True}}
        save_stage_cache(tmp_path, "final", cache, "anthropic", "claude", "p")
        loaded = load_stage_cache(tmp_path, "final", "anthropic", "claude", "p")
        assert loaded.get("xyz") == {"result": True}

    def test_missing_file_returns_empty(self, tmp_path):
        loaded = load_stage_cache(tmp_path, "pass_a", "p", "m", "t")
        assert loaded == {}

    def test_none_cache_dir_returns_empty(self):
        loaded = load_stage_cache(None, "pass_a", "p", "m", "t")
        assert loaded == {}

    def test_unknown_stage_returns_empty(self, tmp_path):
        loaded = load_stage_cache(tmp_path, "invalid_stage", "p", "m", "t")
        assert loaded == {}


# ---------------------------------------------------------------------------
# Version invalidation
# ---------------------------------------------------------------------------


class TestVersionInvalidation:
    def test_model_change_invalidates(self, tmp_path):
        cache = {"entry1": {"data": "ok"}}
        save_stage_cache(tmp_path, "pass_a", cache, "anthropic", "model-v1", "prompt")
        loaded = load_stage_cache(tmp_path, "pass_a", "anthropic", "model-v2", "prompt")
        assert loaded == {}

    def test_provider_change_invalidates(self, tmp_path):
        cache = {"entry1": {"data": "ok"}}
        save_stage_cache(tmp_path, "pass_a", cache, "anthropic", "model", "prompt")
        loaded = load_stage_cache(tmp_path, "pass_a", "openai", "model", "prompt")
        assert loaded == {}

    def test_prompt_change_invalidates(self, tmp_path):
        cache = {"entry1": {"data": "ok"}}
        save_stage_cache(tmp_path, "pass_a", cache, "anthropic", "model", "prompt-v1")
        loaded = load_stage_cache(tmp_path, "pass_a", "anthropic", "model", "prompt-v2")
        assert loaded == {}

    def test_same_versions_preserved(self, tmp_path):
        cache = {"entry1": {"data": "ok"}}
        save_stage_cache(tmp_path, "pass_a", cache, "anthropic", "model", "prompt")
        loaded = load_stage_cache(tmp_path, "pass_a", "anthropic", "model", "prompt")
        assert loaded.get("entry1") == {"data": "ok"}


# ---------------------------------------------------------------------------
# Entry-level operations
# ---------------------------------------------------------------------------


class TestEntryOperations:
    def test_check_entry_valid(self):
        cache = {"img_hash_1": {"_dep_a": "abc", "data": "ok"}}
        result = check_entry(cache, "img_hash_1", {"_dep_a": "abc"})
        assert result == {"_dep_a": "abc", "data": "ok"}

    def test_check_entry_dep_mismatch(self):
        cache = {"img_hash_1": {"_dep_a": "abc", "data": "ok"}}
        result = check_entry(cache, "img_hash_1", {"_dep_a": "different"})
        assert result is None

    def test_check_entry_missing(self):
        cache = {}
        result = check_entry(cache, "missing", {"_dep": "x"})
        assert result is None

    def test_store_entry(self):
        cache = {}
        store_entry(cache, "img1", {"diagram": "data"}, {"_dep": "v1"}, "anthropic", "claude")
        entry = cache["img1"]
        assert entry["diagram"] == "data"
        assert entry["_dep__dep"] == "v1"  # m7: prefixed with _dep_
        assert entry["_provider"] == "anthropic"
        assert entry["_model"] == "claude"

    def test_store_entry_does_not_mutate_data(self):
        cache = {}
        original_data = {"key": "value"}
        store_entry(cache, "img1", original_data, {}, "p", "m")
        assert "key" in original_data
        assert "_provider" not in original_data

    def test_check_entry_backward_compat(self):
        """m7: check_entry reads both prefixed and legacy raw keys."""
        cache = {"img1": {"_dep": "v1", "data": "ok"}}
        result = check_entry(cache, "img1", {"_dep": "v1"})
        assert result is not None


# ---------------------------------------------------------------------------
# No cross-pollution with consulting-slide caches
# ---------------------------------------------------------------------------


class TestNoCrossPollution:
    def test_diagram_filenames_are_distinct(self):
        """Diagram cache files must NOT overlap with consulting-slide cache files."""
        consulting_files = {".analysis_cache.json", ".analysis_cache_deep.json"}
        diagram_files = {_PASS_A_FILENAME, _POST_B_FILENAME, _FINAL_FILENAME}
        assert consulting_files.isdisjoint(diagram_files)

    def test_no_writes_to_analysis_cache(self, tmp_path):
        """Writing diagram caches must not create .analysis_cache.json."""
        cache = {"img1": {"data": "test"}}
        save_stage_cache(tmp_path, "pass_a", cache, "p", "m", "t")
        save_stage_cache(tmp_path, "post_b", cache, "p", "m", "t")
        save_stage_cache(tmp_path, "final", cache, "p", "m", "t")

        assert not (tmp_path / ".analysis_cache.json").exists()
        assert not (tmp_path / ".analysis_cache_deep.json").exists()

    def test_per_miss_flush(self, tmp_path):
        """Each save produces a readable file immediately."""
        cache = {}
        store_entry(cache, "img1", {"a": 1}, {}, "p", "m")
        save_stage_cache(tmp_path, "pass_a", cache, "p", "m", "prompt")

        # File should exist and be loadable
        loaded = load_stage_cache(tmp_path, "pass_a", "p", "m", "prompt")
        assert loaded.get("img1") is not None

        # Add another entry and flush again
        store_entry(cache, "img2", {"b": 2}, {}, "p", "m")
        save_stage_cache(tmp_path, "pass_a", cache, "p", "m", "prompt")

        loaded2 = load_stage_cache(tmp_path, "pass_a", "p", "m", "prompt")
        assert loaded2.get("img1") is not None
        assert loaded2.get("img2") is not None


# ---------------------------------------------------------------------------
# Regression: load_stale_entry bypasses marker validation
# ---------------------------------------------------------------------------


class TestLoadStaleEntry:
    """Regression for stale-cache IoU inheritance (Issue #2)."""

    def test_stale_entry_bypasses_markers(self, tmp_path):
        """load_stale_entry reads entry even after provider/model change."""
        cache = {"img_abc": {"graph": {"nodes": [{"id": "stable_old"}]}}}
        save_stage_cache(tmp_path, "final", cache, "anthropic", "old-model", "old-prompt")
        # Normal load with different markers returns empty
        normal = load_stage_cache(tmp_path, "final", "anthropic", "new-model", "new-prompt")
        assert normal == {}
        # Stale entry loader bypasses markers
        stale = load_stale_entry(tmp_path, "final", "img_abc")
        assert stale is not None
        assert stale["graph"]["nodes"][0]["id"] == "stable_old"

    def test_stale_entry_missing_key(self, tmp_path):
        cache = {"img_abc": {"data": "ok"}}
        save_stage_cache(tmp_path, "final", cache, "p", "m", "t")
        assert load_stale_entry(tmp_path, "final", "nonexistent") is None

    def test_stale_entry_no_file(self, tmp_path):
        assert load_stale_entry(tmp_path, "final", "any") is None

    def test_stale_entry_none_dir(self):
        assert load_stale_entry(None, "final", "any") is None

    def test_stale_entry_unknown_stage(self, tmp_path):
        assert load_stale_entry(tmp_path, "unknown", "any") is None
