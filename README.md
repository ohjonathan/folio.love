# folio

Your consulting portfolio, searchable and AI-ready.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)

## What It Does

Folio converts PPTX, PPT, and PDF presentations into structured Markdown with YAML frontmatter, slide images, and optional LLM-powered analysis. Every conversion preserves three layers: verbatim text, slide images at configurable DPI, and per-slide classification with evidence grounding.

Folio tracks versions automatically -- re-converting an updated deck increments the version, detects per-slide changes, and preserves history. Open `library/` as an Obsidian vault for automatic frontmatter indexing.

## Install

```bash
pip install folio-love
```

The CLI command is `folio`.

For agent-friendly setup (Cursor, Claude Code), see [Agentic Setup](https://github.com/ohjonathan/folio.love/blob/main/docs/guides/agentic_setup.md).

Or install from source:

```bash
git clone https://github.com/ohjonathan/folio.love.git
cd folio.love
pip install -e .
```

Anthropic support is included by default. For OpenAI or Google Gemini, install with extras:

```bash
pip install "folio-love[llm]"        # from PyPI
pip install -e ".[llm]"              # from source
```

## Prerequisites

- Python 3.10+
- [LibreOffice](https://www.libreoffice.org/) or Microsoft PowerPoint (for PPTX/PPT conversion)
- [Poppler](https://poppler.freedesktop.org/) (for PDF image extraction)

```bash
# macOS
brew install --cask libreoffice
brew install poppler

# Ubuntu/Debian
sudo apt install libreoffice poppler-utils
```

<details>
<summary>Managed macOS (no LibreOffice)</summary>

If your machine blocks LibreOffice, Folio can use Microsoft PowerPoint as the renderer. Set `pptx_renderer: powerpoint` in `folio.yaml`, run batch jobs from Terminal.app, and keep a dedicated PowerPoint session with no unrelated presentations open. See [Managed Mac workflow](https://github.com/ohjonathan/folio.love/blob/main/docs/guides/managed_mac_workflow.md) for the full workflow.

If neither renderer is available, export the deck to PDF manually and run `folio convert deck.pdf`.

</details>

## Quick Start

**First conversion**

```bash
folio convert deck.pptx
```

```
✓ deck.pptx
  24 slides → library/deck/deck.md
  Version: 1 | ID: evidence_20260306_deck
```

**With LLM analysis**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
folio convert deck.pptx --passes 2
```

Without a valid API key, analysis is skipped gracefully -- the conversion still completes.

## Commands

### `folio convert`

Convert a single deck to Folio markdown.

```bash
# Basic
folio convert deck.pptx

# With client and engagement metadata
folio convert deck.pptx --client Acme --engagement "DD Q1 2026"

# Deep analysis (two-pass, selective re-analysis of dense slides)
folio convert deck.pptx --passes 2

# Force fresh analysis, ignore cache
folio convert deck.pptx --no-cache

# Full metadata
folio convert deck.pptx \
  --client Acme \
  --engagement "DD Q1 2026" \
  --subtype research \
  --industry "retail,ecommerce" \
  --tags "market-sizing,tam" \
  --note "Updated risk figures"
```

**Flags**

| Flag | Description |
|------|-------------|
| `--client` | Client name (used in output path and frontmatter) |
| `--engagement` | Engagement identifier |
| `--note`, `-n` | Version note (e.g. "Updated per client feedback") |
| `--target`, `-t` | Override output directory |
| `--passes`, `-p` | Analysis depth: `1` = standard, `2` = deep (selective second pass on dense slides) |
| `--no-cache` | Force re-analysis; fresh results replace cached entries |
| `--subtype` | Evidence subtype: `research`, `data_extract`, `external_report`, `benchmark` |
| `--industry` | Industry tags, comma-separated |
| `--tags` | Manual tags to merge with auto-generated, comma-separated |
| `--llm-profile` | Override the configured LLM profile for this run |

### `folio batch`

Batch convert all matching files in a directory.

```bash
# Convert all PPTX files in a directory
folio batch ./materials --client Acme

# Convert PDFs instead
folio batch ./pdfs --pattern "*.pdf" --client Acme

# Disable PowerPoint restart automation
folio batch ./materials --no-dedicated-session
```

Accepts the same flags as `convert` (`--client`, `--engagement`, `--passes`, `--llm-profile`, etc.). Default pattern is `*.pptx`. On macOS with PowerPoint, `--dedicated-session` (the default) enables periodic restart during long batch runs.

### `folio status`

Show library health -- which decks are current, stale, or missing their source file.

```bash
folio status
folio status Acme        # scope to a client
folio status --refresh   # re-check source hashes
```

**Stale** means the source file changed since the last conversion -- re-run `folio convert` on it. **Missing** means the source file can no longer be found at the original path.

### `folio scan`

Scan configured source roots for new, stale, or missing files.

```bash
folio scan
folio scan --scope ClientA
```

Requires `sources` entries in `folio.yaml` (see [Configuration](#configuration)).

### `folio refresh`

Re-convert stale decks in the library.

```bash
folio refresh
folio refresh --scope ClientA/DD_Q1_2026
folio refresh --all     # re-convert everything in scope, not just stale
```

### `folio promote`

Promote a deck's curation level (L0 → L1 → L2 → L3).

```bash
folio promote <deck_id> L1
```

Validates required metadata per level (e.g. L1 requires `client` and `tags`). Use `folio status` to find deck IDs.

**Global flags**: `--verbose` / `-v` (debug logging), `--config` / `-c` (path to `folio.yaml`)

## Output Structure

```
library/
└── Acme/
    └── dd_q1_2026/
        └── market_overview/
            ├── market_overview.md        # Full markdown with frontmatter
            ├── slides/
            │   ├── slide-001.png
            │   ├── slide-002.png
            │   └── ...
            ├── .analysis_cache.json      # LLM response cache
            ├── .texts_cache.json         # Text extraction cache
            └── version_history.json      # Full version log
```

**Example output** (condensed):

````markdown
---
id: acme_dd_q1_2026_evidence_20260306_market_overview
title: Market Overview
type: evidence
subtype: research
status: active
client: Acme
engagement: DD Q1 2026
version: 2
tags:
- ecommerce
- market-sizing
---

# Market Overview

**Source:** `/materials/market_overview.pptx`
**Version:** 2 | **Converted:** 2026-03-06

---

## Slide 1

![Slide 1](slides/slide-001.png)

### Text (Verbatim)

> Total Addressable Market: $4.2B
> Source: Industry Report 2025

### Analysis

**Slide Type:** data_heavy
**Framework:** TAM/SAM/SOM
**Key Data:** TAM $4.2B, SAM $1.8B, SOM $340M

**Evidence:**
- **TAM figure of $4.2B (high):** "Total Addressable Market: $4.2B" *(title)*

---
````

## Configuration

Folio looks for `folio.yaml` by walking up from the current directory. All fields are optional.

```yaml
# folio.yaml
library_root: ./library              # Where converted decks are written

sources:                             # Optional; organize source directories
  - name: materials
    path: /path/to/source/decks
    target_prefix: ""

llm:
  profiles:
    high_quality_anthropic:
      provider: anthropic
      model: claude-sonnet-4-20250514
      api_key_env: ANTHROPIC_API_KEY
      base_url_env: ANTHROPIC_BASE_URL   # Optional enterprise gateway

    fast_openai:
      provider: openai
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY
      base_url_env: OPENAI_BASE_URL      # Optional enterprise gateway

    backup_google:
      provider: google
      model: gemini-2.5-pro
      api_key_env: GEMINI_API_KEY
      base_url_env: GEMINI_BASE_URL      # Optional enterprise gateway

  routing:
    default:
      primary: high_quality_anthropic
      fallbacks: []
    convert:
      primary: high_quality_anthropic
      fallbacks: [backup_google]

conversion:
  image_dpi: 150                     # Slide image resolution (px/in)
  image_format: png
  libreoffice_timeout: 60            # Seconds before conversion times out
  default_passes: 1                  # 1 = standard, 2 = deep
  density_threshold: 2.0             # Pass 2 density trigger
  pptx_renderer: auto                # auto | libreoffice | powerpoint
```

With no `folio.yaml`, Folio uses sensible defaults: output goes to `./library`, images render at 150 DPI, and analysis runs a single Anthropic-backed pass if `ANTHROPIC_API_KEY` is set.

| Environment Variable | Purpose |
|---------------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic credentials (included in base install) |
| `OPENAI_API_KEY` | OpenAI credentials (requires `folio-love[llm]`) |
| `GEMINI_API_KEY` | Google Gemini credentials (requires `folio-love[llm]`) |
| `ANTHROPIC_BASE_URL` | Optional Anthropic-compatible gateway URL |
| `OPENAI_BASE_URL` | Optional OpenAI-compatible gateway URL |
| `GEMINI_BASE_URL` | Optional Gemini-compatible gateway URL |

### Enterprise Gateways and Preflight Warnings

If you route Folio through an enterprise AI gateway, keep the gateway URL in an
environment variable and reference it from the profile with `base_url_env`.
If the env var is unset or blank, Folio silently falls back to the SDK default
endpoint.

Folio now runs a warning-only model preflight once per selected profile per
conversion run. This checks whether the configured model appears usable before
the first expensive pass. The probe is bounded and uses the same runtime
guardrails as normal model calls. A warning does **not** block conversion; it
simply surfaces blocked or unavailable models earlier.

### Scanned and Image-Only PDFs

When a deck has no extractable text, Folio marks that text validation was
unavailable instead of treating the deck as if evidence validation failed.
Those decks still surface review flags, but they no longer get the old blanket
`0.59` confidence cap just because the source is scanned.

### Oversized PDF Page Fallback

Large architecture diagrams and poster-sized PDF pages can exceed Pillow safety
limits at the requested DPI. Folio now backs off DPI per page before hitting
that limit. If a page still cannot be rendered safely, conversion fails with a
specific oversized-image error instead of a generic rendering failure.

### OpenAI GPT-5 Compatibility

GPT-5 OpenAI chat models use a slightly different request shape from GPT-4.x
and GPT-4o. Folio handles that automatically by using
`max_completion_tokens` and omitting `temperature` for `gpt-5*` models while
preserving the existing request shape for non-GPT-5 models.

## How It Works

```
Input (.pptx/.ppt/.pdf)
  │
  ├─ Normalize ──→ Convert to PDF via LibreOffice or PowerPoint
  │
  ├─ Images ─────→ Extract slide images, detect blank slides
  │
  ├─ Text ───────→ Extract structured text per slide, reconcile count
  │
  ├─ Analysis ───→ LLM classification + evidence extraction (cached)
  │                 Pass 2: selective re-analysis of dense slides
  │
  ├─ Tracking ───→ Version detection, per-slide change diffing
  │
  └─ Assembly ───→ YAML frontmatter + Markdown output (atomic write)
```

Each stage is independent and testable. LLM analysis results are cached per-slide -- re-conversion only re-analyzes changed slides. Blank slides are detected via image histogram analysis and excluded from deep analysis.

## Version Tracking

Re-converting an updated deck increments the version and records which slides were added, modified, or removed.

```bash
folio convert deck.pptx --note "Updated risk figures"
```

```
✓ deck.pptx
  24 slides → library/deck/deck.md
  Version: 2 | ID: evidence_20260306_deck
  Modified: slides 3, 7, 12
  Added: slides 24
```

Use `folio status` to find stale decks -- where the source file has changed since the last conversion.

Version history is recorded in both the markdown output and `version_history.json`:

| Version | Date | Changes | Note |
|---------|------|---------|------|
| v2 | 2026-03-06 | 3 modified, 1 added | Updated risk figures |
| v1 | 2026-03-01 | Initial (23 slides) | -- |

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m pytest --cov=folio
```

The test suite depends on dev-only packages such as `python-pptx` and `reportlab`, so run it from the project virtualenv after installing `.[dev]` rather than from an arbitrary system Python.

```
folio/
├── cli.py              # Click CLI (convert, batch, status, scan, refresh, promote)
├── config.py           # FolioConfig + folio.yaml loading
├── converter.py        # Pipeline orchestrator
├── pipeline/
│   ├── normalize.py    # PPTX/PPT → PDF
│   ├── images.py       # PDF → slide images + blank detection
│   ├── text.py         # Structured text extraction + reconciliation
│   └── analysis.py     # LLM analysis + caching
├── output/
│   ├── frontmatter.py  # YAML frontmatter (v2 schema)
│   └── markdown.py     # Markdown assembly
└── tracking/
    ├── sources.py      # Source file tracking + staleness
    └── versions.py     # Version detection + change sets
```

## Roadmap

Search and retrieval (`folio search`) is planned but not yet implemented. Today, converted decks are searchable via Obsidian, grep, or any tool that reads Markdown + YAML frontmatter.

## License

Apache 2.0
