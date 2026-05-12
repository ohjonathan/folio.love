"""Tests for folio.yaml defaults and derivation."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from folio.cli import cli
from folio.config import FolioConfig, SourceConfig
from folio.defaults import (
    DefaultResolutionError,
    resolve_convert_metadata,
    resolve_ingest_metadata,
)
from folio.ingest import IngestResult


def test_config_loads_defaults_block(tmp_path):
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(
        "\n".join(
            [
                "library_root: ./library",
                "defaults:",
                "  client: Scotiabank",
                "  engagement: AI Platform",
                "  type: internal_sync",
                "  date: '2026-04-16'",
                "  participants:",
                "    - Jonathan Oh",
                "  derive:",
                "    date:",
                "      - from: filename.regex",
                "        pattern: '^(\\d{4}-\\d{2}-\\d{2})_'",
            ]
        )
    )

    config = FolioConfig.load(config_path)

    assert config.defaults.client == "Scotiabank"
    assert config.defaults.engagement == "AI Platform"
    assert config.defaults.type == "internal_sync"
    assert config.defaults.participants == ["Jonathan Oh"]
    assert config.defaults.derive["date"][0]["from"] == "filename.regex"


def test_config_loads_defaults_block_when_providers_are_configured(tmp_path):
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(
        "\n".join(
            [
                "library_root: ./library",
                "defaults:",
                "  client: Scotiabank",
                "providers:",
                "  anthropic:",
                "    rate_limit_rpm: 12",
            ]
        )
    )

    config = FolioConfig.load(config_path)

    assert config.defaults.client == "Scotiabank"
    assert config.providers["anthropic"].rate_limit_rpm == 12


def test_ingest_resolution_precedence_cli_then_derive_then_defaults(tmp_path):
    source = tmp_path / "2026-04-17_workshop.md"
    source.write_text("# Workshop\n")
    config = FolioConfig(
        library_root=tmp_path / "library",
    )
    config.defaults.type = "internal_sync"
    config.defaults.date = "2026-01-01"
    config.defaults.client = "Default Client"
    config.defaults.engagement = "Default Engagement"
    config.defaults.participants = ["Default Participant"]
    config.defaults.target_root = str(tmp_path / "library")
    config.defaults.target = "{target_root}/{client_slug}/{engagement_slug}/{type}"
    config.defaults.derive = {
        "date": [{"from": "filename.regex", "pattern": "^(\\d{4}-\\d{2}-\\d{2})_"}],
        "type": [
            {"rule": "filename_contains", "substring": "workshop", "type": "workshop"},
        ],
    }

    resolved = resolve_ingest_metadata(
        config,
        source_path=source,
        client="CLI Client",
        engagement="CLI Engagement",
        subtype="client_meeting",
        event_date=date(2026, 4, 18),
    )

    assert resolved.client == "CLI Client"
    assert resolved.engagement == "CLI Engagement"
    assert resolved.subtype == "client_meeting"
    assert resolved.event_date == date(2026, 4, 18)
    assert resolved.participants == ["Default Participant"]
    assert resolved.target == (
        tmp_path / "library" / "cli_client" / "cli_engagement" / "client_meeting"
    )

    resolved = resolve_ingest_metadata(
        config,
        source_path=source,
        subtype=None,
        event_date=None,
    )

    assert resolved.client == "Default Client"
    assert resolved.engagement == "Default Engagement"
    assert resolved.subtype == "workshop"
    assert resolved.event_date == date(2026, 4, 17)
    assert resolved.participants == ["Default Participant"]
    assert resolved.target == (
        tmp_path / "library" / "default_client" / "default_engagement" / "workshop"
    )


def test_ingest_resolution_derives_client_and_engagement_from_source_root(tmp_path):
    source_root = tmp_path / "source"
    source = source_root / "ClientA" / "ProjectX" / "2026-04-17_sync.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Sync\n")
    config = FolioConfig(
        library_root=tmp_path / "library",
        sources=[SourceConfig(name="meetings", path=str(source_root))],
    )
    config.defaults.type = "internal_sync"
    config.defaults.date = "2026-04-17"
    config.defaults.derive = {
        "client": [{"from": "source_root.client"}],
        "engagement": [{"from": "source_root.engagement"}],
    }

    resolved = resolve_ingest_metadata(
        config,
        source_path=source,
        subtype=None,
        event_date=None,
    )

    assert resolved.client == "ClientA"
    assert resolved.engagement == "ProjectX"


def test_convert_resolution_uses_source_root_then_defaults_for_target_template(tmp_path):
    library = tmp_path / "library"
    source_root = tmp_path / "source"
    source = source_root / "Scotiabank" / "AI Platform" / "brief.docx"
    source.parent.mkdir(parents=True)
    source.write_text("placeholder")
    config = FolioConfig(
        library_root=library,
        sources=[SourceConfig(name="research", path=str(source_root))],
        config_dir=tmp_path,
    )
    config.defaults.client = "Default Client"
    config.defaults.engagement = "Default Engagement"
    config.defaults.target_root = str(library)
    config.defaults.target = "{target_root}/{client_slug}/{engagement_slug}"

    resolved = resolve_convert_metadata(config, source_path=source)

    assert resolved.client == "Scotiabank"
    assert resolved.engagement == "AI Platform"
    assert resolved.target == library / "scotiabank" / "ai_platform"

    resolved = resolve_convert_metadata(
        config,
        source_path=source,
        client="CLI Client",
        engagement="CLI Engagement",
    )

    assert resolved.client == "CLI Client"
    assert resolved.engagement == "CLI Engagement"
    assert resolved.target == library / "cli_client" / "cli_engagement"


def test_ingest_resolution_errors_after_defaults_exhausted(tmp_path):
    source = tmp_path / "note.md"
    source.write_text("# Note\n")

    with pytest.raises(DefaultResolutionError, match="--type"):
        resolve_ingest_metadata(
            FolioConfig(library_root=tmp_path / "library"),
            source_path=source,
            subtype=None,
            event_date=None,
        )


def test_ingest_cli_accepts_missing_type_and_date_for_resolver(tmp_path):
    library = tmp_path / "library"
    source = tmp_path / "2026-04-17_sync.md"
    source.write_text("# Sync\n")
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(
        "\n".join(
            [
                f"library_root: {library}",
                "defaults:",
                "  type: internal_sync",
                "  derive:",
                "    date:",
                "      - from: filename.regex",
                "        pattern: '^(\\d{4}-\\d{2}-\\d{2})_'",
            ]
        )
    )

    with patch(
        "folio.cli.ingest_source",
        return_value=IngestResult(
            interaction_id="test",
            output_path=library / "sync.md",
            version=1,
            review_status="clean",
            llm_status="executed",
        ),
    ) as mock_ingest:
        result = CliRunner().invoke(cli, ["--config", str(config_path), "ingest", str(source)])

    assert result.exit_code == 0, result.output
    assert mock_ingest.call_args.kwargs["subtype"] is None
    assert mock_ingest.call_args.kwargs["event_date"] is None
