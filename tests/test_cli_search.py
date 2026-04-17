"""CLI integration tests for folio search.

Covers SRC-CLI-1..SRC-CLI-31 per docs/specs/v0.9.0_folio_search_spec.md §9.2.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from folio.cli import cli
from folio.pipeline.enrich_data import compute_relationship_proposal_id


REQUIRED_ENVELOPE_KEYS = {
    "schema_version",
    "command",
    "scope",
    "query",
    "trust_override_active",
    "excluded_flagged_count",
    "findings",
}

SHARED_CONTRACT_FINDING_KEYS = {
    "proposal_type",
    "source_id",
    "target_id",
    "subject_id",
    "evidence_bundle",
    "reason_summary",
    "trust_status",
    "schema_gate_result",
    "producer",
    "input_fingerprint",
    "lifecycle_state",
}


# ---- Fixtures (parallel to test_cli_synthesize) ----------------------------


def _make_config(path: Path, library_root: Path) -> None:
    path.write_text(
        yaml.dump({"library_root": str(library_root)}, default_flow_style=False)
    )


def _write_registry(library_root: Path, entries: dict[str, dict]) -> None:
    payload = {
        "_schema_version": 1,
        "updated_at": "2026-04-01T00:00:00Z",
        "decks": entries,
    }
    (library_root / "registry.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _entry(note_id: str, markdown_path: str) -> dict:
    return {
        "id": note_id,
        "title": note_id,
        "type": "evidence",
        "markdown_path": markdown_path,
        "deck_dir": str(Path(markdown_path).parent).replace("\\", "/"),
        "client": "ClientA",
        "engagement": "DD_Q1",
        "source_relative_path": "deck.pptx",
        "source_hash": f"{note_id}-hash",
        "version": 1,
        "converted": "2026-04-01T00:00:00Z",
    }


def _write_note(path: Path, frontmatter: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(
        frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    path.write_text(
        f"---\n{yaml_str}---\n\n# {frontmatter['title']}\n", encoding="utf-8"
    )


def _base_fm(note_id: str, title: str, **overrides) -> dict:
    fm = {
        "id": note_id,
        "title": title,
        "type": "evidence",
        "status": "active",
        "client": "ClientA",
        "engagement": "DD_Q1",
        "created": "2026-04-01",
        "modified": "2026-04-01",
        "curation_level": "L0",
        "review_status": "clean",
        "source": "deck.pptx",
        "source_hash": f"{note_id}-hash",
        "version": 1,
    }
    fm.update(overrides)
    return fm


def _proposal_fm(
    source_id: str,
    *,
    target_id: str,
    relation: str = "impacts",
    basis_fingerprint: str = "sha256:fp",
    rationale: str = "shared framework",
    signals: list[str] | None = None,
    review_status: str = "clean",
    producer: str = "enrich",
) -> dict:
    proposal_id = compute_relationship_proposal_id(
        source_id=source_id,
        relation=relation,
        target_id=target_id,
        basis_fingerprint=basis_fingerprint,
    )
    return _base_fm(
        source_id,
        source_id,
        review_status=review_status,
        _llm_metadata={
            producer: {
                "axes": {
                    "relationships": {
                        "proposals": [
                            {
                                "proposal_id": proposal_id,
                                "relation": relation,
                                "target_id": target_id,
                                "basis_fingerprint": basis_fingerprint,
                                "confidence": "medium",
                                "signals": list(
                                    signals if signals is not None else ["shared-term: framework"]
                                ),
                                "rationale": rationale,
                                "lifecycle_state": "queued",
                                "producer": producer,
                            }
                        ]
                    }
                }
            }
        },
    )


def _setup_clean_proposal_library(tmp_path: Path, *, rationale: str = "shared framework") -> Path:
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    src = "clienta_evidence_src"
    tgt = "clienta_evidence_tgt"
    _write_registry(
        library,
        {src: _entry(src, "ClientA/src.md"), tgt: _entry(tgt, "ClientA/tgt.md")},
    )
    _write_note(
        library / "ClientA" / "src.md",
        _proposal_fm(src, target_id=tgt, rationale=rationale),
    )
    _write_note(library / "ClientA" / "tgt.md", _base_fm(tgt, "Target"))
    return config_path


def _setup_flagged_source_library(tmp_path: Path) -> Path:
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    src = "clienta_evidence_flagged_src"
    tgt = "clienta_evidence_tgt"
    _write_registry(
        library,
        {
            src: _entry(src, "ClientA/flagged_src.md"),
            tgt: _entry(tgt, "ClientA/tgt.md"),
        },
    )
    _write_note(
        library / "ClientA" / "flagged_src.md",
        _proposal_fm(src, target_id=tgt, review_status="flagged"),
    )
    _write_note(library / "ClientA" / "tgt.md", _base_fm(tgt, "Target"))
    return config_path


def _setup_empty_library(tmp_path: Path) -> Path:
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    _write_registry(library, {})
    return config_path


def _invoke(config_path: Path, args: list[str]):
    runner = CliRunner()
    return runner.invoke(cli, ["--config", str(config_path), *args])


# ---- SRC-CLI-1 -------------------------------------------------------------


def test_search_help_lists_query_arg_and_flags(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--help"])
    assert result.exit_code == 0
    assert "QUERY" in result.output
    assert "--scope" in result.output
    assert "--producer" in result.output
    assert "--include-flagged" in result.output
    assert "--json" in result.output
    assert "--limit" in result.output


# ---- SRC-CLI-2 -------------------------------------------------------------


def test_search_registered():
    assert "search" in cli.commands


# ---- SRC-CLI-3 -------------------------------------------------------------


def test_search_query_required(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    result = _invoke(config_path, ["search"])
    assert result.exit_code == 2
    assert "Missing argument" in result.output or "Usage" in result.output


# ---- SRC-CLI-4 -------------------------------------------------------------


def test_search_emits_stdout_default(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    result = _invoke(config_path, ["search", "framework"])
    assert result.exit_code == 0, result.output
    assert "Search for 'framework' in scope" in result.output


# ---- SRC-CLI-5 -------------------------------------------------------------


def test_search_json_output_envelope_keys(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    result = _invoke(config_path, ["search", "framework", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert REQUIRED_ENVELOPE_KEYS == set(payload.keys())


# ---- SRC-CLI-6, SRC-CLI-7 --------------------------------------------------


def test_search_envelope_schema_version_1_1(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    result = _invoke(config_path, ["search", "framework", "--json"])
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.1"


def test_search_envelope_command_search(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    result = _invoke(config_path, ["search", "framework", "--json"])
    payload = json.loads(result.output)
    assert payload["command"] == "search"


# ---- SRC-CLI-8, SRC-CLI-9 (query round-trip) -------------------------------


def test_search_envelope_query_roundtrip_verbatim(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    result = _invoke(config_path, ["search", "Foo Bar", "--json"])
    payload = json.loads(result.output)
    assert payload["query"] == "Foo Bar"


def test_search_envelope_query_roundtrip_unicode(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    result = _invoke(config_path, ["search", "Straße", "--json"])
    payload = json.loads(result.output)
    assert payload["query"] == "Straße"


# ---- SRC-CLI-10, SRC-CLI-11 (trust override) -------------------------------


def test_search_envelope_trust_override_mirrors_flag(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r1 = _invoke(config_path, ["search", "framework", "--json"])
    r2 = _invoke(
        config_path, ["search", "framework", "--json", "--include-flagged"]
    )
    assert json.loads(r1.output)["trust_override_active"] is False
    assert json.loads(r2.output)["trust_override_active"] is True


def test_search_include_flagged_flag_flows(tmp_path):
    config_path = _setup_flagged_source_library(tmp_path)
    result_without = _invoke(config_path, ["search", "framework", "--json"])
    payload_without = json.loads(result_without.output)
    assert payload_without["excluded_flagged_count"] >= 1
    result_with = _invoke(
        config_path, ["search", "framework", "--json", "--include-flagged"]
    )
    payload_with = json.loads(result_with.output)
    assert any(f["trust_status"] == "flagged" for f in payload_with["findings"])


# ---- SRC-CLI-12 (producer filter) ------------------------------------------


def test_search_producer_filter_narrows(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    # producer='enrich' should keep the one proposal
    r = _invoke(
        config_path, ["search", "framework", "--producer", "enrich", "--json"]
    )
    assert r.exit_code == 0
    payload = json.loads(r.output)
    assert len(payload["findings"]) == 1
    # Wrong-case should filter it out
    r2 = _invoke(
        config_path, ["search", "framework", "--producer", "Enrich", "--json"]
    )
    payload2 = json.loads(r2.output)
    assert len(payload2["findings"]) == 0


# ---- SRC-CLI-13 (zero-matches with exclusions) -----------------------------


def test_search_zero_findings_with_exclusions(tmp_path):
    config_path = _setup_flagged_source_library(tmp_path)
    # QUERY matches the flagged proposal; without --include-flagged it's excluded
    r = _invoke(config_path, ["search", "framework"])
    assert r.exit_code == 0
    assert "Matches: 0" in r.output
    assert "Excluded (flagged inputs in scope):" in r.output
    assert "use --include-flagged to include" in r.output


# ---- SRC-CLI-14 (zero-matches zero-excluded breadcrumb) --------------------


def test_search_zero_findings_zero_exclusions_has_diagnostic(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    r = _invoke(config_path, ["search", "nonexistent"])
    assert r.exit_code == 0
    assert "No matches for 'nonexistent'" in r.output


# ---- SRC-CLI-15 ------------------------------------------------------------


def test_search_invalid_scope_exits_nonzero(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(
        config_path, ["search", "framework", "--scope", "nonexistent-scope"]
    )
    assert r.exit_code == 1


# ---- SRC-CLI-16 ------------------------------------------------------------


def test_search_envelope_scope_null_for_library_wide(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(config_path, ["search", "framework", "--json"])
    payload = json.loads(r.output)
    assert payload["scope"] is None


# ---- SRC-CLI-17 (narrowed: PEER-SF-007) ------------------------------------


def test_search_help_copy_mentions_v0_9_0_structural(tmp_path):
    runner = CliRunner()
    r = runner.invoke(cli, ["search", "--help"])
    # Click line-wraps help output; normalize whitespace before substring search.
    normalized = " ".join(r.output.split())
    assert "v0.9.0 structural MVP" in normalized


# ---- SRC-CLI-18, SRC-CLI-19, SRC-CLI-20 -------------------------------


def test_search_envelope_finding_11_shared_contract_keys(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(config_path, ["search", "framework", "--json"])
    payload = json.loads(r.output)
    assert len(payload["findings"]) >= 1
    finding = payload["findings"][0]
    assert SHARED_CONTRACT_FINDING_KEYS <= set(finding.keys())


def test_search_envelope_finding_schema_gate_result_null(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(config_path, ["search", "framework", "--json"])
    payload = json.loads(r.output)
    for f in payload["findings"]:
        assert f["schema_gate_result"] is None


def test_search_envelope_finding_has_input_fingerprint(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(config_path, ["search", "framework", "--json"])
    payload = json.loads(r.output)
    for f in payload["findings"]:
        assert isinstance(f["input_fingerprint"], str)
        assert f["input_fingerprint"]


# ---- SRC-CLI-21 ------------------------------------------------------------


def test_search_limit_caps_findings(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(config_path, ["search", "framework", "--json", "--limit", "0"])
    payload = json.loads(r.output)
    assert len(payload["findings"]) == 0


# ---- SRC-CLI-22 ------------------------------------------------------------


def test_search_stdout_arrow_rendering(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(config_path, ["search", "framework"])
    assert "--impacts-->" in r.output


# ---- SRC-CLI-23 ------------------------------------------------------------


def test_search_evidence_bundle_match_in_json(tmp_path):
    # Library's proposal has signals=["shared-term: framework"]; search "shared-term"
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(config_path, ["search", "shared-term", "--json"])
    payload = json.loads(r.output)
    assert len(payload["findings"]) >= 1


# ---- SRC-CLI-24 (truncation footer, ADV-MIN-002) ---------------------------


def test_search_limit_truncation_stdout_footer(tmp_path):
    # Build a library with 2 matching proposals, limit to 1, check footer
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    entries = {}
    for i in range(3):
        src = f"clienta_evidence_s{i}"
        tgt = f"clienta_evidence_t{i}"
        entries[src] = _entry(src, f"ClientA/s{i}.md")
        entries[tgt] = _entry(tgt, f"ClientA/t{i}.md")
    _write_registry(library, entries)
    for i in range(3):
        src = f"clienta_evidence_s{i}"
        tgt = f"clienta_evidence_t{i}"
        _write_note(
            library / "ClientA" / f"s{i}.md",
            _proposal_fm(
                src,
                target_id=tgt,
                rationale="shared framework",
                basis_fingerprint=f"sha:f{i}",
            ),
        )
        _write_note(library / "ClientA" / f"t{i}.md", _base_fm(tgt, tgt))
    r = _invoke(config_path, ["search", "framework", "--limit", "1"])
    assert r.exit_code == 0
    assert "(showing 1 of 3; use --limit to adjust)" in r.output


# ---- SRC-CLI-25, SRC-CLI-26 (empty / whitespace QUERY, CB-2) ---------------


def test_search_empty_query_cli_exits_2(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    r = _invoke(config_path, ["search", ""])
    assert r.exit_code == 2
    assert "non-whitespace" in r.output or "QUERY must contain" in r.output


def test_search_whitespace_only_query_cli_exits_2(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    r = _invoke(config_path, ["search", "   "])
    assert r.exit_code == 2


# ---- SRC-CLI-27 (registry-missing zero results, CB-3) ----------------------


def test_search_missing_registry_zero_results(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    # Intentionally skip writing registry.json
    r = _invoke(config_path, ["search", "foo"])
    assert r.exit_code == 0
    assert "Matches: 0" in r.output


# ---- SRC-CLI-28 (CSF-1 dash alias) -----------------------------------------


def test_search_envelope_scope_null_for_dash_alias(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(config_path, ["search", "framework", "--scope", "-", "--json"])
    payload = json.loads(r.output)
    assert payload["scope"] is None


# ---- SRC-CLI-29 (CSF-2 limit negative) -------------------------------------


def test_search_limit_negative_cli_exits_2(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    r = _invoke(config_path, ["search", "foo", "--limit", "-1"])
    assert r.exit_code == 2


# ---- SRC-CLI-30 (CSF-3 producer hint) --------------------------------------


def test_search_producer_zero_match_hint(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(
        config_path, ["search", "framework", "--producer", "WrongCase"]
    )
    assert r.exit_code == 0
    assert "Hint: --producer matches exactly" in r.output
    assert "enrich" in r.output


# ---- SRC-CLI-31 (PROD-SF-003 scope-error suggests status) ------------------


def test_search_invalid_scope_error_suggests_status(tmp_path):
    config_path = _setup_clean_proposal_library(tmp_path)
    r = _invoke(
        config_path, ["search", "framework", "--scope", "nonexistent-scope"]
    )
    assert r.exit_code == 1
    assert "Try `folio status`" in r.output or "folio status" in (
        r.stderr if hasattr(r, "stderr") else r.output
    )
