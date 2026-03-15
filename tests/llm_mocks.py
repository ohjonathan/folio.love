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
    # Usage metadata for TokenUsage extraction
    mock_usage = MagicMock()
    mock_usage.input_tokens = 100
    mock_usage.output_tokens = 50
    mock_response.usage = mock_usage
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


def make_openai_response(text: str, finish_reason: str = "stop") -> MagicMock:
    """Create a mock OpenAI ChatCompletion response.

    Simulates the OpenAI SDK response shape:
        response.choices[0].message.content = text
        response.choices[0].finish_reason = finish_reason
    """
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = text
    mock_choice.message = mock_message
    mock_choice.finish_reason = finish_reason
    mock_response.choices = [mock_choice]
    # Usage metadata for TokenUsage extraction
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150
    mock_response.usage = mock_usage
    return mock_response


def make_google_response(text: str, finish_reason: str = "STOP") -> MagicMock:
    """Create a mock Google Gemini response.

    Simulates the Google GenAI SDK response shape:
        response.text = text
        response.candidates[0].finish_reason = finish_reason
    """
    mock_response = MagicMock()
    mock_response.text = text
    mock_candidate = MagicMock()
    mock_candidate.finish_reason = finish_reason
    mock_response.candidates = [mock_candidate]
    # Usage metadata for TokenUsage extraction
    mock_usage_meta = MagicMock()
    mock_usage_meta.prompt_token_count = 100
    mock_usage_meta.candidates_token_count = 50
    mock_usage_meta.total_token_count = 150
    mock_response.usage_metadata = mock_usage_meta
    return mock_response
