# folio

Your consulting portfolio, searchable and AI-ready.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)

## What It Does

Folio turns consulting artifacts into a structured, searchable knowledge base.

- **Deck conversion** — PPTX, PPT, and PDF presentations become structured Markdown with YAML frontmatter, slide images, and LLM-powered evidence extraction.
- **Interaction ingestion** — meeting transcripts and interview notes become structured interaction notes with grounded findings, entity mentions, and reviewability metadata.
- **Enrichment** — existing notes are enriched with auto-generated tags, entity wikilinks resolved against a shared registry, and relationship proposals between documents.
- **Provenance** — claim-level provenance links connect evidence across documents, with human-in-the-loop confirmation.

Folio tracks versions automatically -- re-converting an updated deck or re-ingesting a transcript increments the version, detects changes, and preserves history. Open `library/` as an Obsidian vault for automatic frontmatter indexing.

## Discovery Pipeline

folio organizes work in four tiers. Each tier builds on the ones below it:

- **Tier 1 — Source capture.** `folio convert` turns PPTX/PDF decks into searchable Markdown with extracted text, image analysis, and frontmatter.
- **Tier 2 — Interaction capture.** `folio ingest` takes meeting transcripts and expert-interview notes, tagging participants and extracting entity candidates.
- **Tier 3 — Entity system.** `folio entities` manages a canonical registry of people, departments, systems, and processes, with CSV import for org charts and LLM-proposed soft matches for human review.
- **Tier 4 — Discovery proposal layer.** `folio enrich` analyzes your library and proposes document-level relationships (`supersedes`, `impacts`, `draws_from`, `depends_on`). `folio links` surfaces those proposals for review; confirmed relationships become canonical frontmatter and feed a knowledge graph.

### Tier 4 in depth

Tier 4 turns ad-hoc notes into a structured knowledge graph without requiring you to hand-wire relationships. The flow:

1. **Enrichment produces proposals.** `folio enrich` reads each note and proposes relationships to other notes in the library. Each proposal carries a confidence grade, a basis fingerprint, a producer tag, and a lifecycle state (`queued`, `rejected`, `suppressed`, `accepted`).
2. **Review surfaces proposals.** `folio links review` shows the queue of pending proposals. Confirm promotes a proposal to canonical frontmatter; reject records the rejection so future enrichments remember not to re-propose the same relationship.
3. **Trust-gating keeps the queue clean.** Proposals involving documents with `review_status: flagged` are excluded by default. Use `--include-flagged` to inspect or act on them; the surface tags each proposal with which side (source, target, or both) is flagged.
4. **Rejection memory prevents churn.** Once you reject a proposal, subsequent `folio enrich` runs re-derive the same relationship but mark it `suppressed` instead of `queued` — it stays in frontmatter for audit but never re-enters your review queue until the underlying evidence changes.
5. **Queue-cap enforcement prevents flood.** No single producer may hold more than 20 queued proposals per library at a time. Excess is marked `suppressed`; you work through the top 20 and the next batch promotes automatically.

What's shipped as of v0.6.4: Slices 1–4 (rejection memory, lifecycle schema, emission-time filtering, trust-gating). What's next: acceptance-rate gate enforcement (Slice 5, awaiting field data) and entity-merge rejection memory + shared-consumer expansion (Slice 6+). See `docs/specs/tier4_discovery_proposal_layer_spec.md` for the full contract.

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

Show library health -- which decks are current, stale, or missing their source file. When an entity registry exists, status also reports the total entity count.

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

### `folio entities`

Manage the entity registry -- people, departments, systems, and processes mentioned across your library.

```bash
# List all entities, grouped by type
folio entities

# Filter by type or show only unconfirmed
folio entities --type person
folio entities --unconfirmed

# JSON export
folio entities --json

# Show detail for a specific entity
folio entities show "Alice Chen"
folio entities show "Engineering" --type department

# Import from a CSV org chart
folio entities import org_chart.csv

# Confirm or reject auto-extracted entities
folio entities confirm "Jane Smith"
folio entities reject "Jnae Smith"   # typo cleanup
```

**CSV import format** -- a `name` column is required; all others are optional:

| Column | Description |
|--------|-------------|
| `name` | Person's canonical name (required) |
| `title` | Job title |
| `department` | Department name (auto-created if new) |
| `reports_to` | Manager name (resolved to registry key) |
| `aliases` | Semicolon-separated alternate names |
| `client` | Associated client |

The entity registry is stored as `entities.json` alongside `registry.json` in the library root. Imported entities are confirmed automatically; entities extracted during future ingest passes will be marked as needing confirmation.

### `folio ingest`

Ingest a transcript or notes file into a structured interaction note.

```bash
# Basic ingest
folio ingest transcript.md --type expert_interview --date 2026-03-21

# With full metadata
folio ingest ./transcripts/cto_interview.md \
  --type expert_interview \
  --date 2026-03-21 \
  --client ClientA \
  --engagement "DD Q1 2026" \
  --participants "Jane Smith,John Doe" \
  --duration-minutes 45 \
  --note "initial ingest from cleaned transcript"

# Re-ingest an updated transcript (version increment)
folio ingest ./transcripts/cto_interview.md \
  --type expert_interview \
  --date 2026-03-21 \
  --target library/clienta/ddq126/interactions/2026-03-21_cto_interview/2026-03-21_cto_interview.md
```

**Flags**

| Flag | Description |
|------|-------------|
| `--type` | **Required.** Interaction subtype: `client_meeting`, `expert_interview`, `internal_sync`, `partner_check_in`, `workshop` |
| `--date` | **Required.** Event date (`YYYY-MM-DD`); must not be in the future |
| `--client` | Client name |
| `--engagement` | Engagement identifier |
| `--participants` | Comma-separated participant names |
| `--duration-minutes` | Meeting duration in minutes |
| `--source-recording` | Path to source recording (stored as metadata) |
| `--title` | Override note title (defaults to first H1 or source filename) |
| `--target` | Override output path; point at an existing `.md` to re-ingest |
| `--llm-profile` | Override the configured LLM profile for this run |
| `--note`, `-n` | Version note |

The output is a structured Markdown interaction note containing: a summary, key findings (claims, data points, decisions, open questions), extracted entities as Obsidian wikilinks, grounded quotes with confidence scores, and a collapsed raw transcript. If LLM analysis is unavailable, a degraded note is written with visible warning flags.

Re-ingesting the same source file increments the version rather than creating a duplicate. Identity is resolved by source path, then by content hash.

### `folio enrich`

Enrich existing evidence and interaction notes with tags, entity wikilinks, and relationship proposals.

```bash
# Enrich all eligible notes
folio enrich

# Scope to a client or engagement
folio enrich ClientA
folio enrich ClientA/DD_Q1_2026

# Preview without writing
folio enrich --dry-run

# Force re-enrichment even if fingerprint matches
folio enrich --force
```

Enrichment runs three axes per note:

1. **Tags** — additive merge of LLM-suggested tags with existing tags.
2. **Entities** — mentions are resolved against the entity registry; new names are auto-created as unconfirmed entries with optional proposed matches to existing entities.
3. **Relationships** — `supersedes` and `impacts` proposals between notes in the same engagement, surfaced for human confirmation.

Notes above `L0` curation level or with `reviewed`/`overridden` review status are protected from body mutation. Enrichment is idempotent: a content fingerprint prevents redundant LLM calls unless the note body, entity registry, or relationship context has changed.

### `folio links`

Review and manage document-level relationship proposals.

```bash
# Review pending proposals
folio links review                          # all scopes
folio links review ClientA                  # scoped to a client
folio links review --doc source_doc_id      # one source document
folio links review --target target_doc_id   # proposals pointing at one target
folio links review --page 2                 # paginate (20 per page)
folio links review --include-flagged        # include flagged-input proposals

# Per-document summary
folio links status                          # pending + confirmed counts per source
folio links status --include-flagged        # count flagged-input proposals as pending

# Act on individual proposals
folio links confirm <proposal_id>           # promote to canonical frontmatter
folio links reject <proposal_id>            # record rejection (rejection memory)
folio links confirm <proposal_id> --include-flagged   # consent to act on flagged-input
folio links reject <proposal_id> --include-flagged

# Bulk actions for one source document
folio links confirm-doc <doc_id>
folio links reject-doc <doc_id>
folio links confirm-doc <doc_id> --include-flagged
```

`folio enrich` produces relationship proposals; `folio links` surfaces them for review. Each proposal includes source and target document IDs, a relation (`supersedes`, `impacts`, `draws_from`, `depends_on`), a confidence grade, the producer, and a rationale. Confirming a proposal writes the relationship into canonical frontmatter (`impacts: [...]`, `supersedes: ...`) and records a confirmation receipt under `_llm_metadata.links`; rejecting records a fingerprint so the same relationship never re-enters the review queue.

Proposals involving documents with `review_status: flagged` are excluded from all default surfaces (`review`, `status`, and bulk actions). Pass `--include-flagged` to inspect or act on them; the output annotates each with `(flagged: source)`, `(flagged: target)`, or `(flagged: source, target)` so operators see exactly which side is untrusted. When all pending proposals are filtered by trust-gating, surfaces disclose the excluded count rather than silently reporting empty.

### `folio provenance`

Generate and manage claim-level provenance links between evidence documents.

```bash
# Evaluate all eligible pairs
folio provenance
folio provenance ClientA/DD_Q1_2026

# Preview without writing
folio provenance --dry-run

# Review pending proposals
folio provenance review
folio provenance review --doc source_doc_id

# Confirm or reject proposals
folio provenance confirm <proposal_id>
folio provenance reject <proposal_id>
folio provenance confirm-doc <doc_id>

# Check coverage
folio provenance status

# Manage stale links
folio provenance stale refresh-hashes <link_id>
folio provenance stale acknowledge <link_id>
folio provenance stale remove <link_id>
```

Provenance links connect specific claims in a source document to supporting evidence in target documents. All links require human confirmation before becoming canonical. Stale links (where the underlying evidence has changed) are surfaced for review.

### `folio context`

Scaffold an engagement context document.

```bash
folio context init --client "Acme" --engagement "DD Q1 2026"
folio context init --client "Acme" --engagement "Ops Sprint" --target ./custom/path/
```

Creates a structured `_context.md` with sections for client background, engagement snapshot, objectives, timeline, team, stakeholders, starting hypotheses, and risks. The document is registered at `L1` curation level and serves as the engagement anchor in the knowledge graph.

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

### Deck Conversion (`folio convert`)

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

### Interaction Ingestion (`folio ingest`)

```
Input (.txt/.md transcript)
  │
  ├─ Normalize ──→ Strip frontmatter, normalize whitespace
  │
  ├─ Analysis ───→ LLM extraction: summary, findings, entities, quotes
  │                 Confidence scoring + source-text validation
  │
  ├─ Entities ───→ Resolve mentions against entity registry
  │                 Auto-create unconfirmed entries for new names
  │
  ├─ Identity ───→ Re-ingest detection (path → hash → new)
  │
  └─ Assembly ───→ Interaction note with grounded findings + raw transcript
```

### Enrichment (`folio enrich`)

```
Existing evidence/interaction note
  │
  ├─ Plan ───────→ Fingerprint check, protection rules, disposition
  │
  ├─ Tags ───────→ LLM-suggested tags, additive merge
  │
  ├─ Entities ───→ Mention extraction → registry resolution
  │                 Wikilink injection into managed sections
  │
  ├─ Relations ──→ Peer context → LLM relationship evaluation
  │                 Proposals: supersedes, impacts
  │
  └─ Write ──────→ Frontmatter update + managed body sections (atomic)
```

### Provenance (`folio provenance`)

```
Source note × Target note
  │
  ├─ Extract ────→ Structured evidence items from both documents
  │
  ├─ Shard ──────→ Split into context-window-sized evaluation chunks
  │
  ├─ Evaluate ───→ LLM claim-to-evidence matching per shard
  │
  ├─ Proposals ──→ Pending human confirmation (confirm/reject)
  │
  └─ Links ──────→ Canonical provenance links with staleness tracking
```

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
├── cli.py              # Click CLI (all commands)
├── config.py           # FolioConfig + folio.yaml loading
├── converter.py        # Deck conversion orchestrator
├── ingest.py           # Interaction ingestion orchestrator
├── enrich.py           # Enrichment pipeline (tags, entities, relationships)
├── provenance.py       # Retroactive provenance linking
├── context.py          # Engagement context document creation
├── entity_import.py    # CSV org chart → entity registry
├── naming.py           # Shared naming helpers (IDs, slugs, engagement-short)
├── lock.py             # Library-level file locking
├── llm/                # LLM provider abstraction + runtime
├── pipeline/
│   ├── normalize.py    # PPTX/PPT → PDF
│   ├── images.py       # PDF → slide images + blank detection
│   ├── text.py         # Structured text extraction + reconciliation
│   ├── analysis.py     # LLM analysis + caching (deck conversion)
│   ├── interaction_analysis.py   # LLM analysis (interaction ingestion)
│   ├── enrich_analysis.py        # LLM analysis (enrichment)
│   ├── enrich_data.py            # Enrichment data structures + fingerprinting
│   ├── entity_resolution.py      # Entity mention → registry resolution
│   ├── provenance_analysis.py    # LLM provenance matching
│   ├── provenance_data.py        # Provenance data structures + hashing
│   └── section_parser.py         # Markdown section parser (managed sections)
├── output/
│   ├── frontmatter.py  # YAML frontmatter (v2 schema, evidence + interaction)
│   ├── markdown.py     # Markdown assembly (evidence notes)
│   └── interaction_markdown.py   # Markdown assembly (interaction notes)
└── tracking/
    ├── entities.py     # Entity registry (people, departments, systems, processes)
    ├── registry.py     # Document registry + atomic JSON writes
    ├── sources.py      # Source file tracking + staleness
    └── versions.py     # Version detection + change sets
```

## Framework bundle source

The `frameworks/llm-dev-v1/` directory is a verbatim copy of the canonical bundle maintained in `ohjonathan/johnny-os`. Folio is an adopter, not the framework maintainer — do not modify the bundle in this repo. Framework friction is captured in `docs/retros/llm-dev-v1-adoption.md`, filed upstream as issues on `ohjonathan/johnny-os`, and resynced via `scripts/resync-bundle.sh` after each johnny-os release. Full contract at [`docs/framework-adoption.md`](docs/framework-adoption.md).

## Roadmap

- **Tier 4 discovery proposal layer** — shipped through Slice 4 (v0.6.4). Remaining: acceptance-rate gate enforcement (Slice 5, awaiting field data) and entity-merge rejection memory + shared-consumer expansion (Slice 6+).
- **Daily digest** (`folio digest`) -- summarize recent library activity across engagements (planned; depends on Slice 6+ shared-consumer expansion).
- **Search and retrieval** (`folio search`) -- not yet implemented. Today, converted decks are searchable via Obsidian, grep, or any tool that reads Markdown + YAML frontmatter.

## License

Apache 2.0
