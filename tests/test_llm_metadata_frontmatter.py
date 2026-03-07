"""Tests for _llm_metadata in generated frontmatter (spec §7.4, §9.6)."""

import yaml

from folio.output.frontmatter import generate as build_frontmatter
from folio.tracking.versions import VersionInfo, ChangeSet


class TestLLMMetadataFrontmatter:
    """Verify _llm_metadata structure in frontmatter output."""

    def _parse_frontmatter(self, yaml_str: str) -> dict:
        """Parse YAML frontmatter string to dict."""
        lines = yaml_str.strip().split("\n")
        if lines[0].strip() == "---":
            lines = lines[1:]
        if lines[-1].strip() == "---":
            lines = lines[:-1]
        return yaml.safe_load("\n".join(lines))

    def _version_info(self) -> VersionInfo:
        return VersionInfo(
            version=1,
            note="Initial",
            source_hash="abc123def456",
            source_path="test.pptx",
            slide_count=0,
            timestamp="2026-03-07T00:00:00Z",
            changes=ChangeSet(),
        )

    def test_llm_metadata_written_to_frontmatter(self):
        """S2: _llm_metadata must appear in frontmatter."""
        llm_meta = {
            "convert": {
                "requested_profile": "default",
                "profile": "default_anthropic",
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "fallback_used": False,
                "status": "executed",
                "pass2": {"status": "executed"},
            },
        }
        fm = build_frontmatter(
            title="Test Deck",
            deck_id="test-20260307",
            source_relative_path="test.pptx",
            source_hash="abc123def456",
            source_type="deck",
            version_info=self._version_info(),
            analyses={},
            llm_metadata=llm_meta,
        )
        parsed = self._parse_frontmatter(fm)

        assert "_llm_metadata" in parsed
        convert = parsed["_llm_metadata"]["convert"]
        assert convert["requested_profile"] == "default"
        assert convert["profile"] == "default_anthropic"
        assert convert["provider"] == "anthropic"
        assert convert["model"] == "claude-sonnet-4-20250514"
        assert convert["fallback_used"] is False
        assert convert["status"] == "executed"
        assert convert["pass2"]["status"] == "executed"

    def test_llm_metadata_with_fallback(self):
        """_llm_metadata reflects fallback activation."""
        llm_meta = {
            "convert": {
                "requested_profile": "default",
                "profile": "default_anthropic",
                "provider": "openai",
                "model": "gpt-4o",
                "fallback_used": True,
                "status": "executed",
                "pass2": {"status": "skipped", "reason": "pass_disabled"},
            },
        }
        fm = build_frontmatter(
            title="Test Deck",
            deck_id="test-20260307",
            source_relative_path="test.pptx",
            source_hash="abc123def456",
            source_type="deck",
            version_info=self._version_info(),
            analyses={},
            llm_metadata=llm_meta,
        )
        parsed = self._parse_frontmatter(fm)

        convert = parsed["_llm_metadata"]["convert"]
        assert convert["fallback_used"] is True
        assert convert["provider"] == "openai"
        assert convert["pass2"]["status"] == "skipped"
        assert convert["pass2"]["reason"] == "pass_disabled"

    def test_llm_metadata_absent_when_none(self):
        """No _llm_metadata if not provided."""
        fm = build_frontmatter(
            title="Test Deck",
            deck_id="test-20260307",
            source_relative_path="test.pptx",
            source_hash="abc123def456",
            source_type="deck",
            version_info=self._version_info(),
            analyses={},
        )
        parsed = self._parse_frontmatter(fm)
        assert "_llm_metadata" not in parsed
