"""Tests for folio.digest module (spec v1.2 §13.1 + §13.3)."""

from __future__ import annotations

import ast
import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from folio.cli import cli
from folio.config import FolioConfig
from folio.digest import (
    DailyInputSelection,
    DigestFlaggedCounts,
    DigestResult,
    _activity_date,
    _atomic_write,
    _collect_daily_inputs,
    _collect_weekly_inputs,
    _compact_period,
    _compose_drawn_from,
    _compose_trust_notes,
    _compute_digest_id,
    _compute_digest_path,
    _heading_positions,
    _iso_week_monday,
    _load_existing_digest,
    _matches_scope,
    _parse_date,
    _resolve_engagement_scope,
    _strip_section,
    _validate_body_sections,
    generate_daily_digest,
    generate_weekly_digest,
)
from folio.tracking import registry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _config(library_root: Path) -> FolioConfig:
    folio_yaml = library_root / "folio.yaml"
    folio_yaml.write_text(f"library_root: {library_root}\n")
    return FolioConfig.load(folio_yaml)


def _write_registry(library_root: Path, decks: dict[str, dict]) -> None:
    payload = {
        "_schema_version": 2,
        "updated_at": "2026-04-01T00:00:00Z",
        "decks": decks,
    }
    (library_root / "registry.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _evidence_entry(
    note_id: str,
    md_path: str,
    *,
    modified: str = "2026-04-04",
    review_status: str | None = None,
    title: str | None = None,
) -> dict:
    e = {
        "id": note_id,
        "title": title or note_id,
        "type": "evidence",
        "markdown_path": md_path,
        "deck_dir": str(Path(md_path).parent).replace("\\", "/"),
        "client": "ClientA",
        "engagement": "DD_Q1_2026",
        "modified": modified,
        "source_relative_path": f"sources/{note_id}.pdf",
        "source_hash": "sha256:abc",
        "version": 1,
        "converted": modified,
    }
    if review_status is not None:
        e["review_status"] = review_status
    return e


def _write_evidence_md(
    library_root: Path,
    md_path: str,
    *,
    note_id: str,
    review_status: str | None = None,
    body: str = "Evidence body.",
) -> Path:
    full = library_root / md_path
    full.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": note_id,
        "title": note_id,
        "type": "evidence",
        "source": f"sources/{note_id}.pdf",
        "source_hash": "sha256:abc",
    }
    if review_status is not None:
        fm["review_status"] = review_status
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    full.write_text(f"---\n{yaml_str}---\n\n{body}\n", encoding="utf-8")
    return full


def _setup_engagement(library_root: Path) -> Path:
    engagement_root = library_root / "ClientA" / "DD_Q1_2026"
    engagement_root.mkdir(parents=True)
    (engagement_root / "evidence").mkdir()
    return engagement_root


# A canned valid LLM body (4 LLM-owned daily headings).
_VALID_DAILY_BODY = """## Summary

Daily synthesis text.

## What Moved Today

- Item A
- Item B

## Emerging Risks / Open Questions

- Risk 1

## Suggested Follow-Ups

- Follow up X
"""

_VALID_WEEKLY_BODY = """## Weekly Summary

Weekly synthesis text.

## What Changed This Week

- Change A

## Cross-Cutting Themes

- Theme 1

## Decisions / Risks To Track

- Decision X

## Next Week Lookahead

- Next steps
"""


# ---------------------------------------------------------------------------
# DG-1..DG-4: identity + week helpers
# ---------------------------------------------------------------------------


def test_compute_digest_id_daily():
    """DG-1"""
    digest_id = _compute_digest_id(
        "usbank", "techresilience2026", "20260404", "daily-digest"
    )
    assert digest_id == "usbank_techresilience2026_analysis_20260404_daily-digest"


def test_compute_digest_id_weekly():
    """DG-2"""
    digest_id = _compute_digest_id(
        "usbank", "techresilience2026", "20260330", "weekly-digest"
    )
    assert digest_id == "usbank_techresilience2026_analysis_20260330_weekly-digest"


def test_compute_digest_path_layout(tmp_path):
    """DG-3"""
    eng_root = tmp_path / "client" / "engagement"
    digest_id = "client_engagement_analysis_20260404_daily-digest"
    p = _compute_digest_path(eng_root, digest_id)
    assert p == eng_root / "analysis" / "digests" / digest_id / f"{digest_id}.md"


def test_iso_week_monday():
    """DG-4"""
    assert _iso_week_monday(date(2026, 4, 4)) == date(2026, 3, 30)  # Sat → Mon
    assert _iso_week_monday(date(2026, 3, 30)) == date(2026, 3, 30)  # Mon → same
    assert _iso_week_monday(date(2026, 4, 5)) == date(2026, 3, 30)  # Sun → Mon


def test_compact_period():
    assert _compact_period(date(2026, 4, 4)) == "20260404"


# ---------------------------------------------------------------------------
# DG-5..DG-7: scope resolution
# ---------------------------------------------------------------------------


def test_resolve_engagement_scope_single(tmp_path):
    """DG-5 (MN-3): also asserts engagement_root == library_root/<client>/<engagement>"""
    engagement_root = _setup_engagement(tmp_path)
    config = _config(tmp_path)
    client, engagement, root = _resolve_engagement_scope(config, "ClientA/DD_Q1_2026")
    assert client == "ClientA"
    assert engagement == "DD_Q1_2026"
    assert root == engagement_root.resolve()


def test_resolve_engagement_scope_multi_rejected(tmp_path):
    """DG-6: too few path components"""
    config = _config(tmp_path)
    with pytest.raises(ValueError, match="must resolve under one engagement"):
        _resolve_engagement_scope(config, "ClientA")


def test_resolve_engagement_scope_outside_library_rejected(tmp_path):
    """DG-7"""
    config = _config(tmp_path)
    with pytest.raises(ValueError, match="outside library_root"):
        _resolve_engagement_scope(config, "../../../etc")


# ---------------------------------------------------------------------------
# DG-8..DG-14: _collect_daily_inputs predicate
# ---------------------------------------------------------------------------


def test_collect_daily_inputs_filters_by_scope(tmp_path):
    """DG-8"""
    _setup_engagement(tmp_path)
    (tmp_path / "OtherClient").mkdir()
    _write_evidence_md(
        tmp_path, "ClientA/DD_Q1_2026/evidence/in.md", note_id="in"
    )
    _write_evidence_md(
        tmp_path, "OtherClient/evidence/out.md", note_id="out"
    )
    _write_registry(tmp_path, {
        "in": _evidence_entry("in", "ClientA/DD_Q1_2026/evidence/in.md"),
        "out": _evidence_entry("out", "OtherClient/evidence/out.md"),
    })
    config = _config(tmp_path)
    sel = _collect_daily_inputs(config, "ClientA/DD_Q1_2026", "2026-04-04", False)
    assert [e.id for e in sel.eligible] == ["in"]


def test_collect_daily_inputs_filters_by_type(tmp_path):
    """DG-9 — context and analysis are excluded"""
    _setup_engagement(tmp_path)
    _write_evidence_md(
        tmp_path, "ClientA/DD_Q1_2026/evidence/ev.md", note_id="ev"
    )
    decks = {
        "ev": _evidence_entry("ev", "ClientA/DD_Q1_2026/evidence/ev.md"),
        "ctx": {
            "id": "ctx", "title": "ctx", "type": "context",
            "markdown_path": "ClientA/DD_Q1_2026/context/ctx.md",
            "deck_dir": "ClientA/DD_Q1_2026/context",
            "modified": "2026-04-04",
        },
        "anal": {
            "id": "anal", "title": "anal", "type": "analysis", "subtype": "digest",
            "markdown_path": "ClientA/DD_Q1_2026/analysis/anal.md",
            "deck_dir": "ClientA/DD_Q1_2026/analysis",
            "modified": "2026-04-04",
        },
    }
    _write_registry(tmp_path, decks)
    config = _config(tmp_path)
    sel = _collect_daily_inputs(config, "ClientA/DD_Q1_2026", "2026-04-04", False)
    assert [e.id for e in sel.eligible] == ["ev"]


def test_collect_daily_inputs_uses_modified_then_converted(tmp_path):
    """DG-10"""
    assert _activity_date("2026-04-04", None) == "2026-04-04"
    assert _activity_date(None, "2026-04-03") == "2026-04-03"
    assert _activity_date(None, None) is None
    assert _activity_date("", "2026-04-03") == "2026-04-03"


def test_collect_daily_inputs_excludes_flagged_by_default(tmp_path):
    """DG-11"""
    _setup_engagement(tmp_path)
    _write_evidence_md(
        tmp_path, "ClientA/DD_Q1_2026/evidence/clean.md",
        note_id="clean",
    )
    _write_evidence_md(
        tmp_path, "ClientA/DD_Q1_2026/evidence/flagged.md",
        note_id="flagged", review_status="flagged",
    )
    _write_registry(tmp_path, {
        "clean": _evidence_entry("clean", "ClientA/DD_Q1_2026/evidence/clean.md"),
        "flagged": _evidence_entry(
            "flagged", "ClientA/DD_Q1_2026/evidence/flagged.md",
            review_status="flagged",
        ),
    })
    config = _config(tmp_path)
    sel = _collect_daily_inputs(config, "ClientA/DD_Q1_2026", "2026-04-04", False)
    assert [e.id for e in sel.eligible] == ["clean"]
    assert sel.counts.excluded == 1
    assert sel.counts.included == 0


def test_collect_daily_inputs_missing_frontmatter_fail_open(tmp_path):
    """DG-11b — SF-3: file present but unparseable → not flagged, eligible"""
    _setup_engagement(tmp_path)
    md = tmp_path / "ClientA/DD_Q1_2026/evidence/orphan.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("no frontmatter here\n", encoding="utf-8")
    _write_registry(tmp_path, {
        "orphan": _evidence_entry("orphan", "ClientA/DD_Q1_2026/evidence/orphan.md"),
    })
    config = _config(tmp_path)
    sel = _collect_daily_inputs(config, "ClientA/DD_Q1_2026", "2026-04-04", False)
    assert [e.id for e in sel.eligible] == ["orphan"]
    assert sel.counts.excluded == 0


def test_collect_daily_inputs_non_dict_frontmatter_fail_open(tmp_path):
    """DG-11c — SF-206: non-dict frontmatter (e.g., a YAML list) → fail-open"""
    _setup_engagement(tmp_path)
    md = tmp_path / "ClientA/DD_Q1_2026/evidence/listfm.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("---\n- item1\n- item2\n---\nbody\n", encoding="utf-8")
    _write_registry(tmp_path, {
        "listfm": _evidence_entry("listfm", "ClientA/DD_Q1_2026/evidence/listfm.md"),
    })
    config = _config(tmp_path)
    sel = _collect_daily_inputs(config, "ClientA/DD_Q1_2026", "2026-04-04", False)
    assert [e.id for e in sel.eligible] == ["listfm"]
    assert sel.counts.excluded == 0


def test_collect_daily_inputs_includes_flagged_with_flag(tmp_path):
    """DG-12"""
    _setup_engagement(tmp_path)
    _write_evidence_md(
        tmp_path, "ClientA/DD_Q1_2026/evidence/flagged.md",
        note_id="flagged", review_status="flagged",
    )
    _write_registry(tmp_path, {
        "flagged": _evidence_entry(
            "flagged", "ClientA/DD_Q1_2026/evidence/flagged.md",
            review_status="flagged",
        ),
    })
    config = _config(tmp_path)
    sel = _collect_daily_inputs(config, "ClientA/DD_Q1_2026", "2026-04-04", True)
    assert [e.id for e in sel.eligible] == ["flagged"]
    assert sel.counts.excluded == 0
    assert sel.counts.included == 1


def test_collect_daily_inputs_includes_flagged_count_zero_on_clean_scope(tmp_path):
    """DG-12b — SF-11"""
    _setup_engagement(tmp_path)
    _write_evidence_md(tmp_path, "ClientA/DD_Q1_2026/evidence/clean.md", note_id="clean")
    _write_registry(tmp_path, {
        "clean": _evidence_entry("clean", "ClientA/DD_Q1_2026/evidence/clean.md"),
    })
    config = _config(tmp_path)
    sel = _collect_daily_inputs(config, "ClientA/DD_Q1_2026", "2026-04-04", True)
    assert sel.counts.excluded == 0
    assert sel.counts.included == 0


def test_collect_daily_inputs_iso_timestamp_handled():
    """DG-13"""
    assert _activity_date("2026-04-04T13:00:00Z", None) == "2026-04-04"


def test_collect_daily_inputs_timezone_offset_literal_match():
    """DG-13b — SF-5: literal split, no UTC conversion"""
    assert _activity_date("2026-04-04T23:00:00-05:00", None) == "2026-04-04"


def test_collect_daily_inputs_no_mtime_inference(tmp_path):
    """DG-14 — SF-206: filesystem mtime is never read; only frontmatter modified/converted"""
    _setup_engagement(tmp_path)
    md = tmp_path / "ClientA/DD_Q1_2026/evidence/no-modified.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": "no-modified", "title": "no-modified", "type": "evidence",
        "source": "sources/x.pdf", "source_hash": "sha256:abc",
    }
    md.write_text(
        f"---\n{yaml.dump(fm, sort_keys=False)}---\nbody\n", encoding="utf-8"
    )
    # Touch file so mtime is "today"
    import os as _os
    now_ts = datetime(2026, 4, 4).timestamp()
    _os.utime(md, (now_ts, now_ts))

    # Registry entry has neither modified nor converted
    decks = {
        "no-modified": {
            "id": "no-modified", "title": "no-modified", "type": "evidence",
            "markdown_path": "ClientA/DD_Q1_2026/evidence/no-modified.md",
            "deck_dir": "ClientA/DD_Q1_2026/evidence",
            "client": "ClientA", "engagement": "DD_Q1_2026",
            "source_relative_path": "sources/x.pdf",
            "source_hash": "sha256:abc",
            "version": 1,
            # NO modified, NO converted
        },
    }
    _write_registry(tmp_path, decks)
    config = _config(tmp_path)
    sel = _collect_daily_inputs(config, "ClientA/DD_Q1_2026", "2026-04-04", False)
    # Without frontmatter modified/converted, the input is INELIGIBLE — even if
    # filesystem mtime says today. Predicate uses frontmatter only (design §5).
    assert sel.eligible == []


# ---------------------------------------------------------------------------
# DG-15..DG-16: weekly discovery
# ---------------------------------------------------------------------------


def test_collect_weekly_inputs_iso_week_window(tmp_path):
    """DG-15 — week starting Mon 2026-03-30 includes Mon-Sun, excludes outside"""
    _setup_engagement(tmp_path)
    digest_dir = tmp_path / "ClientA/DD_Q1_2026/analysis/digests"
    digest_dir.mkdir(parents=True, exist_ok=True)

    decks = {}
    for d, in_week in [
        ("2026-03-30", True),  # Monday — in
        ("2026-04-04", True),  # Saturday — in
        ("2026-04-05", True),  # Sunday — in
        ("2026-04-06", False),  # Next Monday — out
        ("2026-03-29", False),  # Prior Sunday — out
    ]:
        compact = d.replace("-", "")
        did = f"ClientA_DD_Q1_2026_analysis_{compact}_daily-digest"
        sub = digest_dir / did
        sub.mkdir()
        fm = {
            "id": did, "type": "analysis", "subtype": "digest",
            "digest_type": "daily", "digest_period": d,
        }
        (sub / f"{did}.md").write_text(
            f"---\n{yaml.dump(fm)}---\n\nbody\n", encoding="utf-8"
        )
        decks[did] = {
            "id": did, "title": did, "type": "analysis", "subtype": "digest",
            "markdown_path": f"ClientA/DD_Q1_2026/analysis/digests/{did}/{did}.md",
            "deck_dir": f"ClientA/DD_Q1_2026/analysis/digests/{did}",
        }
    _write_registry(tmp_path, decks)
    config = _config(tmp_path)
    eligible = _collect_weekly_inputs(config, "ClientA/DD_Q1_2026", date(2026, 3, 30))
    in_ids = sorted([e.id for e in eligible])
    assert len(in_ids) == 3


def test_collect_weekly_inputs_requires_subtype_digest_type(tmp_path):
    """DG-16"""
    _setup_engagement(tmp_path)
    digest_dir = tmp_path / "ClientA/DD_Q1_2026/analysis/digests"
    digest_dir.mkdir(parents=True, exist_ok=True)
    sub = digest_dir / "wrong"
    sub.mkdir()
    # Wrong subtype
    fm = {"id": "wrong", "type": "analysis", "subtype": "synthesis",
          "digest_type": "daily", "digest_period": "2026-03-30"}
    (sub / "wrong.md").write_text(
        f"---\n{yaml.dump(fm)}---\nbody\n", encoding="utf-8"
    )
    decks = {
        "wrong": {
            "id": "wrong", "title": "wrong", "type": "analysis", "subtype": "synthesis",
            "markdown_path": "ClientA/DD_Q1_2026/analysis/digests/wrong/wrong.md",
            "deck_dir": "ClientA/DD_Q1_2026/analysis/digests/wrong",
        },
    }
    _write_registry(tmp_path, decks)
    config = _config(tmp_path)
    eligible = _collect_weekly_inputs(config, "ClientA/DD_Q1_2026", date(2026, 3, 30))
    assert eligible == []


# ---------------------------------------------------------------------------
# DG-17..DG-22: generate_daily_digest behavior
# ---------------------------------------------------------------------------


def _setup_one_input(tmp_path: Path, modified: str = "2026-04-04") -> FolioConfig:
    _setup_engagement(tmp_path)
    _write_evidence_md(tmp_path, "ClientA/DD_Q1_2026/evidence/in.md", note_id="in")
    _write_registry(tmp_path, {
        "in": _evidence_entry(
            "in", "ClientA/DD_Q1_2026/evidence/in.md", modified=modified,
        ),
    })
    return _config(tmp_path)


def test_generate_daily_digest_writes_frontmatter(tmp_path):
    """DG-17"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert result.status == "written"
    assert result.exit_code == 0
    text = result.path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1])
    assert fm["type"] == "analysis"
    assert fm["subtype"] == "digest"
    assert fm["digest_type"] == "daily"
    assert fm["digest_period"] == "2026-04-04"
    assert fm["draws_from"] == ["in"]
    assert fm["version"] == 1
    # MUST omit source-related fields
    for omit in ("source", "source_hash", "source_type", "source_transcript"):
        assert omit not in fm


def test_generate_daily_digest_registers_in_registry(tmp_path):
    """DG-18 (PR-9): asserts source-less field absence + extraction_confidence shape"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    reg = registry.load_registry(tmp_path / "registry.json")
    assert result.digest_id in reg["decks"]
    entry = reg["decks"][result.digest_id]
    assert entry["type"] == "analysis"
    assert entry["subtype"] == "digest"
    assert entry["review_status"] == "flagged"
    assert entry["review_flags"] == ["synthesis_requires_review"]
    # Source-less field absence assertions
    assert "source_relative_path" not in entry
    assert "source_hash" not in entry
    assert "source_type" not in entry
    assert "source_transcript" not in entry
    # extraction_confidence: None → omitted from to_dict()
    assert "extraction_confidence" not in entry


def test_generate_daily_digest_rerun_increments_version(tmp_path):
    """DG-19"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        r1 = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
        r2 = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert r1.status == "written"
    assert r2.status == "rerun"
    fm = yaml.safe_load(r2.path.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm["version"] == 2


def test_generate_daily_digest_rerun_stale_registry_file_absent(tmp_path, caplog):
    """DG-19c — SF-201: registry has digest row, file absent → fresh write + warning"""
    from folio.digest import _compute_digest_id
    from folio.naming import derive_engagement_short
    config = _setup_one_input(tmp_path)
    # Pre-seed registry with a digest row that has no corresponding file
    digest_id = _compute_digest_id(
        "ClientA", derive_engagement_short("DD_Q1_2026") or "DD_Q1_2026",
        "20260404", "daily-digest",
    )
    reg_path = tmp_path / "registry.json"
    reg = json.loads(reg_path.read_text())
    reg["decks"][digest_id] = {
        "id": digest_id, "title": digest_id, "type": "analysis", "subtype": "digest",
        "markdown_path": (
            f"ClientA/DD_Q1_2026/analysis/digests/{digest_id}/{digest_id}.md"
        ),
        "deck_dir": f"ClientA/DD_Q1_2026/analysis/digests/{digest_id}",
        "client": "ClientA", "engagement": "DD_Q1_2026",
    }
    reg_path.write_text(json.dumps(reg))
    # File does NOT exist on disk

    import logging
    with caplog.at_level(logging.WARNING, logger="folio.digest"):
        with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
            result = generate_daily_digest(
                config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
            )
    assert result.status == "written"  # fresh write per §10.4
    fm = yaml.safe_load(result.path.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm["version"] == 1
    # Stale-registry warning should have been logged
    assert any(
        "Registry referenced missing file" in record.message
        for record in caplog.records
    )


def test_generate_daily_digest_rerun_corrupt_yaml_falls_back_to_v1(tmp_path):
    """DG-19b — SF-6 / §10.4"""
    from folio.digest import _compute_digest_id
    from folio.naming import derive_engagement_short
    config = _setup_one_input(tmp_path)
    # Pre-create a path with malformed YAML
    digest_id = _compute_digest_id(
        "ClientA", derive_engagement_short("DD_Q1_2026") or "DD_Q1_2026",
        "20260404", "daily-digest",
    )
    p = (
        tmp_path / "ClientA/DD_Q1_2026/analysis/digests" / digest_id /
        f"{digest_id}.md"
    )
    p.parent.mkdir(parents=True)
    p.write_text("---\nthis is: : malformed: yaml: \n---\nbody\n", encoding="utf-8")
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert result.status == "written"  # treated as fresh write
    fm = yaml.safe_load(result.path.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm["version"] == 1


def test_generate_daily_digest_llm_failure_preserves_existing(tmp_path):
    """DG-20"""
    config = _setup_one_input(tmp_path)
    # First successful run
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        r1 = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    original_text = r1.path.read_text(encoding="utf-8")

    # Second run: LLM raises
    with patch("folio.digest._call_llm", side_effect=RuntimeError("boom")):
        r2 = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert r2.status == "error"
    assert r2.exit_code != 0
    assert r1.path.read_text(encoding="utf-8") == original_text


def test_generate_daily_digest_orphan_self_heal_pre_llm(tmp_path, caplog):
    """DG-20c — B-201: file exists, registry row absent → self-heal BEFORE LLM call.

    Reproduction: pre-create the digest file with valid frontmatter, ensure
    registry row is absent, patch _call_llm to raise. Spec §10.4 row 5 says
    the orphan must be re-registered BEFORE the LLM call so the registry row
    survives even if the LLM fails.
    """
    from folio.digest import _compute_digest_id
    from folio.naming import derive_engagement_short
    config = _setup_one_input(tmp_path)

    # Pre-create the digest file with valid frontmatter (orphan)
    digest_id = _compute_digest_id(
        "ClientA", derive_engagement_short("DD_Q1_2026") or "DD_Q1_2026",
        "20260404", "daily-digest",
    )
    p = (
        tmp_path / "ClientA/DD_Q1_2026/analysis/digests" / digest_id /
        f"{digest_id}.md"
    )
    p.parent.mkdir(parents=True)
    fm = {
        "id": digest_id, "title": "Daily Digest — 2026-04-04",
        "type": "analysis", "subtype": "digest",
        "status": "complete", "authority": "analyzed",
        "curation_level": "L1", "review_status": "flagged",
        "review_flags": ["synthesis_requires_review"],
        "client": "ClientA", "engagement": "DD_Q1_2026",
        "digest_period": "2026-04-04", "digest_type": "daily",
        "draws_from": ["in"],
        "created": "2026-04-04", "modified": "2026-04-04", "version": 5,
    }
    p.write_text(
        f"---\n{yaml.dump(fm, sort_keys=False)}---\n\n## Summary\n\nbody\n",
        encoding="utf-8",
    )

    # Registry has NO entry for the digest
    reg_path = tmp_path / "registry.json"
    reg = json.loads(reg_path.read_text())
    assert digest_id not in reg["decks"]

    # Patch LLM to raise — should NOT prevent the self-heal
    import logging
    with caplog.at_level(logging.WARNING, logger="folio.digest"):
        with patch("folio.digest._call_llm", side_effect=RuntimeError("LLM down")):
            result = generate_daily_digest(
                config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
            )
    assert result.status == "error"
    # Critical assertion: registry row was self-healed BEFORE the LLM call
    reg_after = json.loads((tmp_path / "registry.json").read_text())
    assert digest_id in reg_after["decks"], (
        "Orphan should have been self-healed before LLM call (B-201 fix)"
    )
    # Warning should have been logged
    assert any(
        "Orphan digest detected" in record.message
        for record in caplog.records
    )


def test_generate_daily_digest_atomic_write_failure_no_orphan_tempfile(tmp_path):
    """DG-20b — SF-101: pin mock to tmp.write specifically"""
    config = _setup_one_input(tmp_path)

    # Patch the NamedTemporaryFile helper inside _atomic_write so the write fails
    real_namedtempfile = __import__("tempfile").NamedTemporaryFile

    def mock_namedtempfile(*args, **kwargs):
        f = real_namedtempfile(*args, **kwargs)
        original_write = f.write
        def failing_write(data):
            # Touch the file briefly via close+reopen pattern not needed —
            # the tempfile already exists on disk after creation
            raise OSError("disk full simulation")
        f.write = failing_write
        return f

    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        with patch("folio.digest.tempfile.NamedTemporaryFile",
                   side_effect=mock_namedtempfile):
            result = generate_daily_digest(
                config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
            )
    assert result.status == "error"
    # No orphan .tmp files in the digest folder
    digest_dir = tmp_path / "ClientA/DD_Q1_2026/analysis/digests"
    if digest_dir.exists():
        orphans = list(digest_dir.rglob("*.tmp"))
        assert orphans == [], f"Found orphan tempfiles: {orphans}"


def test_generate_daily_digest_empty_returns_zero_exit(tmp_path):
    """DG-21"""
    _setup_engagement(tmp_path)
    _write_registry(tmp_path, {})
    config = _config(tmp_path)
    result = generate_daily_digest(
        config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
    )
    assert result.status == "empty"
    assert result.exit_code == 0
    assert "No eligible inputs" in result.message


def test_generate_daily_digest_empty_due_to_flagged_message(tmp_path):
    """DG-22"""
    _setup_engagement(tmp_path)
    _write_evidence_md(
        tmp_path, "ClientA/DD_Q1_2026/evidence/f.md",
        note_id="f", review_status="flagged",
    )
    _write_registry(tmp_path, {
        "f": _evidence_entry(
            "f", "ClientA/DD_Q1_2026/evidence/f.md",
            review_status="flagged",
        ),
    })
    config = _config(tmp_path)
    result = generate_daily_digest(
        config, scope="ClientA/DD_Q1_2026", date="2026-04-04",
    )
    assert result.status == "empty"
    assert result.flagged_counts.excluded == 1
    assert "--include-flagged" in result.message


# ---------------------------------------------------------------------------
# DG-23..DG-23g: validation + retry + scrubbing
# ---------------------------------------------------------------------------


def test_generate_daily_digest_body_validates_llm_owned_sections_only(tmp_path):
    """DG-23"""
    config = _setup_one_input(tmp_path)
    bad_body = "## Summary\n\ntext\n## Trust Notes\n\nfake\n"  # missing other LLM-owned
    with patch("folio.digest._call_llm", return_value=bad_body):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert result.status == "error"
    assert "missing" in result.message.lower() or "validation" in result.message.lower()


def test_generate_daily_digest_compliant_omitting_trust_notes_succeeds_no_retry(tmp_path):
    """DG-23a — B-101 regression-guard"""
    config = _setup_one_input(tmp_path)
    call_count = {"n": 0}

    def fake_llm(*args, **kwargs):
        call_count["n"] += 1
        return _VALID_DAILY_BODY  # omits Trust Notes & Documents Drawn From

    with patch("folio.digest._call_llm", side_effect=fake_llm):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert result.status == "written"
    assert call_count["n"] == 1, "LLM should have been called exactly once (no retry)"


def test_generate_daily_digest_strips_stray_system_sections(tmp_path):
    """DG-23b — MN-102 _strip_section"""
    config = _setup_one_input(tmp_path)
    body_with_stray = _VALID_DAILY_BODY + "\n## Trust Notes\n\nLLM-emitted fake\n"
    with patch("folio.digest._call_llm", return_value=body_with_stray):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert result.status == "written"
    text = result.path.read_text(encoding="utf-8")
    # Exactly one `## Trust Notes` heading in the file
    assert text.count("## Trust Notes") == 1
    # And it's the system-rendered version (contains "synthesis artifact")
    assert "synthesis artifact" in text


def test_generate_daily_digest_corrective_reprompt_succeeds(tmp_path):
    """DG-23c — SF-8 §9.4 validation retry"""
    config = _setup_one_input(tmp_path)
    bad_then_good = ["## Summary\n\nshort\n", _VALID_DAILY_BODY]
    counter = {"n": 0}
    def fake_llm(*args, **kwargs):
        out = bad_then_good[counter["n"]]
        counter["n"] += 1
        return out
    with patch("folio.digest._call_llm", side_effect=fake_llm):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert result.status == "written"
    assert counter["n"] == 2


def test_generate_daily_digest_corrective_reprompt_fails_exits_nonzero(tmp_path):
    """DG-23d"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value="## Summary\n\nshort\n"):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    assert result.status == "error"
    assert result.exit_code != 0


def test_validate_body_sections_skips_fenced_headings():
    """DG-23e — SF-104 fence-aware"""
    body = "## Summary\n\ntext\n```\n## Trust Notes\nfenced\n```\n## What Moved Today\n"
    missing, dups = _validate_body_sections(body, ("Trust Notes",))
    # Trust Notes inside fence should not count
    assert "Trust Notes" in missing


def test_validate_body_sections_matches_atx_with_closing_hashes():
    """DG-23f — ATX with closing #"""
    body = "## Trust Notes ##\n\ntext"
    positions = _heading_positions(body, "Trust Notes")
    assert len(positions) == 1


def test_validate_body_sections_matches_trailing_whitespace():
    """DG-23g — ATX with trailing whitespace"""
    body = "## Trust Notes  \n\ntext"
    positions = _heading_positions(body, "Trust Notes")
    assert len(positions) == 1


# ---------------------------------------------------------------------------
# DG-24..DG-24c: Trust Notes branches
# ---------------------------------------------------------------------------


def test_trust_notes_rendered_programmatically_not_llm(tmp_path):
    """DG-24"""
    config = _setup_one_input(tmp_path)
    weird = _VALID_DAILY_BODY + "\n## Trust Notes\n\nLLM lies here.\n"
    with patch("folio.digest._call_llm", return_value=weird):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    text = result.path.read_text(encoding="utf-8")
    assert "LLM lies here." not in text
    assert "synthesis artifact" in text


def test_trust_notes_branch_no_exclusion_no_override():
    """DG-24a"""
    out = _compose_trust_notes(
        include_flagged=False, counts=DigestFlaggedCounts(excluded=0, included=0)
    )
    assert "excluded" not in out.lower() or "synthesis artifact" in out
    assert "Run with --include-flagged" not in out


def test_trust_notes_branch_excluded_singular_plural():
    """DG-24b — SF-11 + SF-12 pluralization"""
    out_singular = _compose_trust_notes(
        include_flagged=False, counts=DigestFlaggedCounts(excluded=1)
    )
    assert "1 source-backed input " in out_singular  # singular
    assert "1 source-backed inputs" not in out_singular  # not plural

    out_plural = _compose_trust_notes(
        include_flagged=False, counts=DigestFlaggedCounts(excluded=3)
    )
    assert "3 source-backed inputs" in out_plural


def test_trust_notes_branch_override_included_count():
    """DG-24c — SF-11 three branch-3 wordings"""
    zero = _compose_trust_notes(
        include_flagged=True, counts=DigestFlaggedCounts(included=0)
    )
    assert "no flagged source-backed inputs were present" in zero

    one = _compose_trust_notes(
        include_flagged=True, counts=DigestFlaggedCounts(included=1)
    )
    assert "1 flagged source-backed input was included" in one

    many = _compose_trust_notes(
        include_flagged=True, counts=DigestFlaggedCounts(included=4)
    )
    assert "4 flagged source-backed inputs were included" in many


def test_documents_drawn_from_wikilinks_deterministic(tmp_path):
    """DG-25"""
    config = _setup_one_input(tmp_path)
    weird_body = _VALID_DAILY_BODY + "\n## Documents Drawn From\n\n- [[fake]]\n"
    with patch("folio.digest._call_llm", return_value=weird_body):
        result = generate_daily_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04"
        )
    text = result.path.read_text(encoding="utf-8")
    assert "[[in]]" in text  # real input
    assert "[[fake]]" not in text  # LLM lie scrubbed


# ---------------------------------------------------------------------------
# DG-26..DG-28: weekly behavior
# ---------------------------------------------------------------------------


def _seed_one_daily(tmp_path: Path, period: str = "2026-03-30") -> FolioConfig:
    config = _setup_one_input(tmp_path, modified=period)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        generate_daily_digest(config, scope="ClientA/DD_Q1_2026", date=period)
    return config


def test_generate_weekly_digest_consumes_dailies_only(tmp_path):
    """DG-26"""
    config = _seed_one_daily(tmp_path, "2026-03-30")
    with patch("folio.digest._call_llm", return_value=_VALID_WEEKLY_BODY):
        result = generate_weekly_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-03-30"
        )
    assert result.status == "written"
    fm = yaml.safe_load(result.path.read_text(encoding="utf-8").split("---", 2)[1])
    # draws_from references the daily digest, not the raw evidence
    assert all("daily-digest" in d for d in fm["draws_from"])


def test_generate_weekly_digest_period_is_iso_monday(tmp_path):
    """DG-27"""
    config = _seed_one_daily(tmp_path, "2026-04-01")  # Wed in week starting 2026-03-30
    with patch("folio.digest._call_llm", return_value=_VALID_WEEKLY_BODY):
        result = generate_weekly_digest(
            config, scope="ClientA/DD_Q1_2026", date="2026-04-04",  # Sat
        )
    fm = yaml.safe_load(result.path.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm["digest_period"] == "2026-03-30"


def test_generate_weekly_digest_empty_when_no_dailies(tmp_path):
    """DG-28"""
    _setup_engagement(tmp_path)
    _write_registry(tmp_path, {})
    config = _config(tmp_path)
    result = generate_weekly_digest(
        config, scope="ClientA/DD_Q1_2026", date="2026-04-04",
    )
    assert result.status == "empty"
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# DG-29..DG-30c: forbidden symbols
# ---------------------------------------------------------------------------


_DIGEST_SOURCE = (Path(__file__).parent.parent / "folio" / "digest.py").read_text(
    encoding="utf-8"
)


def test_no_pickle_loads_in_module():
    """DG-29 — manifest forbidden symbol"""
    assert "pickle.loads" not in _DIGEST_SOURCE


def test_no_unsafe_yaml_load_in_module():
    """DG-29b — SF-10"""
    # All yaml.load occurrences must be yaml.safe_load
    import re as _re
    matches = _re.findall(r"yaml\.load\b(?!_safe|er)", _DIGEST_SOURCE)
    # filter: only flag bare `yaml.load(` (not yaml.safe_load, yaml.SafeLoader)
    bare = [m for m in matches if m == "yaml.load"]
    assert bare == [] or all("safe_load" in line for line in _DIGEST_SOURCE.splitlines() if "yaml.load" in line and "safe" not in line.lower())


def test_no_eval_in_module():
    """DG-30"""
    # Allow `evaluate` / `evaluation` / `eval_` etc; bare `eval(` only
    import re as _re
    bare = _re.findall(r"\beval\(", _DIGEST_SOURCE)
    assert bare == []


def test_no_unsafe_shell_in_module():
    """DG-30b — SF-10. Word-boundary checks: skip docstring text and `re.compile`."""
    import re as _re
    # Strip docstrings (a simple proxy: remove triple-quoted blocks)
    source_no_docstrings = _re.sub(r'"""[\s\S]*?"""', "", _DIGEST_SOURCE)
    # Bare exec( — not preceded by . or letter
    assert not _re.search(r"(?<![.\w])exec\(", source_no_docstrings)
    # Bare compile( — exclude `re.compile`
    bare_compile = _re.findall(r"(?<![.\w])compile\(", source_no_docstrings)
    assert bare_compile == [], f"Found bare compile(): {bare_compile}"
    # os.system
    assert "os.system" not in source_no_docstrings
    # shell=True
    assert "shell=True" not in source_no_docstrings


def test_no_dynamic_import_or_unsafe_subprocess_via_ast():
    """DG-30c — SF-105 AST-based"""
    tree = ast.parse(_DIGEST_SOURCE)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            # __import__ with non-Constant argument
            if isinstance(f, ast.Name) and f.id == "__import__":
                if node.args and not isinstance(node.args[0], ast.Constant):
                    pytest.fail("dynamic __import__ with non-literal arg")
            # importlib.import_module
            if isinstance(f, ast.Attribute) and f.attr == "import_module":
                if node.args and not isinstance(node.args[0], ast.Constant):
                    pytest.fail("dynamic importlib.import_module with non-literal arg")
            # subprocess.run/call/Popen with shell=True
            if (isinstance(f, ast.Attribute) and
                isinstance(f.value, ast.Name) and f.value.id == "subprocess"):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        pytest.fail("subprocess call with shell=True")
        # globals()[...]
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                if node.value.func.id in ("globals", "locals"):
                    pytest.fail("globals()[...] / locals()[...] indirection")


# ---------------------------------------------------------------------------
# DG-REG-1..5: registry-compatibility canaries
# ---------------------------------------------------------------------------


def test_status_includes_digest_in_summary(tmp_path):
    """DG-REG-1"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        generate_daily_digest(config, scope="ClientA/DD_Q1_2026", date="2026-04-04")
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(tmp_path / "folio.yaml"), "status"])
    assert result.exit_code == 0
    # Some 'analysis' marker present in output (group/count line)
    assert "analysis" in result.output.lower()


def test_scan_ignores_digest_rows(tmp_path):
    """DG-REG-2"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = generate_daily_digest(config, scope="ClientA/DD_Q1_2026", date="2026-04-04")
    digest_id = result.digest_id
    runner = CliRunner()
    runner.invoke(cli, ["--config", str(tmp_path / "folio.yaml"), "scan"])
    # Digest entry still present in registry, type/subtype unchanged
    reg = registry.load_registry(tmp_path / "registry.json")
    assert digest_id in reg["decks"]
    assert reg["decks"][digest_id]["type"] == "analysis"
    assert reg["decks"][digest_id]["subtype"] == "digest"


def test_rebuild_registry_retains_digest(tmp_path):
    """DG-REG-3"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = generate_daily_digest(config, scope="ClientA/DD_Q1_2026", date="2026-04-04")
    digest_id = result.digest_id
    # Delete registry, rebuild
    (tmp_path / "registry.json").unlink()
    rebuilt = registry.rebuild_registry(tmp_path)
    assert digest_id in rebuilt["decks"]
    entry = rebuilt["decks"][digest_id]
    assert entry["type"] == "analysis"
    assert entry["subtype"] == "digest"


def test_enrich_skips_digest_row(tmp_path):
    """DG-REG-4"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        gen_result = generate_daily_digest(config, scope="ClientA/DD_Q1_2026", date="2026-04-04")
    pre_text = gen_result.path.read_text(encoding="utf-8")
    runner = CliRunner()
    # Run enrich; digest row should not be modified
    runner.invoke(cli, [
        "--config", str(tmp_path / "folio.yaml"),
        "enrich", "ClientA/DD_Q1_2026", "--dry-run",
    ])
    assert gen_result.path.read_text(encoding="utf-8") == pre_text


def test_refresh_emits_digest_specific_guidance(tmp_path):
    """DG-REG-5 — SF-2 cli.py:1053-1056 patch"""
    config = _setup_one_input(tmp_path)
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        gen_result = generate_daily_digest(config, scope="ClientA/DD_Q1_2026", date="2026-04-04")
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--config", str(tmp_path / "folio.yaml"), "refresh",
    ])
    # The patched message names `folio digest` for digest rows
    assert "folio digest" in result.output
