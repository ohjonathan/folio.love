"""folio digest — daily and weekly synthesis digests.

Implements `folio digest <scope>` per docs/specs/v0.7.0_folio_digest_spec.md
(spec v1.2). Greenfield first slice of the Tier 4 digest cluster — daily +
weekly, engagement-scoped, source-less analysis docs.

Public surface:
- generate_daily_digest(config, *, scope, date, include_flagged, llm_profile)
- generate_weekly_digest(config, *, scope, date, include_flagged, llm_profile)
- DigestResult, DigestFlaggedCounts, DailyInputSelection (dataclasses)
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import yaml

from .config import FolioConfig
from .links import _is_flagged
from .naming import derive_engagement_short, sanitize_token
from .tracking import registry
from .tracking.registry import RegistryEntry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public dataclasses (spec §3.1)
# ---------------------------------------------------------------------------


@dataclass
class DigestFlaggedCounts:
    """Structured flagged-input counts (SF-108).

    Mirrors v0.6.4 `SuppressionCounts` rationale — prevents positional-tuple
    swap bugs between collector and renderer.
    """
    excluded: int = 0
    included: int = 0


@dataclass
class DailyInputSelection:
    """Structured return for `_collect_daily_inputs` (SF-108)."""
    eligible: list  # list[RegistryEntry]
    counts: DigestFlaggedCounts


@dataclass
class DigestResult:
    status: Literal["written", "rerun", "empty", "error"]
    digest_id: Optional[str]
    path: Optional[Path]
    flagged_counts: DigestFlaggedCounts
    draws_from_count: int
    message: str
    exit_code: int


# ---------------------------------------------------------------------------
# Body templates (spec §9)
# ---------------------------------------------------------------------------

# LLM-owned headings the model MUST emit (B-101 / §9.6 ownership split).
_DAILY_LLM_OWNED_HEADINGS = (
    "Summary",
    "What Moved Today",
    "Emerging Risks / Open Questions",
    "Suggested Follow-Ups",
)
_WEEKLY_LLM_OWNED_HEADINGS = (
    "Weekly Summary",
    "What Changed This Week",
    "Cross-Cutting Themes",
    "Decisions / Risks To Track",
    "Next Week Lookahead",
)

# System-owned headings the system inserts deterministically.
_DAILY_SYSTEM_OWNED = ("Documents Drawn From", "Trust Notes")
_WEEKLY_SYSTEM_OWNED = ("Daily Digests Drawn From", "Trust Notes")

# Final-body section order (spec §9.1 / §9.2).
_DAILY_SECTION_ORDER = (
    "Summary",
    "What Moved Today",
    "Emerging Risks / Open Questions",
    "Documents Drawn From",
    "Suggested Follow-Ups",
    "Trust Notes",
)
_WEEKLY_SECTION_ORDER = (
    "Weekly Summary",
    "What Changed This Week",
    "Cross-Cutting Themes",
    "Decisions / Risks To Track",
    "Daily Digests Drawn From",
    "Next Week Lookahead",
    "Trust Notes",
)


# ---------------------------------------------------------------------------
# Scope + date helpers
# ---------------------------------------------------------------------------


def _resolve_engagement_scope(
    config: FolioConfig, scope: str
) -> tuple[str, str, Path]:
    """Validate scope resolves under exactly one engagement subtree.

    Returns sanitized (client, engagement, engagement_root). engagement_root
    is exactly library_root/<client>/<engagement> per spec §7 path layout.
    Raises ValueError on invalid input.
    """
    if not scope or not scope.strip():
        raise ValueError("scope is required")

    library_root = config.library_root.resolve()
    scope_path = (library_root / scope).resolve()

    try:
        scope_path.relative_to(library_root)
    except ValueError:
        raise ValueError(
            f"scope '{scope}' resolves outside library_root {library_root}"
        )

    parts = scope.replace("\\", "/").strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(
            f"scope '{scope}' must resolve under one engagement subtree "
            f"(e.g. 'ClientA/DD_Q1_2026'); got too few path components"
        )

    # Preserve original case for frontmatter/registry (matches
    # analysis_docs.create_analysis_document pattern at analysis_docs.py:154-155).
    # `_compute_digest_id` calls sanitize_token internally for the ID slug.
    client = parts[0]
    engagement = parts[1]
    engagement_root = (library_root / parts[0] / parts[1]).resolve()

    if not engagement_root.exists():
        raise ValueError(
            f"scope '{scope}' engagement root {engagement_root} does not exist"
        )

    return client, engagement, engagement_root


def _parse_date(date_str: str) -> date:
    """Parse YYYY-MM-DD with explicit error (SF-202: capital I + trailing period)."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid --date '{date_str}': expected YYYY-MM-DD format."
        )


def _iso_week_monday(d: date) -> date:
    """Return the Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def _compact_period(d: date) -> str:
    """YYYYMMDD compact form for digest IDs."""
    return d.strftime("%Y%m%d")


def _matches_scope(path: str, scope: str) -> bool:
    """Path-prefix match with trailing-slash normalization (MN-5).

    Mirrors `cli._matches_scope` (cli.py:36-43); reimplemented here to
    avoid importing cli (circular).
    """
    norm_scope = scope.rstrip("/") + "/"
    return path == scope or path.startswith(norm_scope)


# ---------------------------------------------------------------------------
# Input collection (spec §5, §6)
# ---------------------------------------------------------------------------


def _activity_date(entry_modified: Optional[str], entry_converted: Optional[str]) -> Optional[str]:
    """Effective activity date per design §5.

    Returns YYYY-MM-DD literal substring (split on T for ISO timestamps), or
    None if neither modified nor converted is parseable.

    Per SF-5: literal string match; no UTC conversion.
    """
    for value in (entry_modified, entry_converted):
        if not value:
            continue
        # Take literal date portion if ISO timestamp
        date_portion = value.split("T")[0]
        # Validate YYYY-MM-DD shape
        try:
            datetime.strptime(date_portion, "%Y-%m-%d")
            return date_portion
        except (ValueError, TypeError):
            continue
    return None


def _collect_daily_inputs(
    config: FolioConfig,
    scope: str,
    day: str,
    include_flagged: bool,
) -> DailyInputSelection:
    """Apply design §5 daily input predicate.

    Returns DailyInputSelection(eligible, counts) per spec §3.2.
    """
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    data = registry.load_registry(registry_path)
    if data.get("_corrupt"):
        data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, data)

    counts = DigestFlaggedCounts()
    eligible: list[RegistryEntry] = []

    for entry_id, entry_data in data.get("decks", {}).items():
        entry = registry.entry_from_dict(entry_data)

        # Predicate 1: scope match
        if not _matches_scope(entry.markdown_path, scope):
            continue

        # Predicate 2: type filter (excludes context + analysis to prevent recursion)
        if entry.type not in ("evidence", "interaction"):
            continue

        # Predicate 3: effective activity date matches day
        activity = _activity_date(entry.modified, entry.converted)
        if activity is None or activity != day:
            continue

        # Predicate 4: trust-gate (read frontmatter for authoritative review_status)
        md_path = library_root / entry.markdown_path
        fm = registry._read_frontmatter(md_path)
        # SF-3 fail-open: missing/malformed/non-dict frontmatter → not flagged
        if fm is None or not isinstance(fm, dict):
            eligible.append(entry)
            continue

        if _is_flagged(fm.get("review_status")):
            if include_flagged:
                counts.included += 1
                eligible.append(entry)
            else:
                counts.excluded += 1
            continue

        eligible.append(entry)

    eligible.sort(key=lambda e: e.id)
    return DailyInputSelection(eligible=eligible, counts=counts)


def _collect_weekly_inputs(
    config: FolioConfig,
    scope: str,
    week_monday: date,
) -> list[RegistryEntry]:
    """Apply design §6 weekly discovery predicate."""
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    data = registry.load_registry(registry_path)
    if data.get("_corrupt"):
        data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, data)

    eligible: list[RegistryEntry] = []
    week_start = week_monday
    week_end = week_monday + timedelta(days=6)

    for entry_id, entry_data in data.get("decks", {}).items():
        entry = registry.entry_from_dict(entry_data)
        if not _matches_scope(entry.markdown_path, scope):
            continue
        if entry.type != "analysis" or entry.subtype != "digest":
            continue

        md_path = library_root / entry.markdown_path
        fm = registry._read_frontmatter(md_path)
        if fm is None or not isinstance(fm, dict):
            continue

        if fm.get("digest_type") != "daily":
            continue

        period_value = fm.get("digest_period")
        if not isinstance(period_value, str):
            continue
        try:
            period_d = datetime.strptime(period_value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        if not (week_start <= period_d <= week_end):
            continue

        eligible.append(entry)

    eligible.sort(key=lambda e: e.id)
    return eligible


# ---------------------------------------------------------------------------
# Identity + path (spec §7)
# ---------------------------------------------------------------------------


def _compute_digest_id(
    client: str, engagement_short: str, period_compact: str, label: str
) -> str:
    return (
        f"{sanitize_token(client)}_{sanitize_token(engagement_short)}"
        f"_analysis_{period_compact}_{label}"
    )


def _compute_digest_path(engagement_root: Path, digest_id: str) -> Path:
    return engagement_root / "analysis" / "digests" / digest_id / f"{digest_id}.md"


# ---------------------------------------------------------------------------
# Frontmatter rendering + persistence
# ---------------------------------------------------------------------------


def _render_frontmatter(fm: dict) -> str:
    """YAML frontmatter dump (spec §3.2)."""
    yaml_str = yaml.dump(
        fm, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    return f"---\n{yaml_str}---"


def _load_existing_digest(path: Path) -> Optional[dict]:
    """Read existing digest frontmatter for rerun (spec §3.2 + §10.4).

    Returns None on missing file, malformed YAML, or non-dict frontmatter —
    caller falls back to version: 1 per §10.4.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    return fm


def _atomic_write(path: Path, content: str) -> None:
    """Atomic write per spec §10.2 (SF-101 capture-before-write fix)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Optional[Path] = None
    try:
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False,
            suffix=".tmp",
        )
        tmp_path = Path(tmp.name)
        try:
            tmp.write(content)
        finally:
            tmp.close()
        os.replace(tmp_path, path)
        tmp_path = None  # ownership transferred
    except Exception:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _register_digest(
    config: FolioConfig,
    digest_id: str,
    path: Path,
    fm: dict,
    *,
    scope_client: str,
    scope_engagement: str,
) -> None:
    """Build RegistryEntry and upsert (spec §8.2)."""
    library_root = config.library_root.resolve()
    md_rel = str(path.relative_to(library_root)).replace("\\", "/")
    deck_dir_rel = str(path.parent.relative_to(library_root)).replace("\\", "/")

    entry = RegistryEntry(
        id=digest_id,
        title=str(fm.get("title", digest_id)),
        markdown_path=md_rel,
        deck_dir=deck_dir_rel,
        type="analysis",
        subtype="digest",
        modified=str(fm.get("modified")) if fm.get("modified") else None,
        client=scope_client,
        engagement=scope_engagement,
        authority="analyzed",
        curation_level="L1",
        staleness_status="current",
        review_status="flagged",
        review_flags=["synthesis_requires_review"],
        extraction_confidence=None,
    )
    registry_path = library_root / "registry.json"
    registry.upsert_entry(registry_path, entry)


# ---------------------------------------------------------------------------
# Body validation + scrubbing (spec §3.2 + §9.5; SF-104 fence-aware)
# ---------------------------------------------------------------------------


def _heading_positions(body: str, heading: str) -> list[int]:
    """Return line numbers (0-indexed) where `## <heading>` appears, fence-aware.

    Tracks ``` and ~~~ code fences and skips matches inside them. Matches ATX
    heading syntax per CommonMark: 0-3 leading spaces (SF-204), optional trailing
    `#` chars, optional trailing whitespace.
    """
    positions: list[int] = []
    in_fence = False
    fence_marker: Optional[str] = None
    # ATX heading: 0-3 leading spaces, then ## Heading [optional trailing #][whitespace]
    pattern = re.compile(
        rf"^[ ]{{0,3}}##\s+{re.escape(heading)}(?:\s+#+)?\s*$"
    )
    for i, line in enumerate(body.splitlines()):
        stripped = line.strip()
        # Fence tracking
        if not in_fence:
            if stripped.startswith("```"):
                in_fence = True
                fence_marker = "```"
                continue
            if stripped.startswith("~~~"):
                in_fence = True
                fence_marker = "~~~"
                continue
        else:
            if stripped.startswith(fence_marker or "```"):
                in_fence = False
                fence_marker = None
            continue
        if pattern.match(line):
            positions.append(i)
    return positions


def _validate_body_sections(
    body: str, llm_owned_headings: tuple[str, ...]
) -> tuple[list[str], list[str]]:
    """Validate LLM-owned headings only (B-101 / §9.6 ownership split).

    Returns (missing, duplicates). System-owned headings (Trust Notes,
    Documents Drawn From, etc.) are NEVER validated here.
    """
    missing: list[str] = []
    duplicates: list[str] = []
    for heading in llm_owned_headings:
        positions = _heading_positions(body, heading)
        if not positions:
            missing.append(heading)
        elif len(positions) > 1:
            duplicates.append(heading)
    return missing, duplicates


def _strip_section(body: str, heading: str) -> str:
    """Remove ALL `## <heading>` sections from body (MN-102 rename).

    Fence-aware. Removes from the heading line through the next non-fenced
    `## ` heading or end-of-body.
    """
    lines = body.splitlines()
    positions = _heading_positions(body, heading)
    if not positions:
        return body

    # Determine end-of-section for each occurrence: next any-## heading or EOF
    in_fence = False
    fence_marker: Optional[str] = None

    # Build list of all non-fenced `## ` line indices (SF-204: 0-3 leading spaces OK)
    all_h2_positions: list[int] = []
    any_heading_indented = re.compile(r"^[ ]{0,3}##\s+\S")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```"):
                in_fence = True
                fence_marker = "```"
                continue
            if stripped.startswith("~~~"):
                in_fence = True
                fence_marker = "~~~"
                continue
        else:
            if stripped.startswith(fence_marker or "```"):
                in_fence = False
                fence_marker = None
            continue
        if any_heading_indented.match(line):
            all_h2_positions.append(i)

    # For each target position, find the next any-## heading after it (or EOF)
    ranges_to_remove: list[tuple[int, int]] = []
    for pos in positions:
        next_h2 = next(
            (p for p in all_h2_positions if p > pos), len(lines)
        )
        ranges_to_remove.append((pos, next_h2))

    # Remove ranges (in reverse to keep indices stable)
    keep = [True] * len(lines)
    for start, end in ranges_to_remove:
        for j in range(start, end):
            keep[j] = False

    new_lines = [line for line, k in zip(lines, keep) if k]
    return "\n".join(new_lines).rstrip() + ("\n" if body.endswith("\n") else "")


# ---------------------------------------------------------------------------
# Trust Notes block (spec §9.3)
# ---------------------------------------------------------------------------


def _compose_trust_notes(
    *,
    include_flagged: bool,
    counts: DigestFlaggedCounts,
) -> str:
    """Render `## Trust Notes` block (spec §9.3, B-101 + SF-11 + MN-101).

    Uses six-branch matrix per §9.3 (the v1.1 4-branch matrix had the
    hallucination bug ALIGN-001).
    """
    base = (
        "## Trust Notes\n\n"
        "This digest is a synthesis artifact and remains review-required "
        "(`review_status: flagged`, `review_flags: [synthesis_requires_review]`)."
    )
    if not include_flagged and counts.excluded == 0:
        return base
    if not include_flagged and counts.excluded == 1:
        return (
            base + "\n\n"
            "Daily input selection excluded 1 source-backed input with "
            "review_status: flagged. Run with --include-flagged to widen "
            "the input set."
        )
    if not include_flagged and counts.excluded > 1:
        return (
            base + "\n\n"
            f"Daily input selection excluded {counts.excluded} source-backed "
            "inputs with review_status: flagged. Run with --include-flagged "
            "to widen the input set."
        )
    if include_flagged and counts.included == 0:
        return (
            base + "\n\n"
            "Daily input selection ran with --include-flagged; no flagged "
            "source-backed inputs were present in this scope."
        )
    if include_flagged and counts.included == 1:
        return (
            base + "\n\n"
            "Daily input selection ran with --include-flagged; 1 flagged "
            "source-backed input was included in this synthesis."
        )
    # include_flagged and counts.included > 1
    return (
        base + "\n\n"
        f"Daily input selection ran with --include-flagged; {counts.included} "
        "flagged source-backed inputs were included in this synthesis."
    )


def _compose_drawn_from(inputs: list[RegistryEntry], heading: str) -> str:
    """Render `## <heading>` section as deterministic wikilinks (spec §9.3)."""
    lines = [f"## {heading}", ""]
    for entry in sorted(inputs, key=lambda e: e.id):
        lines.append(f"- [[{entry.id}]]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call (spec §3.2 + §9.4)
# ---------------------------------------------------------------------------


def _build_daily_prompt(
    inputs: list[RegistryEntry],
    period: str,
    counts: DigestFlaggedCounts,
    include_flagged: bool,
    library_root: Path,
) -> str:
    """Assemble LLM prompt for daily digest body."""
    sections_required = "\n".join(f"- ## {h}" for h in _DAILY_LLM_OWNED_HEADINGS)
    sections_omit = "\n".join(f"- ## {h}" for h in _DAILY_SYSTEM_OWNED)

    input_blocks: list[str] = []
    for entry in inputs:
        md_path = library_root / entry.markdown_path
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            text = "(unreadable)"
        input_blocks.append(
            f"### Source: {entry.id} ({entry.type})\n\n{text}"
        )
    inputs_text = "\n\n---\n\n".join(input_blocks) if input_blocks else "(no inputs)"

    flagged_note = ""
    if include_flagged and counts.included > 0:
        flagged_note = (
            f"\n\nNote: {counts.included} flagged source-backed input(s) "
            "were included via --include-flagged.\n"
        )

    return (
        f"You are synthesizing a daily digest for engagement work on {period}.\n\n"
        f"Emit ONLY these section headings, in this order:\n{sections_required}\n\n"
        f"Do NOT emit these — the system will append them deterministically:\n{sections_omit}\n"
        f"{flagged_note}\n"
        f"Source notes for synthesis ({len(inputs)} total):\n\n{inputs_text}"
    )


def _build_weekly_prompt(
    daily_inputs: list[RegistryEntry],
    week_monday: date,
    library_root: Path,
) -> str:
    """Assemble LLM prompt for weekly digest body."""
    sections_required = "\n".join(f"- ## {h}" for h in _WEEKLY_LLM_OWNED_HEADINGS)
    sections_omit = "\n".join(f"- ## {h}" for h in _WEEKLY_SYSTEM_OWNED)

    daily_blocks: list[str] = []
    for entry in daily_inputs:
        md_path = library_root / entry.markdown_path
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            text = "(unreadable)"
        daily_blocks.append(f"### Daily digest: {entry.id}\n\n{text}")
    inputs_text = "\n\n---\n\n".join(daily_blocks) if daily_blocks else "(no daily digests)"

    return (
        f"You are synthesizing a weekly digest for the ISO week beginning "
        f"{week_monday.isoformat()} (Monday).\n\n"
        f"Emit ONLY these section headings, in this order:\n{sections_required}\n\n"
        f"Do NOT emit these — the system will append them deterministically:\n{sections_omit}\n\n"
        f"Daily digests to synthesize across ({len(daily_inputs)} total):\n\n{inputs_text}"
    )


def _call_llm(
    config: FolioConfig,
    prompt: str,
    *,
    task: str = "digest",
    llm_profile: Optional[str] = None,
) -> str:
    """Dispatch via LLMConfig.resolve_profile (spec §3.2).

    Raises on all failures (SF-16 / PR-6 contract). Never returns None.
    """
    # Resolve profile per existing precedence (config.py:107-162)
    profile = config.llm.resolve_profile(llm_profile, task=task)

    # Direct anthropic SDK call (mirrors enrich pipeline pattern but
    # simplified for digest's single-prompt synthesis use case).
    # Test suite mocks _call_llm; production wires through the provider.
    provider = (profile.provider or "").lower()
    if provider == "anthropic":
        return _call_anthropic(profile, prompt)
    elif provider == "openai":
        return _call_openai(profile, prompt)
    else:
        raise ValueError(
            f"Unsupported provider '{profile.provider}' for digest synthesis "
            f"(profile={profile.name}). Supported: anthropic, openai."
        )


def _call_anthropic(profile, prompt: str) -> str:
    """Anthropic provider call. Imports lazily."""
    import anthropic  # type: ignore[import-not-found]

    api_key = os.environ.get(profile.api_key_env or "ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"Missing API key in env var '{profile.api_key_env}' for "
            f"profile {profile.name}"
        )
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=profile.model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text  # type: ignore[union-attr]


def _call_openai(profile, prompt: str) -> str:
    """OpenAI provider call. Imports lazily."""
    import openai  # type: ignore[import-not-found]

    api_key = os.environ.get(profile.api_key_env or "OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"Missing API key in env var '{profile.api_key_env}' for "
            f"profile {profile.name}"
        )
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=profile.model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Body assembly (spec §9.4 + §9.5 + §9.6)
# ---------------------------------------------------------------------------


def _build_body_with_validation_retry(
    config: FolioConfig,
    prompt: str,
    inputs: list[RegistryEntry],
    *,
    llm_owned_headings: tuple[str, ...],
    system_owned_headings: tuple[str, ...],
    drawn_from_heading: str,
    section_order: tuple[str, ...],
    include_flagged: bool,
    counts: DigestFlaggedCounts,
    title: str,
    llm_profile: Optional[str],
) -> str:
    """Call LLM, validate LLM-owned headings, retry once on validation failure.

    Per §9.4 + §9.5 + §9.6: LLM-owned validation only; system-owned sections
    appended post-scrub.
    """
    attempt_prompt = prompt
    last_response = ""
    first_missing: list[str] = []
    first_dups: list[str] = []
    for attempt in (1, 2):
        try:
            last_response = _call_llm(
                config, attempt_prompt, task="digest", llm_profile=llm_profile
            )
        except Exception as exc:
            # SF-205: if the corrective re-call raises, preserve the original
            # validation context in the error chain for operator diagnosis.
            if attempt == 2 and (first_missing or first_dups):
                raise RuntimeError(
                    f"LLM corrective re-call raised after first response failed "
                    f"validation (missing={first_missing}, "
                    f"duplicate={first_dups}). Cause: {exc}"
                ) from exc
            raise
        missing, dups = _validate_body_sections(last_response, llm_owned_headings)
        if not missing and not dups:
            break
        if attempt == 2:
            # SF-205: format heading names in error as Markdown form `## <heading>`
            problems = []
            if missing:
                fm = [f"## {h}" for h in missing]
                problems.append(f"missing: {fm}")
            if dups:
                fd = [f"## {h}" for h in dups]
                problems.append(f"duplicate: {fd}")
            raise RuntimeError(
                f"LLM-returned body failed validation after retry: "
                f"{'; '.join(problems)}. Existing digest, if any, preserved."
            )
        # Capture first-response failure for context-preservation if retry raises.
        first_missing, first_dups = list(missing), list(dups)
        # Build corrective re-prompt — name headings in `## <heading>` form (SF-205)
        correction = []
        if missing:
            fm = [f"## {h}" for h in missing]
            correction.append(
                f"Your previous response was missing these required section(s): "
                f"{fm}. Please regenerate the full digest body with all "
                f"these sections (the system will append the "
                f"## {drawn_from_heading} and ## Trust Notes sections; you "
                f"should not emit them)."
            )
        if dups:
            fd = [f"## {h}" for h in dups]
            correction.append(
                f"Your previous response contained more than one occurrence "
                f"of: {fd}. Please emit each required section exactly once."
            )
        attempt_prompt = "\n\n".join(correction) + "\n\n" + prompt

    # Scrub any system-owned sections the LLM emitted (defensive per §9.5)
    scrubbed = last_response
    for system_heading in system_owned_headings:
        scrubbed = _strip_section(scrubbed, system_heading)

    # Compose system-owned blocks
    drawn_from_block = _compose_drawn_from(inputs, drawn_from_heading)
    trust_notes_block = _compose_trust_notes(
        include_flagged=include_flagged, counts=counts
    )

    # Assemble final body in spec section order
    # Strategy: scrubbed text already has LLM-owned sections in some order;
    # we append system-owned blocks at the deterministic positions per
    # section_order.  Simplest: for each heading in section_order, extract
    # its block from the scrubbed body (or use the system-rendered one).
    final_sections: list[str] = [f"# {title}", ""]
    for heading in section_order:
        if heading == drawn_from_heading:
            final_sections.append(drawn_from_block)
            final_sections.append("")
        elif heading == "Trust Notes":
            final_sections.append(trust_notes_block)
            final_sections.append("")
        else:
            block = _extract_section(scrubbed, heading)
            if block:
                final_sections.append(block.rstrip())
                final_sections.append("")
    return "\n".join(final_sections).rstrip() + "\n"


def _extract_section(body: str, heading: str) -> str:
    """Extract `## <heading>` section from body (heading + content up to next ##)."""
    positions = _heading_positions(body, heading)
    if not positions:
        return ""
    lines = body.splitlines()
    start = positions[0]
    # Find next any-## (fence-aware; SF-204: 0-3 leading spaces OK)
    in_fence = False
    fence_marker: Optional[str] = None
    any_heading = re.compile(r"^[ ]{0,3}##\s+\S")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```"):
                in_fence = True
                fence_marker = "```"
                continue
            if stripped.startswith("~~~"):
                in_fence = True
                fence_marker = "~~~"
                continue
        else:
            if stripped.startswith(fence_marker or "```"):
                in_fence = False
                fence_marker = None
            continue
        if any_heading.match(line):
            end = i
            break
    return "\n".join(lines[start:end])


# ---------------------------------------------------------------------------
# Public API: generate_daily_digest (spec §3.1)
# ---------------------------------------------------------------------------


def generate_daily_digest(
    config: FolioConfig,
    *,
    scope: str,
    date: Optional[str] = None,
    include_flagged: bool = False,
    llm_profile: Optional[str] = None,
) -> DigestResult:
    """Generate a daily digest for one engagement scope.

    Per spec §3.1 + §4 + §5 + §10. Caller should serialize concurrent
    invocations via folio.lock.library_lock (cli.py wrapper does this — SF-103).
    """
    try:
        client, engagement, engagement_root = _resolve_engagement_scope(
            config, scope
        )
    except ValueError as e:
        return DigestResult(
            status="error",
            digest_id=None,
            path=None,
            flagged_counts=DigestFlaggedCounts(),
            draws_from_count=0,
            message=f"Invalid scope '{scope}': {e}",
            exit_code=1,
        )

    if date is None:
        day_d = datetime.now().date()
    else:
        try:
            day_d = _parse_date(date)
        except ValueError as e:
            return DigestResult(
                status="error",
                digest_id=None,
                path=None,
                flagged_counts=DigestFlaggedCounts(),
                draws_from_count=0,
                message=str(e),
                exit_code=1,
            )
    day = day_d.isoformat()

    selection = _collect_daily_inputs(config, scope, day, include_flagged)

    if not selection.eligible:
        if selection.counts.excluded > 0 and not include_flagged:
            n = selection.counts.excluded
            noun = "input" if n == 1 else "inputs"
            message = (
                f"No eligible inputs for daily digest on {day}. "
                f"{n} source-backed {noun} excluded because review_status is "
                f"flagged. Use --include-flagged to widen the input set."
            )
        elif include_flagged:
            # SF-203: parenthetical THEN terminal period (matches spec §4)
            message = (
                f"No eligible inputs for daily digest on {day} in scope "
                f"{scope} (--include-flagged was honored; no flagged inputs "
                f"found either)."
            )
        else:
            message = (
                f"No eligible inputs for daily digest on {day} in scope {scope}."
            )
        return DigestResult(
            status="empty",
            digest_id=None,
            path=None,
            flagged_counts=selection.counts,
            draws_from_count=0,
            message=message,
            exit_code=0,
        )

    # Compute identity
    digest_id = _compute_digest_id(
        client, derive_engagement_short(engagement) or engagement,
        _compact_period(day_d), "daily-digest",
    )
    path = _compute_digest_path(engagement_root, digest_id)

    # Rerun handling + corruption fallback per §10.4
    existing_fm = _load_existing_digest(path)
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    reg_data = registry.load_registry(registry_path)
    file_in_registry = digest_id in reg_data.get("decks", {})

    if existing_fm is not None:
        existing_version = existing_fm.get("version")
        if isinstance(existing_version, int):
            new_version = existing_version + 1
        else:
            try:
                new_version = int(existing_version) + 1
            except (TypeError, ValueError):
                logger.warning(
                    "↷ Existing digest at %s has non-integer version; "
                    "treating as fresh write.",
                    path,
                )
                new_version = 1
        created = existing_fm.get("created") or day
        status: Literal["written", "rerun", "empty", "error"] = "rerun"

        # B-201 / SF-4: orphan self-heal — file exists with valid frontmatter
        # but registry row missing. Register BEFORE the LLM call so an
        # LLM failure preserves the now-recovered registry row instead of
        # leaving it orphaned for another rerun cycle. (Spec §10.4 row 5.)
        if not file_in_registry:
            logger.warning(
                "↷ Orphan digest detected at %s; self-healing registry row "
                "before LLM call (spec §10.4).",
                path,
            )
            try:
                _register_digest(
                    config, digest_id, path, existing_fm,
                    scope_client=client, scope_engagement=engagement,
                )
            except Exception as e:
                # Self-heal failure is non-fatal; downstream final upsert
                # will retry. Log and continue.
                logger.warning(
                    "↷ Orphan self-heal upsert failed for %s: %s; "
                    "continuing with rerun.", digest_id, e,
                )
    elif path.exists():
        # File exists but couldn't load frontmatter — corrupt YAML per §10.4
        logger.warning(
            "↷ Existing digest at %s has malformed frontmatter; "
            "treating as fresh write.",
            path,
        )
        new_version = 1
        created = day
        status = "written"
    else:
        new_version = 1
        created = day
        status = "written"
        # SF-201: stale-registry case (registry row exists but file absent)
        if file_in_registry:
            logger.warning(
                "↷ Registry referenced missing file at %s; regenerating.",
                path,
            )

    # Build prompt + LLM call + validation
    title = f"Daily Digest — {day}"
    prompt = _build_daily_prompt(
        selection.eligible, day, selection.counts, include_flagged,
        config.library_root.resolve(),
    )

    try:
        body = _build_body_with_validation_retry(
            config, prompt, selection.eligible,
            llm_owned_headings=_DAILY_LLM_OWNED_HEADINGS,
            system_owned_headings=_DAILY_SYSTEM_OWNED,
            drawn_from_heading="Documents Drawn From",
            section_order=_DAILY_SECTION_ORDER,
            include_flagged=include_flagged,
            counts=selection.counts,
            title=title,
            llm_profile=llm_profile,
        )
    except Exception as e:
        return DigestResult(
            status="error",
            digest_id=digest_id,
            path=path,
            flagged_counts=selection.counts,
            draws_from_count=len(selection.eligible),
            message=(
                f"LLM synthesis failed for daily digest on {day} in scope "
                f"{scope} (existing digest, if any, preserved). Cause: {e}"
            ),
            exit_code=1,
        )

    # Compose frontmatter
    fm: dict = {
        "id": digest_id,
        "title": title,
        "type": "analysis",
        "subtype": "digest",
        "status": "complete",
        "authority": "analyzed",
        "curation_level": "L1",
        "review_status": "flagged",
        "review_flags": ["synthesis_requires_review"],
        "extraction_confidence": None,
        "client": client,
        "engagement": engagement,
        "tags": ["digest", "analysis"],
        "digest_period": day,
        "digest_type": "daily",
        "draws_from": [e.id for e in selection.eligible],
        "created": created,
        "modified": day,
        "version": new_version,
    }

    content = _render_frontmatter(fm) + "\n\n" + body

    try:
        _atomic_write(path, content)
    except OSError as e:
        return DigestResult(
            status="error",
            digest_id=digest_id,
            path=path,
            flagged_counts=selection.counts,
            draws_from_count=len(selection.eligible),
            message=f"Atomic write failed at {path}: {e}",
            exit_code=1,
        )

    try:
        _register_digest(
            config, digest_id, path, fm,
            scope_client=client, scope_engagement=engagement,
        )
    except Exception as e:
        return DigestResult(
            status="error",
            digest_id=digest_id,
            path=path,
            flagged_counts=selection.counts,
            draws_from_count=len(selection.eligible),
            message=(
                f"Registry upsert failed for {digest_id}: {e}. Run "
                f"`folio digest {scope}` again to self-heal (the rerun "
                f"re-registers any orphan digest, see §10.4). If the "
                f"registry itself is corrupt, run `folio status --refresh` "
                f"to trigger rebuild_registry."
            ),
            exit_code=1,
        )

    if status == "rerun":
        message = (
            f"Updated daily digest: {digest_id} "
            f"(version {new_version - 1} → {new_version})"
        )
    else:
        message = f"Wrote daily digest: {digest_id}"

    return DigestResult(
        status=status,
        digest_id=digest_id,
        path=path,
        flagged_counts=selection.counts,
        draws_from_count=len(selection.eligible),
        message=message,
        exit_code=0,
    )


def generate_weekly_digest(
    config: FolioConfig,
    *,
    scope: str,
    date: Optional[str] = None,
    include_flagged: bool = False,  # accepted, no-op per spec §4 + §12
    llm_profile: Optional[str] = None,
) -> DigestResult:
    """Generate a weekly digest from existing daily digests in scope.

    Per spec §3.1 + §4 + §6.
    """
    try:
        client, engagement, engagement_root = _resolve_engagement_scope(
            config, scope
        )
    except ValueError as e:
        return DigestResult(
            status="error",
            digest_id=None,
            path=None,
            flagged_counts=DigestFlaggedCounts(),
            draws_from_count=0,
            message=f"Invalid scope '{scope}': {e}",
            exit_code=1,
        )

    if date is None:
        anchor_d = datetime.now().date()
    else:
        try:
            anchor_d = _parse_date(date)
        except ValueError as e:
            return DigestResult(
                status="error",
                digest_id=None,
                path=None,
                flagged_counts=DigestFlaggedCounts(),
                draws_from_count=0,
                message=str(e),
                exit_code=1,
            )
    week_monday = _iso_week_monday(anchor_d)

    daily_inputs = _collect_weekly_inputs(config, scope, week_monday)

    if not daily_inputs:
        return DigestResult(
            status="empty",
            digest_id=None,
            path=None,
            flagged_counts=DigestFlaggedCounts(),
            draws_from_count=0,
            message=(
                f"No daily digests found for ISO week starting "
                f"{week_monday.isoformat()} in scope {scope}."
            ),
            exit_code=0,
        )

    digest_id = _compute_digest_id(
        client, derive_engagement_short(engagement) or engagement,
        _compact_period(week_monday), "weekly-digest",
    )
    path = _compute_digest_path(engagement_root, digest_id)

    existing_fm = _load_existing_digest(path)
    library_root = config.library_root.resolve()
    registry_path = library_root / "registry.json"
    reg_data = registry.load_registry(registry_path)
    file_in_registry = digest_id in reg_data.get("decks", {})

    if existing_fm is not None:
        existing_version = existing_fm.get("version")
        if isinstance(existing_version, int):
            new_version = existing_version + 1
        else:
            try:
                new_version = int(existing_version) + 1
            except (TypeError, ValueError):
                logger.warning(
                    "↷ Existing weekly digest at %s has non-integer version; "
                    "treating as fresh write.",
                    path,
                )
                new_version = 1
        created = existing_fm.get("created") or week_monday.isoformat()
        status: Literal["written", "rerun", "empty", "error"] = "rerun"

        # B-201 / SF-4: orphan self-heal pre-LLM (same as daily; spec §10.4 row 5)
        if not file_in_registry:
            logger.warning(
                "↷ Orphan weekly digest detected at %s; self-healing registry "
                "row before LLM call (spec §10.4).",
                path,
            )
            try:
                _register_digest(
                    config, digest_id, path, existing_fm,
                    scope_client=client, scope_engagement=engagement,
                )
            except Exception as e:
                logger.warning(
                    "↷ Orphan self-heal upsert failed for %s: %s; "
                    "continuing with rerun.", digest_id, e,
                )
    elif path.exists():
        logger.warning(
            "↷ Existing weekly digest at %s has malformed frontmatter; "
            "treating as fresh write.",
            path,
        )
        new_version = 1
        created = week_monday.isoformat()
        status = "written"
    else:
        new_version = 1
        created = week_monday.isoformat()
        status = "written"
        # SF-201: stale-registry warning (weekly)
        if file_in_registry:
            logger.warning(
                "↷ Registry referenced missing weekly digest file at %s; "
                "regenerating.",
                path,
            )

    title = f"Weekly Digest — week of {week_monday.isoformat()}"
    prompt = _build_weekly_prompt(
        daily_inputs, week_monday, config.library_root.resolve()
    )

    try:
        body = _build_body_with_validation_retry(
            config, prompt, daily_inputs,
            llm_owned_headings=_WEEKLY_LLM_OWNED_HEADINGS,
            system_owned_headings=_WEEKLY_SYSTEM_OWNED,
            drawn_from_heading="Daily Digests Drawn From",
            section_order=_WEEKLY_SECTION_ORDER,
            include_flagged=False,  # weekly always renders the no-exclusion branch
            counts=DigestFlaggedCounts(),
            title=title,
            llm_profile=llm_profile,
        )
    except Exception as e:
        return DigestResult(
            status="error",
            digest_id=digest_id,
            path=path,
            flagged_counts=DigestFlaggedCounts(),
            draws_from_count=len(daily_inputs),
            message=(
                f"LLM synthesis failed for weekly digest on "
                f"{week_monday.isoformat()} in scope {scope} (existing "
                f"digest, if any, preserved). Cause: {e}"
            ),
            exit_code=1,
        )

    fm: dict = {
        "id": digest_id,
        "title": title,
        "type": "analysis",
        "subtype": "digest",
        "status": "complete",
        "authority": "analyzed",
        "curation_level": "L1",
        "review_status": "flagged",
        "review_flags": ["synthesis_requires_review"],
        "extraction_confidence": None,
        "client": client,
        "engagement": engagement,
        "tags": ["digest", "analysis"],
        "digest_period": week_monday.isoformat(),
        "digest_type": "weekly",
        "draws_from": [e.id for e in daily_inputs],
        "created": created,
        "modified": week_monday.isoformat(),
        "version": new_version,
    }

    content = _render_frontmatter(fm) + "\n\n" + body

    try:
        _atomic_write(path, content)
    except OSError as e:
        return DigestResult(
            status="error",
            digest_id=digest_id,
            path=path,
            flagged_counts=DigestFlaggedCounts(),
            draws_from_count=len(daily_inputs),
            message=f"Atomic write failed at {path}: {e}",
            exit_code=1,
        )

    try:
        _register_digest(
            config, digest_id, path, fm,
            scope_client=client, scope_engagement=engagement,
        )
    except Exception as e:
        return DigestResult(
            status="error",
            digest_id=digest_id,
            path=path,
            flagged_counts=DigestFlaggedCounts(),
            draws_from_count=len(daily_inputs),
            message=(
                f"Registry upsert failed for {digest_id}: {e}. Run "
                f"`folio digest {scope} --week` again to self-heal."
            ),
            exit_code=1,
        )

    if status == "rerun":
        message = (
            f"Updated weekly digest: {digest_id} "
            f"(version {new_version - 1} → {new_version})"
        )
    else:
        message = f"Wrote weekly digest: {digest_id}"

    return DigestResult(
        status=status,
        digest_id=digest_id,
        path=path,
        flagged_counts=DigestFlaggedCounts(),
        draws_from_count=len(daily_inputs),
        message=message,
        exit_code=0,
    )
