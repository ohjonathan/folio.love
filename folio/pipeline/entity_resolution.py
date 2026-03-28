"""Entity resolution for interaction ingest."""

from __future__ import annotations

import json
import logging
import re
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..llm import ProviderInput, RateLimiter, execute_with_retry, get_provider
from ..llm.types import FallbackProfileSpec, ProviderRuntimeSettings
from ..tracking.entities import (
    EntityAliasCollisionError,
    EntityEntry,
    EntityRegistry,
    EntitySlugCollisionError,
    entity_from_dict,
    sanitize_wikilink_name,
)

logger = logging.getLogger(__name__)

_ENTITY_TYPE_MAP = {
    "people": "person",
    "departments": "department",
    "systems": "system",
    "processes": "process",
}
_RESULT_TEMPLATE = {key: [] for key in _ENTITY_TYPE_MAP}
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"(\{.*?\})", re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")
_SOFT_MATCH_SYSTEM_PROMPT = """You are matching one extracted Folio entity mention to an existing entity registry.
Return exactly one JSON object and no surrounding prose:
{"match":"<canonical_name>"} or {"match":null}
Choose a match only if one candidate is clearly the same entity.
Never invent a name that is not one of the candidate canonical names.
If the mention is generic, ambiguous, role-only, or not clearly one candidate, return null."""
_SOFT_MATCH_USER_PROMPT = """Entity type: {entity_type}
Extracted name: {name}
Source context: {context}
Candidates:
{candidates}"""


@dataclass(frozen=True)
class CreatedEntity:
    """A new unresolved entity created during resolution."""

    entity_type: str
    key: str
    canonical_name: str
    proposed_match: Optional[str] = None


@dataclass(frozen=True)
class ResolutionResult:
    """Result payload for ingest-time entity resolution."""

    entities: dict[str, list[str]]
    warnings: list[str]
    created_entities: list[CreatedEntity]
    registry_changed: bool = False


@dataclass(frozen=True)
class _ConfirmedCandidate:
    key: str
    canonical_name: str
    aliases: list[str]
    updated_at: str = ""


@dataclass(frozen=True)
class _PendingCreation:
    entry: EntityEntry


def resolve_entities(
    *,
    entities_path: Path,
    extracted_entities: dict[str, list[str]],
    source_text: str,
    provider_name: str,
    model: str,
    api_key_env: str = "",
    base_url_env: str = "",
    fallback_profiles: list[FallbackProfileSpec] | None = None,
    all_provider_settings: dict[str, ProviderRuntimeSettings] | None = None,
) -> ResolutionResult:
    """Generic entity resolution using the shipped policy.

    Reuses the same resolution semantics as ingest-time resolution.
    """
    return resolve_interaction_entities(
        entities_path=entities_path,
        extracted_entities=extracted_entities,
        source_text=source_text,
        provider_name=provider_name,
        model=model,
        api_key_env=api_key_env,
        base_url_env=base_url_env,
        fallback_profiles=fallback_profiles,
        all_provider_settings=all_provider_settings,
    )


def resolve_interaction_entities(
    *,
    entities_path: Path,
    extracted_entities: dict[str, list[str]],
    source_text: str,
    provider_name: str,
    model: str,
    api_key_env: str = "",
    base_url_env: str = "",
    fallback_profiles: list[FallbackProfileSpec] | None = None,
    all_provider_settings: dict[str, ProviderRuntimeSettings] | None = None,
) -> ResolutionResult:
    """Resolve interaction entities against the library registry."""

    copied_entities = _copy_entities(extracted_entities)
    if not entities_path.exists():
        return ResolutionResult(
            entities=copied_entities,
            warnings=[],
            created_entities=[],
            registry_changed=False,
        )

    registry = EntityRegistry(entities_path)
    registry.load()

    warnings: list[str] = []
    created_entities: list[CreatedEntity] = []
    processed_cache: dict[tuple[str, str], str] = {}
    soft_match_cache: dict[tuple[str, str], Optional[str]] = {}
    pending_creations: list[_PendingCreation] = []
    all_provider_settings = all_provider_settings or {}

    resolved_entities = _copy_entities(extracted_entities)
    for plural_type, singular_type in _ENTITY_TYPE_MAP.items():
        values = extracted_entities.get(plural_type, [])
        resolved_values: list[str] = []
        for raw_name in values:
            normalized = _normalize_entity_name(raw_name)
            if not normalized:
                continue
            cache_key = (singular_type, normalized.lower())
            cached = processed_cache.get(cache_key)
            if cached is not None:
                resolved_values.append(cached)
                continue

            matches = registry.lookup(
                normalized,
                entity_type=singular_type,
                confirmed_only=True,
            )
            if len(matches) == 1:
                resolved_name = matches[0][2].canonical_name
            elif len(matches) > 1:
                resolved_name = normalized
                warnings.append(_format_ambiguity_warning(normalized, matches))
            else:
                proposed_match = _soft_match_or_none(
                    registry=registry,
                    entity_type=singular_type,
                    normalized_name=normalized,
                    source_text=source_text,
                    provider_name=provider_name,
                    model=model,
                    api_key_env=api_key_env,
                    base_url_env=base_url_env,
                    fallback_profiles=fallback_profiles or [],
                    all_provider_settings=all_provider_settings,
                    cache=soft_match_cache,
                )
                resolved_name = normalized
                pending_entry = EntityEntry(
                    canonical_name=normalized,
                    type=singular_type,
                    aliases=[],
                    needs_confirmation=True,
                    source="extracted",
                    proposed_match=proposed_match,
                )
                try:
                    registry.add_entity(_clone_entity_entry(pending_entry))
                except (EntityAliasCollisionError, EntitySlugCollisionError, ValueError) as exc:
                    warnings.append(_format_auto_create_warning(pending_entry, exc))
                except Exception as exc:
                    warnings.append(
                        _format_auto_create_warning(pending_entry, exc, unexpected=True)
                    )
                else:
                    pending_creations.append(
                        _PendingCreation(entry=_clone_entity_entry(pending_entry))
                    )

            processed_cache[cache_key] = resolved_name
            resolved_values.append(resolved_name)

        resolved_entities[plural_type] = _dedupe_preserve_order(resolved_values)

    committed_creations, persist_warnings = _persist_pending_creations(
        entities_path=entities_path,
        pending_creations=pending_creations,
    )
    warnings.extend(persist_warnings)
    created_entities = [
        CreatedEntity(
            entity_type=entry.type,
            key=key,
            canonical_name=entry.canonical_name,
            proposed_match=entry.proposed_match,
        )
        for key, entry in committed_creations
    ]

    return ResolutionResult(
        entities=resolved_entities,
        warnings=warnings,
        created_entities=created_entities,
        registry_changed=bool(created_entities),
    )


def _copy_entities(extracted_entities: dict[str, list[str]]) -> dict[str, list[str]]:
    result = {key: [] for key in _RESULT_TEMPLATE}
    for key in result:
        values = extracted_entities.get(key, [])
        if isinstance(values, list):
            result[key] = [str(value) for value in values]
    return result


def _normalize_entity_name(name: str) -> str:
    collapsed = _WHITESPACE_RE.sub(" ", str(name or "")).strip()
    sanitized = sanitize_wikilink_name(collapsed)
    return _WHITESPACE_RE.sub(" ", sanitized).strip()


def _describe_matches(matches: list[tuple[str, str, EntityEntry]]) -> str:
    return ", ".join(f"{entry.canonical_name} ({entity_type})" for entity_type, _key, entry in matches)


def _format_ambiguity_warning(
    normalized_name: str,
    matches: list[tuple[str, str, EntityEntry]],
) -> str:
    return (
        f'⚠ Ambiguous entity: "{normalized_name}" matches {_describe_matches(matches)}\n'
        f"  → Keeping unresolved wikilink: [[{normalized_name}]]"
    )


def _format_auto_create_warning(
    entry: EntityEntry,
    exc: Exception,
    *,
    unexpected: bool = False,
) -> str:
    prefix = "Unexpected error auto-creating" if unexpected else "Could not auto-create"
    return (
        f"{prefix} {entry.type} '{entry.canonical_name}': {exc}. "
        f"Keeping unresolved wikilink."
    )


def _clone_entity_entry(entry: EntityEntry) -> EntityEntry:
    return entity_from_dict(entry.to_dict())


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _soft_match_or_none(
    *,
    registry: EntityRegistry,
    entity_type: str,
    normalized_name: str,
    source_text: str,
    provider_name: str,
    model: str,
    api_key_env: str,
    base_url_env: str,
    fallback_profiles: list[FallbackProfileSpec],
    all_provider_settings: dict[str, ProviderRuntimeSettings],
    cache: dict[tuple[str, str], Optional[str]],
) -> Optional[str]:
    cache_key = (entity_type, normalized_name.lower())
    if cache_key in cache:
        return cache[cache_key]

    candidates = _confirmed_candidates(registry, entity_type)
    if not candidates:
        cache[cache_key] = None
        return None

    top_candidates = candidates[:50]
    response = _run_soft_match(
        entity_type=entity_type,
        normalized_name=normalized_name,
        source_text=source_text,
        candidates=top_candidates,
        provider_name=provider_name,
        model=model,
        api_key_env=api_key_env,
        base_url_env=base_url_env,
        fallback_profiles=fallback_profiles,
        all_provider_settings=all_provider_settings,
    )
    cache[cache_key] = response
    return response


def _confirmed_candidates(registry: EntityRegistry, entity_type: str) -> list[_ConfirmedCandidate]:
    candidates: list[_ConfirmedCandidate] = []
    for _etype, key, entry in registry.iter_entities(entity_type=entity_type):
        if entry.needs_confirmation:
            continue
        candidates.append(
            _ConfirmedCandidate(
                key=key,
                canonical_name=entry.canonical_name,
                aliases=list(entry.aliases or []),
                updated_at=entry.updated_at or entry.created_at or entry.first_seen or "",
            )
        )
    candidates.sort(key=lambda candidate: _sort_timestamp(candidate.updated_at), reverse=True)
    return candidates


def _sort_timestamp(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _run_soft_match(
    *,
    entity_type: str,
    normalized_name: str,
    source_text: str,
    candidates: list[_ConfirmedCandidate],
    provider_name: str,
    model: str,
    api_key_env: str,
    base_url_env: str,
    fallback_profiles: list[FallbackProfileSpec],
    all_provider_settings: dict[str, ProviderRuntimeSettings],
) -> Optional[str]:
    candidate_prompt_lines = [
        f"- {candidate.canonical_name} | aliases: "
        f"{', '.join(candidate.aliases) if candidate.aliases else '(none)'}"
        for candidate in candidates
    ]
    user_prompt = _SOFT_MATCH_USER_PROMPT.format(
        entity_type=entity_type,
        name=normalized_name,
        context=_source_context(source_text, normalized_name),
        candidates="\n".join(candidate_prompt_lines),
    )
    raw_text = _execute_with_fallback(
        prompt=user_prompt,
        system_prompt=_SOFT_MATCH_SYSTEM_PROMPT,
        primary=(provider_name, model, api_key_env, base_url_env),
        fallback_profiles=fallback_profiles,
        all_provider_settings=all_provider_settings,
    )
    if raw_text is None:
        return None

    try:
        payload = _parse_json_object(raw_text)
    except ValueError:
        return None

    match = payload.get("match")
    if match is None:
        return None
    if not isinstance(match, str):
        return None
    match_name = match.strip()
    if not match_name:
        return None

    match_name_lower = match_name.lower()
    for candidate in candidates:
        if candidate.canonical_name.lower() == match_name_lower:
            return candidate.key
    return None


def _source_context(source_text: str, normalized_name: str) -> str:
    target = normalized_name.lower()
    for line in source_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        lower_cleaned = cleaned.lower()
        if target not in lower_cleaned:
            continue
        candidate = _extract_sentence_containing(cleaned, lower_cleaned.index(target))
        if candidate:
            return candidate
    return "(not found)"


def _extract_sentence_containing(text: str, target_index: int) -> str:
    start = 0
    for index, char in enumerate(text):
        if index >= target_index:
            break
        if _is_sentence_boundary(text, index, char):
            start = index + 1
            while start < len(text) and text[start].isspace():
                start += 1

    end = len(text)
    for index in range(target_index, len(text)):
        if _is_sentence_boundary(text, index, text[index]):
            end = index + 1
            break

    return text[start:end].strip()


def _is_sentence_boundary(text: str, index: int, char: str) -> bool:
    if char not in ".!?":
        return False
    if _is_abbreviation_terminator(text[: index + 1]):
        return False
    next_index = index + 1
    while next_index < len(text) and text[next_index] in "\"')]}":
        next_index += 1
    return next_index == len(text) or text[next_index].isspace()


def _is_abbreviation_terminator(prefix: str) -> bool:
    stripped = prefix.rstrip()
    if not stripped:
        return False
    token = stripped.split()[-1].lower()
    if token in {
        "mr.",
        "mrs.",
        "ms.",
        "dr.",
        "prof.",
        "sr.",
        "jr.",
        "st.",
        "inc.",
        "co.",
        "corp.",
        "ltd.",
        "vs.",
        "etc.",
        "e.g.",
        "i.e.",
        "u.s.",
        "u.k.",
    }:
        return True
    return bool(re.fullmatch(r"(?:[a-z]\.){1,}[a-z]?\.?", token))


def _persist_pending_creations(
    *,
    entities_path: Path,
    pending_creations: list[_PendingCreation],
) -> tuple[list[tuple[str, EntityEntry]], list[str]]:
    if not pending_creations:
        return [], []

    warnings: list[str] = []
    try:
        with _locked_entities_file(entities_path):
            latest_registry = EntityRegistry(entities_path)
            latest_registry.load()

            committed: list[tuple[str, EntityEntry]] = []
            for pending in pending_creations:
                entry = _clone_entity_entry(pending.entry)
                try:
                    key = latest_registry.add_entity(entry)
                except (EntityAliasCollisionError, EntitySlugCollisionError, ValueError) as exc:
                    warnings.append(_format_auto_create_warning(entry, exc))
                except Exception as exc:
                    warnings.append(_format_auto_create_warning(entry, exc, unexpected=True))
                else:
                    committed.append((key, entry))

            if not committed:
                return [], warnings

            _write_entities_json_unlocked(entities_path, latest_registry.to_json())
            return committed, warnings
    except OSError as exc:
        names = ", ".join(
            sorted(
                (pending.entry.canonical_name for pending in pending_creations),
                key=str.lower,
            )
        )
        warnings.append(
            "entities.json could not be updated; resolved confirmed entities "
            f"but skipped auto-create for: {names}. ({exc})"
        )
        return [], warnings


@contextmanager
def _locked_entities_file(path: Path):
    """Lock the sidecar file for the full read/merge/write transaction.

    Any OSError raised while opening or locking the file intentionally
    propagates to _persist_pending_creations(), which converts it into the
    read-only fallback warning path.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _write_entities_json_unlocked(path: Path, payload_json: str) -> None:
    tmp_path = path.with_suffix(".tmp")
    try:
        payload = json.loads(payload_json)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp_path.write_text(json.dumps(payload, indent=2))
        tmp_path.rename(path)
    except OSError as e:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise OSError(
            f"Failed to write entity registry {path}: {e}. "
            f"Check disk space and permissions."
        ) from e


def _execute_with_fallback(
    *,
    prompt: str,
    system_prompt: str,
    primary: tuple[str, str, str, str],
    fallback_profiles: list[FallbackProfileSpec],
    all_provider_settings: dict[str, ProviderRuntimeSettings],
) -> Optional[str]:
    attempts = [primary, *fallback_profiles]
    for provider_name, model, api_key_env, base_url_env in attempts:
        provider = get_provider(provider_name)
        settings = all_provider_settings.get(provider_name, ProviderRuntimeSettings())
        limiter = RateLimiter(
            rpm_limit=settings.rate_limit_rpm,
            tpm_limit=settings.rate_limit_tpm,
        )
        try:
            client = provider.create_client(
                api_key_env=api_key_env,
                base_url_env=base_url_env,
            )
            output = execute_with_retry(
                provider,
                client,
                model,
                ProviderInput(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    images=(),
                    max_tokens=256,
                    temperature=0.0,
                    require_store_false=settings.require_store_false,
                ),
                settings,
                limiter,
            )
            return output.raw_text
        except Exception as exc:
            logger.warning(
                "Entity soft-match provider '%s/%s' failed: %s",
                provider_name,
                model,
                exc,
            )
            continue
    return None


def _parse_json_object(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        object_match = _JSON_OBJECT_RE.search(text)
        if object_match:
            text = object_match.group(1).strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Soft-match payload must be an object")
    return payload
