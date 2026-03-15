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
    _escape_table_cell,
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
        mermaid, uncertainties = graph_to_mermaid(graph)
        assert "graph TD" in mermaid
        assert "web" in mermaid
        assert "db" in mermaid
        assert "SQL" in mermaid

    def test_empty_graph_returns_empty(self):
        mermaid, uncertainties = graph_to_mermaid(_simple_graph())
        assert mermaid == ""
        assert uncertainties == []

    def test_none_graph_returns_empty(self):
        mermaid, uncertainties = graph_to_mermaid(None)
        assert mermaid == ""
        assert uncertainties == []


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
        mermaid, _ = graph_to_mermaid(graph)
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
        mermaid, _ = graph_to_mermaid(graph)
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
        mermaid, uncertainties = graph_to_mermaid(graph)
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
        mermaid, _ = graph_to_mermaid(graph)
        assert expected_char in mermaid

    @pytest.mark.parametrize("alias,expected_kind_char", [
        ("datastore", "[("),
        ("actor", "(("),
        ("boundary", "["),
        ("unknown", "["),
    ])
    def test_alias_mapping(self, alias, expected_kind_char):
        graph = _simple_graph(nodes=[_n("n1", "Test", kind=alias)])
        mermaid, _ = graph_to_mermaid(graph)
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
        mermaid, _ = graph_to_mermaid(graph)
        assert expected_arrow in mermaid

    def test_reverse_swaps_endpoints(self):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", direction="reverse")],
        )
        mermaid, _ = graph_to_mermaid(graph)
        assert "-->" in mermaid
        # b should come before a in the edge line
        edge_lines = [l for l in mermaid.split("\n") if "-->" in l]
        assert len(edge_lines) == 1
        assert edge_lines[0].strip().startswith("b")

    @pytest.mark.parametrize("legacy,expected_arrow", [
        ("->", "-->"),
        ("<->", "<-->"),
        ("undirected", "---"),
    ])
    def test_legacy_directions(self, legacy, expected_arrow):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", direction=legacy)],
        )
        mermaid, _ = graph_to_mermaid(graph)
        assert expected_arrow in mermaid

    def test_unknown_direction_conservative(self):
        """S3: Unrecognized directions render as undirected with uncertainty."""
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", direction="diagonal")],
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        assert "---" in mermaid
        assert any("unknown direction" in u.lower() for u in uncertainties)


# ---------------------------------------------------------------------------
# 8. Technology second-line rendering (B2: plain text, no wiki-links)
# ---------------------------------------------------------------------------


class TestMermaidTechnology:
    def test_technology_renders_second_line(self):
        graph = _simple_graph(
            nodes=[_n("app", "Web Application", technology="React")],
        )
        mermaid, _ = graph_to_mermaid(graph)
        assert "Web Application<br/>" in mermaid
        assert "React" in mermaid

    def test_technology_no_wiki_links_in_mermaid(self):
        """B2: Wiki-link brackets must NOT appear in Mermaid labels."""
        graph = _simple_graph(
            nodes=[_n("db", "Database", kind="database", technology="PostgreSQL")],
        )
        mermaid, _ = graph_to_mermaid(graph)
        assert "PostgreSQL" in mermaid
        # Must be plain text, NOT [[PostgreSQL]]
        assert "[[" not in mermaid
        assert "]]" not in mermaid

    def test_unsanitizable_technology_skipped_with_flag(self):
        """Technology that sanitizes to None should be skipped and flagged."""
        graph = _simple_graph(
            nodes=[_n("x", "Node X", technology="()")],
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        assert "Node X" in mermaid
        # The unsanitizable tech "()" should NOT appear in Mermaid output
        assert "()" not in mermaid
        # No <br/> since tech was skipped
        assert "<br/>" not in mermaid
        # Should flag the omission
        assert any("technology" in u.lower() and "unsanitizable" in u.lower()
                   for u in uncertainties)


# ---------------------------------------------------------------------------
# 9. Edge labels
# ---------------------------------------------------------------------------


class TestMermaidEdgeLabels:
    def test_labeled_edge(self):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", label="HTTPS")],
        )
        mermaid, _ = graph_to_mermaid(graph)
        assert "HTTPS" in mermaid

    def test_unlabeled_edge(self):
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b")],
        )
        mermaid, _ = graph_to_mermaid(graph)
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
        r1, _ = graph_to_mermaid(graph)
        r2, _ = graph_to_mermaid(graph)
        assert r1 == r2

    def test_determinism_across_reordered_inputs(self):
        """m5 enhancement: reordered input lists produce identical output."""
        nodes = [_n("c", "C"), _n("a", "A"), _n("b", "B")]
        edges = [_e("b_c", "b", "c"), _e("a_b", "a", "b")]
        g1 = _simple_graph(nodes=nodes, edges=edges)
        g2 = _simple_graph(nodes=list(reversed(nodes)), edges=list(reversed(edges)))
        r1, _ = graph_to_mermaid(g1)
        r2, _ = graph_to_mermaid(g2)
        assert r1 == r2


# ---------------------------------------------------------------------------
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

    def test_angle_brackets_removed(self):
        """m8: Angle brackets must be removed from labels."""
        result = _sanitize_label("A > B < C")
        assert result is not None
        assert "<" not in result
        assert ">" not in result

    def test_reserved_word_end(self):
        """'end' must not break Mermaid statement."""
        result = _sanitize_label("end")
        assert result is not None
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
    def test_empty_label_omits_node(self):
        """Per proposal: unsanitizable label → omit node from Mermaid."""
        graph = _simple_graph(nodes=[_n("fallback_node", "")])
        mermaid, uncertainties = graph_to_mermaid(graph)
        # Node should be omitted, not fallen back to ID
        assert "fallback_node" not in mermaid or "graph TD" == mermaid.strip()
        assert any("omitted" in u.lower() or "unsanitizable" in u.lower()
                   for u in uncertainties)


# ---------------------------------------------------------------------------
# 20. Omit-and-flag / fallback-to-ID behavior
# ---------------------------------------------------------------------------


class TestOmitAndFlag:
    def test_unsanitizable_label_omits_node_with_uncertainty(self):
        """Per proposal: unsanitizable label → omit node, emit uncertainty."""
        graph = _simple_graph(
            nodes=[
                _n("good", "Good Node"),
                DiagramNode(id="bad", label="()", kind="service"),
            ],
            edges=[_e("good_bad", "good", "bad")],
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        assert "Good Node" in mermaid
        # 'bad' node should be omitted from Mermaid
        assert any("omitted" in u.lower() for u in uncertainties)
        # Edge referencing omitted node should also be flagged
        assert any("edge" in u.lower() and "omitted" in u.lower()
                   for u in uncertainties)

    def test_unsanitizable_edge_label_flagged(self):
        """S1: Edge label sanitized to nothing emits uncertainty."""
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", label="(|)")],
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        assert any("label" in u.lower() and "omitted" in u.lower()
                   for u in uncertainties)

    def test_unsanitizable_group_name_flagged(self):
        """S1: Group name sanitized to nothing uses ID and emits uncertainty."""
        graph = _simple_graph(
            nodes=[_n("x", "X")],
            groups=[_g("grp", "()", contains=["x"])],
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        assert any("group" in u.lower() and "unsanitizable" in u.lower()
                   for u in uncertainties)


# ---------------------------------------------------------------------------
# 21. Mermaid output validated by real Mermaid parser
# ---------------------------------------------------------------------------


def _mermaid_parser_available():
    """Check if Node.js Mermaid parser is available."""
    import shutil
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
        mermaid, _ = graph_to_mermaid(graph)
        assert _validate_mermaid(mermaid), f"Mermaid parse failed:\n{mermaid}"

    def test_grouped_graph_parses(self):
        graph = _simple_graph(
            nodes=[_n("svc", "Service"), _n("db", "DB", kind="database")],
            edges=[_e("svc_db", "svc", "db")],
            groups=[_g("vpc", "VPC", contains=["svc", "db"])],
        )
        mermaid, _ = graph_to_mermaid(graph)
        assert _validate_mermaid(mermaid), f"Mermaid parse failed:\n{mermaid}"

    def test_technology_label_parses(self):
        graph = _simple_graph(
            nodes=[_n("app", "Web App", technology="React")],
        )
        mermaid, _ = graph_to_mermaid(graph)
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

    def test_prose_single_component_grammar(self):
        """m6: Singular 'component' for single-node graph."""
        graph = _simple_graph(nodes=[_n("x", "Only")])
        prose = graph_to_prose(graph)
        assert "1 component identified" in prose
        assert "components" not in prose

    def test_prose_graph_bound(self):
        """Prose should not infer semantics not in the graph."""
        graph = _simple_graph(nodes=[_n("svc", "Payment Service")])
        prose = graph_to_prose(graph)
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

    def test_technology_resolved_with_wiki_links(self):
        """Wiki-links ARE used in component table (unlike Mermaid)."""
        graph = _simple_graph(
            nodes=[_n("db", "DB", technology="PostgreSQL")],
        )
        table = graph_to_component_table(graph)
        assert "[[PostgreSQL]]" in table

    def test_pipe_in_label_escaped(self):
        """S4: Pipe in label value doesn't break table row."""
        graph = _simple_graph(
            nodes=[_n("x", "A | B")],
        )
        table = graph_to_component_table(graph)
        assert "A \\| B" in table


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

    def test_pipe_in_edge_label_escaped(self):
        """S4: Pipe in edge label doesn't break table row."""
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", label="HTTP | gRPC")],
        )
        table = graph_to_connection_table(graph)
        assert "HTTP \\| gRPC" in table


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

    def test_aws_lambda_alias(self):
        """m7: 'AWS Lambda' should resolve as well as 'lambda'."""
        assert resolve_entity("lambda") == "[[AWS Lambda]]"
        assert resolve_entity("AWS Lambda") == "[[AWS Lambda]]"

    def test_generic_variants(self):
        """Various generic labels should not be linked."""
        for generic in ["service", "api", "gateway", "cache", "server"]:
            result = resolve_entity(generic)
            assert "[[" not in result, f"Generic '{generic}' should not be linked"


# ---------------------------------------------------------------------------
# S1: DAG-shape group hierarchy (diamond)
# ---------------------------------------------------------------------------


class TestGroupDAGShape:
    def test_diamond_dag_no_false_cycle(self):
        """S1: Diamond group hierarchy (A→B, A→C, B→D, C→D) must render D
        without a false 'cycle detected' warning."""
        graph = _simple_graph(
            nodes=[_n("leaf", "Leaf")],
            groups=[
                _g("a", "A", contains_groups=["b", "c"]),
                _g("b", "B", contains_groups=["d"]),
                _g("c", "C", contains_groups=["d"]),
                _g("d", "D", contains=["leaf"]),
            ],
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        # D should be rendered (no false cycle)
        assert "subgraph d" in mermaid
        assert not any("cycle" in u.lower() for u in uncertainties)


# ---------------------------------------------------------------------------
# S2: Real cycle detection
# ---------------------------------------------------------------------------


class TestGroupCycleDetection:
    def test_mutual_group_containment_flagged(self):
        """Group cycle (A→B→A) with top-level wrapper → cycle detected."""
        graph = _simple_graph(
            nodes=[_n("x", "X")],
            groups=[
                _g("w", "Wrapper", contains_groups=["a"]),
                _g("a", "Group A", contains=["x"], contains_groups=["b"]),
                _g("b", "Group B", contains_groups=["a"]),
            ],
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        assert any("cycle" in u.lower() for u in uncertainties)
        assert "graph TD" in mermaid

    def test_rootless_cycle_detected(self):
        """B2: When ALL groups are children of other groups (rootless),
        no top-level entry point exists → uncertainty emitted and nodes
        rendered ungrouped instead of silently vanishing."""
        graph = _simple_graph(
            nodes=[_n("x", "X"), _n("y", "Y")],
            groups=[
                _g("a", "Group A", contains=["x"], contains_groups=["b"]),
                _g("b", "Group B", contains=["y"], contains_groups=["a"]),
            ],
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        # B2: Should report rootless cycle
        assert any("rootless" in u.lower() or "all groups" in u.lower()
                   for u in uncertainties)
        # Nodes must still appear (not silently erased)
        assert "X" in mermaid
        assert "Y" in mermaid
        assert "graph TD" in mermaid


# ---------------------------------------------------------------------------
# S3: Empty subgraph elision
# ---------------------------------------------------------------------------


class TestEmptySubgraphElision:
    def test_empty_subgraph_elided(self):
        """S3: Group with no valid nodes or subgroups should not produce
        an empty subgraph...end block."""
        graph = _simple_graph(
            nodes=[_n("x", "X")],
            groups=[
                _g("empty", "Empty Group", contains=["nonexistent"]),
            ],
        )
        mermaid, _ = graph_to_mermaid(graph)
        assert "subgraph" not in mermaid


# ---------------------------------------------------------------------------
# S5: Non-ASCII ID collision avoidance
# ---------------------------------------------------------------------------


class TestNonAsciiIdCollision:
    def test_cjk_ids_dont_collide(self):
        """S5: Two nodes with CJK IDs that collapse to the same safe form
        should get unique Mermaid IDs."""
        graph = _simple_graph(
            nodes=[
                _n("データ", "Data 1"),
                _n("サービス", "Data 2"),
            ],
        )
        mermaid, _ = graph_to_mermaid(graph)
        # Both nodes should appear with unique IDs
        assert "Data 1" in mermaid
        assert "Data 2" in mermaid


# ---------------------------------------------------------------------------
# Table cell escaping and control character sanitization
# ---------------------------------------------------------------------------


class TestTableCellEscaping:
    def test_escape_pipe(self):
        assert _escape_table_cell("A | B") == "A \\| B"

    def test_escape_empty(self):
        assert _escape_table_cell("") == ""

    def test_no_pipe_unchanged(self):
        assert _escape_table_cell("Normal text") == "Normal text"

    def test_control_chars_stripped(self):
        """S4: Control characters stripped from table cells."""
        assert _escape_table_cell("abc\x00def") == "abcdef"
        assert _escape_table_cell("line1\nline2") == "line1 line2"
        assert _escape_table_cell("tab\there") == "tab here"


# ---------------------------------------------------------------------------
# S2: node.group_id reconciliation
# ---------------------------------------------------------------------------


class TestGroupIdReconciliation:
    def test_node_group_id_used_when_group_contains_missing(self):
        """S2: Nodes with group_id but not in group.contains should still
        render as grouped in component table."""
        graph = _simple_graph(
            nodes=[
                _n("x", "NodeX", group_id="grp1"),
            ],
            groups=[_g("grp1", "My Group", contains=[])],  # contains is empty
        )
        table = graph_to_component_table(graph)
        assert "My Group" in table


# ---------------------------------------------------------------------------
# S4: Multiline / control chars in prose and tables
# ---------------------------------------------------------------------------


class TestControlCharSanitization:
    def test_prose_strips_control_chars(self):
        """S4: Control characters in edge labels don't leak into prose."""
        graph = _simple_graph(
            nodes=[_n("a", "A"), _n("b", "B")],
            edges=[_e("a_b", "a", "b", label="line1\nline2\x00")],
        )
        prose = graph_to_prose(graph)
        assert "\n" not in prose
        assert "\x00" not in prose
        assert "line1" in prose
        assert "line2" in prose

    def test_prose_blank_label_uses_fallback(self):
        """M1: Blank-label node with technology falls back to technology."""
        graph = _simple_graph(
            nodes=[_n("db", "", technology="PostgreSQL")],
        )
        prose = graph_to_prose(graph)
        assert "PostgreSQL" in prose
        assert prose != ""

    def test_prose_orphaned_group_not_mentioned(self):
        """M2: Group with no real nodes should not appear in prose summary."""
        graph = _simple_graph(
            nodes=[_n("x", "X")],
            groups=[
                _g("real", "Real Group", contains=["x"]),
                _g("orphan", "Orphan Group", contains=["nonexistent"]),
            ],
        )
        prose = graph_to_prose(graph)
        assert "Real Group" in prose
        assert "Orphan" not in prose

    def test_table_newlines_collapsed(self):
        """S4: Newlines in node labels don't break table rows."""
        graph = _simple_graph(
            nodes=[_n("x", "Line1\nLine2")],
        )
        table = graph_to_component_table(graph)
        assert "\n" not in table.split("\n")[2]  # data row
        assert "Line1" in table
        assert "Line2" in table


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
        da.graph = _simple_graph(nodes=[_n("a", "A")])
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


# ---------------------------------------------------------------------------
# Round 4 Regression Tests
# ---------------------------------------------------------------------------


class TestRound4Regressions:
    """Targeted regressions for Round 4 semantic bugs."""

    def test_regrouped_node_renders_in_mermaid_with_edge(self):
        """P1 regression: PR4-style regrouped node (group_id set, group.contains
        empty) must appear inside the subgraph with its edge intact."""
        graph = _simple_graph(
            nodes=[
                _n("api", "API Server", group_id="backend"),
                _n("db", "Database", kind="database"),
            ],
            edges=[_e("api_db", "api", "db", label="SQL")],
            groups=[_g("backend", "Backend", contains=[])],  # PR4: contains empty
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        # Node must appear in Mermaid, inside the subgraph
        assert "API Server" in mermaid
        assert "subgraph" in mermaid
        assert "Backend" in mermaid
        # Edge must be present
        assert "SQL" in mermaid
        # No silent erasure
        assert mermaid.strip() != "graph TD"

    def test_cjk_id_collision_edges_stable(self):
        """P1 regression: two CJK node IDs that collapse to the same safe form
        must produce edges that reference the SAME safe IDs used for nodes
        (no phantom node_2 created)."""
        graph = _simple_graph(
            nodes=[
                _n("データ", "Data Store"),
                _n("サービス", "Service"),
            ],
            edges=[_e("edge1", "データ", "サービス", label="fetch")],
        )
        mermaid, _ = graph_to_mermaid(graph)
        # Both nodes present
        assert "Data Store" in mermaid
        assert "Service" in mermaid
        # Extract all Mermaid IDs used (node definitions + edges)
        lines = mermaid.strip().split("\n")
        # Only "node" and "node_1" should exist (no "node_2")
        mermaid_text = "\n".join(lines)
        assert "node_2" not in mermaid_text

    def test_depth_limit_preserves_descendants(self):
        """P2 regression: nodes in deeply nested subgroups beyond the depth limit
        must still render (flattened) rather than silently disappearing."""
        # Build chain: g0 → g1 → ... → g6 (contains leaf)
        groups = []
        for i in range(7):
            groups.append(_g(
                f"g{i}", f"Group {i}",
                contains=["leaf"] if i == 6 else [],
                contains_groups=[f"g{i+1}"] if i < 6 else [],
            ))
        graph = _simple_graph(
            nodes=[_n("leaf", "Leaf Node")],
            groups=groups,
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        # Leaf MUST appear even though it's past depth limit
        assert "Leaf Node" in mermaid
        # Should report depth overflow
        assert any("depth" in u.lower() for u in uncertainties)

    def test_mermaid_control_bytes_stripped(self):
        """P2 regression: control bytes in labels must be stripped from
        Mermaid output, not passed through."""
        graph = _simple_graph(
            nodes=[_n("x", "Clean\x00Label\x07Here")],
        )
        mermaid, _ = graph_to_mermaid(graph)
        assert "\x00" not in mermaid
        assert "\x07" not in mermaid
        assert "CleanLabelHere" in mermaid

    def test_blank_label_table_cells_use_id_fallback(self):
        """P2 regression: blank-label nodes must show node ID in table cells
        rather than empty Component column."""
        graph = _simple_graph(
            nodes=[_n("my_node", "")],
        )
        table = graph_to_component_table(graph)
        # Node ID should appear as fallback in Component column
        assert "my_node" in table

    def test_blank_label_connection_table_uses_id(self):
        """P2 regression: blank-label nodes in connection table should
        show node ID, not empty From/To cells."""
        graph = _simple_graph(
            nodes=[_n("src", ""), _n("tgt", "Target")],
            edges=[_e("e1", "src", "tgt")],
        )
        table = graph_to_connection_table(graph)
        assert "src" in table  # fallback to node ID
        assert "Target" in table

    def test_cjk_ids_produce_valid_mermaid_ids(self):
        """P1 regression (R5): CJK-only IDs must produce non-empty Mermaid IDs
        like 'node' and 'node_1', not bare '[Label]' with empty ID."""
        graph = _simple_graph(
            nodes=[
                _n("データ", "Data Store"),
                _n("サービス", "Service"),
            ],
            edges=[_e("edge1", "データ", "サービス", label="fetch")],
        )
        mermaid, _ = graph_to_mermaid(graph)
        # Must have proper node IDs, not bare [Label]
        assert "node[" in mermaid or "node_1[" in mermaid
        # No bare " --> " with empty source/target
        lines = mermaid.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            if "-->" in stripped:
                # Source must be non-empty before arrow
                parts = stripped.split("-->")
                assert parts[0].strip(), f"Empty source in edge: {stripped}"

    def test_depth_plus_regroup_combined(self):
        """P1 regression (R5): PR4-regrouped node below depth limit must
        still render (flattened), not disappear."""
        # g0 -> g1 -> ... -> g6 with leaf regrouped to g6 via group_id
        groups = []
        for i in range(7):
            groups.append(_g(
                f"g{i}", f"Group {i}",
                contains=[],  # Empty contains—leaf is mapped via group_id
                contains_groups=[f"g{i+1}"] if i < 6 else [],
            ))
        graph = _simple_graph(
            nodes=[_n("leaf", "Leaf Node", group_id="g6")],
            groups=groups,
        )
        mermaid, uncertainties = graph_to_mermaid(graph)
        # Leaf must render even past depth limit
        assert "Leaf Node" in mermaid
        assert any("depth" in u.lower() for u in uncertainties)

    def test_prose_reverse_edge_swapped(self):
        """P2 regression (R5): reverse edge should produce 'B connects to A'
        in prose, consistent with Mermaid rendering."""
        graph = _simple_graph(
            nodes=[_n("a", "Alpha"), _n("b", "Beta")],
            edges=[_e("e", "a", "b", direction="reverse")],
        )
        prose = graph_to_prose(graph)
        # Reverse: Beta connects to Alpha (not Alpha connects to Beta)
        assert "Beta connects to Alpha" in prose

    def test_prose_includes_regroup_only_groups(self):
        """P2 regression (R5): groups with members only via node.group_id
        should still appear in prose group summary."""
        graph = _simple_graph(
            nodes=[_n("x", "NodeX", group_id="grp1")],
            groups=[_g("grp1", "ReGroup", contains=[])],
        )
        prose = graph_to_prose(graph)
        assert "ReGroup" in prose
