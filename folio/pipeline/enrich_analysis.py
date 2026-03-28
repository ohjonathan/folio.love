"""LLM prompt construction and response parsing for enrich analysis.

Provides two prompt shapes:
1. Primary note-scoped enrich analysis (tags + entities + relationship cues)
2. Bounded relationship evaluation (optional second call)

Uses ``execute_with_retry`` from ``folio.llm.runtime`` for LLM calls.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from ..llm import ProviderInput, RateLimiter, execute_with_retry, get_provider
from ..llm.types import FallbackProfileSpec, ProviderRuntimeSettings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"(\{.*\})", re.DOTALL)


def _extract_json(raw_text: str) -> dict:
    """Extract a JSON object from LLM response text."""
    text = (raw_text or "").strip()
    # Try fenced block first
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        object_match = _JSON_OBJECT_RE.search(text)
        if object_match:
            text = object_match.group(1).strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Response must be a JSON object")
    return payload


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_ENRICH_SYSTEM_PROMPT = """\
You are a structured-output analyst for a consulting knowledge library.
Given a note (evidence or interaction type), you will analyze it and return
a single JSON object with three keys:

{
  "tag_candidates": ["tag1", "tag2", ...],
  "entity_mentions": {
    "people": ["Name1", "Name2"],
    "departments": ["Dept1"],
    "systems": ["System1"],
    "processes": ["Process1"]
  },
  "relationship_cues": [
    {
      "relation": "supersedes|impacts",
      "target_hint": "description or partial ID of the target note",
      "confidence": "high|medium",
      "signals": ["signal1", "signal2"],
      "rationale": "brief explanation"
    }
  ]
}

Rules:
- tag_candidates: propose new tags not already in the existing tags list.
  Tags should be lowercase, hyphenated, and meaningful for consulting research.
  Do not repeat existing tags.
- entity_mentions: extract named people, departments, systems, and processes.
  Only include clearly named entities, not generic role descriptions.
- relationship_cues: only include if you see strong evidence that this note
  supersedes (evidence only) or impacts (interaction only) another specific
  note described in the peer context. Do not guess.
- Return ONLY the JSON object. No prose, no markdown fencing, no explanation.
"""

_RELATIONSHIP_EVAL_SYSTEM_PROMPT = """\
You are evaluating potential document relationships in a consulting knowledge library.
Given a source note descriptor and a list of peer note descriptors from the same
client/engagement scope, determine if any relationship proposals are warranted.

Allowed relationships:
- "supersedes": The source evidence note replaces an older evidence note with
  the same or very similar source lineage (same deck stem, same topic, newer version).
  Only for evidence notes. Singular: at most one target.
- "impacts": The source interaction note changes, informs, or revises the
  understanding in a specific target note. Only for interaction notes.

Return a JSON object:
{
  "proposals": [
    {
      "relation": "supersedes|impacts",
      "target_id": "exact target note ID",
      "confidence": "high|medium",
      "signals": ["signal1", "signal2"],
      "rationale": "brief explanation"
    }
  ]
}

Rules:
- Only propose relationships with HIGH-SIGNAL evidence. Do not guess.
- For supersedes: both notes must share the same source lineage or very similar titles.
- For impacts: there must be explicit reference to or clear influence on the target.
- Low-confidence relationships should NOT be included.
- Return ONLY the JSON object.
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EnrichAnalysisOutput:
    """Output from the primary note-scoped enrich analysis."""

    tag_candidates: list[str] = field(default_factory=list)
    entity_mention_candidates: dict[str, list[str]] = field(default_factory=dict)
    relationship_cues: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_note_for_enrichment(
    note_content: str,
    doc_type: str,
    existing_tags: list[str],
    existing_frontmatter: dict,
    provider_name: str,
    model: str,
    *,
    api_key_env: str = "",
    base_url_env: str = "",
    fallback_profiles: list[FallbackProfileSpec] | None = None,
    all_provider_settings: dict[str, ProviderRuntimeSettings] | None = None,
    peer_context: str = "",
) -> EnrichAnalysisOutput:
    """Run one primary note-scoped enrich analysis pass.

    Returns tag candidates, entity mention candidates, and relationship cues.
    """
    all_provider_settings = all_provider_settings or {}

    user_prompt = _build_enrich_user_prompt(
        note_content=note_content,
        doc_type=doc_type,
        existing_tags=existing_tags,
        existing_frontmatter=existing_frontmatter,
        peer_context=peer_context,
    )

    raw_text = _execute_with_fallback(
        prompt=user_prompt,
        system_prompt=_ENRICH_SYSTEM_PROMPT,
        primary=(provider_name, model, api_key_env, base_url_env),
        fallback_profiles=fallback_profiles or [],
        all_provider_settings=all_provider_settings,
        max_tokens=2048,
    )

    if raw_text is None:
        logger.warning("Enrich analysis returned no output")
        return EnrichAnalysisOutput()

    try:
        payload = _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Enrich analysis returned malformed JSON: %s", exc)
        return EnrichAnalysisOutput()

    return _parse_enrich_output(payload)


def evaluate_relationships(
    note_descriptor: str,
    peer_descriptors: list[str],
    allowed_relations: list[str],
    provider_name: str,
    model: str,
    *,
    api_key_env: str = "",
    base_url_env: str = "",
    fallback_profiles: list[FallbackProfileSpec] | None = None,
    all_provider_settings: dict[str, ProviderRuntimeSettings] | None = None,
) -> list[dict]:
    """Run bounded relationship evaluation.

    Returns a list of raw proposal dicts.
    """
    all_provider_settings = all_provider_settings or {}

    user_prompt = _build_relationship_user_prompt(
        note_descriptor=note_descriptor,
        peer_descriptors=peer_descriptors,
        allowed_relations=allowed_relations,
    )

    raw_text = _execute_with_fallback(
        prompt=user_prompt,
        system_prompt=_RELATIONSHIP_EVAL_SYSTEM_PROMPT,
        primary=(provider_name, model, api_key_env, base_url_env),
        fallback_profiles=fallback_profiles or [],
        all_provider_settings=all_provider_settings,
        max_tokens=2048,
    )

    if raw_text is None:
        return []

    try:
        payload = _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Relationship evaluation returned malformed JSON: %s", exc)
        return []

    proposals = payload.get("proposals", [])
    if not isinstance(proposals, list):
        return []

    # Filter to allowed relations only
    valid = []
    for p in proposals:
        if not isinstance(p, dict):
            continue
        if p.get("relation") not in allowed_relations:
            continue
        if not p.get("target_id"):
            continue
        valid.append(p)

    return valid


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_enrich_user_prompt(
    *,
    note_content: str,
    doc_type: str,
    existing_tags: list[str],
    existing_frontmatter: dict,
    peer_context: str,
) -> str:
    """Build the user prompt for enrich analysis."""
    parts = [
        f"Document type: {doc_type}",
        f"Existing tags: {json.dumps(existing_tags)}",
    ]

    # Include key frontmatter fields as context
    for field_name in ("client", "engagement", "title", "id"):
        val = existing_frontmatter.get(field_name)
        if val:
            parts.append(f"{field_name}: {val}")

    if peer_context:
        parts.append(f"\nPeer context (same client/engagement):\n{peer_context}")

    parts.append(f"\n--- Note Content ---\n{note_content}")

    return "\n".join(parts)


def _build_relationship_user_prompt(
    *,
    note_descriptor: str,
    peer_descriptors: list[str],
    allowed_relations: list[str],
) -> str:
    """Build the user prompt for relationship evaluation."""
    parts = [
        f"Allowed relationship types: {json.dumps(allowed_relations)}",
        f"\n--- Source Note ---\n{note_descriptor}",
        "\n--- Peer Notes ---",
    ]
    for desc in peer_descriptors:
        parts.append(desc)
        parts.append("---")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_enrich_output(payload: dict) -> EnrichAnalysisOutput:
    """Parse the enrich analysis JSON response."""
    tag_candidates = []
    raw_tags = payload.get("tag_candidates", [])
    if isinstance(raw_tags, list):
        for tag in raw_tags:
            if isinstance(tag, str) and tag.strip():
                tag_candidates.append(tag.strip().lower())

    entity_mentions: dict[str, list[str]] = {}
    raw_entities = payload.get("entity_mentions", {})
    if isinstance(raw_entities, dict):
        for category in ("people", "departments", "systems", "processes"):
            values = raw_entities.get(category, [])
            if isinstance(values, list):
                cleaned = [
                    v.strip() for v in values
                    if isinstance(v, str) and v.strip()
                ]
                if cleaned:
                    entity_mentions[category] = cleaned

    relationship_cues = []
    raw_cues = payload.get("relationship_cues", [])
    if isinstance(raw_cues, list):
        for cue in raw_cues:
            if isinstance(cue, dict) and cue.get("relation"):
                relationship_cues.append(cue)

    return EnrichAnalysisOutput(
        tag_candidates=tag_candidates,
        entity_mention_candidates=entity_mentions,
        relationship_cues=relationship_cues,
    )


# ---------------------------------------------------------------------------
# LLM execution with fallback
# ---------------------------------------------------------------------------

def _execute_with_fallback(
    *,
    prompt: str,
    system_prompt: str,
    primary: tuple[str, str, str, str],
    fallback_profiles: list[FallbackProfileSpec],
    all_provider_settings: dict[str, ProviderRuntimeSettings],
    max_tokens: int = 2048,
) -> Optional[str]:
    """Execute LLM call with fallback chain."""
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
                    max_tokens=max_tokens,
                    temperature=0.0,
                    require_store_false=settings.require_store_false,
                ),
                settings,
                limiter,
            )
            return output.raw_text
        except Exception as exc:
            logger.warning(
                "Enrich provider '%s/%s' failed: %s",
                provider_name, model, exc,
            )
            continue
    return None
