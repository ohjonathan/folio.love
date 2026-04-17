"""Synthesis reporting for Tier 4 proposal-layer findings.

Consumes the §5 shared proposal contract from
``docs/specs/tier4_discovery_proposal_layer_spec.md`` and renders a structural
synthesis report across a scope. Read-only; no LLM calls in v0.8.0.

Sub-slice 2 of Shipping Plan §15.6 (shared-consumer expansion). Parity with
``folio.graph.graph_doctor``: both consumers call
``folio.tracking.trust.derive_trust_status`` as the single source of truth
for §5 row 5 (trust_status), consume
``folio.links.collect_pending_relationship_proposals`` as the §5 read path,
and emit the 11 shared-contract keys on each finding.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

import click

from .config import FolioConfig
from .links import collect_pending_relationship_proposals, _matches_scope
from .tracking import registry as registry_mod
from .tracking.trust import derive_trust_status

SCHEMA_VERSION = "1.0"
COMMAND_NAME = "synthesize"


class ScopeResolutionError(Exception):
    """Raised when a synthesize scope argument does not resolve to any
    engagement subtree or document ID (DCB-2 closure)."""


@dataclass(frozen=True)
class SynthesisFinding:
    """A single proposal-linked cross-reference, shaped for the shared envelope.

    Field order mirrors ``folio.graph._SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS``
    (graph.py:30-42) for cross-consumer JSON parity (D2-SF-7). ``proposal_id``
    leads (v0.7.1 precedent); the 11 parent §5 keys follow in graph's order;
    synthesize-specific additives (``relation``, ``flagged_inputs``) trail.
    """

    proposal_id: str
    proposal_type: str
    source_id: str
    target_id: Optional[str]
    subject_id: Optional[str]
    evidence_bundle: list[str]
    reason_summary: str
    trust_status: str
    schema_gate_result: Optional[dict]
    producer: str
    input_fingerprint: str
    lifecycle_state: str
    relation: Optional[str]
    # D2-SF-11 closure: carry the source/target flagged detail so auditors
    # can tell which document triggered the flag. Empty list for trust_status
    # == "ok"; non-empty (containing "source", "target", or both) when
    # flagged. Additive finding-level field per §3.3 CB-3 policy — stays on
    # schema_version "1.0".
    flagged_inputs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SynthesisReport:
    """Structured synthesis-report payload returned by ``synthesize()``.

    ``scope`` is ``None`` for library-wide (matches MIN-1 JSON-null
    convention). Mutations to ``findings`` after construction are idiomatic
    Python violations of ``frozen=True`` intent, not contract guarantees
    (D2-SF-4 accept-as-is note).
    """

    scope: Optional[str]
    findings: list[SynthesisFinding]
    excluded_flagged_count: int
    trust_override_active: bool
    # D2-SF-12 closure: truncation tracking for the stdout footer.
    # Internal-only in v0.8.0; envelope surfacing deferred to v0.8.1 with
    # schema_version bump per spec §3.3 / §10.
    total_available: int = 0
    truncated: bool = False


def _normalize_scope_arg(scope: Optional[str]) -> Optional[str]:
    """Normalize library-wide sentinels to ``None``.

    ``None``, ``"-"``, empty string, and whitespace-only all map to library-
    wide (D2-SF-2 closure).
    """
    if scope is None:
        return None
    stripped = scope.strip()
    if stripped in ("", "-"):
        return None
    return stripped


def _resolve_scope(config: FolioConfig, scope_arg: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Resolve a user-supplied scope argument.

    Returns ``(doc_id, subtree_scope)``. At most one is non-``None``.
    Both ``None`` ⇒ library-wide. Raises :class:`ScopeResolutionError` if
    the argument resolves to neither a registered doc ID nor any
    ``markdown_path`` / ``deck_dir`` subtree (DCB-1 + DCB-2 closure).
    """
    normalized = _normalize_scope_arg(scope_arg)
    if normalized is None:
        return None, None
    library_root = config.library_root.resolve()
    registry_data = registry_mod.load_registry(library_root / "registry.json")
    decks = registry_data.get("decks", {})
    if normalized in decks:
        return normalized, None
    for entry_data in decks.values():
        entry = registry_mod.entry_from_dict(entry_data)
        if _matches_scope(entry.markdown_path, normalized) or _matches_scope(
            entry.deck_dir, normalized
        ):
            return None, normalized
    raise ScopeResolutionError(
        f"scope '{scope_arg}' does not resolve to an engagement or document."
    )


def synthesize(
    config: FolioConfig,
    *,
    scope: Optional[str] = None,
    include_flagged: bool = False,
    limit: Optional[int] = None,
) -> SynthesisReport:
    """Produce a structural synthesis report for the given scope.

    Read-only. Consumes the §5 shared proposal contract via
    ``folio.links.collect_pending_relationship_proposals``, derives trust
    posture via the shared ``folio.tracking.trust.derive_trust_status``,
    and returns one :class:`SynthesisFinding` per pending relationship
    proposal in scope.

    Raises :class:`ScopeResolutionError` if ``scope`` is non-empty and
    matches neither a registered document ID nor any subtree path.
    """
    doc_id, subtree_scope = _resolve_scope(config, scope)
    views, counts = collect_pending_relationship_proposals(
        config,
        scope=subtree_scope,
        doc_id=doc_id,
        include_flagged=include_flagged,
    )
    total_available = len(views)
    if limit is not None:
        views = views[:limit]
    truncated = limit is not None and total_available > len(views)
    findings = [
        SynthesisFinding(
            proposal_id=view.proposal.proposal_id,
            proposal_type="relationship",
            source_id=view.source_id,
            target_id=view.proposal.target_id,
            subject_id=None,
            evidence_bundle=list(view.proposal.signals),
            reason_summary=view.proposal.rationale,
            trust_status=derive_trust_status(view),
            schema_gate_result=None,
            producer=view.producer,
            input_fingerprint=view.proposal.basis_fingerprint,
            lifecycle_state=view.proposal.lifecycle_state,
            relation=view.proposal.relation,
            flagged_inputs=list(view.flagged_inputs),
        )
        for view in views
    ]
    return SynthesisReport(
        scope=_normalize_scope_arg(scope),
        findings=findings,
        excluded_flagged_count=counts.flagged_input,
        trust_override_active=include_flagged,
        total_available=total_available,
        truncated=truncated,
    )


def render_envelope(report: SynthesisReport) -> dict:
    """Build the shared payload-level JSON envelope for ``--json`` output.

    Top-level keys are exactly the six required by the v0.8.0 envelope
    (spec §3.3 E1b producer-exact discipline). Each finding serializes via
    :func:`dataclasses.asdict`; ``flagged_inputs`` is emitted as a
    finding-level additive key (permitted at ``schema_version == "1.0"``).
    ``total_available`` and ``truncated`` are internal-only (stdout
    footer); they are NOT emitted in the envelope until a v0.8.1
    ``schema_version`` bump.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "command": COMMAND_NAME,
        "scope": report.scope,
        "trust_override_active": report.trust_override_active,
        "excluded_flagged_count": report.excluded_flagged_count,
        "findings": [_finding_to_envelope(f) for f in report.findings],
    }


def _finding_to_envelope(finding: SynthesisFinding) -> dict:
    """Convert a :class:`SynthesisFinding` to its envelope dict form.

    Preserves declared field order so that cross-consumer JSON diffs stay
    stable (D2-SF-7 parity with graph emission order).
    """
    return asdict(finding)


def _format_flag_suffix(flagged_inputs: list[str]) -> str:
    """Render ``[flagged: ...]`` showing source/target detail (D2-SF-11)."""
    if not flagged_inputs:
        return ""
    detail = "+".join(sorted(flagged_inputs))
    return f" [flagged: {detail}]"


def _render_synthesis_stdout(report: SynthesisReport) -> None:
    """Print a compact human-readable synthesis summary to stdout.

    Always emits the ``Excluded (flagged inputs): N`` line (even at zero)
    to honor parent §11 rule 5 purposively. Zero-findings + zero-exclusions
    case adds a next-action diagnostic breadcrumb (CB-5); breadcrumb
    ordering leads with scope-check (D2-SF-13). When ``--limit`` caused
    truncation, prints an ``(limited to N of M total)`` footer (D2-SF-12).
    """
    scope_label = report.scope if report.scope is not None else "(library-wide)"
    click.echo(f"Synthesis for scope: {scope_label}")
    click.echo(f"Findings: {len(report.findings)}")
    excluded_suffix = (
        " (use --include-flagged to include)"
        if report.excluded_flagged_count
        else ""
    )
    click.echo(
        f"Excluded (flagged inputs): {report.excluded_flagged_count}{excluded_suffix}"
    )
    if report.trust_override_active:
        click.echo("Trust override active: --include-flagged")
    if not report.findings and report.excluded_flagged_count == 0:
        click.echo(
            "Next: check that the scope resolves, or run `folio ingest` / "
            "`folio enrich` if no proposals have been emitted yet."
        )
    click.echo("")
    for finding in report.findings:
        flag_suffix = _format_flag_suffix(finding.flagged_inputs)
        gate_suffix = ""
        if finding.schema_gate_result is not None:
            rule = finding.schema_gate_result.get("rule", "unknown")
            gate_suffix = f" [schema-gate: {rule}]"
        rel = finding.relation or "<n/a>"
        click.echo(
            f"[{finding.lifecycle_state}{flag_suffix}{gate_suffix}] "
            f"{finding.source_id} --{rel}--> "
            f"{finding.target_id or '—'}  ({finding.producer})"
        )
        click.echo(f"  {finding.reason_summary}")
    if report.truncated:
        click.echo(
            f"(limited to {len(report.findings)} of {report.total_available} "
            "total; use --limit to adjust or omit for all)"
        )
