"""Configuration management for Folio."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# Default env var names per provider (spec §3.3)
_DEFAULT_API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
}


@dataclass
class SourceConfig:
    """A configured source directory."""
    name: str
    path: str
    target_prefix: str = ""


@dataclass
class LLMProfile:
    """A named LLM configuration profile."""
    name: str
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = ""  # Defaults via _DEFAULT_API_KEY_ENV

    def __post_init__(self):
        if not self.api_key_env:
            self.api_key_env = _DEFAULT_API_KEY_ENV.get(
                self.provider, f"{self.provider.upper().replace('-', '_')}_API_KEY"
            )


@dataclass
class LLMRoute:
    """A task-to-profile routing entry."""
    primary: str = ""
    fallbacks: list[str] = field(default_factory=list)


@dataclass
class LLMConfig:
    """LLM configuration with profile and routing support."""
    profiles: dict[str, LLMProfile] = field(default_factory=lambda: {
        "default": LLMProfile(name="default"),
    })
    routing: dict[str, LLMRoute] = field(default_factory=lambda: {
        "default": LLMRoute(primary="default"),
    })

    # Legacy fields for backward compat (used when no profiles section exists)
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"

    def resolve_profile(self, override: str | None = None,
                        task: str = "convert") -> LLMProfile:
        """Resolve the active LLM profile.

        Resolution order (spec §3.5, §6.1):
        1. --llm-profile CLI override (bypasses routing, disables fallback)
        2. routing.<task>.primary
        3. routing.default.primary
        4. first available profile

        Args:
            override: CLI --llm-profile override (takes precedence).
            task: Task name for route lookup (default: "convert").

        Returns:
            The resolved LLMProfile.

        Raises:
            ValueError: if the profile name is not found.
        """
        if override:
            # CLI override: bypass routing entirely
            profile = self.profiles.get(override)
            if profile is None:
                available = ", ".join(sorted(self.profiles.keys()))
                raise ValueError(
                    f"Unknown LLM profile '{override}'. Available: {available}"
                )
            return profile

        # Route resolution: task route → default route → first profile
        route = self.routing.get(task) or self.routing.get("default")
        if route and route.primary:
            profile = self.profiles.get(route.primary)
            if profile:
                return profile

        # Fallback: default route
        if task != "default":
            default_route = self.routing.get("default")
            if default_route and default_route.primary:
                profile = self.profiles.get(default_route.primary)
                if profile:
                    return profile

        # Last resort: return first available profile
        if self.profiles:
            first_name = next(iter(self.profiles))
            return self.profiles[first_name]

        raise ValueError("No LLM profiles configured")

    def get_fallbacks(self, override: str | None = None,
                      task: str = "convert") -> list[LLMProfile]:
        """Get the fallback profiles for the resolved route.

        Returns empty list if --llm-profile override is used (spec §3.5).
        """
        if override:
            return []  # CLI override disables fallback

        route = self.routing.get(task) or self.routing.get("default")
        if not route:
            return []

        fallbacks = []
        for fname in route.fallbacks:
            profile = self.profiles.get(fname)
            if profile:
                fallbacks.append(profile)
        return fallbacks


@dataclass
class ConversionConfig:
    """Conversion settings."""
    image_dpi: int = 150
    image_format: str = "png"
    libreoffice_timeout: int = 60
    default_passes: int = 1
    density_threshold: float = 2.0
    pptx_renderer: str = "auto"


@dataclass
class FolioConfig:
    """Top-level Folio configuration."""
    library_root: Path = field(default_factory=lambda: Path("./library"))
    sources: list[SourceConfig] = field(default_factory=list)
    llm: LLMConfig = field(default_factory=LLMConfig)
    conversion: ConversionConfig = field(default_factory=ConversionConfig)

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """Validate config values have correct types and ranges."""
        c = self.conversion
        if not isinstance(c.image_dpi, int) or c.image_dpi <= 0:
            raise ValueError(f"image_dpi must be a positive integer, got {c.image_dpi!r}")
        if not isinstance(c.default_passes, int) or c.default_passes not in (1, 2):
            raise ValueError(f"default_passes must be 1 or 2, got {c.default_passes!r}")
        if not isinstance(c.density_threshold, (int, float)) or c.density_threshold <= 0:
            raise ValueError(f"density_threshold must be a positive number, got {c.density_threshold!r}")
        if not isinstance(c.libreoffice_timeout, (int, float)) or c.libreoffice_timeout <= 0:
            raise ValueError(f"libreoffice_timeout must be a positive number, got {c.libreoffice_timeout!r}")
        if c.pptx_renderer not in ("auto", "libreoffice", "powerpoint"):
            raise ValueError(
                f"pptx_renderer must be 'auto', 'libreoffice', or 'powerpoint', got {c.pptx_renderer!r}"
            )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "FolioConfig":
        """Load config from folio.yaml, falling back to defaults."""
        if config_path is None:
            # Walk up from cwd looking for folio.yaml
            config_path = _find_config()

        if config_path is None or not config_path.exists():
            return cls()

        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

        sources = [
            SourceConfig(**s) for s in raw.get("sources", [])
        ]
        llm_raw = raw.get("llm") or {}
        profiles_raw = llm_raw.get("profiles") or {}
        routing_raw = llm_raw.get("routing") or {}

        if profiles_raw:
            # New profile-based config (spec §3.1)
            profiles = {}
            for pname, pdata in profiles_raw.items():
                if isinstance(pdata, dict):
                    profiles[pname] = LLMProfile(
                        name=pname,
                        provider=pdata.get("provider", "anthropic"),
                        model=pdata.get("model", "claude-sonnet-4-20250514"),
                        api_key_env=pdata.get("api_key_env", ""),
                    )
            if not profiles:
                profiles = {"default": LLMProfile(name="default")}

            # Parse routing (spec §3.1)
            routing = {}
            for rname, rdata in routing_raw.items():
                if isinstance(rdata, dict):
                    routing[rname] = LLMRoute(
                        primary=rdata.get("primary", ""),
                        fallbacks=rdata.get("fallbacks", []),
                    )

            # Ensure routing.default exists (spec §3.2)
            if "default" not in routing:
                # Auto-create default route pointing to first profile
                first_profile = next(iter(profiles))
                routing["default"] = LLMRoute(primary=first_profile)

            llm = LLMConfig(
                profiles=profiles,
                routing=routing,
                provider=llm_raw.get("provider", "anthropic"),
                model=llm_raw.get("model", "claude-sonnet-4-20250514"),
            )
        else:
            # Legacy flat config (spec §3.4): create synthetic profile + routes
            provider = llm_raw.get("provider", "anthropic")
            model = llm_raw.get("model", "claude-sonnet-4-20250514")
            profile_name = f"default_{provider}"
            profile = LLMProfile(
                name=profile_name, provider=provider, model=model,
            )
            llm = LLMConfig(
                profiles={profile_name: profile},
                routing={
                    "default": LLMRoute(primary=profile_name),
                    "convert": LLMRoute(primary=profile_name),
                },
                provider=provider,
                model=model,
            )
        conv_raw = raw.get("conversion") or {}
        conversion = ConversionConfig(
            image_dpi=conv_raw.get("image_dpi", 150),
            image_format=conv_raw.get("image_format", "png"),
            libreoffice_timeout=conv_raw.get("libreoffice_timeout", 60),
            default_passes=conv_raw.get("default_passes", 1),
            density_threshold=conv_raw.get("density_threshold", 2.0),
            pptx_renderer=conv_raw.get("pptx_renderer", "auto"),
        )

        return cls(
            library_root=Path(raw.get("library_root", "./library")),
            sources=sources,
            llm=llm,
            conversion=conversion,
        )


def _find_config() -> Optional[Path]:
    """Walk up from cwd looking for folio.yaml."""
    current = Path.cwd()
    for _ in range(10):  # max depth
        candidate = current / "folio.yaml"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None
