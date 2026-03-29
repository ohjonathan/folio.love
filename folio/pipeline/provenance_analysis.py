"""LLM matching utilities for retroactive provenance linking."""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass

from ..config import FolioConfig, LLMProfile
from ..llm import ProviderInput, RateLimiter, execute_with_retry, get_provider
from ..llm.types import FallbackProfileSpec, ProviderRuntimeSettings
from .provenance_data import ExtractedEvidenceItem

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
class ContextBudgetPlan:
    claim_chunks: list[list[ExtractedEvidenceItem]]
    target_chunks: list[list[ExtractedEvidenceItem]]
    shard_count: int
    truncated_items: list[str]


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


def plan_context_budget(
    claims: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
    *,
    model_context_window: int = 32000,
    max_shards_per_pair: int = 8,
) -> ContextBudgetPlan:
    """Plan deterministic claim/target sharding for one pair."""
    budget = int(model_context_window * 0.80)
    claims = sorted(claims, key=lambda item: (item.slide_number, item.claim_index))
    target_items = sorted(target_items, key=lambda item: (item.slide_number, item.claim_index))

    truncated: list[str] = []

    claim_entries = [(item, estimate_tokens(_format_claim_line(item, "C"))) for item in claims]
    target_entries = [(item, estimate_tokens(_format_target_line(item, "T"))) for item in target_items]

    fixed_prompt_overhead = 1200
    available = max(1000, budget - fixed_prompt_overhead)

    def fill_chunks(
        items_with_tokens: list[tuple[ExtractedEvidenceItem, int]],
        *,
        available_tokens: int,
        label: str,
    ) -> list[list[ExtractedEvidenceItem]]:
        chunks: list[list[ExtractedEvidenceItem]] = []
        current: list[ExtractedEvidenceItem] = []
        current_tokens = 0
        for item, item_tokens in items_with_tokens:
            effective_tokens = item_tokens
            if item_tokens > available_tokens:
                effective_tokens = available_tokens
                truncated.append(
                    f"{label} quote truncated: slide {item.slide_number}, claim {item.claim_index}"
                )
            if current and current_tokens + effective_tokens > available_tokens:
                chunks.append(current)
                current = []
                current_tokens = 0
            current.append(item)
            current_tokens += effective_tokens
        if current:
            chunks.append(current)
        return chunks or [[]]

    total_claim_tokens = sum(tokens for _, tokens in claim_entries)
    total_target_tokens = sum(tokens for _, tokens in target_entries)

    if total_claim_tokens + total_target_tokens <= available:
        return ContextBudgetPlan(
            claim_chunks=[claims],
            target_chunks=[target_items],
            shard_count=1,
            truncated_items=truncated,
        )

    claim_chunks = [claims]
    target_available = max(1000, available - min(total_claim_tokens, available // 2))
    target_chunks = fill_chunks(target_entries, available_tokens=target_available, label="target evidence")

    if len(target_chunks) == 1 and total_claim_tokens > available:
        claim_available = max(1000, available - min(total_target_tokens, available // 2))
        claim_chunks = fill_chunks(claim_entries, available_tokens=claim_available, label="claim")
        target_chunks = [target_items]

    if len(claim_chunks) > 1 and total_target_tokens > available:
        claim_available = max(1000, available // 2)
        target_available = max(1000, available // 2)
        claim_chunks = fill_chunks(claim_entries, available_tokens=claim_available, label="claim")
        target_chunks = fill_chunks(target_entries, available_tokens=target_available, label="target evidence")

    shard_count = len(claim_chunks) * len(target_chunks)
    if shard_count > max_shards_per_pair:
        raise ValueError(
            f"pair exceeds shard ceiling ({shard_count} shards needed, max {max_shards_per_pair})"
        )

    return ContextBudgetPlan(
        claim_chunks=claim_chunks,
        target_chunks=target_chunks,
        shard_count=shard_count,
        truncated_items=truncated,
    )


def match_provenance(
    *,
    claims: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
    source_doc_id: str,
    target_doc_id: str,
    profile: LLMProfile,
    config: FolioConfig,
    fallback_profiles: list[FallbackProfileSpec],
) -> tuple[list[dict], ContextBudgetPlan]:
    """Run provenance matching with deterministic sharding."""
    plan = plan_context_budget(
        claims,
        target_items,
        model_context_window=config.conversion.diagram_max_tokens,
        max_shards_per_pair=getattr(config.conversion, "max_shards_per_pair", 8),
    )
    merged: dict[tuple[int, int], dict] = {}

    for claim_chunk in plan.claim_chunks:
        for target_chunk in plan.target_chunks:
            raw_matches = _execute_match_call(
                claims=claim_chunk,
                target_items=target_chunk,
                source_doc_id=source_doc_id,
                target_doc_id=target_doc_id,
                profile=profile,
                config=config,
                fallback_profiles=fallback_profiles,
            )
            for match in raw_matches:
                key = (match["source_claim_index"], match["target_claim_index"])
                old = merged.get(key)
                if old is None or _confidence_rank(match["confidence"]) < _confidence_rank(old["confidence"]):
                    merged[key] = match

    return list(merged.values()), plan


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


def _execute_match_call(
    *,
    claims: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
    source_doc_id: str,
    target_doc_id: str,
    profile: LLMProfile,
    config: FolioConfig,
    fallback_profiles: list[FallbackProfileSpec],
) -> list[dict]:
    prompt = _build_user_prompt(
        claims=claims,
        target_items=target_items,
        source_doc_id=source_doc_id,
        target_doc_id=target_doc_id,
    )
    output = _execute_with_fallback(
        prompt=prompt,
        system_prompt=_PROVENANCE_SYSTEM_PROMPT,
        primary=(profile.provider, profile.model, profile.api_key_env, profile.base_url_env),
        fallback_profiles=fallback_profiles,
        all_provider_settings=config.providers,
        max_tokens=2048,
    )
    if output is None:
        return []
    try:
        payload = _extract_json(output)
    except Exception as exc:
        logger.warning("Provenance analysis returned malformed JSON: %s", exc)
        return []
    return _parse_matches(payload, claims, target_items)


def _build_user_prompt(
    *,
    claims: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
    source_doc_id: str,
    target_doc_id: str,
) -> str:
    parts = [
        f"SOURCE_DOC: {source_doc_id}",
        f"TARGET_DOC: {target_doc_id}",
        "",
        "CLAIMS:",
    ]
    for index, item in enumerate(claims, start=1):
        parts.append(_format_claim_line(item, f"C{index}"))
    parts.append("")
    parts.append("TARGET_EVIDENCE:")
    for index, item in enumerate(target_items, start=1):
        parts.append(_format_target_line(item, f"T{index}"))
    parts.append("")
    parts.append('Respond with {"matches":[...]} or [] if nothing matches.')
    return "\n".join(parts)


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


def _format_claim_line(item: ExtractedEvidenceItem, ref: str) -> str:
    return (
        f"{ref}: slide {item.slide_number}, claim {item.claim_index} | "
        f"claim: {json.dumps(item.claim_text, ensure_ascii=False)} | "
        f"quote: {json.dumps(item.supporting_quote, ensure_ascii=False)}"
    )


def _format_target_line(item: ExtractedEvidenceItem, ref: str) -> str:
    return (
        f"{ref}: slide {item.slide_number}, claim {item.claim_index} | "
        f"claim: {json.dumps(item.claim_text, ensure_ascii=False)} | "
        f"quote: {json.dumps(item.supporting_quote, ensure_ascii=False)}"
    )


def _parse_matches(
    payload: object,
    claims: list[ExtractedEvidenceItem],
    target_items: list[ExtractedEvidenceItem],
) -> list[dict]:
    if isinstance(payload, dict):
        raw_matches = payload.get("matches", [])
    elif isinstance(payload, list):
        raw_matches = payload
    else:
        return []

    claim_map = {f"C{index}": item for index, item in enumerate(claims, start=1)}
    target_map = {f"T{index}": item for index, item in enumerate(target_items, start=1)}
    result: list[dict] = []
    for raw_match in raw_matches:
        if not isinstance(raw_match, dict):
            continue
        claim_ref = raw_match.get("claim_ref")
        target_ref = raw_match.get("target_ref")
        if claim_ref not in claim_map or target_ref not in target_map:
            continue
        confidence = raw_match.get("confidence", "low")
        if confidence not in {"high", "medium", "low"}:
            continue
        source_item = claim_map[claim_ref]
        target_item = target_map[target_ref]
        result.append(
            {
                "source_claim": source_item,
                "target_evidence": target_item,
                "source_claim_index": source_item.claim_index,
                "target_claim_index": target_item.claim_index,
                "confidence": confidence,
                "rationale": raw_match.get("rationale", ""),
            }
        )
    return result


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


def _confidence_rank(confidence: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(confidence, 3)


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
