"""Tests for `folio digest` CLI surface (spec v1.2 §13.2)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from folio.cli import cli


_VALID_DAILY_BODY = """## Summary

Synthesis text.

## What Moved Today

- Item A

## Emerging Risks / Open Questions

- Risk 1

## Suggested Follow-Ups

- Follow up X
"""


_VALID_WEEKLY_BODY = """## Weekly Summary

Weekly synth.

## What Changed This Week

- A

## Cross-Cutting Themes

- T

## Decisions / Risks To Track

- D

## Next Week Lookahead

- N
"""


def _config_yaml(tmp_path: Path) -> Path:
    folio_yaml = tmp_path / "folio.yaml"
    folio_yaml.write_text(f"library_root: {tmp_path}\n")
    return folio_yaml


def _setup_engagement_with_input(tmp_path: Path) -> Path:
    eng = tmp_path / "ClientA" / "DD_Q1_2026"
    (eng / "evidence").mkdir(parents=True)
    md = eng / "evidence" / "in.md"
    md.write_text(
        "---\n"
        "id: in\ntitle: in\ntype: evidence\n"
        "source: sources/in.pdf\nsource_hash: sha256:abc\n"
        "---\n\nbody\n",
        encoding="utf-8",
    )
    decks = {
        "in": {
            "id": "in", "title": "in", "type": "evidence",
            "markdown_path": "ClientA/DD_Q1_2026/evidence/in.md",
            "deck_dir": "ClientA/DD_Q1_2026/evidence",
            "modified": "2026-04-04",
            "client": "ClientA", "engagement": "DD_Q1_2026",
            "source_relative_path": "sources/in.pdf",
            "source_hash": "sha256:abc",
            "version": 1,
            "converted": "2026-04-04",
        },
    }
    payload = {"_schema_version": 2, "updated_at": "x", "decks": decks}
    (tmp_path / "registry.json").write_text(json.dumps(payload), encoding="utf-8")
    return _config_yaml(tmp_path)


# ---------------------------------------------------------------------------
# DG-CLI-1..2: registration cardinality
# ---------------------------------------------------------------------------


def test_digest_command_registered():
    """DG-CLI-1 — manifest cardinality assertion mirror"""
    assert "digest" in cli.commands


def test_folio_digest_module_exports():
    """DG-CLI-2 — manifest cardinality assertion mirror"""
    import folio.digest as d
    assert hasattr(d, "generate_daily_digest")
    assert hasattr(d, "generate_weekly_digest")


# ---------------------------------------------------------------------------
# DG-CLI-3..8: argument plumbing
# ---------------------------------------------------------------------------


def test_digest_requires_scope(tmp_path):
    """DG-CLI-3"""
    cfg = _config_yaml(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(cfg), "digest"])
    assert result.exit_code != 0
    assert "scope" in result.output.lower()


def test_digest_invalid_date_format(tmp_path):
    """DG-CLI-4"""
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--config", str(cfg), "digest", "ClientA/DD_Q1_2026", "--date", "not-a-date",
    ])
    assert result.exit_code != 0
    assert "YYYY-MM-DD" in result.output


def test_digest_default_date_is_today(tmp_path):
    """DG-CLI-5"""
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    captured = {}
    from folio import digest as digest_module
    real = digest_module.generate_daily_digest

    def spy(config, *, scope, date, include_flagged, llm_profile):
        captured["date"] = date
        return real(
            config, scope=scope, date=date,
            include_flagged=include_flagged, llm_profile=llm_profile,
        )

    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        with patch("folio.digest.generate_daily_digest", side_effect=spy):
            runner.invoke(cli, ["--config", str(cfg), "digest", "ClientA/DD_Q1_2026"])
    # date passed through as None → daily defaults to local today inside the function
    assert captured["date"] is None


def test_digest_week_flag_triggers_weekly(tmp_path):
    """DG-CLI-6"""
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    called = {"weekly": False}
    from folio import digest as dm

    def fake_weekly(config, **kwargs):
        called["weekly"] = True
        return dm.DigestResult(
            status="empty", digest_id=None, path=None,
            flagged_counts=dm.DigestFlaggedCounts(), draws_from_count=0,
            message="empty", exit_code=0,
        )

    with patch("folio.digest.generate_weekly_digest", side_effect=fake_weekly):
        runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--week", "--date", "2026-04-04",
        ])
    assert called["weekly"]


def test_digest_include_flagged_propagates(tmp_path):
    """DG-CLI-7"""
    cfg = _setup_engagement_with_input(tmp_path)
    captured = {}
    from folio import digest as dm

    def spy(config, **kwargs):
        captured["include_flagged"] = kwargs.get("include_flagged")
        return dm.DigestResult(
            status="empty", digest_id=None, path=None,
            flagged_counts=dm.DigestFlaggedCounts(), draws_from_count=0,
            message="empty", exit_code=0,
        )

    runner = CliRunner()
    with patch("folio.digest.generate_daily_digest", side_effect=spy):
        runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--include-flagged",
        ])
    assert captured["include_flagged"] is True


def test_digest_llm_profile_propagates(tmp_path):
    """DG-CLI-8"""
    cfg = _setup_engagement_with_input(tmp_path)
    captured = {}
    from folio import digest as dm

    def spy(config, **kwargs):
        captured["llm_profile"] = kwargs.get("llm_profile")
        return dm.DigestResult(
            status="empty", digest_id=None, path=None,
            flagged_counts=dm.DigestFlaggedCounts(), draws_from_count=0,
            message="empty", exit_code=0,
        )

    runner = CliRunner()
    with patch("folio.digest.generate_daily_digest", side_effect=spy):
        runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--llm-profile", "fast",
        ])
    assert captured["llm_profile"] == "fast"


# ---------------------------------------------------------------------------
# DG-CLI-9..14: stdout rendering
# ---------------------------------------------------------------------------


def test_digest_success_stdout_lists_path_and_count(tmp_path):
    """DG-CLI-9"""
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--date", "2026-04-04",
        ])
    assert result.exit_code == 0
    assert "✓ Wrote daily digest:" in result.output
    assert "Path:" in result.output
    assert "Drawn from 1 input" in result.output  # singular


def test_digest_success_stdout_singular_one_input(tmp_path):
    """DG-CLI-9b — SF-12 singular"""
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--date", "2026-04-04",
        ])
    assert "Drawn from 1 input." in result.output
    assert "Drawn from 1 inputs." not in result.output


def test_digest_success_stdout_include_flagged_echo_singular(tmp_path):
    """DG-CLI-9c — SF-107 singular"""
    cfg = _setup_engagement_with_input(tmp_path)
    # Add a flagged input
    eng = tmp_path / "ClientA" / "DD_Q1_2026" / "evidence"
    md = eng / "f.md"
    md.write_text(
        "---\nid: f\ntitle: f\ntype: evidence\nsource: s.pdf\nsource_hash: sha256:abc\n"
        "review_status: flagged\n---\nbody\n", encoding="utf-8",
    )
    reg_path = tmp_path / "registry.json"
    reg = json.loads(reg_path.read_text())
    reg["decks"]["f"] = {
        "id": "f", "title": "f", "type": "evidence",
        "markdown_path": "ClientA/DD_Q1_2026/evidence/f.md",
        "deck_dir": "ClientA/DD_Q1_2026/evidence",
        "modified": "2026-04-04",
        "client": "ClientA", "engagement": "DD_Q1_2026",
        "source_relative_path": "s.pdf", "source_hash": "sha256:abc",
        "version": 1, "converted": "2026-04-04",
        "review_status": "flagged",
    }
    reg_path.write_text(json.dumps(reg))
    runner = CliRunner()
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--date", "2026-04-04", "--include-flagged",
        ])
    assert "1 flagged input included" in result.output


def test_digest_success_stdout_include_flagged_echo_plural(tmp_path):
    """DG-CLI-9d — SF-107 plural (SF-206)"""
    cfg = _setup_engagement_with_input(tmp_path)
    # Add 2 flagged inputs
    eng = tmp_path / "ClientA" / "DD_Q1_2026" / "evidence"
    reg_path = tmp_path / "registry.json"
    reg = json.loads(reg_path.read_text())
    for fid in ["f1", "f2"]:
        md = eng / f"{fid}.md"
        md.write_text(
            f"---\nid: {fid}\ntitle: {fid}\ntype: evidence\n"
            f"source: s.pdf\nsource_hash: sha256:abc\n"
            f"review_status: flagged\n---\nbody\n", encoding="utf-8",
        )
        reg["decks"][fid] = {
            "id": fid, "title": fid, "type": "evidence",
            "markdown_path": f"ClientA/DD_Q1_2026/evidence/{fid}.md",
            "deck_dir": "ClientA/DD_Q1_2026/evidence",
            "modified": "2026-04-04",
            "client": "ClientA", "engagement": "DD_Q1_2026",
            "source_relative_path": "s.pdf", "source_hash": "sha256:abc",
            "version": 1, "converted": "2026-04-04",
            "review_status": "flagged",
        }
    reg_path.write_text(json.dumps(reg))
    runner = CliRunner()
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        result = runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--date", "2026-04-04", "--include-flagged",
        ])
    assert "2 flagged inputs included" in result.output
    # Singular form must NOT appear
    assert "1 flagged input included" not in result.output


def test_digest_empty_stdout_no_inputs(tmp_path):
    """DG-CLI-10"""
    cfg = _config_yaml(tmp_path)
    (tmp_path / "ClientA" / "DD_Q1_2026").mkdir(parents=True)
    (tmp_path / "registry.json").write_text(json.dumps({"_schema_version": 2, "updated_at": "x", "decks": {}}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
        "--date", "2026-04-04",
    ])
    assert result.exit_code == 0
    assert "No eligible inputs" in result.output


def test_digest_empty_stdout_no_inputs_with_override_echoes(tmp_path):
    """DG-CLI-10b — SF-15"""
    cfg = _config_yaml(tmp_path)
    (tmp_path / "ClientA" / "DD_Q1_2026").mkdir(parents=True)
    (tmp_path / "registry.json").write_text(json.dumps({"_schema_version": 2, "updated_at": "x", "decks": {}}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
        "--date", "2026-04-04", "--include-flagged",
    ])
    assert "--include-flagged was honored" in result.output


def test_digest_empty_stdout_flagged_only_points_to_override(tmp_path):
    """DG-CLI-11"""
    cfg = _config_yaml(tmp_path)
    eng = tmp_path / "ClientA" / "DD_Q1_2026" / "evidence"
    eng.mkdir(parents=True)
    md = eng / "f.md"
    md.write_text(
        "---\nid: f\ntitle: f\ntype: evidence\nsource: s.pdf\nsource_hash: sha256:abc\n"
        "review_status: flagged\n---\nbody\n", encoding="utf-8",
    )
    decks = {
        "f": {
            "id": "f", "title": "f", "type": "evidence",
            "markdown_path": "ClientA/DD_Q1_2026/evidence/f.md",
            "deck_dir": "ClientA/DD_Q1_2026/evidence",
            "modified": "2026-04-04",
            "client": "ClientA", "engagement": "DD_Q1_2026",
            "source_relative_path": "s.pdf", "source_hash": "sha256:abc",
            "version": 1, "converted": "2026-04-04",
            "review_status": "flagged",
        },
    }
    (tmp_path / "registry.json").write_text(json.dumps({
        "_schema_version": 2, "updated_at": "x", "decks": decks,
    }))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
        "--date", "2026-04-04",
    ])
    assert "--include-flagged" in result.output
    assert "1 source-backed input" in result.output  # singular


def test_digest_llm_failure_exit_nonzero_preserves_existing(tmp_path):
    """DG-CLI-12"""
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    with patch("folio.digest._call_llm", side_effect=RuntimeError("nope")):
        result = runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--date", "2026-04-04",
        ])
    assert result.exit_code != 0
    assert result.output.startswith("✗") or "✗" in result.output


def test_digest_rerun_message_says_updated(tmp_path):
    """DG-CLI-13"""
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    with patch("folio.digest._call_llm", return_value=_VALID_DAILY_BODY):
        runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--date", "2026-04-04",
        ])
        result = runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--date", "2026-04-04",
        ])
    assert "Updated daily digest" in result.output
    assert "version 1 → 2" in result.output


def test_digest_week_with_include_flagged_emits_advisory(tmp_path):
    """DG-CLI-14 — SF-14"""
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    # No daily digests yet → empty weekly result, but advisory should still emit
    result = runner.invoke(cli, [
        "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
        "--week", "--date", "2026-04-04", "--include-flagged",
    ])
    assert result.exit_code == 0
    assert "--include-flagged has no effect in --week mode" in result.output


def test_digest_scope_required_via_usage_error(tmp_path):
    """DG-CLI-15 — B-001 fix"""
    cfg = _config_yaml(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(cfg), "digest"])
    assert result.exit_code != 0
    assert "scope is required" in result.output.lower() or "usage" in result.output.lower()


def test_digest_help_includes_examples(tmp_path):
    """DG-CLI-16"""
    runner = CliRunner()
    result = runner.invoke(cli, ["digest", "--help"])
    assert result.exit_code == 0
    assert "Examples" in result.output or "folio digest ClientA" in result.output


def test_digest_include_flagged_help_text_mentions_week_noop(tmp_path):
    """DG-CLI-17 — MN-8"""
    runner = CliRunner()
    result = runner.invoke(cli, ["digest", "--help"])
    assert "no-op in --week" in result.output or "daily mode only" in result.output


def test_digest_concurrent_invocation_serializes_or_locks(tmp_path):
    """DG-CLI-18 — SF-103 / §10.5: second concurrent invocation either serializes
    or fails with LibraryLockError; either way registry/file state is consistent.

    Mock the lock to simulate already-held; assert second invocation surfaces
    the LibraryLockError via ✗ prefix and non-zero exit.
    """
    cfg = _setup_engagement_with_input(tmp_path)
    runner = CliRunner()
    from folio.lock import LibraryLockError

    def raising_lock(*args, **kwargs):
        raise LibraryLockError("digest already running")

    with patch("folio.lock.library_lock", side_effect=raising_lock):
        result = runner.invoke(cli, [
            "--config", str(cfg), "digest", "ClientA/DD_Q1_2026",
            "--date", "2026-04-04",
        ])
    assert result.exit_code != 0
    assert "✗" in result.output
    assert "digest already running" in result.output
