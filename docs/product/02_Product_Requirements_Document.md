---
id: doc_02_product_requirements_document
type: atom
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Folio: Product Requirements Document

**Version 1.1 | March 2026**
**folio.love**

**v1.1 changes:** Added FR-700 (Trust & Reviewability) section per strategic
direction update. Revised FR-103 to require source grounding for LLM
extractions. Revised FR-607 to flag incomplete output rather than silently
filing it. Revised NFR-100 to establish quality as a hard floor with speed as
a soft target. Updated frontmatter examples with review schema fields.
See `docs/product/strategic_direction_memo.md` for governing principles.

---

## 1. Product Overview

### 1.1 Purpose

This document defines the requirements for Folio, a knowledge management system that converts consulting materials into an AI-native, searchable library. Requirements are prioritized by the hierarchy of value: conversion quality first, then version integrity, then organization features.

Folio's output must be trustworthy enough for direct use in active McKinsey engagements serving Fortune 100 clients. The quality bar is not "searchable and retrievable" but "a senior consultant can include this in a client deliverable without manually verifying every detail."

### 1.2 Scope

Folio v1.0 encompasses:
- Document conversion pipeline (PPTX/PDF to Markdown)
- Source file tracking with relative paths
- Version tracking and change detection
- Optional LLM analysis with bring-your-own provider credentials
- Knowledge library organization (multi-client, multi-engagement)
- Obsidian-compatible output format
- CLI for all operations
- Source grounding and extraction confidence scoring
- Review status tracking and human override persistence

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
| Source Grounding | Mapping from an extracted claim to the specific text that supports it |
| Extraction Confidence | Aggregate score (0.0-1.0) reflecting reliability of LLM analysis for a document |
| Review Status | Machine-tracked state indicating whether a document needs human attention |
| Human Override | A correction made by a human reviewer that persists across re-conversion |

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

The system SHALL generate grounded analysis for each slide using the configured LLM provider when valid credentials are available:
- **Slide Type:** title, executive-summary, framework, data, narrative, next-steps, appendix
- **Framework Detection:** 2x2-matrix, scr, mece, waterfall, gantt, timeline, process-flow, org-chart
- **Visual Description:** Axes labels, quadrant contents, chart types, spatial relationships
- **Key Data Points:** Numbers, percentages, metrics mentioned
- **Main Insight:** One-sentence summary of the "so what"
- **Source Grounding:** Every claim must cite the specific slide text that supports it (see FR-701)
- **Per-Claim Confidence:** Each grounded claim must include a confidence level (high/medium/low)

Supported providers in v1.0:
- Anthropic
- OpenAI
- Google Gemini

**Acceptance Criteria:**
- [ ] Every slide has all five analysis fields populated
- [ ] Framework detection correctly identifies common consulting frameworks
- [ ] Visual description captures information lost in text-only extraction
- [ ] Every claim includes a quoted text span and confidence level
- [ ] Quoted spans are validated against extracted text; unvalidated quotes are flagged
- [ ] If analysis cannot run, conversion succeeds with `review_status: flagged` and flag `analysis_unavailable`

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
- Per-slide sections with image, verbatim text, and grounded analysis
- Evidence block per slide showing claims with quoted sources and confidence
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
│           ├── .texts_cache.json
│           └── .overrides.json  # Human corrections (if any)
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
review_status: clean         # clean | flagged | reviewed | overridden
review_flags: []
extraction_confidence: 0.87
---
```

Here, `engagement` replaces `project` as the metadata field. Example source
paths and directory structures may still use project-style folder names without
changing the frontmatter contract.

#### FR-403: Registry

The system SHALL maintain a `registry.json` with:
- All converted decks
- Source paths and hashes
- Last conversion timestamp
- Current staleness status
- Review status and extraction confidence (for library-wide review queries)

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
- When duplicate-content or empty files are encountered, skip them without
  aborting the batch and report the skipped counts in summary output

#### FR-503: Status Command
```bash
folio status [<scope>]
```
- Show all decks and their status
- Flag stale conversions
- Flag missing source files
- Flag documents with `review_status: flagged`
- Scope to client/engagement or any library-relative path (any path relative to
  `library_root`) if specified

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
  (any path relative to `library_root`)
- Update registry
- Respect human overrides: do not overwrite sections recorded in `.overrides.json`

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

#### FR-607: Graceful Degradation with Explicit Flagging

Folio SHALL degrade to pending analysis without failing conversion when analysis
cannot run because of missing credentials, missing SDKs, provider rejection, or
exhausted transient fallbacks.

When degradation occurs, the system SHALL:
- Set `review_status: flagged` in frontmatter
- Add `analysis_unavailable` to `review_flags`
- Set `extraction_confidence: null`
- Display a visible warning in the markdown body (not just a placeholder)

The conversion still succeeds, but the output is explicitly marked as
incomplete. A document with pending analysis must never appear identical to a
fully analyzed document when browsing in Obsidian or querying via Dataview.

---

### 2.7 Trust & Reviewability (FR-700) — P0 CRITICAL

These requirements ensure that Folio's output meets the quality bar for
professional engagement use. They apply to all LLM-generated content across all
pipeline paths (conversion, ingestion, enrichment).

#### FR-701: Source Grounding

Every LLM-extracted claim SHALL include source grounding:
- A verbatim quoted text span (10-100 characters) from the source material
- The element type the quote came from (title, body, note, chart label)
- A per-claim confidence level (high, medium, low)

Quoted spans SHALL be validated against extracted text. If the quoted span does
not appear in the source material (case-insensitive, whitespace-normalized
fuzzy match), the claim SHALL be flagged as `unvalidated`.

**Acceptance Criteria:**
- [ ] Every LLM claim includes a quoted source span
- [ ] Validation correctly identifies matching and non-matching quotes
- [ ] Unvalidated claims are flagged, not silently discarded

#### FR-702: Extraction Confidence Scoring

Every document SHALL carry an aggregate `extraction_confidence` score (0.0-1.0)
computed from per-claim confidence levels:
- All claims high-confidence and validated: confidence approaches 1.0
- Mix of high and medium: confidence in 0.6-0.8 range
- Any low-confidence or unvalidated claims: confidence below 0.6
- No LLM analysis: `null`
- Whole-document source-text validation unavailable (for example, scanned PDFs
  with zero extracted text): confidence remains non-null and directionally
  meaningful when analysis succeeded; unavailable validation is not treated as
  failed validation

The exact scoring formula is an implementation detail and may be calibrated over
time. The requirement is that the score exists, is queryable, and is
directionally meaningful.

**Acceptance Criteria:**
- [ ] Every analyzed document has a non-null `extraction_confidence`
- [ ] Confidence is queryable via Dataview (`WHERE extraction_confidence < 0.7`)
- [ ] Confidence correlates with actual extraction quality on ground-truth fixtures
- [ ] Documents with unavailable source-text validation still receive a
  meaningful non-null confidence score when analysis succeeded

#### FR-703: Review Status Tracking

Every document SHALL carry a `review_status` field orthogonal to both
`curation_level` and `authority`:

| Status | Meaning |
|--------|---------|
| `clean` | No issues detected by the system |
| `flagged` | System detected issues requiring human attention |
| `reviewed` | Human has reviewed and confirmed the content |
| `overridden` | Human has corrected system output |

The system SHALL automatically set `review_status: flagged` when:
- Any extraction claim is unvalidated (quoted span not found in source)
- Any extraction claim has low confidence
- Analysis was unavailable (degraded conversion)
- Source-text validation was unavailable for the whole document (for example,
  scanned PDFs with zero extracted text)
- Extraction confidence is below a configurable threshold (default: 0.6)

Humans update `review_status` to `reviewed` or `overridden` manually or via
`folio promote` (promotion to L1+ may require `review_status != flagged`).

**Acceptance Criteria:**
- [ ] `review_status` is populated on every document
- [ ] Auto-flagging triggers on the defined conditions
- [ ] `folio status` reports flagged document count

#### FR-704: Review Flags

Every document SHALL carry a `review_flags` list that enumerates specific
issues detected by the system:

Example flags:
- `analysis_unavailable` — LLM analysis could not run
- `low_confidence_slide_N` — slide N has low-confidence extractions
- `unvalidated_claim_slide_N` — slide N has a quoted span that doesn't match source
- `text_validation_unavailable_slide_N` — slide N had no extracted text to
  validate against
- `text_validation_unavailable` — document-level text validation was
  unavailable
- `zero_text_extraction` — every reviewable slide lacked extractable text, so
  the document is flagged for review even if claim confidence remains high
- `high_density_unanalyzed` — dense slide only received single-pass analysis

Review flags are machine-generated. Humans clear them by resolving the
underlying issue or by setting `review_status: reviewed`.

**Acceptance Criteria:**
- [ ] Flags are specific and actionable (include slide numbers where applicable)
- [ ] Flags are queryable via Dataview
- [ ] Clearing `review_status` to `reviewed` does not delete the flags (they remain as historical record)

#### FR-705: Human Override Persistence

When a human corrects an extraction in the markdown body, that correction SHALL
persist across re-conversion (`folio refresh`).

Implementation: the system SHALL maintain a `.overrides.json` sidecar file per
deck that records which sections have been manually edited. During re-conversion,
the pipeline SHALL preserve overridden sections rather than regenerating them.

When an override is active:
- `review_status` SHALL be set to `overridden`
- The overridden sections SHALL be clearly marked in the markdown body
- Re-conversion SHALL warn (not error) that overrides were preserved

**Acceptance Criteria:**
- [ ] Manual edits to analysis sections survive `folio refresh`
- [ ] Overrides are recorded in `.overrides.json`
- [ ] `review_status: overridden` is set when overrides exist
- [ ] User can clear overrides to allow regeneration

#### FR-706: Extraction Provenance

Every LLM extraction SHALL record provenance metadata sufficient to answer
"which model produced this claim, when, and how":
- Model identifier (provider + model name)
- Extraction method (vision analysis, text extraction, OCR)
- Pass number (1 = breadth, 2 = depth)
- Timestamp

This metadata extends the existing `_llm_metadata` block in frontmatter.
Per-slide provenance is recorded in the markdown body alongside evidence blocks.
Document-level provenance remains in `_llm_metadata`.

**Acceptance Criteria:**
- [ ] Every extraction is traceable to a specific model and pass
- [ ] Provenance is recorded, not reconstructed
- [ ] Re-conversion with a different model produces updated provenance

---

## 3. Non-Functional Requirements

### 3.1 Performance & Quality (NFR-100)

Quality is a hard floor. Speed and cost are soft targets tracked for
transparency but never used to gate or throttle quality.

| Requirement | Type | Target |
|-------------|------|--------|
| Extraction accuracy | Hard floor | 99%+ character accuracy for text; directionally accurate for LLM claims |
| Image extraction | Hard floor | 100% of slides captured |
| Source path validity | Hard floor | 100% of paths resolvable |
| Conversion speed (no LLM) | Soft target | <30 seconds for 20-slide deck |
| Conversion speed (with LLM) | Soft target | Tracked, not capped. Multi-pass and validation may increase time. |
| Batch processing | Soft target | Tracked, not capped. |
| Status command | Soft target | <5 seconds for 500-deck library |
| LLM cost per deck | Tracked | Logged in `_llm_metadata` for auditability. Never gates quality decisions. |

### 3.2 Reliability (NFR-200)

| Requirement | Target |
|-------------|--------|
| Text extraction accuracy | 99%+ character accuracy |
| Image extraction | 100% of slides captured |
| Source path validity | 100% of paths resolvable |
| Crash recovery | Never corrupt existing conversions |
| Human override safety | Never silently overwrite human corrections |

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
| Review surfacing | Flagged documents visible in `folio status` and Dataview queries |

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
review_status: clean
review_flags: []
extraction_confidence: 0.91
grounding_summary:
  total_claims: 8
  high_confidence: 6
  medium_confidence: 2
  low_confidence: 0
  validated: 8
  unvalidated: 0
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

**Evidence:**
- **TAM identification (high):** "total addressable market is $2.3B" *(body)*
- **Growth rate (high):** "growing at 12% CAGR" *(body)*
- **Regional split (high):** "North America represents 45% of market" *(body)*
- **Growth driver (medium):** "APAC is fastest growing region (18% CAGR)" *(body)*

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

**Evidence:**
- **Framework identification (high):** "Market Segmentation" *(title)*
- **Positioning claim (medium):** "Company positioned in Stars quadrant" *(body, inferred from visual)*

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
  review_confidence_threshold: 0.6  # Below this, auto-flag for review
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

- PPTX→PDF conversion uses LibreOffice (Linux, unmanaged macOS) or Microsoft
  PowerPoint (managed macOS with `pptx_renderer: powerpoint`)
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
- Quality and accuracy take precedence over cost and processing time in all design decisions

### 5.3 Platform Support

| Platform | Support Level |
|----------|---------------|
| macOS | Full |
| Linux | Full |
| Windows | Best effort (path handling may need testing) |
