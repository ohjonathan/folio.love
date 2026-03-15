"""PR 5: Deterministic diagram rendering — Mermaid, prose, tables, entity resolution.

Pure-deterministic module. No I/O, no vault scanning, no model calls.
All outputs are derived solely from DiagramGraph data.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..pipeline.analysis import (
        DiagramAnalysis,
        DiagramGraph,
        DiagramGroup,
        DiagramNode,
        DiagramEdge,
        SlideAnalysis,
    )

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Entity resolution: curated technology allowlist
# ---------------------------------------------------------------------------

# Case-insensitive lookup → canonical wiki-link output.
# Generic labels (Database, Service, Gateway, etc.) must NOT be linked.
_TECHNOLOGY_WIKI_MAP: dict[str, str] = {
    # Languages
    "python": "[[Python]]",
    "java": "[[Java]]",
    "javascript": "[[JavaScript]]",
    "typescript": "[[TypeScript]]",
    "go": "[[Go]]",
    "golang": "[[Go]]",
    "rust": "[[Rust]]",
    "c#": "[[C#]]",
    "c++": "[[C++]]",
    "ruby": "[[Ruby]]",
    "php": "[[PHP]]",
    "swift": "[[Swift]]",
    "kotlin": "[[Kotlin]]",
    "scala": "[[Scala]]",
    # Databases
    "postgresql": "[[PostgreSQL]]",
    "postgres": "[[PostgreSQL]]",
    "mysql": "[[MySQL]]",
    "mongodb": "[[MongoDB]]",
    "redis": "[[Redis]]",
    "elasticsearch": "[[Elasticsearch]]",
    "dynamodb": "[[DynamoDB]]",
    "cassandra": "[[Cassandra]]",
    "sqlite": "[[SQLite]]",
    "oracle": "[[Oracle Database]]",
    "sql server": "[[SQL Server]]",
    "mariadb": "[[MariaDB]]",
    "neo4j": "[[Neo4j]]",
    "couchdb": "[[CouchDB]]",
    # Cloud platforms
    "aws": "[[AWS]]",
    "azure": "[[Azure]]",
    "gcp": "[[Google Cloud Platform]]",
    "google cloud": "[[Google Cloud Platform]]",
    # Cloud services
    "s3": "[[Amazon S3]]",
    "lambda": "[[AWS Lambda]]",
    "ec2": "[[Amazon EC2]]",
    "rds": "[[Amazon RDS]]",
    "sqs": "[[Amazon SQS]]",
    "sns": "[[Amazon SNS]]",
    "cloudfront": "[[Amazon CloudFront]]",
    "ecs": "[[Amazon ECS]]",
    "eks": "[[Amazon EKS]]",
    "fargate": "[[AWS Fargate]]",
    # Messaging & streaming
    "kafka": "[[Apache Kafka]]",
    "rabbitmq": "[[RabbitMQ]]",
    "nats": "[[NATS]]",
    "pulsar": "[[Apache Pulsar]]",
    # Frameworks & runtimes
    "react": "[[React]]",
    "angular": "[[Angular]]",
    "vue": "[[Vue.js]]",
    "vue.js": "[[Vue.js]]",
    "next.js": "[[Next.js]]",
    "nextjs": "[[Next.js]]",
    "django": "[[Django]]",
    "flask": "[[Flask]]",
    "fastapi": "[[FastAPI]]",
    "spring": "[[Spring Framework]]",
    "spring boot": "[[Spring Boot]]",
    "express": "[[Express.js]]",
    "express.js": "[[Express.js]]",
    "node.js": "[[Node.js]]",
    "nodejs": "[[Node.js]]",
    ".net": "[[.NET]]",
    "rails": "[[Ruby on Rails]]",
    "ruby on rails": "[[Ruby on Rails]]",
    # Infrastructure & DevOps
    "docker": "[[Docker]]",
    "kubernetes": "[[Kubernetes]]",
    "k8s": "[[Kubernetes]]",
    "terraform": "[[Terraform]]",
    "ansible": "[[Ansible]]",
    "jenkins": "[[Jenkins]]",
    "nginx": "[[Nginx]]",
    "apache": "[[Apache HTTP Server]]",
    "kong": "[[Kong]]",
    "envoy": "[[Envoy]]",
    "istio": "[[Istio]]",
    "consul": "[[Consul]]",
    "vault": "[[HashiCorp Vault]]",
    "prometheus": "[[Prometheus]]",
    "grafana": "[[Grafana]]",
    "datadog": "[[Datadog]]",
    # Protocols
    "graphql": "[[GraphQL]]",
    "grpc": "[[gRPC]]",
    "rest": "[[REST]]",
    "websocket": "[[WebSocket]]",
    "mqtt": "[[MQTT]]",
    "amqp": "[[AMQP]]",
    # Data & ML
    "spark": "[[Apache Spark]]",
    "hadoop": "[[Apache Hadoop]]",
    "airflow": "[[Apache Airflow]]",
    "tensorflow": "[[TensorFlow]]",
    "pytorch": "[[PyTorch]]",
    "snowflake": "[[Snowflake]]",
    "bigquery": "[[BigQuery]]",
    "databricks": "[[Databricks]]",
    "aws lambda": "[[AWS Lambda]]",
}

# Generic labels that must NOT receive wiki-links.
_GENERIC_LABELS = frozenset({
    "database", "db", "service", "server", "gateway", "api", "api gateway",
    "web", "web server", "app", "application", "frontend", "backend",
    "cache", "queue", "load balancer", "proxy", "storage", "cdn",
    "microservice", "container", "cluster", "broker", "monitor",
    "logging", "auth", "authentication", "authorization",
})


def resolve_entity(technology: str | None) -> str:
    """Resolve a technology label to a wiki-link or plain text.

    Rules:
    - None/empty → empty string
    - Generic labels → plain text (never linked)
    - Known technology → canonical wiki-link
    - Unknown technology → plain text (conservative fallback)
    """
    if not technology or not technology.strip():
        return ""
    tech = technology.strip()
    key = tech.lower()
    if key in _GENERIC_LABELS:
        return tech
    return _TECHNOLOGY_WIKI_MAP.get(key, tech)


# ---------------------------------------------------------------------------
# Mermaid node shape mapping
# ---------------------------------------------------------------------------

# Live runtime kinds → Mermaid shape format strings.
# The format string receives the sanitized label via .format(label=...).
_NODE_SHAPE_MAP: dict[str, str] = {
    # Live PR 4 kinds
    "service": "[{label}]",
    "database": "[({label})]",
    "queue": "[/{label}/]",
    "user": "(({label}))",
    "external": "([{label}])",
    "process": "({label})",
    "decision": "{{{label}}}",
    "start": "(({label}))",
    "end": "([{label}])",
    "note": ">{label}]",
    "container": "[{label}]",
    "other": "[{label}]",
    # Proposal-era aliases
    "datastore": "[({label})]",
    "actor": "(({label}))",
    "boundary": "[{label}]",
    "unknown": "[{label}]",
}


# ---------------------------------------------------------------------------
# Mermaid edge direction mapping
# ---------------------------------------------------------------------------

_EDGE_DIRECTION_MAP: dict[str, str] = {
    # Live PR 4 directions
    "forward": "-->",
    "reverse": "-->",        # endpoints are swapped at render time
    "bidirectional": "<-->",
    "none": "---",
    # Legacy / fallback values
    "->": "-->",
    "<->": "<-->",
    "undirected": "---",
    "unknown": "---",
}

# Human-readable direction symbols for connection table.
_DIRECTION_DISPLAY: dict[str, str] = {
    "forward": "→",
    "reverse": "←",
    "bidirectional": "↔",
    "none": "—",
    "->": "→",
    "<->": "↔",
    "undirected": "—",
    "unknown": "—",
}


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------

# Mermaid reserved words that can break statements when used as node labels.
_RESERVED_WORDS = frozenset({"end", "subgraph", "graph", "direction"})

# Characters that need escaping/removal in Mermaid labels.
_UNSAFE_LABEL_RE = re.compile(r'[()\[\]{}<>"\|;`]')


def _sanitize_label(label: str) -> str | None:
    """Sanitize a label for safe Mermaid rendering.

    Returns the sanitized label, or None if the label cannot be rendered
    safely (should be omit-and-flagged by the caller).
    """
    if not label or not label.strip():
        return None

    sanitized = label.strip()
    # Remove unsafe characters (includes pipes, brackets, angle brackets)
    sanitized = _UNSAFE_LABEL_RE.sub("", sanitized)
    # Collapse whitespace
    sanitized = " ".join(sanitized.split())

    if not sanitized:
        return None

    # Escape reserved words by quoting
    if sanitized.lower() in _RESERVED_WORDS:
        sanitized = f"{sanitized} "  # trailing space disambiguates

    return sanitized


def _sanitize_edge_label(label: str | None) -> str:
    """Sanitize an edge label for Mermaid. Returns empty string if unusable."""
    if not label or not label.strip():
        return ""
    sanitized = label.strip()
    sanitized = _UNSAFE_LABEL_RE.sub("", sanitized)
    sanitized = " ".join(sanitized.split())
    return sanitized


# Track assigned safe IDs to detect collisions (reset per graph_to_mermaid call).
_safe_id_registry: dict[str, str] = {}


def _make_safe_id(node_id: str) -> str:
    """Ensure a node ID is safe for Mermaid (alphanumeric + underscore).

    Detects collisions from non-ASCII IDs that collapse to the same safe form
    and appends a counter suffix to disambiguate.
    """
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", node_id)
    safe = re.sub(r"_+", "_", safe).strip("_")
    base = safe or "node"

    # Check for collision (different original ID → same safe ID)
    if base in _safe_id_registry:
        if _safe_id_registry[base] != node_id:
            # Collision — find unique suffix
            counter = 1
            while f"{base}_{counter}" in _safe_id_registry:
                counter += 1
            safe = f"{base}_{counter}"
            _safe_id_registry[safe] = node_id
            return safe
    else:
        _safe_id_registry[base] = node_id
    return base


# ---------------------------------------------------------------------------
# Mermaid generator
# ---------------------------------------------------------------------------

_MAX_SUBGRAPH_DEPTH = 5


def graph_to_mermaid(graph: "DiagramGraph") -> tuple[str, list[str]]:
    """Generate deterministic Mermaid flowchart from a DiagramGraph.

    Returns:
        (mermaid_text, uncertainties) — mermaid_text is the Mermaid code,
        uncertainties is a list of rendering warnings (omitted nodes, etc.).
        Empty/None graph returns ("", []).
    """
    if graph is None or (not graph.nodes and not graph.edges):
        return "", []

    # Reset the safe-ID collision registry for this render
    _safe_id_registry.clear()

    lines: list[str] = ["graph TD"]
    uncertainties: list[str] = []
    omitted_node_ids: set[str] = set()

    # Build lookup maps
    node_map = {n.id: n for n in graph.nodes}
    group_map = {g.id: g for g in graph.groups}

    # Determine which nodes belong to which group
    node_to_group: dict[str, str] = {}
    for group in graph.groups:
        for nid in group.contains:
            node_to_group[nid] = group.id

    # Identify top-level groups (not contained by another group)
    child_groups: set[str] = set()
    for group in graph.groups:
        for gid in group.contains_groups:
            child_groups.add(gid)
    top_level_groups = [
        g for g in sorted(graph.groups, key=lambda g: (g.name, g.id))
        if g.id not in child_groups
    ]

    # Render groups recursively.
    # S1 fix: use path-tracking set for cycle detection (pop after recursion)
    # and separate rendered set to avoid re-rendering in DAG shapes.
    recursion_path: set[str] = set()
    rendered_groups: set[str] = set()

    def _render_group(group: "DiagramGroup", depth: int, indent: str) -> None:
        if group.id in recursion_path:
            uncertainties.append(
                f"Cycle detected in group '{group.name}' (id={group.id}); flattened"
            )
            return
        if group.id in rendered_groups:
            return  # DAG convergence — already rendered, skip silently
        if depth > _MAX_SUBGRAPH_DEPTH:
            uncertainties.append(
                f"Max subgraph depth ({_MAX_SUBGRAPH_DEPTH}) exceeded for "
                f"group '{group.name}' (id={group.id}); flattened"
            )
            # Flatten: render contained nodes at current level
            _render_group_nodes(group, indent)
            rendered_groups.add(group.id)
            return

        recursion_path.add(group.id)
        rendered_groups.add(group.id)
        safe_gid = _make_safe_id(group.id)
        sanitized_name = _sanitize_label(group.name) or safe_gid

        # S3: Check if group has any renderable content before emitting subgraph
        has_nodes = any(nid in node_map for nid in group.contains)
        has_subgroups = any(gid in group_map for gid in group.contains_groups)
        if not has_nodes and not has_subgroups:
            recursion_path.discard(group.id)
            return  # Elide empty subgraph

        lines.append(f"{indent}subgraph {safe_gid} [{sanitized_name}]")

        # Render contained nodes
        _render_group_nodes(group, indent + "    ")

        # Render nested subgroups
        nested = sorted(
            [group_map[gid] for gid in group.contains_groups if gid in group_map],
            key=lambda g: (g.name, g.id),
        )
        for nested_group in nested:
            _render_group(nested_group, depth + 1, indent + "    ")

        lines.append(f"{indent}end")
        recursion_path.discard(group.id)

    def _render_group_nodes(group: "DiagramGroup", indent: str) -> None:
        nodes_in_group = sorted(
            [node_map[nid] for nid in group.contains if nid in node_map],
            key=lambda n: (n.label, n.id),
        )
        for node in nodes_in_group:
            node_line = _render_node(node)
            if node_line is not None:
                lines.append(f"{indent}{node_line}")
            else:
                omitted_node_ids.add(node.id)
                uncertainties.append(
                    f"Node '{node.id}' omitted from Mermaid: label unsanitizable"
                )

    def _render_node(node: "DiagramNode") -> str | None:
        safe_id = _make_safe_id(node.id)
        label = _sanitize_label(node.label)
        if label is None:
            label = safe_id  # fallback to node id
            if not label:
                return None

        # B2: Use plain text technology in Mermaid (not wiki-linked).
        # Wiki-links are reserved for component_table and prose.
        if node.technology:
            tech_plain = node.technology.strip()
            if tech_plain:
                # Sanitize the tech label too for Mermaid safety
                tech_safe = _sanitize_label(tech_plain) or tech_plain
                label = f"{label}<br/>{tech_safe}"

        kind = (node.kind or "other").lower()
        shape_fmt = _NODE_SHAPE_MAP.get(kind, _NODE_SHAPE_MAP["other"])
        shape = shape_fmt.format(label=label)
        return f"{safe_id}{shape}"

    # Render top-level groups
    for group in top_level_groups:
        _render_group(group, 1, "    ")

    # Render ungrouped nodes (sorted, after groups)
    grouped_node_ids = set(node_to_group.keys())
    ungrouped_nodes = sorted(
        [n for n in graph.nodes if n.id not in grouped_node_ids],
        key=lambda n: (n.label, n.id),
    )
    for node in ungrouped_nodes:
        node_line = _render_node(node)
        if node_line is not None:
            lines.append(f"    {node_line}")
        else:
            omitted_node_ids.add(node.id)
            uncertainties.append(
                f"Node '{node.id}' omitted from Mermaid: label unsanitizable"
            )

    # Render edges (deterministic order: source label, target label, edge id)
    sorted_edges = sorted(
        graph.edges,
        key=lambda e: (
            node_map.get(e.source_id, _placeholder_node()).label,
            node_map.get(e.target_id, _placeholder_node()).label,
            e.id,
        ),
    )
    for edge in sorted_edges:
        # Skip edges involving omitted nodes
        if edge.source_id in omitted_node_ids or edge.target_id in omitted_node_ids:
            uncertainties.append(
                f"Edge '{edge.id}' omitted from Mermaid: references omitted node"
            )
            continue

        direction = (edge.direction or "forward").lower()
        arrow = _EDGE_DIRECTION_MAP.get(direction, "-->")

        source = edge.source_id
        target = edge.target_id

        # Reverse: swap endpoints, use forward arrow
        if direction == "reverse":
            source, target = target, source

        safe_source = _make_safe_id(source)
        safe_target = _make_safe_id(target)

        edge_label = _sanitize_edge_label(edge.label)
        if edge_label:
            lines.append(f"    {safe_source} {arrow}|{edge_label}| {safe_target}")
        else:
            lines.append(f"    {safe_source} {arrow} {safe_target}")

    return "\n".join(lines), uncertainties


class _PlaceholderNode:
    """Minimal stand-in when a node ID isn't found in the map."""
    label = ""
    id = ""


def _placeholder_node() -> _PlaceholderNode:
    return _PlaceholderNode()


# ---------------------------------------------------------------------------
# Prose generator
# ---------------------------------------------------------------------------


def graph_to_prose(graph: "DiagramGraph") -> str:
    """Generate graph-bound prose description.

    Strictly describes what is in nodes, edges, and groups.
    No semantic inference, no architecture interpretation.
    """
    if graph is None or not graph.nodes:
        return ""

    from ..pipeline.analysis import DiagramNode  # local import to avoid circular

    node_map = {n.id: n for n in graph.nodes}
    sentences: list[str] = []

    if graph.edges:
        # One sentence per edge, deterministic order
        sorted_edges = sorted(
            graph.edges,
            key=lambda e: (
                node_map.get(e.source_id, _placeholder_node()).label,
                node_map.get(e.target_id, _placeholder_node()).label,
                e.id,
            ),
        )
        for edge in sorted_edges:
            src = node_map.get(edge.source_id)
            tgt = node_map.get(edge.target_id)
            if not src or not tgt:
                continue

            src_label = _node_prose_label(src)
            tgt_label = _node_prose_label(tgt)

            if edge.label:
                sentences.append(
                    f"{src_label} connects to {tgt_label} via {edge.label}."
                )
            else:
                sentences.append(f"{src_label} connects to {tgt_label}.")
    else:
        # No edges: list components
        labels = sorted(n.label for n in graph.nodes)
        count = len(graph.nodes)
        noun = "component" if count == 1 else "components"
        sentences.append(
            f"{count} {noun} identified: {', '.join(labels)}."
        )

    # Group summary
    if graph.groups:
        group_names = sorted(g.name for g in graph.groups)
        sentences.append(
            f"Components are organized into {', '.join(group_names)} groups."
        )

    return " ".join(sentences)


def _node_prose_label(node: "DiagramNode") -> str:
    """Format a node label for prose, including technology if present."""
    if node.technology:
        return f"{node.label} ({node.technology})"
    return node.label


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------


def _escape_table_cell(value: str) -> str:
    """Escape pipe characters in Markdown table cell values (S4)."""
    if not value:
        return ""
    return value.replace("|", "\\|")


# ---------------------------------------------------------------------------
# Component table
# ---------------------------------------------------------------------------


def graph_to_component_table(graph: "DiagramGraph") -> str:
    """Generate deterministic Markdown component table.

    Ordering: grouped nodes first (by group name), alphabetical by label
    within each group; ungrouped nodes last, alphabetical by label.
    """
    if graph is None or not graph.nodes:
        return "No components identified."

    # Build group lookup
    node_to_group_name: dict[str, str] = {}
    for group in graph.groups:
        for nid in group.contains:
            node_to_group_name[nid] = group.name

    # Partition and sort
    grouped = sorted(
        [n for n in graph.nodes if n.id in node_to_group_name],
        key=lambda n: (node_to_group_name.get(n.id, ""), n.label, n.id),
    )
    ungrouped = sorted(
        [n for n in graph.nodes if n.id not in node_to_group_name],
        key=lambda n: (n.label, n.id),
    )

    lines = [
        "| Component | Type | Technology | Group | Source | Confidence |",
        "|-----------|------|------------|-------|--------|------------|",
    ]

    for node in grouped + ungrouped:
        tech = resolve_entity(node.technology) if node.technology else ""
        group = node_to_group_name.get(node.id, "")
        confidence = f"{node.confidence:.2f}"
        # S4: Escape pipes in cell values to prevent table breakage
        label = _escape_table_cell(node.label)
        kind = _escape_table_cell(node.kind or "")
        tech = _escape_table_cell(tech)
        group = _escape_table_cell(group)
        source = _escape_table_cell(node.source_text or "")
        lines.append(
            f"| {label} | {kind} | {tech} | {group} | "
            f"{source} | {confidence} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Connection table
# ---------------------------------------------------------------------------


def graph_to_connection_table(graph: "DiagramGraph") -> str:
    """Generate deterministic Markdown connection table.

    Ordering: by source label, then target label, then edge id.
    """
    if graph is None or not graph.edges:
        return "No connections identified."

    node_map = {n.id: n for n in graph.nodes}

    sorted_edges = sorted(
        graph.edges,
        key=lambda e: (
            node_map.get(e.source_id, _placeholder_node()).label,
            node_map.get(e.target_id, _placeholder_node()).label,
            e.id,
        ),
    )

    lines = [
        "| From | To | Label | Direction | Confidence |",
        "|------|----|-------|-----------|------------|",
    ]

    for edge in sorted_edges:
        src = node_map.get(edge.source_id)
        tgt = node_map.get(edge.target_id)
        # S4: Escape pipes in cell values
        from_label = _escape_table_cell(src.label if src else edge.source_id)
        to_label = _escape_table_cell(tgt.label if tgt else edge.target_id)
        label = _escape_table_cell(edge.label or "")
        direction = (edge.direction or "forward").lower()
        dir_display = _DIRECTION_DISPLAY.get(direction, "→")
        confidence = f"{edge.confidence:.2f}"
        lines.append(
            f"| {from_label} | {to_label} | {label} | {dir_display} | {confidence} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------


def render_diagram_analyses(
    analyses: dict[int, "SlideAnalysis"],
) -> dict[int, "SlideAnalysis"]:
    """Populate deterministic rendering fields on DiagramAnalysis instances.

    Skips:
    - Non-DiagramAnalysis slides
    - Abstained analyses with graph is None

    Renders (including abstained candidate graphs with graph is not None):
    - mermaid
    - description
    - component_table
    - connection_table

    Does NOT overwrite inherited SlideAnalysis fields.
    """
    from ..pipeline.analysis import DiagramAnalysis

    for slide_num, analysis in analyses.items():
        if not isinstance(analysis, DiagramAnalysis):
            continue

        # Skip abstained-with-no-graph
        if analysis.graph is None:
            continue

        # Render Mermaid
        try:
            mermaid_text, render_uncertainties = graph_to_mermaid(analysis.graph)

            if mermaid_text:
                analysis.mermaid = mermaid_text

            # Propagate render-time uncertainties
            if render_uncertainties:
                analysis.uncertainties = list(analysis.uncertainties) + render_uncertainties
                analysis.review_required = True
        except Exception as exc:
            logger.warning(
                "Mermaid rendering failed for slide %d: %s", slide_num, exc
            )
            analysis.uncertainties = list(analysis.uncertainties) + [
                f"Mermaid rendering failed: {exc}"
            ]
            analysis.review_required = True

        # Render prose
        try:
            prose = graph_to_prose(analysis.graph)
            if prose:
                analysis.description = prose
        except Exception as exc:
            logger.warning(
                "Prose rendering failed for slide %d: %s", slide_num, exc
            )

        # Render tables
        try:
            analysis.component_table = graph_to_component_table(analysis.graph)
        except Exception as exc:
            logger.warning(
                "Component table rendering failed for slide %d: %s", slide_num, exc
            )

        try:
            analysis.connection_table = graph_to_connection_table(analysis.graph)
        except Exception as exc:
            logger.warning(
                "Connection table rendering failed for slide %d: %s", slide_num, exc
            )

    return analyses
