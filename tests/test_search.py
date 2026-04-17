"""Unit tests for folio.search.

Covers SRC-1..SRC-41 per docs/specs/v0.9.0_folio_search_spec.md §9.1.
v0.9.0 sub-slice 3 of Shipping Plan §15.6 — greenfield `folio search`.
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

from folio import search as search_mod
from folio.config import FolioConfig
from folio.links import RelationshipProposalView, SuppressionCounts
from folio.pipeline.enrich_data import RelationshipProposal
from folio.search import (
    COMMAND_NAME,
    SCHEMA_VERSION,
    SEARCHABLE_FIELDS,
    SearchFinding,
    SearchReport,
    ScopeResolutionError,
    _normalize_search_text,
    _view_matches,
    render_envelope,
    search,
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


# ---- Fixtures --------------------------------------------------------------


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
        signals=list(signals if signals is not None else ["shared-term: framework"]),
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


# ---- SRC-1 -----------------------------------------------------------------


def test_search_dataclass_shapes():
    finding_fields = {f.name for f in fields(SearchFinding)}
    assert SHARED_CONTRACT_KEYS <= finding_fields
    assert "proposal_id" in finding_fields
    assert "relation" in finding_fields
    assert "flagged_inputs" in finding_fields
    report_fields = {f.name for f in fields(SearchReport)}
    assert report_fields >= {
        "scope",
        "query",
        "findings",
        "excluded_flagged_count",
        "trust_override_active",
        "total_available",
        "truncated",
    }


# ---- SRC-2 -----------------------------------------------------------------


def test_search_calls_collect_function(tmp_path):
    config = _make_config(tmp_path)
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([], SuppressionCounts()),
    ) as collect:
        search(config, query="framework", include_flagged=True)
    assert collect.call_count == 1
    kwargs = collect.call_args.kwargs
    assert kwargs["scope"] is None
    assert kwargs["doc_id"] is None
    assert kwargs["include_flagged"] is True


# ---- SRC-3 -----------------------------------------------------------------


def test_search_uses_shared_trust_helper():
    from folio.tracking import trust as trust_mod

    assert search_mod.derive_trust_status is trust_mod.derive_trust_status


# ---- SRC-4 -----------------------------------------------------------------


def test_trust_status_ok_for_unflagged_view(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(flagged_inputs=[])
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="framework")
    assert report.findings[0].trust_status == "ok"


# ---- SRC-5 through SRC-10 (match rules) -----------------------------------


def test_match_source_id(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(source_id="doc_alpha")
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="alpha")
    assert len(report.findings) == 1
    assert report.findings[0].source_id == "doc_alpha"


def test_match_target_id_casefold(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(proposal=_make_proposal(target_id="doc_beta"))
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="BETA")
    assert len(report.findings) == 1


def test_match_relation(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(proposal=_make_proposal(relation="draws_from"))
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="draws")
    assert len(report.findings) == 1


def test_match_producer(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(proposal=_make_proposal(producer="enrich_llm"))
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="llm")
    assert len(report.findings) == 1


def test_match_reason_summary(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(proposal=_make_proposal(rationale="focus on stakeholder buy-in"))
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="stakeholder")
    assert len(report.findings) == 1


def test_match_evidence_bundle_any_element(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(
        proposal=_make_proposal(signals=["other-term: foo", "key-term: roadmap"])
    )
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="roadmap")
    assert len(report.findings) == 1


# ---- SRC-11 ----------------------------------------------------------------


def test_match_evidence_bundle_empty_never_matches(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(
        source_id="zzz",
        proposal=_make_proposal(
            signals=[],
            rationale="no keyword here",
            target_id="zzz2",
            relation="draws_from",
            producer="enrich",
        ),
    )
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="framework")
    assert len(report.findings) == 0


# ---- SRC-12 (Unicode eszett) ----------------------------------------------


def test_match_casefold_unicode_eszett(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(proposal=_make_proposal(rationale="Straße discussion"))
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="STRASSE")
    assert len(report.findings) == 1


# ---- SRC-13 (non-searchable fields) ---------------------------------------


def test_non_searchable_fields_do_not_match(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(
        proposal=_make_proposal(
            proposal_id="rprop-unique-12345",
            basis_fingerprint="sha256:nope",
            rationale="generic",
            signals=["none"],
            target_id="zz",
            relation="draws_from",
            producer="enrich",
        ),
        source_id="generic_source",
    )
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="rprop-unique-12345")
    assert len(report.findings) == 0
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="sha256:nope")
    assert len(report.findings) == 0


# ---- SRC-14 (empty QUERY ValueError) --------------------------------------


def test_empty_query_raises_value_error(tmp_path):
    config = _make_config(tmp_path)
    with pytest.raises(ValueError):
        search(config, query="")


# ---- SRC-15..17 (producer filter) -----------------------------------------


def test_producer_filter_exact_match(tmp_path):
    config = _make_config(tmp_path)
    views = [
        _make_view(
            source_id="a",
            proposal=_make_proposal(proposal_id="r1", producer="enrich"),
        ),
        _make_view(
            source_id="b",
            proposal=_make_proposal(
                proposal_id="r2",
                producer="other",
                rationale="shared framework other",
            ),
        ),
    ]
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=(views, SuppressionCounts()),
    ):
        report = search(config, query="framework", producer="enrich")
    assert len(report.findings) == 1
    assert report.findings[0].producer == "enrich"


def test_producer_filter_case_sensitive(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(proposal=_make_proposal(producer="enrich"))
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="framework", producer="Enrich")
    assert len(report.findings) == 0


def test_producer_filter_applied_after_query(tmp_path):
    config = _make_config(tmp_path)
    views = [
        _make_view(
            source_id="a",
            proposal=_make_proposal(proposal_id="r1", producer="enrich"),
        ),
        _make_view(
            source_id="b",
            proposal=_make_proposal(
                proposal_id="r2",
                producer="enrich",
                rationale="no match term",
                signals=["irrelevant"],
                target_id="other",
                relation="impacts",
            ),
        ),
    ]
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=(views, SuppressionCounts()),
    ):
        report = search(config, query="framework", producer="enrich")
    assert len(report.findings) == 1
    assert report.findings[0].proposal_id == "r1"


# ---- SRC-18, SRC-19 (SuppressionCounts routing, CB-1 carry-forward) -------


def test_excluded_flagged_count_routes_from_counts_flagged_input(tmp_path):
    config = _make_config(tmp_path)
    counts = SuppressionCounts(flagged_input=3, rejection_memory={"enrich": 5})
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([], counts),
    ):
        report = search(config, query="anything")
    assert report.excluded_flagged_count == 3


def test_excluded_count_ignores_rejection_memory(tmp_path):
    config = _make_config(tmp_path)
    counts = SuppressionCounts(flagged_input=2, rejection_memory={"enrich": 5})
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([], counts),
    ):
        report = search(config, query="anything")
    assert report.excluded_flagged_count == 2


# ---- SRC-20 (CSF-4: once per matched view) ---------------------------------


def test_derive_trust_status_called_once_per_matched_view(tmp_path):
    config = _make_config(tmp_path)
    # 10 views, 5 should match QUERY "match_me"
    views = []
    for i in range(10):
        rationale = "match_me text" if i < 5 else "other"
        views.append(
            _make_view(
                source_id=f"s{i}",
                proposal=_make_proposal(
                    proposal_id=f"r{i}",
                    rationale=rationale,
                    target_id=f"t{i}",
                    basis_fingerprint=f"sha:{i}",
                ),
            )
        )

    call_count = {"n": 0}

    def spy(view):
        call_count["n"] += 1
        return "ok"

    with patch("folio.search.derive_trust_status", side_effect=spy):
        with patch(
            "folio.search.collect_pending_relationship_proposals",
            return_value=(views, SuppressionCounts()),
        ):
            report = search(config, query="match_me")
    assert len(report.findings) == 5
    assert call_count["n"] == 5


# ---- SRC-21 ---------------------------------------------------------------


def test_trust_override_active_reflects_flag(tmp_path):
    config = _make_config(tmp_path)
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([], SuppressionCounts()),
    ):
        assert search(config, query="x", include_flagged=True).trust_override_active
        assert not search(config, query="x", include_flagged=False).trust_override_active


# ---- SRC-22 ---------------------------------------------------------------


def test_limit_truncates_findings_after_match_and_filter(tmp_path):
    config = _make_config(tmp_path)
    views = [
        _make_view(
            source_id=f"s{i}",
            proposal=_make_proposal(
                proposal_id=f"r{i}",
                rationale="match",
                target_id=f"t{i}",
                basis_fingerprint=f"sha:{i}",
            ),
        )
        for i in range(10)
    ]
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=(views, SuppressionCounts(flagged_input=2)),
    ):
        report = search(config, query="match", limit=3)
    assert len(report.findings) == 3
    assert report.total_available == 10
    assert report.truncated is True
    assert report.excluded_flagged_count == 2  # NOT post-limit


# ---- SRC-23 (AST-based forbidden-symbol guard, PEER-SF-006) ----------------


def _parse_search_module_ast() -> ast.Module:
    src = (Path(__file__).parent.parent / "folio" / "search.py").read_text(
        encoding="utf-8"
    )
    return ast.parse(src)


def test_no_forbidden_symbols_in_module():
    tree = _parse_search_module_ast()

    forbidden_imports = {"re", "fnmatch"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_imports, (
                    f"forbidden import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module not in forbidden_imports, (
                f"forbidden from-import: {node.module}"
            )

    # re.* call detection
    forbidden_re_funcs = {"search", "match", "compile", "fullmatch", "findall"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            value = node.func.value
            if isinstance(value, ast.Name) and value.id == "re":
                assert node.func.attr not in forbidden_re_funcs, (
                    f"forbidden re.{node.func.attr}"
                )

    # Substring grep fallback for stdlib-dangerous
    src = (Path(__file__).parent.parent / "folio" / "search.py").read_text(
        encoding="utf-8"
    )
    for symbol in [
        "pickle.loads",
        "eval(",
        "exec(",
        "os.system",
        "yaml.load(",
        "__import__(",
    ]:
        assert symbol not in src, f"forbidden symbol present: {symbol}"


# ---- SRC-24 ---------------------------------------------------------------


def test_no_direct_llm_imports_in_module():
    src = (Path(__file__).parent.parent / "folio" / "search.py").read_text(
        encoding="utf-8"
    )
    for bad in ["import folio.llm", "from folio.llm", "import openai", "from openai", "import anthropic", "from anthropic"]:
        assert bad not in src, f"unexpected LLM import: {bad}"


# ---- SRC-25 (CB-4 narrowed) -----------------------------------------------


def test_no_transitive_llm_imports_after_import(tmp_path):
    """CB-4 closure: narrowed to {openai, anthropic} only.

    `folio.llm` is transitively imported by `folio.config` (LLMConfig)
    and entering sys.modules does NOT imply an LLM call. Parity with
    `tests/test_synthesize.py::test_no_transitive_llm_imports_after_import`.
    """
    code = f"""
import json, sys
from pathlib import Path
import yaml
library = Path({str(tmp_path)!r}) / "library"
library.mkdir(exist_ok=True)
(library / "registry.json").write_text(json.dumps({{"_schema_version": 1, "decks": {{}}}}))
cfg_path = Path({str(tmp_path)!r}) / "folio.yaml"
cfg_path.write_text(yaml.dump({{"library_root": str(library)}}))
from folio.config import FolioConfig
from folio.search import search
config = FolioConfig.load(cfg_path)
from folio.links import SuppressionCounts
from unittest.mock import patch
with patch("folio.search.collect_pending_relationship_proposals", return_value=([], SuppressionCounts())):
    _ = search(config, query="x")
assert "openai" not in sys.modules, "openai loaded transitively"
assert "anthropic" not in sys.modules, "anthropic loaded transitively"
print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "OK" in result.stdout


# ---- SRC-26 ---------------------------------------------------------------


def test_schema_version_and_command_constants_exported():
    assert SCHEMA_VERSION == "1.1"
    assert COMMAND_NAME == "search"


# ---- SRC-27, SRC-28, SRC-29 (envelope shape) -------------------------------


def _simple_report(query: str = "framework") -> SearchReport:
    finding = SearchFinding(
        proposal_id="rprop-abc",
        proposal_type="relationship",
        source_id="doc_x",
        target_id="doc_y",
        subject_id=None,
        evidence_bundle=["shared-term: framework"],
        reason_summary="Both docs reference the shared framework.",
        trust_status="ok",
        schema_gate_result=None,
        producer="enrich",
        input_fingerprint="sha256:abc",
        lifecycle_state="queued",
        relation="draws_from",
        flagged_inputs=[],
    )
    return SearchReport(
        scope=None,
        query=query,
        findings=[finding],
        excluded_flagged_count=0,
        trust_override_active=False,
        total_available=1,
        truncated=False,
    )


def test_render_envelope_v0_9_0_producer_exact_keys():
    envelope = render_envelope(_simple_report())
    expected = {
        "schema_version",
        "command",
        "scope",
        "query",
        "trust_override_active",
        "excluded_flagged_count",
        "findings",
    }
    assert set(envelope.keys()) == expected


def test_render_envelope_includes_query_key():
    envelope = render_envelope(_simple_report("framework"))
    assert envelope["query"] == "framework"


def test_render_envelope_query_verbatim_not_casefold():
    envelope = render_envelope(_simple_report("Foo Bar"))
    assert envelope["query"] == "Foo Bar"


# ---- SRC-30 ---------------------------------------------------------------


def test_render_envelope_finding_has_all_11_shared_contract_keys():
    envelope = render_envelope(_simple_report())
    finding = envelope["findings"][0]
    for key in SHARED_CONTRACT_KEYS:
        assert key in finding, f"missing shared-contract key: {key}"
    assert "proposal_id" in finding
    assert "relation" in finding
    assert "flagged_inputs" in finding


# ---- SRC-31, SRC-32 -------------------------------------------------------


def test_schema_gate_result_is_none_on_all_findings(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view()
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="framework")
    for f in report.findings:
        assert f.schema_gate_result is None


def test_input_fingerprint_matches_view_basis_fingerprint(tmp_path):
    config = _make_config(tmp_path)
    view = _make_view(proposal=_make_proposal(basis_fingerprint="sha:unique-xyz"))
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="framework")
    assert report.findings[0].input_fingerprint == "sha:unique-xyz"


# ---- SRC-33 ---------------------------------------------------------------


def test_no_registry_or_doc_mutations(tmp_path):
    config = _make_config(tmp_path)
    library = config.library_root
    registry_path = library / "registry.json"
    before = registry_path.read_bytes()
    view = _make_view()
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        search(config, query="framework")
    after = registry_path.read_bytes()
    assert before == after


# ---- SRC-34, SRC-35 (non-string / None field values, CB-2) ----------------


def test_match_skips_non_string_field_values(tmp_path):
    config = _make_config(tmp_path)
    # Inject a non-string signal via SimpleNamespace (bypasses dataclass
    # typing — simulates malformed frontmatter at runtime).
    proposal = SimpleNamespace(
        proposal_id="rprop-x",
        relation="draws_from",
        target_id="doc_y",
        basis_fingerprint="sha:z",
        confidence="medium",
        signals=[None, 42, "real term here"],
        rationale="generic",
        lifecycle_state="queued",
        producer="enrich",
    )
    view = SimpleNamespace(
        source_id="src",
        source_path=Path("/tmp/s.md"),
        source_markdown_path="s.md",
        producer="enrich",
        proposal=proposal,
        revived=False,
        flagged_inputs=[],
    )
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="real")
    assert len(report.findings) == 1


def test_match_skips_none_target_or_relation(tmp_path):
    config = _make_config(tmp_path)
    proposal = SimpleNamespace(
        proposal_id="rprop-n",
        relation=None,
        target_id=None,
        basis_fingerprint="sha:a",
        confidence="medium",
        signals=["keyword-here"],
        rationale="another thing",
        lifecycle_state="queued",
        producer="enrich",
    )
    view = SimpleNamespace(
        source_id="src",
        source_path=Path("/tmp/s.md"),
        source_markdown_path="s.md",
        producer="enrich",
        proposal=proposal,
        revived=False,
        flagged_inputs=[],
    )
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="keyword-here")
    assert len(report.findings) == 1


# ---- SRC-36 (NFC/NFD equivalence, CB-2) -----------------------------------


def test_match_nfc_nfd_equivalence(tmp_path):
    config = _make_config(tmp_path)
    # Field value uses NFD (combining accent) "cafe\u0301"; QUERY uses NFC ("é").
    view = _make_view(proposal=_make_proposal(rationale="We met at cafe\u0301"))
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view], SuppressionCounts()),
    ):
        report = search(config, query="café")
    assert len(report.findings) == 1


# ---- SRC-37 (zero-width literal) ------------------------------------------


def test_match_zero_width_character_literal(tmp_path):
    config = _make_config(tmp_path)
    zwj = "\u200d"
    # ZWJ in between two letters — match must be literal.
    view_match = _make_view(
        proposal=_make_proposal(rationale=f"foo{zwj}bar context")
    )
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view_match], SuppressionCounts()),
    ):
        report = search(config, query=f"foo{zwj}bar")
    assert len(report.findings) == 1
    # Without ZWJ, the query does NOT match the ZWJ-containing field.
    view_no_zwj = _make_view(
        proposal=_make_proposal(
            rationale="plain prose without special characters at all"
        )
    )
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([view_no_zwj], SuppressionCounts()),
    ):
        report = search(config, query=f"foo{zwj}bar")
    assert len(report.findings) == 0


# ---- SRC-38, SRC-39 (function-level empty rejection, CB-2) ----------------


def test_empty_query_function_level_raises(tmp_path):
    config = _make_config(tmp_path)
    with pytest.raises(ValueError):
        search(config, query="")


def test_whitespace_only_query_function_level_raises(tmp_path):
    config = _make_config(tmp_path)
    with pytest.raises(ValueError):
        search(config, query="   \t\n")


# ---- SRC-40 (surrogate no-crash) ------------------------------------------


def test_surrogate_query_does_not_crash(tmp_path):
    config = _make_config(tmp_path)
    # Surrogate pair can be constructed via chr(0xD83D) (lone surrogate);
    # NFC may raise. We expect either a clean ValueError or a clean return.
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=([], SuppressionCounts()),
    ):
        try:
            search(config, query=chr(0xD83D))
        except (ValueError, UnicodeError):
            pass  # Documented: either rejected cleanly or UnicodeError


# ---- SRC-41 (regex metacharacters match literally, ADV-SF-004) ------------


def test_regex_metacharacters_match_literally(tmp_path):
    config = _make_config(tmp_path)
    views = [
        _make_view(
            source_id="docA",
            proposal=_make_proposal(
                proposal_id="r1", rationale="exactly .* literal here"
            ),
        ),
        _make_view(
            source_id="docB",
            proposal=_make_proposal(
                proposal_id="r2",
                rationale="random text with no wildcards",
                target_id="tB",
                basis_fingerprint="sha:B",
            ),
        ),
    ]
    with patch(
        "folio.search.collect_pending_relationship_proposals",
        return_value=(views, SuppressionCounts()),
    ):
        report = search(config, query=".*")
    # If `.*` were a regex, both would match; literally, only r1 contains ".*".
    assert len(report.findings) == 1
    assert report.findings[0].proposal_id == "r1"


# ---- _normalize_search_text unit tests ------------------------------------


def test_normalize_search_text_none_returns_none():
    assert _normalize_search_text(None) is None


def test_normalize_search_text_int_returns_none():
    assert _normalize_search_text(42) is None


def test_normalize_search_text_empty_returns_none():
    assert _normalize_search_text("") is None


def test_normalize_search_text_whitespace_returns_none():
    assert _normalize_search_text("   \n") is None


def test_normalize_search_text_normalizes_and_casefolds():
    assert _normalize_search_text("Straße") == "strasse"


def test_searchable_fields_constant_is_six_fields():
    assert len(SEARCHABLE_FIELDS) == 6
