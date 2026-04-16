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
        "lifecycle_state": "queued",
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
    assert suppression_counts.rejection_memory == {}
    assert suppression_counts.flagged_input == 0
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
    assert {(item["relation"], item["lifecycle_state"], item["basis_fingerprint"]) for item in proposals} == {
        ("depends_on", "rejected", "sha256:depends"),
        ("draws_from", "rejected", "sha256:draws"),
    }


# ---------------------------------------------------------------------------
# Phase C (v0.6.0): rejection-memory filter, revival, suppression counter,
# call-site return-type migration, safety/defensive tests.
# ---------------------------------------------------------------------------


def _rejected_proposal(source_id: str, relation: str, target_id: str, basis_fingerprint: str, *, confidence: str = "medium", producer: str = "enrich") -> dict:
    p = _proposal(source_id, relation, target_id, basis_fingerprint, confidence=confidence)
    p["lifecycle_state"] = "rejected"
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
    assert suppression_counts.rejection_memory == {"enrich": 1}
    assert suppression_counts.flagged_input == 0


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
    assert suppression_counts.rejection_memory == {}
    assert suppression_counts.flagged_input == 0


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
    assert suppression_counts.rejection_memory == {}
    assert suppression_counts.flagged_input == 0


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
    assert suppression_counts.rejection_memory == {}
    assert suppression_counts.flagged_input == 0


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
    assert suppression_counts.rejection_memory == {}
    assert suppression_counts.flagged_input == 0


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
    assert suppression_counts.rejection_memory == {}
    assert suppression_counts.flagged_input == 0


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
    assert suppression_counts.rejection_memory == {}
    assert suppression_counts.flagged_input == 0


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
                                {"relation": "impacts", "lifecycle_state": "queued",
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
    # No crash (DB-1 fix). The malformed entry with missing target_id is
    # skipped at _iter_producer_proposals (B-001 fix: empty target_id cannot
    # surface as confirmable — confirming it would write canonical
    # `impacts: ['']` and corrupt frontmatter). Only the well-formed
    # proposal surfaces.
    assert len(views) == 1
    assert views[0].proposal.target_id == target_id
    assert counts.rejection_memory == {}
    assert counts.flagged_input == 0


def test_return_type_is_tuple_views_and_counts(tmp_path):
    """DB-4 explicit: collect_pending returns a 2-tuple (views, SuppressionCounts).

    v0.6.4: counts migrated from dict[str, int] to SuppressionCounts dataclass.
    """
    from folio.links import SuppressionCounts
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
    assert isinstance(views, list) and isinstance(counts, SuppressionCounts)


def test_relationship_status_summary_post_migration(tmp_path):
    """DB-4 explicit regression: relationship_status_summary survives tuple-return migration.

    v0.6.4: return type changed from list[RelationshipStatusRow] to
    tuple[list[RelationshipStatusRow], int] where int is total_flagged_excluded.
    """
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
    rows, total_flagged_excluded = relationship_status_summary(FolioConfig.load(config_path))
    # row emitted for the source doc with one pending proposal; no crash.
    assert any(row.source_id == source_id and row.pending == 1 for row in rows)
    assert total_flagged_excluded == 0


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


def test_filter_skips_malformed_target_id_proposals(tmp_path):
    """Codex adversarial B-001: proposals with empty / non-string target_id must not surface."""
    source_id = "clienta_evidence_malformed_tgt"
    target_id = "clienta_evidence_ok_tgt"
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
                                # target_id missing entirely
                                {"relation": "impacts", "lifecycle_state": "queued",
                                 "confidence": "medium", "basis_fingerprint": "sha256:a"},
                                # target_id empty string
                                {"relation": "impacts", "target_id": "", "lifecycle_state": "queued",
                                 "confidence": "medium", "basis_fingerprint": "sha256:b"},
                                # target_id non-string (integer)
                                {"relation": "impacts", "target_id": 123, "lifecycle_state": "queued",
                                 "confidence": "medium", "basis_fingerprint": "sha256:c"},
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
    views, _ = collect_pending_relationship_proposals(config)
    # Only the well-formed proposal surfaces; the three malformed ones are skipped.
    assert len(views) == 1
    assert views[0].proposal.target_id == target_id


def test_filter_rejection_key_ignores_empty_basis_fingerprint(tmp_path):
    """Codex adversarial SF-001: empty basis_fingerprint must not create a valid rejection key."""
    source_id = "clienta_evidence_emptyfp"
    target_id = "clienta_evidence_emptyfp_tgt"
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
                                # Rejected entry with empty basis_fingerprint (producer defect state)
                                {"proposal_id": "rej-1", "relation": "impacts", "target_id": target_id,
                                 "basis_fingerprint": "", "confidence": "medium", "signals": [],
                                 "rationale": "", "lifecycle_state": "rejected", "producer": "enrich"},
                                # Pending entry with a proper basis_fingerprint — must NOT be
                                # suppressed by the empty-fingerprint rejected entry
                                _proposal(source_id, "impacts", target_id, "sha256:legitimate"),
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
    # The pending proposal with a real fingerprint must surface; empty-fp
    # rejection must not act as a suppression key.
    assert len(views) == 1
    assert counts.rejection_memory == {}
    assert counts.flagged_input == 0


# ---------------------------------------------------------------------------
# Phase C (v0.6.4): trust-gated surfacing — source/target review_status filter,
# --include-flagged override, silent-empty protection, disclosure lines.
# ---------------------------------------------------------------------------


def _setup_flagged_lib(
    tmp_path: Path,
    *,
    source_id: str,
    target_id: str,
    source_flagged: bool = False,
    target_flagged: bool = False,
    proposals: list[dict] | None = None,
    extra_targets: dict[str, bool] | None = None,
) -> Path:
    """Build a library where source and/or target have review_status: flagged.

    extra_targets maps target_id -> flagged boolean for multi-target fixtures.
    """
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    entries = {
        source_id: _registry_entry(source_id, f"ClientA/{source_id}.md"),
        target_id: _registry_entry(target_id, f"ClientA/{target_id}.md"),
    }
    for extra_id in (extra_targets or {}):
        entries[extra_id] = _registry_entry(extra_id, f"ClientA/{extra_id}.md")
    _write_registry(library, entries)

    target_rs = "flagged" if target_flagged else "clean"
    _write_note(library / "ClientA" / f"{target_id}.md",
                _base_note(target_id, target_id, review_status=target_rs))
    for extra_id, is_flagged in (extra_targets or {}).items():
        rs = "flagged" if is_flagged else "clean"
        _write_note(library / "ClientA" / f"{extra_id}.md",
                    _base_note(extra_id, extra_id, review_status=rs))

    source_rs = "flagged" if source_flagged else "clean"
    _write_note(
        library / "ClientA" / f"{source_id}.md",
        _base_note(
            source_id,
            "Source",
            review_status=source_rs,
            _llm_metadata={
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": proposals or [
                                _proposal(source_id, "impacts", target_id, "sha256:ok")
                            ]
                        }
                    }
                }
            },
        ),
    )
    return config_path


def test_flagged_source_excluded_by_default(tmp_path):
    """S4-1: proposal from flagged source doc not in views; flagged_input counted."""
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id="clienta_evidence_flagged_src",
        target_id="clienta_evidence_tgt_s4_1",
        source_flagged=True,
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(FolioConfig.load(config_path))
    assert views == []
    assert counts.flagged_input == 1
    assert counts.rejection_memory == {}


def test_flagged_target_excluded_by_default(tmp_path):
    """S4-2: proposal targeting flagged doc not in views; flagged_input counted."""
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id="clienta_evidence_src_s4_2",
        target_id="clienta_evidence_flagged_tgt",
        target_flagged=True,
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(FolioConfig.load(config_path))
    assert views == []
    assert counts.flagged_input == 1
    assert counts.rejection_memory == {}


def test_include_flagged_surfaces_proposals(tmp_path):
    """S4-3: include_flagged=True surfaces flagged-input proposals."""
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id="clienta_evidence_src_s4_3",
        target_id="clienta_evidence_tgt_s4_3",
        source_flagged=True,
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(
        FolioConfig.load(config_path), include_flagged=True
    )
    assert len(views) == 1
    assert counts.flagged_input == 0  # not suppressed when included


def test_flagged_proposals_have_trust_annotation(tmp_path):
    """S4-4: view.flagged_inputs contains "source" / "target" appropriately."""
    # Source-only flagged
    sub_a = tmp_path / "a"
    sub_a.mkdir()
    config_path = _setup_flagged_lib(
        sub_a,
        source_id="clienta_evidence_src_s4_4_src",
        target_id="clienta_evidence_tgt_s4_4_src",
        source_flagged=True,
    )
    from folio.config import FolioConfig
    views, _ = collect_pending_relationship_proposals(
        FolioConfig.load(config_path), include_flagged=True
    )
    assert len(views) == 1
    assert views[0].flagged_inputs == ["source"]

    # Target-only flagged
    sub_b = tmp_path / "b"
    sub_b.mkdir()
    config_path2 = _setup_flagged_lib(
        sub_b,
        source_id="clienta_evidence_src_s4_4_tgt",
        target_id="clienta_evidence_tgt_s4_4_tgt",
        target_flagged=True,
    )
    views2, _ = collect_pending_relationship_proposals(
        FolioConfig.load(config_path2), include_flagged=True
    )
    assert len(views2) == 1
    assert views2[0].flagged_inputs == ["target"]


def test_flagged_excluded_count(tmp_path):
    """S4-5: flagged_input counts correctly across multiple proposals."""
    source_id = "clienta_evidence_src_s4_5"
    target_a = "clienta_evidence_tgt_s4_5_a"
    target_b = "clienta_evidence_tgt_s4_5_b"
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id=source_id,
        target_id=target_a,
        target_flagged=True,
        extra_targets={target_b: True},
        proposals=[
            _proposal(source_id, "impacts", target_a, "sha256:fp-a"),
            _proposal(source_id, "draws_from", target_b, "sha256:fp-b"),
        ],
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(FolioConfig.load(config_path))
    assert views == []
    assert counts.flagged_input == 2


def test_both_source_and_target_flagged(tmp_path):
    """S4-6: both "source" and "target" in flagged_inputs; counted once."""
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id="clienta_evidence_src_s4_6",
        target_id="clienta_evidence_tgt_s4_6",
        source_flagged=True,
        target_flagged=True,
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(
        FolioConfig.load(config_path), include_flagged=True
    )
    assert len(views) == 1
    assert views[0].flagged_inputs == ["source", "target"]
    # Default mode: still counted as 1 suppression, not 2
    views_default, counts_default = collect_pending_relationship_proposals(
        FolioConfig.load(config_path)
    )
    assert views_default == []
    assert counts_default.flagged_input == 1


def test_clean_documents_unaffected(tmp_path):
    """S4-7: proposals between clean review_status docs pass through unchanged."""
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id="clienta_evidence_src_s4_7",
        target_id="clienta_evidence_tgt_s4_7",
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(FolioConfig.load(config_path))
    assert len(views) == 1
    assert views[0].flagged_inputs == []
    assert counts.flagged_input == 0


def test_rejection_memory_precedes_flagged_input(tmp_path):
    """S4-8: a proposal both rejected AND flagged counts as rejection_memory only."""
    source_id = "clienta_evidence_src_s4_8"
    target_id = "clienta_evidence_tgt_s4_8"
    fp = "sha256:both-reasons"
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id=source_id,
        target_id=target_id,
        source_flagged=True,  # source flagged
        proposals=[
            _rejected_proposal(source_id, "impacts", target_id, fp),
            _proposal(source_id, "impacts", target_id, fp),  # same fp -> rejected
        ],
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(FolioConfig.load(config_path))
    assert views == []
    # Rejection-memory wins; flagged_input not bumped for the same proposal.
    assert counts.rejection_memory == {"enrich": 1}
    assert counts.flagged_input == 0


def test_extraction_confidence_not_used_as_filter(tmp_path):
    """S4-9 (SF-C): §11 rule 6 — extraction_confidence is informational only.

    Even though the basis_fingerprint carries no trust signal, a proposal with
    extraction_confidence metadata should not be filtered. We ensure clean-docs
    proposals always surface, and no code path consults extraction_confidence.
    """
    source_id = "clienta_evidence_src_s4_9"
    target_id = "clienta_evidence_tgt_s4_9"
    proposal = _proposal(source_id, "impacts", target_id, "sha256:low-conf")
    proposal["extraction_confidence"] = 0.01  # hypothetical low value
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id=source_id,
        target_id=target_id,
        proposals=[proposal],
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(FolioConfig.load(config_path))
    assert len(views) == 1  # NOT filtered despite low extraction_confidence
    assert counts.flagged_input == 0


def test_malformed_review_status_not_flagged():
    """S4-10 (SF-J): _is_flagged handles None, missing, list, bool, wrong case."""
    from folio.links import _is_flagged
    assert _is_flagged(None) is False
    assert _is_flagged("") is False
    assert _is_flagged("clean") is False
    assert _is_flagged("unknown") is False
    assert _is_flagged("flagged") is True
    assert _is_flagged("FLAGGED") is True
    assert _is_flagged(" Flagged ") is True
    assert _is_flagged(["flagged"]) is False  # list is malformed, fail-open
    assert _is_flagged({"flagged": True}) is False
    assert _is_flagged(True) is False  # boolean truthy but not "flagged"
    assert _is_flagged(1) is False


def test_target_frontmatter_authoritative_vs_registry(tmp_path):
    """S4-11 (CB-1): target flagged state is read from frontmatter, not stale registry."""
    source_id = "clienta_evidence_src_s4_11"
    target_id = "clienta_evidence_tgt_s4_11"
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    # Registry says target is clean (no review_status field at all on registry row)
    _write_registry(
        library,
        {
            source_id: _registry_entry(source_id, f"ClientA/{source_id}.md"),
            target_id: _registry_entry(target_id, f"ClientA/{target_id}.md"),
        },
    )
    # But target frontmatter says flagged
    _write_note(
        library / "ClientA" / f"{target_id}.md",
        _base_note(target_id, target_id, review_status="flagged"),
    )
    _write_note(
        library / "ClientA" / f"{source_id}.md",
        _base_note(
            source_id,
            "Source",
            _llm_metadata={
                "enrich": {"axes": {"relationships": {
                    "proposals": [_proposal(source_id, "impacts", target_id, "sha256:ok")]
                }}}
            },
        ),
    )
    from folio.config import FolioConfig
    views, counts = collect_pending_relationship_proposals(FolioConfig.load(config_path))
    # Frontmatter is authoritative: filtered even though registry row has no review_status
    assert views == []
    assert counts.flagged_input == 1


def test_suppression_counts_structure_prevents_collision():
    """S4-12 (CB-3): producer named 'flagged_input' does not collide with sentinel."""
    from folio.links import SuppressionCounts
    # A producer named "flagged_input" writes to rejection_memory, not the
    # trust-gate scalar. Structure separation prevents collision.
    counts = SuppressionCounts()
    counts.rejection_memory["flagged_input"] = 3  # producer with this literal name
    counts.flagged_input = 2  # trust-gate count
    assert counts.total() == 5
    assert counts.rejection_memory["flagged_input"] == 3
    assert counts.flagged_input == 2


def test_links_review_include_flagged_flag_renders_tag(tmp_path):
    """S4-13 (SF-F): CLI --include-flagged prints (flagged: source) tag."""
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id="clienta_evidence_src_s4_13",
        target_id="clienta_evidence_tgt_s4_13",
        source_flagged=True,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(config_path), "links", "review", "--include-flagged"],
    )
    assert result.exit_code == 0
    assert "(flagged: source)" in result.output


def test_links_review_silent_empty_protection(tmp_path):
    """S4-14: 0-view output includes excluded-count sentence."""
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id="clienta_evidence_src_s4_14",
        target_id="clienta_evidence_tgt_s4_14",
        target_flagged=True,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "links", "review"])
    assert result.exit_code == 0
    assert "0 items" in result.output
    assert "excluded" in result.output
    assert "--include-flagged" in result.output


def test_links_status_discloses_flagged_excluded(tmp_path):
    """S4-15 (CB-2): status output includes flagged-excluded column and disclosure."""
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id="clienta_evidence_src_s4_15",
        target_id="clienta_evidence_tgt_s4_15",
        target_flagged=True,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "links", "status"])
    assert result.exit_code == 0
    # Source row must surface with flagged_excluded count even though pending==0
    assert "clienta_evidence_src_s4_15" in result.output
    assert "Flagged Excluded" in result.output
    assert "flagged-excluded" in result.output


def test_links_confirm_doc_discloses_flagged_excluded(tmp_path):
    """S4-16 (CB-2): confirm-doc with all-flagged source prints diagnostic."""
    source_id = "clienta_evidence_src_s4_16"
    target_id = "clienta_evidence_tgt_s4_16"
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id=source_id,
        target_id=target_id,
        source_flagged=True,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--config", str(config_path), "links", "confirm-doc", source_id]
    )
    assert result.exit_code == 0
    assert "Confirmed 0 proposal(s)" in result.output
    assert "flagged inputs" in result.output
    assert "--include-flagged" in result.output


def test_links_confirm_rejects_flagged_id_without_flag(tmp_path):
    """S4-17 (CB-4): confirm <flagged_id> without --include-flagged errors."""
    source_id = "clienta_evidence_src_s4_17"
    target_id = "clienta_evidence_tgt_s4_17"
    proposal = _proposal(source_id, "impacts", target_id, "sha256:flagged-proposal")
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id=source_id,
        target_id=target_id,
        source_flagged=True,
        proposals=[proposal],
    )
    runner = CliRunner()
    # Try confirming the flagged proposal without --include-flagged
    result = runner.invoke(
        cli, ["--config", str(config_path), "links", "confirm", proposal["proposal_id"]]
    )
    assert result.exit_code == 1
    assert "Unknown proposal_id" in result.output


def test_links_confirm_accepts_flagged_id_with_flag(tmp_path):
    """S4-18 (CB-4): confirm <flagged_id> --include-flagged succeeds."""
    source_id = "clienta_evidence_src_s4_18"
    target_id = "clienta_evidence_tgt_s4_18"
    proposal = _proposal(source_id, "supersedes", target_id, "sha256:flag-confirm",
                         confidence="high")
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id=source_id,
        target_id=target_id,
        source_flagged=True,
        proposals=[proposal],
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(config_path), "links", "confirm",
         proposal["proposal_id"], "--include-flagged"],
    )
    assert result.exit_code == 0
    assert f"Confirmed {proposal['proposal_id']}" in result.output
    # Canonical frontmatter actually updated
    fm = _read_fm(tmp_path / "library" / "ClientA" / f"{source_id}.md")
    assert fm["supersedes"] == target_id


def test_revived_and_flagged_tags_render_together(tmp_path):
    """S4-19 (SF-I): revived + flagged tags render in correct order."""
    source_id = "clienta_evidence_src_s4_19"
    target_id = "clienta_evidence_tgt_s4_19"
    # Rejected old + pending new = revived; source flagged = flagged tag
    config_path = _setup_flagged_lib(
        tmp_path,
        source_id=source_id,
        target_id=target_id,
        source_flagged=True,
        proposals=[
            _rejected_proposal(source_id, "impacts", target_id, "sha256:old-fp"),
            _proposal(source_id, "impacts", target_id, "sha256:new-fp"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(config_path), "links", "review", "--include-flagged"],
    )
    assert result.exit_code == 0
    # Both tags render and revived comes before flagged
    assert "(revived — basis changed) (flagged: source)" in result.output
