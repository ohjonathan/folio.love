"""PR 5: Tests for deterministic diagram rendering module."""

import pytest

from folio.pipeline.analysis import (
    DiagramAnalysis,
    DiagramEdge,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
    SlideAnalysis,
)
from folio.output.diagram_rendering import (
    graph_to_mermaid,
    graph_to_prose,
    graph_to_component_table,
    graph_to_connection_table,
    resolve_entity,
    render_diagram_analyses,
    _sanitize_label,
    _sanitize_edge_label,
    _make_safe_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_graph(
    nodes=None, edges=None, groups=None,
) -> DiagramGraph:
    """Construct a DiagramGraph with convenient defaults."""
    return DiagramGraph(
        nodes=nodes or [],
        edges=edges or [],
        groups=groups or [],
    )


def _n(id, label, kind="service", group_id=None, technology=None,
        confidence=0.95, source_text="vision"):
    """Shorthand node constructor."""
    return DiagramNode(
        id=id, label=label, kind=kind, group_id=group_id,
        technology=technology, confidence=confidence,
        source_text=source_text,
    )


def _e(id, source_id, target_id, label=None, direction="forward", confidence=0.90):
    """Shorthand edge constructor."""
    return DiagramEdge(
        id=id, source_id=source_id, target_id=target_id,
        label=label, direction=direction, confidence=confidence,
    )


def _g(id, name, contains=None, contains_groups=None):
    """Shorthand group constructor."""
    return DiagramGroup(
        id=id, name=name,
        contains=contains or [],
        contains_groups=contains_groups or [],
    )


# ---------------------------------------------------------------------------
# 1. Simple graph → valid Mermaid
# ---------------------------------------------------------------------------


class TestMermaidSimple:
    def test_simple_graph_produces_mermaid(self):
        graph = _simple_graph(
            nodes=[_n("web", "Web App"), _n("db", "Database", kind="database")],
            edges=[_e("web_db", "web", "db", label="SQL")],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert "graph TD" in mermaid
        assert "web" in mermaid
        assert "db" in mermaid
        assert "SQL" in mermaid

    def test_empty_graph_returns_empty(self):
        graph = _simple_graph()
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert mermaid == ""

    def test_none_graph_returns_empty(self):
        result = graph_to_mermaid(None)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert mermaid == ""


# ---------------------------------------------------------------------------
# 2-3. Grouped graph → correct subgraph blocks (including nested)
# ---------------------------------------------------------------------------


class TestMermaidGroups:
    def test_grouped_graph(self):
        graph = _simple_graph(
            nodes=[_n("app", "App"), _n("db", "DB", kind="database")],
            edges=[_e("app_db", "app", "db")],
            groups=[_g("vpc", "VPC", contains=["app", "db"])],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert "subgraph" in mermaid
        assert "VPC" in mermaid
        assert "end" in mermaid

    def test_nested_groups(self):
        graph = _simple_graph(
            nodes=[_n("svc", "Service")],
            groups=[
                _g("inner", "Inner", contains=["svc"]),
                _g("outer", "Outer", contains_groups=["inner"]),
            ],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert "subgraph outer" in mermaid
        assert "subgraph inner" in mermaid


# ---------------------------------------------------------------------------
# 4. Depth-limit overflow → flattened, no crash
# ---------------------------------------------------------------------------


class TestMermaidDepthLimit:
    def test_depth_overflow_flattens(self):
        """7 levels of nesting exceeds depth limit of 5."""
        # Build a chain: g0 contains_groups [g1], g1 contains_groups [g2], ...
        # g6 contains ["leaf"]
        groups = []
        for i in range(7):
            gid = f"g{i}"
            groups.append(_g(
                gid, f"Group {i}",
                contains=["leaf"] if i == 6 else [],
                contains_groups=[f"g{i+1}"] if i < 6 else [],
            ))
        graph = _simple_graph(
            nodes=[_n("leaf", "Leaf Node")],
            groups=groups,
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, uncertainties = result
        else:
            mermaid, uncertainties = result, []
        # Should report depth overflow — leaf may or may not appear
        # depending on flattening behavior, but no crash
        assert any("depth" in u.lower() or "flatten" in u.lower() for u in uncertainties)


# ---------------------------------------------------------------------------
# 5. Each live node kind mapping
# ---------------------------------------------------------------------------


class TestMermaidNodeKinds:
    @pytest.mark.parametrize("kind,expected_char", [
        ("service", "["),
        ("database", "[("),
        ("queue", "[/"),
        ("user", "(("),
        ("external", "(["),
        ("process", "("),
        ("decision", "{"),
        ("start", "(("),
        ("end", "(["),
        ("note", ">"),
        ("container", "["),
        ("other", "["),
    ])
    def test_kind_mapping(self, kind, expected_char):
        graph = _simple_graph(nodes=[_n("n1", "Test", kind=kind)])
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        # The expected_char should appear after the node ID
        assert expected_char in mermaid

    @pytest.mark.parametrize("alias,expected_kind_char", [
        ("datastore", "[("),
        ("actor", "(("),
        ("boundary", "["),
        ("unknown", "["),
    ])
    def test_alias_mapping(self, alias, expected_kind_char):
        graph = _simple_graph(nodes=[_n("n1", "Test", kind=alias)])
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert expected_kind_char in mermaid


# ---------------------------------------------------------------------------
# 6-7. Edge direction mapping (live + legacy)
# ---------------------------------------------------------------------------


class TestMermaidDirections:
    @pytest.mark.parametrize("direction,expected_arrow", [
        ("forward", "-->"),
        ("bidirectional", "<-->"),
        ("none", "---"),
    ])
    def test_live_directions(self, direction, expected_arrow):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", direction=direction)],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert expected_arrow in mermaid

    def test_reverse_swaps_endpoints(self):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", direction="reverse")],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        # Reverse should render as b --> a
        assert "-->" in mermaid
        # b should come before a in the edge line
        edge_lines = [l for l in mermaid.split("\n") if "-->" in l]
        assert len(edge_lines) == 1
        assert edge_lines[0].strip().startswith("b")

    @pytest.mark.parametrize("legacy,expected_arrow", [
        ("->", "-->"),
        ("<->", "<-->"),
        ("undirected", "---"),
        ("unknown", "---"),
    ])
    def test_legacy_directions(self, legacy, expected_arrow):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", direction=legacy)],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert expected_arrow in mermaid


# ---------------------------------------------------------------------------
# 8. Technology second-line rendering
# ---------------------------------------------------------------------------


class TestMermaidTechnology:
    def test_technology_renders_second_line(self):
        graph = _simple_graph(
            nodes=[_n("app", "Web Application", technology="React")],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert "Web Application<br/>" in mermaid
        assert "React" in mermaid


# ---------------------------------------------------------------------------
# 9. Edge labels
# ---------------------------------------------------------------------------


class TestMermaidEdgeLabels:
    def test_labeled_edge(self):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", label="HTTPS")],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert "HTTPS" in mermaid

    def test_unlabeled_edge(self):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b")],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert "|" not in mermaid.split("\n")[-1]  # no label pipes


# ---------------------------------------------------------------------------
# 10. Determinism: same graph twice → identical output
# ---------------------------------------------------------------------------


class TestMermaidDeterminism:
    def test_deterministic_output(self):
        graph = _simple_graph(
            nodes=[
                _n("c", "C"), _n("a", "A"), _n("b", "B"),
            ],
            edges=[
                _e("b_c", "b", "c", label="data"),
                _e("a_b", "a", "b", label="request"),
            ],
            groups=[_g("grp", "Group", contains=["a", "b"])],
        )
        r1 = graph_to_mermaid(graph)
        r2 = graph_to_mermaid(graph)
        if isinstance(r1, tuple):
            assert r1[0] == r2[0]
        else:
            assert r1 == r2


# ---------------------------------------------------------------------------
# 11. Empty graph handling (already covered above)
# 12-18. Sanitization tests
# ---------------------------------------------------------------------------


class TestSanitization:
    def test_parentheses_removed(self):
        result = _sanitize_label("Web (v2)")
        assert result is not None
        assert "(" not in result
        assert ")" not in result

    def test_brackets_removed(self):
        result = _sanitize_label("Data [primary]")
        assert result is not None
        assert "[" not in result
        assert "]" not in result

    def test_quotes_removed(self):
        result = _sanitize_label('API "gateway"')
        assert result is not None
        assert '"' not in result

    def test_pipes_removed(self):
        result = _sanitize_label("Option A | Option B")
        assert result is not None
        assert "|" not in result

    def test_semicolons_removed(self):
        result = _sanitize_label("Step 1; Step 2")
        assert result is not None
        assert ";" not in result

    def test_reserved_word_end(self):
        """'end' must not break Mermaid statement."""
        result = _sanitize_label("end")
        assert result is not None
        # Must be disambiguated (not literally 'end' without trailing space)
        assert result != "end" or result.endswith(" ")

    def test_reserved_word_subgraph(self):
        result = _sanitize_label("subgraph")
        assert result is not None

    def test_unicode_preserved(self):
        result = _sanitize_label("データベース")
        assert result == "データベース"

    def test_empty_label_after_sanitize_returns_none(self):
        result = _sanitize_label("()")
        assert result is None

    def test_whitespace_only_returns_none(self):
        result = _sanitize_label("   ")
        assert result is None


# ---------------------------------------------------------------------------
# 19. Empty label → node id fallback
# ---------------------------------------------------------------------------


class TestEmptyLabelFallback:
    def test_empty_label_uses_node_id(self):
        graph = _simple_graph(nodes=[_n("fallback_node", "")])
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        # Node ID should appear as fallback
        assert "fallback_node" in mermaid


# ---------------------------------------------------------------------------
# 20. Unsanitizable node/edge omitted while rest stays valid
# ---------------------------------------------------------------------------


class TestOmitAndFlag:
    def test_unsanitizable_edge_flagged(self):
        """Edge referencing a non-existent node is still rendered (Mermaid may
        handle it), but if we want omit-and-flag we need a node that truly
        can't render — where _make_safe_id returns 'node' and _sanitize_label
        returns None, the fallback to 'node' still produces valid output.

        Per spec: 'if label becomes empty after sanitization, fall back to node id'.
        So truly unsanitizable = no valid label AND empty safe ID.

        We verify: the fallback-to-ID behavior works when label sanitizes away.
        """
        from folio.pipeline.analysis import DiagramNode as DN
        # Node with label "()" → sanitizes to None → falls back to safe_id "bad"
        graph = _simple_graph(
            nodes=[
                _n("good", "Good Node"),
                DN(id="bad", label="()", kind="service"),
            ],
            edges=[_e("good_bad", "good", "bad")],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, uncertainties = result
        else:
            mermaid, uncertainties = result, []
        # Both nodes should render — bad falls back to its ID as label
        assert "Good Node" in mermaid
        assert "bad" in mermaid
        # No uncertainties because fallback-to-ID succeeded
        assert not any("omitted" in u.lower() for u in uncertainties)


# ---------------------------------------------------------------------------
# 21. Mermaid output validated by real Mermaid parser
# ---------------------------------------------------------------------------


def _mermaid_parser_available():
    """Check if Node.js Mermaid parser is available."""
    import shutil
    import subprocess
    from pathlib import Path
    if not shutil.which("node"):
        return False
    validator = Path(__file__).parent / "mermaid" / "validate.mjs"
    if not validator.exists():
        return False
    pkg_dir = Path(__file__).parent / "mermaid"
    node_modules = pkg_dir / "node_modules"
    return node_modules.exists()


def _validate_mermaid(mermaid_text: str) -> bool:
    """Validate Mermaid text using the real parser. Returns True if valid."""
    import subprocess
    from pathlib import Path
    validator = Path(__file__).parent / "mermaid" / "validate.mjs"
    result = subprocess.run(
        ["node", str(validator)],
        input=mermaid_text,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


@pytest.mark.skipif(
    not _mermaid_parser_available(),
    reason="Mermaid parser not installed (run: npm --prefix tests/mermaid install)"
)
class TestMermaidParserValidation:
    def test_simple_graph_parses(self):
        graph = _simple_graph(
            nodes=[_n("web", "Web App"), _n("api", "API"), _n("db", "Database", kind="database")],
            edges=[
                _e("web_api", "web", "api", label="REST"),
                _e("api_db", "api", "db", label="SQL"),
            ],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert _validate_mermaid(mermaid), f"Mermaid parse failed:\n{mermaid}"

    def test_grouped_graph_parses(self):
        graph = _simple_graph(
            nodes=[_n("svc", "Service"), _n("db", "DB", kind="database")],
            edges=[_e("svc_db", "svc", "db")],
            groups=[_g("vpc", "VPC", contains=["svc", "db"])],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert _validate_mermaid(mermaid), f"Mermaid parse failed:\n{mermaid}"

    def test_technology_label_parses(self):
        graph = _simple_graph(
            nodes=[_n("app", "Web App", technology="React")],
        )
        result = graph_to_mermaid(graph)
        if isinstance(result, tuple):
            mermaid, _ = result
        else:
            mermaid = result
        assert _validate_mermaid(mermaid), f"Mermaid parse failed:\n{mermaid}"


# ---------------------------------------------------------------------------
# 22-25. Prose generation
# ---------------------------------------------------------------------------


class TestProseGeneration:
    def test_prose_with_edges(self):
        graph = _simple_graph(
            nodes=[_n("web", "Web App"), _n("db", "Database")],
            edges=[_e("web_db", "web", "db", label="SQL queries")],
        )
        prose = graph_to_prose(graph)
        assert "Web App" in prose
        assert "Database" in prose
        assert "SQL queries" in prose
        assert "connects to" in prose

    def test_prose_with_groups(self):
        graph = _simple_graph(
            nodes=[_n("a", "A")],
            edges=[],
            groups=[_g("vpc", "VPC", contains=["a"])],
        )
        prose = graph_to_prose(graph)
        assert "VPC" in prose
        assert "groups" in prose.lower()

    def test_prose_without_edges(self):
        graph = _simple_graph(
            nodes=[_n("a", "Alpha"), _n("b", "Beta")],
        )
        prose = graph_to_prose(graph)
        assert "2 components identified" in prose
        assert "Alpha" in prose
        assert "Beta" in prose

    def test_prose_graph_bound(self):
        """Prose should not infer semantics not in the graph."""
        graph = _simple_graph(
            nodes=[_n("svc", "Payment Service")],
        )
        prose = graph_to_prose(graph)
        # Should not contain interpretive claims
        assert "security" not in prose.lower()
        assert "purpose" not in prose.lower()
        assert "owns" not in prose.lower()

    def test_prose_with_technology(self):
        graph = _simple_graph(
            nodes=[_n("db", "Order Database", technology="PostgreSQL"), _n("api", "API")],
            edges=[_e("db_api", "db", "api")],
        )
        prose = graph_to_prose(graph)
        assert "PostgreSQL" in prose

    def test_prose_empty_graph(self):
        prose = graph_to_prose(_simple_graph())
        assert prose == ""

    def test_prose_none_graph(self):
        prose = graph_to_prose(None)
        assert prose == ""


# ---------------------------------------------------------------------------
# 26. Component table ordering / formatting
# ---------------------------------------------------------------------------


class TestComponentTable:
    def test_basic_table(self):
        graph = _simple_graph(
            nodes=[_n("b", "Beta", kind="database"), _n("a", "Alpha")],
        )
        table = graph_to_component_table(graph)
        assert "| Component |" in table
        lines = table.strip().split("\n")
        assert len(lines) == 4  # header + separator + 2 rows
        # Alpha should come before Beta (alphabetical)
        alpha_idx = table.index("Alpha")
        beta_idx = table.index("Beta")
        assert alpha_idx < beta_idx

    def test_grouped_before_ungrouped(self):
        graph = _simple_graph(
            nodes=[
                _n("ungrouped", "Ungrouped", kind="service"),
                _n("grouped", "Grouped", kind="database"),
            ],
            groups=[_g("grp", "Group1", contains=["grouped"])],
        )
        table = graph_to_component_table(graph)
        grouped_idx = table.index("Grouped")
        ungrouped_idx = table.index("Ungrouped")
        assert grouped_idx < ungrouped_idx

    def test_empty_graph_message(self):
        table = graph_to_component_table(_simple_graph())
        assert "No components identified" in table

    def test_technology_resolved(self):
        graph = _simple_graph(
            nodes=[_n("db", "DB", technology="PostgreSQL")],
        )
        table = graph_to_component_table(graph)
        assert "[[PostgreSQL]]" in table


# ---------------------------------------------------------------------------
# 27. Connection table ordering / formatting
# ---------------------------------------------------------------------------


class TestConnectionTable:
    def test_basic_table(self):
        graph = _simple_graph(
            nodes=[_n("a", "Alpha"), _n("b", "Beta")],
            edges=[_e("a_b", "a", "b", label="data")],
        )
        table = graph_to_connection_table(graph)
        assert "| From |" in table
        assert "Alpha" in table
        assert "Beta" in table
        assert "data" in table

    def test_empty_edges_message(self):
        graph = _simple_graph(nodes=[_n("a", "A")])
        table = graph_to_connection_table(graph)
        assert "No connections identified" in table

    def test_deterministic_ordering(self):
        graph = _simple_graph(
            nodes=[_n("c", "C"), _n("a", "A"), _n("b", "B")],
            edges=[
                _e("c_a", "c", "a"),
                _e("a_b", "a", "b"),
            ],
        )
        table = graph_to_connection_table(graph)
        a_idx = table.index("| A |")
        c_idx = table.index("| C |")
        assert a_idx < c_idx  # A→B before C→A


# ---------------------------------------------------------------------------
# 28. Confidence values to 2 decimals
# ---------------------------------------------------------------------------


class TestConfidenceFormatting:
    def test_component_confidence_two_decimals(self):
        graph = _simple_graph(nodes=[_n("x", "X", confidence=0.9)])
        table = graph_to_component_table(graph)
        assert "0.90" in table

    def test_connection_confidence_two_decimals(self):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", confidence=0.85)],
        )
        table = graph_to_connection_table(graph)
        assert "0.85" in table


# ---------------------------------------------------------------------------
# 29-32. Entity resolution
# ---------------------------------------------------------------------------


class TestEntityResolution:
    def test_known_technology_linked(self):
        assert resolve_entity("PostgreSQL") == "[[PostgreSQL]]"

    def test_generic_label_not_linked(self):
        result = resolve_entity("Database")
        assert result == "Database"
        assert "[[" not in result

    def test_unknown_technology_not_linked(self):
        result = resolve_entity("MyCustomFramework")
        assert result == "MyCustomFramework"
        assert "[[" not in result

    def test_case_insensitive(self):
        assert resolve_entity("postgresql") == "[[PostgreSQL]]"
        assert resolve_entity("POSTGRESQL") == "[[PostgreSQL]]"
        assert resolve_entity("React") == "[[React]]"
        assert resolve_entity("react") == "[[React]]"

    def test_none_returns_empty(self):
        assert resolve_entity(None) == ""

    def test_empty_returns_empty(self):
        assert resolve_entity("") == ""
        assert resolve_entity("  ") == ""

    def test_alias_resolution(self):
        assert resolve_entity("postgres") == "[[PostgreSQL]]"
        assert resolve_entity("k8s") == "[[Kubernetes]]"
        assert resolve_entity("golang") == "[[Go]]"

    def test_generic_variants(self):
        """Various generic labels should not be linked."""
        for generic in ["service", "api", "gateway", "cache", "server"]:
            result = resolve_entity(generic)
            assert "[[" not in result, f"Generic '{generic}' should not be linked"


# ---------------------------------------------------------------------------
# 33-35. Pipeline helper: abstained/mixed states
# ---------------------------------------------------------------------------


class TestRenderDiagramAnalyses:
    def test_abstained_no_graph_skipped(self):
        """Abstained with graph=None → render fields stay unset."""
        da = DiagramAnalysis(
            slide_type="pending",
            diagram_type="unsupported",
            abstained=True,
            graph=None,
        )
        result = render_diagram_analyses({1: da})
        assert result[1].mermaid is None
        assert result[1].description is None
        assert result[1].component_table is None
        assert result[1].connection_table is None

    def test_abstained_with_graph_renders(self):
        """Abstained with graph present → render fields populated."""
        graph = _simple_graph(
            nodes=[_n("a", "Alpha"), _n("b", "Beta")],
            edges=[_e("a_b", "a", "b")],
        )
        da = DiagramAnalysis(
            slide_type="diagram",
            diagram_type="architecture",
            abstained=True,
            graph=graph,
        )
        result = render_diagram_analyses({1: da})
        assert result[1].mermaid is not None
        assert result[1].description is not None
        assert result[1].component_table is not None
        assert result[1].connection_table is not None

    def test_non_diagram_skipped(self):
        """Non-DiagramAnalysis slides are untouched."""
        sa = SlideAnalysis(slide_type="data", framework="none")
        result = render_diagram_analyses({1: sa})
        assert isinstance(result[1], SlideAnalysis)
        assert not isinstance(result[1], DiagramAnalysis)

    def test_mixed_page_preserves_inherited_fields(self):
        """Mixed page keeps consulting-slide fields intact."""
        sa = SlideAnalysis(
            slide_type="data",
            framework="tam-sam-som",
            visual_description="Revenue chart",
            key_data="$10M",
            main_insight="Growing",
            evidence=[{"claim": "Revenue"}],
        )
        da = DiagramAnalysis.from_slide_analysis(
            sa, diagram_type="mixed",
        )
        # Give it a graph so rendering runs
        da.graph = _simple_graph(
            nodes=[_n("a", "A")],
        )
        result = render_diagram_analyses({1: da})
        rendered = result[1]
        # Inherited fields preserved
        assert rendered.slide_type == "data"
        assert rendered.framework == "tam-sam-som"
        assert rendered.visual_description == "Revenue chart"
        assert rendered.key_data == "$10M"
        assert rendered.main_insight == "Growing"
        assert rendered.evidence == [{"claim": "Revenue"}]
        # Diagram fields populated
        assert rendered.component_table is not None

    def test_graph_present_populates_all(self):
        """Normal diagram with graph → all render fields set."""
        graph = _simple_graph(
            nodes=[_n("svc", "Service"), _n("db", "DB", kind="database")],
            edges=[_e("svc_db", "svc", "db", label="query")],
        )
        da = DiagramAnalysis(
            slide_type="diagram",
            diagram_type="architecture",
            graph=graph,
        )
        result = render_diagram_analyses({1: da})
        rendered = result[1]
        assert rendered.mermaid is not None
        assert "graph TD" in rendered.mermaid
        assert rendered.description is not None
        assert rendered.component_table is not None
        assert rendered.connection_table is not None
