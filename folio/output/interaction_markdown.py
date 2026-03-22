"""Markdown assembly for interaction notes."""

from __future__ import annotations

from typing import Iterable

from ..pipeline.interaction_analysis import (
    InteractionAnalysisResult,
    InteractionFinding,
    InteractionQuote,
)
from ..tracking.versions import VersionInfo

_HYPOTHESIS_STUB = (
    "[STUB at L0 — filled during L0→L1 promotion by human, refined at L2 by enrichment]\n"
    "[Prompt: Did this interaction change, support, or challenge any active hypotheses?]"
)


def assemble_interaction(
    *,
    title: str,
    frontmatter: str,
    source_display_path: str,
    version_info: VersionInfo,
    analysis_result: InteractionAnalysisResult,
    raw_transcript: str,
) -> str:
    """Render the markdown body for an interaction note."""

    lines: list[str] = [frontmatter.rstrip(), "", f"# {title}", ""]
    lines.append(
        f"Source transcript: `{source_display_path}` | Version: {version_info.version}"
    )
    lines.append("")

    if analysis_result.llm_status != "executed":
        lines.extend(
            [
                "> [!warning] Analysis Unavailable",
                "> LLM analysis did not run for this interaction. Summary and structured findings",
                "> may be incomplete until the note is reprocessed successfully.",
                "",
            ]
        )

    lines.extend(["## Summary", ""])
    if analysis_result.summary:
        lines.extend(analysis_result.summary.splitlines())
    else:
        lines.append("[Summary unavailable — re-run `folio ingest` to populate analysis.]")
    lines.append("")

    lines.extend(["## Key Findings", "", "### Claims", ""])
    _append_findings(lines, analysis_result.claims)
    lines.extend(["", "### Data Points", ""])
    _append_findings(lines, analysis_result.data_points)
    lines.extend(["", "### Decisions", ""])
    _append_findings(lines, analysis_result.decisions)
    lines.extend(["", "### Open Questions", ""])
    _append_findings(lines, analysis_result.open_questions)
    lines.append("")

    lines.extend(["## Entities Mentioned", "", "### People", ""])
    _append_entities(lines, analysis_result.entities.get("people", []))
    lines.extend(["", "### Departments", ""])
    _append_entities(lines, analysis_result.entities.get("departments", []))
    lines.extend(["", "### Systems", ""])
    _append_entities(lines, analysis_result.entities.get("systems", []))
    lines.extend(["", "### Processes", ""])
    _append_entities(lines, analysis_result.entities.get("processes", []))
    lines.append("")

    lines.extend(["## Quotes / Evidence", ""])
    _append_quotes(lines, analysis_result.notable_quotes)
    lines.append("")

    lines.extend(["## Impact on Hypotheses", "", _HYPOTHESIS_STUB, ""])

    lines.append("> [!quote]- Raw Transcript")
    for row in raw_transcript.splitlines() or [""]:
        lines.append(f"> {row}" if row else ">")

    return "\n".join(lines).rstrip() + "\n"


def _append_findings(lines: list[str], findings: Iterable[InteractionFinding]) -> None:
    items = list(findings)
    if not items:
        lines.append("- None captured.")
        return

    for finding in items:
        lines.append(f"- {finding.statement}")
        lines.append(f"  - quote: \"{finding.quote}\"")
        lines.append(
            f"  - details: {finding.element_type}, {finding.confidence}"
        )
        if finding.speaker:
            lines.append(f"  - speaker: {finding.speaker}")
        if finding.timestamp:
            lines.append(f"  - timestamp: {finding.timestamp}")
        if finding.attribution:
            lines.append(f"  - attribution: {finding.attribution}")
        lines.append(f"  - validated: {'yes' if finding.validated else 'no'}")


def _append_entities(lines: list[str], values: Iterable[str]) -> None:
    items = list(values)
    if not items:
        lines.append("- None")
        return
    for item in items:
        lines.append(f"- [[{item}]]")


def _append_quotes(lines: list[str], quotes: Iterable[InteractionQuote]) -> None:
    items = list(quotes)
    if not items:
        lines.append("- None captured.")
        return
    for quote in items:
        lines.append(f"- \"{quote.quote}\"")
        lines.append(f"  - details: {quote.element_type}, {quote.confidence}")
        if quote.speaker:
            lines.append(f"  - speaker: {quote.speaker}")
        if quote.timestamp:
            lines.append(f"  - timestamp: {quote.timestamp}")
        lines.append(f"  - validated: {'yes' if quote.validated else 'no'}")
