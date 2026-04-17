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

from dataclasses import asdict, dataclass
from typing import Optional

import click

from .config import FolioConfig
from .links import collect_pending_relationship_proposals
from .tracking.trust import derive_trust_status

SCHEMA_VERSION = "1.0"
COMMAND_NAME = "synthesize"


@dataclass(frozen=True)
class SynthesisFinding:
    proposal_id: str
    proposal_type: str
    source_id: str
    target_id: Optional[str]
    subject_id: Optional[str]
    relation: Optional[str]
    evidence_bundle: list[str]
    reason_summary: str
    trust_status: str
    producer: str
    lifecycle_state: str
    schema_gate_result: Optional[dict]
    input_fingerprint: str


@dataclass(frozen=True)
class SynthesisReport:
    scope: Optional[str]
    findings: list[SynthesisFinding]
    excluded_flagged_count: int
    trust_override_active: bool


def synthesize(
    config: FolioConfig,
    *,
    scope: Optional[str] = None,
    include_flagged: bool = False,
    limit: Optional[int] = None,
) -> SynthesisReport:
    resolved_scope = None if scope in (None, "-") else scope
    views, counts = collect_pending_relationship_proposals(
        config, scope=resolved_scope, include_flagged=include_flagged
    )
    if limit is not None:
        views = views[:limit]
    findings = [
        SynthesisFinding(
            proposal_id=view.proposal.proposal_id,
            proposal_type="relationship",
            source_id=view.source_id,
            target_id=view.proposal.target_id,
            subject_id=None,
            relation=view.proposal.relation,
            evidence_bundle=list(view.proposal.signals),
            reason_summary=view.proposal.rationale,
            trust_status=derive_trust_status(view),
            producer=view.producer,
            lifecycle_state=view.proposal.lifecycle_state,
            schema_gate_result=None,
            input_fingerprint=view.proposal.basis_fingerprint,
        )
        for view in views
    ]
    return SynthesisReport(
        scope=resolved_scope,
        findings=findings,
        excluded_flagged_count=counts.flagged_input,
        trust_override_active=include_flagged,
    )


def render_envelope(report: SynthesisReport) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": COMMAND_NAME,
        "scope": report.scope,
        "trust_override_active": report.trust_override_active,
        "excluded_flagged_count": report.excluded_flagged_count,
        "findings": [asdict(f) for f in report.findings],
    }


def _render_synthesis_stdout(report: SynthesisReport) -> None:
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
            "Next: run `folio ingest` or `folio enrich` if no proposals "
            "have been emitted yet, or check that the scope resolves."
        )
    click.echo("")
    for finding in report.findings:
        flag = " [flagged]" if finding.trust_status == "flagged" else ""
        gate_suffix = ""
        if finding.schema_gate_result is not None:
            rule = finding.schema_gate_result.get("rule", "unknown")
            gate_suffix = f" [schema-gate: {rule}]"
        rel = finding.relation or "<n/a>"
        click.echo(
            f"[{finding.lifecycle_state}{flag}{gate_suffix}] "
            f"{finding.source_id} --{rel}--> "
            f"{finding.target_id or '—'}  ({finding.producer})"
        )
        click.echo(f"  {finding.reason_summary}")
