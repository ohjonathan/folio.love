"""Tests for config loading, especially null YAML section handling."""

import tempfile
from pathlib import Path

import pytest

from folio.config import FolioConfig


class TestNullYAMLSections:
    """Test that null YAML sections don't crash config loading."""

    def test_llm_null(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("llm:\n")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert config.llm.provider == "anthropic"
        assert config.llm.model == "claude-sonnet-4-20250514"

    def test_conversion_null(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("conversion:\n")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert config.conversion.image_dpi == 150
        assert config.conversion.default_passes == 1

    def test_both_null(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("llm:\nconversion:\n")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert config.llm.provider == "anthropic"
        assert config.conversion.image_dpi == 150

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert config.llm.provider == "anthropic"

    def test_valid_config_still_works(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("llm:\n  model: claude-haiku-4-5-20251001\nconversion:\n  image_dpi: 300\n")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert config.llm.model == "claude-haiku-4-5-20251001"
        assert config.conversion.image_dpi == 300
