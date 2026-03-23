"""Entity resolution for interaction ingest."""

from __future__ import annotations

import json
import logging
import re
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
_JSON_OBJECT_RE = re.compile(r"(\{.*\})", re.DOTALL)
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
    registry_changed = False
    processed_cache: dict[tuple[str, str], str] = {}
    soft_match_cache: dict[tuple[str, str], Optional[str]] = {}
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
                warnings.append(
                    f'Ambiguous entity: "{normalized}" matches '
                    f"{_describe_matches(matches)} -> keeping unresolved wikilink: [[{normalized}]]"
                )
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
                try:
                    created_key = registry.add_entity(
                        EntityEntry(
                            canonical_name=normalized,
                            type=singular_type,
                            aliases=[],
                            needs_confirmation=True,
                            source="extracted",
                            proposed_match=proposed_match,
                        )
                    )
                except (EntityAliasCollisionError, ValueError) as exc:
                    warnings.append(
                        f'Unable to auto-create entity "{normalized}" ({singular_type}): {exc}'
                    )
                except Exception as exc:
                    warnings.append(
                        f'Unable to auto-create entity "{normalized}" ({singular_type}): {exc}'
                    )
                else:
                    registry_changed = True
                    created_entities.append(
                        CreatedEntity(
                            entity_type=singular_type,
                            key=created_key,
                            canonical_name=normalized,
                            proposed_match=proposed_match,
                        )
                    )

            processed_cache[cache_key] = resolved_name
            resolved_values.append(resolved_name)

        resolved_entities[plural_type] = _dedupe_preserve_order(resolved_values)

    if registry_changed:
        registry.save()

    return ResolutionResult(
        entities=resolved_entities,
        warnings=warnings,
        created_entities=created_entities,
        registry_changed=registry_changed,
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

    for candidate in candidates:
        if candidate.canonical_name == match_name:
            return candidate.key
    return None


def _source_context(source_text: str, normalized_name: str) -> str:
    target = normalized_name.lower()
    for line in source_text.splitlines():
        cleaned = line.strip()
        if cleaned and target in cleaned.lower():
            return cleaned
    return "(not found)"


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
