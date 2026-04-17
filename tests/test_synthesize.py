"""Unit tests for folio.synthesize.

Covers SYN-1..SYN-24 per docs/specs/v0.8.0_folio_synthesize_spec.md §9.1.
v0.8.0 sub-slice 2 of Shipping Plan §15.6 — greenfield `folio synthesize`.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from folio import synthesize as synth_mod
from folio.config import FolioConfig
from folio.links import RelationshipProposalView, SuppressionCounts
from folio.pipeline.enrich_data import RelationshipProposal
from folio.synthesize import (
    COMMAND_NAME,
    SCHEMA_VERSION,
    SynthesisFinding,
    SynthesisReport,
    render_envelope,
    synthesize,
)

SHARED_CONTRACT_KEYS = {
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


def _make_config(tmp_path: Path) -> FolioConfig:
    library = tmp_path / "library"
    library.mkdir(exist_ok=True)
    (library / "registry.json").write_text(
        json.dumps({"_schema_version": 1, "decks": {}}), encoding="utf-8"
    )
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(
        yaml.dump({"library_root": str(library)}, default_flow_style=False)
    )
    return FolioConfig.load(config_path)


def _make_proposal(
    *,
    proposal_id: str = "rprop-abc",
    relation: str = "draws_from",
    target_id: str = "target_doc",
    basis_fingerprint: str = "sha256:bbb",
    rationale: str = "shared framework",
    signals: list[str] | None = None,
    producer: str = "enrich",
    lifecycle_state: str = "queued",
) -> RelationshipProposal:
    return RelationshipProposal(
        relation=relation,
        target_id=target_id,
        basis_fingerprint=basis_fingerprint,
        confidence="medium",
        signals=list(signals or ["shared-term: framework"]),
        rationale=rationale,
        lifecycle_state=lifecycle_state,
        proposal_id=proposal_id,
        producer=producer,
    )


def _make_view(
    *,
    source_id: str = "source_doc",
    flagged_inputs: list[str] | None = None,
    proposal: RelationshipProposal | None = None,
) -> RelationshipProposalView:
    prop = proposal or _make_proposal()
    return RelationshipProposalView(
        source_id=source_id,
        source_path=Path("/tmp/source.md"),
        source_markdown_path="source.md",
        producer=prop.producer,
        proposal=prop,
        revived=False,
        flagged_inputs=list(flagged_inputs or []),
    )


# ---- SYN-1 -----------------------------------------------------------------

def test_synthesis_dataclass_shapes():
    finding_fields = {f.name for f in fields(SynthesisFinding)}
    assert SHARED_CONTRACT_KEYS <= finding_fields
    assert "proposal_id" in finding_fields
    assert "relation" in finding_fields
    assert "flagged_inputs" in finding_fields  # D2-SF-11 closure
    report_fields = {f.name for f in fields(SynthesisReport)}
    # D2-SF-12 closure adds total_available + truncated (internal-only,
    # not emitted in envelope until v0.8.1 schema bump).
    assert report_fields >= {
        "scope",
        "findings",
        "excluded_flagged_count",
        "trust_override_active",
    }
    assert "total_available" in report_fields
    assert "truncated" in report_fields


# ---- SYN-2 -----------------------------------------------------------------

def test_synthesize_calls_collect_function(tmp_path):
    # Library has one entry under ClientA to satisfy scope resolution.
    config = _make_config(tmp_path)
    library = config.library_root
    registry_path = library / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "_schema_version": 1,
                "decks": {
                    "clienta_evidence_x": {
                        "id": "clienta_evidence_x",
                        "title": "X",
                        "type": "evidence",
                        "markdown_path": "ClientA/x.md",
                        "deck_dir": "ClientA",
                        "source_relative_path": "deck.pptx",
                        "source_hash": "x-hash",
                        "version": 1,
                        "converted": "2026-04-01T00:00:00Z",
                        "client": "ClientA",
                        "engagement": "DD_Q1",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([], SuppressionCounts()),
    ) as collect:
        synthesize(config, scope="ClientA", include_flagged=True)
    assert collect.call_count == 1
    kwargs = collect.call_args.kwargs
    # DCB-1 closure: subtree scopes route via `scope=`, doc IDs via `doc_id=`.
    # "ClientA" matches the entry's deck_dir subtree, so it resolves as scope.
    assert kwargs["scope"] == "ClientA"
    assert kwargs["doc_id"] is None
    assert kwargs["include_flagged"] is True


# ---- SYN-3 -----------------------------------------------------------------

def test_synthesize_uses_shared_trust_helper():
    from folio.tracking import trust as trust_mod

    assert synth_mod.derive_trust_status is trust_mod.derive_trust_status


# ---- SYN-4 / SYN-5 / SYN-6 -------------------------------------------------

def test_trust_status_ok_for_unflagged_view(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(flagged_inputs=[])
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = synthesize(config)
    assert report.findings[0].trust_status == "ok"


def test_trust_status_flagged_for_source_flag(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(flagged_inputs=["source"])
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = synthesize(config, include_flagged=True)
    assert report.findings[0].trust_status == "flagged"


def test_trust_status_flagged_for_target_flag(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(flagged_inputs=["target"])
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = synthesize(config, include_flagged=True)
    assert report.findings[0].trust_status == "flagged"


# ---- SYN-7 (CB-1 closure) --------------------------------------------------

def test_excluded_flagged_count_routes_from_counts_flagged_input(tmp_path):
    config = _make_config(tmp_path)
    counts = SuppressionCounts(flagged_input=3, rejection_memory={"enrich": 5})
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([], counts),
    ):
        report = synthesize(config)
    assert report.excluded_flagged_count == 3


# ---- SYN-8 -----------------------------------------------------------------

def test_trust_override_active_reflects_flag(tmp_path):
    config = _make_config(tmp_path)
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([], SuppressionCounts()),
    ):
        on = synthesize(config, include_flagged=True)
        off = synthesize(config, include_flagged=False)
    assert on.trust_override_active is True
    assert off.trust_override_active is False


# ---- SYN-9 (producer-side exact) -------------------------------------------

def test_render_envelope_v0_8_0_producer_exact_keys():
    report = SynthesisReport(
        scope=None, findings=[], excluded_flagged_count=0, trust_override_active=False
    )
    envelope = render_envelope(report)
    assert set(envelope.keys()) == {
        "schema_version",
        "command",
        "scope",
        "trust_override_active",
        "excluded_flagged_count",
        "findings",
    }


# ---- SYN-10 / SYN-11 -------------------------------------------------------

def test_render_envelope_schema_version_and_command():
    report = SynthesisReport(
        scope=None, findings=[], excluded_flagged_count=0, trust_override_active=False
    )
    envelope = render_envelope(report)
    assert envelope["schema_version"] == "1.0"
    assert envelope["command"] == "synthesize"


# ---- SYN-12 (CB-2 closure) -------------------------------------------------

def test_render_envelope_finding_has_all_11_shared_contract_keys(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view()
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = synthesize(config)
    envelope = render_envelope(report)
    finding = envelope["findings"][0]
    assert SHARED_CONTRACT_KEYS <= set(finding.keys())
    assert "proposal_id" in finding
    assert "relation" in finding


# ---- SYN-13 ----------------------------------------------------------------

def test_finding_proposal_id_preserves_view_proposal_id(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(proposal=_make_proposal(proposal_id="rprop-xyz"))
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = synthesize(config)
    assert report.findings[0].proposal_id == "rprop-xyz"


# ---- SYN-14 ----------------------------------------------------------------

def test_finding_subject_id_is_none_for_relationship(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view()
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = synthesize(config)
    assert report.findings[0].subject_id is None


# ---- SYN-15 ----------------------------------------------------------------

FORBIDDEN_SUBSTRINGS = [
    "exec(",
    "compile(",
    "os.system",
    "__import__(",
]


def test_no_forbidden_symbols_in_module():
    source = Path("folio/synthesize.py").read_text(encoding="utf-8")
    for needle in FORBIDDEN_SUBSTRINGS:
        assert needle not in source, needle
    # yaml.load without SafeLoader
    assert "yaml.load(" not in source or "yaml.safe_load" in source

    # AST walk for dangerous call patterns
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                    and node.func.attr == "run"
                ):
                    for kw in node.keywords:
                        assert not (
                            kw.arg == "shell"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True
                        ), "subprocess.run(shell=True) forbidden"


# ---- SYN-16 ----------------------------------------------------------------

def test_no_direct_llm_imports_in_module():
    source = Path("folio/synthesize.py").read_text(encoding="utf-8")
    for needle in [
        "from folio.llm",
        "import folio.llm",
        "from openai",
        "import openai",
        "from anthropic",
        "import anthropic",
    ]:
        assert needle not in source, needle


# ---- SYN-17 ----------------------------------------------------------------

def test_schema_version_and_command_constants_exported():
    assert SCHEMA_VERSION == "1.0"
    assert COMMAND_NAME == "synthesize"


# ---- SYN-18 (CB-1 regression guard; SF-C4 closure) -------------------------

def test_excluded_count_ignores_rejection_memory(tmp_path):
    config = _make_config(tmp_path)
    counts = SuppressionCounts(
        rejection_memory={"producer_a": 5}, flagged_input=2
    )
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([], counts),
    ):
        report = synthesize(config)
    assert report.excluded_flagged_count == 2
    assert report.excluded_flagged_count != 7  # NOT total()


# ---- SYN-19 (SF-C5 closure) ------------------------------------------------

def test_derive_trust_status_called_once_per_view(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    views = [_make_view(source_id=f"doc_{i}") for i in range(5)]
    call_log: list = []

    def spy(view):
        call_log.append(view.source_id)
        return "ok"

    monkeypatch.setattr(synth_mod, "derive_trust_status", spy)
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=(views, SuppressionCounts()),
    ):
        report = synthesize(config)
    assert len(call_log) == 5
    assert call_log == [f"doc_{i}" for i in range(5)]
    assert len(report.findings) == 5


# ---- SYN-20 (SF-C7 closure) ------------------------------------------------

def test_no_transitive_llm_imports_after_import(tmp_path):
    # Narrowed to external provider SDKs (openai, anthropic). folio.llm is
    # transitively imported by folio.config (LLMConfig) — loading it does
    # NOT trigger an LLM call; that is the actual concern. The SF-C7 /
    # ADV-SF-005 guard is against provider-SDK loading, which would
    # indicate a direct or transitive LLM invocation path.
    script = (
        "import sys\n"
        "from folio import synthesize\n"
        "from folio.config import FolioConfig\n"
        "import yaml\n"
        "from pathlib import Path\n"
        f"cfg = FolioConfig.load(Path({str(tmp_path / 'folio.yaml')!r}))\n"
        "synthesize.synthesize(cfg)\n"
        "for mod in ('openai', 'anthropic'):\n"
        "    assert mod not in sys.modules, mod\n"
        "print('ok')\n"
    )
    _make_config(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


# ---- SYN-21 (CB-2 closure) -------------------------------------------------

def test_schema_gate_result_is_none_on_all_findings(tmp_path):
    config = _make_config(tmp_path)
    views = [_make_view(source_id=f"doc_{i}") for i in range(3)]
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=(views, SuppressionCounts()),
    ):
        report = synthesize(config)
    for finding in report.findings:
        assert finding.schema_gate_result is None


# ---- SYN-22 (CB-2 closure) -------------------------------------------------

def test_input_fingerprint_matches_view_basis_fingerprint(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(
        proposal=_make_proposal(basis_fingerprint="sha256:unique-fp-value")
    )
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = synthesize(config)
    assert report.findings[0].input_fingerprint == "sha256:unique-fp-value"


# ---- SYN-23 (SF-C8 closure) ------------------------------------------------

def test_limit_truncates_findings_after_count(tmp_path):
    config = _make_config(tmp_path)
    views = [_make_view(source_id=f"doc_{i}") for i in range(10)]
    counts = SuppressionCounts(flagged_input=4)
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=(views, counts),
    ):
        report = synthesize(config, limit=3)
    assert len(report.findings) == 3
    # excluded_flagged_count reflects full upstream exclusion, not post-limit
    assert report.excluded_flagged_count == 4


# ---- SYN-24 (read-only invariant) ------------------------------------------

def test_no_registry_or_doc_mutations(tmp_path):
    config = _make_config(tmp_path)
    registry_path = (tmp_path / "library" / "registry.json")
    registry_bytes_before = registry_path.read_bytes()
    with patch(
        "folio.synthesize.collect_pending_relationship_proposals",
        return_value=([_make_view()], SuppressionCounts()),
    ):
        synthesize(config)
    registry_bytes_after = registry_path.read_bytes()
    assert registry_bytes_before == registry_bytes_after
