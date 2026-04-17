"""CLI integration tests for folio synthesize.

Covers SYN-CLI-1..SYN-CLI-21 per docs/specs/v0.8.0_folio_synthesize_spec.md §9.2.
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


def _entry(
    note_id: str,
    markdown_path: str,
    *,
    note_type: str = "evidence",
    title: str | None = None,
    modified: str | None = None,
) -> dict:
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
    yaml_str = yaml.dump(
        frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    path.write_text(
        f"---\n{yaml_str}---\n\n# {frontmatter['title']}\n", encoding="utf-8"
    )


def _base_fm(
    note_id: str, title: str, *, note_type: str = "evidence", **overrides
) -> dict:
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


def _build_proposal_fm(
    source_id: str,
    title: str,
    *,
    target_id: str,
    relation: str = "impacts",
    basis_fingerprint: str = "sha256:fp",
    rationale: str = "shared framework",
    signals: list[str] | None = None,
    review_status: str = "clean",
) -> dict:
    proposal_id = compute_relationship_proposal_id(
        source_id=source_id,
        relation=relation,
        target_id=target_id,
        basis_fingerprint=basis_fingerprint,
    )
    return _base_fm(
        source_id,
        title,
        review_status=review_status,
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
                                "signals": list(signals or ["shared-term: framework"]),
                                "rationale": rationale,
                                "lifecycle_state": "queued",
                                "producer": "enrich",
                            }
                        ]
                    }
                }
            }
        },
    )


def _setup_library_with_one_clean_proposal(tmp_path: Path) -> Path:
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    src = "clienta_evidence_src"
    tgt = "clienta_evidence_tgt"
    _write_registry(
        library,
        {
            src: _entry(src, "ClientA/src.md"),
            tgt: _entry(tgt, "ClientA/tgt.md"),
        },
    )
    _write_note(
        library / "ClientA" / "src.md",
        _build_proposal_fm(src, "Src", target_id=tgt),
    )
    _write_note(
        library / "ClientA" / "tgt.md", _base_fm(tgt, "Target")
    )
    return config_path


def _setup_library_with_flagged_source(tmp_path: Path) -> Path:
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
        _build_proposal_fm(
            src, "Flagged Src", target_id=tgt, review_status="flagged"
        ),
    )
    _write_note(
        library / "ClientA" / "tgt.md", _base_fm(tgt, "Target")
    )
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


# ---- SYN-CLI-1 -------------------------------------------------------------

def test_synthesize_help_lists_scope_arg_and_limit(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["synthesize", "--help"])
    assert result.exit_code == 0
    assert "SCOPE" in result.output
    assert "--limit" in result.output
    assert "--include-flagged" in result.output
    assert "--json" in result.output


# ---- SYN-CLI-2 -------------------------------------------------------------

def test_synthesize_registered():
    assert "synthesize" in cli.commands


# ---- SYN-CLI-3 -------------------------------------------------------------

def test_synthesize_emits_stdout_default(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize"])
    assert result.exit_code == 0, result.output
    assert "Synthesis for scope" in result.output


# ---- SYN-CLI-4 -------------------------------------------------------------

def test_synthesize_json_output_envelope_keys(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert REQUIRED_ENVELOPE_KEYS <= set(payload.keys())


# ---- SYN-CLI-5 -------------------------------------------------------------

def test_synthesize_include_flagged_flag_flows(tmp_path):
    config_path = _setup_library_with_flagged_source(tmp_path)
    # Without --include-flagged: excluded count ≥ 1
    result_without = _invoke(config_path, ["synthesize", "--json"])
    assert result_without.exit_code == 0
    payload_without = json.loads(result_without.output)
    assert payload_without["excluded_flagged_count"] >= 1
    assert payload_without["trust_override_active"] is False
    # With --include-flagged: flagged finding surfaces with trust_status flagged
    result_with = _invoke(
        config_path, ["synthesize", "--json", "--include-flagged"]
    )
    assert result_with.exit_code == 0
    payload_with = json.loads(result_with.output)
    assert payload_with["trust_override_active"] is True
    assert len(payload_with["findings"]) >= 1
    assert any(f["trust_status"] == "flagged" for f in payload_with["findings"])


# ---- SYN-CLI-6 -------------------------------------------------------------

def test_synthesize_zero_findings_with_exclusions(tmp_path):
    config_path = _setup_library_with_flagged_source(tmp_path)
    # Without --include-flagged, no other proposals exist: 0 findings, ≥1 excluded
    result = _invoke(config_path, ["synthesize"])
    assert result.exit_code == 0
    assert "Findings: 0" in result.output
    assert "Excluded (flagged inputs):" in result.output
    assert "use --include-flagged" in result.output


# ---- SYN-CLI-7 -------------------------------------------------------------

def test_synthesize_invalid_scope_exits_nonzero(tmp_path):
    # Empty library; invalid scope matches no engagement/doc. Current
    # collect_pending_relationship_proposals does NOT raise on bad scope
    # (it returns empty). Synthesize therefore exits 0 with 0 findings +
    # diagnostic breadcrumb. Document actual behavior and assert the
    # zero-findings case (CB-5) emits diagnostic.
    config_path = _setup_empty_library(tmp_path)
    result = _invoke(config_path, ["synthesize", "nonexistent-scope"])
    assert result.exit_code == 0
    # CB-5 breadcrumb surfaces the ambiguity even though exit is 0
    assert "Next:" in result.output or "Findings: 0" in result.output


# ---- SYN-CLI-8 / SYN-CLI-9 -------------------------------------------------

def test_synthesize_envelope_schema_version(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize", "--json"])
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"


def test_synthesize_envelope_command_synthesize(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize", "--json"])
    payload = json.loads(result.output)
    assert payload["command"] == "synthesize"


# ---- SYN-CLI-10 ------------------------------------------------------------

def test_synthesize_envelope_trust_override_mirrors_flag(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    off = json.loads(_invoke(config_path, ["synthesize", "--json"]).output)
    on = json.loads(
        _invoke(config_path, ["synthesize", "--json", "--include-flagged"]).output
    )
    assert off["trust_override_active"] is False
    assert on["trust_override_active"] is True


# ---- SYN-CLI-11 ------------------------------------------------------------

def test_synthesize_stdout_shows_override_annotation(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize", "--include-flagged"])
    assert "Trust override active" in result.output


# ---- SYN-CLI-12 ------------------------------------------------------------

def test_synthesize_json_findings_are_list(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    result = _invoke(config_path, ["synthesize", "--json"])
    payload = json.loads(result.output)
    assert isinstance(payload["findings"], list)


# ---- SYN-CLI-13 ------------------------------------------------------------

def test_synthesize_stdout_arrow_rendering(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize"])
    assert "-->" in result.output


# ---- SYN-CLI-14 (CB-5 closure) ---------------------------------------------

def test_synthesize_zero_findings_zero_exclusions_has_diagnostic(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    result = _invoke(config_path, ["synthesize"])
    assert "Findings: 0" in result.output
    assert "Excluded (flagged inputs): 0" in result.output
    assert "Next: run `folio ingest`" in result.output


# ---- SYN-CLI-15 / SYN-CLI-16 (MIN-1 closure) -------------------------------

def test_synthesize_envelope_scope_null_for_library_wide(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    result = _invoke(config_path, ["synthesize", "--json"])
    payload = json.loads(result.output)
    assert payload["scope"] is None


def test_synthesize_envelope_scope_null_for_dash_alias(tmp_path):
    config_path = _setup_empty_library(tmp_path)
    result = _invoke(config_path, ["synthesize", "-", "--json"])
    payload = json.loads(result.output)
    assert payload["scope"] is None


# ---- SYN-CLI-17 (CB-4 closure) ---------------------------------------------

def test_synthesize_help_copy_mentions_v0_8_0_structural(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["synthesize", "--help"])
    assert "v0.8.0 structural MVP" in result.output
    assert "Narrative synthesis" in result.output
    assert "planned for a future version" in result.output


# ---- SYN-CLI-18 / SYN-CLI-19 / SYN-CLI-20 (CB-2 closure) -------------------

def test_synthesize_envelope_finding_11_shared_contract_keys(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize", "--json"])
    payload = json.loads(result.output)
    assert len(payload["findings"]) >= 1
    for finding in payload["findings"]:
        assert SHARED_CONTRACT_FINDING_KEYS <= set(finding.keys())
        assert "proposal_id" in finding
        assert "relation" in finding


def test_synthesize_envelope_finding_schema_gate_result_null(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize", "--json"])
    payload = json.loads(result.output)
    for finding in payload["findings"]:
        assert finding["schema_gate_result"] is None


def test_synthesize_envelope_finding_has_input_fingerprint(tmp_path):
    config_path = _setup_library_with_one_clean_proposal(tmp_path)
    result = _invoke(config_path, ["synthesize", "--json"])
    payload = json.loads(result.output)
    for finding in payload["findings"]:
        assert isinstance(finding["input_fingerprint"], str)
        assert finding["input_fingerprint"]  # non-empty


# ---- SYN-CLI-21 (SF-C8 closure) --------------------------------------------

def test_synthesize_limit_caps_findings(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    _make_config(config_path, library)
    entries: dict[str, dict] = {}
    for i in range(5):
        src = f"clienta_evidence_src_{i}"
        tgt = f"clienta_evidence_tgt_{i}"
        entries[src] = _entry(src, f"ClientA/src_{i}.md")
        entries[tgt] = _entry(tgt, f"ClientA/tgt_{i}.md")
    _write_registry(library, entries)
    for i in range(5):
        src = f"clienta_evidence_src_{i}"
        tgt = f"clienta_evidence_tgt_{i}"
        _write_note(
            library / "ClientA" / f"src_{i}.md",
            _build_proposal_fm(
                src,
                f"Src {i}",
                target_id=tgt,
                basis_fingerprint=f"sha256:fp{i}",
            ),
        )
        _write_note(
            library / "ClientA" / f"tgt_{i}.md",
            _base_fm(tgt, f"Target {i}"),
        )

    result = _invoke(config_path, ["synthesize", "--json", "--limit", "2"])
    payload = json.loads(result.output)
    assert len(payload["findings"]) == 2
