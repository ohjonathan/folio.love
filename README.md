# folio

Your consulting portfolio, searchable and AI-ready.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)

## What It Does

Turn consulting decks into structured, searchable markdown -- with version tracking and optional AI analysis.

Folio converts PPTX, PPT, and PDF presentations into Markdown with YAML frontmatter, slide images, and optional LLM-powered analysis. Every conversion preserves three layers: exact verbatim text, slide images at configurable DPI, and per-slide analysis with evidence grounding.

Folio tracks versions automatically -- re-converting an updated deck increments the version, detects per-slide changes, and preserves history. Open `library/` as an Obsidian vault and frontmatter is indexed automatically.

## Quick Start

**Prerequisites**

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

If you're on a managed macOS laptop that blocks LibreOffice, Folio can use
Microsoft PowerPoint as the PPTX/PPT renderer. The current PowerPoint path opens
decks via Launch Services (`open -a "Microsoft PowerPoint" ...`) and then exports
to PDF. In batch mode, Folio can also restart PowerPoint periodically during
long PPTX runs when `--dedicated-session` is enabled (the default).

For managed-mac usage:
- Run batch jobs from `Terminal.app`
- Use a dedicated PowerPoint session with no unrelated presentations open
- See [docs/guides/managed_mac_workflow.md](docs/guides/managed_mac_workflow.md)
  for the full workflow and PDF fallback guidance

You can force a specific renderer with `pptx_renderer: powerpoint` in
`folio.yaml`. If neither renderer is available, export the deck to PDF in
PowerPoint and run `folio convert deck.pdf`.

**Install**

```bash
git clone https://github.com/ohjonathan/folio.love.git
cd folio.love
pip install -e .
```

Anthropic support is included in the base install. If you want to use OpenAI or
Google Gemini, install the optional provider SDKs too:

```bash
pip install -e ".[llm]"
```

**First conversion**

```bash
folio convert deck.pptx
```

```
✓ deck.pptx
  24 slides → library/deck/deck.md
  Version: 1 | ID: evidence_20260306_deck
```

**Enable LLM analysis**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
folio convert deck.pptx --passes 2
```

Folio now supports Anthropic, OpenAI, and Google Gemini for slide analysis.
Configure named profiles in `folio.yaml`, then either use the default `convert`
route or override it per run with `--llm-profile`.

```yaml
llm:
  profiles:
    high_quality_anthropic:
      provider: anthropic
      model: claude-sonnet-4-20250514
      api_key_env: ANTHROPIC_API_KEY

    fast_openai:
      provider: openai
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY

    backup_google:
      provider: google
      model: gemini-2.5-pro
      api_key_env: GEMINI_API_KEY

  routing:
    default:
      primary: high_quality_anthropic
      fallbacks: []
    convert:
      primary: high_quality_anthropic
      fallbacks: [backup_google]
```

```bash
# Uses llm.routing.convert
folio convert deck.pptx --passes 2

# Force a specific profile for this run (disables route fallbacks)
folio convert deck.pptx --llm-profile fast_openai
```

Without a valid provider SDK or API key, analysis is skipped gracefully. The
tool still completes conversion and writes provider-aware pending-analysis
messages into the markdown output.

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
| `--llm-profile` | Override the configured LLM profile for this command |

### `folio batch`

Batch convert all matching files in a directory.

```bash
# Automated PPTX conversion
folio batch ./materials --client Acme

# PDF mitigation workflow (not Tier 1)
folio batch ./pdfs --pattern "*.pdf" --client Acme

# Skip restart automation if other presentations are open in PowerPoint
folio batch ./materials --no-dedicated-session
```

```
Converting 3 files...

✓ overview.pptx (18 slides, 4.1s)
✓ financials.pptx (32 slides, 7.8s)
✓ appendix.pptx (12 slides, 2.9s)

Automated PPTX: 3 succeeded, 0 failed
```

Accepts the same flags as `convert` (`--client`, `--engagement`, `--passes`, `--llm-profile`, etc.). Default pattern is `*.pptx`.

`batch` also supports `--dedicated-session/--no-dedicated-session` for the
PowerPoint restart workflow on managed macOS. Operator-exported PDF batches are
supported, but they are mitigation-only and do not count toward Tier 1 automated
conversion goals.

### `folio status`

Show library health -- which decks are current, stale, or missing their source file.

```bash
folio status
folio status Acme    # scope to a client
```

```
Library: 5 decks
  ✓ Current: 3
  ⚠ Stale: 1
  ✗ Missing source: 1

Stale:
  Acme/dd_q1_2026/financials/financials.md

Missing:
  Acme/dd_q1_2026/appendix/appendix.md (source: /materials/appendix.pptx)
```

**Stale** means the source file changed since the last conversion -- re-run `folio convert` on it. **Missing** means the source file can no longer be found at the original path.

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
source: /materials/market_overview.pptx
source_hash: a1b2c3d4e5f6
version: 2
created: 2026-03-01T10:00:00Z
modified: 2026-03-06T14:30:00Z
client: Acme
engagement: DD Q1 2026
industry:
- ecommerce
- retail
frameworks:
- TAM/SAM/SOM
tags:
- ecommerce
- market-sizing
- retail
_llm_metadata:
  convert:
    requested_profile: high_quality_anthropic
    profile: high_quality_anthropic
    provider: anthropic
    model: claude-sonnet-4-20250514
    fallback_used: false
    status: executed
    pass2:
      status: skipped
      reason: pass_disabled
---

# Market Overview

**Source:** `/materials/market_overview.pptx`
**Version:** 2 | **Converted:** 2026-03-06
**Status:** △ Current

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
**Main Insight:** Market sizing shows serviceable segment at 43% of TAM

**Evidence:**
- **TAM figure of $4.2B (high):** "Total Addressable Market: $4.2B" *(title)*
- **SAM represents 43% of TAM (medium, pass 2):** "SAM $1.8B" *(body)* [unverified]

---
````

## Configuration

Folio looks for `folio.yaml` by walking up from the current directory. All
fields are optional, and the example below shows a multi-provider setup rather
than the minimal default config.

```yaml
# folio.yaml — example multi-provider configuration
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

    fast_openai:
      provider: openai
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY

    backup_google:
      provider: google
      model: gemini-2.5-pro
      api_key_env: GEMINI_API_KEY

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

Legacy shorthand is still supported for Anthropic-only setups:

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
```

With no `folio.yaml`, Folio uses these defaults: output goes to `./library`,
images render at 150 DPI, and analysis runs a single Anthropic-backed pass if
`ANTHROPIC_API_KEY` is present.

| Environment Variable | Purpose |
|---------------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic profile credentials |
| `OPENAI_API_KEY` | OpenAI profile credentials (`pip install -e ".[llm]"`) |
| `GEMINI_API_KEY` | Google Gemini profile credentials (`pip install -e ".[llm]"`) |

## How It Works

```
Input (.pptx/.ppt/.pdf)
  │
  ├─ Normalize ──→ Convert to PDF
  │                 LibreOffice (headless) or PowerPoint on macOS
  │                 PowerPoint path: Launch Services open + AppleScript export
  │                 PDF input: direct copy + warning heuristics
  │
  ├─ Images ─────→ Extract slide images, detect blank slides
  │
  ├─ Text ───────→ Extract structured text per slide, reconcile count
  │
  ├─ Analysis ───→ Route-based LLM classification + evidence extraction (cached)
  │                 Optional transient fallback to backup profiles
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
pip install -e ".[dev]"
pytest
pytest --cov=folio
```

```
folio/
├── cli.py              # Click CLI (convert, batch, status)
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
