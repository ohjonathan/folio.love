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

    def test_ingest_route_resolution(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        llm = LLMConfig(
            profiles={
                "default": LLMProfile(name="default"),
                "ingest_main": LLMProfile(name="ingest_main", provider="openai"),
            },
            routing={
                "default": LLMRoute(primary="default"),
                "ingest": LLMRoute(primary="ingest_main"),
            },
        )
        profile = llm.resolve_profile(task="ingest")
        assert profile.name == "ingest_main"
        assert profile.provider == "openai"

    def test_ingest_route_falls_back_to_default(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        llm = LLMConfig(
            profiles={"main": LLMProfile(name="main")},
            routing={"default": LLMRoute(primary="main")},
        )
        profile = llm.resolve_profile(task="ingest")
        assert profile.name == "main"

    def test_ingest_fallbacks_follow_default_when_missing(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        llm = LLMConfig(
            profiles={
                "main": LLMProfile(name="main"),
                "backup": LLMProfile(name="backup", provider="google"),
            },
            routing={
                "default": LLMRoute(primary="main", fallbacks=["backup"]),
            },
        )
        fallbacks = llm.get_fallbacks(task="ingest")
        assert [p.name for p in fallbacks] == ["backup"]

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

    def test_base_url_env_defaults_empty(self):
        from folio.config import LLMProfile
        p = LLMProfile(name="test", provider="openai")
        assert p.base_url_env == ""

    def test_base_url_env_explicit(self):
        from folio.config import LLMProfile
        p = LLMProfile(
            name="test",
            provider="openai",
            base_url_env="OPENAI_BASE_URL",
        )
        assert p.base_url_env == "OPENAI_BASE_URL"

    def test_profile_config_loads_base_url_env(self):
        yaml_content = """\
llm:
  profiles:
    gateway_openai:
      provider: openai
      model: gpt-4o
      api_key_env: OPENAI_API_KEY
      base_url_env: OPENAI_BASE_URL
  routing:
    default:
      primary: gateway_openai
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = FolioConfig.load(Path(f.name))

        profile = config.llm.resolve_profile()
        assert profile.name == "gateway_openai"
        assert profile.base_url_env == "OPENAI_BASE_URL"

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


class TestLLMConfigValidation:
    """Test LLM config validation per spec §3.2."""

    def test_unsupported_provider_rejects(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="unsupported provider 'bogus'"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={"bad": LLMProfile(name="bad", provider="bogus")},
                    routing={"default": LLMRoute(primary="bad")},
                )
            )

    def test_missing_routing_default_rejects(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="routing.default"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={"main": LLMProfile(name="main")},
                    routing={"convert": LLMRoute(primary="main")},
                )
            )

    def test_dangling_route_target_rejects(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="missing profile 'nonexistent'"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={"main": LLMProfile(name="main")},
                    routing={"default": LLMRoute(primary="nonexistent")},
                )
            )

    def test_dangling_fallback_rejects(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="fallback references missing profile 'ghost'"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={"main": LLMProfile(name="main")},
                    routing={"default": LLMRoute(primary="main", fallbacks=["ghost"])},
                )
            )

    def test_valid_config_passes_validation(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        # Should not raise
        config = FolioConfig(
            llm=LLMConfig(
                profiles={
                    "main": LLMProfile(name="main", provider="anthropic"),
                    "backup": LLMProfile(name="backup", provider="google"),
                },
                routing={
                    "default": LLMRoute(primary="main"),
                    "convert": LLMRoute(primary="main", fallbacks=["backup"]),
                },
            )
        )
        assert "main" in config.llm.profiles

    def test_invalid_profile_name_rejects(self):
        """S1: Profile names must match ^[a-z][a-z0-9_]*$."""
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="does not match required pattern"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={"My-Profile": LLMProfile(name="My-Profile")},
                    routing={"default": LLMRoute(primary="My-Profile")},
                )
            )

    def test_numeric_start_profile_name_rejects(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="does not match required pattern"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={"123bad": LLMProfile(name="123bad")},
                    routing={"default": LLMRoute(primary="123bad")},
                )
            )

    def test_fallback_self_reference_rejects(self):
        """M8: Fallback must not reference same profile as primary."""
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="self-referencing fallback"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={"main": LLMProfile(name="main")},
                    routing={"default": LLMRoute(primary="main", fallbacks=["main"])},
                )
            )

    def test_duplicate_fallback_rejects(self):
        """M8: Duplicate fallback entries must be rejected."""
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="duplicate fallback"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={
                        "main": LLMProfile(name="main", provider="anthropic"),
                        "backup": LLMProfile(name="backup", provider="openai"),
                    },
                    routing={
                        "default": LLMRoute(
                            primary="main",
                            fallbacks=["backup", "backup"],
                        ),
                    },
                )
            )

    def test_non_string_base_url_env_rejects(self):
        from folio.config import LLMProfile, LLMConfig, LLMRoute
        with pytest.raises(ValueError, match="base_url_env must be a string"):
            FolioConfig(
                llm=LLMConfig(
                    profiles={
                        "main": LLMProfile(
                            name="main",
                            provider="openai",
                            base_url_env=123,  # type: ignore[arg-type]
                        ),
                    },
                    routing={"default": LLMRoute(primary="main")},
                )
            )


class TestReviewConfidenceThreshold:
    """Test review_confidence_threshold config field."""

    def test_default_value(self):
        config = FolioConfig()
        assert config.conversion.review_confidence_threshold == 0.6

    def test_explicit_yaml_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("conversion:\n  review_confidence_threshold: 0.8\n")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert config.conversion.review_confidence_threshold == 0.8

    def test_below_zero_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="review_confidence_threshold"):
            FolioConfig(conversion=ConversionConfig(review_confidence_threshold=-0.1))

    def test_above_one_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="review_confidence_threshold"):
            FolioConfig(conversion=ConversionConfig(review_confidence_threshold=1.1))

    def test_non_numeric_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="review_confidence_threshold"):
            FolioConfig(conversion=ConversionConfig(review_confidence_threshold="high"))


class TestDiagramMaxTokensConfig:
    """Test diagram_max_tokens config field."""

    def test_default_value(self):
        config = FolioConfig()
        assert config.conversion.diagram_max_tokens == 16384

    def test_explicit_yaml_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("conversion:\n  diagram_max_tokens: 8192\n")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert config.conversion.diagram_max_tokens == 8192

    def test_zero_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="diagram_max_tokens"):
            FolioConfig(conversion=ConversionConfig(diagram_max_tokens=0))

    def test_negative_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="diagram_max_tokens"):
            FolioConfig(conversion=ConversionConfig(diagram_max_tokens=-100))

    def test_non_int_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="diagram_max_tokens"):
            FolioConfig(conversion=ConversionConfig(diagram_max_tokens="auto"))


class TestMaxImagePixelsConfig:
    """Test max_image_pixels config field."""

    def test_default_is_none(self):
        config = FolioConfig()
        assert config.conversion.max_image_pixels is None

    def test_explicit_yaml_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("conversion:\n  max_image_pixels: 89478485\n")
            f.flush()
            config = FolioConfig.load(Path(f.name))
        assert config.conversion.max_image_pixels == 89478485

    def test_none_is_valid(self):
        from folio.config import ConversionConfig
        # Should not raise
        config = FolioConfig(conversion=ConversionConfig(max_image_pixels=None))
        assert config.conversion.max_image_pixels is None

    def test_zero_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="max_image_pixels"):
            FolioConfig(conversion=ConversionConfig(max_image_pixels=0))

    def test_negative_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="max_image_pixels"):
            FolioConfig(conversion=ConversionConfig(max_image_pixels=-1))


# ── P3: Large-document warning config ──────────────────────────────────

class TestLargeDocumentWarnPages:
    """P3: Config field for large_document_warn_pages."""

    def test_default_is_50(self):
        config = FolioConfig()
        assert config.conversion.large_document_warn_pages == 50

    def test_yaml_loading(self, tmp_path):
        yaml_path = tmp_path / "folio.yaml"
        yaml_path.write_text(
            "conversion:\n"
            "  large_document_warn_pages: 100\n"
            "llm:\n"
            "  profiles:\n"
            "    default:\n"
            "      provider: anthropic\n"
            "      model: claude-sonnet-4-20250514\n"
            "  routing:\n"
            "    default:\n"
            "      primary: default\n"
        )
        config = FolioConfig.load(yaml_path)
        assert config.conversion.large_document_warn_pages == 100

    def test_zero_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="large_document_warn_pages"):
            FolioConfig(conversion=ConversionConfig(large_document_warn_pages=0))

    def test_negative_raises(self):
        from folio.config import ConversionConfig
        with pytest.raises(ValueError, match="large_document_warn_pages"):
            FolioConfig(conversion=ConversionConfig(large_document_warn_pages=-1))
