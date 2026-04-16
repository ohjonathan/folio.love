"""Tests for entity registry core module."""

import json
import os
import stat
from pathlib import Path

import pytest

from folio.tracking.entities import (
    _compute_entity_merge_basis_fingerprint,
    _empty_entity_registry,
    _strip_person_id_suffix,
    _transpose_person_name,
    EntityAliasCollisionError,
    EntityAmbiguousError,
    EntityEntry,
    EntityRegistry,
    EntityRegistryError,
    EntitySchemaVersionError,
    EntitySlugCollisionError,
    entity_from_dict,
    person_name_variants,
    sanitize_wikilink_name,
    slugify,
)


def _sample_entity(**overrides) -> EntityEntry:
    defaults = dict(
        canonical_name="Jane Smith",
        type="person",
        aliases=[],
        needs_confirmation=False,
        source="import",
    )
    defaults.update(overrides)
    return EntityEntry(**defaults)


# ---------------------------------------------------------------------------
# Slugify / sanitize
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_entity_key_derivation(self):
        assert slugify("Jane Smith") == "jane_smith"
        assert slugify("SAP ERP") == "sap_erp"
        assert slugify("Incident Triage") == "incident_triage"
        assert slugify("Jane  Smith") == "jane_smith"
        assert slugify("  Jane Smith  ") == "jane_smith"

    def test_slugify_unicode_normalization(self):
        """Precomposed and decomposed forms should produce identical slugs."""
        # é as single codepoint (NFC) vs e + combining accent (NFD)
        precomposed = "Ren\u00e9 Dupont"
        decomposed = "Rene\u0301 Dupont"
        assert slugify(precomposed) == slugify(decomposed) == "ren_dupont"

    def test_wikilink_sanitization(self):
        assert sanitize_wikilink_name("Jane [Smith]") == "Jane Smith"
        assert sanitize_wikilink_name("Dept|Eng") == "DeptEng"
        assert sanitize_wikilink_name("Topic#Heading") == "TopicHeading"
        assert sanitize_wikilink_name("Item^ref") == "Itemref"
        assert sanitize_wikilink_name("  padded  ") == "padded"


class TestPersonNameHelpers:
    def test_transpose_person_name(self):
        assert _transpose_person_name("Link, Rachel") == "Rachel Link"

    def test_transpose_person_name_preserves_suffix(self):
        assert _transpose_person_name("Doe, John Jr.") == "John Doe Jr."

    def test_transpose_person_name_supports_unicode_letters(self):
        assert _transpose_person_name("Díaz, José") == "José Díaz"

    def test_transpose_person_name_supports_extended_roman_suffixes(self):
        assert _transpose_person_name("Doe, Jane VIII") == "Jane Doe VIII"

    def test_transpose_person_name_rejects_non_person_comma_strings(self):
        assert _transpose_person_name("Jordan, Systems") is None
        assert _transpose_person_name("Ernst & Young, LLP") is None
        assert _transpose_person_name("Review, Architecture") is None

    def test_strip_person_id_suffix(self):
        assert _strip_person_id_suffix("Rachelrjlink Link") == "Rachel Link"

    def test_strip_person_id_suffix_allows_zero_initial_suffixes(self):
        assert _strip_person_id_suffix("Christophersmith Smith") == "Christopher Smith"

    def test_person_name_variants_include_transposed_and_stripped_forms(self):
        assert person_name_variants("Link, Rachelrjlink") == [
            "Link, Rachelrjlink",
            "Rachelrjlink Link",
            "Rachel Link",
        ]

    def test_person_name_variants_do_not_transpose_non_person_comma_strings(self):
        assert person_name_variants("Jordan, Systems") == ["Jordan, Systems"]
        assert person_name_variants("Review, Architecture") == ["Review, Architecture"]

    def test_person_name_variants_include_unicode_transposed_form(self):
        assert person_name_variants("Díaz, José") == [
            "Díaz, José",
            "José Díaz",
        ]


# ---------------------------------------------------------------------------
# EntityEntry
# ---------------------------------------------------------------------------

class TestEntityEntry:
    def test_to_dict_excludes_none(self):
        entry = _sample_entity()
        d = entry.to_dict()
        assert "title" not in d
        assert "department" not in d
        assert "proposed_match" not in d

    def test_to_dict_preserves_empty_aliases(self):
        entry = _sample_entity(aliases=[])
        d = entry.to_dict()
        assert "aliases" in d
        assert d["aliases"] == []

    def test_entity_from_dict_filters_unknown(self):
        d = {
            "canonical_name": "Test",
            "type": "person",
            "unknown_field": "should be ignored",
        }
        entry = entity_from_dict(d)
        assert entry.canonical_name == "Test"
        assert not hasattr(entry, "unknown_field")


# ---------------------------------------------------------------------------
# EntityRegistry — basic CRUD
# ---------------------------------------------------------------------------

class TestEntityRegistryCRUD:
    def test_empty_registry_creation(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        assert reg.entity_count() == 0
        reg.save()
        data = json.loads((tmp_path / "entities.json").read_text())
        assert data["_schema_version"] == 1
        assert len(data["entities"]["person"]) == 0

    def test_add_entity_basic(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        entry = _sample_entity()
        key = reg.add_entity(entry)
        assert key == "jane_smith"
        assert reg.entity_count() == 1

    def test_add_entity_with_aliases(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        entry = _sample_entity(aliases=["Jane", "the CTO", "J. Smith"])
        key = reg.add_entity(entry)
        assert key == "jane_smith"
        retrieved = reg.get_entity("person", key)
        assert "Jane" in retrieved.aliases
        assert "the CTO" in retrieved.aliases

    def test_add_entity_duplicate_key(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        with pytest.raises(EntitySlugCollisionError):
            reg.add_entity(_sample_entity())

    def test_slug_collision_rejected(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Jane Smith"))
        with pytest.raises(EntitySlugCollisionError, match="jane_smith"):
            reg.add_entity(_sample_entity(canonical_name="Jane  Smith"))

    def test_slug_collision_across_types_allowed(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Operations", type="department"))
        reg.add_entity(_sample_entity(canonical_name="Operations", type="process"))
        assert reg.entity_count() == 2

    def test_alias_collision_detection(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Jane Smith", aliases=["Jane"]))
        with pytest.raises(EntityAliasCollisionError):
            reg.add_entity(
                _sample_entity(canonical_name="John Doe", aliases=["Jane"])
            )

    def test_first_seen_preserved_on_update(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        entry = _sample_entity(first_seen="2025-01-01T00:00:00Z")
        reg.add_entity(entry)
        reg.update_entity("person", "jane_smith", {"title": "CTO"})
        updated = reg.get_entity("person", "jane_smith")
        assert updated.first_seen == "2025-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# EntityRegistry — lookup
# ---------------------------------------------------------------------------

class TestEntityRegistryLookup:
    def test_lookup_exact_match(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        results = reg.lookup("Jane Smith")
        assert len(results) == 1
        assert results[0][0] == "person"
        assert results[0][1] == "jane_smith"

    def test_lookup_alias_match(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(aliases=["Jane"]))
        results = reg.lookup("Jane")
        assert len(results) == 1

    def test_lookup_case_insensitive(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        results = reg.lookup("jane smith")
        assert len(results) == 1
        results = reg.lookup("JANE SMITH")
        assert len(results) == 1

    def test_lookup_confirmed_only(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(needs_confirmation=True))
        results = reg.lookup("Jane Smith", confirmed_only=True)
        assert len(results) == 0
        results = reg.lookup("Jane Smith", confirmed_only=False)
        assert len(results) == 1

    def test_lookup_no_match(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        results = reg.lookup("John Doe")
        assert len(results) == 0

    def test_lookup_ambiguous_within_type(self, tmp_path):
        """Two entities in different types with same name → ambiguous."""
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Operations", type="department"))
        reg.add_entity(_sample_entity(canonical_name="Operations", type="process"))
        results = reg.lookup("Operations")
        assert len(results) == 2

        with pytest.raises(EntityAmbiguousError):
            reg.lookup_unique("Operations")

        # With type filter → unique
        result = reg.lookup_unique("Operations", entity_type="department")
        assert result is not None
        assert result[0] == "department"


# ---------------------------------------------------------------------------
# EntityRegistry — confirmation
# ---------------------------------------------------------------------------

class TestEntityRegistryConfirmation:
    def test_confirm_entity(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(
            needs_confirmation=True,
            proposed_match="some_key"
        ))
        assert reg.unconfirmed_count() == 1
        changed = reg.confirm_entity("person", "jane_smith")
        assert changed is True
        assert reg.unconfirmed_count() == 0
        entity = reg.get_entity("person", "jane_smith")
        assert entity.needs_confirmation is False
        assert entity.proposed_match is None

    def test_confirm_already_confirmed(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(needs_confirmation=False))
        changed = reg.confirm_entity("person", "jane_smith")
        assert changed is False


# ---------------------------------------------------------------------------
# EntityRegistry — durability
# ---------------------------------------------------------------------------

class TestEntityRegistryDurability:
    def test_atomic_write(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        reg.save()

        # Reload and verify
        reg2 = EntityRegistry(tmp_path / "entities.json")
        reg2.load()
        assert reg2.entity_count() == 1
        entity = reg2.get_entity("person", "jane_smith")
        assert entity.canonical_name == "Jane Smith"

    def test_corrupt_json_error(self, tmp_path):
        path = tmp_path / "entities.json"
        path.write_text("not valid json{{{")
        reg = EntityRegistry(path)
        with pytest.raises(EntityRegistryError, match="Cannot parse"):
            reg.load()

    def test_invalid_entry_skipped(self, tmp_path):
        path = tmp_path / "entities.json"
        data = {
            "_schema_version": 1,
            "entities": {
                "person": {
                    "valid": {"canonical_name": "Valid", "type": "person", "aliases": []},
                    "invalid": {"aliases": []},  # missing canonical_name
                },
                "department": {},
                "system": {},
                "process": {},
            },
        }
        path.write_text(json.dumps(data))
        reg = EntityRegistry(path)
        reg.load()
        assert reg.entity_count() == 1
        assert reg.get_entity("person", "valid") is not None
        assert reg.get_entity("person", "invalid") is None

    def test_schema_version_migration(self, tmp_path):
        path = tmp_path / "entities.json"
        data = {
            "_schema_version": 1,
            "entities": {
                "person": {"js": {"canonical_name": "JS", "type": "person", "aliases": []}},
                "department": {},
                "system": {},
                "process": {},
            },
        }
        path.write_text(json.dumps(data))
        reg = EntityRegistry(path)
        reg.load()
        assert reg.entity_count() == 1

    def test_schema_version_too_new(self, tmp_path):
        path = tmp_path / "entities.json"
        data = {"_schema_version": 999, "entities": {}}
        path.write_text(json.dumps(data))
        reg = EntityRegistry(path)
        with pytest.raises(EntitySchemaVersionError, match="999"):
            reg.load()

    def test_read_only_fallback(self, tmp_path):
        path = tmp_path / "entities.json"
        reg = EntityRegistry(path)
        reg.load()
        reg.add_entity(_sample_entity())

        # Make directory read-only to prevent write
        path.parent.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            with pytest.raises(OSError):
                reg.save()
        finally:
            path.parent.chmod(stat.S_IRWXU)


# ---------------------------------------------------------------------------
# B2: save-without-load guard
# ---------------------------------------------------------------------------

class TestSaveWithoutLoadGuard:
    def test_save_without_load_raises(self, tmp_path):
        """save() without load() must raise to prevent data clobbering."""
        path = tmp_path / "entities.json"
        # Pre-populate existing data
        path.write_text(json.dumps({
            "_schema_version": 1,
            "entities": {
                "person": {"existing": {
                    "canonical_name": "Existing",
                    "type": "person",
                    "aliases": [],
                }},
                "department": {}, "system": {}, "process": {},
            },
        }))

        reg = EntityRegistry(path)
        with pytest.raises(EntityRegistryError, match="load"):
            reg.save()

        # Verify original data is untouched
        data = json.loads(path.read_text())
        assert "existing" in data["entities"]["person"]


# ---------------------------------------------------------------------------
# B1: alias collision in update_entity
# ---------------------------------------------------------------------------

class TestUpdateEntityAliasCollision:
    def test_update_entity_drops_colliding_aliases(self, tmp_path):
        """Upgrading an unconfirmed entity with an alias that collides with
        an existing entity's alias should silently drop the collision."""
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(
            canonical_name="Jane Smith",
            aliases=["Jane"],
        ))
        reg.add_entity(_sample_entity(
            canonical_name="John Doe",
            needs_confirmation=True,
        ))

        # Try to add alias "Jane" to John Doe — it collides with Jane Smith's alias
        changed = reg.update_entity("person", "john_doe", {
            "aliases": ["Jane", "JD"],
        })
        assert changed is True

        # "Jane" should be dropped, "JD" should be kept
        john = reg.get_entity("person", "john_doe")
        assert "JD" in john.aliases
        assert "Jane" not in john.aliases

    def test_update_entity_non_colliding_aliases_pass(self, tmp_path):
        """Non-colliding aliases in update should be applied normally."""
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Jane Smith"))
        reg.add_entity(_sample_entity(canonical_name="John Doe"))

        changed = reg.update_entity("person", "john_doe", {
            "aliases": ["JD", "Johnny"],
        })
        assert changed is True
        john = reg.get_entity("person", "john_doe")
        assert "JD" in john.aliases
        assert "Johnny" in john.aliases


# ---------------------------------------------------------------------------
# v0.6.5 Slice 6a: entity-merge rejection memory
# ---------------------------------------------------------------------------


def _seed_alice_pair(reg: EntityRegistry) -> None:
    """Seed two person entities that will match via last_first_transpose."""
    reg.add_entity(_sample_entity(canonical_name="Alice Chen"))
    reg.add_entity(_sample_entity(canonical_name="Chen, Alice"))


class TestEntityMergeRejectionMemory:
    """Slice 6a spec §7 tests T-1 .. T-15."""

    # T-1
    def test_empty_registry_has_rejected_merges_key(self):
        d = _empty_entity_registry()
        assert d["rejected_merges"] == []

    # T-2
    def test_load_legacy_registry_defaults_rejected_merges_empty(self, tmp_path):
        path = tmp_path / "entities.json"
        # Legacy file shape WITHOUT rejected_merges.
        path.write_text(json.dumps({
            "_schema_version": 1,
            "updated_at": "2026-01-01T00:00:00+00:00",
            "entities": {t: {} for t in ("person", "department", "system", "process")},
        }))
        reg = EntityRegistry(path)
        reg.load()
        assert reg._data["rejected_merges"] == []

    # T-3
    def test_basis_fingerprint_deterministic_and_sorted(self):
        fp1 = _compute_entity_merge_basis_fingerprint(
            "person", "alice_chen", "chen_alice", ["last_first_transpose"]
        )
        fp2 = _compute_entity_merge_basis_fingerprint(
            "person", "chen_alice", "alice_chen", ["last_first_transpose"]
        )
        assert fp1 == fp2
        assert fp1.startswith("sha256:")

    # T-4 (injective encoding — delimiter collision guard)
    def test_basis_fingerprint_changes_when_reasons_change(self):
        fp_ab = _compute_entity_merge_basis_fingerprint(
            "person", "a", "b", ["reason_a", "reason_b"]
        )
        fp_pipe = _compute_entity_merge_basis_fingerprint(
            "person", "a", "b", ["reason_a|reason_b"]
        )
        assert fp_ab != fp_pipe, "canonical JSON encoding must be injective"
        fp_extra = _compute_entity_merge_basis_fingerprint(
            "person", "a", "b", ["reason_a", "reason_b", "alias_overlap"]
        )
        assert fp_ab != fp_extra

    # T-5
    def test_suggest_person_merges_filters_rejected_pair_same_fingerprint(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        _seed_alice_pair(reg)
        before = reg.suggest_person_merges()
        assert len(before) == 1
        reg.reject_person_merge(before[0].left_key, before[0].right_key)
        after = reg.suggest_person_merges()
        assert after == []

    # T-5b
    def test_suggest_person_merges_apply_rejection_memory_false_bypass(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        _seed_alice_pair(reg)
        before = reg.suggest_person_merges()
        reg.reject_person_merge(before[0].left_key, before[0].right_key)
        unfiltered = reg.suggest_person_merges(apply_rejection_memory=False)
        assert len(unfiltered) == 1

    # T-6
    def test_suggest_person_merges_revives_when_basis_changes(self, tmp_path):
        """Seed a rejection with a DIFFERENT fingerprint than the current pair
        would compute, so the revival path fires without mutating aliases
        (alias collision guard prevents overlap between distinct entities)."""
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        _seed_alice_pair(reg)
        current = reg.suggest_person_merges()[0]
        # Seed a rejection record with fabricated basis_fingerprint.
        reg._data["rejected_merges"].append({
            "subject_type": "person",
            "entity_keys": sorted([current.left_key, current.right_key]),
            "basis_fingerprint": "sha256:stale-fingerprint-from-old-basis",
            "reasons_at_rejection": ["some_old_reason"],
            "rejected_at": "2026-01-01T00:00:00+00:00",
        })
        after = reg.suggest_person_merges()
        assert len(after) == 1
        assert after[0].revived is True

    # T-7
    def test_reject_person_merge_idempotent(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        _seed_alice_pair(reg)
        sugg = reg.suggest_person_merges()[0]
        changed1, status1 = reg.reject_person_merge(sugg.left_key, sugg.right_key)
        changed2, status2 = reg.reject_person_merge(sugg.left_key, sugg.right_key)
        assert (changed1, status1) == (True, "rejected")
        assert (changed2, status2) == (False, "already rejected")
        assert len(reg._data["rejected_merges"]) == 1

    # T-8
    def test_reject_person_merge_validates_keys(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        _seed_alice_pair(reg)
        with pytest.raises(EntityRegistryError, match="no longer exists"):
            reg.reject_person_merge("nonexistent_ghost", "alice_chen")
        with pytest.raises(EntityRegistryError, match="no longer exists"):
            reg.reject_person_merge("alice_chen", "nonexistent_ghost")

    # T-12
    def test_count_entity_merge_suppressions_direct(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        _seed_alice_pair(reg)
        assert reg.count_entity_merge_suppressions() == 0
        sugg = reg.suggest_person_merges()[0]
        reg.reject_person_merge(sugg.left_key, sugg.right_key)
        assert reg.count_entity_merge_suppressions() == 1

    # T-13
    def test_rejected_merges_save_load_roundtrip(self, tmp_path):
        path = tmp_path / "entities.json"
        reg = EntityRegistry(path)
        reg.load()
        _seed_alice_pair(reg)
        sugg = reg.suggest_person_merges()[0]
        reg.reject_person_merge(sugg.left_key, sugg.right_key)
        reg.save()

        # Reload from disk.
        reg2 = EntityRegistry(path)
        reg2.load()
        assert len(reg2._data["rejected_merges"]) == 1
        assert reg2.suggest_person_merges() == []

    # T-14 — old-writer / new-reader downgrade compat
    def test_old_writer_preserves_rejected_merges(self, tmp_path):
        """Pre-v0.6.5 code path (setdefault _schema_version=1, save self._data)
        preserves the rejected_merges key we added via the new API."""
        path = tmp_path / "entities.json"
        reg = EntityRegistry(path)
        reg.load()
        _seed_alice_pair(reg)
        sugg = reg.suggest_person_merges()[0]
        reg.reject_person_merge(sugg.left_key, sugg.right_key)
        reg.save()

        # Simulate a "pre-v0.6.5" code path: load, touch unrelated data, save.
        # Current save() preserves all top-level keys via self._data write-through.
        reg2 = EntityRegistry(path)
        reg2.load()
        reg2._data["updated_at"] = "2099-01-01T00:00:00+00:00"  # unrelated mutation
        reg2.save()

        # Third load: rejected_merges should survive intact.
        reg3 = EntityRegistry(path)
        reg3.load()
        assert len(reg3._data["rejected_merges"]) == 1

    # T-6b — revert to prior basis stays suppressed
    def test_suggest_person_merges_revert_to_prior_basis_stays_suppressed(self, tmp_path):
        """Two rejection records with different fingerprints for the same pair:
        current basis matches one of them → suppressed (not revived)."""
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        _seed_alice_pair(reg)
        current = reg.suggest_person_merges()[0]
        sorted_keys = sorted([current.left_key, current.right_key])
        current_fp = current.basis_fingerprint

        # Record two rejections: one fabricated "B" fingerprint, one matching current "A".
        reg._data["rejected_merges"].extend([
            {
                "subject_type": "person",
                "entity_keys": sorted_keys,
                "basis_fingerprint": "sha256:fabricated-B-fingerprint",
                "reasons_at_rejection": ["old_reason_b"],
                "rejected_at": "2026-01-02T00:00:00+00:00",
            },
            {
                "subject_type": "person",
                "entity_keys": sorted_keys,
                "basis_fingerprint": current_fp,
                "reasons_at_rejection": current.reasons,
                "rejected_at": "2026-01-03T00:00:00+00:00",
            },
        ])
        # Current basis matches record A → suppressed (not revived), despite
        # there being a stale non-matching record B.
        assert reg.suggest_person_merges() == []
