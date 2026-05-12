"""CLI tests for correspondence ingest."""

from __future__ import annotations

from email.message import EmailMessage

from click.testing import CliRunner
import yaml

from folio.cli import cli


def _write_eml(path, *, message_id="<msg-1@example.com>") -> None:
    msg = EmailMessage()
    msg["From"] = "Jonathan Oh <jonathan@mckinsey.com>"
    msg["To"] = "Client Lead <lead@client.com>"
    msg["Date"] = "Fri, 17 Apr 2026 10:15:00 -0400"
    msg["Subject"] = "Vendor Decision"
    msg["Message-ID"] = message_id
    msg.set_content("Use Azure for the pilot.")
    path.write_bytes(msg.as_bytes())


def test_ingest_email_command(tmp_path):
    library = tmp_path / "library"
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(f"library_root: {library}\n")
    source = tmp_path / "thread.eml"
    _write_eml(source)

    result = CliRunner().invoke(
        cli,
        ["--config", str(config_path), "ingest-email", str(source), "--client", "ClientA"],
    )

    assert result.exit_code == 0, result.output
    assert "Vendor Decision" not in result.output
    assert "Review: clean" in result.output


def test_ingest_routes_eml_to_correspondence(tmp_path):
    library = tmp_path / "library"
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(f"library_root: {library}\n")
    source = tmp_path / "thread.eml"
    _write_eml(source)

    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(config_path),
            "ingest",
            str(source),
            "--type",
            "email_thread",
            "--client",
            "ClientA",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Review: clean" in result.output


def test_ingest_eml_route_preserves_cli_date_and_participants_precedence(tmp_path):
    library = tmp_path / "library"
    config_path = tmp_path / "folio.yaml"
    config_path.write_text(f"library_root: {library}\n")
    source = tmp_path / "thread.eml"
    _write_eml(source)

    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(config_path),
            "ingest",
            str(source),
            "--type",
            "email_thread",
            "--date",
            "2026-04-18",
            "--participants",
            "Explicit One, Explicit Two",
        ],
    )

    assert result.exit_code == 0, result.output
    [note_path] = library.glob("**/*.md")
    frontmatter = yaml.safe_load(note_path.read_text().split("---", 2)[1].strip())
    assert frontmatter["date"] == "2026-04-18"
    assert frontmatter["participants"] == ["Explicit One", "Explicit Two"]
