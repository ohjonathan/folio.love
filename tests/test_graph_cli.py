"""Graph status and doctor tests."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from folio.analysis_docs import compute_graph_input_fingerprint
from folio.cli import cli
from folio.pipeline.enrich_data import compute_relationship_proposal_id
from folio.tracking.registry import RegistryEntry


def _make_config(path: Path, library_root: Path) -> None:
    path.write_text(yaml.dump({"library_root": str(library_root)}, default_flow_style=False))


def _write_registry(library_root: Path, entries: dict[str, dict]) -> None:
    payload = {
        "_schema_version": 1,
        "updated_at": "2026-04-01T00:00:00Z",
        "decks": entries,
    }
    (library_root / "registry.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_entities(library_root: Path, payload: dict) -> None:
    (library_root / "entities.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _entry(note_id: str, markdown_path: str, *, note_type: str = "evidence", title: str | None = None, modified: str | None = None) -> dict:
    entry = {
        "id": note_id,
        "title": title or note_id,
        "type": note_type,
        "markdown_path": markdown_path,
        "deck_dir": str(Path(markdown_path).parent).replace("\\", "/"),
        "client": "ClientA",
        "engagement": "DD_Q1",
    }
    if note_type in {"context", "analysis"}:
        if modified is not None:
            entry["modified"] = modified
    else:
        entry.update(
            {
                "source_relative_path": "deck.pptx",
                "source_hash": f"{note_id}-hash",
                "version": 1,
                "converted": "2026-04-01T00:00:00Z",
            }
        )
    return entry


def _write_note(path: Path, frontmatter: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{yaml_str}---\n\n# {frontmatter['title']}\n", encoding="utf-8")


def _base_fm(note_id: str, title: str, *, note_type: str = "evidence", **overrides) -> dict:
    fm = {
        "id": note_id,
        "title": title,
        "type": note_type,
        "status": "active",
        "client": "ClientA",
        "engagement": "DD_Q1",
        "created": "2026-04-01",
        "modified": "2026-04-01",
    }
    if note_type not in {"context", "analysis"}:
        fm.update(
            {
                "curation_level": "L0",
                "review_status": "clean",
                "source": "deck.pptx",
                "source_hash": f"{note_id}-hash",
                "version": 1,
            }
        )
    fm.update(overrides)
    return fm


def test_graph_status_reports_expected_aggregate_counts(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    pending_source = "clienta_evidence_pending"
    orphan_doc = "clienta_evidence_orphan"
    protected_doc = "clienta_evidence_protected"
    analysis_doc = "clienta_analysis_synthesis"
    context_doc = "clienta_ddq1_context_20260401_engagement"

    stale_input_entry = RegistryEntry(
        id=context_doc,
        title="Context",
        markdown_path="ClientA/_context.md",
        deck_dir="ClientA",
        type="context",
        modified="2026-04-01",
        client="ClientA",
        engagement="DD_Q1",
    )
    stale_fp = compute_graph_input_fingerprint([stale_input_entry])

    _write_registry(
        library,
        {
            pending_source: _entry(pending_source, "ClientA/pending.md"),
            orphan_doc: _entry(orphan_doc, "ClientA/orphan.md"),
            protected_doc: _entry(protected_doc, "ClientA/protected.md"),
            analysis_doc: _entry(analysis_doc, "ClientA/analysis.md", note_type="analysis", modified="2026-04-02"),
            context_doc: _entry(context_doc, "ClientA/_context.md", note_type="context", modified="2026-04-02"),
        },
    )

    pending_proposal_id = compute_relationship_proposal_id(
        source_id=pending_source,
        relation="impacts",
        target_id=orphan_doc,
        basis_fingerprint="sha256:pending",
    )
    _write_note(
        library / "ClientA" / "pending.md",
        _base_fm(
            pending_source,
            "Pending",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                {
                                    "proposal_id": pending_proposal_id,
                                    "relation": "impacts",
                                    "target_id": orphan_doc,
                                    "basis_fingerprint": "sha256:pending",
                                    "confidence": "medium",
                                    "signals": ["shared_topic"],
                                    "rationale": "pending rationale",
                                    "status": "pending_human_confirmation",
                                    "producer": "enrich",
                                }
                            ]
                        }
                    }
                }
            },
        ),
    )
    _write_note(
        library / "ClientA" / "orphan.md",
        _base_fm(orphan_doc, "Orphan", supersedes="missing_target_doc"),
    )
    _write_note(
        library / "ClientA" / "protected.md",
        _base_fm(
            protected_doc,
            "Protected",
            _llm_metadata={"enrich": {"axes": {"body": {"status": "skipped_protected"}}}},
        ),
    )
    _write_note(
        library / "ClientA" / "_context.md",
        _base_fm(context_doc, "Context", note_type="context"),
    )
    _write_note(
        library / "ClientA" / "analysis.md",
        _base_fm(
            analysis_doc,
            "Analysis",
            note_type="analysis",
            draws_from=[context_doc],
            _llm_metadata={"graph": {"input_fingerprint": stale_fp}},
        ),
    )

    _write_entities(
        library,
        {
            "_schema_version": 1,
            "updated_at": "2026-04-01T00:00:00Z",
            "entities": {
                "person": {
                    "alice_chen": {
                        "canonical_name": "Alice Chen",
                        "type": "person",
                        "aliases": [],
                        "needs_confirmation": False,
                        "source": "import",
                        "first_seen": "2026-04-01T00:00:00Z",
                        "created_at": "2026-04-01T00:00:00Z",
                        "updated_at": "2026-04-01T00:00:00Z",
                    },
                    "chen_alice": {
                        "canonical_name": "Chen, Alice",
                        "type": "person",
                        "aliases": [],
                        "needs_confirmation": False,
                        "source": "import",
                        "first_seen": "2026-04-01T00:00:00Z",
                        "created_at": "2026-04-01T00:00:00Z",
                        "updated_at": "2026-04-01T00:00:00Z",
                    },
                    "bob_example": {
                        "canonical_name": "Bob Example",
                        "type": "person",
                        "aliases": [],
                        "needs_confirmation": True,
                        "source": "extracted",
                        "first_seen": "2026-04-01T00:00:00Z",
                        "created_at": "2026-04-01T00:00:00Z",
                        "updated_at": "2026-04-01T00:00:00Z",
                    },
                },
                "department": {},
                "system": {},
                "process": {},
            },
        },
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "graph", "status"])
    assert result.exit_code == 0
    assert "Pending relationship proposals: 1" in result.output
    assert "Docs without canonical graph links: 2" in result.output
    assert "Orphaned canonical relation targets: 1" in result.output
    assert "Enrich-protected notes: 1" in result.output
    assert "Unconfirmed entities: 1" in result.output
    assert "Confirmed entities missing stubs: 2" in result.output
    assert "Duplicate person candidates: 1" in result.output
    assert "Stale analysis artifacts: 1" in result.output


def test_graph_doctor_json_uses_fixed_finding_schema(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    pending_source = "clienta_evidence_pending"
    orphan_doc = "clienta_evidence_orphan"
    protected_doc = "clienta_evidence_protected"
    analysis_doc = "clienta_analysis_synthesis"
    context_doc = "clienta_ddq1_context_20260401_engagement"

    stale_input_entry = RegistryEntry(
        id=context_doc,
        title="Context",
        markdown_path="ClientA/_context.md",
        deck_dir="ClientA",
        type="context",
        modified="2026-04-01",
        client="ClientA",
        engagement="DD_Q1",
    )
    stale_fp = compute_graph_input_fingerprint([stale_input_entry])

    _write_registry(
        library,
        {
            pending_source: _entry(pending_source, "ClientA/pending.md"),
            orphan_doc: _entry(orphan_doc, "ClientA/orphan.md"),
            protected_doc: _entry(protected_doc, "ClientA/protected.md"),
            analysis_doc: _entry(analysis_doc, "ClientA/analysis.md", note_type="analysis", modified="2026-04-02"),
            context_doc: _entry(context_doc, "ClientA/_context.md", note_type="context", modified="2026-04-02"),
        },
    )
    _write_note(
        library / "ClientA" / "pending.md",
        _base_fm(
            pending_source,
            "Pending",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                {
                                    "proposal_id": compute_relationship_proposal_id(
                                        source_id=pending_source,
                                        relation="impacts",
                                        target_id=orphan_doc,
                                        basis_fingerprint="sha256:pending",
                                    ),
                                    "relation": "impacts",
                                    "target_id": orphan_doc,
                                    "basis_fingerprint": "sha256:pending",
                                    "confidence": "medium",
                                    "signals": [],
                                    "rationale": "pending rationale",
                                    "status": "pending_human_confirmation",
                                    "producer": "enrich",
                                }
                            ]
                        }
                    }
                }
            },
        ),
    )
    _write_note(library / "ClientA" / "orphan.md", _base_fm(orphan_doc, "Orphan", supersedes="missing_target_doc"))
    _write_note(
        library / "ClientA" / "protected.md",
        _base_fm(
            protected_doc,
            "Protected",
            _llm_metadata={"enrich": {"axes": {"body": {"status": "skipped_protected"}}}},
        ),
    )
    _write_note(library / "ClientA" / "_context.md", _base_fm(context_doc, "Context", note_type="context"))
    _write_note(
        library / "ClientA" / "analysis.md",
        _base_fm(
            analysis_doc,
            "Analysis",
            note_type="analysis",
            draws_from=[context_doc],
            _llm_metadata={"graph": {"input_fingerprint": stale_fp}},
        ),
    )
    _write_entities(
        library,
        {
            "_schema_version": 1,
            "updated_at": "2026-04-01T00:00:00Z",
            "entities": {
                "person": {
                    "alice_chen": {
                        "canonical_name": "Alice Chen",
                        "type": "person",
                        "aliases": [],
                        "needs_confirmation": False,
                        "source": "import",
                        "first_seen": "2026-04-01T00:00:00Z",
                        "created_at": "2026-04-01T00:00:00Z",
                        "updated_at": "2026-04-01T00:00:00Z",
                    },
                    "chen_alice": {
                        "canonical_name": "Chen, Alice",
                        "type": "person",
                        "aliases": [],
                        "needs_confirmation": False,
                        "source": "import",
                        "first_seen": "2026-04-01T00:00:00Z",
                        "created_at": "2026-04-01T00:00:00Z",
                        "updated_at": "2026-04-01T00:00:00Z",
                    },
                    "bob_example": {
                        "canonical_name": "Bob Example",
                        "type": "person",
                        "aliases": [],
                        "needs_confirmation": True,
                        "source": "extracted",
                        "first_seen": "2026-04-01T00:00:00Z",
                        "created_at": "2026-04-01T00:00:00Z",
                        "updated_at": "2026-04-01T00:00:00Z",
                    },
                },
                "department": {},
                "system": {},
                "process": {},
            },
        },
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "graph", "doctor", "--json"])
    assert result.exit_code == 0

    findings = json.loads(result.output)
    assert findings
    assert all(
        set(finding.keys()) == {"code", "severity", "subject_id", "detail", "recommended_action"}
        for finding in findings
    )
    assert {
        "pending_relationship_proposal",
        "orphaned_canonical_relation",
        "protected_enrich_body",
        "stale_analysis_artifact",
        "unconfirmed_entity",
        "missing_entity_stub",
        "duplicate_person_candidate",
    }.issubset({finding["code"] for finding in findings})
