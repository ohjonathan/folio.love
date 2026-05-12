"""Default and derived metadata resolution for Folio commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from email.parser import BytesParser
from email.policy import default as email_policy
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import Optional

import yaml

from .config import FolioConfig
from .naming import sanitize_token

_DATE_PREFIX_RE = re.compile(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})")


class DefaultResolutionError(RuntimeError):
    """Raised when required metadata remains unresolved."""


@dataclass(frozen=True)
class ResolvedIngestMetadata:
    client: str | None
    engagement: str | None
    subtype: str
    event_date: date
    participants: list[str] | None
    target: Path | None


@dataclass(frozen=True)
class ResolvedConvertMetadata:
    client: str | None
    engagement: str | None
    target: Path | None


def resolve_ingest_metadata(
    config: FolioConfig,
    *,
    source_path: Path,
    client: str | None = None,
    engagement: str | None = None,
    subtype: str | None = None,
    event_date: date | None = None,
    participants: list[str] | None = None,
    target: Path | None = None,
) -> ResolvedIngestMetadata:
    """Resolve ingest metadata using CLI, derivation, defaults, then error."""

    source_path = Path(source_path)
    inferred_client, inferred_engagement = _infer_convert_source_root(config, source_path)
    resolved_client = (
        client
        or _derive_text_field(config, "client", source_path, source_root_value=inferred_client)
        or config.defaults.client
    )
    resolved_engagement = (
        engagement
        or _derive_text_field(
            config,
            "engagement",
            source_path,
            source_root_value=inferred_engagement,
        )
        or config.defaults.engagement
    )
    derived_participants = (
        participants
        if participants is not None
        else _derive_participants(config, source_path)
    )
    if derived_participants is None and config.defaults.participants:
        derived_participants = list(config.defaults.participants)

    resolved_type = (
        subtype
        or _derive_type(config, source_path, derived_participants)
        or config.defaults.type
    )
    resolved_date = (
        event_date
        or _derive_date(config, source_path)
        or _parse_date(config.defaults.date)
    )
    resolved_target = target or _derive_target(
        config,
        source_path,
        resolved_type,
        client=resolved_client,
        engagement=resolved_engagement,
    ) or _default_target(config)

    missing: list[str] = []
    if not resolved_type:
        missing.append("--type")
    if resolved_date is None:
        missing.append("--date")
    if missing:
        raise DefaultResolutionError(
            "Missing required ingest metadata after defaults/derive resolution: "
            + ", ".join(missing)
        )

    return ResolvedIngestMetadata(
        client=resolved_client,
        engagement=resolved_engagement,
        subtype=resolved_type,
        event_date=resolved_date,
        participants=derived_participants,
        target=resolved_target,
    )


def resolve_convert_metadata(
    config: FolioConfig,
    *,
    source_path: Path,
    client: str | None = None,
    engagement: str | None = None,
    target: Path | None = None,
) -> ResolvedConvertMetadata:
    """Resolve convert client/engagement/target with source-root derivation."""

    inferred_client, inferred_engagement = _infer_convert_source_root(config, source_path)
    resolved_client = (
        client
        or _derive_text_field(config, "client", source_path, source_root_value=inferred_client)
        or inferred_client
        or config.defaults.client
    )
    resolved_engagement = (
        engagement
        or _derive_text_field(
            config,
            "engagement",
            source_path,
            source_root_value=inferred_engagement,
        )
        or inferred_engagement
        or config.defaults.engagement
    )
    resolved_target = target or _derive_target(
        config,
        source_path,
        None,
        client=resolved_client,
        engagement=resolved_engagement,
    ) or _default_target(config)
    return ResolvedConvertMetadata(
        client=resolved_client,
        engagement=resolved_engagement,
        target=resolved_target,
    )


def _derive_date(config: FolioConfig, source_path: Path) -> date | None:
    rules = _derive_rules(config, "date")
    if not rules:
        rules = [
            {"from": "eml.date"},
            {"from": "markdown.frontmatter.date"},
            {"from": "filename.regex"},
        ]
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        source = rule.get("from")
        if source == "eml.date":
            value = _date_from_eml(source_path)
        elif source == "markdown.frontmatter.date":
            value = _date_from_markdown_frontmatter(source_path)
        elif source == "filename.regex":
            value = _date_from_filename(source_path, pattern=rule.get("pattern"))
        elif source == "file.mtime":
            value = date.fromtimestamp(source_path.stat().st_mtime)
        else:
            value = None
        if value is not None:
            return value
    return None


def _derive_participants(config: FolioConfig, source_path: Path) -> list[str] | None:
    rules = _derive_rules(config, "participants")
    if not rules:
        rules = [
            {"from": "eml.headers"},
            {"from": "markdown.frontmatter.participants"},
        ]
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        source = rule.get("from")
        if source == "eml.headers":
            values = _participants_from_eml(source_path)
        elif source == "markdown.frontmatter.participants":
            values = _participants_from_markdown_frontmatter(source_path)
        else:
            values = None
        if values:
            return values
    return None


def _derive_type(
    config: FolioConfig,
    source_path: Path,
    participants: list[str] | None,
) -> str | None:
    for rule in _derive_rules(config, "type"):
        if not isinstance(rule, dict):
            continue
        if "default" in rule:
            return str(rule["default"]).strip() or None
        rule_name = rule.get("rule")
        if rule_name == "all_participants_match_domain":
            domain = str(rule.get("domain", "")).lower()
            if domain and participants and all(domain in p.lower() for p in participants):
                return _rule_type(rule)
        elif rule_name == "any_participant_matches_domain":
            domain = str(rule.get("domain", "")).lower()
            if domain and participants and any(domain in p.lower() for p in participants):
                return _rule_type(rule)
        elif rule_name == "filename_contains":
            substring = str(rule.get("substring", ""))
            if substring and substring.lower() in source_path.name.lower():
                return _rule_type(rule)
    return None


def _derive_text_field(
    config: FolioConfig,
    key: str,
    source_path: Path,
    *,
    source_root_value: str | None = None,
) -> str | None:
    for rule in _derive_rules(config, key):
        if not isinstance(rule, dict):
            continue
        if "default" in rule:
            value = str(rule["default"]).strip()
            if value:
                return value
        source = rule.get("from")
        if source == f"source_root.{key}":
            value = source_root_value
        elif source == f"markdown.frontmatter.{key}":
            value = _metadata_from_markdown_frontmatter(source_path, key)
        elif source == "filename.regex":
            value = _text_from_filename(source_path, pattern=rule.get("pattern"))
        else:
            value = None
        if value:
            return value
    return None


def _derive_target(
    config: FolioConfig,
    source_path: Path,
    subtype: str | None,
    *,
    client: str | None = None,
    engagement: str | None = None,
) -> Path | None:
    for rule in _derive_rules(config, "target"):
        if not isinstance(rule, dict):
            continue
        if rule.get("rule") == "type_is" and rule.get("type") != subtype:
            continue
        target_template = rule.get("target")
        if target_template:
            return _resolve_template_path(
                config,
                str(target_template),
                subtype,
                client=client,
                engagement=engagement,
            )
    if config.defaults.target:
        return _resolve_template_path(
            config,
            config.defaults.target,
            subtype,
            client=client,
            engagement=engagement,
        )
    return None


def _default_target(config: FolioConfig) -> Path | None:
    return None


def _derive_rules(config: FolioConfig, key: str) -> list[dict]:
    value = (config.defaults.derive or {}).get(key, [])
    if isinstance(value, list):
        return value
    return []


def _rule_type(rule: dict) -> str | None:
    value = rule.get("type")
    return str(value).strip() if value is not None else None


def _date_from_filename(source_path: Path, *, pattern: object = None) -> date | None:
    if pattern:
        match = re.search(str(pattern), source_path.name)
        if match:
            value = match.group(1) if match.groups() else match.group(0)
            return _parse_date(value)
    match = _DATE_PREFIX_RE.search(source_path.name)
    if not match:
        return None
    return _parse_date("-".join(match.groups()))


def _date_from_markdown_frontmatter(source_path: Path) -> date | None:
    if source_path.suffix.lower() != ".md":
        return None
    fm = _read_markdown_frontmatter(source_path)
    if not fm:
        return None
    return _parse_date(fm.get("date"))


def _metadata_from_markdown_frontmatter(source_path: Path, key: str) -> str | None:
    if source_path.suffix.lower() != ".md":
        return None
    fm = _read_markdown_frontmatter(source_path)
    if not fm:
        return None
    value = fm.get(key)
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _text_from_filename(source_path: Path, *, pattern: object = None) -> str | None:
    if not pattern:
        return None
    match = re.search(str(pattern), source_path.name)
    if not match:
        return None
    value = match.group(1) if match.groups() else match.group(0)
    cleaned = str(value).strip()
    return cleaned or None


def _participants_from_markdown_frontmatter(source_path: Path) -> list[str] | None:
    if source_path.suffix.lower() != ".md":
        return None
    fm = _read_markdown_frontmatter(source_path)
    if not fm:
        return None
    raw = fm.get("participants")
    if isinstance(raw, list):
        return _dedupe([str(item) for item in raw])
    if isinstance(raw, str):
        return _dedupe(raw.split(","))
    return None


def _read_markdown_frontmatter(source_path: Path) -> dict | None:
    try:
        text = source_path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            try:
                parsed = yaml.safe_load("\n".join(lines[1:index]))
            except yaml.YAMLError:
                return None
            return parsed if isinstance(parsed, dict) else None
    return None


def _date_from_eml(source_path: Path) -> date | None:
    if source_path.suffix.lower() != ".eml":
        return None
    msg = _read_email_message(source_path)
    if msg is None:
        return None
    raw_date = msg.get("date")
    if not raw_date:
        return None
    try:
        parsed = parsedate_to_datetime(raw_date)
    except (TypeError, ValueError):
        return None
    return parsed.date()


def _participants_from_eml(source_path: Path) -> list[str] | None:
    if source_path.suffix.lower() != ".eml":
        return None
    msg = _read_email_message(source_path)
    if msg is None:
        return None
    addresses = getaddresses(
        [msg.get("from", ""), msg.get("to", ""), msg.get("cc", "")]
    )
    values = []
    for name, address in addresses:
        label = name.strip() or address.strip()
        if address and address not in label:
            label = f"{label} <{address}>"
        values.append(label)
    return _dedupe(values)


def _read_email_message(source_path: Path):
    try:
        with source_path.open("rb") as fh:
            return BytesParser(policy=email_policy).parse(fh)
    except OSError:
        return None


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _resolve_template_path(
    config: FolioConfig,
    template: str,
    subtype: str | None,
    *,
    client: str | None = None,
    engagement: str | None = None,
) -> Path:
    target_root = config.defaults.target_root or str(config.library_root)
    resolved_client = client if client is not None else config.defaults.client
    resolved_engagement = (
        engagement if engagement is not None else config.defaults.engagement
    )
    values = {
        "target_root": target_root.rstrip("/"),
        "client": resolved_client or "",
        "client_slug": sanitize_token(resolved_client or ""),
        "engagement": resolved_engagement or "",
        "engagement_slug": sanitize_token(resolved_engagement or ""),
        "type": subtype or "",
    }
    rendered = template.format(**values)
    path = Path(rendered).expanduser()
    if not path.is_absolute() and config.config_dir is not None:
        path = config.config_dir / path
    return path


def _infer_convert_source_root(
    config: FolioConfig,
    source_path: Path,
) -> tuple[str | None, str | None]:
    match = config.match_source_root(source_path)
    if not match:
        return (None, None)
    src_config, rel_path = match
    prefix = FolioConfig.normalize_target_prefix(src_config.target_prefix)
    if prefix:
        return (None, None)
    parts = rel_path.parent.parts
    if len(parts) >= 2:
        return (parts[0], parts[1])
    if len(parts) == 1:
        return (parts[0], None)
    return (None, None)


def _dedupe(values: list[str]) -> list[str] | None:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        cleaned = str(raw).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result or None
