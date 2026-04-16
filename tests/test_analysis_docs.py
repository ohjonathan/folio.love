"""Tests for managed analysis note initialization."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from folio.analysis_docs import compute_graph_input_fingerprint, create_analysis_document
from folio.cli import cli
from folio.tracking import registry
from folio.tracking.registry import RegistryEntry, entry_from_dict


def _minimal_config(library_root: Path):
    from folio.config import FolioConfig

    folio_yaml = library_root / "folio.yaml"
    folio_yaml.write_text(f"library_root: {library_root}\n")
    return FolioConfig.load(folio_yaml)


def _write_registry(library_root: Path, entries: dict[str, dict]) -> None:
    payload = {
        "_schema_version": 1,
        "updated_at": "2026-04-01T00:00:00Z",
        "decks": entries,
    }
    (library_root / "registry.json").write_text(json.dumps(payload), encoding="utf-8")


def _entry(note_id: str, markdown_path: str, *, note_type: str, title: str, modified: str | None = None) -> dict:
    entry = {
        "id": note_id,
        "title": title,
        "type": note_type,
        "markdown_path": markdown_path,
        "deck_dir": str(Path(markdown_path).parent).replace("\\", "/"),
        "client": "Acme",
        "engagement": "DD Q1 2026",
    }
    if note_type in {"context", "analysis"}:
        if modified is not None:
            entry["modified"] = modified
    else:
        entry.update(
            {
                "source_relative_path": "deck.pptx",
                "source_hash": f"{note_id}-hash",
                "version": 1,
                "converted": "2026-04-01T00:00:00Z",
            }
        )
    return entry


def _write_note(path: Path, frontmatter: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{yaml_str}---\n\n# {frontmatter['title']}\n", encoding="utf-8")


def _read_fm(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    end = content.index("\n---", 4)
    return yaml.safe_load(content[4:end]) or {}


def test_create_analysis_document_registers_sourceless_row_and_input_fingerprint(tmp_path):
    config = _minimal_config(tmp_path)

    context_id = "acme_ddq126_context_20260401_engagement"
    evidence_id = "acme_evidence_20260401_market_map"
    _write_registry(
        tmp_path,
        {
            context_id: _entry(
                context_id,
                "acme/ddq126/_context.md",
                note_type="context",
                title="Context",
                modified="2026-04-01",
            ),
            evidence_id: _entry(
                evidence_id,
                "acme/ddq126/evidence.md",
                note_type="evidence",
                title="Evidence",
            ),
        },
    )
    _write_note(
        tmp_path / "acme" / "ddq126" / "_context.md",
        {
            "id": context_id,
            "title": "Context",
            "type": "context",
            "client": "Acme",
            "engagement": "DD Q1 2026",
            "created": "2026-04-01",
            "modified": "2026-04-01",
        },
    )
    _write_note(
        tmp_path / "acme" / "ddq126" / "evidence.md",
        {
            "id": evidence_id,
            "title": "Evidence",
            "type": "evidence",
            "client": "Acme",
            "engagement": "DD Q1 2026",
            "source": "deck.pptx",
            "source_hash": f"{evidence_id}-hash",
            "version": 1,
            "created": "2026-04-01",
            "modified": "2026-04-01",
        },
    )

    with patch("folio.analysis_docs.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        analysis_id, output_path = create_analysis_document(
            config,
            subtype="synthesis",
            title="Growth Synthesis",
            client="Acme",
            engagement="DD Q1 2026",
            draws_from=[context_id],
            depends_on=[evidence_id],
        )

    assert output_path.exists()
    fm = _read_fm(output_path)
    assert fm["type"] == "analysis"
    assert fm["subtype"] == "synthesis"
    assert fm["authority"] == "analyzed"
    assert fm["curation_level"] == "L1"
    assert fm["review_status"] == "flagged"
    assert fm["review_flags"] == ["synthesis_requires_review"]
    assert fm["draws_from"] == [context_id]
    assert fm["depends_on"] == [evidence_id]

    expected_fp = compute_graph_input_fingerprint(
        [
            entry_from_dict(_entry(context_id, "acme/ddq126/_context.md", note_type="context", title="Context", modified="2026-04-01")),
            entry_from_dict(_entry(evidence_id, "acme/ddq126/evidence.md", note_type="evidence", title="Evidence")),
        ]
    )
    assert fm["_llm_metadata"]["graph"]["input_fingerprint"] == expected_fp

    reg_data = json.loads((tmp_path / "registry.json").read_text())
    row = reg_data["decks"][analysis_id]
    assert row["type"] == "analysis"
    assert row["subtype"] == "synthesis"
    assert "source_relative_path" not in row
    assert "source_hash" not in row
    assert "version" not in row


def test_analysis_init_cli_creates_note_and_refresh_skips_it(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(yaml.dump({"library_root": str(library)}, default_flow_style=False))

    runner = CliRunner()
    with patch("folio.analysis_docs.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "analysis",
                "init",
                "synthesis",
                "--title",
                "Growth Synthesis",
                "--client",
                "Acme",
                "--engagement",
                "DD Q1 2026",
            ],
        )
    assert result.exit_code == 0

    reg_data = json.loads((library / "registry.json").read_text())
    analysis_id = next(iter(reg_data["decks"]))
    row = reg_data["decks"][analysis_id]
    assert row["type"] == "analysis"
    assert (library / row["markdown_path"]).exists()

    refresh = runner.invoke(cli, ["--config", str(config_path), "refresh"])
    assert refresh.exit_code == 0
    assert "skipping analysis document" in refresh.output
    assert "Skipped analysis entries: 1" in refresh.output


def test_create_analysis_document_rejects_unknown_inputs(tmp_path):
    config = _minimal_config(tmp_path)
    with pytest.raises(ValueError, match="Unknown input document"):
        create_analysis_document(
            config,
            subtype="hypothesis",
            title="Unknown Inputs",
            client="Acme",
            engagement="DD Q1 2026",
            draws_from=["missing_doc"],
        )


def test_rebuild_registry_discovers_analysis_documents(tmp_path):
    analysis_path = tmp_path / "acme" / "ddq126" / "analysis" / "synthesis" / "growth.md"
    _write_note(
        analysis_path,
        {
            "id": "acme_ddq126_analysis_20260415_growth",
            "title": "Growth",
            "type": "analysis",
            "subtype": "synthesis",
            "client": "Acme",
            "engagement": "DD Q1 2026",
            "authority": "analyzed",
            "curation_level": "L1",
            "review_status": "flagged",
            "review_flags": ["synthesis_requires_review"],
            "created": "2026-04-15",
            "modified": "2026-04-15",
        },
    )

    data = registry.rebuild_registry(tmp_path)
    row = data["decks"]["acme_ddq126_analysis_20260415_growth"]
    assert row["type"] == "analysis"
    assert row["subtype"] == "synthesis"
    assert "source_relative_path" not in row
    assert "source_hash" not in row
