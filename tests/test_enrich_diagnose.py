"""Tests for folio enrich diagnose v1.0.0 (Tier-4 Roadmap row #4 sub-item A).

Module-level tests (ED-1..ED-27) per spec §8.1. Verifies:
  - Per-disposition finding mapping (ED-1..6)
  - Healthy-note omission (ED-7)
  - Scope filter, limit, ordering (ED-8..10)
  - Trust annotation (ED-11)
  - No LLM imports / read-only invariants / dataclass shape (ED-12..14)
  - Defensive defaults for unknown reasons (ED-15a/b/c/d)
  - Forbidden symbols / constants / by_code ordering (ED-16..19)
  - subject_id is deck_id (ED-20)
  - Function-level limit validation (ED-21)
  - Invalid scope + corrupt registry raise ScopeResolutionError (ED-22, ED-23)
  - by_code MappingProxyType immutability (ED-24)
  - recommended_action substitution + frontmatter-edit text (ED-25, ED-26)
  - review_status=flagged alone is omitted (ED-27)
"""

from __future__ import annotations

import ast
import json
from dataclasses import fields
from pathlib import Path
from types import MappingProxyType

import pytest
import yaml

from folio.config import FolioConfig, LLMConfig, LLMProfile, LLMRoute
from folio.enrich import (
    DIAGNOSE_COMMAND_NAME,
    DIAGNOSE_SCHEMA_VERSION,
    DiagnoseFinding,
    DiagnoseResult,
    DiagnoseSummary,
    EnrichPlanEntry,
    ScopeResolutionError,
    _entry_to_finding,
    _finding_sort_key,
    diagnose_notes,
)
from folio.pipeline.section_parser import MarkdownDocument
from folio.tracking import registry as registry_mod


# ---------------------------------------------------------------------------
# Fixture helpers (mirror tests/test_enrich.py patterns)
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path) -> FolioConfig:
    library_root = tmp_path / "library"
    library_root.mkdir(exist_ok=True)
    return FolioConfig(
        library_root=library_root,
        llm=LLMConfig(
            profiles={
                "default": LLMProfile(name="default", provider="anthropic", model="test-model"),
            },
            routing={"default": LLMRoute(primary="default")},
        ),
    )


def _evidence_note(
    note_id: str = "note1",
    title: str = "Test Evidence",
    client: str = "ClientA",
    engagement: str = "DD_Q1",
    curation_level: str = "L0",
    review_status: str = "clean",
    enrich_meta: dict | None = None,
    body: str | None = None,
) -> str:
    fm: dict = {
        "id": note_id,
        "title": title,
        "type": "evidence",
        "status": "active",
        "curation_level": curation_level,
        "review_status": review_status,
        "client": client,
        "engagement": engagement,
        "source": "deck.pptx",
        "source_hash": "abc",
        "version": 1,
        "created": "2026-01-01T00:00:00Z",
        "modified": "2026-01-01T00:00:00Z",
    }
    if enrich_meta is not None:
        fm["_llm_metadata"] = {"enrich": enrich_meta}
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    if body is None:
        body = (
            "## Slide 1\n\n"
            "![Slide 1](slides/slide-001.png)\n\n"
            "### Analysis\n\n"
            "**Slide Type:** data\n**Visual Description:** chart\n"
        )
    return f"---\n{yaml_str}---\n\n# {title}\n\n{body}"


def _setup_registry(library_root: Path, entries: dict) -> None:
    data = {"_schema_version": 1, "decks": entries, "updated_at": "2026-01-01T00:00:00Z"}
    (library_root / "registry.json").write_text(json.dumps(data))


def _write(library_root: Path, rel: str, content: str) -> Path:
    p = library_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def _registry_entry(deck_id: str, rel_path: str, type_: str = "evidence",
                    client: str = "ClientA", engagement: str = "DD_Q1",
                    review_status: str | None = None) -> dict:
    deck_dir = str(Path(rel_path).parent)
    entry: dict = {
        "id": deck_id,
        "title": deck_id,
        "markdown_path": rel_path,
        "deck_dir": deck_dir,
        "type": type_,
        "client": client,
        "engagement": engagement,
    }
    if review_status:
        entry["review_status"] = review_status
    return entry


def _build_lib_with_one_evidence(
    tmp_path: Path,
    *,
    note_id: str = "ClientA_DD_Q1_evidence_001",
    rel_path: str = "ClientA/DD_Q1/evidence/note1.md",
    curation_level: str = "L0",
    review_status: str = "clean",
    enrich_meta: dict | None = None,
    body: str | None = None,
) -> tuple[FolioConfig, Path]:
    config = _make_config(tmp_path)
    content = _evidence_note(
        note_id=note_id,
        curation_level=curation_level,
        review_status=review_status,
        enrich_meta=enrich_meta,
        body=body,
    )
    note_path = _write(config.library_root, rel_path, content)
    _setup_registry(config.library_root, {note_id: _registry_entry(note_id, rel_path)})
    return config, note_path


# ---------------------------------------------------------------------------
# ED-1..6: per-disposition finding mapping
# ---------------------------------------------------------------------------

class TestDispositionMapping:
    def test_protect_frontmatter_unreadable(self, tmp_path):
        # ED-1: unreadable frontmatter → frontmatter_unreadable error.
        config = _make_config(tmp_path)
        # Write a note with malformed YAML frontmatter (mapping value error).
        bad_content = "---\nid: x\ntitle: T\ntype: evidence\nbroken: : value\n---\n\n# T\n"
        _write(config.library_root, "ClientA/DD_Q1/evidence/bad.md", bad_content)
        _setup_registry(config.library_root, {
            "ClientA_DD_Q1_evidence_bad": _registry_entry(
                "ClientA_DD_Q1_evidence_bad", "ClientA/DD_Q1/evidence/bad.md"
            ),
        })
        result = diagnose_notes(config)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "frontmatter_unreadable"
        assert f.severity == "error"
        assert f.detail == "frontmatter unreadable"
        assert f.trust_status == "ok"

    def test_protect_managed_sections_unidentified(self, tmp_path):
        # ED-2: previously-enriched note with no identifiable managed sections.
        # PEER-SF-002: requires _llm_metadata.enrich present (the guard at
        # folio/enrich.py:376 is `if not managed_sections and enrich_meta`).
        prior_enrich = {
            "status": "executed",
            "spec_version": 1,
            "input_fingerprint": "sha256:dummy",
            "managed_body_fingerprint": "sha256:dummy",
            "axes": {},
        }
        body_no_managed = "# Title\n\nNo Slide N or Analysis headings here.\n"
        config, _ = _build_lib_with_one_evidence(
            tmp_path,
            enrich_meta=prior_enrich,
            body=body_no_managed,
        )
        result = diagnose_notes(config)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "managed_sections_unidentified"
        assert f.severity == "warning"

    def test_protect_managed_sections_first_time_omitted(self, tmp_path):
        # ED-2b: First-time-enrich note (no _llm_metadata.enrich) without
        # identifiable managed sections is OMITTED — falls through to
        # ("analyze", "eligible") because first-time enrichment creates
        # the managed sections.
        body_no_managed = "# Title\n\nNo Slide N or Analysis headings.\n"
        config, _ = _build_lib_with_one_evidence(tmp_path, body=body_no_managed)
        result = diagnose_notes(config)
        assert result.findings == ()

    def test_protect_curation_level(self, tmp_path):
        # ED-3: curation_level=L2 → protected_by_curation_level.
        config, _ = _build_lib_with_one_evidence(tmp_path, curation_level="L2")
        result = diagnose_notes(config)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "protected_by_curation_level"
        assert f.severity == "warning"
        assert f.detail == "curation_level=L2"

    def test_protect_review_status_reviewed(self, tmp_path):
        # ED-4: review_status=reviewed → protected_by_review_status.
        config, _ = _build_lib_with_one_evidence(tmp_path, review_status="reviewed")
        result = diagnose_notes(config)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "protected_by_review_status"
        assert f.severity == "warning"
        assert f.detail == "review_status=reviewed"

    def test_protect_review_status_overridden(self, tmp_path):
        # ED-4 (variant): review_status=overridden also surfaces.
        config, _ = _build_lib_with_one_evidence(tmp_path, review_status="overridden")
        result = diagnose_notes(config)
        assert len(result.findings) == 1
        assert result.findings[0].code == "protected_by_review_status"

    def test_conflict_managed_body_fingerprint_mismatch(self, tmp_path):
        # ED-5: stored fingerprint != current body fingerprint → conflict.
        prior_enrich = {
            "status": "executed",
            "spec_version": 1,
            "input_fingerprint": "sha256:dummy",
            "managed_body_fingerprint": "sha256:wrong_value",  # mismatch
            "axes": {},
        }
        config, _ = _build_lib_with_one_evidence(tmp_path, enrich_meta=prior_enrich)
        result = diagnose_notes(config)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "managed_body_conflict"
        assert f.severity == "error"
        assert f.detail == "managed body fingerprint mismatch"

    def test_analyze_stale(self, tmp_path):
        # ED-6: enrich.status=stale → enrich_status_stale info.
        prior_enrich = {
            "status": "stale",
            "spec_version": 1,
            "axes": {},
        }
        config, _ = _build_lib_with_one_evidence(tmp_path, enrich_meta=prior_enrich)
        result = diagnose_notes(config)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "enrich_status_stale"
        assert f.severity == "info"
        assert f.detail == "stale"


class TestHealthyOmission:
    def test_healthy_notes_omitted(self, tmp_path):
        # ED-7: clean L0 notes (eligible) yield no findings.
        config, _ = _build_lib_with_one_evidence(tmp_path)
        result = diagnose_notes(config)
        assert result.findings == ()
        assert result.summary.total == 0
        assert dict(result.summary.by_code) == {}
        assert result.summary.flagged_total == 0
        assert result.truncated is False


# ---------------------------------------------------------------------------
# ED-8..10: scope, limit, ordering
# ---------------------------------------------------------------------------

class TestScopeAndLimit:
    def _build_two_clients_with_protect_each(self, tmp_path):
        config = _make_config(tmp_path)
        for client in ("ClientA", "ClientB"):
            note_id = f"{client}_DD_Q1_evidence_x"
            rel = f"{client}/DD_Q1/evidence/x.md"
            content = _evidence_note(
                note_id=note_id, client=client, curation_level="L2",
            )
            _write(config.library_root, rel, content)
        _setup_registry(config.library_root, {
            f"{client}_DD_Q1_evidence_x": _registry_entry(
                f"{client}_DD_Q1_evidence_x",
                f"{client}/DD_Q1/evidence/x.md",
                client=client,
            )
            for client in ("ClientA", "ClientB")
        })
        return config

    def test_scope_filter_narrows(self, tmp_path):
        # ED-8: scope filter narrows correctly.
        config = self._build_two_clients_with_protect_each(tmp_path)
        result = diagnose_notes(config, scope="ClientA")
        assert len(result.findings) == 1
        assert result.findings[0].subject_id.startswith("ClientA")

    def test_scope_none_returns_all(self, tmp_path):
        config = self._build_two_clients_with_protect_each(tmp_path)
        result = diagnose_notes(config)
        assert len(result.findings) == 2

    def test_limit_truncation_post_sort(self, tmp_path):
        # ED-9: limit truncates after sort.
        config = _make_config(tmp_path)
        for i in range(5):
            note_id = f"ClientA_DD_Q1_evidence_{i:03d}"
            rel = f"ClientA/DD_Q1/evidence/n{i:03d}.md"
            content = _evidence_note(note_id=note_id, curation_level="L2")
            _write(config.library_root, rel, content)
        _setup_registry(config.library_root, {
            f"ClientA_DD_Q1_evidence_{i:03d}": _registry_entry(
                f"ClientA_DD_Q1_evidence_{i:03d}",
                f"ClientA/DD_Q1/evidence/n{i:03d}.md",
            ) for i in range(5)
        })
        result = diagnose_notes(config, limit=2)
        assert len(result.findings) == 2
        assert result.summary.total == 2
        assert result.truncated is True

    def test_deterministic_three_level_sort(self, tmp_path):
        # ED-10: severity desc, then code asc, then subject_id asc.
        # Build: 1 error (managed_body_conflict on note B), 2 warnings of
        # different codes (managed_sections_unidentified vs
        # protected_by_curation_level), checking that errors come first
        # and warnings group by code.
        config = _make_config(tmp_path)
        # One conflict (error)
        prior_enrich = {
            "status": "executed", "spec_version": 1,
            "input_fingerprint": "sha256:x",
            "managed_body_fingerprint": "sha256:wrong",
            "axes": {},
        }
        _write(config.library_root, "ClientA/DD_Q1/evidence/conflict.md",
               _evidence_note(note_id="z_conflict", enrich_meta=prior_enrich))
        # Two protected_by_curation_level (warning, code asc)
        for i in range(2):
            _write(config.library_root, f"ClientA/DD_Q1/evidence/cur{i}.md",
                   _evidence_note(note_id=f"a_cur{i}", curation_level="L2"))
        # Two managed_sections_unidentified (warning, comes before
        # protected_by_curation_level in alpha sort)
        prior_enrich_no_managed = {
            "status": "executed", "spec_version": 1,
            "input_fingerprint": "sha256:x",
            "managed_body_fingerprint": "sha256:y",
            "axes": {},
        }
        for i in range(2):
            _write(
                config.library_root,
                f"ClientA/DD_Q1/evidence/msu{i}.md",
                _evidence_note(
                    note_id=f"a_msu{i}",
                    enrich_meta=prior_enrich_no_managed,
                    body="# T\n\nNo managed sections here.\n",
                ),
            )
        _setup_registry(config.library_root, {
            "z_conflict": _registry_entry("z_conflict", "ClientA/DD_Q1/evidence/conflict.md"),
            "a_cur0": _registry_entry("a_cur0", "ClientA/DD_Q1/evidence/cur0.md"),
            "a_cur1": _registry_entry("a_cur1", "ClientA/DD_Q1/evidence/cur1.md"),
            "a_msu0": _registry_entry("a_msu0", "ClientA/DD_Q1/evidence/msu0.md"),
            "a_msu1": _registry_entry("a_msu1", "ClientA/DD_Q1/evidence/msu1.md"),
        })
        result = diagnose_notes(config)
        assert len(result.findings) == 5
        # First: error (conflict) — only one
        assert result.findings[0].severity == "error"
        assert result.findings[0].code == "managed_body_conflict"
        # Then warnings, code asc: managed_sections_unidentified (m...) before
        # protected_by_curation_level (p...)
        codes_after_error = [f.code for f in result.findings[1:]]
        assert codes_after_error == [
            "managed_sections_unidentified",
            "managed_sections_unidentified",
            "protected_by_curation_level",
            "protected_by_curation_level",
        ]
        # subject_id asc within code group
        msu_ids = [f.subject_id for f in result.findings[1:3]]
        assert msu_ids == sorted(msu_ids)
        cur_ids = [f.subject_id for f in result.findings[3:5]]
        assert cur_ids == sorted(cur_ids)


# ---------------------------------------------------------------------------
# ED-11: trust annotation
# ---------------------------------------------------------------------------

class TestTrustAnnotation:
    def test_trust_status_flagged_on_blocker(self, tmp_path):
        # ED-11: protect-class blocker on a flagged note → trust_status=flagged.
        config, _ = _build_lib_with_one_evidence(
            tmp_path, curation_level="L2", review_status="flagged",
        )
        result = diagnose_notes(config)
        assert len(result.findings) == 1
        assert result.findings[0].trust_status == "flagged"
        assert result.summary.flagged_total == 1

    def test_trust_status_ok_when_clean(self, tmp_path):
        config, _ = _build_lib_with_one_evidence(tmp_path, curation_level="L2")
        result = diagnose_notes(config)
        assert result.findings[0].trust_status == "ok"
        assert result.summary.flagged_total == 0


# ---------------------------------------------------------------------------
# ED-12..14: invariants and shape
# ---------------------------------------------------------------------------

class TestInvariants:
    def test_no_llm_imports_in_diagnose_path(self):
        # ED-12: no openai/anthropic imports in the diagnose code path.
        from folio import enrich as enrich_module
        source = Path(enrich_module.__file__).read_text()
        # Module-wide check (matches G-scope-4 manifest gate).
        assert "from openai" not in source
        assert "import openai" not in source
        assert "from anthropic" not in source
        assert "import anthropic" not in source

    def test_read_only_invariant(self, tmp_path):
        # ED-13: registry.json mtime + content unchanged after diagnose.
        config, _ = _build_lib_with_one_evidence(tmp_path, curation_level="L2")
        registry_path = config.library_root / "registry.json"
        before_mtime = registry_path.stat().st_mtime_ns
        before_content = registry_path.read_bytes()
        diagnose_notes(config)
        after_mtime = registry_path.stat().st_mtime_ns
        after_content = registry_path.read_bytes()
        assert before_mtime == after_mtime
        assert before_content == after_content

    def test_dataclass_frozen_and_field_order(self):
        # ED-14: DiagnoseFinding/Result/Summary are frozen dataclasses with
        # exact field order.
        finding_fields = [f.name for f in fields(DiagnoseFinding)]
        assert finding_fields == [
            "code", "severity", "subject_id", "detail",
            "recommended_action", "trust_status",
        ]
        result_fields = [f.name for f in fields(DiagnoseResult)]
        # DCB-1 closure (D.4): unfiltered_total added as 8th field.
        assert result_fields == [
            "schema_version", "command", "scope", "limit",
            "findings", "summary", "truncated", "unfiltered_total",
        ]
        summary_fields = [f.name for f in fields(DiagnoseSummary)]
        assert summary_fields == ["total", "by_code", "flagged_total"]
        # Frozen check
        f = DiagnoseFinding(
            code="x", severity="info", subject_id="s", detail="d",
            recommended_action="a", trust_status="ok",
        )
        with pytest.raises((AttributeError, Exception)):
            f.code = "y"  # type: ignore


# ---------------------------------------------------------------------------
# ED-15a/b/c/d: defensive defaults for unknown reasons / dispositions
# ---------------------------------------------------------------------------

def _synthetic_entry(disposition: str, reason: str, subject_id: str = "test_id",
                     review_status: str = "clean") -> EnrichPlanEntry:
    """Build a synthetic EnrichPlanEntry bypassing _determine_disposition."""
    from folio.tracking.registry import RegistryEntry
    entry = RegistryEntry(
        id=subject_id, title="t", markdown_path="x.md", deck_dir="x",
        type="evidence", client="C", engagement="E",
    )
    fm = {"id": subject_id, "review_status": review_status}
    doc = MarkdownDocument("# X\n")
    return EnrichPlanEntry(
        entry=entry, md_path=Path("x.md"), doc_type="evidence",
        disposition=disposition, reason=reason,
        existing_fm=fm, doc=doc,
    )


class TestDefensiveDefaults:
    def test_unknown_protect_reason(self):
        # ED-15a
        entry = _synthetic_entry("protect", "future_reason_xyz")
        f = _entry_to_finding(entry)
        assert f is not None
        assert f.code == "managed_sections_unidentified"
        assert f.severity == "warning"
        assert "Unrecognized protect reason: future_reason_xyz" in f.recommended_action

    def test_unknown_conflict_reason(self):
        # ED-15b
        entry = _synthetic_entry("conflict", "new_conflict_xyz")
        f = _entry_to_finding(entry)
        assert f is not None
        assert f.code == "managed_sections_unidentified"
        assert "Unrecognized conflict reason: new_conflict_xyz" in f.recommended_action

    def test_unknown_analyze_reason(self):
        # ED-15c
        entry = _synthetic_entry("analyze", "new_analyze_xyz")
        f = _entry_to_finding(entry)
        assert f is not None
        assert f.code == "managed_sections_unidentified"
        assert "Unrecognized analyze reason: new_analyze_xyz" in f.recommended_action

    def test_unknown_disposition_omitted_with_warning(self):
        # ED-15d
        entry = _synthetic_entry("rebuild", "anything")
        with pytest.warns(RuntimeWarning, match="Unrecognized disposition 'rebuild'"):
            f = _entry_to_finding(entry)
        assert f is None


# ---------------------------------------------------------------------------
# ED-16..20
# ---------------------------------------------------------------------------

class TestForbiddenSymbolsAndConstants:
    def test_no_forbidden_symbols_in_diagnose_path(self):
        # ED-16: whole-file substring grep on folio/enrich.py (matches G-scope-5).
        from folio import enrich as enrich_module
        source = Path(enrich_module.__file__).read_text()
        assert "derive_trust_status" not in source
        assert "from folio.links" not in source
        assert "import folio.links" not in source
        assert "--include-flagged" not in source
        assert "from openai" not in source
        assert "import openai" not in source
        assert "from anthropic" not in source
        assert "import anthropic" not in source

    def test_envelope_constants(self):
        # ED-17
        assert DIAGNOSE_SCHEMA_VERSION == "1.0"
        assert DIAGNOSE_COMMAND_NAME == "enrich diagnose"

    def test_summary_by_code_ordering(self, tmp_path):
        # ED-18: by_code keys sorted alphabetically.
        config = _make_config(tmp_path)
        # Mix of two protect-class codes
        _write(config.library_root, "ClientA/DD_Q1/evidence/c.md",
               _evidence_note(note_id="c_id", curation_level="L2"))
        _write(config.library_root, "ClientA/DD_Q1/evidence/r.md",
               _evidence_note(note_id="r_id", review_status="reviewed"))
        _setup_registry(config.library_root, {
            "c_id": _registry_entry("c_id", "ClientA/DD_Q1/evidence/c.md"),
            "r_id": _registry_entry("r_id", "ClientA/DD_Q1/evidence/r.md"),
        })
        result = diagnose_notes(config)
        keys = list(result.summary.by_code.keys())
        assert keys == sorted(keys)

    def test_truncated_flag(self, tmp_path):
        # ED-19
        config = _make_config(tmp_path)
        for i in range(3):
            _write(config.library_root, f"ClientA/DD_Q1/evidence/n{i}.md",
                   _evidence_note(note_id=f"n_{i}", curation_level="L2"))
        _setup_registry(config.library_root, {
            f"n_{i}": _registry_entry(
                f"n_{i}", f"ClientA/DD_Q1/evidence/n{i}.md",
            )
            for i in range(3)
        })
        # No limit
        r1 = diagnose_notes(config)
        assert r1.truncated is False
        # Limit > total
        r2 = diagnose_notes(config, limit=10)
        assert r2.truncated is False
        # Limit < total
        r3 = diagnose_notes(config, limit=2)
        assert r3.truncated is True

    def test_subject_id_is_deck_id_not_path(self, tmp_path):
        # ED-20
        config, _ = _build_lib_with_one_evidence(
            tmp_path,
            note_id="custom_deck_id_xyz",
            rel_path="ClientA/DD_Q1/evidence/anyname.md",
            curation_level="L2",
        )
        result = diagnose_notes(config)
        assert result.findings[0].subject_id == "custom_deck_id_xyz"
        assert "anyname.md" not in result.findings[0].subject_id


# ---------------------------------------------------------------------------
# ED-21..23: function-level validation + scope/registry errors
# ---------------------------------------------------------------------------

class TestValidation:
    def test_diagnose_notes_limit_validation(self, tmp_path):
        # ED-21
        config, _ = _build_lib_with_one_evidence(tmp_path)
        with pytest.raises(ValueError, match="limit must be >= 1 or None"):
            diagnose_notes(config, limit=0)
        with pytest.raises(ValueError, match="limit must be >= 1 or None"):
            diagnose_notes(config, limit=-1)
        # None and >=1 succeed
        diagnose_notes(config, limit=None)
        diagnose_notes(config, limit=1)

    def test_diagnose_notes_invalid_scope_raises(self, tmp_path):
        # ED-22
        config, _ = _build_lib_with_one_evidence(tmp_path)
        with pytest.raises(ScopeResolutionError, match="ClinetA_typo"):
            diagnose_notes(config, scope="ClinetA_typo")

    def test_diagnose_notes_corrupt_registry_raises(self, tmp_path):
        # ED-23
        config = _make_config(tmp_path)
        # Write a registry with the _corrupt flag
        registry_path = config.library_root / "registry.json"
        registry_path.write_text(json.dumps({"_corrupt": True, "decks": {}}))
        with pytest.raises(ScopeResolutionError, match="corrupt"):
            diagnose_notes(config, scope="any")


# ---------------------------------------------------------------------------
# ED-24: MappingProxyType immutability
# ---------------------------------------------------------------------------

class TestMappingProxyImmutability:
    def test_summary_by_code_is_immutable_mapping(self, tmp_path):
        # ED-24
        config, _ = _build_lib_with_one_evidence(tmp_path, curation_level="L2")
        result = diagnose_notes(config)
        assert isinstance(result.summary.by_code, MappingProxyType)
        with pytest.raises(TypeError):
            result.summary.by_code["new_code"] = 1  # type: ignore


# ---------------------------------------------------------------------------
# ED-25, ED-26: recommended_action substitution + frontmatter-edit text
# ---------------------------------------------------------------------------

class TestRecommendedActionText:
    def test_recommended_action_substitutes_subject_id(self, tmp_path):
        # ED-25: managed_body_conflict and enrich_status_stale must
        # substitute subject_id (no literal <scope> token).
        # Build a conflict note
        prior_enrich = {
            "status": "executed", "spec_version": 1,
            "input_fingerprint": "sha256:x",
            "managed_body_fingerprint": "sha256:wrong",
            "axes": {},
        }
        config, _ = _build_lib_with_one_evidence(
            tmp_path, note_id="my_unique_subject_id_42", enrich_meta=prior_enrich,
        )
        result = diagnose_notes(config)
        f = result.findings[0]
        assert f.code == "managed_body_conflict"
        assert "my_unique_subject_id_42" in f.recommended_action
        assert "<scope>" not in f.recommended_action

    def test_recommended_action_curation_review_text(self, tmp_path):
        # ED-26: curation/review_status action text mentions the manual
        # frontmatter-edit mechanism.
        # Curation
        config, _ = _build_lib_with_one_evidence(tmp_path, curation_level="L2")
        r = diagnose_notes(config)
        action = r.findings[0].recommended_action
        assert "edit the note's `curation_level` frontmatter field" in action
        assert "folio promote" not in action

    def test_recommended_action_review_status_text(self, tmp_path):
        config, _ = _build_lib_with_one_evidence(tmp_path, review_status="reviewed")
        r = diagnose_notes(config)
        action = r.findings[0].recommended_action
        assert "edit the note's `review_status` frontmatter field" in action
        # PROD-SF-002: action must clarify that no folio unflag command exists.
        assert "no `folio unflag` command exists today" in action


# ---------------------------------------------------------------------------
# ED-27: review_status=flagged alone is omitted
# ---------------------------------------------------------------------------

class TestFlaggedAloneOmitted:
    def test_review_status_flagged_alone_omitted(self, tmp_path):
        # ED-27: A note with review_status: flagged AND no other blocker
        # is OMITTED — diagnose surfaces blockers, not flagged-note census.
        # (Note: review_status="flagged" is NOT a protect trigger; only
        # "reviewed" / "overridden" are.)
        config, _ = _build_lib_with_one_evidence(tmp_path, review_status="flagged")
        result = diagnose_notes(config)
        assert result.findings == ()


# ---------------------------------------------------------------------------
# Sort key direct test
# ---------------------------------------------------------------------------

class TestSortKey:
    def test_finding_sort_key_three_level(self):
        f1 = DiagnoseFinding(
            code="aaa", severity="error", subject_id="z",
            detail="d", recommended_action="a", trust_status="ok",
        )
        f2 = DiagnoseFinding(
            code="aaa", severity="warning", subject_id="a",
            detail="d", recommended_action="a", trust_status="ok",
        )
        # Error sorts before warning regardless of subject_id
        assert _finding_sort_key(f1) < _finding_sort_key(f2)
