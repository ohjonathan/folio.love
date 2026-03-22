"""Tests for the `folio ingest` CLI command."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from folio.cli import cli
from folio.ingest import IngestResult


def _make_config(path: Path, library_root: Path) -> None:
    path.write_text(yaml.dump({"library_root": str(library_root)}, default_flow_style=False))


def _make_source(path: Path, content: str = "Transcript content.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _ingest_result(*, llm_status: str = "executed", review_status: str = "clean") -> IngestResult:
    return IngestResult(
        interaction_id="clienta_ddq126_interview_20260321_cto_interview_notes",
        output_path=Path("/tmp/output/2026-03-21_cto_interview_notes.md"),
        version=3,
        review_status=review_status,
        llm_status=llm_status,
    )


class TestIngestCommand:
    @patch("folio.cli.ingest_source")
    def test_ingest_forwards_options(self, mock_ingest_source, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)

        source = tmp_path / "transcripts" / "expert_interview.md"
        _make_source(source)
        recording = tmp_path / "recordings" / "expert_interview.wav"
        _make_source(recording, "audio")
        target = tmp_path / "custom-target"

        mock_ingest_source.return_value = _ingest_result()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--type",
                "expert_interview",
                "--date",
                "2026-03-21",
                "--client",
                "ClientA",
                "--engagement",
                "DD Q1 2026",
                "--participants",
                "Jane Smith, Jane Smith, Johnny Oh",
                "--duration-minutes",
                "45",
                "--source-recording",
                str(recording),
                "--title",
                "CTO Interview Notes",
                "--target",
                str(target),
                "--llm-profile",
                "anthropic_sonnet",
                "--note",
                "initial ingest",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "✓ expert_interview.md" in result.output
        assert "Review: clean" in result.output
        assert "analysis unavailable" not in result.output

        call_kwargs = mock_ingest_source.call_args.kwargs
        assert call_kwargs["source_path"] == source
        assert call_kwargs["subtype"] == "expert_interview"
        assert call_kwargs["event_date"] == date(2026, 3, 21)
        assert call_kwargs["client"] == "ClientA"
        assert call_kwargs["engagement"] == "DD Q1 2026"
        assert call_kwargs["participants"] == ["Jane Smith", "Johnny Oh"]
        assert call_kwargs["duration_minutes"] == 45
        assert call_kwargs["source_recording"] == recording
        assert call_kwargs["title"] == "CTO Interview Notes"
        assert call_kwargs["target"] == target
        assert call_kwargs["llm_profile"] == "anthropic_sonnet"
        assert call_kwargs["note"] == "initial ingest"

    @patch("folio.cli.ingest_source")
    def test_ingest_reports_degraded_output(self, mock_ingest_source, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)

        source = tmp_path / "transcripts" / "client_meeting.txt"
        _make_source(source)
        mock_ingest_source.return_value = _ingest_result(llm_status="pending", review_status="flagged")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--type",
                "client_meeting",
                "--date",
                "2026-03-21",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "analysis unavailable" in result.output
        assert "Review: flagged" in result.output

    def test_ingest_requires_type(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)
        source = tmp_path / "transcripts" / "client_meeting.txt"
        _make_source(source)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--date",
                "2026-03-21",
            ],
        )

        assert result.exit_code != 0
        assert "Missing option '--type'" in result.output

    def test_ingest_requires_date(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)
        source = tmp_path / "transcripts" / "client_meeting.txt"
        _make_source(source)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--type",
                "client_meeting",
            ],
        )

        assert result.exit_code != 0
        assert "Missing option '--date'" in result.output

    def test_ingest_rejects_invalid_date_format(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)
        source = tmp_path / "transcripts" / "client_meeting.txt"
        _make_source(source)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--type",
                "client_meeting",
                "--date",
                "not-a-date",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid value for '--date'" in result.output

    @patch("folio.cli.ingest_source")
    def test_ingest_uses_local_date_for_future_check(self, mock_ingest_source, tmp_path, monkeypatch):
        class _LocalDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                assert tz is None
                return cls(2026, 3, 21, 23, 30, 0)

        monkeypatch.setattr("folio.cli.datetime", _LocalDateTime)

        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)
        source = tmp_path / "transcripts" / "client_meeting.txt"
        _make_source(source)
        mock_ingest_source.return_value = _ingest_result()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--type",
                "client_meeting",
                "--date",
                "2026-03-21",
            ],
        )

        assert result.exit_code == 0, result.output

    def test_ingest_rejects_invalid_extension(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)
        source = tmp_path / "transcripts" / "client_meeting.pdf"
        _make_source(source)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--type",
                "client_meeting",
                "--date",
                "2026-03-21",
            ],
        )

        assert result.exit_code != 0
        assert "supports .txt and .md only" in result.output

    def test_ingest_rejects_missing_source_file(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(tmp_path / "transcripts" / "missing.txt"),
                "--type",
                "client_meeting",
                "--date",
                "2026-03-21",
            ],
        )

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_ingest_rejects_nonexistent_source_recording(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)
        source = tmp_path / "transcripts" / "client_meeting.txt"
        _make_source(source)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--type",
                "client_meeting",
                "--date",
                "2026-03-21",
                "--source-recording",
                str(tmp_path / "missing.wav"),
            ],
        )

        assert result.exit_code != 0
        assert "does not exist" in result.output

    @patch("folio.cli.ingest_source")
    def test_ingest_passes_target_path(self, mock_ingest_source, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, library)
        source = tmp_path / "transcripts" / "client_meeting.txt"
        _make_source(source)
        target = tmp_path / "notes" / "custom.md"
        mock_ingest_source.return_value = _ingest_result()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "ingest",
                str(source),
                "--type",
                "client_meeting",
                "--date",
                "2026-03-21",
                "--target",
                str(target),
            ],
        )

        assert result.exit_code == 0, result.output
        assert mock_ingest_source.call_args.kwargs["target"] == target
