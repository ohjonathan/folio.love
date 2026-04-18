"""CLI integration tests for folio enrich diagnose v1.0.0.

ED-CLI-1..ED-CLI-23d per spec §8.2. Verifies:
  - --help works (ED-CLI-1)
  - Group-reshape regression: legacy `folio enrich [scope]` invocations
    still work (ED-CLI-2/3)
  - Text output shape (ED-CLI-4)
  - [flagged] suffix INSIDE severity bracket (ED-CLI-5)
  - JSON envelope keys (ED-CLI-6/7/8)
  - Empty findings (ED-CLI-9/10)
  - Limit validation (ED-CLI-11/12)
  - Limit truncation text/json (ED-CLI-13/14)
  - Scope arg routing (ED-CLI-15)
  - Findings present → exit 0 (ED-CLI-16)
  - Fatal errors (ED-CLI-17)
  - No lock acquired (ED-CLI-18) — partial; check process behavior
  - --include-flagged absent from --help (ED-CLI-19) — CB-4 firewall
  - enrich → diagnose breadcrumb fire/no-fire (ED-CLI-20a/b)
  - Invalid scope + corrupt registry exit-1 (ED-CLI-21/22)
  - Option-before-scope (ED-CLI-23a/b/c) + subcommand-args-not-rewritten
    (ED-CLI-23d)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml
from click.testing import CliRunner

from folio.cli import cli
from folio.config import FolioConfig, LLMConfig, LLMProfile, LLMRoute


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_config_file(library_root: Path) -> Path:
    """Write a minimal folio.yaml config file pointing at library_root."""
    config_path = library_root / "folio.yaml"
    config_data = {
        "library_root": str(library_root),
        "llm": {
            "profiles": {
                "default": {
                    "name": "default", "provider": "anthropic", "model": "test-model",
                },
                "enrich_profile": {
                    "name": "enrich_profile", "provider": "anthropic",
                    "model": "enrich-model",
                },
            },
            "routing": {
                "default": {"primary": "default"},
                "enrich": {"primary": "enrich_profile", "fallbacks": []},
            },
        },
    }
    config_path.write_text(yaml.dump(config_data))
    return config_path


def _evidence_note(
    note_id: str = "n1",
    title: str = "Test",
    client: str = "ClientA",
    engagement: str = "DD_Q1",
    curation_level: str = "L0",
    review_status: str = "clean",
    enrich_meta: dict | None = None,
    body: str | None = None,
) -> str:
    fm = {
        "id": note_id, "title": title, "type": "evidence", "status": "active",
        "curation_level": curation_level, "review_status": review_status,
        "client": client, "engagement": engagement,
        "source": "deck.pptx", "source_hash": "abc", "version": 1,
        "created": "2026-01-01T00:00:00Z", "modified": "2026-01-01T00:00:00Z",
    }
    if enrich_meta is not None:
        fm["_llm_metadata"] = {"enrich": enrich_meta}
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    if body is None:
        body = (
            "## Slide 1\n\n![Slide 1](slides/slide-001.png)\n\n"
            "### Analysis\n\n**Slide Type:** data\n"
        )
    return f"---\n{yaml_str}---\n\n# {title}\n\n{body}"


def _setup_registry(library_root: Path, entries: dict) -> None:
    data = {"_schema_version": 1, "decks": entries, "updated_at": "2026-01-01T00:00:00Z"}
    (library_root / "registry.json").write_text(json.dumps(data))


def _registry_entry(deck_id: str, rel_path: str, type_: str = "evidence",
                    client: str = "ClientA", engagement: str = "DD_Q1") -> dict:
    deck_dir = str(Path(rel_path).parent)
    return {
        "id": deck_id, "title": deck_id, "markdown_path": rel_path,
        "deck_dir": deck_dir, "type": type_,
        "client": client, "engagement": engagement,
    }


def _write(library_root: Path, rel: str, content: str) -> Path:
    p = library_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def _build_lib(tmp_path: Path, *, curation_level: str = "L0",
               review_status: str = "clean", enrich_meta: dict | None = None,
               note_id: str = "ClientA_DD_Q1_evidence_n1",
               rel_path: str = "ClientA/DD_Q1/evidence/n1.md") -> Path:
    """Returns the config file path."""
    library_root = tmp_path / "lib"
    library_root.mkdir(exist_ok=True)
    content = _evidence_note(
        note_id=note_id, curation_level=curation_level,
        review_status=review_status, enrich_meta=enrich_meta,
    )
    _write(library_root, rel_path, content)
    _setup_registry(library_root, {note_id: _registry_entry(note_id, rel_path)})
    return _make_config_file(library_root)


# ---------------------------------------------------------------------------
# ED-CLI-1: help
# ---------------------------------------------------------------------------

class TestHelp:
    def test_enrich_diagnose_help(self):
        # ED-CLI-1: PROD-MIN-002 closure — help mentions "evidence and interaction notes".
        runner = CliRunner()
        result = runner.invoke(cli, ["enrich", "diagnose", "--help"])
        assert result.exit_code == 0
        assert "Identify evidence and interaction notes" in result.output


# ---------------------------------------------------------------------------
# ED-CLI-2/3: group-reshape regression
# ---------------------------------------------------------------------------

class TestGroupReshapeRegression:
    def test_enrich_group_legacy_invocation(self, tmp_path):
        # ED-CLI-2: `folio enrich [scope]` (no subcommand) routes to enrich_batch.
        # We use --dry-run so no actual LLM calls happen.
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "ClientA", "--dry-run",
        ])
        # Dry-run on a healthy library should exit 0
        assert result.exit_code == 0, result.output

    def test_enrich_group_legacy_flags_preserved(self, tmp_path):
        # ED-CLI-3: group flags (--dry-run, --force) parse cleanly.
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        # --dry-run + --force together
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "--dry-run", "--force",
        ])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# ED-CLI-4/5: text output shape + flagged suffix INSIDE severity bracket
# ---------------------------------------------------------------------------

class TestTextOutput:
    def test_diagnose_text_output_shape(self, tmp_path):
        # ED-CLI-4: shape `[severity] code subject_id: detail\n  Action: ...`
        config_path = _build_lib(tmp_path, curation_level="L2")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose",
        ])
        assert result.exit_code == 0
        out = result.output
        assert "[warning]" in out
        assert "protected_by_curation_level" in out
        assert "ClientA_DD_Q1_evidence_n1" in out
        assert "curation_level=L2" in out
        assert "  Action:" in out
        assert "1 findings" in out

    def test_diagnose_text_flagged_suffix_inside_severity(self, tmp_path):
        # ED-CLI-5: CSF-2 closure — `[flagged]` INSIDE severity bracket
        # (e.g., `[warning [flagged]]`), NOT at end of line.
        config_path = _build_lib(tmp_path, curation_level="L2", review_status="flagged")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose",
        ])
        assert result.exit_code == 0
        # Must contain "[warning [flagged]]" — flagged INSIDE severity bracket
        assert "[warning [flagged]]" in result.output
        # And NOT the v1.0 end-of-line position
        assert ": curation_level=L2 [flagged]" not in result.output


# ---------------------------------------------------------------------------
# ED-CLI-6/7/8: JSON envelope keys
# ---------------------------------------------------------------------------

class TestJsonEnvelope:
    def test_diagnose_json_envelope_keys(self, tmp_path):
        # ED-CLI-6: top-level keys exactly match §7.2.
        config_path = _build_lib(tmp_path, curation_level="L2")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "--json",
        ])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert set(payload.keys()) == {
            "schema_version", "command", "scope", "limit",
            "findings", "summary", "truncated",
        }

    def test_diagnose_json_finding_keys(self, tmp_path):
        # ED-CLI-7: per-finding keys exactly match §7.3.
        config_path = _build_lib(tmp_path, curation_level="L2")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "--json",
        ])
        payload = json.loads(result.output)
        assert payload["findings"]
        keys = set(payload["findings"][0].keys())
        assert keys == {
            "code", "severity", "subject_id", "detail",
            "recommended_action", "trust_status",
        }

    def test_diagnose_json_schema_version(self, tmp_path):
        # ED-CLI-8: schema_version + command constants.
        config_path = _build_lib(tmp_path, curation_level="L2")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "--json",
        ])
        payload = json.loads(result.output)
        assert payload["schema_version"] == "1.0"
        assert payload["command"] == "enrich diagnose"


# ---------------------------------------------------------------------------
# ED-CLI-9/10: empty findings
# ---------------------------------------------------------------------------

class TestEmptyFindings:
    def test_diagnose_empty_findings_text(self, tmp_path):
        # ED-CLI-9: healthy library → "No enrichment hygiene findings."
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose",
        ])
        assert result.exit_code == 0
        assert "No enrichment hygiene findings." in result.output

    def test_diagnose_empty_findings_json(self, tmp_path):
        # ED-CLI-10: healthy library → empty findings, exit 0.
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "--json",
        ])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["findings"] == []
        assert payload["summary"]["total"] == 0
        assert payload["summary"]["by_code"] == {}
        assert payload["summary"]["flagged_total"] == 0
        assert payload["truncated"] is False


# ---------------------------------------------------------------------------
# ED-CLI-11/12/13/14: limit validation + truncation
# ---------------------------------------------------------------------------

class TestLimitBehavior:
    def test_diagnose_limit_validation_zero(self, tmp_path):
        # ED-CLI-11: --limit 0 → exit 2 (Click usage error).
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "--limit", "0",
        ])
        assert result.exit_code == 2

    def test_diagnose_limit_validation_negative(self, tmp_path):
        # ED-CLI-12
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "--limit", "-1",
        ])
        assert result.exit_code == 2

    def test_diagnose_limit_truncation_text(self, tmp_path):
        # ED-CLI-13: --limit 1 with 3 findings → 1 finding rendered.
        library_root = tmp_path / "lib"
        library_root.mkdir()
        for i in range(3):
            note_id = f"ClientA_DD_Q1_evidence_n{i}"
            rel = f"ClientA/DD_Q1/evidence/n{i}.md"
            _write(library_root, rel, _evidence_note(note_id=note_id, curation_level="L2"))
        _setup_registry(library_root, {
            f"ClientA_DD_Q1_evidence_n{i}": _registry_entry(
                f"ClientA_DD_Q1_evidence_n{i}",
                f"ClientA/DD_Q1/evidence/n{i}.md",
            ) for i in range(3)
        })
        config_path = _make_config_file(library_root)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "--limit", "1",
        ])
        assert result.exit_code == 0
        assert "1 findings" in result.output
        # Truncation hint
        assert "showing" in result.output

    def test_diagnose_limit_truncation_json(self, tmp_path):
        # ED-CLI-14
        library_root = tmp_path / "lib"
        library_root.mkdir()
        for i in range(3):
            note_id = f"ClientA_DD_Q1_evidence_n{i}"
            rel = f"ClientA/DD_Q1/evidence/n{i}.md"
            _write(library_root, rel, _evidence_note(note_id=note_id, curation_level="L2"))
        _setup_registry(library_root, {
            f"ClientA_DD_Q1_evidence_n{i}": _registry_entry(
                f"ClientA_DD_Q1_evidence_n{i}",
                f"ClientA/DD_Q1/evidence/n{i}.md",
            ) for i in range(3)
        })
        config_path = _make_config_file(library_root)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose",
            "--json", "--limit", "1",
        ])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert len(payload["findings"]) == 1
        assert payload["truncated"] is True


# ---------------------------------------------------------------------------
# ED-CLI-15: scope arg routing
# ---------------------------------------------------------------------------

class TestScopeArg:
    def test_diagnose_scope_arg(self, tmp_path):
        # ED-CLI-15: scope arg narrows correctly.
        library_root = tmp_path / "lib"
        library_root.mkdir()
        for client in ("ClientA", "ClientB"):
            note_id = f"{client}_DD_Q1_evidence_n1"
            rel = f"{client}/DD_Q1/evidence/n1.md"
            _write(library_root, rel,
                   _evidence_note(note_id=note_id, client=client, curation_level="L2"))
        _setup_registry(library_root, {
            f"{client}_DD_Q1_evidence_n1": _registry_entry(
                f"{client}_DD_Q1_evidence_n1",
                f"{client}/DD_Q1/evidence/n1.md",
                client=client,
            )
            for client in ("ClientA", "ClientB")
        })
        config_path = _make_config_file(library_root)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "ClientA", "--json",
        ])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert len(payload["findings"]) == 1
        assert payload["findings"][0]["subject_id"].startswith("ClientA")


# ---------------------------------------------------------------------------
# ED-CLI-16/17: findings present → exit 0; fatal errors
# ---------------------------------------------------------------------------

class TestExitCodes:
    def test_diagnose_findings_present_exit_zero(self, tmp_path):
        # ED-CLI-16: findings → exit 0 (diagnostic, not pass/fail).
        config_path = _build_lib(tmp_path, curation_level="L2")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose",
        ])
        assert result.exit_code == 0

    def test_diagnose_unreadable_registry_fatal(self, tmp_path):
        # ED-CLI-17: simulate plan_enrichment raising via patching.
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        with patch("folio.enrich.plan_enrichment") as m:
            m.side_effect = RuntimeError("simulated fatal")
            result = runner.invoke(cli, [
                "--config", str(config_path), "enrich", "diagnose",
            ])
        assert result.exit_code == 1
        assert "✗" in result.output


# ---------------------------------------------------------------------------
# ED-CLI-18: no lock acquired (simplified — verify text)
# ---------------------------------------------------------------------------

class TestNoLock:
    def test_diagnose_no_lock_acquired_smoke(self, tmp_path):
        # ED-CLI-18 simplified: just verify diagnose returns quickly with no
        # library_lock import in the diagnose CLI path. Full concurrent-lock
        # test would require fork/thread harness; that's beyond unit scope.
        config_path = _build_lib(tmp_path, curation_level="L2")
        runner = CliRunner()
        # Just verify it runs at all (no lock means no LibraryLockError on
        # an absent lock file, no ImportError, etc.).
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose",
        ])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# ED-CLI-19: --include-flagged absent from --help (CB-4 firewall runtime)
# ---------------------------------------------------------------------------

class TestIncludeFlaggedFirewall:
    def test_diagnose_help_does_not_expose_include_flagged(self):
        # ED-CLI-19: CB-4 closure — --help output must NOT contain
        # the literal substring `--include-flagged`.
        runner = CliRunner()
        result = runner.invoke(cli, ["enrich", "diagnose", "--help"])
        assert result.exit_code == 0
        assert "--include-flagged" not in result.output


# ---------------------------------------------------------------------------
# ED-CLI-20a/b: enrich → diagnose breadcrumb
# ---------------------------------------------------------------------------

class TestBreadcrumb:
    def test_enrich_breadcrumb_fires_when_protected(self, tmp_path):
        # ED-CLI-20a: PROD-SF-006 closure — when enrich_batch returns
        # protected+conflicted > 0, breadcrumb fires.
        config_path = _build_lib(tmp_path, curation_level="L2")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "ClientA", "--dry-run",
        ])
        assert result.exit_code == 0
        assert "Tip: run `folio enrich diagnose" in result.output

    def test_enrich_breadcrumb_silent_when_clean(self, tmp_path):
        # ED-CLI-20b
        config_path = _build_lib(tmp_path)  # healthy
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "ClientA", "--dry-run",
        ])
        assert result.exit_code == 0
        assert "Tip: run `folio enrich diagnose" not in result.output


# ---------------------------------------------------------------------------
# ED-CLI-21/22: invalid scope + corrupt registry → exit 1
# ---------------------------------------------------------------------------

class TestScopeAndRegistryFatal:
    def test_diagnose_invalid_scope_exits_one(self, tmp_path):
        # ED-CLI-21: CB-3 closure.
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "ClinetA_typo",
        ])
        assert result.exit_code == 1
        assert "✗" in result.output
        assert "ClinetA_typo" in result.output

    def test_diagnose_corrupt_registry_exits_one(self, tmp_path):
        # ED-CLI-22: CB-3 closure.
        library_root = tmp_path / "lib"
        library_root.mkdir()
        # Write corrupt registry
        (library_root / "registry.json").write_text(
            json.dumps({"_corrupt": True, "decks": {}})
        )
        config_path = _make_config_file(library_root)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "anyscope",
        ])
        assert result.exit_code == 1
        assert "✗" in result.output


# ---------------------------------------------------------------------------
# ED-CLI-23a/b/c/d: option-before-scope + subcommand-args-not-rewritten
# ---------------------------------------------------------------------------

class TestOptionBeforeScope:
    def test_enrich_option_before_scope_dry_run(self, tmp_path):
        # ED-CLI-23a: CB-2 closure — `folio enrich --dry-run ClientA` works.
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "--dry-run", "ClientA",
        ])
        assert result.exit_code == 0, result.output

    def test_enrich_option_before_scope_llm_profile(self, tmp_path):
        # ED-CLI-23b
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich",
            "--llm-profile", "default", "ClientA", "--dry-run",
        ])
        assert result.exit_code == 0, result.output

    def test_enrich_option_before_scope_force(self, tmp_path):
        # ED-CLI-23c
        config_path = _build_lib(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich",
            "--force", "ClientA", "--dry-run",
        ])
        assert result.exit_code == 0, result.output

    def test_enrich_diagnose_subcommand_after_options_unaffected(self, tmp_path):
        # ED-CLI-23d: CB-2 final closure — `folio enrich diagnose ClientA`
        # routes to diagnose with scope=ClientA (NOT rewritten to --scope).
        config_path = _build_lib(tmp_path, curation_level="L2")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--config", str(config_path), "enrich", "diagnose", "ClientA",
        ])
        assert result.exit_code == 0
        # Findings must appear (proves scope=ClientA was bound to the diagnose
        # subcommand's positional arg, not group-level --scope which is hidden).
        assert "protected_by_curation_level" in result.output
