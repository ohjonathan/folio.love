"""Tests for folder-based watch routing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from folio.cli import cli
from folio.config import FolioConfig
from folio.watch import route_file, run_watch_once


def test_route_file_by_extension():
    assert route_file("deck.pptx") == "convert"
    assert route_file("doc.docx") == "convert"
    assert route_file("thread.eml") == "ingest_email"
    assert route_file("meeting.vtt") == "ingest"
    assert route_file("image.png") == "skip"


def test_watch_once_dry_run_routes_without_moving(tmp_path):
    source = tmp_path / "meeting.vtt"
    source.write_text("WEBVTT\n")
    messages: list[str] = []

    results = run_watch_once(
        FolioConfig(library_root=tmp_path / "library"),
        tmp_path,
        dry_run=True,
        emit=messages.append,
    )

    assert results[0].action == "ingest"
    assert results[0].outcome == "dry_run"
    assert source.exists()
    assert "dry-run" in messages[0]


def test_watch_once_archives_success(tmp_path):
    source = tmp_path / "deck.docx"
    source.write_bytes(b"docx")
    output = tmp_path / "library" / "deck.md"

    with patch(
        "folio.watch.FolioConverter.convert",
        return_value=SimpleNamespace(output_path=output),
    ) as mock_convert:
        results = run_watch_once(
            FolioConfig(library_root=tmp_path / "library"),
            tmp_path,
            stability_seconds=0,
        )

    assert results[0].outcome == "success"
    assert mock_convert.call_args.kwargs["source_path"] == source
    assert not source.exists()
    assert (tmp_path / "_archive" / "deck.docx").exists()


def test_watch_once_writes_failure_log(tmp_path):
    source = tmp_path / "thread.eml"
    source.write_text("not really an email")

    with patch("folio.watch.ingest_email", side_effect=RuntimeError("boom")):
        results = run_watch_once(
            FolioConfig(library_root=tmp_path / "library"),
            tmp_path,
            stability_seconds=0,
        )

    assert results[0].outcome == "failed"
    assert results[0].output_path == tmp_path / "_failed" / "thread.eml"
    logs = list((tmp_path / "_failed").glob("thread.eml.error.log*"))
    assert logs
    assert "boom" in logs[0].read_text()
    assert not source.exists()
    assert (tmp_path / "_failed" / "thread.eml").exists()

    with patch("folio.watch.ingest_email", side_effect=RuntimeError("boom")):
        rerun_results = run_watch_once(
            FolioConfig(library_root=tmp_path / "library"),
            tmp_path,
            stability_seconds=0,
        )

    assert rerun_results == []


def test_watch_cli_once_dry_run(tmp_path):
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(f"library_root: {tmp_path / 'library'}\n")
    (tmp_path / "meeting.txt").write_text("Meeting notes")

    result = CliRunner().invoke(
        cli,
        ["--config", str(config_path), "watch", str(tmp_path), "--once", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
