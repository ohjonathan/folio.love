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


class TestPptxRendererConfig:
    """Test pptx_renderer config validation."""

    def test_default_is_auto(self):
        config = FolioConfig()
        assert config.conversion.pptx_renderer == "auto"

    def test_valid_values(self):
        for value in ("auto", "libreoffice", "powerpoint"):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(f"conversion:\n  pptx_renderer: {value}\n")
                f.flush()
                config = FolioConfig.load(Path(f.name))
            assert config.conversion.pptx_renderer == value

    def test_invalid_value_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="pptx_renderer"):
            FolioConfig(conversion=ConversionConfig(pptx_renderer="invalid"))


class TestLLMProfiles:
    """Test LLM profile configuration and resolution."""

    def test_default_profile_resolution(self):
        config = FolioConfig()
        profile = config.llm.resolve_profile()
        assert profile.name == "default"
        assert profile.provider == "anthropic"
        assert profile.model == "claude-sonnet-4-20250514"

    def test_override_profile_resolution(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        llm = LLMConfig(
            profiles={
                "default": LLMProfile(name="default"),
                "fast": LLMProfile(name="fast", provider="openai", model="gpt-4o-mini"),
            },
            routing={"default": LLMRoute(primary="default")},
        )
        profile = llm.resolve_profile("fast")
        assert profile.provider == "openai"
        assert profile.model == "gpt-4o-mini"

    def test_unknown_profile_raises(self):
        config = FolioConfig()
        with pytest.raises(ValueError, match="Unknown LLM profile 'bogus'"):
            config.llm.resolve_profile("bogus")

    def test_legacy_config_creates_synthetic_profile(self):
        """Legacy config creates default_<provider> per spec §3.4."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("llm:\n  provider: anthropic\n  model: claude-haiku-4-5-20251001\n")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        profile = config.llm.resolve_profile()
        assert profile.name == "default_anthropic"
        assert profile.provider == "anthropic"
        assert profile.model == "claude-haiku-4-5-20251001"
        # Legacy also creates routing
        assert "convert" in config.llm.routing
        assert config.llm.routing["convert"].primary == "default_anthropic"

    def test_profile_based_config_with_routing(self):
        """Profile + routing config per spec §3.1."""
        yaml_content = """\
llm:
  profiles:
    claude:
      provider: anthropic
      model: claude-sonnet-4-20250514
    openai:
      provider: openai
      model: gpt-4o
  routing:
    default:
      primary: claude
    convert:
      primary: claude
      fallbacks: [openai]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert "claude" in config.llm.profiles
        assert "openai" in config.llm.profiles

        claude = config.llm.resolve_profile("claude")
        assert claude.provider == "anthropic"

        openai = config.llm.resolve_profile("openai")
        assert openai.provider == "openai"
        assert openai.model == "gpt-4o"

        # Route resolution
        profile = config.llm.resolve_profile(task="convert")
        assert profile.name == "claude"

        # Fallbacks
        fallbacks = config.llm.get_fallbacks(task="convert")
        assert len(fallbacks) == 1
        assert fallbacks[0].name == "openai"

    def test_cli_override_disables_fallback(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        llm = LLMConfig(
            profiles={
                "prod": LLMProfile(name="prod"),
                "backup": LLMProfile(name="backup", provider="openai"),
            },
            routing={"convert": LLMRoute(primary="prod", fallbacks=["backup"])},
        )
        # Without override: fallbacks are returned
        assert len(llm.get_fallbacks(task="convert")) == 1
        # With override: fallback disabled
        assert llm.get_fallbacks(override="prod", task="convert") == []

    def test_undefined_route_falls_back_to_default(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        llm = LLMConfig(
            profiles={
                "main": LLMProfile(name="main"),
            },
            routing={"default": LLMRoute(primary="main")},
        )
        # "convert" route not defined → falls back to default
        profile = llm.resolve_profile(task="convert")
        assert profile.name == "main"

    def test_api_key_env_auto_generated(self):
        from folio.config import LLMProfile
        p = LLMProfile(name="test", provider="openai")
        assert p.api_key_env == "OPENAI_API_KEY"

        p2 = LLMProfile(name="test", provider="google")
        assert p2.api_key_env == "GEMINI_API_KEY"  # Not GOOGLE_API_KEY

        p3 = LLMProfile(name="test", provider="anthropic")
        assert p3.api_key_env == "ANTHROPIC_API_KEY"

    def test_api_key_env_explicit(self):
        from folio.config import LLMProfile
        p = LLMProfile(name="test", provider="openai", api_key_env="MY_CUSTOM_KEY")
        assert p.api_key_env == "MY_CUSTOM_KEY"

    def test_cli_llm_profile_option_accepted(self):
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(b"fake")
            f.flush()
            result = runner.invoke(cli, ["convert", f.name, "--llm-profile", "default"])
            # Should NOT fail with "No such option"
            assert "No such option" not in (result.output or "")

    def test_batch_llm_profile_option_accepted(self):
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ["batch", tmpdir, "--llm-profile", "default"])
            assert "No such option" not in (result.output or "")
