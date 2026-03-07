"""Shared mock factories for LLM provider testing."""

from __future__ import annotations

import json
from unittest.mock import MagicMock


def make_anthropic_response(text: str, stop_reason: str = "end_turn") -> MagicMock:
    """Create a mock Anthropic Messages API response."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    mock_response.stop_reason = stop_reason
    return mock_response


def make_pass1_json(
    slide_type: str = "data",
    framework: str = "tam-sam-som",
    evidence_count: int = 1,
) -> str:
    """Create a well-formed pass-1 JSON response."""
    evidence = [
        {
            "claim": f"Claim {i}",
            "quote": f"Quote {i}",
            "element_type": "body",
            "confidence": "high",
        }
        for i in range(evidence_count)
    ]
    return json.dumps({
        "slide_type": slide_type,
        "framework": framework,
        "visual_description": "Test visual.",
        "key_data": "Test data",
        "main_insight": "Test insight.",
        "evidence": evidence,
    })


def make_pass2_json(
    slide_type_reassessment: str = "unchanged",
    framework_reassessment: str = "unchanged",
    evidence_count: int = 1,
) -> str:
    """Create a well-formed pass-2 JSON response."""
    evidence = [
        {
            "claim": f"Depth claim {i}",
            "quote": f"Depth quote {i}",
            "element_type": "body",
            "confidence": "high",
        }
        for i in range(evidence_count)
    ]
    return json.dumps({
        "slide_type_reassessment": slide_type_reassessment,
        "framework_reassessment": framework_reassessment,
        "evidence": evidence,
    })
