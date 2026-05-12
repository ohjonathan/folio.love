"""Tests for native EML correspondence ingest."""

from __future__ import annotations

import json
from email.message import EmailMessage
from pathlib import Path

import yaml

from folio.config import FolioConfig
from folio.correspondence import ingest_email, parse_eml


def _write_eml(
    path: Path,
    *,
    message_id: str,
    subject: str = "Vendor Decision",
    body: str = "Initial recommendation: use Azure for the pilot.",
    references: str = "",
) -> None:
    msg = EmailMessage()
    msg["From"] = "Jonathan Oh <jonathan@mckinsey.com>"
    msg["To"] = "Client Lead <lead@client.com>"
    msg["Cc"] = "Partner <partner@mckinsey.com>"
    msg["Date"] = "Fri, 17 Apr 2026 10:15:00 -0400"
    msg["Subject"] = subject
    msg["Message-ID"] = message_id
    if references:
        msg["References"] = references
        msg["In-Reply-To"] = references.split()[-1]
    msg.set_content(body)
    msg.add_attachment(
        b"contract bytes",
        maintype="application",
        subtype="octet-stream",
        filename="SOW_v9.docx",
    )
    path.write_bytes(msg.as_bytes())


def _parse_frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text().split("---", 2)[1].strip())


def test_parse_eml_extracts_headers_message_ids_body_and_attachments(tmp_path):
    source = tmp_path / "thread.eml"
    _write_eml(source, message_id="<msg-1@example.com>")

    thread = parse_eml(source)

    assert thread.subject == "Vendor Decision"
    assert thread.sender == "Jonathan Oh <jonathan@mckinsey.com>"
    assert thread.recipients_to == ["Client Lead <lead@client.com>"]
    assert thread.message_ids == ["<msg-1@example.com>"]
    assert thread.attachments[0].filename == "SOW_v9.docx"
    assert "Azure for the pilot" in thread.body_text


def test_ingest_email_writes_correspondence_note_and_registry(tmp_path):
    library = tmp_path / "library"
    source = tmp_path / "thread.eml"
    _write_eml(source, message_id="<msg-1@example.com>")

    result = ingest_email(
        FolioConfig(library_root=library),
        source_path=source,
        client="Scotiabank",
        engagement="AI Platform",
    )

    assert result.version == 1
    fm = _parse_frontmatter(result.output_path)
    assert fm["type"] == "correspondence"
    assert fm["subtype"] == "email_thread"
    assert fm["source_type"] == "email"
    assert fm["sender"] == "Jonathan Oh <jonathan@mckinsey.com>"
    assert fm["message_ids"] == ["<msg-1@example.com>"]
    assert fm["attachment_count"] == 1
    assert fm["external_thread"] is True
    assert "## Messages" in result.output_path.read_text()

    registry = json.loads((library / "registry.json").read_text())
    entry = registry["decks"][result.correspondence_id]
    assert entry["type"] == "correspondence"
    assert entry["message_ids"] == ["<msg-1@example.com>"]


def test_message_id_overlap_versions_existing_thread(tmp_path):
    library = tmp_path / "library"
    first_source = tmp_path / "thread_v1.eml"
    second_source = tmp_path / "thread_v2.eml"
    _write_eml(first_source, message_id="<msg-1@example.com>")
    _write_eml(
        second_source,
        message_id="<msg-2@example.com>",
        body="Updated recommendation: Azure pilot, GCP later.",
        references="<msg-1@example.com>",
    )
    config = FolioConfig(library_root=library)

    first = ingest_email(config, source_path=first_source, client="ClientA")
    second = ingest_email(config, source_path=second_source, client="ClientA")

    assert second.correspondence_id == first.correspondence_id
    assert second.version == 2
    fm = _parse_frontmatter(second.output_path)
    assert fm["message_ids"] == ["<msg-1@example.com>", "<msg-2@example.com>"]
    assert "GCP later" in second.output_path.read_text()


def test_as_new_entry_ignores_message_id_overlap(tmp_path):
    library = tmp_path / "library"
    first_source = tmp_path / "thread_v1.eml"
    second_source = tmp_path / "thread_v2.eml"
    _write_eml(first_source, message_id="<msg-1@example.com>")
    _write_eml(
        second_source,
        message_id="<msg-2@example.com>",
        body="Forked conversation with a different audience.",
        references="<msg-1@example.com>",
    )
    config = FolioConfig(library_root=library)

    first = ingest_email(config, source_path=first_source, client="ClientA")
    second = ingest_email(
        config,
        source_path=second_source,
        client="ClientA",
        as_new_entry=True,
    )

    assert second.correspondence_id != first.correspondence_id
    assert second.version == 1
