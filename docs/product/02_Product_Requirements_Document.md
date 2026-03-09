---
id: doc_02_product_requirements_document
type: atom
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Folio: Product Requirements Document

**Version 1.0 | January 2026**  
**folio.love**

---

## 1. Product Overview

### 1.1 Purpose

This document defines the requirements for Folio, a knowledge management system that converts consulting materials into an AI-native, searchable library. Requirements are prioritized by the hierarchy of value: conversion quality first, then version integrity, then organization features.

### 1.2 Scope

Folio v1.0 encompasses:
- Document conversion pipeline (PPTX/PDF to Markdown)
- Source file tracking with relative paths
- Version tracking and change detection
- Optional LLM analysis with bring-your-own provider credentials
- Knowledge library organization (multi-client, multi-project)
- Obsidian-compatible output format
- CLI for all operations

### 1.3 Definitions

| Term | Definition |
|------|------------|
| Deck | A PowerPoint presentation (.pptx) or PDF document |
| Library | The organized collection of all converted materials (an Obsidian vault) |
| Source Path | Relative path from the markdown file to the original source file |
| Source Hash | SHA256 hash of the source file for staleness detection |
| Verbatim Text | Exact text extracted from slides, preserving wording |
| Analysis | LLM-generated description of visual content and frameworks |
| Frontmatter | YAML metadata block at the top of markdown files (Obsidian standard) |

---

## 2. Functional Requirements

### 2.1 Core Conversion (FR-100) — P0 CRITICAL

These requirements are non-negotiable. If any of these fail, the entire system fails.

#### FR-101: Slide Image Extraction

The system SHALL extract a PNG image for every slide/page:
- Resolution: 150 DPI minimum
- Format: PNG (lossless)
- Naming: `slide-NNN.png` (zero-padded to 3 digits)
- Storage: `slides/` subdirectory within deck folder

**Acceptance Criteria:**
- [ ] Every slide in source has corresponding image in output
- [ ] Images are legible (text readable, diagrams clear)
- [ ] Images render correctly in Obsidian preview

#### FR-102: Verbatim Text Extraction

The system SHALL extract text exactly as it appears in the source:
- Preserve exact wording (no paraphrasing)
- Maintain bullet points and numbering
- Preserve table structure where detectable
- Display in blockquote format for visual distinction

**Acceptance Criteria:**
- [ ] Text diff between source and extraction shows <1% character difference
- [ ] Bullet points appear as bullets, not mangled
- [ ] Tables render as markdown tables

#### FR-103: LLM Analysis Generation

The system SHALL generate analysis for each slide using the configured LLM provider when valid credentials are available:
- **Slide Type:** title, executive-summary, framework, data, narrative, next-steps, appendix
- **Framework Detection:** 2x2-matrix, scr, mece, waterfall, gantt, timeline, process-flow, org-chart
- **Visual Description:** Axes labels, quadrant contents, chart types, spatial relationships
- **Key Data Points:** Numbers, percentages, metrics mentioned
- **Main Insight:** One-sentence summary of the "so what"

Supported providers in v1.0:
- Anthropic
- OpenAI
- Google Gemini

**Acceptance Criteria:**
- [ ] Every slide has all five analysis fields populated
- [ ] Framework detection correctly identifies common consulting frameworks
- [ ] Visual description captures information lost in text-only extraction
- [ ] If analysis cannot run, conversion still succeeds with pending-analysis placeholders

#### FR-104: Source File Tracking

The system SHALL maintain a link back to the original source file:
- **Relative Path:** Path from markdown file to source (portable across machines)
- **Source Hash:** SHA256 hash of source file at conversion time
- **Display:** Source path shown in markdown header AND frontmatter

**Acceptance Criteria:**
- [ ] Source path is valid and file exists at that location
- [ ] User can open original file within 2 clicks from markdown
- [ ] Path works when library is synced via OneDrive/Dropbox to another machine

#### FR-105: Markdown Assembly

The system SHALL produce a single markdown file per deck with:
- Obsidian-compatible YAML frontmatter
- Source tracking (path and hash)
- Version information
- Per-slide sections with image, verbatim text, and analysis
- Version history table at end

---

### 2.2 Source Management (FR-200) — P0 CRITICAL

#### FR-201: Relative Path Storage

Source paths SHALL be stored as relative paths:
- Relative to the markdown file location
- Use forward slashes (cross-platform compatible)
- Handle spaces and special characters correctly

Example:
```
Markdown: library/ClientA/Project1/market_sizing.md
Source:   sources/ClientA/Project1/market_sizing.pptx
Path:     ../../../sources/ClientA/Project1/market_sizing.pptx
```

#### FR-202: Source Configuration

The system SHALL support configuring source directories:
- Map source roots to library locations
- Store configuration in `folio.yaml` at library root
- Support multiple source roots

```yaml
# folio.yaml
library_root: ./library
sources:
  - name: client-materials
    path: ../client_materials
  - name: internal
    path: ../internal_templates
  - name: research
    path: C:/Users/Johnny/Research  # absolute paths allowed for external sources
```

#### FR-203: Source Hash Verification

The system SHALL track source file hashes:
- Compute SHA256 hash at conversion time
- Store hash in frontmatter and version_history.json
- Compare hashes to detect source file changes

---

### 2.3 Version Tracking (FR-300) — P0 CRITICAL

#### FR-301: Change Detection

When re-converting a previously converted deck, the system SHALL:
- Compare current text to cached previous text
- Identify added slides (new slide numbers)
- Identify removed slides (missing slide numbers)
- Identify modified slides (text content differs)
- Mark unchanged slides

**Acceptance Criteria:**
- [ ] Modified slides correctly detected when single word changes
- [ ] Added/removed slides correctly detected
- [ ] Change summary appears at top of markdown

#### FR-302: Version History

The system SHALL maintain version history in `version_history.json`:
```json
{
  "versions": [
    {
      "version": 1,
      "timestamp": "2026-01-10T14:30:00Z",
      "source_hash": "abc123def456",
      "source_path": "../../../sources/ClientA/market_sizing.pptx",
      "note": "Initial conversion",
      "changes": {
        "added": [1, 2, 3, 4, 5],
        "removed": [],
        "modified": [],
        "unchanged": []
      }
    }
  ]
}
```

#### FR-303: Staleness Detection

The system SHALL detect when source files have changed:
- Compare stored hash to current file hash
- Flag stale conversions in `status` output
- Include staleness warning in markdown frontmatter if detected during read

---

### 2.4 Library Organization (FR-400) — P1

#### FR-401: Directory Structure

The knowledge library SHALL follow this structure:
```
folio_library/
├── folio.yaml               # Configuration
├── registry.json            # Index of all decks
│
├── ClientA/
│   └── Project1/
│       └── market_sizing/
│           ├── market_sizing.md
│           ├── slides/
│           │   ├── slide-001.png
│           │   └── ...
│           ├── version_history.json
│           └── .texts_cache.json
│
├── Internal/
│   └── Templates/
│       └── ...
│
└── Research/
    └── Industry/
        └── ...
```

#### FR-402: Obsidian Frontmatter

Every markdown file SHALL include Obsidian-compatible YAML frontmatter aligned
to the Folio Ontology v2 baseline:
```yaml
---
id: clienta_ddq126_evidence_20260210_market-sizing
title: Market Sizing Analysis
source: ../../../sources/ClientA/Project1/market_sizing.pptx
source_hash: abc123def456
source_type: deck
version: 2
converted: 2026-01-10T14:30:00Z
client: ClientA
engagement: Due Diligence Q1 2026
type: evidence
subtype: research
status: current  # or "stale" if source changed
authority: captured
curation_level: L0
frameworks:
  - 2x2-matrix
  - scr
slide_types:
  - executive-summary
  - framework
  - data
tags:
  - market-sizing
  - competitive-analysis
---
```

#### FR-403: Registry

The system SHALL maintain a `registry.json` with:
- All converted decks
- Source paths and hashes
- Last conversion timestamp
- Current staleness status

---

### 2.5 CLI Commands (FR-500) — P1

#### FR-501: Convert Command
```bash
folio convert <source_file> [--note "version note"] [--target <library_path>] [--llm-profile <profile>]
```
- Convert single file to markdown
- Auto-detect target location from config or create new
- Generate LLM analysis using the configured route or explicit LLM profile
- Preserve deterministic single-profile behavior when `--llm-profile` is used

#### FR-502: Batch Command
```bash
folio batch <source_directory> [--pattern "*.pptx"] [--llm-profile <profile>]
```
- Convert all matching files
- Progress indicator
- Error handling per file (continue on failure)
- Summary output

#### FR-503: Status Command
```bash
folio status [<scope>]
```
- Show all decks and their status
- Flag stale conversions
- Flag missing source files
- Scope to client/engagement or any library-relative path if specified

#### FR-504: Scan Command
```bash
folio scan
```
- Find new files in source directories not yet converted
- Find source files that have changed since conversion
- Output actionable list

#### FR-505: Refresh Command
```bash
folio refresh [--scope <path>] [--all]
```
- Re-convert all stale decks
- Optionally scope to a specific client/engagement or library-relative path
- Update registry

---

### 2.6 LLM Provider Configuration (FR-600) — P1

#### FR-601: Multi-Provider Support

Folio SHALL support Anthropic, OpenAI, and Google Gemini for slide analysis.

#### FR-602: Bring Your Own Credentials

Folio SHALL accept provider credentials through environment variables referenced by configuration, and SHALL NOT require raw secrets in `folio.yaml`.

#### FR-603: Named LLM Profiles

Folio SHALL support named LLM profiles containing:
- Provider
- Model
- Environment variable reference for credentials

#### FR-604: Task Routing

Folio SHALL support route-based selection of LLM profiles by task:
- `routing.default` defines the fallback route for unspecified tasks
- `routing.convert` controls the `folio convert` analysis path in v1.0
- `--llm-profile` overrides route-based selection for a single command invocation

#### FR-605: Optional Transient Fallback

Folio SHALL support configured fallback chains for transient provider failures only.

#### FR-606: Execution Transparency

Folio SHALL record internal LLM execution metadata in output frontmatter, including the requested profile, actual provider/model used, fallback activation, and Pass 2 status.

#### FR-607: Graceful Degradation

Folio SHALL degrade to pending analysis without failing conversion when analysis cannot run because of missing credentials, missing SDKs, provider rejection, or exhausted transient fallbacks.

---

## 3. Non-Functional Requirements

### 3.1 Performance (NFR-100)

| Requirement | Target |
|-------------|--------|
| Conversion speed (no LLM) | <30 seconds for 20-slide deck |
| Conversion speed (with LLM) | <3 minutes for 20-slide deck |
| Batch processing | Process 50 decks in <30 minutes |
| Status command | <5 seconds for 500-deck library |

### 3.2 Reliability (NFR-200)

| Requirement | Target |
|-------------|--------|
| Text extraction accuracy | 99%+ character accuracy |
| Image extraction | 100% of slides captured |
| Source path validity | 100% of paths resolvable |
| Crash recovery | Never corrupt existing conversions |

### 3.3 Portability (NFR-300)

| Requirement | Target |
|-------------|--------|
| Path compatibility | Works on macOS, Linux, Windows |
| Sync compatibility | Works with OneDrive, Dropbox, iCloud |
| Obsidian compatibility | Opens as vault with no errors |

### 3.4 Usability (NFR-400)

| Requirement | Target |
|-------------|--------|
| Zero config start | Basic conversion works without config file |
| Error messages | Actionable (what failed, how to fix) |
| Progress feedback | Long operations show progress |

---

## 4. Data Schemas

### 4.1 Markdown Output Format

```markdown
---
id: clienta_ddq126_evidence_20260210_market-sizing
title: Market Sizing Analysis
source: ../../../sources/ClientA/Project1/market_sizing.pptx
source_hash: abc123def456
source_type: deck
version: 2
converted: 2026-01-10T14:30:00Z
client: ClientA
engagement: Due Diligence Q1 2026
type: evidence
subtype: research
status: current
authority: captured
curation_level: L0
frameworks:
  - 2x2-matrix
slide_types:
  - executive-summary
  - framework
tags:
  - market-sizing
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

# Market Sizing Analysis

**Source:** `../../../sources/ClientA/Project1/market_sizing.pptx`  
**Version:** 2 | **Converted:** 2026-01-10  
**Status:** ✓ Current

## Recent Changes

| Slides Modified | Slides Added | Slides Removed |
|-----------------|--------------|----------------|
| 2, 5 | — | — |

**Note:** Updated market size figures per client feedback

---

## Slide 1

![Slide 1](slides/slide-001.png)

### Text (Verbatim)

> Executive Summary
> 
> The total addressable market is $2.3B, growing at 12% CAGR
> - North America represents 45% of market
> - APAC is fastest growing region (18% CAGR)

### Analysis

**Slide Type:** executive-summary  
**Framework:** None  
**Key Data:** $2.3B TAM, 12% CAGR, 45% North America, 18% APAC growth  
**Main Insight:** Large and growing market with APAC as key growth driver

---

## Slide 2 *(modified)*

![Slide 2](slides/slide-002.png)

### Text (Verbatim)

> Market Segmentation
> 
> [2x2 matrix content...]

### Analysis

**Slide Type:** framework  
**Framework:** 2x2-matrix  
**Visual Description:** X-axis: Market Size (Small → Large), Y-axis: Growth Rate (Low → High). Four quadrants: TL=Niche, TR=Stars, BL=Dogs, BR=Cash Cows. Company positioned in "Stars" quadrant.  
**Key Data:** Market size ranges $100M-$5B, growth rates 2%-25%  
**Main Insight:** Company is well-positioned in high-growth, large-market segment

---

## Version History

| Version | Date | Changes | Note |
|---------|------|---------|------|
| v2 | 2026-01-10 | 2 modified | Updated market size figures |
| v1 | 2026-01-05 | Initial (5 slides) | First conversion |
```

### 4.2 Configuration Schema (folio.yaml)

```yaml
# Folio Configuration
version: 1

library_root: ./library

sources:
  - name: client-materials
    path: ../client_materials
    target_prefix: ""  # Maps to library root
    
  - name: internal
    path: ../internal
    target_prefix: Internal/
    
  - name: research
    path: /absolute/path/to/research
    target_prefix: Research/

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
  image_dpi: 150
  image_format: png
  libreoffice_timeout: 60
  default_passes: 1
  density_threshold: 2.0
  pptx_renderer: auto
```

Legacy shorthand remains valid for Anthropic-only setups:

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
```

---

## 5. Constraints and Assumptions

### 5.1 Technical Constraints

- PPTX→PDF conversion requires either LibreOffice or Microsoft PowerPoint,
  depending on platform and environment
- Poppler required for PDF→image conversion
- Python 3.10+
- Credential and SDK for the selected LLM provider/profile when AI analysis is enabled
- Supported providers: Anthropic, OpenAI, Google Gemini

### 5.2 Assumptions

- Users have Obsidian installed (or compatible markdown viewer)
- Source files are not password-protected
- Sufficient disk space (~100KB per slide for images)
- Network access for LLM API calls
- Provider credentials are managed through environment variables, not committed config

### 5.3 Platform Support

| Platform | Support Level |
|----------|---------------|
| macOS | Full |
| Linux | Full |
| Windows | Best effort (path handling may need testing) |
