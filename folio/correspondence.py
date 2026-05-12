"""Native correspondence ingestion for RFC 5322 email files."""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.policy import default as email_policy
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import Optional

import yaml

from .config import FolioConfig
from .defaults import DefaultResolutionError, resolve_ingest_metadata
from .naming import derive_engagement_short, humanize_token, sanitize_token
from .tracking import registry, sources, versions
from .tracking.registry import RegistryEntry

EMAIL_EXTENSIONS = frozenset({".eml"})
_MESSAGE_ID_RE = re.compile(r"<[^<>]+>")
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class AttachmentInfo:
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class EmailThread:
    subject: str
    sender: str
    recipients_to: list[str]
    recipients_cc: list[str]
    event_date: date
    body_text: str
    message_ids: list[str]
    attachments: list[AttachmentInfo] = field(default_factory=list)

    @property
    def participants(self) -> list[str]:
        return _dedupe([self.sender, *self.recipients_to, *self.recipients_cc])

    @property
    def external_thread(self) -> bool:
        domains = {
            item.rsplit("@", 1)[1].rstrip(">").lower()
            for item in self.participants
            if "@" in item
        }
        return len(domains) > 1


@dataclass
class CorrespondenceResult:
    correspondence_id: str
    output_path: Path
    version: int
    review_status: str
    skipped: bool = False


class CorrespondenceIngestError(RuntimeError):
    """Raised when correspondence ingestion cannot complete."""


def ingest_email(
    config: FolioConfig,
    *,
    source_path: Path,
    client: Optional[str] = None,
    engagement: Optional[str] = None,
    event_date: date | None = None,
    participants: list[str] | None = None,
    title: Optional[str] = None,
    target: Optional[Path] = None,
    note: Optional[str] = None,
    as_new_entry: bool = False,
) -> CorrespondenceResult:
    """Ingest an RFC 5322 `.eml` file as a correspondence note."""

    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    if source_path.suffix.lower() not in EMAIL_EXTENSIONS:
        raise CorrespondenceIngestError(f"Unsupported email source extension: {source_path.suffix}")

    thread = parse_eml(source_path)
    thread = replace(thread, event_date=event_date or thread.event_date)
    effective_participants = participants if participants is not None else thread.participants

    try:
        resolved = resolve_ingest_metadata(
            config,
            source_path=source_path,
            client=client,
            engagement=engagement,
            subtype="email_thread",
            event_date=thread.event_date,
            participants=effective_participants,
            target=target,
        )
    except DefaultResolutionError as exc:
        raise CorrespondenceIngestError(str(exc)) from exc
    effective_client = resolved.client
    effective_engagement = resolved.engagement
    effective_participants = resolved.participants or effective_participants
    target = resolved.target

    library_root = config.library_root.resolve()
    registry_data = _load_registry_data(library_root)
    source_hash = sources.compute_file_hash(source_path)
    match = None if as_new_entry else _find_message_id_overlap(registry_data, thread.message_ids)
    if match and match.source_hash == source_hash:
        output_path = (library_root / match.markdown_path).resolve()
        return CorrespondenceResult(
            correspondence_id=match.id,
            output_path=output_path,
            version=match.version or 1,
            review_status=match.review_status or "clean",
            skipped=True,
        )

    resolved_title = title or thread.subject or humanize_token(source_path.stem)
    correspondence_id, output_dir, markdown_path, existing_fm = _resolve_output_identity(
        library_root=library_root,
        registry_data=registry_data,
        source_path=source_path,
        source_hash=source_hash,
        thread=thread,
        title=resolved_title,
        client=effective_client,
        engagement=effective_engagement,
        target=target,
        match=match,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    source_info = sources.compute_source_info(source_path, markdown_path)
    version_info = versions.compute_version(
        deck_dir=output_dir,
        source_hash=source_info.file_hash,
        source_path=source_info.relative_path,
        slide_count=1,
        new_texts={1: thread.body_text},
        note=note,
    )
    history = versions.load_version_history(output_dir / "version_history.json")
    all_message_ids = _merge_message_ids(
        getattr(match, "message_ids", None) or [],
        thread.message_ids,
    )
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = _generate_correspondence_frontmatter(
        correspondence_id=correspondence_id,
        title=resolved_title,
        thread=thread,
        source_relative_path=source_info.relative_path,
        source_hash=source_info.file_hash,
        version_info=version_info,
        client=effective_client,
        engagement=effective_engagement,
        participants=effective_participants,
        message_ids=all_message_ids,
        existing_frontmatter=existing_fm,
        now_str=now_str,
    )
    markdown = _assemble_correspondence_markdown(
        title=resolved_title,
        frontmatter=frontmatter,
        source_display_path=source_info.relative_path,
        version_info=version_info,
        thread=thread,
        version_history=history,
    )
    _atomic_write_text(markdown_path, markdown)

    if _is_within(markdown_path, library_root):
        registry.upsert_entry(
            library_root / "registry.json",
            RegistryEntry(
                id=correspondence_id,
                title=resolved_title,
                markdown_path=_relative_to_root(markdown_path, library_root),
                deck_dir=_relative_to_root(output_dir, library_root),
                source_relative_path=source_info.relative_path,
                source_hash=source_info.file_hash,
                source_type="email",
                type="correspondence",
                subtype="email_thread",
                version=version_info.version,
                converted=now_str,
                modified=now_str,
                client=effective_client,
                engagement=effective_engagement,
                authority=(existing_fm or {}).get("authority", "captured"),
                curation_level=(existing_fm or {}).get("curation_level", "L0"),
                staleness_status="current",
                review_status="clean",
                review_flags=[],
                extraction_confidence=1.0,
                message_ids=all_message_ids,
            ),
        )

    return CorrespondenceResult(
        correspondence_id=correspondence_id,
        output_path=markdown_path,
        version=version_info.version,
        review_status="clean",
    )


def parse_eml(source_path: Path) -> EmailThread:
    """Parse a single `.eml` envelope into correspondence metadata."""

    msg = _read_email(source_path)
    subject = _decode_header_value(msg.get("subject", "")) or source_path.stem
    sender = _format_first_address(msg.get("from", ""))
    recipients_to = _format_addresses(msg.get("to", ""))
    recipients_cc = _format_addresses(msg.get("cc", ""))
    event_date = _parse_email_date(msg.get("date")) or date.today()
    body_text = _extract_body_text(msg)
    message_ids = _extract_message_ids(msg)
    attachments = _extract_attachments(msg)
    if not body_text.strip():
        raise CorrespondenceIngestError(f"No text body found in {source_path.name}")
    return EmailThread(
        subject=subject,
        sender=sender,
        recipients_to=recipients_to,
        recipients_cc=recipients_cc,
        event_date=event_date,
        body_text=body_text,
        message_ids=message_ids,
        attachments=attachments,
    )


def _read_email(source_path: Path) -> Message:
    with Path(source_path).open("rb") as fh:
        return BytesParser(policy=email_policy).parse(fh)


def _extract_body_text(msg: Message) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart() or _is_attachment(part):
                continue
            content_type = part.get_content_type()
            payload = _safe_get_content(part)
            if not payload:
                continue
            if content_type == "text/plain":
                plain_parts.append(_clean_email_text(payload))
            elif content_type == "text/html":
                html_parts.append(_html_to_text(payload))
    else:
        payload = _safe_get_content(msg)
        if msg.get_content_type() == "text/html":
            html_parts.append(_html_to_text(payload))
        else:
            plain_parts.append(_clean_email_text(payload))
    return "\n\n".join(part for part in (plain_parts or html_parts) if part).strip()


def _safe_get_content(part: Message) -> str:
    try:
        payload = part.get_content()
    except Exception:
        raw = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        payload = raw.decode(charset, errors="replace")
    return str(payload or "")


def _clean_email_text(value: str) -> str:
    lines = []
    for raw in value.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        stripped = raw.rstrip()
        if not stripped:
            lines.append("")
            continue
        if stripped.lower().startswith(("external sender", "confidentiality notice")):
            continue
        if re.match(r"^_{6,}$", stripped):
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def _html_to_text(value: str) -> str:
    text_value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    text_value = re.sub(r"(?i)</p\s*>", "\n\n", text_value)
    text_value = _TAG_RE.sub("", text_value)
    return _clean_email_text(html.unescape(text_value))


def _extract_message_ids(msg: Message) -> list[str]:
    values = []
    for header in ("message-id", "in-reply-to", "references"):
        raw = msg.get(header, "")
        values.extend(_MESSAGE_ID_RE.findall(str(raw)))
    return _dedupe(values)


def _extract_attachments(msg: Message) -> list[AttachmentInfo]:
    attachments: list[AttachmentInfo] = []
    for part in msg.walk() if msg.is_multipart() else []:
        if not _is_attachment(part):
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename() or "attachment"
        attachments.append(
            AttachmentInfo(
                filename=filename,
                content_type=part.get_content_type(),
                size_bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
            )
        )
    return attachments


def _is_attachment(part: Message) -> bool:
    disposition = (part.get_content_disposition() or "").lower()
    return disposition == "attachment" or bool(part.get_filename())


def _decode_header_value(value: object) -> str:
    return str(value or "").strip()


def _format_first_address(value: str) -> str:
    values = _format_addresses(value)
    return values[0] if values else ""


def _format_addresses(value: str) -> list[str]:
    formatted = []
    for name, address in getaddresses([value or ""]):
        label = name.strip() or address.strip()
        if address and address not in label:
            label = f"{label} <{address}>"
        if label:
            formatted.append(label)
    return _dedupe(formatted)


def _parse_email_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(str(value)).date()
    except (TypeError, ValueError):
        return None


def _find_message_id_overlap(registry_data: dict, message_ids: list[str]) -> RegistryEntry | None:
    wanted = set(message_ids)
    if not wanted:
        return None
    for item in registry_data.get("decks", {}).values():
        if item.get("type") != "correspondence":
            continue
        existing = set(item.get("message_ids") or [])
        if wanted & existing:
            return registry.entry_from_dict(item)
    return None


def _resolve_output_identity(
    *,
    library_root: Path,
    registry_data: dict,
    source_path: Path,
    source_hash: str,
    thread: EmailThread,
    title: str,
    client: Optional[str],
    engagement: Optional[str],
    target: Optional[Path],
    match: RegistryEntry | None,
) -> tuple[str, Path, Path, dict | None]:
    if match is not None:
        markdown_path = (library_root / match.markdown_path).resolve()
        existing_fm = _read_frontmatter(markdown_path)
        return match.id, markdown_path.parent, markdown_path, existing_fm

    artifact = _artifact_name(thread.event_date, source_path.stem, title, source_hash)
    output_dir = _resolve_target_dir(library_root, artifact, client, engagement, target)
    markdown_path = output_dir / f"{artifact}.md"
    correspondence_id = _unique_correspondence_id(
        registry_data,
        thread.event_date,
        title,
        client,
        engagement,
        source_hash,
    )
    return correspondence_id, output_dir, markdown_path, None


def _resolve_target_dir(
    library_root: Path,
    artifact: str,
    client: Optional[str],
    engagement: Optional[str],
    target: Optional[Path],
) -> Path:
    if target is not None:
        target = Path(target).resolve()
        if target.suffix.lower() == ".md":
            return target.parent
        return target
    engagement_short = derive_engagement_short(engagement) if engagement else ""
    if client and engagement:
        return (
            library_root
            / sanitize_token(client)
            / sanitize_token(engagement_short or engagement)
            / "correspondence"
            / artifact
        )
    if client:
        return library_root / sanitize_token(client) / "correspondence" / artifact
    return library_root / "correspondence" / artifact


def _artifact_name(event_date: date, source_stem: str, title: str, source_hash: str) -> str:
    descriptor = sanitize_token(title) or sanitize_token(source_stem)
    return f"{event_date.strftime('%Y-%m-%d')}_{descriptor}_{source_hash[:8]}"


def _unique_correspondence_id(
    registry_data: dict,
    event_date: date,
    title: str,
    client: Optional[str],
    engagement: Optional[str],
    source_hash: str,
) -> str:
    parts = []
    if client:
        parts.append(sanitize_token(client))
    if engagement:
        parts.append(sanitize_token(engagement))
    parts.extend(["correspondence", event_date.strftime("%Y%m%d"), sanitize_token(title)])
    candidate = "_".join(part for part in parts if part)
    if candidate not in registry_data.get("decks", {}):
        return candidate
    return f"{candidate}_{source_hash[:8]}"


def _generate_correspondence_frontmatter(
    *,
    correspondence_id: str,
    title: str,
    thread: EmailThread,
    source_relative_path: str,
    source_hash: str,
    version_info: versions.VersionInfo,
    client: Optional[str],
    engagement: Optional[str],
    participants: list[str],
    message_ids: list[str],
    existing_frontmatter: dict | None,
    now_str: str,
) -> str:
    created = now_str
    authority = "captured"
    curation_level = "L0"
    if isinstance(existing_frontmatter, dict):
        created = existing_frontmatter.get("created") or created
        authority = existing_frontmatter.get("authority") or authority
        curation_level = existing_frontmatter.get("curation_level") or curation_level
    fm = {
        "id": correspondence_id,
        "title": title,
        "type": "correspondence",
        "subtype": "email_thread",
        "status": "active",
        "authority": authority,
        "curation_level": curation_level,
        "review_status": "clean",
        "review_flags": [],
        "extraction_confidence": 1.0,
        "source": source_relative_path,
        "source_hash": source_hash,
        "source_type": "email",
        "version": version_info.version,
        "created": created,
        "modified": now_str,
        "converted": now_str,
        "date": thread.event_date.isoformat(),
        "sender": thread.sender,
        "recipients_to": thread.recipients_to,
        "recipients_cc": thread.recipients_cc,
        "participants": participants,
        "thread_message_count": len(message_ids) or 1,
        "attachment_count": len(thread.attachments),
        "external_thread": thread.external_thread,
        "message_ids": message_ids,
        "attachments": [attachment.__dict__ for attachment in thread.attachments],
    }
    if client:
        fm["client"] = client
    if engagement:
        fm["engagement"] = engagement
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---"


def _assemble_correspondence_markdown(
    *,
    title: str,
    frontmatter: str,
    source_display_path: str,
    version_info: versions.VersionInfo,
    thread: EmailThread,
    version_history: list[dict],
) -> str:
    lines = [
        frontmatter,
        "",
        f"# {title}",
        "",
        f"Source email: `{source_display_path}` | Version: {version_info.version}",
        "",
        "## Messages",
        "",
        f"### {thread.event_date.isoformat()} — {thread.sender}",
        "",
        f"To: {', '.join(thread.recipients_to) if thread.recipients_to else 'None'}",
        "",
    ]
    if thread.recipients_cc:
        lines.extend([f"CC: {', '.join(thread.recipients_cc)}", ""])
    lines.extend(thread.body_text.splitlines())
    lines.append("")
    lines.extend(["## Attachments", ""])
    if thread.attachments:
        for attachment in thread.attachments:
            lines.append(
                f"- {attachment.filename} ({attachment.content_type}, {attachment.size_bytes} bytes, sha256: {attachment.sha256})"
            )
    else:
        lines.append("- None")
    lines.append("")
    if version_history:
        lines.extend(["## Version History", ""])
        lines.extend(
            f"- v{item.get('version')}: {item.get('timestamp')} ({item.get('source_path')})"
            for item in version_history
        )
    return "\n".join(lines).rstrip() + "\n"


def _merge_message_ids(existing: list[str], new: list[str]) -> list[str]:
    return _dedupe([*existing, *new])


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _load_registry_data(library_root: Path) -> dict:
    registry_path = library_root / "registry.json"
    if registry_path.exists():
        data = registry.load_registry(registry_path)
        if data.get("_corrupt"):
            data = registry.rebuild_registry(library_root)
            registry.save_registry(registry_path, data)
        return data
    if library_root.exists():
        data = registry.rebuild_registry(library_root)
        registry.save_registry(registry_path, data)
        return data
    return {"_schema_version": 1, "decks": {}}


def _read_frontmatter(md_path: Path) -> dict | None:
    if not md_path.exists():
        return None
    content = md_path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return None
    end = content.find("\n---", 4)
    if end == -1:
        return None
    parsed = yaml.safe_load(content[4:end])
    return parsed if isinstance(parsed, dict) else None


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content)
    tmp_path.replace(path)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _relative_to_root(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
