"""Ingest-time entity resolution against entities.json."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..llm import ProviderInput, RateLimiter, execute_with_retry, get_provider
from ..llm.types import FallbackProfileSpec, ProviderRuntimeSettings
from ..tracking.entities import (
    EntityAliasCollisionError,
    EntityEntry,
    EntityRegistry,
    EntityRegistryError,
    EntitySlugCollisionError,
    sanitize_wikilink_name,
)

logger = logging.getLogger(__name__)

_SOFT_MATCH_SYSTEM_PROMPT = """You are matching one extracted Folio entity mention to an existing entity registry.
Return exactly one JSON object and no surrounding prose:
{"match":"<canonical_name>"} or {"match":null}
Choose a match only if one candidate is clearly the same entity.
Never invent a name that is not one of the candidate canonical names.
If the mention is generic, ambiguous, role-only, or not clearly one candidate, return null.
"""
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"(\{.*\})", re.DOTALL)
_ENTITY_TYPE_BY_EXTRACTION_KEY = {
    "people": "person",
    "departments": "department",
    "systems": "system",
    "processes": "process",
}
_ENTITY_LIST_KEYS = tuple(_ENTITY_TYPE_BY_EXTRACTION_KEY.keys())
_MAX_SOFT_MATCH_CANDIDATES = 50


@dataclass(frozen=True)
class CreatedEntity:
    """Entity auto-created during resolution."""

    entity_list: str
    entity_type: str
    key: str
    canonical_name: str
    proposed_match: str | None = None


@dataclass
class ResolutionResult:
    """Resolved entities plus registry side effects."""

    entities: dict[str, list[str]]
    warnings: list[str] = field(default_factory=list)
    created_entities: list[CreatedEntity] = field(default_factory=list)
    registry_changed: bool = False


@dataclass(frozen=True)
class _Candidate:
    key: str
    canonical_name: str
    aliases: tuple[str, ...]
    updated_at: str


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
    """Resolve extracted interaction entities against an existing registry."""

    resolved_entities = _copy_entities(extracted_entities)
    if not entities_path.exists():
        return ResolutionResult(entities=resolved_entities)

    registry = EntityRegistry(entities_path)
    registry.load()

    warnings: list[str] = []
    created_entities: list[CreatedEntity] = []
    registry_changed = False
    all_provider_settings = all_provider_settings or {}
    soft_match_cache: dict[tuple[str, str], str | None] = {}

    for entity_list in _ENTITY_LIST_KEYS:
        entity_type = _ENTITY_TYPE_BY_EXTRACTION_KEY[entity_list]
        resolved_items: list[str] = []
        seen_resolved: set[str] = set()

        for raw_name in extracted_entities.get(entity_list, []):
            normalized_name = _normalize_entity_name(raw_name)
            if not normalized_name:
                continue

            matches = registry.lookup(
                normalized_name,
                entity_type=entity_type,
                confirmed_only=True,
            )
            if len(matches) == 1:
                resolved_name = matches[0][2].canonical_name
                _append_unique(resolved_items, seen_resolved, resolved_name)
                continue

            if len(matches) > 1:
                candidates = ", ".join(match[2].canonical_name for match in matches)
                warnings.append(
                    f"Ambiguous entity '{normalized_name}' in {entity_type}: {candidates}. "
                    f"Keeping extracted name."
                )
                _append_unique(resolved_items, seen_resolved, normalized_name)
                continue

            cache_key = (entity_type, normalized_name.lower())
            proposed_match = soft_match_cache.get(cache_key)
            if cache_key not in soft_match_cache:
                candidates = _confirmed_candidates(registry, entity_type)
                proposed_match = None
                if candidates:
                    proposed_match = _soft_match_entity(
                        entity_type=entity_type,
                        extracted_name=normalized_name,
                        source_text=source_text,
                        candidates=candidates,
                        provider_name=provider_name,
                        model=model,
                        api_key_env=api_key_env,
                        base_url_env=base_url_env,
                        fallback_profiles=fallback_profiles or [],
                        all_provider_settings=all_provider_settings,
                    )
                soft_match_cache[cache_key] = proposed_match

            try:
                entity_key = registry.add_entity(
                    EntityEntry(
                        canonical_name=normalized_name,
                        type=entity_type,
                        aliases=[],
                        needs_confirmation=True,
                        source="extracted",
                        proposed_match=proposed_match,
                    )
                )
                registry_changed = True
                created_entities.append(
                    CreatedEntity(
                        entity_list=entity_list,
                        entity_type=entity_type,
                        key=entity_key,
                        canonical_name=normalized_name,
                        proposed_match=proposed_match,
                    )
                )
            except (EntitySlugCollisionError, EntityAliasCollisionError, EntityRegistryError) as exc:
                warnings.append(
                    f"Could not auto-create {entity_type} '{normalized_name}': {exc}. "
                    f"Keeping extracted name."
                )

            _append_unique(resolved_items, seen_resolved, normalized_name)

        resolved_entities[entity_list] = resolved_items

    if registry_changed:
        registry.save()

    return ResolutionResult(
        entities=resolved_entities,
        warnings=warnings,
        created_entities=created_entities,
        registry_changed=registry_changed,
    )


def _copy_entities(extracted_entities: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        key: list(extracted_entities.get(key, []))
        for key in _ENTITY_LIST_KEYS
    }


def _append_unique(items: list[str], seen: set[str], value: str) -> None:
    dedupe_key = value.lower()
    if dedupe_key in seen:
        return
    seen.add(dedupe_key)
    items.append(value)


def _normalize_entity_name(name: str) -> str:
    normalized = re.sub(r"\s+", " ", str(name or "").strip())
    return sanitize_wikilink_name(normalized)


def _confirmed_candidates(registry: EntityRegistry, entity_type: str) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for _etype, key, entry in registry.iter_entities(entity_type=entity_type):
        if entry.needs_confirmation:
            continue
        candidates.append(
            _Candidate(
                key=key,
                canonical_name=entry.canonical_name,
                aliases=tuple(entry.aliases),
                updated_at=entry.updated_at or entry.created_at or entry.first_seen or "",
            )
        )

    candidates.sort(
        key=lambda item: (item.updated_at, item.canonical_name.lower()),
        reverse=True,
    )
    return candidates[:_MAX_SOFT_MATCH_CANDIDATES]


def _soft_match_entity(
    *,
    entity_type: str,
    extracted_name: str,
    source_text: str,
    candidates: list[_Candidate],
    provider_name: str,
    model: str,
    api_key_env: str,
    base_url_env: str,
    fallback_profiles: list[FallbackProfileSpec],
    all_provider_settings: dict[str, ProviderRuntimeSettings],
) -> str | None:
    context_line = _source_context_line(source_text, extracted_name)
    prompt = _build_soft_match_prompt(
        entity_type=entity_type,
        extracted_name=extracted_name,
        context_line=context_line,
        candidates=candidates,
    )
    raw_text = _run_with_fallback(
        prompt=prompt,
        system_prompt=_SOFT_MATCH_SYSTEM_PROMPT,
        primary=(provider_name, model, api_key_env, base_url_env),
        fallback_profiles=fallback_profiles,
        all_provider_settings=all_provider_settings,
    )
    if raw_text is None:
        return None

    try:
        payload = _parse_json_object(raw_text)
    except ValueError as exc:
        logger.warning(
            "Soft-match response for '%s'/%s was malformed: %s",
            extracted_name,
            entity_type,
            exc,
        )
        return None

    candidate_by_name = {candidate.canonical_name: candidate.key for candidate in candidates}
    match = payload.get("match")
    if match is None:
        return None
    if not isinstance(match, str):
        logger.warning(
            "Soft-match response for '%s'/%s returned non-string match: %r",
            extracted_name,
            entity_type,
            match,
        )
        return None

    resolved = candidate_by_name.get(match.strip())
    if resolved is None:
        logger.warning(
            "Soft-match response for '%s'/%s returned unknown candidate: %r",
            extracted_name,
            entity_type,
            match,
        )
        return None
    return resolved


def _source_context_line(source_text: str, extracted_name: str) -> str:
    target = extracted_name.lower()
    for line in source_text.splitlines():
        stripped = line.strip()
        if stripped and target in stripped.lower():
            return stripped
    return "(not found)"


def _build_soft_match_prompt(
    *,
    entity_type: str,
    extracted_name: str,
    context_line: str,
    candidates: list[_Candidate],
) -> str:
    lines = [
        f"Entity type: {entity_type}",
        f"Extracted name: {extracted_name}",
        f"Source context: {context_line}",
        "Candidates:",
    ]
    for candidate in candidates:
        aliases = ", ".join(candidate.aliases) if candidate.aliases else "(none)"
        lines.append(f"- {candidate.canonical_name} | aliases: {aliases}")
    return "\n".join(lines)


def _run_with_fallback(
    *,
    prompt: str,
    system_prompt: str,
    primary: tuple[str, str, str, str],
    fallback_profiles: list[FallbackProfileSpec],
    all_provider_settings: dict[str, ProviderRuntimeSettings],
) -> str | None:
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
                "Soft-match provider '%s/%s' failed for prompt '%s': %s",
                provider_name,
                model,
                prompt.splitlines()[1] if "\n" in prompt else prompt,
                exc,
            )
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
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed soft-match JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Malformed soft-match JSON response: top-level payload must be an object")
    return payload
