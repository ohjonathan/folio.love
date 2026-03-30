"""LLM matching utilities for retroactive provenance linking."""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass

from ..llm import ProviderInput, RateLimiter, execute_with_retry, get_provider
from ..llm.types import FallbackProfileSpec, ProviderRuntimeSettings

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"(\[.*\]|\{.*\})", re.DOTALL)

_PROVENANCE_SYSTEM_PROMPT = """\
You are a provenance analyst comparing a newer consulting evidence note against
an older superseded evidence note.

Match newer-source claims to older-target evidence entries when they express the
same substantive fact, even if wording is paraphrased, summarized, rounded, or
scope-narrowed.

Return JSON only. Preferred shape:
{
  "matches": [
    {
      "claim_ref": "C1",
      "target_ref": "T3",
      "confidence": "high|medium|low",
      "rationale": "brief explanation"
    }
  ]
}

Rules:
- High confidence: effectively the same grounded fact.
- Medium confidence: clear paraphrase or same fact with minor narrowing/rounding.
- Low confidence: thematic overlap only.
- Do not invent references that are not listed.
- Do not emit duplicate matches for the same claim_ref/target_ref pair.
"""

@dataclass(frozen=True)
class ProvenanceMatch:
    """One semantic claim-to-evidence match returned by the LLM."""

    claim_ref: str
    target_ref: str
    confidence: str
    rationale: str


def _extract_json(raw_text: str) -> object:
    text = (raw_text or "").strip()
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        object_match = _JSON_OBJECT_RE.search(text)
        if object_match:
            text = object_match.group(1).strip()
    return json.loads(text)


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 3.5))


def context_window_for_model(model: str) -> int:
    """Best-effort context-window estimate for provenance sharding."""
    model_lower = (model or "").lower()
    if any(token in model_lower for token in ("gpt-5", "gpt-4.1", "o3", "o4")):
        return 128000
    if "gemini" in model_lower:
        return 128000
    if "opus" in model_lower or "sonnet" in model_lower or "haiku" in model_lower:
        return 200000
    return 32768


def evaluate_provenance_matches(
    *,
    source_note_id: str,
    target_note_id: str,
    claims_payload: list[dict],
    target_payload: list[dict],
    provider_name: str,
    model: str,
    api_key_env: str = "",
    base_url_env: str = "",
    fallback_profiles: list[FallbackProfileSpec] | None = None,
    all_provider_settings: dict[str, ProviderRuntimeSettings] | None = None,
) -> list[ProvenanceMatch]:
    """Compatibility wrapper used by the top-level provenance pipeline."""
    all_provider_settings = all_provider_settings or {}
    prompt = _build_payload_prompt(
        source_note_id=source_note_id,
        target_note_id=target_note_id,
        claims_payload=claims_payload,
        target_payload=target_payload,
    )
    output = _execute_with_fallback(
        prompt=prompt,
        system_prompt=_PROVENANCE_SYSTEM_PROMPT,
        primary=(provider_name, model, api_key_env, base_url_env),
        fallback_profiles=fallback_profiles or [],
        all_provider_settings=all_provider_settings,
        max_tokens=2048,
    )
    if output is None:
        return []
    try:
        payload = _extract_json(output)
    except Exception as exc:
        logger.warning("Provenance analysis returned malformed JSON: %s", exc)
        return []
    return _parse_payload_matches(payload, claims_payload, target_payload)


def _build_payload_prompt(
    *,
    source_note_id: str,
    target_note_id: str,
    claims_payload: list[dict],
    target_payload: list[dict],
) -> str:
    parts = [
        f"SOURCE_DOC: {source_note_id}",
        f"TARGET_DOC: {target_note_id}",
        "",
        "CLAIMS:",
    ]
    for row in claims_payload:
        parts.append(
            f"{row.get('ref')}: slide {row.get('slide_number')}, claim {row.get('claim_index')} | "
            f"claim: {json.dumps(row.get('claim_text', ''), ensure_ascii=False)} | "
            f"quote: {json.dumps(row.get('supporting_quote', ''), ensure_ascii=False)}"
        )
    parts.append("")
    parts.append("TARGET_EVIDENCE:")
    for row in target_payload:
        parts.append(
            f"{row.get('ref')}: slide {row.get('slide_number')}, claim {row.get('claim_index')} | "
            f"claim: {json.dumps(row.get('claim_text', ''), ensure_ascii=False)} | "
            f"quote: {json.dumps(row.get('supporting_quote', ''), ensure_ascii=False)}"
        )
    parts.append("")
    parts.append('Respond with {"matches":[...]} or [] if nothing matches.')
    return "\n".join(parts)


def _parse_payload_matches(
    payload: object,
    claims_payload: list[dict],
    target_payload: list[dict],
) -> list[ProvenanceMatch]:
    if isinstance(payload, dict):
        raw_matches = payload.get("matches", [])
    elif isinstance(payload, list):
        raw_matches = payload
    else:
        return []

    claim_refs = {str(row.get("ref")) for row in claims_payload}
    target_refs = {str(row.get("ref")) for row in target_payload}
    results: list[ProvenanceMatch] = []
    for raw_match in raw_matches:
        if not isinstance(raw_match, dict):
            continue
        claim_ref = str(raw_match.get("claim_ref", ""))
        target_ref = str(raw_match.get("target_ref", ""))
        confidence = str(raw_match.get("confidence", "low"))
        if claim_ref not in claim_refs or target_ref not in target_refs:
            continue
        if confidence not in {"high", "medium", "low"}:
            continue
        results.append(
            ProvenanceMatch(
                claim_ref=claim_ref,
                target_ref=target_ref,
                confidence=confidence,
                rationale=str(raw_match.get("rationale", "")),
            )
        )
    return results
def _execute_with_fallback(
    *,
    prompt: str,
    system_prompt: str,
    primary: tuple[str, str, str, str],
    fallback_profiles: list[FallbackProfileSpec],
    all_provider_settings: dict[str, ProviderRuntimeSettings],
    max_tokens: int,
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
                "Provenance provider '%s/%s' failed: %s",
                provider_name,
                model,
                exc,
            )
    return None
