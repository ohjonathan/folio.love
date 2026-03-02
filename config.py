"""Configuration management for Folio."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SourceConfig:
    """A configured source directory."""
    name: str
    path: str
    target_prefix: str = ""


@dataclass
class LLMConfig:
    """LLM configuration."""
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    # API key read from ANTHROPIC_API_KEY env var


@dataclass
class ConversionConfig:
    """Conversion settings."""
    image_dpi: int = 150
    image_format: str = "png"
    libreoffice_timeout: int = 60


@dataclass
class FolioConfig:
    """Top-level Folio configuration."""
    library_root: Path = field(default_factory=lambda: Path("./library"))
    sources: list[SourceConfig] = field(default_factory=list)
    llm: LLMConfig = field(default_factory=LLMConfig)
    conversion: ConversionConfig = field(default_factory=ConversionConfig)

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
        llm_raw = raw.get("llm", {})
        llm = LLMConfig(
            provider=llm_raw.get("provider", "anthropic"),
            model=llm_raw.get("model", "claude-sonnet-4-20250514"),
        )
        conv_raw = raw.get("conversion", {})
        conversion = ConversionConfig(
            image_dpi=conv_raw.get("image_dpi", 150),
            image_format=conv_raw.get("image_format", "png"),
            libreoffice_timeout=conv_raw.get("libreoffice_timeout", 60),
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
