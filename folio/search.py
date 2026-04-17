"""Search surface for Tier 4 proposal-layer findings.

Consumes the §5 shared proposal contract from
``docs/specs/tier4_discovery_proposal_layer_spec.md`` as a QUERY lens over
the pending relationship-proposal queue. Read-only; no LLM calls in
v0.9.0.

Sub-slice 3 of Shipping Plan §15.6 (shared-consumer expansion). Parity
with :mod:`folio.graph` and :mod:`folio.synthesize`: all three consumers
call :func:`folio.tracking.trust.derive_trust_status` as the single
source of truth for §5 row 5 (``trust_status``), consume
:func:`folio.links.collect_pending_relationship_proposals` as the §5
read path, and emit the 11 shared-contract keys on each finding. Search
extends the shared payload-level ``--json`` envelope to
``schema_version: "1.1"`` by adding a ``query`` top-level key (first
minor-version increment of the shared envelope — see the v0.8.0
synthesize §3.3 versioning policy).
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

import click

from .config import FolioConfig
from .links import collect_pending_relationship_proposals, _matches_scope
from .tracking import registry as registry_mod
from .tracking.trust import derive_trust_status

SCHEMA_VERSION = "1.1"
COMMAND_NAME = "search"

SEARCHABLE_FIELDS: tuple[str, ...] = (
    "source_id",
    "target_id",
    "relation",
    "producer",
    "reason_summary",
    "evidence_bundle",
)


class ScopeResolutionError(Exception):
    """Raised when --scope does not resolve to any engagement subtree or
    document ID (mirrors :class:`folio.synthesize.ScopeResolutionError`)."""


@dataclass(frozen=True)
class SearchFinding:
    """A single proposal matching QUERY, shaped for the shared envelope.

    Field order mirrors :class:`folio.synthesize.SynthesisFinding` (which
    in turn mirrors ``folio.graph._SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS``)
    for cross-consumer JSON parity. ``proposal_id`` leads; the 11 parent
    §5 keys follow; ``relation`` and ``flagged_inputs`` trail.
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
    flagged_inputs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchReport:
    """Structured search-report payload returned by :func:`search`.

    ``scope`` is ``None`` for library-wide. ``query`` carries the
    verbatim QUERY input (never normalized) for round-trip through JSON.
    """

    scope: Optional[str]
    query: str
    findings: list[SearchFinding]
    excluded_flagged_count: int
    trust_override_active: bool
    total_available: int = 0
    truncated: bool = False
    # CSF-3 closure: observed producer names from the QUERY-matched view
    # set (pre-producer-filter). Populated ONLY when --producer was
    # supplied AND findings==0 — otherwise left as None. Stdout
    # (_render_search_stdout) uses it for the "Hint: --producer matches
    # exactly" breadcrumb. Not emitted in the --json envelope (that would
    # be another top-level-key bump).
    producer_hint_names: Optional[list[str]] = None


def _normalize_scope_arg(scope: Optional[str]) -> Optional[str]:
    """Normalize library-wide sentinels to ``None``.

    ``None``, ``"-"``, empty string, and whitespace-only all map to
    library-wide (MIN-1 carry-forward from synthesize).
    """
    if scope is None:
        return None
    stripped = scope.strip()
    if stripped in ("", "-"):
        return None
    return stripped


def _resolve_scope(
    config: FolioConfig, scope_arg: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """Resolve a user-supplied scope argument.

    Returns ``(doc_id, subtree_scope)``. At most one is non-``None``.
    Both ``None`` ⇒ library-wide. Raises :class:`ScopeResolutionError`
    if the argument resolves to neither a registered doc ID nor any
    ``markdown_path`` / ``deck_dir`` subtree.
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


def _normalize_search_text(value: Any) -> Optional[str]:
    """Normalize a value for search comparison (CB-2 closure).

    Returns ``None`` for non-string, ``None``, empty, or whitespace-only
    values (cannot match any QUERY). Otherwise applies NFC canonical
    composition (so canonically equivalent sequences compare equal) and
    then casefold (so Unicode case folding handles eszett, Turkish
    dotless-I, etc.).
    """
    if not isinstance(value, str):
        return None
    if not value or not value.strip():
        return None
    return unicodedata.normalize("NFC", value).casefold()


def _view_matches(view, needle: str) -> bool:
    """Return ``True`` if ``needle`` substring-matches any of the six
    searchable text fields on ``view`` (§3.6 rule).

    ``needle`` is expected to already be normalized (NFC + casefold).
    Non-string / ``None`` field values are skipped silently via
    :func:`_normalize_search_text`.
    """
    source_id = _normalize_search_text(view.source_id)
    if source_id and needle in source_id:
        return True
    target_id = _normalize_search_text(view.proposal.target_id)
    if target_id and needle in target_id:
        return True
    relation = _normalize_search_text(view.proposal.relation)
    if relation and needle in relation:
        return True
    producer = _normalize_search_text(view.producer)
    if producer and needle in producer:
        return True
    rationale = _normalize_search_text(view.proposal.rationale)
    if rationale and needle in rationale:
        return True
    for signal in view.proposal.signals or []:
        normalized = _normalize_search_text(signal)
        if normalized and needle in normalized:
            return True
    return False


def _view_to_finding(view) -> SearchFinding:
    """Convert a matched view to a :class:`SearchFinding`.

    Called only for matched views (post QUERY + --producer filter),
    honoring CSF-4 "once per matched view" invariant: the shared trust
    helper is invoked exactly once per emitted finding.
    """
    return SearchFinding(
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


def search(
    config: FolioConfig,
    *,
    query: str,
    scope: Optional[str] = None,
    producer: Optional[str] = None,
    include_flagged: bool = False,
    limit: Optional[int] = None,
) -> SearchReport:
    """Produce a search report narrowing pending proposals by QUERY.

    Read-only. Consumes the §5 shared proposal contract via
    :func:`folio.links.collect_pending_relationship_proposals`, derives
    trust posture via the shared :func:`derive_trust_status`, and
    returns one :class:`SearchFinding` per queued relationship proposal
    in scope whose text fields substring-match QUERY (NFC + casefold).

    Raises :class:`ScopeResolutionError` if ``scope`` is non-empty and
    matches neither a registered document ID nor any subtree path.
    Raises :class:`ValueError` if ``query`` is empty or whitespace-only.
    """
    if not isinstance(query, str) or not query or not query.strip():
        raise ValueError(
            "QUERY must contain at least one non-whitespace character."
        )
    needle = _normalize_search_text(query)
    if needle is None:
        # Defensive guard — _normalize_search_text returns None for
        # whitespace-only, which we already rejected above.
        raise ValueError(
            "QUERY must contain at least one non-whitespace character."
        )
    doc_id, subtree_scope = _resolve_scope(config, scope)
    views, counts = collect_pending_relationship_proposals(
        config,
        scope=subtree_scope,
        doc_id=doc_id,
        include_flagged=include_flagged,
    )
    query_matched = [v for v in views if _view_matches(v, needle)]
    if producer is not None:
        producer_matched = [v for v in query_matched if v.producer == producer]
    else:
        producer_matched = query_matched
    total_available = len(producer_matched)
    if limit is not None:
        producer_matched = producer_matched[:limit]
    truncated = limit is not None and total_available > len(producer_matched)
    findings = [_view_to_finding(v) for v in producer_matched]
    producer_hint_names: Optional[list[str]] = None
    if producer is not None and not findings:
        # CSF-3: collect observed producer names from the QUERY-matched
        # views (pre-producer-filter) so stdout can hint at case mismatch.
        producer_hint_names = [v.producer for v in query_matched]
    return SearchReport(
        scope=_normalize_scope_arg(scope),
        query=query,
        findings=findings,
        excluded_flagged_count=counts.flagged_input,
        trust_override_active=include_flagged,
        total_available=total_available,
        truncated=truncated,
        producer_hint_names=producer_hint_names,
    )


def render_envelope(report: SearchReport) -> dict:
    """Build the shared payload-level JSON envelope for ``--json``.

    Top-level keys at ``schema_version: "1.1"``:
    ``schema_version``, ``command``, ``scope``, ``query``,
    ``trust_override_active``, ``excluded_flagged_count``, ``findings``
    (7 keys total). The ``query`` key is the additive that triggers the
    "1.0" → "1.1" bump per synthesize §3.3 versioning policy.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "command": COMMAND_NAME,
        "scope": report.scope,
        "query": report.query,
        "trust_override_active": report.trust_override_active,
        "excluded_flagged_count": report.excluded_flagged_count,
        "findings": [asdict(f) for f in report.findings],
    }


def _validate_query(ctx, param, value: str) -> str:
    """Click callback: reject empty / whitespace-only QUERY (CB-2 closure).

    Raises :class:`click.UsageError` (exit 2) when QUERY is absent of
    non-whitespace characters. Mirrors the function-level guard in
    :func:`search` so CLI and library paths fail identically.
    """
    if not isinstance(value, str) or not value or not value.strip():
        raise click.UsageError(
            "QUERY must contain at least one non-whitespace character."
        )
    return value


def _format_flag_suffix(flagged_inputs: list[str]) -> str:
    """Render `` [flagged: ...]`` showing source/target detail."""
    if not flagged_inputs:
        return ""
    detail = "+".join(sorted(flagged_inputs))
    return f" [flagged: {detail}]"


def _render_search_stdout(report: SearchReport) -> None:
    """Print a compact human-readable search summary to stdout.

    Always prints the excluded-flagged-count line (even at 0) to honor
    parent §11 rule 5 purposively. Zero-findings + zero-exclusions case
    adds a search-specific next-action breadcrumb. When ``--producer``
    was supplied AND findings==0, prints a CSF-3 hint with producer
    names from ``report.producer_hint_names``.
    """
    producer_hint_names = report.producer_hint_names
    scope_label = report.scope if report.scope is not None else "(library-wide)"
    click.echo(f"Search for '{report.query}' in scope: {scope_label}")
    click.echo(f"Matches: {len(report.findings)}")
    excluded_suffix = (
        " (use --include-flagged to include)"
        if report.excluded_flagged_count
        else ""
    )
    click.echo(
        f"Excluded (flagged inputs in scope): {report.excluded_flagged_count}{excluded_suffix}"
    )
    if report.trust_override_active:
        click.echo("Trust override active: --include-flagged")
    if not report.findings and producer_hint_names is not None:
        if producer_hint_names:
            observed = sorted(set(producer_hint_names))
            click.echo(
                "Hint: --producer matches exactly (case-sensitive). "
                f"Observed producers in scope: {observed}"
            )
        else:
            click.echo(
                "Hint: no proposals in scope for any producer. "
                "Run `folio ingest` / `folio enrich` to populate the queue."
            )
    elif (
        not report.findings
        and report.excluded_flagged_count == 0
        and producer_hint_names is None
    ):
        click.echo(
            f"No matches for '{report.query}'. Try a broader scope, check "
            f"spelling, or run `folio ingest` / `folio enrich` if no "
            f"proposals have been emitted yet."
        )
    click.echo("")
    for finding in report.findings:
        flag_suffix = _format_flag_suffix(finding.flagged_inputs)
        rel = finding.relation or "<n/a>"
        click.echo(
            f"[{finding.lifecycle_state}{flag_suffix}] "
            f"{finding.source_id} --{rel}--> "
            f"{finding.target_id or '—'}  ({finding.producer})"
        )
        click.echo(f"  {finding.reason_summary}")
    if report.truncated:
        click.echo(
            f"(showing {len(report.findings)} of {report.total_available}; "
            f"use --limit to adjust)"
        )
