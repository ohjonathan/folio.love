"""Configuration management for Folio."""

from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
from typing import Optional

import yaml

from .llm.types import ProviderRuntimeSettings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default provider runtime settings
# ---------------------------------------------------------------------------

_KNOWN_ENDPOINTS: dict[str, set[str]] = {
    "anthropic": {"messages"},
    "openai": {"chat_completions"},
    "google": {"generate_content"},
}

_DEFAULT_PROVIDER_SETTINGS: dict[str, ProviderRuntimeSettings] = {
    "anthropic": ProviderRuntimeSettings(
        rate_limit_rpm=50,
        rate_limit_tpm=80000,
        max_attempts=3,
        base_delay_seconds=1.0,
        max_delay_seconds=60.0,
        allowed_endpoints=("messages",),
    ),
    "openai": ProviderRuntimeSettings(
        rate_limit_rpm=60,
        rate_limit_tpm=None,
        max_attempts=3,
        base_delay_seconds=1.0,
        max_delay_seconds=60.0,
        allowed_endpoints=("chat_completions",),
    ),
    "google": ProviderRuntimeSettings(
        rate_limit_rpm=60,
        rate_limit_tpm=None,
        max_attempts=3,
        base_delay_seconds=1.0,
        max_delay_seconds=60.0,
        allowed_endpoints=("generate_content",),
    ),
}


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
    base_url_env: str = ""

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

        # Route resolution: task route → default route
        route = self.routing.get(task) or self.routing.get("default")
        if route and route.primary:
            profile = self.profiles.get(route.primary)
            if profile:
                return profile
            raise ValueError(
                f"Route '{task}' references missing profile '{route.primary}'. "
                f"Available: {', '.join(sorted(self.profiles.keys()))}"
            )

        # Fallback: default route
        if task != "default":
            default_route = self.routing.get("default")
            if default_route and default_route.primary:
                profile = self.profiles.get(default_route.primary)
                if profile:
                    return profile
                raise ValueError(
                    f"Default route references missing profile '{default_route.primary}'. "
                    f"Available: {', '.join(sorted(self.profiles.keys()))}"
                )

        raise ValueError(
            f"No route configured for task '{task}' and no default route found"
        )

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
    review_confidence_threshold: float = 0.6
    diagram_max_tokens: int = 16384
    max_image_pixels: Optional[int] = None


@dataclass
class FolioConfig:
    """Top-level Folio configuration."""
    library_root: Path = field(default_factory=lambda: Path("./library"))
    sources: list[SourceConfig] = field(default_factory=list)
    llm: LLMConfig = field(default_factory=LLMConfig)
    conversion: ConversionConfig = field(default_factory=ConversionConfig)
    providers: dict[str, ProviderRuntimeSettings] = field(
        default_factory=lambda: dict(_DEFAULT_PROVIDER_SETTINGS)
    )
    config_dir: Optional[Path] = None  # directory containing folio.yaml

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
        if not isinstance(c.review_confidence_threshold, (int, float)):
            raise ValueError(
                f"review_confidence_threshold must be a number, got {c.review_confidence_threshold!r}"
            )
        if c.review_confidence_threshold < 0.0 or c.review_confidence_threshold > 1.0:
            raise ValueError(
                f"review_confidence_threshold must be between 0.0 and 1.0, got {c.review_confidence_threshold!r}"
            )
        if not isinstance(c.diagram_max_tokens, int) or c.diagram_max_tokens <= 0:
            raise ValueError(
                f"diagram_max_tokens must be a positive integer, got {c.diagram_max_tokens!r}"
            )
        if c.diagram_max_tokens > 32768:
            raise ValueError(
                f"diagram_max_tokens must be <= 32768 (proposal ceiling), got {c.diagram_max_tokens!r}"
            )
        if c.max_image_pixels is not None:
            if not isinstance(c.max_image_pixels, int) or c.max_image_pixels <= 0:
                raise ValueError(
                    f"max_image_pixels must be None or a positive integer, got {c.max_image_pixels!r}"
                )

        # LLM validation (spec §3.2)
        self._validate_llm()

        # Provider runtime settings validation
        self._validate_providers()

    def _validate_providers(self):
        """Validate provider runtime settings."""
        supported = {"anthropic", "openai", "google"}
        for pname, settings in self.providers.items():
            if pname not in supported:
                raise ValueError(
                    f"Unknown provider '{pname}'. Supported: {', '.join(sorted(supported))}"
                )
            if settings.rate_limit_rpm <= 0:
                raise ValueError(
                    f"Provider '{pname}': rate_limit_rpm must be > 0, got {settings.rate_limit_rpm}"
                )
            if settings.rate_limit_tpm is not None and settings.rate_limit_tpm <= 0:
                raise ValueError(
                    f"Provider '{pname}': rate_limit_tpm must be None or > 0, got {settings.rate_limit_tpm}"
                )
            if settings.max_attempts < 1:
                raise ValueError(
                    f"Provider '{pname}': max_attempts must be >= 1, got {settings.max_attempts}"
                )
            if settings.base_delay_seconds <= 0:
                raise ValueError(
                    f"Provider '{pname}': base_delay_seconds must be > 0, got {settings.base_delay_seconds}"
                )
            if settings.max_delay_seconds < settings.base_delay_seconds:
                raise ValueError(
                    f"Provider '{pname}': max_delay_seconds ({settings.max_delay_seconds}) "
                    f"must be >= base_delay_seconds ({settings.base_delay_seconds})"
                )
            known = _KNOWN_ENDPOINTS.get(pname, set())
            for ep in settings.allowed_endpoints:
                if ep not in known:
                    raise ValueError(
                        f"Provider '{pname}': unknown allowed endpoint '{ep}'. "
                        f"Known: {', '.join(sorted(known))}"
                    )
            for ep in settings.excluded_endpoints:
                if ep not in known:
                    raise ValueError(
                        f"Provider '{pname}': unknown excluded endpoint '{ep}'. "
                        f"Known: {', '.join(sorted(known))}"
                    )
            overlap = set(settings.allowed_endpoints) & set(settings.excluded_endpoints)
            if overlap:
                raise ValueError(
                    f"Provider '{pname}': endpoints in both allowed and excluded: "
                    f"{', '.join(sorted(overlap))}"
                )

    def _validate_llm(self):
        """Validate LLM profiles and routing per spec §3.2."""
        _PROFILE_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')
        _SUPPORTED_PROVIDERS = {"anthropic", "openai", "google"}

        # Validate profile names (spec §3.2)
        for pname in self.llm.profiles:
            if not _PROFILE_NAME_RE.match(pname):
                raise ValueError(
                    f"LLM profile name '{pname}' does not match required pattern "
                    f"'^[a-z][a-z0-9_]*$' (spec §3.2)"
                )

        # Validate providers
        for pname, profile in self.llm.profiles.items():
            if profile.provider not in _SUPPORTED_PROVIDERS:
                raise ValueError(
                    f"LLM profile '{pname}' uses unsupported provider "
                    f"'{profile.provider}'. Supported: {', '.join(sorted(_SUPPORTED_PROVIDERS))}"
                )
            if not isinstance(profile.base_url_env, str):
                raise ValueError(
                    f"LLM profile '{pname}' base_url_env must be a string, "
                    f"got {profile.base_url_env!r}"
                )

        # Validate routing.default exists
        if "default" not in self.llm.routing:
            raise ValueError(
                "LLM config requires a 'routing.default' entry (spec §3.2)"
            )

        # Validate all route targets reference existing profiles
        for rname, route in self.llm.routing.items():
            if route.primary and route.primary not in self.llm.profiles:
                raise ValueError(
                    f"LLM route '{rname}' references missing profile "
                    f"'{route.primary}'. Available: {', '.join(sorted(self.llm.profiles.keys()))}"
                )
            for fallback in route.fallbacks:
                if fallback not in self.llm.profiles:
                    raise ValueError(
                        f"LLM route '{rname}' fallback references missing profile "
                        f"'{fallback}'. Available: {', '.join(sorted(self.llm.profiles.keys()))}"
                    )
                # Fallback must not be the same as primary (M8)
                if fallback == route.primary:
                    raise ValueError(
                        f"LLM route '{rname}' fallback '{fallback}' is the same as "
                        f"its primary profile — self-referencing fallback is not allowed"
                    )
            # Reject duplicate fallback entries (M8)
            if len(route.fallbacks) != len(set(route.fallbacks)):
                dupes = [f for f in route.fallbacks if route.fallbacks.count(f) > 1]
                raise ValueError(
                    f"LLM route '{rname}' has duplicate fallback entries: "
                    f"{', '.join(sorted(set(dupes)))}"
                )

    def resolve_source_roots(self, base_path: Optional[Path] = None) -> list[tuple["SourceConfig", Path]]:
        """Resolve configured source roots to absolute paths.

        Args:
            base_path: Base directory for resolving relative paths.
                       Defaults to cwd.

        Returns:
            List of (SourceConfig, resolved_absolute_path) tuples.
        """
        base = Path(base_path) if base_path else (self.config_dir or Path.cwd())
        result = []
        for src in self.sources:
            resolved = (base / src.path).resolve()
            result.append((src, resolved))
        return result

    def match_source_root(
        self, source_path: Path, base_path: Optional[Path] = None
    ) -> Optional[tuple["SourceConfig", Path]]:
        """Match a source file to a configured source root.

        Args:
            source_path: Absolute path to the source file.
            base_path: Base directory for resolving source root paths.

        Returns:
            (SourceConfig, relative_path_from_root) or None if no match.
        """
        source_path = Path(source_path).resolve()
        for src_config, resolved_root in self.resolve_source_roots(base_path):
            try:
                rel = source_path.relative_to(resolved_root)
                return (src_config, rel)
            except ValueError:
                continue
        return None

    @staticmethod
    def normalize_target_prefix(prefix: str) -> str:
        """Normalize a target_prefix for consistent path construction.

        Strips trailing slashes so ``""``, ``"Internal"``, and
        ``"Internal/"`` all behave consistently.

        Raises ValueError if any path component is ``..`` (path traversal).
        """
        cleaned = prefix.strip("/").strip()
        if ".." in cleaned.split("/"):
            raise ValueError(f"target_prefix must not contain '..': {prefix!r}")
        return cleaned

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
                        base_url_env=pdata.get("base_url_env", ""),
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

            # routing.default is required (spec §3.2) — validated by _validate_llm()

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
            review_confidence_threshold=conv_raw.get("review_confidence_threshold", 0.6),
            diagram_max_tokens=conv_raw.get("diagram_max_tokens", 16384),
            max_image_pixels=conv_raw.get("max_image_pixels", None),
        )

        # Parse provider runtime settings (merge onto defaults)
        providers_raw = raw.get("providers") or {}
        providers = dict(_DEFAULT_PROVIDER_SETTINGS)
        for pname, pdata in providers_raw.items():
            if isinstance(pdata, dict) and pname in _DEFAULT_PROVIDER_SETTINGS:
                defaults = _DEFAULT_PROVIDER_SETTINGS[pname]
                providers[pname] = ProviderRuntimeSettings(
                    rate_limit_rpm=pdata.get("rate_limit_rpm", defaults.rate_limit_rpm),
                    rate_limit_tpm=pdata.get("rate_limit_tpm", defaults.rate_limit_tpm),
                    max_attempts=pdata.get("max_attempts", defaults.max_attempts),
                    base_delay_seconds=pdata.get("base_delay_seconds", defaults.base_delay_seconds),
                    max_delay_seconds=pdata.get("max_delay_seconds", defaults.max_delay_seconds),
                    allowed_endpoints=tuple(pdata.get("allowed_endpoints", defaults.allowed_endpoints)),
                    excluded_endpoints=tuple(pdata.get("excluded_endpoints", defaults.excluded_endpoints)),
                    require_store_false=pdata.get("require_store_false", defaults.require_store_false),
                )
            elif isinstance(pdata, dict):
                raise ValueError(
                    f"Unknown provider '{pname}' in config. "
                    f"Known providers: {', '.join(sorted(_DEFAULT_PROVIDER_SETTINGS))}. "
                    f"Check for typos in folio.yaml."
                )

        config_dir = config_path.resolve().parent

        return cls(
            library_root=Path(raw.get("library_root", "./library")),
            sources=sources,
            llm=llm,
            conversion=conversion,
            providers=providers,
            config_dir=config_dir,
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
