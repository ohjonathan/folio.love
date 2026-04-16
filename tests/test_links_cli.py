"""CLI and helper tests for document relationship review."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from folio.cli import cli
from folio.links import collect_pending_relationship_proposals
from folio.pipeline.enrich_data import compute_relationship_proposal_id


def _make_config(path: Path, library_root: Path) -> None:
    path.write_text(yaml.dump({"library_root": str(library_root)}, default_flow_style=False))


def _registry_entry(note_id: str, markdown_path: str, *, title: str | None = None) -> dict:
    return {
        "id": note_id,
        "title": title or note_id,
        "type": "evidence",
        "markdown_path": markdown_path,
        "deck_dir": str(Path(markdown_path).parent).replace("\\", "/"),
        "source_relative_path": "deck.pptx",
        "source_hash": f"{note_id}-hash",
        "version": 1,
        "converted": "2026-03-29T00:00:00Z",
        "client": "ClientA",
        "engagement": "DD_Q1",
    }


def _write_registry(library_root: Path, entries: dict[str, dict]) -> None:
    payload = {
        "_schema_version": 1,
        "updated_at": "2026-03-29T00:00:00Z",
        "decks": entries,
    }
    (library_root / "registry.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_note(path: Path, frontmatter: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{yaml_str}---\n\n# {frontmatter['title']}\n", encoding="utf-8")


def _read_fm(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    end = content.index("\n---", 4)
    return yaml.safe_load(content[4:end]) or {}


def _base_note(note_id: str, title: str, **overrides) -> dict:
    frontmatter = {
        "id": note_id,
        "title": title,
        "type": "evidence",
        "status": "active",
        "curation_level": "L0",
        "review_status": "clean",
        "client": "ClientA",
        "engagement": "DD_Q1",
        "source": "deck.pptx",
        "source_hash": f"{note_id}-hash",
        "version": 1,
        "created": "2026-03-29T00:00:00Z",
        "modified": "2026-03-29T00:00:00Z",
    }
    frontmatter.update(overrides)
    return frontmatter


def _proposal(source_id: str, relation: str, target_id: str, basis_fingerprint: str, *, confidence: str = "medium") -> dict:
    return {
        "proposal_id": compute_relationship_proposal_id(
            source_id=source_id,
            relation=relation,
            target_id=target_id,
            basis_fingerprint=basis_fingerprint,
        ),
        "relation": relation,
        "target_id": target_id,
        "basis_fingerprint": basis_fingerprint,
        "confidence": confidence,
        "signals": ["shared_topic"],
        "rationale": f"{relation} rationale",
        "status": "pending_human_confirmation",
        "producer": "enrich",
    }


def test_collect_pending_relationship_proposals_orders_by_source_then_confidence(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_a = "clienta_evidence_source_a"
    source_b = "clienta_evidence_source_b"
    target = "clienta_evidence_target"

    _write_registry(
        library,
        {
            source_a: _registry_entry(source_a, "ClientA/source_a.md"),
            source_b: _registry_entry(source_b, "ClientA/source_b.md"),
            target: _registry_entry(target, "ClientA/target.md"),
        },
    )
    _write_note(library / "ClientA" / "target.md", _base_note(target, "Target"))
    _write_note(
        library / "ClientA" / "source_a.md",
        _base_note(
            source_a,
            "Source A",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                _proposal(source_a, "impacts", target, "sha256:low", confidence="medium"),
                                _proposal(source_a, "supersedes", target, "sha256:high", confidence="high"),
                            ]
                        }
                    }
                }
            },
        ),
    )
    _write_note(
        library / "ClientA" / "source_b.md",
        _base_note(
            source_b,
            "Source B",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                _proposal(source_b, "impacts", target, "sha256:basis-b", confidence="high"),
                            ]
                        }
                    }
                }
            },
        ),
    )

    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    proposals, suppression_counts = collect_pending_relationship_proposals(config)
    assert suppression_counts == {}
    assert [(view.source_id, view.proposal.confidence, view.proposal.proposal_id) for view in proposals] == [
        (
            source_a,
            "high",
            compute_relationship_proposal_id(
                source_id=source_a,
                relation="supersedes",
                target_id=target,
                basis_fingerprint="sha256:high",
            ),
        ),
        (
            source_a,
            "medium",
            compute_relationship_proposal_id(
                source_id=source_a,
                relation="impacts",
                target_id=target,
                basis_fingerprint="sha256:low",
            ),
        ),
        (
            source_b,
            "high",
            compute_relationship_proposal_id(
                source_id=source_b,
                relation="impacts",
                target_id=target,
                basis_fingerprint="sha256:basis-b",
            ),
        ),
    ]


def test_links_confirm_promotes_canonical_relationship_and_records_confirmation(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_id = "clienta_evidence_source"
    target_id = "clienta_evidence_target"
    proposal = _proposal(source_id, "supersedes", target_id, "sha256:basis-1", confidence="high")

    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, "ClientA/source.md"),
            target_id: _registry_entry(target_id, "ClientA/target.md"),
        },
    )
    _write_note(library / "ClientA" / "target.md", _base_note(target_id, "Target"))
    _write_note(
        library / "ClientA" / "source.md",
        _base_note(
            source_id,
            "Source",
            _llm_metadata={"enrich": {"axes": {"relationships": {"proposals": [proposal]}}}},
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "links", "confirm", proposal["proposal_id"]])
    assert result.exit_code == 0
    assert f"Confirmed {proposal['proposal_id']}" in result.output

    fm = _read_fm(library / "ClientA" / "source.md")
    assert fm["supersedes"] == target_id
    assert fm["_llm_metadata"]["enrich"]["axes"]["relationships"]["proposals"] == []
    confirmation = fm["_llm_metadata"]["links"]["confirmed_relationships"][0]
    assert confirmation["proposal_id"] == proposal["proposal_id"]
    assert confirmation["relation"] == "supersedes"
    assert confirmation["target_id"] == target_id
    assert confirmation["producer"] == "enrich"
    assert confirmation["basis_fingerprint"] == "sha256:basis-1"
    assert confirmation["confirmation_source"] == "folio links confirm"


def test_links_confirm_doc_deduplicates_existing_list_relationships(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_id = "clienta_evidence_source"
    impact_target = "clienta_evidence_impact"
    draws_target = "clienta_analysis_source"

    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, "ClientA/source.md"),
            impact_target: _registry_entry(impact_target, "ClientA/impact.md"),
            draws_target: _registry_entry(draws_target, "ClientA/draws.md"),
        },
    )
    _write_note(library / "ClientA" / "impact.md", _base_note(impact_target, "Impact"))
    _write_note(library / "ClientA" / "draws.md", _base_note(draws_target, "Draws"))
    _write_note(
        library / "ClientA" / "source.md",
        _base_note(
            source_id,
            "Source",
            impacts=[impact_target],
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                _proposal(source_id, "impacts", impact_target, "sha256:impact"),
                                _proposal(source_id, "draws_from", draws_target, "sha256:draws"),
                            ]
                        }
                    }
                }
            },
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "links", "confirm-doc", source_id])
    assert result.exit_code == 0
    assert "Confirmed 2 proposal(s)" in result.output

    fm = _read_fm(library / "ClientA" / "source.md")
    assert fm["impacts"] == [impact_target]
    assert fm["draws_from"] == [draws_target]
    assert fm["_llm_metadata"]["enrich"]["axes"]["relationships"]["proposals"] == []
    confirmed = fm["_llm_metadata"]["links"]["confirmed_relationships"]
    assert len(confirmed) == 2


def test_links_reject_doc_marks_future_relation_proposals_rejected(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)

    source_id = "clienta_analysis_synthesis"
    input_a = "clienta_context_engagement"
    input_b = "clienta_evidence_supporting"

    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, "ClientA/analysis.md"),
            input_a: _registry_entry(input_a, "ClientA/context.md"),
            input_b: _registry_entry(input_b, "ClientA/supporting.md"),
        },
    )
    _write_note(library / "ClientA" / "context.md", _base_note(input_a, "Context"))
    _write_note(library / "ClientA" / "supporting.md", _base_note(input_b, "Supporting"))
    _write_note(
        library / "ClientA" / "analysis.md",
        _base_note(
            source_id,
            "Analysis",
            _llm_metadata={
                "digest": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                _proposal(source_id, "draws_from", input_a, "sha256:draws"),
                                _proposal(source_id, "depends_on", input_b, "sha256:depends"),
                            ]
                        }
                    }
                }
            },
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "links", "reject-doc", source_id])
    assert result.exit_code == 0
    assert "Rejected 2 proposal(s)" in result.output

    fm = _read_fm(library / "ClientA" / "analysis.md")
    proposals = fm["_llm_metadata"]["digest"]["axes"]["relationships"]["proposals"]
    assert {(item["relation"], item["status"], item["basis_fingerprint"]) for item in proposals} == {
        ("depends_on", "rejected", "sha256:depends"),
        ("draws_from", "rejected", "sha256:draws"),
    }


# ---------------------------------------------------------------------------
# Phase C (v0.6.0): rejection-memory filter, revival, suppression counter,
# call-site return-type migration, safety/defensive tests.
# ---------------------------------------------------------------------------


def _rejected_proposal(source_id: str, relation: str, target_id: str, basis_fingerprint: str, *, confidence: str = "medium", producer: str = "enrich") -> dict:
    p = _proposal(source_id, relation, target_id, basis_fingerprint, confidence=confidence)
    p["status"] = "rejected"
    p["producer"] = producer
    return p


def _setup_library_with_producer_proposals(
    tmp_path: Path,
    source_id: str,
    target_id: str,
    proposals: list[dict],
    *,
    producer: str = "enrich",
) -> Path:
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _registry_entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_note(target_id, "Target"))
    _write_note(
        library / "ClientA" / f"{source_id}.md",
        _base_note(
            source_id,
            "Source",
            _llm_metadata={producer: {"axes": {"relationships": {"proposals": proposals}}}},
        ),
    )
    return config_path


def test_pending_filter_excludes_rejected_with_matching_fingerprint(tmp_path):
    source_id = "clienta_evidence_s"
    target_id = "clienta_evidence_t"
    fp = "sha256:same-fp"
    config_path = _setup_library_with_producer_proposals(
        tmp_path,
        source_id,
        target_id,
        [
            _rejected_proposal(source_id, "impacts", target_id, fp),
            _proposal(source_id, "impacts", target_id, fp),
        ],
    )
    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    views, suppression_counts = collect_pending_relationship_proposals(config)
    assert views == []
    assert suppression_counts == {"enrich": 1}


def test_pending_filter_keeps_non_matching_fingerprint(tmp_path):
    source_id = "clienta_evidence_s"
    target_id = "clienta_evidence_t"
    config_path = _setup_library_with_producer_proposals(
        tmp_path,
        source_id,
        target_id,
        [
            _rejected_proposal(source_id, "impacts", target_id, "sha256:old"),
            _proposal(source_id, "impacts", target_id, "sha256:new"),
        ],
    )
    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    views, suppression_counts = collect_pending_relationship_proposals(config)
    assert len(views) == 1
    assert views[0].revived is True
    assert suppression_counts == {}


def test_pending_filter_keeps_unrelated_pending(tmp_path):
    source_id = "clienta_evidence_s"
    target_id = "clienta_evidence_t"
    other_target = "clienta_evidence_u"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _registry_entry(target_id, f"ClientA/{target_id}.md"),
            other_target: _registry_entry(other_target, f"ClientA/{other_target}.md"),
        },
    )
    for t in (target_id, other_target):
        _write_note(library / "ClientA" / f"{t}.md", _base_note(t, t))
    _write_note(
        library / "ClientA" / f"{source_id}.md",
        _base_note(
            source_id,
            "Source",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                _rejected_proposal(source_id, "impacts", target_id, "sha256:a"),
                                _proposal(source_id, "impacts", other_target, "sha256:b"),
                            ]
                        }
                    }
                }
            },
        ),
    )
    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    views, suppression_counts = collect_pending_relationship_proposals(config)
    assert len(views) == 1
    assert views[0].proposal.target_id == other_target
    assert views[0].revived is False
    assert suppression_counts == {}


def test_pending_filter_scoped_per_doc(tmp_path):
    source_a = "clienta_evidence_sa"
    source_b = "clienta_evidence_sb"
    target_id = "clienta_evidence_t"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(
        library,
        {
            source_a: _registry_entry(source_a, f"ClientA/{source_a}.md"),
            source_b: _registry_entry(source_b, f"ClientA/{source_b}.md"),
            target_id: _registry_entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_note(target_id, target_id))
    _write_note(
        library / "ClientA" / f"{source_a}.md",
        _base_note(
            source_a,
            "Source A",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [_rejected_proposal(source_a, "impacts", target_id, "sha256:x")]
                        }
                    }
                }
            },
        ),
    )
    _write_note(
        library / "ClientA" / f"{source_b}.md",
        _base_note(
            source_b,
            "Source B",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [_proposal(source_b, "impacts", target_id, "sha256:x")]
                        }
                    }
                }
            },
        ),
    )
    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    views, suppression_counts = collect_pending_relationship_proposals(config)
    assert len(views) == 1
    assert views[0].source_id == source_b
    assert suppression_counts == {}


def test_pending_filter_scoped_per_producer(tmp_path):
    source_id = "clienta_evidence_s"
    target_id = "clienta_evidence_t"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _registry_entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_note(target_id, target_id))
    _write_note(
        library / "ClientA" / f"{source_id}.md",
        _base_note(
            source_id,
            "Source",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [_rejected_proposal(source_id, "impacts", target_id, "sha256:z", producer="enrich")]
                        }
                    }
                },
                "digest": {
                    "axes": {
                        "relationships": {
                            "proposals": [_proposal(source_id, "impacts", target_id, "sha256:z")]
                        }
                    }
                },
            },
        ),
    )
    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    views, suppression_counts = collect_pending_relationship_proposals(config)
    assert len(views) == 1
    assert views[0].producer == "digest"
    assert suppression_counts == {}


def test_filter_tolerates_malformed_proposal_entries(tmp_path):
    source_id = "clienta_evidence_s"
    target_id = "clienta_evidence_t"
    config_path = _setup_library_with_producer_proposals(
        tmp_path,
        source_id,
        target_id,
        [
            None,  # malformed
            "not-a-dict",  # malformed
            _proposal(source_id, "impacts", target_id, "sha256:ok"),
        ],
    )
    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    views, suppression_counts = collect_pending_relationship_proposals(config)
    assert len(views) == 1
    assert suppression_counts == {}


def test_filter_skips_links_namespace(tmp_path):
    source_id = "clienta_evidence_s"
    target_id = "clienta_evidence_t"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _registry_entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_note(target_id, target_id))
    _write_note(
        library / "ClientA" / f"{source_id}.md",
        _base_note(
            source_id,
            "Source",
            _llm_metadata={
                "links": {
                    "confirmed_relationships": [
                        {"relation": "impacts", "target_id": target_id, "producer": "enrich", "basis_fingerprint": "sha256:old", "confirmed_at": "2026-04-15T00:00:00+00:00"}
                    ]
                },
                "enrich": {"axes": {"relationships": {"proposals": [_proposal(source_id, "impacts", target_id, "sha256:new")]}}},
            },
        ),
    )
    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    views, suppression_counts = collect_pending_relationship_proposals(config)
    assert len(views) == 1  # links namespace is NOT treated as a producer
    assert suppression_counts == {}


# ---------------------------------------------------------------------------
# Phase D.4 (v0.6.0): fix regression tests per D.3 canonical verdict.
# ---------------------------------------------------------------------------


def test_filter_handles_missing_source_id_target_id(tmp_path):
    """DB-1 regression: proposal dicts missing target_id / source_id don't raise KeyError."""
    from folio.links import _proposal_from_raw

    # Bare minimum raw dict — all identity fields missing — must not raise.
    _proposal_from_raw("src-id", "enrich", {})
    _proposal_from_raw("src-id", "enrich", {"relation": "impacts"})
    _proposal_from_raw("src-id", "enrich", {"target_id": "tgt-id"})
    # And the filter path: a full collect_pending over frontmatter with such entries.
    source_id = "clienta_evidence_missing_fields"
    target_id = "clienta_evidence_target_mf"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _registry_entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    _write_note(library / "ClientA" / f"{target_id}.md", _base_note(target_id, target_id))
    _write_note(
        library / "ClientA" / f"{source_id}.md",
        _base_note(
            source_id,
            "Source",
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [
                                # Legacy entry missing target_id — must not crash
                                {"relation": "impacts", "status": "pending_human_confirmation",
                                 "confidence": "medium", "basis_fingerprint": "sha256:legacy"},
                                _proposal(source_id, "impacts", target_id, "sha256:ok"),
                            ]
                        }
                    }
                }
            },
        ),
    )
    from folio.config import FolioConfig

    config = FolioConfig.load(config_path)
    views, counts = collect_pending_relationship_proposals(config)
    # No crash. The entry with missing target_id gets target_id="" and
    # a computed proposal_id; it is harmless to surface (unsupported relation
    # would have filtered it, but "impacts" is supported). Both surface.
    assert len(views) == 2
    assert counts == {}


def test_return_type_is_tuple_views_and_counts(tmp_path):
    """DB-4 explicit: collect_pending returns a 2-tuple (views, counts)."""
    source_id = "clienta_evidence_tuple"
    target_id = "clienta_evidence_tgt_t"
    config_path = _setup_library_with_producer_proposals(
        tmp_path,
        source_id,
        target_id,
        [_proposal(source_id, "impacts", target_id, "sha256:ok")],
    )
    from folio.config import FolioConfig

    result = collect_pending_relationship_proposals(FolioConfig.load(config_path))
    assert isinstance(result, tuple) and len(result) == 2
    views, counts = result
    assert isinstance(views, list) and isinstance(counts, dict)


def test_relationship_status_summary_post_migration(tmp_path):
    """DB-4 explicit regression: relationship_status_summary survives tuple-return migration."""
    from folio.config import FolioConfig
    from folio.links import relationship_status_summary

    source_id = "clienta_evidence_summary"
    target_id = "clienta_evidence_summary_tgt"
    config_path = _setup_library_with_producer_proposals(
        tmp_path,
        source_id,
        target_id,
        [_proposal(source_id, "impacts", target_id, "sha256:ok")],
    )
    rows = relationship_status_summary(FolioConfig.load(config_path))
    # row emitted for the source doc with one pending proposal; no crash.
    assert any(row.source_id == source_id and row.pending == 1 for row in rows)


def test_find_pending_view_post_migration(tmp_path):
    """DB-4 explicit regression: _find_pending_view survives tuple-return migration."""
    from folio.config import FolioConfig
    from folio.links import _find_pending_view

    source_id = "clienta_evidence_find"
    target_id = "clienta_evidence_find_tgt"
    config_path = _setup_library_with_producer_proposals(
        tmp_path,
        source_id,
        target_id,
        [_proposal(source_id, "impacts", target_id, "sha256:ok")],
    )
    config = FolioConfig.load(config_path)
    views, _ = collect_pending_relationship_proposals(config)
    pid = views[0].proposal.proposal_id
    view = _find_pending_view(config, pid)
    assert view.proposal.proposal_id == pid
