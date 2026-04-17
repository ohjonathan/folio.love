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
                                    "lifecycle_state": "queued",
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
    assert "Reviewable duplicate person candidates: 1" in result.output
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
                                    "lifecycle_state": "queued",
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

    payload = json.loads(result.output)
    assert isinstance(payload, dict)
    assert set(payload.keys()) == {
        "findings",
        "producer_acceptance_rates",
        "producer_acceptance_rates_data_integrity",
    }
    findings = payload["findings"]
    assert findings
    # v0.7.1: schema branches by finding["code"]. Pending-proposal findings carry
    # the §5 shared-contract shape (15 keys); non-proposal findings keep the
    # legacy 5-key shape.
    _legacy_keys = {"code", "severity", "subject_id", "detail", "recommended_action"}
    _proposal_extra_keys = {
        "proposal_id",
        "proposal_type",
        "source_id",
        "target_id",
        "evidence_bundle",
        "reason_summary",
        "trust_status",
        "schema_gate_result",
        "producer",
        "input_fingerprint",
        "lifecycle_state",
    }
    for finding in findings:
        if finding["code"] == "pending_relationship_proposal":
            assert set(finding.keys()) == _legacy_keys | _proposal_extra_keys
        else:
            assert set(finding.keys()) == _legacy_keys
    assert {
        "pending_relationship_proposal",
        "orphaned_canonical_relation",
        "protected_enrich_body",
        "stale_analysis_artifact",
        "unconfirmed_entity",
        "missing_entity_stub",
        "duplicate_person_candidate",
    }.issubset({finding["code"] for finding in findings})
    assert isinstance(payload["producer_acceptance_rates"], list)
    assert payload["producer_acceptance_rates_data_integrity"] == {"missing_producer_count": 0}


# ---------------------------------------------------------------------------
# Phase C (v0.6.0): cumulative acceptance-rate aggregator tests.
# ---------------------------------------------------------------------------


def _rejected(target_id: str, basis_fp: str, *, producer: str = "enrich") -> dict:
    return {
        "proposal_id": f"rej-{basis_fp}",
        "relation": "impacts",
        "target_id": target_id,
        "basis_fingerprint": basis_fp,
        "confidence": "medium",
        "signals": [],
        "rationale": "",
        "lifecycle_state": "rejected",
        "producer": producer,
    }


def _confirmed_record(target_id: str, *, producer: str = "enrich", include_producer: bool = True) -> dict:
    record = {
        "relation": "impacts",
        "target_id": target_id,
        "basis_fingerprint": f"sha256:{target_id}",
        "confirmed_at": "2026-04-15T00:00:00+00:00",
    }
    if include_producer:
        record["producer"] = producer
    return record


def _setup_aggregator_library(
    tmp_path: Path,
    source_id: str,
    *,
    rejected_by_producer: dict[str, int] | None = None,
    confirmed_by_producer: dict[str, int] | None = None,
    confirmed_missing_producer: int = 0,
) -> Path:
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    target_id = f"{source_id}_target"
    _write_registry(
        library,
        {
            source_id: _entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_fm(target_id, target_id))

    metadata: dict = {}
    rejected_by_producer = rejected_by_producer or {}
    for producer, count in rejected_by_producer.items():
        metadata[producer] = {"axes": {"relationships": {"proposals": [_rejected(target_id, f"sha256:{producer}-r{i}", producer=producer) for i in range(count)]}}}

    confirmed_list: list[dict] = []
    confirmed_by_producer = confirmed_by_producer or {}
    for producer, count in confirmed_by_producer.items():
        for i in range(count):
            confirmed_list.append(_confirmed_record(target_id, producer=producer))
    for i in range(confirmed_missing_producer):
        confirmed_list.append(_confirmed_record(target_id, include_producer=False))
    if confirmed_list:
        metadata.setdefault("links", {})["confirmed_relationships"] = confirmed_list

    _write_note(
        library / "ClientA" / f"{source_id}.md",
        _base_fm(source_id, "Source", _llm_metadata=metadata),
    )
    return config_path


def _aggregate(config_path: Path):
    from folio.config import FolioConfig
    from folio.graph import _aggregate_producer_acceptance_rates

    return _aggregate_producer_acceptance_rates(FolioConfig.load(config_path))


def test_doctor_acceptance_rate_above_gate(tmp_path):
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_s1",
        confirmed_by_producer={"enrich": 12},
        rejected_by_producer={"enrich": 4},
    )
    rates, missing = _aggregate(config_path)
    assert missing == 0
    assert len(rates) == 1
    assert rates[0].producer == "enrich"
    assert rates[0].accepted == 12 and rates[0].rejected == 4
    assert rates[0].total_reviewed == 16
    assert rates[0].rate == 0.75
    assert rates[0].status == "ok"
    assert rates[0].warmup is False


def test_doctor_acceptance_rate_low_acceptance(tmp_path):
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_s2",
        confirmed_by_producer={"enrich": 2},
        rejected_by_producer={"enrich": 8},
    )
    rates, _ = _aggregate(config_path)
    assert len(rates) == 1
    assert rates[0].rate == 0.20
    assert rates[0].status == "low-acceptance"
    assert rates[0].warmup is False


def test_doctor_acceptance_rate_in_warmup(tmp_path):
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_s3",
        confirmed_by_producer={"enrich": 2},
        rejected_by_producer={"enrich": 3},
    )
    rates, _ = _aggregate(config_path)
    assert len(rates) == 1
    assert rates[0].total_reviewed == 5
    assert rates[0].rate is None
    assert rates[0].status == "warmup"
    assert rates[0].warmup is True


def test_doctor_acceptance_rate_boundary_at_exactly_0_5(tmp_path):
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_s4",
        confirmed_by_producer={"enrich": 10},
        rejected_by_producer={"enrich": 10},
    )
    rates, _ = _aggregate(config_path)
    assert len(rates) == 1
    assert rates[0].rate == 0.50
    assert rates[0].status == "ok"  # strict-less-than threshold


def test_doctor_aggregator_handles_missing_producer_field(tmp_path):
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_s5",
        confirmed_by_producer={"enrich": 2},
        rejected_by_producer={"enrich": 1},
        confirmed_missing_producer=1,
    )
    rates, missing = _aggregate(config_path)
    assert missing == 1
    # 2 accepted + 1 rejected = 3 reviewed → warmup
    assert len(rates) == 1
    assert rates[0].total_reviewed == 3
    assert rates[0].warmup is True


def test_doctor_text_rendering_order_and_scope_note(tmp_path):
    source_id = "clienta_evidence_render"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    target_id = f"{source_id}_target"
    _write_registry(
        library,
        {
            source_id: _entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_fm(target_id, target_id))

    # Producer "a" is low-acceptance; "b" is ok; "c" is warmup.
    metadata = {
        "a": {"axes": {"relationships": {"proposals": [_rejected(target_id, f"sha256:a-r{i}", producer="a") for i in range(8)]}}},
        "b": {"axes": {"relationships": {"proposals": [_rejected(target_id, f"sha256:b-r{i}", producer="b") for i in range(3)]}}},
        "c": {"axes": {"relationships": {"proposals": [_rejected(target_id, f"sha256:c-r{i}", producer="c") for i in range(1)]}}},
        "links": {
            "confirmed_relationships": (
                [_confirmed_record(target_id, producer="a") for _ in range(2)]
                + [_confirmed_record(target_id, producer="b") for _ in range(17)]
                + [_confirmed_record(target_id, producer="c") for _ in range(1)]
            )
        },
    }
    _write_note(library / "ClientA" / f"{source_id}.md", _base_fm(source_id, "S", _llm_metadata=metadata))

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "graph", "doctor"])
    assert result.exit_code == 0
    out = result.output
    assert "### Producer acceptance rates" in out
    # Row ordering: low-acceptance first, then ok, then warmup.
    idx_a = out.index("| a |")
    idx_b = out.index("| b |")
    idx_c = out.index("| c |")
    assert idx_a < idx_b < idx_c
    assert "low-acceptance (< 50%)" in out
    assert "warmup (< 10 reviewed)" in out
    assert (
        "Status column is informational only in v0.6.0; `low-acceptance` "
        "producers continue to surface proposals at normal priority in this slice."
    ) in out


def test_doctor_empty_state_rendering(tmp_path):
    source_id = "clienta_evidence_empty"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(library, {source_id: _entry(source_id, f"ClientA/{source_id}.md")})
    _write_note(library / "ClientA" / f"{source_id}.md", _base_fm(source_id, "S"))

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "graph", "doctor"])
    assert result.exit_code == 0
    assert "### Producer acceptance rates" in result.output
    assert "No producer acceptance-rate data yet." in result.output


def test_doctor_json_schema_producer_acceptance_rates(tmp_path):
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_json",
        confirmed_by_producer={"enrich": 8},
        rejected_by_producer={"enrich": 2},
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "graph", "doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload.keys()) == {"findings", "producer_acceptance_rates", "producer_acceptance_rates_data_integrity"}
    rates = payload["producer_acceptance_rates"]
    assert len(rates) == 1
    r = rates[0]
    assert set(r.keys()) == {"producer", "accepted", "rejected", "total_reviewed", "rate", "status", "warmup"}
    assert r["producer"] == "enrich"
    assert r["rate"] == 0.80
    assert r["status"] == "ok"
    assert r["warmup"] is False


def test_doctor_json_warmup_rate_is_null(tmp_path):
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_jsonwu",
        confirmed_by_producer={"enrich": 1},
        rejected_by_producer={"enrich": 1},
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "graph", "doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    rates = payload["producer_acceptance_rates"]
    assert len(rates) == 1
    assert rates[0]["rate"] is None
    assert rates[0]["status"] == "warmup"
    assert rates[0]["warmup"] is True


# ---------------------------------------------------------------------------
# Phase D.4 (v0.6.0): fix regression tests per D.3 canonical verdict.
# ---------------------------------------------------------------------------


def test_doctor_aggregator_reads_both_sources(tmp_path):
    """DB-4 explicit: aggregator reads rejections from producer list AND acceptances from links.confirmed_relationships."""
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_both",
        confirmed_by_producer={"enrich": 3},
        rejected_by_producer={"enrich": 2},
    )
    rates, _ = _aggregate(config_path)
    assert len(rates) == 1
    assert rates[0].accepted == 3
    assert rates[0].rejected == 2
    assert rates[0].total_reviewed == 5  # catches PR-A-15: both sources counted.


def test_doctor_aggregator_excludes_suppressed_and_stale(tmp_path):
    """DB-4 explicit: future-proof — suppressed / stale lifecycle_states are not counted.

    This test asserts future-proof aggregator behavior; if the lifecycle model changes,
    re-verify the intent before updating the test.
    """
    source_id = "clienta_evidence_suppr"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    target_id = f"{source_id}_target"
    _write_registry(
        library,
        {
            source_id: _entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_fm(target_id, target_id))

    proposals = [
        _rejected(target_id, "sha256:r1", producer="enrich"),
        _rejected(target_id, "sha256:r2", producer="enrich"),
        # suppressed and stale entries must not count toward total_reviewed
        {"proposal_id": "s1", "relation": "impacts", "target_id": target_id,
         "basis_fingerprint": "sha256:s1", "confidence": "medium", "signals": [],
         "rationale": "", "lifecycle_state": "suppressed", "producer": "enrich"},
        {"proposal_id": "s2", "relation": "impacts", "target_id": target_id,
         "basis_fingerprint": "sha256:s2", "confidence": "medium", "signals": [],
         "rationale": "", "lifecycle_state": "stale", "producer": "enrich"},
    ]
    confirmed = [_confirmed_record(target_id, producer="enrich") for _ in range(2)]
    metadata = {
        "enrich": {"axes": {"relationships": {"proposals": proposals}}},
        "links": {"confirmed_relationships": confirmed},
    }
    _write_note(library / "ClientA" / f"{source_id}.md", _base_fm(source_id, "S", _llm_metadata=metadata))

    rates, _ = _aggregate(config_path)
    assert len(rates) == 1
    # Accepted=2 + Rejected=2 = 4; suppressed/stale are NOT counted
    assert rates[0].total_reviewed == 4


def test_doctor_aggregator_skips_links_namespace(tmp_path):
    """DB-4 explicit: aggregator does not enumerate `_llm_metadata.links` as a producer."""
    source_id = "clienta_evidence_links_ns"
    target_id = f"{source_id}_target"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(
        library,
        {
            source_id: _entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_fm(target_id, target_id))

    # Construct a frontmatter where _llm_metadata.links ALSO has an axes.relationships
    # tree (unusual / pathological). Aggregator must skip it.
    metadata = {
        "links": {
            "confirmed_relationships": [_confirmed_record(target_id, producer="enrich")],
            # Pathological: some future code might have written a producer-like tree here.
            "axes": {"relationships": {"proposals": [_rejected(target_id, "sha256:leak", producer="links")]}},
        },
        "enrich": {"axes": {"relationships": {"proposals": [_rejected(target_id, "sha256:ok-rej")]}}},
    }
    _write_note(library / "ClientA" / f"{source_id}.md", _base_fm(source_id, "S", _llm_metadata=metadata))

    rates, _ = _aggregate(config_path)
    # Only "enrich" should appear — never "links".
    assert [r.producer for r in rates] == ["enrich"]


def test_graph_status_post_migration_line_84(tmp_path):
    """DB-4 explicit regression: folio/graph.py graph_status survives tuple-return migration."""
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_gs",
        confirmed_by_producer={"enrich": 0},
        rejected_by_producer={"enrich": 0},
    )
    from folio.config import FolioConfig
    from folio.graph import graph_status

    status = graph_status(FolioConfig.load(config_path))
    # No crash. No pending proposals in this fixture.
    assert status.pending_relationship_proposals == 0


def test_graph_status_post_migration_line_150(tmp_path):
    """DB-4 explicit regression: folio/graph.py graph_doctor pending-path survives tuple-return migration."""
    config_path = _setup_aggregator_library(
        tmp_path,
        "clienta_evidence_gd",
        confirmed_by_producer={"enrich": 0},
        rejected_by_producer={"enrich": 0},
    )
    from folio.config import FolioConfig
    from folio.graph import graph_doctor

    findings = graph_doctor(FolioConfig.load(config_path))
    # No crash. Return a list of dicts (possibly empty) — not the collect_pending tuple.
    assert isinstance(findings, list)


# -----------------------------------------------------------------------------
# v0.7.1 — §5 shared-proposal-contract retrofit (slice 6b.1)
# -----------------------------------------------------------------------------


def _build_minimal_pending_library(
    tmp_path: Path,
    *,
    relation: str = "draws_from",
    target_id: str = "clienta_evidence_target",
    target_present: bool = True,
    flagged_target: bool = False,
    flagged_source: bool = False,
    basis_fingerprint: str = "sha256:pending-abc",
) -> tuple[Path, Path, str, str]:
    """Minimal library with one pending relationship proposal.

    Returns (config_path, library, source_id, proposal_id).
    """
    library = tmp_path / "library"
    library.mkdir(exist_ok=True)
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_id = "clienta_evidence_source"

    registry_entries: dict[str, dict] = {
        source_id: _entry(source_id, "ClientA/source.md"),
    }
    if target_present:
        registry_entries[target_id] = _entry(target_id, "ClientA/target.md")

    _write_registry(library, registry_entries)

    proposal_id = compute_relationship_proposal_id(
        source_id=source_id,
        relation=relation,
        target_id=target_id,
        basis_fingerprint=basis_fingerprint,
    )

    source_overrides: dict = {}
    if flagged_source:
        source_overrides["review_status"] = "flagged"

    _write_note(
        library / "ClientA" / "source.md",
        _base_fm(
            source_id,
            "Source",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                {
                                    "proposal_id": proposal_id,
                                    "relation": relation,
                                    "target_id": target_id,
                                    "basis_fingerprint": basis_fingerprint,
                                    "confidence": "medium",
                                    "signals": ["shared_topic"],
                                    "rationale": "Both docs reference the shared framework.",
                                    "lifecycle_state": "queued",
                                    "producer": "enrich",
                                }
                            ]
                        }
                    }
                }
            },
            **source_overrides,
        ),
    )
    if target_present:
        target_overrides: dict = {}
        if flagged_target:
            target_overrides["review_status"] = "flagged"
        _write_note(
            library / "ClientA" / "target.md",
            _base_fm(target_id, "Target", **target_overrides),
        )

    _write_entities(library, {"_schema_version": 1, "updated_at": "2026-04-01T00:00:00Z", "entities": {}})
    return config_path, library, source_id, proposal_id


def _doctor_json(config_path: Path, *, include_flagged: bool = False) -> dict:
    runner = CliRunner()
    args = ["--config", str(config_path), "graph", "doctor", "--json"]
    if include_flagged:
        args.append("--include-flagged")
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _doctor_stdout(config_path: Path, *, include_flagged: bool = False) -> str:
    runner = CliRunner()
    args = ["--config", str(config_path), "graph", "doctor"]
    if include_flagged:
        args.append("--include-flagged")
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    return result.output


def _pending_finding(payload: dict) -> dict:
    findings = payload["findings"]
    matches = [f for f in findings if f["code"] == "pending_relationship_proposal"]
    assert matches, f"no pending_relationship_proposal in findings: {findings}"
    return matches[0]


def test_graph_doctor_fixture_mandatory_contract_invariant(tmp_path):
    """G-cardinality-1: pending-proposal findings carry all 11 shared-contract
    keys + proposal_id. schema_gate_result shape uses key-subset semantics
    per B2 additive-extension contract."""
    from folio.graph import _SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS

    config_path, *_ = _build_minimal_pending_library(tmp_path)
    payload = _doctor_json(config_path)
    finding = _pending_finding(payload)
    for key in _SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS:
        assert key in finding, f"§5 key {key!r} missing"
    assert "proposal_id" in finding
    gate = finding["schema_gate_result"]
    if gate is not None:
        # Key-subset (not exact) per v1.2 ADV-R2-SF1 closure.
        assert set(gate.keys()) >= {"status", "rule"}


def test_graph_doctor_proposal_id_preserves_view_proposal_id(tmp_path):
    """G-cardinality-2: proposal_id surfaces the view's proposal_id."""
    config_path, _library, _source, proposal_id = _build_minimal_pending_library(tmp_path)
    payload = _doctor_json(config_path)
    finding = _pending_finding(payload)
    assert finding["proposal_id"] == proposal_id
    assert finding["subject_id"] is None  # §5 semantics


def test_graph_doctor_proposal_type_is_relationship(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path)
    finding = _pending_finding(_doctor_json(config_path))
    assert finding["proposal_type"] == "relationship"


def test_graph_doctor_trust_status_ok_when_not_flagged(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path)
    finding = _pending_finding(_doctor_json(config_path))
    assert finding["trust_status"] == "ok"


def test_graph_doctor_trust_status_flagged_when_source_flagged(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path, flagged_source=True)
    finding = _pending_finding(_doctor_json(config_path, include_flagged=True))
    assert finding["trust_status"] == "flagged"


def test_graph_doctor_trust_status_flagged_when_target_flagged(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path, flagged_target=True)
    finding = _pending_finding(_doctor_json(config_path, include_flagged=True))
    assert finding["trust_status"] == "flagged"


def test_graph_doctor_schema_gate_target_registered_pass(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path, target_present=True)
    finding = _pending_finding(_doctor_json(config_path))
    assert finding["schema_gate_result"] is None


def test_graph_doctor_schema_gate_target_registered_fail(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path, target_present=False)
    finding = _pending_finding(_doctor_json(config_path))
    gate = finding["schema_gate_result"]
    assert gate is not None
    assert set(gate.keys()) >= {"status", "rule"}
    assert gate["status"] == "fail"
    assert gate["rule"] == "target_registered"


def test_graph_doctor_evidence_bundle_is_signals_list(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path)
    finding = _pending_finding(_doctor_json(config_path))
    assert finding["evidence_bundle"] == ["shared_topic"]


def test_graph_doctor_reason_summary_is_rationale(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path)
    finding = _pending_finding(_doctor_json(config_path))
    assert finding["reason_summary"] == "Both docs reference the shared framework."


def test_graph_doctor_lifecycle_state_surfaced(tmp_path):
    from folio.pipeline.enrich_data import PROPOSAL_LIFECYCLE_STATES

    config_path, *_ = _build_minimal_pending_library(tmp_path)
    finding = _pending_finding(_doctor_json(config_path))
    assert finding["lifecycle_state"] in PROPOSAL_LIFECYCLE_STATES


def test_graph_doctor_legacy_keys_preserved(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path)
    finding = _pending_finding(_doctor_json(config_path))
    for legacy in ("code", "severity", "detail", "recommended_action"):
        assert legacy in finding


def test_graph_doctor_cli_json_surfaces_contract(tmp_path):
    """P-5 closure: --json serializes every contract key."""
    from folio.graph import _SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS

    config_path, *_ = _build_minimal_pending_library(tmp_path)
    payload = _doctor_json(config_path)
    finding = _pending_finding(payload)
    for key in _SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS:
        assert key in finding
    assert "proposal_id" in finding


def test_graph_doctor_cli_stdout_renders_proposal_id(tmp_path):
    """G-test-3 / PRD-1 / P-1 / P-R2-2 regression guard: stdout renders
    proposal_id, not literal 'None' or an empty string."""
    config_path, _library, _source, proposal_id = _build_minimal_pending_library(tmp_path)
    stdout = _doctor_stdout(config_path)
    assert proposal_id in stdout
    # No literal "None" subject rendering.
    assert "pending_relationship_proposal None:" not in stdout
    # No empty-subject rendering (space between code and colon).
    assert "pending_relationship_proposal :" not in stdout


def test_graph_doctor_cli_stdout_renders_flagged_annotation(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path, flagged_source=True)
    stdout = _doctor_stdout(config_path, include_flagged=True)
    assert "[flagged]" in stdout


def test_graph_doctor_cli_stdout_renders_schema_gate_annotation_on_severity_line(tmp_path):
    """ADV-R2-M1: annotation is on the severity line, not in detail."""
    config_path, *_ = _build_minimal_pending_library(tmp_path, target_present=False)
    stdout = _doctor_stdout(config_path)
    assert "[schema-gate: target_registered]" in stdout
    # Annotation lives on the same line as severity/code.
    for line in stdout.splitlines():
        if "pending_relationship_proposal" in line:
            assert "[schema-gate: target_registered]" in line


def test_graph_doctor_recommended_action_baseline_when_ok(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path)
    finding = _pending_finding(_doctor_json(config_path))
    assert finding["recommended_action"] == "Review with `folio links review` and confirm or reject it."


def test_graph_doctor_recommended_action_notes_flagged_input(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path, flagged_source=True)
    finding = _pending_finding(_doctor_json(config_path, include_flagged=True))
    assert "flagged" in finding["recommended_action"]


def test_graph_doctor_recommended_action_points_to_refresh_on_target_missing(tmp_path):
    config_path, *_ = _build_minimal_pending_library(tmp_path, target_present=False)
    finding = _pending_finding(_doctor_json(config_path))
    assert "folio refresh" in finding["recommended_action"] or "folio ingest" in finding["recommended_action"]
